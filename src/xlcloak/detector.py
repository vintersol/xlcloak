"""PII detection pipeline wrapping Presidio AnalyzerEngine."""

from __future__ import annotations

import spacy.util
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from xlcloak.models import CellRef, EntityType, ScanResult
from xlcloak.token_engine import TokenRegistry

# Mapping from Presidio entity names to xlcloak EntityType values
PRESIDIO_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "EMAIL_ADDRESS": EntityType.EMAIL,
    "PHONE_NUMBER": EntityType.PHONE,
    "PERSON": EntityType.PERSON,
    "URL": EntityType.URL,
    "ORGANIZATION": EntityType.ORG,
}

# Entity names to pass to AnalyzerEngine.analyze() — avoids unwanted types
# like credit cards, IBANs, crypto wallets, etc.
PHASE2_ENTITIES: list[str] = list(PRESIDIO_TO_ENTITY_TYPE.keys())


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
        return self._analyzer

    def detect_cell(
        self,
        cell: CellRef,
        registry: TokenRegistry,
    ) -> tuple[list[ScanResult], str]:
        """Detect PII in a single cell and return results plus replaced text.

        Replacements are applied right-to-left so that earlier offsets remain
        valid after each substitution (D-03).

        Args:
            cell: The cell to scan. ``cell.value`` must not be ``None``.
            registry: Token registry used to look up or mint stable tokens.

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
        raw_results = analyzer.analyze(
            text=cell.value,
            language="en",
            entities=PHASE2_ENTITIES,
            score_threshold=self._threshold,
        )

        # Sort descending by start offset for safe right-to-left replacement
        sorted_results = sorted(raw_results, key=lambda r: r.start, reverse=True)

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
