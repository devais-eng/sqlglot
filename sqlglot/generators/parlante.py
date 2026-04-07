from __future__ import annotations

from sqlglot import exp
from sqlglot.generators.postgres import PostgresGenerator


class ParlanteGenerator(PostgresGenerator):
    TRANSFORMS = {
        **PostgresGenerator.TRANSFORMS,
        exp.Operator: lambda self, e: f"{self.sql(e, 'this')} {e.args['operator']} {self.sql(e, 'expression')}",
    }

    def anonymous_sql(self, expression: exp.Anonymous) -> str:
        if expression.name == "PARLANTE_MATCH":
            return self.func("MATCH", *expression.expressions, normalize=False)
        if expression.name == "PARLANTE_PHRASE_MATCH":
            return self.func("PHRASE_MATCH", *expression.expressions, normalize=False)
        return super().anonymous_sql(expression)
