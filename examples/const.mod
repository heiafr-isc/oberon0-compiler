(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE Test;

    CONST x = 21 * 2;
          y = 2 * x + 1;

    PROCEDURE Say42*;
    BEGIN
        WriteInt(x, 5);
        WriteLn;
        WriteInt(y, 5);
        WriteLn;
    END Say42;

END Test.
