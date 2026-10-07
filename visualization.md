## Stage 5: LED Matrix Visualization

### LED Renderer

`target/stage4/renderer.S` reads the current full-cubie permutation and orientations. The frontend calls it once for the input state and once after each complete move returned by the solver. Half turns and inverse turns execute their constituent quarter turns before the redraw. No recorded solution or animation is linked into the GUI program.

The GUI source is `target/stage4/ripes/solver-gui.s`. Its input is editable and `expected_length=-1`; it accepts arbitrary legal states. `walkthrough-gui.s` contains the short test and omits delay for stepping. `solved-gui.s` provides a uniform-face smoke test.

The renderer uses `LED_MATRIX_0_BASE`, `LED_MATRIX_0_WIDTH`, and `LED_MATRIX_0_HEIGHT`. It checks Width 35 and Height 25 before writing. A pixel address is `BASE + 4*(y*WIDTH+x)`: the row stride is derived from the WIDTH symbol, and the renderer advances by that stride for successive rows. A swapped width/height produces no draw rather than writing outside the intended net.

| Face | Top-left pixel | Solved color |
|---|---|---|
| U | (9, 0) | White, `0xffffff` |
| L | (0, 7) | Orange, `0xff8000` |
| F | (9, 7) | Green, `0x00c040` |
| R | (18, 7) | Red, `0xff2020` |
| B | (27, 7) | Blue, `0x2060ff` |
| D | (9, 14) | Yellow, `0xffe000` |

Each face contains four 4x3-pixel facelets. The occupied face slots form U above L/F/R/B and D below F. Separator columns are x=8,17,26, and separator rows are y=6,13. The bounding net is 35x20; the bottom five rows remain black. Every frame clears all 875 pixels and paints the 288 facelet pixels.

A corner's three colors are stored in a consistent cyclic order. For a face slot j and twist o, the displayed color uses `(j-o) mod 3`. Since j-o lies in -2..2, one addition of three when negative suffices. The fixed FUL corner is handled explicitly; the other seven read the live cubie arrays. The renderer preserves saved registers and does not alter the search state, path, or cubie arrays.

### One Source Tree, Two Submission Builds

The assemble-time switch is the C-preprocessor definition `RENDER=0` or `RENDER=1`. The frontend uses `#if defined(RENDER) && RENDER`, so explicitly defining zero really removes both renderer calls. The exporter sets `-DRENDER=0` by default and `-DRENDER=1` for `--render`; it appends renderer code/data only for the GUI build. The pinned native Ripes assembler rejected `.if/.endif` in the retained `renderer-switch-probe-result.txt`, so an `.equ` switch in a standalone native file would not work here. Both exports come from the same handwritten source tree. GNU sections are converted to native Ripes directives, and the CLI export contains no peripheral symbols.

Both builds use the same parser, coordinate encoders, search, output, replay, and final goal check. Differences consist of renderer calls, renderer code/data, and its delay loop. The default animation delay is 1,000,000 loop iterations; `--delay 0` is useful for stepping or testing. The delay is omitted from instruction-count and code-size comparison builds. The 128 KiB static-data limit still includes all LED renderer data in the complete GUI build.

The archived renderer-off specified-input ELF in `target/stage4/evidence/asm-r2/21345671111111/solver.elf` has SHA-256:

```text
b4ba9a07c22956b924ea1c9634cfafae5b6358de66abfffd058b132b55656106
```

It retains 1,864 linked text bytes and 81,020 static bytes. The complete distance-11 sweep was rerun on 2026-10-07. Rebuilding under a different checkout path can change non-executed ELF symbol metadata and the whole-file hash; `check_rebuilt_sections.py` checks addresses, sizes and bytes of every allocated program/data section against the archived measured ELFs. All twelve C/R0/R1/R2 rebuilds match those sections. A renderer-enabled link with RAM device constants and delay zero has 2,196 text bytes and 81,168 static bytes. This is a sizing model, not a measurement of an instantiated GUI peripheral. The additional renderer data is 148 bytes: 24 palette bytes, 24 corner-color bytes, 96 facelet-map bytes, and a four-byte frame counter.

The actual standalone GUI export was also audited as a whole, with device constants bound only to allow linking. Its `.data` is **81,168 bytes (79.27 KiB)**, with no separate `.bss` or `.rodata` in that export. All LED palette, corner-color, facelet-map and frame-counter data are included. It leaves **49,904 bytes** below 128 KiB. The renderer directly writes the memory-mapped LED window and allocates no additional framebuffer. Even conservatively adding the 3,500-byte peripheral pixel window gives 84,668 bytes, below the limit. This audit is in `target/stage4/gui-static-budget.json`; it establishes data size, not actual GUI display.

### Renderer Verification

The host C generator `generate_renderer.c` checks sticker movement against independent three-dimensional rotations about the R, B, and D axes. All 1,323 comparisons across moving positions, cubies, twists, faces, and sticker normals passed. This checks both the facelet arrangement and the direction of orientation cycling.

The same host C generator creates pixel fixtures for the input and every returned move of the final C solver. A separate target test links those fixtures and compares every actual framebuffer word after each redraw. It uses RAM at a test address to stand in for the LED device; this checks assembly drawing and row-major addressing, while remaining separate from real peripheral testing. Test-only fixtures and validation code are excluded from the GUI and graded CLI builds.

| Fixture | Frames | ISS --iret | RV32_5S --iret | Result |
|---|---:|---:|---:|---|
| Solved | 1 | 13,503 | 13,502 | All pixels, frame count and cubie replay passed |
| Short | 4 | 53,535 | 53,534 | All pixels, frame count and cubie replay passed |
| Specified distance-11 input | 12 | 3,020,469 | 3,020,468 | All pixels, frame count and cubie replay passed |

Across both models this covers 34 frames and 29,750 word comparisons. `a2=0` means no pixel mismatch and `a3=length+1` confirms the redraw count. These instrumented counts are not solver speed comparisons: they include fixture checking and omit animation delay.

The exported native GUI sources were also assembled and executed in pinned Ripes after replacing only the peripheral symbols with test RAM constants and adding a frame-counter observation. The solved, short, and specified cases produced 1, 4, and 12 frames respectively and passed full-cubie replay. This caught and fixed a GNU `.section .data` directive that the native assembler did not accept. The delivered GUI sources use native `.data` directives.

## Stage 6: Instruction-Level Walkthrough in Ripes

### Actual Five-Stage Trace

A renderer-off run of `26471352122222` on the pinned RV32_5S retired 2,484 instructions over 3,287 cycles. `capture_pipeline.py` retained the actual `--pipeline` report in `pipeline-trace.json`. The report contains the initial cycles 0 through 100, so it establishes the parser sequence below, rather than claiming to show later search edges. `pipeline-events.json` extracts those observations.

| Instruction, first execution | IF | ID | EX | MEM | WB |
|---|---:|---:|---:|---:|---:|
| `lbu t3,0(t0)` | 25 | 26 | 27 | 28 | 29 |
| `addi t3,t3,-49` | 26 | 27 | 29 | 30 | 31 |
| `bgeu t3,t6,.Lfailed` | 27 | 29 | 30 | 31 | 32 |
| `sb t3,0(t5)` | 35 | 36 | 37 | 38 | 39 |

The load fetches the input's first character, '2', whose byte value is 50. The add converts it to internal cubie index 1. The unsigned range check compares 1 against 7 and continues. The store commits that value to `cubie_p[0]`. The trace shows a load-use interlock at cycle 28: the dependent add is delayed, and the following branch also stalls. Forwarding then permits the add and comparison to proceed.

IF fetches the instruction, ID decodes it and reads registers, EX computes the address or comparison, MEM performs the byte access, and WB commits a register result when enabled. A store or branch may appear in the WB column without writing a register; stage occupancy alone does not imply RegWrite.

| Instruction | Expected register-write enable | Expected operand/writeback/PC selection |
|---|---|---|
| `lbu` | 1, destination t3 | Address = t0 + immediate 0; WB selects zero-extended memory byte |
| `addi` | 1, destination t3 | ALU operand B selects immediate -49; WB selects ALU result |
| `bgeu` | 0 | Comparator uses register operands, including forwarded t3; this check selects sequential PC |
| `sb` | 0 | Address = t5 + immediate 0; byte memory-write enabled; store data is 1 |

These signal values follow from the instructions and the query values. The CLI trace measures stage occupancy; it does not capture GUI wire values. The GUI procedure below is the remaining way to observe the register-write and multiplexer signals directly.

Later, the search's `.Ledge` performs three halfword transition loads. Joint-A, joint-B, and permutation byte loads then test the remaining depth. A rejected child branches to `.Lreject` before committing a path or frame. On accepted descent, `.Lcommit` writes three halfword caches and the turn cursor to the parent frame, initializes the next frame, and advances the depth. In the renderer, `sw t6,0(a2)` updates a 32-bit LED word with a palette RGB value; the store's register-write enable remains zero.

### GUI Demonstration Procedure

1. Open the pinned Windows Ripes executable. Select RV32I without ISA extensions.
2. In the I/O tab instantiate one LED Matrix. Set **Width 35** and **Height 25**; Height appears above Width in the panel. Instantiate it before loading the GUI source so its assembler symbols exist.
3. Load `solved-gui.s` and run it with RV32_ISS. Check six uniform, distinguishable faces, the separator rows/columns, and the five unused bottom rows.
4. Load `solver-gui.s` and run it with RV32_ISS. Check the input, each actual output move, and the solved final frame. `render_frames` should finish at 12 for the specified input. Increasing `--delay` when exporting slows the animation.
5. For the signal walkthrough, select RV32_5S and load the renderer-off `ripes/26471352122222.s`. Reset and step the first parser load, dependent add, range branch, and cubie store. The instruction sequence is the same as the recorded CLI trace; compare phases rather than assuming GUI counters use an identical display offset.
6. Inspect the register-file write-enable path, ALU operand mux, writeback mux, forwarding selection, and branch/PC selection. Show the load's memory result entering t3, the load-use bubble, the forwarded arithmetic result at the branch, and the byte write to `cubie_p[0]`.
7. Continue to `.Ledge` and `.Lcommit` to explain cutoff versus accepted descent. Capture the relevant GUI states and their instruction/register values. A renderer store can be stepped separately with `walkthrough-gui.s`.

### Evidence Status and Remaining GUI Gate

Renderer implementation, geometry checks, target pixel comparisons, native-source syntax checks, and the actual five-stage CLI trace are complete. Actual LED-peripheral screenshots, animation observation, and GUI signal inspection are **not yet verified**.

Native app control is unavailable in this session; the available browser controls cannot inspect the Ripes desktop window. Consequently no actual LED peripheral or GUI wire state was inspected. **Manual screenshots required** before claiming those GUI evidence items as passed. The following files are deliberately absent until captured in real Ripes; do not use a mockup or generated image.

| Manual screenshot | What it must show |
|---|---|
| `led-configuration.png` | Actual LED Matrix, Width 35 and Height 25, and peripheral assembler symbols |
| `led-initial.png` | Initial scrambled cube after the first `render_cube` call |
| `led-intermediate.png` | Cube after an actual move from the computed solution, with the move/frame identified |
| `led-solved.png` | Final six uniform faces, successful cubie replay and `render_frames=length+1` |
| `pipeline-load.png` | Parser `lbu`, its stage/PC, register write enable and memory writeback selection |
| `pipeline-load-use.png` | Dependent `addi` interlock/bubble and forwarding selection |
| `pipeline-branch-store.png` | Range-check branch PC choice and `sb` memory update with register write disabled |
| `pipeline-led-store.png` | `sw t6,0(a2)` in MEM, LED address and 24-bit RGB store data |

Store captures in `target/stage4/screenshots/` and add them to HackMD only after inspecting them. Step to the instruction after each `call render_cube` to capture stable initial/intermediate/final frames. For the short test, expect four frames; for the specified distance-11 test, expect twelve. The delay only slows execution and is not a promise that a particular frame will remain visible after the simulator runs to completion.

### Transition Lookup and LED Store Through All Five Stages

The search contains `slli t4,t0,1; add t4,s5,t4; lhu t0,0(t4)`. A transition entry occupies two bytes. The shift converts the coordinate to its byte offset, and the add combines it with the selected face-row base. For the `lhu`, IF fetches the actual instruction at PC; ID reads address register t4 and decodes an unsigned halfword load; EX computes t4+0; MEM reads the two little-endian bytes; WB zero-extends the halfword into t0 with register-write enabled. The next two analogous lookups update both joint coordinates before any PDB cutoff. This is a semantic walkthrough; the recorded first-100-cycle trace does not reach this later search loop.

For `sw t6,0(a2)` in the renderer, IF fetches the store and ID reads a2 and t6. EX computes a2+0 with the immediate selected as the ALU's second operand. MEM writes the palette's 32-bit word to the LED's row-major pixel address. WB performs no register write. Advancing a2 by four selects the next column; advancing the tile-row base by `4*WIDTH` selects the next row. The palette values use only the low 24 bits. The separate physical replay updates cubie arrays before rendering, so the colors represent the current cube after the solver's actual move.

### Reproduction

In WSL:

```sh
make -f target/stage4/Makefile renderer gui
python3 target/stage4/build_assembly.py --render-test --vector 12345671111111 --expect 0
python3 target/stage4/build_assembly.py --render-test --vector 26471352122222 --expect 3
python3 target/stage4/build_assembly.py --render-test --vector 21345671111111 --expect 11
```

In Windows PowerShell:

```powershell
$stage4 = (Resolve-Path .\target\stage4).Path
python "$stage4\measure.py" --kind asm-r2-render-test
python "$stage4\test_native_renderer.py"
python "$stage4\capture_pipeline.py"
```

Then in WSL:

```sh
python3 target/stage4/summarize_pipeline.py
```

