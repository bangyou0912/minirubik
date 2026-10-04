.data
.globl cube_input
cube_input:
    .asciz "21345671111111"

.text
.globl main
main:
    la s0, cube_input
    mv a0, s0
    jal ra, parse_ida_coords
    bnez a3, main_invalid

    mv s1, a0
    mv s2, a1
    mv s3, a2

# RENDER_BEGIN
    # Keep a physical cube state for the renderer
    mv a0, s0
    jal ra, pack_ascii_state
    mv s4, a0
    mv s5, a1
# RENDER_END

    mv a0, s1
    mv a1, s2
    mv a2, s3
    jal ra, ida_solve
    bltz a0, main_invalid

    mv s6, a0
    mv s7, a1

# RENDER_BEGIN
    # Redraw the initial state and every state on the returned path
    mv a0, s4
    mv a1, s5
    mv a2, s6
    mv a3, s7
    jal ra, led_animate_solution
# RENDER_END

    # Leave the solution result in a0 and a1 for inspection
    mv a0, s6
    mv a1, s7
    j main_exit

main_invalid:
    li a0, -1
    li a1, 0

main_exit:
    li a7, 10
    ecall
