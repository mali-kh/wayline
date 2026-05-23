# Real-workload correctness validation

Per-cell DSF↔Argo report equivalence across all reps.
Equivalence rule: identical `n_global_tracks`, `counts_by_class`, and per-track `class`/`cameras`/`hop_count`.

| cell | reps | OK | FAIL | NO_REPORT | n_tracks (mean) | classes |
|------|------|----|------|-----------|-----------------|---------|
| n4-d120-jpg | 20 | 17 | 0 | 3 | 32.0 | bus,car,motorcycle,truck |
| n4-d120-png | 20 | 19 | 0 | 1 | 30.0 | car,motorcycle,truck |
| n4-d30-jpg | 20 | 20 | 0 | 0 | 30.0 | bus,car,motorcycle,truck |
| n4-d60-jpg | 20 | 19 | 0 | 1 | 32.0 | bus,car,motorcycle,truck |

## Missing reports

- n4-d120-jpg rep 13
- n4-d120-jpg rep 14
- n4-d120-jpg rep 3
- n4-d120-png rep 1
- n4-d60-jpg rep 15

