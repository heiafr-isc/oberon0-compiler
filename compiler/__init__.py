# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Generic Scanner and Parser for Compilers
"""

import traceback
import typing
from abc import ABC, abstractmethod


class Scanner(ABC):
    def __init__(self, text: typing.TextIO):
        self.text = text  # type: typing.TextIO
        self.ch = None  # type: str
        self.text_line = ""  # type: str
        self.line_no = 0  # type: int
        self.col_no = 0  # type: int
        self.eof = False  # type: bool

        self.get_next_char()
        self.get_next_symbol()

    def skip_space(self):
        while self.ch.isspace():
            self.get_next_char()

    def error(self, msg: str):
        print(f"Error: {msg} at line {self.line_no}, column {self.col_no}")
        frames = [
            f
            for f in traceback.extract_stack()
            if f.filename != __file__ and f.name != "check_sym"
        ][-1]
        print(f"  from {frames.filename}, line {frames.lineno} ({frames.name})")

    def get_next_char(self):
        while not self.eof and self.text_line == "":
            self.text_line = self.text.readline()
            self.line_no += 1
            self.col_no = 0
            if self.text_line == "":
                self.eof = True
                break
            self.text_line = self.text_line.rstrip()
        if self.eof:
            self.ch = ""
        else:
            assert self.text_line != ""
            self.ch = self.text_line[0]
            self.text_line = self.text_line[1:]
            self.col_no += 1

    @abstractmethod
    def get_next_symbol(self):
        raise NotImplementedError


class Parser:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner
        self.has_error = False

    def error(self, msg: str):
        self.scanner.error(msg)
        self.has_error = True

    @property
    def next_sym(self):
        return self.scanner.sym

    def get_next_symbol(self):
        self.scanner.get_next_symbol()
