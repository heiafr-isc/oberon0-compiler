(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE Test;

    PROCEDURE Print42*;
    VAR x, y : INTEGER;
    BEGIN
        OpenInput;
        ReadInt(x);
        ReadInt(y);
        WriteInt(x, 5);
        WriteInt(y, 5);
        WriteLn;
    END Print42;

END Test.
