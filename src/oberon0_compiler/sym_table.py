# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-2 Symbol Table
"""

from dataclasses import dataclass, field

import wasm_gen as W  # noqa
from loguru import logger


@dataclass
class Symbol:
    name: str


@dataclass
class Type(Symbol):
    index: int
    size: int


@dataclass
class Variable(Symbol):
    type_: Type


@dataclass
class LocalVariable(Variable):
    offset: int


@dataclass
class GlobalVariable(Variable):
    offset: int


@dataclass
class FormalParameter(Variable):
    by_ref: bool


@dataclass
class Constant(Variable):
    value: int


@dataclass
class ProcedureDefinition(Symbol):
    exported: bool
    params: list[FormalParameter]
    stack_size: int


@dataclass
class SystemCall(Symbol):
    index: int
    params: list[FormalParameter]
    return_type: Type | None = None


@dataclass
class Scope:
    level: int
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def add(self, symbol: Symbol) -> None:
        if symbol.name in self.symbols:
            raise KeyError(
                f"Symbol {symbol.name} already defined in scope {self.level}"
            )
        self.symbols[symbol.name] = symbol

    def find(self, name: str, class_: type) -> Symbol | None:
        logger.debug(f"Looking for {name} at level {self.level}")
        if name in self.symbols:
            s = self.symbols[name]
            logger.debug(f"Found {s}")
            if isinstance(s, class_):
                return s
        return None


@dataclass
class SymbolTable:
    scopes: list[Scope] = field(default_factory=list)

    def current_level(self) -> int:
        return len(self.scopes) - 1

    def current_scope(self) -> Scope:
        return self.scopes[-1]

    def new_scope(self) -> None:
        level = len(self.scopes)
        logger.debug(f"New scope at level {level}")
        self.scopes.append(Scope(level=level))

    def close_scope(self) -> None:
        if len(self.scopes) == 0:
            raise IndexError("No scope to close")
        logger.debug(f"Closing scope at level {self.current_level()}")
        for s in self.scopes[-1].symbols.values():
            logger.debug(f"> {s}")
        self.scopes.pop()

    def add(self, symbol: Symbol) -> None:
        scope = self.current_scope()
        scope.add(symbol)

    def find(
        self,
        name: str,
        class_: type = Symbol,
        min_level: int = 0,
        max_level: int | None = None,
    ) -> Symbol | None:
        for scope in reversed(self.scopes[min_level:max_level]):
            s = scope.find(name, class_)
            if s is not None:
                return s
        logger.debug(f"Symbol {name} not found")
        return None

    def get(
        self,
        name: str,
        class_: type = Symbol,
        min_level: int = 0,
        max_level: int | None = None,
    ) -> Symbol:
        s = self.find(name, class_, min_level, max_level)
        if s is None:
            raise LookupError(f"Symbol {name} not found")
        return s

    def type_(
        self, name: str, min_level: int = 0, max_level: int | None = None
    ) -> Type:
        s = self.get(name, class_=Type, min_level=min_level, max_level=max_level)
        if not isinstance(s, Type):
            raise TypeError(f"Symbol {name} is not a type")
        return s
