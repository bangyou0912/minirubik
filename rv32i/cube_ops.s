.text
.globl quarter_turn
.globl apply_move

# a0 is the face index where 0 is R, 1 is B, and 2 is D
# a1 is packed permutation data with seven 3-bit fields
# a2 is packed orientation data with seven 2-bit fields
# Returns the new packed permutation in a0 and orientation in a1
quarter_turn:
    # R source entries packed as seven 3-bit fields
    li t0, 0x1ab0a1
    # R twist entries packed as seven 2-bit fields
    li t1, 0x189

    beqz a0, quarter_turn_face_selected
    li a3, 1
    beq a0, a3, quarter_turn_face_b

    # D source entries packed as seven 3-bit fields
    li t0, 0x1a1750
    # Every D twist entry is zero
    li t1, 0
    j quarter_turn_face_selected

quarter_turn_face_b:
    # B source entries packed as seven 3-bit fields
    li t0, 0xf5888
    # B twist entries packed as seven 2-bit fields
    li t1, 0x2640

quarter_turn_face_selected:
    mv t3, a1
    mv t4, a2
    li t2, 0
    li t5, 0
    li t6, 0

quarter_turn_loop:
    # Read the source index for this destination
    andi a3, t0, 7

    # Copy the selected permutation field
    slli a4, a3, 1
    add a4, a4, a3
    srl a5, t3, a4
    andi a5, a5, 7
    slli a6, t2, 1
    add a6, a6, t2
    sll a5, a5, a6
    or t5, t5, a5

    # Add the twist and reduce the result modulo 3
    slli a4, a3, 1
    srl a5, t4, a4
    andi a5, a5, 3
    andi a7, t1, 3
    add a5, a5, a7
    sltiu a7, a5, 3
    bnez a7, quarter_turn_mod_done
    addi a5, a5, -3

quarter_turn_mod_done:
    slli a6, t2, 1
    sll a5, a5, a6
    or t6, t6, a5

    srli t0, t0, 3
    srli t1, t1, 2
    addi t2, t2, 1
    li a7, 7
    blt t2, a7, quarter_turn_loop

    mv a0, t5
    mv a1, t6
    ret

# a0 is the move index from 0 through 8
# a1 is packed permutation data
# a2 is packed orientation data
# Returns the new packed permutation in a0 and orientation in a1
apply_move:
    addi sp, sp, -16
    sw ra, 12(sp)
    sw a2, 8(sp)

    # Decode face and turn count by repeated subtraction
    li t0, 0
apply_move_decode:
    sltiu t1, a0, 3
    bnez t1, apply_move_decoded
    addi a0, a0, -3
    addi t0, t0, 1
    j apply_move_decode

apply_move_decoded:
    addi a0, a0, 1
    sw a0, 4(sp)
    sw t0, 0(sp)

apply_move_loop:
    lw a0, 0(sp)
    lw a2, 8(sp)
    jal ra, quarter_turn

    # Feed this result into the next quarter turn
    sw a1, 8(sp)
    mv a1, a0
    lw t0, 4(sp)
    addi t0, t0, -1
    sw t0, 4(sp)
    bnez t0, apply_move_loop

    mv a0, a1
    lw a1, 8(sp)
    lw ra, 12(sp)
    addi sp, sp, 16
    ret
