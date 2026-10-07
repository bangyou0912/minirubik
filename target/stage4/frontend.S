/* All target frontend work is hand-written RV32I. No host-supplied ranks/path. */
.section .text.start
.globl _start
_start:
    li sp,0x1000000
    call assembly_main
#ifdef RENDER_TEST
    la t0,render_fault
    lw a2,0(t0)
    la t0,render_frames
    lw a3,0(t0)
#endif
    li a7,10
    ecall
.section .text
.globl assembly_main
assembly_main:
    addi sp,sp,-48
    sw ra,44(sp)
    sw s0,40(sp)
    sw s1,36(sp)
    sw s2,32(sp)
    sw s3,28(sp)
    sw s4,24(sp)
    sw s5,20(sp)
    sw s6,16(sp)
    la s0,cubie_p
    la s1,cubie_o
    la s2,workspace
    la t0,input_vector
    li t1,0
    li t2,0
    li t6,7
.Lparse_p:
    lbu t3,0(t0)
    addi t3,t3,-49
    bgeu t3,t6,.Lfailed
    li t4,1
    sll t4,t4,t3
    and t5,t2,t4
    bnez t5,.Lfailed
    or t2,t2,t4
    add t5,s0,t1
    sb t3,0(t5)
    addi t0,t0,1
    addi t1,t1,1
    bltu t1,t6,.Lparse_p
    li t1,0
    li t2,0
    li t4,3
.Lparse_o:
    lbu t3,0(t0)
    addi t3,t3,-49
    bgeu t3,t4,.Lfailed
    add t2,t2,t3
    add t5,s1,t1
    sb t3,0(t5)
    addi t0,t0,1
    addi t1,t1,1
    bltu t1,t6,.Lparse_o
    lbu t3,0(t0)
    bnez t3,.Lfailed
.Lsum:
    bltu t2,t4,.Lsum_done
    addi t2,t2,-3
    j .Lsum
.Lsum_done:
    bnez t2,.Lfailed
    /* Lehmer rank: add the fixed factorial weight for each inversion. */
    li t0,0
    li t1,0
    la t6,factorial_weights
.Lrank_i:
    add t2,s0,t1
    lbu t3,0(t2)
    lhu t4,0(t6)
    addi t5,t1,1
.Lrank_j:
    add a0,s0,t5
    lbu a0,0(a0)
    bgeu a0,t3,1f
    add t0,t0,t4
1:  addi t5,t5,1
    li a0,7
    bltu t5,a0,.Lrank_j
    addi t6,t6,2
    addi t1,t1,1
    li a0,6
    bltu t1,a0,.Lrank_i
    sw t0,0(sp)
    mv a0,s0
    mv a1,s1
    li a2,0
    call joint_rank
    sw a0,4(sp)
    mv a0,s0
    mv a1,s1
    li a2,3
    call joint_rank
    mv a3,a0
    lw a1,0(sp)
    lw a2,4(sp)
    la a0,search_tables
    mv a4,s2
    li a5,0
    call s2_solve
    beqz a0,.Lfailed
    lbu s3,203(s2)
    li t0,12
    bgeu s3,t0,.Lfailed
    la t0,expected_length
    lw t0,0(t0)
    bltz t0,2f
    bne s3,t0,.Lfailed
2:
#if defined(RENDER) && RENDER
    call render_cube
#endif
    li s4,0
.Lpath:
    bgeu s4,s3,.Lreplayed
    add t0,s2,s4
    lbu t0,192(t0)
    li t1,9
    bgeu t0,t1,.Lfailed
    slli t1,t0,2
    la t2,move_names
    add t1,t1,t2
    lw a0,0(t1)
    li a7,4
    ecall
    li s5,0
    mv s6,t0
    li t1,3
    bltu s6,t1,3f
    li s5,1
    addi s6,s6,-3
    bltu s6,t1,3f
    li s5,2
    addi s6,s6,-3
3:  addi s6,s6,1
.Lquarters:
    mv a0,s5
    call physical_quarter
    addi s6,s6,-1
    bnez s6,.Lquarters
#if defined(RENDER) && RENDER
    call render_cube
#endif
    addi s4,s4,1
    j .Lpath
.Lreplayed:
    la a0,newline
    li a7,4
    ecall
    li t0,0
.Lgoal:
    add t1,s0,t0
    lbu t2,0(t1)
    bne t2,t0,.Lfailed
    add t1,s1,t0
    lbu t2,0(t1)
    bnez t2,.Lfailed
    addi t0,t0,1
    li t1,7
    bltu t0,t1,.Lgoal
    mv a0,s3
    li a1,1
    j .Lmain_return
.Lfailed:
    li a0,-1
    li a1,0
.Lmain_return:
    lw ra,44(sp)
    lw s0,40(sp)
    lw s1,36(sp)
    lw s2,32(sp)
    lw s3,28(sp)
    lw s4,24(sp)
    lw s5,20(sp)
    lw s6,16(sp)
    addi sp,sp,48
    ret

joint_rank:
    addi sp,sp,-16
    li t0,0
    addi t6,a2,3
.Ljoint_scan:
    add t1,a0,t0
    lbu t2,0(t1)
    bltu t2,a2,4f
    bgeu t2,t6,4f
    sub t2,t2,a2
    add t3,sp,t2
    sb t0,0(t3)
    add t1,a1,t0
    lbu t4,0(t1)
    sb t4,3(t3)
4:  addi t0,t0,1
    li t1,7
    bltu t0,t1,.Ljoint_scan
    lbu a3,0(sp)
    lbu a4,1(sp)
    lbu a5,2(sp)
    sltu t0,a3,a4
    sub a4,a4,t0
    lbu t1,1(sp)
    sltu t0,a3,a5
    sltu t1,t1,a5
    sub a5,a5,t0
    sub a5,a5,t1
    slli t0,a3,1
    add t0,t0,a3
    slli t0,t0,1
    add t0,t0,a4
    slli t1,t0,2
    add t0,t0,t1
    add t0,t0,a5
    slli a0,t0,5
    slli t1,t0,2
    sub a0,a0,t1
    sub a0,a0,t0
    lbu t0,3(sp)
    slli t1,t0,3
    add t0,t0,t1
    lbu t1,4(sp)
    slli t2,t1,1
    add t1,t1,t2
    add a0,a0,t0
    add a0,a0,t1
    lbu t0,5(sp)
    add a0,a0,t0
    addi sp,sp,16
    ret

physical_quarter:
    slli t0,a0,3
    sub t0,t0,a0
    la t1,source_map
    add t1,t1,t0
    la t2,twist_map
    add t2,t2,t0
    la t5,cubie_p
    la a1,cubie_o
    la t6,temp_p
    la a2,temp_o
    li t0,7
.Lphysical:
    lbu t3,0(t1)
    add t4,t5,t3
    lbu t4,0(t4)
    sb t4,0(t6)
    add t3,a1,t3
    lbu t3,0(t3)
    lbu t4,0(t2)
    add t3,t3,t4
    addi t4,t3,-3
    bltz t4,5f
    mv t3,t4
5:  sb t3,0(a2)
    addi t1,t1,1
    addi t2,t2,1
    addi t6,t6,1
    addi a2,a2,1
    addi t0,t0,-1
    bnez t0,.Lphysical
    la t6,temp_p
    la a2,temp_o
    li t0,7
.Lcopy:
    lbu t3,0(t6)
    sb t3,0(t5)
    lbu t3,0(a2)
    sb t3,0(a1)
    addi t6,t6,1
    addi a2,a2,1
    addi t5,t5,1
    addi a1,a1,1
    addi t0,t0,-1
    bnez t0,.Lcopy
    ret
.section .rodata
.balign 2
factorial_weights: .half 720,120,24,6,2,1
source_map: .byte 1,4,2,0,3,5,6,0,1,2,4,5,6,3,0,2,5,3,1,4,6
twist_map: .byte 1,2,0,2,1,0,0,0,0,0,1,2,1,2,0,0,0,0,0,0,0
.balign 4
move_names: .word name_R,name_R2,name_Rp,name_B,name_B2,name_Bp,name_D,name_D2,name_Dp
name_R: .asciz "R "
name_R2: .asciz "R2 "
name_Rp: .asciz "R' "
name_B: .asciz "B "
name_B2: .asciz "B2 "
name_Bp: .asciz "B' "
name_D: .asciz "D "
name_D2: .asciz "D2 "
name_Dp: .asciz "D' "
newline: .asciz "\n"
.section .bss
.balign 4
workspace: .space 204
.globl cubie_p,cubie_o
cubie_p: .space 7
cubie_o: .space 7
temp_p: .space 7
temp_o: .space 7

