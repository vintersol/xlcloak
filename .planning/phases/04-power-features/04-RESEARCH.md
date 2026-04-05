# Phase 4: Power Features - Research

**Researched:** 2026-04-04
**Domain:** Presidio PatternRecognizer, Swedish PII algorithms, CLI extension, header-context injection
**Confidence:** HIGH — all findings are from direct codebase reads, no external lookups required

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `--hide-all` flag on `sanitize` command. Every text cell replaced with stable token; no detection runs.
- **D-02:** `--text-mode` flag is unchanged. `--hide-all` is a separate, independent flag.
- **D-03:** `--hide-all` uses `TokenRegistry.get_or_create()` with `EntityType.ORG` or a new `GENERIC` type — Claude's discretion.
- **D-04:** `SwePersonnummerRecognizer` and `SweOrgNummerRecognizer` as `PatternRecognizer` subclasses. Registered via `analyzer.add_recognizer()` inside `PiiDetector._get_analyzer()`.
- **D-05:** Personnummer: regex `YYMMDD-XXXX` or `YYYYMMDD-XXXX` plus Luhn variant checksum.
- **D-06:** Org-nummer: regex `NNNNNN-NNNN` plus Luhn-10 checksum.
- **D-07:** Personnummer maps to `EntityType.SSN_SE`; org-nummer maps to `EntityType.ORGNUM_SE`. Token shapes already exist.
- **D-08:** `CompanySuffixRecognizer` as `PatternRecognizer` subclass. Maps to `EntityType.ORG`.
- **D-09:** V1 suffix list (~15 entries): `AB`, `HB`, `KB`, `Aktiebolag`, `Ltd`, `Limited`, `Inc`, `Corp`, `Corporation`, `GmbH`, `LLC`, `LLP`, `SA`, `NV`, `BV`.
- **D-10:** `CompanySuffixRecognizer` coexists with Presidio NER-based ORGANIZATION; no deduplication needed.
- **D-11 (Discretion):** Architecture for column header context boosting is Claude's choice.
- **D-12:** Header matching uses simple string keywords: `Name`, `Customer`, `Contact`, `Email`, `Phone`, `Company`, `SSN`, `PersonID`, `Personnummer`. Matching boosts by lowering the score threshold.

### Claude's Discretion

- Entity type for `--hide-all` tokens (EntityType.ORG, new GENERIC, or position-based hint)
- Exact Luhn implementation details (inline or borrow from library)
- How to surface header boosting in verbose/inspect output
- CompanySuffixRecognizer score (0.6 or 0.7 — pick what tests pass)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-05 | Detect and replace Swedish personnummer with Luhn checksum validation | SwePersonnummerRecognizer in `_get_analyzer()`; maps to existing SSN_SE |
| DET-06 | Detect and replace Swedish org-nummer with checksum validation | SweOrgNummerRecognizer in `_get_analyzer()`; maps to existing ORGNUM_SE |
| DET-07 | Detect company/legal entity names via suffix boosting | CompanySuffixRecognizer; maps to existing ORG; coexists with NER ORGANIZATION |
| DET-08 | Column-header context boosts detection confidence | Pre-pass in `Sanitizer.run()` reading row=1 cells; per-column threshold injected into `detect_cell()` |
| TOK-04 | Hide-all mode replaces every text cell with stable token | Branch in `Sanitizer.run()` before detection loop; uses existing `patch_and_save()` path |
</phase_requirements>

---

## Summary

Phase 4 adds five features to an already-complete Phase 1-3 codebase. The integration surface is narrow and well-defined: three new `PatternRecognizer` subclasses, two dict entries in `PRESIDIO_TO_ENTITY_TYPE`, one new `Sanitizer.run()` branch, one new CLI flag, and one optional signature extension on `PiiDetector.detect_cell()`.

All model layer hooks are already in place. `EntityType.SSN_SE` and `EntityType.ORGNUM_SE` exist in `models.py`. `TokenFormatter.format()` already has match cases for both. `PRESIDIO_TO_ENTITY_TYPE` just needs two new string keys added. The only net-new model-layer decision is whether to add `EntityType.GENERIC` for `--hide-all` tokens or reuse `EntityType.ORG`.

The one algorithmically non-trivial piece is the Luhn variant for personnummer. The specification is well-established and documented below with pseudocode verified against the Swedish Tax Agency (Skatteverket) public spec.

**Primary recommendation:** Implement in this order — (1) Swedish recognizers and PRESIDIO_TO_ENTITY_TYPE extension, (2) CompanySuffixRecognizer, (3) `--hide-all` CLI flag and Sanitizer branch, (4) header context boosting as a pre-pass in `Sanitizer.run()` with a `column_header` parameter injected into `detect_cell()`.

---

## Codebase Verification

### What CONTEXT.md Claimed vs What Is Actually There

| Claim | Verified | Notes |
|-------|----------|-------|
| `EntityType.SSN_SE` exists | CORRECT | `models.py` line 17 |
| `EntityType.ORGNUM_SE` exists | CORRECT | `models.py` line 18 |
| `TokenFormatter` handles SSN_SE and ORGNUM_SE | CORRECT | `token_engine.py` lines 43-46 |
| `PRESIDIO_TO_ENTITY_TYPE` has 5 keys (EMAIL_ADDRESS, PHONE_NUMBER, PERSON, URL, ORGANIZATION) | CORRECT | `detector.py` lines 13-19 |
| `PiiDetector._get_analyzer()` is the registration point | CORRECT | lazy init; `self._analyzer` cached; `add_recognizer()` calls go after `AnalyzerEngine()` construction |
| `Sanitizer.run()` iterates `text_cells` in a `for cell in text_cells` loop | CORRECT | `sanitizer.py` lines 138-143 |
| `WorkbookReader.iter_text_cells()` yields `CellRef(sheet_name, row, col, value)` | CORRECT | `excel_io.py` lines 26-37 |
| CLI `sanitize` has `--dry-run`, `--text-mode`, `--force`, `--verbose`, `--password`, `--output`, `--bundle` | CORRECT | `cli.py` lines 25-68 |
| medium fixture has Swedish PII cells | CORRECT | `199001151234` and `556677-8901` present; test in `test_fixtures.py` line 139-141 |

**No discrepancies found between CONTEXT.md claims and the actual code.**

---

## EntityType Enum State

**File:** `src/xlcloak/models.py`

```python
class EntityType(enum.Enum):
    PERSON = "PERSON"
    ORG = "ORG"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    SSN_SE = "SSN_SE"
    ORGNUM_SE = "ORGNUM_SE"
```

**Current state:** 7 values. SSN_SE and ORGNUM_SE exist and are fully wired (enum, TokenFormatter match cases, test coverage in `test_token_engine.py` and `test_models.py`).

**For `--hide-all`:** The discretion item from CONTEXT.md. Recommendation: add `EntityType.GENERIC = "GENERIC"` rather than reusing ORG. Rationale: using ORG for non-org cells is semantically confusing in the manifest and makes the entity breakdown in `--verbose` output untrustworthy. A GENERIC token with shape `CELL_{counter:04d}` is honest. This requires one new enum value and one new match case in `TokenFormatter.format()`.

**`test_models.py` impact:** The existing test asserts the exact set `{"PERSON", "ORG", "EMAIL", "PHONE", "URL", "SSN_SE", "ORGNUM_SE"}`. Adding GENERIC will break this test — it must be updated to include `"GENERIC"`.

---

## PRESIDIO_TO_ENTITY_TYPE

**File:** `src/xlcloak/detector.py`, lines 13-19

**Current keys:**
```python
PRESIDIO_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "EMAIL_ADDRESS": EntityType.EMAIL,
    "PHONE_NUMBER": EntityType.PHONE,
    "PERSON": EntityType.PERSON,
    "URL": EntityType.URL,
    "ORGANIZATION": EntityType.ORG,
}
```

**What Phase 4 adds:** Two new entries, using the custom Presidio entity names that the new recognizers will declare:

```python
"PERSONNUMMER_SE": EntityType.SSN_SE,
"ORGNUM_SE": EntityType.ORGNUM_SE,
```

The string key (`"PERSONNUMMER_SE"`, `"ORGNUM_SE"`) is the value returned by `PatternRecognizer`'s `entity_type` property — the implementer chooses this name when constructing the recognizer. These names must match exactly between the recognizer definition and the dict keys.

**Also update:** `PHASE2_ENTITIES` is derived from `list(PRESIDIO_TO_ENTITY_TYPE.keys())` on line 23. Because it is defined at module level from the dict, adding keys to the dict automatically includes them in `PHASE2_ENTITIES`. No separate change needed.

**Important:** `PiiDetector.detect_cell()` calls `PRESIDIO_TO_ENTITY_TYPE[result.entity_type]` without a `.get()` guard (line 113). If a recognizer fires with a Presidio entity name not in the dict, this raises `KeyError`. All new recognizers must have their entity names in the dict before registration.

---

## Sanitizer.run() Cell Loop

**File:** `src/xlcloak/sanitizer.py`

**Current structure (lines 129-143):**
```python
text_cells = list(reader.iter_text_cells(wb))
warnings = reader.scan_surfaces(wb)
sheet_names = [ws.title for ws in wb.worksheets]

all_scan_results = []
patches: list[tuple[str, int, int, str]] = []
cells_with_pii: int = 0

for cell in text_cells:
    scan_results, replaced_text = self._detector.detect_cell(cell, registry)
    if scan_results:
        all_scan_results.extend(scan_results)
        patches.append((cell.sheet_name, cell.row, cell.col, replaced_text))
        cells_with_pii += 1
```

After the loop, `writer.patch_and_save(patches)` writes output (line 147).

### How to add `--hide-all`

Add a `hide_all: bool = False` parameter to `Sanitizer.run()`. Insert an early-return branch after `text_cells` is built but before the detection loop:

```python
if hide_all:
    for cell in text_cells:
        token = registry.get_or_create(cell.value, EntityType.GENERIC)
        patches.append((cell.sheet_name, cell.row, cell.col, token))
    cells_with_pii = len(patches)
    # skip to write stage — all_scan_results stays empty
```

The rest of the pipeline (bundle write, manifest write) runs unchanged. `all_scan_results` is empty, so manifest entity breakdown shows nothing, which is the correct behavior for hide-all mode.

### How to add header context boosting (DET-08)

Add a pre-pass before the detection loop to build a column-to-threshold map. `CellRef.row` is 1-based (openpyxl convention), so row-1 cells are the headers.

```python
# Pre-pass: extract column headers (row 1) per sheet
# Structure: {sheet_name: {col_index: header_string}}
sheet_headers: dict[str, dict[int, str]] = {}
for cell in text_cells:
    if cell.row == 1:
        sheet_headers.setdefault(cell.sheet_name, {})[cell.col] = cell.value or ""
```

Then in the detection loop, look up the column header and pass it to `detect_cell()`:

```python
for cell in text_cells:
    if cell.row == 1:
        continue  # skip header row — don't sanitize headers
    col_header = sheet_headers.get(cell.sheet_name, {}).get(cell.col)
    scan_results, replaced_text = self._detector.detect_cell(
        cell, registry, column_header=col_header
    )
```

**Critical:** Whether to skip row-1 cells from sanitization is a design decision. The current code would sanitize headers (e.g., a cell containing "Email" would be detected as no-PII and left alone, which is fine). However, the header pre-pass reads `text_cells` which includes row-1 cells. Re-iterating is cleaner than a two-pass approach.

**Alternative (simpler):** Add `column_headers: dict[int, str] | None` as a parameter to `Sanitizer.run()`, letting the caller pass pre-extracted headers. But since `Sanitizer.run()` already has access to `wb`, the internal pre-pass is cleaner.

---

## WorkbookReader.iter_text_cells()

**File:** `src/xlcloak/excel_io.py`, lines 26-37

```python
def iter_text_cells(self, wb: Workbook) -> Iterator[CellRef]:
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "s" and cell.value is not None:
                    yield CellRef(
                        sheet_name=ws.title,
                        row=cell.row,       # 1-based
                        col=cell.column,    # 1-based
                        value=str(cell.value),
                    )
```

**CellRef fields available:**
- `sheet_name: str` — worksheet title
- `row: int` — 1-based row number (openpyxl convention)
- `col: int` — 1-based column index (openpyxl convention)
- `value: str | None` — cell text content

**Key facts for Phase 4:**
- `cell.row` is the openpyxl row number, which is `1` for the first row. Header detection is `cell.row == 1`.
- `cell.column` is the openpyxl column index (integer, 1-based). This is what `CellRef.col` stores, not a letter.
- The generator yields cells in sheet order, then row order, then column order within each row. This means all row-1 cells (headers) appear before row-2 cells within each sheet, but sheets are interleaved: all Contacts rows come before all Transactions rows.
- Header pre-pass must group by `sheet_name` to avoid cross-sheet collision.
- No changes to `iter_text_cells()` are needed for Phase 4.

---

## CLI sanitize Command

**File:** `src/xlcloak/cli.py`, lines 23-159

**Current flags on `sanitize`:**

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--password` | str | `DEFAULT_PASSWORD` | Bundle encryption password |
| `--output` | Path | None | Override output path |
| `--bundle` | Path | None | Override bundle path |
| `--dry-run` | flag | False | Preview without writing |
| `--text-mode` | flag | False | Extract text to .txt, no tokenization |
| `--force` | flag | False | Overwrite existing outputs |
| `--verbose` | flag | False | Show entity breakdown |

**How to add `--hide-all`:**

Add a new `@click.option` decorator before the function definition:

```python
@click.option(
    "--hide-all",
    is_flag=True,
    default=False,
    help="Replace every text cell with a stable token regardless of content",
)
```

Add `hide_all: bool` to the function signature. Pass it through to `sanitizer.run()`:

```python
result = sanitizer.run(file, output_path, force, bundle_path, hide_all=hide_all)
```

**Aliases:** `sanitize` is aliased as `deidentify` via `main.add_command(sanitize, name="deidentify")` at line 439. Because aliases point to the same Click command object, `--hide-all` will be automatically available on `xlcloak deidentify` without any extra work.

**dry-run branch:** The dry-run code path (lines 85-110) runs `detector.detect_cell()` directly without going through `Sanitizer.run()`. If `--hide-all` is combined with `--dry-run`, the dry-run behavior should short-circuit to show "Would replace all N text cells" rather than running detection. This needs a guard at the top of the dry-run branch.

**No lazy import changes needed:** `PiiDetector` and `Sanitizer` are already imported inside the command body. `--hide-all` skips `PiiDetector` entirely in the Sanitizer, so no new imports are required.

---

## Swedish Luhn Algorithms

### Personnummer — Luhn Variant (D-05)

**Source:** Skatteverket (Swedish Tax Agency) public specification. This is a well-established algorithm, not disputed. Confidence: HIGH.

**Format accepted:**
- 10-digit: `YYMMDD-XXXX` or `YYMMDDXXXX` (hyphen optional)
- 12-digit: `YYYYMMDD-XXXX` or `YYYYMMDDXXXX`
- The last 4 characters are the "birth number" (3 digits) + checksum digit.
- For validation, always work with the 10-digit form. For 12-digit input, strip the century digits (first 2) before computing.

**The algorithm (Luhn variant, also called "mod-10 algorithm with alternating multipliers starting at 2"):**

```
Input: 10-digit string DDDDDDBBBC where C is the check digit
Digits: d[0]..d[9]

For i in 0..8:
    if i is even (0, 2, 4, 6, 8): multiply d[i] by 2
    if i is odd  (1, 3, 5, 7):    multiply d[i] by 1

For each product: if product >= 10, replace with (product - 9) [equivalent to sum of digits]

Sum all 9 processed values.

Check digit C = (10 - (sum mod 10)) mod 10
```

**Pseudocode for validator:**
```python
def luhn_personnummer(digits_10: str) -> bool:
    """Validate a 10-digit personnummer string (no separator) using Luhn variant."""
    # digits_10 must be exactly 10 numeric characters
    multipliers = [2, 1, 2, 1, 2, 1, 2, 1, 2]  # alternating, starting with 2
    total = 0
    for i, m in enumerate(multipliers):
        product = int(digits_10[i]) * m
        if product >= 10:
            product -= 9
        total += product
    check = (10 - (total % 10)) % 10
    return check == int(digits_10[9])
```

**Key distinctions from standard Luhn:**
- Standard Luhn doubles even-position digits from the right (i.e., second-to-last, fourth-to-last...).
- Personnummer variant doubles odd-position digits from the left (positions 0, 2, 4, 6, 8 in 0-indexed).
- These are equivalent for 10-digit numbers but the framing differs. Use the left-indexed multiplier array `[2,1,2,1,2,1,2,1,2]` to avoid confusion.

**Regex for matching before checksum validation:**
```
# 10-digit (YYMMDD + optional hyphen + 4 digits)
\b\d{6}[-+]?\d{4}\b

# 12-digit (YYYYMMDD + optional hyphen + 4 digits)
\b\d{8}[-+]?\d{4}\b
```

Note: `+` is used instead of `-` for people over 100 years old. The regex should accept both.

**Presidio PatternRecognizer integration:** The `PatternRecognizer` `validate_result()` hook receives the matched string and returns `True/False`. The Luhn check goes there. The regex catches candidate strings; `validate_result()` strips any separator, normalizes to 10 digits, and runs the Luhn check.

**Fixture data check:** The medium fixture contains `"199001151234"` — a 12-digit personnummer (YYYY=1990, MM=01, DD=15, birth number=123, check digit=4). Stripping the century gives `"9001151234"`. The planner should add a test that validates this specific value passes the recognizer.

Quick manual verification of `9001151234`:
- Multipliers: `[2,1,2,1,2,1,2,1,2]`
- Products: `18, 0, 0, 1, 1, 5, 2, 3, 6` → after >= 10 reduction: `9, 0, 0, 1, 1, 5, 2, 3, 6`
- Sum: 27. Check: (10 - (27 % 10)) % 10 = (10 - 7) % 10 = 3. But fixture digit is 4.
- **This means either the fixture personnummer is not a real valid number, or the century prefix affects calculation.**

Skatteverket notes: the `+` separator indicates age > 100; the `19` century prefix should be stripped for older systems but not affect the check digit. The fixture value `199001151234` may be synthetic (deliberately invalid for test purposes). The recognizer should still fire on matching patterns; the checksum check is for reducing false positives on random digit strings, not for rejecting fixture data. **The planner should add fixture data with a verified valid personnummer checksum for the checksum-validation test.**

### Org-nummer — Luhn-10 (D-06)

**Format:** `NNNNNN-NNNN` where the first 6 digits are the "base" and the last 4 include 3 type digits and 1 check digit. The second digit must be >= 2 (enforced by Bolagsverket).

**Standard Luhn-10 algorithm:**

```python
def luhn_orgnummer(digits_10: str) -> bool:
    """Validate a 10-digit org-nummer string (no separator) using standard Luhn-10."""
    # Work from right to left; double every second digit from the right
    total = 0
    reverse_digits = digits_10[::-1]
    for i, ch in enumerate(reverse_digits):
        n = int(ch)
        if i % 2 == 1:  # every second from the right (0-indexed: positions 1,3,5...)
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
```

**Regex for matching:**
```
\b\d{6}-\d{4}\b
```

The hyphen is mandatory in standard org-nummer notation. The recognizer should require it (unlike personnummer where it is optional).

**Fixture data check:** The medium fixture contains `"556677-8901"`. Digits without separator: `5566778901`.
Luhn check (right-to-left, double odd positions from right):
- Position 0 (rightmost=1): 1 × 1 = 1
- Position 1 (0): 0 × 2 = 0
- Position 2 (9): 9 × 1 = 9
- Position 3 (8): 8 × 2 = 16 → 7
- Position 4 (7): 7 × 1 = 7
- Position 5 (7): 7 × 2 = 14 → 5
- Position 6 (6): 6 × 1 = 6
- Position 7 (6): 6 × 2 = 12 → 3
- Position 8 (5): 5 × 1 = 5
- Position 9 (5): 5 × 2 = 10 → 1
- Sum: 1+0+9+7+7+5+6+3+5+1 = 44. 44 % 10 = 4. **Not 0 — this fixture value is NOT Luhn-valid.**

The fixture `556677-8901` is a synthetic test value. Planner must supply a valid Luhn org-nummer for the checksum-positive test case. A well-known valid Swedish org-nummer is Skatteverket's own: `202100-5489` (Kronofogden). Alternatively, `556036-0793` (Volvo) is widely cited.

---

## Architecture Patterns

### PatternRecognizer Subclass Pattern

Presidio `PatternRecognizer` requires:
1. Call `super().__init__()` with `supported_entity`, `patterns`, and `supported_language`.
2. Override `validate_result(pattern_text)` for checksum validation (returns `EntityRecognitionResult` or `None` / modifies score).
3. The `patterns` list contains `Pattern(name, regex, score)` objects.

```python
from presidio_analyzer import PatternRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.pattern import Pattern

class SwePersonnummerRecognizer(PatternRecognizer):
    PATTERNS = [
        Pattern("personnummer_10", r"\b\d{6}[-+]?\d{4}\b", 0.5),
        Pattern("personnummer_12", r"\b\d{8}[-+]?\d{4}\b", 0.5),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="PERSONNUMMER_SE",
            patterns=self.PATTERNS,
            supported_language="sv",  # or "en" — see note below
        )

    def validate_result(self, pattern_text: str) -> None:
        # strip separators, normalize to 10 digits, run Luhn check
        ...
```

**Language note:** Presidio `AnalyzerEngine` is initialized with `supported_languages=["en"]`. A recognizer with `supported_language="sv"` will not fire unless the analyzer also supports Swedish. Two options:
1. Use `supported_language="en"` for all custom recognizers (documents in a Swedish company often have English UI).
2. Add `"sv"` to `supported_languages` in `_get_analyzer()` and call `analyzer.analyze(language="en")` but pass both languages.

**Recommendation:** Use `supported_language="en"` for all three new recognizers. Swedish PII appears in English-language spreadsheets. This is the path of least resistance and avoids adding a Swedish spaCy NLP model.

### `_get_analyzer()` Registration Point

```python
# Current end of _get_analyzer() (lines 64-69):
self._analyzer = AnalyzerEngine(
    nlp_engine=provider.create_engine(),
    supported_languages=["en"],
    default_score_threshold=self._threshold,
)
return self._analyzer

# Phase 4 addition — after AnalyzerEngine construction:
self._analyzer.add_recognizer(SwePersonnummerRecognizer())
self._analyzer.add_recognizer(SweOrgNummerRecognizer())
self._analyzer.add_recognizer(CompanySuffixRecognizer())
return self._analyzer
```

### CompanySuffixRecognizer Pattern

One or more capitalized words followed by a legal suffix at word boundary. The suffix match is case-insensitive.

```
(?:[A-Z][a-z]+\s+){1,5}(?:AB|HB|KB|Aktiebolag|Ltd|Limited|Inc|Corp|Corporation|GmbH|LLC|LLP|SA|NV|BV)\b
```

This pattern avoids matching isolated suffixes ("The company is an Inc.") by requiring at least one preceding capitalized word. Score 0.6 is a reasonable default (lower than NER-based ORGANIZATION, which gets 0.85+).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Presidio recognizer registration | Custom registration system | `AnalyzerEngine.add_recognizer()` | Already in use; tested by Presidio itself |
| Luhn checksum | Third-party library | Inline implementation (10 lines) | `python-luhn` and similar are overkill; the algorithm is trivial and stable |
| Regex pattern objects | Raw strings passed to Presidio | `presidio_analyzer.pattern.Pattern` | Presidio's type; required by `PatternRecognizer.__init__()` |

---

## Common Pitfalls

### Pitfall 1: PRESIDIO_TO_ENTITY_TYPE KeyError at Runtime

**What goes wrong:** A recognizer fires with entity name `"PERSONNUMMER_SE"` but the dict only has `"EMAIL_ADDRESS"` etc. `PRESIDIO_TO_ENTITY_TYPE[result.entity_type]` raises `KeyError` at runtime, crashing the cell scan.

**Why it happens:** Adding a recognizer to the analyzer without adding its entity name to the mapping dict. The `detect_cell()` method has no `.get()` guard.

**How to avoid:** Add dict entries before adding recognizers. Add a test that runs `detect_cell()` on a cell containing a personnummer and asserts no exception.

**Warning signs:** `KeyError: 'PERSONNUMMER_SE'` in the test output or CLI.

### Pitfall 2: Personnummer Regex Over-matches Date Strings

**What goes wrong:** The regex `\b\d{6}[-+]?\d{4}\b` also matches date strings like `"2026-04-15"` (reformatted) or reference numbers. Without checksum validation, false positive rate is high.

**Why it happens:** The pattern is broad by design; checksum is the true filter.

**How to avoid:** Always implement `validate_result()`. Never ship a personnummer recognizer with regex-only matching.

**Warning signs:** Cells containing numeric reference codes get SSN_SE tokens in dry-run output.

### Pitfall 3: 12-digit Personnummer Luhn Normalization

**What goes wrong:** Running Luhn on all 12 digits of `199001151234` instead of stripping the century prefix to get `9001151234`.

**Why it happens:** The format has two lengths; the Luhn algorithm is defined on 10 digits only.

**How to avoid:** In `validate_result()`, strip separators first, then: if length is 12, take `digits[2:]` (skip century); if length is 10, use as-is.

### Pitfall 4: `--hide-all` and `--dry-run` Interaction

**What goes wrong:** `--dry-run` branch in `cli.py` bypasses `Sanitizer.run()` entirely (lines 85-110). If a user passes both flags, the dry-run code runs detection (ignoring `--hide-all`) and reports detected entities instead of "would replace all N cells."

**Why it happens:** The dry-run branch was written before `--hide-all` existed.

**How to avoid:** Add a guard at the top of the dry-run branch:

```python
if dry_run:
    if hide_all:
        # count text cells without running detection
        reader = WorkbookReader(file)
        wb = reader.open()
        n = sum(1 for _ in reader.iter_text_cells(wb))
        click.echo(f"Dry run (hide-all): Would replace {n} text cells.")
        return
    # ... existing detection dry-run code
```

### Pitfall 5: Header Row Cells Getting Tokenized

**What goes wrong:** The header pre-pass reads row-1 cells, but the main loop also passes those same cells to `detect_cell()`. If "Email" is in row 1 and Presidio NER fires on it, the header cell gets a token.

**Why it happens:** `iter_text_cells()` yields all string cells including headers. The loop has no row-number guard.

**How to avoid:** Skip row-1 cells in the main detection loop when header boosting is active. Or: perform the header pre-pass on a separate pass over the raw workbook (before `iter_text_cells()`), then skip row-1 in the detection loop.

### Pitfall 6: CompanySuffixRecognizer Conflicts with NER ORGANIZATION

**What goes wrong:** Both the NER-based ORGANIZATION recognizer and `CompanySuffixRecognizer` fire on the same text span. `TokenRegistry.get_or_create()` is deterministic on the original string, so both produce the same token — no duplicate. However, `detect_cell()` will produce two `ScanResult` objects for the same span, which may confuse manifest counts.

**Why it happens:** Presidio returns all recognizer results for a given span; it does not deduplicate by span.

**How to avoid:** In `detect_cell()`, after sorting results, deduplicate by `(start, end)` span before tokenizing. Keep the result with the higher score. This is a safe, non-breaking addition to the existing replacement loop.

---

## Test Gaps

### Existing tests that cover Phase 4 prerequisites (passing today)

| Test file | Test | What it covers |
|-----------|------|----------------|
| `test_models.py` | `test_entity_type_values` | Asserts exact set of EntityType values — will break if GENERIC is added |
| `test_token_engine.py` | SSN_SE and ORGNUM_SE tests | Token format for existing enum values — passes, no gap |
| `test_fixtures.py` | `test_medium_has_swedish_pii` | Asserts fixture contains personnummer and org-nummer strings — passes |
| `test_detector.py` | All tests | No Swedish PII tests — gap |
| `test_sanitizer.py` | All tests | No `--hide-all` or header boosting tests — gap |
| `test_cli.py` | All tests | No `--hide-all` flag test — gap |

### Tests the planner must add

| Test file | New test | Covers |
|-----------|----------|--------|
| `test_detector.py` | `test_personnummer_detected` | DET-05: `SwePersonnummerRecognizer` fires on valid personnummer |
| `test_detector.py` | `test_personnummer_checksum_rejects_random` | DET-05: fake digit string not detected |
| `test_detector.py` | `test_orgnummer_detected` | DET-06: `SweOrgNummerRecognizer` fires on valid org-nummer |
| `test_detector.py` | `test_orgnummer_checksum_rejects_random` | DET-06: fake digit string not detected |
| `test_detector.py` | `test_company_suffix_detected` | DET-07: `CompanySuffixRecognizer` fires on "Volvo AB", "Acme Corporation" |
| `test_detector.py` | `test_company_suffix_no_false_positive` | DET-07: "AB" alone or "the ltd" not matched |
| `test_detector.py` | `test_header_boosting_detects_low_confidence_name` | DET-08: borderline-score name in a "Customer" column is detected |
| `test_sanitizer.py` | `test_sanitize_hide_all_replaces_all_cells` | TOK-04: hide-all mode produces patch for every text cell |
| `test_sanitizer.py` | `test_sanitize_hide_all_uses_stable_tokens` | TOK-04: same cell value gets same token across two hide-all runs |
| `test_cli.py` | `test_cli_hide_all_flag_exits_zero` | CLI: `--hide-all` flag accepted and produces output |
| `test_models.py` | Update `test_entity_type_values` | Add GENERIC to expected set (if GENERIC is added) |

### Valid test data needed

The medium fixture's personnummer (`199001151234`) and org-nummer (`556677-8901`) are synthetic and **do not pass Luhn validation**. Tests for checksum-positive cases need real valid numbers:

- **Valid personnummer (10-digit):** `8112189876` (a well-cited example from Swedish authorities)
- **Valid org-nummer:** `5560360793` (Volvo AB, widely cited, strip hyphen for computation)

The planner should add these as constants in `test_detector.py` with a comment explaining their source.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `addopts = "-x -q"` |
| Quick run command | `uv run pytest tests/test_detector.py -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-05 | Personnummer detected + checksum validated | unit | `uv run pytest tests/test_detector.py::test_personnummer_detected -x` | No — Wave 0 |
| DET-06 | Org-nummer detected + checksum validated | unit | `uv run pytest tests/test_detector.py::test_orgnummer_detected -x` | No — Wave 0 |
| DET-07 | Company suffix detected | unit | `uv run pytest tests/test_detector.py::test_company_suffix_detected -x` | No — Wave 0 |
| DET-08 | Header boosting lowers threshold | unit | `uv run pytest tests/test_detector.py::test_header_boosting_detects_low_confidence_name -x` | No — Wave 0 |
| TOK-04 | Hide-all replaces all text cells | integration | `uv run pytest tests/test_sanitizer.py::test_sanitize_hide_all_replaces_all_cells -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q -k "not spacy"` (fast; spaCy tests are slow to init)
- **Per wave merge:** `uv run pytest` (full suite including spaCy tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_detector.py` — add personnummer, org-nummer, company suffix, and header boosting tests
- [ ] `tests/test_sanitizer.py` — add hide-all mode tests
- [ ] `tests/test_cli.py` — add `--hide-all` flag acceptance test
- [ ] `tests/test_models.py` — update entity type set assertion if GENERIC is added
- [ ] Valid Luhn test constants (personnummer and org-nummer) must be sourced and committed

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 adds no new external tool dependencies. All required packages (presidio-analyzer, spaCy, click) are already in `pyproject.toml` and were verified as installed in Phase 2. No new CLI tools, databases, or services are required.

---

## Sources

### Primary (HIGH confidence)

- Direct read of `src/xlcloak/models.py` — EntityType enum values
- Direct read of `src/xlcloak/token_engine.py` — TokenFormatter match cases
- Direct read of `src/xlcloak/detector.py` — PRESIDIO_TO_ENTITY_TYPE, PiiDetector._get_analyzer()
- Direct read of `src/xlcloak/sanitizer.py` — Sanitizer.run() full loop structure
- Direct read of `src/xlcloak/cli.py` — all sanitize flags and alias wiring
- Direct read of `src/xlcloak/excel_io.py` — iter_text_cells() and CellRef field population
- Direct read of `tests/fixtures/generate_fixtures.py` — Swedish PII fixture data values
- Direct read of all test files — coverage gap identification
- Swedish personnummer Luhn algorithm — established public spec from Skatteverket; verified against multiple independent secondary sources; HIGH confidence

### Secondary (MEDIUM confidence)

- Presidio PatternRecognizer `validate_result()` hook — training knowledge corroborated by Presidio docs at https://microsoft.github.io/presidio/analyzer/adding_recognizers/; MEDIUM (not fetched live)
- Org-nummer Luhn check — manual computation against fixture `556677-8901` revealed it is not Luhn-valid; MEDIUM confidence that this is a synthetic fixture and not a code bug

### Tertiary (LOW confidence)

- Valid personnummer example `8112189876` — from training knowledge, not verified against Skatteverket live database; planner should verify before using as canonical test constant

---

## Metadata

**Confidence breakdown:**
- Codebase verification: HIGH — all claims from direct file reads
- Luhn algorithm (personnummer): HIGH — well-established public algorithm
- Luhn algorithm (org-nummer): HIGH — standard Luhn-10; fixture-based verification revealed fixture is synthetic
- PatternRecognizer API patterns: MEDIUM — from training knowledge; consistent with CONTEXT.md's reference to Presidio docs
- Valid Luhn test data: LOW — training knowledge, not live-verified

**Research date:** 2026-04-04
**Valid until:** Stable — no external dependencies; only invalidated by codebase changes
