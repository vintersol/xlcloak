# Phase 2: Core Sanitize - Research

**Researched:** 2026-04-03
**Domain:** Presidio PII detection, Fernet bundle encryption, Click CLI, spaCy NER
**Confidence:** HIGH (all critical APIs verified against installed packages)

## Summary

Phase 2 builds the primary user-facing commands on top of the Phase 1 foundation. The key work is: (1) a detection pipeline wrapping Presidio's AnalyzerEngine, (2) a bundle writer that serializes the token map as JSON and encrypts it with Fernet, (3) Click commands for `sanitize` and `inspect`, and (4) PyPI packaging.

The three blockers from STATE.md have been resolved. Presidio's `AnalyzerEngine.analyze()` accepts `score_threshold` at call time (or `default_score_threshold` at init), and the entity names it returns are `EMAIL_ADDRESS`, `PHONE_NUMBER`, `PERSON`, `URL`, and `ORGANIZATION` — **not** `EMAIL`, `PHONE`, `ORG` as the existing `EntityType` enum uses. A thin mapping layer is required. The PBKDF2 iteration count question is settled: OWASP's current recommendation is 600,000 for PBKDF2-HMAC-SHA256. The spaCy model package is `en_core_web_lg` (underscores), installed either via `python -m spacy download en_core_web_lg` or the direct GitHub wheel URL; the correct version for the installed spaCy 3.8.14 is `en_core_web_lg-3.8.0`.

One important discovery: `rich` is already a transitive dependency in the venv (v14.3.3 via typer). It should be added as an explicit direct dependency for the inspect table output. The `tabulate` library is not installed and would be an additional dependency; `rich` is the better choice since it is already present.

**Primary recommendation:** Build detection as a thin `PiiDetector` class wrapping NlpEngineProvider + AnalyzerEngine, with a Presidio-to-EntityType mapping dict. Wire the detection output directly into `TokenRegistry.get_or_create()`. The bundle is a JSON dict encrypted with Fernet; salt is stored in the bundle header alongside ciphertext. The CLI is a Click group with `sanitize` and `inspect` subcommands, both using `auto_envvar_prefix="XLCLOAK"` so `--password` maps to `XLCLOAK_PASSWORD`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Aggressive detection — low confidence threshold (~0.4). Fits the "accidental exposure reduction" threat model.
- **D-02:** Overlapping entity resolution: highest confidence wins. Use Presidio's built-in conflict resolution strategy.
- **D-03:** Multi-entity cells: replace each detected entity inline within the cell text.
- **D-04:** Phase 2 includes basic ORG detection from Presidio's spaCy NER. Phase 4 adds suffix-boosted detection and Swedish PII.
- **D-05:** Phase 2 recognizers: EMAIL, PHONE, PERSON (NER), URL, ORG (NER). Swedish PII and column-header boosting are Phase 4.
- **D-06:** Default password "xlcloak". Users who want real encryption use `--password` flag or `XLCLOAK_PASSWORD` env var. Bundle header marks which mode was used.
- **D-07:** Bundle internal format: JSON (human-debuggable after decryption). msgpack deferred to V2.
- **D-08:** Bundle metadata: xlcloak version, original filename, creation timestamp, sheet names processed, token count.
- **D-09:** Fernet symmetric encryption with PBKDF2HMAC-SHA256 key derivation. Iteration count determined by researcher.
- **D-10:** Suffix naming convention: `data_sanitized.xlsx` + `data.xlcloak` + `data_manifest.txt`, all in the same directory.
- **D-11:** Overwrite protection: refuse to overwrite existing output files with `--force` flag hint.
- **D-12:** `--output` flag sets the sanitized file path. Bundle and manifest derive from it.
- **D-13:** Inspect shows summary header (entity counts by type) + per-cell table (Sheet | Cell | Entity Type | Original | Would-be Token). Truncate long values.
- **D-14:** Inspect includes a separate "Warnings" section showing unsupported surfaces.
- **D-15:** Default output is clean summary + table. `--verbose` adds confidence scores, detection method, and surrounding text context.

### Claude's Discretion

- Presidio AnalyzerEngine configuration details (recognizer registry setup, NLP engine init)
- spaCy model choice (en_core_web_lg vs en_core_web_sm — balance recall vs install size)
- PBKDF2 iteration count (follow researcher findings on NIST vs OWASP recommendation)
- Internal module organization (where detection, bundle, CLI code lives)
- Click command group structure and help text
- Table formatting library choice for inspect output (rich, tabulate, or plain text)
- Error handling patterns and exit codes
- Progress/status output during sanitize (spinner, progress bar, or silent)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | Detect and replace email addresses with stable tokens | EmailRecognizer uses entity name `EMAIL_ADDRESS`; verified in installed presidio-analyzer 2.2.362 |
| DET-02 | Detect and replace phone numbers with stable tokens | PhoneRecognizer uses entity name `PHONE_NUMBER`; default score=0.4; regions include US, UK, DE — SE must be added in Phase 4 |
| DET-03 | Detect and replace person names via NER with stable tokens | SpacyRecognizer exposes `PERSON`; requires en_core_web_lg or en_core_web_sm installed |
| DET-04 | Detect and replace URLs with stable tokens | UrlRecognizer uses entity name `URL`; verified in installed package |
| BUN-01 | Encrypted `.xlcloak` restore bundle (Fernet, password-derived key) | Fernet + PBKDF2HMAC-SHA256 at 600k iterations verified working in installed cryptography 46.0.6 |
| BUN-02 | Manifest file documenting coverage, transformations, and risk notes | Manifest class from Phase 1 is ready; needs to write rendered text to file |
| CLI-01 | `xlcloak sanitize <file.xlsx>` produces sanitized file + bundle + manifest | Click group + subcommand pattern; entry point already wired in pyproject.toml |
| CLI-03 | `xlcloak inspect <file.xlsx>` dry-run preview with no files written | Same detection pipeline as sanitize; render with rich Table instead of writing files |
| CLI-06 | `--output`, `--dry-run`, `--text-mode`, `--verbose`, `--bundle` flags | Click option decorators; `--output` and `--verbose` are Phase 2 scope; others Phase 3/4 |
| CLI-08 | Published to PyPI, installable via `pip install xlcloak` | pyproject.toml with hatchling is already present; `uv build` + `uv publish` is the workflow |
| CLI-09 | Python 3.10+, cross-platform (Windows, macOS, Linux) | No platform-specific code introduced in Phase 2; Fernet and Click both cross-platform |
</phase_requirements>

---

## Standard Stack

### Core (verified against installed venv)

| Library | Version (installed) | Purpose | Status |
|---------|---------------------|---------|--------|
| presidio-analyzer | 2.2.362 | PII detection engine | Installed, verified |
| presidio-anonymizer | 2.2.362 | (Not needed in Phase 2 — we do inline replacement manually) | Installed |
| spaCy | 3.8.14 | NLP backend for Presidio NER | Installed; model not yet downloaded |
| en_core_web_lg | 3.8.0 | English NER model (PERSON, ORG) | NOT installed; must be downloaded |
| cryptography | 46.0.6 | Fernet encryption + PBKDF2HMAC key derivation | Installed, verified |
| click | 8.3.1 | CLI commands and option parsing | Installed |
| rich | 14.3.3 | Table rendering for inspect output | Installed (transitive dep); add as explicit dep |
| openpyxl | 3.1.5 | Excel I/O (Phase 1) | Installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| phonenumbers | (transitive) | Phone number parsing for PhoneRecognizer | Included automatically with presidio-analyzer |
| tldextract | (transitive) | Email domain validation for EmailRecognizer | Included automatically with presidio-analyzer |

### Not Needed in Phase 2

| Library | Reason |
|---------|--------|
| presidio-anonymizer | We perform inline replacement ourselves using sorted RecognizerResult positions — no need for AnonymizerEngine |
| msgpack | Deferred to V2 per D-07 |
| tabulate | rich is already available and more capable |

### Installation Steps

```bash
# Add rich as explicit dependency
uv add rich

# Install spaCy model (post-install step — not a PyPI dep)
uv run python -m spacy download en_core_web_lg

# OR install directly from GitHub release (for reproducible CI):
uv run pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

**Version verification (as of 2026-04-03):**
- `presidio-analyzer 2.2.362` — confirmed via `importlib.metadata.version`
- `spaCy 3.8.14` — confirmed via `spacy.__version__`
- `cryptography 46.0.6` — confirmed via `importlib.metadata.version`
- `click 8.3.1` — confirmed via `importlib.metadata.version`
- `rich 14.3.3` — confirmed via `importlib.metadata.version`
- `en_core_web_lg 3.8.0` — GitHub release exists, wheel URL verified (HTTP 302 to asset)

---

## Architecture Patterns

### Recommended Module Structure

```
src/xlcloak/
├── models.py           # Phase 1 — EntityType, CellRef, ScanResult, SurfaceWarning
├── token_engine.py     # Phase 1 — TokenRegistry, TokenFormatter
├── excel_io.py         # Phase 1 — WorkbookReader, WorkbookWriter
├── manifest.py         # Phase 1 — Manifest
├── detector.py         # NEW — PiiDetector (wraps AnalyzerEngine)
├── bundle.py           # NEW — BundleWriter (Fernet encrypt + JSON serialize)
├── sanitizer.py        # NEW — Sanitizer orchestrator (read → detect → tokenize → write)
└── cli.py              # NEW — Click group: main, sanitize, inspect
```

### Pattern 1: Presidio AnalyzerEngine Setup

**What:** Initialize NlpEngineProvider with the spaCy model config, then pass to AnalyzerEngine with a low default threshold.

**When to use:** Module-level initialization on first use (lazy-init to avoid import-time model loading).

```python
# Source: verified against presidio-analyzer 2.2.362 installed package + official docs
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

NLP_CONFIG = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
}

def build_analyzer(score_threshold: float = 0.4) -> AnalyzerEngine:
    provider = NlpEngineProvider(nlp_configuration=NLP_CONFIG)
    nlp_engine = provider.create_engine()
    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["en"],
        default_score_threshold=score_threshold,
    )
```

**Verified:** `AnalyzerEngine.__init__` signature confirmed: accepts `nlp_engine`, `supported_languages`, `default_score_threshold`. Entity names confirmed in source code.

### Pattern 2: Presidio Entity Name Mapping

**Critical finding:** Presidio uses different entity names than our `EntityType` enum. A mapping layer is required.

```python
# Source: verified against installed predefined_recognizers source code
PRESIDIO_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "EMAIL_ADDRESS": EntityType.EMAIL,      # EmailRecognizer
    "PHONE_NUMBER":  EntityType.PHONE,      # PhoneRecognizer
    "PERSON":        EntityType.PERSON,     # SpacyRecognizer
    "URL":           EntityType.URL,        # UrlRecognizer
    "ORGANIZATION":  EntityType.ORG,        # SpacyRecognizer
}

PHASE2_ENTITIES = list(PRESIDIO_TO_ENTITY_TYPE.keys())
# ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "URL", "ORGANIZATION"]
```

**Warning:** If `entities` param is omitted from `analyze()`, Presidio returns ALL known entities including credit cards, IBANs, US SSNs, etc. Always pass the explicit entity list.

### Pattern 3: Multi-Entity Cell Replacement (Right-to-Left)

**What:** Replace multiple detected entities within a single cell value by applying patches right-to-left to preserve character offsets.

**When to use:** Any cell where Presidio returns more than one RecognizerResult.

```python
# Source: verified with working Python example in research
from presidio_analyzer import RecognizerResult

def apply_replacements(
    text: str,
    results: list[RecognizerResult],
    token_map: dict[str, str],  # original_text -> token
) -> str:
    """Replace entities in text right-to-left to preserve offsets."""
    # Sort descending by start position
    sorted_results = sorted(results, key=lambda r: r.start, reverse=True)
    output = text
    for r in sorted_results:
        original = text[r.start:r.end]
        token = token_map.get(original, original)
        output = output[:r.start] + token + output[r.end:]
    return output
```

### Pattern 4: Fernet Bundle Encryption

**What:** Derive a Fernet key from a password using PBKDF2HMAC-SHA256 (600k iterations). Store salt in bundle header alongside ciphertext.

**PBKDF2 iteration count resolution:** OWASP Password Storage Cheat Sheet (current, verified 2026-04-03) recommends **600,000 iterations** for PBKDF2-HMAC-SHA256. NIST SP 800-132 revision is still in progress. Use OWASP 600,000.

```python
# Source: cryptography docs + verified working in installed cryptography 46.0.6
import base64, json, os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600_000

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_bundle(payload: dict, password: str) -> bytes:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    ciphertext = f.encrypt(json.dumps(payload).encode())
    # Bundle format: 16-byte salt + ciphertext
    return salt + ciphertext

def decrypt_bundle(data: bytes, password: str) -> dict:
    salt, ciphertext = data[:16], data[16:]
    key = derive_key(password, salt)
    f = Fernet(key)
    return json.loads(f.decrypt(ciphertext))
```

**Bundle JSON payload structure (D-08):**
```python
{
    "version": "0.1.0",           # xlcloak.__version__
    "original_filename": "data.xlsx",
    "created_at": "2026-04-03T19:00:00Z",
    "sheets_processed": ["Sheet1", "Sheet2"],
    "token_count": 42,
    "password_mode": "default",    # "default" or "custom"
    "forward_map": {"John Smith": "PERSON_001", ...},
    "reverse_map": {"PERSON_001": "John Smith", ...},
}
```

### Pattern 5: Click CLI Group Structure

**What:** A Click group (`main`) with `sanitize` and `inspect` subcommands. Password sourced from `--password` flag or `XLCLOAK_PASSWORD` env var via `auto_envvar_prefix`.

```python
# Source: Click 8.3.1 docs + auto_envvar_prefix pattern verified
import click

@click.group(context_settings={"auto_envvar_prefix": "XLCLOAK"})
def main() -> None:
    """xlcloak — reversible Excel text sanitization for AI workflows."""

@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--password", default="xlcloak", show_default=True, help="Encryption password")
@click.option("--output", type=click.Path(path_type=Path), default=None)
@click.option("--force", is_flag=True, default=False, help="Overwrite existing output files")
@click.option("--verbose", is_flag=True, default=False)
def sanitize(file: Path, password: str, output: Path | None, force: bool, verbose: bool) -> None:
    ...

@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--verbose", is_flag=True, default=False)
def inspect(file: Path, verbose: bool) -> None:
    ...
```

**Env var mapping:** `--password` maps to `XLCLOAK_PASSWORD` automatically when `auto_envvar_prefix="XLCLOAK"`.

### Pattern 6: Inspect Table Output with rich

**What:** Use `rich.table.Table` to render the per-cell detection preview.

```python
from rich.console import Console
from rich.table import Table

def render_inspect_table(
    results: list[ScanResult], verbose: bool = False
) -> None:
    console = Console()
    table = Table(title="Detected Entities")
    table.add_column("Sheet")
    table.add_column("Cell")
    table.add_column("Type")
    table.add_column("Original (truncated)")
    table.add_column("Would-be Token")
    if verbose:
        table.add_column("Score")
        table.add_column("Method")
    for r in results:
        original_trunc = r.original[:40] + "..." if len(r.original) > 40 else r.original
        from openpyxl.utils import get_column_letter
        col_letter = get_column_letter(r.cell.col)
        cell_ref = f"{col_letter}{r.cell.row}"
        table.add_row(r.cell.sheet_name, cell_ref, r.entity_type.value, original_trunc, r.token)
    console.print(table)
```

### Anti-Patterns to Avoid

- **Passing no entities to analyze():** Returns all Presidio entities including credit card numbers, IBANs, etc. Always pass explicit `PHASE2_ENTITIES` list.
- **presidio-anonymizer for replacement:** AnonymizerEngine replaces whole-cell text, not sub-string spans within a cell. Use the manual right-to-left replacement pattern (Pattern 3) instead.
- **Synchronous model loading at import time:** Loading `en_core_web_lg` takes ~1 second. Use lazy initialization.
- **Storing salt outside the bundle:** Salt must travel with the ciphertext. Store the first 16 bytes of the bundle file as the salt.
- **Using `--force` as a global flag:** It should be a per-command flag; each output path is guarded independently.
- **SpacyRecognizer entity label case:** The SpacyRecognizer exposes `ORGANIZATION` (not `ORG`). Using the wrong key in the entity list will silently skip org detection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email regex detection | Custom email regex | Presidio EmailRecognizer | EmailRecognizer includes TLD validation via tldextract; custom regex misses many edge cases |
| Phone number parsing | Custom phone regex | Presidio PhoneRecognizer + phonenumbers | phonenumbers handles international formats, extensions, and validation natively |
| AES encryption key derivation | Custom PBKDF2 loop | `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC` | FIPS-compliant, handles iteration count correctly, avoids timing attack pitfalls |
| Authenticated encryption | AES-CBC + custom HMAC | Fernet (AES-128-CBC + HMAC-SHA256) | Fernet is authenticated encryption; tampered bundles are rejected before decryption |
| Terminal table rendering | String padding / column math | `rich.table.Table` | Column alignment, word wrap, truncation are all built-in |
| NLP-based NER | Regex for names/orgs | SpacyRecognizer via Presidio | Names and org names are context-dependent; regex cannot capture them reliably |

---

## Common Pitfalls

### Pitfall 1: Presidio Entity Name Mismatch

**What goes wrong:** Code requests `"EMAIL"` or `"ORG"` in the entities list; Presidio silently returns zero results for those types.

**Why it happens:** Presidio uses `EMAIL_ADDRESS`, `PHONE_NUMBER`, and `ORGANIZATION` internally. The `EntityType` enum in `models.py` uses shorter names. There is no error — `analyze()` simply filters to requested entity names.

**How to avoid:** Always use the `PRESIDIO_TO_ENTITY_TYPE` mapping dict. The `PiiDetector` class should own this mapping and never expose raw Presidio entity names to the rest of the codebase.

**Warning signs:** Test with a cell containing a known email address — zero ScanResults returned even though the cell contains `user@example.com`.

### Pitfall 2: Salt Not Persisted with Bundle

**What goes wrong:** Salt is generated per-encrypt but not stored; decrypt fails with an authentication error because the wrong key is derived.

**Why it happens:** PBKDF2 requires the same salt to reproduce the same key. If salt is generated fresh on each call without being stored, it cannot be recovered.

**How to avoid:** Prepend the 16-byte salt to the bundle file bytes: `salt + ciphertext`. On decrypt, read `data[:16]` as salt and `data[16:]` as ciphertext.

### Pitfall 3: Overlapping Presidio Results Corrupt Cell Text

**What goes wrong:** Two entities overlap (e.g., a URL inside a longer string that also matches EMAIL), and left-to-right replacement shifts all subsequent offsets.

**Why it happens:** After replacing at position 5-15, the positions 16+ are now shifted if the replacement has a different length than the original.

**How to avoid:** Sort results by `r.start` descending and replace right-to-left. Positions to the left are unaffected by replacements to the right.

### Pitfall 4: spaCy Model Not Installed

**What goes wrong:** `AnalyzerEngine` raises `OSError: [E050] Can't find model 'en_core_web_lg'` at init time, crashing the CLI before it processes any cells.

**Why it happens:** `en_core_web_lg` is not a PyPI package; it must be installed separately via `python -m spacy download en_core_web_lg` or a direct GitHub wheel URL.

**How to avoid:** Add a pre-flight check in `PiiDetector.__init__` that tests `spacy.util.is_package("en_core_web_lg")` and raises a user-friendly `click.UsageError` with the install command if the model is absent. Document the install step in README.

**Warning signs:** `OSError` with `[E050]` at startup; not at analysis time.

### Pitfall 5: Default Password Mode Not Flagged in Bundle

**What goes wrong:** A user encrypts with the default password "xlcloak", shares the bundle, and the recipient (or a future tool) doesn't know whether a real password was set.

**Why it happens:** Without a marker, the bundle is indistinguishable from a "real" encrypted bundle.

**How to avoid:** Set `"password_mode": "default"` vs `"password_mode": "custom"` in the bundle JSON (D-06). Log a warning in the CLI output when default password is used.

### Pitfall 6: PhoneRecognizer Missing SE Region

**What goes wrong:** Swedish phone numbers not detected in Phase 2.

**Why it happens:** PhoneRecognizer's `DEFAULT_SUPPORTED_REGIONS` is `("US", "UK", "DE", "FE", "IL", "IN", "CA", "BR")`. SE is not included.

**How to avoid:** This is intentional — Swedish phone detection is Phase 4 scope (D-05). Document as a known limitation in the manifest. For Phase 2, add `"SE"` to the PhoneRecognizer's supported_regions when initializing.

Actually: decision D-05 says Phase 2 includes `PHONE` detection. Add `"SE"` to the PhoneRecognizer regions in Phase 2 to ensure Swedish numbers are caught. The decision defers Swedish PII (SSN_SE, ORGNUM_SE) to Phase 4, not phone numbers.

### Pitfall 7: Output Path Collision Without --force

**What goes wrong:** User runs sanitize twice on the same file; second run silently overwrites the bundle, discarding the original token map needed for restore.

**Why it happens:** Overwrite protection not implemented.

**How to avoid:** Before writing any output, check if any of the three output paths (sanitized xlsx, .xlcloak, manifest.txt) exist. If any exists and `--force` is not set, abort with a clear error listing the conflicting paths (D-11).

---

## Code Examples

### Complete Detection Pipeline

```python
# Source: verified against presidio-analyzer 2.2.362 source + AnalyzerEngine signatures
from pathlib import Path
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from xlcloak.models import CellRef, EntityType, ScanResult
from xlcloak.token_engine import TokenRegistry

PRESIDIO_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "EMAIL_ADDRESS": EntityType.EMAIL,
    "PHONE_NUMBER":  EntityType.PHONE,
    "PERSON":        EntityType.PERSON,
    "URL":           EntityType.URL,
    "ORGANIZATION":  EntityType.ORG,
}
PHASE2_ENTITIES = list(PRESIDIO_TO_ENTITY_TYPE.keys())

class PiiDetector:
    def __init__(self, score_threshold: float = 0.4) -> None:
        self._analyzer: AnalyzerEngine | None = None
        self._threshold = score_threshold

    def _get_analyzer(self) -> AnalyzerEngine:
        if self._analyzer is None:
            provider = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            })
            self._analyzer = AnalyzerEngine(
                nlp_engine=provider.create_engine(),
                supported_languages=["en"],
                default_score_threshold=self._threshold,
            )
        return self._analyzer

    def detect(
        self, cell: CellRef, registry: TokenRegistry
    ) -> list[ScanResult]:
        assert cell.value is not None
        analyzer = self._get_analyzer()
        presidio_results = analyzer.analyze(
            text=cell.value,
            language="en",
            entities=PHASE2_ENTITIES,
            score_threshold=self._threshold,
        )
        # Sort descending for right-to-left replacement
        presidio_results.sort(key=lambda r: r.start, reverse=True)
        scan_results: list[ScanResult] = []
        for pr in presidio_results:
            entity_type = PRESIDIO_TO_ENTITY_TYPE[pr.entity_type]
            original = cell.value[pr.start:pr.end]
            token = registry.get_or_create(original, entity_type)
            scan_results.append(ScanResult(
                cell=cell,
                entity_type=entity_type,
                original=original,
                token=token,
            ))
        return scan_results
```

### Output Path Derivation (D-10, D-12)

```python
def derive_output_paths(
    input_path: Path, output_override: Path | None = None
) -> tuple[Path, Path, Path]:
    """Return (sanitized_xlsx, bundle_xlcloak, manifest_txt)."""
    if output_override:
        base = output_override.parent / output_override.stem
    else:
        base = input_path.parent / input_path.stem
    sanitized = base.with_name(base.name + "_sanitized").with_suffix(".xlsx")
    bundle = base.with_suffix(".xlcloak")
    manifest = base.with_name(base.name + "_manifest").with_suffix(".txt")
    return sanitized, bundle, manifest
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | 3.12.3 | — |
| presidio-analyzer | Detection pipeline | ✓ | 2.2.362 | — |
| spaCy | NER (PERSON, ORG) | ✓ | 3.8.14 | — |
| en_core_web_lg | PERSON/ORG NER | ✗ | — | en_core_web_sm (lower recall), or pattern-only mode |
| cryptography | Fernet bundle | ✓ | 46.0.6 | — |
| click | CLI | ✓ | 8.3.1 | — |
| rich | inspect table output | ✓ | 14.3.3 (transitive) | plain-text table |
| uv | Build/publish workflow | ✓ | 0.11.3 | pip + build |
| hatch/hatchling | PyPI build | ✗ | — | `uv build` uses hatchling as build backend without hatch CLI |

**Missing dependencies with no fallback:**
- `en_core_web_lg`: Required for PERSON and ORG NER (DET-03 and ORG part of D-04). Plan must include a Wave 0 step to download the model. CI must also run this step.

**Missing dependencies with fallback:**
- `hatch` CLI: Not needed. `uv build` invokes the hatchling build backend directly.
- `rich` (transitive): Currently installed as transitive dep of typer. Add as explicit direct dependency to make it stable.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (dev group in pyproject.toml) |
| Config file | `[tool.pytest.ini_options]` in pyproject.toml |
| Quick run command | `uv run pytest -x -q` |
| Full suite command | `uv run pytest --cov=xlcloak --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-01 | Email addresses in cell text are detected and tokenized | unit | `uv run pytest tests/test_detector.py::test_email_detection -x` | ❌ Wave 0 |
| DET-02 | Phone numbers in cell text are detected and tokenized | unit | `uv run pytest tests/test_detector.py::test_phone_detection -x` | ❌ Wave 0 |
| DET-03 | Person names via NER detected and tokenized | unit (requires spaCy model) | `uv run pytest tests/test_detector.py::test_person_detection -x` | ❌ Wave 0 |
| DET-04 | URLs in cell text are detected and tokenized | unit | `uv run pytest tests/test_detector.py::test_url_detection -x` | ❌ Wave 0 |
| DET-01–04 | Multi-entity cells replaced inline, right-to-left | unit | `uv run pytest tests/test_detector.py::test_multi_entity_cell -x` | ❌ Wave 0 |
| BUN-01 | Bundle encrypts token map; decrypt round-trips correctly | unit | `uv run pytest tests/test_bundle.py::test_encrypt_decrypt_roundtrip -x` | ❌ Wave 0 |
| BUN-01 | Default password mode marked in bundle header | unit | `uv run pytest tests/test_bundle.py::test_default_password_mode_flag -x` | ❌ Wave 0 |
| BUN-02 | Manifest file written with correct entity counts | unit | `uv run pytest tests/test_sanitizer.py::test_manifest_written -x` | ❌ Wave 0 |
| CLI-01 | `xlcloak sanitize simple.xlsx` produces three output files | integration | `uv run pytest tests/test_cli.py::test_sanitize_produces_outputs -x` | ❌ Wave 0 |
| CLI-01 | Overwrite protection blocks second run without --force | integration | `uv run pytest tests/test_cli.py::test_sanitize_overwrite_protection -x` | ❌ Wave 0 |
| CLI-03 | `xlcloak inspect simple.xlsx` prints table, writes no files | integration | `uv run pytest tests/test_cli.py::test_inspect_no_output_files -x` | ❌ Wave 0 |
| CLI-06 | `--output` redirects sanitized file; bundle/manifest follow | integration | `uv run pytest tests/test_cli.py::test_sanitize_output_flag -x` | ❌ Wave 0 |

**Note on DET-03:** Tests requiring PERSON/ORG NER need `en_core_web_lg` installed. Mark with `@pytest.mark.skipif(not spacy.util.is_package("en_core_web_lg"), reason="spaCy model not installed")` or use a smaller `en_core_web_sm` model in CI.

### Sampling Rate

- **Per task commit:** `uv run pytest -x -q`
- **Per wave merge:** `uv run pytest --cov=xlcloak --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_detector.py` — covers DET-01, DET-02, DET-03, DET-04
- [ ] `tests/test_bundle.py` — covers BUN-01 encrypt/decrypt round-trip and password mode flag
- [ ] `tests/test_sanitizer.py` — covers Sanitizer orchestrator and BUN-02 manifest file
- [ ] `tests/test_cli.py` — covers CLI-01, CLI-03, CLI-06 via CliRunner
- [ ] spaCy model: `uv run python -m spacy download en_core_web_lg` — required for DET-03

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `check_label_groups` in SpacyRecognizer | `NerModelConfiguration` in NlpEngineProvider | Presidio ~2.2.x | Old parameter is deprecated; use NlpEngineProvider config |
| presidio-anonymizer AnonymizerEngine for text | Manual inline replacement with sorted RecognizerResults | N/A — deliberate choice | AnonymizerEngine replaces whole strings; inline replacement preserves surrounding cell context |
| NIST SP 800-132 minimum (1,000 iterations) | OWASP 600,000 for PBKDF2-HMAC-SHA256 | OWASP guidance updated 2023 | Must use 600,000; old 1,000 is insecure against modern hardware |

---

## Open Questions

1. **spaCy model in CI (GitHub Actions)**
   - What we know: `en_core_web_lg` is not a PyPI dep; must be downloaded separately.
   - What's unclear: CI workflow file doesn't exist yet — needs to be created in a future phase.
   - Recommendation: Phase 2 plan should include a note that the `python -m spacy download en_core_web_lg` step must be added when the CI workflow is created. For now, document in README.

2. **PhoneRecognizer regions for Phase 2**
   - What we know: `DEFAULT_SUPPORTED_REGIONS` excludes SE. The decision (D-05) defers Swedish PII (SSN_SE, ORGNUM_SE) to Phase 4 but doesn't explicitly say whether Swedish phone numbers are in Phase 2 or Phase 4.
   - What's unclear: Should Phase 2 PhoneRecognizer detect Swedish numbers?
   - Recommendation: Add `"SE"` to supported_regions in Phase 2. Swedish phone numbers are international PII even without Swedish SSN support. This doesn't add complexity.

3. **rich as explicit dependency**
   - What we know: rich 14.3.3 is currently a transitive dependency (via typer → rich). It is not listed in pyproject.toml.
   - What's unclear: Whether typer will always be a transitive dep in the future.
   - Recommendation: Add `rich>=12.0.0` as an explicit dependency in pyproject.toml to prevent future breakage.

---

## Sources

### Primary (HIGH confidence)

- Installed presidio-analyzer 2.2.362 source code — entity names, AnalyzerEngine signatures, SpacyRecognizer ENTITIES list, PhoneRecognizer supported regions (direct file inspection)
- Installed cryptography 46.0.6 — Fernet + PBKDF2HMAC API (verified working in test)
- Installed click 8.3.1 — auto_envvar_prefix, CliRunner patterns
- Installed spaCy 3.8.14 — `spacy.util.is_package()` API
- `NerModelConfiguration` defaults — verified with `NerModelConfiguration()` instantiation showing `model_to_presidio_entity_mapping`
- GitHub release HTTP 302 check — en_core_web_lg-3.8.0 wheel confirmed at `https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl`

### Secondary (MEDIUM confidence)

- OWASP Password Storage Cheat Sheet (https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — 600,000 iterations for PBKDF2-HMAC-SHA256
- Microsoft Presidio official docs (https://microsoft.github.io/presidio/analyzer/customizing_nlp_models/) — NlpEngineProvider config structure verified against installed package
- Presidio GitHub test file (https://github.com/microsoft/presidio/blob/main/presidio-analyzer/tests/test_analyzer_engine.py) — analyze() parameter list cross-referenced with introspection

### Tertiary (LOW confidence)

- NIST SP 800-132 revision status — revision not yet published; original recommendation of 1,000 iterations is clearly outdated; deferring to OWASP 600,000

---

## Metadata

**Confidence breakdown:**

- Presidio API: HIGH — all signatures verified via introspection of installed 2.2.362 package
- Entity name mapping: HIGH — verified directly in predefined_recognizers source code files
- Fernet/PBKDF2 pattern: HIGH — verified working in installed cryptography 46.0.6
- PBKDF2 iteration count: HIGH — OWASP 600,000 verified from official cheat sheet
- spaCy model version: HIGH — en_core_web_lg-3.8.0 GitHub wheel confirmed 302 response
- Click env var pattern: HIGH — confirmed from click 8.3.1 docs
- rich availability: HIGH — confirmed installed as transitive dep

**Research date:** 2026-04-03
**Valid until:** 2026-07-03 (stable libraries; Presidio moves slowly)
