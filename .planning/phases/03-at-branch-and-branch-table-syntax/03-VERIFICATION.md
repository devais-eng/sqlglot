---
phase: 03-at-branch-and-branch-table-syntax
verified: 2026-04-08T00:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 3: AT BRANCH and @branch Table Syntax — Verification Report

**Phase Goal:** Both `AT BRANCH <name>` and `@<name>` syntax forms parse to `exp.Version` and generate back as `AT BRANCH <name>`, with no regressions on existing operators or Postgres tests
**Verified:** 2026-04-08
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                | Status     | Evidence                                                                                    |
|----|--------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| 1  | `SELECT * FROM t AT BRANCH main` parses and generates back as-is                    | VERIFIED   | `parse_one(...).sql(dialect='parlante')` returns `'SELECT * FROM t AT BRANCH main'`        |
| 2  | `SELECT * FROM t@main` parses and generates as `SELECT * FROM t AT BRANCH main`     | VERIFIED   | `parse_one(...).sql(dialect='parlante')` returns normalized verbose form                    |
| 3  | `SELECT * FROM t AT BRANCH main AS tbl` round-trips with version before alias       | VERIFIED   | Output preserves `AT BRANCH main AS tbl` ordering                                           |
| 4  | Non-branch Version (e.g. TIMESTAMP) triggers unsupported warning, not exception      | VERIFIED   | `gen.unsupported_messages` contains `"Parlante only supports AT BRANCH versioning, got: 'TIMESTAMP'"` |
| 5  | `SELECT a @@ b` round-trips correctly (tsvector unaffected)                         | VERIFIED   | Output `'SELECT a @@ b FROM t'`; `table.args["version"]` is `None`                         |
| 6  | All existing Parlante operator and function tests still pass                          | VERIFIED   | `python -m unittest tests.dialects.test_parlante -v` → 22 tests, 0 failures                |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact                              | Provides                                        | Status   | Details                                                                                                   |
|---------------------------------------|-------------------------------------------------|----------|-----------------------------------------------------------------------------------------------------------|
| `sqlglot/parsers/parlante.py`         | `_parse_version` override for AT BRANCH and @   | VERIFIED | Method exists, substantive (47 lines, three branches), wired — `TABLE_POSTFIX_TOKENS` extends parent     |
| `sqlglot/generators/parlante.py`      | `version_sql` override emitting `AT BRANCH`     | VERIFIED | Method exists, substantive, auto-discovered (not in TRANSFORMS), outputs `'AT BRANCH main'`              |
| `tests/dialects/test_parlante.py`     | AT BRANCH round-trip, shorthand, AST, unsupported, regression tests | VERIFIED | Contains `test_at_branch_*` family; 22 tests total, all passing                          |

---

### Key Link Verification

| From                            | To                  | Via                                              | Status  | Details                                                                                         |
|---------------------------------|---------------------|--------------------------------------------------|---------|-------------------------------------------------------------------------------------------------|
| `sqlglot/parsers/parlante.py`   | `exp.Version`       | `_parse_version` returns `exp.Version(this="BRANCH", kind="AT", expression=...)` | WIRED | Confirmed by AST inspection: `version.name == "BRANCH"`, `version.text("kind") == "AT"` |
| `sqlglot/generators/parlante.py`| `version_sql`       | Auto-discovered method emits `AT BRANCH <name>`  | WIRED   | `exp.Version` not in TRANSFORMS; method auto-discovered; output confirmed `'AT BRANCH main'`   |
| `sqlglot/parsers/parlante.py`   | `TokenType.PARAMETER` | `_match(TokenType.PARAMETER)` for @shorthand   | WIRED   | `PARAMETER in ParlanteParse.TABLE_POSTFIX_TOKENS` is True; @shorthand produces identical AST  |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                           | Status    | Evidence                                                                                         |
|-------------|-------------|-------------------------------------------------------|-----------|--------------------------------------------------------------------------------------------------|
| BRN-01      | 03-01       | `AT BRANCH main` parses to `exp.Version` on table     | SATISFIED | `table.args["version"]` is `exp.Version(name="BRANCH", kind="AT")` for verbose form             |
| BRN-02      | 03-01       | `@main` parses identically to BRN-01                  | SATISFIED | `table.args["version"]` is identical `exp.Version` node for @shorthand form                     |
| BRN-03      | 03-01       | Both forms generate as `AT BRANCH main`               | SATISFIED | Both `AT BRANCH main` and `@main` input → `'SELECT * FROM t AT BRANCH main'` output             |
| BRN-04      | 03-01       | Version before alias round-trips                      | SATISFIED | `SELECT * FROM t AT BRANCH main AS tbl` → identical output, version precedes alias              |
| BRN-05      | 03-01       | Non-branch Version raises unsupported                 | SATISFIED | `gen.version_sql(Version(this="TIMESTAMP", ...))` → `unsupported_messages` is non-empty         |
| BRN-06      | 03-01       | `@@` and `<->` unaffected                             | SATISFIED | `SELECT a @@ b FROM t` round-trips; `table.args["version"]` is None; `<->` round-trips         |
| BRN-07      | 03-01       | Existing operator tests pass                          | SATISFIED | All 22 tests pass including pre-existing operator, match, tsvector, and l2-distance tests        |

---

### Anti-Patterns Found

None detected. No TODOs, placeholders, empty implementations, or console.log-only stubs found in the modified files.

---

### Human Verification Required

None. All behaviors are programmatically verifiable:
- Parse/generate round-trips confirmed via Python invocations
- AST structure verified via direct attribute inspection
- Unsupported warning confirmed via `unsupported_messages` list
- Postgres test suite (25 tests) confirmed passing with no regressions

---

### Gaps Summary

No gaps. All six truths verified, all three artifacts substantive and wired, all seven requirements satisfied.

Notable implementation detail confirmed: `TABLE_POSTFIX_TOKENS` was extended to include `TokenType.PARAMETER`. This is critical wiring — without it the parser fast-path consumes `@branch` as a table alias before `_parse_version` runs. The fix is present and verified.

---

_Verified: 2026-04-08_
_Verifier: Claude (gsd-verifier)_
