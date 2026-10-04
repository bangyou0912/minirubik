#!/usr/bin/env python3
"""Runs every distance-11 state through the full RV32I pipeline on Ripes
and records the retired instruction count of each.

The program is the one tools/test_full_pipeline.py builds:
full_pipeline_harness.s + input_coords.s + ida_search.s + search_tables.s.
It parses the ASCII vector, solves it, and replays the returned moves in
the program, so each count is the official renderer-off main.s path plus
the replay check. A state passes only if the length is 11 and the replay
ends at the goal coordinates.

The distance-11 states come from the independent BFS in
tools/reference_model.py (about 3.5 minutes). Results are appended to a
CSV as they finish, so an interrupted sweep resumes where it stopped.

Usage (Windows Python, since Ripes.exe is a Windows program):
    python tools/sweep_dist11_iss.py --limit 5        # quick trial
    python tools/sweep_dist11_iss.py                  # all 2,644 states
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reference_model  # noqa: E402
from test_full_pipeline import build_merged, run, signed32, GOAL  # noqa: E402

FIELDS = ["vector", "length", "final_perm", "final_a", "final_b", "iret", "pass"]


def distance_11_vectors():
    dist, _ = reference_model.bfs()
    vectors = sorted(reference_model.state_to_vector(p, o)
                     for (p, o), d in dist.items() if d == 11)
    if len(vectors) != 2644:
        sys.exit(f"expected 2644 distance-11 states, BFS found {len(vectors)}")
    return vectors


def run_one(args, workdir, vector):
    src = os.path.join(workdir, f"sweep_{vector}.s")
    rv = os.path.join(os.path.dirname(HERE), "rv32i")
    build_merged(os.path.join(HERE, "full_pipeline_harness.s"), vector,
                 [os.path.join(rv, "input_coords.s"),
                  os.path.join(rv, "ida_search.s"),
                  os.path.join(rv, "search_tables.s")], src)
    try:
        data, err = run(args.ripes, src, args.proc, args.timeout)
    finally:
        os.remove(src)
    if err:
        return {"vector": vector, "length": "", "final_perm": "", "final_a": "",
                "final_b": "", "iret": "", "pass": f"ERROR {err.strip()[:80]}"}
    regs = data.get("registers", {})
    length = signed32(regs.get("x10"))
    final = (regs.get("x11"), regs.get("x12"), regs.get("x13"))
    ok = length == 11 and final == GOAL
    return {"vector": vector, "length": length, "final_perm": final[0],
            "final_a": final[1], "final_b": final[2],
            "iret": data.get("# instructions retired"), "pass": ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "_sweep_dist11_iss.csv"))
    ap.add_argument("--proc", default="RV32_ISS")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=600000)
    ap.add_argument("--ripes", default=os.path.join(
        os.environ.get("USERPROFILE", ""), "Apps", "Ripes-continuous", "Ripes.exe"))
    args = ap.parse_args()

    print("building the reference BFS, about 3.5 minutes ...", flush=True)
    vectors = distance_11_vectors()
    done = {}
    if os.path.exists(args.out):
        with open(args.out, newline="") as f:
            for row in csv.DictReader(f):
                if row["pass"] in ("True", "False"):
                    done[row["vector"]] = row
    todo = [v for v in vectors if v not in done]
    if args.limit is not None:
        todo = todo[:args.limit]
    print(f"{len(vectors)} distance-11 states, {len(done)} already in {args.out}, "
          f"running {len(todo)} on {args.proc} with {args.workers} workers", flush=True)

    new_file = not os.path.exists(args.out)
    started = time.time()
    with open(args.out, "a", newline="") as f, \
            tempfile.TemporaryDirectory() as workdir, \
            ThreadPoolExecutor(args.workers) as pool:
        writer = csv.DictWriter(f, FIELDS)
        if new_file:
            writer.writeheader()
        futures = [pool.submit(run_one, args, workdir, v) for v in todo]
        for n, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            writer.writerow(row)
            f.flush()
            done[row["vector"]] = {k: str(v) for k, v in row.items()}
            if n % 50 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)} done, {time.time() - started:.0f} s", flush=True)

    rows = [done[v] for v in vectors if v in done]
    passed = [r for r in rows if r["pass"] == "True"]
    print(f"\nstates measured: {len(rows)}/{len(vectors)}")
    print(f"passed (length 11 and replay reaches {GOAL}): {len(passed)}/{len(rows)}")
    failed = [r["vector"] for r in rows if r["pass"] != "True"]
    if failed:
        print("failed:", " ".join(failed[:20]))
    if passed:
        irets = sorted((int(r["iret"]), r["vector"]) for r in passed)
        mean = sum(i for i, _ in irets) / len(irets)
        print(f"min retired: {irets[0][0]:,} ({irets[0][1]})")
        print(f"max retired: {irets[-1][0]:,} ({irets[-1][1]})")
        print(f"mean retired: {mean:,.0f}")
        print(f"max as share of 5x10^7: {irets[-1][0] / 5e7:.1%}")
        print("top 5 by retired instructions:")
        for i, v in irets[:-6:-1]:
            print(f"  {v}  {i:,}")


if __name__ == "__main__":
    main()
