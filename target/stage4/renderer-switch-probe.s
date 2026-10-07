.equ RENDER, 0
.if RENDER
.word LED_MATRIX_0_BASE
.endif
.text
.globl main
main:
    li a7, 10
    ecall
