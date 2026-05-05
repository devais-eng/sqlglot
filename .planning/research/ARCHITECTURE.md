# Architecture Patterns

**Domain:** Adding the Parlante dialect (Postgres superset) to sqlglot
**Researched:** 2026-04-07

## Recommended Architecture

A new dialect in sqlglot consists of up to four files:

```
sqlglot/dialects/parlante.py       # Dialect class (orchestrator)
sqlglot/parsers/parlante.py        # ParlantParser (optional, if parsing differs)
sqlglot/generators/parlante.py     # ParlantGenerator (optional, if generation differs)
```

The dialect file in `sqlglot/dialects/` is always required. The parser and generator files in their respective subpackages are required only when Parlante's behavior deviates from Postgres. The separation of parser/generator into subpackages is standard for all 34 existing dialects.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `sqlglot/dialects/parlante.py` | Dialect-level feature flags, Tokenizer inner class, registration with metaclass, assembly of Parser/Generator | `__init__.py`, `dialect.py` metaclass |
| `sqlglot/parsers/parlante.py` | SQL token → AST overrides specific to Parlante | Imported by the dialect file via `Parser = ParlantParser` |
| `sqlglot/generators/parlante.py` | AST → SQL generation overrides specific to Parlante | Imported by the dialect file via `Generator = ParlantGenerator` |
| `sqlglot/dialects/__init__.py` | Lazy-import index; the `DIALECTS` list drives lazy loading | Consumed by `dialect.py`'s `_Dialect` metaclass |

### Inheritance Chain (confirmed from Redshift and Materialize)

```
Dialect (dialect.py)
  └── Postgres (dialects/postgres.py)
        └── Parlante (dialects/parlante.py)

PostgresParser (parsers/postgres.py)
  └── ParlantParser (parsers/parlante.py)

PostgresGenerator (generators/postgres.py)
  └── ParlantGenerator (generators/parlante.py)
```

The Tokenizer inner class inside `Parlante` must inherit from `Postgres.Tokenizer`, not the base `Tokenizer`. See Redshift for the exact pattern:

```python
class Tokenizer(Postgres.Tokenizer):
    KEYWORDS = {**Postgres.Tokenizer.KEYWORDS, ...}
```

## How Dialect Registration Works

**Source:** `sqlglot/dialects/__init__.py` lines 67–126 (verified) and `sqlglot/dialects/dialect.py` lines 137–232 (verified).

Registration is fully automatic via the `_Dialect` metaclass. The flow is:

1. The metaclass `__new__` fires when Python defines the `Parlante` class.
2. It calls `Dialects.__members__.get("PARLANTE")` — if there is a matching `Dialects` enum entry, it registers under `enum.value`; otherwise it registers under `clsname.lower()` (i.e., `"parlante"`).
3. Therefore, calling `sqlglot.parse_one("...", dialect="parlante")` works once the module is imported — no additional wiring needed.

### Required change in `__init__.py`

The `DIALECTS` list in `sqlglot/dialects/__init__.py` (lines 67–100) drives lazy loading. `MODULE_BY_DIALECT` maps each name to `name.lower()` as the module filename. Adding `"Parlante"` to this list:

- Makes `from sqlglot.dialects import Parlante` work without an explicit import.
- Ensures `Dialect.classes` enumerates Parlante (the `classes` property checks `len(DIALECT_MODULE_NAMES) != len(cls._classes)` and loads any gaps).
- Satisfies the `_try_load` path in `_Dialect`.

**Single line addition to `DIALECTS` list:**
```python
DIALECTS = [
    ...
    "Parlante",   # add here, alphabetical position between Oracle and Postgres
    "Postgres",
    ...
]
```

### Optional: `Dialects` enum entry

Adding a `PARLANTE = "parlante"` entry to the `Dialects` enum in `dialect.py` allows using the enum for type-safe dialect references (e.g., `dialect=Dialects.PARLANTE`). It is not required for string-based lookup (`dialect="parlante"`) to work — the metaclass falls back to `clsname.lower()` when no enum entry is found. Omit it for a minimal-scope first milestone; add it if the dialect needs to be referenced by enum anywhere.

## mypyc Compilation Scope

**Source:** `sqlglotc/setup.py` `_source_files()` function (lines 44–74, verified).

The mypyc build explicitly enumerates what it compiles. The `_source_files()` function compiles:

- Top-level files: `errors.py`, `generator.py`, `helper.py`, `parser.py`, `schema.py`, `serde.py`, `time.py`, `tokenizer_core.py`, `trie.py`
- All `.py` files in `expressions/`, `generators/`, `parsers/` (via `_subpkg_files(src_dir, "parsers")` with no explicit list — it uses `os.listdir`, so new files are picked up automatically)
- A curated subset of `optimizer/`
- `executor/table.py`

**Dialects are not compiled.** `sqlglot/dialects/` is absent from `_source_files()`. New dialect files in `sqlglot/dialects/` never require any change to the mypyc build.

However, if Parlante needs a dedicated parser file (`sqlglot/parsers/parlante.py`) or generator file (`sqlglot/generators/parlante.py`), those files **will be compiled automatically** because `_subpkg_files` uses `os.listdir` on the entire `parsers/` and `generators/` directories. No changes to `sqlglotc/setup.py` are needed.

## Data Flow for a New Dialect

```
User: parse_one("...", dialect="parlante")
  → Dialect.get("parlante")
  → _Dialect._try_load("parlante")
  → importlib.import_module("sqlglot.dialects.parlante")
  → Parlante class already registered by metaclass __new__ on import
  → Parlante.tokenizer_class = Parlante.Tokenizer (inherits Postgres.Tokenizer)
  → Parlante.parser_class = ParlantParser (inherits PostgresParser)
  → Parlante.generator_class = ParlantGenerator (inherits PostgresGenerator)
```

## Patterns to Follow

### Pattern 1: Postgres superset dialect (use Redshift as the reference)

`sqlglot/dialects/parlante.py`:
```python
from __future__ import annotations

from sqlglot.dialects.postgres import Postgres
from sqlglot.generators.parlante import ParlantGenerator
from sqlglot.parsers.parlante import ParlantParser
from sqlglot.tokens import TokenType


class Parlante(Postgres):
    # Override feature flags here

    class Tokenizer(Postgres.Tokenizer):
        KEYWORDS = {
            **Postgres.Tokenizer.KEYWORDS,
            # Parlante-specific keywords
        }

    Parser = ParlantParser

    Generator = ParlantGenerator
```

`sqlglot/parsers/parlante.py`:
```python
from sqlglot.parsers.postgres import PostgresParser


class ParlantParser(PostgresParser):
    # Override FUNCTIONS, STATEMENT_PARSERS, etc.
    pass
```

`sqlglot/generators/parlante.py`:
```python
from sqlglot.generators.postgres import PostgresGenerator


class ParlantGenerator(PostgresGenerator):
    # Override TRANSFORMS, TYPE_MAPPING, or add *_sql() methods
    pass
```

### Pattern 2: Minimal dialect (use Materialize as the reference)

If Parlante only diverges in generation (no new syntax to parse), the dialect file can inline everything and omit the separate parser file entirely. Materialize does this — it only has a `Generator = MaterializeGenerator` line with no Tokenizer override.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Registering the dialect manually

The metaclass handles registration automatically. Never call `_Dialect._classes["parlante"] = Parlante` manually — it creates double registration and ordering bugs.

### Anti-Pattern 2: Adding dialect file to mypyc source list

`sqlglot/dialects/` is intentionally excluded from mypyc. Do not add dialect files to `sqlglotc/setup.py`.

### Anti-Pattern 3: Inheriting from base `Tokenizer` instead of `Postgres.Tokenizer`

The inner Tokenizer class must inherit from `Postgres.Tokenizer` so that all Postgres-specific token overrides (operators, keywords, heredoc strings, etc.) are inherited. Using bare `tokens.Tokenizer` discards all Postgres-specific token work.

### Anti-Pattern 4: Adding `Dialects` enum entry and forgetting `__init__.py`, or vice versa

These are independent. The enum entry controls type-safe access; the `DIALECTS` list controls lazy loading. Both can be omitted (class name lowercased is used for lookup), but if either is added, both should be kept consistent.

## New vs Modified Files

| File | Status | Required | Notes |
|------|--------|----------|-------|
| `sqlglot/dialects/parlante.py` | New | Yes | Dialect orchestrator |
| `sqlglot/parsers/parlante.py` | New | If parse differs | Inherits PostgresParser |
| `sqlglot/generators/parlante.py` | New | If generation differs | Inherits PostgresGenerator |
| `sqlglot/dialects/__init__.py` | Modified | Yes | Add `"Parlante"` to `DIALECTS` list |
| `sqlglot/dialects/dialect.py` | Modified | No | Add `PARLANTE = "parlante"` to `Dialects` enum only if enum access is needed |
| `sqlglotc/setup.py` | Not modified | No | parsers/ and generators/ are auto-discovered; dialects/ is excluded by design |
| `tests/dialects/test_parlante.py` | New | Yes (per CLAUDE.md) | Dialect test file |

## Sources

- `sqlglot/dialects/__init__.py` (lines 67–126): DIALECTS list, lazy-load mechanism — HIGH confidence (read directly)
- `sqlglot/dialects/dialect.py` (lines 137–232): `_Dialect` metaclass, `__new__` registration, `Dialects` enum — HIGH confidence (read directly)
- `sqlglot/dialects/redshift.py`, `sqlglot/dialects/materialize.py`: Postgres superset patterns — HIGH confidence (read directly)
- `sqlglot/parsers/redshift.py`, `sqlglot/generators/redshift.py`, `sqlglot/parsers/materialize.py`, `sqlglot/generators/materialize.py`: Parser/Generator separation pattern — HIGH confidence (read directly)
- `sqlglotc/setup.py` (lines 44–74): mypyc compilation scope — HIGH confidence (read directly)
