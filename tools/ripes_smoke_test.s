# Confirms the Ripes CLI measurement pipeline works end to end; not part of
# the graded RV32I solution. Expected: 5 cycles, 5 instructions retired on
# RV32_SS.
.text
.globl main
main:
    li a0, 5
    li a1, 7
    add a2, a0, a1
    li a7, 10   # RARS/Ripes exit syscall
    ecall
