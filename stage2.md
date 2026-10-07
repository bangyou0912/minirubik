## Stage 2: Three-Coordinate IDA* with Pattern Databases

### 2.1 Target Constraints and Design Choice

Stage 1 measured approximately 80.65 additional host bytes per additional guest byte written in the Windows Ripes build. Its simple memory loop retired approximately 7.50 million instructions/s on `RV32_ISS` and 155,027 instructions/s on `RV32_5S`. These measurements describe that probe, not the BFS solver.

The baseline allocates 18,405,414 bytes across its three dominant allocations and performs an estimated 992,023,200 instructions in transition updates alone. Keeping its complete move table would require 3,674,160 bytes even after removing the queue, exceeding the 128 KiB static-data budget. The target also requires every distance-11 input to finish within 50,000,000 retired instructions on `RV32_ISS`.

The adopted design is IDA* with three pattern-database lower bounds. It retains compact coordinate transitions, removes the full-state BFS queue and move table from the target, and performs the actual solution search on the target. C generates the abstract transition and distance tables on the host. The complete baseline BFS is used only by the host verifier.

The measured ISS loop rate would correspond to about 6.66 seconds for 50 million instructions, but the budget is an instruction count, not a time limit. Search performance must ultimately be measured with Ripes `--iret`.

### 2.2 State Representation

The cube retains the baseline's fixed front-upper-left corner and internal cubie numbering. Three coordinates replace the composite full-state rank:

| Coordinate | Range | Information retained | Goal |
|---|---:|---|---:|
| Permutation | 0..5039 | Full permutation of all seven movable corners | 0 |
| Joint A | 0..5669 | Positions and orientations of cubies 0, 1, 2 | 0 |
| Joint B | 0..5669 | Positions and orientations of cubies 3, 4, 5 | 2916 |

Each coordinate fits in 16 bits. A joint coordinate has

\[
(7\times6\times5)\times3^3=210\times27=5,670
\]

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

\[
h(s)=\max\bigl(h_{\mathrm{perm}},h_A,h_B\bigr).
\]

Each PDB contains exact BFS distances in its abstract graph, using all nine HTM moves with unit cost. For each projection `pi` and move `m`, the required relationship is

\[
\pi(m(s))=m_{\pi}(\pi(s)).
\]

Thus, every full-state solution of length `d` projects to an abstract path of length at most `d`. The abstract shortest distance cannot exceed `d`. Each PDB is admissible, and taking their maximum preserves admissibility. Their distances are not added: a single move can improve more than one projection.

IDA* starts with bound `h(root)` and increases the bound by one after an unsuccessful iteration. At depth `g`, a branch is rejected when `g + h(s) > bound`. Each iteration exhausts all eligible paths under that bound before increasing it. Because the lower bound never overestimates, a shortest solution cannot be discarded. The first successful bound therefore returns a shortest solution.

The implementation uses an explicit stack of twelve frames for depths 0 through 11. It checks the goal coordinates explicitly and stores the returned move sequence separately. No recursive search calls are used.

Two consecutive turns of the same face are omitted. They either cancel or combine into one HTM move, so a shortest path never needs such a pair. The root considers nine moves; subsequent nodes consider the six moves on the other two faces. This pruning reduces the tree but does not alone make depth-11 search affordable; the PDBs supply additional pruning.

For a legal cube, all three goal coordinates imply a solved state. Permutation fixes every corner position, A/B fix six orientations, and the orientation-sum invariant forces the seventh orientation to zero.

### 2.5 Memory Budget

Distances are stored as bytes and transitions as 16-bit values. The generated PDB maximum is 7 for each projection. Although those distances can be packed more tightly, byte storage avoids decoding work and already fits comfortably within the budget.

| Target data | Calculation | Bytes |
|---|---|---:|
| Permutation quarter-turn transitions | `3 * 5040 * 2` | 30,240 |
| Shared joint quarter-turn transitions | `3 * 5670 * 2` | 34,020 |
| Permutation PDB | `5040` | 5,040 |
| Joint A PDB | `5670` | 5,670 |
| Joint B PDB | `5670` | 5,670 |
| **Tables subtotal** | | **80,640** |
| Explicit search frames | `12 * 16` | 192 |
| Solution move buffer | `11` | 11 |
| Solution length | `1` | 1 |
| **Defined data subtotal** | | **80,844** |
| **Remaining within 128 KiB** | `131072 - 80844` | **50,228** |

Each 16-byte frame contains six 16-bit fields for current and cached-child coordinates and four byte-sized search-control fields. Its power-of-two stride can be addressed with a shift on RV32I. The C generator checks the structure sizes instead of assuming them.

This is the size of the defined tables and search workspace, not a final ELF section measurement. Input/output buffers, strings, alignment, and any later target globals must be included in the Stage 4 `.data + .bss + .rodata` total. Host verification arrays and diagnostic counters are not target data. The table file serializes 16-bit entries explicitly in little-endian order.

### 2.6 Comparing Heuristic Choices

A smaller permutation-plus-orientation design requires 40,383 table bytes. The joint design uses more memory to retain relationships between corner position and orientation. Both were evaluated using the same move order, consecutive-face pruning, and one-step bound increments.

An expanded edge is counted whenever the search generates a child, including children subsequently rejected by the heuristic. Counts include all IDA* iterations. Node visits and edges are recorded separately in the CSV.

| Design | Table bytes | Edges for `21345671111111` | Maximum edges among all distance-11 states |
|---|---:|---:|---:|
| Permutation + orientation | 40,383 | 233,961 | 639,792 |
| Permutation + joint A + joint B, shared transitions | 80,640 | 87,021 | 238,434 |

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

The generated table binary has SHA-256:

```text
190903f699ec5a9cfb3b7a396d4a5e59477aee9059cbbb66d56ba13e35c27ee9
```

These checks establish correctness relative to the baseline's move geometry. The generator and oracle share that geometry, so they do not constitute an independent physical derivation of the cube's face turns.

The host checks used WSL Ubuntu 22.04, GCC 11.4.0 and `-O3 -std=c99`. The final optimized C search was subsequently rechecked over all states in Stage 3, with H3 wall-clock time of 285.33 seconds. H4 is not applicable to the adopted byte-distance/uint16-transition layout; experimental packed files are not linked. The baseline repository HEAD was `231796cc48868f4ea276f652139b6bebbad0cd02`.

### 2.8 What Remains for Target Validation

The mathematical argument establishes shortest-path optimality, and the host operation counts support choosing the joint heuristic. They do not establish compliance with the 50-million-instruction limit.

Stage 3 will refine the C implementation and compare target-relevant operation costs. Stage 4 must measure the final renderer-off RV32I program using the pinned Ripes build and `--iret`, including the specified vector and all 2,644 distance-11 states. The state with the largest host edge count is not automatically the state with the largest retired-instruction count.


