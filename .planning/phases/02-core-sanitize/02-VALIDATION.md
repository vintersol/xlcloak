---
phase: 2
slug: core-sanitize
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DET-01,DET-02,DET-03,DET-04 | unit | `uv run pytest tests/test_detector.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | BUN-01,BUN-02 | unit | `uv run pytest tests/test_bundle.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | CLI-01,CLI-03,CLI-06 | integration | `uv run pytest tests/test_cli.py -x -q` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | CLI-08,CLI-09 | integration | `uv run pip install -e . && xlcloak --help` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_detector.py` — stubs for DET-01 through DET-04 (email, phone, person, URL detection)
- [ ] `tests/test_bundle.py` — stubs for BUN-01, BUN-02 (encrypted bundle, manifest)
- [ ] `tests/test_cli.py` — stubs for CLI-01, CLI-03, CLI-06 (sanitize, inspect, flags)
- [ ] `tests/conftest.py` — extend existing with detector/bundle fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-platform install | CLI-09 | Requires macOS/Windows/Linux environments | Install via `pip install xlcloak` on each OS, run `xlcloak --version` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
