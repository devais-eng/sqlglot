# Codebase Structure

**Analysis Date:** 2026-04-07

## Directory Layout

```
/home/filippo/GithubProjects/sqlglot/
├── sqlglot/                   # Main package
│   ├── __init__.py            # Public API entry point
│   ├── parser.py              # Base Parser class (370+ KB)
│   ├── generator.py           # Base Generator class (250+ KB)
│   ├── tokens.py              # Token definitions and Tokenizer base
│   ├── tokenizer_core.py      # Core tokenizer logic (mypyc-compiled)
│   ├── expressions/           # AST node definitions (modular)
│   ├── dialects/              # 34+ SQL dialect implementations
│   ├── parsers/               # Dialect-specific parser customizations
│   ├── generators/            # Dialect-specific generator customizations
│   ├── optimizer/             # Query optimization rules
│   ├── executor/              # SQL execution engine
│   ├── schema.py              # Database schema representation
│   ├── lineage.py             # Column-level lineage tracking
│   ├── helper.py              # Utility functions
│   ├── errors.py              # Exception classes
│   ├── transforms.py          # AST transformation utilities
│   ├── diff.py                # SQL diff functionality
│   ├── serde.py               # Serialization/deserialization
│   ├── time.py                # Temporal handling
│   ├── planner.py             # Query planner
│   ├── trie.py                # Trie data structure for keyword matching
│   ├── jsonpath.py            # JSON path parsing
│   └── typing/                # Type annotations and typing helpers
│
├── sqlglotc/                  # mypyc-compiled C extension (optional)
│   └── Various .so files when compiled
│
├── tests/                     # Test suite
│   ├── test_parser.py         # Parser unit tests
│   ├── test_generator.py      # Generator unit tests
│   ├── test_expressions.py    # Expression class tests
│   ├── test_optimizer.py      # Optimizer rule tests
│   ├── test_transpile.py      # Cross-dialect transpilation tests
│   ├── test_executor.py       # SQL executor tests
│   ├── test_lineage.py        # Lineage analysis tests
│   ├── dialects/              # Dialect-specific tests
│   │   ├── test_snowflake.py
│   │   ├── test_bigquery.py
│   │   ├── test_postgres.py
│   │   └── ... (one per dialect)
│   ├── fixtures/              # Test data and SQL fixtures
│   └── helpers.py             # Test utilities
│
├── posts/                     # Documentation
│   ├── ast_primer.md          # AST tutorial (recommended reading)
│   └── onboarding.md          # Architecture deep-dive
│
├── benchmarks/                # Performance benchmarks
│   └── Various benchmark scripts
│
├── Makefile                   # Development commands
├── pyproject.toml             # Project metadata and build config
├── setup.py                   # Package setup
├── README.md                  # Project overview
└── CONTRIBUTING.md            # Contribution guidelines
```

## Directory Purposes

**`sqlglot/` (main package):**
- Purpose: Core transpiler implementation
- Contains: Parser, Generator, Expression definitions, Dialects, Optimizer
- Key files: `__init__.py` (public API), `parser.py`, `generator.py`

**`sqlglot/expressions/`:**
- Purpose: Modular AST node definitions organized by semantic category
- Contains: Expression subclasses grouped by domain
- Key files:
  - `core.py`: Base Expr class, fundamental expressions (Identifier, Column, Literal, etc.)
  - `query.py`: SELECT, INSERT, UPDATE, DELETE, CTE, set operations
  - `functions.py`: Function expression types
  - `dml.py`: Data manipulation (INSERT, UPDATE, DELETE, MERGE)
  - `ddl.py`: Data definition (CREATE, DROP, ALTER)
  - `aggregate.py`: Aggregation functions (SUM, COUNT, AVG, etc.)
  - `array.py`: Array operations
  - `string.py`: String functions
  - `temporal.py`: Date/time functions
  - `math.py`: Math functions
  - `json.py`: JSON operations
  - `datatypes.py`: DataType and type system
  - `constraints.py`: Column/table constraints
  - `properties.py`: Table/database properties
  - `builders.py`: Helper functions for programmatic expression building

**`sqlglot/dialects/`:**
- Purpose: SQL dialect-specific implementations
- Contains: 34+ dialect files + base Dialect class
- Key files:
  - `dialect.py`: Base Dialect class (92+ KB), dialect registry, helper functions
  - `snowflake.py`, `bigquery.py`, `postgres.py`, `mysql.py`, etc.: Individual dialects
  - Pattern: Each dialect subclasses Dialect and overrides Tokenizer, Parser, Generator

**`sqlglot/parsers/`:**
- Purpose: Dialect-specific parser customizations
- Contains: Parser subclasses for dialects requiring custom parsing
- Pattern: Not all dialects need custom parsers; only those with unique syntax

**`sqlglot/generators/`:**
- Purpose: Dialect-specific generator customizations
- Contains: Generator subclasses for dialects requiring custom SQL generation
- Pattern: Most dialects customize generator; some inherit base behavior

**`sqlglot/optimizer/`:**
- Purpose: Query optimization and transformation rules
- Contains: Individual rule modules + orchestrator
- Key files:
  - `optimizer.py`: optimize() function, RULES tuple (orchestrator)
  - `qualify.py`: Normalize identifiers and table/column qualification
  - `annotate_types.py`: Type inference (35+ KB, largest rule)
  - `simplify.py`: Expression simplification (60+ KB)
  - `pushdown_predicates.py`: Move filters down in query tree
  - `pushdown_projections.py`: Project only needed columns
  - `merge_subqueries.py`: Flatten subqueries
  - `eliminate_*`: Remove unnecessary joins, CTEs, subqueries
  - `scope.py`: Scope analysis (dependencies between SELECT blocks)
  - `resolver.py`: Symbol resolution for qualified names

**`sqlglot/executor/`:**
- Purpose: In-memory SQL execution engine
- Contains: Python-based query executor
- Files: `python.py` (executor logic), `table.py`, `env.py`, `context.py`

**`tests/`:**
- Purpose: Comprehensive test suite
- Organization:
  - Root test files: Core functionality (parser, generator, optimizer, transpile)
  - `dialects/`: One test file per dialect
  - `fixtures/`: Test SQL data and expected outputs
- Pattern: Tests inherit from helpers.Validator with validate_identity(), validate_all()

**`posts/`:**
- Purpose: Developer documentation
- Key reads:
  - `ast_primer.md`: AST fundamentals (HIGHLY RECOMMENDED)
  - `onboarding.md`: Architecture deep-dive

**`benchmarks/`:**
- Purpose: Performance testing against other SQL parsers
- Used by: `make bench`, `make bench-optimize`

## Key File Locations

**Entry Points:**
- `sqlglot/__init__.py`: Public API (tokenize, parse, parse_one, transpile, optimize)
- `sqlglot/__main__.py`: CLI entry point
- `sqlglot/dialects/dialect.py`: Dialect registry and factory

**Core Logic:**
- `sqlglot/parser.py`: Parser class (370+ KB, largest file)
- `sqlglot/generator.py`: Generator class (250+ KB)
- `sqlglot/tokens.py`: Tokenizer, Token, TokenType
- `sqlglot/tokenizer_core.py`: Core tokenizer (mypyc-compiled)
- `sqlglot/expressions/core.py`: Base Expr class and fundamental expressions

**Configuration:**
- `pyproject.toml`: Python project config (dependencies, build settings)
- `setup.py`: Package setup (minimal, delegates to pyproject.toml)
- `Makefile`: Development commands (install, test, lint, check)
- `.pre-commit-config.yaml`: Pre-commit hooks (ruff, mypy)

**Schema & Metadata:**
- `sqlglot/schema.py`: Schema classes (MappingSchema)
- `sqlglot/optimizer/scope.py`: Scope analysis for qualification

## Naming Conventions

**Files:**
- Module files: `lowercase_with_underscores.py` (e.g., `tokenizer_core.py`, `generator.py`)
- Package directories: `lowercase` (e.g., `sqlglot/expressions/`, `sqlglot/dialects/`)
- Dialect files: `{dialect_name}.py` (e.g., `snowflake.py`, `bigquery.py`)

**Directories:**
- Core: `sqlglot/` (main package)
- Domain-specific: `sqlglot/expressions/`, `sqlglot/dialects/`, `sqlglot/optimizer/`
- Tests: `tests/` with same structure as source

**Classes:**
- Expression subclasses: `PascalCase` (e.g., Select, Column, BinaryOp)
- Base classes: `PascalCase` (e.g., Expr, Dialect, Generator, Parser)
- Enum: `PascalCase` (e.g., TokenType, Dialects, ErrorLevel)

**Functions:**
- Public functions: `lowercase_with_underscores` (e.g., parse_one, transpile, optimize)
- Private functions: `_lowercase_with_underscores` (e.g., _match, _parse_select)
- Parser methods: `_parse_<construct>` (e.g., _parse_select, _parse_create, _parse_csv)
- Generator methods: `<expr_name>_sql` (e.g., select_sql, column_sql, binary_op_sql)
- Builder functions: `build_<function>` (e.g., build_logarithm, build_array_concat)

**Variables:**
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., RULES, KEYWORDS, TRANSFORMS)
- Instance variables: `lowercase_with_underscores` (e.g., expression, this, args)
- Temporary/loop vars: `short_names` (e.g., expr, arg, node, col)

## Where to Add New Code

**New SQL Function Support:**
- Expression class: `sqlglot/expressions/functions.py` (if new function category, create file in expressions/)
- Parser builder: `sqlglot/parser.py` (add `build_<function_name>`)
- Generator method: Override in dialect's Generator subclass in `sqlglot/dialects/<dialect>.py` OR in `sqlglot/generator.py` if cross-dialect
- Tests: `tests/test_<domain>.py` or `tests/dialects/test_<dialect>.py`

**New Dialect Support:**
- Dialect class: Create `sqlglot/dialects/<dialect_name>.py`
- Parser subclass: `sqlglot/dialects/<dialect_name>.py` (if needed) OR inherit base
- Generator subclass: `sqlglot/dialects/<dialect_name>.py` (override TRANSFORMS and methods)
- Tests: Create `tests/dialects/test_<dialect_name>.py`
- Registration: Add enum entry to `Dialects` in `sqlglot/dialects/dialect.py`

**New Optimizer Rule:**
- Rule module: `sqlglot/optimizer/<rule_name>.py`
- Function signature: `def <rule_name>(expression: Expr, schema: Schema = None, ...) -> Expr`
- Registration: Add to RULES tuple in `sqlglot/optimizer/optimizer.py`
- Tests: `tests/test_optimizer.py` (add test method)

**New Utilities:**
- Shared helpers: `sqlglot/helper.py`
- Expression builders: `sqlglot/expressions/builders.py`
- Type annotations: `sqlglot/typing/` or `sqlglot/_typing.py`

**Tests:**
- Unit tests: `tests/test_<module>.py` parallel to source
- Dialect tests: `tests/dialects/test_<dialect>.py`
- Test data/fixtures: `tests/fixtures/` directory

## Special Directories

**`sqlglotc/` (C Extension):**
- Purpose: mypyc-compiled modules for performance
- Generated: Yes (built from `sqlglot/` source via mypyc)
- Committed: No (build artifacts only)
- Usage: Automatically imported by `sqlglot/tokens.py` if available
- Compile: `make install-devc` or `UV=1 make install-devc`

**`sqlglot-integration-tests/` (Submodule):**
- Purpose: Integration tests against real databases (Snowflake, BigQuery, etc.)
- Generated: No (git submodule)
- Committed: Via submodule reference
- Usage: Separate from unit tests; requires database credentials

**`.planning/codebase/`:**
- Purpose: GSD (Get Stuff Done) codebase documentation
- Generated: Yes (created by mapper agents)
- Committed: Yes (artifacts for planning/execution)
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md

**`posts/`:**
- Purpose: Developer documentation
- Generated: No (manually maintained)
- Committed: Yes
- Key files: `ast_primer.md`, `onboarding.md`

---

*Structure analysis: 2026-04-07*
