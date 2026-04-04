"""Unit tests for PiiDetector — all four entity types plus multi-entity cells."""

from __future__ import annotations

import re

import pytest
import spacy.util

from xlcloak.detector import PiiDetector
from xlcloak.models import CellRef, EntityType
from xlcloak.token_engine import TokenRegistry

# Skip the entire module if the spaCy model is not installed.
# Tests pass locally once `python -m spacy download en_core_web_lg` has been run.
pytestmark = pytest.mark.skipif(
    not spacy.util.is_package("en_core_web_lg"),
    reason="spaCy model en_core_web_lg not installed",
)


# ---------------------------------------------------------------------------
# Module-scoped fixtures (AnalyzerEngine is expensive to init)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def detector() -> PiiDetector:
    """Return a shared PiiDetector instance (model loaded once per test module)."""
    return PiiDetector(score_threshold=0.4)


@pytest.fixture
def registry() -> TokenRegistry:
    """Return a fresh TokenRegistry for each test."""
    return TokenRegistry()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EMAIL_TOKEN_RE = re.compile(r"^EMAIL_\d{3}@example\.com$")
_PHONE_TOKEN_RE = re.compile(r"^\+10-000-000-\d{3}$")
_URL_TOKEN_RE = re.compile(r"^https://example\.com/URL_\d{3}$")
_PERSON_TOKEN_RE = re.compile(r"^PERSON_\d{3}$")
_ORG_TOKEN_RE = re.compile(r"^ORG_\d{3}$")


def _make_cell(value: str) -> CellRef:
    return CellRef(sheet_name="Sheet1", row=1, col=1, value=value)


# ---------------------------------------------------------------------------
# Per-entity-type tests
# ---------------------------------------------------------------------------


def test_email_detection(detector: PiiDetector, registry: TokenRegistry) -> None:
    cell = _make_cell("contact user@example.com for details")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    email_results = [r for r in scan_results if r.entity_type == EntityType.EMAIL]
    assert len(email_results) >= 1, "Expected at least one EMAIL result"

    result = email_results[0]
    assert result.original == "user@example.com"
    assert _EMAIL_TOKEN_RE.match(result.token), f"Token {result.token!r} doesn't match email pattern"
    assert result.original not in replaced_text
    assert result.token in replaced_text


def test_phone_detection(detector: PiiDetector, registry: TokenRegistry) -> None:
    cell = _make_cell("call (555) 123-4567 to confirm")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    phone_results = [r for r in scan_results if r.entity_type == EntityType.PHONE]
    assert len(phone_results) >= 1, "Expected at least one PHONE result"

    result = phone_results[0]
    # Presidio may normalise the number slightly; check it came from the cell
    assert result.original in cell.value
    assert _PHONE_TOKEN_RE.match(result.token), f"Token {result.token!r} doesn't match phone pattern"
    assert result.original not in replaced_text
    assert result.token in replaced_text


def test_url_detection(detector: PiiDetector, registry: TokenRegistry) -> None:
    cell = _make_cell("visit https://acme.com/page for info")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    url_results = [r for r in scan_results if r.entity_type == EntityType.URL]
    assert len(url_results) >= 1, "Expected at least one URL result"

    result = url_results[0]
    assert "acme.com" in result.original
    assert _URL_TOKEN_RE.match(result.token), f"Token {result.token!r} doesn't match URL pattern"
    assert result.original not in replaced_text
    assert result.token in replaced_text


def test_person_detection(detector: PiiDetector, registry: TokenRegistry) -> None:
    """Requires en_core_web_lg NER model."""
    cell = _make_cell("Manager: John Smith is responsible")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    person_results = [r for r in scan_results if r.entity_type == EntityType.PERSON]
    assert len(person_results) >= 1, "Expected at least one PERSON result"

    result = person_results[0]
    assert "John" in result.original or "Smith" in result.original
    assert _PERSON_TOKEN_RE.match(result.token), f"Token {result.token!r} doesn't match person pattern"


def test_org_detection(detector: PiiDetector, registry: TokenRegistry) -> None:
    """Requires en_core_web_lg NER model."""
    cell = _make_cell("Works at Microsoft Corporation in Seattle")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    org_results = [r for r in scan_results if r.entity_type == EntityType.ORG]
    assert len(org_results) >= 1, "Expected at least one ORG result"

    result = org_results[0]
    assert "Microsoft" in result.original
    assert _ORG_TOKEN_RE.match(result.token), f"Token {result.token!r} doesn't match org pattern"


# ---------------------------------------------------------------------------
# Multi-entity cell tests
# ---------------------------------------------------------------------------


def test_multi_entity_cell(detector: PiiDetector, registry: TokenRegistry) -> None:
    """Both PERSON and EMAIL in same cell — offsets must not corrupt each other."""
    cell = _make_cell("Contact John Smith at john@acme.com for support")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    email_results = [r for r in scan_results if r.entity_type == EntityType.EMAIL]
    person_results = [r for r in scan_results if r.entity_type == EntityType.PERSON]

    assert len(email_results) >= 1, "Expected at least one EMAIL in multi-entity cell"
    assert len(person_results) >= 1, "Expected at least one PERSON in multi-entity cell"

    # Original PII must not appear in replaced text
    assert "john@acme.com" not in replaced_text
    assert "John Smith" not in replaced_text

    # Token patterns must appear in replaced text
    assert any(_EMAIL_TOKEN_RE.match(r.token) for r in email_results)
    assert any(_PERSON_TOKEN_RE.match(r.token) for r in person_results)
    for r in email_results + person_results:
        assert r.token in replaced_text

    # Surrounding context must be preserved
    assert "Contact" in replaced_text
    assert "for support" in replaced_text


# ---------------------------------------------------------------------------
# Determinism test
# ---------------------------------------------------------------------------


def test_same_value_same_token(detector: PiiDetector, registry: TokenRegistry) -> None:
    """Same email value in two different cells must yield the same token."""
    cell_a = CellRef(sheet_name="Sheet1", row=1, col=1, value="Send to alice@corp.com please")
    cell_b = CellRef(sheet_name="Sheet2", row=5, col=3, value="Reply to alice@corp.com now")

    results_a, _ = detector.detect_cell(cell_a, registry)
    results_b, _ = detector.detect_cell(cell_b, registry)

    emails_a = [r for r in results_a if r.entity_type == EntityType.EMAIL]
    emails_b = [r for r in results_b if r.entity_type == EntityType.EMAIL]

    assert len(emails_a) >= 1
    assert len(emails_b) >= 1

    assert emails_a[0].token == emails_b[0].token, (
        f"Same original should yield same token; got {emails_a[0].token!r} vs {emails_b[0].token!r}"
    )


# ---------------------------------------------------------------------------
# No-PII test
# ---------------------------------------------------------------------------


def test_no_pii_returns_empty(detector: PiiDetector, registry: TokenRegistry) -> None:
    """Non-PII text must return empty scan_results and unchanged replaced_text."""
    cell = _make_cell("Q1 revenue was 5000 units sold")
    scan_results, replaced_text = detector.detect_cell(cell, registry)

    assert scan_results == [], f"Expected no scan results, got {scan_results}"
    assert replaced_text == cell.value, "replaced_text must equal cell.value when no PII found"
