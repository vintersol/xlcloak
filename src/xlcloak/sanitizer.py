"""Sanitizer orchestrator — wires detection, tokenization, bundle, and manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import click

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
        detector: PiiDetector,
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

        # Detect and tokenize
        all_scan_results = []
        patches: list[tuple[str, int, int, str]] = []
        cells_with_pii: int = 0

        if hide_all:
            for cell in text_cells:
                token = registry.get_or_create(cell.value, EntityType.GENERIC)
                patches.append((cell.sheet_name, cell.row, cell.col, token))
            cells_with_pii = len(patches)
            # all_scan_results stays empty — manifest entity breakdown is intentionally empty
        else:
            # Pre-pass: extract column headers from row-1 cells, grouped by sheet
            # Structure: {sheet_name: {col_index: header_text}}
            # text_cells is already a list, so this iteration is safe
            sheet_headers: dict[str, dict[int, str]] = {}
            for cell in text_cells:
                if cell.row == 1:
                    sheet_headers.setdefault(cell.sheet_name, {})[cell.col] = cell.value or ""

            for cell in text_cells:
                if cell.row == 1:
                    continue  # Never tokenize header row cells

                col_header = sheet_headers.get(cell.sheet_name, {}).get(cell.col)
                scan_results, replaced_text = self._detector.detect_cell(
                    cell, registry, column_header=col_header
                )
                if scan_results:
                    all_scan_results.extend(scan_results)
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
