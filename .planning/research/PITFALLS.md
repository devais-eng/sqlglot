# Pitfalls Research

**Domain:** Adding a Postgres-extending dialect (Parlante) to sqlglot
**Researched:** 2026-04-07
**Confidence:** HIGH — all findings verified against source code

## Critical Pitfalls

### Pitfall 1: MATCH Keyword Blocked by FUNCTION_PARSERS

**What goes wrong:**
`MATCH(x)` silently parses as a MySQL-style `MATCH(cols) AGAINST(...)` construct instead of a plain function call. The `FUNCTION_PARSERS` dict in the base `parser.Parser` has `"MATCH"` mapped to `_parse_match_against` (line 1487 of `parser.py`). This handler fires before `FUNCTIONS` dict lookup (lines 6785–6787 of `parser.py`). Adding `"MATCH"` to the dialect's `FUNCTIONS` dict has zero effect because `FUNCTION_PARSERS` short-circuits it.

**Why it happens:**
Developers assume `FUNCTIONS` dict entries override all other parsing paths. They do not — `FUNCTION_PARSERS` takes priority inside `_parse_function_call`. The `"MATCH"` entry in `FUNCTION_PARSERS` is inherited from `parser.Parser` and is not overridden by `PostgresParser`.

**How to avoid:**
In `ParlanteParsers.FUNCTION_PARSERS`, exclude the inherited `"MATCH"` entry using a dict comprehension filter:

```python
FUNCTION_PARSERS = {
    k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"
}
```

Then add the desired `"MATCH"` entry to `FUNCTIONS` normally.

**Warning signs:**
- `MATCH(x)` produces an `exp.MatchAgainst` node instead of `exp.Anonymous` or your custom expression
- `repr(parse_one("MATCH(x)", dialect="parlante"))` shows `MatchAgainst`
- `validate_identity("MATCH(x)")` fails with unexpected SQL output

**Phase to address:**
Phase 1 (Tokenizer + Parser foundation), before any function alias work.

---

### Pitfall 2: TRANSFORMS Inheritance Silences Auto-Discovered Generator Methods

**What goes wrong:**
When a child generator defines `TRANSFORMS = {**PostgresGenerator.TRANSFORMS, ...}`, any expression type that Postgres already handles via a TRANSFORMS entry will block the child's auto-discovered `<expr>_sql` method. The dispatch builder (`generator.py` lines 77–92) fills dispatch from `cls.TRANSFORMS` first, then adds auto-discovered methods only for types `not in dispatch` (line 89). If `exp.SomeExpr` is in the inherited TRANSFORMS, a `someexpr_sql` method on the child generator is silently ignored.

**Why it happens:**
Developers define both a `TRANSFORMS` entry (inherited from parent) and a new `_sql` method for the same expression type. The `_build_dispatch` function is explicit: TRANSFORMS wins over auto-discovery.

**How to avoid:**
To override a parent TRANSFORMS entry with a child method, remove the entry from the child's TRANSFORMS using a dict filter:

```python
TRANSFORMS = {
    k: v for k, v in PostgresGenerator.TRANSFORMS.items()
    if k not in {exp.BitwiseXor, exp.SomeOtherExpr}
    # Now define someotherexpr_sql(self, expression) as a method
}
```

Alternatively, put the override directly in TRANSFORMS as a lambda or module-level function (only use methods for complex, single-entry-point logic per CLAUDE.md coding rule 1).

**Warning signs:**
- A `<expr>_sql` method on the generator is never called during tests
- Adding `print()` to the method never fires
- Output matches Postgres behavior even after overriding the method

**Phase to address:**
Phase 2 (Generator), before any output rendering work.

---

### Pitfall 3: `<=>` Conflicts with NULLSAFE_EQ Already in the Base Tokenizer

**What goes wrong:**
`<=>` is already defined in `tokens.Tokenizer.KEYWORDS` as `TokenType.NULLSAFE_EQ` (line 217 of `tokens.py`), and `TokenType.NULLSAFE_EQ` is handled by `parser.Parser.EQUALITY` as `exp.NullSafeEQ`. If Parlante wants `<=>` to mean a custom operator, overriding the KEYWORDS entry will shadow NULL-safe equality for ALL queries that transit through the Parlante dialect — including transpilations from MySQL or other dialects that produce `exp.NullSafeEQ`.

**Why it happens:**
The tokenizer maps the character sequence `<=>` to a TokenType at scan time. There is no per-statement context. Once `<=>` maps to a custom `TokenType`, the NullSafeEQ semantic is gone for this dialect's tokenizer.

**How to avoid:**
Option A: Assign `<=>` to a brand-new `TokenType` (e.g., `SPACESHIP_OP`) and add that new token to `RANGE_PARSERS` in the parser. Accept that NullSafeEQ transpilation through Parlante is broken.

Option B: Keep `<=>` as `TokenType.NULLSAFE_EQ` and handle it in the generator by overriding the `nullsafeeq_sql` method or the `exp.NullSafeEQ` TRANSFORMS entry to emit the Parlante-specific operator text.

Option B is almost always correct — it preserves cross-dialect transpilation. Option A should only be chosen if Parlante's `<=>` has fundamentally different semantics that cannot map onto NullSafeEQ.

**Warning signs:**
- Cross-dialect tests `validate_all("x <=> y", write={"mysql": ...})` break
- MySQL queries using `<=>` fail to transpile to Parlante correctly

**Phase to address:**
Phase 1 (Tokenizer), as the first decision before defining any operator semantics.

---

### Pitfall 4: New TokenType Values Require Rebuilding the mypyc Extension

**What goes wrong:**
New `TokenType` enum values must be added to `sqlglot/tokenizer_core.py`. This file is compiled into a `.so` extension by `sqlglotc/setup.py`. If a developer has an installed C extension (via `make install-devc`) and adds new TokenType values without rebuilding, the Python `tokenizer_core.TokenType` and the compiled extension's `TokenType` will be out of sync, causing `AttributeError` or integer mismatch errors at runtime.

**Why it happens:**
`tokenizer_core.py` is the only source for `TokenType` and `Token`. It is shared between pure-Python and mypyc paths. The enum uses `auto()` which assigns sequential integers. Adding a new value in the middle reorders all subsequent values in the compiled binary.

**How to avoid:**
Always append new `TokenType` values at the END of the enum, never in the middle. After adding values, run `make test` (not `make testc`) which hides `.so` files during the run. Only run `make testc` after also running `make install-devc` to rebuild the extension.

**Warning signs:**
- `AttributeError: TRIPLE_AT` when the C extension is loaded
- Tests pass with `make unit` but fail with `make unitc`
- Cryptic `TokenType` comparison failures where an int value mismatches

**Phase to address:**
Phase 1 (Tokenizer), whenever new TokenType values are introduced.

---

### Pitfall 5: Multi-Char Operators That Are Strict Prefixes of Each Other

**What goes wrong:**
Postgres already defines `@@` as `TokenType.DAT`. Adding `@@@` requires careful trie interaction. The trie scanner is greedy (longest match wins) — so `@@@` will correctly beat `@@` IF both are in the trie. The danger is the reverse: if only `@@` is defined, the input `@@@` tokenizes as `@@` + a single `@` PARAMETER token. Similarly `|||` is `||` (DPIPE) + `|` (PIPE). `###` is `#` (HASH) three times. `===` is `==` (EQ) + `=` (EQ).

The trie only includes an entry when: `" " in key or any(single in key for single in cls.SINGLE_TOKENS)` (line 116 of `tokens.py`). All proposed operators contain SINGLE_TOKEN characters (`@`, `|`, `#`, `=`) so they will be correctly inserted into the trie.

**Why it happens:**
Developers forget that the trie can only match a longer key if that longer key is explicitly registered. The greedy match works correctly, but only over registered keywords.

**How to avoid:**
In the Parlante tokenizer KEYWORDS, add all three-char operators BEFORE testing. Verify with a quick tokenization check:

```python
from sqlglot.dialects.parlante import Parlante
tokens = Parlante.tokenizer_class().tokenize("x @@@ y")
assert tokens[1].text == "@@@", f"got {tokens[1].text}"
```

**Warning signs:**
- Tokenizing `x @@@ y` yields 3 tokens (x, @@, @) instead of 3 tokens (x, @@@, y)
- Parser receives two separate tokens where one was expected

**Phase to address:**
Phase 1 (Tokenizer), with explicit tokenization unit tests for each operator.

---

### Pitfall 6: `MATCH` Token Type Not in FUNC_TOKENS

**What goes wrong:**
If the Parlante tokenizer maps the keyword `"MATCH"` to `TokenType.MATCH` (as SQLite does), then `MATCH(x)` will NOT parse as a function call. The `_parse_function_call` method checks `token_type not in self.FUNC_TOKENS` (line 6780 of `parser.py`) and returns `None`. `TokenType.MATCH` is NOT in `FUNC_TOKENS`. It is in `ID_VAR_TOKENS`, which means the identifier can be used in variable positions, but not as a function name.

**Why it happens:**
`FUNC_TOKENS` is a separate set from `ID_VAR_TOKENS`. A token being parseable as an identifier does not make it parseable as a function name. Only `TokenType.VAR`, type tokens, and a specific allow-list in `FUNC_TOKENS` (lines 807–857 of `parser.py`) can head a function call.

**How to avoid:**
Do NOT add `"MATCH": TokenType.MATCH` to the Parlante tokenizer KEYWORDS. Instead, leave `MATCH` to tokenize as `TokenType.VAR` (the default for unrecognized words). The function call path then works via the `FUNCTIONS` dict lookup.

If you need a custom token for `MATCH` as a statement keyword (e.g., in STATEMENT_PARSERS), add `TokenType.MATCH` to `FUNC_TOKENS` in the Parlante parser:

```python
FUNC_TOKENS = {*PostgresParser.FUNC_TOKENS, TokenType.MATCH}
```

**Warning signs:**
- `MATCH(x)` silently parses to `None` or falls through to a `exp.Command`
- No error is raised; the SQL just silently mis-parses

**Phase to address:**
Phase 1 (Tokenizer + Parser), when mapping function-name aliases.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `exp.Anonymous` for custom functions | Quick to implement | Breaks `find_all`, type-checking, and cross-dialect transpilation; violates CLAUDE.md rule 2 | Never — always check `expressions.py` first |
| Building SQL with f-strings in generator methods | Simple for one-liners | Breaks quoting, escaping, identifier normalization; violates CLAUDE.md rule 3 | Never |
| Putting new operator handling in TRANSFORMS as a lambda that uses f-string | Quick for simple ops | Fragile; use `self.binary(e, "###")` instead | Acceptable for truly trivial binary operators if `self.binary` is called internally |
| Skipping FUNCTIONS dict and using only FUNCTION_PARSERS | Handles complex parse-time logic | Makes the function invisible to `sqlglot.expressions.FUNCTION_BY_NAME` | Only for functions with truly complex argument parsing |
| Adding `"MATCH"` to FUNCTIONS without removing it from FUNCTION_PARSERS | Seems complete | Silently dead code; FUNCTION_PARSERS always wins | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Dialect registration | Forgetting to add `"Parlante"` to `DIALECTS` list in `sqlglot/dialects/__init__.py` | Add to `DIALECTS` list AND `MODULE_BY_DIALECT`; dialect is auto-registered by `_Dialect.__new__` but lazy-loading from `parse_one(dialect="parlante")` requires the `__init__.py` entry |
| Dialect registration | Forgetting to add `PARLANTE = "parlante"` to the `Dialects` enum in `dialect.py` | Without the enum entry, `Dialects.PARLANTE` is unavailable and string lookup falls back to `clsname.lower()` which works but is inconsistent |
| Generator inheritance | Calling `**PostgresGenerator.TRANSFORMS` without removing conflicting entries | Use a comprehension to exclude entries you want to override with `_sql` methods (see Pitfall 2) |
| Parser inheritance | Defining `FUNCTIONS = {**PostgresParser.FUNCTIONS, "MATCH": my_builder}` | Works; FUNCTIONS dict lookup fires after FUNCTION_PARSERS; must also remove `"MATCH"` from FUNCTION_PARSERS |
| Operator semantics | Using `self.binary(e, "@@@")` in the generator | Correct approach; do NOT build the string with f-strings |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `_DISPATCH_CACHE` populated before all dialects loaded | Generator method overrides don't fire in tests if the cache was populated by an earlier test that instantiated the same generator class | This is not a runtime problem; the cache is per-class and correct once the class is defined. No action needed. | Not applicable |
| Calling `annotate_types()` inside a generator method unconditionally | Significant slowdown on complex queries | Only call `annotate_types()` when type information is actually needed (pattern from `_round_sql` in `generators/postgres.py`) | Every query using the affected expression |

---

## "Looks Done But Isn't" Checklist

- [ ] **Dialect registration:** `"Parlante"` added to `DIALECTS` list in `sqlglot/dialects/__init__.py` — verify with `from sqlglot.dialects import Parlante`
- [ ] **FUNCTION_PARSERS override for MATCH:** verify `parse_one("MATCH(x)", dialect="parlante")` does not return `exp.MatchAgainst`
- [ ] **Operator trie entries:** tokenize each of `@@@`, `|||`, `###`, `===`, `<=>` in isolation and assert single token with correct text
- [ ] **TRANSFORMS inheritance audit:** for each new `_sql` method, verify the corresponding expression class is NOT in the inherited TRANSFORMS dict
- [ ] **Generator method naming:** verify each method name is exactly `<classname.lower()>_sql` — e.g., `exp.TripleAt` → `tripleat_sql`; check against `exp.EXPR_CLASSES` dict
- [ ] **FUNCTIONS dict keys uppercase:** all function alias keys must be uppercase strings (e.g., `"MATCH"` not `"match"`)
- [ ] **New TokenType values appended last:** never insert in middle of `tokenizer_core.py` enum
- [ ] **`make test` passes:** run with `.so` files hidden to ensure pure-Python path works

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| MATCH parsed as MatchAgainst | LOW | Add `{k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"}` to parser |
| TRANSFORMS blocking _sql method | LOW | Add expression class to the exclusion filter in TRANSFORMS dict comprehension |
| `<=>` semantic collision | MEDIUM | Decide on Option A vs B (see Pitfall 3); if Option A, audit all cross-dialect tests |
| TokenType enum order corrupted | HIGH | Remove the misplaced value, append at end, rebuild C extension with `make install-devc` |
| Operator tokenizing incorrectly | LOW | Add the 3-char string to KEYWORDS, verify with tokenization test |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| MATCH keyword in FUNCTION_PARSERS | Phase 1: Parser | `parse_one("MATCH(x)", dialect="parlante")` is not `MatchAgainst` |
| TRANSFORMS blocking _sql methods | Phase 2: Generator | Add `print` to each new `_sql` method in tests; confirm it fires |
| `<=>` semantic conflict | Phase 1: Tokenizer | `validate_all` round-trip from MySQL `<=>` through Parlante |
| TokenType enum ordering | Phase 1: Tokenizer | `make testc` passes after `make install-devc` |
| Operator trie prefix conflicts | Phase 1: Tokenizer | Explicit tokenization assertions for each operator |
| MATCH not in FUNC_TOKENS | Phase 1: Parser | `parse_one("MATCH(x)", dialect="parlante")` produces expected function node |
| Dialect not in `__init__.py` DIALECTS | Phase 1: Dialect scaffold | `python -c "from sqlglot.dialects import Parlante"` succeeds |

---

## Sources

- `sqlglot/generator.py` lines 74–92: `_build_dispatch` — TRANSFORMS vs auto-discovery precedence (HIGH confidence, direct source inspection)
- `sqlglot/parser.py` lines 807–857: `FUNC_TOKENS` — which token types can head a function call (HIGH confidence)
- `sqlglot/parser.py` lines 1480–1500: `FUNCTION_PARSERS` — `"MATCH"` entry priority over `FUNCTIONS` (HIGH confidence)
- `sqlglot/tokens.py` lines 106–117: trie construction — the `any(single in key ...)` filter that determines what enters the trie (HIGH confidence)
- `sqlglot/tokenizer_core.py` lines 798–856: `_scan_keywords` — greedy longest-match trie logic (HIGH confidence)
- `sqlglot/tokenizer_core.py` lines 217 (base KEYWORDS `<=>` entry) and `tokenizer_core.py` TokenType enum (HIGH confidence)
- `sqlglot/dialects/__init__.py` lines 67–126: `DIALECTS` list and lazy-loading mechanism (HIGH confidence)
- `sqlglot/dialects/dialect.py` lines 229–232: `_Dialect.__new__` — auto-registration by lowercase class name (HIGH confidence)
- `sqlglotc/setup.py` lines 44–74: mypyc compilation scope — which files are compiled (HIGH confidence)
- CLAUDE.md coding rules 1–6: PR-rejection patterns for generators (HIGH confidence)

---
*Pitfalls research for: adding Parlante dialect to sqlglot (Postgres extension with custom operators and function aliases)*
*Researched: 2026-04-07*
