#!/usr/bin/env python3
"""Checks parse_ida_coords against state_to_ida_coords (for 8 valid
vectors) and against solver.c's own INVALID_STATES list (9 vectors, one
per rejection path, from the Makefile) for rejection. Also runs one
end-to-end ASCII-string -> parse_ida_coords -> ida_solve check for the
specified vector.

No parsing/search logic of its own: the harness text is generated per
vector (embedding the test string as .data), merged with the student's
own rv32i/input_coords.s (and rv32i/ida_search.s + search_tables.s for
the end-to-end check) via tools/cube_tables.merge_many.

Usage (Windows Python, Ripes.exe is a native Windows app):
    python tools\\test_input_coords.py --parser rv32i\\input_coords.s \\
        --ida rv32i\\ida_search.s --tables rv32i\\search_tables.s
"""
import argparse
import os
import sys

from cube_tables import (
    TEST_VECTORS, KNOWN_OPTIMAL_LENGTHS, default_ripes_path, merge_many,
    run_ripes_regs,
)

# One vector per rejection path, from the Makefile's INVALID_STATES:
# short, long, cubie digit low, cubie digit high, orientation digit low,
# orientation digit high, non-digit, duplicate cubie, parity violation.
INVALID_VECTORS = [
    "1234567111111",
    "123456711111111",
    "02345671111111",
    "82345671111111",
    "12345671111110",
    "12345671111114",
    "1234567111111a",
    "11345671111111",
    "12345671111112",
]

PARSE_HARNESS_TEMPLATE = """.data
test_string:
    .asciz "{vec}"

.text
.globl main
main:
    la a0, test_string
    jal ra, parse_ida_coords
    li a7, 10
    ecall
"""

E2E_HARNESS_TEMPLATE = """.data
test_string:
    .asciz "{vec}"

.text
.globl main
main:
    la a0, test_string
    jal ra, parse_ida_coords
    bnez a3, e2e_done
    jal ra, ida_solve
    mv a3, a1
    j e2e_store
e2e_done:
    li a0, -1
e2e_store:
    li a7, 10
    ecall
"""


def run_one(ripes, harness_text, extra_solutions, timeout_ms, reg_names):
    here = os.path.dirname(os.path.abspath(__file__))
    tmp_harness = os.path.join(here, "_tmp_input_coords_harness.s")
    with open(tmp_harness, "w", encoding="utf-8") as f:
        f.write(harness_text)
    merged = merge_many(tmp_harness, extra_solutions)
    try:
        return run_ripes_regs(ripes, merged, [], reg_names, timeout_ms)
    finally:
        os.remove(tmp_harness)
        os.remove(merged)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", required=True, help="path to input_coords.s")
    ap.add_argument("--ida", required=True, help="path to ida_search.s")
    ap.add_argument("--tables", required=True, help="path to search_tables.s")
    ap.add_argument("--ripes", default=default_ripes_path())
    ap.add_argument("--timeout", type=int, default=15000)
    ap.add_argument("--e2e-timeout", type=int, default=60000)
    args = ap.parse_args()

    total = 0
    failed = 0

    # 1. Valid vectors: compare against the independent Python coordinate
    #    conversion.
    from cube_tables import state_to_ida_coords, TEST_STATES
    for vec, (p, o) in zip(TEST_VECTORS, TEST_STATES):
        total += 1
        exp_perm, exp_a, exp_b = state_to_ida_coords(p, o)
        harness = PARSE_HARNESS_TEMPLATE.format(vec=vec)
        regs, err = run_one(
            args.ripes, harness, [args.parser], args.timeout,
            ["x10", "x11", "x12", "x13"])
        label = f"valid {vec}"
        if err:
            print(f"FAIL  {label}\n      Ripes error: {err}")
            failed += 1
            continue
        got = (regs["x10"], regs["x11"], regs["x12"], regs["x13"])
        exp = (exp_perm, exp_a, exp_b, 0)
        if got != exp:
            print(f"FAIL  {label}\n      got {got}, expected {exp}")
            failed += 1
        else:
            print(f"ok    {label}  -> {got}")

    # 2. Invalid vectors: must all report status -1 in a3 (x13).
    for vec in INVALID_VECTORS:
        total += 1
        harness = PARSE_HARNESS_TEMPLATE.format(vec=vec)
        regs, err = run_one(
            args.ripes, harness, [args.parser], args.timeout, ["x13"])
        label = f"invalid {vec}"
        if err:
            print(f"FAIL  {label}\n      Ripes error: {err}")
            failed += 1
            continue
        status = regs["x13"]
        if status is not None and status > 2**31:
            status -= 2**32
        if status != -1:
            print(f"FAIL  {label}\n      a3={status}, expected -1 (rejected)")
            failed += 1
        else:
            print(f"ok    {label}  -> rejected")

    # 3. End-to-end: the specified vector, ASCII string straight through
    #    parse_ida_coords -> ida_solve.
    total += 1
    spec_vec = "21345671111111"
    spec_len = KNOWN_OPTIMAL_LENGTHS[TEST_VECTORS.index(spec_vec)]
    harness = E2E_HARNESS_TEMPLATE.format(vec=spec_vec)
    regs, err = run_one(
        args.ripes, harness, [args.parser, args.ida, args.tables],
        args.e2e_timeout, ["x10"])
    label = f"end-to-end {spec_vec}"
    if err:
        print(f"FAIL  {label}\n      Ripes error: {err}")
        failed += 1
    else:
        length = regs["x10"]
        if length is not None and length > 2**31:
            length -= 2**32
        if length != spec_len:
            print(f"FAIL  {label}\n      length={length}, expected {spec_len}")
            failed += 1
        else:
            print(f"ok    {label}  length={length}")

    print(f"\n{total - failed}/{total} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
