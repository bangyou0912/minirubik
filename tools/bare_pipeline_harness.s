# Test harness, not part of the graded solution: parse_ida_coords then
# ida_solve, nothing else -- no replay check, so retired-instruction count
# matches exactly what the actual solve costs, for direct comparison
# against whatever the student measured for the same two calls.
#
# Avoid parentheses inside '#' comments -- Ripes's assembler misreads
# them as unmatched parentheses.
#
# test_string label is provided by the caller, same convention as
# full_pipeline_harness.s.
#
# Returns: a0 = path length from ida_solve, -1 if rejected.
.text
.globl main
main:
    la a0, test_string
    jal ra, parse_ida_coords
    bnez a3, bare_pipeline_reject
    jal ra, ida_solve
    j bare_pipeline_exit
bare_pipeline_reject:
    li a0, -1
bare_pipeline_exit:
    li a7, 10
    ecall
