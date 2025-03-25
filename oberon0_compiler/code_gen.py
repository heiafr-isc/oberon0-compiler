# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-2 WASM Code Generator
"""


from typing import ClassVar

import wasm_gen as W  # noqa
from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from wasm_gen import instructions as I  # noqa
from wasm_gen.type import i32_t

from oberon0_compiler import ast, sym_table
from oberon0_compiler.ast import Node
from oberon0_compiler.sym_table import SymbolTable

console = Console()


class CodeGenError(Exception):
    def __init__(self, message, file_name, line_no, col_no):
        super().__init__(message)
        self.file_name = file_name
        self.line_no = line_no
        self.col_no = col_no


class CodeGenerator(BaseModel):
    ast: Node = ast
    code: W.Module = None

    _sp: W.Global = None
    _current_function: list[W.Function] = []
    _symbol_table: ClassVar[SymbolTable] = SymbolTable()

    def check(self, condition, message):
        if not condition:
            logger.error(self._symbol_table)
            raise CodeGenError(
                message,
                self.ast.file_name,
                self.ast.line_no,
                self.ast.col_no,
            )

    def current_function(self):
        assert len(self._current_function) > 0
        return self._current_function[-1]

    def add_syscalls(self):
        logger.debug("Adding system calls")

        integer: sym_table.Type = self._symbol_table.find(
            "INTEGER", class_=sym_table.Type, max_level=1
        )

        assert integer is not None
        logger.debug(f"INTEGER: {integer}")

        syscalls = [
            (
                "OpenInput",
                W.BaseFunction(type=W.FunctionType(params=[], results=[])),
                [],
                None,
            ),
            (
                "ReadInt",
                W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[])),
                [sym_table.Argument(type=integer, byref=True)],
                None,
            ),
            (
                "eot",
                W.BaseFunction(type=W.FunctionType(params=[], results=[i32_t])),
                [],
                integer,
            ),
            (
                "WriteChar",
                W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[])),
                [sym_table.Argument(type=integer, byref=False)],
                None,
            ),
            (
                "WriteInt",
                W.BaseFunction(type=W.FunctionType(params=[i32_t, i32_t], results=[])),
                [
                    sym_table.Argument(type=integer, byref=False),
                    sym_table.Argument(type=integer, byref=False),
                ],
                None,
            ),
            (
                "WriteLn",
                W.BaseFunction(type=W.FunctionType(params=[], results=[])),
                [],
                None,
            ),
        ]

        for name, f, args, ret in syscalls:
            self.code.imports.append(W.Import(node=f, module="sys", name=name))
            self._symbol_table.add(
                sym_table.SystemCall(
                    name=name, arguments=args, return_type=ret, syscall=f
                ),
            )

    def add_memory(self):
        m1 = W.BaseMemory(type=W.MemoryType(min_pages=1))
        self.code.imports.append(W.Import(node=m1, module="env", name="memory"))

    def add_stack_pointer(self):
        self._sp = W.BaseGlobal(type=W.GlobalType(type=i32_t, mutable=True))
        self.code.imports.append(
            W.Import(node=self._sp, module="env", name="__stack_pointer")
        )

    def addr_of(self, expr):
        self.check(isinstance(expr, ast.SimpleExpression), "Expression expected")
        self.check(expr.sign is None, "Sign not allowed")
        self.check(
            isinstance(expr.term.factor, ast.SimpleFactor), "Simple factor expected"
        )
        self.check(len(expr.term.mulop_factors) == 0, "No mulop factors allowed")
        self.check(len(expr.addop_terms) == 0, "No addop terms allowed")

        sym = self._symbol_table.find(expr.term.factor.ident)
        self.check(sym is not None, f"Unknown symbol: {expr.term.factor.ident}")
        self.current_function().body.extend(
            [
                I.GlobalGet(global_=self._sp),
                I.I32Const(value=sym.offset),
                I.I32Sub(),
            ]
        )

    def function_call(self, f):
        s = self._symbol_table.find(f.ident)
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)
        self.check(s is not None, f"Unknown procedure: {f.ident}")
        self.check(isinstance(s, sym_table.SystemCall), "Only system calls allowed")
        self.check(s.return_type == integer, "Return type must be INTEGER")
        self.system_call(f, s)

    def factor(self, f) -> sym_table.Type:
        if isinstance(f, ast.Number):
            logger.debug(f"Number: {f.value}")
            self.current_function().body.append(I.I32Const(value=f.value))
            return self._symbol_table.find(
                "INTEGER", class_=sym_table.Type, max_level=1
            )
        elif isinstance(f, ast.SimpleFactor):
            sym = self._symbol_table.find(f.ident)
            self.check(sym is not None, f"Unknown symbol: {f.ident}")
            self.check(len(f.selector) == 0, "Selectors not yet implemented")

            self.current_function().body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=sym.offset),
                    I.I32Sub(),
                    I.I32Load(),
                ]
            )
            return sym.type

        elif isinstance(f, ast.FunctionCall):
            self.function_call(f)
        elif isinstance(f, ast.ExpressionFactor):
            return self.expression(f.expression)
        elif isinstance(f, ast.Negation):
            fn = self.current_function()
            t = self.factor(f.factor)
            fn.body.append(I.I32Const(value=0))
            fn.body.append(I.I32Eq())
            return t
        else:
            raise Exception(f"Unknown factor: {f}")

    def term(self, t) -> sym_table.Type:
        f1_type = self.factor(t.factor)
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)
        boolean = self._symbol_table.find("BOOLEAN", class_=sym_table.Type, max_level=1)
        fn = self.current_function()
        for op, f in t.mulop_factors:
            f2_type = self.factor(f)
            self.check(f1_type == f2_type, "Type mismatch")
            if op == "*":
                self.check(f1_type == integer, "Type mismatch : expected INTEGER")
                fn.body.append(I.I32Mul())
            elif op == "DIV":
                self.check(f1_type == integer, "Type mismatch : expected INTEGER")
                fn.body.append(I.I32DivS())
            elif op == "MOD":
                self.check(f1_type == integer, "Type mismatch : expected INTEGER")
                fn.body.append(I.I32RemS())
            elif op == "&":
                self.check(f1_type == boolean, "Type mismatch : expected BOOLEAN")
                fn.body.append(I.I32And())
            else:
                raise Exception(f"Unknown mulop: {op}")

        return f1_type

    def simple_expression(self, expr) -> sym_table.Type:
        fn = self.current_function()
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)

        if expr.sign == "-":
            fn.body.append(I.I32Const(value=0))
            t1_type = self.term(expr.term)
            self.check(t1_type == integer, "Type mismatch")
            fn.body.append(I.I32Sub())
        else:
            t1_type = self.term(expr.term)

        boolean = self._symbol_table.find("BOOLEAN", class_=sym_table.Type, max_level=1)

        for op, t in expr.addop_terms:
            t2_type = self.term(t)
            self.check(t1_type == t2_type, "Type mismatch")
            if op == "+":
                self.check(t1_type == integer, "Type mismatch : expected INTEGER")
                fn.body.append(I.I32Add())
            elif op == "-":
                self.check(t1_type == integer, "Type mismatch : expected INTEGER")
                fn.body.append(I.I32Sub())
            elif op == "OR":
                self.check(t1_type == boolean, "Type mismatch : expected BOOLEAN")
                fn.body.append(I.I32Or())
            else:
                raise Exception(f"Unknown addop: {op}")
        return t1_type

    def complex_expression(self, expr) -> sym_table.Type:
        boolean = self._symbol_table.find("BOOLEAN", class_=sym_table.Type, max_level=1)
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)
        e1_type = self.simple_expression(expr.simple_expression)
        if expr.relation is None:
            return e1_type

        fn = self.current_function()
        e2_type = self.simple_expression(expr.relation[1])
        self.check(e1_type == e2_type, "Type mismatch")
        if expr.relation[0] == "=":
            fn.body.append(I.I32Eq())
        elif expr.relation[0] == "#":
            fn.body.append(I.I32Ne())
        elif expr.relation[0] == "<":
            self.check(e1_type == integer, "Type mismatch : expected INTEGER")
            fn.body.append(I.I32LtS())
        elif expr.relation[0] == "<=":
            self.check(e1_type == integer, "Type mismatch : expected INTEGER")
            fn.body.append(I.I32LeS())
        elif expr.relation[0] == ">":
            self.check(e1_type == integer, "Type mismatch : expected INTEGER")
            fn.body.append(I.I32GtS())
        elif expr.relation[0] == ">=":
            self.check(e1_type == integer, "Type mismatch : expected INTEGER")
            fn.body.append(I.I32GeS())
        else:
            raise Exception(f"Unknown relation: {expr.relation[0]}")
        return boolean

    def expression(self, expr) -> sym_table.Type:
        if isinstance(expr, ast.SimpleExpression):
            return self.simple_expression(expr)
        elif isinstance(expr, ast.ComplexExpression):
            return self.complex_expression(expr)
        else:
            raise Exception(f"Unknown expression: {expr}")

    def assignment(self, a):
        sym = self._symbol_table.find(a.ident)
        fn = self.current_function()
        fn.body.extend(
            [
                I.GlobalGet(global_=self._sp),
                I.I32Const(value=sym.offset),
                I.I32Sub(),
            ]
        )
        self.expression(a.expression)
        fn.body.append(I.I32Store())

    def system_call(self, p, s):
        logger.debug(f"System call: {p.ident}")
        self.check(len(p.params) == len(s.arguments), "Wrong number of arguments")
        for i, a in enumerate(p.params):
            # TODO: check type
            if s.arguments[i].byref:
                logger.debug(f"argument: {a} byref")
                self.addr_of(a)
            else:
                logger.debug(f"argument: {a} byval")
                self.expression(a)

        self.current_function().body.append(I.Call(function=s.syscall))

    def while_loop(self, w):
        fn = self.current_function()

        fn.body.append(I.Block())
        self.expression(w.condition)
        fn.body.append(I.I32Const(value=0))
        fn.body.append(I.I32Eq())
        fn.body.append(I.BrIf(label=0))

        fn.body.append(I.Loop())
        self.statement_sequence(w.body.statements)
        self.expression(w.condition)
        fn.body.append(I.BrIf(label=0))
        fn.body.append(I.End())

        fn.body.append(I.End())

    def if_statement(self, i):
        fn = self.current_function()
        self.expression(i.condition)
        fn.body.append(I.If())
        self.statement_sequence(i.then.statements)

        for c, s in i.elsif:
            fn.body.append(I.Else())
            self.expression(c)
            fn.body.append(I.If())
            self.statement_sequence(s.statements)

        if i.else_ is not None:
            fn.body.append(I.Else())
            self.statement_sequence(i.else_.statements)

        for _ in range(len(i.elsif) + 1):
            fn.body.append(I.End())

    def statement_sequence(self, statements):
        for s in statements:
            if isinstance(s, ast.EmptyStatement):
                pass
            elif isinstance(s, ast.ProcedureCall):
                self.procedure_call(s)
            elif isinstance(s, ast.Assignment):
                self.assignment(s)
            elif isinstance(s, ast.While):
                self.while_loop(s)
            elif isinstance(s, ast.If):
                self.if_statement(s)
            else:
                raise Exception(f"Unknown statement: {s}")

    def procedure_call(self, p):
        s = self._symbol_table.find(p.ident)
        self.check(s is not None, f"Unknown procedure: {p.ident}")
        if isinstance(s, sym_table.SystemCall):
            self.system_call(p, s)

    def procedure(self, p):
        if p.exported:
            self.check(
                len(self._current_function) == 0,
                "Exported procedures cannot have parameters",
            )

        f = W.Function(type=W.FunctionType(params=[], results=[]))
        self._current_function.append(f)

        for vl in p.declarations.var_declarations:
            ptr = 0
            type = self._symbol_table.find(vl.type.ident, class_=sym_table.Type)
            self.check(type is not None, f"Unknown type: {vl.type.ident}")
            for v in vl.ident_list:
                self._symbol_table.add(
                    sym_table.LocalVariable(
                        name=v,
                        type=type,
                        offset=ptr,
                    )
                )
                ptr += type.size

        # Procedure preamble (make room for local variables)
        f.body.extend(
            [
                I.GlobalGet(global_=self._sp),
                I.I32Const(value=ptr),
                I.I32Sub(),
                I.GlobalSet(global_=self._sp),
            ]
        )

        self.statement_sequence(p.body.statements)

        # Procedure postamble (reclaim memory for local variables)
        f.body.extend(
            [
                I.GlobalGet(global_=self._sp),
                I.I32Const(value=ptr),
                I.I32Add(),
                I.GlobalSet(global_=self._sp),
            ]
        )

        f.body.append(I.End())
        self.code.funcs.append(f)
        if p.exported:
            self.code.exports.append(W.Export(node=f, name=p.ident))

        self._current_function.pop()

    def generate(self, io):
        # Start with an empty symbol table
        CodeGenerator._symbol_table = SymbolTable()

        self.check(isinstance(self.ast, ast.Module), "Module expected")
        self._symbol_table.new_scope()
        self.code = W.Module()

        self._symbol_table.add(
            sym_table.Type(name="INTEGER", type=ast.Type(ident="INTEGER"), size=4)
        )
        self._symbol_table.add(
            sym_table.Type(name="BOOLEAN", type=ast.Type(ident="BOOLEAN"), size=4)
        )

        self.add_syscalls()
        self.add_memory()
        self.add_stack_pointer()

        d = self.ast.Declarations
        for p in d.procedure_declarations:
            self.procedure(p)

        io.write(bytes(self.code))
