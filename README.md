# xlcloak

`xlcloak` helps you safely use Excel files with AI tools.

It replaces sensitive text in a `.xlsx` file with stable placeholder tokens, lets AI work on that sanitized copy, and then restores the original values from an encrypted bundle.

## How It Works

| Stage 1: Before sanitize | -> | Stage 2: AI-safe copy | -> | Stage 3: After Restore |
|---|---|---|---|---|
| myemail@gmail.com |  | EMAIL_01 |  | myemail@gmail.com |
| My Company AB |  | ORG_01 |  | My Company AB |
| My Company AB |  | ORG_01 |  | My Company AB |

## Quick Start

### Commands

| Command | Purpose | Example |
|---|---|---|
| `xlcloak inspect <file.xlsx>` | Preview what sensitive data would be detected. Writes nothing. | `xlcloak inspect report.xlsx --verbose` |
| `xlcloak sanitize <file.xlsx>` | Create a sanitized workbook + encrypted restore bundle. | `xlcloak sanitize report.xlsx --password "your-password"` |
| `xlcloak diff <sanitized.xlsx>` | Check which tokens AI changed before restore. | `xlcloak diff report_sanitized.xlsx --bundle report.xlcloak` |
| `xlcloak restore <sanitized.xlsx>` | Restore original values where tokens are still intact. | `xlcloak restore report_sanitized.xlsx --bundle report.xlcloak --output report` |
| `xlcloak --help` | Show all commands and global help text. | `xlcloak --help` |

### Key Options

| Option | Used With | What It Does |
|---|---|---|
| `--password TEXT` | `sanitize`, `restore`, `diff` | Password for bundle encryption/decryption. |
| `--output PATH` | `sanitize`, `restore` | Set a base output name/path. xlcloak appends `_sanitized` or `_restored`. |
| `--bundle PATH` | `sanitize`, `restore`, `diff` | Set or point to the `.xlcloak` encrypted bundle file. |
| `-f, --force` | `sanitize`, `restore` | Overwrite existing output files. |
| `-c, --full-column Sheet.Col` | `sanitize` | Force tokenization of a whole column from row 2 onward (row 1 header is kept). |
| `--dry-run` | `sanitize` | Show what would happen without writing files. |
| `--verbose` | all commands | Show more detail in output. |
| `--columns-only` | `sanitize` | Only tokenize `--full-column` columns; skip Presidio/spaCy detection. |
| `--hide-all` | `sanitize` | Tokenize all text cells, not just detected PII. |
| `--text-mode` | `sanitize` | Export text cells to `.txt` instead of token replacement. |


## Install

```bash
pip install xlcloak
```

Confirm it works:

```bash
xlcloak --help
```

## Command Details

### `inspect`

Preview detections without writing files.

Example:

```bash
xlcloak inspect report.xlsx --verbose
```

| Option | Description |
|---|---|
| `--verbose` | Show confidence scores and detection methods. |

### `sanitize`

Create sanitized workbook + encrypted bundle (+ manifest).

Example:

```bash
xlcloak sanitize report.xlsx --password "choose-a-strong-password" -c Data.B -f
```

| Option | Description |
|---|---|
| `--password TEXT` | Encryption password for bundle output. |
| `--output PATH` | Base path/name for output. Final file becomes `<base>_sanitized.xlsx`. |
| `--bundle PATH` | Explicit output path for `.xlcloak` bundle. |
| `--dry-run` | Show what would be replaced without writing files. |
| `--text-mode` | Write all text cells to a `.txt` file. |
| `-f, --force` | Overwrite output files if they already exist. |
| `--hide-all` | Replace every text cell with tokens. |
| `-c, --full-column Sheet.Col` | Force full-cell tokenization for chosen columns from row 2 onward. |
| `--columns-only` | Only tokenize columns passed with `--full-column`. |
| `--verbose` | Show detailed summary and entity breakdown. |

### `diff`

Compare sanitized workbook tokens with what is expected from the bundle.

Example:

```bash
xlcloak diff report_sanitized.xlsx --bundle report.xlcloak --password "choose-a-strong-password" --verbose
```

| Option | Description |
|---|---|
| `--bundle PATH` | Path to `.xlcloak` bundle (required). |
| `--password TEXT` | Bundle decryption password. |
| `--verbose` | Also show unchanged tokens and non-token cell count. |

### `restore`

Restore original values where tokens are still present.

Example:

```bash
xlcloak restore report_sanitized.xlsx --bundle report.xlcloak --password "choose-a-strong-password" --output report -f
```

| Option | Description |
|---|---|
| `--bundle PATH` | Path to `.xlcloak` bundle (required). |
| `--password TEXT` | Bundle decryption password. |
| `--output PATH` | Base path/name for output. Final file becomes `<base>_restored.xlsx`. |
| `-f, --force` | Overwrite existing output files. |
| `--verbose` | Show skipped token details if AI changed them. |

## `inspect` vs `sanitize --dry-run`

| Command | Best use | Output style |
|---|---|---|
| `inspect` | Understand what was found and where (sheet/cell-level detail). | Rich table with entity rows and optional scores (`--verbose`). |
| `sanitize --dry-run` | Estimate replacement volume before writing files. | Summary counts only (entities, forced-column counts, hide-all counts). |

## Notes and Safety Tips

- If you skip `--password`, the default password is used. This is convenient for testing, but not safe for real sensitive data.
- Keep your `.xlcloak` bundle and password safe. You need both to restore originals.
- If AI deletes or edits tokens, those cells are skipped during restore and reported.
- `sanitize` also writes a text manifest (`*_manifest.txt`), and `restore` writes a restore report (`*_restore_manifest.txt`).
- `--columns-only` requires at least one `--full-column`/`-c`, and it cannot be combined with `--hide-all`.
- Formulas, charts, and comments are treated as unsupported surfaces and are reported as warnings (not sanitized).

## License

MIT
