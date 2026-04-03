# Roadmap: xlcloak

## Overview

xlcloak is built bottom-up, starting from the components where correctness is irreversible. Phase 1 establishes the token engine and Excel I/O pipeline — the foundation everything else depends on. Phase 2 builds the primary user command: sanitize with detection, encrypted bundle, and manifest. Phase 3 completes the round-trip with restore, diff, and conflict-aware reconciliation. Phase 4 adds differentiating power features: Swedish PII patterns, context-aware detection, hide-all mode, and company/entity detection. The result is a PyPI-installable CLI that delivers the full inspect → sanitize → send to AI → restore workflow.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Token engine correctness and validated Excel I/O pipeline
- [ ] **Phase 2: Core Sanitize** - Working sanitize command with detection, encrypted bundle, and manifest
- [ ] **Phase 3: Restore & Diff** - Complete round-trip with conflict-aware reconciliation and diff
- [ ] **Phase 4: Power Features** - Swedish PII, context-aware detection, hide-all mode, entity detection

## Phase Details

### Phase 1: Foundation
**Goal**: A correct, tested token engine and validated Excel read/write pipeline exist as the stable base for all subsequent work
**Depends on**: Nothing (first phase)
**Requirements**: TOK-01, TOK-02, TOK-03, DET-09, TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. The same input value always produces the same token across independent sanitize runs (deterministic, not random)
  2. Tokens are human-readable with type prefixes (e.g., PERSON_001, ORG_001, SSN_SE_001) and survive Excel round-trip without corruption
  3. Tokens preserve the shape of the original where possible (an email-shaped input produces an email-shaped token)
  4. A workbook with formulas, comments, charts, and merged cells can be read and written back with no data loss in text cells, and unsupported surfaces (formulas, comments, charts, VBA) appear as warnings in the manifest
  5. Three example .xlsx fixtures (simple/medium/hard) exist with graduated PII complexity and are used to validate all phases
**Plans**: TBD

### Phase 2: Core Sanitize
**Goal**: Users can sanitize an xlsx file and receive a sanitized copy, encrypted restore bundle, and manifest — and inspect what would be sanitized without writing files
**Depends on**: Phase 1
**Requirements**: DET-01, DET-02, DET-03, DET-04, BUN-01, BUN-02, CLI-01, CLI-03, CLI-06, CLI-08, CLI-09
**Success Criteria** (what must be TRUE):
  1. User runs `xlcloak sanitize file.xlsx` and receives a sanitized file, an encrypted `.xlcloak` bundle, and a manifest — all in a single command
  2. User runs `xlcloak inspect file.xlsx` and sees a dry-run preview of what would be replaced with no output files written
  3. Email addresses, phone numbers, person names (via NER), and URLs in cell text are detected and replaced with stable tokens
  4. The `.xlcloak` bundle is encrypted with a password-derived Fernet key; the manifest documents coverage, transformations, and risk notes
  5. The package is installable via `pip install xlcloak` and works on Python 3.10+ on Windows, macOS, and Linux
**Plans**: TBD
**UI hint**: no

### Phase 3: Restore & Diff
**Goal**: Users can complete the full round-trip — restoring originals from a bundle with conflict-aware reconciliation, and diffing a sanitized file against its bundle
**Depends on**: Phase 2
**Requirements**: BUN-03, BUN-04, BUN-05, BUN-06, CLI-02, CLI-04, CLI-05, CLI-07
**Success Criteria** (what must be TRUE):
  1. User runs `xlcloak restore file.xlsx --bundle file.xlcloak` and unchanged sanitized cells are restored to originals while AI-modified cells are left as-is
  2. Restore output includes a reconciliation report showing exactly which cells were restored, skipped (conflict), and left untouched (new)
  3. User runs `xlcloak diff file.xlsx --bundle file.xlcloak` and sees a clear summary of what changed between the sanitized file and the bundle
  4. User can run `xlcloak reconcile` for explicit reconciliation, and compatibility aliases (`deidentify`, `identify`) route correctly to their commands
**Plans**: TBD

### Phase 4: Power Features
**Goal**: Users get differentiating detection capabilities — Swedish PII patterns, column-header context boosting, hide-all mode, and company/entity detection
**Depends on**: Phase 3
**Requirements**: DET-05, DET-06, DET-07, DET-08, TOK-04
**Success Criteria** (what must be TRUE):
  1. Swedish personnummer and org-nummer are detected and replaced with tokens, with checksum validation rejecting false positives
  2. Detection confidence is visibly higher for cells in columns whose headers indicate PII (e.g., "Customer", "Name", "Contact") compared to unheaded columns
  3. Company and legal entity names (AB, Ltd, GmbH, Inc, LLC suffixes) are detected as first-class entities, not just caught incidentally by NER
  4. User can run with `--text-mode hide-all` and every text cell is replaced with a stable token regardless of content
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/? | Not started | - |
| 2. Core Sanitize | 0/? | Not started | - |
| 3. Restore & Diff | 0/? | Not started | - |
| 4. Power Features | 0/? | Not started | - |
