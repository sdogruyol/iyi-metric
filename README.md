# iyi Metric

A port of [crystal-metric](https://github.com/kostya/crystal-metric) — 26
benchmarks in one file — to iyi. Each benchmark is a class implementing the
`Bench` trait; the parameters, inputs and expected results are the Crystal
file's.

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

The four JSON benchmarks print `err`: current Crystal (1.21) running the
original `metric.cr` prints the same four results, digit for digit
(`JsonGenerate` checksum `3931493865`), so the expected values are kept as the
Crystal file has them.

`Knuckeotide`, `RegexDna` and `Revcomp` read input produced by `Fasta`, whose
random state is global, as in Crystal: they match their expected values only
when `Fasta` runs first, which the full run does.
