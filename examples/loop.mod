(*
SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: Apache-2.0 OR MIT
*)

MODULE Test;

    PROCEDURE Loop*;
        VAR i, max: INTEGER;
    BEGIN
        OpenInput;
        ReadInt(max);
        i := 1;
        WHILE i < max DO
            WriteInt(i*10, 5);
            WriteLn;
            i := i + 2;
        END;
    END Loop;

END Test.
