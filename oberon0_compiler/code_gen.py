# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-2 WASM Code Generator
"""


import wasm_gen as W  # noqa
from loguru import logger
from pydantic import BaseModel
from wasm_gen import instructions as I  # noqa
from wasm_gen.type import i32_t

from oberon0_compiler import ast, sym_table


class Context(BaseModel):
    current_function: W.Function = None
    symbol_table: sym_table.SymbolTable = sym_table.SymbolTable()


class CodeGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.code = None
        self.sp: W.Global = None
        self.context = Context()

    def add_syscalls(self):
        logger.debug("Adding system calls")
        open_input = W.BaseFunction(type=W.FunctionType(params=[], results=[]))
        read_int = W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[]))
        eot = W.BaseFunction(type=W.FunctionType(params=[], results=[i32_t]))
        write_char = W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[]))
        write_int = W.BaseFunction(
            type=W.FunctionType(params=[i32_t, i32_t], results=[])
        )
        write_ln = W.BaseFunction(type=W.FunctionType(params=[], results=[]))

        self.code.imports.extend(
            [
                W.Import(node=open_input, module="sys", name="OpenInput"),
                W.Import(node=read_int, module="sys", name="ReadInt"),
                W.Import(node=eot, module="sys", name="eot"),
                W.Import(node=write_char, module="sys", name="WriteChar"),
                W.Import(node=write_int, module="sys", name="WriteInt"),
                W.Import(node=write_ln, module="sys", name="WriteLn"),
            ]
        )

        self.context.symbol_table.add(
            sym_table.SystemCall(
                name="OpenInput",
                arguments=[],
                return_type=None,
                syscall=open_input,
            )
        )

        self.context.symbol_table.add(
            sym_table.SystemCall(
                name="ReadInt",
                arguments=[sym_table.Argument(type=ast.IntegerType(), byref=True)],
                return_type=None,
                syscall=read_int,
            )
        )

        self.context.symbol_table.add(
            sym_table.SystemCall(
                name="eot",
                arguments=[],
                return_type=ast.IntegerType(),
                syscall=eot,
            )
        )

        self.context.symbol_table.add(
            sym_table.SystemCall(
                name="WriteChar",
                arguments=[sym_table.Argument(type=ast.IntegerType(), byref=False)],
                return_type=None,
                syscall=write_char,
            )
        )

        self.context.symbol_table.add(
            sym_table.SystemCall(
                name="WriteInt",
                arguments=[
                    sym_table.Argument(type=ast.IntegerType(), byref=False),
                    sym_table.Argument(type=ast.IntegerType(), byref=False),
                ],
                return_type=None,
                syscall=write_int,
            )
        )

        self.context.symbol_table.add(
            sym_table.SystemCall(
                name="WriteLn",
                arguments=[],
                return_type=None,
                syscall=write_ln,
            )
        )

    def add_memory(self):
        m1 = W.BaseMemory(type=W.MemoryType(min_pages=1))
        self.code.imports.append(W.Import(node=m1, module="env", name="memory"))

    def add_stack_pointer(self):
        self.sp = W.BaseGlobal(type=W.GlobalType(type=i32_t, mutable=True))
        self.code.imports.append(
            W.Import(node=self.sp, module="env", name="__stack_pointer")
        )

    def addr_of(self, expr):
        assert isinstance(expr, ast.SimpleExpression)
        assert expr.sign is None
        assert isinstance(expr.term.factor, ast.SimpleFactor)
        assert len(expr.term.mulop_factors) == 0
        assert len(expr.addop_terms) == 0

        sym = self.context.symbol_table.find(expr.term.factor.ident)
        self.context.current_function.body.extend(
            [
                I.GlobalGet(global_=self.sp),
                I.I32Const(value=sym.offset),
                I.I32Sub(),
            ]
        )

    def factor(self, f):
        if isinstance(f, ast.Number):
            self.context.current_function.body.append(I.I32Const(value=f.value))
        elif isinstance(f, ast.SimpleFactor):
            sym = self.context.symbol_table.find(f.ident)
            if sym:
                self.context.current_function.body.extend(
                    [
                        I.GlobalGet(global_=self.sp),
                        I.I32Const(value=sym.offset),
                        I.I32Sub(),
                        I.I32Load(),
                    ]
                )
        elif isinstance(f, ast.FunctionCall):
            raise ValueError("Function calls not yet implemented")
        elif isinstance(f, ast.ExpressionFactor):
            self.expression(f.expression)
        elif isinstance(f, ast.Negation):
            self.factor(f.factor)
            self.context.current_function.body.append(I.I32Neg())
        else:
            raise ValueError(f"Unknown factor: {f}")

    def term(self, t):
        self.factor(t.factor)
        for op, f in t.mulop_factors:
            self.factor(f)
            if op == "*":
                self.context.current_function.body.append(I.I32Mul())
            elif op == "DIV":
                self.context.current_function.body.append(I.I32DivS())
            elif op == "MOD":
                self.context.current_function.body.append(I.I32RemS())
            else:
                raise ValueError(f"Unknown mulop: {op}")

    def simple_expression(self, expr):
        self.term(expr.term)
        if expr.sign == "-":
            self.context.current_function.body.append(I.I32Neg())
        for op, t in expr.addop_terms:
            self.term(t)
            if op == "+":
                self.context.current_function.body.append(I.I32Add())
            elif op == "-":
                self.context.current_function.body.append(I.I32Sub())
            else:
                raise ValueError(f"Unknown addop: {op}")

    def expression(self, expr):
        if isinstance(expr, ast.SimpleExpression):
            self.simple_expression(expr)
        else:
            raise ValueError(f"Unknown expression: {expr}")

    def assignment(self, a):
        sym = self.context.symbol_table.find(a.ident)
        f = self.context.current_function
        f.body.extend(
            [
                I.GlobalGet(global_=self.sp),
                I.I32Const(value=sym.offset),
                I.I32Sub(),
            ]
        )
        self.expression(a.expression)
        f.body.append(I.I32Store())

    def type_size(self, t):
        if isinstance(t, ast.ArrayType):
            return t.size * self.type_size(t.type)
        if isinstance(t, ast.IntegerType):
            return 4
        if isinstance(t, ast.BooleanType):
            return 4
        raise ValueError(f"Unknown type: {t}")

    def system_call(self, p, s):
        assert len(p.params) == len(s.arguments)
        for i, a in enumerate(p.params):
            # TODO: check type
            if s.arguments[i].byref:
                self.addr_of(a)
            else:
                self.expression(a)

        self.context.current_function.body.append(I.Call(function=s.syscall))

    def procedure_call(self, p):
        s = self.context.symbol_table.find(p.ident)
        if s is None:
            raise ValueError(f"Unknown procedure: {p.ident}")
        if isinstance(s, sym_table.SystemCall):
            self.system_call(p, s)

    def procedure(self, p):
        if p.exported and len(p.params) > 0:
            raise ValueError("Exported procedures cannot have parameters")

        f = W.Function(type=W.FunctionType(params=[], results=[]))
        self.context.current_function = f

        for vl in p.declarations.var_declarations:
            ptr = 0
            for v in vl.ident_list:
                self.context.symbol_table.add(
                    sym_table.LocalVariable(
                        name=v,
                        type=vl.type,
                        size=self.type_size(vl.type),
                        offset=ptr,
                    )
                )
                ptr += self.type_size(vl.type)

        # Procedure preamble (make room for local variables)
        f.body.extend(
            [
                I.GlobalGet(global_=self.sp),
                I.I32Const(value=ptr),
                I.I32Sub(),
                I.GlobalSet(global_=self.sp),
            ]
        )

        for s in p.body.statements:
            if isinstance(s, ast.ProcedureCall):
                self.procedure_call(s)
            elif isinstance(s, ast.Assignment):
                self.assignment(s)

        # Procedure postamble (reclaim memory for local variables)
        f.body.extend(
            [
                I.GlobalGet(global_=self.sp),
                I.I32Const(value=ptr),
                I.I32Add(),
                I.GlobalSet(global_=self.sp),
            ]
        )

        f.body.append(I.End())
        self.code.funcs.append(f)
        if p.exported:
            self.code.exports.append(W.Export(node=f, name=p.ident))

    def generate(self, filename):
        assert isinstance(self.ast, ast.Module)
        self.code = W.Module()
        self.add_syscalls()
        self.add_memory()
        self.add_stack_pointer()

        d = self.ast.Declarations
        for p in d.procedure_declarations:
            self.procedure(p)

        with open(filename, "wb") as f:
            f.write(bytes(self.code))
