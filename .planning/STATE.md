# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Native Parlante dialect — no regex preprocessing, mypyc-compilable
**Current focus:** Defining requirements for v1.0

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-07 — Milestone v1.0 started

## Accumulated Context

- `PARLANTE_DIALECT.md` in repo root is the detailed implementation spec — read this before planning any phase
- The Parlante library lives at `github.com/filippoGaffuriRiva/parlante`; `src/parlante/dialect.py` has the Generator logic to migrate
- Parlante extends `Postgres` dialect — all Postgres parsing behavior is inherited
- `<->` (L2 distance) already parses as `exp.Distance` in Postgres — do not add it to new token types
- `_native_operator_sql` function from the Parlante library should move into the fork's dialect file
- Codebase map available at `.planning/codebase/` (generated 2026-04-07)
