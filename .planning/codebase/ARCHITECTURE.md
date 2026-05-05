# Architecture

**Analysis Date:** 2026-04-07

## Pattern Overview

**Overall:** Classic three-phase compiler architecture (Tokenizer → Parser → Generator) with pluggable dialect system and optional AST optimization pipeline.

**Key Characteristics:**
- Recursive descent parser producing semantic AST (not syntax tree)
- Multi-dialect support via pluggable Dialect class hierarchy
- Semantic-preserving transpilation: parse in source dialect → AST → generate in target dialect
- Optional optimizer pipeline that applies sequential transformation rules
- Pure Python implementation with optional mypyc C extension for performance

## Layers

**Tokenization Layer:**
- Purpose: Converts SQL strings into token sequences (lexical analysis)
- Location: `sqlglot/tokens.py`, `sqlglot/tokenizer_core.py` (mypyc-compiled)
- Contains: Token definitions, TokenType enum, base Tokenizer class
- Depends on: Token definitions, dialect-specific token mappings
- Used by: Parser via `Tokenizer.tokenize()`

**Parsing Layer:**
- Purpose: Converts token sequences into Abstract Syntax Tree (lexical analysis → syntactic analysis)
- Location: `sqlglot/parser.py`, `sqlglot/parsers/` subdirectories
- Contains: Base Parser class with recursive descent parsing methods (pattern: `_parse_*`), builder functions
- Depends on: Tokens, Expression classes, dialect-specific parsers
- Used by: Dialect.parse() which returns list of Expr

**Expression Layer (AST):**
- Purpose: Represents all semantic SQL concepts as Python classes (AST nodes)
- Location: `sqlglot/expressions/` directory with modular organization (core.py, query.py, functions.py, etc.)
- Contains: Base Expr class, 300+ expression subclasses, AST traversal/transformation methods
- Depends on: Core Python, helper utilities
- Used by: Parser (output), Generator (input), Optimizer (transformation)

**Generation Layer:**
- Purpose: Converts AST back to SQL strings (code generation)
- Location: `sqlglot/generator.py`
- Contains: Base Generator class with auto-discovered methods (pattern: `<expr_name>_sql()`), TRANSFORMS dict
- Depends on: Expressions, dialect-specific generators, helper utilities
- Used by: Dialect.generate() which returns SQL string

**Optimization Layer:**
- Purpose: Applies semantic-preserving transformations to optimize AST
- Location: `sqlglot/optimizer/` directory
- Contains: Modular optimization rules (qualify, annotate_types, simplify, pushdown_predicates, etc.)
- Depends on: Expressions, Schema, Scope analysis
- Used by: Optional `optimize()` function; can be called independently

**Schema & Analysis Layer:**
- Purpose: Represents database structure and performs metadata analysis
- Location: `sqlglot/schema.py`, `sqlglot/optimizer/scope.py`, `sqlglot/optimizer/resolver.py`
- Contains: Schema classes (MappingSchema), table/column resolution, scope analysis for qualified identification
- Depends on: Expressions, Dialects
- Used by: Optimizer rules, qualifier, lineage analysis

**Lineage & Metadata Layer:**
- Purpose: Traces column-level data flow through SQL statements
- Location: `sqlglot/lineage.py`
- Contains: Lineage tracking, node dependency graphs
- Depends on: Expressions, Schema, Optimizer

**Dialect System:**
- Purpose: Encapsulates dialect-specific tokenizer, parser, and generator customizations
- Location: `sqlglot/dialects/dialect.py` (base), `sqlglot/dialects/<dialect>.py` (implementations)
- Contains: Base Dialect class, 34+ dialect implementations (Snowflake, BigQuery, PostgreSQL, etc.)
- Depends on: Tokenizer, Parser, Generator, Expressions
- Used by: All public APIs (tokenize, parse, transpile) via `Dialect.get_or_raise()`

## Data Flow

**Tokenization:**
1. SQL string input
2. Tokenizer maps lexemes to TokenType via KEYWORDS/SINGLE_TOKENS dicts
3. Handles string literals, identifiers, comments based on dialect
4. Output: list[Token] with text, type, position metadata

**Parsing:**
1. Token sequence from Tokenizer
2. Parser uses recursive descent, maintains index/cursor
3. Match methods: `_match()`, `_match_set()`, `_match_csv()`, `_parse_wrapped()`
4. Builds nested Expr objects, each with parent reference and arg_key
5. Output: list[Expr] (one per statement) or exp.Command for unparseable SQL

**Expression Building:**
1. Parser creates Expr instances using builders (e.g., `build_logarithm`, `build_like`)
2. Dialects can override builders via token→Callable mappings
3. Each Expr maintains: args dict, parent reference, arg_key, type metadata
4. Traversal methods: `.find()`, `.find_all()`, `.walk()`, `.transform()`

**Optimization (Optional):**
1. AST input to optimizer
2. Sequential rule application in order defined by RULES tuple
3. Each rule inspects/transforms AST using .find_all(), .transform()
4. Notable rules: qualify (requires schema), annotate_types (infers types), simplify (boolean/arithmetic)
5. Output: modified Expr with normalized structure

**Generation:**
1. Expr tree from Parser or Optimizer
2. Generator recursively traverses, dispatching to dialect-specific methods
3. Dispatch mechanism: auto-discovered `<expr_name>_sql()` methods + TRANSFORMS dict
4. Helper methods: `self.func()`, `self.sql()`, `self.expressions()`, `self.sep()`, `self.seg()`
5. Output: SQL string in target dialect

**Public API Flow:**
- `sqlglot.tokenize(sql, dialect)` → Dialect.tokenize() → list[Token]
- `sqlglot.parse(sql, dialect)` → Dialect.parse() → list[Expr]
- `sqlglot.parse_one(sql, dialect)` → Dialect.parse() → single Expr or Block
- `sqlglot.transpile(sql, read, write)` → Dialect.parse() → Dialect.generate() → list[str]
- `sqlglot.optimize(expr, schema, dialect)` → apply RULES sequentially → Expr

**State Management:**
- Tokenizer: maintains position tracking in SQL string
- Parser: maintains index/cursor in token sequence, error list
- Expr: maintains parent references, type annotations, metadata dict
- Generator: maintains formatting state (indent level, pretty-print flag)
- Optimizer: operates on AST structure via transformation, no mutable state

## Key Abstractions

**Expression (Expr):**
- Purpose: Base class for all AST nodes, represents semantic SQL concepts
- Examples: `exp.Select`, `exp.Column`, `exp.Alias`, `exp.BinaryOp`, `exp.Function`
- Pattern: Each subclass defines `arg_types` dict (field names → required boolean)
- Properties: `.this`, `.expression`, `.expressions` provide structured access to children
- Methods: `.find()`, `.find_all()`, `.walk()`, `.transform()`, `.sql()` for AST manipulation

**Dialect:**
- Purpose: Encapsulates language-specific syntax and semantics
- Examples: 34 implementations including Snowflake, BigQuery, PostgreSQL, DuckDB, Spark
- Pattern: Subclasses override Tokenizer, Parser, Generator; define feature flags
- Customization: KEYWORDS/SINGLE_TOKENS maps, FUNCTIONS maps, Generator.TRANSFORMS
- Access: `Dialect.get_or_raise(name)` returns singleton dialect instance

**Schema:**
- Purpose: Represents database structure for metadata-driven optimization
- Pattern: Abstract base class with MappingSchema implementation
- Structure: Nested dict {catalog: {db: {table: {column: type}}}} or shallower
- Usage: Passed to optimizer rules for type inference and qualification

**Generator Method Dispatch:**
- Purpose: Route each Expr type to appropriate SQL generation logic
- Pattern: `<expr_name>_sql(self, expression)` methods auto-discovered by name
- Fallback: TRANSFORMS dict for simple cases (rename_func, lambdas)
- Resolution: `_build_dispatch()` builds cache mapping Expr class → method

**Parser Builder Functions:**
- Purpose: Construct Expr instances with dialect-specific customizations
- Pattern: `build_<function_name>(args: BuilderArgs, dialect: Dialect) → Expr`
- Used by: Parser when evaluating function tokens via FUNCTIONS mapping
- Examples: `build_logarithm`, `build_array_concat`, `build_like`

**Optimization Rules:**
- Purpose: Semantic-preserving AST transformations
- Pattern: Function signature `rule(expr: Expr, schema: Schema, ...) → Expr`
- Execution: Applied sequentially in order defined by RULES tuple
- Examples: qualify (normalize), simplify (reduce expressions), pushdown_predicates

## Entry Points

**`sqlglot/__init__.py` Public API:**
- Location: `sqlglot/__init__.py`
- Triggers: User imports (e.g., `import sqlglot`)
- Responsibilities: Re-exports core classes and functions, initializes mypyc runtime

**`sqlglot.tokenize(sql, dialect)`:**
- Location: `sqlglot/__init__.py`
- Triggers: User calls tokenize()
- Responsibilities: Delegates to Dialect.tokenize(), returns Token list

**`sqlglot.parse(sql, dialect, **opts)`:**
- Location: `sqlglot/__init__.py`
- Triggers: User calls parse()
- Responsibilities: Delegates to Dialect.parse(), returns Expr list

**`sqlglot.parse_one(sql, dialect, into, **opts)`:**
- Location: `sqlglot/__init__.py`
- Triggers: User calls parse_one()
- Responsibilities: Calls Dialect.parse(), returns single Expr or raises error, handles Block for multiple statements

**`sqlglot.transpile(sql, read, write, **opts)`:**
- Location: `sqlglot/__init__.py`
- Triggers: User calls transpile()
- Responsibilities: Parses in read dialect, generates in write dialect, returns SQL strings

**`sqlglot.optimize(expression, schema, dialect, rules, **kwargs)`:**
- Location: `sqlglot/optimizer/optimizer.py`
- Triggers: User calls optimize()
- Responsibilities: Applies optimization rules sequentially, passes schema/dialect to each rule

**Dialect Initialization:**
- Location: `sqlglot/dialects/dialect.py`
- Triggers: `Dialect.get_or_raise()` called
- Responsibilities: Lazy-loads dialect module, instantiates Tokenizer/Parser/Generator classes

## Error Handling

**Strategy:** Fail softly with command fallback; errors collected during parsing without halting.

**Patterns:**
- Parser collects errors in `_errors` list instead of raising immediately
- Unparseable SQL wrapped in `exp.Command` to preserve original text
- ParseError, TokenError, UnsupportedError raised for critical failures
- ErrorLevel enum controls error reporting: IGNORE, WARN, RAISE

**Examples:**
- Invalid syntax: Parser returns exp.Command with original SQL
- Missing dialect: Dialect.get_or_raise() raises ParseError
- Unsupported generation: Generator.unsupported() logs warning or raises based on ErrorLevel

## Cross-Cutting Concerns

**Logging:** 
- Module-level loggers in each submodule (e.g., `logger = logging.getLogger("sqlglot")`)
- Logs errors, warnings, optimization steps; debug tracing in parser

**Validation:**
- Parser validation during token matching
- Schema validation in optimizer rules
- Type validation via annotate_types rule
- Unsupported feature detection in Generator via @unsupported_args decorator

**Authentication:**
- Not applicable (SQLGlot is a transpiler library, not a database client)

**Type Inference:**
- Handled by `annotate_types` optimizer rule
- Requires schema information for best results
- Attaches DataType to each Expr node

**Comment Preservation:**
- Comments collected during tokenization, attached to Expr nodes
- Best-effort preservation; not guaranteed across all transpilations

**Performance:**
- Core tokenizer and parser compiled to C via mypyc when using `[c]` extra
- Pure Python fallback available
- Generator optimized for minimal string allocations

---

*Architecture analysis: 2026-04-07*
