# xlcloak

## What This Is

A reversible Excel text sanitization CLI for AI workflows. `xlcloak` sanitizes `.xlsx` files before sending them to AI tools — replacing names, emails, phone numbers, Swedish PII, company names, and other sensitive text with stable tokens — then restores the originals afterward via an encrypted bundle. It's a practical exposure-reduction tool for anyone feeding spreadsheets to AI systems, published as an open-source PyPI package.

## Core Value

Sensitive text in Excel files never reaches AI tools, and the round-trip back to originals is reliable and conflict-aware.

## Requirements

### Validated

- ✓ Same source value always maps to the same token across the entire workbook — v1.0
- ✓ Tokens are human-readable and type-prefixed (PERSON_001, ORG_001, SSN_SE_001, etc.) — v1.0
- ✓ Tokens preserve the shape of the original value where possible — v1.0
- ✓ Unsupported surfaces (formulas, comments, charts, VBA) logged as warnings in manifest — v1.0
- ✓ Three example .xlsx fixtures (simple/medium/hard) serve as test and validation data — v1.0
- ✓ User can sanitize an `.xlsx` file via CLI, producing sanitized copy + encrypted bundle + manifest — v1.0
- ✓ User can inspect a file (dry-run preview) without writing any output — v1.0
- ✓ Detection via pattern recognizers (email, phone, URL) — v1.0
- ✓ Detection via NER recognizers (person names via spaCy en_core_web_lg) — v1.0
- ✓ Encrypted `.xlcloak` restore bundle (Fernet, PBKDF2HMAC-SHA256, 600k iterations) — v1.0
- ✓ Manifest file documenting coverage, transformations, and risk notes — v1.0
- ✓ User can restore a sanitized `.xlsx` from its bundle with conflict-aware reconciliation — v1.0
- ✓ User can diff a sanitized file against its bundle to see what changed — v1.0
- ✓ User can reconcile a modified sanitized file against its bundle — v1.0
- ✓ Hide-all mode: every text cell replaced with a stable CELL_NNNN token — v1.0
- ✓ Swedish personnummer detected with Luhn checksum validation — v1.0
- ✓ Swedish org-nummer detected with modulo-11 checksum validation — v1.0
- ✓ Company and legal entity names detected as first-class entities (AB, Ltd, GmbH, Inc, LLC) — v1.0
- ✓ Detection boosted by column header context (Customer, Name, Email, Phone columns) — v1.0
- ✓ CLI aliases: `deidentify` → `sanitize`, `identify` → `restore`, `reconcile` — v1.0
- ✓ PyPI-ready packaging (pyproject.toml, hatchling, classifiers, readme) — v1.0 (publish pending)
- ✓ Python 3.10+, cross-platform code (Windows/macOS/Linux) — v1.0

### Active

- [ ] Publish to PyPI (`pip install xlcloak`) — packaging complete, manual publish step remaining
- [ ] CI pipeline (GitHub Actions: lint, test, build) — not yet set up
- [ ] NER for organization and location names (spaCy catches some, but no dedicated org/location recognizer) — partial

### Out of Scope

- Numeric obfuscation / date shifting — deferred to v2 (NUM-01, NUM-02)
- Formula sanitization — v1 detects but does not modify formula strings
- Comments, notes, sheet names, named ranges, chart labels, VBA, external links — v1 logs as warnings
- `.xlsm` / `.xlsb` support — v1 is `.xlsx` only
- Batch mode — future consideration
- Enterprise key management (HSM, KMS) — password-derived keys cover individual/team use
- Mobile or web interface — CLI only
- User-supplied domain configuration (dictionaries, per-column overrides) — deferred to v2 (ADV-01, ADV-02)
- Adversarial anonymization (k-anonymity, differential privacy) — different threat model

## Context

**Current state:** v1.0 shipped. Full inspect → sanitize → AI → restore workflow is functional. ~4,800 LOC Python. 90 commits over 2 days (2026-04-02 → 2026-04-04).

**Tech stack:** Python 3.10+, openpyxl, Microsoft Presidio + spaCy en_core_web_lg, Fernet/PBKDF2HMAC, Click, Rich, hatchling/uv.

**Known issues:**
- NER for organization names relies solely on spaCy — no dedicated ORG recognizer beyond CompanySuffixRecognizer suffix matching
- PyPI not yet published (packaging metadata is complete)
- No CI pipeline yet
- Swedish Luhn/checksum implementations should be verified against Skatteverket spec

**Threat model:** Accidental exposure reduction, not adversarial anonymization. The tool is designed for users who trust their AI tool but don't want sensitive data unnecessarily transmitted.

## Constraints

- **Language**: Python 3.10+
- **Excel I/O**: openpyxl
- **PII detection**: Microsoft Presidio + custom recognizers
- **Bundle encryption**: Fernet (cryptography library, password-derived key)
- **Packaging**: PyPI distribution
- **Quality bar**: Public open-source — needs tests, docs, CI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fernet for bundle encryption | Simple symmetric encryption, authenticated (AES-128-CBC + HMAC-SHA256), password-derived key fits CLI workflow | ✓ Good — clean implementation, PBKDF2HMAC at 600k iterations (OWASP 2023) |
| Microsoft Presidio for NER/PII | Industry-standard PII detection, extensible with custom recognizers, good Python support | ✓ Good — pluggable architecture proved essential for Swedish recognizers; note: `registry.add_recognizer()` not `engine.add_recognizer()` in installed version |
| openpyxl for Excel I/O | De facto Python library for `.xlsx` read/write, well-maintained | ✓ Good — copy-then-patch strategy (shutil.copy2 + openpyxl patch) preserved non-text content |
| V1 text-only, V2 numeric | Ship reliable text sanitization first; numeric transforms add complexity | ✓ Good — correct call, numeric deferred cleanly |
| Global counter across all entity types | Per D-02: PERSON_001, ORG_002, EMAIL_003 (not per-type counters) | ✓ Good — simpler, prevents cross-type token collisions |
| Lazy spaCy import inside CLI command | Avoid loading 500MB model on `xlcloak --help` | ✓ Good — `inspect` and `sanitize` init spaCy only when needed |
| data_only=False on load_workbook | Preserves formula strings for detection rather than evaluating to cached values | ✓ Good — formulas visible as strings in scan_surfaces |
| PBKDF2_ITERATIONS = 600,000 | OWASP 2023 recommendation for PBKDF2-SHA256 (NIST says 480k) | ✓ Good — conservative choice, acceptable perf |
| Password mode flag in bundle | Store 'default'/'custom' in payload for restore UX (prompt only when custom) | ✓ Good — clean UX without requiring user to remember which mode |
| Span deduplication in detect_cell | Keep highest-score result per (start,end) span — prevents double-replacement when CompanySuffixRecognizer and NER ORGANIZATION fire on same text | ✓ Good — necessary correctness fix |
| Column header boosting threshold 0.3 | Lowered from default 0.4 when column header matches PII keywords | ✓ Good — measurably improves recall for name/email columns |
| Committed .xlsx binaries to repo | CI needs fixtures without running generator; binary diffs are small | ✓ Good — no issues in practice |
| Sheet-level warnings use row=0/col=0 sentinel | Distinguishes sheet-level from cell-level warnings in Manifest | ✓ Good — clean API |

## Evolution

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-04 after v1.0 milestone completion — all 4 phases shipped*
