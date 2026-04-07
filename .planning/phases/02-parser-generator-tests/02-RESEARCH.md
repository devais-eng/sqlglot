# Phase 2: Parser + Generator + Tests - Research

**Researched:** 2026-04-07
**Domain:** sqlglot dialect parser, generator, and test infrastructure — Parlante superset of Postgres
**Confidence:** HIGH

## Summary

Phase 2 adds a `Parser` and `Generator` to the `Parlante` dialect so that `@@@`, `|||`, `###`, `===`, `<=>` survive a full parse → generate round-trip as native symbols, and `MATCH`/`PHRASE_MATCH` calls survive without being hijacked by the MySQL `MATCH ... AGAINST` parser.

The tokenizer from Phase 1 already classifies all five operators as `TokenType.OPERATOR`. The base parser's `RANGE_PARSERS[TokenType.OPERATOR]` handler (`_parse_operator`) expects `OPERATOR(schema.op)` parenthesized form — it tries `_match(L_PAREN)` first, finds none, and returns the LHS without consuming the operator or RHS. Parlante's Parser must override this entry with a handler that reads the already-consumed operator text from `self._prev.text` and directly constructs `exp.Operator`. The `MATCH` function is caught by `FUNCTION_PARSERS["MATCH"]` before `FUNCTIONS["MATCH"]` is reached — Parlante must remove that entry (following the ClickHouse pattern) and register its own `FUNCTIONS["MATCH"]` lambda. The base generator's `binary()` method wraps the `operator` field in `OPERATOR(...)` — Parlante must override `exp.Operator` in `TRANSFORMS` with a lambda that emits the symbol directly. `anonymous_sql` needs to be overridden to map `PARLANTE_MATCH` → `MATCH` and `PARLANTE_PHRASE_MATCH` → `PHRASE_MATCH`.

The established codebase pattern for new dialects that extend a Postgres-family parser/generator is to create separate files: `sqlglot/parsers/parlante.py` (`ParlanteParse(PostgresParser)`) and `sqlglot/generators/parlante.py` (`ParlanteGenerator(PostgresGenerator)`), then assign `Parser = ParlanteParse` and `Generator = ParlanteGenerator` in `sqlglot/dialects/parlante.py`.

**Primary recommendation:** Create `sqlglot/parsers/parlante.py` and `sqlglot/generators/parlante.py`, update `sqlglot/dialects/parlante.py`, and extend `tests/dialects/test_parlante.py` with round-trip tests.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PAR-01 | `col @@@ 'query'` parses to `exp.Operator` with operator `@@@` | Override `RANGE_PARSERS[TokenType.OPERATOR]` in ParlanteParse to read `self._prev.text` and build `exp.Operator` directly |
| PAR-02 | `|||`, `###`, `===` parse to `exp.Operator` nodes | Same RANGE_PARSERS override handles all `TokenType.OPERATOR` tokens |
| PAR-03 | `col <=> '[0.1,0.2]'` parses to `exp.Operator` with operator `<=>` | Phase 1 remapped `<=>` to `TokenType.OPERATOR`; same RANGE_PARSERS override handles it |
| PAR-04 | `MATCH(col, 'query')` parses to `exp.Anonymous(this="PARLANTE_MATCH", ...)` | Remove `"MATCH"` from `FUNCTION_PARSERS` (ClickHouse pattern); add `"MATCH"` to `FUNCTIONS` lambda |
| PAR-05 | `PHRASE_MATCH(col, 'query')` parses to `exp.Anonymous(this="PARLANTE_PHRASE_MATCH", ...)` | Add `"PHRASE_MATCH"` to `FUNCTIONS` lambda; no FUNCTION_PARSERS conflict |
| GEN-01 | `exp.Operator` with `@@@` generates `col @@@ 'query'` | Override `exp.Operator` in `TRANSFORMS` with lambda that emits `operator` field directly without `OPERATOR(...)` wrapper |
| GEN-02 | Same native output for `|||`, `###`, `===`, `<=>` | Same TRANSFORMS entry handles all `exp.Operator` nodes |
| GEN-03 | `exp.Anonymous("PARLANTE_MATCH", ...)` generates `MATCH(col, query)` | Override `anonymous_sql` to intercept name `PARLANTE_MATCH` and call `self.func("MATCH", ..., normalize=False)` |
| GEN-04 | `exp.Anonymous("PARLANTE_PHRASE_MATCH", ...)` generates `PHRASE_MATCH(col, query)` | Same `anonymous_sql` override handles `PARLANTE_PHRASE_MATCH` |
| GEN-05 | All other `exp.Anonymous` fall through to default behavior | `anonymous_sql` override calls `super().anonymous_sql(expression)` as default branch |
| TST-01 | `tests/dialects/test_parlante.py` follows sqlglot dialect test conventions | File already exists from Phase 1; extend with new test methods |
| TST-02 | `validate_identity()` round-trip for each operator | `self.validate_identity("col @@@ 'query'")` etc. in TestParlante |
| TST-03 | `validate_identity()` round-trip for MATCH and PHRASE_MATCH | `self.validate_identity("MATCH(col, 'query')")` etc. |
| TST-04 | Regression: `@@` and `<->` parse/generate correctly under Parlante | `@@` → `MatchAgainst` already works; `<->` → `Distance` already works (verified by running) |
| TST-05 | Full Postgres test suite passes with no new failures | Run `python -m unittest tests.dialects.test_postgres` before and after changes |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlglot.parsers.postgres.PostgresParser` | repo HEAD | Base class for ParlanteParse | Parlante is a Postgres superset; inherits all Postgres parser behavior |
| `sqlglot.generators.postgres.PostgresGenerator` | repo HEAD | Base class for ParlanteGenerator | Inherits all Postgres generation, including `matchagainst_sql` for `@@` round-trip |
| `sqlglot.expressions.core.exp.Operator` | repo HEAD | AST node for infix operators | Already defined with `arg_types = {"this": True, "operator": True, "expression": True}`; used by existing `OPERATOR(...)` parser |
| `sqlglot.expressions.core.exp.Anonymous` | repo HEAD | AST node for unrecognized functions | Used to represent MATCH/PHRASE_MATCH internally with prefixed names |
| `tests.dialects.test_dialect.Validator` | repo HEAD | Test base class | Provides `validate_identity()` and `validate_all()` helpers |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlglot.parser.binary_range_parser` | repo HEAD | Helper for building `RANGE_PARSERS` entries | Not needed here — we need custom operator text, not a fixed binary class |
| `sqlglot.generator.unsupported_args` | repo HEAD | Mark unsupported function args | Not needed for Phase 2 |

**Files to create:**
```
sqlglot/parsers/parlante.py       — ParlanteParse(PostgresParser)
sqlglot/generators/parlante.py    — ParlanteGenerator(PostgresGenerator)
```

**Files to modify:**
```
sqlglot/dialects/parlante.py      — add Parser = ParlanteParse, Generator = ParlanteGenerator
tests/dialects/test_parlante.py   — add Phase 2 test methods
```

## Architecture Patterns

### Recommended File Structure

```
sqlglot/
├── dialects/
│   └── parlante.py           # Tokenizer + Parser/Generator class assignments
├── parsers/
│   └── parlante.py           # ParlanteParse(PostgresParser)
└── generators/
    └── parlante.py           # ParlanteGenerator(PostgresGenerator)

tests/dialects/
└── test_parlante.py          # Phase 1 tokenizer tests + Phase 2 parser/generator tests
```

### Pattern 1: Parser/Generator in Separate Files (mandatory for dialects)

**What:** Define Parser and Generator classes in separate module files under `sqlglot/parsers/` and `sqlglot/generators/`, then assign them as class attributes in the dialect file.

**When to use:** Always, for every dialect. No dialect defines inline inner `class Parser` in the dialect file.

**Evidence:** Every Postgres-extending dialect (Redshift, RisingWave, Dune, etc.) follows this pattern. The metaclass (`_Dialect.__new__`) uses `klass.__dict__.get("Parser", ...)` to detect the assignment in the dialect's own `__dict__` — both inline class defs and class attribute assignments satisfy this.

**Example (from `sqlglot/dialects/risingwave.py`):**
```python
from sqlglot.parsers.risingwave import RisingWaveParser
from sqlglot.generators.risingwave import RisingWaveGenerator

class RisingWave(Postgres):
    Parser = RisingWaveParser
    Generator = RisingWaveGenerator
```

**Applied to Parlante (`sqlglot/dialects/parlante.py`):**
```python
from sqlglot.parsers.parlante import ParlanteParse
from sqlglot.generators.parlante import ParlanteGenerator

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

    Parser = ParlanteParse
    Generator = ParlanteGenerator
```

### Pattern 2: Override `RANGE_PARSERS[TokenType.OPERATOR]` for Bare Infix Operators

**What:** Override the `TokenType.OPERATOR` entry in `RANGE_PARSERS` with a handler that builds `exp.Operator` from the already-consumed operator token (`self._prev.text`).

**Why needed:** The base `_parse_operator` expects `OPERATOR(schema.op)` parenthesized form and immediately breaks out of its loop when no `L_PAREN` follows. Bare tokens like `@@@` are already consumed (as the OPERATOR token that triggered RANGE_PARSERS dispatch) but the RHS is never parsed.

**Mechanism verified in `sqlglot/parser.py` lines 5681-5682:** `_match_set(self.RANGE_PARSERS)` advances past the token, then calls `RANGE_PARSERS[self._prev.token_type](self, this)`. At the point of call, `self._prev` is the `@@@` token, `self._curr` is the RHS start.

**Example (`sqlglot/parsers/parlante.py`):**
```python
from sqlglot.parser import binary_range_parser
from sqlglot.parsers.postgres import PostgresParser
from sqlglot import exp
from sqlglot.tokens import TokenType


class ParlanteParse(PostgresParser):
    FUNCTION_PARSERS = {
        **{k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"},
    }

    FUNCTIONS = {
        **PostgresParser.FUNCTIONS,
        "MATCH": lambda args: exp.Anonymous(this="PARLANTE_MATCH", expressions=args),
        "PHRASE_MATCH": lambda args: exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=args),
    }

    RANGE_PARSERS = {
        **PostgresParser.RANGE_PARSERS,
        TokenType.OPERATOR: lambda self, this: self.expression(
            exp.Operator(
                this=this,
                operator=self._prev.text,
                expression=self._parse_bitwise(),
            )
        ),
    }
```

### Pattern 3: Remove FUNCTION_PARSERS Entry to Unblock FUNCTIONS Fallthrough

**What:** When a function name appears in `FUNCTION_PARSERS`, it intercepts the call before `FUNCTIONS` is consulted. To route a function to `FUNCTIONS` instead, remove it from `FUNCTION_PARSERS` in the subclass.

**Evidence:** ClickHouse uses this exact pattern at `sqlglot/parsers/clickhouse.py` line 363:
```python
FUNCTION_PARSERS = {
    **{k: v for k, v in parser.Parser.FUNCTION_PARSERS.items() if k != "MATCH"},
    ...
}
```

**Priority order (from `sqlglot/parser.py` lines 6785-6808):**
1. `FUNCTION_PARSERS.get(upper)` — checked first
2. `FUNCTIONS.get(upper)` — only reached if FUNCTION_PARSERS has no entry

**Applied to Parlante:** Remove `"MATCH"` from the spread, add custom lambdas to `FUNCTIONS`.

### Pattern 4: Override `exp.Operator` in Generator TRANSFORMS

**What:** Override `TRANSFORMS[exp.Operator]` to emit the operator symbol directly, bypassing the `binary()` method's `OPERATOR(...)` wrapping behavior.

**Why needed:** `generator.py` line 4259: `op = f"OPERATOR({self.sql(op_func)})"` — the `binary()` method wraps the `operator` field in `OPERATOR(...)` when it is truthy. There is no mechanism to opt out; the override must go in `TRANSFORMS`.

**Why auto-discovery fails:** `exp.Operator` is already registered in the base `Generator.TRANSFORMS` (line 225) and in `PostgresGenerator.TRANSFORMS` (via spread). An auto-discovered `operator_sql` method in `ParlanteGenerator` would be silently ignored because `TRANSFORMS` takes precedence for already-registered types.

**Example (`sqlglot/generators/parlante.py`):**
```python
from sqlglot import exp
from sqlglot.generators.postgres import PostgresGenerator


class ParlanteGenerator(PostgresGenerator):
    TRANSFORMS = {
        **PostgresGenerator.TRANSFORMS,
        exp.Operator: lambda self, e: f"{self.sql(e, 'this')} {e.args['operator']} {self.sql(e, 'expression')}",
    }

    def anonymous_sql(self, expression: exp.Anonymous) -> str:
        name = expression.name
        if name == "PARLANTE_MATCH":
            return self.func("MATCH", *expression.expressions, normalize=False)
        if name == "PARLANTE_PHRASE_MATCH":
            return self.func("PHRASE_MATCH", *expression.expressions, normalize=False)
        return super().anonymous_sql(expression)
```

**Why f-string is acceptable here:** The `exp.Operator` lambda cannot use `self.binary(e, ...)` because `binary()` inspects `node.args.get("operator")` and re-wraps it. There is no public generator API for "emit operator field literally". Per CLAUDE.md guidelines, f-strings are acceptable as a last resort when no proper API exists.

**Why `normalize=False`:** `func(name, ...)` calls `normalize_func(name)` which uppercases by default (`NORMALIZE_FUNCTIONS = "upper"`). With `normalize=False`, the name `"MATCH"` is emitted exactly as given — correct since it's already the right case. Avoids dependency on normalization settings.

### Anti-Patterns to Avoid

- **Auto-discovered `operator_sql` method:** Will be silently ignored because `exp.Operator` is already in `TRANSFORMS` from the base generator. Must use `TRANSFORMS` override.
- **Overriding `_parse_operator` method:** Would require understanding all `OPERATOR(...)` call sites and preserving backward compat. The targeted `RANGE_PARSERS` override is scoped to exactly what's needed.
- **Using `binary_range_parser(exp.Operator)`:** `binary_range_parser` creates a fixed expression type; it doesn't capture the operator text. The lambda form is required.
- **Defining `class Parser(PostgresParser):` inline in the dialect file:** No existing dialect does this; all use separate files. The metaclass resolves it via `klass.__dict__.get("Parser")`, so either approach works mechanically — but separate files is the established pattern and required for mypyc compatibility (the stated goal of this fork).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Operator precedence for `@@@` | Custom precedence logic | `_parse_bitwise()` on the RHS | `@@@` is a comparison-level operator; bitwise precedence is correct |
| Function name dispatch | Custom if/elif in parser | `FUNCTIONS` dict + remove from `FUNCTION_PARSERS` | Established mechanism, handles alias lookup and arg parsing |
| Exact-case function output | Build name string manually | `self.func(name, ..., normalize=False)` | Handles formatting, arg separation, pretty-print wide output |
| Expression class for new operators | Define new exp.XxxOp class | `exp.Operator` with `operator` field | `exp.Operator` already exists for this exact use case |

## Common Pitfalls

### Pitfall 1: `_parse_operator` Loop Breaks Immediately for Bare Tokens

**What goes wrong:** When the `RANGE_PARSERS[TokenType.OPERATOR]` delegate is the default `lambda self, this: self._parse_operator(this)`, the method immediately tries `_match(L_PAREN)`, finds none (the next token is the RHS like `'query'`), and breaks out of its loop returning `this` unchanged. The `@@@` token and RHS are abandoned, causing a parse error on the RHS as an unexpected token.

**Why it happens:** `_parse_operator` is designed for the `OPERATOR(schema.op)` PostgreSQL extension syntax. It is not designed for bare operator tokens.

**How to avoid:** Override `RANGE_PARSERS[TokenType.OPERATOR]` in `ParlanteParse`. At the point the lambda is called, the OPERATOR token has already been consumed — `self._prev.text` holds the symbol (e.g. `"@@@"`). Read it and parse the RHS with `self._parse_bitwise()`.

**Warning signs:** Parse error "Invalid expression / Unexpected token" on the RHS literal. Confirmed: `sqlglot.parse_one("col @@@ 'query'", dialect='parlante')` currently produces this error.

### Pitfall 2: `FUNCTION_PARSERS["MATCH"]` Intercepts Before `FUNCTIONS["MATCH"]`

**What goes wrong:** Adding `"MATCH"` to `ParlanteParse.FUNCTIONS` has no effect because `FUNCTION_PARSERS` is checked first at `parser.py` line 6785. The existing `"MATCH": lambda self: self._parse_match_against()` will always win, and `_parse_match_against` expects `MATCH(cols, ...) AGAINST (query)` syntax, failing with a missing `AGAINST` keyword error.

**Why it happens:** `FUNCTION_PARSERS` has absolute priority over `FUNCTIONS` for matching function names. A subclass dict spread includes the parent's entry unless explicitly excluded.

**How to avoid:** Use dict comprehension to exclude `"MATCH"` from the spread: `{k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"}`.

**Warning signs:** `MATCH(col, 'query')` still fails with "Required keyword: 'this' missing for `MatchAgainst`". Confirmed: this error occurs currently.

### Pitfall 3: Generator `binary()` Wraps Operator Field in `OPERATOR(...)`

**What goes wrong:** Calling `self.binary(expression, "@@@")` or relying on the default `exp.Operator: lambda self, e: self.binary(e, "")` transform produces `col OPERATOR(@@@) 'query'` instead of `col @@@ 'query'`. This is because `binary()` at line 4257-4259 detects a truthy `operator` field and replaces `op` with `f"OPERATOR({self.sql(op_func)})"`.

**Why it happens:** The `binary()` method implements the generic PostgreSQL `OPERATOR(schema.op)` syntax for all `exp.Operator` nodes. It has no way to distinguish "bare symbol" from "schema-qualified symbol".

**How to avoid:** Add `exp.Operator` to `ParlanteGenerator.TRANSFORMS` with a lambda that bypasses `binary()` entirely, building the output as `f"{self.sql(e, 'this')} {e.args['operator']} {self.sql(e, 'expression')}"`.

**Warning signs:** Generated SQL contains `OPERATOR(@@@)` instead of `@@@`. Validate with `parse_one(...).sql(dialect='parlante')`.

### Pitfall 4: Auto-Discovered `operator_sql` Method Silently Ignored

**What goes wrong:** Defining `def operator_sql(self, expression: exp.Operator)` in `ParlanteGenerator` has no effect. The generator dispatches via `TRANSFORMS` first; the method name lookup only applies to expression types not already in `TRANSFORMS`.

**Why it happens:** Both base `Generator.TRANSFORMS` (line 225) and `PostgresGenerator.TRANSFORMS` (spread from base) contain `exp.Operator`. The `ParlanteGenerator.TRANSFORMS` spread from `PostgresGenerator.TRANSFORMS` carries this forward. Auto-discovery only runs as fallback for types absent from `TRANSFORMS`.

**How to avoid:** Put the `exp.Operator` override directly in `TRANSFORMS = {**PostgresGenerator.TRANSFORMS, exp.Operator: lambda ...}`.

**Warning signs:** Tests fail with `OPERATOR(@@@)` output even though `operator_sql` method is defined.

### Pitfall 5: `<=>` Now Routes Through `exp.Operator`, Not `exp.NullSafeEQ`

**What goes wrong (new behavior, NOT a bug):** Under Parlante, `col <=> rhs` parses to `exp.Operator(this=col, operator="<=>", expression=rhs)` — not to `exp.NullSafeEQ`. This is intentional. If any test expects `exp.NullSafeEQ` for `<=>`, it will fail.

**Why it happens:** Phase 1 remapped `<=>` from `TokenType.NULLSAFE_EQ` to `TokenType.OPERATOR`. The base `EQUALITY` dict `{TokenType.NULLSAFE_EQ: exp.NullSafeEQ}` no longer applies.

**How to avoid:** Write Parlante tests for `<=>` that assert `exp.Operator` type. Do not use `validate_all` to compare Parlante `<=>` against Postgres `<=>` (they produce different AST nodes).

**Warning signs:** Test assertion `isinstance(result, exp.NullSafeEQ)` fails.

### Pitfall 6: Postgres Test Suite May Fail if `<->` Breaks

**What goes wrong:** If `RANGE_PARSERS` override accidentally catches `<->` (which is `TokenType.LR_ARROW`, not `TokenType.OPERATOR`), the L2 distance operator would break.

**Why it happens (non-issue):** `<->` is tokenized as `TokenType.LR_ARROW` in the base tokenizer; Phase 1 does not remap it. The `RANGE_PARSERS` override is keyed on `TokenType.OPERATOR` only. No conflict.

**Warning signs (for regression):** `embedding <-> '[0.1,0.2]'` parsed under Parlante returns wrong type. Verified currently: returns `exp.Distance` correctly.

## Code Examples

Verified patterns from codebase analysis:

### Complete `sqlglot/parsers/parlante.py`

```python
# Source: ClickHouse pattern for FUNCTION_PARSERS exclusion (sqlglot/parsers/clickhouse.py:363)
# Source: RANGE_PARSERS mechanism verified in sqlglot/parser.py lines 5681-5682, 9838-9857
from __future__ import annotations

from sqlglot import exp
from sqlglot.parsers.postgres import PostgresParser
from sqlglot.tokens import TokenType


class ParlanteParse(PostgresParser):
    FUNCTION_PARSERS = {
        **{k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"},
    }

    FUNCTIONS = {
        **PostgresParser.FUNCTIONS,
        "MATCH": lambda args: exp.Anonymous(this="PARLANTE_MATCH", expressions=args),
        "PHRASE_MATCH": lambda args: exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=args),
    }

    RANGE_PARSERS = {
        **PostgresParser.RANGE_PARSERS,
        TokenType.OPERATOR: lambda self, this: self.expression(
            exp.Operator(
                this=this,
                operator=self._prev.text,
                expression=self._parse_bitwise(),
            )
        ),
    }
```

### Complete `sqlglot/generators/parlante.py`

```python
# Source: binary() method verified in sqlglot/generator.py lines 4248-4267
# Source: anonymous_sql verified in sqlglot/generator.py lines 3668-3675
# Source: func() with normalize=False verified in sqlglot/generator.py lines 4295-4304
from __future__ import annotations

from sqlglot import exp
from sqlglot.generators.postgres import PostgresGenerator


class ParlanteGenerator(PostgresGenerator):
    TRANSFORMS = {
        **PostgresGenerator.TRANSFORMS,
        exp.Operator: lambda self, e: f"{self.sql(e, 'this')} {e.args['operator']} {self.sql(e, 'expression')}",
    }

    def anonymous_sql(self, expression: exp.Anonymous) -> str:
        name = expression.name
        if name == "PARLANTE_MATCH":
            return self.func("MATCH", *expression.expressions, normalize=False)
        if name == "PARLANTE_PHRASE_MATCH":
            return self.func("PHRASE_MATCH", *expression.expressions, normalize=False)
        return super().anonymous_sql(expression)
```

### Updated `sqlglot/dialects/parlante.py`

```python
# Source: RisingWave and Dune dialect patterns
from __future__ import annotations

from sqlglot.dialects.postgres import Postgres
from sqlglot.generators.parlante import ParlanteGenerator
from sqlglot.parsers.parlante import ParlanteParse
from sqlglot.tokens import TokenType


class Parlante(Postgres):
    class Tokenizer(Postgres.Tokenizer):
        KEYWORDS = {
            **Postgres.Tokenizer.KEYWORDS,
            "@@@": TokenType.OPERATOR,
            "|||": TokenType.OPERATOR,
            "###": TokenType.OPERATOR,
            "===": TokenType.OPERATOR,
            "<=>": TokenType.OPERATOR,  # override base NULLSAFE_EQ
        }

    Parser = ParlanteParse

    Generator = ParlanteGenerator
```

### Phase 2 Test Methods to Add to `tests/dialects/test_parlante.py`

```python
# Source: Validator.validate_identity pattern from tests/dialects/test_dialect.py lines 53-66
# Source: test_postgres.py validate_identity usage patterns

def test_operator_roundtrip(self):
    self.validate_identity("col @@@ 'query'")
    self.validate_identity("col ||| 'query'")
    self.validate_identity("col ### 'query'")
    self.validate_identity("col === 'query'")
    self.validate_identity("col <=> '[0.1,0.2]'")

def test_match_roundtrip(self):
    self.validate_identity("MATCH(col, 'query')")
    self.validate_identity("PHRASE_MATCH(col, 'query')")

def test_no_regression_tsvector(self):
    self.validate_identity("x @@ y")

def test_no_regression_l2_distance(self):
    self.validate_identity("embedding <-> '[0.1,0.2]'")

def test_operator_ast_type(self):
    from sqlglot import exp
    result = self.parse_one("col @@@ 'query'")
    self.assertIsInstance(result, exp.Operator)
    self.assertEqual(result.args["operator"], "@@@")

def test_match_ast_type(self):
    from sqlglot import exp
    result = self.parse_one("MATCH(col, 'query')")
    self.assertIsInstance(result, exp.Anonymous)
    self.assertEqual(result.name, "PARLANTE_MATCH")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `OPERATOR(paradedb.@@@)` regex rewrite | Native `@@@` token → `exp.Operator` | Phase 2 | No regex preprocessing; correct AST without string manipulation |
| `MATCH(...)` → `PARLANTE_MATCH(...)` regex | Parser FUNCTIONS override | Phase 2 | Parser handles it at token level; no regex risk |
| Module-level `_native_operator_sql` function + TRANSFORMS | Lambda in TRANSFORMS | Phase 2 | Inline lambda preferred by CLAUDE.md for simple one-liners |

**Deprecated/outdated (from PARLANTE_DIALECT.md):**
- `rewrite_parlante_syntax()` in `src/parlante/dialect.py`: the whole approach is replaced; out of scope for this fork
- `OPERATOR(paradedb.@@@)` form: no longer needed as Parlante tokenizer emits bare OPERATOR tokens

## Open Questions

1. **Chained Parlante operators (e.g., `a @@@ b @@@ c`)**
   - What we know: The RANGE_PARSERS lambda creates a single `exp.Operator` node with one LHS and RHS
   - What's unclear: Whether chained same-operator expressions are a real use case for Parlante
   - Recommendation: Not required by phase requirements; ignore for now

2. **`self.expression(exp.Operator(...))` vs direct `exp.Operator(...)` construction**
   - What we know: RisingWave parser uses `self.expression(exp.WatermarkColumnConstraint(...))`. The ClickHouse FUNCTIONS lambda uses `exp.RegexpLike.from_arg_list`. The base RANGE_PARSERS lambdas mix both approaches.
   - What's unclear: Whether `self.expression()` adds comment tracking. It wraps the call to attach `_prev_comments`.
   - Recommendation: Use `self.expression(exp.Operator(...))` to match the pattern in `_parse_operator` (line 9849) and other RANGE_PARSERS entries.

## Sources

### Primary (HIGH confidence)

- Codebase read: `sqlglot/parser.py` lines 1166-1187 — base `RANGE_PARSERS` dict; `TokenType.OPERATOR` entry calls `_parse_operator`
- Codebase read: `sqlglot/parser.py` lines 9838-9857 — `_parse_operator` method: confirms it expects `L_PAREN` after OPERATOR token; bare tokens break immediately
- Codebase read: `sqlglot/parser.py` lines 1467-1500 — `FUNCTION_PARSERS` dict; `"MATCH"` at line 1487 confirmed
- Codebase read: `sqlglot/parser.py` lines 6785-6808 — FUNCTION_PARSERS checked before FUNCTIONS (lines 6785-6787 vs 6806-6808)
- Codebase read: `sqlglot/parser.py` lines 5681-5682 — `_parse_range` advances past token then calls RANGE_PARSERS; `self._prev` holds the consumed token
- Codebase read: `sqlglot/generator.py` lines 4248-4267 — `binary()` method; line 4259 wraps `operator` field in `OPERATOR(...)`
- Codebase read: `sqlglot/generator.py` line 225 — base `Generator.TRANSFORMS[exp.Operator]`
- Codebase read: `sqlglot/generators/postgres.py` lines 285-392 — `PostgresGenerator.TRANSFORMS`; confirms `exp.Operator` is present via base spread
- Codebase read: `sqlglot/generators/postgres.py` lines 459-463 — `matchagainst_sql` override for `@@` → `expr @@ this` syntax (Parlante inherits this)
- Codebase read: `sqlglot/generator.py` lines 3668-3675 — `anonymous_sql` implementation
- Codebase read: `sqlglot/generator.py` lines 4295-4304 — `func()` with `normalize` parameter
- Codebase read: `sqlglot/generator.py` line 1028-1033 — `normalize_func`; default is uppercase
- Codebase read: `sqlglot/dialects/dialect.py` lines 263-268 — metaclass resolves `parser_class`/`generator_class` from `klass.__dict__`
- Codebase read: `sqlglot/dialects/postgres.py` lines 126-128 — `Parser = PostgresParser`, `Generator = PostgresGenerator` as class attributes
- Codebase read: `sqlglot/dialects/risingwave.py` — `Parser = RisingWaveParser`, `Generator = RisingWaveGenerator` pattern
- Codebase read: `sqlglot/parsers/clickhouse.py` line 363 — FUNCTION_PARSERS exclusion pattern for `"MATCH"`
- Codebase read: `sqlglot/expressions/core.py` lines 2181-2183 — `exp.Operator` class definition
- Codebase read: `sqlglot/expressions/core.py` lines 1943-1949 — `exp.Anonymous` class; `name` property
- Codebase read: `tests/dialects/test_dialect.py` lines 53-66 — `validate_identity` implementation
- Empirical run: `python3 -c "..."` — confirmed `@@@` parse error, `MATCH` parse error, `@@` round-trips correctly, `<->` round-trips correctly

### Secondary (MEDIUM confidence)

- `PARLANTE_DIALECT.md` — author's intent; aligned with code analysis; used to validate approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all from direct codebase reads; no assumptions
- Architecture: HIGH — every code path traced to source; empirical tests confirm current behavior
- Pitfalls: HIGH — each pitfall confirmed by live test or direct code reading
- Test patterns: HIGH — `validate_identity` and `validate_all` are well-established

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable codebase; invalidated only by changes to `parser.py` RANGE_PARSERS/FUNCTION_PARSERS, `generator.py` binary(), or restructuring of dialect registration)
