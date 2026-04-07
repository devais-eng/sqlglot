from __future__ import annotations

from sqlglot import exp
from sqlglot.parsers.postgres import PostgresParser
from sqlglot.tokens import TokenType


class ParlanteMatch(exp.Expression, exp.Func):
    arg_types = {"this": True, "expressions": False}
    is_var_len_args = True
    _sql_names = ["MATCH"]


class ParlantePhraseMatch(exp.Expression, exp.Func):
    arg_types = {"this": True, "expressions": False}
    is_var_len_args = True
    _sql_names = ["PHRASE_MATCH"]


class ParlanteParse(PostgresParser):
    FUNCTION_PARSERS = {k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"}

    FUNCTIONS = {
        **PostgresParser.FUNCTIONS,
        "MATCH": ParlanteMatch.from_arg_list,
        "PHRASE_MATCH": ParlantePhraseMatch.from_arg_list,
    }

    RANGE_PARSERS = {
        **PostgresParser.RANGE_PARSERS,
        TokenType.OPERATOR: lambda self, this: self.expression(
            exp.Operator(
                this=this,
                operator=self._prev.text,
                expression=self._parse_bitwise(),
            )
        ),
    }
