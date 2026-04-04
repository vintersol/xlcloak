# xlcloak

Reversible Excel text sanitization CLI for AI workflows.

`xlcloak` sanitizes `.xlsx` files before sending them to AI tools — replacing names, emails, phone numbers, and other sensitive text with stable tokens — then restores the originals afterward via an encrypted bundle.

## Installation

```bash
pip install xlcloak
python -m spacy download en_core_web_lg
```

## Usage

```bash
xlcloak inspect file.xlsx          # Preview detection results (dry-run)
xlcloak sanitize file.xlsx         # Sanitize file, produce bundle and manifest
```

## License

MIT
