# xlcloak

Reversible Excel text sanitization CLI for AI workflows.

`xlcloak` sanitizes `.xlsx` files before sending them to AI tools — replacing names, emails, phone numbers, and other sensitive text with stable tokens — then restores the originals afterward via an encrypted bundle.

## Installation

```bash
pip install xlcloak
python -m spacy download en_core_web_lg
```

## Quick start

A complete round-trip looks like this:

**1. Inspect before sanitizing**

```bash
xlcloak inspect report.xlsx
```

Shows a summary of detected PII entities per sheet. Add `--verbose` to see confidence scores and detection method per entity.

**2. Sanitize**

```bash
xlcloak sanitize report.xlsx
```

Produces three outputs:
- `report_sanitized.xlsx` — the file to send to your AI tool (PII replaced with tokens like `PERSON_001`, `EMAIL_002`)
- `report.xlcloak` — the encrypted restore bundle (contains the full token map, password-protected)
- `report_sanitized_manifest.json` — a human-readable summary of what was replaced

**3. Send the sanitized file to your AI tool**

The AI sees only tokens, never the original names or emails.

**4. Check what changed before restoring**

```bash
xlcloak diff report_sanitized.xlsx --bundle report.xlcloak
```

Shows a table of cells where the AI modified or removed a token. Tokens that were deleted cannot be restored automatically.

**5. Restore**

```bash
xlcloak restore report_sanitized.xlsx --bundle report.xlcloak
```

Writes `report_restored.xlsx` with original values put back. Cells where the AI removed a token are skipped and reported.

## Commands

### `xlcloak inspect <file>`

Scan an Excel file and report detected PII entities without modifying anything.

| Option | Description |
|--------|-------------|
| `--verbose` | Show confidence scores and detection method per entity |

### `xlcloak sanitize <file>`

Replace PII with stable tokens and produce an encrypted restore bundle.

| Option | Description |
|--------|-------------|
| `--password TEXT` | Encryption password for the bundle (required unless using insecure legacy mode). |
| `--use-default-password` | Use built-in default password (`xlcloak`) for legacy workflows (unsafe). |
| `--output PATH` | Output path for the sanitized file |
| `--bundle PATH` | Explicit output path for the `.xlcloak` bundle |
| `--allow-unsupported-surfaces` | Proceed when formulas/comments/charts are detected (unsafe). |
| `--dry-run` | Preview detection without writing any files |
| `--text-mode` | Extract all text cells to a `.txt` file instead of token replacement |
| `--force` | Overwrite existing output files |
| `--verbose` | Show entity breakdown by type after sanitizing |

### `xlcloak restore <file>`

Decrypt the restore bundle and write a file with original values put back.

| Option | Description |
|--------|-------------|
| `--bundle PATH` | Path to the `.xlcloak` restore bundle (required) |
| `--password TEXT` | Decryption password (required unless using insecure legacy mode) |
| `--use-default-password` | Use built-in default password (`xlcloak`) for legacy workflows (unsafe). |
| `--output PATH` | Output path for the restored file |
| `--force` | Overwrite existing output |
| `--verbose` | Show list of AI-modified tokens that were skipped |
| `--allow-unbound-restore` | Allow restore when bundle/workbook binding metadata is missing (unsafe). |

### `xlcloak diff <file>`

Compare a (potentially AI-modified) sanitized file against the original bundle and show what changed.

| Option | Description |
|--------|-------------|
| `--bundle PATH` | Path to the `.xlcloak` restore bundle (required) |
| `--password TEXT` | Decryption password |
| `--verbose` | Also show unchanged token cells and non-token cell count |

## Aliases

| Alias | Equivalent |
|-------|------------|
| `deidentify` | `sanitize` |
| `identify` | `restore` |
| `reconcile` | `restore` |

## How it works

When you run `sanitize`, xlcloak detects PII using Microsoft Presidio and replaces each entity with a stable token (`PERSON_001`, `ORG_002`, `EMAIL_003`, and so on). The mapping from token back to original value is serialized and encrypted with Fernet symmetric encryption, using a PBKDF2-derived key from your password. The result is the `.xlcloak` bundle. When you run `restore`, xlcloak decrypts the bundle, looks up each token in the file, and writes the original value back. If the AI deleted or modified a token, that cell is skipped and reported rather than silently corrupted.

## License

MIT
