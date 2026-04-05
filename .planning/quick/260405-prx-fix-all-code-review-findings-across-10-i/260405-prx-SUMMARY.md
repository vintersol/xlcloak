---
phase: quick
plan: 260405-prx
subsystem: core
tags: [bugfix, hardening, cleanup, token-engine, cli, bundle, detector, sanitizer]
dependency_graph:
  requires: []
  provides:
    - Non-PII SSN_SE and ORGNUM_SE token formats
    - Regex-based diff command for mixed-content cells
    - Header-skipping dry-run and inspect matching Sanitizer.run()
    - Salt length guard in BundleReader
    - Explicit ValueError in detector (no assert)
    - GENERIC fallback for unknown Presidio entity types
    - No variable shadowing in sanitizer
    - Cleaned-up unused imports and dependencies
  affects:
    - src/xlcloak/token_engine.py
    - src/xlcloak/cli.py
    - src/xlcloak/bundle.py
    - src/xlcloak/detector.py
    - src/xlcloak/sanitizer.py
    - pyproject.toml
    - tests/test_token_engine.py
    - tests/test_models.py
tech_stack:
  added: []
  patterns:
    - re.compile with sorted keys for regex-based token detection in diff
    - warnings.warn for non-fatal unknown entity fallback
key_files:
  modified:
    - src/xlcloak/token_engine.py
    - src/xlcloak/cli.py
    - src/xlcloak/bundle.py
    - src/xlcloak/detector.py
    - src/xlcloak/sanitizer.py
    - pyproject.toml
    - tests/test_token_engine.py
    - tests/test_models.py
decisions:
  - SSN_SE tokens changed from 1000000-NNNN to SSN_SE_NNN to eliminate PII-resembling format
  - ORGNUM_SE tokens changed from 000000-NNNN to ORGNUM_SE_NNN for same reason
  - diff uses sorted descending key length regex (same pattern as restorer.py) for substring token detection
  - dry-run and inspect now mirror Sanitizer.run() header extraction and row-1 skip
  - detector.py uses warnings.warn + GENERIC fallback for unknown Presidio entity types (non-fatal)
  - sanitizer.py local output vars renamed to sanitized_out/bundle_out/manifest_out to avoid parameter shadowing
metrics:
  started: "2026-04-05T16:00:00Z"
  completed: "2026-04-05T16:43:00Z"
  duration: "~43 minutes"
  tasks_completed: 4
  files_changed: 8
---

# Quick Task 260405-prx: Fix All Code Review Findings Summary

**One-liner:** Hardened xlcloak against 10 code review findings: eliminated PII-resembling Swedish token formats, fixed CLI behavioral divergences in diff/dry-run/inspect, added defensive guards in bundle/detector/sanitizer, and cleaned unused imports and dependencies.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix token format for SSN_SE and ORGNUM_SE | 5b2ef5b | token_engine.py, test_token_engine.py |
| 2 | Fix CLI diff/dry-run/inspect behavioral divergences | 0865576 | cli.py |
| 3 | Defensive coding fixes in bundle, detector, sanitizer | a7f4271 | bundle.py, detector.py, sanitizer.py |
| 4 | Cleanup — unused import, unused deps, stale docstring | a5a871f | sanitizer.py, pyproject.toml, test_models.py |

## What Was Done

### Task 1: Token Format Fix (Finding 1)

Changed `TokenFormatter.format()` to produce clearly synthetic tokens:
- `EntityType.SSN_SE`: `1000000-{counter:04d}` → `SSN_SE_{counter:03d}` (e.g., `SSN_SE_001`)
- `EntityType.ORGNUM_SE`: `000000-{counter:04d}` → `ORGNUM_SE_{counter:03d}` (e.g., `ORGNUM_SE_001`)

Updated 4 regex assertions in `test_token_engine.py` to match the new format. The restorer builds regex from `reverse_map` keys dynamically, so no changes needed there. All 3 e2e round-trip tests continue to pass — token shape changes do not affect the sanitize-restore cycle.

### Task 2: CLI Behavioral Divergences (Findings 2-4)

**diff command (Finding 2):** Replaced exact-value-in-dict lookup with a compiled regex (longest-key-first, same approach as restorer.py). This catches tokens embedded in mixed-content cells like "Contact: PERSON_001 at EMAIL_001@example.com".

**dry-run (Finding 3) and inspect (Finding 4):** Added pre-pass header extraction mirroring `Sanitizer.run()`. Both commands now:
1. Collect all text cells into a list
2. Extract `sheet_headers: dict[str, dict[int, str]]` from row-1 cells
3. Skip row-1 cells in the detection loop
4. Pass `column_header` to `detect_cell()` for boost-threshold logic

### Task 3: Defensive Coding (Findings 5-8)

**bundle.py (Finding 5):** Added guard before salt slice — raises `ValueError` with clear message if file size < `SALT_LENGTH` (16 bytes).

**detector.py (Finding 6):** Replaced `assert cell.value is not None` with `if cell.value is None: raise ValueError(...)`. Asserts are disabled in optimized Python runs; explicit ValueError is always enforced.

**detector.py (Finding 7):** Replaced `PRESIDIO_TO_ENTITY_TYPE[result.entity_type]` with `.get()` + `warnings.warn()` + `EntityType.GENERIC` fallback. Unknown entity types from future Presidio versions or custom recognizers no longer cause `KeyError`.

**sanitizer.py (Finding 8):** Renamed `sanitized_path`, `bundle_path`, `manifest_path` local variables to `sanitized_out`, `bundle_out`, `manifest_out` to eliminate shadowing of the `bundle_path` parameter.

### Task 4: Cleanup (Findings 9-11)

**Finding 9:** Removed `import sys` from `sanitizer.py` (unused — `sys.exit` is only in `cli.py`). Also removed pre-existing unused `import xlcloak` discovered during ruff check.

**Finding 10:** Removed `presidio-anonymizer>=2.2.354` and `pyyaml>=6.0.1` from `pyproject.toml` dependencies. Neither is imported anywhere in `src/`.

**Finding 11:** Renamed `test_entity_type_has_seven_members` to `test_entity_type_has_eight_members` in `tests/test_models.py`. Also removed unused `import pytest` from that file (discovered during ruff check of the modified file).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Remove unused `import xlcloak` from sanitizer.py**
- **Found during:** Task 4 ruff check
- **Issue:** `sanitizer.py` had `import xlcloak` that was never referenced in the file body (pre-existing dead import)
- **Fix:** Removed the import alongside the planned `import sys` removal
- **Files modified:** `src/xlcloak/sanitizer.py`
- **Commit:** a5a871f

**2. [Rule 2 - Missing Critical Functionality] Remove unused `import pytest` from test_models.py**
- **Found during:** Task 4 ruff check
- **Issue:** `tests/test_models.py` had `import pytest` that was never used (pre-existing)
- **Fix:** Removed alongside the planned function rename
- **Files modified:** `tests/test_models.py`
- **Commit:** a5a871f

## Verification Results

```
173 passed in 38.35s
```

- All 173 tests pass (0 failures)
- All 3 e2e round-trip tests pass (simple.xlsx, medium.xlsx, hard.xlsx)
- ruff check clean on all modified files

## Known Stubs

None — all changes are defensive fixes and behavioral corrections. No stub values introduced.

## Self-Check: PASSED

Files exist:
- src/xlcloak/token_engine.py: FOUND
- src/xlcloak/cli.py: FOUND
- src/xlcloak/bundle.py: FOUND
- src/xlcloak/detector.py: FOUND
- src/xlcloak/sanitizer.py: FOUND
- pyproject.toml: FOUND
- tests/test_token_engine.py: FOUND
- tests/test_models.py: FOUND

Commits exist:
- 5b2ef5b: Task 1 — token format fix
- 0865576: Task 2 — CLI behavioral divergences
- a7f4271: Task 3 — defensive coding
- a5a871f: Task 4 — cleanup
