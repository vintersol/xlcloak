# Project Research Summary

**Project:** xlcloak
**Domain:** Reversible Excel PII sanitization CLI for AI-assisted workflows
**Researched:** 2026-04-03
**Confidence:** MEDIUM (web access unavailable during research; all findings from training data through Aug 2025)

## Executive Summary

xlcloak is a Python CLI tool that sanitizes personally identifiable information from `.xlsx` spreadsheets before submission to AI tools, then restores originals (with conflict-aware reconciliation for AI-modified cells) using an encrypted `.xlcloak` bundle. The project has clear hard constraints: Python 3.10+, openpyxl for Excel I/O, Microsoft Presidio for PII detection, and the PyCA `cryptography` library for Fernet encryption. Experts build tools in this domain as a layered pipeline with strict layer isolation: workbook I/O, PII detection, token transformation, and bundle encryption are each independent components with typed intermediate representations. This architecture is the only one that makes the reconciliation problem tractable.

The recommended build sequence is bottom-up: establish the stable token engine first (correctness here is irreversible — a broken token mapping means data loss), then layer detection and Excel I/O on top, then add the encrypted bundle and restore path, and finally add power-user features (column-header context boosting, custom dictionaries, Swedish PII patterns). The single biggest risk is treating the reconciliation ("conflict-aware restore") as a simple overwrite — it must be modeled as a three-way merge (original / sanitized / current) from the start, not retrofitted later.

The threat model is explicitly "accidental exposure reduction, not adversarial anonymization." This scoping decision has direct implications for every technical choice: spaCy's `en_core_web_lg` (not the transformer model), Fernet symmetric encryption (not AES-GCM with manual nonce management), and pattern-based Swedish PII recognizers with checksum validation (not statistical population-level privacy guarantees). Keeping scope locked to this threat model is the primary risk mitigation for project creep.

---

## Key Findings

### Recommended Stack

The stack is largely constrained by PROJECT.md requirements. Python 3.11+ is the recommended runtime (3.10 is the floor). openpyxl 3.1.x is the only credible `.xlsx` read/write library. Presidio (analyzer + anonymizer 2.2.x) with spaCy 3.7.x and the `en_core_web_lg` model handles NER-based PII detection. The PyCA `cryptography` library (42.x) with Fernet + PBKDF2HMAC-SHA256 at 480,000 iterations handles bundle encryption. Click 8.1.x is the CLI framework — explicitly preferred over Typer given the multi-command option complexity. Configuration is PyYAML with `safe_load()` only. Tooling is ruff (lint/format), mypy strict, pytest + pytest-cov, uv for package management. Start with stdlib JSON for bundle serialization; msgpack is a deferred optimization.

The spaCy model (`en_core_web_lg`) is not a standard PyPI dependency — it requires a post-install download step. This is a known installation UX pitfall and must be handled at first run.

**Core technologies:**
- **Python 3.11+**: Runtime — hard constraint from PROJECT.md; structural pattern matching useful for dispatch
- **openpyxl 3.1.x**: Excel I/O — only active `.xlsx` read/write library; no COM/Win32 dependency
- **presidio-analyzer + presidio-anonymizer 2.2.x**: PII detection and token replacement — Microsoft-backed, pluggable recognizer architecture enables Swedish PII patterns without forking
- **spaCy 3.7.x + en_core_web_lg**: NER backend — acceptable recall/size trade-off for offline CLI use; no PyTorch required
- **cryptography 42.x (Fernet + PBKDF2HMAC)**: Bundle encryption — authenticated encryption with password-derived keys; random salt stored in bundle header
- **Click 8.1.x**: CLI framework — decorator-based, CliRunner for testing, handles complex option interactions cleanly
- **PyYAML 6.0.x**: Configuration — human-authored domain config; `safe_load()` only
- **ruff + mypy + pytest**: Quality toolchain — 2024-2025 Python standard
- **uv**: Dependency management — fast, covers all workflow steps

### Expected Features

Research confirms a clear three-tier feature hierarchy. The workflow is only complete when all table stakes features exist together — a sanitize command without an encrypted bundle, or a restore command without conflict-aware reconciliation, is incomplete.

**Must have (table stakes):**
- Email, phone, person name (NER), and URL detection and replacement — any miss is a trust-breaker
- Stable token mapping (same input → same token, per-bundle) — broken mapping means broken restore
- Readable token format (e.g., `<PERSON_1>`) — must survive Excel round-trip without corruption
- Restore from bundle with conflict-aware reconciliation — the core value proposition
- Encrypted `.xlcloak` bundle — unencrypted bundle makes sanitization theater
- Dry-run / inspect mode — users will not run a destructive command blind
- Manifest / audit log — power users need to know what was and was not covered
- Warnings for unsupported surfaces (formulas, comments, charts) — silent omission is a trust-breaker
- Cross-platform CLI; PyPI installable

**Should have (differentiators):**
- Swedish personnummer and org-nummer detection (with Luhn checksum validation) — essentially zero other open-source Excel sanitizers handle Nordic ID formats
- Context-aware detection via column headers (boost confidence when column is named "Contact", "Name", etc.) — dramatically reduces false negatives in structured Excel data
- Hide-all mode (every text cell tokenized) — safe default for high-sensitivity documents
- Company / legal entity detection (entity suffix patterns: AB, Ltd, GmbH, Inc.)
- `diff` command (audit what the sanitized file exposed before sending)
- User-supplied deny/allow lists and per-column mode overrides
- Named `.xlcloak` bundle format with version header — enables team workflows

**Defer to v2+:**
- Numeric obfuscation / date shifting (lossy, complex, different threat model)
- Formula sanitization (requires Excel formula AST parser; risk of breaking workbook logic)
- `.xlsm` / `.xlsb` support (openpyxl support limited)
- Batch / folder mode
- TUI / interactive mode
- Enterprise key management (HSM, KMS)
- GUI / web interface

### Architecture Approach

xlcloak is best built as a strict layered pipeline with explicit typed intermediate representations at each boundary: `CellModel` (from Workbook I/O), `DetectionResult` (from Detection Layer), `TokenRegistry` (from Transform Layer). The Workbook I/O Layer has zero knowledge of PII; the Detection Layer has zero knowledge of Excel structure; the Transform Layer knows about neither. This isolation is what makes the reconciliation problem testable and is the central architectural decision. The Orchestration Layer wires these components together for each command (sanitize, restore, inspect, diff). The CLI is the last layer added, not the first — integration testing through the CLI before unit tests exist is a trap to avoid.

**Major components:**
1. **CLI Layer** — Click commands, argument parsing, exit codes, invokes engines
2. **Orchestration Layer** — `SanitizeEngine` / `RestoreEngine`; coordinates all components for each command
3. **Workbook I/O Layer** — openpyxl; produces `CellModel` list; logs unsupported surfaces; applies writes in a single final pass
4. **Detection Layer** — Presidio `AnalyzerEngine` + custom recognizers; processes one string at a time; returns `DetectionResult` spans
5. **Transform Layer** — `TokenRegistry` (bidirectional dict); `Tokenizer` (span-based right-to-left replacement)
6. **Bundle Layer** — Fernet encryption + PBKDF2; serializes `TokenRegistry`; writes `manifest.json`
7. **Config Layer** — `SanitizeConfig` dataclass injected at engine init; never read config files inside detection/transform functions

**Recommended build order:** Workbook I/O → Detection → Transform → Bundle → Orchestration → CLI (Config alongside any layer). This ensures each layer has passing unit tests before the next layer builds on it.

### Critical Pitfalls

1. **Token instability across sanitize runs** — Use deterministic HMAC-based token generation (not `uuid4()` or `random`); test same-input → same-token across two independent runs; lock this before writing any restore logic
2. **openpyxl round-trip data loss** — Use copy-then-patch strategy (`shutil.copy2` original, then modify only target cells); test a no-op round-trip against a workbook with conditional formatting, data validation, sparklines, and merged cells; sparklines and threaded comments are known-lossy surfaces
3. **Partial token replacement offset corruption** — Always replace spans right-to-left by start offset; use Presidio's `ConflictResolutionStrategy` to resolve overlapping results before applying; test cells with two or more PII entities
4. **NER confidence threshold miscalibration** — Use per-entity-type thresholds with column-header boosting; a single global threshold tuned for document text will both over- and under-detect in short Excel cell values
5. **Fernet key derivation errors** — Use PBKDF2HMAC-SHA256 with 480,000 iterations, random 16-byte salt stored in bundle header alongside KDF params; never pass raw password as Fernet key; test cross-machine bundle portability

---

## Implications for Roadmap

Based on the dependency graph from FEATURES.md and the build order from ARCHITECTURE.md, a four-phase structure is recommended. The phase order is dictated by hard technical dependencies — each phase produces the typed artifact that the next phase consumes.

### Phase 1: Foundation — Token Engine and Excel I/O

**Rationale:** The token engine's correctness is irreversible. If token stability is wrong at this stage, every downstream component is built on a broken foundation. Excel I/O must also be validated here because openpyxl round-trip data loss is a critical pitfall that is very painful to retrofit a fix for.

**Delivers:** A tested, correct token engine; a validated Excel read/write pipeline; the `CellModel` and `TokenRegistry` typed representations; a no-op round-trip test suite against real `.xlsx` files.

**Addresses features:** Stable token mapping; readable token format; workbook iteration (including merged cell handling); unsupported surface detection (formulas, comments).

**Avoids pitfalls:** Token instability (Pitfall 1); openpyxl round-trip data loss (Pitfall 2); substring offset collision (Pitfall 6); merged cell iteration (Pitfall 8); cell type preservation (Pitfall 7).

**Research flag:** Standard patterns — no additional phase research needed. openpyxl and deterministic hashing are well-documented.

### Phase 2: Core Sanitize Command

**Rationale:** With a stable token engine and validated Excel I/O, the Presidio detection pipeline and the full `sanitize` command can be built on solid ground. This phase produces the primary user-facing artifact.

**Delivers:** Working `xlcloak sanitize` CLI command with `--dry-run`; Presidio-based detection for email, phone, person, URL; manifest output; encrypted `.xlcloak` bundle; PyPI-installable package with spaCy model handling.

**Uses:** presidio-analyzer, presidio-anonymizer, spaCy `en_core_web_lg`, Fernet/PBKDF2HMAC, Click, PyYAML.

**Implements:** Detection Layer, Bundle Layer, CLI Layer, Orchestration Layer (sanitize path only).

**Avoids pitfalls:** NER threshold calibration (Pitfall 3); spaCy model install failure (Pitfall 4); Fernet key derivation errors (Pitfall 5); manifest/file divergence (Pitfall 10); CLI exit codes (Pitfall 13); bundle file naming collision (Pitfall 15).

**Research flag:** Needs phase research. Presidio's `AnalyzerEngine` API (including `ConflictResolutionStrategy` availability and batch analyze API) should be verified against current docs before implementation begins. spaCy pip-installable model package names (`en-core-web-lg`) need live verification.

### Phase 3: Restore and Reconciliation

**Rationale:** The restore command depends on the bundle format (Phase 2) and the token engine (Phase 1) both being stable. Reconciliation is the most complex correctness problem in the project and must be implemented and tested thoroughly before any power-user features are added.

**Delivers:** Working `xlcloak restore` command with conflict-aware (three-way merge) reconciliation; `xlcloak diff` command; complete end-to-end workflow test.

**Implements:** Orchestration Layer (restore path); reconciliation engine; diff path.

**Avoids pitfalls:** Reconciliation "unchanged" detection errors (Pitfall 11); multi-line cell NER context (Pitfall 12).

**Research flag:** Standard patterns for the diff and reconciliation logic. Three-way merge model is well-understood.

### Phase 4: Power User Features

**Rationale:** With the core workflow solid, differentiating features can be added incrementally. Swedish PII patterns, context-aware detection, hide-all mode, and custom config are independent of each other and can be prioritized within the phase based on user demand.

**Delivers:** Swedish personnummer and org-nummer recognizers (with Luhn checksum validation); context-aware column header boosting; hide-all mode; company/legal entity detection; user-supplied deny/allow lists and per-column config overrides.

**Implements:** Custom Presidio `PatternRecognizer` subclasses; `DetectionConfig` injection; `SanitizeConfig` YAML schema.

**Avoids pitfalls:** Swedish checksum false positives (Pitfall 9).

**Research flag:** Swedish personnummer and org-nummer checksum algorithms (Luhn variant) should be verified against current Skatteverket specification before implementing the recognizers.

### Phase Ordering Rationale

- Phase 1 before Phase 2: `TokenRegistry` type and correctness must exist before the Detection Layer can produce output that feeds into it. openpyxl round-trip validation must precede writing any cell modification logic.
- Phase 2 before Phase 3: The bundle format produced in Phase 2 is the input consumed by the restore path in Phase 3. Changing the bundle schema after restore is implemented creates migration complexity.
- Phase 3 before Phase 4: Correctness of the core workflow (sanitize → AI edit → restore) must be verified before adding detection variations (Swedish PII, hide-all mode) that exercise the same pipeline. A bug in the restore engine discovered after Phase 4 is harder to isolate.
- Phase 4 is internally parallelizable: Swedish recognizers, header context boosting, and custom config are independent of each other.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2:** Verify current Presidio `AnalyzerEngine` API surface (batch analyze, `ConflictResolutionStrategy`) against live docs. Verify spaCy 3.x pip-installable model package names. Confirm PBKDF2 iteration count against current OWASP guidance (was 600,000 for SHA-256 in late 2023 — STACK.md uses 480,000 citing NIST 2023; reconcile).
- **Phase 4:** Verify Swedish personnummer Luhn checksum algorithm and org-nummer checksum against current Skatteverket specification.

Phases with standard patterns (skip research-phase):
- **Phase 1:** openpyxl cell model, deterministic hashing, dataclass typing — all well-documented with stable APIs.
- **Phase 3:** Three-way merge reconciliation model is a standard algorithm; no novel integration needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core library choices (openpyxl, Presidio, cryptography, Click) are HIGH confidence from PROJECT.md constraints and training data. Version numbers for spaCy, uv, hatchling, and Presidio sub-versions are MEDIUM — verify on PyPI before pinning. |
| Features | MEDIUM | Table stakes and anti-features are HIGH (derived directly from PROJECT.md and domain reasoning). Differentiator claims (e.g., "essentially zero other tools handle Swedish Excel PII") are LOW — no live market verification was possible. |
| Architecture | MEDIUM | Layered pipeline pattern and component boundaries are HIGH confidence as general software design. Presidio API specifics (`ConflictResolutionStrategy`, batch analyze) are MEDIUM — verify against current docs. |
| Pitfalls | HIGH | Most pitfalls are language/library-agnostic correctness problems (offset replacement, round-trip data loss, key derivation) verified by training knowledge of well-documented library behaviors. Presidio threshold defaults are MEDIUM. |

**Overall confidence:** MEDIUM — sufficient to begin roadmap planning and Phase 1 implementation. Phase 2 should start with a Presidio API verification step.

### Gaps to Address

- **Presidio API verification:** `ConflictResolutionStrategy` existence and accessibility, batch analyze API availability, and exact default `score_threshold` values need live-docs check before Phase 2 implementation begins.
- **PBKDF2 iteration count discrepancy:** STACK.md cites 480,000 (NIST 2023); OWASP 2023 guidance was 600,000 for SHA-256. Reconcile against the most current guidance before the bundle encryption implementation in Phase 2.
- **spaCy model pip package names:** `en-core-web-lg` package name and install mechanism for spaCy 3.7.x must be verified — these changed between spaCy 2.x and 3.x.
- **Swedish personnummer checksum:** The Luhn-variant algorithm for personnummer and the separate org-nummer checksum must be verified against Skatteverket specification (not from training data alone) before Phase 4 recognizer implementation.
- **openpyxl threaded comments:** Behavior of threaded comments (vs. legacy notes) in the current openpyxl release should be verified — this affects the unsupported surface warning list in Phase 1.

---

## Sources

### Primary (HIGH confidence)
- `/home/ajans/code/xlcloak/.planning/PROJECT.md` — hard requirements, out-of-scope decisions, threat model
- Python `cryptography` library Fernet/PBKDF2HMAC documentation — stable API, well-established
- NIST SP 800-132 / OWASP Password Storage Cheat Sheet — PBKDF2 iteration count guidance

### Secondary (MEDIUM confidence)
- Microsoft Presidio documentation (training knowledge, Aug 2025 cutoff) — `AnalyzerEngine` API, recognizer plugin architecture, context words
- openpyxl documentation (training knowledge, Aug 2025 cutoff) — cell model, merged cells, known lossy surfaces
- spaCy documentation (training knowledge, Aug 2025 cutoff) — model packages, NLP pipeline behavior
- Click documentation (training knowledge, Aug 2025 cutoff) — command structure, CliRunner

### Tertiary (LOW confidence — verify before use)
- Market claims about competitor tools lacking Swedish Excel PII support — no live verification possible
- Presidio default `score_threshold` values — derived from training knowledge, needs live-docs confirmation
- spaCy pip-installable model package names (`en-core-web-lg`) — package naming has changed across major versions

---
*Research completed: 2026-04-03*
*Ready for roadmap: yes*
