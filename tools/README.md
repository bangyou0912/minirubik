# tools/

Verification tooling for the hw1 submission. Nothing here is the state
representation, search design, or RV32I code — those stay in `solver.c`,
future RV32I sources, and the HackMD note, written and argued by the
repository owner per the course's AI-use disclosure (§4.1).

## reference_model.py

A from-scratch Python BFS over the 2x2x2 cube's quotient group, used only to
cross-check `solver.c` / `mini.c` output, not to pick a representation for
them. The quarter-turn tables (`_SOURCE`, `_TWIST`) are transcribed from
`solver.c`, since they encode the physical cube's geometry, not a design
choice — like copying chess's move rules rather than re-deriving them. The
BFS, state encoding, and vector conversion are independent.

```sh
python3 tools/reference_model.py build              # ~3.5 min, full BFS
python3 tools/reference_model.py verify 21345671111111 ...
python3 tools/reference_model.py vector 11           # one state at distance 11
```

Confirmed against the current `tests/solutions.txt` (2026-10-04): all eight
vectors' optimal distances match the move counts in that file, and the full
BFS reproduces 3,674,160 reachable states with diameter 11.

This checks that the *given* vectors are optimal; it does not yet check all
3,674,160 states against `solver.c`'s own table (that needs an instrumented
build of `solver.c` to dump `toward_solved[]`, which touches the student's
own code and is left for the owner to add if deeper H3 coverage is wanted).
