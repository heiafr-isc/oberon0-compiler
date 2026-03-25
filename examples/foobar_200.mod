(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE FooBar;

    PROCEDURE FooBar*;
        VAR i : INTEGER;
    BEGIN
        i := 1;
        WHILE i <= 200 DO
            IF (i MOD 5 = 0) & (i MOD 7 = 0) THEN
                WriteChar(70); WriteChar(111); WriteChar(111);
                WriteChar(66); WriteChar(97); WriteChar(114); WriteLn;
            ELSIF i MOD 5 = 0 THEN
                WriteChar(70); WriteChar(111); WriteChar(111); WriteLn;
            ELSIF i MOD 7 = 0 THEN
                WriteChar(66); WriteChar(97); WriteChar(114); WriteLn;
            ELSE
                WriteInt(i, 4); WriteLn;
            END ;
            i := i + 1;
        END ;

    END FooBar;

END FooBar.
