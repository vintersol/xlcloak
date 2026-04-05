"""Restore engine for xlcloak — reconciles sanitized xlsx with an encrypted bundle."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from xlcloak.bundle import DEFAULT_PASSWORD, BundleReader
from xlcloak.excel_io import WorkbookReader, WorkbookWriter
from xlcloak.sanitizer import check_overwrite


@dataclass
class RestoreResult:
    """Result of a restore run."""

    restored_path: Path
    manifest_path: Path
    restored_count: int
    skipped_count: int
    new_count: int
    total_cells: int
    skipped_cells: list[dict] = field(default_factory=list)
    """Each entry: {"token": str, "original": str}"""
    bundle_version: str = ""
    password_mode: str = ""


def derive_restore_paths(
    input_path: Path,
    output_override: Path | None = None,
) -> tuple[Path, Path]:
    """Derive output paths for the restored xlsx and manifest.

    Args:
        input_path: The sanitized .xlsx file being restored.
        output_override: Optional explicit path for the restored file.

    Returns:
        Tuple of (restored_xlsx_path, manifest_path).
    """
    if output_override is not None:
        base = output_override.parent / output_override.stem
    else:
        base = input_path.parent / input_path.stem

    restored_path = base.with_name(base.name + "_restored").with_suffix(".xlsx")
    manifest_path = base.with_name(base.name + "_restore_manifest").with_suffix(".txt")
    return restored_path, manifest_path


def render_report(result: RestoreResult) -> str:
    """Render a human-readable restore report string.

    Args:
        result: The RestoreResult from a restore run.

    Returns:
        A multi-line string report.
    """
    lines: list[str] = [
        "xlcloak restore report",
        "=======================",
        f"Bundle version: {result.bundle_version}",
        f"Password mode: {result.password_mode}",
        "",
        f"Cells processed: {result.total_cells}",
        f"Restored: {result.restored_count}",
        f"Skipped (AI-modified): {result.skipped_count}",
        f"Unchanged: {result.new_count}",
    ]

    if result.skipped_cells:
        lines.append("")
        lines.append("Skipped tokens (not found in file -- likely modified by AI):")
        for sc in result.skipped_cells:
            count = int(sc.get("count", 1))
            if count > 1:
                lines.append(f"  {sc['token']} (was: {sc['original']}) x{count}")
            else:
                lines.append(f"  {sc['token']} (was: {sc['original']})")

    return "\n".join(lines)


class Restorer:
    """Orchestrates the restore pipeline.

    Pipeline: read bundle -> read sanitized xlsx -> reconcile tokens ->
              write restored xlsx -> write restore manifest
    """

    def __init__(self, password: str = DEFAULT_PASSWORD) -> None:
        """Initialize Restorer.

        Args:
            password: Decryption password for the bundle.
        """
        self._password = password

    def run(
        self,
        sanitized_path: Path,
        bundle_path: Path,
        output_path: Path | None = None,
        force: bool = False,
    ) -> RestoreResult:
        """Run the restore pipeline on *sanitized_path* using *bundle_path*.

        Reconciliation logic:
        - Cell value IS a key in reverse_map -> restore to original (restored_count++)
        - Cell value is NOT a known token -> leave unchanged (new_count++)
        - Any token in reverse_map NOT found in file -> AI modified (skipped_count++)

        Args:
            sanitized_path: Path to the sanitized .xlsx file (with tokens).
            bundle_path: Path to the .xlcloak encrypted bundle.
            output_path: Optional override for the restored file path.
            force: If True, overwrite existing output files.

        Returns:
            RestoreResult with paths, counts, and skipped cell details.

        Raises:
            ValueError: If the bundle password is wrong or the bundle is corrupted.
            click.UsageError: If output files exist and force is False.
        """
        # Decrypt bundle — raises ValueError on wrong password
        payload = BundleReader(self._password).read(bundle_path)
        reverse_map: dict[str, str] = payload["reverse_map"]
        raw_occurrences = payload.get("token_occurrences", {})
        if isinstance(raw_occurrences, dict) and raw_occurrences:
            expected_occurrences = {
                token: int(count)
                for token, count in raw_occurrences.items()
                if token in reverse_map and int(count) > 0
            }
            if not expected_occurrences:
                expected_occurrences = {token: 1 for token in reverse_map}
        else:
            expected_occurrences = {token: 1 for token in reverse_map}
        bundle_version: str = payload.get("version", "")
        password_mode: str = payload.get("password_mode", "")

        # Derive output paths
        restored_path, manifest_path = derive_restore_paths(sanitized_path, output_path)

        # Check for existing files (raises click.UsageError if not force)
        check_overwrite([restored_path, manifest_path], force)

        # Walk all text cells in the sanitized xlsx
        reader = WorkbookReader(sanitized_path)
        wb = reader.open()

        patches: list[tuple[str, int, int, str]] = []
        found_token_occurrences: Counter[str] = Counter()
        cells_walked = 0

        # Build a compiled regex from all token keys, sorted longest-first to
        # avoid prefix collisions (e.g. PERSON_0019 before PERSON_001).
        if reverse_map:
            sorted_keys = sorted(reverse_map.keys(), key=len, reverse=True)
            token_pattern: re.Pattern[str] | None = re.compile(
                "|".join(re.escape(k) for k in sorted_keys)
            )
        else:
            token_pattern = None

        for cell in reader.iter_text_cells(wb):
            cells_walked += 1
            if token_pattern is None:
                continue
            cell_found: set[str] = set()

            def _replace(m: re.Match, _found: set[str] = cell_found) -> str:
                token = m.group(0)
                _found.add(token)
                found_token_occurrences[token] += 1
                return reverse_map[token]

            new_value = token_pattern.sub(_replace, cell.value)
            if cell_found:
                patches.append((cell.sheet_name, cell.row, cell.col, new_value))

        # Compute counts
        restored_count = len(patches)
        missing_occurrences: dict[str, int] = {}
        for token, expected_count in expected_occurrences.items():
            observed_count = found_token_occurrences.get(token, 0)
            if observed_count < expected_count:
                missing_occurrences[token] = expected_count - observed_count
        skipped_count = sum(missing_occurrences.values())
        new_count = cells_walked - restored_count

        skipped_cells = [
            {
                "token": tok,
                "original": reverse_map[tok],
                "count": missing_occurrences[tok],
            }
            for tok in sorted(missing_occurrences)
        ]

        # Write restored xlsx
        WorkbookWriter(sanitized_path, restored_path).patch_and_save(patches)

        # Build and write restore manifest
        result = RestoreResult(
            restored_path=restored_path,
            manifest_path=manifest_path,
            restored_count=restored_count,
            skipped_count=skipped_count,
            new_count=new_count,
            total_cells=cells_walked,
            skipped_cells=skipped_cells,
            bundle_version=bundle_version,
            password_mode=password_mode,
        )

        manifest_path.write_text(render_report(result))

        return result
