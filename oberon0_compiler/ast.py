# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 Abstract Syntax Tree
"""


from pydantic import BaseModel


class Node(BaseModel):
    pass

    def __str__(self):
        return ""


class Module(Node):
    ident: str
    Declarations: "Declarations"
    body: "StatementSequence"

    def __str__(self):
        decl = str(self.Declarations)
        body = str(self.body)
        res = f"MODULE {self.ident};"
        if decl:
            res += "\n" + decl
        if body:
            res += "\nBEGIN\n" + body
        return res + f"\nEND {self.ident}."


class Declarations(Node):
    const_declarations: list["ConstantDeclaration"]
    type_declarations: list["TypeDeclaration"]
    var_declarations: list["VariableDeclaration"]
    procedure_declarations: list["ProcedureDeclaration"]

    def __str__(self):
        c = "\n".join(str(d) for d in self.const_declarations)
        t = "\n".join(str(d) for d in self.type_declarations)
        v = "\n".join(str(d) for d in self.var_declarations)
        p = "\n".join(str(d) for d in self.procedure_declarations)
        return "\n".join([i for i in [c, t, v, p] if i])


class ConstantDeclaration(Node):
    ident: str
    expression: "Expression"

    def __str__(self):
        return f"CONST {self.ident} = {self.expression}"


class TypeDeclaration(Node):
    ident: str
    type: "Type"

    def __str__(self):
        return f"TYPE {self.ident} = {self.type}"


class VariableDeclaration(Node):
    ident_list: list[str]
    type: "Type"

    def __str__(self):
        return f"VAR {', '.join(self.ident_list)}: {self.type};"


class ProcedureDeclaration(Node):
    ident: str
    exported: bool
    params: list["FormalParameter"]
    declarations: "Declarations"
    body: "StatementSequence"

    def __str__(self):
        e = "*" if self.exported else ""
        fp = f"({', '.join(str(p) for p in self.params)})" if self.params else ""
        decl = str(self.declarations)
        body = str(self.body)

        res = f"PROCEDURE {self.ident}{e}{fp};"
        if decl:
            res += "\n" + decl
        if body:
            res += "\nBEGIN\n" + body
        return res + f"\nEND {self.ident}"


class FormalParameter(Node):
    by_ref: bool
    ident_list: list[str]
    type: "Type"

    def __str__(self):
        return f"{', '.join(self.ident_list)}: {self.type}"


class Type(Node):
    pass


class IntegerType(Type):
    pass

    def __str__(self):
        return "INTEGER"


class BooleanType(Type):
    pass

    def __str__(self):
        return "BOOLEAN"


class CustomType(Type):
    ident: str

    def __str__(self):
        return self.ident


class ArrayType(Type):
    size: "Expression"
    type: "Type"

    def __str__(self):
        return f"ARRAY {self.size} OF {self.type}"


class StatementSequence(Node):
    statements: list["Statement"]

    def __str__(self):
        return ";\n".join([str(s) for s in self.statements if type(s) is not Statement])


class Statement(Node):
    pass

    def __str__(self):
        return "<EMPTY>"


class Assignment(Statement):
    ident: str
    selector: list["IndexSelector"]
    expression: "Expression"

    def __str__(self):
        lhs = f"{self.ident}{"".join([str(i) for i in self.selector])}"
        rhs = f"{self.expression}"
        return f"{lhs} := {rhs}"


class ProcedureCall(Statement):
    ident: str
    params: list["Expression"]

    def __str__(self):
        return f"{self.ident}({', '.join(str(p) for p in self.params)})"


class If(Statement):
    condition: "Expression"
    then: "StatementSequence"
    elsif: list[tuple["Expression", "StatementSequence"]] | None
    else_: StatementSequence | None

    def __str__(self):
        res = f"IF {self.condition} THEN\n{self.then}"
        if len(self.elsif) > 0:
            res += "\n".join(f"ELSIF {c} THEN\n{s}" for c, s in self.elsif)
        if self.else_:
            res += "ELSE\n" + str(self.else_)
        return res + "\nEND"


class While(Statement):
    condition: "Expression"
    body: "StatementSequence"

    def __str__(self):
        return f"WHILE {self.condition} DO\n{self.body}\nEND"


class Repeat(Statement):
    body: "StatementSequence"
    condition: "Expression"

    def __str__(self):
        return f"REPEAT\n{self.body}\nUNTIL {self.condition}"


class Expression(Node):
    pass

    def __str__(self):
        return ""


class ComplexExpression(Expression):
    simple_expression: "SimpleExpression"
    relation: tuple[str, "SimpleExpression"] | None

    def __str__(self):
        return (
            f"{self.simple_expression} {self.relation[0]} {self.relation[1]}"
            if self.relation
            else str(self.simple_expression)
        )


class SimpleExpression(Expression):
    sign: str | None
    term: "Term"
    addop_terms: list[tuple[str, "Term"]]

    def __str__(self):
        addop = "".join(f" {op} {t}" for op, t in self.addop_terms)
        return f"{self.sign or ''}{self.term}{addop}"


class Term(Node):
    factor: "Factor"
    mulop_factors: list[tuple[str, "Factor"]]

    def __str__(self):
        mulop = "".join(f" {op} {f}" for op, f in self.mulop_factors)
        return f"{self.factor}{mulop}"


class Factor(Node):
    pass


class FunctionCall(Factor):
    ident: str
    params: list["Expression"]

    def __str__(self):
        return f"{self.ident}({', '.join(str(p) for p in self.params)})"


class SimpleFactor(Factor):
    ident: str
    selector: list["IndexSelector"]

    def __str__(self):
        return self.ident + "".join(str(s) for s in self.selector)


class Number(Factor):
    value: int

    def __str__(self):
        return str(self.value)


class ExpressionFactor(Factor):
    expression: "Expression"

    def __str__(self):
        return f"({self.expression})"


class Negation(Factor):
    factor: "Factor"

    def __str__(self):
        return f"~{self.factor}"


class IndexSelector(Node):
    expression: "Expression"

    def __str__(self):
        return f"[{self.expression}]"
