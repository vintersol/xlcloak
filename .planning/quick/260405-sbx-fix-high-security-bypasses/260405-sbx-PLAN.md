---
phase: quick
plan: 260405-sbx
type: execute
wave: 1
depends_on: []
files_modified:
  - src/xlcloak/cli.py
  - src/xlcloak/sanitizer.py
  - src/xlcloak/restorer.py
  - src/xlcloak/bundle.py
  - src/xlcloak/excel_io.py
  - tests/test_cli.py
  - tests/test_restorer.py
  - tests/test_sanitizer.py
  - tests/test_bundle.py
autonomous: true
must_haves:
  truths:
    - "No implicit insecure default password path in sanitize/restore"
    - "Restore only applies on exact token-cell matches"
    - "Bundle/workbook binding is enforced by default"
    - "Unsupported surfaces block sanitize by default"
---

<objective>
Implement the approved security hardening for all High-severity bypasses in the xlcloak sanitize/restore pipeline.
</objective>

<success_criteria>
- Secure defaults are enforced in CLI and runtime behavior
- Unsafe behavior only available through explicit override flags
- Existing functionality remains intact for explicit secure paths
- Tests cover each high-severity bypass fix
</success_criteria>
