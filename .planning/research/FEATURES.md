# Feature Landscape

**Domain:** SQLGlot dialect implementation — Parlante (Postgres superset for ParadeDB FTS + pgvector)
**Researched:** 2026-04-07

---

## Table Stakes

Features users expect. Missing = dialect produces wrong SQL or fails to parse.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Tokenize `@@@` as a single OPERATOR token | `@@@` is the primary ParadeDB FTS operator; without it, tokenizer splits it into `@@` (DAT) + `@` (PARAMETER), breaking all FTS queries | Low | Trie longest-match handles this once `"@@@": TokenType.OPERATOR` is in KEYWORDS |
| Tokenize `\|\|\|` as a single OPERATOR token | ParadeDB OR operator; currently splits into `\|\|` (DPIPE) + `\|` (PIPE) | Low | Same trie mechanism |
| Tokenize `###` as a single OPERATOR token | ParadeDB phrase operator; currently three separate `#` (HASH) tokens | Low | Same trie mechanism |
| Tokenize `===` as a single OPERATOR token | ParadeDB exact-match operator; currently `==` (EQ) + `=` (EQ) | Low | `=` is in SINGLE_TOKENS so `===` enters the trie via KEYWORDS |
| Tokenize `<=>` as OPERATOR (not NULLSAFE_EQ) | pgvector cosine distance; base tokenizer maps `<=>` to `TokenType.NULLSAFE_EQ` producing `IS NOT DISTINCT FROM` | Low | Override the base KEYWORDS entry; `<=>` already in trie, just remap the token type |
| Parse `MATCH(col, 'query')` as `exp.Anonymous("PARLANTE_MATCH")` | Base parser's FUNCTION_PARSERS intercepts `MATCH` and calls `_parse_match_against()`, producing a broken `MatchAgainst` node expecting `AGAINST(...)` | Medium | Requires removing MATCH from FUNCTION_PARSERS and adding it to FUNCTIONS |
| Parse `PHRASE_MATCH(col, 'query')` as `exp.Anonymous("PARLANTE_PHRASE_MATCH")` | Without this, `PHRASE_MATCH` is treated as an unknown function and may parse incorrectly or produce `exp.Anonymous("PHRASE_MATCH")` — acceptable but inconsistent naming | Low | Base FUNCTIONS lookup handles unknown functions as `exp.Anonymous` with the literal name; still need explicit entry to ensure correct naming |
| Generate `@@@`, `\|\|\|`, `###`, `===`, `<=>` as native symbols | The base generator's `binary()` method wraps `exp.Operator.operator` in `OPERATOR(...)` (e.g., `OPERATOR(paradedb.@@@)`); ParadeDB extensions require the bare symbol | Low | Requires TRANSFORMS override for `exp.Operator` since the entry already exists in the base TRANSFORMS dict — auto-discovery is bypassed |
| Generate `MATCH(col, 'query')` (not `PARLANTE_MATCH(...)`) | The internal `PARLANTE_MATCH` name must be unwrapped to `MATCH` on output; `normalize=False` preserves exact casing | Low | Override `anonymous_sql`; use `self.func(..., normalize=False)` |
| Generate `PHRASE_MATCH(col, 'query')` (not `PARLANTE_PHRASE_MATCH(...)`) | Same as MATCH | Low | Same override |
| Dialect registration via `dialect="parlante"` string | Consumers call `sqlglot.parse_one(sql, dialect="parlante")`; the lazy-loader requires `"Parlante"` in `DIALECTS` list in `sqlglot/dialects/__init__.py` | Low | Add `"Parlante"` to DIALECTS list; `MODULE_BY_DIALECT` auto-maps it to module `"parlante"` |

---

## Differentiators

Features that set the dialect apart from the regex-rewrite hack.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| No regex pre-scan on every query | Current `rewrite_parlante_syntax()` splits every SQL string on string-literal boundaries even for plain Postgres queries; native tokenizer only fires on actual `@@@`/`|||`/etc. characters | Already achieved by correct tokenizer implementation | Performance win is the primary motivation for this entire milestone |
| `MATCH`/`PHRASE_MATCH` safe inside identifiers | Regex `\bMATCH\s*\(` can fire inside quoted identifiers or schema-prefixed names; tokenizer-level parsing is immune | Already achieved by parser-level dispatch | No extra work needed |
| Round-trip fidelity via `validate_identity` | `parse_one(sql, dialect="parlante").sql(dialect="parlante")` must produce the original SQL unchanged for all Parlante syntax | Medium | The PARLANTE_MATCH internal name + anonymous_sql override gives this; operator round-trip requires generator + tokenizer cooperate |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Dedicated `exp.ParadeDBMatch` expression class | No upstream expression class exists; adding one requires changes to `expressions/` which increases rebase surface area and is overkill for a function with no semantic analysis needs | Use `exp.Anonymous(this="PARLANTE_MATCH", ...)` as the handoff doc specifies |
| Dedicated `exp.PgvectorCosine` expression class | Same reasoning; `exp.Operator` with `pgvector.<=>` as the operator field already represents it correctly | Keep using `exp.Operator` |
| Touching `<->` (L2 distance) | Already handled by base Postgres dialect as `exp.Distance` via `TokenType.LR_ARROW`; confirmed working | Leave it; do not add `"<->": TokenType.OPERATOR` to Parlante's KEYWORDS |
| Parser subclass in a separate file | The handoff spec intentionally keeps everything in `dialects/parlante.py`; splitting into `parsers/parlante.py` + `generators/parlante.py` adds indirection with no benefit for a three-method dialect | Inline Parser/Generator in the dialect file |
| Regex workaround for any operator | The entire point of this milestone is to eliminate the regex hack | All operators must be handled at the tokenizer level |

---

## Feature Dependencies

```
Tokenizer (KEYWORDS overrides)
    → must emit TokenType.OPERATOR for @@@, |||, ###, ===, <=>
    → only then does the base Parser._parse_operator() build exp.Operator nodes
    → which the Generator then needs to unwrap

Parser (FUNCTIONS override for MATCH/PHRASE_MATCH)
    → must run AFTER tokenizer produces correct tokens
    → requires removing MATCH from FUNCTION_PARSERS
      (FUNCTION_PARSERS has priority over FUNCTIONS; if MATCH remains in
       FUNCTION_PARSERS it calls _parse_match_against() regardless of FUNCTIONS)
    → PHRASE_MATCH has no FUNCTION_PARSERS entry so only FUNCTIONS is needed

Generator (TRANSFORMS for exp.Operator, anonymous_sql override)
    → independent of tokenizer/parser at generation time
    → exp.Operator TRANSFORMS entry CANNOT use auto-discovery because
      exp.Operator already exists in the parent TRANSFORMS dict
      (_build_dispatch skips auto-discovered methods for already-dispatched types)
    → anonymous_sql override is standard method override, no special constraint
```

---

## Edge Cases

### 1. `<=>` conflicts with base KEYWORDS NULLSAFE_EQ

**Situation:** `tokens.Tokenizer.KEYWORDS` maps `"<=>"` to `TokenType.NULLSAFE_EQ`. Postgres dialect inherits this. If Parlante adds `"<=>": TokenType.OPERATOR` to its KEYWORDS (using `**Postgres.Tokenizer.KEYWORDS, "<=>": TokenType.OPERATOR`), the dict literal `{**base, "<=>": new}` overwrites the base entry. Confirmed correct behavior.

**Edge case within edge case:** The base `KEYWORDS` has `"<="` (LTE) and `"<"` (LT) in SINGLE_TOKENS. The trie scans longest-match, so `<=>` (3 chars) beats `<=` (2 chars). No ambiguity.

### 2. `@@@` vs `@@` both in the trie

**Situation:** Postgres KEYWORDS has `"@@": TokenType.DAT`. Parlante adds `"@@@": TokenType.OPERATOR`. Both enter the trie. Trie scan: at position of `@@@`, the trie traverses `@`→`@`→`@` finding the `@@@` entry, which is longer than `@@`. Longest match wins. Verified by tokenizer_core.py scan logic: `word = chars` is updated each time `0 in trie`, so the last valid node (longest match) is used.

**Residual risk:** A query with `@@` followed immediately by `@` (no space), such as `a@@@b` where the intent is `a @@ @b` (Postgres FTS followed by parameter reference), would be misread. This is acceptable: the Parlante dialect intentionally claims `@@@` as a single operator.

### 3. `MATCH` in `FUNCTION_PARSERS` vs `FUNCTIONS`

**Situation:** `parser.Parser.FUNCTION_PARSERS["MATCH"]` → `_parse_match_against()`. This takes priority over `FUNCTIONS["MATCH"]`. The Parlante Parser must override `FUNCTION_PARSERS` to remove `MATCH`.

**Correct pattern** (mirrors ClickHouse's approach in `parsers/clickhouse.py:362`):
```python
FUNCTION_PARSERS = {
    **{k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"},
}
```
Then add `MATCH` to `FUNCTIONS`:
```python
FUNCTIONS = {
    **PostgresParser.FUNCTIONS,
    "MATCH": lambda args: exp.Anonymous(this="PARLANTE_MATCH", expressions=args),
    "PHRASE_MATCH": lambda args: exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=args),
}
```

**Note:** `PHRASE_MATCH` has no `FUNCTION_PARSERS` entry in any base class, so it only needs the `FUNCTIONS` entry.

### 4. `===` ambiguity with `==` (EQ)

**Situation:** `==` is in base KEYWORDS as `TokenType.EQ`. Adding `===` creates a trie entry that is longer. The scan will match `===` as one token. However: `=` is also a SINGLE_TOKEN. The trie scan starts when the current char is in SINGLE_TOKENS (which `=` is) — this is fine because `_scan_keywords` runs first and the trie traversal captures multi-char sequences starting from single-token chars.

**Residual risk:** `====` would match `===` + `=`. This is not a valid SQL sequence so no real risk.

### 5. `exp.Operator` TRANSFORMS override cannot use auto-discovery

**Situation:** `_build_dispatch` in `generator.py:89` only adds auto-discovered `*_sql` methods if `expr_cls not in dispatch`. Since `exp.Operator` is in the base `Generator.TRANSFORMS`, it is in the dispatch dict before auto-discovery runs. Defining `operator_sql` on the Parlante Generator would have no effect unless `exp.Operator` is also removed from TRANSFORMS.

**Correct approach:** Use TRANSFORMS explicitly for `exp.Operator` in the Parlante Generator. This is the one case where CLAUDE.md rule 1's TRANSFORMS exception applies — the base already uses TRANSFORMS for this type, and a method override would be silently ignored.

### 6. `normalize=False` in `anonymous_sql` override

**Situation:** `self.func("MATCH", ..., normalize=False)` preserves exact casing. Without it, `normalize_functions="upper"` (the Postgres default) would output `MATCH` correctly but `normalize_functions="lower"` would output `match`. ParadeDB's `pg_search` extension is case-sensitive in function names: `MATCH` is the correct form. `normalize=False` is load-bearing.

### 7. Non-paradedb/pgvector OPERATOR() forms in the generator

**Situation:** The existing `_native_operator_sql` logic falls through to `gen.binary(expression, "")` for operators not in paradedb/pgvector namespace. `gen.binary` with an empty string `op` argument picks up the `operator` field from `node.args.get("operator")` and wraps it in `OPERATOR(...)`. This correctly preserves e.g. `OPERATOR(pg_catalog.~)` (seen in Postgres test at line 167).

**No change needed here** — the fallback behavior is correct.

### 8. `SINGLESTORE` dialect also has a MATCH override

Not relevant to Parlante directly, but confirms the pattern: ClickHouse removes MATCH from FUNCTION_PARSERS (confirmed in `parsers/clickhouse.py`). Parlante should follow the same approach rather than trying to use the FUNCTIONS dict alone.

---

## MVP Recommendation

Implement in this order (each step depends on the previous):

1. **Tokenizer KEYWORDS** — `@@@`, `|||`, `###`, `===`, `<=>` → `TokenType.OPERATOR`. This is the foundation; all binary operator parsing depends on tokens.
2. **Parser FUNCTION_PARSERS + FUNCTIONS** — Remove MATCH from FUNCTION_PARSERS, add MATCH + PHRASE_MATCH to FUNCTIONS. Independent of step 1.
3. **Generator TRANSFORMS** — Override `exp.Operator` with `_native_operator_sql` logic. Requires step 1 to produce testable inputs.
4. **Generator anonymous_sql** — Map PARLANTE_MATCH/PARLANTE_PHRASE_MATCH back to output names. Requires step 2.
5. **Dialect registration** — Add `"Parlante"` to `DIALECTS` in `__init__.py` and `PARLANTE = "parlante"` to the `Dialects` enum. No dependencies, can be done anytime.

Defer: Nothing. All five steps are needed for a working dialect — none are optional.

---

## Test Matrix

| Test case | Input (parlante) | Expected output (parlante) | What it validates |
|-----------|-----------------|---------------------------|-------------------|
| Basic FTS | `SELECT id FROM t WHERE body @@@ 'login'` | round-trip identical | `@@@` tokenizer + generator |
| ParadeDB OR | `SELECT id FROM t WHERE body \|\|\| 'foo'` | round-trip identical | `\|\|\|` tokenizer + generator |
| ParadeDB phrase | `SELECT id FROM t WHERE body ### 'foo bar'` | round-trip identical | `###` tokenizer + generator |
| ParadeDB exact | `SELECT id FROM t WHERE body === 'foo'` | round-trip identical | `===` tokenizer + generator |
| pgvector cosine | `SELECT id FROM t ORDER BY embedding <=> '[0.1,0.2]'` | round-trip identical | `<=>` tokenizer + generator |
| MATCH function | `SELECT MATCH(body, 'login')` | `SELECT MATCH(body, 'login')` | MATCH function parser + generator |
| PHRASE_MATCH function | `SELECT PHRASE_MATCH(body, 'foo bar')` | `SELECT PHRASE_MATCH(body, 'foo bar')` | PHRASE_MATCH parser + generator |
| Non-Parlante OPERATOR preserved | `SELECT c FROM t WHERE c OPERATOR(pg_catalog.~) '^foo$'` | round-trip identical | Non-paradedb operator fallback in generator |
| Postgres `@@` (DAT) not broken | `SELECT a @@ b` (Postgres FTS) | `SELECT MATCH(b) AGAINST(a)` or identical | `@@` still tokenized as DAT, not consumed by `@@@` |
| L2 distance unchanged | `SELECT embedding <-> '[0.1]'` | round-trip identical | `<->` still LR_ARROW → exp.Distance, NOT touched |
| MATCH case sensitivity | `SELECT match(col, 'q')` | `SELECT MATCH(col, 'q')` | normalize=False preserves MATCH name |
| NULL-safe EQ not broken (MySQL context) | Not applicable — `<=>` redefined for this dialect intentionally | N/A | Acceptance: Parlante is not MySQL-compatible |

---

## Sources

- `/home/filippo/GithubProjects/sqlglot/PARLANTE_DIALECT.md` — authoritative handoff spec (HIGH confidence)
- `/home/filippo/GithubProjects/parlante/src/parlante/dialect.py` — existing implementation to migrate from (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/tokenizer_core.py` — trie scan logic, line 798–856 (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/tokens.py` — SINGLE_TOKENS, KEYWORDS baseline, trie construction condition (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/dialects/postgres.py` — `@@` → DAT, Postgres tokenizer KEYWORDS (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/parsers/postgres.py` — FUNCTION_PARSERS, RANGE_PARSERS (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/parsers/clickhouse.py:362` — precedent for removing MATCH from FUNCTION_PARSERS (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/generator.py:77–92` — `_build_dispatch` auto-discovery logic, `exp.Operator not in dispatch` constraint (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/generator.py:4248` — `binary()` method, `OPERATOR(...)` wrapping behavior (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/dialects/dialect.py:229–232` — metaclass auto-registration of dialect classes (HIGH confidence)
- `/home/filippo/GithubProjects/sqlglot/sqlglot/dialects/__init__.py` — DIALECTS list, lazy loader (HIGH confidence)
- Live tokenization tests confirming current broken behavior for `@@@`, `|||`, `###`, `===`, and `<=>` in Postgres dialect (HIGH confidence — runtime verified)
