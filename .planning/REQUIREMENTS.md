# Requirements: xlcloak

**Defined:** 2026-04-03
**Core Value:** Sensitive text in Excel files never reaches AI tools, and the round-trip back to originals is reliable and conflict-aware.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Detection

- [x] **DET-01**: User can detect and replace email addresses with stable tokens
- [x] **DET-02**: User can detect and replace phone numbers with stable tokens
- [x] **DET-03**: User can detect and replace person names via NER with stable tokens
- [x] **DET-04**: User can detect and replace URLs with stable tokens
- [x] **DET-05**: User can detect and replace Swedish personnummer (with Luhn checksum validation)
- [x] **DET-06**: User can detect and replace Swedish org-nummer (with checksum validation)
- [ ] **DET-07**: User can detect and replace company/legal entity names (AB, Ltd, GmbH, Inc, LLC suffixes boost detection)
- [ ] **DET-08**: Detection confidence is boosted by column header context (e.g., "Customer" column boosts NER)
- [x] **DET-09**: Unsupported surfaces (formulas, comments, charts, VBA, etc.) are logged as warnings in the manifest

### Tokenization

- [x] **TOK-01**: Same source value always maps to the same token across the entire workbook
- [x] **TOK-02**: Tokens are human-readable and type-prefixed (e.g., PERSON_001, ORG_001, SSN_SE_001)
- [x] **TOK-03**: Tokens preserve the shape of the original value where possible (email stays email-shaped, phone stays phone-shaped)
- [ ] **TOK-04**: Hide-all mode replaces every text cell with a stable token regardless of content

### Bundle & Restore

- [x] **BUN-01**: Sanitize command produces an encrypted `.xlcloak` restore bundle (Fernet, password-derived key)
- [x] **BUN-02**: Sanitize command produces a manifest file documenting coverage, transformations, and risk notes
- [x] **BUN-03**: Restore command restores original values from bundle with conflict-aware reconciliation
- [x] **BUN-04**: Reconciliation: unchanged sanitized cells restored automatically, changed cells skipped, new cells untouched
- [x] **BUN-05**: Reconciliation report included in restore output showing what was restored, skipped, and conflicted
- [x] **BUN-06**: Diff command compares a sanitized file against its bundle to show what changed

### Test Fixtures

- [x] **TEST-01**: Three example `.xlsx` files (simple/medium/hard) serve as test and validation data
- [x] **TEST-02**: Simple fixture: single sheet, basic PII (names, emails, phones)
- [x] **TEST-03**: Medium fixture: multiple sheets, cross-sheet references, Swedish PII, company names, mixed content
- [x] **TEST-04**: Hard fixture: formulas, comments, merged cells, charts, unsupported surfaces, multi-entity cells, edge cases

### CLI & Distribution

- [x] **CLI-01**: User can run `xlcloak sanitize <file.xlsx>` to produce sanitized file + bundle + manifest
- [x] **CLI-02**: User can run `xlcloak restore <file.xlsx> --bundle <bundle.xlcloak>` to restore originals
- [x] **CLI-03**: User can run `xlcloak inspect <file.xlsx>` for dry-run preview with no files written
- [x] **CLI-04**: User can run `xlcloak diff <file.xlsx> --bundle <bundle.xlcloak>` to compare changes
- [x] **CLI-05**: User can run `xlcloak reconcile <file.xlsx> --bundle <bundle.xlcloak>` for explicit reconciliation
- [x] **CLI-06**: CLI supports `--output`, `--dry-run`, `--text-mode`, `--verbose`, `--bundle` flags
- [x] **CLI-07**: Compatibility aliases: `deidentify` -> `sanitize`, `identify` -> `restore`
- [x] **CLI-08**: Published to PyPI, installable via `pip install xlcloak`
- [x] **CLI-09**: Supports Python 3.10+, cross-platform (Windows, macOS, Linux)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Numeric Obfuscation

- **NUM-01**: Configurable numeric transforms (scale, sheet-scale, column-scale, bucket, noise)
- **NUM-02**: Date shifting for date-typed cells

### Extended Surfaces

- **SURF-01**: Formula string literal scanning and sanitization
- **SURF-02**: Comments and notes scanning
- **SURF-03**: Sheet name sanitization
- **SURF-04**: Chart label and text sanitization
- **SURF-05**: Named range sanitization

### Advanced Features

- **ADV-01**: Custom dictionaries (deny/allow lists) via config file
- **ADV-02**: Per-column mode overrides via config file
- **ADV-03**: Batch mode (process multiple files)
- **ADV-04**: `.xlsm` / `.xlsb` support

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Adversarial anonymization (k-anonymity, differential privacy) | Different threat model; xlcloak is accidental exposure reduction |
| Built-in AI integration | Tool sits in a workflow; should not own the AI step |
| GUI / web interface | Target user is CLI-comfortable; GUI adds packaging complexity |
| TUI / interactive mode | CLI flags are sufficient; TUI adds framework dependency |
| Enterprise key management (HSM, KMS) | Different buyer; password-derived keys cover individual/team use |
| Automatic bundle versioning / migration | V1 can be strict: bundle version must match tool version |
| Mobile app | CLI tool, not a mobile product |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DET-01 | Phase 2 | Complete |
| DET-02 | Phase 2 | Complete |
| DET-03 | Phase 2 | Complete |
| DET-04 | Phase 2 | Complete |
| DET-05 | Phase 4 | Complete |
| DET-06 | Phase 4 | Complete |
| DET-07 | Phase 4 | Pending |
| DET-08 | Phase 4 | Pending |
| DET-09 | Phase 1 | Complete |
| TOK-01 | Phase 1 | Complete |
| TOK-02 | Phase 1 | Complete |
| TOK-03 | Phase 1 | Complete |
| TOK-04 | Phase 4 | Pending |
| TEST-01 | Phase 1 | Complete |
| TEST-02 | Phase 1 | Complete |
| TEST-03 | Phase 1 | Complete |
| TEST-04 | Phase 1 | Complete |
| BUN-01 | Phase 2 | Complete |
| BUN-02 | Phase 2 | Complete |
| BUN-03 | Phase 3 | Complete |
| BUN-04 | Phase 3 | Complete |
| BUN-05 | Phase 3 | Complete |
| BUN-06 | Phase 3 | Complete |
| CLI-01 | Phase 2 | Complete |
| CLI-02 | Phase 3 | Complete |
| CLI-03 | Phase 2 | Complete |
| CLI-04 | Phase 3 | Complete |
| CLI-05 | Phase 3 | Complete |
| CLI-06 | Phase 2 | Complete |
| CLI-07 | Phase 3 | Complete |
| CLI-08 | Phase 2 | Complete |
| CLI-09 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after roadmap creation*
