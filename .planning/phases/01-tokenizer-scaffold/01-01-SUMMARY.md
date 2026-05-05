---
phase: 01-tokenizer-scaffold
plan: 01
subsystem: dialects
tags: [sqlglot, tokenizer, parlante, postgres, operator, trie]

# Dependency graph
requires: []
provides:
  - Parlante dialect class extending Postgres registered in sqlglot
  - Tokenizer KEYWORDS override mapping @@@, |||, ###, ===, <=> to TokenType.OPERATOR
  - Four passing test methods covering registration, operator tokens, @@ and <-> regressions
affects:
  - 01-02  # Phase 1 Plan 2 (parser + generator) extends this scaffold

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Extend Postgres.Tokenizer.KEYWORDS with spread-first pattern to preserve base mappings"
    - "Register dialect via DIALECTS list in dialects/__init__.py for lazy import"

key-files:
  created:
    - sqlglot/dialects/parlante.py
    - tests/dialects/test_parlante.py
  modified:
    - sqlglot/dialects/__init__.py

key-decisions:
  - "Spread **Postgres.Tokenizer.KEYWORDS first so <=> override comes after (not before) base NULLSAFE_EQ mapping"
  - "Register Parlante in DIALECTS list (not Dialects enum) - metaclass auto-registers via clsname.lower()"
  - "All five Parlante operators use existing TokenType.OPERATOR — no new token type needed"

patterns-established:
  - "Dialect keyword override: spread parent KEYWORDS first, then add dialect-specific entries"
  - "DIALECTS list drives MODULE_BY_DIALECT and __getattr__ lazy import"

requirements-completed:
  - REG-01
  - TOK-01
  - TOK-02
  - TOK-03
  - TOK-04
  - TOK-05
  - TOK-06
  - TOK-07

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 1 Plan 01: Tokenizer Scaffold Summary

**Parlante dialect registered in sqlglot with trie-based tokenizer emitting @@@, |||, ###, ===, <=> as single TokenType.OPERATOR tokens**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-07T12:57:45Z
- **Completed:** 2026-04-07T12:59:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `sqlglot/dialects/parlante.py` (~17 lines) — Parlante extends Postgres, overrides Tokenizer.KEYWORDS with five operator entries
- Registered `"Parlante"` in `DIALECTS` list enabling `dialect="parlante"` lookups via lazy import
- Four test methods covering dialect registration, all five operator tokens (5 subtests), and two Postgres regression cases (`@@` → DAT, `<->` → LR_ARROW)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create parlante.py and register dialect** - `8b36c990` (feat)
2. **Task 2: Write test_parlante.py and run tests** - `45f2f4ae` (test)

## Files Created/Modified

- `sqlglot/dialects/parlante.py` — New Parlante dialect class with Tokenizer.KEYWORDS override
- `sqlglot/dialects/__init__.py` — Added "Parlante" to DIALECTS list between "Oracle" and "Postgres"
- `tests/dialects/test_parlante.py` — Four test methods: dialect registration, operator tokens, @@ regression, <-> regression

## Decisions Made

- **Spread ordering matters for <=>**: `**Postgres.Tokenizer.KEYWORDS` is spread first so the subsequent `"<=>": TokenType.OPERATOR` entry overrides the base `NULLSAFE_EQ` mapping. Reversing the order would lose the override.
- **DIALECTS list, not Dialects enum**: The metaclass auto-registers via `clsname.lower()`, so only the DIALECTS list entry is needed for lazy import. Adding a Dialects enum member would be redundant.
- **No new TokenType needed**: All five operators reuse the existing `TokenType.OPERATOR` value, consistent with the research decision.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing `pytz` import errors cause 2 failures in `make unit` (`test_bigquery`, `test_convert`). These are unrelated to Parlante and existed before this plan. All 4 Parlante tests and all 25 Postgres tests pass cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Dialect scaffold is complete and tested; Phase 2 (parser + generator) can now extend `Parlante` with `Parser` and `Generator` inner classes
- Watch-out carried forward: `FUNCTION_PARSERS["MATCH"]` priority over `FUNCTIONS["MATCH"]` (Phase 2 must remove key from Parlante's Parser)
- Watch-out carried forward: `RANGE_PARSERS[TokenType.OPERATOR]` must be overridden for infix `@@@` parsing (KEYWORDS alone insufficient)
- Watch-out carried forward: `exp.Operator` already in `Postgres.Generator.TRANSFORMS` — auto-discovered `operator_sql` will be silently ignored; must use `TRANSFORMS = {**Postgres.Generator.TRANSFORMS, exp.Operator: ...}`

---
*Phase: 01-tokenizer-scaffold*
*Completed: 2026-04-07*
