from __future__ import annotations

from sqlglot import exp
from sqlglot.parsers.postgres import PostgresParser
from sqlglot.tokens import TokenType


class ParlanteParse(PostgresParser):
    FUNCTION_PARSERS = {k: v for k, v in PostgresParser.FUNCTION_PARSERS.items() if k != "MATCH"}

    FUNCTIONS = {
        **PostgresParser.FUNCTIONS,
        "MATCH": lambda args: exp.Anonymous(this="PARLANTE_MATCH", expressions=args),
        "PHRASE_MATCH": lambda args: exp.Anonymous(this="PARLANTE_PHRASE_MATCH", expressions=args),
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
