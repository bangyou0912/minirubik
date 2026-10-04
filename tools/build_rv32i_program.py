#!/usr/bin/env python3
"""Build one Ripes-loadable source from the maintained RV32I modules.

The CLI build removes marked renderer calls and omits the renderer module so
LED peripheral symbols are never referenced. The GUI build keeps those calls
and must be loaded after a 35 by 25 LED Matrix has been instantiated in Ripes.
"""
import argparse
import os


MODULES = (
    "rv32i/main.s",
    "rv32i/input_coords.s",
    "rv32i/ida_search.s",
    "rv32i/cube_ops.s",
    "rv32i/led_matrix.s",
    "rv32i/search_tables.s",
)


def select_render_blocks(text, enabled):
    output = []
    inside = False
    for line in text.splitlines(keepends=True):
        marker = line.strip()
        if marker == "# RENDER_BEGIN":
            if inside:
                raise SystemExit("nested RENDER_BEGIN marker")
            inside = True
            continue
        if marker == "# RENDER_END":
            if not inside:
                raise SystemExit("RENDER_END without RENDER_BEGIN")
            inside = False
            continue
        if enabled or not inside:
            output.append(line)
    if inside:
        raise SystemExit("RENDER_BEGIN without RENDER_END")
    return "".join(output)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument("--vector", default="21345671111111")
    parser.add_argument("--render", action="store_true")
    parser.add_argument(
        "--output",
        default=os.path.join(root, "tools", "_merged_minirubik.s"),
    )
    args = parser.parse_args()

    if len(args.vector) != 14 or not args.vector.isdigit():
        parser.error("--vector must contain exactly 14 decimal digits")

    pieces = []
    for relative in MODULES:
        if relative == "rv32i/led_matrix.s" and not args.render:
            continue
        path = os.path.join(root, relative)
        with open(path, encoding="utf-8") as source:
            text = source.read()
        if relative == "rv32i/main.s":
            text = select_render_blocks(text, args.render)
            old_vector = '    .asciz "21345671111111"'
            if old_vector not in text:
                raise SystemExit("could not find cube_input in main.s")
            text = text.replace(
                old_vector, f'    .asciz "{args.vector}"', 1
            )
        pieces.append(f"# ---- {relative} ----\n{text.rstrip()}\n")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="\n") as output:
        output.write("\n".join(pieces))

    mode = "GUI renderer" if args.render else "CLI measurement"
    print(f"wrote {mode} build to {args.output}")


if __name__ == "__main__":
    main()
