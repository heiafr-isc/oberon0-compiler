# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

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
from .type_checker import TypeChecker

console = Console()
app = typer.Typer()


FilterDict: TypeAlias = dict[str | None, str | int | bool]


__version__ = "0.1.1"


def version_callback(value: bool) -> None:
    if value:
        print(f"Oberon0 compiler version: {__version__}")
        raise typer.Exit()


@app.command(context_settings={"ignore_unknown_options": False})
def main(  # noqa: PLR0913
    source: Annotated[Path, typer.Argument(help="Oberon-0 source file (.mod)")],
    destination: Annotated[Path | None, typer.Argument()] = None,
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
    try:
        source_file = source.open("r")
        scanner.open(source_file)
    except OSError as e:
        logger.error(f"Cannot open source file {source}: {e}")
        raise typer.Exit(code=1) from e

    parser = Parser(scanner=scanner)

    ast_ = None
    try:
        ast_ = parser.parse()
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise typer.Exit(code=1) from e

    assert ast_ is not None
    if show_tree:
        console.print(Panel(Pretty(ast_, indent_size=2), title="Syntax Tree"))

    checker = TypeChecker()
    try:
        checker.check(ast_)
    except Exception as e:
        logger.error(f"Type checking failed: {e}")
        raise typer.Exit(code=1) from e

    gen = CodeGenerator()

    if destination is None:
        destination = Path(source.name).with_suffix(".wasm")

    with destination.open("wb") as output_file:
        try:
            gen.generate(ast_, output_file)
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
