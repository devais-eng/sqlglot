# sqlglot-parlante fork

## What This Is

A fork of sqlglot that embeds the Parlante SQL dialect natively inside the package. Parlante is a Postgres superset used by the Parlante library to support ParadeDB full-text search operators (`@@@`, `|||`, `###`, `===`) and pgvector distance operators (`<=>`). Moving the dialect inside sqlglot enables it to be mypyc-compiled alongside the rest of the package.

## Core Value

The Parlante library can use `sqlglot[c]` (compiled) without any regex preprocessing — native tokenizer handles Parlante syntax in a single pass.

## Current Milestone: v1.0 Parlante Dialect Creation

**Goal:** Implement the Parlante dialect as a native sqlglot dialect so it is mypyc-compilable and requires no external regex rewriting.

**Target features:**
- Tokenizer with Parlante operator token types (`@@@`, `|||`, `###`, `===`, `<=>`)
- Parser with `MATCH` / `PHRASE_MATCH` function mappings (to avoid SQL keyword collision)
- Generator that outputs native operator symbols and restores `MATCH`/`PHRASE_MATCH` names
- Dialect registration in `sqlglot/dialects/__init__.py`
- Tests covering round-trip parse → generate for all Parlante syntax

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Tokenizer recognizes `@@@`, `|||`, `###`, `===`, `<=>` as operator tokens
- [ ] Parser maps `MATCH(col, query)` to `exp.Anonymous("PARLANTE_MATCH", ...)` to avoid SQL keyword collision
- [ ] Parser maps `PHRASE_MATCH(col, query)` to `exp.Anonymous("PARLANTE_PHRASE_MATCH", ...)`
- [ ] Generator unwraps `PARLANTE_MATCH` → `MATCH` and `PARLANTE_PHRASE_MATCH` → `PHRASE_MATCH` in output
- [ ] Generator strips `OPERATOR(paradedb.X)` / `OPERATOR(pgvector.X)` back to native symbol
- [ ] Dialect registered as `"parlante"` in `sqlglot/dialects/__init__.py`
- [ ] Tests covering all Parlante-specific syntax (operators + functions)

### Out of Scope

- CustomDremio dialect — separate project, not part of this milestone
- Changes to upstream sqlglot parser behavior — extend only, never modify base
- Parlante library migration (consuming this fork) — done by library maintainer after fork ships

## Context

- **mypyc constraint**: `sqlglot[c]` compiles `Parser` and `Tokenizer` via mypyc. External Python code cannot subclass compiled classes, blocking `Parlante.Parser(Postgres.Parser)` from being defined outside the package.
- **Current workaround**: `rewrite_parlante_syntax()` in the Parlante library does ~8 regex passes over every query string before handing it to the Postgres parser (1 string-split pass + 7 substitution passes). Fires on every query even when no Parlante syntax is present.
- **Reference implementation**: `src/parlante/dialect.py` in `github.com/filippoGaffuriRiva/parlante` — contains the regex hack and the Generator logic to migrate.
- **Spec**: `PARLANTE_DIALECT.md` in this repo — detailed handoff document with exact code to implement.
- **Base dialect**: Parlante extends `Postgres` (not the base sqlglot dialect).

## Constraints

- **Compatibility**: Must not break any existing sqlglot tests — this is a fork, not a contribution to upstream
- **Scope**: Parlante dialect file must be self-contained; no changes to `expressions.py` or `parser.py` base classes
- **Style**: Follow sqlglot coding conventions (CLAUDE.md rules): auto-discovered generator methods over TRANSFORMS where possible, no f-string SQL generation

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MATCH → PARLANTE_MATCH rename in parser | `MATCH` is a SQL keyword that would collide; prefixed name avoids ambiguity | — Pending |
| Operators as `TokenType.OPERATOR` | Reuses existing Postgres `exp.Operator` expression, no new expression class needed | — Pending |
| Dialect lives in `sqlglot/dialects/parlante.py` | Standard location, auto-registration via metaclass | — Pending |

---
*Last updated: 2026-04-07 — v1.0 milestone started*
