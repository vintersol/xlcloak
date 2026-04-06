"""Sanitizer orchestrator - wires detection, tokenization, bundle, and manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import click
from openpyxl.utils.cell import column_index_from_string

from xlcloak.bundle import DEFAULT_PASSWORD, BundleWriter
from xlcloak.detector import PiiDetector
from xlcloak.excel_io import WorkbookReader, WorkbookWriter
from xlcloak.manifest import Manifest
from xlcloak.models import EntityType
from xlcloak.token_engine import TokenRegistry


@dataclass
class SanitizeResult:
    """Result of a sanitize run."""

    sanitized_path: Path
    bundle_path: Path
    manifest_path: Path
    token_count: int
    cells_sanitized: int
    entity_counts: dict[str, int] = field(default_factory=dict)


def parse_full_column_specs(
    specs: tuple[str, ...] | list[str],
    sheet_names: list[str],
) -> set[tuple[str, int]]:
    """Parse and validate ``--full-column`` specs in ``Sheet.Col`` format."""
    resolved: set[tuple[str, int]] = set()
    known_sheets = set(sheet_names)

    for spec in specs:
        if spec.count(".") != 1:
            raise click.UsageError(
                f"Invalid --full-column value '{spec}'. Expected format: Sheet.Col"
            )

        sheet_name, col_part = spec.split(".", 1)
        sheet_name = sheet_name.strip()
        col_part = col_part.strip()

        if not sheet_name or not col_part:
            raise click.UsageError(
                f"Invalid --full-column value '{spec}'. Expected format: Sheet.Col"
            )
        if sheet_name not in known_sheets:
            raise click.UsageError(
                f"Unknown sheet '{sheet_name}' in --full-column '{spec}'."
            )
        if not col_part.isalpha():
            raise click.UsageError(
                f"Invalid column '{col_part}' in --full-column '{spec}'. "
                "Column must be letters like A, B, AA."
            )
        try:
            col_index = column_index_from_string(col_part.upper())
        except ValueError as exc:
            raise click.UsageError(
                f"Invalid column '{col_part}' in --full-column '{spec}'."
            ) from exc

        resolved.add((sheet_name, col_index))

    return resolved


def derive_output_paths(
    input_path: Path,
    output_override: Path | None = None,
    bundle_override: Path | None = None,
) -> tuple[Path, Path, Path]:
    """Derive the three output paths from input (or override) path.

    Args:
        input_path: Source .xlsx path.
        output_override: Optional explicit output path for the sanitized file.
        bundle_override: Optional explicit output path for the encrypted bundle.

    Returns:
        Tuple of (sanitized_xlsx_path, bundle_path, manifest_path).
    """
    if output_override is not None:
        base = output_override.parent / output_override.stem
    else:
        base = input_path.parent / input_path.stem

    sanitized_path = base.with_name(base.name + "_sanitized").with_suffix(".xlsx")
    bundle_path = bundle_override if bundle_override is not None else base.with_suffix(".xlcloak")
    manifest_path = base.with_name(base.name + "_manifest").with_suffix(".txt")
    return sanitized_path, bundle_path, manifest_path


def check_overwrite(paths: list[Path], force: bool) -> None:
    """Raise UsageError if any output paths already exist and force is False.

    Args:
        paths: List of output paths to check.
        force: If True, skip the check.

    Raises:
        click.UsageError: If any paths exist and force is False.
    """
    if force:
        return
    existing = [p for p in paths if p.exists()]
    if existing:
        raise click.UsageError(
            f"Output file(s) already exist: {', '.join(str(p) for p in existing)}. "
            "Use --force to overwrite."
        )


class Sanitizer:
    """Orchestrates the full sanitize pipeline.

    Pipeline: read workbook -> detect PII -> tokenize -> write sanitized xlsx
              -> write encrypted bundle -> write manifest
    """

    def __init__(
        self,
        detector: PiiDetector | None,
        password: str = DEFAULT_PASSWORD,
    ) -> None:
        """Initialize Sanitizer.

        Args:
            detector: Configured PiiDetector instance.
            password: Encryption password for the bundle.
        """
        self._detector = detector
        self._password = password

    def run(
        self,
        input_path: Path,
        output_path: Path | None = None,
        force: bool = False,
        bundle_path: Path | None = None,
        hide_all: bool = False,
        full_columns: tuple[str, ...] | list[str] = (),
        columns_only: bool = False,
    ) -> SanitizeResult:
        """Run the full sanitize pipeline on *input_path*.

        Args:
            input_path: Path to the source .xlsx file.
            output_path: Optional override for the sanitized file path.
            force: If True, overwrite existing output files.

        Returns:
            SanitizeResult with paths and counts.

        Raises:
            click.UsageError: If output files exist and force is False.
        """
        if hide_all and columns_only:
            raise click.UsageError("--hide-all and --columns-only cannot be used together.")

        sanitized_out, bundle_out, manifest_out = derive_output_paths(
            input_path, output_path, bundle_path
        )
        check_overwrite([sanitized_out, bundle_out, manifest_out], force)

        registry = TokenRegistry()

        # Read workbook
        reader = WorkbookReader(input_path)
        wb = reader.open()

        text_cells = list(reader.iter_text_cells(wb))
        warnings = reader.scan_surfaces(wb)
        sheet_names = [ws.title for ws in wb.worksheets]
        forced_targets = parse_full_column_specs(full_columns, sheet_names)
        if columns_only and not forced_targets:
            raise click.UsageError("--columns-only requires at least one --full-column/-c.")

        # Detect and tokenize
        all_scan_results = []
        patches: list[tuple[str, int, int, str]] = []
        cells_with_pii: int = 0
        token_occurrences: dict[str, int] = {}
        processed_cells: set[tuple[str, int, int]] = set()

        # Forced columns are always processed first and excluded from detection.
        for cell in text_cells:
            if (cell.sheet_name, cell.col) not in forced_targets:
                continue
            if cell.row == 1:
                # Treat row 1 as a header row for forced columns and keep it unchanged.
                processed_cells.add((cell.sheet_name, cell.row, cell.col))
                continue
            token = registry.get_or_create(cell.value, EntityType.GENERIC)
            patches.append((cell.sheet_name, cell.row, cell.col, token))
            token_occurrences[token] = token_occurrences.get(token, 0) + 1
            cells_with_pii += 1
            processed_cells.add((cell.sheet_name, cell.row, cell.col))

        if hide_all:
            for cell in text_cells:
                cell_key = (cell.sheet_name, cell.row, cell.col)
                if cell_key in processed_cells:
                    continue
                token = registry.get_or_create(cell.value, EntityType.GENERIC)
                patches.append((cell.sheet_name, cell.row, cell.col, token))
                token_occurrences[token] = token_occurrences.get(token, 0) + 1
                cells_with_pii += 1
            # all_scan_results stays empty - manifest entity breakdown is intentionally empty
        elif not columns_only:
            if self._detector is None:
                raise RuntimeError("PiiDetector is required unless --columns-only is used.")

            # Pre-pass: extract column headers from row-1 cells, grouped by sheet
            # Structure: {sheet_name: {col_index: header_text}}
            sheet_headers: dict[str, dict[int, str]] = {}
            for cell in text_cells:
                if cell.row == 1:
                    sheet_headers.setdefault(cell.sheet_name, {})[cell.col] = cell.value or ""

            for cell in text_cells:
                cell_key = (cell.sheet_name, cell.row, cell.col)
                if cell_key in processed_cells:
                    continue

                col_header = (
                    sheet_headers.get(cell.sheet_name, {}).get(cell.col)
                    if cell.row > 1
                    else None
                )
                scan_results, replaced_text = self._detector.detect_cell(
                    cell, registry, column_header=col_header
                )
                if scan_results:
                    all_scan_results.extend(scan_results)
                    for result in scan_results:
                        token_occurrences[result.token] = token_occurrences.get(result.token, 0) + 1
                    patches.append((cell.sheet_name, cell.row, cell.col, replaced_text))
                    cells_with_pii += 1

        # Write sanitized xlsx
        writer = WorkbookWriter(input_path, sanitized_out)
        writer.patch_and_save(patches)

        # Write encrypted bundle
        bundle_writer = BundleWriter(self._password)
        bundle_writer.write(
            bundle_out,
            registry.forward_map,
            registry.reverse_map,
            input_path.name,
            sheet_names,
            len(registry),
            token_occurrences=token_occurrences,
        )

        # Build and write manifest
        manifest = Manifest(
            file_name=input_path.name,
            sheets_processed=len(wb.worksheets),
            cells_scanned=len(text_cells),
            cells_sanitized=cells_with_pii,
            tokens_generated=len(registry),
        )
        manifest.add_scan_results(all_scan_results)
        manifest.add_warnings(warnings)
        manifest_out.write_text(manifest.render())

        return SanitizeResult(
            sanitized_path=sanitized_out,
            bundle_path=bundle_out,
            manifest_path=manifest_out,
            token_count=len(registry),
            cells_sanitized=cells_with_pii,
            entity_counts=manifest.entity_counts,
        )
