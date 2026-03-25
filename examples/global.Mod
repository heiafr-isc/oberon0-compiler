(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE TestGlobal;
  VAR m, n: INTEGER;

  PROCEDURE Run*;
  BEGIN OpenInput;
    m := 20;
    n := 10;
    WriteInt(n, 5); WriteLn;
    WriteInt(m, 5); WriteLn;
    WriteInt(m+n, 5); WriteLn;
    WriteInt(m*n, 5); WriteLn;
  END Run;

END TestGlobal.
