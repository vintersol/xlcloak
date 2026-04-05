---
phase: 03-restore-diff
plan: 01
subsystem: cli
tags: [restorer, reconciliation, bundle, fernet, openpyxl, click, tdd]

requires:
  - phase: 02-core-sanitize
    provides: BundleWriter/BundleReader, WorkbookReader/WorkbookWriter, check_overwrite, DEFAULT_PASSWORD, SanitizeResult

provides:
  - Restorer class with token reconciliation logic (restore/skip/new classification)
  - RestoreResult dataclass with counts and skipped cell details
  - derive_restore_paths() function producing _restored.xlsx and _restore_manifest.txt naming
  - render_report() function producing human-readable restore manifest
  - restore CLI command with --bundle (required), --password, --force, --output, --verbose flags
  - Wrong-password error handling (ValueError -> clear CLI error, no traceback)

affects: [03-diff, packaging, ci]

tech-stack:
  added: []
  patterns:
    - Lazy import of Restorer inside restore CLI command body (consistent with sanitize pattern)
    - Token reconciliation via reverse_map key lookup: found=restore, missing=skip (AI-modified), other=new
    - check_overwrite reused from sanitizer.py for overwrite protection
    - TDD: RED commit (failing tests) then GREEN commit (implementation)

key-files:
  created:
    - src/xlcloak/restorer.py
    - tests/test_restorer.py
  modified:
    - src/xlcloak/__init__.py
    - src/xlcloak/cli.py
    - tests/test_cli.py

key-decisions:
  - "Skipped detection via missing tokens: tokens in reverse_map not found in sanitized file -> AI modified (no per-cell position tracking needed)"
  - "skipped_cells list contains {token, original} pairs (not cell addresses) because bundle has no cell position data"
  - "new_count = cells_walked - restored_count: cells that never held tokens OR AI-added text (indistinguishable without position data)"
  - "render_report() is a standalone function not a method on Restorer, keeping RestoreResult a pure dataclass"

patterns-established:
  - "Restore manifest written by Restorer.run() automatically (not a separate CLI step)"
  - "derive_restore_paths() follows same pattern as derive_output_paths() in sanitizer.py"
  - "CLI restore command: ValueError (wrong password) -> sys.exit(1), UsageError (overwrite) -> re-raise"

requirements-completed: [BUN-03, BUN-04, BUN-05, CLI-02]

duration: 4min
completed: 2026-04-04
---

# Phase 03 Plan 01: Restore Command and Reconciliation Engine Summary

**Restorer class with token reconciliation logic (restore/skip/new) plus restore CLI command with --bundle, --password, --force, --output, --verbose flags and wrong-password error handling**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-04T10:13:15Z
- **Completed:** 2026-04-04T10:16:34Z
- **Tasks:** 2 (TDD: 3 commits)
- **Files modified:** 5

## Accomplishments

- Restorer class wired to BundleReader, WorkbookReader/WorkbookWriter, and check_overwrite — full round-trip from sanitized xlsx to restored xlsx
- Token reconciliation: cells matching reverse_map keys restored; missing tokens counted as AI-modified (skipped); non-token cells counted as new/unchanged
- restore CLI command follows sanitize command pattern exactly: lazy import, ValueError/UsageError handling, success output, verbose skipped-token listing
- 14 unit tests (test_restorer.py) + 4 CLI tests (test_cli.py) — all 30 test suite tests pass

## Task Commits

1. **Task 1 RED: failing tests** - `a1d3f4c` (test)
2. **Task 1 GREEN: implement Restorer module** - `8336136` (feat)
3. **Task 2: wire restore CLI command** - `7f41f77` (feat)

## Files Created/Modified

- `src/xlcloak/restorer.py` - Restorer class, RestoreResult dataclass, derive_restore_paths(), render_report()
- `src/xlcloak/__init__.py` - Added Restorer and RestoreResult to imports and __all__
- `src/xlcloak/cli.py` - Added restore command with all required flags
- `tests/test_restorer.py` - 14 unit tests for reconciliation logic, paths, counts, report rendering
- `tests/test_cli.py` - 4 restore CLI tests: help, produces file, wrong password, overwrite protection

## Decisions Made

- Skipped detection uses missing-token approach: tokens in reverse_map not found in sanitized file counted as AI-modified. This is honest about the limitation (no per-cell position data in bundle) while still useful.
- skipped_cells list carries `{token, original}` pairs, not cell coordinates — the bundle does not store which cell held which token.
- render_report() is a standalone module-level function rather than a Restorer method, keeping RestoreResult a pure data class.
- new_count covers both never-tokenized cells and AI-added text — these are indistinguishable without cell position tracking.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

All created files found on disk. All commit hashes verified in git log.

## Next Phase Readiness

- Restore pipeline is complete and tested; ready for Plan 02 (diff command)
- BundleReader and WorkbookReader interfaces confirmed stable for diff use
- check_overwrite reuse pattern established; diff can follow the same approach
