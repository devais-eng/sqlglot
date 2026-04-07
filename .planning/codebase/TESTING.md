# Testing Patterns

**Analysis Date:** 2026-04-07

## Test Framework

**Runner:**
- Python built-in `unittest` framework
- No external test runners (pytest, nose, etc.)
- Standard commands in Makefile: `make test`, `make unit`, `make testc`

**Run Commands:**
```bash
make test              # Run all tests (pure Python, hides .so files)
make test-fast        # Run all tests with --failfast
make unit             # Run only unit tests (skip integration), pure Python
make testc            # Run all tests with mypyc C extension built
make unitc            # Run only unit tests with C extension
python -m unittest    # Run all tests directly
python -m unittest tests.test_expressions.TestExpressions     # Specific test class
python -m unittest tests.test_expressions.TestExpressions.test_alias  # Specific test method
```

**Assertion Library:**
- Standard `unittest` assertions: `assertEqual()`, `assertRaises()`, `assertIn()`, `assertIsNone()`, `assertIsInstance()`
- Custom assertion methods: `assert_is()`, `assert_equals()`
- Logger assertion helper: `assertLogs()` with context manager

## Test File Organization

**Location:**
- Co-located with source: Tests are in `tests/` directory, not within `sqlglot/`
- Core tests: `tests/test_<module>.py` (e.g., `test_parser.py`, `test_generator.py`, `test_schema.py`)
- Dialect tests: `tests/dialects/test_<dialect>.py` (33 dialect test files)

**Naming:**
- Test classes: `Test<Component>` (e.g., `TestParser`, `TestGenerator`, `TestSnowflake`)
- Test methods: `test_<feature_or_scenario>()` (e.g., `test_parse_empty()`, `test_cast()`, `test_snowflake()`)

**Structure:**
```
tests/
├── test_parser.py         # Parser functionality
├── test_generator.py      # Generator functionality
├── test_build.py          # Expression builders
├── test_schema.py         # Schema functionality
├── test_optimizer.py      # Optimization rules
├── test_time.py           # Time/date handling
├── dialects/
│   ├── test_dialect.py    # Base Validator class, dialect tests
│   ├── test_snowflake.py  # Snowflake-specific tests
│   ├── test_duckdb.py     # DuckDB-specific tests
│   └── ...                # Other dialect tests (33 total)
├── fixtures/              # Test data files
│   ├── identity.sql       # SQL for identity validation
│   ├── pretty.sql         # Formatted SQL examples
│   └── optimizer/         # Optimizer test fixtures
└── helpers.py             # Test utilities and constants
```

## Test Structure

**Base Class Pattern:**

The `Validator` base class in `tests/dialects/test_dialect.py` provides common test infrastructure:

```python
class Validator(unittest.TestCase):
    dialect = None

    def parse_one(self, sql, **kwargs):
        return parse_one(sql, read=self.dialect, **kwargs)

    def validate_identity(self, sql, write_sql=None, pretty=False, check_command_warning=False, identify=False):
        """Test that SQL round-trips through parse/generate."""
        expression = self.parse_one(sql)
        self.assertEqual(
            write_sql or sql,
            expression.sql(dialect=self.dialect, pretty=pretty, identify=identify)
        )
        return expression

    def validate_all(self, sql, read=None, write=None, pretty=False, identify=False):
        """
        Validate that:
        1. Everything in `read` transpiles to `sql`
        2. `sql` transpiles to everything in `write`
        """
```

**Dialect Test Class Pattern:**

```python
class TestSnowflake(Validator):
    maxDiff = None
    dialect = "snowflake"

    def test_snowflake(self):
        self.validate_identity("SELECT session")
        self.validate_identity(
            "SELECT DATE_PART(EPOCH_MILLISECOND, CURRENT_TIMESTAMP()) AS a"
        )
        self.validate_all(
            "SELECT CAST(x AS INT)",
            read={
                "postgres": "SELECT CAST(x AS INTEGER)",
                "bigquery": "SELECT CAST(x AS INT64)",
            },
            write={
                "duckdb": "SELECT CAST(x AS INT)",
                "postgres": "SELECT CAST(x AS INTEGER)",
            },
        )
```

## Test Patterns

**Testing SQL Round-Trip (Identity):**
```python
# Simplest: SQL should parse and generate identically
self.validate_identity("SELECT * FROM table")

# With expected output different from input
self.validate_identity(
    "SELECT MOD(x, y)",     # Input
    "SELECT x % y"          # Expected output for this dialect
)

# With options
self.validate_identity(
    sql,
    pretty=True,            # Generate pretty-printed output
    identify=True,          # Quote identifiers
    check_command_warning=True  # Expect parse warning for unsupported syntax
)
```

**Testing Cross-Dialect Transpilation:**
```python
self.validate_all(
    "SELECT CAST(x AS TEXT)",           # Canonical representation
    read={
        "mysql": "SELECT CAST(x AS CHAR)",
        "bigquery": "SELECT CAST(x AS STRING)",
    },
    write={
        "postgres": "SELECT CAST(x AS TEXT)",
        "oracle": "SELECT CAST(x AS CLOB)",
        "snowflake": "SELECT CAST(x AS VARCHAR)",
    },
)
```

**Testing Unsupported Features:**
```python
self.validate_all(
    "SELECT BITMAP_BIT_POSITION(10)",
    write={
        "duckdb": "SELECT (CASE WHEN 10 > 0 THEN 10 - 1 ELSE ABS(10) END) % 32768",
        "snowflake": "SELECT BITMAP_BIT_POSITION(10)",
    },
)

# With unsupported error
self.validate_all(
    "SELECT * FROM table",
    write={
        "unsupported_dialect": UnsupportedError,  # Expect exception
    },
)
```

**Testing with Subtests:**
```python
def test_complex_scenario(self):
    for dialect in ["snowflake", "duckdb", "postgres"]:
        with self.subTest(f"Testing {dialect}"):
            expr = parse_one(sql, read=dialect)
            self.assertEqual(expr.sql("snowflake"), expected)
```

**Testing Error Conditions:**
```python
def test_parse_error(self):
    with self.assertRaises(ParseError):
        parse_one("")

    with self.assertRaises(ParseError) as ctx:
        parse_one("SELECT 1;", read="sqlite", into=[exp.From])
    
    self.assertEqual(str(ctx.exception), expected_message)
    self.assertEqual(ctx.exception.errors, expected_errors)
```

**Testing Logger Output:**
```python
def test_unsupported_warning(self):
    with self.assertLogs(parser_logger) as cm:
        expression = self.parse_one(unsupported_sql)
    
    assert f"'{unsupported_sql[:100]}' contains unsupported syntax" in cm.output[0]
```

**Testing Expression Properties:**
```python
def test_column(self):
    expr = parse_one("SELECT a, ARRAY[1] b FROM table")
    columns = expr.find_all(exp.Column)
    assert len(list(columns)) == 1
    
    # Chain assertions
    result = parse_one("date").assert_is(exp.Column)
    self.assertIsNotNone(result)
```

**Testing Expression Transformation:**
```python
def test_modify_ast(self):
    ast = self.parse_one("DATEADD(DAY, n, d)")
    ast.set("unit", exp.Literal.string("MONTH"))
    self.assertEqual(ast.sql("snowflake"), "DATEADD(MONTH, n, d)")
```

**Testing with Type Annotation:**
```python
# For tests that depend on is_type() checks
from sqlglot.optimizer import annotate_types

def test_type_sensitive_transpilation(self):
    # Without annotation - is_type() returns False
    expr = self.validate_identity("SELECT BASE64_ENCODE('Hello World')")
    
    # With annotation - types are inferred
    annotated = annotate_types(expr, dialect="snowflake")
    self.assertEqual(annotated.sql("duckdb"), "SELECT TO_BASE64(ENCODE('Hello World'))")
```

## Mocking

**Framework:** Python `unittest.mock`

**Pattern:**
```python
from unittest import mock

with mock.patch('module.target') as mock_obj:
    # Test code
    mock_obj.assert_called()
```

**Examples from codebase:**
- Mocking subprocess calls for lazy loading tests
- Mocking logger for output verification

**What to Mock:**
- External I/O (subprocess, files)
- Logger calls (to verify specific messages)
- Dependencies in isolation tests

**What NOT to Mock:**
- Expression classes and builders
- Parser/Generator (test actual transpilation)
- Dialect implementations (test behavior end-to-end)
- Standard library basics (dict, list operations)

## Test Data and Fixtures

**Fixtures Location:** `tests/fixtures/`

**SQL Fixtures:**
- `identity.sql`: Basic SQL statements for round-trip testing
- `pretty.sql`: SQL examples for pretty-printing validation
- `optimizer/`: Query optimizer test fixtures

**Test Schema Constants in `helpers.py`:**
```python
TPCH_SCHEMA = {
    "lineitem": {
        "l_orderkey": "bigint",
        "l_partkey": "bigint",
        ...
    },
    ...
}

TPCDS_SCHEMA = {...}  # TPC-DS schema for complex queries
```

**Loading Fixtures:**
```python
from tests.helpers import load_sql_fixtures, load_sql_fixture_pairs

# Load individual SQL statements
for sql in load_sql_fixtures("identity.sql"):
    # Test each statement

# Load pairs (input/expected output)
for meta, sql, expected in load_sql_fixture_pairs("partial.sql"):
    # Test transformations with metadata
```

**Fixture Metadata:**
```
#dialect: snowflake
#pretty: true
SELECT * FROM table;
SELECT
  *
FROM table
```

## Coverage

**Requirements:** Not explicitly enforced in codebase

**View Coverage:**
- No standard coverage command in Makefile
- Coverage tracking is manual/implicit through test organization

**Coverage Strategy:**
- Core functionality heavily tested: Parser, Generator, Expressions
- All 34+ dialects have dedicated test files with comprehensive cases
- Integration tests in separate repository (`sqlglot-integration-tests` submodule)
- Critical transpilation paths have cross-dialect test matrices

## Test Types

**Unit Tests:**
- Scope: Individual functions, parser methods, generator methods
- Pattern: Test isolated functionality in `test_parser.py`, `test_generator.py`, `test_build.py`
- Run with: `make unit` (excludes integration tests)
- Example: `test_parse_empty()`, `test_column()`, `test_float()`

**Dialect Tests:**
- Scope: Dialect-specific parsing, generation, and transpilation
- Pattern: Extend `Validator` base class, use `validate_identity()` and `validate_all()`
- Location: `tests/dialects/test_<dialect>.py`
- Coverage: All SQL features supported by dialect, edge cases, workarounds
- Example: TestSnowflake, TestDuckDB, TestBigQuery

**Integration Tests:**
- Scope: Cross-dialect transpilation, real database queries
- Location: `sqlglot-integration-tests/` (submodule)
- Trigger: Run actual SQL in target databases to verify correctness
- Pattern: `make test` runs these; `make unit` skips them
- Control: `SKIP_INTEGRATION=1` environment variable

**Cross-Dialect Validation:**
- Pattern: Single `validate_all()` call tests multiple dialect paths
- Example: One test validates TEXT casting across 15+ dialects simultaneously
- Efficiency: Reduces redundant test code while maximizing coverage

## Common Patterns

**Async Testing:**
- Not used (pure Python, synchronous operations)
- All parser/generator operations are synchronous

**Error Testing:**
```python
# Basic error testing
with self.assertRaises(ParseError):
    parse_one("")

# Error details testing
with self.assertRaises(ParseError) as ctx:
    parse_one("invalid", read="dialect")

# Check error properties
self.assertEqual(len(ctx.exception.errors), 1)
self.assertIn("description", ctx.exception.errors[0])
```

**Assertion Chaining:**
```python
# Some expression classes support assertion chaining
expr = parse_one("(1)").assert_is(exp.Tuple)
result = self.validate_identity("...").assert_is(exp.AggFunc)
```

**Multiple Assertions in Single Test:**
```python
def test_feature(self):
    self.validate_identity("SELECT 1")
    self.validate_identity("SELECT 2")
    self.validate_all("SELECT x", read={...}, write={...})
    # All assertions contribute to same test
```

**Environment-Based Test Skipping:**
```python
SKIP_INTEGRATION = string_to_bool(os.environ.get("SKIP_INTEGRATION", "0").lower())

# Used in test discovery to skip integration tests
```

## Test Execution Context

**Pure Python vs C Extension:**
- `make test`: Hides `.so` files, runs pure Python tests
- `make testc`: Builds C extension, runs with compiled modules
- Both test suites must pass (`make check`)
- Core modules (parser_core, tokenizer_core, etc.) have compiled versions in `sqlglotc/`

**Pre-Commit Integration:**
- Tests run via pre-commit hooks
- `ruff check` with `--fix` for auto-correction
- `ruff format` for code formatting
- `mypy sqlglot tests` for type checking

---

*Testing analysis: 2026-04-07*
