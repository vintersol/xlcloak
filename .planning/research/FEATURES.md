# Feature Landscape

**Domain:** Reversible Excel text sanitization CLI for AI workflows
**Researched:** 2026-04-03
**Confidence note:** External web search and WebFetch are unavailable in this session. All findings derive from training knowledge of the Presidio, openpyxl, and data anonymization ecosystems (training cutoff August 2025). Confidence levels reflect this constraint.

---

## Table Stakes

Features users expect from any PII sanitization tool. Missing = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Email address detection and replacement | Emails are the #1 PII leak vector; any sanitizer that misses them is useless | Low | Regex-based; high precision |
| Phone number detection | Universal PII; present in nearly every business spreadsheet | Medium | Country format variations require multiple patterns |
| Person name detection (NER) | Names are core personal data; pure regex cannot cover; NER required | High | Presidio + spaCy NER; recall < 100%, needs tuning |
| Stable token mapping (same input → same token) | Without this, AI responses referencing "PERSON_1" cannot be reconciled — tokens drift | Medium | In-memory dict per session, persisted in bundle |
| Readable token format (e.g., `<PERSON_1>`) | Tokens must survive Excel round-trip without cell format corruption; must be human-parseable in AI output | Low | Angle-bracket or bracket-wrapped tokens are conventional |
| Restore to original from bundle | The entire value proposition; if restore breaks, the tool has no purpose | High | Conflict-aware reconciliation is table stakes here, not a differentiator |
| Dry-run / inspect mode | Users will not run a destructive command blind; preview is safety infrastructure | Low | CLI flag; no writes |
| Encrypted bundle | If the bundle is plaintext, sanitizing the xlsx is theater | Medium | Fernet + PBKDF2; password prompt UX matters |
| Manifest / audit log | Power users and teams need to know what was changed and what was skipped | Medium | JSON or YAML; machine-readable preferred |
| Cross-platform CLI (Windows, macOS, Linux) | Developer and analyst audience uses all three; Windows is dominant in enterprise Excel use | Medium | Python packaging handles most of this; path separators, encoding edge cases remain |
| PyPI installable (`pip install xlcloak`) | Any friction to install kills adoption in the target audience | Low | Standard `pyproject.toml`; ensure entry_points CLI hook |
| Warnings for unsanitized surfaces (formulas, comments) | Users must know what the tool did NOT cover; silent omission is a trust-breaker | Low | Log to manifest; print summary to stderr |
| URL detection | URLs frequently embed PII (names in paths, email in query strings) | Low | Regex-based |

## Differentiators

Features that set xlcloak apart from generic anonymization tools. Not universally expected but high-value for the target audience.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Context-aware detection via column headers | Most PII tools treat every cell equally; header-boosted scoring dramatically reduces false negatives in structured Excel data (e.g., column named "Customer" → boost NER confidence for that column) | High | Presidio supports context words; xlcloak must extract column headers and pass as context |
| Swedish PII patterns (personnummer, org-nummer) | Essentially zero other open-source Excel sanitizers handle Swedish national ID formats; this is a strong niche differentiator for Nordic users | Medium | Personnummer: `YYMMDD-NNNN` and `YYYYMMDD-NNNN`; org-nummer: `NNNNNN-NNNN`; Luhn-like checksums for validation |
| Hide-all mode (every text cell → token) | For high-sensitivity documents or when NER precision is too low, blanket replacement is the safe default; no other lightweight CLI tool offers this as a first-class mode | Low | Token must still be stable (deterministic per cell value) |
| Reconciliation of AI-modified cells on restore | The AI editing workflow means some cells change; a naive restore that overwrites AI edits destroys the workflow. Conflict-aware restore (skip changed, restore unchanged) is novel in this class of tool | High | Requires cell-level hash comparison between sanitized-original and sanitized-current states |
| User-supplied dictionaries and deny/allow lists | Domain-specific proper nouns (ERP codes, project names, client abbreviations) are the long tail of exposure; custom dicts are the escape hatch no generic tool offers | Medium | YAML/JSON config file; per-column overrides add complexity |
| Per-column mode overrides | A column of product SKUs should not run NER; a column of "Contact Name" should be maximally aggressive — column-level config gives fine-grained control | Medium | Depends on custom config infrastructure |
| Company / legal entity detection as first-class | Generic NER marks organizations, but legal entity suffixes (AB, Ltd, GmbH, Inc., LLC) are strong signals that most tools treat as noise; xlcloak should weight these | Medium | Presidio pattern recognizer for entity suffixes + NER combination |
| Shape-preserving tokens | Tokens that preserve visible length (e.g., `████████` or padded token strings) reduce AI model confusion about cell content type; standard angle-bracket tokens already partially do this | Low | Mostly cosmetic; angle-bracket tokens are sufficient |
| `.xlcloak` bundle format as a portable artifact | A named, versioned bundle format (not just a zip + JSON) is a differentiator for team workflows: share bundle, share restore capability | Low | Extension naming + version header in bundle metadata |
| Diff command (sanitized vs. bundle) | Lets users audit exactly what a sanitized file exposed before sending it; useful for compliance workflows | Medium | Requires reading both sanitized xlsx and bundle mapping |

## Anti-Features

Features to explicitly NOT build in V1, with rationale.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Numeric obfuscation / date shifting | Numeric transforms (shift dates, scale values) are lossy and complex; reversibility is fragile; adds a second threat model | Defer to V2; log numeric cells with high-entropy values as informational only |
| Formula sanitization | Formulas reference cell addresses, not values; sanitizing formula content requires AST-level Excel formula parsing (no simple Python library); risk of breaking workbook logic is very high | Log formulas as "not sanitized" in manifest; warn user |
| Comments, notes, chart labels, VBA, pivot caches | These surfaces require deep openpyxl knowledge and differ across xlsx versions; the ROI vs. complexity ratio is unfavorable for V1 | Log presence as warnings; document the gap explicitly in README |
| `.xlsm` / `.xlsb` support | `.xlsm` (macro-enabled) and `.xlsb` (binary) require separate parsers; openpyxl support for these is limited and fragile | `.xlsx` only in V1; document clearly at install |
| Batch / folder mode | Multiple files at once adds error-aggregation complexity and ambiguous bundle naming; single-file discipline is safer for V1 | Document shell one-liner for batch (`for f in *.xlsx; do xlcloak sanitize $f; done`) |
| TUI / interactive mode | A terminal UI adds a UI framework dependency and maintenance burden; CLI flags are sufficient for the target audience | Rich CLI with `--help` and `--dry-run` covers the interaction surface |
| Enterprise key management (HSM, KMS) | Vault/KMS integration is a multi-week project and targets a different buyer; password-derived keys cover the individual/team use case | Document Fernet key derivation; defer KMS to enterprise fork |
| GUI / web interface | The target user is comfortable with CLI; a GUI adds packaging complexity for zero workflow benefit | CLI only; recommend wrapping with shell aliases if needed |
| Adversarial anonymization guarantees | k-anonymity, l-diversity, differential privacy — these require statistical analysis of the dataset and are categorically different from PII scrubbing | State threat model clearly: "accidental exposure reduction, not adversarial anonymization" |
| Built-in AI integration (send to GPT, etc.) | The tool sits in a workflow; it should not own the AI step; coupling to a specific AI provider makes xlcloak brittle and opinionated beyond its scope | Produce a sanitized file; the user pipes it to their AI tool |
| Automatic bundle versioning / migration | Bundle format migrations require backward-compatibility infrastructure; V1 can be strict: bundle version must match tool version | Include bundle version in metadata; error clearly on mismatch |

---

## Feature Dependencies

```
Custom config (dicts, per-column overrides)
  └── requires: config file loader + schema validation
  └── requires: column header extraction (same system used for context boosting)

Context-aware detection (header boosting)
  └── requires: column header extraction from openpyxl
  └── requires: Presidio context words API

Stable token mapping
  └── requires: deterministic token generator (hash or counter)
  └── feeds: bundle (token → original mapping)
  └── feeds: restore command
  └── feeds: reconciliation logic

Reconciliation on restore
  └── requires: stable token mapping
  └── requires: cell-level hash of sanitized-original state (stored in bundle)
  └── requires: re-reading current sanitized xlsx at restore time

Diff command
  └── requires: bundle (token mapping)
  └── requires: current sanitized xlsx
  └── depends on: stable token mapping (tokens are the join key)

Manifest
  └── requires: detection pass results (what was found, where, confidence)
  └── requires: unsupported surface scan (formulas, comments, etc.)
  └── feeds: user trust in what the tool did/did not cover

Swedish PII recognizers (personnummer, org-nummer)
  └── requires: custom Presidio PatternRecognizer subclasses
  └── independent of NER pipeline (pattern-only)

Hide-all mode
  └── requires: stable token mapping
  └── independent of NER/Presidio (bypasses detection entirely)
  └── feeds: same restore/reconcile pipeline as token mode
```

---

## MVP Recommendation

The project's Active Requirements list is already well-scoped. Based on feature dependencies and user trust requirements:

**Prioritize in Phase 1 (foundation):**
1. Core detection pipeline (email, phone, NER names, URLs) — table stakes, everything else depends on this working reliably
2. Stable token mapping — dependency for restore, reconcile, diff
3. `sanitize` CLI command with dry-run flag — primary user-facing action
4. Manifest output — users won't trust the tool without an audit trail

**Prioritize in Phase 2 (completeness):**
5. Encrypted `.xlcloak` bundle
6. `restore` with conflict-aware reconciliation — completes the core workflow
7. Swedish PII patterns (personnummer, org-nummer) — stated first-class requirement
8. Hide-all mode — simple to implement once token mapping exists

**Prioritize in Phase 3 (power user):**
9. Context-aware detection via column headers — high-value differentiator, moderate complexity
10. Company / legal entity detection
11. `diff` command
12. Custom dictionaries and per-column config

**Defer to V2:**
- Numeric obfuscation / date shifting
- Batch mode
- `.xlsm` / `.xlsb` support

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Table stakes features | MEDIUM | Based on training knowledge of Presidio, anonymization tools, and CLI tool conventions; external verification unavailable |
| Swedish PII patterns | HIGH | Personnummer and org-nummer formats are well-documented ISO/national standards; not dependent on current web sources |
| Presidio capabilities (context words, custom recognizers) | MEDIUM | Based on training knowledge through ~Aug 2025; API may have changed; verify against current Presidio docs |
| Reconciliation as differentiator | HIGH | Derived directly from PROJECT.md stated core value; not a market claim |
| Anti-features rationale | HIGH | Derived from PROJECT.md Out of Scope section + complexity reasoning; not market-dependent |

---

## Sources

- `/home/ajans/code/xlcloak/.planning/PROJECT.md` — Primary project context, requirements, out-of-scope decisions
- Training knowledge: Microsoft Presidio architecture and recognizer API (through August 2025)
- Training knowledge: openpyxl cell/sheet model for surface coverage analysis
- Training knowledge: Fernet/cryptography library for bundle encryption patterns
- Training knowledge: Data anonymization CLI tool conventions (ARX, sdcMicro, `faker`-based tools)
- Note: WebSearch, WebFetch, Brave Search all unavailable in this session. All market/ecosystem claims are LOW-to-MEDIUM confidence and should be spot-checked against current PyPI ecosystem and Presidio docs before finalizing roadmap.
