# Archived results — bandwidth matrix v1

Run date: 2026-04-17 (tmux log `run-all-20260417-014026.log`).

## Matrix used for these runs

| Class | Rate | Where |
|---|---|---|
| **F** | 1 Gbps (125 MB/s) | same-tier (edge↔edge, compute↔compute) |
| **M** | 300 Mbps (37.5 MB/s) | cross-tier generic |
| **S** | 100 Mbps (12.5 MB/s) | engineered bottlenecks: anrg-3↔6, anrg-4↔7, anrg-5↔8 |

The exact tc script + bandwidth ConfigMap in effect are preserved next to
this file as `setup-tc-matrix.sh` and `bandwidth-configmap.yml`.

## Warm-mean makespans (runs 5–20, N=16 per cell)

| Benchmark | config | mean (s) | std (s) | p95 (s) |
|---|---|---:|---:|---:|
| iobt | random | 40.81 | 3.59 | 46.25 |
| iobt | heft | 37.56 | 1.17 | 40.00 |
| iobt | heft-eps05 (ε=0.5) | 37.62 | 1.54 | 39.75 |
| iobt | heft-eps (ε=1.0) | 37.19 | 1.70 | 39.25 |
| iobt | heft-eps20 (ε=2.0) | 37.12 | 1.27 | 39.25 |
| hetero-compute | random | 47.56 | 3.00 | 53.00 |
| hetero-compute | heft | 43.81 | 0.81 | 45.00 |
| hetero-compute | heft-eps (ε=1.0) | 44.19 | 0.73 | 45.25 |
| wide-pipeline-flex | random | 38.81 | 2.19 | 42.00 |
| wide-pipeline-flex | heft | 36.88 | 1.73 | 39.75 |
| wide-pipeline-flex | heft-eps (ε=1.0) | 37.60 | 1.14 | 39.30 |

## Headlines (HEFT vs random, warm)

| Benchmark | mean reduction | p95 reduction | std ratio |
|---|---:|---:|---:|
| iobt | 8.0% | 13.5% | 3.1× tighter |
| hetero-compute | 7.9% | 15.1% | 3.7× tighter |
| wide-pipeline-flex | 5.0% | 5.4% | 1.3× tighter |

## Figures generated from this data

`figures/`:
- `makespan-distribution.png` — box plots per config per benchmark
- `makespan-convergence.png` — makespan vs run index
- `prediction-scatter.png` — actual vs HEFT-predicted (HEFT configs only)
- `iobt-infer-placement.png` — share of infer-i placements per compute node

## Why kept

Gains with this matrix were modest (5–10% HEFT vs random) because the 3-way
compute candidate set + only-3-bottleneck-pairs structure meant random only
hit a bottleneck ~⅓ of the time per branch. Matrix v2 narrows the escape
routes so random is systematically slow.

These v1 numbers stay as a **less-asymmetric** data point for the paper
(shows HEFT wins even under moderate asymmetry, scales harder under severe
asymmetry).
