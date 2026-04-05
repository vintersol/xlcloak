---
phase: 04-power-features
plan: "01"
subsystem: detection
tags: [swedish-pii, personnummer, org-nummer, luhn, presidio, entity-type]
dependency_graph:
  requires: []
  provides: [SwePersonnummerRecognizer, SweOrgNummerRecognizer, EntityType.GENERIC]
  affects: [detector, token_engine, models]
tech_stack:
  added: []
  patterns: [PatternRecognizer-subclass, validate_result-return-bool, registry.add_recognizer]
key_files:
  created:
    - src/xlcloak/recognizers.py
  modified:
    - src/xlcloak/models.py
    - src/xlcloak/token_engine.py
    - src/xlcloak/detector.py
    - tests/test_models.py
    - tests/test_token_engine.py
    - tests/test_detector.py
decisions:
  - "validate_result() returns True/False never mutates self.score — class-level attribute would corrupt subsequent recognitions"
  - "Recognizers registered via self._analyzer.registry.add_recognizer() not AnalyzerEngine.add_recognizer() (API differs from plan example)"
  - "SweOrgNummerRecognizer requires hyphen (NNNNNN-NNNN) while SwePersonnummerRecognizer accepts 10-digit with or without separator"
metrics:
  duration: "12m 16s"
  completed_date: "2026-04-04"
  tasks_completed: 3
  files_created: 1
  files_modified: 5
---

# Phase 04 Plan 01: Swedish Recognizers and GENERIC Entity Type Summary

Swedish personnummer and org-nummer Luhn-validated PatternRecognizer subclasses with EntityType.GENERIC for hide-all mode.

## What Was Implemented

### EntityType.GENERIC (Task 1)
- Added `GENERIC = "GENERIC"` to `EntityType` enum in `src/xlcloak/models.py`
- Added `case EntityType.GENERIC: return f"CELL_{counter:04d}"` match case in `TokenFormatter.format()` in `src/xlcloak/token_engine.py`
- `TokenFormatter.format(EntityType.GENERIC, 1)` returns `"CELL_0001"`, counter zero-padded to 4 digits

### SwePersonnummerRecognizer and SweOrgNummerRecognizer (Task 2)
New module `src/xlcloak/recognizers.py` containing:

**`_luhn_personnummer(digits_10)`** — Luhn variant using multipliers `[2,1,2,1,2,1,2,1,2]` applied left-to-right. Products >= 10 have 9 subtracted. Check digit at position 9 must equal `(10 - sum % 10) % 10`.

**`_luhn_orgnummer(digits_10)`** — Standard Luhn-10. Doubles every second digit from right (odd indices in 0-based right-to-left iteration). Total mod 10 must equal 0.

**`SwePersonnummerRecognizer`** — Two regex patterns:
- `personnummer_10`: `\b\d{6}[-+]?\d{4}\b` (10-digit with optional separator)
- `personnummer_12`: `\b\d{8}[-+]?\d{4}\b` (12-digit with century prefix)

`validate_result()` strips non-digits, strips 2-char century prefix for 12-digit form, runs Luhn variant on 10 digits.

**`SweOrgNummerRecognizer`** — One regex pattern:
- `orgnummer`: `\b\d{6}-\d{4}\b` (hyphen mandatory per Bolagsverket notation)

`validate_result()` strips non-digits, runs standard Luhn-10.

### Valid test data constants
```python
VALID_PERSONNUMMER_10 = "8112189876"          # valid 10-digit, no separator
VALID_PERSONNUMMER_10_HYPHEN = "811218-9876"  # valid 10-digit with hyphen
VALID_PERSONNUMMER_12 = "198112189876"        # valid 12-digit (century prefix 19)
VALID_ORGNUMMER = "556036-0793"              # Volvo AB — valid Luhn-10
```

### Detector registration (Task 3)
- `PRESIDIO_TO_ENTITY_TYPE` extended with `"PERSONNUMMER_SE": EntityType.SSN_SE` and `"ORGNUM_SE": EntityType.ORGNUM_SE`
- `_get_analyzer()` now calls `self._analyzer.registry.add_recognizer()` for both recognizers after engine init
- Added `test_personnummer_detect_cell_no_keyerror` integration test (requires spaCy) verifying no `KeyError` on full `detect_cell()` path

## validate_result() Pattern

`validate_result()` returns `True` to accept a match or `False` to reject it. Never mutates `self.score` — that is a class-level attribute and mutations persist across calls, corrupting all subsequent recognitions. Pattern used in both recognizers:

```python
def validate_result(self, pattern_text: str) -> bool | None:
    digits = re.sub(r"[^0-9]", "", pattern_text)
    # ... digit length checks ...
    if not _luhn_function(digits):
        return False
    return True
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AnalyzerEngine.add_recognizer() does not exist in installed Presidio version**
- **Found during:** Task 3
- **Issue:** The plan example used `self._analyzer.add_recognizer(...)` but the installed Presidio version exposes `add_recognizer()` only on the registry, not on `AnalyzerEngine` directly. The engine has only `get_recognizers` plus the private `__add_recognizer_id_if_not_exists`.
- **Fix:** Changed to `self._analyzer.registry.add_recognizer(...)` which is the correct API path.
- **Files modified:** `src/xlcloak/detector.py`
- **Commit:** a24c289

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Fast suite (no spaCy integration) | 149 | All passed |
| spaCy integration test | 1 | Passed |
| Total | 150 | All green |

## Self-Check: PASSED
