#!/usr/bin/env python3
"""Emit C constants from the checked-in RV32I search tables.

This is a data-format bridge for the student's own C search implementation.
It makes no representation, heuristic, or search-algorithm decisions.
"""
import argparse
from pathlib import Path


TABLES = (
    ("perm_transition", "half", 5040 * 3, 5040),
    ("perm_pdb", "byte", 5040, 12),
    ("joint_a_transition", "half", 5670 * 3, 5670),
    ("joint_a_pdb", "byte", 5670, 12),
    ("joint_b_transition", "half", 5670 * 3, 5670),
    ("joint_b_pdb", "byte", 5670, 12),
)
GOALS = {"perm_pdb": 0, "joint_a_pdb": 0, "joint_b_pdb": 2916}


def parse_tables(source):
    specs = {name: (kind, length, limit) for name, kind, length, limit in TABLES}
    values = {name: [] for name in specs}
    current = None
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in specs:
            current = stripped[:-1]
            continue
        if current is None or not stripped.startswith("."):
            continue
        kind, length, limit = specs[current]
        directive = "." + kind
        if not stripped.startswith(directive + " "):
            continue
        for token in stripped[len(directive):].split(","):
            try:
                value = int(token.strip(), 0)
            except ValueError as exc:
                raise ValueError(f"{source}:{line_number}: bad {current} entry") from exc
            if not 0 <= value < limit:
                raise ValueError(f"{source}:{line_number}: {current} value {value} out of range")
            values[current].append(value)
            if len(values[current]) > length:
                raise ValueError(f"{current}: too many entries")
    for name, _, length, _ in TABLES:
        if len(values[name]) != length:
            raise ValueError(f"{name}: got {len(values[name])}, expected {length}")
    for name, goal in GOALS.items():
        if values[name][goal] != 0 or values[name].count(0) != 1:
            raise ValueError(f"{name}: expected a unique zero at {goal}")
    return values


def emit_header(values, output):
    lines = [
        "/* Generated from rv32i/search_tables.s. Data only; do not edit. */",
        "#ifndef MINIRUBIK_SEARCH_TABLES_C_H",
        "#define MINIRUBIK_SEARCH_TABLES_C_H",
        "typedef unsigned char cube_u8;",
        "typedef unsigned short cube_u16;",
        "",
    ]
    for name, kind, length, _ in TABLES:
        c_type = "cube_u16" if kind == "half" else "cube_u8"
        shape = f"[{length // 3}][3]" if kind == "half" else f"[{length}]"
        lines.append(f"static const {c_type} {name}_c{shape} = {{")
        data = values[name]
        if kind == "half":
            for index in range(0, length, 3):
                lines.append("    {" + ", ".join(map(str, data[index:index + 3])) + "},")
        else:
            for index in range(0, length, 20):
                lines.append("    " + ", ".join(map(str, data[index:index + 20])) + ",")
        lines.append("};")
        lines.append("")
    lines.append("#endif")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=root / "rv32i/search_tables.s")
    parser.add_argument("--output", type=Path, default=root / "rv32i/search_tables_c.h")
    args = parser.parse_args()
    tables = parse_tables(args.input)
    emit_header(tables, args.output)
    size = sum(length * (2 if kind == "half" else 1)
               for _, kind, length, _ in TABLES)
    print(f"wrote {args.output}; {size} data bytes across {len(TABLES)} tables")
    for name in GOALS:
        print(f"{name}: unique zero at {GOALS[name]}, maximum {max(tables[name])}")


if __name__ == "__main__":
    main()
