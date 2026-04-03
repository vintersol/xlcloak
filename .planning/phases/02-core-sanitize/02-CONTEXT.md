# Phase 2: Core Sanitize - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Working `sanitize` and `inspect` CLI commands. The sanitize command runs Presidio-based PII detection (email, phone, person names via NER, URLs, and basic ORG via NER), replaces detected entities with stable tokens using the Phase 1 token engine, writes a sanitized Excel copy via copy-then-patch, produces an encrypted `.xlcloak` restore bundle (Fernet, password-derived key), and generates a manifest file. The inspect command provides a dry-run preview of what sanitize would do, with no files written. Package is installable via `pip install xlcloak` on Python 3.10+.

</domain>

<decisions>
## Implementation Decisions

### Detection pipeline
- **D-01:** Aggressive detection — low confidence threshold (~0.4). Fits the "accidental exposure reduction" threat model: better to over-sanitize than miss real PII.
- **D-02:** Overlapping entity resolution: highest confidence wins. Use Presidio's built-in conflict resolution strategy.
- **D-03:** Multi-entity cells: replace each detected entity inline within the cell text. A cell like "Contact: John Smith, john@acme.com" becomes "Contact: PERSON_001, EMAIL_002@example.com".
- **D-04:** Phase 2 includes basic ORG detection from Presidio's spaCy NER — ORG is the most important entity type. Phase 4 adds suffix-boosted detection (AB, Ltd, GmbH, etc.) and Swedish PII on top.
- **D-05:** Phase 2 recognizers: EMAIL, PHONE, PERSON (NER), URL, ORG (NER). Swedish PII (SSN_SE, ORGNUM_SE), column-header boosting, and company suffix detection are Phase 4.

### Password & bundle
- **D-06:** Default password "xlcloak" for zero-friction use. Users who want real encryption use `--password` flag or `XLCLOAK_PASSWORD` environment variable. Bundle header marks which mode was used.
- **D-07:** Bundle internal format: JSON (human-debuggable after decryption). msgpack deferred to V2 if size becomes an issue.
- **D-08:** Bundle metadata: xlcloak version, original filename, creation timestamp, sheet names processed, token count. Enough to validate compatibility on restore.
- **D-09:** Fernet symmetric encryption with PBKDF2HMAC-SHA256 key derivation from password. Iteration count to be determined by researcher (NIST 480k vs OWASP 600k).

### CLI output naming
- **D-10:** Suffix naming convention: `data_sanitized.xlsx` + `data.xlcloak` + `data_manifest.txt`, all in the same directory as the input file.
- **D-11:** Overwrite protection: refuse to overwrite existing output files, show error with `--force` flag hint.
- **D-12:** `--output` flag sets the sanitized file path. Bundle and manifest derive from it (same directory, same stem + respective suffixes).

### Inspect command
- **D-13:** Inspect shows summary header (entity counts by type) + per-cell table (Sheet | Cell | Entity Type | Original | Would-be Token). Truncate long values.
- **D-14:** Inspect includes a separate "Warnings" section showing unsupported surfaces (formulas, charts, comments) that won't be sanitized.
- **D-15:** Default output is clean summary + table. `--verbose` adds confidence scores, detection method (NER vs pattern), and surrounding text context.

### Claude's Discretion
- Presidio AnalyzerEngine configuration details (recognizer registry setup, NLP engine init)
- spaCy model choice (en_core_web_lg vs en_core_web_sm — balance recall vs install size)
- PBKDF2 iteration count (follow researcher findings on NIST vs OWASP recommendation)
- Internal module organization (where detection, bundle, CLI code lives)
- Click command group structure and help text
- Table formatting library choice for inspect output (rich, tabulate, or plain text)
- Error handling patterns and exit codes
- Progress/status output during sanitize (spinner, progress bar, or silent)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` -- Project vision, constraints (Python 3.10+, openpyxl, Presidio, Fernet), key decisions
- `.planning/REQUIREMENTS.md` -- Full v1 requirements; Phase 2 covers DET-01, DET-02, DET-03, DET-04, BUN-01, BUN-02, CLI-01, CLI-03, CLI-06, CLI-08, CLI-09
- `.planning/ROADMAP.md` -- Phase 2 success criteria (5 criteria: sanitize command, inspect command, detection, encrypted bundle, pip installable)

### Phase 1 foundation (consumed by Phase 2)
- `src/xlcloak/token_engine.py` -- TokenRegistry (bidirectional mapping, global counter) and TokenFormatter (shape-preserving tokens)
- `src/xlcloak/models.py` -- EntityType enum, CellRef, ScanResult, SurfaceWarning dataclasses
- `src/xlcloak/excel_io.py` -- WorkbookReader (iter_text_cells, scan_surfaces) and WorkbookWriter (copy-then-patch)
- `src/xlcloak/manifest.py` -- Manifest class (render() produces human-readable report)
- `.planning/phases/01-foundation/01-CONTEXT.md` -- Phase 1 decisions: global counter, type prefixes, shape preservation rules

### Technology stack
- `CLAUDE.md` section "Technology Stack" -- Pinned versions for Presidio, spaCy, cryptography, Click, openpyxl, hatchling, uv

No external specs or ADRs -- requirements fully captured in planning docs above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TokenRegistry` (`src/xlcloak/token_engine.py`): Ready to use — call `get_or_create(value, entity_type)` for each detection. Returns stable token, handles dedup.
- `TokenFormatter` (`src/xlcloak/token_engine.py`): Produces shaped tokens per entity type. Already handles all 7 entity types.
- `WorkbookReader` (`src/xlcloak/excel_io.py`): `iter_text_cells()` yields every string cell as CellRef. `scan_surfaces()` returns SurfaceWarning list.
- `WorkbookWriter` (`src/xlcloak/excel_io.py`): `patch_and_save()` does copy-then-patch. Accepts list of (sheet, row, col, new_value) tuples.
- `Manifest` (`src/xlcloak/manifest.py`): `add_scan_results()` and `add_warnings()` accumulate data. `render()` produces the manifest text.
- `EntityType` enum (`src/xlcloak/models.py`): PERSON, ORG, EMAIL, PHONE, URL, SSN_SE, ORGNUM_SE — all types already defined.
- Test fixtures: `tests/fixtures/` contains simple/medium/hard .xlsx files with graduated PII complexity.

### Established Patterns
- copy-then-patch strategy for Excel writes (shutil.copy2 then openpyxl patch)
- data_only=False on load_workbook preserves formula strings
- Sheet-level warnings use row=0/col=0 sentinel
- Python 3.10 match statement for entity type dispatch
- dataclass-based models (CellRef, ScanResult, SurfaceWarning)

### Integration Points
- Detection pipeline needs to: iterate text cells via WorkbookReader, run Presidio on each cell value, create ScanResult objects, feed to TokenRegistry
- Sanitize command orchestrates: read -> detect -> tokenize -> write (via WorkbookWriter) + bundle + manifest
- Inspect command reuses: read -> detect -> tokenize (same pipeline) but renders to terminal instead of writing files
- Bundle needs: TokenRegistry.forward_map and .reverse_map for serialization
- Manifest.add_scan_results() already accepts list[ScanResult] — detection pipeline produces these

</code_context>

<specifics>
## Specific Ideas

- ORG detection is the most important entity type — user explicitly flagged this. Ensure ORG recall is prioritized when configuring Presidio recognizers and NER model.
- Default password "xlcloak" enables zero-friction workflow for individual use. The encryption is still real (Fernet + PBKDF2), just with a known key — it's about bundle integrity and format, not adversarial security.
- Global counter from Phase 1 ensures PERSON_001 and EMAIL_002 are clearly independent tokens (no confusion about whether _001 entities are related across types).

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02-core-sanitize*
*Context gathered: 2026-04-03*
