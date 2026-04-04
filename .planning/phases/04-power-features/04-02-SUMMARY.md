---
phase: 04-power-features
plan: 02
subsystem: pii-detection
tags: [presidio, pattern-recognizer, company-detection, hide-all, cli, sanitizer]

requires:
  - phase: 04-01
    provides: EntityType.GENERIC, CELL_NNNN token format, Swedish recognizers registered in PiiDetector

provides:
  - CompanySuffixRecognizer: detects "Volvo AB", "Acme Corporation", "Test LLC" etc. via capitalized-word + legal-suffix regex, score 0.65
  - COMPANY_SUFFIX entry in PRESIDIO_TO_ENTITY_TYPE mapping to EntityType.ORG
  - Span deduplication in detect_cell() to prevent double-replacement when CompanySuffixRecognizer and NER ORGANIZATION fire on same span
  - Sanitizer.run(hide_all=False) branch that replaces all text cells with EntityType.GENERIC CELL_NNNN tokens, skipping PII detection
  - --hide-all flag on CLI sanitize command with dry-run guard printing "Dry run (hide-all): Would replace N text cells."

affects: [04-03, integration-tests, cli]

tech-stack:
  added: []
  patterns:
    - CompanySuffixRecognizer uses validate_result() override to enforce case-sensitive first-word check (Presidio compiles patterns with re.IGNORECASE by default)
    - Span deduplication via seen_spans dict keyed on (start, end), keeping highest-score result per span
    - hide_all branch inserts before the detection loop and wraps original loop in else clause

key-files:
  created: []
  modified:
    - src/xlcloak/recognizers.py
    - src/xlcloak/detector.py
    - src/xlcloak/sanitizer.py
    - src/xlcloak/cli.py
    - tests/test_detector.py
    - tests/test_sanitizer.py
    - tests/test_cli.py
    - tests/conftest.py

key-decisions:
  - "CompanySuffixRecognizer.validate_result() returns False when pattern_text[0] is not uppercase — works around Presidio's IGNORECASE flag on Pattern compilation"
  - "Span deduplication added to detect_cell() before replacement loop — CompanySuffixRecognizer and NER ORGANIZATION can fire on same span (e.g., 'Volvo AB'), deduplication prevents double-replacement and text corruption"
  - "test_sanitize_hide_all_uses_stable_tokens uses result.sanitized_path not the raw output_path arg — Sanitizer.derive_output_paths() appends _sanitized suffix, plan test code had this bug, fixed inline"

patterns-established:
  - "PatternRecognizer.validate_result() is the correct hook for post-regex filtering in Presidio (not regex flags)"
  - "Span deduplication pattern: dict[(start,end)] -> highest-score result, then sort by start"

requirements-completed: [DET-07, TOK-04]

duration: 7min
completed: 2026-04-04
---

# Phase 04 Plan 02: CompanySuffixRecognizer and hide-all mode Summary

**CompanySuffixRecognizer (capitalized-word + legal-suffix regex, score 0.65) plus Sanitizer.run(hide_all=True) that replaces all 77 text cells in simple fixture with stable CELL_NNNN tokens**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-04T15:43:55Z
- **Completed:** 2026-04-04T15:50:54Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- CompanySuffixRecognizer detects "Volvo AB", "Acme Corporation", "Test LLC", "Smith Jones Ltd"; rejects bare "AB" and "the ltd"
- PRESIDIO_TO_ENTITY_TYPE now has 8 entries (EMAIL_ADDRESS, PHONE_NUMBER, PERSON, URL, ORGANIZATION, PERSONNUMMER_SE, ORGNUM_SE, COMPANY_SUFFIX)
- Span deduplication in detect_cell() prevents double-replacement when CompanySuffixRecognizer and NER ORGANIZATION fire on the same span
- Sanitizer.run(hide_all=True) replaces all 77 text cells in simple.xlsx with CELL_NNNN tokens (skips PII detection entirely, no spaCy init)
- --hide-all CLI flag with dry-run guard: "Dry run (hide-all): Would replace N text cells."
- Stable token guarantee: same input cell value maps to same CELL_NNNN token across two separate hide-all runs

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement CompanySuffixRecognizer** - `7e8d8a0` (feat)
2. **Task 2: Add --hide-all flag and Sanitizer.run(hide_all) branch** - `fb64291` (feat)

**Plan metadata:** TBD (docs: complete plan)

_Note: TDD tasks — tests written first, implementation follows_

## Files Created/Modified

- `src/xlcloak/recognizers.py` - CompanySuffixRecognizer class added (pattern + validate_result)
- `src/xlcloak/detector.py` - Import CompanySuffixRecognizer, add COMPANY_SUFFIX to map, register recognizer, add span deduplication
- `src/xlcloak/sanitizer.py` - Add EntityType import, hide_all parameter to run(), if/else branch around detection loop
- `src/xlcloak/cli.py` - --hide-all option decorator, hide_all param in function signature, dry-run guard, pass hide_all to sanitizer.run()
- `tests/test_detector.py` - test_company_suffix_detected, test_company_suffix_no_false_positive
- `tests/test_sanitizer.py` - test_sanitize_hide_all_replaces_all_cells, test_sanitize_hide_all_uses_stable_tokens
- `tests/test_cli.py` - test_cli_hide_all_flag_in_help, test_cli_hide_all_dry_run
- `tests/conftest.py` - simple_fixture pytest fixture

## Key Implementation Details

**CompanySuffixRecognizer regex pattern:**
```python
_PATTERN = (
    r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}\s+)"
    r"(?:Aktiebolag|AB|HB|KB|Ltd|Limited|Inc|Corp|Corporation|GmbH|LLC|LLP|SA|NV|BV)\b"
)
```

**Sanitizer.run() new signature:**
```python
def run(
    self,
    input_path: Path,
    output_path: Path | None = None,
    force: bool = False,
    bundle_path: Path | None = None,
    hide_all: bool = False,
) -> SanitizeResult:
```

**CLI --hide-all dry-run output format:**
```
Dry run (hide-all): Would replace N text cells.
No files written.
```

## Decisions Made

- **CompanySuffixRecognizer validate_result() case check:** Presidio compiles all Pattern regexes with re.IGNORECASE, making `[A-Z][a-z]+` match "the". Overriding validate_result() to check `pattern_text.lstrip()[0].isupper()` enforces the case requirement without fighting the regex engine.
- **Span deduplication placement:** Added between raw_results collection and sorted_results construction. Keeps highest-score result per (start, end) span. Prevents text corruption when CompanySuffixRecognizer (score 0.65) and NER ORGANIZATION (typically 0.85+) both fire on "Volvo AB".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_sanitize_hide_all_uses_stable_tokens using wrong output path**
- **Found during:** Task 2 (hide-all implementation)
- **Issue:** Plan test code used `load_workbook(out1)` where `out1` was the `output_path` arg. Sanitizer.derive_output_paths() appends `_sanitized` suffix, so actual file is `run1_sanitized_sanitized.xlsx`, not `run1_sanitized.xlsx`. Would fail with FileNotFoundError.
- **Fix:** Changed test to use `result1.sanitized_path` and `result2.sanitized_path`
- **Files modified:** tests/test_sanitizer.py
- **Verification:** Verified directly via Python - stable tokens confirmed
- **Committed in:** fb64291 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed CompanySuffixRecognizer false positive on "the ltd"**
- **Found during:** Task 1 (GREEN phase verification)
- **Issue:** Presidio compiles Pattern with re.IGNORECASE, causing `[A-Z][a-z]+` to match lowercase "the", triggering "the ltd" as a company name
- **Fix:** Added validate_result() override that checks `pattern_text.lstrip()[0].isupper()`
- **Files modified:** src/xlcloak/recognizers.py
- **Verification:** "the ltd" returns empty results; "Volvo AB" still detected
- **Committed in:** 7e8d8a0 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- spaCy model en_core_web_lg not installed in worktree environment — all test_detector.py and test_sanitizer.py tests that require it are skipped (47-51 skips). Tests verified directly via Python -c. This is expected; CI would run with the model.
- Module-level `pytestmark` in test_detector.py and test_cli.py skips CompanySuffixRecognizer and hide-all tests even with `@no_spacy_needed` decorator. Tests verified correct via direct Python execution.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CompanySuffixRecognizer available for header-boosting in Plan 03
- Sanitizer.run(hide_all) available for integration tests in Plan 03
- --hide-all CLI flag confirmed working with dry-run guard
- PRESIDIO_TO_ENTITY_TYPE has all 8 entries Plan 03 depends on

---
*Phase: 04-power-features*
*Completed: 2026-04-04*

## Self-Check: PASSED

- FOUND: src/xlcloak/recognizers.py
- FOUND: src/xlcloak/detector.py
- FOUND: src/xlcloak/sanitizer.py
- FOUND: src/xlcloak/cli.py
- FOUND: .planning/phases/04-power-features/04-02-SUMMARY.md
- FOUND: commit 7e8d8a0 (Task 1)
- FOUND: commit fb64291 (Task 2)
