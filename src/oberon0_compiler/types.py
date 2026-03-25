# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 types
"""

from . import sym_table as SYM

types = [
    SYM.Type(name=name, index=i, size=size)
    for i, (name, size) in enumerate([("INTEGER", 4), ("BOOLEAN", 4)])
]

integer = types[0]
boolean = types[1]
