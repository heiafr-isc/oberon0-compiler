# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-2 WASM Code Generator
"""


from dataclasses import dataclass

from loguru import logger
from rich.console import Console

from . import ast, types
from . import sym_table as SYM
from .scanner import Position

console = Console()


class TypeCheckError(Exception):
    def __init__(self, message: str, position: Position) -> None:
        super().__init__(message)
        self.position = position

    def __str__(self) -> str:
        p = self.position
        return (
            f"{self.args[0]} (File {p.file_name}, Line {p.line_no}, Column {p.col_no})"
        )


@dataclass
class TypeChecker:

    def ensure(self, node: ast.Node, condition: bool, message: str) -> None:
        if not condition:
            raise TypeCheckError(message, node.position)

    def function_call(self, f: ast.FunctionCall) -> SYM.Type | None:
        s = f.symbol
        self.ensure(f, isinstance(s, SYM.SystemCall), "Only system calls allowed")
        assert isinstance(s, SYM.SystemCall)
        self.ensure(
            f,
            s.return_type is not None and s.return_type == types.integer,
            "Return type must be INTEGER",
        )
        self.system_call(f, s)
        return s.return_type

    def factor(self, f: ast.Factor) -> SYM.Type | None:
        if isinstance(f, ast.Number):
            logger.debug(f"Number: {f.value}")
            return types.integer
        elif isinstance(f, ast.Ident):
            assert isinstance(f.symbol, SYM.Variable) or isinstance(
                f.symbol, SYM.Constant
            )
            return f.symbol.type_

        elif isinstance(f, ast.FunctionCall):
            return self.function_call(f)
        elif isinstance(f, ast.ExpressionFactor):
            return self.expression(f.expression)
        elif isinstance(f, ast.Negation):
            return self.factor(f.factor)
        else:
            raise TypeCheckError(f"Unknown factor: {f}", f.position)

    def term(self, t: ast.Term) -> SYM.Type:
        f1_type = self.factor(t.factor)
        assert f1_type is not None
        for op, f in t.mulop_factors:
            f2_type = self.factor(f)
            self.ensure(t, f1_type == f2_type, "Type mismatch")
            if op == "*":
                self.ensure(
                    t, f1_type == types.integer, "Type mismatch : expected INTEGER"
                )
            elif op == "DIV":
                self.ensure(
                    t, f1_type == types.integer, "Type mismatch : expected INTEGER"
                )
            elif op == "MOD":
                self.ensure(
                    t, f1_type == types.integer, "Type mismatch : expected INTEGER"
                )
            elif op == "&":
                self.ensure(
                    t, f1_type == types.boolean, "Type mismatch : expected BOOLEAN"
                )
            else:
                raise TypeCheckError(f"Unknown mulop: {op}", t.position)

        return f1_type

    def simple_expression(self, expr: ast.SimpleExpression) -> SYM.Type:
        t1_type = self.term(expr.term)
        for op, t in expr.addop_terms:
            t2_type = self.term(t)
            self.ensure(expr, t1_type == t2_type, "Type mismatch")
            if op == "+":
                self.ensure(
                    expr, t1_type == types.integer, "Type mismatch : expected INTEGER"
                )
            elif op == "-":
                self.ensure(
                    expr, t1_type == types.integer, "Type mismatch : expected INTEGER"
                )
            elif op == "OR":
                self.ensure(
                    expr, t1_type == types.boolean, "Type mismatch : expected BOOLEAN"
                )
            else:
                raise TypeCheckError(f"Unknown addop: {op}", expr.position)
        return t1_type

    def complex_expression(self, expr: ast.ComplexExpression) -> SYM.Type:
        e1_type = self.simple_expression(expr.simple_expression)
        if expr.relation is None:
            return e1_type

        e2_type = self.simple_expression(expr.relation[1])
        self.ensure(expr, e1_type == e2_type, f"Type mismatch {e1_type} {e2_type}")
        if expr.relation[0] == "=":
            pass
        elif expr.relation[0] == "#":
            pass
        elif expr.relation[0] == "<":
            self.ensure(
                expr, e1_type == types.integer, "Type mismatch : expected INTEGER"
            )
        elif expr.relation[0] == "<=":
            self.ensure(
                expr, e1_type == types.integer, "Type mismatch : expected INTEGER"
            )
        elif expr.relation[0] == ">":
            self.ensure(
                expr, e1_type == types.integer, "Type mismatch : expected INTEGER"
            )
        elif expr.relation[0] == ">=":
            self.ensure(
                expr, e1_type == types.integer, "Type mismatch : expected INTEGER"
            )
        else:
            raise TypeCheckError(f"Unknown relation: {expr.relation[0]}", expr.position)
        return types.boolean

    def expression(self, expr: ast.Expression) -> SYM.Type:
        if isinstance(expr, ast.SimpleExpression):
            return self.simple_expression(expr)
        elif isinstance(expr, ast.ComplexExpression):
            return self.complex_expression(expr)
        else:
            raise TypeCheckError(f"Unknown expression: {expr}", expr.position)

    def assignment(self, a: ast.Assignment) -> None:
        sym = a.symbol
        self.ensure(a, sym is not None, f"Unknown symbol: {sym}")
        assert sym is not None
        self.expression(a.expression)

    def system_call(
        self, p: ast.FunctionCall | ast.ProcedureCall, s: SYM.SystemCall
    ) -> None:
        logger.debug(f"System call: {p.symbol.name}")
        self.ensure(p, len(p.params) == len(s.params), "Wrong number of arguments")
        # for i, a in enumerate(p.params):
        #     # TODO: check type
        #     pass

    def while_loop(self, w: ast.While) -> None:
        self.expression(w.condition)
        self.statement_sequence(w.body.statements)

    def repeat_loop(self, w: ast.Repeat) -> None:
        self.statement_sequence(w.body.statements)
        self.expression(w.condition)

    def if_statement(self, i: ast.If) -> None:
        self.expression(i.condition)
        self.statement_sequence(i.then.statements)

        if i.elsif is not None:
            for c, s in i.elsif:
                self.expression(c)
                self.statement_sequence(s.statements)

        if i.else_ is not None:
            self.statement_sequence(i.else_.statements)

    def statement_sequence(self, statements: list[ast.Statement]) -> None:
        for s in statements:
            if isinstance(s, ast.EmptyStatement):
                pass
            elif isinstance(s, ast.ProcedureCall):
                self.procedure_call(s)
            elif isinstance(s, ast.Assignment):
                self.assignment(s)
            elif isinstance(s, ast.While):
                self.while_loop(s)
            elif isinstance(s, ast.Repeat):
                self.repeat_loop(s)
            elif isinstance(s, ast.If):
                self.if_statement(s)
            else:
                raise TypeCheckError(f"Unknown statement: {s}", s.position)

    def procedure_call(self, p: ast.ProcedureCall) -> None:
        s = p.symbol
        if isinstance(s, SYM.SystemCall):
            self.system_call(p, s)

    def procedure(self, p: ast.ProcedureDeclaration) -> None:
        if p.exported:
            self.ensure(
                p,
                len(p.symbol.params) == 0,
                "Exported procedures cannot have parameters",
            )
        self.statement_sequence(p.body.statements)

    def check(self, ast_: ast.Module) -> None:
        self.ensure(ast_, isinstance(ast_, ast.Module), "Module expected")
        d = ast_.declarations
        for p in d.procedure_declarations:
            self.procedure(p)

        logger.debug("Type checking completed successfully")
