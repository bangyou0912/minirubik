.text
.globl main
main:
    li t0, 0x20000000
    mv t1, a0
    li t2, 90
    beqz t1, done
loop:
    sb t2, 0(t0)
    addi t0, t0, 1
    addi t1, t1, -1
    bnez t1, loop
done:
    li a0, 0
    li a7, 10
    ecall
