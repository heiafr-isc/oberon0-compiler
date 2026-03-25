# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

make-doc:
    uv run sphinx-build -M html docs public

clean:
    rm -Rf dist .venv .ruff_cache .pytest_cache
    find . -type d -name "__pycache__" -exec rm -Rf {} +
