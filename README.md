# iyi Metric

A port of [crystal-metric](https://github.com/kostya/crystal-metric) — 26
benchmarks in one file — to iyi. Each benchmark is a class implementing the
`Bench` trait; the parameters, inputs and expected results are the Crystal
file's, and so is every result it prints.

## iyi compiles it up to 5.6x faster than Crystal

The same 26 benchmarks, the same results, digit for digit. The iyi version is
2,935 lines against Crystal's 2,261, and it still compiles faster in every
scenario measured:

<table>
<tr><th></th><th>Crystal 1.21.0</th><th>iyi 0.15.4</th><th></th></tr>
<tr><td>Build from scratch (debug)</td><td>4.83 s</td><td><b>0.87 s</b></td><td><h3>5.6x faster</h3></td></tr>
<tr><td>Type check (<code>--no-codegen</code>)</td><td>1.02 s</td><td><b>0.25 s</b></td><td><h3>4.1x faster</h3></td></tr>
<tr><td>Rebuild after a one-line edit (debug)</td><td>1.98 s</td><td><b>0.52 s</b></td><td><h3>3.8x faster</h3></td></tr>
<tr><td><code>--release</code> build</td><td>21.06 s</td><td><b>10.80 s</b></td><td><h3>1.9x faster</h3></td></tr>
</table>

The debug loop is under a second. In the 4.83 s Crystal takes to build this
program from nothing, iyi builds it **five and a half times**, and a build
from scratch takes **about half the compiler memory**.

Median of five runs per scenario, alternating between the compilers, each
build with its own compiler cache in a scratch directory:

| Scenario | Crystal (s) | iyi (s) | iyi is | Crystal RSS (MiB) | iyi RSS (MiB) |
|---|--:|--:|--:|--:|--:|
| Type check only (`--no-codegen`) | 1.02 | 0.25 | **4.1x faster** | 298 | 226 |
| Debug build, cold cache | 4.83 | 0.87 | **5.6x faster** | 843 | 413 |
| Debug build, warm cache, no change | 1.98 | 0.49 | **4.0x faster** | 440 | 280 |
| Debug build, warm cache, one-line edit | 1.98 | 0.52 | **3.8x faster** | 455 | 281 |
| `--release` build, cold cache | 21.06 | 10.80 | **1.9x faster** | 704 | 377 |
| `--release` build, warm cache, one-line edit | 21.09 | 10.81 | **2.0x faster** | 704 | 377 |

The one-line edit changes a string literal in the driver, on the same line in
both files. `--release` is where the gap is narrowest; there both compilers
hand the program to LLVM 20's optimiser. Measured on the machine described
under [Run time](#run-time-crystal-vs-iyi), load average 12–21. Reproduce
with `./compile_speed.py`. An earlier run of the same script put every ratio
it shares with this one within 0.5x of the numbers above.

## Run

```
iyi build --release -o metric metric.iyi
./metric
./metric Brainfuck2
./metric Brainfuck,Brainfuck2
```

A `--release` run without a filter writes `results.js` beside `metric.iyi`;
a build without `--release` reads it and prints each benchmark's time as an
award against the release time. `SILENT=1` prints only the summary line,
`RUN_MARK=1` prints `---RUN---` before each benchmark. The exit status is 1
when any result differs from its expected value.

## Expected values

Every benchmark produces the same result as Crystal's `metric.cr`: the 22
that print `ok` match the same expected values, and the four JSON benchmarks
print `err` in both, with the same numbers digit for digit (`JsonGenerate`
checksum `3931493865`). The four expected values in `metric.cr` are stale.
Crystal 1.9.2, 1.13.3, 1.16.3, 1.17.1, 1.18.2, 1.19.1, 1.20.0 and 1.21.0 on
Linux x86_64 all print the same `JsonGenerate` and `JsonParsePure` results as
iyi. Where the stale values come from:

- `JsonParsePure`, `JsonParseSerializable` and `JsonParsePull` expect the
  averages from before upstream commit `a73bad6` added `.round(10)` to the
  generated coordinates. Without the rounding, Crystal's average `x` is
  `0.4999535894712113`, the expected value.
- `JsonGenerate` expects `1584466874`, which neither the rounded input
  (`3931493865`) nor the unrounded input (`3249492003`) produces.

The expected values are kept as the Crystal file has them.

`Knuckeotide`, `RegexDna` and `Revcomp` read input produced by `Fasta`, whose
random state is global, as in Crystal: they match their expected values only
when `Fasta` runs first, which the full run does.

## Run time: Crystal vs iyi

`./compare.py` builds `../crystal-metric/metric.cr` and `metric.iyi` with
`--release`, runs each binary five times, alternating between them, and
keeps the fastest time per benchmark. `✗` marks a result that differs from
its expected value (see above).

Crystal 1.21.0 (LLVM 20.1.8) vs iyi 0.15.4 (release build from `install.sh`),
on a 12-vCPU QEMU VM with 11 GiB of RAM. The machine had other work running:
load average 21–32 throughout. Treat differences under about 20% as noise.

| Benchmark | Crystal (s) | iyi (s) | iyi / Crystal |
|---|--:|--:|--:|
| Pidigits | 0.571 | 0.998 | 1.75 |
| Binarytrees | 0.754 | 0.965 | 1.28 |
| Brainfuck | 3.648 | 1.389 | 0.38 |
| Brainfuck2 | 1.451 | 1.118 | 0.77 |
| Fannkuchredux | 2.113 | 2.090 | 0.99 |
| Fasta | 0.899 | 0.759 | 0.84 |
| Knuckeotide | 0.725 | 0.743 | 1.03 |
| Mandelbrot | 0.615 | 0.726 | 1.18 |
| Matmul | 0.386 | 0.470 | 1.22 |
| Nbody | 0.642 | 0.810 | 1.26 |
| RegexDna | 1.097 | 0.467 | 0.43 |
| Revcomp | 0.594 | 0.648 | 1.09 |
| Spectralnorm | 0.795 | 0.847 | 1.07 |
| Threadring | 0.546 | 0.761 | 1.39 |
| Base64Encode | 0.869 | 1.750 | 2.01 |
| Base64Decode | 0.763 | 1.665 | 2.18 |
| Primes | 0.804 | 1.086 | 1.35 |
| JsonGenerate | 0.791 ✗ | 0.947 ✗ | 1.20 |
| JsonParsePure | 0.416 ✗ | 0.483 ✗ | 1.16 |
| JsonParseSerializable | 0.303 ✗ | 0.573 ✗ | 1.89 |
| JsonParsePull | 0.286 ✗ | 0.541 ✗ | 1.89 |
| Mandelbrot2 | 0.688 | 1.360 | 1.98 |
| Noise | 1.051 | 1.679 | 1.60 |
| Sudoku | 0.735 | 0.846 | 1.15 |
| TextRaytracer | 1.160 | 1.249 | 1.08 |
| NeuralNet | 0.956 | 1.518 | 1.59 |
| **Total** | **23.660** | **26.489** | **1.12** |
| Geometric mean of ratios | | | 1.21 |
| Peak RSS (MiB) | 1833 | 1684 | 0.92 |
| Binary size (KiB) | 2844 | 925 | 0.33 |

Below 1.00, iyi is faster or smaller. The environment variables `CRYSTAL`,
`IYI`, `CRYSTAL_SRC` and `ROUNDS` override the compilers, the Crystal source
and the number of runs.
