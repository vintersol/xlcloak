"""CLI integration tests for the xlcloak sanitize command."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import spacy.util
from click.testing import CliRunner

from xlcloak.cli import main
from xlcloak.sanitizer import derive_output_paths

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


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_sanitize_produces_outputs(tmp_path: Path) -> None:
    """sanitize command exits 0 and produces three output files."""
    fixture = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, fixture)

    runner = CliRunner()
    result = runner.invoke(main, ["sanitize", str(fixture)])

    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"

    sanitized, bundle, manifest = derive_output_paths(fixture)
    assert sanitized.exists(), f"Sanitized file not found: {sanitized}"
    assert bundle.exists(), f"Bundle file not found: {bundle}"
    assert manifest.exists(), f"Manifest file not found: {manifest}"


def test_cli_sanitize_overwrite_protection(tmp_path: Path) -> None:
    """Second invocation without --force exits non-zero with --force hint."""
    fixture = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, fixture)

    runner = CliRunner()
    runner.invoke(main, ["sanitize", str(fixture)])  # first run

    result = runner.invoke(main, ["sanitize", str(fixture)])  # second run
    assert result.exit_code != 0, "Expected non-zero exit on overwrite without --force"
    assert "--force" in result.output, f"Expected --force hint in output: {result.output!r}"


def test_cli_sanitize_output_flag(tmp_path: Path) -> None:
    """--output flag redirects sanitized file to specified path."""
    fixture = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, fixture)

    custom_output = tmp_path / "out" / "custom.xlsx"
    custom_output.parent.mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(main, ["sanitize", str(fixture), "--output", str(custom_output)])

    assert result.exit_code == 0, f"Expected exit 0: {result.output}"
    sanitized, bundle, manifest = derive_output_paths(fixture, custom_output)
    assert sanitized.exists(), f"Sanitized file not found: {sanitized}"
    assert bundle.exists(), f"Bundle file not found: {bundle}"
    assert manifest.exists(), f"Manifest file not found: {manifest}"


def test_cli_sanitize_default_password_warning(tmp_path: Path) -> None:
    """Invoking sanitize without --password shows default password warning."""
    fixture = tmp_path / "simple.xlsx"
    shutil.copy2(SIMPLE_FIXTURE, fixture)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["sanitize", str(fixture)])

    # Warning goes to stderr; mix_stderr=False keeps them separate
    assert "default password" in result.stderr, (
        f"Expected 'default password' in stderr: {result.stderr!r}"
    )
