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
    # PARAMETER (@) must be in TABLE_POSTFIX_TOKENS so the fast-path in _parse_table does not
    # consume "@branch" as a table alias before _parse_version gets a chance to handle it.
    TABLE_POSTFIX_TOKENS = PostgresParser.TABLE_POSTFIX_TOKENS | frozenset(
        [TokenType.PARAMETER]
    )

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
