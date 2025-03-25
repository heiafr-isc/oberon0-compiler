# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-2 Symbol Table
"""


import wasm_gen as W  # noqa
from loguru import logger
from pydantic import BaseModel

from oberon0_compiler import ast


class Symbol(BaseModel):
    name: str


class Type(Symbol):
    type: ast.Type
    size: int


class Variable(Symbol):
    type: Type


class LocalVariable(Variable):
    offset: int


class GlobalVariable(Variable):
    offset: int


class Constant(Variable):
    value: int


class Argument(BaseModel):
    type: Type
    byref: bool


class ProcedureDefinition(Symbol):
    arguments: list[Argument] = []


class SystemCall(ProcedureDefinition):
    syscall: W.BaseFunction
    return_type: Type | None = None


class Scope(BaseModel):
    level: int
    symbols: list[Symbol] = []

    def add(self, symbol):
        self.symbols.append(symbol)

    def find(self, name, class_):
        logger.debug(f"Looking for {name} in {self.symbols} at level {self.level}")
        for s in self.symbols:
            if isinstance(s, class_) and s.name == name:
                logger.debug(f"Found {s}")
                return s
        return None


class SymbolTable(BaseModel):
    scopes: list[Scope] = []

    def current_level(self):
        return len(self.scopes) - 1

    def new_scope(self):
        level = len(self.scopes)
        self.scopes.append(Scope(level=level))

    def close_scope(self):
        assert len(self.scopes) > 0
        self.scopes.pop()

    def add(self, symbol):
        scope = self.scopes[-1]
        scope.add(symbol)

    def find(self, name, class_=Symbol, min_level=0, max_level=None):
        for scope in reversed(self.scopes[min_level:max_level]):
            s = scope.find(name, class_)
            if s is not None:
                return s
        logger.debug(f"Symbol {name} not found")
        return None
