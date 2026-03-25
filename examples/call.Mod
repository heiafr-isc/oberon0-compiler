(*
SPDX-FileCopyrightText: 2026 Jacques Supcik <jacques.supcik@hefr.ch>
SPDX-License-Identifier: MIT
*)

MODULE TestCall;
  VAR m, n: INTEGER;

  PROCEDURE Say33;
  BEGIN
    WriteInt(33, 5); WriteLn;
  END Say33;

  PROCEDURE Say44();
  BEGIN
    WriteInt(44, 5); WriteLn;
  END Say44;

  PROCEDURE SayN(n: INTEGER);
  BEGIN
    WriteInt(n, 5); WriteLn;
  END SayN;

  PROCEDURE SetN(VAR n: INTEGER; m: INTEGER);
  BEGIN
    n := m;
  END SetN;

  PROCEDURE Run*;
    VAR x: INTEGER;
  BEGIN OpenInput;
    Say33;
    Say33();
    Say44;
    Say44();
    x := 7;
    SayN(x);
    SetN(x, 42);
    SayN(x);
    WriteInt(x, 5); WriteLn;
  END Run;

END TestCall.
