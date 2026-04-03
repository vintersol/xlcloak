# Technology Stack

**Project:** xlcloak
**Researched:** 2026-04-03
**Note on versions:** All network tools (WebSearch, WebFetch, Brave, pip) were blocked during
this research session. Versions are sourced from training data (knowledge cutoff August 2025).
Each entry carries an explicit confidence level. Verify pinned versions against PyPI before
writing `pyproject.toml`.

---

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

**Note on spaCy model choice:** `en_core_web_trf` (transformer-based) gives best accuracy but adds a heavy PyTorch dependency (~1-2 GB). Not worth it for a CLI tool where false-negative PII leakage is acceptable risk (threat model is accidental exposure reduction, not adversarial). Stick with `en_core_web_lg`.

**Note on Swedish NER:** spaCy has no first-class Swedish NER model that ships with Presidio. Swedish person/org detection will rely on custom `PatternRecognizer` rules (personnummer regex: `\d{6,8}[-+]\d{4}`, org-nummer: `\d{6}-\d{4}`) plus context-boost from column headers. This is sufficient for V1 because the threat model is accidental exposure, not adversarial. Document this limitation clearly.

### Encryption / Bundle

| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| cryptography | 42.x (>=42.0.0) | Fernet symmetric encryption + PBKDF2HMAC key derivation | PROJECT.md constraint; PyCA cryptography is the reference Python crypto library; Fernet provides authenticated encryption (AES-128-CBC + HMAC-SHA256); PBKDF2HMAC with SHA256 and 480,000 iterations (NIST 2023 recommendation) derives a key from user password; no secrets stored at rest | HIGH |

**Fernet key derivation pattern:**
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import base64, os

salt = os.urandom(16)
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
fernet = Fernet(key)
```

Store `salt` in bundle header (unencrypted) alongside the Fernet-encrypted payload. The `.xlcloak` bundle format should be: `[4-byte magic][salt-16-bytes][fernet-ciphertext]`.

### CLI Framework

| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| Click | 8.1.x (>=8.1.7) | CLI commands, options, argument parsing | Mature, battle-tested; decorator-based API is clean for a multi-command CLI (`sanitize`, `restore`, `inspect`, `diff`, `reconcile`); built-in `--help` generation, error handling, and `CliRunner` for testing; no runtime magic | HIGH |

**Why NOT Typer:** Typer wraps Click with type-annotation-based interface. Good DX for simple scripts. But xlcloak's commands have non-trivial option interactions (e.g. `--mode`, `--config`, `--dry-run` combinations) where Click's explicit `@click.option` decorators are clearer and more testable. Typer also adds a fastapi-style dependency that is unnecessary here.

**Why NOT argparse:** stdlib argparse requires more boilerplate for subcommands and lacks `CliRunner` test integration. Not worth it when Click is available.

### Serialization / Bundle Format

| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| msgpack | 1.0.x (>=1.0.7) | Serialize token map and manifest inside the encrypted bundle | Compact binary serialization; faster and smaller than JSON for large token maps (workbooks with thousands of cells); no external attack surface since it is only deserialized after Fernet decryption succeeds | MEDIUM |

**Alternative: JSON** — Use JSON instead of msgpack if simplicity is prioritized and bundle size is acceptable. JSON is human-readable after decryption (useful for debugging), has zero additional dependencies, and is part of stdlib. For V1, JSON is a reasonable choice. Upgrade to msgpack if bundle size becomes a concern.

**Recommendation:** Start with JSON (stdlib). Switch to msgpack only if profiling shows size/speed problems with large workbooks (>50k cells).

### Configuration / User Config

| Technology | Version (pin >=) | Purpose | Why | Confidence |
|------------|-----------------|---------|-----|------------|
| PyYAML | 6.0.x (>=6.0.1) | Parse user-supplied domain config files | YAML is the natural format for human-authored config (dictionaries, per-column overrides, deny/allow lists); PyYAML is the de facto parser; use `yaml.safe_load()` only — never `yaml.load()` | HIGH |

**Alternative: TOML (stdlib tomllib in 3.11+)** — TOML is simpler and safer (no `load()` footgun). Python 3.11+ ships `tomllib` for reading. However, TOML write support (`tomli_w`) requires an extra dep, and YAML is more natural for nested overrides with comments. YAML is fine given `safe_load()` discipline.

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

**Why NOT Poetry:** Poetry is heavy and has a history of resolver slowness. uv is now the preferred choice for new projects that don't need Poetry's publish workflow features. For PyPI publishing, `uv publish` works.

---

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

---

## Installation

```bash
# Bootstrap project with uv
uv init xlcloak
cd xlcloak

# Core runtime dependencies
uv add openpyxl>=3.1.2
uv add presidio-analyzer>=2.2.354
uv add presidio-anonymizer>=2.2.354
uv add "spacy>=3.7.4"
uv add "cryptography>=42.0.0"
uv add "click>=8.1.7"
uv add "pyyaml>=6.0.1"

# spaCy model (post-install step, not a PyPI dep — document in README)
python -m spacy download en_core_web_lg

# Dev dependencies
uv add --dev pytest>=8.1.0
uv add --dev pytest-cov>=5.0.0
uv add --dev ruff>=0.4.0
uv add --dev mypy>=1.9.0
```

**pyproject.toml entry_points:**
```toml
[project.scripts]
xlcloak = "xlcloak.cli:main"
```

**spaCy model install note:** `en_core_web_lg` must be downloaded separately and is not a PyPI package with a stable version pin. Document as a post-install step in README and consider shipping a `setup` subcommand that runs `python -m spacy download en_core_web_lg` automatically on first run.

---

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

---

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
