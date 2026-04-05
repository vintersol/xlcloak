# Phase 4: Power Features - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Add differentiating detection capabilities: Swedish PII patterns (personnummer, org-nummer), column-header context boosting, company/legal entity suffix detection, and hide-all mode. All features plug into the existing Presidio-based detection pipeline and CLI.

</domain>

<decisions>
## Implementation Decisions

### Hide-all Mode

- **D-01:** Add a new `--hide-all` flag to the `sanitize` command. When set, every text cell is replaced with a stable token regardless of content — no PII detection runs.
- **D-02:** The existing `--text-mode` flag (extracts text to .txt, no tokenization) is **unchanged**. `--hide-all` is a separate flag, not a refactor of `--text-mode`.
- **D-03:** `--hide-all` uses the existing `TokenRegistry.get_or_create()` pipeline with `EntityType.ORG` or a dedicated `GENERIC` type — Claude's discretion on entity type choice.

### Swedish Recognizers

- **D-04:** Implement two `PatternRecognizer` subclasses: `SwePersonnummerRecognizer` and `SweOrgNummerRecognizer`. Register both via `analyzer.add_recognizer()` inside `PiiDetector._get_analyzer()`.
- **D-05:** Personnummer validation: regex matching `YYMMDD-XXXX` or `YYYYMMDD-XXXX` (10 or 12 digits, optional hyphen) **plus** Luhn variant checksum validation. The checksum rejects false positives from random digit sequences.
- **D-06:** Org-nummer validation: regex matching `NNNNNN-NNNN` with Luhn-10 checksum. See STATE.md blocker: verify exact Swedish org-nummer checksum algorithm against Skatteverket spec before implementing.
- **D-07:** Recognized entities map to existing `EntityType.SSN_SE` (personnummer) and `EntityType.ORGNUM_SE` (org-nummer). Token shapes already defined in `TokenFormatter`.

### Company / Legal Entity Detection

- **D-08:** Add a `CompanySuffixRecognizer` as a `PatternRecognizer` subclass. Pattern: one or more capitalized words followed by a recognized legal suffix at word boundary. Maps to `EntityType.ORG`.
- **D-09:** V1 suffix list (core international + Swedish): `AB`, `HB`, `KB`, `Aktiebolag`, `Ltd`, `Limited`, `Inc`, `Corp`, `Corporation`, `GmbH`, `LLC`, `LLP`, `SA`, `NV`, `BV` (~15 suffixes). Case-insensitive match for suffixes.
- **D-10:** `CompanySuffixRecognizer` coexists with Presidio's NER-based ORGANIZATION detection. Both contribute to `EntityType.ORG` tokens — no deduplication needed since `TokenRegistry.get_or_create()` is deterministic on the original string.

### Column-header Context Boosting

- **D-11 (Claude's discretion):** Architecture for passing column header context to `PiiDetector.detect_cell()` is left to Claude during planning. Options include: adding `column_header: str | None` param to `detect_cell()`, a pre-pass in `Sanitizer` that extracts row-1 headers, or a context-aware wrapper. The requirement (DET-08) says detection confidence is "visibly higher" for cells in PII-labeled columns.
- **D-12:** Header matching is simple string matching: column headers containing keywords like `Name`, `Customer`, `Contact`, `Email`, `Phone`, `Company`, `SSN`, `PersonID`, `Personnummer` boost the Presidio score threshold downward (accept lower-confidence matches). No ML or semantic matching in V1.

### Claude's Discretion
- Entity type for `--hide-all` tokens (could be `EntityType.ORG`, a new `GENERIC` type, or use the cell's position as a hint)
- Exact Luhn implementation details (borrow from existing libraries or implement inline)
- How to surface header boosting in verbose/inspect output
- Whether `CompanySuffixRecognizer` score is 0.6 or 0.7 (pick what tests pass)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DET-05, DET-06, DET-07, DET-08, TOK-04 are the four pending Phase 4 requirements
- `.planning/ROADMAP.md` — Phase 4 success criteria (4 items)

### Existing codebase — integration points
- `src/xlcloak/models.py` — EntityType enum (SSN_SE, ORGNUM_SE already exist)
- `src/xlcloak/token_engine.py` — TokenFormatter already handles SSN_SE and ORGNUM_SE
- `src/xlcloak/detector.py` — PiiDetector, PRESIDIO_TO_ENTITY_TYPE mapping, _get_analyzer() (where recognizers are registered)
- `src/xlcloak/sanitizer.py` — Sanitizer.run() pipeline (where hide-all mode branches)
- `src/xlcloak/cli.py` — sanitize command (where --hide-all flag is added)
- `tests/fixtures/generate_fixtures.py` — medium fixture already has Swedish PII cells (personnummer 199001151234, org-nummer 556677-8901)

### External specs
- Skatteverket personnummer spec — verify Luhn variant checksum before implementation (STATE.md blocker from Phase 1)
- Presidio PatternRecognizer docs — https://microsoft.github.io/presidio/analyzer/adding_recognizers/

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TokenRegistry.get_or_create(value, entity_type)` — deterministic, works for any entity type including new ones
- `TokenFormatter` — already has `SSN_SE` and `ORGNUM_SE` match cases; just needs recognizers to feed it
- `PRESIDIO_TO_ENTITY_TYPE` dict in `detector.py` — extend with new entity type mappings
- `PiiDetector._get_analyzer()` — lazy init pattern; add `add_recognizer()` calls here
- `WorkbookReader.iter_text_cells()` — yields CellRef(sheet_name, row, col, value); header boosting needs row=1 awareness

### Established Patterns
- Custom entity types go in `EntityType` enum (models.py), token shape goes in `TokenFormatter.format()` match case
- All Presidio entity names map through `PRESIDIO_TO_ENTITY_TYPE` — new recognizers follow the same pattern
- CLI lazy imports (`from xlcloak.detector import PiiDetector` inside command body) — keeps help fast
- Copy-then-patch write strategy — hide-all mode uses same `WorkbookWriter.patch_and_save(patches)` path

### Integration Points
- New recognizers: `PiiDetector._get_analyzer()` calls `self._analyzer.add_recognizer(SwePersonnummerRecognizer())`
- New entity types for SE recognizers: extend `PRESIDIO_TO_ENTITY_TYPE` with `"PERSONNUMMER_SE": EntityType.SSN_SE` etc.
- Header boosting: `Sanitizer.run()` needs a header-extraction pass before the cell-detection loop
- Hide-all: branch in `Sanitizer.run()` (or separate method) — skip detection, tokenize all text cells directly via `registry.get_or_create(cell.value, entity_type)`

</code_context>

<specifics>
## Specific Ideas

- `--hide-all` is a new flag separate from `--text-mode` — user was explicit that `--text-mode` should not change
- Luhn checksum for personnummer: full validation, not just regex — user wants false positive rejection
- Suffix list is ~15 core entries (not 50+): AB, HB, KB, Aktiebolag, Ltd, Limited, Inc, Corp, Corporation, GmbH, LLC, LLP, SA, NV, BV

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-power-features*
*Context gathered: 2026-04-04*
