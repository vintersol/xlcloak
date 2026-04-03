# xlcloak

## What This Is

A reversible Excel text sanitization CLI for AI workflows. `xlcloak` sanitizes `.xlsx` files before sending them to AI tools — replacing names, emails, phone numbers, and other sensitive text with stable tokens — then restores the originals afterward via an encrypted bundle. It's a practical exposure-reduction tool for anyone feeding spreadsheets to AI systems, published as an open-source PyPI package.

## Core Value

Sensitive text in Excel files never reaches AI tools, and the round-trip back to originals is reliable and conflict-aware.

## Requirements

### Validated

- [x] Same source value always maps to the same token across the entire workbook — *Validated in Phase 1: Foundation*
- [x] Token mode: sensitive text replaced with stable, shape-preserving tokens (names, orgs, emails, phones, SSNs) — *Validated in Phase 1: Foundation (token engine + formatters)*
- [x] Unsupported surfaces (formulas, comments, charts, etc.) logged as warnings in manifest — *Validated in Phase 1: Foundation*
- [x] Three example .xlsx fixtures (simple/medium/hard) serve as test and validation data — *Validated in Phase 1: Foundation*

### Active

- [ ] User can sanitize an `.xlsx` file via CLI, producing a sanitized copy, encrypted restore bundle, and manifest
- [ ] User can restore a sanitized `.xlsx` from its bundle, with conflict-aware reconciliation
- [ ] User can inspect a file (dry-run preview) without writing any output
- [ ] User can diff a sanitized file against its bundle to see what changed
- [ ] User can reconcile a modified sanitized file against its bundle
- [ ] Token mode: sensitive text replaced with stable, shape-preserving tokens (names, orgs, emails, phones, SSNs)
- [ ] Hide-all mode: every text cell replaced with a stable token
- [ ] Same source value always maps to the same token across the entire workbook
- [ ] Detection via pattern recognizers (email, phone, Swedish personnummer, org-nummer, URLs)
- [ ] Detection via NER recognizers (person, organization, location)
- [ ] Detection boosted by workbook context (column headers, sheet structure)
- [ ] User-supplied domain configuration (dictionaries, per-column overrides, deny/allow lists)
- [ ] Company and legal entity names detected as first-class entities
- [ ] Encrypted `.xlcloak` restore bundle (Fernet, password-derived key)
- [ ] Manifest file documenting coverage, transformations, and risk notes
- [ ] Restore performs conflict-aware reconciliation (unchanged cells restored, changed cells skipped, new cells untouched)
- [ ] Unsupported surfaces (formulas, comments, charts, etc.) logged as warnings in manifest
- [ ] Published to PyPI, installable via `pip install xlcloak`
- [ ] Python 3.10+, cross-platform (Windows, macOS, Linux)

### Out of Scope

- Numeric obfuscation / date shifting — deferred to V2
- Formula sanitization — V1 detects but does not modify
- Comments, notes, sheet names, named ranges, data validation, chart labels, pivot caches, VBA, external links — V1 logs these as warnings
- `.xlsm` / `.xlsb` support — V1 is `.xlsx` only
- Batch mode / TUI — future consideration
- Enterprise key management — future consideration
- Mobile or web interface — CLI only

## Context

- The tool sits in a workflow: inspect → sanitize → send to AI → restore. The AI agent edits the sanitized workbook; restore brings back originals for unmodified cells.
- Swedish PII patterns (personnummer, org-nummer) are a first-class requirement alongside international patterns.
- Company/legal entity detection is explicitly called out as harder than person names — context signals from column headers are critical.
- Domain-specific proper nouns (project names, ERP labels) are acknowledged as hard; custom dictionaries are the escape hatch.
- The threat model is "accidental exposure reduction," not adversarial anonymization.

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
| Fernet for bundle encryption | Simple symmetric encryption, well-supported via `cryptography` lib, password-derived key fits CLI workflow | -- Pending |
| Microsoft Presidio for NER/PII | Industry-standard PII detection, extensible with custom recognizers, good Python support | -- Pending |
| openpyxl for Excel I/O | De facto Python library for `.xlsx` read/write, well-maintained | -- Pending |
| V1 text-only, V2 numeric | Ship reliable text sanitization first; numeric transforms add complexity | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-03 after Phase 1 completion*
