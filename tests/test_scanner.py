# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

import io
import typing

from oberon0_compiler.scanner import Scanner
from oberon0_compiler.token import Token


def test_assignment() -> None:
    src = "VAR i := 12;"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.VAR
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.BECOMES
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.NUMBER
    assert scanner.value == "12"
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.SEMICOLON


def test_compare_leq() -> None:
    src = "i <= -5"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.LEQ
    assert scanner.value == "<="
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.MINUS
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.NUMBER
    assert scanner.value == "5"


def test_compare_less() -> None:
    src = "i < 0"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.LSS
    assert scanner.value == "<"
    scanner.get_next_symbol()
    next_sym = typing.cast(Token, scanner.sym)
    assert next_sym == Token.NUMBER
    assert scanner.value == "0"
