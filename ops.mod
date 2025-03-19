(*
SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: Apache-2.0 OR MIT
*)

MODULE Test;

    PROCEDURE Add*;
        VAR x, y, z: INTEGER;
    BEGIN
        OpenInput;
        ReadInt(x);
        ReadInt(y);
        z := x + y;
        WriteInt(z, 5);
        WriteLn;
    END Add;

    PROCEDURE Mul*;
        VAR x, y: INTEGER;
    BEGIN
        OpenInput;
        ReadInt(x);
        ReadInt(y);
        WriteInt(x * y, 5);
        WriteLn;
    END Mul;

    PROCEDURE Div*;
        VAR x, y: INTEGER;
    BEGIN
        OpenInput;
        ReadInt(x);
        ReadInt(y);
        WriteInt(x DIV y, 5);
        WriteLn;
        WriteInt(x MOD y, 5);
        WriteLn;
    END Div;

END Test.
