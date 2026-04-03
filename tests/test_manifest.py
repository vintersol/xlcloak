"""Tests for the Manifest module."""

from __future__ import annotations

from xlcloak.manifest import Manifest
from xlcloak.models import CellRef, EntityType, ScanResult, SurfaceWarning


# ---------------------------------------------------------------------------
# Header and basic rendering
# ---------------------------------------------------------------------------


def test_manifest_renders_header() -> None:
    """Manifest.render() contains the xlcloak header and file name."""
    m = Manifest("test.xlsx")
    output = m.render()
    assert "xlcloak Manifest" in output
    assert "File: test.xlsx" in output


def test_manifest_renders_stats() -> None:
    """Manifest.render() includes the numeric stats fields."""
    m = Manifest(
        "data.xlsx",
        sheets_processed=3,
        cells_scanned=100,
        cells_sanitized=20,
        tokens_generated=15,
    )
    output = m.render()
    assert "Sheets processed: 3" in output
    assert "Cells scanned: 100" in output
    assert "Cells sanitized: 20" in output
    assert "Tokens generated: 15" in output


# ---------------------------------------------------------------------------
# Warning rendering
# ---------------------------------------------------------------------------


def test_manifest_renders_warnings() -> None:
    """Warnings with a cell reference render as 'Sheet!ColRow: surface_type'."""
    m = Manifest("book.xlsx")
    # Column 2 = B, row 5
    warning = SurfaceWarning(
        cell=CellRef(sheet_name="Sheet1", row=5, col=2),
        surface_type="formula",
        detail="=SUM(A1:A4)",
        level="WARNING",
    )
    m.add_warnings([warning])
    output = m.render()
    # Should contain Sheet1!B5: formula
    assert "Sheet1!B5: formula" in output


def test_manifest_renders_sheet_level_warning() -> None:
    """Chart warnings (row=0, col=0) show sheet name but no !A0 cell ref."""
    m = Manifest("charts.xlsx")
    warning = SurfaceWarning(
        cell=CellRef(sheet_name="Summary", row=0, col=0),
        surface_type="chart",
        detail="2 chart(s)",
        level="WARNING",
    )
    m.add_warnings([warning])
    output = m.render()
    # Sheet name should appear
    assert "Summary" in output
    assert "chart" in output
    # Must NOT include "!A0" which would be wrong
    assert "!A0" not in output


def test_manifest_empty_warnings() -> None:
    """Manifest with no warnings renders without crashing."""
    m = Manifest("empty.xlsx")
    output = m.render()
    # Should still have Warnings section
    assert "Warnings:" in output
    # No crash — that's the main assertion
    assert isinstance(output, str)
    assert len(output) > 0


def test_manifest_multiple_warnings() -> None:
    """Multiple warnings are all rendered in the output."""
    m = Manifest("multi.xlsx")
    w1 = SurfaceWarning(
        cell=CellRef(sheet_name="Sheet1", row=1, col=1),
        surface_type="formula",
        detail="=A1+B1",
        level="WARNING",
    )
    w2 = SurfaceWarning(
        cell=CellRef(sheet_name="Sheet1", row=3, col=4),
        surface_type="comment",
        detail="reviewer note",
        level="WARNING",
    )
    m.add_warnings([w1, w2])
    output = m.render()
    assert "formula" in output
    assert "comment" in output


# ---------------------------------------------------------------------------
# Entity breakdown
# ---------------------------------------------------------------------------


def test_manifest_renders_entity_breakdown() -> None:
    """add_scan_results populates entity_counts; render() shows breakdown."""
    m = Manifest("scan.xlsx")
    results = [
        ScanResult(
            cell=CellRef("Sheet1", 1, 1),
            entity_type=EntityType.PERSON,
            original="Alice",
            token="PERSON_001",
        ),
        ScanResult(
            cell=CellRef("Sheet1", 2, 1),
            entity_type=EntityType.PERSON,
            original="Bob",
            token="PERSON_002",
        ),
        ScanResult(
            cell=CellRef("Sheet1", 3, 1),
            entity_type=EntityType.EMAIL,
            original="alice@example.com",
            token="EMAIL_003",
        ),
    ]
    m.add_scan_results(results)
    output = m.render()
    assert "PERSON: 2" in output
    assert "EMAIL: 1" in output


def test_manifest_add_scan_results_updates_counters() -> None:
    """add_scan_results increments cells_sanitized and tokens_generated."""
    m = Manifest("scan.xlsx")
    results = [
        ScanResult(
            cell=CellRef("Sheet1", 1, 1),
            entity_type=EntityType.ORG,
            original="Acme Corp",
            token="ORG_001",
        ),
    ]
    m.add_scan_results(results)
    assert m.cells_sanitized == 1
    assert m.tokens_generated == 1
