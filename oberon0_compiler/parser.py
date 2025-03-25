# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 parser
"""

import typing

from loguru import logger
from pydantic import BaseModel

from oberon0_compiler import ast
from oberon0_compiler.scanner import Scanner
from oberon0_compiler.token import Token


class Parser(BaseModel):

    scanner: Scanner
    has_error: bool = False

    def raise_error(self, msg: str) -> None:
        self.has_error = True
        self.scanner.raise_error(msg)

    @typing.no_type_check
    def check_sym(self, expected: Token):
        if self.scanner.sym != expected:
            self.raise_error(f"Expected '{expected}', but got '{self.scanner.sym}'")

    def index_selector(self) -> list["ast.IndexSelector"]:
        logger.debug("parsing index_selector")
        s = []
        while self.scanner.sym == Token.LBRACK:
            self.scanner.get_next_symbol()
            s.append(ast.IndexSelector(expression=self.expression()))
            self.check_sym(Token.RBRACK)
            self.scanner.get_next_symbol()
        return s

    def factor(self) -> "ast.Factor":
        logger.debug("parsing factor")
        if self.scanner.sym == Token.IDENT:
            ident = self.scanner.value
            self.scanner.get_next_symbol()
            if self.scanner.sym == Token.LPAREN:
                self.scanner.get_next_symbol()
                params = []
                if self.scanner.sym != Token.RPAREN:
                    params.append(self.expression())
                    while self.scanner.sym == Token.COMMA:
                        self.scanner.get_next_symbol()
                        params.append(self.expression())
                self.check_sym(Token.RPAREN)
                self.scanner.get_next_symbol()
                return ast.FunctionCall(ident=ident, params=params)
            if self.scanner.sym in {Token.PERIOD, Token.LBRACK}:
                selector = self.index_selector()
            else:
                selector = []
            return ast.SimpleFactor(ident=ident, selector=selector)
        elif self.scanner.sym == Token.NUMBER:
            value = self.scanner.value
            self.scanner.get_next_symbol()
            return ast.Number(value=int(value))
        elif self.scanner.sym == Token.LPAREN:
            self.scanner.get_next_symbol()
            e = self.expression()
            self.check_sym(Token.RPAREN)
            self.scanner.get_next_symbol()
            return ast.ExpressionFactor(expression=e)
        elif self.scanner.sym == Token.NOT:
            self.scanner.get_next_symbol()
            return ast.Negation(factor=self.factor())
        else:
            self.raise_error(f"Expected factor, but got '{self.scanner.sym}'")
            return ast.Factor()

    def term(self) -> "ast.Term":
        logger.debug("parsing term")
        f = self.factor()
        m = []
        while self.scanner.sym in [Token.TIMES, Token.DIV, Token.MOD, Token.AND]:
            op = self.scanner.value
            self.scanner.get_next_symbol()
            m.append((op, self.factor()))
        return ast.Term(factor=f, mulop_factors=m)

    def expression(self) -> "ast.Expression":
        logger.debug("parsing expression")

        def simple_expression():
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
            return ast.SimpleExpression(sign=sign, term=t, addop_terms=a)

        e = simple_expression()

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
                simple_expression=e, relation=(op, simple_expression())
            )
        return e

    def statement_sequence(self) -> "ast.StatementSequence":
        logger.debug("parsing statement_sequence")
        s = [self.statement()]
        while self.scanner.sym == Token.SEMICOLON:
            self.scanner.get_next_symbol()
            s.append(self.statement())
        return ast.StatementSequence(statements=s)

    def statement(self) -> "ast.Statement":  # noqa: C901 PLR0915
        logger.debug("parsing statement")

        def assignment_or_procedure_call():
            logger.debug("parsing assignment_or_procedure_call")
            ident = self.scanner.value
            self.scanner.get_next_symbol()
            if self.scanner.sym in [Token.PERIOD, Token.LBRACK]:
                selector = self.index_selector()
            else:
                selector = []
            if self.scanner.sym == Token.BECOMES:
                self.scanner.get_next_symbol()
                return ast.Assignment(
                    ident=ident, selector=selector, expression=self.expression()
                )
            else:
                params = []
                if self.scanner.sym == Token.LPAREN:
                    self.scanner.get_next_symbol()
                    if self.scanner.sym != Token.RPAREN:
                        params.append(self.expression())
                        while self.scanner.sym == Token.COMMA:
                            self.scanner.get_next_symbol()
                            params.append(self.expression())
                    self.check_sym(Token.RPAREN)
                    self.scanner.get_next_symbol()
                return ast.ProcedureCall(ident=ident, selector=selector, params=params)

        def if_statement():
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
            return ast.If(condition=condition, then=then, elsif=elsif, else_=else_)

        def while_statement():
            logger.debug("parsing while_statement")
            self.scanner.get_next_symbol()
            condition = self.expression()
            self.check_sym(Token.DO)
            self.scanner.get_next_symbol()
            body = self.statement_sequence()
            self.check_sym(Token.END)
            self.scanner.get_next_symbol()
            return ast.While(condition=condition, body=body)

        def repeat_statement():
            logger.debug("parsing repeat_statement")
            self.scanner.get_next_symbol()
            body = self.statement_sequence()
            self.check_sym(Token.UNTIL)
            self.scanner.get_next_symbol()
            condition = self.expression()
            return ast.Repeat(body=body, condition=condition)

        if self.scanner.sym == Token.IDENT:
            return assignment_or_procedure_call()
        elif self.scanner.sym == Token.IF:
            return if_statement()
        elif self.scanner.sym == Token.WHILE:
            return while_statement()
        elif self.scanner.sym == Token.REPEAT:
            return repeat_statement()
        else:  # Empty statement
            return ast.EmptyStatement()

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

    def type_(self) -> "ast.Type":
        logger.debug("parsing type")
        if self.scanner.sym == Token.IDENT:
            ident = self.scanner.value
            self.scanner.get_next_symbol()
            if ident == "INTEGER":
                return ast.Type(ident="INTEGER")
            elif ident == "BOOLEAN":
                return ast.Type(ident="BOOLEAN")
            return ast.Type(ident=ident)
        elif self.scanner.sym == Token.ARRAY:
            self.scanner.get_next_symbol()
            expr = self.expression()
            self.check_sym(Token.OF)
            self.scanner.get_next_symbol()
            t = self.type_()
            return ast.ArrayType(size=expr, type=t)
        else:
            self.raise_error(f"Expected type, but got '{self.scanner.sym}'")
            return ast.Type()

    def declarations(self) -> "ast.Declarations":  # noqa: C901 PLR0915
        logger.debug("parsing declarations")

        def const_declaration():
            logger.debug("parsing const_declaration")
            c = []
            if self.scanner.sym == Token.CONST:
                self.scanner.get_next_symbol()
                while self.scanner.sym == Token.IDENT:
                    ident = self.scanner.value
                    self.scanner.get_next_symbol()
                    self.check_sym(Token.EQL)
                    self.scanner.get_next_symbol()
                    c.append(
                        ast.ConstantDeclaration(
                            ident=ident, expression=self.expression()
                        )
                    )
                    self.check_sym(Token.SEMICOLON)
                    self.scanner.get_next_symbol()
            return c

        def type_declaration():
            logger.debug("parsing type_declaration")
            t = []
            if self.scanner.sym == Token.TYPE:
                self.scanner.get_next_symbol()
                while self.scanner.sym == Token.IDENT:
                    ident = self.scanner.value
                    self.scanner.get_next_symbol()
                    self.check_sym(Token.EQ)
                    self.scanner.get_next_symbol()
                    t.append(ast.TypeDeclaration(ident=ident, type=self.type_()))
                    self.check_sym(Token.SEMICOLON)
                    self.scanner.get_next_symbol()
            return t

        def var_declaration():
            logger.debug("parsing var_declaration")
            v = []
            if self.scanner.sym == Token.VAR:
                self.scanner.get_next_symbol()
                while self.scanner.sym == Token.IDENT:
                    idents = self.ident_list()
                    self.check_sym(Token.COLON)
                    self.scanner.get_next_symbol()
                    v.append(
                        ast.VariableDeclaration(ident_list=idents, type=self.type_())
                    )
                    self.check_sym(Token.SEMICOLON)
                    self.scanner.get_next_symbol()
            return v

        def procedure_declaration():
            logger.debug("parsing procedure_declaration")

            def procedure_heading():
                logger.debug("parsing procedure_heading")
                self.scanner.get_next_symbol()
                self.check_sym(Token.IDENT)
                ident = self.scanner.value
                self.scanner.get_next_symbol()
                exported = False
                if self.scanner.sym == Token.TIMES:
                    exported = True
                    self.scanner.get_next_symbol()
                params = []
                if self.scanner.sym == Token.LPAREN:
                    self.scanner.get_next_symbol()
                    while self.scanner.sym != Token.RPAREN:
                        by_ref = False
                        if self.scanner.sym == Token.VAR:
                            by_ref = True
                            self.scanner.get_next_symbol()
                        fp_idents = self.ident_list()
                        self.check_sym(Token.COLON)
                        self.scanner.get_next_symbol()
                        params.append(
                            ast.FormalParameter(
                                by_ref=by_ref, ident_list=fp_idents, type=self.type_()
                            )
                        )
                    self.scanner.get_next_symbol()
                return (ident, exported, params)

            def procedure_body():
                logger.debug("parsing procedure_body")
                d = self.declarations()
                self.check_sym(Token.BEGIN)
                self.scanner.get_next_symbol()
                if self.scanner.sym != Token.END:
                    st_seq = self.statement_sequence()
                else:
                    st_seq = ast.StatementSequence(statements=[])
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
                ident, exported, params = procedure_heading()
                self.check_sym(Token.SEMICOLON)
                self.scanner.get_next_symbol()
                decl, body, end_ident = procedure_body()
                if ident != end_ident:
                    self.error(f"Expected '{ident}', but got '{end_ident}'")

                p.append(
                    ast.ProcedureDeclaration(
                        ident=ident,
                        exported=exported,
                        params=params,
                        declarations=decl,
                        body=body,
                    )
                )
            return p

        d = ast.Declarations(
            const_declarations=const_declaration(),
            type_declarations=type_declaration(),
            var_declarations=var_declaration(),
            procedure_declarations=procedure_declaration(),
        )
        return d

    def module(self) -> "ast.Module":
        logger.debug("parsing module")
        self.check_sym(Token.MODULE)
        self.scanner.get_next_symbol()
        self.check_sym(Token.IDENT)
        name = self.scanner.value
        self.scanner.get_next_symbol()
        self.check_sym(Token.SEMICOLON)
        self.scanner.get_next_symbol()
        d = self.declarations()
        if self.scanner.sym == Token.BEGIN:
            self.scanner.get_next_symbol()
            b = self.statement_sequence()
        else:
            b = ast.StatementSequence(statements=[])
        self.check_sym(Token.END)
        self.scanner.get_next_symbol()
        self.check_sym(Token.IDENT)

        if self.scanner.value != name:
            self.raise_error(f"Expected '{name}', but got '{self.scanner.value}'")

        self.scanner.get_next_symbol()
        self.check_sym(Token.PERIOD)
        self.scanner.get_next_symbol()
        self.check_sym(Token.EOF)

        return ast.Module(ident=name, Declarations=d, body=b)

    def parse(self):
        logger.debug("Parsing")
        ast.actual_scanner = self.scanner
        self.scanner.get_next_symbol()
        return self.module()
