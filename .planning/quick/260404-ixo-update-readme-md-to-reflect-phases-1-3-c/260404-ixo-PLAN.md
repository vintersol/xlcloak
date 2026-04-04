---
phase: quick
plan: 260404-ixo
type: execute
wave: 1
depends_on: []
files_modified: [README.md]
autonomous: true
requirements: []
must_haves:
  truths:
    - "README documents all five primary commands: inspect, sanitize, restore, diff, and their aliases"
    - "README shows correct flags for each command"
    - "README reflects the restore bundle workflow (sanitize produces .xlcloak bundle, restore consumes it)"
    - "README shows CLI aliases: reconcile, deidentify, identify"
  artifacts:
    - path: "README.md"
      provides: "Up-to-date CLI reference for phases 1-3 functionality"
  key_links: []
---

<objective>
Rewrite README.md to accurately document the xlcloak CLI as built through phases 1-3.

Purpose: The current README only mentions `inspect` and `sanitize`. The `restore`, `diff` commands and the `reconcile`/`deidentify`/`identify` aliases are undocumented. Anyone installing the package cannot figure out how to restore a file.
Output: README.md with complete installation, quickstart workflow, full command reference, and alias table.
</objective>

<execution_context>
@/home/ajans/code/xlcloak/.claude/get-shit-done/workflows/execute-plan.md
@/home/ajans/code/xlcloak/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite README.md with full CLI reference</name>
  <files>README.md</files>
  <action>
Replace the current README.md with a complete document covering:

**Header block** — keep the one-liner tagline: "Reversible Excel text sanitization CLI for AI workflows."

**Installation section** — pip install + spacy model download (already correct, keep as-is):
```
pip install xlcloak
python -m spacy download en_core_web_lg
```

**Quick start section** — show the common round-trip workflow:
1. Inspect a file before sanitizing: `xlcloak inspect report.xlsx`
2. Sanitize: `xlcloak sanitize report.xlsx` (explain the three outputs: sanitized xlsx, .xlcloak bundle, manifest JSON)
3. Send the sanitized xlsx to your AI tool
4. Restore: `xlcloak restore report_sanitized.xlsx --bundle report.xlcloak` (explain this writes report_restored.xlsx)
5. Check what AI changed before restoring: `xlcloak diff report_sanitized.xlsx --bundle report.xlcloak`

**Commands reference section** — one subsection per command with synopsis, description, and key options:

`xlcloak inspect <file>`
- `--verbose` — show confidence scores and detection method per entity

`xlcloak sanitize <file>`
- `--password TEXT` — encryption password (default prints a warning; use a real password for sensitive data)
- `--output PATH` — output path for sanitized file
- `--bundle PATH` — explicit output path for the .xlcloak bundle
- `--dry-run` — preview detection without writing files
- `--text-mode` — extract all text cells to a .txt file (no token replacement)
- `--force` — overwrite existing output files
- `--verbose` — show entity breakdown by type after sanitizing

`xlcloak restore <file>`
- `--bundle PATH` (required) — path to the .xlcloak restore bundle
- `--password TEXT` — decryption password
- `--output PATH` — output path for restored file
- `--force` — overwrite existing output
- `--verbose` — show list of AI-modified tokens that were skipped

`xlcloak diff <file>`
- `--bundle PATH` (required) — path to the .xlcloak restore bundle
- `--password TEXT` — decryption password
- `--verbose` — also show unchanged token cells and non-token cell count

**Aliases section** — brief table:
| Alias | Equivalent |
|-------|------------|
| `deidentify` | `sanitize` |
| `identify` | `restore` |
| `reconcile` | `restore` |

**How it works section** — 2-3 sentence explanation of the token-map + Fernet encryption approach (entities replaced with stable tokens like PERSON_001, EMAIL_002; token map encrypted with user password into .xlcloak bundle; restore decrypts and reverses; AI-modified cells where the token is gone are skipped and reported).

**License section** — MIT (keep as-is).

Write clean Markdown. No badges, no emoji. Keep the tone practical and direct — this is a developer tool README, not a marketing page.
  </action>
  <verify>
    <automated>python -c "
import re, pathlib
text = pathlib.Path('README.md').read_text()
cmds = ['inspect', 'sanitize', 'restore', 'diff']
aliases = ['reconcile', 'deidentify', 'identify']
missing = [c for c in cmds + aliases if c not in text]
assert not missing, f'Missing from README: {missing}'
assert '--bundle' in text, '--bundle flag not documented'
assert '--dry-run' in text, '--dry-run flag not documented'
print('README check passed')
"</automated>
  </verify>
  <done>README.md documents all four primary commands (inspect, sanitize, restore, diff) and three aliases, includes --bundle and --dry-run flags, and describes the round-trip workflow.</done>
</task>

</tasks>

<verification>
Run: `python -c "import pathlib; t=pathlib.Path('README.md').read_text(); print(len(t), 'chars'); print('Commands found:', [c for c in ['inspect','sanitize','restore','diff','reconcile','deidentify','identify'] if c in t])"`

Expected: all 7 command/alias names present, file is non-trivially sized (>1500 chars).
</verification>

<success_criteria>
README.md accurately reflects the current xlcloak CLI: four primary commands with their flags, three aliases, the sanitize-send-restore workflow, and a brief explanation of how the token-map encryption works.
</success_criteria>

<output>
After completion, create `.planning/quick/260404-ixo-update-readme-md-to-reflect-phases-1-3-c/260404-ixo-SUMMARY.md`
</output>
