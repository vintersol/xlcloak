---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | TOK-01 | unit | `uv run pytest tests/test_token_engine.py -k determinism` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | TOK-02 | unit | `uv run pytest tests/test_token_engine.py -k prefix` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | TOK-03 | unit | `uv run pytest tests/test_token_engine.py -k shape` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | DET-09 | integration | `uv run pytest tests/test_excel_io.py -k surface` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | DET-09 | integration | `uv run pytest tests/test_excel_io.py -k roundtrip` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | TEST-01 | integration | `uv run pytest tests/test_fixtures.py` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | TEST-02 | integration | `uv run pytest tests/test_fixtures.py -k simple` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 2 | TEST-03 | integration | `uv run pytest tests/test_fixtures.py -k medium` | ❌ W0 | ⬜ pending |
| 01-03-04 | 03 | 2 | TEST-04 | integration | `uv run pytest tests/test_fixtures.py -k hard` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — project metadata, dependencies, pytest config
- [ ] `src/xlcloak/__init__.py` — package init
- [ ] `tests/conftest.py` — shared fixtures, tmp_path helpers
- [ ] `uv sync` — install dependencies and dev tools

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
