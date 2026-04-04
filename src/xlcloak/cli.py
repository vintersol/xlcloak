"""Click CLI entry point for xlcloak."""

from __future__ import annotations

import sys
from pathlib import Path

import click

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
