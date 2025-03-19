# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

import io

from oberon0_compiler.scanner import Scanner
from oberon0_compiler.token import Token


def test_assignment():
    src = "VAR i := 0;"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.VAR
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    scanner.get_next_symbol()
    assert scanner.sym == Token.BECOMES
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    scanner.get_next_symbol()
    assert scanner.sym == Token.SEMICOLON


def test_compare_leq():
    src = "i <= 0"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    assert scanner.sym == Token.LEQ
    assert scanner.value == "<="
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == 0


def test_compare_less():
    src = "i < 0"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    assert scanner.sym == Token.LSS
    assert scanner.value == "<"
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == 0
