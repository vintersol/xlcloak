---
phase: 01-foundation
verified: 2026-04-03T15:01:35Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 1: Foundation Verification Report

**Phase Goal:** A correct, tested token engine and validated Excel read/write pipeline exist as the stable base for all subsequent work
**Verified:** 2026-04-03T15:01:35Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | The same input value always produces the same token across independent sanitize runs (deterministic) | VERIFIED | `test_deterministic_across_registries` passes; behavioral spot-check confirmed two fresh registries produce identical token sequences |
| 2 | Tokens are human-readable with type prefixes (e.g., PERSON_001, ORG_001, SSN_SE_001) and survive Excel round-trip without corruption | VERIFIED | 7 format tests pass; round-trip spot-check confirmed patched tokens read back unchanged |
| 3 | Tokens preserve the shape of the original (email-shaped input produces email-shaped token) | VERIFIED | 3 shape tests pass; EMAIL has `@` and `.com`, PHONE starts with `+`, URL starts with `https://` |
| 4 | A workbook with formulas, comments, charts, and merged cells can be read/written with no text cell data loss, and unsupported surfaces appear as warnings in the manifest | VERIFIED | Hard fixture scan returns 11 warnings covering formula, comment, chart, merged_cells, data_validation; WorkbookWriter copy-then-patch confirmed to preserve non-text content |
| 5 | Three example .xlsx fixtures (simple/medium/hard) exist with graduated PII complexity and are used to validate all phases | VERIFIED | simple.xlsx (5 663 bytes), medium.xlsx (9 275 bytes), hard.xlsx (11 605 bytes) all exist and are non-zero; 22 fixture validation tests pass |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Project metadata, deps, build config | VERIFIED | Contains `name = "xlcloak"`, `version = "0.1.0"`, hatchling build backend, pytest config, ruff, mypy sections |
| `src/xlcloak/__init__.py` | Package init with version and public API exports | VERIFIED | Contains `__version__ = "0.1.0"`, exports TokenRegistry, TokenFormatter, EntityType, WorkbookReader, WorkbookWriter, Manifest |
| `src/xlcloak/models.py` | EntityType enum, CellRef, ScanResult, SurfaceWarning | VERIFIED | EntityType has exactly 7 members; all 4 types defined as dataclasses |
| `src/xlcloak/token_engine.py` | TokenFormatter and TokenRegistry | VERIFIED | Both classes present; get_or_create, reverse_lookup, forward_map, reverse_map, __len__ all implemented; 102 lines, fully substantive |
| `src/xlcloak/excel_io.py` | WorkbookReader and WorkbookWriter | VERIFIED | WorkbookReader (open, iter_text_cells, scan_surfaces), WorkbookWriter (prepare, patch_cells, patch_and_save); 171 lines |
| `src/xlcloak/manifest.py` | Manifest class with render() | VERIFIED | Manifest with add_warnings, add_scan_results, render; formats cell refs and sheet-level warnings correctly; 91 lines |
| `tests/test_token_engine.py` | Token engine tests, min 80 lines | VERIFIED | 302 lines, 29 test functions (exceeds 15-test minimum) |
| `tests/test_excel_io.py` | Round-trip and surface detection tests, min 60 lines | VERIFIED | 272 lines, 11 test functions |
| `tests/test_manifest.py` | Manifest warning output tests, min 30 lines | VERIFIED | 156 lines, 8 test functions |
| `tests/fixtures/generate_fixtures.py` | Programmatic fixture generator, min 100 lines | VERIFIED | 391 lines; generate_simple, generate_medium, generate_hard, __main__ block |
| `tests/fixtures/simple.xlsx` | Single-sheet basic PII fixture | VERIFIED | 5 663 bytes; 1 sheet ("Contacts"), headers confirmed, PII data confirmed |
| `tests/fixtures/medium.xlsx` | Multi-sheet Swedish PII fixture | VERIFIED | 9 275 bytes; 3 sheets, Swedish SSN (199001151234) and org-nummer (556677-8901) confirmed |
| `tests/fixtures/hard.xlsx` | Complex fixture with unsupported surfaces | VERIFIED | 11 605 bytes; 5 sheets, surface warnings confirmed for formula, comment, chart, merged_cells |
| `tests/test_fixtures.py` | Fixture validation tests, min 60 lines | VERIFIED | 276 lines, 22 test functions (exceeds 18-test minimum) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/xlcloak/token_engine.py` | `src/xlcloak/models.py` | imports EntityType enum | WIRED | Line 5: `from xlcloak.models import EntityType` |
| `tests/test_token_engine.py` | `src/xlcloak/token_engine.py` | imports TokenRegistry, TokenFormatter | WIRED | Inline imports in each test function: `from xlcloak.token_engine import TokenRegistry` / `TokenFormatter` |
| `src/xlcloak/excel_io.py` | `src/xlcloak/models.py` | imports CellRef, SurfaceWarning | WIRED | Line 13: `from xlcloak.models import CellRef, SurfaceWarning` |
| `src/xlcloak/manifest.py` | `src/xlcloak/models.py` | imports SurfaceWarning, ScanResult | WIRED | Lines 9: `from xlcloak.models import ScanResult, SurfaceWarning` |
| `src/xlcloak/excel_io.py` | `openpyxl` | load_workbook for reading/writing | WIRED | Line 10: `from openpyxl import load_workbook`; used in open() and patch_cells() |
| `tests/fixtures/generate_fixtures.py` | `openpyxl` | creates Workbook objects | WIRED | Line 16: `from openpyxl import Workbook` |
| `tests/test_fixtures.py` | `src/xlcloak/excel_io.py` | uses WorkbookReader for round-trip and surface detection | WIRED | Line 15: `from xlcloak.excel_io import WorkbookReader, WorkbookWriter` |
| `tests/test_fixtures.py` | `tests/fixtures/` | references generated .xlsx files | WIRED | Line 17: `FIXTURES_DIR = Path(__file__).parent / "fixtures"` |

---

### Data-Flow Trace (Level 4)

Token engine and Excel I/O are library components (not dynamic data renderers). Data flows are verified by the test suite itself rather than through component-to-component render pipelines. The Manifest class accumulates data via add_warnings/add_scan_results and renders it through render() — confirmed by 8 manifest tests including entity breakdown and warning formatting tests.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `manifest.py render()` | `self.warnings` | `add_warnings(list[SurfaceWarning])` | Yes — populated from WorkbookReader.scan_surfaces() in tests | FLOWING |
| `manifest.py render()` | `self.entity_counts` | `add_scan_results(list[ScanResult])` | Yes — populated from detection results | FLOWING |
| `excel_io.py iter_text_cells()` | cell iterator | openpyxl worksheet rows | Yes — reads from actual .xlsx file bytes | FLOWING |
| `token_engine.py get_or_create()` | `_forward dict` | per-call registration | Yes — tests confirm distinct values accumulate distinctly | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Determinism: two fresh registries produce identical tokens | `python -c "r1=TokenRegistry(); r2=TokenRegistry(); ..."` | 'John Smith' -> PERSON_001, 'test@email.com' -> EMAIL_002@example.com, 'Acme Corp' -> ORG_003 — both identical | PASS |
| Shape preservation: email/phone/URL tokens are correctly shaped | `python -c "... assert '@' in email_tok ..."` | email=EMAIL_001@example.com, phone=+10-000-000-002, url=https://example.com/URL_003 | PASS |
| Hard fixture surface detection | `scan_surfaces(hard.xlsx)` | 11 warnings; types={chart, comment, data_validation, formula, merged_cells} | PASS |
| Medium fixture Swedish PII content | `iter_text_cells(medium.xlsx)` | SSN 199001151234 found, org-nummer 556677-8901 found, URL found | PASS |
| Excel round-trip patch and read-back | `patch_and_save(simple.xlsx, [('Contacts',2,1,'PERSON_001')])` | Patched cell reads back as 'PERSON_001', other cells preserved | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| TOK-01 | 01-01-PLAN.md | Same source value always maps to the same token across the entire workbook | SATISFIED | test_same_value_returns_same_token, test_deterministic_across_registries pass; behavioral spot-check confirmed |
| TOK-02 | 01-01-PLAN.md | Tokens are human-readable and type-prefixed (PERSON_001, ORG_001, SSN_SE_001) | SATISFIED | 7 format tests pass covering all EntityType members |
| TOK-03 | 01-01-PLAN.md | Tokens preserve the shape of the original value where possible | SATISFIED | test_email_token_is_email_shaped, test_phone_token_starts_with_plus, test_url_token_is_valid_url pass |
| DET-09 | 01-02-PLAN.md | Unsupported surfaces (formulas, comments, charts, VBA, etc.) are logged as warnings in the manifest | SATISFIED | WorkbookReader.scan_surfaces() detects formulas, comments, charts, merged cells, images, data validation, named ranges; Manifest.render() formats warning lines |
| TEST-01 | 01-03-PLAN.md | Three example .xlsx files (simple/medium/hard) serve as test and validation data | SATISFIED | All three files exist at tests/fixtures/{simple,medium,hard}.xlsx; test_all_fixtures_exist and test_all_fixtures_readable pass |
| TEST-02 | 01-03-PLAN.md | Simple fixture: single sheet, basic PII (names, emails, phones) | SATISFIED | simple.xlsx has 1 sheet "Contacts"; test_simple_single_sheet, test_simple_has_pii_data pass |
| TEST-03 | 01-03-PLAN.md | Medium fixture: multiple sheets, cross-sheet references, Swedish PII, company names, mixed content | SATISFIED | medium.xlsx has 3 sheets; Swedish SSN and org-nummer confirmed present; test_medium_* tests pass |
| TEST-04 | 01-03-PLAN.md | Hard fixture: formulas, comments, merged cells, charts, unsupported surfaces, multi-entity cells, edge cases | SATISFIED | hard.xlsx has 5 sheets; formula, comment, chart, merged_cells warnings confirmed; test_hard_* tests pass |

**Requirements Coverage: 8/8 — all Phase 1 requirements satisfied**

No orphaned requirements: REQUIREMENTS.md traceability table maps exactly TOK-01, TOK-02, TOK-03, DET-09, TEST-01, TEST-02, TEST-03, TEST-04 to Phase 1, matching the phase's declared requirements.

---

### Anti-Patterns Found

No anti-patterns detected in implementation files.

Scan covered: token_engine.py, excel_io.py, manifest.py, models.py, __init__.py

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found |

---

### Human Verification Required

None. All success criteria are verifiable programmatically for this phase (no UI, no visual rendering, no external service integration). The full test suite (82 tests) passes in 0.42 seconds.

---

## Summary

Phase 1 goal fully achieved. All five observable truths hold. All 14 artifacts are substantive and wired. All 8 requirements are satisfied. The token engine is deterministic, shape-preserving, and overflow-guarded. The Excel I/O pipeline reads and writes without data loss, detects all unsupported surfaces, and the Manifest renders warning output correctly. Three graduated .xlsx fixtures exist and are validated by 22 fixture tests. 82 tests pass in total across the full suite.

---

_Verified: 2026-04-03T15:01:35Z_
_Verifier: Claude (gsd-verifier)_
