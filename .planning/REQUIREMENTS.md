# Requirements: sqlglot-parlante fork

**Defined:** 2026-04-07
**Core Value:** Native Parlante dialect — no regex preprocessing, mypyc-compilable

## v1 Requirements

### Dialect Registration

- [ ] **REG-01**: `sqlglot.parse_one(sql, dialect="parlante")` resolves the Parlante dialect (dialect auto-registered via metaclass, lazy-loaded via `DIALECTS` list in `__init__.py`)

### Tokenizer

- [ ] **TOK-01**: `@@@` tokenizes as a single `TokenType.OPERATOR` token (not split into `@@` + `@`)
- [ ] **TOK-02**: `|||` tokenizes as a single `TokenType.OPERATOR` token
- [ ] **TOK-03**: `###` tokenizes as a single `TokenType.OPERATOR` token
- [ ] **TOK-04**: `===` tokenizes as a single `TokenType.OPERATOR` token
- [ ] **TOK-05**: `<=>` tokenizes as `TokenType.OPERATOR` (overrides base `NULLSAFE_EQ` mapping)
- [ ] **TOK-06**: `<->` tokenizes unchanged (L2 distance — handled by Postgres base, must not regress)
- [ ] **TOK-07**: `@@` (tsvector match) tokenizes unchanged (must not regress)

### Parser

- [ ] **PAR-01**: `col @@@ 'query'` parses to an `exp.Operator` AST node with operator `@@@`
- [ ] **PAR-02**: `col ||| 'query'`, `col ### 'query'`, `col === 'query'` parse to `exp.Operator` AST nodes with the correct operator symbol
- [ ] **PAR-03**: `col <=> '[0.1,0.2]'` parses to an `exp.Operator` AST node with operator `<=>`
- [ ] **PAR-04**: `MATCH(col, 'query')` parses to `exp.Anonymous(this="PARLANTE_MATCH", expressions=[col, 'query'])` — not routed to MySQL `MATCH ... AGAINST` parser
- [ ] **PAR-05**: `PHRASE_MATCH(col, 'query')` parses to `exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=[col, 'query'])`

### Generator

- [ ] **GEN-01**: `exp.Operator` with operator `@@@` generates `col @@@ 'query'` (native symbol, not `OPERATOR(paradedb.@@@)`)
- [ ] **GEN-02**: Same native output for `|||`, `###`, `===`, `<=>`
- [ ] **GEN-03**: `exp.Anonymous("PARLANTE_MATCH", [col, query])` generates `MATCH(col, query)` preserving exact case
- [ ] **GEN-04**: `exp.Anonymous("PARLANTE_PHRASE_MATCH", [col, query])` generates `PHRASE_MATCH(col, query)` preserving exact case
- [ ] **GEN-05**: All other `exp.Anonymous` expressions fall through to default Postgres generator behavior

### Tests

- [ ] **TST-01**: `tests/dialects/test_parlante.py` created following sqlglot dialect test conventions
- [ ] **TST-02**: `validate_identity()` round-trip for each operator: parse → generate produces identical SQL
- [ ] **TST-03**: `validate_identity()` round-trip for `MATCH` and `PHRASE_MATCH` function calls
- [ ] **TST-04**: Regression: `@@` (tsvector) and `<->` (L2 distance) parse correctly and unchanged under Parlante dialect
- [ ] **TST-05**: Regression: full Postgres test suite passes with Parlante dialect

## v2 Requirements

### CustomDremio dialect

- **DREMIO-01**: `sqlglot.parse_one(sql, dialect="custom_dremio")` resolves the CustomDremio dialect
- **DREMIO-02**: Nessie `AT BRANCH` syntax parses to `exp.Table` with `meta["catalog_branch"]`
- **DREMIO-03**: `CREATE [OR REPLACE] VDS` statements parse and generate correctly
- **DREMIO-04**: All Dremio-specific functions preserve their names round-trip

## Out of Scope

| Feature | Reason |
|---------|--------|
| Parlante library migration | Done by library maintainer after this fork ships — not part of this milestone |
| Changes to upstream sqlglot base classes | Fork extends only, never modifies base behavior |
| `Dialects` enum entry for PARLANTE | Auto-registration via metaclass is sufficient; typed enum constant is a cosmetic addition, deferred |
| CustomDremio dialect | Separate concern, not blocking Parlante library adoption |
| Operator precedence / expression types beyond exp.Operator | Parlante operators are binary infix — no new expression classes needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REG-01 | Phase 1 | Pending |
| TOK-01 | Phase 1 | Pending |
| TOK-02 | Phase 1 | Pending |
| TOK-03 | Phase 1 | Pending |
| TOK-04 | Phase 1 | Pending |
| TOK-05 | Phase 1 | Pending |
| TOK-06 | Phase 1 | Pending |
| TOK-07 | Phase 1 | Pending |
| PAR-01 | Phase 2 | Pending |
| PAR-02 | Phase 2 | Pending |
| PAR-03 | Phase 2 | Pending |
| PAR-04 | Phase 2 | Pending |
| PAR-05 | Phase 2 | Pending |
| GEN-01 | Phase 2 | Pending |
| GEN-02 | Phase 2 | Pending |
| GEN-03 | Phase 2 | Pending |
| GEN-04 | Phase 2 | Pending |
| GEN-05 | Phase 2 | Pending |
| TST-01 | Phase 2 | Pending |
| TST-02 | Phase 2 | Pending |
| TST-03 | Phase 2 | Pending |
| TST-04 | Phase 2 | Pending |
| TST-05 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 — roadmap created, phase mapping confirmed*
