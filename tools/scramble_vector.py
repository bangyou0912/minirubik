#!/usr/bin/env python3
"""Turns a move sequence into the 14-character input vector it produces
from the solved state, using the same move tables as tools/cube_tables.py.

    python tools/scramble_vector.py "R B' D2"

The vector's optimal distance can then be confirmed independently with
    python tools/reference_model.py verify <vector>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cube_tables as c


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    p, o = list(range(7)), [0] * 7
    for name in sys.argv[1].split():
        if name not in c.MOVE_NAMES:
            sys.exit(f"unknown move {name!r}; use one of {' '.join(c.MOVE_NAMES)}")
        p, o = c.expected_apply_move(c.MOVE_NAMES.index(name), p, o)
    print("".join(str(x + 1) for x in p) + "".join(str(x + 1) for x in o))


if __name__ == "__main__":
    main()
