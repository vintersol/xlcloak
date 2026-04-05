# Phase 4: Power Features - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-04
**Phase:** 04-power-features
**Mode:** discuss
**Areas discussed:** Hide-all mode flag, Swedish recognizer design, Company suffix detection

## Gray Areas Presented

| Area | Selected |
|------|----------|
| Hide-all mode flag | Yes |
| Swedish recognizer design | Yes |
| Header context architecture | No |
| Company suffix detection | Yes |

## Decisions Recorded

### Hide-all Mode
- **Question:** --text-mode is a boolean; ROADMAP says --text-mode hide-all. How to reconcile?
- **User chose:** New `--hide-all` flag on sanitize; `--text-mode` unchanged
- **Reason:** Clean, no breakage to existing behavior

### Swedish Recognizers — Validation
- **Question:** Luhn checksum or regex-only for personnummer?
- **User chose:** Regex + Luhn variant checksum (full validation, rejects false positives)

### Swedish Recognizers — Architecture
- **Question:** PatternRecognizer subclasses vs pre-scan vs standalone module?
- **User chose:** Presidio PatternRecognizer subclasses, registered via add_recognizer()

### Company Suffix Detection — Approach
- **Question:** PatternRecognizer vs NER boost vs column-header only?
- **User chose:** PatternRecognizer for suffix patterns (maps to EntityType.ORG)

### Company Suffix Detection — Suffix List
- **Question:** Core ~15 suffixes, Swedish-only, or large 50+ list?
- **User chose:** Core international + Swedish (~15): AB, HB, KB, Aktiebolag, Ltd, Limited, Inc, Corp, Corporation, GmbH, LLC, LLP, SA, NV, BV

## Not Discussed (Header Context Architecture)
- Architecture for passing column header context left to Claude's discretion during planning
- Requirement: detection confidence visibly higher for PII-labeled columns
