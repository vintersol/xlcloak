---
phase: quick
plan: 260405-sbx
subsystem: cli, sanitizer, restorer, bundle, excel-io
tags: [security, hardening, restore, encryption, cli]
key_files:
  modified:
    - src/xlcloak/cli.py
    - src/xlcloak/sanitizer.py
    - src/xlcloak/restorer.py
    - src/xlcloak/bundle.py
    - src/xlcloak/excel_io.py
    - tests/test_bundle.py
    - tests/test_restorer.py
    - tests/test_sanitizer.py
    - tests/test_cli.py
    - tests/test_e2e.py
    - README.md
metrics:
  completed: "2026-04-05"
---

# Quick Task 260405-sbx: Fix High Security Bypass Issues

## What Was Implemented

1. Password hardening in CLI
- `sanitize` and `restore` no longer silently use the built-in default password.
- Added explicit unsafe opt-in flag: `--use-default-password`.
- Added centralized password resolution with mutually-exclusive validation (`--password` vs `--use-default-password`).

2. Exact-token restore matching
- Removed substring regex replacement in restore path.
- Restore now only applies when a cell value exactly equals a token in `reverse_map`.

3. Bundle/workbook binding
- Added `bundle_id` (UUID) to encrypted bundle payload.
- Added workbook marker persistence via very-hidden metadata sheet (`__xlcloak_meta__`) containing bundle ID.
- Restore now enforces binding by default and rejects mismatches.
- Added explicit unsafe override: `--allow-unbound-restore`.

4. Unsupported-surface fail-closed behavior
- `sanitize` now blocks by default when formulas/comments/charts are detected.
- Added explicit unsafe override: `--allow-unsupported-surfaces`.

5. Test and docs updates
- Updated tests for new secure defaults and binding behavior.
- Added tests for unbound/mismatched restore handling and unsupported-surface blocking.
- Updated README command options for new flags.

## Verification
- Targeted modules passed:
  - `tests/test_bundle.py`
  - `tests/test_restorer.py`
  - `tests/test_sanitizer.py`
  - `tests/test_cli.py`
  - `tests/test_e2e.py`
- Full test suite passed via:
  - `./.venv/bin/python -m pytest -q`
