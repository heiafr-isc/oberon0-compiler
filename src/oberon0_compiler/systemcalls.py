# SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: MIT

"""
Oberon-0 System Calls
"""

# Note : The index of a formal parameter of a system call is not
# neeeded by the code generator, so we set it to -1.

from . import sym_table as SYM
from .types import integer

system_calls = [
    SYM.SystemCall(name=name, index=i, params=params, return_type=return_type)
    for i, (name, params, return_type) in enumerate(
        [
            ("OpenInput", [], None),
            (
                "ReadInt",
                [SYM.FormalParameter(name="var", type_=integer, by_ref=True)],
                None,
            ),
            ("eot", [], integer),
            (
                "WriteChar",
                [SYM.FormalParameter(name="c", type_=integer, by_ref=False)],
                None,
            ),
            (
                "WriteInt",
                [
                    SYM.FormalParameter(name="n", type_=integer, by_ref=False),
                    SYM.FormalParameter(name="w", type_=integer, by_ref=False),
                ],
                None,
            ),
            ("WriteLn", [], None),
        ]
    )
]

OpenInput = system_calls[0]
ReadInt = system_calls[1]
eot = system_calls[2]
WriteChar = system_calls[3]
WriteInt = system_calls[4]
WriteLn = system_calls[5]
