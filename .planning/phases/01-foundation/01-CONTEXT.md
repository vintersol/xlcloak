# Phase 1: Foundation - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A correct, tested token engine and validated Excel read/write pipeline exist as the stable base for all subsequent work. Includes token generation with deterministic mapping, shape-preserving token formatting, Excel I/O that handles unsupported surfaces gracefully, and three graduated test fixtures.

</domain>

<decisions>
## Implementation Decisions

### Token format & naming
- **D-01:** Full descriptive type prefixes: PERSON, ORG, EMAIL, PHONE, URL, SSN_SE, ORGNUM_SE
- **D-02:** Global ever-increasing counter across all types (not per-type). PERSON_001, ORG_002, EMAIL_003, etc. — same entity number is NOT shared across types; it simply increments globally
- **D-03:** 3-digit zero-padded counter (001 through 999). Handles up to 999 entities per workbook run

### Token shape preservation
- **D-04:** Email tokens are email-shaped: `EMAIL_003@example.com` — passes basic email validation
- **D-05:** Phone tokens are numeric placeholders: `+10-000-000-004` — counter embedded in last digits, looks like a phone number
- **D-06:** Person and org name tokens are plain: `PERSON_001`, `ORG_002` — names have no structural format to preserve
- **D-07:** URL tokens are URL-shaped: `https://example.com/URL_005` — remains a valid URL
- **D-08:** SSN_SE and ORGNUM_SE shape preservation: Claude's discretion during implementation (e.g., numeric placeholders matching digit patterns)

### Claude's Discretion
- Project structure and module layout (package organization, where fixtures live)
- Test fixture content details (specific PII scenarios in simple/medium/hard xlsx files)
- SSN_SE and ORGNUM_SE token shape (numeric placeholders matching Swedish format patterns)
- Internal token engine architecture (registry, mapping data structures)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — Project vision, constraints (Python 3.10+, openpyxl, Presidio, Fernet), key decisions
- `.planning/REQUIREMENTS.md` — Full v1 requirements with traceability; Phase 1 covers TOK-01, TOK-02, TOK-03, DET-09, TEST-01 through TEST-04
- `.planning/ROADMAP.md` — Phase 1 success criteria (5 criteria covering determinism, readability, shape preservation, Excel round-trip, fixtures)

### Technology stack
- `CLAUDE.md` §Technology Stack — Pinned versions for openpyxl, Click, pytest, ruff, mypy, uv, hatchling

No external specs or ADRs — requirements fully captured in planning docs above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, only LICENSE file exists

### Established Patterns
- None yet — Phase 1 establishes the foundational patterns

### Integration Points
- Token engine will be consumed by Phase 2's sanitize command and detection pipeline
- Excel I/O pipeline will be consumed by Phase 2's sanitize and Phase 3's restore
- Test fixtures will be used across all phases for validation

</code_context>

<specifics>
## Specific Ideas

- Global counter was chosen over per-type counters to avoid the appearance that PERSON_001 and EMAIL_001 are related entities — a global counter makes it clear each token is independently numbered
- Shape-preserving tokens should pass basic format validation so AI tools and Excel recognize the data type (email fields stay email-shaped, phone fields stay phone-shaped)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-03*
