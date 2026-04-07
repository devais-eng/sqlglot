---
phase: 02-parser-generator-tests
plan: 01
subsystem: dialects
tags: [sqlglot, parlante, postgres, parser, generator, operator, anonymous, round-trip]

# Dependency graph
requires:
  - phase: 01-tokenizer-scaffold
    provides: Parlante dialect registered, TokenType.OPERATOR for @@@/|||/###/===/<=>, test scaffold
provides:
  - ParlanteParse(PostgresParser) with MATCH excluded from FUNCTION_PARSERS and OPERATOR in RANGE_PARSERS
  - ParlanteGenerator(PostgresGenerator) with exp.Operator TRANSFORMS override and anonymous_sql routing
  - Full parse→generate round-trip for all five Parlante operators and MATCH/PHRASE_MATCH functions
  - 10 passing test methods covering round-trips, AST types, and Postgres regressions
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Exclude inherited FUNCTION_PARSERS keys via dict comprehension to unblock FUNCTIONS fallthrough"
    - "Override RANGE_PARSERS[TokenType.OPERATOR] to handle infix custom operators"
    - "Use TRANSFORMS override (not auto-discovered method) when parent TRANSFORMS already has the key"
    - "Use anonymous_sql method with name check for dialect-specific anonymous function routing"

key-files:
  created:
    - sqlglot/parsers/parlante.py
    - sqlglot/generators/parlante.py
  modified:
    - sqlglot/dialects/parlante.py
    - tests/dialects/test_parlante.py

key-decisions:
  - "Exclude MATCH from FUNCTION_PARSERS via dict comprehension — FUNCTION_PARSERS takes priority over FUNCTIONS, so without exclusion MATCH routes to _parse_match_against and fails on missing AGAINST keyword"
  - "RANGE_PARSERS[TokenType.OPERATOR] uses self._prev.text to capture operator symbol at call time — at this point the OPERATOR token has been consumed so _prev holds it and _curr is the RHS start"
  - "TRANSFORMS override required for exp.Operator — auto-discovered operator_sql is silently ignored because base generator.py line 225 already registers exp.Operator in TRANSFORMS"
  - "anonymous_sql dispatch by expression.name with super() fallback — clean single-method approach for routing PARLANTE_MATCH/PARLANTE_PHRASE_MATCH without touching TRANSFORMS"
  - "normalize=False in self.func() calls — preserves MATCH/PHRASE_MATCH exact case regardless of dialect normalization settings"

patterns-established:
  - "Parser exclusion pattern: {k: v for k, v in Parent.FUNCTION_PARSERS.items() if k != 'KEY'} to unblock FUNCTIONS fallthrough"
  - "RANGE_PARSERS infix operator: lambda self, this: self.expression(exp.Operator(this=this, operator=self._prev.text, expression=self._parse_bitwise()))"

requirements-completed:
  - PAR-01
  - PAR-02
  - PAR-03
  - PAR-04
  - PAR-05
  - GEN-01
  - GEN-02
  - GEN-03
  - GEN-04
  - GEN-05
  - TST-01
  - TST-02
  - TST-03
  - TST-04
  - TST-05

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 2 Plan 01: Parser, Generator, and Tests Summary

**ParlanteParse + ParlanteGenerator wired into Parlante dialect enabling full parse→generate round-trip for @@@/|||/###/===/<=>, MATCH(), and PHRASE_MATCH() with zero Postgres regressions**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-07T13:43:45Z
- **Completed:** 2026-04-07T13:45:35Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `sqlglot/parsers/parlante.py` with `ParlanteParse(PostgresParser)`: MATCH excluded from FUNCTION_PARSERS, MATCH/PHRASE_MATCH added to FUNCTIONS, TokenType.OPERATOR wired in RANGE_PARSERS for infix parsing
- Created `sqlglot/generators/parlante.py` with `ParlanteGenerator(PostgresGenerator)`: TRANSFORMS override for exp.Operator emitting `lhs @@@ rhs`, anonymous_sql dispatching PARLANTE_MATCH → MATCH() and PARLANTE_PHRASE_MATCH → PHRASE_MATCH()
- Updated `sqlglot/dialects/parlante.py`: assigned `Parser = ParlanteParse` and `Generator = ParlanteGenerator` alongside existing Tokenizer inner class
- Extended test suite from 4 to 10 methods: 5 operator round-trips, 2 function round-trips, 2 regression guards, 2 AST-type assertions — all passing
- Postgres test suite: 25/25 tests pass, zero new failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Create parser, generator, and update dialect** - `8b09bf30` (feat)
2. **Task 2: Extend test_parlante.py and run full suite** - `c52fb79b` (test)

**Plan metadata:** (see final commit)

## Files Created/Modified

- `sqlglot/parsers/parlante.py` — ParlanteParse with FUNCTION_PARSERS exclusion, FUNCTIONS additions, RANGE_PARSERS OPERATOR override
- `sqlglot/generators/parlante.py` — ParlanteGenerator with TRANSFORMS override for exp.Operator and anonymous_sql routing
- `sqlglot/dialects/parlante.py` — Added Parser = ParlanteParse and Generator = ParlanteGenerator class attributes
- `tests/dialects/test_parlante.py` — Six new test methods + exp import

## Decisions Made

- **MATCH exclusion from FUNCTION_PARSERS**: Without removal, `FUNCTION_PARSERS["MATCH"]` fires first and routes to `_parse_match_against`, which expects `AGAINST` keyword and throws. Exclusion via dict comprehension allows FUNCTIONS fallthrough.
- **TRANSFORMS override for exp.Operator**: Base `generator.py:225` registers `exp.Operator` in TRANSFORMS with a `binary()` call that adds `OPERATOR(...)` wrapper. Auto-discovered `operator_sql` method would be silently ignored. Explicit TRANSFORMS override is the correct approach.
- **f-string in TRANSFORMS lambda acceptable**: The operator field must be emitted literally; no public generator API handles this without the OPERATOR wrapper. Plan explicitly noted this as the correct approach.
- **normalize=False**: Preserves exact function name casing (MATCH, PHRASE_MATCH) across all normalization settings.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all three watch-outs documented from Phase 1 research were handled as planned without surprises.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Parlante dialect is now fully functional end-to-end: tokenize → parse → generate round-trips correctly for all Parlante-specific syntax
- Milestone v1.0 is complete: native Parlante dialect replaces fragile regex rewrite hack
- No outstanding blockers

---
*Phase: 02-parser-generator-tests*
*Completed: 2026-04-07*
