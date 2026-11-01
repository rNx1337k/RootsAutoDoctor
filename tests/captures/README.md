# Recorded sessions

Every `.radrec` file in this folder is replayed by `tests/test_captures.py` with the current code: the program must
send exactly the same bytes and reach the same results (identification, faults, measuring values, adaptation and
coding results). A change that alters how the program talks to a module, or how it reads the answer, fails here.

- `simulador_*.radrec` — reference sessions recorded with the built-in simulators (marked `"simulated": true`).
  They protect the protocol code until real recordings exist.
- Sessions recorded on a real car (**Options → Record communication**, or the on-car validation in technician
  mode) are added here as they are made, named after the car, the module and the interface, for example
  `a3_8l_asz_kkl_01_17_03.radrec`.

To check one file by hand: `python -c "from rad import replay; print(replay.run('tests/captures/<file>.radrec'))"`.
Recordings contain no customer data: only the bytes exchanged with the car and the program's own results.
