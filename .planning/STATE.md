# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Native Parlante dialect — no regex preprocessing, mypyc-compilable
**Current focus:** Phase 1 — Tokenizer + Scaffold

## Current Position

Phase: 3 of 3 (AT BRANCH and @branch table syntax)
Plan: 1 of 1 in current phase
Status: Plan 03-01 complete — AT BRANCH parser/generator overrides + 22 passing tests
Last activity: 2026-04-08 — Plan 03-01 executed: _parse_version + version_sql + 6 new tests

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-tokenizer-scaffold | 1 | ~2min | ~2min |
| 02-parser-generator-tests | 1 | ~2min | ~2min |
| 03-at-branch-and-branch-table-syntax | 1 | ~4min | ~4min |

**Recent Trend:**
- Last 5 plans: 01-01 (~2min)
- Trend: On track

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- MATCH → PARLANTE_MATCH rename: `MATCH` is a SQL keyword; prefixed name avoids MySQL MATCH...AGAINST collision
- Operators as `TokenType.OPERATOR`: Reuses existing Postgres `exp.Operator`, no new expression class needed
- Dialect lives in `sqlglot/dialects/parlante.py`: Standard location, auto-registration via metaclass
- Keyword spread ordering: **Postgres.Tokenizer.KEYWORDS spread first so <=> override takes effect (plan 01-01)
- DIALECTS list only (not Dialects enum): metaclass auto-registers via clsname.lower() (plan 01-01)
- MATCH excluded from FUNCTION_PARSERS via dict comprehension to allow FUNCTIONS fallthrough (plan 02-01)
- TRANSFORMS override required for exp.Operator — base generator TRANSFORMS already has the key; auto-discovered method silently ignored (plan 02-01)
- anonymous_sql dispatch by name with super() fallback for PARLANTE_MATCH/PARLANTE_PHRASE_MATCH routing (plan 02-01)
- TABLE_POSTFIX_TOKENS must include PARAMETER to bypass fast-path alias parsing for @branch shorthand (plan 03-01)
- _parse_version checks AT BRANCH before PARAMETER — _match_text_seq is non-destructive on failure (plan 03-01)
- version_sql uses self.unsupported() not raise for non-BRANCH Version expressions (plan 03-01)

### Roadmap Evolution

- Phase 3 added: AT BRANCH and @branch table syntax

### Pending Todos

None yet.

### Blockers/Concerns

None — all Phase 2 watch-outs resolved in plan 02-01.

## Session Continuity

Last session: 2026-04-08
Stopped at: Completed 03-01-PLAN.md — AT BRANCH parsing + 22 passing tests
