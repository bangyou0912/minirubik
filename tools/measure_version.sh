#!/usr/bin/env bash
# Measure one version of the RV32I solver for the development history.
# Run from the repository root inside WSL:
#     bash tools/measure_version.sh              # working tree
#     bash tools/measure_version.sh <commit>     # a committed version
#     bash tools/measure_version.sh <commit> <vector> ...
# Builds the renderer-off CLI program with the current
# tools/build_rv32i_program.py from that version's rv32i/ sources, runs each
# vector on RV32_ISS, and reports retired instructions, the returned length,
# and .text bytes for the whole program and for rv32i/ida_search.s alone.
set -euo pipefail

REV=${1:-WORKTREE}
shift || true
VECTORS=("$@")
[ ${#VECTORS[@]} -eq 0 ] && VECTORS=(21345671111111 54721631111111)
RIPES=${RIPES:-/mnt/c/Users/user/Apps/Ripes-continuous/Ripes.exe}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

mkdir -p "$OUT/tools"
if [ "$REV" = WORKTREE ]; then
    cp -r rv32i "$OUT/"
    LABEL="working tree on $(git rev-parse --short HEAD)"
    git diff --quiet HEAD -- rv32i || LABEL="$LABEL, with uncommitted rv32i changes"
else
    git archive "$REV" rv32i | tar -x -C "$OUT"
    LABEL="$(git log -1 --format='%h %s' "$REV")"
fi
cp tools/build_rv32i_program.py "$OUT/tools/"

text_bytes() {
    riscv64-unknown-elf-as -march=rv32i -mabi=ilp32 -o "$OUT/t.o" "$1"
    riscv64-unknown-elf-size -A "$OUT/t.o" | awk '$1==".text"{print $2}'
}

python3 "$OUT/tools/build_rv32i_program.py" --output "$OUT/prog.s" >/dev/null
echo "version: $LABEL"
echo "Ripes model: RV32_ISS, renderer-off CLI build"
echo "whole program .text bytes: $(text_bytes "$OUT/prog.s")"
echo "rv32i/ida_search.s .text bytes: $(text_bytes "$OUT/rv32i/ida_search.s")"
printf '%-16s %8s %14s\n' vector length retired
for v in "${VECTORS[@]}"; do
    python3 "$OUT/tools/build_rv32i_program.py" --vector "$v" --output "$OUT/prog.s" >/dev/null
    "$RIPES" --mode cli --src "$(wslpath -w "$OUT/prog.s")" -t asm --proc RV32_ISS \
        --timeout 300000 --iret --regs --json 2>&1 |
        python3 -c "
import json, sys
s = sys.stdin.read(); d = json.loads(s[s.find('{'):])
a0 = d['registers']['x10']; a0 = a0 - 2**32 if a0 >= 2**31 else a0
print(f'%-16s %8d %14s' % ('$v', a0, format(d['# instructions retired'], ',')))"
done
