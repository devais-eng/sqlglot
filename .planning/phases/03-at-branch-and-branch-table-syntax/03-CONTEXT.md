# Phase 3: AT BRANCH and @branch table syntax - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the Parlante parser and generator to handle catalog branch references on table expressions. Both `SELECT * FROM table AT BRANCH main` and `SELECT * FROM table@main` forms must be parsed. Generator always emits the verbose `AT BRANCH` form.

</domain>

<decisions>
## Implementation Decisions

### Syntax forms
- Parse BOTH `AT BRANCH <name>` and `@<name>` shorthand on table references
- `table@main` and `table AT BRANCH main` are semantically identical (pure syntactic sugar)
- Scope limited to AT BRANCH only — no AT TAG, AT COMMIT, or other Nessie versioning forms
- Both forms always accepted — no env var / config toggle (dialect is stateless)

### AST representation
- Reuse `exp.Version` (existing expression class) to store branch info
- Store as `Version(this="BRANCH", kind="AT", expression=<identifier>)` on `table.args["version"]`
- Branch and time-travel versioning are mutually exclusive (share the same slot) — this correctly models reality since no database supports both simultaneously
- No new expression class needed

### Generator round-trip
- Always emit `AT BRANCH <name>` form (normalize @shorthand to verbose form)
- Override `version_sql` in Parlante generator to handle `this="BRANCH"` case
- Non-branch Version expressions (e.g. TIMESTAMP AS OF from Spark transpilation) should raise unsupported error
- AT BRANCH appears before table alias: `table AT BRANCH main AS t` (ALIAS_POST_VERSION=True, like Spark)

### Claude's Discretion
- Exact tokenizer changes needed for `@branch` shorthand parsing (may need special handling to avoid collision with `@@` tsvector operator)
- How to wire `AT BRANCH` keyword sequence into `_parse_version()` or a Parlante override
- Test structure and specific test cases beyond the round-trip requirement

</decisions>

<specifics>
## Specific Ideas

- User's prior implementation used `_parse_table_parts` override with `table.meta["catalog_branch"]` — we are explicitly moving away from this toward `exp.Version` for proper AST integration
- The existing `_parse_version()` in base parser matches `TIMESTAMP_SNAPSHOT` / `VERSION_SNAPSHOT` tokens — Parlante will need to extend this to also match AT BRANCH keyword sequence
- `@` shorthand must not break existing `@@` (tsvector) operator which is inherited from Postgres dialect

</specifics>

<deferred>
## Deferred Ideas

- AT TAG / AT COMMIT (Nessie catalog versioning) — add as future phase if needed
- Config toggle for strict mode (only allow one syntax form) — not needed given stateless dialect design
- LanceDB `@version` numeric shorthand — different semantics, different phase

</deferred>

---

*Phase: 03-at-branch-and-branch-table-syntax*
*Context gathered: 2026-04-08*
