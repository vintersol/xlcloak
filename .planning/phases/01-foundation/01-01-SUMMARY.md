---
phase: 01-foundation
plan: 01
subsystem: token-engine
tags: [python, openpyxl, click, cryptography, presidio, hatchling, uv, pytest, ruff, mypy]

# Dependency graph
requires: []
provides:
  - pyproject.toml with full dependency spec and hatchling build system
  - src/xlcloak package with src layout (Python 3.10+)
  - EntityType enum with 7 PII entity types (PERSON, ORG, EMAIL, PHONE, URL, SSN_SE, ORGNUM_SE)
  - CellRef, ScanResult, SurfaceWarning shared dataclasses
  - TokenFormatter: shape-preserving token string generation with match dispatch
  - TokenRegistry: deterministic bidirectional mapping with global counter
  - 41 passing tests covering determinism, prefixes, shape preservation, overflow guard
affects: [01-02, 01-03, 02-detection, 02-sanitize, 03-restore]

# Tech tracking
tech-stack:
  added:
    - "hatchling 1.x (build backend)"
    - "uv 0.11.3 (dependency management + venv)"
    - "openpyxl>=3.1.2 (Excel I/O)"
    - "click>=8.1.7 (CLI)"
    - "cryptography>=42.0.0 (Fernet encryption)"
    - "presidio-analyzer>=2.2.354 (PII detection)"
    - "presidio-anonymizer>=2.2.354 (token replacement)"
    - "pyyaml>=6.0.1 (user config)"
    - "pytest>=8.1.0 + pytest-cov>=5.0.0 (testing)"
    - "ruff>=0.4.0 (linting + formatting)"
    - "mypy>=1.9.0 (static type checking)"
  patterns:
    - "src layout (src/xlcloak/) for package isolation — tests always import installed package"
    - "TDD: write failing tests first, implement to green, commit separately"
    - "from __future__ import annotations in all source files (Python 3.10 compat)"
    - "Python 3.10 match statement for entity type dispatch in TokenFormatter"
    - "dataclass for value-object types (CellRef, ScanResult, SurfaceWarning)"
    - "Global counter across all entity types (not per-type) per D-02"

key-files:
  created:
    - "pyproject.toml (project metadata, deps, build system, tool config)"
    - "src/xlcloak/__init__.py (package entry point, version, public API re-exports)"
    - "src/xlcloak/models.py (EntityType, CellRef, ScanResult, SurfaceWarning)"
    - "src/xlcloak/token_engine.py (TokenFormatter, TokenRegistry)"
    - "tests/conftest.py (tmp_workbook_path fixture)"
    - "tests/test_models.py (12 model tests)"
    - "tests/test_token_engine.py (29 token engine tests)"
  modified: []

key-decisions:
  - "Global counter across all entity types (D-02): PERSON_001, ORG_002, EMAIL_003 — not PERSON_001, ORG_001"
  - "Shape-preserving tokens per entity type: EMAIL_003@example.com, +10-000-000-004, https://example.com/URL_005"
  - "SSN_SE format 1000000-{counter:04d} (clearly synthetic Swedish-style date prefix)"
  - "ORGNUM_SE format 000000-{counter:04d} (clearly synthetic org number)"
  - "Overflow guard at 999 unique entities raises ValueError with clear message"
  - "uv installed via installer (not pip) — system Python 3.12 has no pip module"

patterns-established:
  - "TDD pattern: failing test commit (test:) then implementation commit (feat:)"
  - "EntityType enum as dispatch key for TokenFormatter match statement"
  - "TokenRegistry owns both _forward and _reverse dicts plus _counter and _formatter"
  - "Public API re-exported from xlcloak/__init__.py via explicit __all__"

requirements-completed: [TOK-01, TOK-02, TOK-03]

# Metrics
duration: 3min
completed: 2026-04-03
---

# Phase 1 Plan 01: Project Scaffolding and Token Engine Summary

**Deterministic shape-preserving token engine with 41 passing tests — EntityType enum, TokenRegistry with global counter, TokenFormatter with match dispatch for 7 PII types**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-03T14:43:42Z
- **Completed:** 2026-04-03T14:46:30Z
- **Tasks:** 2 (each with TDD RED + GREEN commits)
- **Files modified:** 7

## Accomplishments

- Project scaffold with pyproject.toml (hatchling build backend, all runtime + dev deps) and src/ layout
- EntityType enum (7 members), CellRef, ScanResult, SurfaceWarning dataclasses in models.py
- TokenFormatter using Python 3.10 match statement — produces shape-preserving tokens for all 7 entity types
- TokenRegistry with deterministic bidirectional mapping, global counter (not per-type), overflow guard at 999
- 41 tests across test_models.py (12) and test_token_engine.py (29) — all green

## Task Commits

Each task committed with TDD discipline (failing test first, then implementation):

1. **Task 1 RED: Models test scaffold** - `d3b0eb3` (test)
2. **Task 1 GREEN: Models implementation** - `bfaa735` (feat)
3. **Task 2 RED: Token engine tests** - `a9a6d0c` (test)
4. **Task 2 GREEN: Token engine implementation** - `372b3eb` (feat)

**Plan metadata:** (docs commit — recorded after state update)

_Note: TDD tasks have separate test and implementation commits_

## Files Created/Modified

- `pyproject.toml` — Project metadata, all dependencies, hatchling build system, pytest/ruff/mypy config
- `src/xlcloak/__init__.py` — Package version (0.1.0), public API re-exports (EntityType, TokenRegistry, TokenFormatter)
- `src/xlcloak/models.py` — EntityType enum (7 members), CellRef/ScanResult/SurfaceWarning dataclasses
- `src/xlcloak/token_engine.py` — TokenFormatter (match dispatch, 7 entity types) + TokenRegistry (deterministic, bidirectional, global counter)
- `tests/conftest.py` — tmp_workbook_path pytest fixture
- `tests/test_models.py` — 12 tests for models
- `tests/test_token_engine.py` — 29 tests for determinism, prefixes, shapes, global counter, reverse lookup, overflow

## Decisions Made

- Used Python 3.10 `match` statement in TokenFormatter for clean dispatch — matches project language constraint
- SSN_SE token shape `1000000-{counter:04d}` and ORGNUM_SE `000000-{counter:04d}` — both clearly synthetic while matching Swedish numeric format patterns (D-08 was left to Claude's discretion)
- uv installed via official installer script since system Python 3.12 has no pip module — this is the canonical install method for uv anyway
- dev dependencies installed with `uv sync --extra dev` (not just `uv sync`) to get pytest, ruff, mypy into venv

## Deviations from Plan

None — plan executed exactly as written. TDD flow followed as specified. All acceptance criteria met.

## Issues Encountered

- uv was not pre-installed; installed via `curl -LsSf https://astral.sh/uv/install.sh | sh` (standard install path, not a deviation)
- `uv sync` without `--extra dev` did not install pytest; required `uv sync --extra dev` — standard uv behavior for optional deps

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Token engine fully tested and ready for consumption by Phase 2 detection and sanitize pipeline
- Models (EntityType, CellRef, ScanResult, SurfaceWarning) ready for Excel I/O and detection integration
- pyproject.toml deps include presidio-analyzer/anonymizer, openpyxl, cryptography — all ready for Phase 2
- Blocker noted in STATE.md: verify Presidio AnalyzerEngine API before implementing detection in Phase 2

## Self-Check: PASSED

Files verified:
- src/xlcloak/models.py: FOUND
- src/xlcloak/token_engine.py: FOUND
- src/xlcloak/__init__.py: FOUND
- pyproject.toml: FOUND
- tests/test_token_engine.py: FOUND
- tests/test_models.py: FOUND
- tests/conftest.py: FOUND

Commits verified: d3b0eb3, bfaa735, a9a6d0c, 372b3eb — all present in git log

---
*Phase: 01-foundation*
*Completed: 2026-04-03*
