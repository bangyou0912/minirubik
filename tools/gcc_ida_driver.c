/* Measurement driver for the GCC-compiled C search, the counterpart of
 * tools/ida_only_harness.s. Ripes sets a0, a1, a2 to the three starting
 * coordinates with --reginit; _start leaves them untouched and calls
 * c_entry, which returns the path length in a0. The returned moves are
 * left in c_solution for inspection.
 *
 * Build: riscv64-unknown-elf-gcc -O2 -march=rv32i -mabi=ilp32 -nostdlib
 *        -Wl,--no-relax -Irv32i tools/gcc_ida_driver.c
 * --no-relax keeps the linker from emitting gp-relative accesses, since
 * nothing here initializes gp.
 */
#include "../rv32i/ida_reference.c"

cube_u8 c_solution[11];

int c_entry(unsigned perm, unsigned joint_a, unsigned joint_b)
{
    return ida_solve_c((cube_u16)perm, (cube_u16)joint_a,
                       (cube_u16)joint_b, c_solution);
}

__asm__(".section .text.start\n"
        ".globl _start\n"
        "_start:\n"
        "    call c_entry\n"
        "    li a7, 10\n"
        "    ecall\n");
