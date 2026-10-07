## Stage 3: Improving Efficiency in C

### 3.1 Scope and Comparison Method

Stage 3 preserves the three-coordinate representation, PDB contents, IDA* bounds, move order, and consecutive-face pruning selected in Stage 2. The goal is to reduce the work performed per generated edge without changing which edges are searched or which optimal solution is returned.

Eight C variants were compared: the Stage 2 control, delayed child-frame creation, and six early-cutoff PDB orders. All variants were run on every one of the **2,644 distance-11 states**, plus the solved state. For every input, they returned the same length, exact move sequence, and generated-edge count as the original Stage 2 implementation.

The counters record logical C operations: coordinate-transition reads, PDB reads, frame initializations, solution-path writes, and comparisons. They include all IDA* iterations. They are not hardware memory-access measurements or Ripes retired-instruction counts.

The adopted implementation is `target/stage3/search.c`, using delayed frame creation and the PDB order **joint A, joint B, permutation (ABP)**.

### 3.2 Reject Children Before Writing Their Frames

The original C search generated a child, wrote its path entry and full frame, advanced the stack, and only then evaluated the child's heuristic. A rejected child therefore incurred frame initialization and stack-entry processing before immediately returning to its parent.

The revised order is:

```text
Advance all three coordinates
Check the candidate against the remaining-depth limit
If rejected, continue enumerating the parent's moves
Otherwise, write the path entry
If solved, return the solution
Otherwise, initialize the child frame and descend
```

Of the **191,546,980** edges generated across all distance-11 inputs, **159,629,656** were rejected by the heuristic. Delaying the writes prevents these rejected candidates from receiving a child frame or path entry. A solved child also returns directly without requiring a frame.

| Logical operation | Stage 2 control | Delayed-frame variant | Reduction |
|---|---:|---:|---:|
| Frame initializations, including roots | 191,563,876 | 31,931,576 | 83.33% |
| Solution-path writes | 191,546,980 | 31,917,324 | 83.34% |
| Generated edges | 191,546,980 | 191,546,980 | 0% |

This changes when state is committed to the stack, not the search tree. The revised loop also removes the per-dispatch `face == 255` entry check used by the control: a frame is entered only after its candidate has already passed pruning.

### 3.3 Replace the Inner-Loop Maximum with Early Cutoffs

The root needs the numerical value

\[
h=\max(h_{\mathrm{perm}},h_A,h_B)
\]

to choose the first IDA* bound. For a child, however, the search only needs to know whether this maximum exceeds the remaining depth.

The equivalent cutoff can be evaluated incrementally:

```c
if (joint_A_distance[a] > remaining)
    reject;
if (joint_B_distance[b] > remaining)
    reject;
if (permutation_distance[p] > remaining)
    reject;
```

Once one PDB rejects the child, later PDBs need not be read. The numerical maximum is still computed once per input to establish the first bound. Root rejection checks within later iterations are unnecessary because each bound is at least the root's heuristic.

All six PDB orders were evaluated on the complete distance-11 set. Here, P means permutation, A means joint A, and B means joint B.

| PDB order | Total PDB reads |
|---|---:|
| PAB | 329,846,059 |
| PBA | 335,184,028 |
| APB | 318,314,654 |
| **ABP, adopted** | **317,244,628** |
| BPA | 333,669,221 |
| BAP | 327,261,226 |

ABP minimizes the aggregate PDB-read count over this test set. This does not establish that it is best for every individual input or that it minimizes retired instructions.

There is a comparison tradeoff: early cutoffs perform more direct threshold comparisons, but eliminate almost all comparisons used to construct a maximum.

| Comparison category | Stage 2 control | Adopted ABP variant |
|---|---:|---:|
| Comparisons used to compute maxima | 383,133,040 | 5,288 |
| Remaining-depth comparisons | 191,563,876 | 317,236,696 |
| **Combined logical comparisons** | **574,696,916** | **317,241,984** |

These logical comparisons must not be interpreted as an equal number of branch instructions. Compiler lowering, branch outcomes, and pipeline penalties determine the actual target cost.

### 3.4 Preserve All Coordinate Updates

Every generated edge still performs three transition reads: one for permutation and one for each joint coordinate.

The search enumerates a face's quarter, half, and inverse turns by repeatedly advancing its cached child coordinates. Even if the first PDB rejects a quarter-turn candidate, all three coordinates must remain advanced so the next update produces the correct half-turn candidate.

Therefore, early rejection skips subsequent **distance-table reads**, not coordinate transitions. The aggregate transition-read count remains **574,640,940**, exactly three times the generated-edge count. This distinction prevents an optimization from corrupting later candidates on the same face.

### 3.5 Remove Diagnostic Work and Audit RV32I Arithmetic

Operation counters are enabled only in comparison builds through `S3_COUNT`. In the production build, preprocessing removes the counter accesses and their conditional checks. In particular, 64-bit edge and visit accounting does not run in the target search.

The coordinate representation already avoids division, remainder, and full-state re-ranking in the search loop. Stage 3 retains this property. The C was compiled for RV32I for inspection using:

```text
-O2 -std=c99 -march=rv32i -mabi=ilp32 -ffreestanding
```

The compiler-output audit found:

| Check | Result |
|---|---|
| Multiply or divide instructions | None |
| Multiply, divide, or remainder helper calls | None |
| Production diagnostic-counter accesses | None |

The 16-byte frame stride permits shift-based indexing, and 16-bit transition entries use a two-byte stride. Constant multiplications in coordinate encoding are synthesized using base-integer instructions.

Local pointers were introduced for the active permutation and joint transition rows. Inspection showed that the compiler still synthesizes the non-power-of-two face-row strides using shifts and additions inside the search loop. Consequently, no reduction in addressing cost is attributed to that source-level change.

This compiler output is an audit of C compatibility and lowering, not the final hand-written Stage 4 assembly program and not a retired-instruction measurement.

### 3.6 Operation-Count Results

Across the complete distance-11 set, the selected implementation reduces PDB reads and workspace writes while preserving the search tree:

| Operation | Stage 2 control | Selected Stage 3 | Reduction |
|---|---:|---:|---:|
| Generated edges | 191,546,980 | 191,546,980 | 0% |
| Transition reads | 574,640,940 | 574,640,940 | 0% |
| PDB reads | 574,699,560 | 317,244,628 | **44.80%** |
| Frame initializations | 191,563,876 | 31,931,576 | **83.33%** |
| Solution-path writes | 191,546,980 | 31,917,324 | **83.34%** |

The selected variant produces the following results on the specified vector and the maximum-edge distance-11 state:

| Input | Operation | Stage 2 control | Selected Stage 3 |
|---|---|---:|---:|
| `21345671111111` | Generated edges | 87,021 | 87,021 |
| | PDB reads | 261,081 | 145,410 |
| | Frame initializations | 87,026 | 14,508 |
| | Solution-path writes | 87,021 | 14,504 |
| `54721631111111` | Generated edges | 238,434 | 238,434 |
| | PDB reads | 715,323 | 393,703 |
| | Frame initializations | 238,440 | 39,742 |
| | Solution-path writes | 238,434 | 39,737 |

The table layout and workspace sizes are unchanged: **80,640 bytes of tables plus 204 bytes of workspace**, leaving **50,228 bytes** within the 128 KiB budget for later input/output data and alignment. Diagnostic counters are excluded from this target-data subtotal. The final linked section sizes still need checking in Stage 4.

### 3.7 Correctness Verification

The selected production build, with counters compiled out, was tested against the full baseline BFS oracle over **all 3,674,160 legal states**. Every returned length matched the exact BFS distance, and every returned sequence was replayed through the full cubie model to confirm that it solved the cube.

| Verification | Result |
|---|---|
| All eight counted variants versus original Stage 2, 2,644 hard states plus solved state | Identical lengths, move sequences, and edge counts |
| Production shortest-path check | 3,674,160 / 3,674,160 passed |
| H3 wall-clock time | 246.73 s |
| H4 packed accessors | Not applicable: byte PDBs and uint16 transitions |
| Full-cubie solution replay | 3,674,160 / 3,674,160 passed |
| Workspace boundary guards, move ranges, and consecutive-face checks | Passed |
| Out-of-range coordinate rejection | Passed |
| ASan and UBSan | Passed on all eight supplied solution vectors, a three-move scramble, and the maximum-edge state |

The exhaustive production check used GCC 11.4.0 with `-O3 -std=c99` under WSL Ubuntu 22.04 and reported **246.643 CPU seconds**. The 2026-10-07 H3 revalidation took **246.73 seconds (4 min 6.73 s)**, recorded by `/usr/bin/time -p` in `target/stage3/wall-time.txt`. These are verification durations, not a controlled solver-speed comparison. The arithmetic audit used the RISC-V GCC 10.2.0 toolchain.

Because the representation, heuristic, pruning condition, and search order are preserved, the Stage 2 shortest-path argument still applies. The exhaustive checks verify that the C changes implement those choices correctly relative to the baseline move model.

### 3.8 Reproduction and Next Measurement

Run these commands from the repository root:

```sh
# Compare eight counted C variants on all distance-11 states.
make -f target/stage3/Makefile compare

# Summarize existing operation counts and inspect RV32I compiler output.
python3 target/stage3/summarize.py

# Verify the production search over all legal states.
make -f target/stage3/Makefile check

# Run the representative ASan/UBSan checks.
make -f target/stage3/Makefile sanitize
```

The raw per-input counts are in `target/stage3/operations.csv`. Aggregate results are in `target/stage3/results.json`; correctness logs are in `all-state-verification.txt` and `sanitizer-verification.txt` in the same directory.

Stage 3 establishes reductions in logical table reads, comparisons, and workspace writes. It does not establish a percentage speedup or compliance with the 50-million-instruction limit. Stage 4 must translate the selected C structure and measure the actual renderer-off program with Ripes `--iret`, including all 2,644 distance-11 inputs.
