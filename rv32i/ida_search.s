.text
.globl ida_solve

# a0 is the permutation coordinate
# a1 is the joint A coordinate
# a2 is the joint B coordinate
# Returns the optimal move count in a0
# Returns a pointer to move bytes in a1
# Returns minus one in a0 if no solution exists through depth 11
ida_solve:
    addi sp, sp, -48
    sw s0, 0(sp)
    sw s1, 4(sp)
    sw s2, 8(sp)
    sw s3, 12(sp)
    sw s4, 16(sp)
    sw s5, 20(sp)
    sw s6, 24(sp)
    sw s7, 28(sp)
    sw s8, 32(sp)
    sw s9, 36(sp)
    sw s10, 40(sp)
    sw s11, 44(sp)

    la s0, perm_transition
    la s1, joint_a_transition
    la s2, joint_b_transition
    la s3, perm_pdb
    la s4, joint_a_pdb
    la s5, joint_b_pdb
    la s6, ida_frames
    la s7, ida_solution_moves
    li s10, 11

    sh a0, 0(s6)
    sh a1, 2(s6)
    sh a2, 4(s6)
    sb zero, 6(s6)
    li t0, 3
    sb t0, 7(s6)
    sb zero, 8(s6)

    # The initial threshold is the maximum of all three PDB values
    add t0, s3, a0
    lbu t1, 0(t0)
    add t0, s4, a1
    lbu t2, 0(t0)
    bgeu t1, t2, ida_root_max_a_done
    mv t1, t2
ida_root_max_a_done:
    add t0, s5, a2
    lbu t2, 0(t0)
    bgeu t1, t2, ida_root_max_b_done
    mv t1, t2
ida_root_max_b_done:
    beqz t1, ida_root_solved
    mv s8, t1
    bgtu s8, s10, ida_not_found

ida_begin_iteration:
    li s9, 0
    mv s11, s6
    sb zero, 6(s6)
    li t0, 3
    sb t0, 7(s6)

ida_search_loop:
    # s11 always points at the current 12-byte frame
    mv t0, s11

    lbu a3, 6(t0)
    li t1, 9
    bgeu a3, t1, ida_frame_exhausted
    addi t1, a3, 1
    sb t1, 6(t0)

    # Decode the face and number of quarter turns
    li t1, 3
    bltu a3, t1, ida_face_r
    li t1, 6
    bltu a3, t1, ida_face_b
    li a4, 2
    addi a5, a3, -5
    j ida_face_ready
ida_face_b:
    li a4, 1
    addi a5, a3, -2
    j ida_face_ready
ida_face_r:
    li a4, 0
    addi a5, a3, 1

ida_face_ready:
    lbu t1, 7(t0)
    beq t1, a4, ida_search_loop
    lhu a0, 0(t0)
    lhu a1, 2(t0)
    lhu a2, 4(t0)
    slli a7, a4, 1

ida_turn_loop:
    # Each transition row contains R, B, and D halfwords
    slli t0, a0, 1
    slli t1, a0, 2
    add t0, t0, t1
    add t0, t0, a7
    add t0, s0, t0
    lhu a0, 0(t0)

    slli t0, a1, 1
    slli t1, a1, 2
    add t0, t0, t1
    add t0, t0, a7
    add t0, s1, t0
    lhu a1, 0(t0)

    slli t0, a2, 1
    slli t1, a2, 2
    add t0, t0, t1
    add t0, t0, a7
    add t0, s2, t0
    lhu a2, 0(t0)

    addi a5, a5, -1
    bnez a5, ida_turn_loop

    # Compute the child heuristic
    add t0, s3, a0
    lbu t2, 0(t0)
    add t0, s4, a1
    lbu t3, 0(t0)
    bgeu t2, t3, ida_child_max_a_done
    mv t2, t3
ida_child_max_a_done:
    add t0, s5, a2
    lbu t3, 0(t0)
    bgeu t2, t3, ida_child_max_b_done
    mv t2, t3
ida_child_max_b_done:

    addi a6, s9, 1
    add t3, a6, t2
    bgtu t3, s8, ida_search_loop
    beqz t2, ida_found

    # Record the path move and push the child frame
    add t0, s7, s9
    sb a3, 0(t0)
    addi t0, s11, 12
    sh a0, 0(t0)
    sh a1, 2(t0)
    sh a2, 4(t0)
    sb zero, 6(t0)
    sb a4, 7(t0)
    sb a6, 8(t0)
    mv s9, a6
    mv s11, t0
    j ida_search_loop

ida_frame_exhausted:
    beqz s9, ida_iteration_exhausted
    addi s9, s9, -1
    addi s11, s11, -12
    j ida_search_loop

ida_iteration_exhausted:
    addi s8, s8, 1
    bgtu s8, s10, ida_not_found
    j ida_begin_iteration

ida_found:
    add t0, s7, s9
    sb a3, 0(t0)
    mv a0, a6
    mv a1, s7
    j ida_return

ida_root_solved:
    li a0, 0
    mv a1, s7
    j ida_return

ida_not_found:
    li a0, -1
    mv a1, s7

ida_return:
    lw s0, 0(sp)
    lw s1, 4(sp)
    lw s2, 8(sp)
    lw s3, 12(sp)
    lw s4, 16(sp)
    lw s5, 20(sp)
    lw s6, 24(sp)
    lw s7, 28(sp)
    lw s8, 32(sp)
    lw s9, 36(sp)
    lw s10, 40(sp)
    lw s11, 44(sp)
    addi sp, sp, 48
    ret

.data
.align 2
.globl ida_frames
ida_frames:
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

.globl ida_solution_moves
ida_solution_moves:
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
