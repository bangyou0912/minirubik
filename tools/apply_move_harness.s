# Test harness, not part of the graded solution: zero cube logic here, only
# the calling sequence and exit syscall. Your apply_move: goes in your own
# solution file (e.g. rv32i/cube_ops.s), merged in by test_apply_move.py --
# Ripes has no .include.
#
# Note: avoid parentheses inside '#' comments -- Ripes's assembler misreads
# them as an unmatched-parenthesis error.
#
# Calling convention, matching solver.c's own move encoding:
#   x10 a0 = move index 0..8. move / 3 selects the face, 0=R 1=B 2=D.
#            move % 3 + 1 is the quarter-turn count, 1, 2, or 3.
#            So R=0, R2=1, R-prime=2, B=3, B2=4, B-prime=5, D=6, D2=7,
#            D-prime=8, same order as solver.c's move_names.
#   x11 a1 = packed p, same format as quarter_turn
#   x12 a2 = packed o, same format as quarter_turn
#   on return: a0 = new packed p, a1 = new packed o
.text
.globl main
main:
    jal ra, apply_move
    li a7, 10
    ecall

# ---------------- your apply_move label goes below ----------------
