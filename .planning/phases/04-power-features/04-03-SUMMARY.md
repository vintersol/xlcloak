---
phase: 04-power-features
plan: 03
subsystem: detection
tags: [presidio, spacy, pii, header-boosting, sanitizer, openpyxl]

# Dependency graph
requires:
  - phase: 04-power-features plan 01
    provides: Swedish PII recognizers (SwePersonnummerRecognizer, SweOrgNummerRecognizer, CompanySuffixRecognizer)
  - phase: 04-power-features plan 02
    provides: hide_all=True mode in Sanitizer.run(), span deduplication in detect_cell()

provides:
  - _header_matches_pii_keyword() helper function with _PII_HEADER_KEYWORDS frozenset
  - _BOOSTED_THRESHOLD = 0.3 applied when column header matches PII keyword
  - detect_cell(cell, registry, column_header=None) signature with threshold boosting
  - sheet_headers pre-pass in Sanitizer.run() (dict[sheet_name][col_index] = header_text)
  - Row-1 skip guard in Sanitizer.run() normal detection mode
  - Phase 4 gate integration test (medium fixture + hide-all)

affects:
  - Any future plan that extends detect_cell() or Sanitizer.run()
  - Phase 5 if user-domain configuration adds per-column overrides

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Header-context boosting: score_threshold lowered from 0.4 to 0.3 for PII-labeled columns"
    - "Header pre-pass pattern: two-pass over text_cells (first for row-1 headers, second for detection)"
    - "Row-1 skip guard: continue statement before detect_cell() in normal detection loop"

key-files:
  created: []
  modified:
    - src/xlcloak/detector.py
    - src/xlcloak/sanitizer.py
    - tests/test_detector.py
    - tests/test_sanitizer.py

key-decisions:
  - "Header keyword matching uses substring check (any(kw in header.lower())) not exact match — handles 'Customer Name', 'Email Address' naturally"
  - "Boosted threshold is 0.3 (vs default 0.4) — accepts lower-confidence matches in PII-labeled columns"
  - "hide_all=True branch left unchanged — tokenizes ALL cells including row-1 (no header distinction in hide-all mode)"
  - "Test fix: plan-written tests used output path directly; corrected to use result.sanitized_path (derive_output_paths appends _sanitized suffix)"

patterns-established:
  - "Pre-pass pattern: iterate text_cells twice (headers first, detection second) to build context before processing"
  - "TDD keyword-function tests: test module-level helper functions directly without spaCy model load"

requirements-completed: [DET-08]

# Metrics
duration: 6min
completed: 2026-04-04
---

# Phase 4 Plan 03: Header Context Boosting Summary

**Column-header context boosting (DET-08): PiiDetector lowers score threshold to 0.3 for cells in PII-labeled columns (Customer, Email, Phone, etc.), and Sanitizer skips row-1 headers from tokenization**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-04T15:53:33Z
- **Completed:** 2026-04-04T15:59:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `_header_matches_pii_keyword()` with `_PII_HEADER_KEYWORDS` frozenset (10 keywords) — no spaCy required
- Updated `detect_cell()` to accept `column_header: str | None = None` and apply `_BOOSTED_THRESHOLD = 0.3` when header matches
- Added header pre-pass in `Sanitizer.run()` building `sheet_headers: dict[str, dict[int, str]]` from row-1 cells
- Added row-1 skip guard in detection loop — header values never appear as patches in sanitized output
- Added Phase 4 gate test: medium fixture + hide-all integration (161 tests all green)

## Task Commits

Each task was committed atomically:

1. **Task 1: Column-header context boosting in PiiDetector.detect_cell()** - `79f6570` (feat)
2. **Task 2: Header pre-pass in Sanitizer.run() + row-1 skip guard + integration test** - `61f543b` (feat)

**Plan metadata:** _(to be added by final commit)_

_Note: Both tasks used TDD — tests written first, confirmed failing, then implementation added._

## Files Created/Modified
- `src/xlcloak/detector.py` - Added `_PII_HEADER_KEYWORDS`, `_BOOSTED_THRESHOLD`, `_header_matches_pii_keyword()`, updated `detect_cell()` signature
- `src/xlcloak/sanitizer.py` - Added `sheet_headers` pre-pass, row-1 skip guard, `column_header` passed to `detect_cell()`
- `tests/test_detector.py` - Added `test_header_matches_pii_keyword_positive`, `test_header_matches_pii_keyword_negative`, `test_header_boosting_detect_cell`
- `tests/test_sanitizer.py` - Added `test_sanitize_header_row_not_tokenized`, `test_sanitize_medium_fixture_hide_all_integration`

## Implementation Details

**Header keyword set:**
```python
_PII_HEADER_KEYWORDS = frozenset({
    "name", "customer", "contact", "email", "phone",
    "company", "ssn", "personid", "personnummer", "organisation",
})
```

**Boosted threshold:** 0.3 (default: 0.4) — accepts matches that normal mode rejects

**sheet_headers structure:**
```python
sheet_headers: dict[str, dict[int, str]] = {}
# {sheet_name: {col_index: header_text}}
# e.g., {"Contacts": {1: "Name", 2: "Email", 3: "Phone"}}
```

**Integration test outcome:** medium fixture + hide-all mode completed successfully. The medium fixture contains synthetic (Luhn-invalid) Swedish PII and company names; hide-all bypasses detection so Luhn-invalid values are not an issue.

## Decisions Made

- Header keyword matching uses substring check (`any(kw in header.lower())`) not exact match — handles compound headers like "Customer Name" and "Email Address" naturally
- `hide_all=True` branch left unchanged — in hide-all mode, every text cell (including row-1) is replaced; no header distinction
- Test fix applied: plan-written tests checked `output` path directly but `derive_output_paths()` appends `_sanitized` suffix; corrected to use `result.sanitized_path`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test path assertions for derive_output_paths behavior**
- **Found during:** Task 2 (RED phase running test_sanitize_header_row_not_tokenized)
- **Issue:** Plan-written tests used `output` path (e.g., `out.xlsx`) for `load_workbook()` and `output.exists()`, but `derive_output_paths()` appends `_sanitized` suffix producing `out_sanitized.xlsx`
- **Fix:** Changed `load_workbook(output)` to `load_workbook(result.sanitized_path)` and `output.exists()` to `result.sanitized_path.exists()`
- **Files modified:** tests/test_sanitizer.py
- **Verification:** Both tests pass after fix
- **Committed in:** `61f543b` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan-provided test code)
**Impact on plan:** Fix was necessary for correctness. Plan-provided test code assumed output path = final path, but derive_output_paths always appends `_sanitized`. No scope creep.

## Issues Encountered
None beyond the test path fix above.

## Known Stubs
None - all functionality is fully implemented and wired.

## Next Phase Readiness
- Phase 4 (power-features) is COMPLETE — all 3 plans executed, all 161 tests green
- SC1 (Swedish PII detected + Luhn rejects false positives): test_personnummer_detected + test_personnummer_checksum_rejects_invalid pass
- SC2 (Header boosting visible): test_header_matches_pii_keyword_positive + test_header_boosting_detect_cell pass
- SC3 (Company suffix detection): test_company_suffix_detected + test_company_suffix_no_false_positive pass
- SC4 (--hide-all mode): test_sanitize_hide_all_replaces_all_cells + test_cli_hide_all_dry_run pass

## Self-Check: PASSED

All files found: src/xlcloak/detector.py, src/xlcloak/sanitizer.py, tests/test_detector.py, tests/test_sanitizer.py, 04-03-SUMMARY.md
All commits found: 79f6570 (Task 1), 61f543b (Task 2), e5667ad (metadata)

---
*Phase: 04-power-features*
*Completed: 2026-04-04*
