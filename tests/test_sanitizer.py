"""Integration tests for the Sanitizer orchestrator."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
import pytest
import spacy.util

from xlcloak.detector import PiiDetector
from xlcloak.sanitizer import SanitizeResult, Sanitizer, derive_output_paths

# Skip entire module if spaCy model is not installed
pytestmark = pytest.mark.skipif(
    not spacy.util.is_package("en_core_web_lg"),
    reason="spaCy model en_core_web_lg not installed",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SIMPLE_FIXTURE = FIXTURES_DIR / "simple.xlsx"


@pytest.fixture(scope="module")
def detector() -> PiiDetector:
    """Return a shared PiiDetector (model loaded once per module)."""
    return PiiDetector(score_threshold=0.4)


# ---------------------------------------------------------------------------
# derive_output_paths tests
# ---------------------------------------------------------------------------


def test_derive_output_paths_default() -> None:
    """Default: paths derived from input path stem."""
    sanitized, bundle, manifest = derive_output_paths(Path("/tmp/data.xlsx"))
    assert sanitized == Path("/tmp/data_sanitized.xlsx")
    assert bundle == Path("/tmp/data.xlcloak")
    assert manifest == Path("/tmp/data_manifest.txt")


def test_derive_output_paths_with_override() -> None:
    """Override: paths derived from output override stem."""
    sanitized, bundle, manifest = derive_output_paths(
        input_path=Path("/tmp/data.xlsx"),
        output_override=Path("/out/custom.xlsx"),
    )
    assert sanitized == Path("/out/custom_sanitized.xlsx")
    assert bundle == Path("/out/custom.xlcloak")
    assert manifest == Path("/out/custom_manifest.txt")


# ---------------------------------------------------------------------------
# Sanitizer.run integration tests
# ---------------------------------------------------------------------------


def test_sanitize_produces_three_files(tmp_path: Path, detector: PiiDetector) -> None:
    """Running sanitize on a fixture produces sanitized xlsx, bundle, and manifest."""
    input_path = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, input_path)

    result = Sanitizer(detector).run(input_path)

    assert isinstance(result, SanitizeResult)
    assert result.sanitized_path.exists(), "Sanitized xlsx not created"
    assert result.bundle_path.exists(), "Bundle file not created"
    assert result.manifest_path.exists(), "Manifest file not created"


def test_sanitize_overwrite_protection(tmp_path: Path, detector: PiiDetector) -> None:
    """Second run without --force raises UsageError."""
    input_path = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, input_path)

    sanitizer = Sanitizer(detector)
    sanitizer.run(input_path)  # first run

    with pytest.raises(click.UsageError, match="--force"):
        sanitizer.run(input_path)  # second run without force


def test_sanitize_overwrite_with_force(tmp_path: Path, detector: PiiDetector) -> None:
    """Second run with force=True succeeds without error."""
    input_path = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, input_path)

    sanitizer = Sanitizer(detector)
    sanitizer.run(input_path)  # first run
    result = sanitizer.run(input_path, force=True)  # second run with force

    assert result.sanitized_path.exists()
    assert result.bundle_path.exists()
    assert result.manifest_path.exists()


def test_manifest_written(tmp_path: Path, detector: PiiDetector) -> None:
    """Manifest file contains expected header and entity breakdown section."""
    input_path = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, input_path)

    result = Sanitizer(detector).run(input_path)

    manifest_text = result.manifest_path.read_text()
    assert "xlcloak Manifest" in manifest_text
    assert "Entity breakdown:" in manifest_text
