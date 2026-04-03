# Architecture Patterns

**Domain:** Reversible Excel PII sanitization CLI (xlcloak)
**Researched:** 2026-04-03
**Confidence:** MEDIUM — based on training knowledge of Presidio architecture and openpyxl data model; web access unavailable for verification

---

## Recommended Architecture

xlcloak is best structured as a layered pipeline where responsibilities are cleanly separated: the workbook I/O layer knows nothing about PII, the detection layer knows nothing about Excel, and the transform layer knows nothing about either. This separation enables independent testing and makes each layer swappable.

```
┌─────────────────────────────────────────────────────────┐
│  CLI Layer                                              │
│  (Typer/Click entry points, argument parsing, exit codes│
└───────────────────────┬─────────────────────────────────┘
                        │ commands: sanitize, restore,
                        │           inspect, diff, reconcile
┌───────────────────────▼─────────────────────────────────┐
│  Orchestration Layer                                    │
│  (SanitizeEngine, RestoreEngine — coordinate all below) │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
┌──────▼──────┐     ┌─────────▼──────────┐
│  Workbook   │     │  Detection Layer   │
│  I/O Layer  │     │  (PII Recognizers) │
│  (openpyxl) │     │  (Presidio-based)  │
└──────┬──────┘     └─────────┬──────────┘
       │                      │
┌──────▼──────────────────────▼──────────┐
│  Transform Layer                       │
│  (Tokenizer, Token Registry, Mapper)   │
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│  Bundle Layer                          │
│  (Encrypted .xlcloak, Manifest writer) │
└────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Consumes | Produces |
|-----------|---------------|----------|----------|
| **CLI Layer** | Parse arguments, invoke engines, print results, handle exit codes | User input | Command invocations |
| **Orchestration Layer** | Coordinate a full sanitize or restore operation end-to-end | Commands from CLI, outputs from all other layers | Sanitized workbook, bundle, manifest |
| **Workbook I/O Layer** | Load `.xlsx` into an internal cell model; write modified workbooks back to disk | File path + openpyxl | `CellModel` list, patched workbook |
| **Detection Layer** | Accept a cell value + context (column header, entity type hints) and return detected PII spans with entity types and confidence scores | `CellModel`, column context | `DetectionResult` list (span, entity type, score) |
| **Transform Layer** | Map detected spans to stable tokens; maintain a consistent value→token registry for the entire workbook | `DetectionResult` list | Token-substituted strings, `TokenRegistry` |
| **Bundle Layer** | Serialize the token registry + original values into an encrypted `.xlcloak` file; write manifest; deserialize for restore | `TokenRegistry`, password, manifest data | `.xlcloak` bundle, `manifest.json` |

Key boundary rule: the Detection Layer accepts plain strings and returns spans. It has no knowledge of Excel structure. The Workbook I/O Layer extracts strings and reassembles them — it has no knowledge of PII. This is intentional: it makes each component independently testable and makes it straightforward to add new file formats later.

---

## Component Detail

### Workbook I/O Layer

Built on openpyxl. Responsibilities:
- Load workbook, enumerate sheets, enumerate cells
- Detect and extract column headers (row 1 heuristic, configurable)
- Produce a flat list of `CellModel` objects: `{sheet, row, col, value, header_context}`
- Accept modified values and write back to cloned workbook
- Log unsupported surfaces (formulas, charts, comments, defined names) to a warning list passed to the manifest

This layer does NOT make decisions about what is PII. It is purely structural.

### Detection Layer

Built on Microsoft Presidio `AnalyzerEngine` with custom recognizers added for:
- Swedish personnummer (10- and 12-digit patterns)
- Swedish org-nummer
- Custom pattern recognizers for any domain-supplied patterns

The detection pipeline per cell:
1. Receive cell value string + header context
2. Run `AnalyzerEngine.analyze()` with language + entity list
3. Apply context-aware boosting: if column header matches known PII signals (e.g., "name", "email", "personnr"), raise confidence threshold
4. Filter results by minimum confidence score
5. Return `DetectionResult` list

The Detection Layer is configurable: allow/deny lists, per-column entity type overrides, and custom dictionaries are all injected at initialization time via a `DetectionConfig` object. The layer does not know about sheets or workbook structure — it processes one string at a time.

### Transform Layer

Two sub-components:

**Token Registry** — A bidirectional dict: `{original_value: token, token: original_value}`. Ensures the same input value always produces the same token across the entire workbook (cross-sheet consistency). In token mode, tokens are stable and shape-preserving (same character class distribution as original, e.g., `"Anna Svensson"` → `"PERSON_7f3a"`). In hide-all mode, every text cell gets a deterministic positional token.

**Tokenizer** — Takes a string + `DetectionResult` list, replaces each detected span with its token from the registry (or mints a new one), and returns the sanitized string.

The Token Registry is the central artifact. It gets serialized into the bundle and reconstructed on restore.

### Bundle Layer

Two sub-components:

**Bundle Serializer** — Serializes `{token_registry, workbook_metadata}` to JSON, encrypts with Fernet using a password-derived key (PBKDF2-HMAC-SHA256 + random salt), writes `.xlcloak` file. The salt is stored in the bundle header (plaintext) so restore only needs the password.

**Manifest Writer** — Writes `manifest.json` alongside the sanitized file: coverage stats (cells scanned, PII detected, entities replaced), transformation log (entity types and counts, not values), unsupported surface warnings, and risk notes. The manifest is not sensitive — it contains no original values.

---

## Data Flow

### Sanitize path

```
.xlsx file + password + config
        │
        ▼
Workbook I/O: load → CellModel list + unsupported surface warnings
        │
        ▼
Detection: for each cell → DetectionResult list
        │
        ▼
Transform: DetectionResult → token substitution → sanitized strings + TokenRegistry
        │
        ├──→ Workbook I/O: patch cell values → write sanitized .xlsx
        │
        └──→ Bundle Layer: encrypt TokenRegistry → write .xlcloak
                         + Manifest Writer → write manifest.json
```

### Restore path

```
sanitized .xlsx + .xlcloak bundle + password
        │
        ▼
Bundle Layer: decrypt → TokenRegistry
        │
        ▼
Workbook I/O: load sanitized workbook → CellModel list
        │
        ▼
Reconciliation: for each cell
    - token present in registry + cell unchanged → restore original
    - token present but cell modified → skip (AI edited)
    - no token in cell → skip (new content)
        │
        ▼
Workbook I/O: patch cell values → write restored .xlsx
```

### Inspect / dry-run path

Same as sanitize path up through the Transform step — but the Workbook I/O write step and Bundle Layer write step are skipped. Only manifest preview is emitted to stdout.

### Diff path

```
sanitized .xlsx + .xlcloak bundle + password
        │
        ▼
Bundle Layer: decrypt → TokenRegistry
        │
        ▼
Workbook I/O: load → CellModel list
        │
        ▼
Compare each cell value against TokenRegistry:
    - token found, value unchanged → "unchanged"
    - token found, value modified → "modified" (show diff)
    - no token → "new"
        │
        ▼
Emit diff report to stdout
```

---

## Patterns to Follow

### Pattern 1: Pipeline with explicit intermediate types

Define dataclasses for `CellModel`, `DetectionResult`, `TokenRegistry` at the project outset. Each layer boundary is typed. This prevents the "god function" failure mode where one function loads the workbook, detects PII, substitutes tokens, and writes output all in one pass — which is untestable and unextendable.

```python
@dataclass
class CellModel:
    sheet: str
    row: int
    col: int
    value: str
    header_context: str | None

@dataclass
class DetectionResult:
    start: int
    end: int
    entity_type: str
    score: float

@dataclass
class TokenRegistry:
    value_to_token: dict[str, str]
    token_to_value: dict[str, str]
    metadata: dict  # entity type per token, mint timestamp
```

### Pattern 2: Configuration object injected at engine init

Do not read config files inside detection or transform functions. Construct a `SanitizeConfig` at CLI parse time and inject it into engines. This makes the core logic easily testable without touching the filesystem.

```python
@dataclass
class SanitizeConfig:
    mode: Literal["token", "hide_all"]
    deny_list: list[str]
    allow_list: list[str]
    per_column_overrides: dict[str, list[str]]  # header -> entity types
    custom_patterns: list[PatternConfig]
    min_score: float = 0.7
```

### Pattern 3: Reconciliation as a three-way merge

The restore reconciliation is not a simple overwrite. Model it as comparing three states:
- **original** value (from TokenRegistry)
- **sanitized** value (what was written to the sanitized file, i.e., the token)
- **current** value (what is in the file being restored, possibly edited by AI)

Only restore when `current == sanitized` (unchanged token). If `current != sanitized`, the AI modified that cell — skip restore, keep AI's content. This is the correct mental model for conflict-aware reconciliation.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mutating the openpyxl workbook in-place during detection

**What goes wrong:** Loading the workbook and writing sanitized values into it as detection proceeds, then saving at the end.
**Why bad:** Conflates read and write phases. Cannot diff or dry-run. Cannot roll back if detection fails mid-file.
**Instead:** Read all cells into `CellModel` list first (pure read), then produce sanitized values (pure transform), then apply all writes in a single pass.

### Anti-Pattern 2: Token registry stored only in memory during sanitize

**What goes wrong:** Token registry built in memory; if the process crashes after the sanitized file is written but before the bundle is written, originals are unrecoverable.
**Instead:** Write the bundle atomically. Use a temp file + rename pattern: write `.xlcloak.tmp`, rename to `.xlcloak` only after the sanitized `.xlsx` write has also succeeded.

### Anti-Pattern 3: Flat string replacement instead of span-aware substitution

**What goes wrong:** Using `str.replace(original, token)` on the full cell string. Fails when a cell contains two names, or when a value appears as a substring of another value.
**Instead:** Presidio returns spans `(start, end)`. Sort spans by position (right-to-left to avoid index shifting) and replace by index.

### Anti-Pattern 4: One Presidio `AnalyzerEngine` instance per cell

**What goes wrong:** Presidio engine initialization is expensive (loads NLP models). Creating a new instance per cell makes large workbooks extremely slow.
**Instead:** Initialize one `AnalyzerEngine` per sanitize operation and reuse it across all cells.

### Anti-Pattern 5: Storing original values in the manifest

**What goes wrong:** Manifest intended for human inspection ends up containing original PII values, defeating the purpose of sanitization.
**Instead:** Manifest contains only entity type counts, token count, coverage percentage, and warnings. Never original values or tokens-to-originals mappings. Those live only in the encrypted bundle.

---

## Suggested Build Order (Phase Dependencies)

The components have clear dependencies. Build bottom-up:

```
1. Workbook I/O Layer          — No deps. Needed by everything.
2. Detection Layer             — Needs Presidio installed. No Excel knowledge needed.
3. Transform Layer             — Needs DetectionResult types from Detection Layer.
4. Bundle Layer                — Needs TokenRegistry type from Transform Layer.
5. Orchestration Layer         — Wires 1-4 together into sanitize/restore operations.
6. CLI Layer                   — Thin wrapper on Orchestration Layer.
7. Config Layer                — Can be built alongside any of 1-6; inject into engines.
```

Building in this order means each layer has passing unit tests before the next layer builds on it. The CLI is the last thing wired up, not the first — avoids the trap of testing only through the CLI.

---

## Scalability Considerations

| Concern | At 100-row files | At 10K-row files | At 100K-row files |
|---------|-----------------|-----------------|-------------------|
| Presidio NER latency | Negligible | Noticeable (~2-10s) | Slow (30s+) with spaCy model |
| openpyxl memory | Fine | Fine | May be high for wide files |
| Token registry size | Trivial | Trivial | Trivial (most files have few unique PII values) |
| Bundle encryption | Instantaneous | Instantaneous | Instantaneous (Fernet is fast) |

For V1, single-threaded is fine. spaCy model loading (Presidio's NER backend) is the dominant latency. If this becomes a user complaint, the mitigation is to process cells in batches using Presidio's batch analyze API rather than one-at-a-time, which reduces model call overhead significantly. This is a V2 concern.

---

## Sources

- Microsoft Presidio documentation (official): https://microsoft.github.io/presidio/ — training knowledge, MEDIUM confidence
- openpyxl documentation (official): https://openpyxl.readthedocs.io/ — training knowledge, MEDIUM confidence
- Fernet encryption (cryptography library): https://cryptography.io/en/latest/fernet/ — training knowledge, HIGH confidence (stable, well-established API)
- Architecture patterns derived from standard ETL pipeline design and PII anonymization system design knowledge — training knowledge, MEDIUM confidence

**Note:** Web access was unavailable during this research session. All Presidio API details (e.g., `AnalyzerEngine.analyze()` signature, batch API availability) should be verified against current Presidio docs before implementation. Presidio is actively maintained and API surface may have changed since training cutoff.
