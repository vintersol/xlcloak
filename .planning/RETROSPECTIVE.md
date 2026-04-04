# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-04
**Phases:** 4 | **Plans:** 12 | **Sessions:** ~4

### What Was Built

- Full inspect → sanitize → AI → restore CLI workflow in a single `xlcloak` package
- Token engine: deterministic, shape-preserving, bidirectional (PERSON_001, EMAIL_001@placeholder.com, SSN_SE_190001000002)
- PII detection: Presidio + spaCy NER + 4 custom recognizers (Swedish personnummer, org-nummer, company suffix, generic)
- Encrypted restore bundle: Fernet + PBKDF2HMAC-SHA256 at 600k iterations, msgpack-free JSON payload
- Conflict-aware restore: restore=unchanged tokens, skip=AI-modified tokens, new=untracked cells
- Column-header context boosting: lowers Presidio score threshold for PII-labeled columns
- 4,807 LOC Python, 90 commits, shipped in 2 days

### What Worked

- **Bottom-up build order:** Token engine → detection → bundle → CLI → power features. Each layer had a stable, tested base. No rework from foundation.
- **TDD pattern with RED/GREEN commits:** Catching regressions immediately kept confidence high throughout. Phase summaries consistently reported "all N tests passing."
- **Lazy spaCy import:** Keeping the 500MB model out of `--help` path was the right call early — avoids a poor first impression for new users.
- **Copy-then-patch for Excel I/O:** shutil.copy2 + targeted openpyxl writes preserved formatting, charts, and styles without any round-trip data loss.
- **Presidio's custom recognizer API:** The pluggable architecture made Swedish PII patterns a 2-hour addition, not a fork.

### What Was Inefficient

- **Presidio API surprise:** `registry.add_recognizer()` vs `engine.add_recognizer()` — small gap between docs and installed version caused a debug round. Should have probed the live API before writing tests.
- **Requirements duplication in PROJECT.md:** Active requirements contained duplicates and already-validated items mixed with pending ones. Needed a cleanup pass at milestone close.
- **No CI from the start:** Testing is all local. Setting up GitHub Actions after the fact is harder than scaffolding it in Phase 1.
- **MILESTONES.md extraction bug:** The gsd-tools accomplishment extractor picked up a debug note from a phase summary and wrote it verbatim into MILESTONES.md. Required manual fix.

### Patterns Established

- `from __future__ import annotations` in all source files for Python 3.10 forward-ref compat
- Lazy CLI imports: heavy dependencies (spaCy, Presidio) imported inside command functions, not at module top
- `dataclass` for value objects (CellRef, ScanResult, SurfaceWarning, RestoreResult) — no inheritance, no methods except `__post_init__` validators
- Row-0/col-0 sentinel in SurfaceWarning for sheet-level vs cell-level distinction
- TDD RED commit → GREEN commit separation in git history

### Key Lessons

1. **Probe live APIs before writing tests.** Library docs and installed versions diverge. 30 seconds of `dir(obj)` prevents a broken test suite.
2. **Scaffold CI in Phase 1.** Adding it retroactively when the project has 4,800 lines and platform-specific deps (spaCy model) is substantially harder.
3. **Keep SUMMARY.md one-liners clean.** The gsd-tools extractor reads them programmatically. Debug notes in phase summaries pollute MILESTONES.md.
4. **Bottom-up is the right order for CLI tools.** Don't build the CLI before the engine. Every CLI shortcut taken early becomes rework when the engine API stabilizes.

### Cost Observations

- Model mix: ~100% sonnet-4.6 (no haiku/opus delegation observed)
- Sessions: ~4 focused sessions
- Notable: 4 complete phases in 2 calendar days — bottom-up ordering and TDD kept velocity high without accumulating bugs

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~4 | 4 | Initial project — bottom-up build, TDD pattern established |

### Cumulative Quality

| Milestone | Tests | LOC | Notes |
|-----------|-------|-----|-------|
| v1.0 | 100+ | 4,807 | No CI yet; all tests local |

### Top Lessons (Verified Across Milestones)

1. Probe live library APIs before writing tests against them
2. Scaffold CI in the first phase, not the last
