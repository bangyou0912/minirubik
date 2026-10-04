# HackMD 1.2 probe: touch exactly a0 distinct guest bytes, then exit.
#
# Ripes keeps guest memory in an unordered_map keyed by byte address, so one
# hash entry exists per distinct guest byte that the program has written. This
# harness writes one byte to each of a0 consecutive addresses starting at
# 0x20000000, well clear of the program's own .text and .data, so the number
# of live map entries equals a0 exactly.
#
# Byte stores, not word stores, keep the relationship one entry per guest
# byte rather than four entries per store, which makes the host-bytes per
# guest-byte ratio read directly off the resident-set delta.
#
# a0 is set from the host with --reginit gpr:10=N.
.text
.globl main
main:
    li   t0, 0x20000000      # probe region base
    mv   t1, a0              # bytes remaining
    li   t2, 0x5a            # payload, any nonzero value
    beqz t1, probe_done

probe_loop:
    sb   t2, 0(t0)
    addi t0, t0, 1
    addi t1, t1, -1
    bnez t1, probe_loop

probe_done:
    mv   a0, zero
    li   a7, 10
    ecall
