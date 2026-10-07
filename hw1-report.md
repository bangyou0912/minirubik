# Phase 1: minirubik on RV32I.

## Environment

| Item | Value |
|---|---|
| Host | Windows + WSL2 Ubuntu 22.04 |
| Host compiler | gcc 11.4.0, `cc -O3 -std=c99` |
| Reference RV32I compiler | `riscv64-unknown-elf-gcc -O2 -march=rv32i -mabi=ilp32`, version 10.2.0 |
| Ripes build, pinned | Windows x86_64 continuous build `Ripes-v2.2.6-106-g5b8a616` |
| Ripes processor | `RV32_ISS` (ISA simulator), ISA RV32I, no extensions (M and C disabled) |
| Baseline | https://github.com/sysprog21/minirubik |
| Fork | https://github.com/bangyou0912/minirubik |
| Working branch | `hw1-redo` |
| Baseline commit | `231796cc48868f4ea276f652139b6bebbad0cd02` |
| Submission tag | Not used; submit the explicit `hw1-redo` branch below |
| Submission branch | https://github.com/bangyou0912/minirubik/tree/hw1-redo |


> Revalidated on 2026-10-07. Stage 1 retains the recovered raw measurements from the pinned installation; H1/H2, H3, the complete target hard-state sweep, C/R0/R1/R2 comparisons, renderer checks and the pipeline trace have been rechecked. Real GUI screenshots remain manual required.

## Stage 1: Characterize the baseline

### 1.1 What the Program Computes

`solver.c` computes a shortest solution for a 2×2×2 Rubik’s Cube using the **half-turn metric (HTM)**, where a 90°, 180°, or 270° face turn each counts as one move.

Before answering a query, the program performs BFS from the solved state over all **3,674,160 reachable states**. When it first discovers a state, it stores the inverse move that returns that state to its predecessor. Following these stored moves produces a shortest solution in at most **11 moves**. Optimality follows from BFS exploring states in nondecreasing distance and every move having unit cost.

### 1.2 How the Program Represents a Cube

The program fixes the front-upper-left corner to eliminate equivalent configurations caused by whole-cube rotations. It represents the remaining seven corners with two arrays:

```c
typedef struct {
    uint8_t p[7], o[7];
} state_t;
```

- `p[i]` identifies the corner cubie occupying position `i`.
- `o[i]` records its orientation as `0`, `1`, or `2`.

There are \(7! = 5,040\) corner permutations. Because the total corner twist must be zero modulo three, only six orientations are independent, giving \(3^6 = 729\) orientation configurations. The total state count is therefore:

$7! \times 3^6 = 5,040 \times 729 = 3,674,160.$

The program encodes the permutation using a Lehmer rank and the first six orientations using a base-three rank. It combines them into a dense array index:

$\text{rank} = p_{\text{rank}} \times 729 + o_{\text{rank}}.$

Every valid state has a unique rank between `0` and `3,674,159`; the solved state has rank `0`.

### 1.3 Invariants the Program Relies On

A valid state must satisfy the following conditions:

1. **Permutation validity:** `p[7]` contains each value from `0` through `6` exactly once.
2. **Orientation validity:** every entry in `o[7]` lies between `0` and `2`.
3. **Twist conservation:**

     $\sum_{i=0}^{6} o[i] \equiv 0 \pmod{3}.$
 
   This determines the seventh orientation from the first six. The corner permutation itself does not have to be even.

Every legal move preserves these conditions. The `source` table describes how corners change positions, while the `twist` table describes their orientation changes. Permutation and orientation evolve independently, allowing the program to use separate transition tables.

Correct solution reconstruction also depends on move invertibility and FIFO queue order. Together, these ensure that each stored inverse move leads to a state exactly one BFS level closer to solved.

### 1.4 Where the Cost Lies

The dominant cost is constructing the complete BFS table before answering each query.

| Allocation | Purpose  | Bytes |
|---|---|---:|
| `toward_solved` | One move toward solved per state  | 3,674,160 |
| `queue` | BFS queue of 32-bit state ranks  | 14,696,640 |
| Factored transition tables | Quarter-turn transitions for permutation and orientation  | 34,614 |
| **Combined peak of these allocations** | | **18,405,414** |

These allocations coexist during construction and total approximately **17.553 MiB**. The queue accounts for about **79.8%** of that total.

BFS expands every state and examines nine moves per state:

$3,674,160 \times 9 = 33,067,440$ edge expansions. 

Each edge advances both the permutation and orientation tables, producing **66,134,880 transition updates**, in addition to visited-state checks, move-table writes, and queue operations.

At an assumed 15 instructions per transition update, this gives:

$66,134,880 \times 15 = 992,023,200 \approx 10^9$ retired instructions.

This is an **operation-based estimate, not a target measurement**, and it does not account for all construction overhead.

After construction, a query requires at most 11 move-table lookups, although each step also applies the move and recomputes the state rank. The complete table construction therefore dominates both execution time and memory use.

### 1.5 Measurement Setup

I ran `target/measure.py` on my Windows installation, using the installed Ripes continuous build.

| Item | Configuration |
|---|---|
| Ripes executable | `C:\Users\user\Apps\Ripes-continuous\Ripes.exe` |
| Processor models | `RV32_ISS` and `RV32_5S` |
| Test program | `target/memory_probe.s` |
| Repetitions | Three runs per configuration |
| Summary statistic | Median |
| Raw results | `target/measurements.json` |



The probe writes one byte to each of \(N\) consecutive guest addresses, starting at `0x20000000`. Its loop contains four instructions:

```asm
loop:
    sb   t2, 0(t0)
    addi t0, t0, 1
    addi t1, t1, -1
    bnez t1, loop
```

Each iteration touches a new address, so the probe writes exactly \(N\) distinct guest bytes. Including initialization and termination, its retired-instruction count is \(4N+7\), which agrees with Ripes’ reported counts.

### 1.6 Host Bytes per Guest Byte

Ripes’ VSRTL memory model stores guest bytes as entries in a sparse hash map. To measure the resulting host-memory overhead, I compared a small-region probe with a large-region probe on `RV32_ISS`.

The script obtains the process’s **peak working set** through Windows’ `GetProcessMemoryInfo`. Subtracting the small probe’s peak from the large probe’s peak reduces the contribution of fixed startup costs.

| Guest bytes written | Run 1  |    Run 2    |    Run 3    |   Median    |
|:-------------------:|:----------------------:|:-----------:|:-----------:|:-----------:|
|          0          |       30,687,232       | 30,707,712  | 30,683,136  | 30,687,232  |
|        4,096        |       31,051,776       | 31,158,272  | 31,014,912  | 31,051,776  |
|      1,048,576      |      115,286,016       | 115,314,688 | 115,249,152 | 115,286,016 |

All working-set values are in bytes. Using the small and large probes, the measured slope is:

$r=
\frac{115,286,016-31,051,776}
     {1,048,576-4,096}
\approx80.65$

Thus, this installation consumed approximately **80.65 additional host bytes per additional guest byte written** over the measured interval.

Applying this slope to the baseline’s three dominant allocations gives:

$18,405,414\times80.6471
\approx1,484,342,506\text{ host bytes}$

This is approximately **1,415.58 MiB, or 1.38 GiB**, of additional host memory.

This projection is an estimate rather than a measurement of the baseline. Hash-table growth, allocator behavior, and process residency can change the slope at larger sizes.

### Retired Instructions per Second

I measured simulation throughput using Ripes’ `--iret`, `--cycles`, and `--exectime` options. The reported rate uses Ripes’ simulation execution time, excluding process startup and assembly overhead:

$\text{Rate}=
\frac{\text{Retired instructions}}
     {\text{Execution time in milliseconds}/1000}$

The same loop was used on both models. The pipelined model used a smaller region to keep the test short while retaining a measurable execution duration.

|   Model    | Guest bytes written | Retired instructions |  Cycles   | Execution times, three runs | Median time | Retired instructions/s |
|:----------:|:-------------------:|:--------------------:|:---------:|:---------------------------:|:-----------:|:----------------------:|
| `RV32_ISS` |      1,048,576      |      4,194,311       | 4,194,311 |      563, 559, 519 ms       |   559 ms    |     **7,503,240**      |
| `RV32_5S`  |       65,536        |       262,151        |  393,227  |   1,560, 1,781, 1,691 ms    |  1,691 ms   |      **155,027**       |

The measured CPI was approximately **1.00** for `RV32_ISS` and **1.50** for `RV32_5S`. CPI describes simulated cycles per retired instruction; it is distinct from the host’s simulation throughput.

### Implications for the Baseline

The baseline performs 66,134,880 factored transition updates. Assuming roughly 15 instructions per update gives:

$66,134,880\times15=992,023,200$

Using the measured loop throughput produces the following idealized execution-time estimates:

|   Model    | Measured retired instructions/s | Estimated time for 992,023,200 instructions |
|:----------:|:-------------------------------:|:-------------------------------------------:|
| `RV32_ISS` |            7,503,240            |       Approximately **2.20 minutes**        |
| `RV32_5S`  |             155,027             |        Approximately **1.78 hours**         |

These are extrapolations, not baseline timings. The BFS performs random table accesses and conditional queue operations, whereas the probe performs sequential stores. The instruction estimate also omits some construction overhead.

Section 7 of `report.md` argues that the complete table should be retained as a verification artifact. These measurements show why rebuilding that artifact inside Ripes is costly: the baseline’s 17.553 MiB of dominant guest allocations projects to roughly 1.38 GiB of additional host memory, and its estimated instruction count is especially expensive on the pipelined model.

Exhaustive model verification can remain on the host. The target implementation should instead use a smaller search representation and establish shortest-path correctness through its algorithm and validation, without reconstructing the complete state table for every query.

## Stage 2: Three-Coordinate IDA* with Pattern Databases

### 2.1 Target Constraints and Design Choice

Stage 1 measured approximately 80.65 additional host bytes per additional guest byte written in the Windows Ripes build. Its simple memory loop retired approximately 7.50 million instructions/s on `RV32_ISS` and 155,027 instructions/s on `RV32_5S`. These measurements describe that probe, not the BFS solver.

The baseline allocates 18,405,414 bytes across its three dominant allocations and performs an estimated 992,023,200 instructions in transition updates alone. Keeping its complete move table would require 3,674,160 bytes even after removing the queue, exceeding the 128 KiB static-data budget. The target also requires every distance-11 input to finish within 50,000,000 retired instructions on `RV32_ISS`.

The adopted design is IDA* with three pattern-database lower bounds. It retains compact coordinate transitions, removes the full-state BFS queue and move table from the target, and performs the actual solution search on the target. C generates the abstract transition and distance tables on the host. The complete baseline BFS is used only by the host verifier.

The measured ISS loop rate would correspond to about 6.66 seconds for 50 million instructions, but the budget is an instruction count, not a time limit. Search performance must ultimately be measured with Ripes `--iret`.

### 2.2 State Representation

The cube retains the baseline's fixed front-upper-left corner and internal cubie numbering. Three coordinates replace the composite full-state rank:

| Coordinate  |  Range  |             Information retained              | Goal |
|:-----------:|:-------:|:---------------------------------------------:|:----:|
| Permutation | 0..5039 | Full permutation of all seven movable corners |  0   |
|   Joint A   | 0..5669 | Positions and orientations of cubies 0, 1, 2  |  0   |
|   Joint B   | 0..5669 | Positions and orientations of cubies 3, 4, 5  | 2916 |

Each coordinate fits in 16 bits. A joint coordinate has

$(7\times6\times5)\times3^3=210\times27=5,670$

possible values. The three positions are an ordered selection without replacement, and the three orientations are recorded in cubie order rather than position order.

For positions `x[0]`, `x[1]`, and `x[2]`, remove the preceding positions from the remaining choices:

```text
second = x[1] - (x[1] > x[0])
third  = x[2] - (x[2] > x[0]) - (x[2] > x[1])
position_rank = (x[0] * 6 + second) * 5 + third
orientation_rank = (o[0] * 3 + o[1]) * 3 + o[2]
joint_rank = position_rank * 27 + orientation_rank
```

In the solved cube, A occupies positions `(0,1,2)` and B occupies `(3,4,5)`. Their position ranks are 0 and 108, so their joint goals are 0 and `108 * 27 = 2916`.

The tuple represents a complete legal cube. Permutation identifies all seven corner positions; A and B identify the orientations of six corners; twist conservation determines the seventh. This argument relies on the input being legal, including the modulo-three orientation-sum invariant.

The search updates the three coordinates directly by transition lookup. It never splits a composite rank using division by 729 and never reconstructs and re-ranks all cubies at every search edge. Division in the host generator and verifier is outside target execution.

### 2.3 Sharing the Joint Transition Table

Joint A and B use the same coordinate encoding. A face turn changes a tracked corner's position and adds a twist determined by the destination position. Neither operation depends on the corner's name or on whether it belongs to A or B.

Consequently, their quarter-turn transition functions are identical. The initial separately generated A/B transition arrays were compared byte-for-byte and matched. Exhaustive projection checks subsequently verified the shared table for both groups against the full cubie model.

The two groups therefore share one transition table but retain separate distance tables, because their goal coordinates differ. Sharing saves 34,020 bytes without changing any coordinate update, heuristic value, or search order. This is a memory improvement; no target instruction-speed improvement is claimed.

Three quarter-turn rows are stored for each coordinate type. Applying a row successively produces the quarter, half, and inverse turns, avoiding storage for all nine moves. During child enumeration, the frame caches the previous quarter-turn child so those successive updates are reused.

### 2.4 Heuristic and Shortest-Path Guarantee

The heuristic is

$h(s)=\max\bigl(h_{\mathrm{perm}},h_A,h_B\bigr).$

Each PDB contains exact BFS distances in its abstract graph, using all nine HTM moves with unit cost. For each projection `pi` and move `m`, the required relationship is

$\pi(m(s))=m_{\pi}(\pi(s)).$

Thus, every full-state solution of length `d` projects to an abstract path of length at most `d`. The abstract shortest distance cannot exceed `d`. Each PDB is admissible, and taking their maximum preserves admissibility. Their distances are not added: a single move can improve more than one projection.

IDA* starts with bound `h(root)` and increases the bound by one after an unsuccessful iteration. At depth `g`, a branch is rejected when `g + h(s) > bound`. Each iteration exhausts all eligible paths under that bound before increasing it. Because the lower bound never overestimates, a shortest solution cannot be discarded. The first successful bound therefore returns a shortest solution.

The implementation uses an explicit stack of twelve frames for depths 0 through 11. It checks the goal coordinates explicitly and stores the returned move sequence separately. No recursive search calls are used.

Two consecutive turns of the same face are omitted. They either cancel or combine into one HTM move, so a shortest path never needs such a pair. The root considers nine moves; subsequent nodes consider the six moves on the other two faces. This pruning reduces the tree but does not alone make depth-11 search affordable; the PDBs supply additional pruning.

For a legal cube, all three goal coordinates imply a solved state. Permutation fixes every corner position, A/B fix six orientations, and the orientation-sum invariant forces the seventh orientation to zero.

### 2.5 Memory Budget

Distances are stored as bytes and transitions as 16-bit values. The generated PDB maximum is 7 for each projection. Although those distances can be packed more tightly, byte storage avoids decoding work and already fits comfortably within the budget.

|              Target data              |   Calculation    |   Bytes    |
|:-------------------------------------:|:----------------:|:----------:|
| Permutation quarter-turn transitions  |  `3 * 5040 * 2`  |   30,240   |
| Shared joint quarter-turn transitions |  `3 * 5670 * 2`  |   34,020   |
|            Permutation PDB            |      `5040`      |   5,040    |
|              Joint A PDB              |      `5670`      |   5,670    |
|              Joint B PDB              |      `5670`      |   5,670    |
|          **Tables subtotal**          |                  | **80,640** |
|        Explicit search frames         |    `12 * 16`     |    192     |
|         Solution move buffer          |       `11`       |     11     |
|            Solution length            |       `1`        |     1      |
|       **Defined data subtotal**       |                  | **80,844** |
|     **Remaining within 128 KiB**      | `131072 - 80844` | **50,228** |

Each 16-byte frame contains six 16-bit fields for current and cached-child coordinates and four byte-sized search-control fields. Its power-of-two stride can be addressed with a shift on RV32I. The C generator checks the structure sizes instead of assuming them.

This is the size of the defined tables and search workspace, not a final ELF section measurement. Input/output buffers, strings, alignment, and any later target globals must be included in the Stage 4 `.data + .bss + .rodata` total. Host verification arrays and diagnostic counters are not target data. The table file serializes 16-bit entries explicitly in little-endian order.

### 2.6 Comparing Heuristic Choices

A smaller permutation-plus-orientation design requires 40,383 table bytes. The joint design uses more memory to retain relationships between corner position and orientation. Both were evaluated using the same move order, consecutive-face pruning, and one-step bound increments.

An expanded edge is counted whenever the search generates a child, including children subsequently rejected by the heuristic. Counts include all IDA* iterations. Node visits and edges are recorded separately in the CSV.

|                       Design                        | Table bytes | Edges for `21345671111111` | Maximum edges among all distance-11 states |
|:---------------------------------------------------:|:-----------:|:--------------------------:|:------------------------------------------:|
|              Permutation + orientation              |   40,383    |          233,961           |                  639,792                   |
| Permutation + joint A + joint B, shared transitions |   80,640    |           87,021           |                  238,434                   |

For both designs, the maximum-edge state is `54721631111111`. The joint heuristic reduces expanded edges by approximately 62.8% for the specified vector and 62.7% for the maximum-edge case. These are freshly reproduced host operation counts, not copied Ripes results from the reference report.

The selected three-coordinate design omits a separate orientation coordinate to keep each edge to three coordinate updates. This remains a design choice to evaluate further: an added orientation PDB may prune additional branches, and the shared-table layout leaves enough space for that experiment. No local 20% overhead or 9.46% break-even result is claimed. Whether a fourth coordinate is worthwhile must be established through a controlled comparison in the later stages.

### 2.7 Verification and Reproduction

The table generator, search reference, and verifier are in `target/stage2/`. Run the complete host verification from the repository root:

```sh
make -f target/stage2/Makefile check
```

For the exhaustive projection/admissibility checks plus only the distance-11 search checks:

```sh
make -f target/stage2/Makefile quick
```

`all-state-verification.txt` retains the completed exhaustive-run result; `verification.txt` records the quick check. `distance11.csv` contains each hard state's coordinates, edge counts, visits, and returned length. The baseline source remains unchanged and supplies the host BFS oracle.

The validation checks table coverage, transition ranges, consistency for every HTM move, unique PDB goals, and four-quarter-turn identity. It also checks projection commutation, heuristic admissibility, and full-goal equivalence over all 3,674,160 legal states. Returned paths are replayed using the full `solver.c` cubie model rather than only the projected tables.

The complete run passed for **all 3,674,160 states**: every returned length matched the baseline BFS distance and every returned sequence solved the full cubie model. Host CPU time was **172.499 seconds**, including projection checks and the alternative-heuristic comparison. All **2,644 distance-11 states** passed; their maximum joint-search edge count was **238,434**.

These checks establish correctness relative to the baseline's move geometry. The generator and oracle share that geometry, so they do not constitute an independent physical derivation of the cube's face turns.

### 2.8 What Remains for Target Validation

The mathematical argument establishes shortest-path optimality, and the host operation counts support choosing the joint heuristic. They do not establish compliance with the 50-million-instruction limit.

Stage 3 will refine the C implementation and compare target-relevant operation costs. Stage 4 must measure the final renderer-off RV32I program using the pinned Ripes build and `--iret`, including the specified vector and all 2,644 distance-11 states. The state with the largest host edge count is not automatically the state with the largest retired-instruction count.

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

|           Logical operation            | Stage 2 control | Delayed-frame variant | Reduction |
|:--------------------------------------:|:---------------:|:---------------------:|:---------:|
| Frame initializations, including roots |   191,563,876   |      31,931,576       |  83.33%   |
|          Solution-path writes          |   191,546,980   |      31,917,324       |  83.34%   |
|            Generated edges             |   191,546,980   |      191,546,980      |    0%     |

This changes when state is committed to the stack, not the search tree. The revised loop also removes the per-dispatch `face == 255` entry check used by the control: a frame is entered only after its candidate has already passed pruning.

### 3.3 Replace the Inner-Loop Maximum with Early Cutoffs

The root needs the numerical value

$h=\max(h_{\mathrm{perm}},h_A,h_B)$

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

|    PDB order     | Total PDB reads |
|:----------------:|:---------------:|
|       PAB        |   329,846,059   |
|       PBA        |   335,184,028   |
|       APB        |   318,314,654   |
| **ABP, adopted** | **317,244,628** |
|       BPA        |   333,669,221   |
|       BAP        |   327,261,226   |

ABP minimizes the aggregate PDB-read count over this test set. This does not establish that it is best for every individual input or that it minimizes retired instructions.

There is a comparison tradeoff: early cutoffs perform more direct threshold comparisons, but eliminate almost all comparisons used to construct a maximum.

|        Comparison category         | Stage 2 control | Adopted ABP variant |
|:----------------------------------:|:---------------:|:-------------------:|
| Comparisons used to compute maxima |   383,133,040   |        5,288        |
|    Remaining-depth comparisons     |   191,563,876   |     317,236,696     |
|  **Combined logical comparisons**  | **574,696,916** |   **317,241,984**   |

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

|                    Check                    | Result |
|:-------------------------------------------:|:------:|
|       Multiply or divide instructions       |  None  |
| Multiply, divide, or remainder helper calls |  None  |
|   Production diagnostic-counter accesses    |  None  |

The 16-byte frame stride permits shift-based indexing, and 16-bit transition entries use a two-byte stride. Constant multiplications in coordinate encoding are synthesized using base-integer instructions.

Local pointers were introduced for the active permutation and joint transition rows. Inspection showed that the compiler still synthesizes the non-power-of-two face-row strides using shifts and additions inside the search loop. Consequently, no reduction in addressing cost is attributed to that source-level change.

This compiler output is an audit of C compatibility and lowering, not the final hand-written Stage 4 assembly program and not a retired-instruction measurement.

### 3.6 Operation-Count Results

Across the complete distance-11 set, the selected implementation reduces PDB reads and workspace writes while preserving the search tree:

|       Operation       | Stage 2 control | Selected Stage 3 | Reduction  |
|:---------------------:|:---------------:|:----------------:|:----------:|
|    Generated edges    |   191,546,980   |   191,546,980    |     0%     |
|   Transition reads    |   574,640,940   |   574,640,940    |     0%     |
|       PDB reads       |   574,699,560   |   317,244,628    | **44.80%** |
| Frame initializations |   191,563,876   |    31,931,576    | **83.33%** |
| Solution-path writes  |   191,546,980   |    31,917,324    | **83.34%** |

The selected variant produces the following results on the specified vector and the maximum-edge distance-11 state:

|      Input       |       Operation       | Stage 2 control | Selected Stage 3 |
|:----------------:|:---------------------:|:---------------:|:----------------:|
| `21345671111111` |    Generated edges    |     87,021      |      87,021      |
|                  |       PDB reads       |     261,081     |     145,410      |
|                  | Frame initializations |     87,026      |      14,508      |
|                  | Solution-path writes  |     87,021      |      14,504      |
| `54721631111111` |    Generated edges    |     238,434     |     238,434      |
|                  |       PDB reads       |     715,323     |     393,703      |
|                  | Frame initializations |     238,440     |      39,742      |
|                  | Solution-path writes  |     238,434     |      39,737      |

The table layout and workspace sizes are unchanged: **80,640 bytes of tables plus 204 bytes of workspace**, leaving **50,228 bytes** within the 128 KiB budget for later input/output data and alignment. Diagnostic counters are excluded from this target-data subtotal. The final linked section sizes still need checking in Stage 4.

### 3.7 Correctness Verification

The selected production build, with counters compiled out, was tested against the full baseline BFS oracle over **all 3,674,160 legal states**. Every returned length matched the exact BFS distance, and every returned sequence was replayed through the full cubie model to confirm that it solved the cube.

|                                      Verification                                       |                                              Result                                              |
|:---------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------------:|
| All eight counted variants versus original Stage 2, 2,644 hard states plus solved state |                        Identical lengths, move sequences, and edge counts                        |
|                             Production shortest-path check                              |                                   3,674,160 / 3,674,160 passed                                   |
|                                   H3 wall-clock time                                    |                                             246.73 s                                             |
|                                   H4 packed accessors                                   |                         Not applicable: byte PDBs and uint16 transitions                         |
|                               Full-cubie solution replay                                |                                   3,674,160 / 3,674,160 passed                                   |
|           Workspace boundary guards, move ranges, and consecutive-face checks           |                                              Passed                                              |
|                            Out-of-range coordinate rejection                            |                                              Passed                                              |
|                                     ASan and UBSan                                      | Passed on all eight supplied solution vectors, a three-move scramble, and the maximum-edge state |

The exhaustive production check used GCC 11.4.0 with `-O3 -std=c99` under WSL Ubuntu 22.04 and reported **246.643 CPU seconds**. The required H3 wall-clock measurement was **246.73 seconds (4 min 6.73 s)**, recorded by `/usr/bin/time -p` in `target/stage3/wall-time.txt`. These are verification durations, not a controlled solver-speed comparison. The arithmetic audit used the RISC-V GCC 10.2.0 toolchain.

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

## Stage 4: Handwritten RV32I Assembly and Target Measurements

### 4.1 Target Program and Test Data

The final target program is handwritten RV32I in `target/stage4/frontend.S` and `target/stage4/search.S`. It parses an arbitrary fourteen-character input, derives the permutation and both joint coordinates, searches on the simulated processor, prints the solution, and applies every returned move to the full cubie state. No solution path or full-domain distance table is supplied by the host.

The editable native entry point is `target/stage4/ripes/solver.s`. Its `expected_length` is -1, so changing only `input_vector` is sufficient for arbitrary legal inputs. The three named test files retain known-length assertions.

The host-generated abstract tables from Stage 2 are linked as read-only data. The assembly preserves the final Stage 3 algorithm: iterative IDA*, an explicit stack, same-face pruning, and early heuristic tests in joint-A / joint-B / permutation order. Its bound begins at the maximum of the three root distances and increases through 11. Consequently, the admissibility and shortest-path arguments from Stage 2 still apply.

The parser verifies permutation digits and uniqueness, orientation digits, a zero twist sum modulo three, and string termination. Lehmer rank uses fixed factorial weights; joint encoding uses shifts and adds. Physical replay reduces an orientation sum in 0..4 with one conditional subtraction. No multiply, divide, remainder, arithmetic helper, heap allocation, recursion, or floating-point operation is used. GNU assembly/link audits also check the static-data budget and absence of unresolved symbols.

The input and optional expected length are assembly-time constants. Setting `expected_length` to -1 permits an unseen state; the solver still computes its path and validates replay. Success returns `a0=solution length` and `a1=1`. Failure returns `a0=0xffffffff` and `a1=0`. The expected length is only a post-search test assertion and does not control the search.

|             Included test              |      Input       | Exact distance |
|:--------------------------------------:|:----------------:|:--------------:|
|              Solved cube               | `12345671111111` |       0        |
| Short scramble, generated by `R D2 B'` | `26471352122222` |       3        |
|       Specified distance-11 case       | `21345671111111` |       11       |

The short case and supplementary test expectations were derived using the original C BFS oracle. Standalone files under `target/stage4/ripes/` contain the handwritten instructions and literal table bytes, so they can be loaded directly into Ripes without `.incbin` support. The exporter uses preprocessing and copies existing bytes; it does not generate heuristic tables or solution paths in Python.

### 4.2 Register and Memory Organization

The active quarter-turn coordinates remain in `t0`, `t1`, and `t2`, and the turn cursor remains in `t3`. The permutation and shared joint row bases remain in `s5` and `s6`. The three distance-table bases remain in `s7` through `s9`. Frame address, depth, bound, remaining depth, and face occupy the other saved registers.

Row bases change when a face changes or a suspended parent resumes, rather than being reconstructed for every edge. Advancing to the next face adds the fixed strides 10,080 and 11,340. Selecting a resumed face uses the fact that its index is only 0, 1, or 2. All three cached child coordinates advance before any cutoff, including for rejected children, so repeated quarter turns still produce the correct half-turn and inverse-turn candidates.

Each frame remains 16 bytes. Twelve frames, eleven path bytes, and one length byte occupy 204 bytes. Accepted descent saves the parent's cached coordinates and cursor, then initializes the next frame. Rejected children retain their state in registers and do not create a frame. Returning to a parent reloads its suspended cursor. The assembly functions preserve the ABI saved registers and use a bounded runtime stack; the IDA* stack itself is static.

### 4.3 Measurement Conventions and GCC Reference

All performance claims below use Ripes `--iret`, not host operation estimates or wall-clock speed. Counts include input parsing, coordinate encoding, target search, printed moves, full-cubie replay, validation, and the terminating ecall. The renderer is absent. Code size is bytes of linked `.text`; static data is `.data + .bss + .rodata`.


The compiler reference uses the final `target/stage3/search.c`, compiled with RISC-V GCC 10.2.0 at `-O2 -march=rv32i -mabi=ilp32`. Its freestanding frontend performs equivalent parsing, output, expected-length checking, and full-cubie replay. Console output was added to the preparatory reference before comparison, so its final figures supersede the earlier reference that only returned registers. Full flags, ELF hashes, section sizes, and disassemblies are retained in build manifests.

### 4.4 Measured Refinement

|     Version     |                                      Change                                       | Linked .text bytes | ISS count, solved | ISS count, short | ISS count, specified case |
|:---------------:|:---------------------------------------------------------------------------------:|:------------------:|:-----------------:|:----------------:|:-------------------------:|
|  GCC reference  |                     Final C algorithm and equivalent frontend                     |       2,184        |        791        |      2,724       |         5,474,251         |
|   Assembly R0   | Register-resident active state and retained row bases; four cache stores per edge |       1,888        |        745        |      2,525       |         3,157,232         |
|   Assembly R1   |                      Write those caches only when descending                      |       1,888        |        745        |      2,485       |         2,867,160         |
| **Assembly R2** |                        Remove an unused frame-entry block                         |     **1,864**      |      **745**      |    **2,485**     |       **2,867,160**       |

For the specified case, R1 removes 290,072 retired instructions relative to R0. Four stores disappear on each of 72,518 edges that does not suspend the parent for a descent. This matches the measured difference exactly. R2 saves 24 bytes but changes none of the measured instruction counts; deleting unreachable code is a code-size improvement only.

The final assembly uses approximately 47.6% fewer retired instructions on the specified case and 14.7% fewer linked text bytes than GCC. It also wins on the solved and short tests. On the additional stress case `54721631111111`, GCC retires 14,971,675 instructions and R2 retires 7,832,368. These comparisons do not establish that every possible input beats GCC; a full-domain comparative sweep was not performed.

|       Final R2 test        | RV32_ISS --iret | RV32_5S --iret | Expected length and in-program replay |
|:--------------------------:|:---------------:|:--------------:|:-------------------------------------:|
|           Solved           |       745       |      744       |                Passed                 |
|           Short            |      2,485      |     2,484      |                Passed                 |
| Specified distance-11 case |    2,867,160    |   2,867,159    |                Passed                 |

The table uses the known-length test assertions in both C and assembly. The generic native `solver.s` skips that assertion: its specified-input ISS count is 2,867,159, one instruction fewer, and its in-program replay still passes.

The one-instruction difference is the observed termination-count convention of these two models. Each model's own count is reported. The directly assembled standalone Ripes files reproduced these same six counts and validation results.

### 4.5 Static Data and Exhaustive Hard-State Gate

|                           Final R2 section                           |   Bytes    |
|:--------------------------------------------------------------------:|:----------:|
| .rodata: abstract tables, input, assertions, maps and output strings |   80,788   |
|            .bss: workspace and full-cubie replay buffers             |    232     |
|                                .data                                 |     0      |
|                        **Total static data**                         | **81,020** |
|                    Remaining below 131,072 bytes                     |   50,052   |

The GCC reference uses 81,004 static bytes. The handwritten frontend therefore costs 16 additional static bytes while reducing text size and retired instructions. Table packing was unnecessary to meet the budget; the final target retains byte distances and uint16 transitions.

Every one of the **2,644 unique distance-11 states** was executed on the pinned RV32_ISS build. Each returned length 11, passed full-cubie replay inside the program, and remained below the 50,000,000-instruction ceiling. There were no missing cases, duplicate inputs, or accepted timeouts.

|      Complete hard-state sweep       |             Result              |
|:------------------------------------:|:-------------------------------:|
|            States tested             |              2,644              |
|     Minimum retired instructions     |            1,385,412            |
|   **Maximum retired instructions**   |          **7,832,368**          |
|         Maximum-count input          |        `54721631111111`         |
| Specified input, reported separately | `21345671111111`: **2,867,160** |

The sweep instantiates each fourteen-character string and expected-length word in a fixed linked ELF. Only those nineteen data bytes change; instructions, tables, and layout remain identical. The input list, template, executable, and per-case ELF hashes are recorded. This supplies a constant input before execution, rather than transferring any search result to the target.

The sweep used four independent Ripes processes and took 385.11 seconds wall time. That elapsed time describes the test workflow, not a single-processor simulation rate. Raw per-state rows are in `asm-r2-distance11.csv`; the coverage and maximum are in `asm-r2-sweep.json`.

### 4.6 Additional Correctness Evidence

The final assembly also passed 82 valid supplementary inputs: 34 cases selected across depths 0 through 11 and 48 deterministic arbitrary states, all with exact distances supplied by the host BFS. An additional query, `76543211111111`, was built with no expected-length assertion and independently returned length 11 with successful replay on both ISS and RV32_5S.

Five invalid strings tested duplicate permutation entries, out-of-range permutation/orientation digits, a nonzero twist sum, and a zero digit; all were rejected.

As an independent check, the original C cubie model replayed the paths actually printed by Ripes for the full hard-state set and the 82 supplementary inputs. All **2,726 recorded paths** had exact BFS length, contained legal moves with no consecutive same-face turns, and reached the solved state. This supplements, rather than replaces, the replay performed inside the target program.

The host H1-H3 evidence from Stages 2-3 remains separate: the final C search passed all 3,674,160 states, with H3 wall time 246.73 seconds. The handwritten target was tested on the complete hard-state set and the listed supplementary cases; it was not executed over the entire domain.

### 4.7 Reproduction

From WSL in the repository root:

```sh
make -f target/stage4/Makefile reference assembly ripes extra-cases
python3 target/stage4/export_ripes.py --output solver.s
# Arbitrary unseen input: omit --expect to retain the default -1.
python3 target/stage4/build_assembly.py --vector 76543211111111
```

From Windows PowerShell:

```powershell
$stage4 = (Resolve-Path .\target\stage4).Path
python "$stage4\measure.py" --kind reference
python "$stage4\measure.py" --kind asm-r2
python "$stage4\measure.py" --kind asm-r2 --native
python "$stage4\sweep.py" --revision 2 --workers 4
python "$stage4\test_extra.py"
```

For R0/R1, build the same three inputs with `--revision 0` or `--revision 1`, then run `measure.py --kind asm-r0` or `--kind asm-r1`. Per-version records are saved separately.

The renderer and actual five-stage CLI trace are complete and verified as described in Stages 5–6. Real LED-peripheral screenshots and GUI wire-signal captures are manual-required items, explicitly listed below; neither is claimed as captured.

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

## H1–H4 / T5–T7 Verification Summary

Results below separate host proofs, actual target execution, and manual GUI evidence. No screenshot or GUI signal value is asserted to have been captured.

| Gate | Requirement | Result and scope | Evidence / reproduction |
|---|---|---|---|
| H1 | Every heuristic is admissible against exact BFS | PASS, all 3,674,160 legal states; projection commutation checked for all nine moves | `target/stage2/verification.txt`; `make -f target/stage2/Makefile quick` |
| H2 | Every depended-on table populated; max and solved entries verified | PASS, transition ranges and identities; all three PDBs fully populated, max 7, solved distance 0 | `target/stage4/table-audit.json`; `python target/stage4/audit_tables.py`; Stage 2 verifier |
| H3 | Search length equals BFS distance for every state | PASS, all 3,674,160 states, with full-cubie replay; 2026-10-07 wall time **246.73 s**, CPU 246.643 s | `target/stage3/all-state-verification.txt`, `wall-time.txt`; `make -f target/stage3/Makefile check` |
| H4 | Packed accessors match unpacked values at even/odd indices | N/A: production stores byte PDBs and uint16 transitions; no packed accessor | `target/stage2/joint.h`, table audit |
| T5 | Applying every target-returned path solves the cube | PASS on all 2,644 distance-11 inputs plus 82 valid supplementary inputs; target full-cubie replay and independent host replay of 2,726 printed paths | `asm-r2-distance11.csv`, `extra-test-results.json`, `printed-path-verification.txt` under `target/stage4/` |
| T6 | `21345671111111` returns optimal length 11 | PASS on ISS and RV32_5S; ISS 2,867,160 retired instructions with expected-length test enabled | `target/stage4/asm-r2-native-measurements.json` |
| T7 | Solved, short and hard tests reproduce on ISS and a visual pipeline model; arbitrary inlined input supported | PASS on the pinned RV32_ISS and RV32_5S for all three tests; editable generic source and extra arbitrary-input checks also pass. Actual GUI display/wire screenshots remain MANUAL REQUIRED | `asm-r2-native-measurements.json`, `generic-source-test.json`, `extra-test-results.json`; [GUI procedure](https://github.com/bangyou0912/minirubik/blob/hw1-redo/visualization.md) |

T5 reports the executed target coverage; it does not claim an exhaustive assembly run over all 3,674,160 states. H3 establishes the host search's exhaustive optimality. T7's CLI run of RV32_5S executes the visual model, but does not substitute for the assignment's separate GUI wire-signal observation.

| Actual PDB bytes | Populated | Maximum distance | Solved index | Solved distance |
|---|---:|---:|---:|---:|
| Permutation | 5,040 / 5,040 | 7 | 0 | 0 |
| Joint A | 5,670 / 5,670 | 7 | 0 | 0 |
| Joint B | 5,670 / 5,670 | 7 | 2,916 | 0 |

Permutation transitions contain 15,120 uint16 entries in 0..5039. Shared joint transitions contain 17,010 uint16 entries in 0..5669. A transition's solved entry is a quarter-turn successor, not a distance of zero; the table audit lists those successors explicitly.

The complete renderer-off ISS sweep covers exactly the host oracle's 2,644 unique hard states, with no omitted or timed-out case. Maximum **7,832,368 < 50,000,000** at `54721631111111`; specified vector **2,867,160**. Final assembly `.text` is 1,864 bytes; CLI static data is 81,020 bytes; complete standalone GUI static data is 81,168 bytes, both below 131,072 bytes. The GCC reference uses 2,184 text bytes and retires 5,474,251 instructions on the specified input.

The renderer passed 1,323 independent geometry comparisons and 29,750 target framebuffer word comparisons across 34 frames in ISS and RV32_5S. Those framebuffer tests use a RAM stand-in. Real peripheral animation and control-signal screenshots are **manual required**, with a precise capture checklist in [visualization.md](https://github.com/bangyou0912/minirubik/blob/hw1-redo/visualization.md).

## Reproduce from a Fresh Checkout

Use the explicit submission branch. `main` remains the hosted BFS baseline.
The checked-in native Ripes sources contain all table bytes, so the basic
GUI/CLI demonstrations do not require rebuilding tables first.

```sh
git clone --branch hw1-redo https://github.com/bangyou0912/minirubik.git
cd minirubik
# Ubuntu/WSL dependencies: gcc, make, python3,
# riscv64-unknown-elf-gcc and riscv64-unknown-elf-binutils.
sh target/stage4/reproduce.sh
```

Run the host build inside the same Windows checkout via `/mnt/c/...` in WSL.
Then open PowerShell in that checkout and use the pinned Windows Ripes binary:

```powershell
# Optional path override; SHA-256 must still match target/measurements.json.
$env:RIPES_EXE = 'C:\Users\user\Apps\Ripes-continuous\Ripes.exe'
.\target\stage4\reproduce.ps1 -FullSweep
```

The `-FullSweep` switch runs all 2,644 hard states. Omitting it runs the other
target checks and audits the recorded complete sweep without rerunning it.
The Ripes pin is `Ripes-v2.2.6-106-g5b8a616`, SHA-256
`bd2ddea8cd6fcf6902cda7366fe99ab6dd0c7fdbbc7efcfdb89ede20acc67f0f`.
Scripts reject a different binary instead of silently mixing measurements.

`target/stage4/evidence/` retains the original measured C/R0/R1/R2 ELF,
manifest and disassembly for all three tests. `evidence/rebuilt/` retains the
2026-10-07 recompiled artifacts for the new measurement records. Generated
objects and native host binaries stay under ignored `build/` directories.
`check_rebuilt_sections.py` compares every allocated section's address, size
and byte hash, so a checkout path's non-executed symbol metadata does not
invalidate an equivalent rebuild. `.gitattributes` preserves LF for source
hashes and treats table/ELF files as binary.

For a grader-supplied legal input, export from WSL without a known-length
assertion, then load the resulting source into Ripes:

```sh
python3 target/stage4/export_ripes.py --vector 76543211111111 --output arbitrary.s
python3 target/stage4/export_ripes.py --render --vector 76543211111111 --output arbitrary-gui.s
```

Both use `expected_length=-1` and the same solver. Only the GUI export adds
renderer calls/code/data and delay. The target verifies the returned path by
replaying it on the full cubie model, regardless of a known-length assertion.
Rerunning verification changes wall times; the submitted durations describe
the recorded submission run, not a promise of identical timing on another host.

Actual screenshots must be captured using Stage 6's checklist. No image is
included as a substitute for real peripheral or control-signal evidence.
