OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
  . = 0x1000;
  .text : { *(.text.start) *(.text .text.*) }
  . = ALIGN(4);
  .rodata : { *(.rodata .rodata.*) *(.srodata .srodata.*) }
  . = ALIGN(4);
  .data : { *(.data .data.*) *(.sdata .sdata.*) }
  . = ALIGN(16);
  .bss (NOLOAD) : { *(.bss .bss.*) *(.sbss .sbss.*) *(COMMON) }
  /DISCARD/ : { *(.comment) *(.riscv.attributes) *(.eh_frame*) }
}
