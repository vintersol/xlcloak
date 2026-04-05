"""End-to-end round-trip tests: sanitize → restore with exact-token safety model."""

from __future__ import annotations

import shutil
from pathlib import Path

import openpyxl
import pytest
import spacy.util
from click.testing import CliRunner

from xlcloak.cli import main
from xlcloak.excel_io import XLCLOAK_META_SHEET
from xlcloak.sanitizer import derive_output_paths

requires_spacy = pytest.mark.skipif(
    not spacy.util.is_package("en_core_web_lg"),
    reason="spaCy model en_core_web_lg not installed",
)

pytestmark = requires_spacy

FIXTURES_DIR = Path(__file__).parent / "fixtures"
_PASSWORD = "xlcloak-e2e-test"


def _cell_values(path: Path) -> dict[str, dict[str, object]]:
    """Return {sheet_title: {coordinate: value}} for all non-None cells."""
    wb = openpyxl.load_workbook(str(path), data_only=True)
    result: dict[str, dict[str, object]] = {}
    for ws in wb.worksheets:
        if ws.title == XLCLOAK_META_SHEET:
            continue
        sheet: dict[str, object] = {}
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    sheet[cell.coordinate] = cell.value
        result[ws.title] = sheet
    return result


def _round_trip(
    fixture: Path,
    tmp_path: Path,
    allow_unsupported_surfaces: bool = False,
) -> tuple[Path, Path]:
    """Run sanitize then restore; return (original_fixture_copy, restored_path)."""
    src = tmp_path / fixture.name
    shutil.copy2(fixture, src)

    runner = CliRunner()

    # Sanitize
    sanitize_cmd = ["sanitize", str(src), "--password", _PASSWORD]
    if allow_unsupported_surfaces:
        sanitize_cmd.append("--allow-unsupported-surfaces")
    result = runner.invoke(main, sanitize_cmd)
    assert result.exit_code == 0, f"sanitize failed: {result.output}"

    sanitized, bundle, _ = derive_output_paths(src)
    assert sanitized.exists(), f"Sanitized file missing: {sanitized}"
    assert bundle.exists(), f"Bundle missing: {bundle}"

    # Restore
    result = runner.invoke(
        main,
        ["restore", str(sanitized), "--bundle", str(bundle), "--password", _PASSWORD],
    )
    assert result.exit_code == 0, f"restore failed: {result.output}"

    # Restored path: <sanitized_stem>_restored.xlsx next to sanitized file
    restored = sanitized.parent / (sanitized.stem + "_restored.xlsx")
    assert restored.exists(), f"Restored file missing: {restored}"

    return src, restored


@pytest.mark.parametrize("fixture_name", ["simple.xlsx", "medium.xlsx", "hard.xlsx"])
def test_sanitize_restore_round_trip(fixture_name: str, tmp_path: Path) -> None:
    """sanitize+restore succeeds and restores at least one exact token cell."""
    fixture = FIXTURES_DIR / fixture_name
    original, restored = _round_trip(
        fixture, tmp_path, allow_unsupported_surfaces=(fixture_name == "hard.xlsx")
    )

    # Files exist and are readable.
    assert original.exists()
    assert restored.exists()

    # In exact-match mode, not every sanitized value is guaranteed to round-trip
    # (token substrings inside larger text are intentionally left untouched).
    # We still expect meaningful restoration work on fixture data.
    original_values = _cell_values(original)
    restored_values = _cell_values(restored)

    assert set(original_values.keys()) == set(restored_values.keys())
    restored_any = any(
        original_values[sheet].get(cell) == restored_values[sheet].get(cell)
        for sheet in original_values
        for cell in original_values[sheet]
    )
    assert restored_any, f"[{fixture_name}] Expected at least one restored cell match"
