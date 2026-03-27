# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-2 WASM Code Generator
"""

from dataclasses import dataclass, field
from typing import BinaryIO

import wasm_gen as W  # noqa
from loguru import logger
from rich.console import Console
from wasm_gen import instructions as I  # noqa
from wasm_gen.type import i32_t

from . import ast
from . import sym_table as SYM
from .scanner import Position

console = Console()

system_calls = [
    (
        "OpenInput",
        W.BaseFunction(type=W.FunctionType(params=[], results=[])),
    ),
    (
        "ReadInt",
        W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[])),
    ),
    (
        "eot",
        W.BaseFunction(type=W.FunctionType(params=[], results=[i32_t])),
    ),
    (
        "WriteChar",
        W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[])),
    ),
    (
        "WriteInt",
        W.BaseFunction(type=W.FunctionType(params=[i32_t, i32_t], results=[])),
    ),
    (
        "WriteLn",
        W.BaseFunction(type=W.FunctionType(params=[], results=[])),
    ),
]


class CodeGenError(Exception):
    def __init__(self, message: str, position: Position) -> None:
        super().__init__(message)
        self.position = position

    def __str__(self) -> str:
        p = self.position
        return (
            f"{self.args[0]} (File {p.file_name}, Line {p.line_no}, Column {p.col_no})"
        )


@dataclass
class CodeGenerator:
    code: W.Module | None = None
    _sp: W.BaseGlobal | None = None
    _current_function: list[W.Function] = field(default_factory=list)

    def ensure(self, node: ast.Node, condition: bool, message: str) -> None:
        if not condition:
            raise CodeGenError(message, node.position)

    def current_function(self) -> W.Function:
        assert len(self._current_function) > 0
        return self._current_function[-1]

    def add_syscalls(self) -> None:
        logger.debug("Adding system calls")
        assert self.code is not None
        for name, func in system_calls:
            self.code.imports.append(
                W.Import(
                    node=func,
                    module="sys",
                    name=name,
                )
            )

    def add_memory(self) -> None:
        assert self.code is not None
        m1 = W.BaseMemory(type=W.MemoryType(min_pages=1))
        self.code.imports.append(W.Import(node=m1, module="env", name="memory"))

    def add_stack_pointer(self) -> None:
        assert self.code is not None
        self._sp = W.BaseGlobal(type=W.GlobalType(type=i32_t, mutable=True))
        self.code.imports.append(
            W.Import(node=self._sp, module="env", name="__stack_pointer")
        )

    def addr_of_symbol(self, node: ast.Node, sym: SYM.Symbol) -> None:
        assert self._sp is not None
        fn = self.current_function()
        if isinstance(sym, SYM.LocalVariable):
            fn.body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=sym.offset),
                    I.I32Add(),
                ]
            )
        elif isinstance(sym, SYM.GlobalVariable):
            fn.body.extend(
                [
                    I.I32Const(value=sym.offset),
                ]
            )
        elif isinstance(sym, SYM.FormalParameter):
            self.ensure(node, sym.by_ref, "Symbol must be by reference")
            fn.body.extend(
                [
                    I.LocalGet(localidx=sym.index),
                ]
            )
        else:
            raise CodeGenError(
                f"Unknown instance of symbol: {sym} (NOT YET IMPLEMENTED)",
                node.position,
            )

    def addr_of_expr(self, expr: ast.Expression) -> None:
        self.ensure(expr, isinstance(expr, ast.SimpleExpression), "Expression expected")
        assert isinstance(expr, ast.SimpleExpression)
        self.ensure(expr, expr.sign is None, "Sign not allowed")
        self.ensure(
            expr,
            isinstance(expr.term.factor, ast.Ident),
            "Simple factor expected",
        )
        assert isinstance(expr.term.factor, ast.Ident)
        self.ensure(expr, len(expr.term.mulop_factors) == 0, "No mulop factors allowed")
        self.ensure(expr, len(expr.addop_terms) == 0, "No addop terms allowed")

        self.addr_of_symbol(expr, expr.term.factor.symbol)

    def function_call(self, f: ast.FunctionCall) -> None:
        s = f.symbol
        self.ensure(f, isinstance(s, SYM.SystemCall), "Only system calls allowed")
        assert isinstance(s, SYM.SystemCall)
        self.system_call(f, s)

    def factor(self, f: ast.Factor) -> None:
        assert self.code is not None and self._sp is not None
        if isinstance(f, ast.Number):
            logger.debug(f"Number: {f.value}")
            self.current_function().body.append(I.I32Const(value=f.value))
        elif isinstance(f, ast.Ident):
            sym = f.symbol
            if isinstance(sym, SYM.LocalVariable):
                self.current_function().body.extend(
                    [
                        I.GlobalGet(global_=self._sp),
                        I.I32Const(value=sym.offset),
                        I.I32Add(),
                        I.I32Load(),
                    ]
                )
            elif isinstance(sym, SYM.GlobalVariable):
                self.current_function().body.extend(
                    [
                        I.I32Const(value=sym.offset),
                        I.I32Load(),
                    ]
                )
            elif isinstance(sym, SYM.FormalParameter):
                if sym.by_ref:
                    self.current_function().body.extend(
                        [
                            I.LocalGet(localidx=sym.index),
                            I.I32Load(),
                        ]
                    )
                else:
                    self.current_function().body.extend(
                        [
                            I.LocalGet(localidx=sym.index),
                        ]
                    )
            elif isinstance(sym, SYM.Constant):
                self.current_function().body.append(I.I32Const(value=sym.value))
            else:
                raise CodeGenError(f"Unknown symbol: {sym}", f.position)

        elif isinstance(f, ast.FunctionCall):
            self.function_call(f)
        elif isinstance(f, ast.ExpressionFactor):
            self.expression(f.expression)
        elif isinstance(f, ast.Negation):
            fn = self.current_function()
            self.factor(f.factor)
            fn.body.append(I.I32Const(value=0))
            fn.body.append(I.I32Eq())
        else:
            raise CodeGenError(f"Unknown factor: {f}", f.position)

    def term(self, t: ast.Term) -> None:
        self.factor(t.factor)
        fn = self.current_function()
        for op, f in t.mulop_factors:
            self.factor(f)
            if op == "*":
                fn.body.append(I.I32Mul())
            elif op == "DIV":
                fn.body.append(I.I32DivS())
            elif op == "MOD":
                fn.body.append(I.I32RemS())
            elif op == "&":
                fn.body.append(I.I32And())
            else:
                raise CodeGenError(f"Unknown mulop: {op}", t.position)

    def simple_expression(self, expr: ast.SimpleExpression) -> None:
        fn = self.current_function()

        if expr.sign == "-":
            fn.body.append(I.I32Const(value=0))
            self.term(expr.term)
            fn.body.append(I.I32Sub())
        else:
            self.term(expr.term)

        for op, t in expr.addop_terms:
            self.term(t)
            if op == "+":
                fn.body.append(I.I32Add())
            elif op == "-":
                fn.body.append(I.I32Sub())
            elif op == "OR":
                fn.body.append(I.I32Or())
            else:
                raise CodeGenError(f"Unknown addop: {op}", expr.position)

    def complex_expression(self, expr: ast.ComplexExpression) -> None:
        self.simple_expression(expr.simple_expression)
        if expr.relation is None:
            return

        fn = self.current_function()
        self.simple_expression(expr.relation[1])
        if expr.relation[0] == "=":
            fn.body.append(I.I32Eq())
        elif expr.relation[0] == "#":
            fn.body.append(I.I32Ne())
        elif expr.relation[0] == "<":
            fn.body.append(I.I32LtS())
        elif expr.relation[0] == "<=":
            fn.body.append(I.I32LeS())
        elif expr.relation[0] == ">":
            fn.body.append(I.I32GtS())
        elif expr.relation[0] == ">=":
            fn.body.append(I.I32GeS())
        else:
            raise CodeGenError(f"Unknown relation: {expr.relation[0]}", expr.position)

    def expression(self, expr: ast.Expression) -> None:
        if isinstance(expr, ast.SimpleExpression):
            self.simple_expression(expr)
        elif isinstance(expr, ast.ComplexExpression):
            self.complex_expression(expr)
        else:
            raise CodeGenError(f"Unknown expression: {expr}", expr.position)

    def assignment(self, a: ast.Assignment) -> None:
        fn = self.current_function()
        sym = a.symbol
        self.ensure(a, sym is not None, f"Unknown symbol: {sym}")
        assert sym is not None
        self.addr_of_symbol(a, sym)
        self.expression(a.expression)

        if isinstance(sym, SYM.FormalParameter) and not sym.by_ref:
            fn.body.append(I.LocalSet(localidx=sym.index))
        else:
            fn.body.append(I.I32Store())

    def system_call(
        self, p: ast.FunctionCall | ast.ProcedureCall, s: SYM.SystemCall
    ) -> None:
        logger.debug(f"System call: {p.symbol.name}")
        self.ensure(p, len(p.params) == len(s.params), "Wrong number of arguments")
        for i, a in enumerate(p.params):
            # TODO: check type
            if s.params[i].by_ref:
                logger.debug(f"argument: {a} by ref")
                self.addr_of_expr(a)
            else:
                logger.debug(f"argument: {a} by val")
                self.expression(a)

        self.current_function().body.append(I.Call(function=system_calls[s.index][1]))

    def while_loop(self, w: ast.While) -> None:
        fn = self.current_function()

        fn.body.append(I.Block())
        fn.body.append(I.Loop())

        self.expression(w.condition)
        fn.body.append(I.I32Const(value=0))
        fn.body.append(I.I32Eq())
        fn.body.append(I.BrIf(label=1))
        self.statement_sequence(w.body.statements)
        fn.body.append(I.Br(label=0))
        fn.body.append(I.End())
        fn.body.append(I.End())

    def repeat_loop(self, w: ast.Repeat) -> None:
        fn = self.current_function()
        fn.body.append(I.Loop())
        self.statement_sequence(w.body.statements)
        self.expression(w.condition)
        fn.body.append(I.BrIf(label=0))
        fn.body.append(I.End())

    def if_statement(self, i: ast.If) -> None:
        fn = self.current_function()
        self.expression(i.condition)
        fn.body.append(I.If())
        self.statement_sequence(i.then.statements)

        if i.elsif is not None:
            for c, s in i.elsif:
                fn.body.append(I.Else())
                self.expression(c)
                fn.body.append(I.If())
                self.statement_sequence(s.statements)

        if i.else_ is not None:
            fn.body.append(I.Else())
            self.statement_sequence(i.else_.statements)

        if i.elsif is not None:
            for _ in range(len(i.elsif)):
                fn.body.append(I.End())

        fn.body.append(I.End())

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
                raise CodeGenError(f"Unknown statement: {s}", s.position)

    def procedure_call(self, p: ast.ProcedureCall) -> None:
        s = p.symbol
        if isinstance(s, SYM.SystemCall):
            self.system_call(p, s)

    def procedure(self, p: ast.ProcedureDeclaration) -> None:
        assert self.code is not None and self._sp is not None
        if p.symbol.exported:
            self.ensure(
                p,
                len(p.symbol.params) == 0,
                "Exported procedures cannot have parameters",
            )

        f = W.Function(type=W.FunctionType(params=[], results=[]))
        self._current_function.append(f)

        # Procedure preamble (make room for local variables)

        if p.symbol.stack_size > 0:
            f.body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=p.symbol.stack_size),
                    I.I32Sub(),
                    I.GlobalSet(global_=self._sp),
                ]
            )

        self.statement_sequence(p.body.statements)

        # Procedure postamble (reclaim memory for local variables)
        if p.symbol.stack_size > 0:
            f.body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=p.symbol.stack_size),
                    I.I32Add(),
                    I.GlobalSet(global_=self._sp),
                ]
            )

        f.body.append(I.End())
        self.code.funcs.append(f)
        if p.symbol.exported:
            self.code.exports.append(W.Export(node=f, name=p.symbol.name))

        self._current_function.pop()

    def generate(self, ast_: ast.Module, io: BinaryIO) -> None:

        self.ensure(ast_, isinstance(ast_, ast.Module), "Module expected")
        self.code = W.Module()

        self.add_syscalls()
        self.add_memory()
        self.add_stack_pointer()

        d = ast_.declarations

        for p in d.procedure_declarations:
            self.procedure(p)

        io.write(bytes(self.code))
