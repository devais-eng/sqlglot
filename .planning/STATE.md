# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Native Parlante dialect — no regex preprocessing, mypyc-compilable
**Current focus:** Phase 1 — Tokenizer + Scaffold

## Current Position

Phase: 1 of 2 (Tokenizer + Scaffold)
Plan: 1 of 1 in current phase
Status: Plan 01-01 complete — ready for Phase 2
Last activity: 2026-04-07 — Plan 01-01 executed: Parlante dialect scaffold + tokenizer

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-tokenizer-scaffold | 1 | ~2min | ~2min |

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2 watch-out: `FUNCTION_PARSERS["MATCH"]` takes priority over `FUNCTIONS["MATCH"]` — must remove the key from `FUNCTION_PARSERS` in Parlante's Parser (see research SUMMARY.md §Critical Watch-Outs #1)
- Phase 2 watch-out: `RANGE_PARSERS[TokenType.OPERATOR]` must be overridden — adding to KEYWORDS alone is insufficient for infix `@@@` parsing (research §Critical Watch-Outs #2)
- Phase 2 watch-out: `exp.Operator` is already in `Postgres.Generator.TRANSFORMS` — auto-discovered `operator_sql` will be silently ignored; must use `TRANSFORMS = {**Postgres.Generator.TRANSFORMS, exp.Operator: ...}` (research §Critical Watch-Outs #3)

## Session Continuity

Last session: 2026-04-07
Stopped at: Completed 01-01-PLAN.md — Parlante dialect scaffold + tokenizer
Resume file: None
