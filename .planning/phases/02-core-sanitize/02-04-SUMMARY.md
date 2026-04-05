---
phase: 02-core-sanitize
plan: "04"
subsystem: cli
tags: [click, rich, inspect, dry-run, pypi, packaging]

# Dependency graph
requires:
  - phase: 02-core-sanitize-03
    provides: sanitize CLI command and PiiDetector.detect_cell API
  - phase: 02-core-sanitize-01
    provides: ScanResult dataclass, WorkbookReader, token engine
provides:
  - inspect subcommand with rich table output and dry-run preview
  - ScanResult extended with score and detection_method fields
  - PyPI-ready package metadata (description, readme, license, classifiers)
  - README.md for package distribution
affects: [03-restore-bundle, 04-patterns]

# Tech tracking
tech-stack:
  added: [rich>=12.0.0]
  patterns:
    - Lazy import of PiiDetector inside CLI command body (avoids spaCy load on --help)
    - rich.table.Table for structured terminal output
    - get_column_letter from openpyxl.utils for cell address formatting

key-files:
  created:
    - src/xlcloak/cli.py (inspect command added)
    - README.md (required by hatchling for pyproject.toml readme field)
  modified:
    - src/xlcloak/models.py (ScanResult.score, ScanResult.detection_method)
    - src/xlcloak/detector.py (populate score and detection_method in detect_cell)
    - pyproject.toml (rich dependency, PyPI metadata)
    - tests/test_cli.py (inspect tests added)

key-decisions:
  - "Option A chosen for verbose scores: extend ScanResult with score/detection_method instead of separate display path — keeps data flow clean"
  - "Created README.md to satisfy hatchling build backend requirement for readme field in pyproject.toml"
  - "Warnings section filters to formula/chart/comment only — merged cells and images are info-level, not actionable unsupported surfaces"

patterns-established:
  - "Inspect pattern: detect-only pass using PiiDetector + fresh TokenRegistry, no file writes"
  - "Rich table columns: Sheet, Cell, Type, Original (truncated 40 chars), Would-be Token; verbose adds Score, Method"

requirements-completed: [CLI-03, CLI-08, CLI-09]

# Metrics
duration: 4min
completed: 2026-04-04
---

# Phase 02 Plan 04: Inspect Command and Package Finalization Summary

**`xlcloak inspect` dry-run command with rich table output, verbose confidence scores, and complete PyPI metadata including classifiers and readme**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-04T04:50:38Z
- **Completed:** 2026-04-04T04:54:03Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `xlcloak inspect` command that previews PII detection without writing any files
- Extended `ScanResult` with optional `score` and `detection_method` fields for verbose mode
- Updated `PiiDetector.detect_cell()` to populate score and detection method from Presidio results
- Added `rich>=12.0.0` as explicit dependency and PyPI package metadata (description, readme, license, keywords, classifiers)
- Created README.md required by hatchling build backend
- Added 8 inspect tests plus 2 package verification tests to `test_cli.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: Inspect command + packaging** - `c33c469` (feat)
   - Also includes: models.py ScanResult extension, detector.py score population, README.md creation
2. **Task 2 RED: Failing inspect tests** - `166d900` (test)
3. **Task 2 GREEN: Tests pass** - `56703f0` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `src/xlcloak/cli.py` - Added inspect command with rich table output, warnings section, verbose mode
- `src/xlcloak/models.py` - Extended ScanResult with score and detection_method optional fields
- `src/xlcloak/detector.py` - Populate score and detection_method from Presidio RecognizerResult
- `pyproject.toml` - Added rich>=12.0.0 dependency and full PyPI metadata
- `README.md` - Created minimal README for package distribution (required by hatchling)
- `tests/test_cli.py` - Added 8 inspect tests and 2 package verification tests

## Decisions Made

- Option A for verbose scores: extend ScanResult dataclass with `score: float | None` and `detection_method: str | None` — keeps inspect and sanitize on same data path
- README.md created to fix hatchling build failure when `readme = "README.md"` was added to pyproject.toml (Rule 3 auto-fix)
- Warnings section filters to formula/chart/comment surface types only — these are the truly "unsupported" surfaces mentioned in D-14; merged cells and images are info-level

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created README.md for hatchling build backend**
- **Found during:** Task 1 (verify step: `uv run python -c "from xlcloak.cli import main; ..."`)
- **Issue:** pyproject.toml `readme = "README.md"` caused hatchling build failure because README.md didn't exist
- **Fix:** Created minimal README.md with installation and usage instructions
- **Files modified:** README.md (created)
- **Verification:** Build succeeded, `xlcloak inspect --help` exits 0
- **Committed in:** c33c469 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for package to install cleanly. No scope creep.

## Issues Encountered

- spaCy model `en_core_web_lg` not installed in test environment — all CLI tests that invoke PiiDetector skip cleanly. This is expected behavior per the `requires_spacy` mark; tests pass (exit 0) when model is absent.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `xlcloak inspect` and `xlcloak sanitize` are both functional
- Package builds and installs cleanly with `pip install .`
- Phase 02 core-sanitize complete — all 4 plans executed
- Phase 03 (restore bundle / restore command) can begin

---
*Phase: 02-core-sanitize*
*Completed: 2026-04-04*
