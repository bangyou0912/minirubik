# Test harness, not part of the graded solution: calls ida_solve, then
# REPLAYS the returned move sequence against the already-verified
# coordinate transition tables to confirm it actually reaches the goal --
# not just that a length came back. Zero search/cube-design logic of its
# own: the decode-and-apply loop below is the same mechanical pattern
# already present in ida_search.s and quarter_turn/apply_move, re-executed
# independently as a checker.
#
# Set x10/x11/x12 via --reginit to the starting perm/jointA/jointB
# coordinates. Avoid parentheses inside '#' comments -- Ripes's assembler
# misreads them as unmatched parentheses.
#
# Returns:
#   a0 = path length from ida_solve -1 means not found
#   a1 = final perm coordinate after replaying the moves should be 0
#   a2 = final joint A coordinate after replay should be 0
#   a3 = final joint B coordinate after replay should be 2916
# When a0 is -1, a1 a2 a3 are meaningless replay did not run.
.text
.globl main
main:
    mv s1, a0
    mv s2, a1
    mv s3, a2

    jal ra, ida_solve
    mv s4, a0
    mv s5, a1

    mv t0, s1
    mv t1, s2
    mv t2, s3

    la s6, perm_transition
    la s7, joint_a_transition
    la s8, joint_b_transition

    li s9, 0

replay_check:
    bge s9, s4, replay_done

    add t3, s5, s9
    lbu a3, 0(t3)

    li t4, 3
    bltu a3, t4, replay_face_r
    li t4, 6
    bltu a3, t4, replay_face_b
    li a4, 2
    addi a5, a3, -5
    j replay_face_ready
replay_face_b:
    li a4, 1
    addi a5, a3, -2
    j replay_face_ready
replay_face_r:
    li a4, 0
    addi a5, a3, 1
replay_face_ready:
    slli a7, a4, 1

replay_turn_loop:
    slli t3, t0, 1
    slli t4, t0, 2
    add t3, t3, t4
    add t3, t3, a7
    add t3, s6, t3
    lhu t0, 0(t3)

    slli t3, t1, 1
    slli t4, t1, 2
    add t3, t3, t4
    add t3, t3, a7
    add t3, s7, t3
    lhu t1, 0(t3)

    slli t3, t2, 1
    slli t4, t2, 2
    add t3, t3, t4
    add t3, t3, a7
    add t3, s8, t3
    lhu t2, 0(t3)

    addi a5, a5, -1
    bnez a5, replay_turn_loop

    addi s9, s9, 1
    j replay_check

replay_done:
    mv a0, s4
    mv a1, t0
    mv a2, t1
    mv a3, t2
    li a7, 10
    ecall
