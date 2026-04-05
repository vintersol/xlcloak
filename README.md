# xlcloak

Reversible Excel text sanitization CLI for AI workflows.

`xlcloak` sanitizes `.xlsx` files before sending them to AI tools by replacing sensitive text with stable tokens, then restores originals afterward from an encrypted bundle.

## Install

```bash
pip install xlcloak
python -m spacy download en_core_web_lg
```

## Overview

1. Inspect an Excel file for PII.
2. Sanitize and generate an encrypted restore bundle.
3. Let AI edit the sanitized file.
4. Diff AI changes against token expectations.
5. Restore original values where tokens are intact.

## Command quick reference

| Command | What it does | Common use example |
|---|---|---|
| `xlcloak inspect <file>` | Scan for PII without writing files. | `xlcloak inspect report.xlsx --verbose` |
| `xlcloak sanitize <file>` | Replace PII with tokens and create `.xlcloak` bundle. | `xlcloak sanitize report.xlsx --password "$XLCLOAK_PASSWORD"` |
| `xlcloak diff <file>` | Show token changes between AI-edited file and bundle. | `xlcloak diff report_sanitized.xlsx --bundle report.xlcloak` |
| `xlcloak restore <file>` | Restore original values from bundle into edited file. | `xlcloak restore report_sanitized.xlsx --bundle report.xlcloak --output report_restored.xlsx` |

## Typical workflows

### Safe default flow

```bash
xlcloak inspect report.xlsx
xlcloak sanitize report.xlsx --password "$XLCLOAK_PASSWORD"
xlcloak diff report_sanitized.xlsx --bundle report.xlcloak
xlcloak restore report_sanitized.xlsx --bundle report.xlcloak --output report_restored.xlsx
```

### Dry-run detection only

```bash
xlcloak sanitize report.xlsx --dry-run --verbose
```

### Use explicit output paths

```bash
xlcloak sanitize report.xlsx \
  --output out/report_sanitized.xlsx \
  --bundle out/report.xlcloak

xlcloak restore out/report_sanitized.xlsx \
  --bundle out/report.xlcloak \
  --output out/report_restored.xlsx
```

## Options by command

### `inspect`

| Option | Description |
|---|---|
| `--verbose` | Show confidence scores and detection method per entity. |

### `sanitize`

| Option | Description |
|---|---|
| `--password TEXT` | Encryption password for the bundle. If omitted, a random key is used and a warning is printed (not suitable for sensitive data). |
| `--output PATH` | Output path for the sanitized file. |
| `--bundle PATH` | Explicit output path for the `.xlcloak` bundle. |
| `--dry-run` | Preview detection without writing files. |
| `--text-mode` | Extract all text cells to a `.txt` file instead of token replacement. |
| `--force` | Overwrite existing output files. |
| `--verbose` | Show entity breakdown by type after sanitizing. |

### `diff`

| Option | Description |
|---|---|
| `--bundle PATH` | Path to the `.xlcloak` restore bundle (required). |
| `--password TEXT` | Decryption password. |
| `--verbose` | Show unchanged token cells and non-token cell count. |

### `restore`

| Option | Description |
|---|---|
| `--bundle PATH` | Path to the `.xlcloak` restore bundle (required). |
| `--password TEXT` | Decryption password. |
| `--output PATH` | Output path for the restored file. |
| `--force` | Overwrite existing output. |
| `--verbose` | Show AI-modified tokens that were skipped. |

## Aliases

| Alias | Equivalent |
|---|---|
| `deidentify` | `sanitize` |
| `identify` | `restore` |
| `reconcile` | `restore` |

## How it works

`sanitize` detects PII with Microsoft Presidio and replaces each entity with stable tokens (`PERSON_001`, `ORG_002`, `EMAIL_003`, etc.). The token-to-original map is encrypted (Fernet + PBKDF2-derived key) in the `.xlcloak` bundle. `restore` decrypts that bundle and writes originals back where tokens are still present. If AI removed or altered a token, that cell is skipped and reported.

## License

MIT
