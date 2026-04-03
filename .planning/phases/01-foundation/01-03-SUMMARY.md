---
phase: 01-foundation
plan: 03
subsystem: testing
tags: [openpyxl, pytest, fixtures, xlsx, pii, swedish-pii, round-trip]

# Dependency graph
requires:
  - phase: 01-foundation plan 01
    provides: TokenRegistry, TokenFormatter, EntityType — models underpinning fixture content design
  - phase: 01-foundation plan 02
    provides: WorkbookReader, WorkbookWriter — the public API all fixture tests exercise

provides:
  - Three graduated .xlsx test fixtures: simple (1 sheet, basic PII), medium (3 sheets, Swedish PII), hard (5 sheets, formulas/comments/charts/merged cells)
  - Programmatic fixture generator (tests/fixtures/generate_fixtures.py) — reproducible, version-controlled source of truth
  - 22 fixture validation tests covering structure, PII content, Swedish PII, round-trip integrity, and surface detection

affects: [02-detection, 03-bundle, 04-cli, all future phases using test fixtures]

# Tech tracking
tech-stack:
  added: []  # No new libraries — openpyxl already a dependency; BarChart/Comment/DataValidation used from existing install
  patterns:
    - "Programmatic fixture generation: generate_fixtures.py creates .xlsx files via openpyxl Workbook API"
    - "Fixture validation through public API: tests import WorkbookReader/WorkbookWriter only — no direct openpyxl"
    - "Cross-sheet consistency: same person names appear on Contacts and Transactions sheets in medium fixture"
    - "Graduated fixture complexity: simple (no surfaces), medium (Swedish PII), hard (all unsupported surfaces)"

key-files:
  created:
    - tests/fixtures/generate_fixtures.py
    - tests/fixtures/simple.xlsx
    - tests/fixtures/medium.xlsx
    - tests/fixtures/hard.xlsx
    - tests/test_fixtures.py
  modified: []

key-decisions:
  - "Committed generated .xlsx binaries to repo — CI needs them without running generator; binary diffs are small"
  - "ASCII approximations for Swedish names with diacritics (Bjorn Stromberg, not Bjorn Ström berg) — avoids encoding issues while still testing non-ASCII-looking content"
  - "TDD applied with single commit: tests written first, then verified all 22 pass immediately (public API + fixtures already complete)"
  - "Hard fixture formula detection relies on openpyxl data_type='f' — formulas written as strings (=SUM(A1:A2)) so scan_surfaces correctly identifies them"

patterns-established:
  - "Fixture test pattern: use FIXTURES_DIR = Path(__file__).parent / 'fixtures' for path resolution"
  - "Round-trip test pattern: WorkbookWriter.patch_and_save() to tmp_path, then re-read with WorkbookReader"
  - "Surface detection assertion: filter scan_surfaces() result by surface_type for targeted warnings check"

requirements-completed: [TEST-01, TEST-02, TEST-03, TEST-04]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 01 Plan 03: Test Fixtures Summary

**Three programmatically generated .xlsx fixtures (simple/medium/hard) validated by 22 pytest tests exercising WorkbookReader round-trips and surface detection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T14:55:19Z
- **Completed:** 2026-04-03T14:57:43Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `generate_fixtures.py` with `generate_simple`, `generate_medium`, `generate_hard` functions and `__main__` block — 250+ lines, fully reproducible
- Generated three .xlsx fixtures: simple (1 sheet, 20 rows, 5 names/5 emails/3 phones/2 companies), medium (3 sheets, Swedish personnummer 199001151234 + org-nummer 556677-8901, mixed-content cells, cross-sheet names), hard (5 sheets, formulas, 3 comments, merged cells, BarChart, edge cases)
- Wrote 22 passing fixture validation tests through the public `WorkbookReader`/`WorkbookWriter` API, confirming structure, PII content, Swedish PII, round-trip integrity, and surface detection
- Full test suite: 82/82 tests passing (60 prior + 22 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fixture generator script** - `f3e62fc` (feat)
2. **Task 2: Fixture validation tests** - `f225b6c` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `tests/fixtures/generate_fixtures.py` — Programmatic generator for all three fixtures; run to regenerate
- `tests/fixtures/simple.xlsx` — Single-sheet fixture, 20 rows, basic PII (5,663 bytes)
- `tests/fixtures/medium.xlsx` — 3-sheet fixture, Swedish PII, mixed-content cells (9,275 bytes)
- `tests/fixtures/hard.xlsx` — 5-sheet fixture, formulas, comments, BarChart, merged cells, edge cases (11,605 bytes)
- `tests/test_fixtures.py` — 22 fixture validation tests via public WorkbookReader/WorkbookWriter API

## Decisions Made

- Committed generated .xlsx binaries to repo: CI requires fixtures without running the generator; binary deltas are small and binary fixtures serve as documentation
- ASCII-only names for Swedish fixture content (e.g., "Bjorn Stromberg" without umlauts): per plan guidance, the key is the names exist, not perfect Unicode; avoids encoding fragility
- TDD RED phase was a single write (tests written all at once before verification): since both the API (Plans 01-02) and fixtures were already present, no intermediate failing state was needed — all 22 tests passed immediately on first run

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three fixtures are committed and stable — Phase 2 (detection) can use them immediately for PII detection integration tests
- `generate_fixtures.py` is the source of truth: if fixture format needs to change, regenerate by running `uv run python tests/fixtures/generate_fixtures.py`
- Hard fixture covers all surface types that scan_surfaces() detects — ensures detection pipeline is exercised end-to-end

## Self-Check: PASSED

All files verified present:
- `tests/fixtures/generate_fixtures.py` — FOUND
- `tests/fixtures/simple.xlsx` — FOUND
- `tests/fixtures/medium.xlsx` — FOUND
- `tests/fixtures/hard.xlsx` — FOUND
- `tests/test_fixtures.py` — FOUND
- `.planning/phases/01-foundation/01-03-SUMMARY.md` — FOUND

Commits verified:
- `f3e62fc` feat(01-03): add fixture generator and generated .xlsx files — FOUND
- `f225b6c` feat(01-03): add fixture validation tests — FOUND

Test results: 82/82 passing (22 new fixture tests + 60 prior tests)

---
*Phase: 01-foundation*
*Completed: 2026-04-03*
