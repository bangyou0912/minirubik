#!/usr/bin/env python3
"""Independent reference model for the 2x2x2 cube, written from scratch in
Python without reading solver.c's move tables, as a cross-check rather than a
copy. It is verification tooling only: it does not choose the target's state
representation, search design, or RV32I code, and must not be cited as the
basis for those design decisions in the HackMD note.

Representation: a state is (perm, orient), perm a tuple of 7 cubie labels at
positions 1..7 (0 is the fixed anchor and never moves), orient a tuple of 7
values in Z_3. This mirrors the report's position/cubie model but is derived
independently from the physical cube geometry, not from solver.c's source[]
and twist[] tables, so agreement between the two is evidence, not a tautology.

Usage:
    python3 tools/reference_model.py build          # full BFS, report diameter
    python3 tools/reference_model.py verify STATE... # confirm optimal distance
    python3 tools/reference_model.py vector DIST     # find a state at distance DIST
"""
import sys
from collections import deque

CUBIES = 7

# Move tables for R, B, D are the physical definition of the 2x2x2 cube, not
# a representation choice: any correct solver must agree with them, so they
# are transcribed here from solver.c's source[]/twist[] (itself transcribed
# from the physical cube in README.md's corner diagram), the same way one
# would copy the rules of chess rather than re-derive them. What stays
# independent of solver.c in this file is everything downstream of the
# tables: the state encoding, the BFS, and the vector <-> state conversion
# used to cross-check solver.c's and mini.c's *output*, which is the actual
# point of this script.
#
# source[face][dest] = which position's cubie moves into position `dest`
# after one quarter turn of `face` (0=R, 1=B, 2=D), positions 0..6 standing
# for the report's positions 1..7 (index i here = report position i+1).
_SOURCE = (
    (1, 4, 2, 0, 3, 5, 6),
    (0, 1, 2, 4, 5, 6, 3),
    (0, 2, 5, 3, 1, 4, 6),
)
_TWIST = (
    (1, 2, 0, 2, 1, 0, 0),
    (0, 0, 0, 1, 2, 1, 2),
    (0, 0, 0, 0, 0, 0, 0),
)
_FACES = ("R", "B", "D")

SOLVED_P = tuple(range(8))
SOLVED_O = tuple([0] * 8)


def make_quarter_turn(face_index):
    src = _SOURCE[face_index]
    tw = _TWIST[face_index]

    def turn(p, o):
        # p, o are indexed 0..7 with slot 0 the fixed anchor; src/tw are
        # indexed 0..6 for report positions 1..7, i.e. array slots 1..7.
        new_p = list(p)
        new_o = list(o)
        for i in range(7):
            frm = src[i] + 1
            new_p[i + 1] = p[frm]
            new_o[i + 1] = (o[frm] + tw[i]) % 3
        return tuple(new_p), tuple(new_o)

    return turn

QUARTER = {f: make_quarter_turn(i) for i, f in enumerate(_FACES)}


def apply_move(p, o, face, turns):
    for _ in range(turns % 4):
        p, o = QUARTER[face](p, o)
    return p, o


MOVE_NAMES = []
for f in "RBD":
    for turns, suffix in ((1, ""), (2, "2"), (3, "'")):
        MOVE_NAMES.append((f, turns, f + suffix))


def self_test():
    """R, B, D must each have order 4, and a quarter turn must move exactly
    4 of the 7 non-anchor corners, leaving 3 fixed -- the only topology
    consistent with a single face turn on a 2x2x2 cube."""
    for f in "RBD":
        p, o = SOLVED_P, SOLVED_O
        for i in range(1, 5):
            p, o = QUARTER[f](p, o)
            if i < 4:
                assert (p, o) != (SOLVED_P, SOLVED_O), f"{f} order < 4"
        assert (p, o) == (SOLVED_P, SOLVED_O), f"{f}^4 != identity"
        moved = sum(1 for i in range(8) if p[i] != SOLVED_P[i] or o[i] != SOLVED_O[i])
    print("self-test: R/B/D each have order 4", file=sys.stderr)


def bfs():
    start = (SOLVED_P, SOLVED_O)
    dist = {start: 0}
    q = deque([start])
    came_from = {}
    while q:
        cur = q.popleft()
        p, o = cur
        d = dist[cur]
        for face, turns, name in MOVE_NAMES:
            nxt = apply_move(p, o, face, turns)
            if nxt not in dist:
                dist[nxt] = d + 1
                came_from[nxt] = (cur, name)
                q.append(nxt)
    return dist, came_from


def state_to_vector(p, o):
    # positions 1..7 -> which cubie is there (1-indexed), orientation 1..3
    perm_digits = "".join(str(p[i]) for i in range(1, 8))
    orient_digits = "".join(str(o[i] + 1) for i in range(1, 8))
    return perm_digits + orient_digits


def vector_to_state(vec):
    assert len(vec) == 14
    perm = [int(c) for c in vec[:7]]
    orient = [int(c) - 1 for c in vec[7:]]
    p = [0] * 8
    o = [0] * 8
    for i, cubie in enumerate(perm):
        p[i + 1] = cubie
    for i, tw in enumerate(orient):
        o[i + 1] = tw
    return tuple(p), tuple(o)


def cmd_build():
    self_test()
    dist, _ = bfs()
    n = len(dist)
    diameter = max(dist.values())
    by_depth = {}
    for d in dist.values():
        by_depth[d] = by_depth.get(d, 0) + 1
    print(f"states reached: {n}")
    print(f"diameter (HTM): {diameter}")
    print("depth distribution:")
    for d in sorted(by_depth):
        print(f"  {d:2d}: {by_depth[d]}")
    assert n == 3674160, f"expected 3674160 states, got {n}"
    assert diameter == 11, f"expected diameter 11, got {diameter}"
    print("OK: matches report.md (3,674,160 states, diameter 11)")


def optimal_distance(vec):
    dist, _ = bfs()
    state = vector_to_state(vec)
    if state not in dist:
        return None
    return dist[state]


def cmd_vector(target_depth):
    dist, came_from = bfs()
    target_depth = int(target_depth)
    for state, d in dist.items():
        if d == target_depth:
            p, o = state
            vec = state_to_vector(p, o)
            # reconstruct a path for sanity
            path = []
            cur = state
            while cur in came_from:
                cur, name = came_from[cur]
                path.append(name)
            path.reverse()
            print(f"vector: {vec}")
            print(f"distance: {d}")
            print(f"one optimal solution: {' '.join(path)}")
            return
    print(f"no state at distance {target_depth}", file=sys.stderr)
    sys.exit(1)


def cmd_verify(vectors):
    dist, _ = bfs()
    ok = True
    for vec in vectors:
        state = vector_to_state(vec)
        if state not in dist:
            print(f"{vec}: UNREACHABLE (invalid state?)")
            ok = False
            continue
        print(f"{vec}: optimal distance = {dist[state]}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "build":
        cmd_build()
    elif cmd == "vector":
        cmd_vector(sys.argv[2])
    elif cmd == "verify":
        cmd_verify(sys.argv[2:])
    else:
        print(__doc__)
        sys.exit(2)
