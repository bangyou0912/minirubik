/* GUI-only LED renderer. Base/dimensions are supplied by the real peripheral.
 * RENDER_TEST uses a RAM stand-in and compares every pixel after every move.
 */
#ifndef RENDER_DELAY
#define RENDER_DELAY 250000
#endif
.section .text
.globl render_cube
render_cube:
    li t1,LED_MATRIX_0_WIDTH
    li t2,LED_MATRIX_0_HEIGHT
    li t3,35
    bne t1,t3,.Rdone
    li t3,25
    bne t2,t3,.Rdone
    li t3,LED_MATRIX_0_BASE
.Rclear_row:
    mv t4,t1
.Rclear_pixel:
    sw zero,0(t3)
    addi t3,t3,4
    addi t4,t4,-1
    bnez t4,.Rclear_pixel
    addi t2,t2,-1
    bnez t2,.Rclear_row
    la t0,facelet_map
    li t1,24
.Rfacelet:
    lbu t2,0(t0)
    lbu t3,1(t0)
    beqz t2,.Rfixed
    addi t5,t2,-1
    la t4,cubie_o
    add t4,t4,t5
    lbu t4,0(t4)
    sub t3,t3,t4
    bgez t3,1f
    addi t3,t3,3
1:  la t4,cubie_p
    add t4,t4,t5
    lbu t2,0(t4)
    addi t2,t2,1
.Rfixed:
    slli t4,t2,1
    add t4,t4,t2
    add t4,t4,t3
    la t5,corner_colors
    add t4,t4,t5
    lbu t4,0(t4)
    slli t4,t4,2
    la t5,face_palette
    add t4,t4,t5
    lw t6,0(t4)
    lbu t4,2(t0)
    lbu t5,3(t0)
    li a1,LED_MATRIX_0_WIDTH
    slli a1,a1,2
    slli t4,t4,2
    li a0,LED_MATRIX_0_BASE
    add a0,a0,t4
    beqz t5,.Raddressed
.Ry:
    add a0,a0,a1
    addi t5,t5,-1
    bnez t5,.Ry
.Raddressed:
    li a4,3
.Rtile_row:
    mv a2,a0
    li a3,4
.Rtile_pixel:
    sw t6,0(a2)
    addi a2,a2,4
    addi a3,a3,-1
    bnez a3,.Rtile_pixel
    add a0,a0,a1
    addi a4,a4,-1
    bnez a4,.Rtile_row
    addi t0,t0,4
    addi t1,t1,-1
    bnez t1,.Rfacelet
    la t0,render_frames
    lw t1,0(t0)
#ifdef RENDER_TEST
    /* Reference is host C generated; only the renderer test links it. */
    la t2,expected_frames
    li t3,3500
    mv t4,t1
    beqz t4,.Rreference
.Rframe_offset:
    add t2,t2,t3
    addi t4,t4,-1
    bnez t4,.Rframe_offset
.Rreference:
    li t3,LED_MATRIX_0_BASE
    li t4,875
.Rverify:
    lw t5,0(t2)
    lw t6,0(t3)
    beq t5,t6,2f
    la a0,render_fault
    li a1,1
    sw a1,0(a0)
2:  addi t2,t2,4
    addi t3,t3,4
    addi t4,t4,-1
    bnez t4,.Rverify
#endif
    addi t1,t1,1
    sw t1,0(t0)
    li t0,RENDER_DELAY
    beqz t0,.Rdone
.Rdelay:
    addi t0,t0,-1
    bnez t0,.Rdelay
.Rdone:
    ret
#include "renderer_data.inc"
.section .data
.balign 4
.globl render_frames
render_frames: .word 0
#ifdef RENDER_TEST
.globl render_fault
render_fault: .word 0
#endif
