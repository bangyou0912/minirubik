## Stage 1: Baseline and Target Measurements

### Baseline Computation and Invariants

`solver.c` builds a complete breadth-first table for the 2x2x2 cube with one corner fixed. In the half-turn metric, each of the nine moves `R R2 R' B B2 B' D D2 D'` costs one step. First discovery in FIFO BFS establishes a shortest path; the stored inverse move takes a query one level closer to solved. Queries need at most eleven move-table lookups, plus move application and re-ranking.

The seven movable corners are represented by `p[7]` and `o[7]`. Positions form a permutation of 0 through 6, orientations are 0 through 2, and the total orientation is zero modulo three. The seventh orientation is determined by the first six. Permutation need not be even. A Lehmer rank and a base-three orientation rank combine as `p_rank * 729 + o_rank`, giving `7! * 3^6 = 3,674,160` states.

The three dominant allocations total 18,405,414 bytes (17.553 MiB): a 3,674,160-byte move table, a 14,696,640-byte queue, and 34,614 bytes of factored transitions. Building the table expands 33,067,440 edges and performs 66,134,880 coordinate updates. Assuming fifteen instructions per update gives 992,023,200 instructions. This is an estimate, not a Ripes baseline measurement, and omits other overhead.

### Reproduced Measurements

The probe writes one byte to each of N consecutive guest addresses. Its loop has four instructions, and the measured complete program retires `4*N + 7`. Each configuration was run three times; the summary uses medians. `target/measurements.json` retains the individual readings. Ripes runs as a Windows executable; the probe sources being stored in WSL does not change the process executing the simulator.

The pinned executable is `C:\Users\user\Apps\Ripes-continuous\Ripes.exe`, identified by SHA-256:

```text
bd2ddea8cd6fcf6902cda7366fe99ab6dd0c7fdbbc7efcfdb89ede20acc67f0f
```

| Guest bytes written, RV32_ISS | Median Windows peak working set |
|---:|---:|
| 0 | 30,687,232 bytes |
| 4,096 | 31,051,776 bytes |
| 1,048,576 | 115,286,016 bytes |

The slope between the small and large regions is `(115286016 - 31051776) / (1048576 - 4096) = 80.65` additional host bytes per additional guest byte. Projecting the baseline's dominant guest allocations using this measured slope gives approximately 1.38 GiB of additional host memory. This is an extrapolation for this installation, not a guaranteed hash-map ratio or a measured baseline run.

| Processor | Retired instructions | Median Ripes execution time | Instructions/s |
|---|---:|---:|---:|
| RV32_ISS | 4,194,311 | 559 ms | 7,503,240 |
| RV32_5S | 262,151 | 1,691 ms | 155,027 |

The rates use Ripes simulation time rather than process startup time. Extrapolating 992,023,200 instructions gives approximately 2.20 minutes on ISS and 1.78 hours on the five-stage model. BFS random accesses differ from this sequential probe, so these are idealized estimates.

### Critical Reading of Section 7

Section 7 recommends keeping the complete table as a verification artifact. Its verification value can be retained on the host without forcing every simulated query to rebuild it. Removing only the queue still leaves about 3.5 MiB of move data, above the 128 KiB target limit, and sweeping by BFS level adds millions of comparisons. RV32I additionally has no multiply or divide instructions, so repeatedly splitting and recombining full ranks incurs synthesized arithmetic or forbidden helper calls unless the representation is changed.

The target therefore needs a compact representation and an optimal query-time search. Stages 2 and 3 adopt coordinate transitions, abstract distance lower bounds, and explicit-stack IDA*, while exhaustive BFS remains a host verification oracle.

### Optional Native Baseline

A separate Linux solver run under WSL reported 19,044 KiB peak RSS (18.60 MiB), 0.10 seconds elapsed, and exit status zero for `21345671111111`. This is supplemental evidence. Linux RSS and Windows peak working set are different accounting metrics; no precise cross-environment overhead ratio is inferred from them.
