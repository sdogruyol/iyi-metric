#!/usr/bin/env python3
"""Crystal vs iyi on the same 26 benchmarks.

Builds crystal-metric's metric.cr and this directory's metric.iyi with
--release, runs the two binaries ROUNDS times each, interleaved so that load
on the machine falls on both alike, and prints a Markdown table of the fastest
time per benchmark. Each binary runs in a scratch directory of its own, so the
results.js next to metric.iyi is left alone.

    ./compare.py

Environment: CRYSTAL (default `crystal`), IYI (default `iyi`),
CRYSTAL_SRC (default ../crystal-metric/metric.cr), ROUNDS (default 5).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CRYSTAL = os.environ.get("CRYSTAL", "crystal")
IYI = os.environ.get("IYI", "iyi")
CRYSTAL_SRC = os.environ.get("CRYSTAL_SRC", os.path.join(HERE, "..", "crystal-metric", "metric.cr"))
ROUNDS = int(os.environ.get("ROUNDS", "5"))

LINE = re.compile(r"^(\w+): (ok|err)\b")


def build(work):
    cr = os.path.join(work, "crystal")
    iy = os.path.join(work, "iyi")
    os.makedirs(cr)
    os.makedirs(iy)
    shutil.copy(CRYSTAL_SRC, cr)
    shutil.copy(os.path.join(HERE, "metric.iyi"), iy)
    shutil.copy(os.path.join(HERE, "iyi.mod"), iy)
    subprocess.run([CRYSTAL, "build", "--release", "metric.cr", "-o", "metric"], cwd=cr, check=True)
    subprocess.run([IYI, "build", "--release", "-o", "metric", "metric.iyi"], cwd=iy, check=True)
    return {"Crystal": cr, "iyi": iy}


def run(directory):
    """One full run: time per benchmark (results.js), ok/err per benchmark, peak RSS in KiB."""
    results = os.path.join(directory, "results.js")
    if os.path.exists(results):
        os.remove(results)
    # Exit status 1 means a result differed from its expected value; the
    # statuses are collected below, so it is not a failure of the run.
    proc = subprocess.run(
        ["/usr/bin/time", "-f", "%M", "./metric"], cwd=directory, capture_output=True, text=True
    )
    statuses = {}
    for line in proc.stdout.splitlines():
        match = LINE.match(line)
        if match:
            statuses[match.group(1)] = match.group(2)
    rss = int(proc.stderr.strip().splitlines()[-1])
    with open(results) as f:
        times = json.load(f)
    return times, statuses, rss


def main():
    work = tempfile.mkdtemp(prefix="metric-compare-")
    try:
        dirs = build(work)
        times = {name: {} for name in dirs}
        statuses = {}
        rss = {name: 0 for name in dirs}
        for r in range(ROUNDS):
            for name, directory in dirs.items():
                print(f"round {r + 1}/{ROUNDS}: {name}", file=sys.stderr)
                t, s, m = run(directory)
                for bench, seconds in t.items():
                    times[name][bench] = min(seconds, times[name].get(bench, seconds))
                statuses[name] = s
                rss[name] = max(rss[name], m)
        sizes = {name: os.path.getsize(os.path.join(d, "metric")) for name, d in dirs.items()}
    finally:
        shutil.rmtree(work)

    cr, iy = times["Crystal"], times["iyi"]
    print(f"| Benchmark | Crystal (s) | iyi (s) | iyi / Crystal |")
    print(f"|---|--:|--:|--:|")
    for bench in cr:
        marks = {n: "" if statuses[n].get(bench) == "ok" else " ✗" for n in dirs}
        print(
            f"| {bench} | {cr[bench]:.3f}{marks['Crystal']} | {iy[bench]:.3f}{marks['iyi']} "
            f"| {iy[bench] / cr[bench]:.2f} |"
        )
    total_cr, total_iy = sum(cr.values()), sum(iy.values())
    print(f"| **Total** | **{total_cr:.3f}** | **{total_iy:.3f}** | **{total_iy / total_cr:.2f}** |")
    geo = 1.0
    for bench in cr:
        geo *= iy[bench] / cr[bench]
    print(f"| Geometric mean of ratios | | | {geo ** (1 / len(cr)):.2f} |")
    print(f"| Peak RSS (MiB) | {rss['Crystal'] / 1024:.0f} | {rss['iyi'] / 1024:.0f} | {rss['iyi'] / rss['Crystal']:.2f} |")
    print(
        f"| Binary size (KiB) | {sizes['Crystal'] / 1024:.0f} | {sizes['iyi'] / 1024:.0f} "
        f"| {sizes['iyi'] / sizes['Crystal']:.2f} |"
    )


if __name__ == "__main__":
    main()
