#!/usr/bin/env python3
"""T7-style check: runs the exact same merged source on RV32_ISS and on a
pipelined model, confirming the solution length and replay goal coordinates
match, and reporting each model's retired instructions, cycles, and CPI.

Builds ONE merged .s (full_pipeline_harness.s + a test_string for the
given vector + input_coords.s + ida_search.s + search_tables.s) and runs
it unmodified on both --proc values, so the two runs are provably the
same program. RV32_ISS retires the terminating ecall differently and reports
one more retired instruction than the visual models in the tested continuous
build. That model-specific difference is reported but is not a T7 failure.

Usage (Windows Python, Ripes.exe is a native Windows app):
    python tools\\test_full_pipeline.py --vector 21345671111111 \\
        --parser rv32i\\input_coords.s --ida rv32i\\ida_search.s \\
        --tables rv32i\\search_tables.s
"""
import argparse
import json
import os
import subprocess

GOAL = (0, 0, 2916)


def build_merged(harness_path, vector, solution_paths, out_path):
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(".data\ntest_string:\n    .asciz \"%s\"\n\n" % vector)
        f.write(open(harness_path, encoding="utf-8").read())
        for p in solution_paths:
            f.write("\n\n# ---- merged in from " + p + " ----\n")
            f.write(open(p, encoding="utf-8").read())


def run(ripes, src, proc, timeout_ms):
    cmd = [
        ripes, "--mode", "cli", "--src", src, "-t", "asm",
        "--proc", proc, "--timeout", str(timeout_ms),
        "--regs", "--json", "--iret", "--cycles", "--cpi", "--runinfo",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stdout + result.stderr
    start = result.stdout.find("{")
    if start < 0:
        return None, f"no JSON object:\n{result.stdout}\n{result.stderr}"
    try:
        return json.loads(result.stdout[start:]), None
    except json.JSONDecodeError:
        return None, f"non-JSON:\n{result.stdout}\n{result.stderr}"


def signed32(v):
    if v is None:
        return None
    return v - 2**32 if v > 2**31 else v


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--vector", default="21345671111111")
    ap.add_argument("--parser", required=True)
    ap.add_argument("--ida", required=True)
    ap.add_argument("--tables", required=True)
    ap.add_argument(
        "--harness", default=os.path.join(here, "full_pipeline_harness.s"))
    ap.add_argument(
        "--ripes", default=os.path.join(
            os.environ.get("USERPROFILE", ""), "Apps", "Ripes-continuous",
            "Ripes.exe"))
    ap.add_argument("--iss-proc", default="RV32_ISS")
    ap.add_argument("--pipeline-proc", default="RV32_5S")
    ap.add_argument("--timeout", type=int, default=240000)
    ap.add_argument(
        "--keep", action="store_true",
        help="keep the merged .s file for GUI inspection instead of deleting it")
    args = ap.parse_args()

    merged_path = os.path.join(here, "_merged_full_pipeline.s")
    build_merged(args.harness, args.vector, [args.parser, args.ida, args.tables],
                 merged_path)

    results = {}
    ok = True
    for proc in (args.iss_proc, args.pipeline_proc):
        print(f"--- running on {proc} ---")
        data, err = run(args.ripes, merged_path, proc, args.timeout)
        if err:
            print(f"FAIL  {proc}: {err}")
            ok = False
            continue
        regs = data.get("registers", {})
        length = signed32(regs.get("x10"))
        final = (regs.get("x11"), regs.get("x12"), regs.get("x13"))
        iret = data.get("# instructions retired")
        cycles = data.get("cycles")
        cpi = data.get("CPI")
        runinfo = data.get("runinfo") or {}
        results[proc] = dict(
            length=length, final=final, iret=iret, cycles=cycles, cpi=cpi,
            runinfo=runinfo, raw=data)
        print(f"  length={length}  final_coords={final}  "
              f"iret={iret}  cycles={cycles}  cpi={cpi}")
        print(f"  runinfo: {runinfo}")
        if length != 11 and args.vector == "21345671111111":
            print(f"  WARNING: expected length 11 for {args.vector}")
            ok = False
        if final != GOAL:
            print(f"  WARNING: replay did not reach goal {GOAL}")
            ok = False

    if args.iss_proc in results and args.pipeline_proc in results:
        a, b = results[args.iss_proc], results[args.pipeline_proc]
        print("\n--- comparison ---")
        print(f"length match:  {a['length'] == b['length']}")
        print(f"final match:   {a['final'] == b['final']}")
        print(f"iret match:    {a['iret'] == b['iret']} "
              f"({a['iret']} vs {b['iret']})")
        print(f"iret delta:    {a['iret'] - b['iret']}")
        print(f"cycles:        {args.iss_proc}={a['cycles']}  "
              f"{args.pipeline_proc}={b['cycles']}")
        print(f"cpi:           {args.iss_proc}={a['cpi']}  {args.pipeline_proc}={b['cpi']}")

    if args.keep:
        print(f"\nmerged source kept at: {merged_path}")
    else:
        os.remove(merged_path)

    print("\nPASS" if ok else "\nFAIL")


if __name__ == "__main__":
    main()
