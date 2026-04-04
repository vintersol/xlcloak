"""PII detection pipeline wrapping Presidio AnalyzerEngine."""

from __future__ import annotations

import spacy.util
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from xlcloak.models import CellRef, EntityType, ScanResult
from xlcloak.recognizers import (
    CompanySuffixRecognizer,
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

# Common English words that spaCy's NER frequently misclassifies as PERSON or ORGANIZATION.
# Only add words with evidence of false positives — keep this conservative.
NER_DENY_LIST: frozenset[str] = frozenset({
    "budget", "account", "contract", "invoice", "meeting",
    "report", "review", "manager", "project", "department",
    "office", "system", "service", "team", "group",
    "policy", "schedule", "plan", "proposal", "agreement",
})


def _header_matches_pii_keyword(header: str | None) -> bool:
    """Return True if the column header contains a PII-indicating keyword."""
    if not header:
        return False
    lower = header.lower()
    return any(kw in lower for kw in _PII_HEADER_KEYWORDS)


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
        assert cell.value is not None, "cell.value must not be None"

        analyzer = self._get_analyzer()
        threshold = _BOOSTED_THRESHOLD if _header_matches_pii_keyword(column_header) else self._threshold
        raw_results = analyzer.analyze(
            text=cell.value,
            language="en",
            entities=PHASE2_ENTITIES,
            score_threshold=threshold,
        )

        # Deduplicate by span — keep highest-score result when two recognizers fire on same span
        seen_spans: dict[tuple[int, int], object] = {}
        for r in raw_results:
            key = (r.start, r.end)
            if key not in seen_spans or r.score > seen_spans[key].score:  # type: ignore[union-attr]
                seen_spans[key] = r
        deduped_results = list(seen_spans.values())

        # Filter NER false positives: common English words tagged as PERSON/ORGANIZATION
        deduped_results = [
            r for r in deduped_results
            if not (
                r.entity_type in ("PERSON", "ORGANIZATION", "COMPANY_SUFFIX")
                and cell.value[r.start:r.end].lower() in NER_DENY_LIST
            )
        ]

        # Sort descending by start offset for safe right-to-left replacement
        sorted_results = sorted(deduped_results, key=lambda r: r.start, reverse=True)

        scan_results: list[ScanResult] = []
        replaced_text = cell.value

        for result in sorted_results:
            original = cell.value[result.start : result.end]
            entity_type = PRESIDIO_TO_ENTITY_TYPE[result.entity_type]
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
