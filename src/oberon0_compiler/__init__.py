# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 compiler
"""

import sys
from pathlib import Path
from typing import Annotated, TypeAlias

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

from .code_gen import CodeGenerator
from .parser import Parser
from .scanner import Scanner

console = Console()
app = typer.Typer()


FilterDict: TypeAlias = dict[str | None, str | int | bool]


__version__ = "0.1.0"


def version_callback(value: bool) -> None:
    if value:
        print(f"Oberon0 compiler version: {__version__}")
        raise typer.Exit()


@app.command(context_settings={"ignore_unknown_options": False})
def main(  # noqa: PLR0913
    source: Annotated[
        typer.FileText, typer.Argument(help="Oberon-0 source file (.mod)")
    ],
    destination: Annotated[typer.FileBinaryWrite | None, typer.Argument()] = None,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
    debug: bool = False,
    debug_scanner: bool = False,
    debug_parser: bool = False,
    debug_code_gen: bool = False,
    show_tree: bool = False,
) -> None:
    "Oberon-0 compiler"

    logger.remove()

    level_per_module: FilterDict = {"": "INFO"}

    if debug:
        level_per_module[""] = "DEBUG"
    if debug_scanner:
        level_per_module["oberon0_compiler.scanner"] = "DEBUG"
    if debug_parser:
        level_per_module["oberon0_compiler.parser"] = "DEBUG"
    if debug_code_gen:
        level_per_module["oberon0_compiler.code_gen"] = "DEBUG"

    logger.add(sys.stdout, filter=level_per_module, level=0)

    scanner = Scanner()
    scanner.open(source)
    parser = Parser(scanner=scanner)

    ast_ = None
    try:
        ast_ = parser.parse()
    except SyntaxError as e:
        print(f"{e.msg} (File {e.filename}, Line {e.lineno}, Column {e.offset})")

    if parser.has_error:
        print("Syntax errors. aborting")
        raise typer.Exit(code=1)

    assert ast_ is not None
    if show_tree:
        console.print(Panel(Pretty(ast_, indent_size=2), title="Syntax Tree"))

    gen = CodeGenerator()

    if destination is None:
        destination_path = Path(source.name).with_suffix(".wasm")
        with destination_path.open("wb") as destination_file:
            gen.generate(ast_, destination_file)
    else:
        gen.generate(ast_, destination)


if __name__ == "__main__":
    app()
