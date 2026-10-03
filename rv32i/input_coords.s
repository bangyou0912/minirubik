.text
.globl parse_ida_coords

# a0 points to a NUL-terminated 14-character state string
# Returns permutation, joint A, and joint B in a0, a1, and a2
# Returns zero in a3 on success and minus one on invalid input
parse_ida_coords:
    addi sp, sp, -64
    sw s0, 32(sp)
    sw s1, 36(sp)
    sw s2, 40(sp)
    sw s3, 44(sp)
    sw ra, 60(sp)
    mv s0, a0

    # Parse the seven cubie labels and build position_of
    li t0, 0
    li t1, 0
parse_ida_perm_loop:
    lbu t2, 0(s0)
    li t3, 49
    bltu t2, t3, parse_ida_invalid
    li t3, 56
    bgeu t2, t3, parse_ida_invalid
    addi t2, t2, -49

    li t3, 1
    sll t3, t3, t2
    and t4, t1, t3
    bnez t4, parse_ida_invalid
    or t1, t1, t3

    add t4, sp, t0
    sb t2, 0(t4)
    addi t4, sp, 16
    add t4, t4, t2
    sb t0, 0(t4)

    addi s0, s0, 1
    addi t0, t0, 1
    li t3, 7
    bltu t0, t3, parse_ida_perm_loop

    # Parse orientations and accumulate their sum
    li t0, 0
    li t1, 0
parse_ida_orientation_loop:
    lbu t2, 0(s0)
    li t3, 49
    bltu t2, t3, parse_ida_invalid
    li t3, 52
    bgeu t2, t3, parse_ida_invalid
    addi t2, t2, -49

    addi t4, sp, 8
    add t4, t4, t0
    sb t2, 0(t4)
    add t1, t1, t2

    addi s0, s0, 1
    addi t0, t0, 1
    li t3, 7
    bltu t0, t3, parse_ida_orientation_loop

    # Require exactly 14 characters
    lbu t2, 0(s0)
    bnez t2, parse_ida_invalid

    # A legal corner orientation sum is zero modulo three
parse_ida_orientation_mod:
    sltiu t2, t1, 3
    bnez t2, parse_ida_orientation_checked
    addi t1, t1, -3
    j parse_ida_orientation_mod
parse_ida_orientation_checked:
    bnez t1, parse_ida_invalid

    # Rank the full permutation with the solver.c Lehmer scheme
    li s1, 0
    li t0, 0
parse_ida_rank_perm_outer:
    add t1, sp, t0
    lbu t2, 0(t1)
    addi t3, t0, 1
    li t4, 0
parse_ida_rank_perm_inner:
    li t5, 7
    bgeu t3, t5, parse_ida_rank_perm_inner_done
    add t1, sp, t3
    lbu t5, 0(t1)
    bgeu t5, t2, parse_ida_rank_perm_not_smaller
    addi t4, t4, 1
parse_ida_rank_perm_not_smaller:
    addi t3, t3, 1
    j parse_ida_rank_perm_inner
parse_ida_rank_perm_inner_done:
    li t6, 7
    sub t6, t6, t0
    li a4, 0
    mv a5, t6
parse_ida_rank_perm_multiply:
    beqz a5, parse_ida_rank_perm_multiply_done
    add a4, a4, s1
    addi a5, a5, -1
    j parse_ida_rank_perm_multiply
parse_ida_rank_perm_multiply_done:
    add s1, a4, t4
    addi t0, t0, 1
    li t1, 7
    bltu t0, t1, parse_ida_rank_perm_outer

    li a4, 0
    jal ra, parse_ida_joint_coord
    mv s2, a4
    li a4, 3
    jal ra, parse_ida_joint_coord
    mv s3, a4

    mv a0, s1
    mv a1, s2
    mv a2, s3
    li a3, 0
    j parse_ida_return

parse_ida_invalid:
    li a0, 0
    li a1, 0
    li a2, 0
    li a3, -1

parse_ida_return:
    lw s0, 32(sp)
    lw s1, 36(sp)
    lw s2, 40(sp)
    lw s3, 44(sp)
    lw ra, 60(sp)
    addi sp, sp, 64
    ret

# a4 selects the first tracked cubie, either zero or three
# Uses parsed permutation data in the caller frame
# Returns the joint coordinate in a4
parse_ida_joint_coord:
    addi t0, sp, 16
    add t0, t0, a4
    lbu t1, 0(t0)
    lbu t2, 1(t0)
    lbu t3, 2(t0)

    # Rank three ordered positions selected from seven
    sltu t4, t1, t2
    sub t4, t2, t4
    sltu t5, t1, t3
    sub t5, t3, t5
    sltu t6, t2, t3
    sub t5, t5, t6

    slli t6, t1, 5
    slli a5, t1, 1
    sub t6, t6, a5
    slli a5, t4, 2
    add a5, a5, t4
    add t6, t6, a5
    add t6, t6, t5

    # Multiply the position rank by 27
    slli a5, t6, 5
    slli a6, t6, 2
    sub a5, a5, a6
    sub t6, a5, t6

    # Append the three base-three orientations
    addi t0, sp, 8
    add a5, t0, t1
    lbu a5, 0(a5)
    add a6, t0, t2
    lbu a6, 0(a6)
    add a7, t0, t3
    lbu a7, 0(a7)
    slli t0, a5, 3
    add t0, t0, a5
    slli t4, a6, 1
    add t4, t4, a6
    add t0, t0, t4
    add t0, t0, a7
    add a4, t6, t0
    ret
