# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

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
    gen = CodeGenerator(ast=ast)
    gen.generate(dst)
    return dst


def simple_test(name: str):
    with open(Path(__file__).parent / f"mod/{name}.mod") as src:
        dst = compile(src)
    with open(Path(__file__).parent / f"mod/{name}.wasm", "rb") as expected:
        assert dst.getvalue() == expected.read()


def test_add():
    simple_test("add")


def test_mul():
    simple_test("mul")


def test_ops():
    simple_test("ops")


def test_sample():
    simple_test("sample")
