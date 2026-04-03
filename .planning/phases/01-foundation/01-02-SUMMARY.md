---
phase: 01-foundation
plan: 02
subsystem: excel-io
tags: [openpyxl, excel, manifest, surface-detection, copy-then-patch]

# Dependency graph
requires:
  - phase: 01-foundation plan 01
    provides: CellRef, SurfaceWarning, ScanResult, EntityType dataclasses from models.py
provides:
  - WorkbookReader: open(), iter_text_cells(), scan_surfaces() using openpyxl
  - WorkbookWriter: copy-then-patch strategy via prepare(), patch_cells(), patch_and_save()
  - Manifest: add_warnings(), add_scan_results(), render() for human-readable report
  - Surface detection for formulas, comments, charts, merged cells, images, data validation, named ranges
affects:
  - Phase 02 (detection layer will call WorkbookReader.iter_text_cells and Manifest.add_scan_results)
  - Phase 03 (sanitize/restore commands consume the full pipeline)

# Tech tracking
tech-stack:
  added: [pytest>=9.0.2, pytest-cov>=7.1.0]
  patterns:
    - Copy-then-patch: shutil.copy2 preserves all non-cell content, openpyxl patches only text cells
    - TDD: failing test commit (RED) followed by implementation commit (GREEN) per task
    - data_only=False in load_workbook to preserve formula strings as cell values

key-files:
  created:
    - src/xlcloak/excel_io.py
    - src/xlcloak/manifest.py
    - tests/test_excel_io.py
    - tests/test_manifest.py
  modified:
    - src/xlcloak/__init__.py

key-decisions:
  - "data_only=False on load_workbook preserves formula strings; data_only=True would lose them"
  - "Sheet-level warnings (charts, images, merged cells) use row=0, col=0 sentinel to distinguish from cell-level warnings"
  - "Manifest renders row=0/col=0 warnings without cell reference (just sheet name) to avoid confusing !A0 output"

patterns-established:
  - "Copy-then-patch: copy source to output first, then load output and patch — preserves formatting, merged cells, charts"
  - "Surface detection: per-cell scan for formula/comment, per-sheet scan for charts/images/merged/data-validation, workbook scan for named ranges"
  - "TDD commit convention: test(phase-plan) for RED phase, feat(phase-plan) for GREEN phase"

requirements-completed: [DET-09]

# Metrics
duration: 3min
completed: 2026-04-03
---

# Phase 01 Plan 02: Excel I/O Pipeline Summary

**openpyxl WorkbookReader/WorkbookWriter with copy-then-patch strategy and Manifest surface-warning renderer**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-03T14:50:06Z
- **Completed:** 2026-04-03T14:52:41Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- WorkbookReader reads text cells via iter_text_cells() and scans 7 surface types via scan_surfaces()
- WorkbookWriter copies source to output with shutil.copy2 then patches cells — preserves formatting, merged cells, charts
- Manifest renders structured text report with warnings section (cell references as Sheet!ColRow), entity breakdown, and stats
- 19 tests passing across test_excel_io.py (11) and test_manifest.py (8); full suite at 60 green

## Task Commits

Each task was committed atomically with TDD RED/GREEN commits:

1. **Task 1 RED: Excel I/O failing tests** - `d3dfec5` (test)
2. **Task 1 GREEN: WorkbookReader and WorkbookWriter** - `c1b7244` (feat)
3. **Task 2 RED: Manifest failing tests** - `ac9b0e1` (test)
4. **Task 2 GREEN: Manifest module + package exports** - `c9a0e8f` (feat)

_TDD tasks have separate RED (test) and GREEN (implementation) commits._

## Files Created/Modified

- `src/xlcloak/excel_io.py` - WorkbookReader (open, iter_text_cells, scan_surfaces), WorkbookWriter (prepare, patch_cells, patch_and_save)
- `src/xlcloak/manifest.py` - Manifest class with add_warnings, add_scan_results, render
- `src/xlcloak/__init__.py` - Added WorkbookReader, WorkbookWriter, Manifest exports
- `tests/test_excel_io.py` - 11 tests: round-trip, patch, iter filtering, surface detection
- `tests/test_manifest.py` - 8 tests: header, stats, warning rendering, entity breakdown

## Decisions Made

- `data_only=False` on `load_workbook` — preserves formula strings so they can be detected and warned; `data_only=True` would silently lose formula text
- Sheet-level warnings (charts, images, merged cell ranges) use `row=0, col=0` as a sentinel value distinguishing them from cell-level warnings
- Manifest formats sheet-level warnings as `{sheet}: {detail}` (no cell ref) to avoid confusing `!A0` output

## Deviations from Plan

None - plan executed exactly as written. The only addition was installing pytest/pytest-cov which were listed in the stack but not yet added to pyproject.toml.

## Issues Encountered

pytest was not yet installed when tests were first run (environment bootstrapped from plan 01-01). Installed pytest>=9.0.2 and pytest-cov as dev dependencies via `uv add --dev` before running RED phase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Excel I/O pipeline complete: WorkbookReader/WorkbookWriter ready for detection layer (Phase 02)
- Manifest module ready to receive scan results from Presidio analysis
- All 60 tests passing including Plan 01 token engine tests
- Surface scanner covers all 7 surface types; chart/image detection requires real .xlsx fixtures (noted in test file, validated in Plan 03)
- Concern: Chart and image creation via openpyxl programmatic API is limited — hard fixture tests deferred to Plan 03 as planned

## Self-Check: PASSED

All files present: excel_io.py, manifest.py, test_excel_io.py, test_manifest.py, 01-02-SUMMARY.md
All commits found: d3dfec5, c1b7244, ac9b0e1, c9a0e8f

---
*Phase: 01-foundation*
*Completed: 2026-04-03*
