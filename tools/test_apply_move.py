#!/usr/bin/env python3
"""Checks a hand-written RV32I `apply_move` against solver.c's own move
encoding (move // 3 = face, move % 3 + 1 = quarter-turn count) built on
top of the already-verified quarter_turn tables. See tools/cube_tables.py
for what's transcribed vs. generic test infrastructure.

Calling convention (see apply_move_harness.s): a0=move 0..8, a1=packed p,
a2=packed o; returns a0=new packed p, a1=new packed o.

Usage (run with Windows Python, since Ripes.exe is a native Windows app):
    python tools\\test_apply_move.py --solution rv32i\\cube_ops.s
"""
import argparse
import os
import sys

from cube_tables import (
    MOVE_NAMES, TEST_STATES, default_ripes_path, expected_apply_move,
    merge_harness_and_solution, pack_o, pack_p, run_ripes, unpack_o, unpack_p,
)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--solution", required=True,
        help="path to your own .s file, e.g. rv32i/cube_ops.s")
    ap.add_argument(
        "--harness", default=os.path.join(here, "apply_move_harness.s"))
    ap.add_argument("--ripes", default=default_ripes_path())
    ap.add_argument("--timeout", type=int, default=5000)
    args = ap.parse_args()

    merged_path = merge_harness_and_solution(args.harness, args.solution)
    try:
        total = 0
        failed = 0
        for p, o in TEST_STATES:
            for move in range(9):
                total += 1
                exp_p, exp_o = expected_apply_move(move, p, o)
                exp = (pack_p(exp_p), pack_o(exp_o))
                got, err = run_ripes(
                    args.ripes, merged_path, move, pack_p(p), pack_o(o),
                    args.timeout)
                label = f"move={MOVE_NAMES[move]:<2} p={p} o={o}"
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
