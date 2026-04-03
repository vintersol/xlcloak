# Phase 2: Core Sanitize - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 02-core-sanitize
**Areas discussed:** Detection thresholds, Password & bundle, CLI output naming, Inspect command

---

## Detection thresholds

### Sensitivity

| Option | Description | Selected |
|--------|-------------|----------|
| Aggressive (Recommended) | Lower confidence threshold (~0.4). Catches more PII at the cost of some false positives. Fits the 'accidental exposure reduction' threat model. | ✓ |
| Balanced | Medium threshold (~0.6). Standard Presidio defaults. | |
| Conservative | Higher threshold (~0.8). Only high-confidence detections. | |

**User's choice:** Aggressive
**Notes:** None

### Overlap resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Highest confidence wins (Recommended) | Keep the detection with the highest score. Presidio has built-in support. | ✓ |
| Longest span wins | Keep the detection that covers the most text. | |
| Keep all, separate tokens | Tokenize each detection independently. | |

**User's choice:** Highest confidence wins
**Notes:** None

### Multi-entity cells

| Option | Description | Selected |
|--------|-------------|----------|
| Replace each entity in-place (Recommended) | Scan the full cell text, replace each detected entity with its token inline. | ✓ |
| Replace entire cell | If any PII is detected, replace the whole cell value with a single token. | |

**User's choice:** Replace each entity in-place
**Notes:** None

### ORG detection in Phase 2

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include basic ORG (Recommended) | Presidio's spaCy NER already detects organizations. Include it now. | ✓ |
| No, defer all ORG to Phase 4 | Keep Phase 2 strictly to DET-01 through DET-04. | |

**User's choice:** Yes, include basic ORG
**Notes:** "Please go with 1. and notice that org detection is the most important type of them all!"

---

## Password & bundle

### Password provision

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive prompt (Recommended) | Prompt for password with confirmation. Also support --password flag and env var. | |
| Flag only | Require --password flag. No interactive prompt. | |
| Prompt only | Always prompt interactively. No flag or env var. | |

**User's choice:** Other -- "Is it possible to keep a constant password in app? This will make user not having to bother about pwd"

**Follow-up: Password friction resolution**

| Option | Description | Selected |
|--------|-------------|----------|
| Default password with opt-in custom | Ship a well-known default password (e.g., 'xlcloak'). Users who want real encryption pass --password or set XLCLOAK_PASSWORD. | ✓ |
| Prompt but remember | Prompt on first use, save to ~/.xlcloak/config. Subsequent runs reuse it silently. | |
| Always prompt | Prompt every time. Support --password flag and env var for scripting. | |

**User's choice:** Default password with opt-in custom
**Notes:** User priority is zero-friction UX. Accepted that open-source means the default password is public.

### Bundle serialization format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON (Recommended) | Human-debuggable after decryption. Slightly larger but V1 simplicity wins. | ✓ |
| msgpack | Compact binary. Faster for large token maps. | |

**User's choice:** JSON
**Notes:** None

### Bundle metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Essential metadata (Recommended) | xlcloak version, original filename, creation timestamp, sheet names, token count. | ✓ |
| Minimal | Just the token map and xlcloak version. | |
| Rich metadata | Everything plus manifest snapshot, cell coordinates, file hash. | |

**User's choice:** Essential metadata
**Notes:** None

---

## CLI output naming

### Output file naming

| Option | Description | Selected |
|--------|-------------|----------|
| Suffix convention (Recommended) | data_sanitized.xlsx + data.xlcloak + data_manifest.txt | ✓ |
| Subdirectory | Creates data_xlcloak/ directory. | |
| Configurable via --output | No default convention, require --output flag. | |

**User's choice:** Suffix convention
**Notes:** None

### Overwrite behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail with hint (Recommended) | Refuse to overwrite, show error with --force flag hint. | ✓ |
| Overwrite silently | Just overwrite. | |
| Ask interactively | Prompt 'Overwrite? [y/N]'. | |

**User's choice:** Fail with hint
**Notes:** None

### --output flag

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, --output for sanitized file (Recommended) | --output sets the sanitized file path. Bundle and manifest derive from it. | ✓ |
| Separate flags for each | --output, --bundle-output, --manifest-output. | |

**User's choice:** Yes, --output for sanitized file
**Notes:** None

---

## Inspect command

### Inspect output

| Option | Description | Selected |
|--------|-------------|----------|
| Summary + per-cell table (Recommended) | Header with counts, then table: Sheet, Cell, Entity Type, Original, Would-be Token. | ✓ |
| Summary only | Just counts and entity breakdown. | |
| Full detail | Everything: summary, per-cell table, surface warnings, manifest preview. | |

**User's choice:** Summary + per-cell table
**Notes:** None

### Surface warnings in inspect

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, in a separate section (Recommended) | After the PII table, show a 'Warnings' section. | ✓ |
| No, PII only | Keep inspect focused on what WILL be replaced. | |

**User's choice:** Yes, in a separate section
**Notes:** None

### Verbosity

| Option | Description | Selected |
|--------|-------------|----------|
| Default: summary + table, --verbose adds context (Recommended) | --verbose shows confidence scores, detection method, surrounding text context. | ✓ |
| Always full detail | No verbosity toggle. | |

**User's choice:** Default: summary + table, --verbose adds context
**Notes:** None

---

## Claude's Discretion

- Presidio AnalyzerEngine configuration details
- spaCy model choice (en_core_web_lg vs en_core_web_sm)
- PBKDF2 iteration count
- Internal module organization
- Click command group structure
- Table formatting for inspect output
- Error handling patterns and exit codes
- Progress output during sanitize

## Deferred Ideas

None -- discussion stayed within phase scope
