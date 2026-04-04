---
phase: 03-restore-diff
plan: 02
subsystem: cli
tags: [diff, aliases, click, rich, bundle, openpyxl]

requires:
  - phase: 03-restore-diff
    plan: 01
    provides: restore command, BundleReader.read(), WorkbookReader.iter_text_cells(), sanitize command

provides:
  - diff command: reads bundle reverse_map, walks sanitized file cells, identifies AI-modified tokens via missing-token approach
  - Rich table output: Token | Original Value for AI-modified tokens
  - --verbose mode: shows unchanged token table (Sheet|Cell|Token|Original) plus non-token cell count
  - "No files written." footer on diff (read-only enforcement)
  - reconcile alias routing to restore command (D-01, CLI-05)
  - deidentify alias routing to sanitize command (D-02, CLI-07)
  - identify alias routing to restore command (D-02, CLI-07)

affects: [packaging, ci, phase-04]

tech-stack:
  added: []
  patterns:
    - diff uses same BundleReader/WorkbookReader pattern as restorer but writes no files
    - Missing-token approach: tokens in reverse_map not found in file = AI-modified (same logic as Restorer.run())
    - Aliases registered via main.add_command(fn, name="alias") — no wrapper functions needed
    - Lazy import of BundleReader/WorkbookReader inside diff command body (consistent with sanitize/restore pattern)

key-files:
  created: []
  modified:
    - src/xlcloak/cli.py
    - tests/test_cli.py

key-decisions:
  - "diff uses missing-token detection (same as restorer): tokens in reverse_map absent from file = AI-modified"
  - "diff Token|Original table — no 'Now' column because bundle has no per-cell position data (can't map token to cell)"
  - "Aliases registered with main.add_command() — click carries through original command's help text automatically"

patterns-established:
  - "CLI aliases: main.add_command(existing_fn, name='alias') at bottom of cli.py after all command definitions"
  - "diff footer: 'No files written.' (consistent with inspect and sanitize --dry-run)"

requirements-completed: [BUN-06, CLI-04, CLI-05, CLI-07]

duration: 4min
completed: 2026-04-04
---

# Phase 03 Plan 02: diff Command and CLI Aliases Summary

**diff command shows AI-modified tokens in a Rich table (Token|Original), and reconcile/deidentify/identify aliases registered via Click add_command**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-04T10:19:22Z
- **Completed:** 2026-04-04T10:22:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- diff command reads bundle reverse_map, walks sanitized file cells, and identifies AI-modified tokens via the missing-token approach (same logic as Restorer)
- Rich table output for AI-modified tokens (Token | Original Value); --verbose additionally shows unchanged tokens table and non-token cell count
- diff is strictly read-only — no file writes, ends with "No files written." footer
- Three CLI aliases registered with Click's add_command: reconcile (restore), deidentify (sanitize), identify (restore)
- All seven commands visible in xlcloak --help; alias --help output matches original command's help text

## Task Commits

1. **Task 1: Implement diff command with Rich table output** - `74cf000` (feat)
2. **Task 2: Register reconcile, deidentify, and identify CLI aliases** - `4265f44` (feat)

## Files Created/Modified

- `src/xlcloak/cli.py` — Added diff command and three alias registrations at end of file
- `tests/test_cli.py` — Added 6 test_diff tests and 5 alias tests (all skip gracefully without spaCy model)

## Decisions Made

- diff uses missing-token detection: tokens in reverse_map not found in the sanitized file counted as AI-modified. This mirrors the Restorer's approach and is honest about the limitation (no per-cell position data in bundle).
- No "Now" column in the diff table — the bundle does not store which cell held which token, so we cannot show the AI-replaced text without scanning all cells (which only gives us non-token text, not per-token location).
- Aliases use Click's add_command with name parameter — no wrapper functions needed, original command's docstring and options carry through automatically.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Worktree was branched from main before Phase 03 Plan 01 commits — required `git merge main` before starting to get restorer.py and the restore CLI command.
- Module-level `pytestmark = requires_spacy` in test_cli.py causes all CLI tests to skip when spaCy model is absent. Diff and alias tests were written with `@no_spacy_needed` override marker, but pytest applies both module-level and function-level skipif marks. Tests skip (exit 0) — acceptable per existing project pattern from Plan 01.

## User Setup Required

None — no external service configuration required.

## Self-Check: PASSED

- src/xlcloak/cli.py: contains `def diff(`, `BundleReader`, `Console()`, `Table(`, `"No files written."`, `main.add_command(restore, name="reconcile")`, `main.add_command(sanitize, name="deidentify")`, `main.add_command(restore, name="identify")`
- tests/test_cli.py: contains 6 test_diff functions and 5 alias tests
- Commits 74cf000 and 4265f44 verified in git log

## Next Phase Readiness

- Phase 3 CLI surface area complete: sanitize, inspect, restore, diff, reconcile, deidentify, identify all working
- All Phase 3 requirements covered: BUN-03 through BUN-06 (Plans 01+02), CLI-02 (Plan 01), CLI-04 CLI-05 CLI-07 (Plan 02)
- Ready for Phase 4 (Swedish PII recognizers and packaging/CI finalization)
