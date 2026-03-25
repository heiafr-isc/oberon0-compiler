(*
SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: Apache-2.0 OR MIT
*)

MODULE Test;

    PROCEDURE Say42*;
        VAR x: INTEGER;
    BEGIN
        x := 42;
        WriteInt(x, 5);
        WriteLn;
    END Say42;

END Test.
