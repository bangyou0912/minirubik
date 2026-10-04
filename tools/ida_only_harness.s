# Measurement harness for ida_solve only.
# Set a0, a1, and a2 to the three starting coordinates with reginit.
# Returns the path length in a0 and the move pointer in a1.
.text
.globl main
main:
    jal ra, ida_solve
    li a7, 10
    ecall
