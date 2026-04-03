# xlcloak — Reversible Excel Text Sanitization CLI for AI Workflows

`xlcloak` sanitizes `.xlsx` files before AI processing and restores them afterward. This is done to not let AI tools process sensitive information. It is a **reversible sanitization tool**, not a formal anonymization framework.

- Reduces accidental exposure of sensitive text to AI systems
- Preserves joins, lookups, grouping, and workbook relationships where possible
- Supports a round-trip back to the original via an encrypted restore bundle
- Provides explicit visibility into what was changed, skipped, or unsupported

---

## Installation

```bash
pip install xlcloak
```

Supports Windows, macOS, and Linux. Requires Python 3.10+.

---

## Commands

```bash
xlcloak sanitize <file.xlsx> [--output <dir>] [--text-mode <mode>] [--dry-run]
xlcloak restore  <file.xlsx> --bundle <bundle.xlcloak> [--output <dir>]
xlcloak inspect  <file.xlsx> [--text-mode <mode>]
xlcloak diff     <file.xlsx> --bundle <bundle.xlcloak>
xlcloak reconcile <file.xlsx> --bundle <bundle.xlcloak>
```

| Flag          | Description                                   |
| ------------- | --------------------------------------------- |
| `--output`    | Output directory (default: current directory) |
| `--dry-run`   | Preview mode, no files written                |
| `--bundle`    | Path to encrypted restoration bundle          |
| `--text-mode` | Text sanitization mode (`token` or `hide-all`) |
| `--verbose`   | Detailed logging                              |

- `xlcloak sanitize` writes a sanitized `.xlsx`, an encrypted `.xlcloak` bundle, and a `manifest.md`.
- `xlcloak restore` reconciles the bundle against the current workbook before restoring — it does not blindly overwrite.
- `xlcloak inspect` is a dry-run preview with no files written.

Compatibility aliases: `deidentify` → `sanitize`, `identify` → `restore`.

---

## Text Sanitization Modes

### `token` mode (default)

Detects sensitive text and replaces it with stable, workbook-wide tokens. Non-sensitive text is left untouched. Where possible, replacements preserve the shape of the original value (e.g. an email stays an email, a phone number stays a phone number).

| Input | Output |
|---|---|
| `Anna Svensson` | `PERSON_001` |
| `Volvo AB` | `ORG_001` |
| `19900101-1234` | `SSN_SE_001` |
| `anna@example.com` | `person_001@example.test` |
| `070-123 45 67` | `070-555 12 34` |

### `hide-all` mode

Replaces every text-bearing cell with a stable token regardless of content. Use when maximum suppression is needed.

| Input | Output |
|---|---|
| `Quarterly review notes` | `TEXT_001` |
| `Project Falcon` | `TEXT_002` |
| `Volvo AB` | `TEXT_003` |

The same source value always maps to the same token across the entire workbook, preserving joins, lookups, and cross-sheet references.

---

## Detection Strategy

V1 uses a layered approach:

1. **Pattern recognizers** — email, phone, Swedish personnummer, Swedish org-nummer, URLs
2. **NER recognizers** — person, organization, location
3. **Workbook context** — column headers, sheet structure, repeated values, tabular neighborhoods
4. **Domain configuration** — user-supplied dictionaries, per-column overrides, deny/allow lists

Company and legal entity names are a first-class requirement. Context signals (column headers like `Customer`, `Vendor`, `Counterparty`) boost recognition precision significantly.

| Column header   | Cell value           | Likely interpretation         |
| --------------- | -------------------- | ----------------------------- |
| `Employee Name` | `Anna Svensson`      | person                        |
| `Company`       | `Volvo AB`           | legal entity / organization   |
| `Counterparty`  | `Skanska Sverige AB` | legal entity                  |
| `Project`       | `Falcon`             | domain-specific proper noun   |

V1 handles person names, company/legal entity names, and structured identifiers well. Domain-specific proper nouns (internal project names, ERP labels, branded terms) are harder — use custom dictionaries for those.

---

## Version Scope

### V1 — Text Sanitization

**In scope:** `.xlsx` visible cell values, context-aware detection, workbook-wide tokenization, encrypted restore bundle, inspect/manifest/reconcile workflow.

**Not in scope:** numeric obfuscation, date shifting, formulas, comments/notes, sheet names, named ranges, data validation, chart labels, pivot caches, VBA, external links, `.xlsm`/`.xlsb`.

Unsupported surfaces are logged in the manifest as warnings.

### V2 — Numeric Confidentiality (planned)

Configurable numeric transforms: `scale`, `sheet-scale`, `column-scale`, `bucket`, `noise`. Postponed until V1 text handling is highly reliable.

---

## Restore Bundle (`.xlcloak`)

Output set for `xlcloak sanitize financials.xlsx`:

```
financials.sanitized.xlsx
financials.xlcloak
financials.manifest.md
```

The encrypted `.xlcloak` bundle contains token mappings, integrity metadata, and cell restoration references. It is encrypted by default because a plaintext remap file would expose the original sensitive values.

### Reconciliation

`xlcloak restore` performs conflict-aware reconciliation:

- Unchanged sanitized cells → restored automatically
- Changed sanitized cells → reported and skipped by default
- New cells → left untouched
- Missing or conflicting cells → included in reconciliation report

This lets an AI agent edit the workbook while still allowing safe restoration of unmodified cells.

---

## Manifest Example

```md
# xlcloak Manifest

## Run Info
- Source: financials.xlsx  →  financials.sanitized.xlsx
- Processed at: 2026-04-01T12:00:00Z  |  xlcloak 0.1.0

## Coverage
| Surface     | Status        | Count  |
|-------------|---------------|--------|
| Cell values | processed     | 12,481 |
| Formulas    | detected-only | 1,942  |
| Comments    | skipped       | 17     |
| Charts      | skipped       | 3      |

## Transformations
- Text mode: token  |  Tokens created: 43  (org: 18, person: 9, structured: 16)

## Risk Notes
- Formula string literals were not sanitized.
- Bundle must be protected — it enables full restoration.
```

---

## Threat Model

**Protects against:** accidental exposure of names, emails, phone numbers, legal entities, and structured identifiers to AI tools.

**Does not protect against:** motivated attackers with auxiliary knowledge, inference from workbook structure, leakage through unsupported surfaces, or bundle compromise.

---

## Example Workflow

```bash
xlcloak inspect financials.xlsx
xlcloak sanitize financials.xlsx --text-mode token
# ... send financials.sanitized.xlsx to AI agent ...
xlcloak restore financials.sanitized.xlsx --bundle financials.xlcloak
```

---

## Tech Stack

| Component              | Library / Tool                           |
| ---------------------- | ---------------------------------------- |
| Excel read/write       | openpyxl                                 |
| PII / entity detection | Microsoft Presidio + custom recognizers  |
| Swedish PII patterns   | custom recognizers                       |
| Context layer          | xlcloak-native workbook analysis         |
| CLI framework          | click or typer                           |
| Hashing / integrity    | hashlib (SHA-256)                        |
| Bundle encryption      | TBD                                      |
| Packaging              | PyPI via setuptools or poetry            |

---

## Future Considerations

- V2: numeric transforms, column/sheet scaling, bucketing, noise
- Later: comments/notes scanning, formula literal scanning, sheet name support, chart text, `.xlsm`/`.xlsb`, batch mode, TUI, enterprise key management
