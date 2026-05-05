# Technology Stack

**Project:** Parlante dialect for sqlglot fork
**Researched:** 2026-04-07
**Confidence:** HIGH — all findings verified against codebase files

---

## What Needs to Be Built

One new file plus two one-line edits:

| Artifact | Path | Change |
|----------|------|--------|
| New dialect file | `sqlglot/dialects/parlante.py` | Create |
| Dialect list | `sqlglot/dialects/__init__.py` | Add `"Parlante"` to `DIALECTS` |
| Dialects enum (optional) | `sqlglot/dialects/dialect.py` | Add `PARLANTE = "parlante"` — not required, but makes `Dialects.PARLANTE` available |

**No other files need to change.** No separate parsers/ or generators/ file is required — all three inner classes can live inline in `parlante.py`.

---

## Core APIs Verified Against Codebase

### Registration

**`sqlglot/dialects/__init__.py`** — `DIALECTS` is a plain list of class name strings:

```python
DIALECTS = [
    ...
    "Parlante",   # add here alphabetically
    ...
]
```

`MODULE_BY_DIALECT = {name: name.lower() for name in DIALECTS}` automatically derives the module name `"parlante"`.

The `_Dialect` metaclass (`dialect.py:229-232`) auto-registers every `Dialect` subclass when the class is defined:

```python
enum = Dialects.__members__.get(clsname.upper())
cls._classes[enum.value if enum is not None else clsname.lower()] = klass
```

`"Parlante".upper()` → `"PARLANTE"` is not in `Dialects.__members__` (unless you add it), so it falls back to `clsname.lower()` = `"parlante"`. This means `dialect="parlante"` works immediately. `SingleStore` in this codebase is evidence: it is NOT in the `Dialects` enum but IS in `DIALECTS` and resolves via the fallback path.

To also expose `Dialects.PARLANTE` (useful for type-safe dialect selection), add to `dialect.py`:

```python
PARLANTE = "parlante"
```

This is optional for runtime but expected for consistency with other dialects like `EXASOL`.

---

### Tokenizer — Adding Multi-Character Operators

**File:** `sqlglot/dialects/parlante.py` inline class

**Pattern verified in:** `postgres.py`, `duckdb.py`, `singlestore.py`

```python
class Tokenizer(Postgres.Tokenizer):
    KEYWORDS = {
        **Postgres.Tokenizer.KEYWORDS,
        "@@@": TokenType.OPERATOR,
        "|||": TokenType.OPERATOR,
        "###": TokenType.OPERATOR,
        "===": TokenType.OPERATOR,
        "<=>": TokenType.OPERATOR,   # overrides base NULLSAFE_EQ
    }
```

**Why this works:** `_TokenizerBase.__init_subclass__` (tokens.py:108-116) builds `_KEYWORD_TRIE` from keys that contain a SINGLE_TOKEN char. `@` is `SINGLE_TOKENS["@"]`, `|` is `SINGLE_TOKENS["|"]`, `#` is `SINGLE_TOKENS["#"]`, `=` is `SINGLE_TOKENS["="]`, `<` is `SINGLE_TOKENS["<"]` — so all five symbols enter the trie and are matched greedily before individual chars.

**Critical note on `<=>` conflict:** The base tokenizer (`tokens.py:217`) maps `"<=>": TokenType.NULLSAFE_EQ`. The Postgres tokenizer does not override this. By adding `"<=>": TokenType.OPERATOR` to Parlante's KEYWORDS, the Parlante tokenizer overrides it. Verify this override takes effect by checking that `Postgres.Tokenizer.KEYWORDS` is spread first (it is, via `**Postgres.Tokenizer.KEYWORDS`).

**Why `TokenType.OPERATOR`:** Existing token types like `DAT` (`@@`) are already claimed by Postgres for `@@` (tsvector match). Using `TokenType.OPERATOR` for Parlante's custom operators is correct because:
- No existing token type is available that is semantically neutral
- The RANGE_PARSERS entry for `TokenType.OPERATOR` will be overridden (see Parser section below)
- This avoids adding new entries to `tokenizer_core.py` (mypyc-compiled, IntEnum values are baked in)

---

### Parser — FUNCTIONS Dict and RANGE_PARSERS

**Files verified:** `parsers/postgres.py`, `parser.py`

#### MATCH / PHRASE_MATCH via FUNCTIONS

```python
from sqlglot.parsers.postgres import PostgresParser

class Parser(PostgresParser):
    FUNCTIONS = {
        **PostgresParser.FUNCTIONS,
        "MATCH": lambda args: exp.Anonymous(this="PARLANTE_MATCH", expressions=args),
        "PHRASE_MATCH": lambda args: exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=args),
    }
```

**Why this works:**
- `MATCH` in Postgres tokenizes as `VAR` (Postgres does not add `"MATCH"` to its KEYWORDS). `VAR` is in `FUNC_TOKENS` (`parser.py:840`), so `_parse_function_call` proceeds to the `FUNCTIONS` lookup.
- The lambda receives the parsed arg list and returns an `exp.Anonymous` node.
- `exp.Anonymous` (confirmed at `expressions/core.py:1943`) has `arg_types = {"this": True, "expressions": False}` and `is_var_len_args = True`. The `.name` property returns `self.this` when `this` is a string.

**Do NOT use a dedicated expression class for PARLANTE_MATCH** — these are internal names that only exist transiently in the AST for Parlante→Parlante generation. `exp.Anonymous` is correct here.

#### Custom Binary Operators via RANGE_PARSERS

**Critical finding:** The spec draft maps `@@@` etc. to `TokenType.OPERATOR` and relies on `_parse_operator`. This is wrong. `_parse_operator` (`parser.py:9838-9857`) immediately tries to match `TokenType.L_PAREN`. With no `(` after `@@@`, it breaks and returns `this` — the operator token is consumed but the `exp.Operator` node is never created.

**Correct implementation:** Override `RANGE_PARSERS` to intercept `TokenType.OPERATOR` tokens and dispatch based on `self._prev.text` (the operator symbol just consumed):

```python
from sqlglot.parser import binary_range_parser

_PARLANTE_NATIVE_OPS = frozenset({"@@@", "|||", "###", "===", "<=>"})

class Parser(PostgresParser):
    FUNCTIONS = { ... }   # as above

    RANGE_PARSERS = {
        **PostgresParser.RANGE_PARSERS,
        TokenType.OPERATOR: lambda self, this: (
            self.expression(
                exp.Operator(
                    this=this,
                    operator=self._prev.text,
                    expression=self._parse_bitwise(),
                )
            )
            if self._prev.text in _PARLANTE_NATIVE_OPS
            else self._parse_operator(this)
        ),
    }
```

**How `self._prev.text` is available:** After `_match_set(self.RANGE_PARSERS)` at `parser.py:5681`, `self._prev` is the consumed `@@@` token. `self._prev.text` is the exact symbol string. This pattern is used throughout the codebase.

**`exp.Operator` structure** (verified at `expressions/core.py:2181`): `arg_types = {"this": True, "operator": True, "expression": True}`. Store the native symbol string (`"@@@"`) in `operator`. The generator reads this field.

---

### Generator — anonymous_sql Auto-Discovery and TRANSFORMS

**File:** `sqlglot/generators/postgres.py` (verified), `sqlglot/generator.py` (verified)

**Auto-discovery mechanism** (`generator.py:77-92`):

```python
def _build_dispatch(cls):
    dispatch = dict(cls.TRANSFORMS)
    for attr_name in dir(cls):
        if not attr_name.endswith("_sql") or attr_name.startswith("_"):
            continue
        expr_key = attr_name[:-4]               # strip "_sql"
        expr_cls = exp.EXPR_CLASSES.get(expr_key)  # lookup by cls.key = cls.__name__.lower()
        if expr_cls and expr_cls not in dispatch:
            dispatch[expr_cls] = getattr(cls, attr_name)
    return dispatch
```

`exp.EXPR_CLASSES` is keyed by `cls.key = cls.__name__.lower()` (`expressions/core.py:106`). So `"anonymous"` maps to `exp.Anonymous`, and the method `anonymous_sql` is auto-discovered.

**Key rule:** Auto-discovery only applies if the expression class is NOT already in `TRANSFORMS`. Since the Postgres generator does not add `exp.Anonymous` to its `TRANSFORMS`, our `anonymous_sql` override will be auto-discovered without needing a `TRANSFORMS` entry.

**TRANSFORMS for exp.Operator:** The base generator's `TRANSFORMS` (`generator.py:225`) has:

```python
exp.Operator: lambda self, e: self.binary(e, ""),  # The operator is produced in `binary`
```

`binary()` (`generator.py:4248-4267`) reads `op_func = node.args.get("operator")` and, if set, wraps it as `OPERATOR({op_func})`. For Parlante operators, `operator` will be `"@@@"` (a string), so `binary()` would emit `OPERATOR(@@@)` — wrong.

**Correct implementation: use TRANSFORMS with a function that checks the operator field:**

```python
def _parlante_operator_sql(self, expression: exp.Operator) -> str:
    op = expression.args.get("operator", "")
    if isinstance(op, str) and op in _PARLANTE_NATIVE_OPS:
        return f"{self.sql(expression, 'this')} {op} {self.sql(expression, 'expression')}"
    return self.binary(expression, "")
```

Per CLAUDE.md rule 1: since this has a single entry point, use auto-discovered method syntax, NOT a TRANSFORMS lambda. Name it `operator_sql` (maps to `exp.Operator` via `exp.EXPR_CLASSES["operator"]`). But wait — the base generator has `exp.Operator` in `TRANSFORMS` (not as an auto-discovered method). The auto-discovery only adds to dispatch if `expr_cls not in dispatch`. Since `exp.Operator` IS already in `TRANSFORMS`, the auto-discovered `operator_sql` will NOT override it.

**Resolution:** You must use `TRANSFORMS` to override `exp.Operator`:

```python
class Generator(PostgresGenerator):
    TRANSFORMS = {
        **PostgresGenerator.TRANSFORMS,
        exp.Operator: _parlante_operator_sql,
    }

    def anonymous_sql(self, expression: exp.Anonymous) -> str:
        name = expression.name
        if name == "PARLANTE_MATCH":
            return self.func("MATCH", *expression.expressions, normalize=False)
        if name == "PARLANTE_PHRASE_MATCH":
            return self.func("PHRASE_MATCH", *expression.expressions, normalize=False)
        return super().anonymous_sql(expression)
```

`_parlante_operator_sql` must be a module-level function (not a method), since it's referenced in TRANSFORMS before the class body is complete:

```python
def _parlante_operator_sql(self: "ParlanteSupertype", expression: exp.Operator) -> str:
    op = expression.args.get("operator", "")
    if isinstance(op, str) and op in _PARLANTE_NATIVE_OPS:
        return f"{self.sql(expression, 'this')} {op} {self.sql(expression, 'expression')}"
    return self.binary(expression, "")
```

This pattern is precedented: `postgres/generators.py` uses module-level functions like `_date_add_sql`, `_date_diff_sql`, etc. that are referenced in `TRANSFORMS`.

Per CLAUDE.md rule 1: "Only use TRANSFORMS for simple one-liners like `rename_func("OTHER_NAME")` or lambdas or functions with multiple entry points." `exp.Operator` already has a TRANSFORMS entry in the parent, so `TRANSFORMS` override is required regardless of complexity.

**`self.func(name, *args, normalize=False)`** — confirmed signature at `generator.py:4295-4304`. `normalize=False` preserves exact case of function name. Required for `MATCH` and `PHRASE_MATCH` which are uppercase names that must not be lowercased.

---

## Complete File Structure

### `sqlglot/dialects/parlante.py`

```python
from __future__ import annotations

from sqlglot import exp
from sqlglot.dialects.postgres import Postgres
from sqlglot.generators.postgres import PostgresGenerator
from sqlglot.parsers.postgres import PostgresParser
from sqlglot.tokens import TokenType

_PARLANTE_NATIVE_OPS: frozenset[str] = frozenset({"@@@", "|||", "###", "===", "<=>"})


def _parlante_operator_sql(self: PostgresGenerator, expression: exp.Operator) -> str:
    op = expression.args.get("operator", "")
    if isinstance(op, str) and op in _PARLANTE_NATIVE_OPS:
        return f"{self.sql(expression, 'this')} {op} {self.sql(expression, 'expression')}"
    return self.binary(expression, "")


class Parlante(Postgres):
    class Tokenizer(Postgres.Tokenizer):
        KEYWORDS = {
            **Postgres.Tokenizer.KEYWORDS,
            "@@@": TokenType.OPERATOR,
            "|||": TokenType.OPERATOR,
            "###": TokenType.OPERATOR,
            "===": TokenType.OPERATOR,
            "<=>": TokenType.OPERATOR,
        }

    class Parser(PostgresParser):
        FUNCTIONS = {
            **PostgresParser.FUNCTIONS,
            "MATCH": lambda args: exp.Anonymous(this="PARLANTE_MATCH", expressions=args),
            "PHRASE_MATCH": lambda args: exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=args),
        }

        RANGE_PARSERS = {
            **PostgresParser.RANGE_PARSERS,
            TokenType.OPERATOR: lambda self, this: (
                self.expression(
                    exp.Operator(
                        this=this,
                        operator=self._prev.text,
                        expression=self._parse_bitwise(),
                    )
                )
                if self._prev.text in _PARLANTE_NATIVE_OPS
                else self._parse_operator(this)
            ),
        }

    class Generator(PostgresGenerator):
        TRANSFORMS = {
            **PostgresGenerator.TRANSFORMS,
            exp.Operator: _parlante_operator_sql,
        }

        def anonymous_sql(self, expression: exp.Anonymous) -> str:
            name = expression.name
            if name == "PARLANTE_MATCH":
                return self.func("MATCH", *expression.expressions, normalize=False)
            if name == "PARLANTE_PHRASE_MATCH":
                return self.func("PHRASE_MATCH", *expression.expressions, normalize=False)
            return super().anonymous_sql(expression)
```

### `sqlglot/dialects/__init__.py`

Add `"Parlante"` to the `DIALECTS` list (keep alphabetically sorted, between `"Oracle"` and `"Postgres"`).

### `sqlglot/dialects/dialect.py` (optional)

Add `PARLANTE = "parlante"` to `Dialects` enum, between `ORACLE` and `POSTGRES`. This enables `Dialects.PARLANTE` enum access. Not required for runtime resolution.

---

## Alternatives Considered

| Decision | Chosen | Alternative | Why Not |
|----------|--------|-------------|---------|
| Operator token type | `TokenType.OPERATOR` with RANGE_PARSERS override | Add new entries to `tokenizer_core.py` | Requires editing mypyc-compiled file, adds enum values that affect compiled code hash |
| Operator token type | `TokenType.OPERATOR` | Re-use `TokenType.DAT`, `ADJACENT`, etc. | Those token types have semantic meaning in Postgres and would break Postgres behavior when inherited |
| Inline vs split files | Inline in `parlante.py` | Separate `parsers/parlante.py`, `generators/parlante.py` | Parlante is a thin superset; split is only warranted for large dialects; Materialize uses split, but it's a larger dialect |
| MATCH function mapping | `exp.Anonymous` with prefix | New `exp.ParlanteMath` expression class | Dedicated class would require editing `expressions/` files; Anonymous is the correct type for dialect-specific transient nodes |
| Generator exp.Operator | TRANSFORMS entry | Auto-discovered `operator_sql` method | `exp.Operator` is already in base `TRANSFORMS`; auto-discovery skips classes already in dispatch (`generator.py:89`) |

---

## What NOT to Do (CLAUDE.md Rules Applied)

| Rule | Don't | Do Instead |
|------|-------|------------|
| Rule 1 (auto-naming) | Put `anonymous_sql` logic in TRANSFORMS | Define `def anonymous_sql(...)` method — it IS auto-discovered for `exp.Anonymous` |
| Rule 1 (exception) | Try to auto-discover `operator_sql` | Use TRANSFORMS — `exp.Operator` is already in parent TRANSFORMS, auto-discovery is blocked |
| Rule 2 (existing classes) | `exp.Anonymous(this="MATCH", ...)` directly in generator output | Use prefixed internal name `PARLANTE_MATCH` in parser; restore in generator |
| Rule 3 level 1 (generator helpers) | Build string with f-string | Use `self.func("MATCH", ..., normalize=False)` for the MATCH/PHRASE_MATCH output |
| Rule 10 (minimal) | Add `__init__` or docstrings to Parlante | None needed; class body is declaration only |

---

## F-String Exception in `_parlante_operator_sql`

`_parlante_operator_sql` uses an f-string (`f"{self.sql(...)} {op} {self.sql(...)}"`) — this looks like it violates CLAUDE.md Rule 3. However:

1. The base generator's `_date_diff_sql` and `_date_add_sql` also use f-strings for binary expressions
2. Binary expression generation is the one case where `self.sql(e, 'this') + " op " + self.sql(e, 'expression')` is standard and safe — the operator symbol is a trusted constant from our own frozenset
3. `exp.Binary` doesn't have a higher-level builder that applies here

The alternative would be `return self.binary(expression, op)` — but `binary()` doesn't accept a plain string `op` positionally for `exp.Operator` without also calling `OPERATOR(...)` wrapping. Looking at `binary()` source: `op_func = node.args.get("operator")` — if `operator` is a string, it does `f"OPERATOR({self.sql(op_func)})"`. We cannot use `self.binary(expression, op)` with the existing field because it wraps it.

**Best approach without f-string:** Store the native op in a separate arg or clear the `operator` field before calling `binary`. But that mutates the AST. The f-string is acceptable here per the pattern in the Postgres generator itself.

---

## Sources

- `sqlglot/dialects/__init__.py` — registration mechanism (verified)
- `sqlglot/dialects/dialect.py:229-232` — metaclass `__new__`, `_classes` key derivation (verified)
- `sqlglot/dialects/dialect.py:80-115` — `Dialects` enum, `SINGLESTORE` absence as precedent (verified)
- `sqlglot/dialects/postgres.py` — Tokenizer KEYWORDS pattern for multi-char operators (verified)
- `sqlglot/dialects/singlestore.py` — pattern for dialect without enum entry (verified)
- `sqlglot/tokenizer_core.py:43,358` — `NULLSAFE_EQ`, `OPERATOR` token types (verified)
- `sqlglot/tokens.py:108-116` — trie construction with SINGLE_TOKEN chars (verified)
- `sqlglot/tokens.py:217` — `"<=>": TokenType.NULLSAFE_EQ` in base (verified)
- `sqlglot/parser.py:5681-5682` — `RANGE_PARSERS` dispatch, `self._prev` availability (verified)
- `sqlglot/parser.py:9838-9857` — `_parse_operator` logic showing `(` requirement (verified)
- `sqlglot/parser.py:807-856` — `FUNC_TOKENS`, confirming `VAR` is included, `MATCH` is not (verified)
- `sqlglot/parser.py:6780` — `FUNC_TOKENS` check in `_parse_function_call` (verified)
- `sqlglot/generator.py:77-92` — `_build_dispatch` auto-discovery logic (verified)
- `sqlglot/generator.py:225` — `exp.Operator` in base TRANSFORMS (verified)
- `sqlglot/generator.py:4248-4267` — `binary()` method, `OPERATOR(...)` wrapping behavior (verified)
- `sqlglot/generator.py:4295-4304` — `func()` signature including `normalize` param (verified)
- `sqlglot/expressions/core.py:106` — `cls.key = cls.__name__.lower()` auto-key (verified)
- `sqlglot/expressions/core.py:1943-1949` — `exp.Anonymous` class, `.name` property (verified)
- `sqlglot/expressions/core.py:2181-2183` — `exp.Operator` arg_types (verified)
- `sqlglot/expressions/__init__.py:51` — `EXPR_CLASSES` construction (verified)
