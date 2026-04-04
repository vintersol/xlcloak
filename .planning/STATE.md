---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: MVP
status: complete
stopped_at: v1.0 milestone archived
last_updated: "2026-04-04T00:00:00.000Z"
last_activity: 2026-04-04
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 12
  completed_plans: 12
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** Sensitive text in Excel files never reaches AI tools, and the round-trip back to originals is reliable and conflict-aware.
**Current focus:** v1.0 shipped — planning next milestone

## Current Position

Phase: 04
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-04-04

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-foundation P01 | 3 | 2 tasks | 7 files |
| Phase 01-foundation P02 | 3 | 2 tasks | 5 files |
| Phase 01-foundation P03 | 2 | 2 tasks | 5 files |
| Phase 02-core-sanitize P02 | 2 | 2 tasks | 3 files |
| Phase 02-core-sanitize P03 | 20 | 2 tasks | 5 files |
| Phase 02-core-sanitize P04 | 4 | 2 tasks | 6 files |
| Phase 03-restore-diff P01 | 4 | 2 tasks | 5 files |
| Phase 03-restore-diff P02 | 4 | 2 tasks | 2 files |
| Phase 04-power-features P01 | 736 | 3 tasks | 6 files |
| Phase 04-power-features P02 | 7 | 2 tasks | 8 files |
| Phase 04-power-features P03 | 6 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Fernet symmetric encryption with PBKDF2HMAC-SHA256 for bundle (password-derived key)
- Init: Microsoft Presidio + spaCy en_core_web_lg for PII/NER detection
- Init: openpyxl for Excel I/O; copy-then-patch strategy to avoid round-trip data loss
- Init: Click 8.1.x for CLI (chosen over Typer for multi-command option complexity)
- Init: Build order is bottom-up — token engine before detection before bundle before CLI
- [Phase 01-foundation]: Global counter across all entity types (D-02): PERSON_001, ORG_002, EMAIL_003 — not per-type counters
- [Phase 01-foundation]: SSN_SE token 1000000-{counter:04d}, ORGNUM_SE 000000-{counter:04d} — clearly synthetic Swedish-style numeric formats
- [Phase 01-foundation]: TokenFormatter uses Python 3.10 match statement for entity type dispatch
- [Phase 01-foundation]: data_only=False on load_workbook preserves formula strings for detection
- [Phase 01-foundation]: Sheet-level warnings use row=0/col=0 sentinel to distinguish from cell-level warnings
- [Phase 01-foundation]: Copy-then-patch strategy: shutil.copy2 then openpyxl patch preserves all non-text content
- [Phase 01-foundation]: Committed .xlsx binaries to repo — CI needs them without running generator; binary diffs are small
- [Phase 01-foundation]: Hard fixture formula detection relies on openpyxl data_type='f' — formulas written as strings preserve scan_surfaces detection
- [Phase 02-core-sanitize]: PBKDF2_ITERATIONS = 600_000 chosen (OWASP 2023 over NIST 480k) — resolves STATE.md blocker
- [Phase 02-core-sanitize]: Password mode flag ('default'/'custom') stored in bundle payload for Phase 3 CLI restore UX
- [Phase 02-core-sanitize]: Lazy import of PiiDetector inside sanitize CLI command body to avoid loading spaCy model on xlcloak --help
- [Phase 02-core-sanitize]: cells_sanitized counts distinct cells with PII (not total detections) - consistent with Manifest semantics
- [Phase 02-core-sanitize]: Option A for verbose scores: extend ScanResult with score/detection_method instead of separate display path — keeps data flow clean
- [Phase 02-core-sanitize]: inspect command filters warnings to formula/chart/comment only — merged cells and images are info-level, not actionable unsupported surfaces
- [Phase 03-restore-diff]: Skipped detection via missing tokens: tokens in reverse_map not found in sanitized file -> AI modified (no per-cell position tracking needed)
- [Phase 03-restore-diff]: render_report() is a standalone function not a method on Restorer, keeping RestoreResult a pure dataclass
- [Phase 03-restore-diff]: diff uses missing-token detection (same as restorer): tokens in reverse_map absent from file = AI-modified
- [Phase 03-restore-diff]: CLI aliases registered via main.add_command(fn, name='alias') at bottom of cli.py — no wrapper functions
- [Phase 04-power-features]: validate_result() returns True/False never mutates self.score — class-level attribute would corrupt subsequent recognitions
- [Phase 04-power-features]: Recognizers registered via self._analyzer.registry.add_recognizer() not AnalyzerEngine.add_recognizer() (API differs from plan example in installed Presidio version)
- [Phase 04-power-features]: SweOrgNummerRecognizer requires hyphen (NNNNNN-NNNN) while SwePersonnummerRecognizer accepts 10-digit with or without separator
- [Phase 04-power-features]: CompanySuffixRecognizer.validate_result() checks isupper() to enforce case-sensitive first word (Presidio IGNORECASE workaround)
- [Phase 04-power-features]: Span deduplication in detect_cell() keeps highest-score result per (start,end) span — prevents double-replacement when CompanySuffixRecognizer and NER ORGANIZATION fire on same text
- [Phase 04-power-features]: Sanitizer.run(hide_all=True) skips PII detection entirely and wraps all text cells with EntityType.GENERIC — no spaCy init in hide-all mode
- [Phase 04-power-features]: Header keyword matching uses substring check (any(kw in header.lower())) — handles compound headers like Customer Name naturally
- [Phase 04-power-features]: Boosted threshold is 0.3 vs default 0.4 — applied when column_header matches _PII_HEADER_KEYWORDS
- [Phase 04-power-features]: hide_all=True branch left unchanged — tokenizes ALL cells including row-1; header distinction only in normal detection mode

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: Verify Presidio AnalyzerEngine API (ConflictResolutionStrategy, batch analyze) against live docs before implementation
- Phase 2: Reconcile PBKDF2 iteration count — NIST 2023 cites 480k, OWASP 2023 cites 600k for SHA-256
- Phase 2: Verify spaCy 3.x pip-installable model package name (en-core-web-lg vs en_core_web_lg)
- Phase 4: Verify Swedish personnummer Luhn-variant checksum and org-nummer checksum against Skatteverket spec

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260404-ixo | Update README.md to reflect phases 1-3 complete | 2026-04-04 | 65d44b5 | [260404-ixo-update-readme-md-to-reflect-phases-1-3-c](.planning/quick/260404-ixo-update-readme-md-to-reflect-phases-1-3-c/) |
| 260404-uuo | Fix restorer substring replacement and NER false positives | 2026-04-04 | a7c6e3b | [260404-uuo-fix-restorer-substring-replacement-and-n](.planning/quick/260404-uuo-fix-restorer-substring-replacement-and-n/) |

## Session Continuity

Last session: 2026-04-04T00:00:00Z
Stopped at: Completed quick task 260404-uuo
Resume file: None
