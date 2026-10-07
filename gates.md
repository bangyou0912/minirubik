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
| T7 | Solved, short and hard tests reproduce on ISS and a visual pipeline model; arbitrary inlined input supported | PASS on the pinned RV32_ISS and RV32_5S for all three tests; editable generic source and extra arbitrary-input checks also pass. Actual GUI display/wire screenshots remain MANUAL REQUIRED | `asm-r2-native-measurements.json`, `generic-source-test.json`, `extra-test-results.json`; [GUI procedure](visualization.md) |

T5 reports the executed target coverage; it does not claim an exhaustive assembly run over all 3,674,160 states. H3 establishes the host search's exhaustive optimality. T7's CLI run of RV32_5S executes the visual model, but does not substitute for the assignment's separate GUI wire-signal observation.

| Actual PDB bytes | Populated | Maximum distance | Solved index | Solved distance |
|---|---:|---:|---:|---:|
| Permutation | 5,040 / 5,040 | 7 | 0 | 0 |
| Joint A | 5,670 / 5,670 | 7 | 0 | 0 |
| Joint B | 5,670 / 5,670 | 7 | 2,916 | 0 |

Permutation transitions contain 15,120 uint16 entries in 0..5039. Shared joint transitions contain 17,010 uint16 entries in 0..5669. A transition's solved entry is a quarter-turn successor, not a distance of zero; the table audit lists those successors explicitly.

The complete renderer-off ISS sweep covers exactly the host oracle's 2,644 unique hard states, with no omitted or timed-out case. Maximum **7,832,368 < 50,000,000** at `54721631111111`; specified vector **2,867,160**. Final assembly `.text` is 1,864 bytes; CLI static data is 81,020 bytes; complete standalone GUI static data is 81,168 bytes, both below 131,072 bytes. The GCC reference uses 2,184 text bytes and retires 5,474,251 instructions on the specified input.

The renderer passed 1,323 independent geometry comparisons and 29,750 target framebuffer word comparisons across 34 frames in ISS and RV32_5S. Those framebuffer tests use a RAM stand-in. Real peripheral animation and control-signal screenshots are **manual required**, with a precise capture checklist in [visualization.md](visualization.md).
