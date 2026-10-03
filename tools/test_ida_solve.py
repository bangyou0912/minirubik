#!/usr/bin/env python3
"""Checks ida_solve end to end via Ripes: for each of the 8 known test
vectors, converts the state to (perm, jointA, jointB) coordinates,
--reginit's them in, runs ida_solve through tools/ida_harness.s (which
also replays the returned moves against the verified transition tables),
and checks both the returned length against the known-optimal count AND
that replaying the moves actually reaches the goal coordinates.

No search logic of its own -- see tools/ida_harness.s and
tools/cube_tables.py for what's generic infrastructure vs. transcribed
fact.

Usage (Windows Python, Ripes.exe is a native Windows app):
    python tools\\test_ida_solve.py --ida rv32i\\ida_search.s \\
        --tables rv32i\\search_tables.s
"""
import argparse
import os
import sys

from cube_tables import (
    KNOWN_OPTIMAL_LENGTHS, TEST_STATES, default_ripes_path, merge_many,
    run_ripes_regs, state_to_ida_coords,
)

GOAL_PERM = 0
GOAL_JOINT_A = 0
GOAL_JOINT_B = 2916


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--ida", required=True, help="path to ida_search.s")
    ap.add_argument("--tables", required=True, help="path to search_tables.s")
    ap.add_argument(
        "--harness", default=os.path.join(here, "ida_harness.s"))
    ap.add_argument("--ripes", default=default_ripes_path())
    ap.add_argument("--timeout", type=int, default=15000)
    args = ap.parse_args()

    merged_path = merge_many(args.harness, [args.ida, args.tables])
    try:
        total = 0
        failed = 0
        for (p, o), expected_len in zip(TEST_STATES, KNOWN_OPTIMAL_LENGTHS):
            total += 1
            perm_coord, joint_a_coord, joint_b_coord = state_to_ida_coords(p, o)
            regs, err = run_ripes_regs(
                args.ripes, merged_path,
                [(10, perm_coord), (11, joint_a_coord), (12, joint_b_coord)],
                ["x10", "x11", "x12", "x13"], args.timeout)
            label = f"p={p} o={o} coords=({perm_coord},{joint_a_coord},{joint_b_coord})"
            if err:
                print(f"FAIL  {label}\n      Ripes error: {err}")
                failed += 1
                continue
            length = regs["x10"]
            if length > 2**31:
                length -= 2**32  # Ripes reports x10 as unsigned; -1 wraps
            final_perm, final_a, final_b = regs["x11"], regs["x12"], regs["x13"]
            at_goal = (length >= 0 and
                       (final_perm, final_a, final_b) ==
                       (GOAL_PERM, GOAL_JOINT_A, GOAL_JOINT_B))
            if length != expected_len or not at_goal:
                print(f"FAIL  {label}")
                print(f"      length={length}, expected {expected_len}; "
                      f"replay ended at ({final_perm},{final_a},{final_b}), "
                      f"goal=({GOAL_PERM},{GOAL_JOINT_A},{GOAL_JOINT_B}), "
                      f"at_goal={at_goal}")
                failed += 1
                continue
            print(f"ok    {label}  length={length}, replay reaches goal")
        print(f"\n{total - failed}/{total} passed")
        sys.exit(1 if failed else 0)
    finally:
        os.remove(merged_path)


if __name__ == "__main__":
    main()
