# Roadmap: sqlglot-parlante fork

## Overview

Implement the Parlante SQL dialect as a native sqlglot dialect inside this fork. Phase 1 lays the scaffold and tokenizer so operator tokens resolve correctly. Phase 2 wires the parser, generator, and tests into a complete, round-trip-verified implementation that replaces the regex preprocessor in the Parlante library.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Tokenizer + Scaffold** - Register dialect and tokenize all five Parlante operators as single tokens
- [ ] **Phase 2: Parser + Generator + Tests** - Wire operator parsing, function mappings, and generator output; verify with full test suite
- [ ] **Phase 3: AT BRANCH and @branch table syntax** - Parse AT BRANCH / @branch clauses on table references and round-trip them

## Phase Details

### Phase 1: Tokenizer + Scaffold
**Goal**: The Parlante dialect is registered and every Parlante operator tokenizes as a single `TokenType.OPERATOR` token
**Depends on**: Nothing (first phase)
**Requirements**: REG-01, TOK-01, TOK-02, TOK-03, TOK-04, TOK-05, TOK-06, TOK-07
**Success Criteria** (what must be TRUE):
  1. `sqlglot.parse_one("SELECT 1", dialect="parlante")` succeeds without error (dialect is registered)
  2. `@@@`, `|||`, `###`, `===` each tokenize as a single `TokenType.OPERATOR` token — not split into shorter sub-tokens
  3. `<=>` tokenizes as `TokenType.OPERATOR` (overrides the base `NULLSAFE_EQ` mapping)
  4. `@@` and `<->` tokenize identically under the Parlante dialect as they do under the Postgres dialect (no regression)
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md — Create parlante.py dialect scaffold, register in __init__.py, write tokenizer tests

### Phase 2: Parser + Generator + Tests
**Goal**: Every Parlante operator and function name survives a full parse → generate round-trip, producing identical SQL to the input
**Depends on**: Phase 1
**Requirements**: PAR-01, PAR-02, PAR-03, PAR-04, PAR-05, GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, TST-01, TST-02, TST-03, TST-04, TST-05
**Success Criteria** (what must be TRUE):
  1. `col @@@ 'query'` parses to `exp.Operator` and generates back as `col @@@ 'query'` (not `OPERATOR(paradedb.@@@)`) — same for `|||`, `###`, `===`, `<=>`
  2. `MATCH(col, 'query')` parses to `exp.Anonymous("PARLANTE_MATCH", ...)` — not routed to MySQL `MATCH ... AGAINST` — and generates back as `MATCH(col, 'query')` with exact case
  3. `PHRASE_MATCH(col, 'query')` parses to `exp.Anonymous("PARLANTE_PHRASE_MATCH", ...)` and generates back as `PHRASE_MATCH(col, 'query')` with exact case
  4. `@@` (tsvector) and `<->` (L2 distance) parse and generate correctly and unchanged under the Parlante dialect (no regression from Phase 1 or Phase 2 changes)
  5. The full Postgres test suite passes with no new failures after Parlante dialect is introduced
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md — Create parser + generator files, wire dialect, extend tests, verify round-trips and Postgres regression

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Tokenizer + Scaffold | 0/1 | Not started | - |
| 2. Parser + Generator + Tests | 0/1 | Not started | - |
| 3. AT BRANCH and @branch table syntax | 0/0 | Not started | - |

### Phase 3: AT BRANCH and @branch table syntax

**Goal:** Both `AT BRANCH <name>` and `@<name>` syntax forms parse to `exp.Version` and generate back as `AT BRANCH <name>`, with no regressions on existing operators or Postgres tests
**Depends on:** Phase 2
**Requirements:** BRN-01, BRN-02, BRN-03, BRN-04, BRN-05, BRN-06, BRN-07
**Plans:** 1 plan

Plans:
- [ ] 03-01-PLAN.md — Add _parse_version + version_sql overrides and AT BRANCH tests
