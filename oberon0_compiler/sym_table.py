# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-2 Symbol Table
"""


import wasm_gen as W  # noqa
from pydantic import BaseModel

from oberon0_compiler import ast


class Symbol(BaseModel):
    name: str


class Variable(Symbol):
    type: ast.Type
    size: int


class LocalVariable(Variable):
    offset: int


class GlobalVariable(Variable):
    offset: int


class Constant(Variable):
    value: int


class Argument(BaseModel):
    type: ast.Type
    byref: bool


class ProcedureDefinition(Symbol):
    arguments: list[Argument] = []


class SystemCall(ProcedureDefinition):
    syscall: W.BaseFunction
    return_type: ast.Type | None = None


class SymbolTable(BaseModel):
    symbols: list[Symbol] = []

    def add(self, symbol):
        self.symbols.append(symbol)

    def find(self, name):
        for s in self.symbols:
            if s.name == name:
                return s
        return None
