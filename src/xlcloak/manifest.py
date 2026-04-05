"""Manifest generation for xlcloak — surface warnings and scan summary."""

from __future__ import annotations

from datetime import datetime, timezone

from openpyxl.utils import get_column_letter

from xlcloak.models import ScanResult, SurfaceWarning


class Manifest:
    """Produce a human-readable report of what xlcloak did to a workbook."""

    def __init__(
        self,
        file_name: str,
        sheets_processed: int = 0,
        cells_scanned: int = 0,
        cells_sanitized: int = 0,
        tokens_generated: int = 0,
    ) -> None:
        self.file_name = file_name
        self.sheets_processed = sheets_processed
        self.cells_scanned = cells_scanned
        self.cells_sanitized = cells_sanitized
        self.tokens_generated = tokens_generated
        self.warnings: list[SurfaceWarning] = []
        self.entity_counts: dict[str, int] = {}

    def add_warnings(self, warnings: list[SurfaceWarning]) -> None:
        """Append surface warnings to the manifest."""
        self.warnings.extend(warnings)

    def add_scan_results(self, results: list[ScanResult]) -> None:
        """Record PII scan results and update only the entity breakdown."""
        for result in results:
            key = result.entity_type.value
            self.entity_counts[key] = self.entity_counts.get(key, 0) + 1

    def _format_warning_line(self, w: SurfaceWarning) -> str:
        """Format a single warning line with optional cell reference."""
        # Sheet-level warnings use row=0, col=0 — no cell coordinate
        if w.cell.row == 0 and w.cell.col == 0:
            return f"  - {w.cell.sheet_name}: {w.surface_type} {w.detail} -- not sanitized"
        col_letter = get_column_letter(w.cell.col)
        cell_ref = f"{w.cell.sheet_name}!{col_letter}{w.cell.row}"
        return f"  - {cell_ref}: {w.surface_type} {w.detail} -- not sanitized"

    def render(self) -> str:
        """Produce the full manifest text."""
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        lines: list[str] = [
            "xlcloak Manifest",
            "================",
            f"File: {self.file_name}",
            f"Date: {now}",
            "Mode: sanitize",
            "",
            f"Sheets processed: {self.sheets_processed}",
            f"Cells scanned: {self.cells_scanned}",
            f"Cells sanitized: {self.cells_sanitized}",
            f"Tokens generated: {self.tokens_generated}",
            "",
            "Entity breakdown:",
        ]

        if self.entity_counts:
            for entity_type, count in sorted(self.entity_counts.items()):
                lines.append(f"  {entity_type}: {count}")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("Warnings:")

        if self.warnings:
            for w in self.warnings:
                lines.append(self._format_warning_line(w))
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("Risk notes:")
        lines.append("  (none)")

        return "\n".join(lines)
