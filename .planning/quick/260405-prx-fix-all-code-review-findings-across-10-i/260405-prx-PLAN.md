---
phase: quick
plan: 260405-prx
type: execute
wave: 1
depends_on: []
files_modified:
  - src/xlcloak/token_engine.py
  - src/xlcloak/cli.py
  - src/xlcloak/bundle.py
  - src/xlcloak/detector.py
  - src/xlcloak/sanitizer.py
  - src/xlcloak/pyproject.toml
  - tests/test_token_engine.py
  - tests/test_models.py
autonomous: true
must_haves:
  truths:
    - "SSN_SE and ORGNUM_SE tokens no longer resemble real Swedish PII"
    - "diff command detects tokens embedded in mixed-content cells"
    - "dry-run and inspect skip row-1 headers matching actual sanitize behavior"
    - "BundleReader rejects truncated files with a clear error"
    - "Unknown Presidio entity types produce GENERIC fallback instead of KeyError"
    - "All 173 existing tests pass"
    - "All 3 e2e round-trip tests pass"
  artifacts:
    - path: "src/xlcloak/token_engine.py"
      provides: "SSN_SE_NNN / ORGNUM_SE_NNN token format"
    - path: "src/xlcloak/cli.py"
      provides: "Regex-based diff, header-skipping dry-run and inspect"
    - path: "src/xlcloak/bundle.py"
      provides: "Salt length guard in BundleReader.read()"
    - path: "src/xlcloak/detector.py"
      provides: "Explicit ValueError instead of assert; .get() fallback for unknown entities"
  key_links:
    - from: "src/xlcloak/token_engine.py"
      to: "tests/test_token_engine.py"
      via: "Token format regex assertions must match new format"
      pattern: "SSN_SE_\\d{3}|ORGNUM_SE_\\d{3}"
---

<objective>
Fix 10 code review findings across the xlcloak codebase, grouped into 4 logical tasks.

Purpose: Harden defensive coding, fix behavioral divergences between CLI commands and core logic, eliminate PII-resembling token formats, and clean up unused dependencies.
Output: All source files patched, all 173+ tests green.
</objective>

<execution_context>
@/home/ajans/code/xlcloak/.claude/get-shit-done/workflows/execute-plan.md
@/home/ajans/code/xlcloak/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/xlcloak/token_engine.py
@src/xlcloak/cli.py
@src/xlcloak/bundle.py
@src/xlcloak/detector.py
@src/xlcloak/sanitizer.py
@src/xlcloak/models.py
@src/xlcloak/restorer.py
@tests/test_token_engine.py
@tests/test_models.py
@tests/test_e2e.py
@pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix token format for SSN_SE and ORGNUM_SE</name>
  <files>src/xlcloak/token_engine.py, tests/test_token_engine.py</files>
  <action>
**Finding 1 — Token formats resemble real Swedish PII.**

In `src/xlcloak/token_engine.py`, change the two token format strings inside `TokenFormatter.format()`:

- Line 44: `case EntityType.SSN_SE:` — change `f"1000000-{counter:04d}"` to `f"SSN_SE_{counter:03d}"`
- Line 46: `case EntityType.ORGNUM_SE:` — change `f"000000-{counter:04d}"` to `f"ORGNUM_SE_{counter:03d}"`

This aligns with the naming style used by PERSON_NNN, ORG_NNN, EMAIL_NNN.

In `tests/test_token_engine.py`, update the 4 assertions that match the old format:

- Line 108: change regex from `r"^1000000-\d{4}$"` to `r"^SSN_SE_\d{3}$"`
- Line 116: change regex from `r"^000000-\d{4}$"` to `r"^ORGNUM_SE_\d{3}$"`
- Line 286: change regex from `r"^1000000-\d{4}$"` to `r"^SSN_SE_\d{3}$"`
- Line 294: change regex from `r"^000000-\d{4}$"` to `r"^ORGNUM_SE_\d{3}$"`

No changes needed in restorer.py — it builds regex dynamically from reverse_map keys, so new token strings will work automatically. No changes needed in test_e2e.py — it compares round-trip cell values, not token shapes.
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest tests/test_token_engine.py -x -q</automated>
  </verify>
  <done>SSN_SE tokens are `SSN_SE_001` style, ORGNUM_SE tokens are `ORGNUM_SE_001` style. All token engine tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Fix CLI diff/dry-run/inspect behavioral divergences</name>
  <files>src/xlcloak/cli.py</files>
  <action>
**Finding 2 — `diff` command uses exact match instead of regex.**

In `cli.py` lines 397-408, the `diff` command checks `cell_ref.value in reverse_map` which only catches cells whose entire value is a single token. Mixed-content cells (e.g., "Contact: PERSON_001 at EMAIL_001@example.com") are missed.

Fix: Build the same compiled-regex pattern as `restorer.py` does, then use `re.findall()` to detect tokens:

After line 388 (`reverse_map: dict[str, str] = payload.get("reverse_map", {})`), add:

```python
import re
# Build compiled regex from reverse_map keys (same approach as restorer.py)
if reverse_map:
    sorted_keys = sorted(reverse_map.keys(), key=len, reverse=True)
    token_pattern = re.compile("|".join(re.escape(k) for k in sorted_keys))
else:
    token_pattern = None
```

Then replace the cell-walking loop (lines 401-408) to use regex matching:

```python
for cell_ref in reader.iter_text_cells(wb):
    if token_pattern is None:
        non_token_count += 1
        continue
    matches = token_pattern.findall(cell_ref.value)
    if matches:
        cell_addr = get_column_letter(cell_ref.col) + str(cell_ref.row)
        for token in matches:
            found_tokens.setdefault(token, []).append(
                (cell_ref.sheet_name, cell_addr)
            )
    else:
        non_token_count += 1
```

Note: `re` is already available in the module scope (add `import re` at top of file if not present — check first).

**Finding 3 — `sanitize --dry-run` does not skip row-1 headers.**

In the dry-run path (around line 110), the loop `for cell_ref in reader.iter_text_cells(wb)` iterates all cells including row-1 headers. The actual `Sanitizer.run()` skips `cell.row == 1` and uses header-based boosting.

Fix: Add header extraction and row-1 skip logic mirroring `Sanitizer.run()`:

After `wb = reader.open()` and before the cell iteration loop, add:
```python
# Pre-pass: extract column headers (mirrors Sanitizer.run)
text_cells = list(reader.iter_text_cells(wb))
sheet_headers: dict[str, dict[int, str]] = {}
for cell_ref in text_cells:
    if cell_ref.row == 1:
        sheet_headers.setdefault(cell_ref.sheet_name, {})[cell_ref.col] = cell_ref.value or ""
```

Then change the detection loop to:
```python
all_results = []
for cell_ref in text_cells:
    if cell_ref.row == 1:
        continue
    col_header = sheet_headers.get(cell_ref.sheet_name, {}).get(cell_ref.col)
    scan_results, _replaced = detector.detect_cell(cell_ref, registry, column_header=col_header)
    all_results.extend(scan_results)
```

**Finding 4 — `inspect` command has the same header-skip divergence.**

Apply the same pattern to the `inspect` command (around line 271). After opening the workbook, add header extraction, convert to list, then skip row-1 and pass `column_header` to `detect_cell`:

```python
text_cells = list(reader.iter_text_cells(wb))
sheet_headers: dict[str, dict[int, str]] = {}
for cell_ref in text_cells:
    if cell_ref.row == 1:
        sheet_headers.setdefault(cell_ref.sheet_name, {})[cell_ref.col] = cell_ref.value or ""

all_results = []
for cell_ref in text_cells:
    if cell_ref.row == 1:
        continue
    col_header = sheet_headers.get(cell_ref.sheet_name, {}).get(cell_ref.col)
    scan_results, _replaced = detector.detect_cell(cell_ref, registry, column_header=col_header)
    all_results.extend(scan_results)
```
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest tests/test_cli.py -x -q</automated>
  </verify>
  <done>diff uses regex substring scan for token detection. dry-run and inspect both skip row-1 headers and pass column_header for boost logic, matching Sanitizer.run() behavior.</done>
</task>

<task type="auto">
  <name>Task 3: Defensive coding fixes in bundle, detector, sanitizer</name>
  <files>src/xlcloak/bundle.py, src/xlcloak/detector.py, src/xlcloak/sanitizer.py</files>
  <action>
**Finding 5 — BundleReader.read() missing salt length guard.**

In `bundle.py` line 117, after `data = path.read_bytes()`, add before the salt slice:

```python
if len(data) < SALT_LENGTH:
    raise ValueError(
        "Bundle file is too small -- corrupted or not a valid .xlcloak file"
    )
```

**Finding 6 — detector.py uses assert for runtime check.**

In `detector.py` line 128, replace:
```python
assert cell.value is not None, "cell.value must not be None"
```
with:
```python
if cell.value is None:
    raise ValueError("cell.value must not be None")
```

**Finding 7 — PRESIDIO_TO_ENTITY_TYPE KeyError on unknown entity.**

In `detector.py` line 173, replace:
```python
entity_type = PRESIDIO_TO_ENTITY_TYPE[result.entity_type]
```
with:
```python
entity_type = PRESIDIO_TO_ENTITY_TYPE.get(result.entity_type)
if entity_type is None:
    import warnings
    warnings.warn(
        f"Unknown Presidio entity type '{result.entity_type}' -- falling back to GENERIC",
        stacklevel=2,
    )
    entity_type = EntityType.GENERIC
```

Note: `import warnings` should be at the top of file to follow convention. Move it there if preferred, but a local import in this rarely-hit branch is also acceptable.

**Finding 8 — sanitizer.py variable shadows parameter.**

In `sanitizer.py` line 120, the unpacking:
```python
sanitized_path, bundle_path, manifest_path = derive_output_paths(...)
```
shadows the `bundle_path` parameter (line 104). Rename to:
```python
sanitized_out, bundle_out, manifest_out = derive_output_paths(
    input_path, output_path, bundle_path
)
```

Then update ALL subsequent references in the method body:
- `check_overwrite([sanitized_out, bundle_out, manifest_out], force)` (was line 123)
- `bundle_writer.write(bundle_out, ...)` (was line 175, using `bundle_path`)
- `manifest_out.write_text(manifest.render())` (was line 193, using `manifest_path`)
- `return SanitizeResult(sanitized_path=sanitized_out, bundle_path=bundle_out, manifest_path=manifest_out, ...)` (was line 195-201)

Verify no other references to `sanitized_path`, `bundle_path`, or `manifest_path` as local variables remain (the parameter `bundle_path` is still used in the `derive_output_paths` call).
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest tests/test_bundle.py tests/test_detector.py tests/test_sanitizer.py -x -q</automated>
  </verify>
  <done>BundleReader rejects truncated files. Detector uses explicit ValueError and GENERIC fallback. Sanitizer has no variable shadowing.</done>
</task>

<task type="auto">
  <name>Task 4: Cleanup — unused import, unused deps, stale docstring</name>
  <files>src/xlcloak/sanitizer.py, pyproject.toml, tests/test_models.py</files>
  <action>
**Finding 9 — Unused `import sys` in sanitizer.py.**

Remove line 5 (`import sys`) from `src/xlcloak/sanitizer.py`. Verify `sys` is not used anywhere in the file (it is not — `sys.exit` calls are only in `cli.py`).

**Finding 10 — Unused dependencies in pyproject.toml.**

In `pyproject.toml`, remove these two lines from the `dependencies` array:
- `"presidio-anonymizer>=2.2.354",` (line 25) — never imported anywhere in src/
- `"pyyaml>=6.0.1",` (line 27) — never imported anywhere in src/

Keep `presidio-analyzer` — it IS used. Keep all other deps.

**Finding 11 — Stale docstring in test_models.py.**

In `tests/test_models.py` line 14, the function `test_entity_type_has_seven_members` has a name saying "seven" but the assertion checks for 8. Rename the function to `test_entity_type_has_eight_members`. The docstring is in the function name itself (no separate docstring to fix).
  </action>
  <verify>
    <automated>cd /home/ajans/code/xlcloak && uv run pytest tests/ -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>No unused imports. No unused dependencies in pyproject.toml. Test function name matches reality (eight members).</done>
</task>

</tasks>

<verification>
Run the full test suite to confirm no regressions:

```bash
cd /home/ajans/code/xlcloak && uv run pytest tests/ -x -q
```

All 173+ tests must pass. The 3 e2e round-trip tests (simple.xlsx, medium.xlsx, hard.xlsx) must pass — these validate that the token format change does not break the sanitize-restore cycle.

Verify ruff passes:
```bash
cd /home/ajans/code/xlcloak && uv run ruff check src/ tests/
```
</verification>

<success_criteria>
- All 173+ existing tests pass (0 failures)
- All 3 e2e round-trip tests pass
- `ruff check` clean on modified files
- SSN_SE tokens are `SSN_SE_NNN` format (no numeric-only tokens)
- ORGNUM_SE tokens are `ORGNUM_SE_NNN` format
- `diff` command uses regex substring matching
- `dry-run` and `inspect` skip row-1 headers
- BundleReader rejects files < 16 bytes
- No `assert` used for runtime validation in detector
- Unknown entity types produce GENERIC fallback with warning
- No variable shadowing in sanitizer
- No unused imports or dependencies
</success_criteria>

<output>
After completion, create `.planning/quick/260405-prx-fix-all-code-review-findings-across-10-i/260405-prx-SUMMARY.md`
</output>
