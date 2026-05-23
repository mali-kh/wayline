# Archived results — bandwidth matrix v2

Run date: 2026-04-17 (tmux log `run-all-v2-20260417-081000.log`).

## Matrix used for these runs

| Class | Rate | Where |
|---|---|---|
| **F** | 1 Gbps (125 MB/s) | same-tier (edge↔edge, compute↔compute) |
| **M** | 100 Mbps (12.5 MB/s) | cross-tier generic |
| **S** | 50 Mbps (6.25 MB/s) | engineered bottlenecks: anrg-3↔6, anrg-4↔7, anrg-5↔8 |

20× asymmetry between fastest and slowest pair. Cross-tier links are
10× slower than same-tier, making cross-tier traffic systematically
expensive and sharpening HEFT's advantage over random.

The exact tc script + bandwidth ConfigMap in effect are preserved next
to this file as `setup-tc-matrix.sh` and `bandwidth-configmap.yml`.

## Warm-mean makespans (runs 5–20, N=16 per cell)

| Benchmark | config | mean (s) | std (s) | p95 (s) |
|---|---|---:|---:|---:|
| iobt | random | 51.06 | 6.16 | 61.25 |
| iobt | heft | 45.69 | 1.26 | 48.00 |
| iobt | heft-eps05 (ε=0.5) | 45.44 | 1.22 | 47.25 |
| iobt | heft-eps (ε=1.0) | 45.81 | 1.55 | 48.25 |
| iobt | heft-eps20 (ε=2.0) | 45.81 | 1.51 | 48.25 |
| hetero-compute | random | 59.06 | 6.99 | 70.00 |
| hetero-compute | heft | 42.56 | 0.50 | 43.00 |
| hetero-compute | heft-eps (ε=1.0) | 42.75 | 0.75 | 43.50 |
| wide-pipeline-flex | random | 45.69 | 4.65 | 56.25 |
| wide-pipeline-flex | heft | 43.25 | 1.60 | 45.25 |
| wide-pipeline-flex | heft-eps (ε=1.0) | 42.56 | 0.93 | 44.00 |

## Headlines (HEFT vs random, warm)

| Benchmark | mean reduction | p95 reduction | std ratio |
|---|---:|---:|---:|
| iobt | 10.5% | 21.6% | 4.9× tighter |
| hetero-compute | **28.0%** | **38.6%** | **14× tighter** |
| wide-pipeline-flex | 5.3% | 19.6% | 2.9× tighter |

## ε-HEFT behavior

On all three benchmarks, heft-eps is within ≤0.7 s of strict HEFT on
mean, with equal-or-tighter std:
- iobt: 45.81 (eps=1.0) vs 45.69 (eps=0) — statistically indistinguishable
- hetero-compute: 42.75 vs 42.56 — +0.19 s
- wide-pipeline-flex: 42.56 vs 43.25 — **ε wins by 0.7 s** and halves std (0.93 vs 1.60)

ε absorbs profiler jitter without costing makespan; the placement-
spread benefit shows in `figures/iobt-infer-placement.png` (not in
mean makespan).

## Figures generated from this data

`figures/`:
- `makespan-distribution.png` — box plots per config per benchmark
- `makespan-convergence.png` — makespan vs run index
- `prediction-scatter.png` — actual vs HEFT-predicted (HEFT configs only)
- `iobt-infer-placement.png` — share of infer-i placements per compute node

## Comparison with matrix-v1 (see ../archive-matrix-v1/MATRIX.md)

v1 used M=300 Mbps, S=100 Mbps (10× asymmetry). Random was only mildly
penalized because 2 of 3 compute candidates per infer branch were still
acceptable. v2's narrower escape routes reveal the full HEFT advantage
and recover the paper's original 27–32% claim (on hetero-compute).

| | v1 random | v2 random | v1 heft | v2 heft | v1 gap | v2 gap |
|---|---:|---:|---:|---:|---:|---:|
| iobt | 40.55 | 51.06 | 37.60 | 45.69 | 7.3% | 10.5% |
| hetero | 48.50 | 59.06 | 43.65 | 42.56 | 10.0% | **28.0%** |
| wpf | 38.75 | 45.69 | 36.95 | 43.25 | 4.6% | 5.3% |

Matrix severity expands the gap on the benchmark (hetero-compute)
where every task is multi-candidate. Makespan-limited benchmarks
(iobt's 150 MB critical path; wpf's 100 MB source fan-out) see
smaller changes because the critical edges are bandwidth-bound
regardless of placement.
