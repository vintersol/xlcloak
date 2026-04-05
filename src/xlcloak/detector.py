"""PII detection pipeline wrapping Presidio AnalyzerEngine."""

from __future__ import annotations

import warnings

import spacy.util
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from xlcloak.models import CellRef, EntityType, ScanResult
from xlcloak.recognizers import (
    CompanySuffixRecognizer,
    LoosePhoneRecognizer,
    SweOrgNummerRecognizer,
    SwePersonnummerRecognizer,
)
from xlcloak.token_engine import TokenRegistry

# Mapping from Presidio entity names to xlcloak EntityType values
PRESIDIO_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "EMAIL_ADDRESS": EntityType.EMAIL,
    "PHONE_NUMBER": EntityType.PHONE,
    "PERSON": EntityType.PERSON,
    "URL": EntityType.URL,
    "ORGANIZATION": EntityType.ORG,
    "PERSONNUMMER_SE": EntityType.SSN_SE,    # SwePersonnummerRecognizer
    "ORGNUM_SE": EntityType.ORGNUM_SE,       # SweOrgNummerRecognizer
    "COMPANY_SUFFIX": EntityType.ORG,        # CompanySuffixRecognizer
}

# Entity names to pass to AnalyzerEngine.analyze() — avoids unwanted types
# like credit cards, IBANs, crypto wallets, etc.
PHASE2_ENTITIES: list[str] = list(PRESIDIO_TO_ENTITY_TYPE.keys())

# PII-indicating column header keywords for context boosting (D-12)
_PII_HEADER_KEYWORDS = frozenset({
    "name", "customer", "contact", "email", "phone",
    "company", "ssn", "personid", "personnummer", "organisation",
})

_BOOSTED_THRESHOLD = 0.3  # Used when column header indicates PII context

_OBVIOUS_HEADER_LABELS = frozenset({
    "name",
    "full name",
    "first name",
    "last name",
    "customer",
    "customer name",
    "contact",
    "contact name",
    "email",
    "email address",
    "e-mail",
    "phone",
    "phone number",
    "mobile",
    "company",
    "company name",
    "organization",
    "organisation",
    "ssn",
    "person id",
    "personid",
    "personnummer",
})


def _header_matches_pii_keyword(header: str | None) -> bool:
    """Return True if the column header contains a PII-indicating keyword."""
    if not header:
        return False
    lower = header.lower()
    return any(kw in lower for kw in _PII_HEADER_KEYWORDS)


def _is_obvious_header_label(text: str) -> bool:
    """Return True if text looks like a schema/header label, not user content."""
    normalized = " ".join(text.lower().replace("_", " ").replace("-", " ").split())
    return normalized in _OBVIOUS_HEADER_LABELS


class PiiDetector:
    """Wraps Presidio AnalyzerEngine with lazy initialization and entity mapping.

    The spaCy model is only loaded on first use, so import time is fast.
    """

    def __init__(self, score_threshold: float = 0.4) -> None:
        """Initialize PiiDetector.

        Args:
            score_threshold: Minimum confidence score for a result to be
                included. 0.4 is aggressive — favours recall over precision,
                appropriate for an exposure-reduction tool.
        """
        self._threshold = score_threshold
        self._analyzer: AnalyzerEngine | None = None

    def _get_analyzer(self) -> AnalyzerEngine:
        """Return the cached AnalyzerEngine, initializing it on first call.

        Raises:
            RuntimeError: If the spaCy model 'en_core_web_lg' is not installed.
        """
        if self._analyzer is not None:
            return self._analyzer

        if not spacy.util.is_package("en_core_web_lg"):
            raise RuntimeError(
                "spaCy model 'en_core_web_lg' not installed. "
                "Run: python -m spacy download en_core_web_lg"
            )

        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            }
        )
        self._analyzer = AnalyzerEngine(
            nlp_engine=provider.create_engine(),
            supported_languages=["en"],
            default_score_threshold=self._threshold,
        )
        self._analyzer.registry.add_recognizer(SwePersonnummerRecognizer())
        self._analyzer.registry.add_recognizer(SweOrgNummerRecognizer())
        self._analyzer.registry.add_recognizer(CompanySuffixRecognizer())
        self._analyzer.registry.add_recognizer(LoosePhoneRecognizer())
        return self._analyzer

    def detect_cell(
        self,
        cell: CellRef,
        registry: TokenRegistry,
        column_header: str | None = None,
    ) -> tuple[list[ScanResult], str]:
        """Detect PII in a single cell and return results plus replaced text.

        Replacements are applied right-to-left so that earlier offsets remain
        valid after each substitution (D-03).

        Args:
            cell: The cell to scan. ``cell.value`` must not be ``None``.
            registry: Token registry used to look up or mint stable tokens.
            column_header: Optional column header text. If it contains a PII
                keyword, the score threshold is lowered to 0.3 to accept
                lower-confidence matches.

        Returns:
            A two-tuple ``(scan_results, replaced_text)`` where:
            - ``scan_results`` is a list of :class:`ScanResult` in
              left-to-right (document) order.
            - ``replaced_text`` is the cell text with all PII replaced by
              tokens.

        Raises:
            AssertionError: If ``cell.value`` is ``None``.
        """
        if cell.value is None:
            raise ValueError("cell.value must not be None")

        analyzer = self._get_analyzer()
        threshold = _BOOSTED_THRESHOLD if _header_matches_pii_keyword(column_header) else self._threshold
        raw_results = analyzer.analyze(
            text=cell.value,
            language="en",
            entities=PHASE2_ENTITIES,
            score_threshold=threshold,
        )

        # Suppress obvious header labels (for example "Email") that may be
        # misclassified by NER as PERSON.
        raw_results = [
            r
            for r in raw_results
            if not (
                r.entity_type == "PERSON"
                and r.start == 0
                and r.end == len(cell.value)
                and _is_obvious_header_label(cell.value)
            )
        ]

        # Deduplicate by span — keep highest-score result when two recognizers fire on same span
        seen_spans: dict[tuple[int, int], object] = {}
        for r in raw_results:
            key = (r.start, r.end)
            if key not in seen_spans or r.score > seen_spans[key].score:  # type: ignore[union-attr]
                seen_spans[key] = r
        deduped_results = list(seen_spans.values())

        # Remove overlapping spans — greedy selection by score (highest score wins).
        # Sort descending by score so higher-confidence results are selected first.
        # An EMAIL_ADDRESS and a URL recognizer may both fire on "user@acme.com",
        # producing non-identical but overlapping spans; without this step the
        # right-to-left replacement would shift offsets and corrupt output.
        scored_results = sorted(deduped_results, key=lambda r: r.score, reverse=True)
        non_overlapping: list[object] = []
        accepted_ranges: list[tuple[int, int]] = []
        for r in scored_results:
            overlaps = any(
                r.start < end and r.end > start  # type: ignore[union-attr]
                for start, end in accepted_ranges
            )
            if not overlaps:
                non_overlapping.append(r)
                accepted_ranges.append((r.start, r.end))  # type: ignore[union-attr]
        deduped_results = non_overlapping

        # Sort descending by start offset for safe right-to-left replacement
        sorted_results = sorted(deduped_results, key=lambda r: r.start, reverse=True)

        scan_results: list[ScanResult] = []
        replaced_text = cell.value

        for result in sorted_results:
            original = cell.value[result.start : result.end]
            entity_type = PRESIDIO_TO_ENTITY_TYPE.get(result.entity_type)
            if entity_type is None:
                warnings.warn(
                    f"Unknown Presidio entity type '{result.entity_type}' -- falling back to GENERIC",
                    stacklevel=2,
                )
                entity_type = EntityType.GENERIC
            token = registry.get_or_create(original, entity_type)
            detection_method = (
                "NER"
                if result.entity_type in ("PERSON", "ORGANIZATION")
                else "pattern"
            )
            scan_results.append(
                ScanResult(
                    cell=cell,
                    entity_type=entity_type,
                    original=original,
                    token=token,
                    score=result.score,
                    detection_method=detection_method,
                )
            )
            # Apply replacement right-to-left in replaced_text
            replaced_text = (
                replaced_text[: result.start] + token + replaced_text[result.end :]
            )

        # Return scan_results in left-to-right (document) order
        scan_results.reverse()

        return scan_results, replaced_text
