# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 scanner
"""

import io
import typing
from enum import Enum
from pathlib import Path

from loguru import logger
from pydantic import BaseModel

from oberon0_compiler.token import Token


# @typing.no_type_check
class Scanner(BaseModel):
    eof: bool = False
    sym: Enum | None = None  # Next Symbol
    value: str = ""

    _ch: str = ""
    _file_name: Path | None = None
    _text: typing.TextIO | None = None
    _text_line: str = ""
    _line_no: int = 0
    _col_no: int = 0

    _keyword = {str(i): i for i in Token if str(i).isupper()}
    _symbol = {
        str(i): i for i in Token if not str(i).isupper() and not str(i).islower()
    }

    def open(self, text: io.TextIOBase) -> None:
        self._text = text
        if hasattr(text, "name"):
            self._file_name = Path(text.name)
        else:
            self._file_name = None

        self.get_next_char()

    def raise_error(self, msg: str) -> None:
        logger.error(msg)
        raise SyntaxError(
            msg, (self._file_name, self._line_no, self._col_no, self._text_line)
        )

    def skip_space(self):
        while self._ch.isspace():
            self.get_next_char()

    def skip_comment(self):
        while True:
            self.get_next_char()
            if self.eof:
                self.error("Unterminated comment")
                return
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

    def get_next_char(self):
        while not self.eof and self._text_line == "":
            self._text_line = self._text.readline()
            self._line_no += 1
            self._col_no = 0
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
            self._col_no += 1

    def get_next_symbol(self):  # noqa: C901

        def token() -> tuple[Enum, str]:
            value = ""
            prev_token = None
            prev_value = None
            while True:
                value += self._ch
                candidates = set(
                    [i for i in self._symbol.keys() if i.startswith(value)]
                )
                if len(candidates) <= 0:
                    if prev_token is None:
                        self.error(f"Unknown symbol '{value}'")
                        return (Token.OTHER, value)
                    else:
                        return (prev_token, prev_value)
                elif len(candidates) == 1:
                    self.get_next_char()
                    return (self._symbol[candidates.pop()], value)
                else:
                    prev_token = self._symbol.get(value, None)
                    prev_value = value
                    self.get_next_char()

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
                self.value = int(self._ch)
                self.get_next_char()
                while self._ch.isdigit():
                    self.value = self.value * 10 + int(self._ch)
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
