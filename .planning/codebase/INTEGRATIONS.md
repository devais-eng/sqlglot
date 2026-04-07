# External Integrations

**Analysis Date:** 2026-04-07

## Overview

SQLGlot is a **zero-dependency library** designed to have no external runtime dependencies. All functionality requires only Python standard library. External tools are used only in development and testing.

## APIs & External Services

**None.** SQLGlot does not integrate with any external APIs or cloud services in production. All SQL parsing, transpilation, and optimization is performed locally.

## Data Storage

**Databases:**
- Not applicable at runtime. No persistent database connections.
- Development/Testing only: duckdb >= 0.6 used to validate transpilation and optimization behavior across dialects

**File Storage:**
- Local filesystem only. SQLGlot operates on SQL strings and AST objects in memory.
- No cloud storage integrations (S3, GCS, etc.)

**Caching:**
- None. All operations are stateless and deterministic.

## In-Memory Data Structures

**Query Execution:**
- `sqlglot.executor.table.Table` - In-memory table representation with rows and column metadata
  - Location: `sqlglot/executor/table.py`
  - Used for local SQL execution (experimental feature)
  - No external data source; data provided programmatically

**Schema Representation:**
- `sqlglot.schema.MappingSchema` - In-memory schema store using nested Python dicts
  - Location: `sqlglot/schema.py`
  - Format: `{"table": {"col": "type"}}`
  - No external schema retrieval

## Authentication & Identity

**Auth Provider:** Not applicable

SQLGlot does not authenticate with any external services. All operations are local and stateless.

## Monitoring & Observability

**Error Tracking:** None

SQLGlot uses Python's standard `logging` module for internal diagnostics. No external error tracking service integration.

**Logs:**
- Python `logging` module (standard library)
- Logger name: `"sqlglot"`
- Configuration: Default handlers (no external targets)

**Diagnostic Output:**
- stderr for error messages
- stdout for CLI output
- No metrics collection or remote telemetry

## CI/CD & Deployment

**Hosting:** Not applicable

SQLGlot is a library distributed via PyPI. It runs in the user's Python environment.

**Distribution:**
- PyPI: https://pypi.org/project/sqlglot/
- Published via GitHub Actions workflow on version tags
- Supports prebuilt wheels for Python 3.9-3.14 on Linux x86_64/aarch64, macOS universal2, Windows AMD64

**CI Pipeline:**
- GitHub Actions
  - package-publish.yml: Builds and publishes wheels and sdist
  - benchmark-sqlglot.yml: Runs performance benchmarks on PR `/benchmark` comments
  - run-integration-tests.yml: Executes dialect-specific integration tests
  - package-test.yml: Validates package integrity

**Wheel Building:**
- cibuildwheel v3.3.1 - Multi-platform, multi-Python-version wheel generation
- Targets: cp39, cp310, cp311, cp312, cp313, cp314
- Platforms: Linux x86_64/aarch64, macOS universal2, Windows AMD64
- Source distribution (sdist) also published for source installs

**Version Management:**
- setuptools_scm - Automatic version detection from git tags
- Semantic versioning (MAJOR.MINOR.PATCH)
- Tag pattern: `v*` (e.g., `v24.0.0`)

## Development Tool Integrations

**Pre-commit Framework:**
- `.pre-commit-config.yaml` defines local hooks (not external service)
- Custom hooks:
  - Integration test sync scripts (on commit, checkout, push, merge)
  - ruff check and format
  - mypy type checking
  
**GitHub CLI Integration:**
- Optional: `gh` (GitHub CLI) used for integration test automation
- Not required for basic usage, only for managing integration test PRs

## Webhooks & Callbacks

**Incoming:** None

SQLGlot does not expose or receive webhooks.

**Outgoing:** None

SQLGlot does not send webhooks or callbacks to external services.

## Optional Development Dependencies

**Only for Development (extras_require["dev"]):**
- pandas - Test data generation and validation
- duckdb - Dialect-specific behavior validation
- pyperf - Performance benchmarking
- pdoc - Documentation HTML generation
- ruff, mypy, pre-commit - Code quality checks (local tools)

These dependencies are **never imported in production code** and only used in:
- `tests/` directory - Unit and integration test suites
- `benchmarks/` directory - Performance measurement
- Documentation generation
- CI/CD pipelines

## C Extension Build Dependencies

**sqlglotc (optional[c] extra):**
- mypyc (mypy compiler) - Compiles Python modules to C for performance
- setuptools, setuptools_scm - Build system
- mypy ecosystem - Type checking during compilation

Build-time only; resulting `.so` files contain no external dependencies.

## Third-Party Dialect Test Databases

**During Development/Testing:**
- DuckDB - In-memory database used to validate SQL transpilations
- Test fixtures stored in `tests/fixtures/` (local files, not external services)

**Not Used:**
- No Snowflake, BigQuery, Redshift, or other cloud database connections in the codebase
- Dialect transpilations tested by generating target SQL and validating syntax
- Type inference tested through optimizer rules without external schema providers

## No External Configuration Required

SQLGlot requires **zero environment variables** for runtime operation.

Optional environment variables (build-time only):
- `UV=1` - Use uv package manager instead of pip (development convenience)
- `MYPYPATH` - mypy import path (set during C extension build)
- `MYPYC_OPT` - Mypyc optimization flag (development build control)
- `SKIP_INTEGRATION=1` - Skip integration tests during test runs

## Integration Test Submodule

**Location:** `sqlglot-integration-tests/` (git submodule)

**Purpose:** Maintain compatibility with dbt, Airflow, and other integration scenarios

**Sync Mechanism:**
- Pre-commit hooks synchronize state across git operations
- Not a runtime dependency of sqlglot itself
- Optional for core development

## Lineage & Metadata Analysis

**Query Lineage Tracing:**
- Location: `sqlglot/lineage.py`
- Operates on parsed SQL AST
- No external lineage database
- Produces in-memory `Node` objects for column-level data flow tracking
- Can generate HTML visualization via `node.to_html()` (uses HTML generation, no external service)

**Schema Inference:**
- Optimizer rules infer types and relationships from SQL text
- No external schema lookup (user-provided schema via `schema` parameter)

## Summary: Zero Runtime Dependencies

SQLGlot achieves its "no-dependency" design by:
1. Implementing all parsing, transpilation, and optimization logic in pure Python
2. Using only Python standard library for core functionality
3. Avoiding network calls, external services, and system dependencies
4. Supporting optional mypyc compilation for performance (doesn't add runtime dependencies)
5. Keeping all test and development dependencies optional via setuptools extras

This design allows SQLGlot to be deployed anywhere Python 3.9+ is available without additional system dependencies or configuration.

---

*Integration audit: 2026-04-07*
