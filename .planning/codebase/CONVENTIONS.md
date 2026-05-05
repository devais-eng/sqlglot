# Coding Conventions

**Analysis Date:** 2026-04-07

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `tokenizer_core.py`, `parser.py`, `generator.py`, `expressions.py`
- Dialect files use dialect name: `sqlglot/dialects/snowflake.py`, `tests/dialects/test_snowflake.py`
- Test files follow pattern: `tests/test_<module>.py` or `tests/dialects/test_<dialect>.py`

**Functions:**
- Parser methods use underscore prefix with `_parse_` naming: `_parse_create()`, `_parse_select()`, `_parse_condition()`, `_parse_csv()`
- Generator methods use auto-discovered pattern: `<expression_name>_sql()` (e.g., `myfunc_sql()` for `MyFunc` expression)
- Helper/builder functions use descriptive names: `build_var_map()`, `build_like()`, `binary_range_parser()`, `build_logarithm()`
- Private helper functions start with underscore: `_parse_binary_range()`, `_builder()`
- Classes use PascalCase: `Parser`, `Generator`, `Validator`, `Expression`

**Variables:**
- Snake_case for local variables and parameters: `expression`, `this`, `args`, `dialect`
- Type variables use uppercase single letters: `T`, `E`, `G` (with TypeVar annotations)
- Constants use UPPERCASE: `TRANSFORMS`, `KEYWORDS`, `OPTIONS_TYPE`

**Types:**
- Expression classes inherit from `Expr` or `Expression` base classes
- Type hints use modern syntax with `|` for unions: `exp.Expr | None`, `Type[E]`
- Generic types use: `t.Callable`, `dict[str, t.Any]`, `list[T]`

## Code Style

**Formatting:**
- Tool: Ruff formatter (configured via `.pre-commit-config.yaml`)
- Line length: 100 characters (configured in `pyproject.toml`)
- No trailing semicolons in Python

**Linting:**
- Tool: Ruff linter (in pre-commit hooks)
- Config: `tool.ruff.lint` section in `pyproject.toml`
- Extended rules: `extend-select = ["UP"]` (modernization rules)
- Ignored rules: `E721` (type comparison), `E741` (ambiguous variable names)

**Type Checking:**
- Tool: mypy (in pre-commit hooks)
- Entry: `mypy sqlglot tests`
- Configuration: `pyproject.toml` (implicit)

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library imports (`import logging`, `import typing as t`, etc.)
3. Collections imports (`from collections import defaultdict`, `from collections.abc import Sequence`)
4. Third-party imports (none for pure Python parser, but may include mypyc extensions)
5. Local imports (`from sqlglot import exp`, `from sqlglot.helper import ...`)
6. TYPE_CHECKING block with forward references

**Pattern Example from `parser.py`:**
```python
from __future__ import annotations

import itertools
import logging
import re
import typing as t
from collections import defaultdict

from sqlglot import exp
from sqlglot.errors import ...
from sqlglot.helper import ...
from sqlglot.tokens import Token, Tokenizer, TokenType

if t.TYPE_CHECKING:
    from sqlglot.expressions import ExpOrStr
    from sqlglot._typing import E, BuilderArgs
    ...
```

**Path Aliases:**
- Star imports used in expression module: `from sqlglot.expressions.core import *`
- Explicit imports for forward references and public API
- Conditional imports in `TYPE_CHECKING` block to avoid circular imports

## Error Handling

**Patterns:**
- Custom exception hierarchy in `sqlglot/errors.py`: `SqlglotError` (base), `ParseError`, `TokenError`, `UnsupportedError`, `OptimizeError`, `SchemaError`, `ExecuteError`
- `ParseError` has `.errors` attribute containing list of error dicts with detailed context
- Use `ParseError.new()` class method to construct with full context information
- Error levels defined in `ErrorLevel` enum: `IGNORE`, `WARN`, `RAISE`, `IMMEDIATE`
- Parser/Generator log errors/warnings via `logger.error()`, `logger.warning()`
- Use `assertRaises()` context manager in tests to verify error handling

**Example from `errors.py`:**
```python
class ParseError(SqlglotError):
    def __init__(self, message: str, errors: list[dict[str, t.Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []
```

## Logging

**Framework:** Python's built-in `logging` module

**Pattern:**
- Module-level logger: `logger = logging.getLogger("sqlglot")`
- Used sparingly: only for important events (errors, warnings)
- Examples: `logger.error()`, `logger.warning()`
- Test utilities can check logger output with `self.assertLogs()`

**When to Log:**
- Errors during parsing: `logger.error(str(error))`
- Unsupported features: `logger.warning(msg)`
- Avoid logging in hot paths (performance-critical code)

## Comments

**When to Comment:**
- Complex parsing/generation logic needs explanatory comments
- Dialect-specific quirks and workarounds
- Non-obvious design decisions
- Minimal comments for obvious code (prefer clear naming)

**JSDoc/TSDoc:**
- Docstrings used for public API and classes
- Class docstrings describe purpose and important parameters
- Method docstrings used for complex methods with multiple branches
- Args documented in docstring with type and description

**Example from `generator.py`:**
```python
class Generator:
    """
    Generator converts a given syntax tree to the corresponding SQL string.

    Args:
        pretty: Whether to format the produced SQL string.
            Default: False.
        identify: Determines when an identifier should be quoted.
        ...
    """
```

## Function Design

**Size:**
- Parser methods typically 5-50 lines
- Helper builders 5-20 lines
- Generator methods use TRANSFORMS for simple single-liners, methods for complex logic
- Large functions broken into named helper functions

**Parameters:**
- Use `*args` and `**kwargs` for flexible parsing in builder functions
- Type hints required: `BuilderArgs`, specific expression types, `Dialect`
- Optional parameters with defaults in generator methods

**Return Values:**
- Parser methods return `exp.Expr | None`
- Generator methods return `str`
- Builder functions return specific expression types
- Helper functions return construction-ready expressions

**Parameter Pattern:**
```python
def binary_range_parser(
    expr_type: Type[exp.Expr], reverse_args: bool = False
) -> t.Callable[[Parser, exp.Expr | None], exp.Expr | None]:
```

## Module Design

**Exports:**
- `expressions/__init__.py` uses star imports with explicit private exports
- Public helper functions exported from `expressions/builders.py`
- Generator/Parser subclasses export TRANSFORMS mappings

**Barrel Files:**
- `expressions/__init__.py` re-exports all expression classes from submodules
- Central aggregation of `EXPR_CLASSES` dict for expression lookup
- Centralized `ALL_FUNCTIONS` registry for function discovery

**Example Pattern:**
```python
# expressions/__init__.py
from sqlglot.expressions.core import *  # noqa: F401,F403
from sqlglot.expressions.builders import *  # noqa: F401,F403

ALL_FUNCTIONS = subclasses(__name__, Func, {AggFunc, Anonymous, Func})
EXPR_CLASSES: dict[str, type[Expr]] = {cls.key: cls for cls in subclasses(__name__, Expr)}
```

## Expression Building

**Use helper functions over direct construction:**
- `exp.func("name", *args)` instead of `exp.Anonymous(...)`
- `exp.array(*elements)` instead of `exp.Array(expressions=[...])`
- `exp.and_(expr1, expr2)` instead of `exp.And(this=..., expression=...)`
- `exp.case().when(cond, val).else_(default)` for CASE expressions
- `exp.cast(expr, "TYPE")` instead of `exp.Cast(this=..., to=...)`
- `exp.column("col", "table")` for column construction
- Operators: `col1 + col2`, `arr[index]`, `arg.is_(exp.Null())`

**Generator SQL building:**
- Use `self.func("NAME", *args)` for function generation
- Use `self.sql()` to recursively generate nested expressions
- Use `self.binary()`, `self.expressions()`, `self.seg()` for common patterns
- Only use f-strings with SQL fragments as absolute last resort (breaks quoting/escaping)

## Special Patterns

**Type Checking with `is_type()` vs `is_string`:**
- `is_string`: Syntactic check for literal strings only (fast, works without annotation)
- `is_type()`: Semantic type check (requires `annotate_types()` to populate type info)
- Use `is_string` for quick literal checks
- Use `is_type()` when type semantics matter (e.g., text operations)
- Combined pattern: `if arg.is_string or arg.is_type(*exp.DataType.TEXT_TYPES)`

**Literal Value Extraction:**
- Use `to_py()` method on literals: `int(arg.to_py())` for number extraction
- Avoid direct parsing of `arg.this` strings
- Check literal type first: `if arg.is_number and arg.to_py()`

**Avoid Compile-Time NULL Checks:**
- Don't check for `exp.Null()` in Python code
- Generate SQL with `IS NULL` checks to handle runtime NULLs
- Use CASE expressions with NULL handling

**Find with Scope Boundaries:**
- Use `find_ancestor(exp.Where, exp.Having, exp.Select)` to stop at scope boundaries
- Stop at Select to stay within current query scope
- Prevents crossing into parent queries

**Unsupported Arguments Decorator:**
- Use `@unsupported_args("arg_name", ...)` for generator methods
- Marks unsupported arguments and triggers appropriate error level

---

*Convention analysis: 2026-04-07*
