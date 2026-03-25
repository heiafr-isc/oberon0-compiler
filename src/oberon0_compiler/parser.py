# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-0 parser
"""

import typing
from dataclasses import dataclass, field

import wasm_gen as W  # noqa
from loguru import logger

from . import ast, systemcalls, types
from . import sym_table as SYM
from .scanner import Position, Scanner
from .token import Token


class ParserError(Exception):
    def __init__(self, message: str, position: Position) -> None:
        super().__init__(message)
        self.position = position

    def __str__(self) -> str:
        p = self.position
        return (
            f"{self.args[0]} (File {p.file_name}, Line {p.line_no}, Column {p.col_no})"
        )


def eval_const(expr: ast.Node) -> int:
    if isinstance(expr, ast.Number):
        return expr.value
    elif isinstance(expr, ast.ConstantDeclaration):
        return expr.symbol.value
    elif isinstance(expr, ast.SimpleExpression):
        x: int = eval_const(expr.term)
        for op, t in expr.addop_terms:
            y: int = eval_const(t)
            if op == "+":
                x += y
            elif op == "-":
                x -= y
            else:
                raise ParserError(
                    f"Invalid operator '{op}' in constant expression",
                    expr.position,
                )
        if expr.sign == "-":
            x = -x
        return x
    elif isinstance(expr, ast.Term):
        x = eval_const(expr.factor)
        for op, f in expr.mulop_factors:
            y = eval_const(f)
            if op == "*":
                x *= y
            elif op == "DIV":
                x //= y
            elif op == "MOD":
                x %= y
            else:
                raise ParserError(
                    f"Invalid operator '{op}' in constant expression", expr.position
                )
        return x
    elif isinstance(expr, ast.Ident):
        if isinstance(expr.symbol, SYM.Constant):
            return expr.symbol.value
        else:
            raise ParserError(
                f"Expected constant, but got '{expr.symbol}'", expr.position
            )

    else:
        raise ParserError(f"{type(expr)} Not yet implemented", expr.position)


@dataclass
class Parser:

    scanner: Scanner
    sym_table: SYM.SymbolTable = field(default_factory=SYM.SymbolTable)

    @typing.no_type_check
    def check_sym(self, expected: Token):
        if self.scanner.sym != expected:
            raise ParserError(
                f"Expected '{expected}', but got '{self.scanner.sym}'",
                self.scanner.position(),
            )

    def factor(self) -> ast.Factor:
        logger.debug("parsing factor")
        if self.scanner.sym == Token.IDENT:
            ident = self.scanner.value
            sym = self.sym_table.get(ident)

            self.scanner.get_next_symbol()
            next_sym = typing.cast(Token | None, self.scanner.sym)
            if next_sym == Token.LPAREN:
                self.scanner.get_next_symbol()
                params = []
                param_sym = typing.cast(Token | None, self.scanner.sym)
                if param_sym != Token.RPAREN:
                    params.append(self.expression())
                    while typing.cast(Token | None, self.scanner.sym) == Token.COMMA:
                        self.scanner.get_next_symbol()
                        params.append(self.expression())
                self.check_sym(Token.RPAREN)
                self.scanner.get_next_symbol()
                return ast.FunctionCall(
                    position=self.scanner.position(), symbol=sym, params=params
                )
            assert isinstance(sym, SYM.Variable) or isinstance(sym, SYM.Constant)
            return ast.Ident(position=self.scanner.position(), symbol=sym)
        elif self.scanner.sym == Token.NUMBER:
            value = self.scanner.value
            self.scanner.get_next_symbol()
            return ast.Number(position=self.scanner.position(), value=int(value))
        elif self.scanner.sym == Token.LPAREN:
            self.scanner.get_next_symbol()
            e = self.expression()
            self.check_sym(Token.RPAREN)
            self.scanner.get_next_symbol()
            return ast.ExpressionFactor(position=self.scanner.position(), expression=e)
        elif self.scanner.sym == Token.NOT:
            self.scanner.get_next_symbol()
            return ast.Negation(position=self.scanner.position(), factor=self.factor())
        else:
            raise ParserError(
                f"Expected factor, but got '{self.scanner.sym}'",
                self.scanner.position(),
            )
            return ast.Factor(position=self.scanner.position())

    def term(self) -> ast.Term:
        logger.debug("parsing term")
        f = self.factor()
        m = []
        while self.scanner.sym in [Token.TIMES, Token.DIV, Token.MOD, Token.AND]:
            op = self.scanner.value
            self.scanner.get_next_symbol()
            m.append((op, self.factor()))
        return ast.Term(position=self.scanner.position(), factor=f, mulop_factors=m)

    def expression(self) -> ast.Expression:
        logger.debug("parsing expression")

        def simple_expression() -> ast.SimpleExpression:
            logger.debug("parsing simple_expression")
            sign = None
            if self.scanner.sym in {Token.PLUS, Token.MINUS}:
                sign = self.scanner.value
                self.scanner.get_next_symbol()
            t = self.term()
            a = []
            while self.scanner.sym in [Token.PLUS, Token.MINUS, Token.OR]:
                op = self.scanner.value
                self.scanner.get_next_symbol()
                a.append((op, self.term()))
            return ast.SimpleExpression(
                position=self.scanner.position(), sign=sign, term=t, addop_terms=a
            )

        e: ast.Expression = simple_expression()

        assert isinstance(e, ast.SimpleExpression)

        if self.scanner.sym in [
            Token.EQL,
            Token.NEQ,
            Token.LSS,
            Token.LEQ,
            Token.GTR,
            Token.GEQ,
        ]:
            op = self.scanner.value
            self.scanner.get_next_symbol()
            e = ast.ComplexExpression(
                position=self.scanner.position(),
                simple_expression=e,
                relation=(op, simple_expression()),
            )
        return e

    def statement_sequence(self) -> ast.StatementSequence:
        logger.debug("parsing statement_sequence")
        s = [self.statement()]
        while self.scanner.sym == Token.SEMICOLON:
            self.scanner.get_next_symbol()
            s.append(self.statement())
        return ast.StatementSequence(position=self.scanner.position(), statements=s)

    def statement(self) -> ast.Statement:  # noqa: C901 PLR0915
        logger.debug("parsing statement")

        def assignment_or_procedure_call() -> ast.Statement:
            logger.debug("parsing assignment_or_procedure_call")
            ident = self.scanner.value
            sym = self.sym_table.get(ident)
            self.scanner.get_next_symbol()
            if self.scanner.sym == Token.BECOMES:
                self.scanner.get_next_symbol()
                return ast.Assignment(
                    position=self.scanner.position(),
                    symbol=sym,
                    expression=self.expression(),
                )
            else:
                params = []
                if self.scanner.sym == Token.LPAREN:
                    self.scanner.get_next_symbol()
                    next_sym = typing.cast(Token | None, self.scanner.sym)
                    if next_sym != Token.RPAREN:
                        params.append(self.expression())
                        while (
                            typing.cast(Token | None, self.scanner.sym) == Token.COMMA
                        ):
                            self.scanner.get_next_symbol()
                            params.append(self.expression())
                    self.check_sym(Token.RPAREN)
                    self.scanner.get_next_symbol()
                return ast.ProcedureCall(
                    position=self.scanner.position(),
                    symbol=sym,
                    params=params,
                )

        def if_statement() -> ast.If:
            logger.debug("parsing if_statement")
            self.scanner.get_next_symbol()
            condition = self.expression()
            self.check_sym(Token.THEN)
            self.scanner.get_next_symbol()
            then = self.statement_sequence()
            elsif = []
            else_ = None
            while self.scanner.sym == Token.ELSIF:
                self.scanner.get_next_symbol()
                e = self.expression()
                self.check_sym(Token.THEN)
                self.scanner.get_next_symbol()
                s = self.statement_sequence()
                elsif.append((e, s))
            if self.scanner.sym == Token.ELSE:
                self.scanner.get_next_symbol()
                else_ = self.statement_sequence()
            self.check_sym(Token.END)
            self.scanner.get_next_symbol()
            return ast.If(
                position=self.scanner.position(),
                condition=condition,
                then=then,
                elsif=elsif,
                else_=else_,
            )

        def while_statement() -> ast.While:
            logger.debug("parsing while_statement")
            self.scanner.get_next_symbol()
            condition = self.expression()
            self.check_sym(Token.DO)
            self.scanner.get_next_symbol()
            body = self.statement_sequence()
            self.check_sym(Token.END)
            self.scanner.get_next_symbol()
            return ast.While(
                position=self.scanner.position(), condition=condition, body=body
            )

        def repeat_statement() -> ast.Repeat:
            logger.debug("parsing repeat_statement")
            self.scanner.get_next_symbol()
            body = self.statement_sequence()
            self.check_sym(Token.UNTIL)
            self.scanner.get_next_symbol()
            condition = self.expression()
            return ast.Repeat(
                position=self.scanner.position(), body=body, condition=condition
            )

        if self.scanner.sym == Token.IDENT:
            return assignment_or_procedure_call()
        elif self.scanner.sym == Token.IF:
            return if_statement()
        elif self.scanner.sym == Token.WHILE:
            return while_statement()
        elif self.scanner.sym == Token.REPEAT:
            return repeat_statement()
        else:  # Empty statement
            return ast.EmptyStatement(position=self.scanner.position())

    def ident_list(self) -> list[str]:
        logger.debug("parsing ident_list")
        self.check_sym(Token.IDENT)
        idents = [self.scanner.value]
        self.scanner.get_next_symbol()
        while self.scanner.sym == Token.COMMA:
            self.scanner.get_next_symbol()
            self.check_sym(Token.IDENT)
            idents.append(self.scanner.value)
            self.scanner.get_next_symbol()
        return idents

    def type_(self) -> ast.Type:
        logger.debug("parsing type")
        if self.scanner.sym == Token.IDENT:
            ident = self.sym_table.get(self.scanner.value)
            self.scanner.get_next_symbol()
            return ast.NamedType(position=self.scanner.position(), ident=ident)
        else:
            raise ParserError(
                f"Expected type, but got '{self.scanner.sym}'", self.scanner.position()
            )
            return ast.Type(position=self.scanner.position())

    def declarations(
        self, global_: bool = False
    ) -> ast.Declarations:  # noqa: C901 PLR0915
        logger.debug("parsing declarations")

        def const_declaration() -> list[ast.ConstantDeclaration]:
            logger.debug("parsing const_declaration")
            c: list[ast.ConstantDeclaration] = []
            if self.scanner.sym == Token.CONST:
                self.scanner.get_next_symbol()
                while typing.cast(Token | None, self.scanner.sym) == Token.IDENT:
                    ident = self.scanner.value
                    self.scanner.get_next_symbol()
                    self.check_sym(Token.EQL)
                    self.scanner.get_next_symbol()
                    sym = SYM.Constant(
                        name=ident,
                        type_=types.integer,
                        value=eval_const(self.expression()),
                    )
                    self.sym_table.add(sym)
                    c.append(
                        ast.ConstantDeclaration(
                            position=self.scanner.position(), symbol=sym
                        ),
                    )
                    self.check_sym(Token.SEMICOLON)
                    self.scanner.get_next_symbol()
            return c

        def var_declaration() -> list[ast.VariableDeclaration]:
            logger.debug("parsing var_declaration")
            v: list[ast.VariableDeclaration] = []
            offset = 0
            if self.scanner.sym == Token.VAR:
                self.scanner.get_next_symbol()
                while typing.cast(Token | None, self.scanner.sym) == Token.IDENT:
                    idents = self.ident_list()
                    self.check_sym(Token.COLON)
                    self.scanner.get_next_symbol()
                    type_ = self.sym_table.type_(self.scanner.value)
                    self.scanner.get_next_symbol()
                    for i in idents:
                        sym: SYM.Variable
                        if global_:
                            sym = SYM.GlobalVariable(name=i, offset=offset, type_=type_)
                        else:
                            sym = SYM.LocalVariable(name=i, offset=offset, type_=type_)
                        self.sym_table.add(sym)
                        offset += type_.size
                        v.append(
                            ast.VariableDeclaration(
                                position=self.scanner.position(),
                                symbol=sym,
                            )
                        )
                    self.check_sym(Token.SEMICOLON)
                    self.scanner.get_next_symbol()
            return v

        def procedure_declaration() -> list[ast.ProcedureDeclaration]:
            logger.debug("parsing procedure_declaration")

            def fp_section() -> list[SYM.FormalParameter]:
                by_ref = False
                if self.scanner.sym == Token.VAR:
                    by_ref = True
                    self.scanner.get_next_symbol()
                fp_idents = self.ident_list()
                self.check_sym(Token.COLON)
                self.scanner.get_next_symbol()
                type_ = self.sym_table.type_(self.scanner.value)
                res = []
                for index, i in enumerate(fp_idents):
                    sym = SYM.FormalParameter(
                        name=i, type_=type_, index=index, by_ref=by_ref
                    )
                    self.sym_table.add(sym)
                    res.append(sym)

                return res

            def procedure_heading() -> tuple[str, bool, list[SYM.FormalParameter]]:
                logger.debug("parsing procedure_heading")
                self.scanner.get_next_symbol()
                self.check_sym(Token.IDENT)
                ident = self.scanner.value
                self.scanner.get_next_symbol()
                exported = False
                if self.scanner.sym == Token.TIMES:
                    exported = True
                    self.scanner.get_next_symbol()
                params: list[SYM.FormalParameter] = []
                if self.scanner.sym == Token.LPAREN:
                    self.scanner.get_next_symbol()

                    while typing.cast(Token | None, self.scanner.sym) != Token.RPAREN:
                        params.extend(fp_section())
                        while (
                            typing.cast(Token | None, self.scanner.sym)
                            == Token.SEMICOLON
                        ):
                            self.scanner.get_next_symbol()
                            params.extend(fp_section())

                    self.scanner.get_next_symbol()
                return (ident, exported, params)

            def procedure_body() -> tuple[ast.Declarations, ast.StatementSequence, str]:
                logger.debug("parsing procedure_body")
                d = self.declarations()
                self.check_sym(Token.BEGIN)
                self.scanner.get_next_symbol()
                if self.scanner.sym != Token.END:
                    st_seq = self.statement_sequence()
                else:
                    st_seq = ast.StatementSequence(
                        position=self.scanner.position(), statements=[]
                    )
                self.check_sym(Token.END)
                self.scanner.get_next_symbol()
                self.check_sym(Token.IDENT)
                ident = self.scanner.value
                self.scanner.get_next_symbol()
                self.check_sym(Token.SEMICOLON)
                self.scanner.get_next_symbol()
                return (d, st_seq, ident)

            p = []
            while self.scanner.sym == Token.PROCEDURE:
                self.sym_table.new_scope()
                ident, exported, params = procedure_heading()
                self.check_sym(Token.SEMICOLON)
                self.scanner.get_next_symbol()
                decl, body, end_ident = procedure_body()
                if ident != end_ident:
                    raise ParserError(
                        f"Expected '{ident}', but got '{end_ident}'",
                        self.scanner.position(),
                    )
                # Compute stack size for local variables
                stack_size = sum(
                    i.type_.size
                    for i in self.sym_table.current_scope().symbols.values()
                    if isinstance(i, SYM.LocalVariable)
                )
                self.sym_table.close_scope()
                sym = SYM.ProcedureDefinition(
                    name=ident, exported=exported, stack_size=stack_size, params=params
                )
                self.sym_table.add(sym)

                p.append(
                    ast.ProcedureDeclaration(
                        position=self.scanner.position(),
                        symbol=sym,
                        exported=exported,
                        declarations=decl,
                        body=body,
                    )
                )
            return p

        d = ast.Declarations(
            position=self.scanner.position(),
            const_declarations=const_declaration(),
            var_declarations=var_declaration(),
            procedure_declarations=procedure_declaration(),
        )
        return d

    def add_types(self) -> None:
        self.sym_table.add(types.integer)
        self.sym_table.add(types.boolean)

    def add_system_calls(self) -> None:
        self.sym_table.add(systemcalls.OpenInput)
        self.sym_table.add(systemcalls.ReadInt)
        self.sym_table.add(systemcalls.eot)
        self.sym_table.add(systemcalls.WriteChar)
        self.sym_table.add(systemcalls.WriteInt)
        self.sym_table.add(systemcalls.WriteLn)

    def module(self) -> ast.Module:
        logger.debug("parsing module")
        self.check_sym(Token.MODULE)
        self.scanner.get_next_symbol()
        self.check_sym(Token.IDENT)
        name = self.scanner.value
        self.scanner.get_next_symbol()
        self.check_sym(Token.SEMICOLON)
        self.scanner.get_next_symbol()
        self.sym_table.new_scope()

        self.add_types()
        self.add_system_calls()

        d = self.declarations(global_=True)
        if self.scanner.sym == Token.BEGIN:
            self.scanner.get_next_symbol()
            b = self.statement_sequence()
        else:
            b = ast.StatementSequence(position=self.scanner.position(), statements=[])
        self.check_sym(Token.END)
        self.scanner.get_next_symbol()
        self.check_sym(Token.IDENT)
        self.sym_table.close_scope()

        if self.scanner.value != name:
            raise ParserError(
                f"Expected '{name}', but got '{self.scanner.value}'",
                self.scanner.position(),
            )

        self.scanner.get_next_symbol()
        self.check_sym(Token.PERIOD)
        self.scanner.get_next_symbol()
        self.check_sym(Token.EOF)

        return ast.Module(
            position=self.scanner.position(), ident=name, declarations=d, body=b
        )

    def parse(self) -> ast.Module:
        logger.debug("Parsing")
        ast.actual_scanner = self.scanner
        self.scanner.get_next_symbol()
        return self.module()
