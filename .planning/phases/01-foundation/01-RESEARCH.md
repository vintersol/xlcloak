# Phase 1: Foundation — Research

**Researched:** 2026-04-03
**Phase:** 01-foundation
**Requirements:** TOK-01, TOK-02, TOK-03, DET-09, TEST-01, TEST-02, TEST-03, TEST-04

## Executive Summary

Phase 1 builds two core modules (token engine + Excel I/O) and three test fixtures. The token engine is a pure-Python mapping system with no external dependencies beyond the standard library. The Excel I/O layer wraps openpyxl with a copy-then-patch strategy to preserve formatting and unsupported surfaces. Test fixtures are programmatically generated `.xlsx` files covering graduated PII complexity.

## Token Engine Design

### Architecture

The token engine needs three components:

1. **TokenRegistry** — Maintains the bidirectional mapping between original values and tokens. Key design:
   - `dict[str, str]` for forward map (original → token)
   - `dict[str, str]` for reverse map (token → original)
   - Global counter (`int`) starting at 1, incrementing per new unique value
   - Thread-safety not required for V1 (single-threaded CLI)

2. **TokenFormatter** — Produces the shaped token string given entity type and counter. Per CONTEXT.md decisions:
   - `PERSON_001` / `ORG_002` — plain prefix + counter
   - `EMAIL_003@example.com` — email-shaped
   - `+10-000-000-004` — phone-shaped with counter in last digits
   - `https://example.com/URL_005` — URL-shaped
   - `SSN_SE_006` / `ORGNUM_SE_007` — shape TBD (Claude's discretion)

3. **EntityType enum** — Python `enum.Enum` defining recognized types: PERSON, ORG, EMAIL, PHONE, URL, SSN_SE, ORGNUM_SE. Used as keys in formatter dispatch.

### Determinism (TOK-01)

The same input value must always produce the same token. This means:
- The registry must be **order-dependent but deterministic** — process cells in a fixed order (sheet-by-sheet, row-by-row, left-to-right)
- The counter is scoped to a single sanitize run, not persisted across runs
- Two independent runs on the same file must produce identical output if cell iteration order is identical
- openpyxl iterates cells in row-major order by default (`ws.iter_rows()`), which is deterministic

### Shape Preservation (TOK-03)

Format functions per entity type:

```python
def format_email(counter: int) -> str:
    return f"EMAIL_{counter:03d}@example.com"

def format_phone(counter: int) -> str:
    return f"+10-000-000-{counter:03d}"

def format_url(counter: int) -> str:
    return f"https://example.com/URL_{counter:03d}"

def format_plain(entity_type: str, counter: int) -> str:
    return f"{entity_type}_{counter:03d}"
```

### SSN_SE / ORGNUM_SE Shape (Claude's Discretion)

Swedish personnummer format: YYYYMMDD-XXXX (12 digits with hyphen). Token shape: `100000000{counter:03d}` formatted as `1000000-{counter:04d}` — looks numeric but clearly fake (year 1000).

Swedish org-nummer format: NNNNNN-NNNN (10 digits). Token shape: `000000-{counter:04d}` — all-zero prefix is clearly synthetic.

## Excel I/O Pipeline

### openpyxl Capabilities and Limitations

**What openpyxl preserves on read/write:**
- Cell values (text, numbers, dates, booleans)
- Cell formatting (fonts, fills, borders, number formats)
- Merged cells
- Sheet names and order
- Column widths and row heights
- Images (with `openpyxl.drawing`)

**What openpyxl loses or mishandles:**
- **Formulas**: Preserved as strings (e.g., `=SUM(A1:A10)`) but cached values may be lost. openpyxl reads formula strings, not computed results.
- **Charts**: openpyxl can read chart objects but modifying the workbook may break chart references.
- **Comments/Notes**: `openpyxl.comments.Comment` — readable and writable, but threaded comments (newer Excel) may not survive.
- **VBA macros**: Not supported (`.xlsx` doesn't have macros; `.xlsm` does).
- **Data validation**: Preserved on read/write.
- **Conditional formatting**: Preserved on read/write.
- **Pivot tables**: Read-only, easily corrupted on write.
- **External links**: Preserved but fragile.

### Copy-then-Patch Strategy

The safest approach for sanitization:
1. Copy the original file to a new path (binary copy via `shutil.copy2`)
2. Open the copy with openpyxl
3. Patch only text cell values — leave everything else untouched
4. Save the patched copy

This avoids openpyxl round-trip issues because we only modify cell values, not structure.

### Unsupported Surface Detection (DET-09)

Need to scan for and report these surfaces without modifying them:

| Surface | How to detect | Warning level |
|---------|--------------|---------------|
| Formulas | `cell.data_type == 'f'` or `str(cell.value).startswith('=')` | WARNING — formula string not sanitized |
| Comments | `cell.comment is not None` | WARNING — comment text not sanitized |
| Charts | `ws._charts` list | WARNING — chart labels not sanitized |
| Merged cells | `ws.merged_cells.ranges` | INFO — merged cell values processed normally |
| VBA | N/A for `.xlsx` | N/A |
| Sheet names | Always present | INFO — sheet names not sanitized |
| Named ranges | `wb.defined_names` | INFO — named range labels not sanitized |
| Data validation | `ws.data_validations` | INFO — validation rules not sanitized |
| Images | `ws._images` | INFO — image content not sanitized |

### Manifest Structure

The manifest should be a structured report documenting what was done:

```
xlcloak Manifest
================
File: input.xlsx
Date: 2026-04-03T12:00:00
Mode: sanitize

Sheets processed: 3
Cells scanned: 1,500
Cells sanitized: 47
Tokens generated: 23

Entity breakdown:
  PERSON: 8
  EMAIL: 6
  PHONE: 4
  ORG: 3
  URL: 2

Warnings:
  - Sheet1!B5: formula =SUM(A1:A10) — not sanitized
  - Sheet2!C3: comment "Check with John" — not sanitized
  - Sheet1: 1 chart — labels not sanitized

Risk notes:
  - 3 cells in columns without headers — detection confidence lower
```

For Phase 1, the manifest structure can be defined but only the "Warnings" section (unsupported surfaces) needs to be functional. Entity breakdown comes in Phase 2 with detection.

## Test Fixtures

### Fixture Strategy

Generate fixtures programmatically using openpyxl rather than creating them manually. This ensures:
- Reproducibility (re-generate if format changes)
- Documentation (code IS the spec)
- Version control friendly (Python source, not binary `.xlsx`)

### Fixture Definitions (TEST-01 through TEST-04)

**Simple fixture (TEST-02):**
- Single sheet, 20-30 rows
- Clear column headers: Name, Email, Phone, Company, Notes
- Mix of PII and non-PII text
- All values are plain text (no formulas, no merged cells)
- PII: 5 person names, 5 emails, 3 phone numbers, 2 company names

**Medium fixture (TEST-03):**
- 3 sheets (Contacts, Transactions, Summary)
- 50-100 rows per sheet
- Cross-sheet value references (same person name appears on multiple sheets)
- Swedish PII: 2 personnummer, 1 org-nummer
- Company names with legal suffixes (AB, Ltd)
- Some columns without headers
- Mixed content cells ("Contact John Smith at john@example.com")

**Hard fixture (TEST-04):**
- 5 sheets with varied structure
- Formulas referencing other cells
- Comments/notes on cells containing PII
- Merged cells spanning rows and columns
- A chart referencing data
- Cells with multiple entity types in one value
- Edge cases: empty cells, very long text, special characters, Unicode names
- Data validation dropdowns
- Conditional formatting

### Fixture Generation Script

Place in `tests/fixtures/generate_fixtures.py`. Each fixture function:
1. Creates a `Workbook()`
2. Populates cells with known data
3. Saves to `tests/fixtures/{name}.xlsx`
4. Returns the expected token mappings (for test assertions)

## Project Structure

### Recommended Layout

```
xlcloak/
├── pyproject.toml
├── README.md
├── LICENSE
├── CLAUDE.md
├── src/
│   └── xlcloak/
│       ├── __init__.py          # Package version, public API
│       ├── cli.py               # Click commands (Phase 2)
│       ├── token_engine.py      # TokenRegistry, TokenFormatter, EntityType
│       ├── excel_io.py          # WorkbookReader, WorkbookWriter, surface scanner
│       ├── manifest.py          # Manifest generation
│       └── models.py            # Shared data classes (CellRef, ScanResult, etc.)
├── tests/
│   ├── conftest.py              # Shared fixtures, tmp_path helpers
│   ├── test_token_engine.py     # Token generation, determinism, shape preservation
│   ├── test_excel_io.py         # Read/write round-trip, surface detection
│   ├── test_manifest.py         # Manifest generation
│   └── fixtures/
│       ├── generate_fixtures.py # Programmatic fixture generation
│       ├── simple.xlsx          # Generated, gitignored? Or committed?
│       ├── medium.xlsx
│       └── hard.xlsx
└── .planning/                   # GSD planning artifacts
```

### Key Design Decision: src Layout

Use `src/xlcloak/` layout (PEP 517 standard). This prevents accidental imports of the source package during testing — tests always import from the installed package.

### Fixture Handling

Commit the generated `.xlsx` files to the repo. Rationale:
- CI needs them without running generation
- They serve as documentation
- Binary diffs are small for these sizes
- Generation script is the source of truth for rebuilding

## Packaging Setup

### pyproject.toml Key Sections

```toml
[project]
name = "xlcloak"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "openpyxl>=3.1.2",
    "click>=8.1.7",
    "cryptography>=42.0.0",
    "presidio-analyzer>=2.2.354",
    "presidio-anonymizer>=2.2.354",
    "pyyaml>=6.0.1",
]

[project.scripts]
xlcloak = "xlcloak.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/xlcloak"]
```

For Phase 1, only `openpyxl` is needed as a runtime dependency. Other deps can be declared but aren't used until later phases.

### Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.1.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.9.0",
]
```

## Validation Architecture

### Critical Paths to Test

1. **Token determinism**: Same file → same tokens across runs
2. **Token uniqueness**: No two different values map to the same token
3. **Token bijectivity**: Forward and reverse maps are consistent
4. **Shape correctness**: Each entity type produces correctly shaped tokens
5. **Global counter**: Counter increments across types, not per-type
6. **Excel round-trip**: Read → write → read produces identical cell values
7. **Surface detection**: Formulas, comments, charts detected and reported
8. **Fixture validity**: Each fixture has the expected structure and content

### Test Categories

| Category | What it validates | Requirement |
|----------|------------------|-------------|
| Unit: TokenRegistry | Mapping correctness, determinism, counter behavior | TOK-01 |
| Unit: TokenFormatter | Shape output per entity type | TOK-02, TOK-03 |
| Unit: EntityType | Enum completeness, prefix strings | TOK-02 |
| Integration: Excel round-trip | Read/write preserves values | DET-09 |
| Integration: Surface scanner | Detects formulas, comments, charts | DET-09 |
| Integration: Manifest | Correct warning output | DET-09 |
| Fixture: Generation | Fixtures create valid xlsx with expected content | TEST-01–04 |
| Fixture: Round-trip | Each fixture survives read/write without data loss | TEST-01–04 |

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| openpyxl chart detection API changes between versions | Low | Medium | Pin openpyxl>=3.1.2, test chart detection |
| Merged cells lose values on round-trip | Medium | High | Test merged cell handling explicitly; copy-then-patch strategy helps |
| Counter overflow at 999 | Low | Low | Raise clear error; 999 entities per workbook is generous for V1 |
| Unicode in cell values causes encoding issues | Low | Medium | Test with Swedish characters (åäö), CJK, emoji |

## Dependencies for Phase 1

**Runtime:** openpyxl>=3.1.2
**Dev:** pytest>=8.1.0, pytest-cov>=5.0.0, ruff>=0.4.0, mypy>=1.9.0
**Build:** hatchling, uv

No network dependencies. No external APIs. Pure local computation.

## RESEARCH COMPLETE
