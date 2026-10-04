.equ LED_FRAME_DELAY, 6000

.text
.globl pack_ascii_state
.globl led_facelet_rgb
.globl led_clear
.globl led_render_cube
.globl led_animate_solution

# a0 points to a validated 14-character state string
# Returns packed permutation in a0 and packed orientation in a1
pack_ascii_state:
    mv t0, a0
    li t1, 0
    li t2, 0
    li t3, 0
pack_ascii_perm_loop:
    lbu t4, 0(t0)
    addi t4, t4, -49
    sll t4, t4, t3
    or t1, t1, t4
    addi t0, t0, 1
    addi t2, t2, 1
    addi t3, t3, 3
    li t5, 7
    bltu t2, t5, pack_ascii_perm_loop

    li t2, 0
    li t3, 0
    li t6, 0
pack_ascii_orientation_loop:
    lbu t4, 0(t0)
    addi t4, t4, -49
    sll t4, t4, t3
    or t6, t6, t4
    addi t0, t0, 1
    addi t2, t2, 1
    addi t3, t3, 2
    li t5, 7
    bltu t2, t5, pack_ascii_orientation_loop

    mv a0, t1
    mv a1, t6
    ret

# a0 is packed permutation data
# a1 is packed orientation data
# a2 is a facelet index from zero through twenty-three
# Returns the 24-bit RGB value in a0
led_facelet_rgb:
    la t0, led_facelet_map
    add t0, t0, a2
    lbu t1, 0(t0)
    srli t2, t1, 2
    andi t3, t1, 3

    li t4, 7
    beq t2, t4, led_facelet_fixed_corner

    slli t4, t2, 1
    add t4, t4, t2
    srl t5, a0, t4
    andi t5, t5, 7

    slli t4, t2, 1
    srl t6, a1, t4
    andi t6, t6, 3
    j led_facelet_corner_ready

led_facelet_fixed_corner:
    li t5, 7
    li t6, 0

led_facelet_corner_ready:
    add t3, t3, t6
    sltiu t4, t3, 3
    bnez t4, led_facelet_orientation_ready
    addi t3, t3, -3
led_facelet_orientation_ready:
    slli t4, t5, 1
    add t4, t4, t5
    add t4, t4, t3
    la t0, led_cubie_colors
    add t0, t0, t4
    lbu t1, 0(t0)
    slli t1, t1, 2
    la t0, led_rgb_colors
    add t0, t0, t1
    lw a0, 0(t0)
    ret

# Clears the configured LED Matrix to black
led_clear:
    li t0, LED_MATRIX_0_BASE
    li t1, LED_MATRIX_0_HEIGHT
    li t2, LED_MATRIX_0_WIDTH
led_clear_row:
    mv t3, t2
led_clear_column:
    sw zero, 0(t0)
    addi t0, t0, 4
    addi t3, t3, -1
    bnez t3, led_clear_column
    addi t1, t1, -1
    bnez t1, led_clear_row
    ret

# a0 is packed permutation data
# a1 is packed orientation data
# Draws a 35 by 20 unfolded cube net in the 35 by 25 matrix
led_render_cube:
    addi sp, sp, -48
    sw ra, 0(sp)
    sw s0, 4(sp)
    sw s1, 8(sp)
    sw s2, 12(sp)
    sw s3, 16(sp)
    sw s4, 20(sp)
    sw s5, 24(sp)
    sw s6, 28(sp)
    sw s7, 32(sp)

    mv s0, a0
    mv s1, a1
    li s2, 0
    li s7, 24

led_render_facelet_loop:
    mv a0, s0
    mv a1, s1
    mv a2, s2
    jal ra, led_facelet_rgb
    mv s3, a0

    srli t0, s2, 2
    slli t0, t0, 1
    la t1, led_face_origins
    add t1, t1, t0
    lbu s4, 0(t1)
    lbu s5, 1(t1)

    andi t0, s2, 3
    andi t1, t0, 1
    slli t1, t1, 2
    add s4, s4, t1
    srli t0, t0, 1
    slli t1, t0, 1
    add t0, t0, t1
    add s5, s5, t0

    # Form y times width by repeated addition to stay in RV32I
    li t0, LED_MATRIX_0_WIDTH
    li t1, 0
    mv t2, s5
led_render_row_offset:
    beqz t2, led_render_row_offset_done
    add t1, t1, t0
    addi t2, t2, -1
    j led_render_row_offset
led_render_row_offset_done:
    add t1, t1, s4
    slli t1, t1, 2
    li t2, LED_MATRIX_0_BASE
    add t2, t2, t1
    slli s6, t0, 2

    li t3, 3
led_render_pixel_rows:
    sw s3, 0(t2)
    sw s3, 4(t2)
    sw s3, 8(t2)
    sw s3, 12(t2)
    add t2, t2, s6
    addi t3, t3, -1
    bnez t3, led_render_pixel_rows

    addi s2, s2, 1
    bltu s2, s7, led_render_facelet_loop

    lw ra, 0(sp)
    lw s0, 4(sp)
    lw s1, 8(sp)
    lw s2, 12(sp)
    lw s3, 16(sp)
    lw s4, 20(sp)
    lw s5, 24(sp)
    lw s6, 28(sp)
    lw s7, 32(sp)
    addi sp, sp, 48
    ret

led_frame_delay:
    li t0, LED_FRAME_DELAY
led_frame_delay_loop:
    addi t0, t0, -1
    bnez t0, led_frame_delay_loop
    ret

# a0 and a1 are the initial packed permutation and orientation
# a2 is the number of moves and a3 points to the move bytes
# Returns the final packed permutation and orientation in a0 and a1
led_animate_solution:
    addi sp, sp, -32
    sw ra, 0(sp)
    sw s0, 4(sp)
    sw s1, 8(sp)
    sw s2, 12(sp)
    sw s3, 16(sp)
    sw s4, 20(sp)

    mv s0, a0
    mv s1, a1
    mv s2, a2
    mv s3, a3
    li s4, 0

    jal ra, led_clear
    mv a0, s0
    mv a1, s1
    jal ra, led_render_cube
    jal ra, led_frame_delay

led_animate_move_loop:
    bgeu s4, s2, led_animate_done
    add t0, s3, s4
    lbu a0, 0(t0)
    mv a1, s0
    mv a2, s1
    jal ra, apply_move
    mv s0, a0
    mv s1, a1

    mv a0, s0
    mv a1, s1
    jal ra, led_render_cube
    jal ra, led_frame_delay

    addi s4, s4, 1
    j led_animate_move_loop

led_animate_done:
    mv a0, s0
    mv a1, s1
    mv a2, s2
    lw ra, 0(sp)
    lw s0, 4(sp)
    lw s1, 8(sp)
    lw s2, 12(sp)
    lw s3, 16(sp)
    lw s4, 20(sp)
    addi sp, sp, 32
    ret

.data
.align 2

# Face order is U, L, F, R, B, D
led_rgb_colors:
    .word 0xffffff, 0xff8000, 0x00ff00
    .word 0xff0000, 0x0000ff, 0xffff00

# Three sticker colors for each cubie in orientation order
led_cubie_colors:
    .byte 0, 3, 2
    .byte 5, 2, 3
    .byte 5, 1, 2
    .byte 0, 4, 3
    .byte 5, 3, 4
    .byte 5, 4, 1
    .byte 0, 1, 4
    .byte 0, 2, 1

# Each byte packs a position in the high bits and sticker slot below
# Faces contain four entries in row-major order
led_facelet_map:
    .byte 24, 12, 28, 0
    .byte 25, 30, 22, 9
    .byte 29, 2, 10, 5
    .byte 1, 14, 6, 17
    .byte 13, 26, 18, 21
    .byte 8, 4, 20, 16

# Pixel origins for U, L, F, R, B, D
led_face_origins:
    .byte 9, 0, 0, 7, 9, 7, 18, 7, 27, 7, 9, 14
