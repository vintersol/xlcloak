# Domain Pitfalls: Reversible Excel Text Sanitization CLI

**Domain:** PII detection + reversible text sanitization + Excel I/O + CLI tooling
**Researched:** 2026-04-03
**Confidence note:** External search tools unavailable. All findings from training-data knowledge of Presidio, openpyxl, Fernet, and Excel internals (knowledge cutoff Aug 2025). Confidence levels reflect this. Flag all HIGH-confidence items for live-docs verification before implementation.

---

## Critical Pitfalls

Mistakes in this category cause rewrites, data loss, or silent corruption.

---

### Pitfall 1: Token Instability Across Sanitize Runs

**What goes wrong:** The same source value produces different tokens on different runs. When the AI-modified sanitized file is restored, the mapping table no longer matches what was actually in the file — restore silently maps nothing, or worse, maps wrong cells.

**Why it happens:** Token generation uses random IDs (uuid4, random integer) without seeding or deterministic hashing. Developer assumes "same run = same tokens" and never tests multi-run stability.

**Consequences:** The round-trip is broken. Reconciliation compares tokens that no longer correspond to the correct originals. Users cannot re-sanitize a partially-restored file. Trust in the tool collapses.

**Prevention:**
- Tokens MUST be derived deterministically: `HMAC(secret_salt, canonical(original_value))` or a seeded counter persisted in the bundle.
- The salt must be per-bundle (stored in bundle), not global. This prevents cross-bundle token collisions while ensuring intra-run stability.
- Test: sanitize the same file twice with the same salt; assert token maps are identical.

**Warning signs:**
- Token generation code contains `uuid4()`, `random.randint()`, or `secrets.token_hex()` without a stable seed or persistent counter.
- No test asserting same-input → same-token across two independent sanitize invocations.

**Phase:** Foundation (token engine). Must be locked before any restore logic is written.

---

### Pitfall 2: openpyxl Round-Trip Data Loss on Rich Content

**What goes wrong:** Reading and re-writing an `.xlsx` file with openpyxl silently drops or corrupts content that openpyxl does not model: sparklines, data validation rules, conditional formatting expressions with external references, VBA remnants in `.xlsx`, custom XML parts, legacy drawing objects, and threaded comments (the newer comment type distinct from legacy notes).

**Why it happens:** openpyxl reads what it understands; on write it serialises only what it modelled. Unknown XML namespaces are dropped. Developer tests on simple files, ships, then a real-world enterprise workbook loses its conditional formatting or data validation.

**Consequences:** The "sanitized" file is a functionally degraded copy. Users notice missing features; they blame the tool even if the PII was correctly handled. Worse, if restore writes back on top of the degraded sanitized file, the originals are recovered but the structural damage remains.

**Prevention:**
- In V1: adopt a "minimum-touch" write strategy. Read cells + styles; write back only what was changed. Keep original XML parts untouched where possible.
- Alternatively: use a copy-then-patch approach — `shutil.copy2` the original, open the copy with openpyxl, modify only target cells, save. This preserves XML openpyxl doesn't model.
- Enumerate known-lossy surfaces in the manifest as warnings (this is already scoped into requirements, but implementation must actually enumerate them reliably).
- Test against a workbook with: data validation, conditional formatting, sparklines, a table (`<tableFile>`), threaded comments, and a chart. Assert these survive a no-op sanitize (sanitize a file with no PII, verify output is structurally equivalent).

**Warning signs:**
- Test suite uses only freshly-created openpyxl workbooks rather than real `.xlsx` files downloaded from Excel or Google Sheets.
- No "no-op round-trip" test for complex workbooks.
- `wb.save()` called on the loaded workbook without any structural preservation strategy.

**Phase:** Excel I/O layer (early). Must be validated before token replacement logic is layered on top.

---

### Pitfall 3: NER Confidence Threshold Too Low or Too High

**What goes wrong:**
- Too low: Every product name, city abbreviation, column label ("Name", "ID"), and common noun gets a token. The sanitized file is unreadable noise; AI tools can't interpret it.
- Too high: Real names and org names in ambiguous context (e.g., "Anna" as a column value vs. "Anna Lindqvist" as a full name) are missed. The tool gives false confidence.

**Why it happens:** Presidio's default `score_threshold` (0.35–0.5 depending on recognizer) is tuned for document-level text, not short cell values. Cells have minimal context — a name in isolation triggers nothing; a full name in a "Contact" column should always trigger.

**Consequences:**
- Too low: User complains the tool broke their spreadsheet's readability.
- Too high: The tool misses the PII it was built to catch. Users discover this and stop trusting it.

**Prevention:**
- Implement per-entity-type thresholds, not one global threshold.
- Use column header context to boost confidence: if the header matches "name", "contact", "person", "email", etc. — lower the threshold for that column.
- Test with adversarial inputs: single-word values, numeric-looking strings ("123456"), values that are valid PII only in Swedish context (personnummer).
- Ship a default configuration with documented threshold choices and rationale.

**Warning signs:**
- Single `score_threshold` global constant in the codebase.
- No column-header-aware scoring logic.
- Threshold chosen by vibes rather than recall/precision measurement on a test set.

**Phase:** PII detection engine. Header-context boosting must be designed upfront, not bolted on later.

---

### Pitfall 4: Presidio spaCy Model Not Installed / Wrong Language

**What goes wrong:** Presidio's NLP engine relies on a spaCy language model (`en_core_web_lg` or similar). This model is not installed by default — it requires a separate `python -m spacy download` step. Swedish NER requires `sv_core_news_lg` or equivalent. On a fresh `pip install xlcloak`, the tool crashes on first use with an obscure spaCy error.

**Why it happens:** The spaCy model is too large for a PyPI wheel dependency and ships separately. Developers test in their own environment where the model is already present.

**Consequences:** Every new install fails on first use. Critical blocker for user adoption; the error message is opaque to non-Python users.

**Prevention:**
- At startup, detect missing models and emit a clear diagnostic: "xlcloak requires the spaCy English model. Run: `python -m spacy download en_core_web_lg`" — or better, auto-download if not present.
- Evaluate `spacy-model-packages` (spaCy's official pip-installable model packages, e.g., `en-core-web-lg`) as a proper pip dependency that installs the model automatically. This is supported since spaCy 3.x.
- CI must test from a clean environment (no pre-installed models).

**Warning signs:**
- `spacy download` not mentioned in installation docs.
- CI runs against an environment with pre-warmed pip caches that already have the model.
- No startup model-check code.

**Phase:** Packaging / CLI bootstrap. Must be solved before first PyPI release.

---

### Pitfall 5: Bundle Decryption Key Derived Incorrectly (Fernet + PBKDF2 Misuse)

**What goes wrong:** Fernet requires a 32-byte URL-safe base64-encoded key. If the developer passes a raw password string directly as the key, or uses a weak KDF (MD5, SHA256 without iterations), the encryption is broken. If the salt is hardcoded or not stored in the bundle, the bundle is non-portable (can only be decrypted on the same machine).

**Why it happens:** Fernet's API accepts any 32-byte base64 string — it does not validate that the key came from a proper KDF. Mistakes are silent.

**Consequences:**
- Hardcoded salt: bundle can only be decrypted on the machine that created it (or when salt is re-derived the same way). Portability breaks.
- Weak KDF: key is crackable; the "encryption" provides no real protection.
- Wrong key format: cryptography library raises a confusing error at decrypt time, not at encrypt time.

**Prevention:**
- Use `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC` with SHA-256, minimum 480,000 iterations (OWASP 2023 recommendation), random 16-byte salt stored in bundle header.
- Store KDF parameters (algorithm, iterations, salt) in bundle alongside ciphertext so future versions can upgrade params without breaking old bundles.
- Write a unit test: encrypt with password A, attempt decrypt with password B, assert `InvalidToken` is raised. Encrypt, move bundle to different process/machine simulation, decrypt successfully.

**Warning signs:**
- `hashlib.sha256(password).digest()` used as Fernet key.
- `os.urandom` call for salt is absent or salt is a constant.
- KDF parameters not stored in bundle.

**Phase:** Bundle encryption. Must be reviewed before any alpha release. Consider a security-focused code review of this component specifically.

---

### Pitfall 6: Partial Token Replacement Within a Cell (Substring Collision)

**What goes wrong:** A cell contains "Contact: Anna Lindqvist, +46701234567". The sanitizer correctly detects two entities. It replaces them in sequence using string offsets. If entity offsets overlap (Presidio can return overlapping results), or if the replacement of entity 1 shifts the string length and entity 2's offset is now wrong, the second replacement corrupts the cell.

**Why it happens:** String replacement by character offset assumes the string is not mutated between replacements. Sequential in-place replacement breaks this assumption.

**Consequences:** Cells with multiple PII entities are garbled. The garbling may be subtle (only the second entity is wrong) and hard to detect without test cases that have exactly two entities per cell.

**Prevention:**
- Always process replacements right-to-left by start offset, so earlier replacements don't shift later offsets.
- Or: collect all replacements first, sort descending by start position, apply in a single pass.
- Presidio has built-in overlap handling — use `ConflictResolutionStrategy` (raise or merge) to resolve overlapping results before applying. Do not assume Presidio results are non-overlapping.
- Test: cell with two distinct PII values, cell with overlapping detections, cell with PII at position 0 and at end.

**Warning signs:**
- Replacement loop iterates forward through results without re-indexing.
- No test for a cell containing two or more PII entities.

**Phase:** Token replacement engine. Foundational correctness issue.

---

### Pitfall 7: Cell Type Handling — Numbers Stored as Text, and Vice Versa

**What goes wrong:** Swedish personnummer (`YYYYMMDD-XXXX`) and org-nummer (`XXXXXX-XXXX`) can be stored as numbers if a user typed them into Excel without a leading apostrophe. When stored as numbers, openpyxl returns an `int` or `float`, not a string — and string-based regex patterns silently never match.

**Conversely:** A column of amounts stored as strings ("1,234.56") will be read as strings. If token replacement converts a numeric-looking string, restore must write back the original type exactly.

**Why it happens:** Excel has a weak type system. openpyxl faithfully returns the stored type. Developers test on `cell.value` as strings and miss the integer case.

**Consequences:**
- Personnummer/org-nummer stored as integers never get detected.
- Restored values have wrong types (e.g., string "12345" instead of integer 12345), breaking formulas that reference those cells.

**Prevention:**
- Always stringify cell values for pattern matching: `str(cell.value)`.
- Store original cell value type in the bundle (not just the value). On restore, cast back to original type.
- Test: personnummer entered as number, personnummer entered as text (with apostrophe), amounts as strings. Verify detection in all cases, verify type-exact restore.

**Warning signs:**
- PII detection receives `cell.value` directly without `str()` conversion.
- Bundle stores only `{"original": "550101-1234"}` without type metadata.

**Phase:** Cell reading and bundle schema. Design the bundle schema with type metadata from the start — retrofitting is painful.

---

## Moderate Pitfalls

---

### Pitfall 8: Merged Cells Cause Incorrect Iteration

**What goes wrong:** openpyxl's `ws.iter_rows()` returns `None` for cells that are part of a merge range but are not the top-left anchor. If the sanitizer processes these cells (which have `cell.value == None`) or tries to write tokens to them, it either skips silently or raises on write.

**Prevention:**
- Before processing, build a set of merge-range member cells (not anchors). Skip them during detection and replacement.
- On restore, only write to non-merged or anchor cells. openpyxl handles propagation.
- Test: workbook with merged cells containing PII in the anchor cell. Assert detection finds it, token is written to anchor only, restore is correct.

**Phase:** Cell iteration / Excel I/O layer.

---

### Pitfall 9: Swedish PII Patterns — Checksum Validation vs. Pattern Match

**What goes wrong:** Swedish personnummer has a Luhn-variant checksum. A naive regex matches any 10-digit string in the right format, producing many false positives on order numbers, ERP IDs, invoice numbers, and account codes that happen to look like personnummer.

**Why it happens:** Regex alone cannot validate the checksum. Developers implement the regex first, see "good enough" results, ship without checksum validation.

**Consequences:** High false-positive rate on financial/ERP spreadsheets, which are the most likely use case. Users see their invoice IDs tokenized. Trust drops.

**Prevention:**
- Implement Luhn checksum validation in the personnummer recognizer — only flag values that pass the checksum.
- Same principle applies to org-nummer (different checksum algorithm).
- Treat "looks like personnummer but fails checksum" as a low-confidence match — only flag if column header provides strong context.
- Test with real-looking but invalid personnummer (wrong checksum digit) — assert NOT detected.

**Warning signs:**
- Personnummer recognizer contains only a regex, no checksum logic.
- No test case with a value that matches the regex but fails the checksum.

**Phase:** Custom recognizer implementation.

---

### Pitfall 10: Manifest Divergence from Actual Transformations

**What goes wrong:** The manifest documents what was "expected" to be found (entities detected), but not what was actually written. If an error occurs mid-write (disk full, openpyxl exception), the manifest says 47 tokens were applied but only 30 were written to disk.

**Prevention:**
- Write the manifest only after the sanitized file has been fully written and fsynced.
- Include a hash of the sanitized output file in the manifest so integrity can be verified at restore time.
- On restore, verify manifest hash against the file being restored; warn if mismatch.

**Phase:** File write / manifest generation.

---

### Pitfall 11: Restore Reconciliation "Unchanged" Detection Is Wrong

**What goes wrong:** The reconciliation logic needs to know if a cell was modified by the AI agent after sanitization. The naive approach is `token_in_file == token_in_bundle`. But what if the AI replaced `<PERSON_1>` with `<person_1>` (case change), or added trailing whitespace, or the cell was reformatted by Excel on open/save? The reconciliation concludes the cell was "changed" and refuses to restore — but the original PII is permanently lost.

**Prevention:**
- Canonicalize token comparison: strip whitespace, normalize case for token matching.
- Document what counts as "unchanged" vs. "modified" in the manifest spec and test it explicitly.
- For cells the AI did modify meaningfully, do NOT restore (correct behavior) — but emit a clear log entry so users can manually handle those cells.

**Phase:** Restore/reconciliation engine.

---

### Pitfall 12: Multi-Line Cell Content Breaks NER Context

**What goes wrong:** Excel cells can contain newlines (`\n` or `\r\n`). Presidio's NLP pipeline may not handle multi-line strings as expected — some spaCy pipelines split on newlines, breaking entity spans that cross the break.

**Prevention:**
- Sanitize cell text line-by-line if multi-line, then reassemble with original line breaks.
- Or: replace `\n` with a sentinel, run NER, restore newlines. Either way, test multi-line cells explicitly.
- Test: a cell with "First: John\nLast: Smith" — assert both names are detected.

**Phase:** PII detection / text preprocessing.

---

## Minor Pitfalls

---

### Pitfall 13: CLI Exit Codes Not Standardized

**What goes wrong:** Errors (wrong password, file not found, detection failure) exit with code 0. Shell scripts using `xlcloak` in pipelines silently continue on failure.

**Prevention:** Use distinct non-zero exit codes: 1 = usage error, 2 = file I/O error, 3 = decryption failure (wrong password), 4 = reconciliation conflict. Document in `--help`.

**Phase:** CLI surface.

---

### Pitfall 14: Large Files Loaded Entirely into Memory

**What goes wrong:** openpyxl's standard mode loads the entire workbook into memory. A 50MB enterprise xlsx with 200K rows will cause OOM on modest machines.

**Prevention:** For V1, document a practical row limit (e.g., "tested up to 50K rows"). Detect large files and warn. V2 roadmap: openpyxl read-only mode for detection, write with streaming. Do not architect V1 assuming you'll always have memory — make the cell iteration layer swappable.

**Phase:** Architecture (cell iteration abstraction).

---

### Pitfall 15: Bundle File Naming Collision

**What goes wrong:** User sanitizes `report.xlsx` → `report_sanitized.xlsx` + `report.xlcloak`. User sanitizes again → overwrites the bundle silently. Original mapping is gone. Restore is now broken.

**Prevention:** Bundle filename should include a timestamp or content hash suffix. Or: before overwrite, check if bundle exists and prompt/fail. At minimum, never silently overwrite a bundle.

**Phase:** CLI file I/O.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Token engine | Token instability (Pitfall 1) | Deterministic HMAC-based tokens from day 1 |
| Token engine | Substring offset collision (Pitfall 6) | Right-to-left replacement pass |
| Excel I/O | openpyxl round-trip loss (Pitfall 2) | Copy-then-patch strategy; no-op round-trip test |
| Excel I/O | Merged cell iteration (Pitfall 8) | Skip non-anchor merged cells |
| Excel I/O | Type preservation (Pitfall 7) | Store and restore original cell type in bundle |
| PII detection | Threshold tuning (Pitfall 3) | Per-entity, header-context-aware thresholds |
| PII detection | spaCy model absent (Pitfall 4) | Startup model check; pip-installable model package |
| PII detection | Swedish checksum (Pitfall 9) | Luhn validation in custom recognizer |
| PII detection | Multi-line cells (Pitfall 12) | Line-by-line NER with reassembly |
| Bundle encryption | Fernet key derivation (Pitfall 5) | PBKDF2HMAC, random salt, store KDF params in bundle |
| Restore engine | Reconciliation correctness (Pitfall 11) | Canonicalize token comparison; clear conflict logs |
| Manifest | Manifest/file divergence (Pitfall 10) | Write manifest after fsync; include file hash |
| CLI | Exit codes (Pitfall 13) | Standardize exit codes in first CLI milestone |
| CLI | Bundle overwrite (Pitfall 15) | Timestamp/hash suffix or existence check |
| Packaging | Large file OOM (Pitfall 14) | Document limits; swappable cell iteration layer |

---

## Confidence Assessment

| Pitfall Area | Confidence | Basis |
|---|---|---|
| Token stability design | HIGH | Deterministic token generation is a well-established requirement in any reversible anonymization system |
| openpyxl round-trip data loss | HIGH | openpyxl's documented limitations; widely reported in community; sparklines/threaded comments known lossy |
| Presidio threshold behavior | MEDIUM | Based on Presidio architecture knowledge; exact default values need live-docs verification |
| spaCy model installation | HIGH | pip-installable model packages (e.g., `en-core-web-lg`) are documented in spaCy 3.x; still verify current install mechanism |
| Fernet/PBKDF2 usage | HIGH | cryptography library API is stable and well-documented; OWASP iteration count should be verified against current guidance |
| Substring offset replacement | HIGH | Classic string mutation bug; language-agnostic, well-understood |
| Excel cell type handling | HIGH | openpyxl returns native Python types for numeric cells; well-documented behavior |
| Swedish checksum validation | HIGH | Personnummer Luhn checksum is a documented algorithm; org-nummer has a separate checksum — both should be verified against Skatteverket spec |
| Merged cell iteration | HIGH | openpyxl merged cell behavior is documented and well-known |
| Multi-line NER | MEDIUM | spaCy pipeline behavior on newline-containing strings needs verification against current spaCy version |

---

## Sources

Note: External search tools were unavailable during this research session. Findings are based on training-data knowledge (cutoff Aug 2025) of:

- Microsoft Presidio documentation and architecture (presidio.microsoft.com)
- openpyxl documentation (openpyxl.readthedocs.io)
- spaCy documentation and model packaging (spacy.io)
- Python `cryptography` library Fernet/PBKDF2 documentation
- OWASP Password Storage Cheat Sheet (PBKDF2 iteration counts)
- Skatteverket specification for personnummer and org-nummer checksum algorithms

**Validation priority before implementation:**
1. Verify current spaCy pip-installable model package names (`en-core-web-lg`, `sv-core-news-lg`) — these change with spaCy major versions.
2. Verify PBKDF2 iteration count against current OWASP guidance (was 600,000 for SHA-256 as of late 2023).
3. Verify openpyxl's handling of threaded comments vs. legacy notes in the current release.
4. Verify Presidio's `ConflictResolutionStrategy` API — confirm it exists and is accessible at the `AnalyzerEngine` level.
