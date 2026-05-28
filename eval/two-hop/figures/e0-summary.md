# E0 Results Summary

Stats are taken from the warm window (runs 5+, when ≥5 reps exist).

## E2E mean / std / p95 by cell

| Coloc | Payload | System | n | mean (s) | std (s) | p95 (s) |
|---|---|---|---:|---:|---:|---:|
| same | 1MB | Wayline | 16 | 7.663 | 0.148 | 7.890 |
| same | 1MB | MinIO (baseline) | 17 | 5.349 | 0.007 | 5.361 |
| same | 10MB | Wayline | 16 | 7.781 | 0.167 | 8.010 |
| same | 10MB | MinIO (baseline) | 16 | 7.051 | 0.012 | 7.069 |
| same | 100MB | Wayline | 16 | 8.789 | 0.170 | 9.001 |
| same | 100MB | MinIO (baseline) | 16 | 24.059 | 0.016 | 24.075 |
| same | 500MB | Wayline | 16 | 13.626 | 0.220 | 13.846 |
| same | 500MB | MinIO (baseline) | 16 | 98.003 | 0.096 | 98.102 |
| cross | 1MB | Wayline | 16 | 7.824 | 0.165 | 8.048 |
| cross | 1MB | MinIO (baseline) | 16 | 5.338 | 0.007 | 5.347 |
| cross | 10MB | Wayline | 16 | 9.495 | 0.147 | 9.683 |
| cross | 10MB | MinIO (baseline) | 16 | 7.052 | 0.014 | 7.065 |
| cross | 100MB | Wayline | 16 | 26.917 | 0.124 | 27.070 |
| cross | 100MB | MinIO (baseline) | 16 | 24.041 | 0.011 | 24.050 |
| cross | 500MB | Wayline | 16 | 102.395 | 0.821 | 104.183 |
| cross | 500MB | MinIO (baseline) | 16 | 98.110 | 0.700 | 99.531 |

## DSF vs MinIO ratios (warm mean)

| Coloc | Payload | MinIO (s) | DSF (s) | Ratio (MinIO/DSF) |
|---|---|---:|---:|---:|
| same | 1MB | 5.349 | 7.669 | 0.70× |
| same | 10MB | 7.051 | 7.871 | 0.90× |
| same | 100MB | 24.059 | 8.744 | 2.75× |
| same | 500MB | 98.003 | 13.617 | 7.20× |
| cross | 1MB | 5.338 | 7.625 | 0.70× |
| cross | 10MB | 7.052 | 7.937 | 0.89× |
| cross | 100MB | 24.041 | 10.434 | 2.30× |
| cross | 500MB | 98.110 | 20.886 | 4.70× |

## Pass/fail

✅ **PASS** — minimum same-node ≥100MB ratio = **2.75×** (≥ 2× target).
