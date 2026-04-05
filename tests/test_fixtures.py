"""Fixture validation tests — structure, content, round-trip integrity, surface detection.

Tests validate the three .xlsx fixtures (simple/medium/hard) via the public
WorkbookReader / WorkbookWriter API. No direct openpyxl imports.

Requirements covered: TEST-01, TEST-02, TEST-03, TEST-04
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xlcloak.excel_io import WorkbookReader, WorkbookWriter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Cross-fixture tests (TEST-01)
# ---------------------------------------------------------------------------


def test_all_fixtures_exist() -> None:
    """All three .xlsx fixture files must be present on disk."""
    assert (FIXTURES_DIR / "simple.xlsx").exists()
    assert (FIXTURES_DIR / "medium.xlsx").exists()
    assert (FIXTURES_DIR / "hard.xlsx").exists()


def test_all_fixtures_readable() -> None:
    """WorkbookReader must open all three fixtures without raising exceptions."""
    for name in ("simple.xlsx", "medium.xlsx", "hard.xlsx"):
        reader = WorkbookReader(FIXTURES_DIR / name)
        wb = reader.open()
        assert wb is not None, f"Failed to open {name}"


# ---------------------------------------------------------------------------
# Simple fixture tests (TEST-02)
# ---------------------------------------------------------------------------


def test_simple_fixture_exists() -> None:
    """simple.xlsx exists at the expected path."""
    assert (FIXTURES_DIR / "simple.xlsx").exists()


def test_simple_single_sheet() -> None:
    """simple.xlsx has exactly one sheet named 'Contacts'."""
    reader = WorkbookReader(FIXTURES_DIR / "simple.xlsx")
    wb = reader.open()
    assert wb.sheetnames == ["Contacts"]


def test_simple_has_headers() -> None:
    """First row of the Contacts sheet contains all expected column headers."""
    reader = WorkbookReader(FIXTURES_DIR / "simple.xlsx")
    wb = reader.open()
    ws = wb["Contacts"]
    headers = [ws.cell(row=1, column=c).value for c in range(1, 6)]
    assert "Name" in headers
    assert "Email" in headers
    assert "Phone" in headers
    assert "Company" in headers
    assert "Notes" in headers


def test_simple_has_pii_data() -> None:
    """iter_text_cells yields cells containing known PII: name, email, phone."""
    reader = WorkbookReader(FIXTURES_DIR / "simple.xlsx")
    wb = reader.open()
    all_values = [cell.value for cell in reader.iter_text_cells(wb)]

    assert any("John Smith" in v for v in all_values if v), "Missing name 'John Smith'"
    assert any("john.smith@acme.com" in v for v in all_values if v), "Missing email"
    assert any("+1-555-0101" in v for v in all_values if v), "Missing phone"


def test_simple_roundtrip(tmp_path: Path) -> None:
    """WorkbookWriter copy-then-patch round-trip: patched cell updated, others unchanged."""
    src = FIXTURES_DIR / "simple.xlsx"
    out = tmp_path / "simple_patched.xlsx"

    # Read original to find a known cell value
    reader = WorkbookReader(src)
    wb_orig = reader.open()
    ws_orig = wb_orig["Contacts"]
    original_name = ws_orig.cell(row=2, column=1).value  # "John Smith"

    # Patch name cell
    writer = WorkbookWriter(src, out)
    writer.patch_and_save([("Contacts", 2, 1, "PERSON_001")])

    # Verify patch applied
    reader2 = WorkbookReader(out)
    wb_patched = reader2.open()
    ws_patched = wb_patched["Contacts"]
    assert ws_patched.cell(row=2, column=1).value == "PERSON_001"

    # Verify other cells unchanged
    email_original = ws_orig.cell(row=2, column=2).value
    assert ws_patched.cell(row=2, column=2).value == email_original


def test_simple_no_warnings() -> None:
    """simple.xlsx has no unsupported surfaces: no formulas, comments, or charts."""
    reader = WorkbookReader(FIXTURES_DIR / "simple.xlsx")
    wb = reader.open()
    warnings = reader.scan_surfaces(wb)
    surface_types = [w.surface_type for w in warnings]
    assert "formula" not in surface_types
    assert "comment" not in surface_types
    assert "chart" not in surface_types


# ---------------------------------------------------------------------------
# Medium fixture tests (TEST-03)
# ---------------------------------------------------------------------------


def test_medium_fixture_exists() -> None:
    """medium.xlsx exists at the expected path."""
    assert (FIXTURES_DIR / "medium.xlsx").exists()


def test_medium_three_sheets() -> None:
    """medium.xlsx has exactly three sheets: Contacts, Transactions, Summary."""
    reader = WorkbookReader(FIXTURES_DIR / "medium.xlsx")
    wb = reader.open()
    assert wb.sheetnames == ["Contacts", "Transactions", "Summary"]


def test_medium_has_swedish_pii() -> None:
    """iter_text_cells yields cells with Swedish personnummer and org-nummer."""
    reader = WorkbookReader(FIXTURES_DIR / "medium.xlsx")
    wb = reader.open()
    all_values = [cell.value for cell in reader.iter_text_cells(wb)]

    assert any("199001151234" in v for v in all_values if v), "Missing Swedish personnummer"
    assert any("556677-8901" in v for v in all_values if v), "Missing Swedish org-nummer"


def test_medium_has_mixed_content_cells() -> None:
    """At least one cell contains both a name-like string and an email address."""
    reader = WorkbookReader(FIXTURES_DIR / "medium.xlsx")
    wb = reader.open()
    all_values = [cell.value for cell in reader.iter_text_cells(wb)]

    # A mixed-content cell contains "@" and has multiple words (name + email)
    mixed = [v for v in all_values if v and "@" in v and " " in v]
    assert len(mixed) >= 1, "Expected at least one mixed-content cell (name + email)"


def test_medium_cross_sheet_names() -> None:
    """'Erik Andersson' appears on both the Contacts and Transactions sheets."""
    reader = WorkbookReader(FIXTURES_DIR / "medium.xlsx")
    wb = reader.open()

    contacts_values = [
        cell.value
        for cell in reader.iter_text_cells(wb)
        if cell.sheet_name == "Contacts"
    ]
    transactions_values = [
        cell.value
        for cell in reader.iter_text_cells(wb)
        if cell.sheet_name == "Transactions"
    ]

    contacts_has_name = any(
        "Erik Andersson" in v for v in contacts_values if v
    )
    transactions_has_name = any(
        "Erik Andersson" in v for v in transactions_values if v
    )

    assert contacts_has_name, "Erik Andersson not found in Contacts sheet"
    assert transactions_has_name, "Erik Andersson not found in Transactions sheet"


def test_medium_has_url() -> None:
    """iter_text_cells yields a cell containing the internal report URL."""
    reader = WorkbookReader(FIXTURES_DIR / "medium.xlsx")
    wb = reader.open()
    all_values = [cell.value for cell in reader.iter_text_cells(wb)]

    assert any(
        v and "https://internal.acme.com" in v for v in all_values
    ), "Missing URL in Summary sheet"


# ---------------------------------------------------------------------------
# Hard fixture tests (TEST-04)
# ---------------------------------------------------------------------------


def test_hard_fixture_exists() -> None:
    """hard.xlsx exists at the expected path."""
    assert (FIXTURES_DIR / "hard.xlsx").exists()


def test_hard_five_sheets() -> None:
    """hard.xlsx has exactly 5 sheets."""
    reader = WorkbookReader(FIXTURES_DIR / "hard.xlsx")
    wb = reader.open()
    assert len(wb.sheetnames) == 5


def test_hard_has_formulas() -> None:
    """scan_surfaces returns at least one warning with surface_type='formula'."""
    reader = WorkbookReader(FIXTURES_DIR / "hard.xlsx")
    wb = reader.open()
    warnings = reader.scan_surfaces(wb)
    formula_warnings = [w for w in warnings if w.surface_type == "formula"]
    assert len(formula_warnings) >= 1, "Expected formula warnings in hard.xlsx"


def test_hard_has_comments() -> None:
    """scan_surfaces returns at least one warning with surface_type='comment'."""
    reader = WorkbookReader(FIXTURES_DIR / "hard.xlsx")
    wb = reader.open()
    warnings = reader.scan_surfaces(wb)
    comment_warnings = [w for w in warnings if w.surface_type == "comment"]
    assert len(comment_warnings) >= 1, "Expected comment warnings in hard.xlsx"


def test_hard_has_charts() -> None:
    """scan_surfaces returns at least one warning with surface_type='chart'."""
    reader = WorkbookReader(FIXTURES_DIR / "hard.xlsx")
    wb = reader.open()
    warnings = reader.scan_surfaces(wb)
    chart_warnings = [w for w in warnings if w.surface_type == "chart"]
    assert len(chart_warnings) >= 1, "Expected chart warnings in hard.xlsx"


def test_hard_has_merged_cells() -> None:
    """scan_surfaces returns at least one warning with surface_type='merged_cells'."""
    reader = WorkbookReader(FIXTURES_DIR / "hard.xlsx")
    wb = reader.open()
    warnings = reader.scan_surfaces(wb)
    merged_warnings = [w for w in warnings if w.surface_type == "merged_cells"]
    assert len(merged_warnings) >= 1, "Expected merged_cells warnings in hard.xlsx"


def test_hard_has_edge_cases() -> None:
    """iter_text_cells yields a multi-entity cell with both email and phone."""
    reader = WorkbookReader(FIXTURES_DIR / "hard.xlsx")
    wb = reader.open()
    all_values = [cell.value for cell in reader.iter_text_cells(wb)]

    multi_entity = [
        v for v in all_values
        if v and "@" in v and "+1-555" in v
    ]
    assert len(multi_entity) >= 1, "Expected multi-entity cell with email + phone"


def test_hard_roundtrip_preserves_formulas(tmp_path: Path) -> None:
    """After copy-then-patch, formula strings in the Formulas sheet are preserved."""
    src = FIXTURES_DIR / "hard.xlsx"
    out = tmp_path / "hard_patched.xlsx"

    # Patch a text cell (not the formula cell)
    writer = WorkbookWriter(src, out)
    writer.patch_and_save([("Data", 3, 1, "PERSON_001")])

    # Verify formula cell A3 in Formulas sheet still contains the formula string
    reader = WorkbookReader(out)
    wb = reader.open()
    ws_formulas = wb["Formulas"]
    formula_value = ws_formulas["A3"].value
    assert formula_value == "=SUM(A1:A2)", (
        f"Formula not preserved after round-trip: got {formula_value!r}"
    )
