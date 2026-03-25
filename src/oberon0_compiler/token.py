# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-0 tokens
"""

from enum import Enum


class Token(str, Enum):
    NULL = "null"
    TIMES = "*"
    DIV = "DIV"
    MOD = "MOD"
    AND = "&"
    PLUS = "+"
    MINUS = "-"
    OR = "OR"
    EQL = "="
    NEQ = "#"
    LSS = "<"
    LEQ = "<="
    GTR = ">"
    GEQ = ">="
    PERIOD = "."
    NOT = "~"
    LPAREN = "("
    IDENT = "identifier"
    NUMBER = "number"
    IF = "IF"
    WHILE = "WHILE"
    REPEAT = "REPEAT"
    COMMA = ","
    COLON = ":"
    BECOMES = ":="
    RPAREN = ")"
    THEN = "THEN"
    OF = "OF"
    DO = "DO"
    SEMICOLON = ";"
    END = "END"
    ELSE = "ELSE"
    ELSIF = "ELSIF"
    UNTIL = "UNTIL"
    CONST = "CONST"
    VAR = "VAR"
    PROCEDURE = "PROCEDURE"
    BEGIN = "BEGIN"
    MODULE = "MODULE"
    EOF = "eof"
    OTHER = "unknown"

    def __str__(self) -> str:
        return self.value
