# Exercise the real clear, draw, delay, and move loop against sparse test RAM.
# a0 and a1 hold packed state data and a2 holds one move index.
.equ LED_MATRIX_0_BASE, 0x20000000
.equ LED_MATRIX_0_WIDTH, 35
.equ LED_MATRIX_0_HEIGHT, 25

.text
.globl main
main:
    addi sp, sp, -16
    sw a2, 0(sp)
    mv t0, a0
    mv t1, a1

    mv a0, t0
    mv a1, t1
    li a2, 1
    mv a3, sp
    jal ra, led_animate_solution

    addi sp, sp, 16
    li a7, 10
    ecall
