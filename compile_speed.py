#!/usr/bin/env python3
"""Crystal vs iyi compile time on the same 26 benchmarks.

Compiles crystal-metric's metric.cr with `crystal` and this directory's
metric.iyi with `iyi` in each scenario below, ROUNDS times, alternating
between the two compilers, and prints a Markdown table of the median wall
time and the compiler's peak memory. Every build runs in a scratch directory
with its own compiler cache, so a "cold" build starts with nothing cached and
the caches in your home directory are neither used nor touched.

    ./compile_speed.py

Environment: CRYSTAL (default `crystal`), IYI (default `iyi`),
CRYSTAL_SRC (default ../crystal-metric/metric.cr), ROUNDS (default 5).
"""

import os
import signal
import shutil
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CRYSTAL = os.environ.get("CRYSTAL", "crystal")
IYI = os.environ.get("IYI", "iyi")
CRYSTAL_SRC = os.environ.get("CRYSTAL_SRC", os.path.join(HERE, "..", "crystal-metric", "metric.cr"))
ROUNDS = int(os.environ.get("ROUNDS", "5"))
# The slowest build here takes about 40 s on a loaded machine.
HANG_SECONDS = 120

# The edit: one string literal on one line of the driver, the same line in
# both files, and one that a --release build compiles (the release-results
# error is behind `unless flag?(:release)`, so editing it would let a release
# build reuse everything). Each edited build flips it, so every one of them
# sees a change.
EDIT_FROM = "---RUN---"
EDIT_TO = "---RUN!--"


class Compiler:
    def __init__(self, name, source, command, cache_var, work):
        self.name = name
        # Not `name`: Crystal 1.21's debug build deadlocks, every thread
        # parked on a futex, when the source sits in a directory called
        # `Crystal`; it did every time it was tried, and never in `src`.
        self.dir = os.path.join(work, "src-" + name.lower())
        self.source = os.path.join(self.dir, os.path.basename(source))
        self.command = command
        self.cache_var = cache_var
        self.cache = os.path.join(work, "cache-" + name.lower())
        self.hangs = 0
        os.makedirs(self.dir)
        shutil.copy(source, self.dir)
        with open(self.source) as f:
            if EDIT_FROM not in f.read():
                sys.exit(f"{self.source}: the edit's anchor {EDIT_FROM!r} is not there")

    def clear_cache(self):
        shutil.rmtree(self.cache, ignore_errors=True)
        os.makedirs(self.cache)

    def flip_edit(self):
        with open(self.source) as f:
            text = f.read()
        if EDIT_FROM in text:
            text = text.replace(EDIT_FROM, EDIT_TO)
        else:
            text = text.replace(EDIT_TO, EDIT_FROM)
        with open(self.source, "w") as f:
            f.write(text)

    def build(self, args, cold=False):
        """Wall seconds and peak RSS in KiB of one compiler run.

        A run that outlives HANG_SECONDS is killed and run again (a cold one
        from an empty cache again), and counted in `self.hangs`, so another
        deadlock like the one `__init__` names is reported, not waited on.
        """
        env = dict(os.environ, **{self.cache_var: self.cache})
        command = ["/usr/bin/time", "-f", "%e %M"] + self.command + args + [os.path.basename(self.source)]
        while True:
            proc = subprocess.Popen(
                command,
                cwd=self.dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                out, err = proc.communicate(timeout=HANG_SECONDS)
                break
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                self.hangs += 1
                print(f"{self.name} {' '.join(args)}: hung, killed, retrying", file=sys.stderr)
                if cold:
                    self.clear_cache()
        if proc.returncode != 0:
            sys.exit(f"{self.name} {' '.join(args)} failed:\n{out}{err}")
        seconds, rss = err.strip().splitlines()[-1].split()
        return float(seconds), int(rss)


# (label, build arguments, cold: clear the cache first, edit: flip the edit first)
SCENARIOS = [
    ("Type check only (`--no-codegen`)", ["--no-codegen"], True, False),
    ("Debug build, cold cache", ["-o", "metric"], True, False),
    ("Debug build, warm cache, no change", ["-o", "metric"], False, False),
    ("Debug build, warm cache, one-line edit", ["-o", "metric"], False, True),
    ("`--release` build, cold cache", ["--release", "-o", "metric"], True, False),
    ("`--release` build, warm cache, one-line edit", ["--release", "-o", "metric"], False, True),
]


def main():
    work = tempfile.mkdtemp(prefix="metric-compile-")
    try:
        compilers = [
            Compiler("Crystal", CRYSTAL_SRC, [CRYSTAL, "build"], "CRYSTAL_CACHE_DIR", work),
            Compiler("iyi", os.path.join(HERE, "metric.iyi"), [IYI, "build"], "IYI_CACHE_DIR", work),
        ]
        for c in compilers:
            c.clear_cache()
        rows = []
        for label, args, cold, edit in SCENARIOS:
            samples = {c.name: [] for c in compilers}
            for r in range(ROUNDS):
                for c in compilers:
                    if cold:
                        c.clear_cache()
                    elif r == 0:
                        c.build(args)  # warm the cache for this mode, not timed
                    if edit:
                        c.flip_edit()
                    print(f"{label}: round {r + 1}/{ROUNDS}: {c.name}", file=sys.stderr)
                    samples[c.name].append(c.build(args, cold))
            rows.append((label, samples))
    finally:
        shutil.rmtree(work)

    print("| Scenario | Crystal (s) | iyi (s) | iyi is | Crystal RSS (MiB) | iyi RSS (MiB) |")
    print("|---|--:|--:|--:|--:|--:|")
    for label, samples in rows:
        cr = statistics.median(s for s, _ in samples["Crystal"])
        iy = statistics.median(s for s, _ in samples["iyi"])
        cr_rss = max(m for _, m in samples["Crystal"]) / 1024
        iy_rss = max(m for _, m in samples["iyi"]) / 1024
        speed = f"**{cr / iy:.1f}x faster**" if iy < cr else f"{iy / cr:.1f}x slower"
        print(f"| {label} | {cr:.2f} | {iy:.2f} | {speed} | {cr_rss:.0f} | {iy_rss:.0f} |")
    for c in compilers:
        if c.hangs:
            print(f"\n{c.name}: {c.hangs} build(s) hung and were killed and run again.")


if __name__ == "__main__":
    main()
