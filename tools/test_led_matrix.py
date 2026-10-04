#!/usr/bin/env python3
"""Verify the RV32I cube-to-facelet color mapping through Ripes CLI."""
import argparse
import os

from cube_tables import (
    TEST_STATES,
    TEST_VECTORS,
    expected_apply_move,
    default_ripes_path,
    merge_many,
    pack_o,
    pack_p,
    run_ripes_regs,
)

RGB = (0xFFFFFF, 0xFF8000, 0x00FF00, 0xFF0000, 0x0000FF, 0xFFFF00)
CUBIE_COLORS = (
    (0, 3, 2),
    (5, 2, 3),
    (5, 1, 2),
    (0, 4, 3),
    (5, 3, 4),
    (5, 4, 1),
    (0, 1, 4),
    (0, 2, 1),
)
FACELETS = (
    (6, 0), (3, 0), (7, 0), (0, 0),
    (6, 1), (7, 2), (5, 2), (2, 1),
    (7, 1), (0, 2), (2, 2), (1, 1),
    (0, 1), (3, 2), (1, 2), (4, 1),
    (3, 1), (6, 2), (4, 2), (5, 1),
    (2, 0), (1, 0), (5, 0), (4, 0),
)


def expected_hash(p, o):
    value = 0
    for position, slot in FACELETS:
        if position == 7:
            cubie, orientation = 7, 0
        else:
            cubie, orientation = p[position], o[position]
        color = RGB[CUBIE_COLORS[cubie][(slot + orientation) % 3]]
        value = ((value << 5) | (value >> 27)) & 0xFFFFFFFF
        value ^= color
    return value


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--renderer",
        default=os.path.join(here, "..", "rv32i", "led_matrix.s"),
    )
    parser.add_argument(
        "--cube-ops",
        default=os.path.join(here, "..", "rv32i", "cube_ops.s"),
    )
    parser.add_argument("--ripes", default=default_ripes_path())
    parser.add_argument("--timeout", type=int, default=10000)
    args = parser.parse_args()

    harness = os.path.join(here, "led_facelet_harness.s")
    animation_harness = os.path.join(here, "led_animation_harness.s")
    merged = merge_many(harness, [args.renderer, args.cube_ops])
    passed = 0
    try:
        for vector, state in zip(TEST_VECTORS, TEST_STATES):
            p, o = state
            expected = expected_hash(p, o)
            regs, error = run_ripes_regs(
                args.ripes,
                merged,
                [(10, pack_p(p)), (11, pack_o(o))],
                ["x10"],
                args.timeout,
            )
            if error:
                print(f"FAIL {vector}: {error}")
                continue
            actual = regs["x10"]
            if actual != expected:
                print(
                    f"FAIL {vector}: expected 0x{expected:08x}, "
                    f"got 0x{actual:08x}"
                )
                continue
            passed += 1
            print(f"PASS {vector}: facelet hash 0x{actual:08x}")
    finally:
        os.remove(merged)

    solved_p = list(range(7))
    solved_o = [0] * 7
    animation = merge_many(
        animation_harness, [args.renderer, args.cube_ops]
    )
    try:
        for move in range(9):
            expected_p, expected_o = expected_apply_move(
                move, solved_p, solved_o
            )
            regs, error = run_ripes_regs(
                args.ripes,
                animation,
                [(10, pack_p(solved_p)), (11, pack_o(solved_o)), (12, move)],
                ["x10", "x11"],
                args.timeout,
            )
            if error:
                print(f"FAIL move {move}: {error}")
                continue
            actual = (regs["x10"], regs["x11"])
            expected = (pack_p(expected_p), pack_o(expected_o))
            if actual != expected:
                print(
                    f"FAIL move {move}: expected {expected}, got {actual}"
                )
                continue
            passed += 1
            print(f"PASS move {move}: animation reached {actual}")
    finally:
        os.remove(animation)

    total = len(TEST_STATES) + 9
    print(f"\n{passed}/{total} LED renderer checks passed")
    raise SystemExit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
