# Phase 3: Restore & Diff - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete the full sanitize → AI → restore round-trip. The `restore` command reads a sanitized xlsx + encrypted bundle, applies conflict-aware reconciliation (unchanged tokenized cells get originals back, AI-modified cells stay as-is), and writes a new restored xlsx with a reconciliation report. The `diff` command shows what the AI changed without writing files. `reconcile` is an alias for `restore`. Compatibility aliases `deidentify`/`identify` route to `sanitize`/`restore`.

</domain>

<decisions>
## Implementation Decisions

### restore vs reconcile
- **D-01:** `reconcile` is an alias for `restore` — same command, same logic, small surface area. No separate interactive mode or strategy flags in Phase 3. Register via Click's `add_command(..., name='reconcile')`.
- **D-02:** Compatibility aliases: `deidentify` → `sanitize`, `identify` → `restore`. Register both via `add_command` in cli.py.

### Conflict detection logic
- **D-03:** Conflict rule (Claude's discretion on implementation, but this is the model):
  - Cell value is in `reverse_map` (it's still a token) → **restore** original
  - Cell value is NOT in `reverse_map` and cell was tokenized in bundle → **skip** (AI-modified, conflict)
  - Cell position was not in the bundle's token map → **new cell** → leave untouched
  - Cells not scanned by Phase 2 (non-text, formulas, merged cells) → leave untouched
- **D-04:** Conflict resolution strategy: skip-conflicts (safe default). No overwrite-all or interactive mode in Phase 3.

### diff output
- **D-05:** `diff` shows changed cells only in a Rich table: Token | Original Value. Summary header: "N tokens replaced by AI." Footer: "No files written." (V1 limitation: Sheet/Cell/Now columns require per-cell position tracking not present in the Phase 2 bundle format — deferred to V2.)
- **D-06:** `diff` with `--verbose` additionally shows unchanged token cells and new cells (cells present in sanitized file but absent from bundle). Default (no flag) shows changed only.
- **D-07:** `diff` is read-only — no output files written, ever.

### Restore output
- **D-08:** `restore` writes `data_restored.xlsx` (same directory as input, `_restored` suffix). Follows Phase 2 suffix naming convention. Original sanitized file is preserved.
- **D-09:** Overwrite protection: refuse to overwrite existing output files, show `--force` hint. Mirrors `sanitize` behavior (Phase 2 D-11).

### Reconciliation report
- **D-10:** `restore` prints a stdout summary AND writes `data_restore_manifest.txt` alongside the restored file. Mirrors how `sanitize` produces both terminal output and a manifest file.
- **D-11:** Report contents: restored count, skipped (conflict) count, new/untouched count, total cells processed, bundle version, password mode. List of skipped cells if any (sheet/cell/current value).

### Password handling
- **D-12:** `restore` and `diff` accept `--password` flag (default: `xlcloak`). If bundle was created with default password, no warning is needed — default just works. If wrong password supplied, `BundleReader` raises `ValueError("Invalid password or corrupted bundle")` — surface this clearly as a CLI error.

### Claude's Discretion
- Internal module layout (e.g., `restorer.py` vs logic inline in cli.py)
- Exact reconciliation algorithm implementation (cell comparison, position tracking)
- Click argument/option layout for restore/diff commands (matching sanitize convention is fine)
- Rich table styling for diff output (consistent with inspect command)
- Exit codes and error message wording

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — Vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — Phase 3 covers BUN-03, BUN-04, BUN-05, BUN-06, CLI-02, CLI-04, CLI-05, CLI-07
- `.planning/ROADMAP.md` — Phase 3 success criteria (4 criteria: restore with reconciliation, reconciliation report, diff command, reconcile alias)

### Phase 2 foundation (consumed by Phase 3)
- `src/xlcloak/bundle.py` — `BundleReader.read()` returns dict with `forward_map`, `reverse_map`, `version`, `original_filename`, `password_mode`; `DEFAULT_PASSWORD` constant
- `src/xlcloak/cli.py` — Click command group structure; `@main.command()` pattern; `sanitize` and `inspect` as reference for flag design
- `src/xlcloak/sanitizer.py` — `derive_output_paths()` naming convention; `check_overwrite()` pattern; `SanitizeResult` dataclass as model for `RestoreResult`
- `src/xlcloak/excel_io.py` — `WorkbookReader.iter_text_cells()` for iterating sanitized file; `WorkbookWriter` copy-then-patch for writing restored file
- `src/xlcloak/models.py` — `CellRef`, `ScanResult`, `SurfaceWarning` dataclasses; `EntityType` enum

### Phase 1 & 2 context
- `.planning/phases/01-foundation/01-CONTEXT.md` — Token format decisions
- `.planning/phases/02-core-sanitize/02-CONTEXT.md` — Bundle format (D-06/D-07/D-08/D-09/D-10/D-11/D-12), naming convention (D-10), overwrite protection (D-11)

No external specs or ADRs — requirements fully captured in planning docs above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BundleReader` (`src/xlcloak/bundle.py`): Call `BundleReader(password).read(path)` → returns `{"forward_map": {...}, "reverse_map": {...}, "version": ..., "sheets_processed": [...], ...}`. Already handles decryption and `InvalidToken` → `ValueError`.
- `WorkbookReader` (`src/xlcloak/excel_io.py`): `iter_text_cells(wb)` yields `CellRef` for every string cell in the sanitized file — use this to walk cells during restore/diff.
- `WorkbookWriter` (`src/xlcloak/excel_io.py`): `patch_and_save(wb_path, patches)` does copy-then-patch. Accepts list of `(sheet, row, col, new_value)` tuples — same interface restore will need.
- `derive_output_paths()` (`src/xlcloak/sanitizer.py`): Extend or mirror this for `_restored.xlsx` / `_restore_manifest.txt` naming.
- `check_overwrite()` (`src/xlcloak/sanitizer.py`): Reuse directly for restore's overwrite protection.
- Rich table already used in `inspect` command — use same `Console` + `Table` pattern for `diff` output.

### Established Patterns
- copy-then-patch strategy for Excel writes (shutil.copy2 then openpyxl patch)
- `--password` flag with `DEFAULT_PASSWORD` default
- `--force` flag for overwrite protection
- `--verbose` flag for extra detail
- Lazy import of heavy deps (PiiDetector) inside command body — restore/diff don't need PiiDetector so no lazy import needed
- dataclass-based result objects (`SanitizeResult`) — create `RestoreResult` following same pattern

### Integration Points
- `restore` command: `BundleReader.read()` → walk sanitized xlsx via `WorkbookReader` → compare cell values to `reverse_map` → collect patches (restored cells) and conflicts → `WorkbookWriter.patch_and_save()` → write manifest
- `diff` command: same read path as restore but output-only — collect changed/unchanged/new stats, render Rich table, exit without writing
- `reconcile` alias: `main.add_command(restore_cmd, name='reconcile')` in cli.py
- `deidentify`/`identify` aliases: `main.add_command(sanitize_cmd, name='deidentify')` and `main.add_command(restore_cmd, name='identify')`

</code_context>

<specifics>
## Specific Ideas

- diff output should look like the preview shown during discussion: summary header ("N cells changed by AI:"), Rich table (Sheet | Cell | Was (token) | Now), footer ("No files written.") — consistent with inspect's table style
- reconcile being an alias keeps CLI surface area small — users who run `reconcile` get exactly what `restore` gives them, no surprises

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-restore-diff*
*Context gathered: 2026-04-04*
