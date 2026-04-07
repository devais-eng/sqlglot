# Research Summary — Parlante Dialect v1.0

**Synthesized:** 2026-04-07
**Confidence:** HIGH — all findings verified against live codebase source files

---

## Executive Summary

Replace the regex-based SQL rewriter with a proper sqlglot dialect. Parlante is a thin Postgres superset adding five binary operators (`@@@`, `|||`, `###`, `===`, `<=>`) and two function aliases (`MATCH`, `PHRASE_MATCH`). The entire implementation is **one new file** (`sqlglot/dialects/parlante.py`) plus **one line** in `sqlglot/dialects/__init__.py`.

---

## Stack Additions

No new dependencies. Implementation uses only existing sqlglot infrastructure:
- `Postgres.Tokenizer.KEYWORDS` — extend with operator entries
- `Postgres.Parser.FUNCTIONS` + `FUNCTION_PARSERS` — override MATCH handling
- `Postgres.Generator.TRANSFORMS` + `anonymous_sql` — operator/function output
- `sqlglot/dialects/__init__.py` `DIALECTS` list — one-line registration

---

## Feature Table Stakes (all required)

| Feature | Status | Notes |
|---------|--------|-------|
| `@@@`, `\|\|\|`, `###`, `===` tokenized as single tokens | Required | Trie longest-match handles correctly once registered |
| `<=>` tokenized as `TokenType.OPERATOR` | Required | **Conflict**: base maps `<=>` to `TokenType.NULLSAFE_EQ` — must override |
| `MATCH(col, query)` parsed to `exp.Anonymous("PARLANTE_MATCH")` | Required | **Conflict**: `FUNCTION_PARSERS["MATCH"]` exists (MySQL syntax) — must remove |
| `PHRASE_MATCH(col, query)` parsed to `exp.Anonymous("PARLANTE_PHRASE_MATCH")` | Required | No conflict, straightforward FUNCTIONS entry |
| Generator: native operator output (`@@@` not `OPERATOR(paradedb.@@@)`) | Required | Must use `TRANSFORMS[exp.Operator]` — auto-discovery silently ignored |
| Generator: `MATCH`/`PHRASE_MATCH` name restoration | Required | `anonymous_sql` override — IS auto-discovered (no TRANSFORMS needed) |
| Dialect registration (`dialect="parlante"`) | Required | Add `"Parlante"` to `DIALECTS` in `__init__.py` |

---

## Critical Watch-Outs

### 1. MATCH / FUNCTION_PARSERS collision (Highest Risk)
`FUNCTION_PARSERS` takes priority over `FUNCTIONS` for string-keyed names. `parser.Parser.FUNCTION_PARSERS["MATCH"]` invokes `_parse_match_against()` (MySQL `MATCH ... AGAINST` syntax). Adding `"MATCH"` to `FUNCTIONS` alone is **dead code**. Must also explicitly remove `"MATCH"` from `FUNCTION_PARSERS` in Parlante's Parser — exactly as ClickHouse does at `parsers/clickhouse.py:362`.

### 2. RANGE_PARSERS bug in original spec
The spec draft proposes adding `@@@` etc. to `KEYWORDS` as `TokenType.OPERATOR`. This is necessary but not sufficient. The `RANGE_PARSERS[TokenType.OPERATOR]` handler calls `_parse_operator()` which immediately expects a `(` token — native `@@@` has no `(`. Must override `RANGE_PARSERS[TokenType.OPERATOR]` with a lambda that reads `self._prev.text` and builds `exp.Operator` directly (the token text is available post-consumption at `parser.py:5681-5682`).

### 3. exp.Operator TRANSFORMS vs auto-discovery
`_build_dispatch` (`generator.py:77-92`) adds auto-discovered `*_sql` methods **only for expression types not already in TRANSFORMS**. `exp.Operator` is in `Postgres.Generator.TRANSFORMS`. Defining `operator_sql(self, e)` in Parlante's Generator would be **silently ignored**. Must use `TRANSFORMS = {**Postgres.Generator.TRANSFORMS, exp.Operator: ...}`.

### 4. TokenType enum ordering (mypyc)
Any new `TokenType` values must be appended at the **end** of the enum in `tokenizer_core.py` to avoid reordering compiled integer values in the mypyc C extension.

### 5. `<->` must not be touched
L2 distance (`<->`) already parses as `exp.Distance` via `TokenType.LR_ARROW` in the base parser. Do not add it to Parlante's KEYWORDS.

---

## Architecture

- **Files to create:** `sqlglot/dialects/parlante.py`
- **Files to modify:** `sqlglot/dialects/__init__.py` (one line: add `"Parlante"` to `DIALECTS`)
- **Files NOT modified:** `parser.py`, `expressions.py`, `tokens.py`, `sqlglotc/setup.py`
- **mypyc scope:** `dialects/` is NOT compiled by mypyc — dialect file itself is pure Python. Only `parsers/` and `generators/` subdirs are compiled. No setup.py changes needed.
- **Registration:** `_Dialect` metaclass auto-registers `"parlante"` via `clsname.lower()` on class definition. `DIALECTS` list enables lazy loading from `parse_one(dialect="parlante")`.

---

## Suggested Phase Structure

**Phase 1 — Tokenizer + Scaffold**
Register dialect, add 5 operator entries to KEYWORDS trie. Verify each tokenizes as a single token. Foundation for all subsequent work.

**Phase 2 — Parser + Generator + Tests**
Remove `MATCH` from `FUNCTION_PARSERS`, add `FUNCTIONS` entries, override `RANGE_PARSERS[TokenType.OPERATOR]`, wire `TRANSFORMS[exp.Operator]`, add `anonymous_sql` override. Full round-trip tests.

---

## Confidence Gaps

- Explicit test needed: `@@` and `<->` unaffected after `<=>` remap
- `normalize=False` in `anonymous_sql` is load-bearing — needs casing assertion test
