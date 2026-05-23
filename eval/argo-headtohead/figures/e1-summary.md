# E1 Results Summary

Warm window: runs 5..20, N=16 per cell.

## Per-cell stats

| Benchmark | System | n | mean (s) | std (s) | p95 (s) |
|---|---|---:|---:|---:|---:|
| iobt | Wayline | 16 | 45.56 | 1.41 | 47.00 |
| iobt | Argo Workflows | 16 | 157.31 | 2.64 | 161.00 |
| hetero-compute | Wayline | 16 | 43.00 | 0.71 | 44.00 |
| hetero-compute | Argo Workflows | 16 | 110.12 | 3.55 | 114.00 |
| wide-pipeline-flex | Wayline | 15 | 45.40 | 1.25 | 47.00 |
| wide-pipeline-flex | Argo Workflows | 16 | 175.94 | 2.46 | 178.00 |

## Wayline vs Argo ratio (Argo/Wayline, warm mean)

| Benchmark | Wayline (s) | Argo (s) | Ratio | Std ratio |
|---|---:|---:|---:|---:|
| iobt | 45.56 | 157.31 | **3.45×** | 1.87× |
| hetero-compute | 43.00 | 110.12 | **2.56×** | 5.02× |
| wide-pipeline-flex | 45.40 | 175.94 | **3.88×** | 1.96× |
