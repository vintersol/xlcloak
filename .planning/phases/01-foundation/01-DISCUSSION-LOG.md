# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 01-foundation
**Areas discussed:** Token format & naming, Token shape preservation

---

## Token format & naming

### Prefix style

| Option | Description | Selected |
|--------|-------------|----------|
| Full type name | PERSON_001, ORG_001, EMAIL_001 — immediately clear what entity type was replaced | ✓ |
| Short abbreviation | PER_001, ORG_001, EML_001 — more compact | |
| Bracketed tokens | [PERSON_001], [ORG_001] — visually distinct from real data | |

**User's choice:** Full type name
**Notes:** None

### Counter scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-type counters | PERSON_001, PERSON_002, ORG_001 — each type starts at 001 | |
| Global counter | PERSON_001, ORG_002, EMAIL_003 — single incrementing counter | ✓ |

**User's choice:** Global counter
**Notes:** User raised concern that per-type counters (e.g., PERSON_001 and EMAIL_001) could mislead users into thinking the tokens refer to the same entity. Global counter avoids this ambiguity.

### Counter padding

| Option | Description | Selected |
|--------|-------------|----------|
| 3-digit fixed | 001 through 999 — clean alignment in columns | ✓ |
| Dynamic padding | Pad based on total count — compact but inconsistent across runs | |
| No padding | 1, 2, 3 — simplest but misaligns | |

**User's choice:** 3-digit fixed
**Notes:** None

### Entity type names

| Option | Description | Selected |
|--------|-------------|----------|
| Descriptive types | PERSON, ORG, EMAIL, PHONE, URL, SSN_SE, ORGNUM_SE — clear, Swedish types get _SE suffix | ✓ |
| Short types | PER, ORG, EML, PHN, URL, SSN, ONR — compact | |

**User's choice:** Descriptive types
**Notes:** None

---

## Token shape preservation

### Email shape

| Option | Description | Selected |
|--------|-------------|----------|
| Realistic email shape | EMAIL_003@example.com — passes basic email validation | ✓ |
| Flat token only | EMAIL_003 — simpler but not recognized as email | |
| Domain-preserving | EMAIL_003@acme.com — keeps original domain, leaks domain name | |

**User's choice:** Realistic email shape
**Notes:** None

### Phone shape

| Option | Description | Selected |
|--------|-------------|----------|
| Numeric placeholder | +10-000-000-004 — counter embedded in last digits | ✓ |
| Flat token only | PHONE_004 — simple but not recognized as phone | |
| You decide | Let Claude pick during implementation | |

**User's choice:** Numeric placeholder
**Notes:** None

### Person/org name shape

| Option | Description | Selected |
|--------|-------------|----------|
| Plain token | PERSON_001, ORG_002 — names have no structural format to preserve | ✓ |
| Fake name substitution | Replace with plausible fake names — adds complexity | |

**User's choice:** Plain token
**Notes:** None

### URL shape

| Option | Description | Selected |
|--------|-------------|----------|
| URL-shaped placeholder | https://example.com/URL_005 — remains a valid URL | ✓ |
| Flat token only | URL_005 — simple but not parsed as URL | |

**User's choice:** URL-shaped placeholder
**Notes:** None

---

## Claude's Discretion

- Project structure and module layout
- Test fixture content details
- SSN_SE and ORGNUM_SE token shapes
- Internal token engine architecture

## Deferred Ideas

None
