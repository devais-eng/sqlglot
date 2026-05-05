# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3.9+ - Core library and all dialect implementations, parser, optimizer, tokenizer, and generator
- C (via mypyc) - Optional compiled extensions for performance-critical modules

## Runtime

**Environment:**
- Python 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
- Platform: Cross-platform (Linux, macOS, Windows, ARM supported via cibuildwheel)

**Package Manager:**
- pip (standard)
- uv (optional, supported for faster installation - set `UV=1` environment variable)
- Lockfile: Not applicable (pure setuptools project, no lock files committed)

## Frameworks & Core Tools

**Build & Compilation:**
- setuptools >= 61.0 - Package build system
- setuptools_scm - Version management from git tags
- mypyc (mypy compiler) - Optional C extension compilation for performance (via `sqlglot[c]` extra)
- cibuildwheel v3.3.1 - Multi-platform wheel building in CI/CD

**Type Checking:**
- mypy - Static type checking with PEP 484 annotations
- sqlglot-mypy - Custom mypy plugin for SQLGlot-specific type checking
- typing_extensions - Backported typing features (TypedDict, Unpack, etc.)
- types-python-dateutil, types-pytz - Type stubs for dependencies

**Code Quality & Formatting:**
- ruff 0.15.6 - Fast linting and formatting (configured via pyproject.toml)
  - UP rule enabled for Python modernization
  - Line length: 100 characters
  - Extensions: E721, E741 ignored
- pre-commit - Git hooks framework for running checks

**Testing:**
- unittest - Python standard library test runner (used exclusively, not pytest)
- Custom test framework in `tests/` - Integration with dialect-specific test suites

**Development & Documentation:**
- pdoc - API documentation generation (HTML docs in `docs/` directory)
- pyperf - Performance benchmarking framework (used in `benchmarks/` module)

## Key Dependencies

**Core (No External Runtime Dependencies):**
SQLGlot is a **zero-dependency library** at runtime. All core functionality requires only Python stdlib.

**Development Only (extras_require["dev"]):**
- duckdb >= 0.6 - Testing cross-dialect functionality and optimization validation
- pandas - Test fixtures and dataframe test validation
- pandas-stubs - Type hints for pandas
- python-dateutil - Testing time/date functionality
- pytz - Testing timezone handling
- pdoc - Documentation generation
- pre-commit - Git hook management
- ruff 0.15.6 - Linting and formatting
- setuptools_scm - Version management
- typing_extensions - Advanced type hints
- pyperf - Benchmarking framework
- mypy - Type checking
- sqlglot-mypy - Custom mypy plugin
- types-python-dateutil, types-pytz - Type stubs

**Optional (extras_require["c"]):**
- sqlglotc - mypyc-compiled C extensions for performance (same version as sqlglot)
  - Requires build dependencies: setuptools >= 61.0, setuptools_scm, sqlglot-mypy, types-python-dateutil

**Deprecated (extras_require["rs"]):**
- sqlglotrs 0.13.0 - Rust tokenizer (deprecated, use sqlglotc instead)

## Configuration

**Environment:**
- No environment variables required for basic usage
- Optional: MYPYPATH used during C extension compilation to resolve imports
- Optional: MYPYC_OPT=0 used during development builds to disable mypyc optimizations

**Build Configuration Files:**
- `pyproject.toml` - Modern Python project metadata and tool configuration
  - setuptools, setuptools_scm, ruff, mypy, uv.sources
- `setup.py` - Legacy build configuration (version-agnostic via setuptools_scm)
- `setup.cfg` - mypy configuration
- `Makefile` - Development commands (install, test, lint, benchmark)
- `.pre-commit-config.yaml` - Pre-commit hooks (ruff, ruff-format, mypy)
- `sqlglotc/setup.py` - C extension build configuration using mypyc
- `sqlglotc/pyproject.toml` - C extension metadata

## C Extension (sqlglotc)

**Purpose:** Performance optimization via mypyc compilation

**Compiled Modules:**
- `sqlglot/errors.py`
- `sqlglot/generator.py`
- `sqlglot/helper.py`
- `sqlglot/parser.py`
- `sqlglot/schema.py`
- `sqlglot/serde.py`
- `sqlglot/time.py`
- `sqlglot/tokenizer_core.py`
- `sqlglot/trie.py`
- All modules in `sqlglot/expressions/`, `sqlglot/generators/`, `sqlglot/parsers/`
- Selected optimizer modules: scope.py, resolver.py, isolate_table_selects.py, normalize_identifiers.py, qualify.py, qualify_tables.py, qualify_columns.py, simplify.py, annotate_types.py
- Executor table module: `sqlglot/executor/table.py`

**Build Targets:**
- Python 3.9-3.14 wheels for x86_64, aarch64, AMD64, universal2 (macOS)
- Platform-specific: Linux (x86_64, aarch64), macOS (universal2), Windows (AMD64)

**Installation Modes:**
- `pip install sqlglot` - Pure Python (default)
- `pip install "sqlglot[c]"` - With C extensions (prebuilt wheel if available, builds from source otherwise)
- `make install` - Pure Python development
- `make install-dev` - Development with optional C extension build
- `make install-devc` - Development with C extension (unoptimized)
- `make install-devc-release` - Production C extension (optimized)

## CLI Tool

**Command:** `python -m sqlglot` or `sqlglot` (when installed)

**Capabilities:**
- SQL transpilation with `--read` and `--write` dialect flags
- SQL parsing and tokenization with `--parse` and `--tokenize` flags
- Pretty-printing control with `--no-pretty` flag
- Identifier quoting control with `--identify` flag
- Error handling with `--error-level` flag (IGNORE, WARN, RAISE, IMMEDIATE)
- stdin support with `-` argument

## Platform Requirements

**Development:**
- Python 3.9+ with development headers
- For C extensions: C compiler (gcc, clang, MSVC), mypyc, setuptools
- Git (for version detection via setuptools_scm)
- Optional: make, gh (GitHub CLI for integration test management)

**Production:**
- Python 3.9+ runtime only
- No external system dependencies beyond Python standard library

## Supported SQL Dialects

31+ SQL dialects supported, including:
- Standard/Generic: DuckDB, Postgres, MySQL, SQLite, Oracle, T-SQL, Snowflake, BigQuery
- Spark: Spark, Spark2, Databricks
- Prestos: Presto, Trino
- Cloud: Redshift, Athena, Fabric
- Data warehouses: ClickHouse, Exasol, Doris, SingleStore, Dremio
- Specialized: Dune, PRQL, Solr, Tableau, Teradata, Risingwave, StarRocks, Drill, Materialize

## Testing

**Test Runner:** Python's `unittest` (standard library)

**Test Execution:**
- `make test` - Run all tests with pure Python (hides .so files)
- `make testc` - Run all tests with C extensions
- `make unit` - Unit tests only (skip integration tests)
- `make unitc` - Unit tests with C extensions
- `make test-fast` - Tests with failfast flag

**Integration Tests:**
- Submodule in `sqlglot-integration-tests/`
- Uses GitHub CLI (`gh`) for automation
- Pre-commit hooks sync integration tests across commit/push/merge/checkout events

**Test Organization:**
- Unit tests: `tests/test_*.py` files
- Dialect tests: `tests/dialects/test_*.py` files
- Fixtures: `tests/fixtures/` directory
- Test utilities: `tests/helpers.py`

**Benchmarks:**
- `make bench` - Run all benchmarks (parse, transpile, optimize)
- `make bench-parse` - Parsing benchmark
- `make bench-transpile` - Transpilation benchmark
- `make bench-optimize` - Optimization benchmark
- pyperf framework for performance measurement
- Automated benchmark comments on PRs with `/benchmark` comment

## CI/CD

**GitHub Actions:**
- `package-publish.yml` - Automated wheel building and PyPI publication on version tags
- `benchmark-sqlglot.yml` - Automated benchmark comparisons on PR comments
- `run-integration-tests.yml` - Integration test orchestration
- `package-test.yml` - Package validation

**Version Management:**
- Semantic versioning: MAJOR.MINOR.PATCH
- Version auto-detected from git tags via setuptools_scm
- Fallback version: 0.0.0

---

*Stack analysis: 2026-04-07*
