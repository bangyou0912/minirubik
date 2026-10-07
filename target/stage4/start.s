.section .text.start
.globl _start
_start:
    li sp, 0x1000000
    call reference_main
    li a7, 10
    ecall
