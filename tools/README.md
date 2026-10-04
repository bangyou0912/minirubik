# tools/

Verification tooling for the hw1 submission. Nothing here is the state
representation, search design, or RV32I code — those stay in `solver.c`,
future RV32I sources, and the HackMD note, written and argued by the
repository owner per the course's AI-use disclosure (§4.1).

## verify_host_gates.c

Host-only checks for H1, H2, and the packed-field portion of H4. It includes
the unmodified `solver.c` in one translation unit so the baseline BFS table
is the exact-distance oracle, then checks all 3,674,160 full-state ranks
against the generated search tables. The generator itself separately checks
that each projection BFS covered its whole coordinate space.

```sh
gcc -O3 -std=c99 -I. tools/verify_host_gates.c -o /tmp/verify_host_gates
/tmp/verify_host_gates rv32i/search_tables.s
```

This is AI-assisted verification tooling, not a student measurement or the
final C search implementation. The owner must run and record the results
personally before putting them in the HackMD note. H3 remains open until a
student-written final C search implementation can be tested exhaustively.

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

## LED Matrix renderer

`test_led_matrix.py` checks the 24 facelet colors for all eight known vectors,
then runs the real clear, draw, delay, and move loop for all nine moves. The
tests use ordinary sparse guest RAM in place of the GUI-only MMIO peripheral.

```sh
python tools/test_led_matrix.py
```

`build_rv32i_program.py` concatenates the maintained RV32I modules into the
single source file Ripes expects. The CLI build omits all renderer code and
LED symbols. The GUI build includes them.

```sh
python tools/build_rv32i_program.py \
    --output tools/_merged_minirubik_cli.s
python tools/build_rv32i_program.py --render \
    --output tools/_merged_minirubik_gui.s
```

Before loading the GUI build, add an LED Matrix in the Ripes I/O tab and set
Width to 35 and Height to 25. The installed Ripes assembler rejects `.if`
and `.endif`, despite those directives appearing as an example on the
assignment page, so the build script implements the renderer switch before
assembly. Both builds still come from the same maintained source modules.
