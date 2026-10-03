#!/usr/bin/env python3
"""Host-side generator for rv32i/search_tables.s.

Produces DATA only (.half/.byte tables, no control flow) -- no search
algorithm or RV32I instruction logic lives here. The projection scheme is
exactly as specified:
  - permutation coordinate: solver.c's own p-rank, 0..5039, full 7-cubie
    permutation, ranked by the same Lehmer code as solver.c's rank_state.
  - joint A coordinate: position + orientation of cubies {0,1,2} only.
  - joint B coordinate: position + orientation of cubies {3,4,5} only.
  - joint rank = position_rank * 27 + orientation_rank, position_rank over
    the 7*6*5 = 210 ordered placements of 3 labeled cubies among 7 slots
    (a falling-factorial / Lehmer-style rank, same technique as solver.c's
    rank_state and unrank_state, generalized to picking 3 of 7).
  - transitions act via R/B/D single quarter turns only; R2/R'/etc. are
    produced at runtime by looking the table up 1-3 times (not stored here).

Everything here is either transcribed from solver.c's source[]/twist[]
(the physical cube, not a design choice) or a direct implementation of the
projection scheme already specified -- no new state-representation or
search-algorithm decisions are made in this file.

Usage:
    python3 tools/generate_search_tables.py
Writes rv32i/search_tables.s and prints a validation report; exits 1 if
any check fails.
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cube_tables import SOURCE, TWIST  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "rv32i", "search_tables.s")

FACE_NAMES = ("R", "B", "D")

# pos_to_new_pos[face][j] = the position a cubie currently at position j
# moves to after one quarter turn of `face`. Derived as the functional
# inverse of SOURCE[face] (SOURCE[face][i] = the position the cubie at
# destination i came FROM).
POS_TO_NEW_POS = []
for face in range(3):
    inv = [0] * 7
    for i in range(7):
        inv[SOURCE[face][i]] = i
    POS_TO_NEW_POS.append(inv)


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


# ---------------------------------------------------------------- full permutation

def build_permutation_tables():
    """BFS over all 5040 full 7-cubie permutations (orientation-free),
    half-turn metric: like solver.c's build_table, every node's 9
    neighbors (3 faces x 1/2/3 quarter turns) are all at cost 1, not
    chained as 2 or 3 unit hops -- R2 costs the same single move as R."""
    solved = tuple(range(7))
    dist = {solved: 0}
    q = deque([solved])
    while q:
        p = q.popleft()
        for face in range(3):
            cur = p
            for _turn in range(3):
                cur = tuple(cur[SOURCE[face][i]] for i in range(7))
                if cur not in dist:
                    dist[cur] = dist[p] + 1
                    q.append(cur)
    assert len(dist) == 5040, f"permutation BFS covered {len(dist)}, expected 5040"

    rank_of = {p: rank_full_perm(p) for p in dist}
    transition_table = [[0, 0, 0] for _ in range(5040)]
    pdb = [0] * 5040
    for p, r in rank_of.items():
        pdb[r] = dist[p]
        for face in range(3):
            # stored table is the single quarter turn only; R2/R' are
            # reconstructed at runtime by looking this up 2 or 3 times.
            new_p = tuple(p[SOURCE[face][i]] for i in range(7))
            transition_table[r][face] = rank_of[new_p]
    return transition_table, pdb


# ---------------------------------------------------------------- joint patterns

def build_joint_tables(cubies):
    """BFS over the position+orientation pattern of exactly the three
    cubies in `cubies` (e.g. (0, 1, 2)), ignoring the other four.
    Half-turn metric, same reasoning as build_permutation_tables: all 9
    neighbors of a node are at cost 1, not chained as 1/2/3 unit hops."""
    solved_pos = tuple(cubies)       # cubie c starts at position c
    solved_ori = (0, 0, 0)
    start = (solved_pos, solved_ori)
    dist = {start: 0}
    q = deque([start])

    def step(pos, ori, face):
        new_pos = tuple(POS_TO_NEW_POS[face][pos[k]] for k in range(3))
        new_ori = tuple(
            (ori[k] + TWIST[face][new_pos[k]]) % 3 for k in range(3))
        return new_pos, new_ori

    while q:
        pos, ori = q.popleft()
        for face in range(3):
            cur_pos, cur_ori = pos, ori
            for _turn in range(3):
                cur_pos, cur_ori = step(cur_pos, cur_ori, face)
                state = (cur_pos, cur_ori)
                if state not in dist:
                    dist[state] = dist[(pos, ori)] + 1
                    q.append(state)
    assert len(dist) == 5670, f"joint BFS covered {len(dist)}, expected 5670"

    def rank_of_state(pos, ori):
        return rank_k_from_n(pos, 7) * 27 + (ori[0] * 9 + ori[1] * 3 + ori[2])

    transition_table = [[0, 0, 0] for _ in range(5670)]
    pdb = [0] * 5670
    for (pos, ori), d in dist.items():
        r = rank_of_state(pos, ori)
        pdb[r] = d
        for face in range(3):
            # stored table is the single quarter turn only.
            new_pos, new_ori = step(pos, ori, face)
            transition_table[r][face] = rank_of_state(new_pos, new_ori)
    return transition_table, pdb


# ---------------------------------------------------------------- validation

def validate(name, transition_table, pdb, n_coords):
    """Checks against all 9 moves (R,R2,R',B,B2,B',D,D2,D'), not just the 3
    stored single quarter turns: R, B, D alone form a *directed* graph
    (R^-1 = R^3, not a 1-step reverse edge), so checking |h(u)-h(v)|<=1 on
    those 3 edges alone is the wrong test -- only h(v) <= h(u)+1 is
    guaranteed there. The full 9-move set contains each move's own
    inverse, which is the actual consistency check (matches the student's
    own stated criterion)."""
    ok = True
    if len(pdb) != n_coords:
        print(f"FAIL {name}: pdb has {len(pdb)} entries, expected {n_coords}")
        ok = False
    # The spec requires exactly one zero (the unique goal coordinate), not
    # that it be numbered 0 -- the solved pattern's rank depends on which
    # cubie labels are tracked and isn't guaranteed to land on 0.
    zero_coords = [i for i, d in enumerate(pdb) if d == 0]
    if len(zero_coords) != 1:
        print(f"FAIL {name}: expected exactly one coordinate at distance 0, "
              f"got {zero_coords}")
        ok = False
    else:
        print(f"note {name}: goal coordinate is {zero_coords[0]}")

    # Build all 9 move tables by composing the single quarter turn 1, 2,
    # or 3 times, exactly as the real search will via repeated lookups.
    move_table = [[0] * 9 for _ in range(n_coords)]
    for coord in range(n_coords):
        for face in range(3):
            cur = coord
            for turn in range(3):
                cur = transition_table[cur][face]
                move_table[coord][face * 3 + turn] = cur

    for coord in range(n_coords):
        for move in range(9):
            nxt = move_table[coord][move]
            if not (0 <= nxt < n_coords):
                print(f"FAIL {name}: move_table[{coord}][{move}]={nxt} out of range")
                ok = False
                continue
            if abs(pdb[coord] - pdb[nxt]) > 1:
                print(f"FAIL {name}: |h({coord})-h({nxt})|>1 via move {move} "
                      f"({pdb[coord]} vs {pdb[nxt]})")
                ok = False
    if ok:
        print(f"ok   {name}: {n_coords} coordinates, BFS-covered, "
              f"consistent across all 9 moves, transitions in range, "
              f"unique zero at goal")
    return ok


# ---------------------------------------------------------------- .s emission

def emit_half_table(f, label, transition_table):
    f.write(f".globl {label}\n{label}:\n")
    flat = [v for row in transition_table for v in row]
    for i in range(0, len(flat), 12):
        chunk = flat[i:i + 12]
        f.write("    .half " + ", ".join(str(v) for v in chunk) + "\n")
    f.write("\n")


def emit_byte_table(f, label, pdb):
    f.write(f".globl {label}\n{label}:\n")
    for i in range(0, len(pdb), 20):
        chunk = pdb[i:i + 20]
        f.write("    .byte " + ", ".join(str(v) for v in chunk) + "\n")
    f.write("\n")


def main():
    perm_transition, perm_pdb = build_permutation_tables()
    joint_a_transition, joint_a_pdb = build_joint_tables((0, 1, 2))
    joint_b_transition, joint_b_pdb = build_joint_tables((3, 4, 5))

    all_ok = True
    all_ok &= validate("perm_transition/perm_pdb", perm_transition, perm_pdb, 5040)
    all_ok &= validate("joint_a_transition/joint_a_pdb", joint_a_transition,
                        joint_a_pdb, 5670)
    all_ok &= validate("joint_b_transition/joint_b_pdb", joint_b_transition,
                        joint_b_pdb, 5670)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# Generated by tools/generate_search_tables.py -- do not edit "
            "by hand.\n"
            "# Data only: no search logic. Layout is state-major,\n"
            "# table[coordinate][face] with face order R=0, B=1, D=2, so\n"
            "# a coordinate's row starts at byte offset coord*6 in the\n"
            "# .half tables and coord*1 in the .byte tables.\n"
            "# perm: full 7-cubie permutation rank, 0..5039 -- solver.c's\n"
            "#   own p-rank; identity permutation ranks to 0.\n"
            "# joint_a: position+orientation pattern of cubies 0, 1, 2 only.\n"
            "# joint_b: position+orientation pattern of cubies 3, 4, 5 only.\n"
            "# joint rank = position_rank * 27 + orientation_rank; the\n"
            "#   solved/goal coordinate is whatever rank that formula gives\n"
            "#   the solved pattern -- 0 for perm and joint_a, 2916 for\n"
            "#   joint_b -- so look up the unique zero entry in each _pdb\n"
            "#   table rather than assuming it is coordinate 0.\n"
            "# Note: avoid parentheses inside '#' comments in this file --\n"
            "#   Ripes's assembler misreads them as unmatched parentheses.\n"
            ".data\n"
            ".align 2\n\n"
        )
        emit_half_table(f, "perm_transition", perm_transition)
        emit_byte_table(f, "perm_pdb", perm_pdb)
        emit_half_table(f, "joint_a_transition", joint_a_transition)
        emit_byte_table(f, "joint_a_pdb", joint_a_pdb)
        emit_half_table(f, "joint_b_transition", joint_b_transition)
        emit_byte_table(f, "joint_b_pdb", joint_b_pdb)

    expected_bytes = 5040 * 3 * 2 + 5040 + 5670 * 3 * 2 + 5670 + 5670 * 3 * 2 + 5670
    actual_bytes = (
        len(perm_transition) * 3 * 2 + len(perm_pdb)
        + len(joint_a_transition) * 3 * 2 + len(joint_a_pdb)
        + len(joint_b_transition) * 3 * 2 + len(joint_b_pdb)
    )
    print(f"\ntotal data bytes: {actual_bytes} (expected {expected_bytes})")
    if actual_bytes != expected_bytes or actual_bytes != 114660:
        print(f"FAIL: byte total mismatch (expected exactly 114660)")
        all_ok = False
    else:
        print("ok   total is exactly 114,660 bytes")

    print(f"\nwrote {OUT_PATH}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
