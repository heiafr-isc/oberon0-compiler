# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-0 scanner
"""

import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from loguru import logger

from .token import Token


@dataclass
class Position:
    file_name: str
    line_no: int
    col_no: int


class ScannerError(Exception):
    def __init__(self, message: str, position: Position) -> None:
        super().__init__(message)
        self.position = position

    def __str__(self) -> str:
        p = self.position
        return (
            f"{self.args[0]} (File {p.file_name}, Line {p.line_no}, Column {p.col_no})"
        )


# @typing.no_type_check
@dataclass
class Scanner:
    eof: bool = False
    sym: Enum | None = None  # Next Symbol
    value: str = ""
    file_name: Path | None = None
    line_no: int = 0
    col_no: int = 0

    _ch: str = ""
    _text: io.TextIOBase | None = None
    _text_line: str = ""

    _keyword = {str(i): i for i in Token if str(i).isupper()}
    _symbol = {
        str(i): i for i in Token if not str(i).isupper() and not str(i).islower()
    }

    def open(self, text: io.TextIOBase) -> None:
        self._text = text
        if isinstance(text, io.TextIOWrapper):
            self.file_name = Path(text.name)
        else:
            self.file_name = None

        self.get_next_char()

    def position(self) -> Position:
        return Position(
            file_name=str(self.file_name) if self.file_name else "",
            line_no=self.line_no,
            col_no=self.col_no,
        )

    def skip_space(self) -> None:
        while self._ch.isspace():
            self.get_next_char()

    def skip_comment(self) -> None:
        while True:
            self.get_next_char()
            if self.eof:
                raise ScannerError("Unterminated comment", self.position())
            if self._ch == "(":
                self.get_next_char()
                if self._ch == "*":
                    self.get_next_char()
                    self.skip_comment()
            if self._ch == "*":
                self.get_next_char()
                if self._ch == ")":
                    self.get_next_char()
                    return

    def get_next_char(self) -> None:
        assert self._text is not None
        while not self.eof and self._text_line == "":
            self._text_line = self._text.readline()
            self.line_no += 1
            self.col_no = 0
            if self._text_line == "":
                self.eof = True
                break
            self._text_line = self._text_line.rstrip()
        if self.eof:
            self._ch = ""
        else:
            assert self._text_line != ""
            self._ch = self._text_line[0]
            self._text_line = self._text_line[1:]
            self.col_no += 1

    def get_next_symbol(self) -> None:  # noqa: C901

        def token() -> tuple[Enum, str]:
            prev_token = None
            prev_value = None
            value = ""
            while not self.eof:
                value += self._ch
                t = self._symbol.get(value, None)
                if t is None:
                    break
                prev_token = t
                prev_value = value
                self.get_next_char()
            if prev_token is None:
                raise ScannerError(f"Unknown symbol '{value}'", self.position())
            else:
                assert prev_value is not None
                return (prev_token, prev_value)

        while True:
            self.skip_space()
            if self.eof:
                self.sym = Token.EOF
            elif self._ch.isalpha():
                self.value = self._ch
                self.get_next_char()
                while self._ch.isalpha() or self._ch.isdigit():
                    self.value += self._ch
                    self.get_next_char()
                if (kw := self.value) in self._keyword:
                    self.sym = self._keyword[kw]
                else:
                    self.sym = Token.IDENT
            elif self._ch.isdigit():
                self.value = self._ch
                self.get_next_char()
                while self._ch.isdigit():
                    self.value += self._ch
                    self.get_next_char()
                self.sym = Token.NUMBER
            else:
                self.sym, self.value = token()
                if (self.sym == Token.LPAREN) and (self._ch == "*"):
                    self.get_next_char()
                    logger.debug("Skipping comment")
                    self.skip_comment()
                    self.sym = None
            if self.sym is not None:
                logger.debug(f"Symbol: {self.sym} Value: {self.value}")
                break
