# Phase 3: AT BRANCH and @branch Table Syntax - Research

**Researched:** 2026-04-08
**Domain:** SQLGlot parser/generator extension — version clause on table references
**Confidence:** HIGH

## Summary

Phase 3 extends the Parlante parser and generator to handle catalog branch references on table expressions. The implementation requires overriding `_parse_version` in `ParlanteParse` and `version_sql` in `ParlanteGenerator`. No new expression classes, no new token types, and no changes to the base SQLGlot codebase are needed.

The two syntax forms (`AT BRANCH <name>` and `@<name>`) map to the same `exp.Version(this="BRANCH", kind="AT", expression=<identifier>)` AST node. The tokenizer already produces `PARAMETER` for `@` and `DAT` for `@@` — no tokenizer changes are required and `@@` (tsvector) is not at risk.

The generator override is trivial: the base `version_sql` produces `FOR BRANCH AT main`; the Parlante override must emit `AT BRANCH main` instead.

**Primary recommendation:** Override `_parse_version` in `ParlanteParse` to detect both `AT BRANCH <name>` (text sequence) and `PARAMETER` + `VAR` (`@<name>`), then override `version_sql` in `ParlanteGenerator` to emit `AT BRANCH <name>`. No tokenizer changes needed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Syntax forms
- Parse BOTH `AT BRANCH <name>` and `@<name>` shorthand on table references
- `table@main` and `table AT BRANCH main` are semantically identical (pure syntactic sugar)
- Scope limited to AT BRANCH only — no AT TAG, AT COMMIT, or other Nessie versioning forms
- Both forms always accepted — no env var / config toggle (dialect is stateless)

#### AST representation
- Reuse `exp.Version` (existing expression class) to store branch info
- Store as `Version(this="BRANCH", kind="AT", expression=<identifier>)` on `table.args["version"]`
- Branch and time-travel versioning are mutually exclusive (share the same slot) — this correctly models reality since no database supports both simultaneously
- No new expression class needed

#### Generator round-trip
- Always emit `AT BRANCH <name>` form (normalize @shorthand to verbose form)
- Override `version_sql` in Parlante generator to handle `this="BRANCH"` case
- Non-branch Version expressions (e.g. TIMESTAMP AS OF from Spark transpilation) should raise unsupported error
- AT BRANCH appears before table alias: `table AT BRANCH main AS t` (ALIAS_POST_VERSION=True, like Spark)

### Claude's Discretion
- Exact tokenizer changes needed for `@branch` shorthand parsing (may need special handling to avoid collision with `@@` tsvector operator)
- How to wire `AT BRANCH` keyword sequence into `_parse_version()` or a Parlante override
- Test structure and specific test cases beyond the round-trip requirement

### Deferred Ideas (OUT OF SCOPE)
- AT TAG / AT COMMIT (Nessie catalog versioning) — add as future phase if needed
- Config toggle for strict mode (only allow one syntax form) — not needed given stateless dialect design
- LanceDB `@version` numeric shorthand — different semantics, different phase
</user_constraints>

---

## Standard Stack

### Core (all from SQLGlot itself — no external dependencies)

| Component | Location | Purpose | Notes |
|-----------|----------|---------|-------|
| `exp.Version` | `sqlglot/expressions/query.py:1100` | Stores branch/version info on table | `arg_types = {"this": True, "kind": True, "expression": False}` |
| `_parse_version` | `sqlglot/parser.py:4797` | Base version parsing — called from `_parse_table` | Override in `ParlanteParse` |
| `version_sql` | `sqlglot/generator.py:2424` | Base version generation | Override in `ParlanteGenerator` |
| `ALIAS_POST_VERSION` | `sqlglot/dialects/dialect.py:753` | Controls version-before-alias ordering | Already `True` for Parlante (default) |
| `_match_text_seq` | `sqlglot/parser.py:1926` | Match a sequence of text tokens by value | Use for `AT BRANCH` sequence |
| `_parse_id_var` | `sqlglot/parser.py:8224` | Parse an identifier or variable token | Use for branch name |

### Supporting

| Component | Location | Purpose |
|-----------|----------|---------|
| `TokenType.PARAMETER` | `sqlglot/tokens.py:147` | `@` single character token | Already produced for `@` |
| `TokenType.DAT` | `sqlglot/dialects/postgres.py:73` | `@@` tsvector operator | Unaffected by our changes |
| `_is_connected` | `sqlglot/parser.py:1941` | Check if tokens are adjacent (no space) | Can guard `@branch` parsing |

---

## Architecture Patterns

### Pattern 1: Overriding `_parse_version` in a dialect parser

The base `_parse_version` is defined in `sqlglot/parser.py` and is called from `_parse_table` at two points:
- Line 4757: when `ALIAS_POST_VERSION=True` — before alias (Parlante's case)
- Line 4785: when `ALIAS_POST_VERSION=False` — after alias

The override pattern is: call `super()._parse_version()` first (handles `FOR VERSION` / `FOR TIMESTAMP` — existing Presto/Iceberg forms), then add additional cases before returning `None`:

```python
# In ParlanteParse
def _parse_version(self) -> exp.Version | None:
    # Handle AT BRANCH <name> keyword sequence
    if self._match_text_seq("AT", "BRANCH"):
        return self.expression(
            exp.Version(
                this="BRANCH",
                kind="AT",
                expression=self._parse_id_var(),
            )
        )
    # Handle @<name> shorthand (PARAMETER token immediately after table name)
    if self._match(TokenType.PARAMETER):
        return self.expression(
            exp.Version(
                this="BRANCH",
                kind="AT",
                expression=self._parse_id_var(),
            )
        )
    return super()._parse_version()
```

### Pattern 2: Overriding `version_sql` in a dialect generator

Existing examples in the codebase:
- `bigquery.py:660`: remaps `TIMESTAMP` → `SYSTEM_TIME`
- `hive.py:449`: strips the `FOR ` prefix
- `tsql.py:478`: handles `FROM`/`BETWEEN` range forms

The Parlante override must:
1. Handle `this == "BRANCH"` → emit `AT BRANCH <name>`
2. Raise unsupported for any other `this` value (non-branch Version expressions)

```python
# In ParlanteGenerator
def version_sql(self, expression: exp.Version) -> str:
    if expression.name != "BRANCH":
        self.unsupported(f"Version kind '{expression.name}' is not supported in Parlante")
        return ""
    return f"AT BRANCH {self.sql(expression, 'expression')}"
```

### Pattern 3: Generator table_sql — version positioning

The base `generator.py:table_sql` (line 2298) already handles `ALIAS_POST_VERSION`:
- When `True`: version SQL is placed in `pre_alias` — **before** the alias
- The `table_sql` result is: `{table}{version} {alias}`

This means `SELECT * FROM t AT BRANCH main AS tbl` is produced correctly if `version_sql` emits `AT BRANCH main` and `ALIAS_POST_VERSION=True` (which is already the default).

### Tokenizer token flow for `t@main`

Verified by live test:

```
VAR: 't'          (start=14, end=14)
PARAMETER: '@'    (start=15, end=15)  ← adjacent to 't'
VAR: 'main'       (start=16, end=19)
```

The `@` is `TokenType.PARAMETER` (base tokenizer SINGLE_TOKENS). The Postgres tokenizer maps `@@` → `TokenType.DAT` in its KEYWORDS dict, which the trie processes before SINGLE_TOKENS, so `@@` is **not** affected by our `@` handling.

**No tokenizer changes needed** — the `PARAMETER` token is already produced correctly.

### Anti-Patterns to Avoid

- **Adding `AT BRANCH` to tokenizer KEYWORDS dict**: Unnecessary. `_match_text_seq("AT", "BRANCH")` works because both tokens are `VAR` and `_match_text_seq` matches by text value. Adding a multi-word token type would require a new `TokenType` enum member in the base tokens.py (which would be a change to base SQLGlot, not desired).
- **Using `_is_connected()` guard on PARAMETER**: While `t@main` has `@` adjacent to `t`, the `@` is consumed **after** `_parse_table_parts` returns (at the `_parse_version` call site). By that point the cursor is past the table name. `_is_connected()` would check the current position vs `@`, not `t` vs `@`. It is safe to simply match `TokenType.PARAMETER` without a connectivity guard — if `@` appears elsewhere (e.g. in a WHERE clause), it won't reach `_parse_version`.
- **Adding `@` to `RANGE_PARSERS`**: The existing `TokenType.OPERATOR` entry in `RANGE_PARSERS` handles infix operators. `@branch` is not infix — it's a postfix on the table name. Using RANGE_PARSERS here would be wrong architecture.
- **Building SQL with f-strings in `version_sql`**: Only use `self.sql(expression, 'expression')` for the branch name to ensure proper quoting/escaping of identifiers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Keyword sequence matching | Custom token lookahead | `_match_text_seq("AT", "BRANCH")` |
| Identifier parsing for branch name | Custom identifier extraction | `_parse_id_var()` |
| Version-before-alias ordering | Custom table_sql | `ALIAS_POST_VERSION=True` (already default) |
| Unsupported construct error | Custom exception | `self.unsupported("message")` |

---

## Common Pitfalls

### Pitfall 1: `AT` conflicts with `AtIndex`
**What goes wrong:** The base parser at line 4771 has `if isinstance(this, exp.Table) and self._match_text_seq("AT")` — it creates `exp.AtIndex`. If `AT BRANCH` is not consumed by `_parse_version` first, the `AT` would create an `AtIndex` with `BRANCH` as the expression.

**Why it happens:** `_match_text_seq` at line 4771 only matches `AT`, then tries to parse an `id_var` for whatever follows.

**How to avoid:** In `ALIAS_POST_VERSION=True` mode, `_parse_version()` is called at line 4757, **before** line 4771. The Parlante `_parse_version` override consumes `AT BRANCH <name>` before the `AtIndex` check is reached. This is safe by design.

**Warning signs:** `sqlglot.parse_one("SELECT * FROM t AT BRANCH main", dialect="parlante")` returns an `exp.AtIndex` instead of `exp.Table` with a `version` arg.

### Pitfall 2: `@` consumed as Postgres parameter
**What goes wrong:** In some contexts `@` is a parameter placeholder (e.g., `@var` in T-SQL). However, in Postgres-derived dialects, `@` in a SELECT/WHERE expression is unusual. The `PARAMETER` token handler in the primary expression parsers (line 1158: `TokenType.PARAMETER: lambda self: self._parse_parameter()`) would consume `@` in expression context.

**Why it happens:** `@` is in the primary expression handlers. But `_parse_version` is called from `_parse_table` after table parts are parsed — not from expression parsing. When the cursor is positioned right after a table name and sees `PARAMETER`, only `_parse_version` is checking at that point.

**How to avoid:** The `_parse_version` override in `ParlanteParse` runs in the table context (called from `_parse_table`), not the expression context. There is no conflict.

**Warning signs:** `SELECT * FROM t@main` parses the `@main` as a parameter expression rather than a version.

### Pitfall 3: Base `version_sql` output format
**What goes wrong:** If `version_sql` is not overridden in `ParlanteGenerator`, the base implementation produces `FOR BRANCH AT main` (confirmed by live test), not `AT BRANCH main`.

**Why it happens:** Base `version_sql` is `f"FOR {expression.name} {kind} {expr}"` — designed for Presto/Iceberg `FOR VERSION AS OF <expr>` pattern.

**How to avoid:** Override `version_sql` in `ParlanteGenerator`. Already a locked decision.

### Pitfall 4: Quoted branch names
**What goes wrong:** Branch names like `"my-branch"` (quoted identifiers) should be emitted with quotes in the generated SQL. Using string interpolation `f"AT BRANCH {expression.expression.name}"` would strip quoting.

**How to avoid:** Use `self.sql(expression, 'expression')` in `version_sql` — this correctly handles both quoted and unquoted identifiers.

---

## Code Examples

### Verified: exp.Version for BRANCH (live test)

```python
from sqlglot import exp
v = exp.Version(this="BRANCH", kind="AT", expression=exp.to_identifier("main"))
# v.name  → "BRANCH"
# v.text("kind")  → "AT"
# Base generator: "FOR BRANCH AT main"  (wrong — must override)
```

### Verified: Tokenizer output for t@main and a@@b (live test)

```python
# sqlglot.tokenize("SELECT * FROM t@main", dialect="parlante")
# VAR 't', PARAMETER '@', VAR 'main'

# sqlglot.tokenize("SELECT a @@ b", dialect="parlante")  
# VAR 'a', DAT '@@', VAR 'b'   ← @@ is unaffected
```

### Verified: table_sql with ALIAS_POST_VERSION=True (live test)

```python
# With version_sql returning "FOR BRANCH AT main" (base behavior):
# table_sql result: "mytable FOR BRANCH AT main AS t"
# With version_sql returning "AT BRANCH main" (Parlante override):
# table_sql result: "mytable AT BRANCH main AS t"
```

### Verified: _match_text_seq for AT BRANCH tokens

```python
# sqlglot.tokenize("SELECT * FROM t AT BRANCH main", dialect="parlante")
# VAR 'AT', VAR 'BRANCH', VAR 'main'
# → _match_text_seq("AT", "BRANCH") matches both tokens by text value
```

### Pattern: _parse_version override (prescriptive)

```python
# In sqlglot/parsers/parlante.py
from sqlglot.tokens import TokenType
from sqlglot import exp

class ParlanteParse(PostgresParser):
    # ... existing code ...
    
    def _parse_version(self) -> exp.Version | None:
        if self._match_text_seq("AT", "BRANCH"):
            return self.expression(
                exp.Version(this="BRANCH", kind="AT", expression=self._parse_id_var())
            )
        if self._match(TokenType.PARAMETER):
            return self.expression(
                exp.Version(this="BRANCH", kind="AT", expression=self._parse_id_var())
            )
        return super()._parse_version()
```

### Pattern: version_sql override (prescriptive)

```python
# In sqlglot/generators/parlante.py
class ParlanteGenerator(PostgresGenerator):
    # ... existing code ...
    
    def version_sql(self, expression: exp.Version) -> str:
        if expression.name != "BRANCH":
            self.unsupported(f"Parlante only supports AT BRANCH versioning, got: {expression.name!r}")
            return ""
        return f"AT BRANCH {self.sql(expression, 'expression')}"
```

---

## Open Questions

1. **Should `@<name>` with a space be accepted?**
   - What we know: `t @ main` (with spaces) tokenizes as `VAR PARAMETER VAR` identically to `t@main`. The `_match(TokenType.PARAMETER)` in `_parse_version` doesn't care about adjacency.
   - What's unclear: Whether the user intends the shorthand to require no space (like Nessie CLI syntax) or to allow it.
   - Recommendation: Accept both — `_match(TokenType.PARAMETER)` does not enforce adjacency, and requiring it would need `_is_connected()` guard. Accept both forms silently; this is the simpler implementation.

2. **Should `version_sql` propagate unsupported or raise immediately?**
   - What we know: `self.unsupported()` respects the generator's `unsupported_level` setting — it can either collect messages or raise `UnsupportedError` immediately.
   - Recommendation: Use `self.unsupported(...)` (not `raise`) to follow the existing pattern used throughout all generators. The caller controls error level.

---

## Sources

### Primary (HIGH confidence — verified by reading source code + live tests)

- `sqlglot/parser.py` — `_parse_version` (line 4797), `_parse_table` flow (lines 4756–4785), `_match_text_seq` (line 1926), `_parse_id_var` (line 8224)
- `sqlglot/generator.py` — `version_sql` (line 2424), `table_sql` (lines 2280–2339), `unsupported` (line 953)
- `sqlglot/expressions/query.py` — `class Version` (line 1100)
- `sqlglot/tokens.py` — `SINGLE_TOKENS` `"@": TokenType.PARAMETER` (line 147), trie construction (line 108–117)
- `sqlglot/dialects/postgres.py` — `"@@": TokenType.DAT` (line 73)
- `sqlglot/dialects/dialect.py` — `ALIAS_POST_VERSION = True` (line 753)
- Live Python tests confirming token output for `t@main`, `a@@b`, and `AT BRANCH main`

### Secondary (MEDIUM confidence — read code, not live-tested end-to-end)

- `sqlglot/generators/bigquery.py:660`, `hive.py:449`, `tsql.py:478` — existing `version_sql` override patterns

---

## Metadata

**Confidence breakdown:**
- Tokenizer behavior: HIGH — verified by live tokenizer output
- Parser flow (AT BRANCH): HIGH — read source, confirmed ALIAS_POST_VERSION ordering, no conflict with AtIndex
- Parser flow (@shorthand): HIGH — confirmed PARAMETER token, no conflict with expression context
- Generator override: HIGH — confirmed base output, pattern clear from existing overrides
- ALIAS_POST_VERSION positioning: HIGH — read table_sql source, confirmed with live test
- No tokenizer changes needed: HIGH — confirmed PARAMETER already produced

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable codebase, no fast-moving dependencies)
