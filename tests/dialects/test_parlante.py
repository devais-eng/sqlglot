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

