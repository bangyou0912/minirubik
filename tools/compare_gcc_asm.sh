#!/usr/bin/env bash
# Compare the GCC-compiled C search with the hand-written RV32I search.
# Run from the repository root inside WSL:
#     bash tools/compare_gcc_asm.sh [vector]
# Both sides are measured with the same boundary: the search call only,
# entered with the three coordinates in a0..a2 and exited with ecall 10.
# Input parsing, replay and the LED renderer are excluded on both sides.
set -euo pipefail

VECTOR=${1:-21345671111111}
RIPES=${RIPES:-/mnt/c/Users/user/Apps/Ripes-continuous/Ripes.exe}
CC=riscv64-unknown-elf-gcc
CFLAGS="-O2 -march=rv32i -mabi=ilp32"
OUT=$(mktemp -d)

COORDS=$(python3 -c "
import sys; sys.path.insert(0, 'tools'); import cube_tables as c
p, o = c._parse_vector('$VECTOR'); print(*c.state_to_ida_coords(p, o))")
read -r PERM JA JB <<<"$COORDS"
echo "vector $VECTOR -> coordinates perm=$PERM jointA=$JA jointB=$JB"

$CC $CFLAGS -nostdlib -Wl,--no-relax -o "$OUT/gcc_ida.elf" tools/gcc_ida_driver.c
riscv64-unknown-elf-as -march=rv32i -mabi=ilp32 -o "$OUT/asm_ida.o" rv32i/ida_search.s
cat tools/ida_only_harness.s rv32i/ida_search.s rv32i/search_tables.s > "$OUT/asm_ida.s"

run() {
    "$RIPES" --mode cli --src "$(wslpath -w "$1")" -t "$2" --proc RV32_ISS \
        --timeout 300000 --reginit "gpr:10=$PERM,11=$JA,12=$JB" \
        --iret --regs --json 2>&1 |
        python3 -c "
import json, sys
s = sys.stdin.read(); d = json.loads(s[s.find('{'):])
print(d['# instructions retired'], d['registers']['x10'])"
}

read -r C_IRET C_LEN <<<"$(run "$OUT/gcc_ida.elf" elf)"
read -r A_IRET A_LEN <<<"$(run "$OUT/asm_ida.s" asm)"
C_FN=$(riscv64-unknown-elf-nm -S "$OUT/gcc_ida.elf" | awk '$4=="ida_solve_c"{print strtonum("0x"$2)}')
C_TEXT=$(riscv64-unknown-elf-size -A "$OUT/gcc_ida.elf" | awk '$1==".text"{print $2}')
A_TEXT=$(riscv64-unknown-elf-size -A "$OUT/asm_ida.o" | awk '$1==".text"{print $2}')

echo "compiler: $($CC --version | head -1)  flags: $CFLAGS"
echo "Ripes model: RV32_ISS"
printf '%-28s %14s %14s\n' "" "GCC -O2 C" "hand asm"
printf '%-28s %14s %14s\n' "returned length" "$C_LEN" "$A_LEN"
printf '%-28s %14s %14s\n' "retired instructions" "$C_IRET" "$A_IRET"
printf '%-28s %14s %14s\n' "search .text bytes" "$C_FN" "$A_TEXT"
printf '%-28s %14s %14s\n' "whole program .text bytes" "$C_TEXT" "-"
echo "search .text: C counts ida_solve_c only; asm counts all of rv32i/ida_search.s"
echo "whole C .text adds the _start stub and c_entry wrapper"
rm -rf "$OUT"
