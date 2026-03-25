(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE Test;

    PROCEDURE Bool*;
        VAR x, y : INTEGER; z : BOOLEAN;
    BEGIN
        OpenInput;
        ReadInt(x);
        ReadInt(y);
        z := x > y;
    END Bool;

END Test.
