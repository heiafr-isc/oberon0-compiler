# Oberon0 Compiler

Oberon0 Compiler is a small compiler for the Oberon-0 language implemented in Python. It parses source files, performs type checking, and generates WebAssembly output.

## Requirements

- Python 3.12 or newer
- uv

## Installation

```bash
uv sync
```

## Usage

Compile an Oberon-0 source file:

```bash
uv run oberon0-compiler examples/sample.mod
```

This creates a `.wasm` file in the current directory. You can also provide an explicit output path:

```bash
uv run oberon0-compiler examples/sample.mod sample.wasm
```

Show the parsed syntax tree:

```bash
uv run oberon0-compiler examples/sample.mod --show-tree
```

## Development

Run tests:

```bash
uv run pytest
```

Run type checking:

```bash
uv run mypy src
```