#!/usr/bin/env python3
"""HackMD 1.3: simulation rate, retired instructions per second.

Builds the renderer-off CLI program for a given 14-character vector, runs it
on each requested Ripes processor model, and reports retired instructions,
cycles, CPI, Ripes's own reported execution time, the wall-clock time of the
whole process, and the resulting instructions-per-second rate.

Two timings are printed on purpose. --exectime is Ripes's measurement of the
simulation loop alone; the process wall clock additionally carries assembler
and start-up cost, so it is the pessimistic bound. Report whichever one the
note's measurement conventions declare, but record both so the overhead is
visible.

Usage, from Windows:
    python tools/measure_sim_rate.py
    python tools/measure_sim_rate.py --vectors 21345671111111 54721631111111 \
        --procs RV32_ISS RV32_5S --repeat 5
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cube_tables  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(vector, out_path):
    cmd = [sys.executable, os.path.join(ROOT, "tools", "build_rv32i_program.py"),
           "--vector", vector, "--output", out_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_once(ripes_exe, src, proc, timeout_ms):
    cmd = [
        ripes_exe, "--mode", "cli", "--src", src, "-t", "asm",
        "--proc", proc, "--timeout", str(timeout_ms),
        "--iret", "--cycles", "--cpi", "--exectime", "--regs", "--json",
    ]
    started = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.perf_counter() - started
    start = result.stdout.find("{")
    if result.returncode != 0 or start < 0:
        return None, wall, result.stdout + result.stderr
    try:
        data = json.loads(result.stdout[start:])
    except json.JSONDecodeError:
        return None, wall, result.stdout + result.stderr
    return data, wall, None


def pick(data, *keys):
    for key in keys:
        if key in data:
            return data[key]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", nargs="+",
                        default=["21345671111111", "54721631111111"])
    parser.add_argument("--procs", nargs="+", default=["RV32_ISS", "RV32_5S"])
    parser.add_argument("--repeat", type=int, default=3,
                        help="runs per cell; the median is reported")
    parser.add_argument("--timeout", type=int, default=600000)
    parser.add_argument("--ripes", default=cube_tables.default_ripes_path())
    args = parser.parse_args()

    if not os.path.exists(args.ripes):
        raise SystemExit(f"Ripes.exe not found at {args.ripes}")

    rows = []
    for vector in args.vectors:
        src = os.path.join(ROOT, "tools", f"_merged_rate_{vector}.s")
        build(vector, src)
        for proc in args.procs:
            samples = []
            payload = None
            for _ in range(max(1, args.repeat)):
                data, wall, err = run_once(args.ripes, src, proc, args.timeout)
                if err:
                    raise SystemExit(f"{vector} on {proc} failed:\n{err}")
                payload = data
                samples.append((wall, pick(data, "execution time (ms)",
                                           "exectime")))
            walls = [s[0] for s in samples]
            exectimes = [s[1] for s in samples if s[1] is not None]
            iret = pick(payload, "# instructions retired", "iret")
            cycles = pick(payload, "cycles")
            cpi = pick(payload, "CPI", "cpi")
            length = payload.get("registers", {}).get("x10")
            wall_med = statistics.median(walls)
            exec_med = statistics.median(exectimes) if exectimes else None
            rows.append({
                "vector": vector, "proc": proc, "iret": iret,
                "cycles": cycles, "cpi": cpi, "length": length,
                "wall_s": wall_med,
                "exec_ms": exec_med,
                "rate_wall": iret / wall_med if iret and wall_med else None,
                "rate_exec": (iret / (exec_med / 1000.0)
                              if iret and exec_med else None),
                "runs": len(samples),
            })
            print(f"  {vector} {proc}: iret={iret} cycles={cycles} cpi={cpi} "
                  f"len={length} wall={wall_med:.3f}s exectime={exec_med}")
        os.remove(src)

    print()
    print("| Input | Model | Retired instructions | Ripes exec time | "
          "Process wall time | Instr/s, exec time | Instr/s, wall clock | "
          "Result |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        exec_s = f"{r['exec_ms'] / 1000.0:.3f} s" if r["exec_ms"] else "n/a"
        rate_e = f"{r['rate_exec']:,.0f}" if r["rate_exec"] else "n/a"
        print(f"| {r['vector']} | {r['proc']} | {r['iret']:,} | {exec_s} | "
              f"{r['wall_s']:.3f} s | {rate_e} | {r['rate_wall']:,.0f} | "
              f"optimal length {r['length']} |")
    print()
    print(f"median of {rows[0]['runs']} runs per cell; "
          f"Ripes build at {args.ripes}")


if __name__ == "__main__":
    main()
