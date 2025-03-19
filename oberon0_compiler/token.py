# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 tokens
"""

from enum import Enum

_tokens = [
    ("NULL", "null"),
    ("TIMES", "*"),
    ("DIV", "DIV"),
    ("MOD", "MOD"),
    ("AND", "&"),
    ("PLUS", "+"),
    ("MINUS", "-"),
    ("OR", "OR"),
    ("EQL", "="),
    ("NEQ", "#"),
    ("LSS", "<"),
    ("LEQ", "<="),
    ("GTR", ">"),
    ("GEQ", ">="),
    ("PERIOD", "."),
    ("NOT", "~"),
    ("LPAREN", "("),
    ("LBRACK", "["),
    ("IDENT", "identifier"),
    ("NUMBER", "number"),
    ("IF", "IF"),
    ("WHILE", "WHILE"),
    ("REPEAT", "REPEAT"),
    ("COMMA", ","),
    ("COLON", ":"),
    ("BECOMES", ":="),
    ("RPAREN", ")"),
    ("RBRACK", "]"),
    ("THEN", "THEN"),
    ("OF", "OF"),
    ("DO", "DO"),
    ("SEMICOLON", ";"),
    ("END", "END"),
    ("ELSE", "ELSE"),
    ("ELSIF", "ELSIF"),
    ("UNTIL", "UNTIL"),
    ("ARRAY", "ARRAY"),
    ("RECORD", "RECORD"),
    ("CONST", "CONST"),
    ("TYPE", "TYPE"),
    ("VAR", "VAR"),
    ("PROCEDURE", "PROCEDURE"),
    ("BEGIN", "BEGIN"),
    ("MODULE", "MODULE"),
    ("EOF", "eof"),
    ("OTHER", "unknown"),
]

token_str = dict(_tokens)

Token = Enum("Token", [(i[1][0], i[0]) for i in enumerate(_tokens)])
Token.__str__ = lambda self: token_str[self.name]
