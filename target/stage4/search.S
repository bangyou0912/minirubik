/* Hand-written RV32I IDA*. ABI matches the final C s2_solve.
 * Active child coordinates remain in t0/t1/t2; face-row bases in s5/s6.
 * REVISION=0 commits cached child/turn on every edge.
 * REVISION=1 commits them only when descending into an accepted child.
 * REVISION=2 also removes an unused frame-entry block (24 linked text bytes).
 */
#ifndef REVISION
#define REVISION 2
#endif
.section .text
.globl s2_solve
s2_solve:
    li t4,5040
    bgeu a1,t4,.Linvalid
    li t4,5670
    bgeu a2,t4,.Linvalid
    bgeu a3,t4,.Linvalid
    addi sp,sp,-64
    sw s0,0(sp)
    sw s1,4(sp)
    sw s2,8(sp)
    sw s3,12(sp)
    sw s4,16(sp)
    sw s5,20(sp)
    sw s6,24(sp)
    sw s7,28(sp)
    sw s8,32(sp)
    sw s9,36(sp)
    sw s10,40(sp)
    sw s11,44(sp)
    mv s0,a0
    mv s1,a4
    sw a1,48(sp)
    sw a2,52(sp)
    sw a3,56(sp)
    li t4,64260
    add s7,s0,t4
    li t4,5040
    add s8,s7,t4
    li t4,5670
    add s9,s8,t4
    add t4,s7,a1
    lbu s4,0(t4)
    add t4,s8,a2
    lbu t5,0(t4)
    bgeu s4,t5,1f
    mv s4,t5
1:  add t4,s9,a3
    lbu t5,0(t4)
    bgeu s4,t5,2f
    mv s4,t5
2:  or t4,a1,a2
    bnez t4,.Lbound
    li t4,2916
    bne a3,t4,.Lbound
    sb zero,203(s1)
    j .Lsuccess
.Lbound:
    mv s2,s1
    li s3,0
    lw t0,48(sp)
    lw t1,52(sp)
    lw t2,56(sp)
    sh t0,0(s2)
    sh t1,2(s2)
    sh t2,4(s2)
    sb s4,12(s2)
    li t4,3
    sb t4,13(s2)
    li s11,0
    li t3,0
    mv s10,s4
    j .Lrows
#if REVISION < 2
.Lenter:
    lhu t0,6(s2)
    lhu t1,8(s2)
    lhu t2,10(s2)
    lbu s10,12(s2)
    lbu s11,14(s2)
    lbu t3,15(s2)
#endif
.Lrows:
    /* Face is 0..2: choose stride by zero/one/two without multiplication. */
    mv s5,s0
    li t4,30240
    add s6,s0,t4
    beqz s11,.Lface
    li t4,10080
    li t5,11340
    li t6,1
    beq s11,t6,3f
    slli t4,t4,1
    slli t5,t5,1
3:  add s5,s5,t4
    add s6,s6,t5
.Lface:
    lbu t4,13(s2)
    beq s11,t4,.Lnextface
.Ledge:
    slli t4,t0,1
    add t4,s5,t4
    lhu t0,0(t4)
    slli t4,t1,1
    add t4,s6,t4
    lhu t1,0(t4)
    slli t4,t2,1
    add t4,s6,t4
    lhu t2,0(t4)
    addi t3,t3,1
#if REVISION == 0
    sh t0,6(s2)
    sh t1,8(s2)
    sh t2,10(s2)
    sb t3,15(s2)
#endif
    addi t6,s10,-1
    add t4,s8,t1
    lbu t5,0(t4)
    bltu t6,t5,.Lreject
    add t4,s9,t2
    lbu t5,0(t4)
    bltu t6,t5,.Lreject
    add t4,s7,t0
    lbu t5,0(t4)
    bltu t6,t5,.Lreject
    slli t4,s11,1
    add t4,t4,s11
    add t4,t4,t3
    addi t4,t4,-1
    add t5,s1,s3
    sb t4,192(t5)
    or t4,t0,t1
    bnez t4,.Lcommit
    li t4,2916
    bne t2,t4,.Lcommit
    addi t4,s3,1
    sb t4,203(s1)
    j .Lsuccess
.Lcommit:
    beqz t6,.Lreject
#if REVISION != 0
    sh t0,6(s2)
    sh t1,8(s2)
    sh t2,10(s2)
    sb t3,15(s2)
#endif
    sb s11,14(s2)
    addi s2,s2,16
    addi s3,s3,1
    sh t0,0(s2)
    sh t1,2(s2)
    sh t2,4(s2)
    sb t6,12(s2)
    sb s11,13(s2)
    mv s10,t6
    li s11,0
    li t3,0
    j .Lrows
.Lreject:
    li t4,3
    bltu t3,t4,.Ledge
.Lnextface:
    addi s11,s11,1
    li t4,3
    beq s11,t4,.Lpop
    lhu t0,0(s2)
    lhu t1,2(s2)
    lhu t2,4(s2)
    li t3,0
    li t4,10080
    add s5,s5,t4
    li t4,11340
    add s6,s6,t4
    j .Lface
.Lpop:
    addi s3,s3,-1
    bltz s3,.Ldeeper
    addi s2,s2,-16
    /* A parent's turn may already equal three. */
    lhu t0,6(s2)
    lhu t1,8(s2)
    lhu t2,10(s2)
    lbu s10,12(s2)
    lbu s11,14(s2)
    lbu t3,15(s2)
    li t4,3
    beq t3,t4,.Lresume_next
    j .Lrows
.Lresume_next:
    /* .Lrows computes current bases before advancing the face. */
    mv s5,s0
    li t4,30240
    add s6,s0,t4
    beqz s11,.Lnextface
    li t4,10080
    li t5,11340
    li t6,1
    beq s11,t6,4f
    slli t4,t4,1
    slli t5,t5,1
4:  add s5,s5,t4
    add s6,s6,t5
    j .Lnextface
.Ldeeper:
    addi s4,s4,1
    li t4,12
    bltu s4,t4,.Lbound
    li t4,255
    sb t4,203(s1)
    li a0,0
    j .Lreturn
.Lsuccess:
    li a0,1
.Lreturn:
    lw s0,0(sp)
    lw s1,4(sp)
    lw s2,8(sp)
    lw s3,12(sp)
    lw s4,16(sp)
    lw s5,20(sp)
    lw s6,24(sp)
    lw s7,28(sp)
    lw s8,32(sp)
    lw s9,36(sp)
    lw s10,40(sp)
    lw s11,44(sp)
    addi sp,sp,64
    ret
.Linvalid:
    li a0,0
    ret


