# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 Abstract Syntax Tree
"""

from dataclasses import dataclass

from . import sym_table as SYM
from .scanner import Position, Scanner

actual_scanner: Scanner | None = None


@dataclass
class Node:
    position: Position

    def __str__(self) -> str:
        return ""


@dataclass
class Type(Node):
    pass


@dataclass
class Expression(Node):

    def __str__(self) -> str:
        return ""


@dataclass
class ConstantDeclaration(Node):
    symbol: SYM.Constant

    def __str__(self) -> str:
        return f"CONST {self.symbol.name} = {self.symbol.value}"


@dataclass
class VariableDeclaration(Node):
    symbol: SYM.LocalVariable | SYM.GlobalVariable

    def __str__(self) -> str:
        return f"VAR {self.symbol.name}: {self.symbol.type_};"


@dataclass
class Declarations(Node):
    const_declarations: list[ConstantDeclaration]
    var_declarations: list[VariableDeclaration]
    procedure_declarations: list["ProcedureDeclaration"]

    def __str__(self) -> str:
        c = "\n".join(str(d) for d in self.const_declarations)
        v = "\n".join(str(d) for d in self.var_declarations)
        p = "\n".join(str(d) for d in self.procedure_declarations)
        return "\n".join([i for i in [c, v, p] if i])


@dataclass
class Statement(Node):
    pass


@dataclass
class StatementSequence(Node):
    statements: list[Statement]

    def __str__(self) -> str:
        return ";\n".join([str(s) for s in self.statements if type(s) is not Statement])


@dataclass
class ProcedureDeclaration(Node):
    symbol: SYM.ProcedureDefinition
    exported: bool
    declarations: Declarations
    body: StatementSequence

    def __str__(self) -> str:
        e = "*" if self.exported else ""
        fp = (
            f"({', '.join(str(p) for p in self.symbol.params)})"
            if self.symbol.params
            else ""
        )
        decl = str(self.declarations)
        body = str(self.body)

        res = f"PROCEDURE {self.symbol.name}{e}{fp};"
        if decl:
            res += "\n" + decl
        if body:
            res += "\nBEGIN\n" + body
        return res + f"\nEND {self.symbol.name}"


@dataclass
class NamedType(Type):
    ident: SYM.Symbol

    def __str__(self) -> str:
        return self.ident.name


@dataclass
class EmptyStatement(Statement):
    pass

    def __str__(self) -> str:
        return "<EMPTY>"


@dataclass
class Assignment(Statement):
    symbol: SYM.Symbol
    expression: Expression

    def __str__(self) -> str:
        lhs = f"{self.symbol.name}"
        rhs = f"{self.expression}"
        return f"{lhs} := {rhs}"


@dataclass
class ProcedureCall(Statement):
    symbol: SYM.Symbol
    params: list[Expression]

    def __str__(self) -> str:
        return f"{self.symbol.name}({', '.join(str(p) for p in self.params)})"


@dataclass
class If(Statement):
    condition: Expression
    then: StatementSequence
    elsif: list[tuple[Expression, StatementSequence]] | None
    else_: StatementSequence | None

    def __str__(self) -> str:
        res = f"IF {self.condition} THEN\n{self.then}"
        if self.elsif is not None and len(self.elsif) > 0:
            res += "\n".join(f"ELSIF {c} THEN\n{s}" for c, s in self.elsif)
        if self.else_:
            res += "ELSE\n" + str(self.else_)
        return res + "\nEND"


@dataclass
class While(Statement):
    condition: Expression
    body: StatementSequence

    def __str__(self) -> str:
        return f"WHILE {self.condition} DO\n{self.body}\nEND"


@dataclass
class Repeat(Statement):
    body: StatementSequence
    condition: Expression

    def __str__(self) -> str:
        return f"REPEAT\n{self.body}\nUNTIL {self.condition}"


@dataclass
class Factor(Node):
    pass


@dataclass
class Term(Node):
    factor: Factor
    mulop_factors: list[tuple[str, Factor]]

    def __str__(self) -> str:
        mulop = "".join(f" {op} {f}" for op, f in self.mulop_factors)
        return f"{self.factor}{mulop}"


@dataclass
class FunctionCall(Factor):
    symbol: SYM.Symbol
    params: list[Expression]

    def __str__(self) -> str:
        return f"{self.symbol.name}({', '.join(str(p) for p in self.params)})"


@dataclass
class SimpleExpression(Expression):
    sign: str | None
    term: Term
    addop_terms: list[tuple[str, Term]]

    def __str__(self) -> str:
        addop = "".join(f" {op} {t}" for op, t in self.addop_terms)
        return f"{self.sign or ''}{self.term}{addop}"


@dataclass
class ComplexExpression(Expression):
    simple_expression: SimpleExpression
    relation: tuple[str, SimpleExpression] | None

    def __str__(self) -> str:
        return (
            f"{self.simple_expression} {self.relation[0]} {self.relation[1]}"
            if self.relation
            else str(self.simple_expression)
        )


@dataclass
class SimpleFactor(Factor):
    symbol: SYM.Symbol

    def __str__(self) -> str:
        return self.symbol.name


@dataclass
class Number(Factor):
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class ExpressionFactor(Factor):
    expression: Expression

    def __str__(self) -> str:
        return f"({self.expression})"


@dataclass
class Negation(Factor):
    factor: Factor

    def __str__(self) -> str:
        return f"~{self.factor}"


@dataclass
class Module(Node):
    ident: str
    declarations: Declarations
    body: StatementSequence

    def __str__(self) -> str:
        decl = str(self.declarations)
        body = str(self.body)
        res = f"MODULE {self.ident};"
        if decl:
            res += "\n" + decl
        if body:
            res += "\nBEGIN\n" + body
        return res + f"\nEND {self.ident}."
