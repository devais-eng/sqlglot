from __future__ import annotations

from sqlglot.dialects.postgres import Postgres
from sqlglot.generators.parlante import ParlanteGenerator
from sqlglot.parsers.parlante import ParlanteParse, ParlanteMatch, ParlantePhraseMatch
from sqlglot.tokens import TokenType

__all__ = ["Parlante", "ParlanteMatch", "ParlantePhraseMatch"]


class Parlante(Postgres):
    class Tokenizer(Postgres.Tokenizer):
        KEYWORDS = {
            **Postgres.Tokenizer.KEYWORDS,
            "@@@": TokenType.OPERATOR,
            "|||": TokenType.OPERATOR,
            "###": TokenType.OPERATOR,
            "===": TokenType.OPERATOR,
            "<=>": TokenType.OPERATOR,  # override base NULLSAFE_EQ
        }

    Parser = ParlanteParse
    Generator = ParlanteGenerator
