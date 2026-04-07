from __future__ import annotations

from sqlglot.dialects.postgres import Postgres
from sqlglot.tokens import TokenType


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
