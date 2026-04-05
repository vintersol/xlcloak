---
phase: quick
plan: 260404-uuo
type: execute
wave: 1
depends_on: []
files_modified:
  - src/xlcloak/restorer.py
  - src/xlcloak/detector.py
  - tests/test_restorer.py
  - tests/test_detector.py
autonomous: true
must_haves:
  truths:
    - "Cells containing mixed text and tokens are fully restored (substring replacement)"
    - "Common English words like Budget and Account are not flagged as PII by NER"
    - "All e2e round-trip tests pass (simple, medium, hard fixtures)"
  artifacts:
    - path: "src/xlcloak/restorer.py"
      provides: "Substring-based token replacement in restore pipeline"
      contains: "re.sub"
    - path: "src/xlcloak/detector.py"
      provides: "NER false-positive deny-list filtering"
      contains: "NER_DENY_LIST"
  key_links:
    - from: "src/xlcloak/restorer.py"
      to: "reverse_map keys"
      via: "compiled regex pattern from all token keys"
      pattern: "re\\.compile|re\\.sub"
    - from: "src/xlcloak/detector.py"
      to: "analyzer.analyze results"
      via: "post-analysis deny-list filter"
      pattern: "NER_DENY_LIST"
---

<objective>
Fix two bugs causing e2e round-trip test failures: (1) restorer only replaces cells whose entire value matches a token — must do substring replacement, (2) spaCy NER tags common English words (Budget, Account) as ORGANIZATION — must filter these via deny-list.

Purpose: Make sanitize-restore round-trip lossless for all fixture files.
Output: Fixed restorer.py and detector.py with updated unit tests.
</objective>

<execution_context>
@/home/ajans/code/xlcloak/.claude/get-shit-done/workflows/execute-plan.md
@/home/ajans/code/xlcloak/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/xlcloak/restorer.py
@src/xlcloak/detector.py
@tests/test_restorer.py
@tests/test_detector.py
@tests/test_e2e.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix restorer substring token replacement</name>
  <files>src/xlcloak/restorer.py, tests/test_restorer.py</files>
  <behavior>
    - Test: cell with single token "PERSON_001" restores to original (existing behavior preserved)
    - Test: cell with mixed text "Contact PERSON_001 at EMAIL_002" restores both tokens via substring replacement
    - Test: cell with no tokens remains unchanged
    - Test: overlapping token prefixes (e.g. PERSON_001 vs PERSON_0019) — longer token replaced correctly (sort by length desc)
    - Test: restored_count counts cells where at least one substitution occurred, not total token replacements
    - Test: found_tokens tracks all tokens found across all cells (for skipped/missing logic)
  </behavior>
  <action>
In `src/xlcloak/restorer.py`, replace the exact-match restore logic (lines 144-153) with regex-based substring replacement:

1. Add `import re` at top of file.

2. After building `reverse_map` (line 126), build a compiled regex pattern:
   - Sort reverse_map keys by length descending (longest first to avoid prefix collisions)
   - Compile: `token_pattern = re.compile("|".join(re.escape(k) for k in sorted(reverse_map.keys(), key=len, reverse=True)))`
   - Handle empty reverse_map gracefully (set token_pattern to None, skip regex work)

3. Replace the cell iteration loop (lines 144-153) with:
   ```python
   for cell in reader.iter_text_cells(wb):
       cells_walked += 1
       if token_pattern is None:
           continue
       cell_found: set[str] = set()
       def _replace(m: re.Match) -> str:
           cell_found.add(m.group(0))
           return reverse_map[m.group(0)]
       new_value = token_pattern.sub(_replace, cell.value)
       if cell_found:
           patches.append((cell.sheet_name, cell.row, cell.col, new_value))
           found_tokens.update(cell_found)
   ```

4. Update `restored_count = len(patches)` — this now counts cells with at least one substitution (correct semantics).

5. Update unit tests in `tests/test_restorer.py` to add tests for substring replacement, mixed-content cells, and the no-match case. Keep all existing tests passing.
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest tests/test_restorer.py -x -v</automated>
  </verify>
  <done>Restorer handles substring token replacement in mixed-content cells. All restorer unit tests pass including new ones for mixed content.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add NER false-positive deny-list to detector</name>
  <files>src/xlcloak/detector.py, tests/test_detector.py</files>
  <behavior>
    - Test: "Budget approved for 2026" does NOT produce an ORGANIZATION detection for "Budget"
    - Test: "Account manager review" does NOT produce ORGANIZATION/PERSON detections for "Account" or "manager"
    - Test: legitimate entity "Microsoft" still detected as ORGANIZATION (not in deny-list)
    - Test: deny-list only applies to NER-based detections (PERSON, ORGANIZATION), not pattern-based
    - Test: deny-list matching is case-insensitive
  </behavior>
  <action>
In `src/xlcloak/detector.py`:

1. Add a module-level deny-list constant after the existing `_BOOSTED_THRESHOLD` line:
   ```python
   # Common English words that spaCy's NER frequently misclassifies as PERSON or ORGANIZATION.
   # Only add words with evidence of false positives — keep this conservative.
   NER_DENY_LIST: frozenset[str] = frozenset({
       "budget", "account", "contract", "invoice", "meeting",
       "report", "review", "manager", "project", "department",
       "office", "system", "service", "team", "group",
       "policy", "schedule", "plan", "proposal", "agreement",
   })
   ```

2. In `detect_cell()`, after the overlap-removal step (line 163, `deduped_results = non_overlapping`) and BEFORE the right-to-left sort, add deny-list filtering:
   ```python
   # Filter NER false positives: common English words tagged as PERSON/ORGANIZATION
   deduped_results = [
       r for r in deduped_results
       if not (
           r.entity_type in ("PERSON", "ORGANIZATION", "COMPANY_SUFFIX")
           and cell.value[r.start:r.end].lower() in NER_DENY_LIST
       )
   ]
   ```

3. Update unit tests in `tests/test_detector.py` to verify deny-list filtering works for known false positives and does not filter legitimate entities.
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest tests/test_detector.py -x -v</automated>
  </verify>
  <done>NER deny-list filters false positives for common English words. Legitimate entities still detected. All detector unit tests pass.</done>
</task>

<task type="auto">
  <name>Task 3: Verify e2e round-trip tests pass</name>
  <files></files>
  <action>
Run the full e2e test suite to confirm both fixes work together in the round-trip pipeline. Also run the complete test suite to ensure no regressions.

1. Run e2e tests: `uv run pytest tests/test_e2e.py -x -v`
2. Run full suite: `uv run pytest -x`
3. If any test fails, diagnose and fix. The most likely remaining issues:
   - Additional NER false positives not in the deny-list — add them
   - Edge cases in token regex (special characters in tokens) — re.escape should handle this
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest -x</automated>
  </verify>
  <done>All e2e round-trip tests pass (simple.xlsx, medium.xlsx, hard.xlsx). Full test suite passes with zero failures.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_restorer.py -x -v` — all restorer tests pass
- `uv run pytest tests/test_detector.py -x -v` — all detector tests pass
- `uv run pytest tests/test_e2e.py -x -v` — all round-trip tests pass
- `uv run pytest -x` — full suite, zero failures
</verification>

<success_criteria>
- Restorer performs substring token replacement (not exact-match only)
- NER deny-list prevents false positives for common English words
- All three e2e round-trip fixtures (simple, medium, hard) pass
- Full test suite passes with no regressions
</success_criteria>

<output>
After completion, create `.planning/quick/260404-uuo-fix-restorer-substring-replacement-and-n/260404-uuo-SUMMARY.md`
</output>
