# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

from io import BytesIO, TextIOBase
from pathlib import Path

# from typing import TextIO
from oberon0_compiler.code_gen import CodeGenerator
from oberon0_compiler.parser import Parser
from oberon0_compiler.scanner import Scanner


def compile(src: TextIOBase) -> BytesIO:
    dst = BytesIO()
    scanner = Scanner()
    scanner.open(src)
    parser = Parser(scanner=scanner)
    ast = parser.parse()
    gen = CodeGenerator()
    gen.generate(ast, dst)
    return dst


def simple_test(name: str) -> None:
    with open(Path(__file__).parent / f"mod/{name}.mod") as src:
        dst = compile(src)
    with open(Path(__file__).parent / f"mod/{name}.wasm.expected", "rb") as expected:
        assert dst.getvalue() == expected.read()


def test_add() -> None:
    simple_test("add")


def test_mul() -> None:
    simple_test("mul")


def test_ops() -> None:
    simple_test("ops")


def test_sample() -> None:
    simple_test("sample")
