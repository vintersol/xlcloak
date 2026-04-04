---
phase: quick
plan: 260404-uuo
subsystem: restorer, detector
tags: [bug-fix, regex, ner, e2e, round-trip]
dependency_graph:
  requires: []
  provides: [substring-restore, ner-deny-list, overlapping-span-fix]
  affects: [src/xlcloak/restorer.py, src/xlcloak/detector.py]
tech_stack:
  added: []
  patterns: [greedy-interval-selection, regex-sub-reverse-map, frozenset-deny-list]
key_files:
  created:
    - tests/test_e2e.py
  modified:
    - src/xlcloak/restorer.py
    - src/xlcloak/detector.py
    - tests/test_restorer.py
    - tests/test_detector.py
decisions:
  - "Greedy span selection (longest wins) for overlapping Presidio detections — prevents garbled sanitized output when EMAIL and URL share a domain substring"
  - "NER_DENY_LIST as frozenset at module level — conservative, only add words with confirmed false positives"
  - "token_pattern=None guard for empty reverse_map avoids no-op regex compile overhead"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-04"
  tasks_completed: 3
  files_changed: 5
---

# Quick Task 260404-uuo: Fix Restorer Substring Replacement and NER False Positives

**One-liner:** Regex-based substring token restoration and NER deny-list filtering, plus greedy span deduplication fix that prevented e2e round-trip from passing.

## What Was Done

### Task 1: Substring token replacement in restorer

The restorer previously used exact-match (`if cell.value in reverse_map`) which failed for cells containing tokens embedded in surrounding text (e.g., `"Contact PERSON_001 at EMAIL_002@example.com for details"`).

Fixed by:
- Adding `import re` to `restorer.py`
- Building a compiled `token_pattern` from reverse_map keys sorted longest-first (prevents prefix collisions like `PERSON_001` vs `PERSON_0019`)
- Replacing exact-match with `token_pattern.sub()` for substring replacement
- `restored_count` now counts cells with at least one substitution (correct semantics)

### Task 2: NER deny-list for false positives

SpaCy's NER frequently classifies common English business words (`Budget`, `Account`, etc.) as ORGANIZATION. Added `NER_DENY_LIST` frozenset to filter these post-analysis.

Fixed by:
- Adding `NER_DENY_LIST` module-level constant with 20 common false-positive words
- Filtering PERSON/ORGANIZATION/COMPANY_SUFFIX results where matched text is in deny-list
- Pattern-based detections (email, phone, URL) are unaffected

### Task 3: E2e round-trip tests + overlapping span fix (auto-fix)

Running e2e tests revealed a **pre-existing sanitizer bug**: when Presidio detected both EMAIL (0-19) and URL (11-19) on `john.smith@acme.com`, both spans survived deduplication (different spans), then right-to-left replacement corrupted the cell value because inner-span replacements shifted character offsets used by outer-span replacements.

Fixed by:
- Replacing the simple `(start, end)` exact dedup with greedy interval selection
- Keeps the longest span when any two spans overlap (longest wins, then by score)
- This fix resolves the root cause of all 3 e2e test failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed overlapping span deduplication in detect_cell()**
- **Found during:** Task 3 (e2e test execution)
- **Issue:** Presidio detects EMAIL and URL on the same email address (URL recognizer fires on the domain). Both survived the `(start, end)` dedup (different spans). Right-to-left replacement processed the inner URL span first, then the outer EMAIL span at original offsets on the already-modified string, producing garbled output like `EMAIL_003@example.comexample.com/URL_002`.
- **Fix:** Added greedy interval selection — sort candidates by (length, score) descending, keep a span only if it doesn't overlap with any already-accepted span.
- **Files modified:** `src/xlcloak/detector.py`
- **Commit:** `a7c6e3b`

## Commits

| Hash | Message |
|------|---------|
| `0f62808` | feat(quick-260404-uuo): substring token replacement in restorer |
| `21131d4` | feat(quick-260404-uuo): add NER deny-list to filter false positives |
| `a7c6e3b` | feat(quick-260404-uuo): add e2e round-trip tests; fix overlapping span bug |

## Test Results

- `uv run pytest tests/test_restorer.py` — 19 passed
- `uv run pytest tests/test_detector.py` — 23 passed
- `uv run pytest tests/test_e2e.py` — 3 passed (simple.xlsx, medium.xlsx, hard.xlsx)
- `uv run pytest` — 174 passed, 0 failed

## Self-Check: PASSED

- `src/xlcloak/restorer.py` — exists, uses `token_pattern.sub()` (Pattern.sub is equivalent to re.sub per plan intent)
- `src/xlcloak/detector.py` — exists, contains `NER_DENY_LIST`
- `tests/test_e2e.py` — exists
- All commits (0f62808, 21131d4, a7c6e3b) verified in git log
