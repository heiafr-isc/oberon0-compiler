# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 compiler
"""

import sys
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

from oberon0_compiler import ast
from oberon0_compiler.code_gen import CodeGenerator
from oberon0_compiler.parser import Parser
from oberon0_compiler.scanner import Scanner
from oberon0_compiler.token import Token

__all__ = ["Parser", "Scanner", "Token", "ast"]

console = Console()
app = typer.Typer()


@app.command(context_settings={"ignore_unknown_options": False})
def main(  # noqa: PLR0913
    source: Annotated[Path, typer.Argument(help="Oberon-0 source file (.mod)")],
    destination: Annotated[Path | None, typer.Argument(help="WASM object file")] = None,
    debug: bool = False,
    debug_scanner: bool = False,
    debug_parser: bool = False,
    debug_code_gen: bool = False,
    show_tree: bool = False,
):
    """
    Oberon-0 compiler
    """

    logger.remove()

    level_per_module = {"": "INFO"}

    if debug:
        level_per_module[""] = "DEBUG"
    if debug_scanner:
        level_per_module["oberon0_compiler.scanner"] = "DEBUG"
    if debug_parser:
        level_per_module["oberon0_compiler.parser"] = "DEBUG"
    if debug_code_gen:
        level_per_module["oberon0_compiler.code_gen"] = "DEBUG"

    logger.add(sys.stdout, filter=level_per_module, level=0)

    try:
        f = open(source)
    except FileNotFoundError:
        print(f"File {source} not found")
        typer.Exit(code=1)

    scanner = Scanner()
    scanner.open(f)
    parser = Parser(scanner=scanner)

    try:
        ast = parser.parse()
    except SyntaxError as e:
        print(f"{e.msg} (File {e.filename}, Line {e.lineno}, Column {e.offset})")

    if parser.has_error:
        print("Syntax errors. aborting")
        raise typer.Exit(code=1)

    if show_tree:
        console.print(Panel(Pretty(ast, indent_size=2), title="Syntax Tree"))

    gen = CodeGenerator(ast=ast)

    if destination is None:
        destination = Path(source.name).stem + ".wasm"
    with open(destination, "wb") as f:
        gen.generate(f)


if __name__ == "__main__":
    app()
