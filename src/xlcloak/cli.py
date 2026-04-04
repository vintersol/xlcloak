"""Click CLI entry point for xlcloak."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from openpyxl.utils import get_column_letter
from rich.console import Console
from rich.table import Table

import xlcloak
from xlcloak.bundle import DEFAULT_PASSWORD


@click.group(context_settings={"auto_envvar_prefix": "XLCLOAK"})
@click.version_option(version=xlcloak.__version__, prog_name="xlcloak")
def main() -> None:
    """xlcloak -- reversible Excel text sanitization for AI workflows."""


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--password",
    default=DEFAULT_PASSWORD,
    show_default=True,
    help="Encryption password for the restore bundle",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for sanitized file (bundle and manifest derive from it)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing output files",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed output",
)
def sanitize(
    file: Path,
    password: str,
    output_path: Path | None,
    force: bool,
    verbose: bool,
) -> None:
    """Sanitize FILE, producing a sanitized xlsx, encrypted bundle, and manifest."""
    from xlcloak.detector import PiiDetector
    from xlcloak.sanitizer import Sanitizer

    if password == DEFAULT_PASSWORD:
        click.echo(
            "Warning: Using default password. Use --password for real encryption.",
            err=True,
        )

    try:
        detector = PiiDetector()
        sanitizer = Sanitizer(detector, password)
        result = sanitizer.run(file, output_path, force)
    except click.UsageError:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Sanitized: {result.sanitized_path}")
    click.echo(f"Bundle:    {result.bundle_path}")
    click.echo(f"Manifest:  {result.manifest_path}")
    click.echo(f"Tokens:    {result.token_count} unique entities replaced")

    if verbose and result.entity_counts:
        click.echo("")
        click.echo("Entity breakdown:")
        for entity_type, count in sorted(result.entity_counts.items()):
            click.echo(f"  {entity_type}: {count}")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show confidence scores and detection method",
)
def inspect(file: Path, verbose: bool) -> None:
    """Preview what sanitize would do — no files written."""
    from xlcloak.detector import PiiDetector
    from xlcloak.excel_io import WorkbookReader
    from xlcloak.token_engine import TokenRegistry

    try:
        detector = PiiDetector()
        registry = TokenRegistry()
        reader = WorkbookReader(file)
        wb = reader.open()

        all_results = []
        for cell_ref in reader.iter_text_cells(wb):
            scan_results, _replaced = detector.detect_cell(cell_ref, registry)
            all_results.extend(scan_results)

        warnings = reader.scan_surfaces(wb)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Summary header
    click.echo(f"xlcloak inspect: {file.name}")
    click.echo("")

    if all_results:
        entity_counts: dict[str, int] = {}
        for r in all_results:
            key = r.entity_type.value
            entity_counts[key] = entity_counts.get(key, 0) + 1

        click.echo(f"Detected {len(all_results)} entities:")
        for etype, count in sorted(entity_counts.items()):
            click.echo(f"  {etype}: {count}")
        click.echo("")

        # Per-cell table
        console = Console()
        table = Table(show_header=True, header_style="bold")
        table.add_column("Sheet")
        table.add_column("Cell")
        table.add_column("Type")
        table.add_column("Original")
        table.add_column("Would-be Token")
        if verbose:
            table.add_column("Score")
            table.add_column("Method")

        for r in all_results:
            cell_addr = get_column_letter(r.cell.col) + str(r.cell.row)
            original_display = (
                r.original[:40] + "..." if len(r.original) > 40 else r.original
            )
            row_values = [
                r.cell.sheet_name,
                cell_addr,
                r.entity_type.value,
                original_display,
                r.token,
            ]
            if verbose:
                score_str = f"{r.score:.2f}" if r.score is not None else ""
                method_str = r.detection_method or ""
                row_values.extend([score_str, method_str])
            table.add_row(*row_values)

        console.print(table)
    else:
        click.echo("No entities detected.")
        click.echo("")

    # Warnings section
    # Filter to only surface-type warnings that indicate unsupported surfaces
    # (formulas, charts, comments — not info-level items like merged cells)
    unsupported_warnings = [
        w
        for w in warnings
        if w.surface_type in ("formula", "chart", "comment")
    ]
    if unsupported_warnings:
        click.echo("")
        click.echo("Warnings (unsupported surfaces -- not sanitized):")
        for w in unsupported_warnings:
            if w.cell.row == 0 and w.cell.col == 0:
                # Sheet-level warning
                click.echo(f"  - {w.cell.sheet_name}: {w.detail}")
            else:
                cell_addr = get_column_letter(w.cell.col) + str(w.cell.row)
                click.echo(f"  - {w.cell.sheet_name}!{cell_addr}: {w.surface_type} {w.detail}")

    click.echo("")
    click.echo("No files written.")
