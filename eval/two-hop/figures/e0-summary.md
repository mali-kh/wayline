# E0 Results Summary

Stats are taken from the warm window (runs 5+, when ≥5 reps exist).

## E2E mean / std / p95 by cell

| Coloc | Payload | System | n | mean (s) | std (s) | p95 (s) |
|---|---|---|---:|---:|---:|---:|
| same | 1MB | Wayline | 16 | 9.575 | 0.548 | 10.608 |
| same | 1MB | MinIO (baseline) | 16 | 5.372 | 0.018 | 5.385 |
| same | 10MB | Wayline | 16 | 9.619 | 0.448 | 10.249 |
| same | 10MB | MinIO (baseline) | 16 | 7.118 | 0.097 | 7.277 |
| same | 100MB | Wayline | 16 | 10.442 | 0.548 | 11.207 |
| same | 100MB | MinIO (baseline) | 16 | 24.349 | 0.562 | 24.382 |
| same | 500MB | Wayline | 16 | 17.237 | 0.918 | 18.326 |
| same | 500MB | MinIO (baseline) | 16 | 98.833 | 0.135 | 99.016 |
| cross | 1MB | Wayline | 16 | 9.613 | 0.459 | 10.401 |
| cross | 1MB | MinIO (baseline) | 16 | 5.373 | 0.016 | 5.398 |
| cross | 10MB | Wayline | 16 | 11.524 | 0.512 | 12.264 |
| cross | 10MB | MinIO (baseline) | 16 | 7.068 | 0.017 | 7.093 |
| cross | 100MB | Wayline | 16 | 28.096 | 0.549 | 28.980 |
| cross | 100MB | MinIO (baseline) | 16 | 24.206 | 0.119 | 24.352 |
| cross | 500MB | Wayline | 16 | 104.687 | 0.992 | 105.980 |
| cross | 500MB | MinIO (baseline) | 8 | 98.738 | 0.126 | 98.861 |

## DSF vs MinIO ratios (warm mean)

| Coloc | Payload | MinIO (s) | DSF (s) | Ratio (MinIO/DSF) |
|---|---|---:|---:|---:|
| same | 1MB | 5.372 | 9.575 | 0.56× |
| same | 10MB | 7.118 | 9.619 | 0.74× |
| same | 100MB | 24.349 | 10.442 | 2.33× |
| same | 500MB | 98.833 | 17.237 | 5.73× |
| cross | 1MB | 5.373 | 9.613 | 0.56× |
| cross | 10MB | 7.068 | 11.524 | 0.61× |
| cross | 100MB | 24.206 | 28.096 | 0.86× |
| cross | 500MB | 98.738 | 104.687 | 0.94× |

## Pass/fail

✅ **PASS** — minimum same-node ≥100MB ratio = **2.33×** (≥ 2× target).
