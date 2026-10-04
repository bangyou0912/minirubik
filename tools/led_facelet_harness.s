# Pure color-mapping harness.  The LED symbols are test constants only.
# No MMIO routine is called.  The result is a rolling hash of all twenty-four
# facelet RGB values in U, L, F, R, B, D order.
.equ LED_MATRIX_0_BASE, 0x10000000
.equ LED_MATRIX_0_WIDTH, 35
.equ LED_MATRIX_0_HEIGHT, 25

.text
.globl main
main:
    mv s0, a0
    mv s1, a1
    li s2, 0
    li s3, 0
    li s4, 24

led_test_loop:
    mv a0, s0
    mv a1, s1
    mv a2, s2
    jal ra, led_facelet_rgb

    slli t0, s3, 5
    srli t1, s3, 27
    or s3, t0, t1
    xor s3, s3, a0

    addi s2, s2, 1
    bltu s2, s4, led_test_loop

    mv a0, s3
    li a7, 10
    ecall
