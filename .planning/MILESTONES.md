# Milestones

## v1.0 MVP (Shipped: 2026-04-04)

**Phases completed:** 4 phases, 12 plans, 22 tasks

**Key accomplishments:**

- Deterministic shape-preserving token engine with 41 passing tests — EntityType enum, TokenRegistry with global counter, TokenFormatter with match dispatch for 7 PII types
- openpyxl WorkbookReader/WorkbookWriter with copy-then-patch strategy and Manifest surface-warning renderer
- Three programmatically generated .xlsx fixtures (simple/medium/hard) validated by 22 pytest tests exercising WorkbookReader round-trips and surface detection
- PiiDetector wrapping Presidio AnalyzerEngine with lazy spaCy init, entity type mapping, and right-to-left multi-entity cell replacement
- Fernet-encrypted restore bundle with PBKDF2HMAC-SHA256 (600k iterations), 16-byte salt header, password mode flag, and full round-trip test coverage
- Click-based `xlcloak sanitize` command wiring PiiDetector -> TokenRegistry -> WorkbookWriter -> BundleWriter -> Manifest into a single pipeline with _sanitized.xlsx / .xlcloak / _manifest.txt output naming
- `xlcloak inspect` dry-run command with rich table output, verbose confidence scores, and complete PyPI metadata including classifiers and readme
- Restorer class with token reconciliation logic (restore/skip/new) plus restore CLI command with --bundle, --password, --force, --output, --verbose flags and wrong-password error handling
- diff command shows AI-modified tokens in a Rich table (Token|Original), and reconcile/deidentify/identify aliases registered via Click add_command
- Swedish PII recognizers (SwePersonnummerRecognizer + SweOrgNummerRecognizer with Luhn/modulo-11 checksum validation) and EntityType.GENERIC for hide-all mode
- CompanySuffixRecognizer (capitalized-word + legal-suffix regex, score 0.65) plus Sanitizer.run(hide_all=True) that replaces all text cells with stable CELL_NNNN tokens
- Column-header context boosting (DET-08): PiiDetector lowers score threshold to 0.3 for cells in PII-labeled columns (Customer, Email, Phone, etc.), and Sanitizer skips row-1 headers from tokenization

---
