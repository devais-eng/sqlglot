import unittest

import sqlglot
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
