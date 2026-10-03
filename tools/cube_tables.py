"""Shared ground-truth tables and Ripes-driving plumbing for the
test_*.py checkers in this directory. Everything here is either
transcribed from solver.c (the physical cube's fixed definition and its
own move-index convention, not a design choice) or generic test
infrastructure (packing, process invocation, JSON parsing) -- no cube
logic of the student's own is implemented here.
"""
import json
import os
import subprocess
import tempfile

# source[face][i] / twist[face][i], transcribed from solver.c.
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
MOVE_NAMES = ("R", "R2", "R'", "B", "B2", "B'", "D", "D2", "D'")


def expected_quarter_turn(face, p, o):
    src, tw = SOURCE[face], TWIST[face]
    new_p = [p[src[i]] for i in range(7)]
    new_o = [(o[src[i]] + tw[i]) % 3 for i in range(7)]
    return new_p, new_o


def expected_apply_move(move, p, o):
    """Transcribed from solver.c's apply_move: move // 3 is the face,
    move % 3 + 1 is how many quarter turns to apply."""
    face = move // 3
    turns = move % 3 + 1
    for _ in range(turns):
        p, o = expected_quarter_turn(face, p, o)
    return p, o


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


def merge_harness_and_solution(harness_path, solution_path):
    """Ripes's assembler has no .include; concatenate the harness (a
    main: driver + exit syscall, no cube logic) with the student's own
    solution file into one temp .s file for Ripes to assemble."""
    harness = open(harness_path, encoding="utf-8").read()
    solution = open(solution_path, encoding="utf-8").read()
    fd, path = tempfile.mkstemp(suffix=".s", prefix="cube_merged_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(harness)
        f.write("\n\n# ---- merged in from " + solution_path + " ----\n")
        f.write(solution)
    return path


def run_ripes(ripes_exe, src, x10, x11, x12, timeout_ms):
    """Sets x10/x11/x12 via --reginit, runs src on RV32_SS, and returns
    the resulting (x10, x11) pair read back via --regs --json."""
    reginit = f"10={x10},11={x11},12={x12}"
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


def default_ripes_path():
    return os.path.join(
        os.environ.get("USERPROFILE", ""), "Apps", "Ripes", "Ripes.exe")
