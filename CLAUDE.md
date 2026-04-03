# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

This repository is in early initialization — only a LICENSE file exists. No build system, language, or project structure has been established yet.

Once code is added, update this file with:
- Build, lint, and test commands
- High-level architecture and key entry points

<!-- GSD:project-start source:PROJECT.md -->
## Project

**xlcloak**

A reversible Excel text sanitization CLI for AI workflows. `xlcloak` sanitizes `.xlsx` files before sending them to AI tools — replacing names, emails, phone numbers, and other sensitive text with stable tokens — then restores the originals afterward via an encrypted bundle. It's a practical exposure-reduction tool for anyone feeding spreadsheets to AI systems, published as an open-source PyPI package.

**Core Value:** Sensitive text in Excel files never reaches AI tools, and the round-trip back to originals is reliable and conflict-aware.

### Constraints

- **Language**: Python 3.10+
- **Excel I/O**: openpyxl
- **PII detection**: Microsoft Presidio + custom recognizers
- **Bundle encryption**: Fernet (cryptography library, password-derived key)
- **Packaging**: PyPI distribution
- **Quality bar**: Public open-source — needs tests, docs, CI
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Framework
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| Python | 3.10+ | Runtime | PROJECT.md constraint; 3.10 structural pattern matching is useful for dispatch; 3.11+ is the safe default for new projects in 2025 | HIGH |
| openpyxl | 3.1.x (>=3.1.2) | Read/write `.xlsx` files | PROJECT.md constraint; de facto Python `.xlsx` library; handles cell values, styles, named ranges; no COM/Win32 dependency; active maintenance | HIGH |
### PII Detection
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| presidio-analyzer | 2.2.x (>=2.2.354) | NER + pattern-based PII detection | PROJECT.md constraint; Microsoft-backed; pluggable recognizer architecture lets us add Swedish personnummer/org-nummer without forking; ships built-in recognizers for email, phone, person, org, URL | HIGH |
| presidio-anonymizer | 2.2.x (>=2.2.354) | Token replacement engine | Pairs with analyzer; provides `OperatorConfig` for replace/hash/custom operators; version-locks with presidio-analyzer | HIGH |
| spacy | 3.7.x (>=3.7.4) | NLP backend for Presidio NER | Presidio's default NLP engine; `en_core_web_lg` model gives best recall for names/orgs at acceptable size; alternative `en_core_web_sm` is smaller but misses more entities | MEDIUM |
| spacy model: en_core_web_lg | 3.7.x | English NER | Larger model justified: xlcloak processes files offline before AI submission, so inference latency is acceptable; better recall for org names and locations matters more than startup speed | MEDIUM |
### Encryption / Bundle
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| cryptography | 42.x (>=42.0.0) | Fernet symmetric encryption + PBKDF2HMAC key derivation | PROJECT.md constraint; PyCA cryptography is the reference Python crypto library; Fernet provides authenticated encryption (AES-128-CBC + HMAC-SHA256); PBKDF2HMAC with SHA256 and 480,000 iterations (NIST 2023 recommendation) derives a key from user password; no secrets stored at rest | HIGH |
### CLI Framework
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| Click | 8.1.x (>=8.1.7) | CLI commands, options, argument parsing | Mature, battle-tested; decorator-based API is clean for a multi-command CLI (`sanitize`, `restore`, `inspect`, `diff`, `reconcile`); built-in `--help` generation, error handling, and `CliRunner` for testing; no runtime magic | HIGH |
### Serialization / Bundle Format
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| msgpack | 1.0.x (>=1.0.7) | Serialize token map and manifest inside the encrypted bundle | Compact binary serialization; faster and smaller than JSON for large token maps (workbooks with thousands of cells); no external attack surface since it is only deserialized after Fernet decryption succeeds | MEDIUM |
### Configuration / User Config
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| PyYAML | 6.0.x (>=6.0.1) | Parse user-supplied domain config files | YAML is the natural format for human-authored config (dictionaries, per-column overrides, deny/allow lists); PyYAML is the de facto parser; use `yaml.safe_load()` only — never `yaml.load()` | HIGH |
### Testing
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| pytest | 8.x (>=8.1.0) | Test runner | Standard; excellent plugin ecosystem; Click's `CliRunner` integrates natively | HIGH |
| pytest-cov | 5.x (>=5.0.0) | Coverage reporting | Required for open-source quality bar | HIGH |
### Code Quality
| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| ruff | 0.4.x (>=0.4.0) | Linting + formatting | Replaces flake8 + isort + black in a single fast tool; 2024-2025 standard for new Python projects; zero config in most cases | HIGH |
| mypy | 1.9.x (>=1.9.0) | Static type checking | Catches contract violations in the token-map/recognizer pipeline early; use `strict = true` in `mypy.ini` | MEDIUM |
### Packaging
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pyproject.toml (PEP 517/518) | — | Project metadata and build config | Standard since Python 3.11; replaces `setup.py` | HIGH |
| hatchling | 1.x | Build backend | Simpler than setuptools for pure-Python packages; good PyPI support; alternative is setuptools which is equally valid | MEDIUM |
| uv | 0.x (>=0.1.0) | Dependency management / virtual envs | Fast Rust-based replacement for pip + venv; 2024-2025 de facto standard for new projects; `uv add`, `uv sync`, `uv run` cover all workflow steps | MEDIUM |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Excel I/O | openpyxl | xlrd/xlwt | xlrd dropped `.xlsx` in 2.0; xlwt write-only and unmaintained |
| Excel I/O | openpyxl | xlsxwriter | Write-only; cannot read existing files |
| NER backend | spaCy (via Presidio) | transformers (HuggingFace) | Adds PyTorch; 2+ GB install; overkill for accidental-exposure threat model |
| NER backend | spaCy (via Presidio) | stanza | Lower adoption in PII tooling; no Presidio integration path |
| PII detection | presidio-analyzer | regex-only custom | Misses contextual entity disambiguation; org names especially need NER |
| PII detection | presidio-analyzer | scrubadub | Smaller ecosystem; fewer built-in recognizers; no custom recognizer plugin API |
| Encryption | Fernet (cryptography) | AES-GCM via hazmat | Fernet is authenticated + higher-level; GCM is fine but requires explicit nonce management — no benefit here |
| Encryption | Fernet (cryptography) | itsdangerous | itsdangerous uses Fernet internally but adds web framework coupling |
| CLI | Click | Typer | Typer DX improvement is small for complex option sets; adds wrapper complexity |
| CLI | Click | argparse | More boilerplate; no CliRunner for testing |
| Serialization | JSON (stdlib) | msgpack | JSON is simpler and debuggable for V1; msgpack deferred to V2 if needed |
| Build backend | hatchling | setuptools | Both valid; hatchling is cleaner for new projects |
| Dependency mgmt | uv | pip + venv | uv is dramatically faster; same interface pattern |
| Dependency mgmt | uv | Poetry | Poetry resolver has been slower historically; uv now covers the same use cases |
## Installation
# Bootstrap project with uv
# Core runtime dependencies
# spaCy model (post-install step, not a PyPI dep — document in README)
# Dev dependencies
## Confidence Assessment
| Component | Confidence | Reason |
|-----------|------------|--------|
| openpyxl as Excel I/O | HIGH | PROJECT.md hard constraint; de facto standard; no credible alternative |
| presidio-analyzer + anonymizer | HIGH | PROJECT.md hard constraint; active Microsoft project; pluggable architecture confirmed in training data |
| cryptography / Fernet | HIGH | PROJECT.md hard constraint; PyCA reference library; well-documented Fernet + PBKDF2 API |
| spaCy 3.7 as NER backend | MEDIUM | Cannot verify exact current version; spaCy 3.x has been the active major line since 2021; 3.7.x is the last confirmed training-data version |
| Click 8.1 | HIGH | Stable, widely used; no credible successor; 8.1 has been the active minor since 2022 |
| ruff for linting | HIGH | Emerged as the 2024-2025 Python linting standard; confirmed by broad ecosystem adoption |
| uv for packaging | MEDIUM | Rapid development; versions move fast; pin conservatively and verify before use |
| hatchling build backend | MEDIUM | Valid choice but setuptools is equally defensible; no version verified |
| PyYAML for config | HIGH | Stable and de facto; safe_load() usage avoids known CVEs |
| presidio-analyzer version numbers | MEDIUM | Last confirmed version was ~2.2.35x range; verify on PyPI before pinning |
| spaCy model en_core_web_lg | MEDIUM | Model availability tied to spaCy version; download step must match installed spaCy version |
## Sources
- Training data (knowledge cutoff August 2025) — all version numbers
- PROJECT.md — language, Excel I/O, PII detection, encryption constraints
- PyPI JSON API — blocked during this session; verify all versions at https://pypi.org before pinning
- NIST SP 800-132 (2010, updated guidance 2023) — PBKDF2 iteration count recommendation
- Presidio docs: https://microsoft.github.io/presidio/
- spaCy docs: https://spacy.io/usage/models
- cryptography docs: https://cryptography.io/en/latest/fernet/
- Click docs: https://click.palletsprojects.com/en/8.x/
- openpyxl docs: https://openpyxl.readthedocs.io/en/stable/
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
