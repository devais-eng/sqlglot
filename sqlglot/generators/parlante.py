from __future__ import annotations

from sqlglot import exp
from sqlglot.generators.postgres import PostgresGenerator
from sqlglot.parsers.parlante import ParlanteMatch, ParlantePhraseMatch


class ParlanteGenerator(PostgresGenerator):
    TRANSFORMS = {
        **PostgresGenerator.TRANSFORMS,
        exp.Operator: lambda self, e: f"{self.sql(e, 'this')} {e.args['operator']} {self.sql(e, 'expression')}",
        ParlanteMatch: lambda self, e: self.func("MATCH", e.this, *e.expressions, normalize=False),
        ParlantePhraseMatch: lambda self, e: self.func("PHRASE_MATCH", e.this, *e.expressions, normalize=False),
    }
