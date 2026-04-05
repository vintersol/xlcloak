# Phase 3: Restore & Diff - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-04
**Phase:** 03-restore-diff
**Mode:** discuss
**Areas discussed:** restore/reconcile distinction, diff output format, restore output file, reconciliation report delivery

## Gray Areas Presented

### restore vs reconcile
| Question | Options | User Choice |
|----------|---------|-------------|
| How should restore and reconcile relate? | Same logic/alias; reconcile is interactive; reconcile adds --strategy | Same logic, reconcile is an alias |

### diff output format
| Question | Options | User Choice |
|----------|---------|-------------|
| What should diff show? | Changed cells table; summary only; all cells table | Table: changed cells only |

Preview selected:
```
xlcloak diff: data_sanitized.xlsx vs data.xlcloak

3 cells changed by AI:

Sheet       Cell  Was (token)    Now
──────────────────────────────────────────
Employees   B2    PERSON_001     John Smith
Employees   C2    EMAIL_002@...  john@acme.com
Summary     A1    ORG_003        Acme Corp

No files written.
```

### Restore output destination
| Question | Options | User Choice |
|----------|---------|-------------|
| What file does restore write? | New file data_restored.xlsx; overwrite in place | New file: data_restored.xlsx |

### Reconciliation report
| Question | Options | User Choice |
|----------|---------|-------------|
| Where does the reconciliation report go? | Stdout + manifest file; stdout only; manifest only | Stdout summary + manifest file |

## Corrections Made

No corrections — all recommended options confirmed.

## Auto-Resolved

Not applicable (standard discuss mode).
