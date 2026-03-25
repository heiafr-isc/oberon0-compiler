(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE PrintOddNumbers;

    PROCEDURE Run*;
        VAR i, max: INTEGER;
    BEGIN
        OpenInput;
        ReadInt(max);
        i := 1;
        WHILE i < max DO
            WriteInt(i, 5);
            WriteLn;
            i := i + 2;
        END;
    END Run;

END PrintOddNumbers.
