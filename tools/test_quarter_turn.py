#!/usr/bin/env python3
"""Checks a hand-written RV32I `quarter_turn` subroutine against solver.c's
own source[]/twist[] tables (the physical cube's fixed definition), run
through Ripes's actual CLI simulator. This drives Ripes and compares
results; it contains no cube-turn logic of its own to hand to the student --
the expected values below are the same tables already public in solver.c
and tools/reference_model.py.

Calling convention the student's code must follow (see
quarter_turn_harness.s): a0=face, a1=packed p (3 bits x 7), a2=packed o
(2 bits x 7); returns a0=new packed p, a1=new packed o.

Ripes's assembler has no `.include`, so the harness (the `main:` driver and
exit syscall) and the student's own solution file are concatenated into a
temp file before each run, rather than asking the student to paste their
code into the harness file.

Usage (run with Windows Python, since Ripes.exe is a native Windows app):
    python tools\\test_quarter_turn.py --solution rv32i\\cube_ops.s
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

# Transcribed from solver.c -- the physical cube, not a design choice.
SOURCE = (
    (1, 4, 2, 0, 3, 5, 6),
    (0, 1, 2, 4, 5, 6, 3),
    (0, 2, 5, 3, 1, 4, 6),
)
TWIST = (
    (1, 2, 0, 2, 1, 0, 0),
    (0, 0, 0, 1, 2, 1, 2),
    (0, 0, 0, 0, 0, 0, 0),
)
FACE_NAMES = ("R", "B", "D")


def expected_quarter_turn(face, p, o):
    src, tw = SOURCE[face], TWIST[face]
    new_p = [p[src[i]] for i in range(7)]
    new_o = [(o[src[i]] + tw[i]) % 3 for i in range(7)]
    return new_p, new_o


def pack_p(p):
    v = 0
    for i, x in enumerate(p):
        v |= (x & 0x7) << (3 * i)
    return v


def pack_o(o):
    v = 0
    for i, x in enumerate(o):
        v |= (x & 0x3) << (2 * i)
    return v


def unpack_p(v):
    return [(v >> (3 * i)) & 0x7 for i in range(7)]


def unpack_o(v):
    return [(v >> (2 * i)) & 0x3 for i in range(7)]


# tests/solutions.txt vectors, converted to solver.c's 0-6 internal labels
# (vector digit - 1), plus the solved state.
TEST_STATES = [
    ([0, 1, 2, 3, 4, 5, 6], [0, 0, 0, 0, 0, 0, 0]),  # solved
    ([5, 1, 2, 3, 4, 0, 6], [0, 2, 0, 2, 2, 0, 0]),  # 62345713133111
    ([1, 2, 0, 4, 5, 6, 3], [0, 1, 0, 1, 1, 0, 2]),  # 24316572122213
    ([1, 4, 6, 2, 3, 5, 0], [1, 1, 1, 0, 0, 0, 0]),  # 25713642221111
    ([1, 3, 4, 6, 5, 2, 0], [0, 1, 0, 2, 2, 2, 2]),  # 24513763133333
    ([3, 6, 4, 1, 5, 0, 2], [0, 2, 1, 0, 2, 1, 0]),  # 43752611332133
    ([1, 4, 0, 5, 2, 6, 3], [1, 0, 2, 2, 1, 1, 0]),  # 25416373331111
    ([1, 0, 2, 3, 4, 5, 6], [0, 0, 0, 0, 0, 0, 0]),  # 21345671111111
]


def run_ripes(ripes_exe, src, face, p, o, timeout_ms):
    reginit = f"10={face},11={pack_p(p)},12={pack_o(o)}"
    cmd = [
        ripes_exe, "--mode", "cli", "--src", src, "-t", "asm",
        "--proc", "RV32_SS", "--timeout", str(timeout_ms),
        "--reginit", reginit, "--regs", "--json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stdout + result.stderr
    # stdout has a banner line before the JSON report; take from the first
    # '{' onward.
    start = result.stdout.find("{")
    if start < 0:
        return None, f"no JSON object in output:\n{result.stdout}\n{result.stderr}"
    try:
        data = json.loads(result.stdout[start:])
    except json.JSONDecodeError:
        return None, f"non-JSON output:\n{result.stdout}\n{result.stderr}"
    regs = data.get("registers", {})
    return (regs.get("x10"), regs.get("x11")), None


def merge_harness_and_solution(harness_path, solution_path):
    """Ripes's assembler has no `.include`; concatenate the harness (the
    main: driver + exit syscall, no cube logic) with the student's own
    solution file into one temp .s file for Ripes to assemble."""
    harness = open(harness_path, encoding="utf-8").read()
    solution = open(solution_path, encoding="utf-8").read()
    fd, path = tempfile.mkstemp(suffix=".s", prefix="quarter_turn_merged_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(harness)
        f.write("\n\n# ---- merged in from " + solution_path + " ----\n")
        f.write(solution)
    return path


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--solution", required=True,
        help="path to your own .s file, e.g. rv32i/cube_ops.s")
    ap.add_argument(
        "--harness", default=os.path.join(here, "quarter_turn_harness.s"),
        help="path to the harness file (default: tools/quarter_turn_harness.s)")
    ap.add_argument(
        "--ripes", default=r"%USERPROFILE%\Apps\Ripes\Ripes.exe".replace(
            "%USERPROFILE%", os.environ.get("USERPROFILE", "")))
    ap.add_argument("--timeout", type=int, default=5000)
    args = ap.parse_args()

    merged_path = merge_harness_and_solution(args.harness, args.solution)
    try:
        total = 0
        failed = 0
        for p, o in TEST_STATES:
            for face in range(3):
                total += 1
                exp_p, exp_o = expected_quarter_turn(face, p, o)
                exp = (pack_p(exp_p), pack_o(exp_o))
                got, err = run_ripes(
                    args.ripes, merged_path, face, p, o, args.timeout)
                label = f"face={FACE_NAMES[face]} p={p} o={o}"
                if err:
                    print(f"FAIL  {label}\n      Ripes error: {err}")
                    failed += 1
                    continue
                if got != exp:
                    got_p = unpack_p(got[0]) if got[0] is not None else None
                    got_o = unpack_o(got[1]) if got[1] is not None else None
                    print(f"FAIL  {label}")
                    print(f"      expected p={exp_p} o={exp_o}")
                    print(f"      got      p={got_p} o={got_o}")
                    failed += 1
                else:
                    print(f"ok    {label}")
        print(f"\n{total - failed}/{total} passed")
        sys.exit(1 if failed else 0)
    finally:
        os.remove(merged_path)


if __name__ == "__main__":
    main()
