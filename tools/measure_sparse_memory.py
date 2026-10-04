#!/usr/bin/env python3
"""HackMD 1.2: host bytes per guest byte in Ripes's sparse memory.

Ripes stores guest memory in an unordered_map keyed by byte address, one hash
entry per distinct guest byte, so a 32-bit store creates four entries. This
script measures what one guest byte actually costs in host memory, which is
what makes the 128 KiB static budget on the target bite.

Method. tools/sparse_mem_harness.s writes one byte to each of N consecutive
guest addresses in an otherwise untouched region, so exactly N map entries go
live. Ripes runs under a Windows process handle this script holds open, and
PeakWorkingSetSize is read through GetProcessMemoryInfo after the process
exits, which is race-free: the peak is cumulative, so no polling is needed and
a short run cannot be missed. Subtracting the N=0 control run leaves the cost
attributable to the N live entries.

Usage, from Windows:
    python tools/measure_sparse_memory.py
    python tools/measure_sparse_memory.py --sizes 0 4096 65536 1048576 \
        --repeat 5 --project 18405414
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cube_tables  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "tools", "sparse_mem_harness.s")


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def peak_working_set(handle):
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(
        wt.HANDLE(handle), ctypes.byref(counters), counters.cb)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.PeakWorkingSetSize, counters.PeakPagefileUsage


def run_probe(ripes_exe, guest_bytes, timeout_ms):
    cmd = [
        ripes_exe, "--mode", "cli", "--src", HARNESS, "-t", "asm",
        "--proc", cube_tables.DEFAULT_PROC, "--timeout", str(timeout_ms),
        "--reginit", f"gpr:10={guest_bytes}", "--iret", "--json",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise SystemExit(f"N={guest_bytes} failed:\n{out}\n{err}")
    # The Popen handle is still open here, so the exited process object still
    # carries its accounting.
    peak_ws, peak_commit = peak_working_set(int(proc._handle))
    return peak_ws, peak_commit


def human(n):
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024 or unit == "GiB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{n:,.0f} B"
        n /= 1024.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int,
                        default=[0, 4096, 65536, 262144, 1048576, 4194304])
    parser.add_argument("--repeat", type=int, default=3,
                        help="runs per size; the median is reported")
    parser.add_argument("--timeout", type=int, default=600000)
    parser.add_argument("--project", type=int, default=18405414,
                        help="baseline peak in bytes, projected at the "
                             "measured ratio")
    parser.add_argument("--ripes", default=cube_tables.default_ripes_path())
    args = parser.parse_args()

    if not os.path.exists(args.ripes):
        raise SystemExit(f"Ripes.exe not found at {args.ripes}")
    if 0 not in args.sizes:
        raise SystemExit("--sizes must include 0, the control run")

    results = {}
    for n in sorted(set(args.sizes)):
        ws_samples, commit_samples = [], []
        for _ in range(max(1, args.repeat)):
            ws, commit = run_probe(args.ripes, n, args.timeout)
            ws_samples.append(ws)
            commit_samples.append(commit)
        results[n] = (statistics.median(ws_samples),
                      statistics.median(commit_samples))
        print(f"  N={n:>10,}  peak working set {human(results[n][0])}  "
              f"peak commit {human(results[n][1])}")

    base_ws, base_commit = results[0]
    print()
    print("| Guest bytes touched | Ripes peak working set | Delta over "
          "control | Host bytes per guest byte |")
    print("| --- | --- | --- | --- |")
    print(f"| 0, control | {human(base_ws)} | 0 B | n/a |")
    ratios = []
    for n in sorted(results):
        if n == 0:
            continue
        ws = results[n][0]
        delta = ws - base_ws
        ratio = delta / n
        ratios.append((n, ratio))
        print(f"| {n:,} | {human(ws)} | {human(delta)} | {ratio:.2f} |")

    print()
    largest_n, largest_ratio = ratios[-1]
    print(f"Largest probe, N={largest_n:,}, gives {largest_ratio:.2f} host "
          f"bytes per guest byte. Smaller probes read high because the "
          f"control's own allocator slack absorbs them, so the largest probe "
          f"is the one to quote.")
    projected = args.project * largest_ratio
    print(f"Projection: the baseline's {args.project:,}-byte peak would cost "
          f"{human(projected)} of host memory at that ratio.")
    print()
    print(f"median of {max(1, args.repeat)} runs per size; Ripes build at "
          f"{args.ripes}; model {cube_tables.DEFAULT_PROC}")


if __name__ == "__main__":
    main()
