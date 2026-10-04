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


# tests/solutions.txt vectors (parsed programmatically from the 14-char
# strings below, not hand-transcribed -- an earlier hand-transcribed
# version of this table had several digits swapped, which quarter_turn
# and apply_move's self-consistency tests couldn't catch since both sides
# of those tests applied the same transform to the same, possibly wrong,
# state; it only surfaced once a test compared against the vector's
# independently known optimal length). KNOWN_OPTIMAL_LENGTHS is the move
# count from that same file (independently cross-checked against
# tools/reference_model.py's from-scratch BFS earlier).
TEST_VECTORS = [
    "12345671111111",
    "62345713133111",
    "24316572122213",
    "25713642221111",
    "24513763133333",
    "43752611332133",
    "25416373331111",
    "21345671111111",
]
KNOWN_OPTIMAL_LENGTHS = [0, 8, 8, 8, 9, 9, 10, 11]


def _parse_vector(vec):
    p = [int(c) - 1 for c in vec[:7]]
    o = [int(c) - 1 for c in vec[7:]]
    return p, o


TEST_STATES = [_parse_vector(v) for v in TEST_VECTORS]

# pos_to_new_pos[face][j] = the position a cubie currently at position j
# moves to after one quarter turn of `face` -- the functional inverse of
# SOURCE[face] (SOURCE[face][i] = the position the cubie at destination i
# came FROM). Shared by generate_search_tables.py and any IDA*-coordinate
# test tooling.
POS_TO_NEW_POS = []
for _face in range(3):
    _inv = [0] * 7
    for _i in range(7):
        _inv[SOURCE[_face][_i]] = _i
    POS_TO_NEW_POS.append(_inv)

JOINT_A_CUBIES = (0, 1, 2)
JOINT_B_CUBIES = (3, 4, 5)


def rank_full_perm(p):
    """Lehmer code, identical algorithm to solver.c's rank_state (the
    permutation half only): identity (0,1,2,3,4,5,6) ranks to 0."""
    rank = 0
    for i in range(7):
        smaller = sum(1 for j in range(i + 1, 7) if p[j] < p[i])
        rank = rank * (7 - i) + smaller
    return rank


def rank_k_from_n(choices, n):
    """Falling-factorial rank of an ordered selection of len(choices)
    distinct values from range(n), generalizing solver.c's permutation
    ranking technique to picking k of n instead of all n."""
    avail = list(range(n))
    k = len(choices)
    rank = 0
    for idx in range(k):
        c = avail.index(choices[idx])
        weight = 1
        for r in range(k - idx - 1):
            weight *= (n - idx - 1 - r)
        rank += c * weight
        avail.pop(c)
    return rank


def state_to_ida_coords(p, o):
    """Converts a solver.c-style state (p[0..6], o[0..6], 0-6 cubie
    labels) into the three IDA* search coordinates: full permutation
    rank, and the two joint-pattern ranks for cubies {0,1,2}/{3,4,5}.
    position_of[c] = the position holding cubie c; a tracked cubie's
    orientation is o at THAT position, since orientation travels with
    the physical cubie, not with the position."""
    perm_coord = rank_full_perm(p)
    position_of = {cubie: pos for pos, cubie in enumerate(p)}

    def joint_coord(cubies):
        positions = tuple(position_of[c] for c in cubies)
        orientations = tuple(o[position_of[c]] for c in cubies)
        return rank_k_from_n(positions, 7) * 27 + (
            orientations[0] * 9 + orientations[1] * 3 + orientations[2])

    return perm_coord, joint_coord(JOINT_A_CUBIES), joint_coord(JOINT_B_CUBIES)


def merge_harness_and_solution(harness_path, solution_path):
    """Ripes's assembler has no .include; concatenate the harness (a
    main: driver + exit syscall, no cube logic) with the student's own
    solution file into one temp .s file for Ripes to assemble."""
    return merge_many(harness_path, [solution_path])


def merge_many(harness_path, solution_paths):
    """Same as merge_harness_and_solution, for a harness that depends on
    more than one of the student's own files (e.g. ida_search.s plus its
    search_tables.s data)."""
    fd, path = tempfile.mkstemp(suffix=".s", prefix="cube_merged_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(open(harness_path, encoding="utf-8").read())
        for sp in solution_paths:
            f.write("\n\n# ---- merged in from " + sp + " ----\n")
            f.write(open(sp, encoding="utf-8").read())
    return path


DEFAULT_PROC = "RV32_ISS"


def run_ripes(ripes_exe, src, x10, x11, x12, timeout_ms, proc=DEFAULT_PROC):
    """Sets x10/x11/x12 via --reginit, runs src on `proc` (RV32_ISS by
    default -- the model the assignment actually names; only the
    continuous/master Ripes build has it, not the v2.2.6 release), and
    returns the resulting (x10, x11) pair read back via --regs --json."""
    reginit = f"gpr:10={x10},11={x11},12={x12}"
    cmd = [
        ripes_exe, "--mode", "cli", "--src", src, "-t", "asm",
        "--proc", proc, "--timeout", str(timeout_ms),
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


def run_ripes_regs(ripes_exe, src, reginit_pairs, reg_names, timeout_ms,
                    proc=DEFAULT_PROC):
    """General form of run_ripes: reginit_pairs is a list of (index, value)
    for --reginit, reg_names is the list of "xN" register names to read
    back. Returns (dict of name->value, error) with error None on success."""
    cmd = [
        ripes_exe, "--mode", "cli", "--src", src, "-t", "asm",
        "--proc", proc, "--timeout", str(timeout_ms),
    ]
    if reginit_pairs:
        reginit = "gpr:" + ",".join(f"{idx}={val}" for idx, val in reginit_pairs)
        cmd += ["--reginit", reginit]
    cmd += ["--regs", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stdout + result.stderr
    start = result.stdout.find("{")
    if start < 0:
        return None, f"no JSON object in output:\n{result.stdout}\n{result.stderr}"
    try:
        data = json.loads(result.stdout[start:])
    except json.JSONDecodeError:
        return None, f"non-JSON output:\n{result.stdout}\n{result.stderr}"
    regs = data.get("registers", {})
    return {name: regs.get(name) for name in reg_names}, None


def default_ripes_path():
    """Points at the continuous/master build, not the v2.2.6 release --
    RV32_ISS (the model the assignment names) only exists there."""
    return os.path.join(
        os.environ.get("USERPROFILE", ""), "Apps", "Ripes-continuous",
        "Ripes.exe")
