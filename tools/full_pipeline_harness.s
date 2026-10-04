# Test harness, not part of the graded solution: zero cube logic of its
# own. Parses an ASCII state string via parse_ida_coords, solves it via
# ida_solve, then replays the returned moves through the same verified
# coordinate transition tables to confirm they reach the goal -- the same
# pattern as ida_harness.s, now driven by the raw string instead of
# pre-set coordinate registers, so T5/T6/T7-style checks exercise the
# real input path end to end.
#
# Avoid parentheses inside '#' comments -- Ripes's assembler misreads
# them as unmatched parentheses.
#
# The test string is provided by whichever file defines a `test_string`
# label (see tools/test_full_pipeline.py); this harness only references
# it by name.
#
# Returns:
#   a0 = path length from ida_solve, -1 if parse_ida_coords rejected the
#        input or ida_solve found nothing
#   a1 = final perm coordinate after replay, should be 0 on success
#   a2 = final joint A coordinate after replay, should be 0 on success
#   a3 = final joint B coordinate after replay, should be 2916 on success
.text
.globl main
main:
    la a0, test_string
    jal ra, parse_ida_coords
    bnez a3, pipeline_reject

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

pipeline_replay_check:
    bge s9, s4, pipeline_replay_done

    add t3, s5, s9
    lbu a3, 0(t3)

    li t4, 3
    bltu a3, t4, pipeline_face_r
    li t4, 6
    bltu a3, t4, pipeline_face_b
    li a4, 2
    addi a5, a3, -5
    j pipeline_face_ready
pipeline_face_b:
    li a4, 1
    addi a5, a3, -2
    j pipeline_face_ready
pipeline_face_r:
    li a4, 0
    addi a5, a3, 1
pipeline_face_ready:
    slli a7, a4, 1

pipeline_turn_loop:
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
    bnez a5, pipeline_turn_loop

    addi s9, s9, 1
    j pipeline_replay_check

pipeline_replay_done:
    mv a0, s4
    mv a1, t0
    mv a2, t1
    mv a3, t2
    j pipeline_exit

pipeline_reject:
    li a0, -1

pipeline_exit:
    li a7, 10
    ecall
