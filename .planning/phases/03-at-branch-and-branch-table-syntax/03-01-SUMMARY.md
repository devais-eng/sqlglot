---
phase: 03-at-branch-and-branch-table-syntax
plan: 01
subsystem: parlante-dialect
tags: [parser, generator, branch-syntax, version-clause]
dependency_graph:
  requires: [02-01]
  provides: [at-branch-parsing, shorthand-normalization, version-sql-override]
  affects: [sqlglot/parsers/parlante.py, sqlglot/generators/parlante.py, tests/dialects/test_parlante.py]
tech_stack:
  added: []
  patterns: [_parse_version-override, version_sql-override, TABLE_POSTFIX_TOKENS-extension]
key_files:
  created: []
  modified:
    - sqlglot/parsers/parlante.py
    - sqlglot/generators/parlante.py
    - tests/dialects/test_parlante.py
decisions:
  - TABLE_POSTFIX_TOKENS must include PARAMETER to bypass fast-path alias parsing
  - _match_text_seq("AT", "BRANCH") checked before _match(PARAMETER) — both non-destructive on mismatch
  - version_sql uses self.unsupported() (not raise) for non-BRANCH Version expressions
  - False positive tests document @@→MatchAgainst behavior (not exp.Operator) in Postgres/Parlante
metrics:
  duration: ~4 minutes
  completed: 2026-04-08
  tasks_completed: 2
  files_modified: 3
---

# Phase 3 Plan 1: AT BRANCH and @branch Table Syntax Summary

**One-liner:** `_parse_version` and `version_sql` overrides enabling `AT BRANCH <name>` and `@<name>` shorthand on table references, with `TABLE_POSTFIX_TOKENS` fix to prevent fast-path alias hijacking.

## What Was Built

Both `AT BRANCH <name>` (verbose) and `@<name>` (shorthand) syntax forms are now supported on Parlante table references. Both produce an identical `exp.Version(this="BRANCH", kind="AT", expression=<identifier>)` AST node stored in `table.args["version"]`. The generator always emits the verbose `AT BRANCH <name>` form (normalizing the shorthand). Non-BRANCH Version expressions emit an unsupported warning.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add `_parse_version` and `version_sql` overrides | 468bb3ba | sqlglot/parsers/parlante.py, sqlglot/generators/parlante.py |
| 2 | Add AT BRANCH tests and verify no regressions | 55f24079 | tests/dialects/test_parlante.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `TABLE_POSTFIX_TOKENS` missing `PARAMETER` caused `@branch` to parse as alias**

- **Found during:** Task 1 verification
- **Issue:** The `_parse_table` fast-path (lines 4692-4699 in parser.py) checks if the current token is NOT in `TABLE_POSTFIX_TOKENS` and NOT a terminator. Since `PARAMETER` (`@`) was not in `TABLE_POSTFIX_TOKENS`, the fast-path called `_parse_table_alias`, which internally called `_parse_id_var` → `_parse_placeholder` → `_parse_parameter`, consuming `@main` as a `Parameter` alias before `_parse_version` ever ran.
- **Fix:** Added `TABLE_POSTFIX_TOKENS = PostgresParser.TABLE_POSTFIX_TOKENS | frozenset([TokenType.PARAMETER])` to `ParlanteParse`. This causes the fast-path to skip alias parsing when `@` follows the table name, falling through to `self._retreat(index)` and then the full `_parse_table` flow that calls `_parse_version` first.
- **Files modified:** sqlglot/parsers/parlante.py
- **Commit:** 468bb3ba

**2. [Rule 1 - Bug] False positive test for `AT something` used incorrect assertion type**

- **Found during:** Task 2 test execution
- **Issue:** Test assumed `SELECT * FROM t AT something` would produce a parseable result (an `AtIndex`). In reality, both Postgres and Parlante raise a `ParseError` for `AT` not followed by `BRANCH` (or recognized identifiers in appropriate context). The initial test assertion `assertIsNone(table2.args.get("version"))` was unreachable because the parse itself raised.
- **Fix:** Changed to `assertRaises(Exception)` — this correctly documents that `AT something` is rejected, confirming no false `AT BRANCH` interpretation occurs.
- **Files modified:** tests/dialects/test_parlante.py
- **Commit:** 55f24079

**3. [Rule 1 - Bug] False positive test for `@@` operator used `exp.Operator` instead of `exp.MatchAgainst`**

- **Found during:** Task 2 test execution
- **Issue:** In Postgres/Parlante, `@@` is tokenized as `DAT` (not `OPERATOR`) and parsed as `exp.MatchAgainst`, not `exp.Operator`. The initial test asserted `assertIsNotNone(tree.find(exp.Operator))` which always fails for `@@` expressions.
- **Fix:** Changed assertion to `assertIsNotNone(tree.find(exp.MatchAgainst))` and added a round-trip assertion to confirm branch + tsvector coexist correctly.
- **Files modified:** tests/dialects/test_parlante.py
- **Commit:** 55f24079

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `TABLE_POSTFIX_TOKENS` extension | Only way to prevent fast-path from consuming `@branch` as alias before `_parse_version` runs — adding to postfix tokens forces the full parse path |
| `_match_text_seq("AT", "BRANCH")` before `_match(PARAMETER)` | `_match_text_seq` is non-destructive on mismatch; `_match` is not. Order must be: try AT BRANCH first, then @ shorthand, then super() |
| `self.unsupported()` not `raise` | Follows all existing generator patterns; caller controls error level via `unsupported_level` setting |
| `@@` → `MatchAgainst` documented | Clarifies that `@@` in Postgres/Parlante context is not `exp.Operator` — important for test authors |

## Test Coverage Added

6 new test methods in `TestParlante`:
- `test_at_branch_roundtrip` — verbose form, version-before-alias, schema-qualified
- `test_at_branch_shorthand` — @shorthand normalized to AT BRANCH (both plain and aliased)
- `test_at_branch_ast_type` — Version node structure verified for both syntax forms
- `test_at_branch_unsupported_version` — TIMESTAMP Version triggers unsupported warning
- `test_at_branch_no_regression` — operators and tsvector unaffected
- `test_at_branch_false_positives` — @var in SELECT, AT-without-BRANCH error, @@+branch combo

Total: 22 tests in test_parlante (previously 16), all passing.
Postgres test suite: 25 tests, all passing — no regressions.

## Self-Check: PASSED

Files exist:
- sqlglot/parsers/parlante.py: FOUND
- sqlglot/generators/parlante.py: FOUND
- tests/dialects/test_parlante.py: FOUND

Commits exist:
- 468bb3ba: FOUND
- 55f24079: FOUND

All 22 Parlante tests passing. All 25 Postgres tests passing.
