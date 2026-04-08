import unittest

import sqlglot
from sqlglot import exp
from sqlglot.dialects.parlante import ParlanteMatch, ParlantePhraseMatch
from sqlglot.tokens import TokenType
from tests.dialects.test_dialect import Validator


class TestParlante(Validator):
    dialect = "parlante"

    def test_dialect_registered(self):
        self.assertIsNotNone(sqlglot.parse_one("SELECT 1", dialect="parlante"))

    def test_operator_tokens(self):
        d = sqlglot.Dialect.get_or_raise("parlante")
        for op in ("@@@", "|||", "###", "===", "<=>"):
            with self.subTest(op=op):
                tokens = d.tokenize(f"a {op} b")
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

    def test_operator_roundtrip(self):
        self.validate_identity("col @@@ 'query'")
        self.validate_identity("col ||| 'query'")
        self.validate_identity("col ### 'query'")
        self.validate_identity("col === 'query'")
        self.validate_identity("col <=> '[0.1,0.2]'")

    def test_match_roundtrip(self):
        self.validate_identity("MATCH(col, 'query')")
        self.validate_identity("PHRASE_MATCH(col, 'query')")

    def test_no_regression_tsvector(self):
        self.validate_identity("x @@ y")

    def test_no_regression_l2_distance(self):
        self.validate_identity("embedding <-> '[0.1,0.2]'")

    def test_operator_ast_type(self):
        result = self.parse_one("col @@@ 'query'")
        self.assertIsInstance(result, exp.Operator)
        self.assertEqual(result.args["operator"], "@@@")

    def test_match_ast_type(self):
        result = self.parse_one("MATCH(col, 'query')")
        self.assertIsInstance(result, ParlanteMatch)
        phrase = self.parse_one("PHRASE_MATCH(col, 'query')")
        self.assertIsInstance(phrase, ParlantePhraseMatch)

    def test_operator_in_string_literal(self):
        # '@@@' is a string value, not an infix operator
        result = self.parse_one("SELECT '@@@'")
        lit = result.expressions[0]
        self.assertIsInstance(lit, exp.Literal)
        self.assertEqual(lit.this, "@@@")
        self.assertIsNone(result.find(exp.Operator))

    def test_operator_as_quoted_identifier(self):
        # "@@@" is a quoted column name, not an operator
        result = self.parse_one('SELECT "@@@" FROM t')
        self.assertIsNone(result.find(exp.Operator))
        col = result.find(exp.Column)
        self.assertIsNotNone(col)
        self.assertEqual(col.name, "@@@")

    def test_triple_equals_not_eq(self):
        # === is a Parlante operator, not SQL equality
        result = self.parse_one("col === 1")
        self.assertIsInstance(result, exp.Operator)
        self.assertNotIsInstance(result, exp.EQ)
        self.assertEqual(result.args["operator"], "===")

    def test_operators_in_select_context(self):
        self.validate_identity("SELECT col @@@ 'query' FROM t")
        self.validate_identity("SELECT * FROM t WHERE col <=> '[1,2,3]'")

    def test_match_in_where_clause(self):
        self.validate_identity("SELECT * FROM t WHERE MATCH(col, 'query')")
        self.validate_identity("SELECT * FROM t WHERE PHRASE_MATCH(col, 'query')")

    def test_spaceship_not_nullsafe_eq(self):
        result = self.parse_one("col <=> '[0.1,0.2]'")
        self.assertIsInstance(result, exp.Operator)
        self.assertNotIsInstance(result, exp.NullSafeEQ)
        self.assertEqual(result.args["operator"], "<=>")

    def test_at_branch_roundtrip(self):
        # BRN-01: verbose AT BRANCH form round-trips unchanged
        self.validate_identity("SELECT * FROM t AT BRANCH main")
        # BRN-04: version clause appears before alias
        self.validate_identity("SELECT * FROM t AT BRANCH main AS tbl")
        # Schema-qualified table with branch
        self.validate_identity("SELECT * FROM schema1.t AT BRANCH main")

    def test_at_branch_shorthand(self):
        # BRN-02, BRN-03: @shorthand is normalized to verbose AT BRANCH form
        self.validate_identity("SELECT * FROM t@main", "SELECT * FROM t AT BRANCH main")
        self.validate_identity("SELECT * FROM t@main AS tbl", "SELECT * FROM t AT BRANCH main AS tbl")

    def test_at_branch_ast_type(self):
        # Verbose form: table node carries a Version arg
        tree = sqlglot.parse_one("SELECT * FROM t AT BRANCH main", dialect="parlante")
        table = tree.find(exp.Table)
        self.assertIsNotNone(table)
        version = table.args.get("version")
        self.assertIsInstance(version, exp.Version)
        self.assertEqual(version.name, "BRANCH")
        self.assertEqual(version.text("kind"), "AT")
        self.assertEqual(version.expression.name, "main")

        # @shorthand produces identical AST
        tree2 = sqlglot.parse_one("SELECT * FROM t@main", dialect="parlante")
        table2 = tree2.find(exp.Table)
        version2 = table2.args.get("version")
        self.assertIsInstance(version2, exp.Version)
        self.assertEqual(version2.name, "BRANCH")
        self.assertEqual(version2.text("kind"), "AT")
        self.assertEqual(version2.expression.name, "main")

    def test_at_branch_unsupported_version(self):
        # BRN-05: non-branch Version nodes emit unsupported warning
        from sqlglot.generators.parlante import ParlanteGenerator

        gen = ParlanteGenerator()
        version = exp.Version(
            this="TIMESTAMP", kind="AS OF", expression=exp.Literal.string("2024-01-01")
        )
        gen.version_sql(version)
        self.assertTrue(len(gen.unsupported_messages) > 0)

    def test_at_branch_no_regression(self):
        # BRN-06: tsvector @@ operator is unaffected by branch parsing
        self.validate_identity("SELECT a @@ b FROM t")
        # BRN-07: Parlante operator and branch reference work together in the same query
        self.validate_identity("SELECT col @@@ 'q' FROM t AT BRANCH main")

    def test_at_branch_false_positives(self):
        # @var in a SELECT expression must NOT parse as a branch reference — the table
        # should carry no version arg and the Parameter node should appear in the select list.
        tree = sqlglot.parse_one("SELECT @var FROM t", dialect="parlante")
        table = tree.find(exp.Table)
        self.assertIsNone(table.args.get("version"))
        self.assertIsNotNone(tree.find(exp.Parameter))

        # AT without BRANCH is a parse error (not silently treated as a branch reference)
        with self.assertRaises(Exception):
            sqlglot.parse_one("SELECT * FROM t AT something", dialect="parlante")

        # tsvector @@ (DAT) in a select expression is unaffected by branch shorthand @
        # (tsvector case: no table version, @@ parsed as MatchAgainst — not a branch)
        tree_tv = sqlglot.parse_one("SELECT a @@ b FROM t", dialect="parlante")
        table_tv = tree_tv.find(exp.Table)
        self.assertIsNone(table_tv.args.get("version"))
        self.assertIsNotNone(tree_tv.find(exp.MatchAgainst))

        # @@ tsvector in a WHERE clause is unaffected when a branch is present on the table.
        # In Postgres/Parlante, @@ in WHERE context parses as MatchAgainst (not exp.Operator).
        tree3 = sqlglot.parse_one(
            "SELECT * FROM t@main WHERE x @@ y", dialect="parlante"
        )
        table3 = tree3.find(exp.Table)
        version3 = table3.args.get("version")
        self.assertIsInstance(version3, exp.Version)
        self.assertEqual(version3.name, "BRANCH")
        # @@ in WHERE parsed as MatchAgainst — not consumed as a branch
        self.assertIsNotNone(tree3.find(exp.MatchAgainst))
        # Round-trip confirms both branch and tsvector are preserved
        self.assertEqual(tree3.sql(dialect="parlante"), "SELECT * FROM t AT BRANCH main WHERE x @@ y")

