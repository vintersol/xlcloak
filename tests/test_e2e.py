"""End-to-end round-trip tests: sanitize → restore → identical cell values."""

from __future__ import annotations

import shutil
from pathlib import Path

import openpyxl
import pytest
import spacy.util
from click.testing import CliRunner

from xlcloak.cli import main
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
        sheet: dict[str, object] = {}
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    sheet[cell.coordinate] = cell.value
        result[ws.title] = sheet
    return result


def _round_trip(fixture: Path, tmp_path: Path) -> tuple[Path, Path]:
    """Run sanitize then restore; return (original_fixture_copy, restored_path)."""
    src = tmp_path / fixture.name
    shutil.copy2(fixture, src)

    runner = CliRunner()

    # Sanitize
    result = runner.invoke(main, ["sanitize", str(src), "--password", _PASSWORD])
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
    """sanitize followed by restore produces cell values identical to the original."""
    fixture = FIXTURES_DIR / fixture_name
    original, restored = _round_trip(fixture, tmp_path)

    original_values = _cell_values(original)
    restored_values = _cell_values(restored)

    assert set(original_values.keys()) == set(restored_values.keys()), (
        f"Sheet names differ.\n"
        f"  Original sheets: {sorted(original_values.keys())}\n"
        f"  Restored sheets: {sorted(restored_values.keys())}"
    )

    for sheet_title in original_values:
        orig_sheet = original_values[sheet_title]
        rest_sheet = restored_values[sheet_title]

        missing = {c: v for c, v in orig_sheet.items() if c not in rest_sheet}
        extra = {c: v for c, v in rest_sheet.items() if c not in orig_sheet}
        mismatched = {
            c: (orig_sheet[c], rest_sheet[c])
            for c in orig_sheet
            if c in rest_sheet and orig_sheet[c] != rest_sheet[c]
        }

        assert not missing, (
            f"[{fixture_name}] Sheet '{sheet_title}': cells present in original but missing from restored: {missing}"
        )
        assert not extra, (
            f"[{fixture_name}] Sheet '{sheet_title}': extra cells in restored not in original: {extra}"
        )
        assert not mismatched, (
            f"[{fixture_name}] Sheet '{sheet_title}': cell value mismatches (original → restored):\n"
            + "\n".join(f"  {c}: {o!r} → {r!r}" for c, (o, r) in mismatched.items())
        )
