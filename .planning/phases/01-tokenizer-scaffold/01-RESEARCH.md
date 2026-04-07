# Phase 1: Tokenizer + Scaffold - Research

**Researched:** 2026-04-07
**Domain:** sqlglot dialect registration and tokenizer KEYWORDS mechanism
**Confidence:** HIGH

## Summary

Phase 1 creates `sqlglot/dialects/parlante.py` with a `Parlante(Postgres)` class and a `Tokenizer` inner class that overrides `KEYWORDS` to map `@@@`, `|||`, `###`, `===`, and `<=>` to `TokenType.OPERATOR`. The dialect is registered by adding `"Parlante"` to the `DIALECTS` list in `sqlglot/dialects/__init__.py`, which triggers lazy-loading by the metaclass when `dialect="parlante"` is first used.

The tokenizer mechanism is trie-based with longest-match semantics. Multi-character operator sequences like `@@@` require an explicit entry in `KEYWORDS` to be captured as a single token — without the entry the trie stops at `@@` (which Postgres maps to `TokenType.DAT`) and emits `@@` + `@` (PARAMETER). Every character in `@`, `|`, `#`, `=` is already in `SINGLE_TOKENS`; the trie's `single_token` flag is therefore `True` for all Parlante operators, which means the emit condition `prev_space or single_token or not char` is always satisfied, and the KEYWORDS override is sufficient.

`<->` is in the base `Tokenizer.KEYWORDS` (not Postgres-specific) as `TokenType.LR_ARROW`. Because Parlante inherits Postgres which inherits base, `<->` is present with no changes required. `@@` lives in `Postgres.Tokenizer.KEYWORDS` as `TokenType.DAT`; the Parlante Tokenizer inherits it unchanged.

**Primary recommendation:** Add five KEYWORDS entries to `Parlante.Tokenizer`, register the dialect via the `DIALECTS` list, and write token-level tests using `Dialect.tokenize()`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REG-01 | `sqlglot.parse_one(sql, dialect="parlante")` resolves the Parlante dialect | Metaclass auto-registers the class as `"parlante"` key; lazy-loading driven by `DIALECTS` list in `__init__.py` |
| TOK-01 | `@@@` tokenizes as a single `TokenType.OPERATOR` token | Add `"@@@": TokenType.OPERATOR` to KEYWORDS; trie longest-match selects it over the `@@` prefix |
| TOK-02 | `|||` tokenizes as a single `TokenType.OPERATOR` token | Add `"|||": TokenType.OPERATOR`; `|` is a SINGLE_TOKEN so trie entry is picked up automatically |
| TOK-03 | `###` tokenizes as a single `TokenType.OPERATOR` token | Add `"###": TokenType.OPERATOR`; `#` is a SINGLE_TOKEN |
| TOK-04 | `===` tokenizes as a single `TokenType.OPERATOR` token | Add `"===": TokenType.OPERATOR`; `=` is a SINGLE_TOKEN |
| TOK-05 | `<=>` tokenizes as `TokenType.OPERATOR` (overrides base `NULLSAFE_EQ`) | Override `"<=>": TokenType.OPERATOR` in Parlante.Tokenizer.KEYWORDS, shadowing the base entry |
| TOK-06 | `<->` tokenizes unchanged (L2 distance, no regression) | `<->` is in base `Tokenizer.KEYWORDS` as `TokenType.LR_ARROW`; Parlante inherits it, no action needed |
| TOK-07 | `@@` (tsvector match) tokenizes unchanged (no regression) | `@@` is in `Postgres.Tokenizer.KEYWORDS` as `TokenType.DAT`; Parlante inherits it via `**Postgres.Tokenizer.KEYWORDS` |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlglot.tokens.TokenType` | repo HEAD | Token type enum for all token classifications | Shared across all dialects; `OPERATOR` already exists |
| `sqlglot.dialects.postgres.Postgres` | repo HEAD | Base class for Parlante | Parlante is a Postgres superset; inherits all Postgres tokenizer, parser, generator |
| `sqlglot.dialects.dialect.Dialect` | repo HEAD | Metaclass-driven registration | `__new__` registers `clsname.lower()` in `_classes` automatically |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlglot.dialects.__init__.DIALECTS` list | repo HEAD | Drives lazy module loading | Add `"Parlante"` here to enable `dialect="parlante"` string lookup |
| `sqlglot.dialects.dialect.Dialects` enum | repo HEAD | Typed constants for dialects | Optional — OUT OF SCOPE per REQUIREMENTS.md; metaclass falls back to `clsname.lower()` |

**Installation:** No new dependencies. Files to create/modify:
- Create: `sqlglot/dialects/parlante.py`
- Modify: `sqlglot/dialects/__init__.py` (add `"Parlante"` to `DIALECTS`)

## Architecture Patterns

### Recommended File Structure

```
sqlglot/dialects/
├── parlante.py          # New file: Parlante dialect class
└── __init__.py          # Add "Parlante" to DIALECTS list

tests/dialects/
└── test_parlante.py     # New file: Phase 1 tokenizer tests
```

### Pattern 1: Dialect Registration via DIALECTS List

**What:** Add the class name string to `DIALECTS` in `sqlglot/dialects/__init__.py`. The `__getattr__` in that module will import `sqlglot.dialects.parlante` on first use and find `Parlante` in it.

**When to use:** Every new built-in dialect follows this pattern.

**Example (from `sqlglot/dialects/__init__.py`):**
```python
DIALECTS = [
    # ... existing dialects ...
    "Parlante",   # ADD THIS — must match class name exactly
]
```

The metaclass `_Dialect.__new__` then registers the key: `"parlante"` (since `Dialects.__members__` has no `PARLANTE` entry, it uses `clsname.lower()`).

### Pattern 2: Tokenizer KEYWORDS Override for Multi-Char Operators

**What:** Define `KEYWORDS` in the inner `Tokenizer` class, spreading the parent's dict first, then adding/overriding entries.

**When to use:** Any time a dialect needs to tokenize character sequences that conflict with or extend parent token definitions.

**Mechanism (from `sqlglot/tokenizer_core.py`):**
- `_KEYWORD_TRIE` is built from all `KEYWORDS` entries whose keys contain spaces or any `SINGLE_TOKENS` character
- `_scan_keywords()` uses the trie for longest-match: it records `word = chars` every time `0 in trie` (exact match found), then advances further looking for longer matches
- At the end, if `single_token` is True (any char in key is a SINGLE_TOKEN), the longest match wins
- All Parlante operators (`@@@`, `|||`, `###`, `===`, `<=>`) contain only SINGLE_TOKEN chars, so the trie condition triggers correctly

**Confirmed operator characters in `SINGLE_TOKENS`:**
- `@` → `TokenType.PARAMETER`
- `|` → `TokenType.PIPE`
- `#` → `TokenType.HASH`
- `=` → `TokenType.EQ`
- `<` → `TokenType.LT`
- `>` → `TokenType.GT`
- `-` → `TokenType.DASH`

**Example — the complete Parlante dialect file for Phase 1:**
```python
from __future__ import annotations

from sqlglot.dialects.postgres import Postgres
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
```

### Pattern 3: Tokenizer Tests via `Dialect.tokenize()`

**What:** Instantiate the dialect and call `.tokenize(sql)` to get a `list[Token]`, then assert on `token.token_type` and `token.text`.

**Example (modeled on `tests/test_tokens.py`):**
```python
import unittest
import sqlglot
from sqlglot.tokens import TokenType


class TestParlante(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importing triggers registration via metaclass
        from sqlglot.dialects.parlante import Parlante
        cls.dialect = Parlante()

    def test_ttt_operator(self):
        tokens = self.dialect.tokenize("col @@@ 'query'")
        op = next(t for t in tokens if t.text == "@@@")
        self.assertEqual(op.token_type, TokenType.OPERATOR)
```

### Anti-Patterns to Avoid

- **Using `Dialects` enum entry:** Out of scope per REQUIREMENTS.md. The metaclass auto-registers via `clsname.lower()` when no enum member matches. Do not add `PARLANTE = "parlante"` to the `Dialects` enum.
- **Modifying `tokens.py` base KEYWORDS:** Never modify the shared base. Override only in the dialect's inner `Tokenizer` class.
- **Adding parser/generator logic in Phase 1:** Phase 1 only covers tokenizer and scaffold. Parser (PAR-*) and Generator (GEN-*) requirements are Phase 2.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Longest-match operator tokenization | Custom scan loop | `KEYWORDS` dict entry | `_scan_keywords()` already implements trie longest-match |
| Dialect lookup by string | Custom registry | `DIALECTS` list + metaclass | `_Dialect.__new__` and `_try_load` handle registration and lazy import |
| Test helpers for parse/generate | Custom assertion utils | `Validator.validate_identity()` from `tests/dialects/test_dialect.py` | Already handles parse → generate round-trip comparison |

**Key insight:** The trie longest-match is the entire solution for TOK-01 through TOK-05. No custom tokenizer method override needed — only data (KEYWORDS entries).

## Common Pitfalls

### Pitfall 1: Forgetting `**Postgres.Tokenizer.KEYWORDS` spread

**What goes wrong:** Writing `KEYWORDS = {"@@@": TokenType.OPERATOR, ...}` without the spread drops all Postgres keyword mappings including `@@` → `DAT`, `<->` → `LR_ARROW`, and all SQL keywords.

**Why it happens:** Python class attribute assignment replaces the parent's value entirely.

**How to avoid:** Always start with `**Postgres.Tokenizer.KEYWORDS` then add/override specific entries.

**Warning signs:** `@@` no longer parsed as DAT, basic SQL keywords fail to tokenize.

### Pitfall 2: Missing `DIALECTS` entry in `__init__.py`

**What goes wrong:** Importing `parlante.py` directly works in Python, but `sqlglot.parse_one("...", dialect="parlante")` raises `ValueError: ... Unknown dialect 'parlante'`.

**Why it happens:** `get_or_raise` calls `cls.get("parlante")`, which calls `_try_load("parlante")`. `_try_load` only attempts `importlib.import_module(f"sqlglot.dialects.{key}")` when `key in DIALECT_MODULE_NAMES`. `DIALECT_MODULE_NAMES` is derived from the `DIALECTS` list. Without the list entry, the import is never attempted.

**How to avoid:** Add `"Parlante"` to the `DIALECTS` list in `sqlglot/dialects/__init__.py`.

**Warning signs:** REG-01 test fails with ValueError even though the file exists.

### Pitfall 3: `<=>` not overriding base NULLSAFE_EQ

**What goes wrong:** `<=>` still tokenizes as `TokenType.NULLSAFE_EQ` under Parlante.

**Why it happens:** The base `Tokenizer.KEYWORDS` has `"<=>": TokenType.NULLSAFE_EQ`. If the spread comes first and the override is missing, the base value is kept.

**How to avoid:** After `**Postgres.Tokenizer.KEYWORDS`, explicitly add `"<=>": TokenType.OPERATOR` (the dict literal later entry wins).

**Warning signs:** TOK-05 assertion fails; token type is NULLSAFE_EQ not OPERATOR.

### Pitfall 4: `@@@` splits into `@@` + `@`

**What goes wrong:** Without `"@@@"` in KEYWORDS, the trie finds `@@` as the longest match (→ `TokenType.DAT` from Postgres), then the remaining `@` is emitted as `TokenType.PARAMETER`.

**Why it happens:** The trie longest-match records the last complete word found while advancing. Without `@@@` in the trie, `@@` is the longest complete entry.

**How to avoid:** Add `"@@@": TokenType.OPERATOR` to KEYWORDS.

**Warning signs:** `sqlglot.tokenize("col @@@ 'x'", dialect="parlante")` returns 5+ tokens instead of 4.

## Code Examples

### Complete `parlante.py` for Phase 1

```python
# Source: Pattern derived from sqlglot/dialects/singlestore.py and postgres.py
from __future__ import annotations

from sqlglot.dialects.postgres import Postgres
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
```

### Registration change in `sqlglot/dialects/__init__.py`

```python
# Source: sqlglot/dialects/__init__.py pattern
DIALECTS = [
    # ... existing entries in alphabetical order ...
    "Parlante",  # ADD — between "Oracle" and "Postgres" alphabetically
    # ... rest of list ...
]
```

### Phase 1 test file skeleton

```python
# Source: tests/dialects/test_dialect.py Validator pattern
import unittest
import sqlglot
from sqlglot.tokens import TokenType
from tests.dialects.test_dialect import Validator


class TestParlante(Validator):
    dialect = "parlante"

    def test_dialect_registered(self):
        self.assertIsNotNone(sqlglot.parse_one("SELECT 1", dialect="parlante"))

    def test_operator_tokens(self):
        for op in ("@@@", "|||", "###", "===", "<=>"):
            with self.subTest(op=op):
                tokens = sqlglot.Dialect.get_or_raise("parlante").tokenize(f"a {op} b")
                op_token = next(t for t in tokens if t.text == op)
                self.assertEqual(op_token.token_type, TokenType.OPERATOR)

    def test_no_regression_at_at(self):
        tokens = sqlglot.Dialect.get_or_raise("parlante").tokenize("a @@ b")
        op_token = next(t for t in tokens if t.text == "@@")
        self.assertEqual(op_token.token_type, TokenType.DAT)

    def test_no_regression_lr_arrow(self):
        tokens = sqlglot.Dialect.get_or_raise("parlante").tokenize("a <-> b")
        op_token = next(t for t in tokens if t.text == "<->")
        self.assertEqual(op_token.token_type, TokenType.LR_ARROW)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `PARLANTE = "parlante"` in `Dialects` enum required | Metaclass auto-registers via `clsname.lower()` | Present in codebase | No enum entry needed; REQUIREMENTS.md marks this as out-of-scope |
| External plugin via entry points | DIALECTS list + module in package | Present in codebase | Built-in dialects use DIALECTS list; entry_points is fallback for plugins |

## Open Questions

1. **Alphabetical placement of `"Parlante"` in DIALECTS**
   - What we know: The list is roughly alphabetical
   - What's unclear: Whether order matters for anything beyond readability
   - Recommendation: Place between `"Oracle"` and `"Postgres"` (alphabetical); order has no functional impact

2. **Test placement: `tests/dialects/test_parlante.py` vs `tests/test_tokens.py`**
   - What we know: Dialect tests live in `tests/dialects/`; token tests in `tests/test_tokens.py`
   - What's unclear: Which file is more appropriate for Phase 1 (tokenizer-only) tests
   - Recommendation: Use `tests/dialects/test_parlante.py` as the long-term home; Phase 1 tests go there even though they only exercise the tokenizer; Phase 2 tests extend the same file

## Sources

### Primary (HIGH confidence)

- Codebase read: `sqlglot/tokenizer_core.py` `_scan_keywords()` — confirmed trie longest-match logic, `single_token` flag behavior, emit condition
- Codebase read: `sqlglot/tokens.py` `Tokenizer.KEYWORDS` and `SINGLE_TOKENS` — confirmed `@`, `|`, `#`, `=`, `<`, `>`, `-` are all SINGLE_TOKENS; `<=>` maps to `NULLSAFE_EQ`, `<->` maps to `LR_ARROW`
- Codebase read: `sqlglot/dialects/postgres.py` `Tokenizer.KEYWORDS` — confirmed `@@` maps to `TokenType.DAT`; `<->` NOT in Postgres-specific KEYWORDS (lives in base)
- Codebase read: `sqlglot/dialects/__init__.py` — confirmed `DIALECTS` list, `MODULE_BY_DIALECT`, lazy `__getattr__` import pattern
- Codebase read: `sqlglot/dialects/dialect.py` `_Dialect.__new__` — confirmed metaclass registers `clsname.lower()` when no `Dialects` enum member matches
- Codebase read: `sqlglot/trie.py` `new_trie()` — confirmed trie structure and `{0: True}` leaf sentinel for complete-word match

### Secondary (MEDIUM confidence)

- `PARLANTE_DIALECT.md` in repo root — author's own description of intended implementation; aligned with what codebase analysis shows

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all from direct codebase reads
- Architecture: HIGH — trie mechanism traced to source, registration path confirmed
- Pitfalls: HIGH — each pitfall derived from specific code paths in `_scan_keywords()` and `_try_load()`

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable codebase; only invalidated by changes to tokenizer_core.py or dialect registration)
