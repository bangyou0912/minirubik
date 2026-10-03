# Test harness, not part of the graded solution: it contains zero cube logic,
# only the calling sequence and exit syscall, same role as ripes_smoke_test.s.
# Paste your own quarter_turn: implementation below the line marked, then
# run it through tools/test_quarter_turn.py.
#
# Note: Ripes's assembler seems to choke on parentheses inside comments
# ("unmatched parenthesis"), so none appear below -- keep it that way if you
# edit this file.
#
# Calling convention, yours to keep or change; update test_quarter_turn.py
# if you do:
#   x10 a0 = face index: 0 = R, 1 = B, 2 = D
#   x11 a1 = packed p: p[i] in bits 3i..3i+2 for i = 0..6, 21 bits used,
#            values 0..6, same meaning as solver.c's state_t.p[i]
#   x12 a2 = packed o: o[i] in bits 2i..2i+1 for i = 0..6, 14 bits used,
#            same meaning as solver.c's state_t.o[i]
#   on return: a0 = new packed p, a1 = new packed o
.text
.globl main
main:
    jal ra, quarter_turn
    li a7, 10
    ecall

# ---------------- your quarter_turn label goes below ----------------
