---
phase: 04-power-features
verified: 2026-04-04T16:12:00Z
status: passed
score: 18/18 must-haves verified
re_verification: false
---

# Phase 04: Power Features Verification Report

**Phase Goal:** Swedish PII recognizers (personnummer, org-nummer), company suffix recognizer, --hide-all mode, and column-header context boosting — all features integrated and tested.
**Verified:** 2026-04-04T16:12:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Swedish personnummer in valid Luhn-variant format is detected and replaced with SSN_SE-shaped token | VERIFIED | `test_personnummer_detected` passes; SwePersonnummerRecognizer fires on "8112189876", "811218-9876", "198112189876" |
| 2 | Random 10-digit strings that fail the Luhn check are NOT detected as personnummer | VERIFIED | `test_personnummer_checksum_rejects_invalid` passes; "123456-7890" and "199001151234" return empty results |
| 3 | Swedish org-nummer in valid Luhn-10 format is detected and replaced with ORGNUM_SE-shaped token | VERIFIED | `test_orgnummer_detected` passes; SweOrgNummerRecognizer fires on "556036-0793" |
| 4 | Random NNNNNN-NNNN strings that fail Luhn-10 are NOT detected as org-nummer | VERIFIED | `test_orgnummer_checksum_rejects_invalid` passes; "556677-8901" and "123456-7890" return empty results |
| 5 | EntityType.GENERIC exists and produces CELL_NNNN-shaped tokens | VERIFIED | `EntityType.GENERIC = "GENERIC"` in models.py; `TokenFormatter.format(EntityType.GENERIC, 1)` returns "CELL_0001" |
| 6 | CompanySuffixRecognizer fires on "Volvo AB", "Acme Corporation", "Test LLC" | VERIFIED | `test_company_suffix_detected` passes; smoke check returns `[type: COMPANY_SUFFIX, start: 0, end: 8, score: 1.0]` for "Volvo AB" |
| 7 | CompanySuffixRecognizer does NOT fire on "AB" alone or "the ltd" | VERIFIED | `test_company_suffix_no_false_positive` passes; validate_result() rejects lowercase-first matches |
| 8 | xlcloak sanitize file.xlsx --hide-all replaces every text cell with a CELL_NNNN token | VERIFIED | `test_sanitize_hide_all_replaces_all_cells` passes; sanitizer.run(hide_all=True) produces patches for all text cells using EntityType.GENERIC |
| 9 | Same cell value gets the same CELL_NNNN token in two separate hide-all runs | VERIFIED | `test_sanitize_hide_all_uses_stable_tokens` passes; first cell in both output workbooks has identical token |
| 10 | xlcloak sanitize file.xlsx --hide-all --dry-run prints "Would replace N text cells" and exits 0 | VERIFIED | `test_cli_hide_all_dry_run` passes; CLI prints "Dry run (hide-all): Would replace N text cells." |
| 11 | --hide-all appears in xlcloak sanitize --help | VERIFIED | `test_cli_hide_all_flag_in_help` passes; option decorated at line 63-68 of cli.py |
| 12 | A borderline-confidence name in a "Customer" column is detected when it would not be in an unlabeled column | VERIFIED | `_header_matches_pii_keyword("Customer")` returns True; threshold lowered to 0.3 when header matches; `test_header_boosting_detect_cell` passes |
| 13 | Row-1 (header) cells are never tokenized by the main detection loop | VERIFIED | `test_sanitize_header_row_not_tokenized` passes; `continue` guard at sanitizer.py:157 skips row==1 cells |
| 14 | Header context does not affect --hide-all mode | VERIFIED | hide_all=True branch is independent of sheet_headers pre-pass; tokenizes ALL cells including row-1 |
| 15 | PiiDetector.detect_cell() accepts optional column_header parameter | VERIFIED | Signature at detector.py:98-103 includes `column_header: str | None = None` |
| 16 | Medium fixture end-to-end sanitize with --hide-all completes successfully | VERIFIED | `test_sanitize_medium_fixture_hide_all_integration` passes; output file exists, cells_sanitized > 0, token_count > 0 |
| 17 | All recognizers registered in PiiDetector and PRESIDIO_TO_ENTITY_TYPE has 8 entries | VERIFIED | detector.py lines 18-27: 8-entry dict; lines 93-95: registry.add_recognizer() for all three custom recognizers |
| 18 | Full test suite passes | VERIFIED | `uv run pytest tests/ -v` → 161 passed in 50.82s |

**Score:** 18/18 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/xlcloak/recognizers.py` | SwePersonnummerRecognizer, SweOrgNummerRecognizer, CompanySuffixRecognizer | VERIFIED | 153 lines; all three classes present with Luhn validation and validate_result() overrides |
| `src/xlcloak/models.py` | EntityType.GENERIC added | VERIFIED | Line 19: `GENERIC = "GENERIC"` |
| `src/xlcloak/token_engine.py` | CELL_NNNN match case for EntityType.GENERIC | VERIFIED | Lines 47-48: `case EntityType.GENERIC: return f"CELL_{counter:04d}"` |
| `src/xlcloak/detector.py` | PRESIDIO_TO_ENTITY_TYPE extended, recognizers registered, _header_matches_pii_keyword, column_header param | VERIFIED | 8-entry dict; 3 add_recognizer calls; _header_matches_pii_keyword() at line 42; detect_cell() signature includes column_header |
| `src/xlcloak/sanitizer.py` | Sanitizer.run(hide_all=False) parameter and branch, sheet_headers pre-pass, row-1 skip | VERIFIED | Lines 105, 140-166: hide_all branch, sheet_headers dict, continue guard |
| `src/xlcloak/cli.py` | --hide-all flag on sanitize command, dry-run guard | VERIFIED | Lines 63-68: option decorator; lines 92-103: hide-all dry-run guard; line 161: hide_all=hide_all passed to sanitizer |
| `tests/test_detector.py` | personnummer + org-nummer + company suffix + header boosting tests | VERIFIED | 18 tests total; all pass |
| `tests/test_sanitizer.py` | hide-all mode tests, header row test, medium fixture integration test | VERIFIED | test_sanitize_hide_all_replaces_all_cells, test_sanitize_hide_all_uses_stable_tokens, test_sanitize_header_row_not_tokenized, test_sanitize_medium_fixture_hide_all_integration |
| `tests/test_cli.py` | --hide-all CLI tests | VERIFIED | test_cli_hide_all_flag_in_help, test_cli_hide_all_dry_run |
| `tests/conftest.py` | simple_fixture pytest fixture | VERIFIED | Lines 10-17: `simple_fixture` fixture returning Path to tests/fixtures/simple.xlsx |
| `tests/fixtures/medium.xlsx` | Medium fixture file | VERIFIED | File exists at /home/ajans/code/xlcloak/tests/fixtures/medium.xlsx |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/xlcloak/recognizers.py` | `src/xlcloak/detector.py` | `registry.add_recognizer(SwePersonnummerRecognizer())` | WIRED | detector.py line 93 |
| `src/xlcloak/recognizers.py` | `src/xlcloak/detector.py` | `registry.add_recognizer(SweOrgNummerRecognizer())` | WIRED | detector.py line 94 |
| `src/xlcloak/recognizers.py` | `src/xlcloak/detector.py` | `registry.add_recognizer(CompanySuffixRecognizer())` | WIRED | detector.py line 95 |
| `src/xlcloak/detector.py` | `src/xlcloak/models.py` | `PRESIDIO_TO_ENTITY_TYPE["PERSONNUMMER_SE"] = EntityType.SSN_SE` | WIRED | detector.py line 24 |
| `src/xlcloak/detector.py` | `src/xlcloak/models.py` | `PRESIDIO_TO_ENTITY_TYPE["ORGNUM_SE"] = EntityType.ORGNUM_SE` | WIRED | detector.py line 25 |
| `src/xlcloak/detector.py` | `src/xlcloak/models.py` | `PRESIDIO_TO_ENTITY_TYPE["COMPANY_SUFFIX"] = EntityType.ORG` | WIRED | detector.py line 26 |
| `src/xlcloak/cli.py` | `src/xlcloak/sanitizer.py` | `sanitizer.run(file, output_path, force, bundle_path, hide_all=hide_all)` | WIRED | cli.py line 161 |
| `src/xlcloak/sanitizer.py` | `src/xlcloak/models.py` | `registry.get_or_create(cell.value, EntityType.GENERIC)` | WIRED | sanitizer.py line 142 |
| `src/xlcloak/sanitizer.py` | `src/xlcloak/detector.py` | `detect_cell(cell, registry, column_header=col_header)` | WIRED | sanitizer.py lines 160-162 |
| `src/xlcloak/sanitizer.py` | `src/xlcloak/excel_io.py` | `sheet_headers` pre-pass reading cell.row == 1 from text_cells | WIRED | sanitizer.py lines 150-153 |

Note: Plan 01 specified `add_recognizer()` on AnalyzerEngine directly; the implementation correctly uses `self._analyzer.registry.add_recognizer()` (actual Presidio API). Both key link patterns match the substantive intent.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `sanitizer.py` hide_all branch | `patches`, `token` | `registry.get_or_create(cell.value, EntityType.GENERIC)` — iterates real text_cells from WorkbookReader | Yes — real cell values from opened workbook | FLOWING |
| `sanitizer.py` detection branch | `scan_results`, `replaced_text` | `PiiDetector.detect_cell()` via Presidio AnalyzerEngine | Yes — actual NLP analysis with real thresholds | FLOWING |
| `detector.py` header boosting | `threshold` | `_header_matches_pii_keyword(column_header)` returning boolean against frozenset | Yes — real keyword matching | FLOWING |
| `cli.py` hide-all dry-run | `n` (cell count) | `WorkbookReader.iter_text_cells(wb)` iterating real workbook | Yes — actual workbook read | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command / Method | Result | Status |
|----------|-----------------|--------|--------|
| SwePersonnummerRecognizer detects "8112189876" | `test_personnummer_detected` | 8 recognizer unit tests passed in 1.49s | PASS |
| CompanySuffixRecognizer detects "Volvo AB" | Smoke check via `python -c` | `[type: COMPANY_SUFFIX, start: 0, end: 8, score: 1.0]` | PASS |
| EntityType.GENERIC in enum | `python -c "from xlcloak.models import EntityType; print([e.value for e in EntityType])"` | Includes "GENERIC" | PASS |
| --hide-all --dry-run prints correct message | `test_cli_hide_all_dry_run` | Passes with "hide-all" and "Would replace" in output | PASS |
| Full test suite | `uv run pytest tests/ -v` | 161 passed in 50.82s, 0 failures | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DET-05 | 04-01 | Swedish personnummer detection + Luhn checksum | SATISFIED | SwePersonnummerRecognizer with _luhn_personnummer(); 4 tests pass; marked [x] in REQUIREMENTS.md |
| DET-06 | 04-01 | Swedish org-nummer detection + checksum | SATISFIED | SweOrgNummerRecognizer with _luhn_orgnummer(); 4 tests pass; marked [x] in REQUIREMENTS.md |
| DET-07 | 04-02 | Company/legal entity detection (AB, Ltd, GmbH, Inc, LLC suffixes) | SATISFIED | CompanySuffixRecognizer with capitalized-word + suffix regex; test_company_suffix_detected passes; marked [x] in REQUIREMENTS.md |
| DET-08 | 04-03 | Detection confidence boosted by column header context | SATISFIED | _header_matches_pii_keyword() + _BOOSTED_THRESHOLD=0.3; sheet_headers pre-pass in Sanitizer; 4 tests pass; marked [x] in REQUIREMENTS.md |
| TOK-04 | 04-02 | Hide-all mode replaces every text cell with a stable token | SATISFIED | Sanitizer.run(hide_all=True); --hide-all CLI flag; stable token test passes; marked [x] in REQUIREMENTS.md |

All 5 phase-04 requirements (DET-05, DET-06, DET-07, DET-08, TOK-04) are satisfied. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

Zero anti-patterns detected across all modified source files. No TODOs, FIXMEs, empty returns, placeholder stubs, or hardcoded empty data that flows to rendering.

Notable implementation deviation (not a defect): Plan 01 specified `self._analyzer.add_recognizer()` but Presidio's AnalyzerEngine does not expose that method directly. The implementation correctly uses `self._analyzer.registry.add_recognizer()`. Documented in 04-01-SUMMARY.md as an auto-fixed deviation.

### Human Verification Required

None. All observable truths are verifiable programmatically through unit tests, integration tests, and the 161-test suite.

### Gaps Summary

No gaps. All 18 must-have truths are verified. All artifacts exist, are substantive (non-stub), and are wired. Data flows through real WorkbookReader, Presidio, and TokenRegistry paths. The full pytest suite is green.

---

_Verified: 2026-04-04T16:12:00Z_
_Verifier: Claude (gsd-verifier)_
