# xlcloak — Reversible Excel Text Sanitization CLI for AI Workflows

## Overview

`xlcloak` is a CLI tool that sanitizes Excel files before they are processed by AI agents, and restores them afterward.

The product is intentionally **V1 text-first**:

- **V1:** reversible **text de-identification / text sanitization**
- **V2:** reversible **numeric confidentiality transforms**

This split is deliberate. The first release should be extremely strong at protecting sensitive text, especially:

- person names
- company names
- legal entity names
- emails
- phone numbers
- addresses
- Swedish personnummer
- Swedish org-nummer

The goal is to let users leverage agentic AI on real spreadsheets without unnecessarily exposing sensitive text values, while preserving workbook utility where possible and restoring originals afterward.

---

## Product Positioning

`xlcloak` is a **reversible spreadsheet sanitization tool for AI workflows**.

It is designed to:

- reduce accidental exposure of sensitive text to AI systems
- preserve joins, lookups, grouping, and workbook relationships where possible
- support a reversible round trip back to the original workbook
- provide explicit visibility into what was changed, what was skipped, and what could not be safely processed

It is **not** a promise of irreversible anonymization.

---

## Version Scope

## V1 — Text Sanitization Only

V1 focuses entirely on **text de-identification** and restoration.

### In scope for V1

- `.xlsx` files only
- visible cell values
- workbook-wide consistent text tokenization
- context-aware detection of:
  - person names
  - company names
  - legal entity names
  - emails
  - phone numbers
  - addresses
  - Swedish personnummer
  - Swedish organization numbers
- encrypted restore bundle
- dry-run / inspect mode
- manifest with coverage and warnings
- restore + reconciliation workflow
- schema-aware text replacements
- strict `hide-all` mode for maximum text suppression

### Not in scope for V1

- numeric obfuscation
- date shifting
- modifying formulas
- comments / notes
- sheet names
- named ranges
- data validation lists
- conditional formatting text
- chart labels / titles
- pivot caches
- VBA macros
- external links
- `.xlsm` and `.xlsb`

---

## V2 — Numeric Confidentiality

V2 adds configurable numeric transformations.

Examples of future numeric modes:

- `scale`
- `sheet-scale`
- `column-scale`
- `bucket`
- `noise`

Numeric transformation is intentionally postponed so V1 can become highly reliable for text before introducing formula-behavior tradeoffs.

---

## Installation

```bash
pip install xlcloak
````

Supports Windows, macOS, and Linux. Requires Python 3.10+.

---

## Commands

## Primary Commands

### `xlcloak sanitize <file.xlsx> [options]`

Scans the workbook and sanitizes text-bearing cells according to the selected text mode.

Writes:

* a sanitized `.xlsx` file
* an encrypted `.xlcloak` bundle containing restoration data
* a manifest `.md` file documenting what was changed, what was skipped, and what requires caution

### `xlcloak restore <file.xlsx> --bundle <bundle.xlcloak> [options]`

Restores original values from the encrypted bundle.

Performs reconciliation:

* unchanged cells are restored automatically
* changed cells are reported and skipped by default
* new cells are left untouched by default

### `xlcloak inspect <file.xlsx> [options]`

Preview mode. Reports what would be sanitized, with no files written.

### `xlcloak diff <file.xlsx> --bundle <bundle.xlcloak>`

Compares the current sanitized workbook with the bundle’s recorded expectations and reports changed, missing, and new cells relevant to restoration.

### `xlcloak reconcile <file.xlsx> --bundle <bundle.xlcloak>`

Produces a conflict-aware reconciliation report for restoration decisions.

## Compatibility Aliases

For backward compatibility, these may be supported as aliases:

* `xlcloak deidentify` → `xlcloak sanitize`
* `xlcloak identify` → `xlcloak restore`

The preferred command names are:

* `sanitize`
* `restore`

---

## CLI Interface

```bash
xlcloak sanitize <file.xlsx> [--output <dir>] [--text-mode <mode>] [--dry-run]
xlcloak restore <file.xlsx> --bundle <bundle.xlcloak> [--output <dir>]
xlcloak inspect <file.xlsx> [--text-mode <mode>]
xlcloak diff <file.xlsx> --bundle <bundle.xlcloak>
xlcloak reconcile <file.xlsx> --bundle <bundle.xlcloak>
```

| Flag          | Description                                   |
| ------------- | --------------------------------------------- |
| `--output`    | Output directory (default: current directory) |
| `--dry-run`   | Preview mode, no files written                |
| `--bundle`    | Path to encrypted restoration bundle          |
| `--text-mode` | Text sanitization mode                        |
| `--verbose`   | Detailed logging                              |

---

## Text Sanitization Modes

V1 makes text handling the core feature.

### 1. `token` mode

This is the default smart mode.

`xlcloak` detects sensitive text and replaces it with stable, workbook-wide tokens.

Examples:

* `Anna Svensson` → `PERSON_001`
* `Volvo AB` → `ORG_001`
* `556000-0000` → `ORGNUM_SE_001`
* `19900101-1234` → `SSN_SE_001`
* `anna@example.com` → `EMAIL_001`

Use this when you want to preserve as much non-sensitive text as possible while masking sensitive content.

### 2. `hide-all` mode

This is the strict mode.

Every text-bearing cell is replaced with a stable, reversible token, regardless of whether the content is recognized as PII or an entity.

Examples:

* `Quarterly review notes` → `TEXT_001`
* `Project Falcon` → `TEXT_002`
* `Volvo AB` → `TEXT_003`
* `Customer escalation pending` → `TEXT_004`

Use this when the goal is maximum exposure reduction and you want **all text hidden**, not just text confidently recognized as sensitive.

### Why both modes exist

* `token` mode is precision-oriented
* `hide-all` mode is maximum-suppression-oriented

This gives users both a smart mode and a “hide everything textual” mode.

---

## Core V1 Requirement: Company and Legal Entity Recognition

Company and legal entity names are a first-class V1 requirement.

This is not treated as a secondary feature or an optional enhancement.

Examples of target values:

* `Volvo AB`
* `Acme Holding Sverige AB`
* `Nordic Industrial Partners`
* `Länsförsäkringar Bank AB`
* `Region Stockholm`
* `Skanska Sverige AB`

The same recognized company or legal entity should map to the same token throughout the entire workbook, across all sheets.

Example:

* `Volvo AB` → `ORG_001` everywhere it appears

This consistency is critical to preserve:

* VLOOKUP / XLOOKUP joins
* cross-sheet references
* grouping behavior
* pivot table categories
* repeated business entities across tabs

---

## Will V1 Handle Proper Names / Proper Nouns?

### Yes — for many of them

V1 should handle the most important proper names well:

* person names
* company names
* legal entity names
* many location-like entities where configured as sensitive

### But not all proper nouns are equally detectable

A generic NER model alone will not reliably capture every domain-specific proper noun, such as:

* internal project names
* product codenames
* customer segments
* site aliases
* internal team names
* contract nicknames
* ERP labels
* branded initiative names

Examples:

* `Project Falcon`
* `North Star`
* `Blue Ledger`
* `Kundteam Syd`
* `Göteborg HQ`
* `Red Account`

Because of this, V1 should not promise “all proper nouns are always detected.”

Instead, V1 should combine:

* pattern recognizers
* named entity recognition
* workbook context
* column semantics
* custom dictionaries

That is how company and legal-entity recognition becomes strong enough for real use.

---

## Context-Aware Detection

Recognizing company and legal entity names cannot rely only on generic NLP.

V1 should use workbook context to improve precision and recall.

### Context signals include

* column headers
* table headers
* repeated values
* neighboring cells
* sheet names as hints only
* workbook-wide frequency
* structured tabular patterns
* known suffixes for legal entities
* user-supplied dictionaries

### Examples

If a column is named:

* `Customer`
* `Employer`
* `Vendor`
* `Company`
* `Legal Entity`
* `Counterparty`
* `Supplier`
* `Client`

then values in that column should be interpreted with stronger organization / legal-entity priors.

Examples:

| Column header   | Cell value           | Likely interpretation         |
| --------------- | -------------------- | ----------------------------- |
| `Employee Name` | `Anna Svensson`      | person                        |
| `Company`       | `Volvo AB`           | legal entity / organization   |
| `Customer`      | `Nordea Bank Abp`    | organization                  |
| `Project`       | `Falcon`             | domain-specific proper noun   |
| `Counterparty`  | `Skanska Sverige AB` | legal entity                  |
| `Site`          | `Göteborg HQ`        | location / custom domain term |

### Why context matters

Without context, a recognizer may:

* miss company names
* misclassify legal entities as generic text
* fail on abbreviations
* fail on internal business names
* behave inconsistently across sheets

With context, V1 becomes materially better at recognizing the entities users care most about.

---

## Detection Strategy in V1

V1 text sanitization should use a layered approach.

### Layer 1 — Pattern recognizers

Good for high-confidence structured text:

* email
* phone
* Swedish personnummer
* Swedish organization numbers
* URLs if configured
* account-like identifiers if configured

### Layer 2 — NER recognizers

Good for name-like entities:

* person
* organization
* location

### Layer 3 — Workbook context

Improves entity interpretation using:

* headers
* sheet structure
* repeated values
* tabular neighborhoods
* value distributions

### Layer 4 — Domain configuration

Supports user-supplied knowledge such as:

* company dictionary
* customer list
* legal-entity suffix rules
* project-name dictionary
* deny/allow lists
* per-sheet or per-column overrides

---

## Schema-Aware Text Replacement

V1 should preserve usability where possible by using schema-aware replacements.

Examples:

* preserve consistent tokens workbook-wide
* optionally preserve formatting shape
* optionally preserve text length bands
* preserve exact repeated values as the same token
* preserve entity categories where detected

Examples:

* `anna@example.com` → `person_001@example.test`
* `070-123 45 67` → `070-555 12 34`
* `19900101-1234` → `SSN_SE_001`
* `Volvo AB` → `ORG_001`

This improves workbook survivability after sanitization.

---

## Consistency Rule

The same source value must always map to the same output token across the entire workbook.

Examples:

* `Anna Svensson` → `PERSON_001` everywhere
* `Volvo AB` → `ORG_001` everywhere
* `19900101-1234` → `SSN_SE_001` everywhere

This consistency preserves relationships such as:

* joins
* repeated keys
* lookup matches
* category grouping
* cross-sheet associations

---

## Supported File Formats

* `.xlsx` only in V1

---

## What V1 Processes

V1 processes:

* visible cell values containing text

V1 does not modify other workbook surfaces, but reports them where possible.

---

## Known Unsupported Surfaces in V1

The following are not scanned or modified in V1, but are logged in the manifest as warnings or coverage gaps:

* text inside formulas
* cell comments / notes
* sheet names
* named ranges
* data validation dropdown text
* conditional formatting rules
* embedded chart labels / titles
* pivot caches
* headers / footers
* hyperlinks beyond displayed cell text
* VBA macros
* external workbook connections

---

## Cross-Sheet References

Cross-sheet references are supported indirectly by consistency.

Because tokenization is workbook-wide and stable, repeated text values remain repeated after sanitization, which helps preserve:

* lookups
* repeated labels
* joins across sheets
* groupings

Formulas themselves are not modified in V1.

---

## Restore Bundle (`.xlcloak`)

V1 uses an encrypted bundle format instead of a plaintext remap JSON.

Example output set:

```text
financials.sanitized.xlsx
financials.xlcloak
financials.manifest.md
```

The encrypted `.xlcloak` bundle contains the information required for restoration, such as:

* tool version
* creation timestamp
* source file metadata
* token mappings
* integrity metadata
* restoration metadata
* cell restoration references

### Why a bundle instead of JSON

A plaintext JSON remap file would contain the original sensitive values and restoration data in cleartext.

That is too risky as a default.

The `.xlcloak` bundle should therefore be:

* encrypted by default
* integrity-protected
* versioned
* extensible
* optionally password-protected
* suitable for future enterprise storage patterns

---

## Manifest File (`manifest.md`)

Generated alongside the sanitized workbook.

Contains:

* run information
* sheets processed
* coverage by workbook surface
* summary statistics
* warnings
* restoration notes
* risk notes
* tool version
* timestamp

Example:

```md
# xlcloak Manifest

## Run Info
- Source file: financials.xlsx
- Output file: financials.sanitized.xlsx
- Bundle file: financials.xlcloak
- Processed at: 2026-04-01T12:00:00Z
- xlcloak version: 0.1.0

## Coverage
| Surface | Status | Count | Notes |
|---|---:|---:|---|
| Cell values | processed | 12,481 | text-bearing visible cells only |
| Formulas | detected-only | 1,942 | literals in formulas not modified |
| Comments | skipped | 17 | unsupported in v1 |
| Sheet names | skipped | 5 | unsupported in v1 |
| Charts | skipped | 3 | labels may contain sensitive text |

## Transformations
- Text mode: token
- Text tokens created: 43
- Company/legal-entity tokens: 18
- Person tokens: 9
- Structured identifiers masked: 16

## Risk Notes
- Some formulas contain string literals that may reveal sensitive data.
- Comments and chart labels were not sanitized.
- Bundle file can fully restore the workbook and must be protected.

## Restore Compatibility
- Safe automatic restore: yes
- Reconciliation needed if edited: yes
```

---

## Restoration and Reconciliation

When `xlcloak restore` is run, the tool does not blindly overwrite the workbook.

It performs a reconciliation step.

### Default behavior

* unchanged sanitized cells → restored automatically
* changed sanitized cells → reported and skipped by default
* new cells → left untouched
* missing cells → reported
* conflicting cells → included in reconciliation report

This allows an AI agent to modify the workbook while still letting `xlcloak` restore original content where safe.

### Why this matters

A simple reverse pass is not enough in real workflows.

Users need to know:

* what was safe to restore
* what the agent changed
* where restoration would overwrite edits
* which cells require manual review

That is why restoration is treated as a **reconciliation workflow**, not just a reversal step.

---

## Integrity Validation

The restore process checks whether expected sanitized cells still match the recorded state needed for safe restoration.

This can be implemented using per-cell integrity metadata such as:

* sheet name
* cell address
* sanitized value hash
* token reference
* restoration metadata version

If the current cell no longer matches the expected sanitized state, it is considered changed and is skipped by default.

---

## Threat Model

## Protects against

`xlcloak` is designed to reduce:

* accidental exposure of direct identifiers to AI tools
* casual inspection of sensitive text in workbooks sent to agents
* avoidable leakage of names, emails, phone numbers, legal entities, and structured identifiers

## Does not protect against

`xlcloak` does not claim to protect against:

* a motivated attacker with strong auxiliary knowledge
* inference from workbook structure or business logic
* leakage through unsupported workbook surfaces
* leakage if the encrypted bundle is compromised
* guaranteed irreversible anonymization

### Important note

V1 is a reversible sanitization system, not a formal anonymization framework.

---

## Safe Defaults

Recommended defaults for V1:

* text-first sanitization only
* `token` mode as the default
* `hide-all` mode available for stricter use cases
* encrypted bundle by default
* `inspect` before `sanitize`
* formulas in detect-only mode
* explicit manifest warnings for unsupported surfaces
* restore with conflict-aware reconciliation

---

## Example Workflow

### Smart mode

```bash
xlcloak inspect financials.xlsx
xlcloak sanitize financials.xlsx --text-mode token
xlcloak restore financials.sanitized.xlsx --bundle financials.xlcloak
```

### Hide-all mode

```bash
xlcloak sanitize financials.xlsx --text-mode hide-all
```

---

## Tech Stack

| Component              | Library / Tool                          |
| ---------------------- | --------------------------------------- |
| Excel read/write       | openpyxl                                |
| PII / entity detection | Microsoft Presidio + custom recognizers |
| Swedish PII patterns   | custom recognizers                      |
| Context layer          | xlcloak-native workbook analysis           |
| CLI framework          | click or typer                          |
| Hashing / integrity    | hashlib (SHA-256)                       |
| Bundle encryption      | TBD                                     |
| Packaging              | PyPI via setuptools or poetry           |

---

## V1 Design Principles

V1 should be:

* text-first
* explicit about limits
* highly reliable for company and legal-entity names
* context-aware
* reversible
* conflict-aware on restore
* safe by default
* honest about unsupported workbook surfaces

---

## Future Considerations

### V2

* numeric confidentiality transforms
* workbook / sheet / column scaling
* bucketing
* noise
* exclusions and rules for percentages, IDs, and dates

### Later

* comments / notes scanning
* formula string-literal scanning
* sheet name and named range support
* chart text support
* `.xlsm` and `.xlsb`
* standalone executable packaging
* batch mode
* TUI mode
* enterprise key management for bundles

---

## Recommended Headline

### `xlcloak` — Reversible Excel Text Sanitization for AI Workflows

Safely prepare `.xlsx` workbooks for LLMs and agents by pseudonymizing sensitive text, with special emphasis on company and legal-entity names, preserving workbook utility where possible, and restoring originals afterward using an encrypted bundle and reconciliation-aware restore flow.

```
