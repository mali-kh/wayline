# 20-rep Re-run Campaign — ON WAYLINE (wl-system) — STATUS
System under test: WAYLINE release (wl.io, wl-system, port 8082, wl SDK, wl-vemcmt images).
Validated: full MCMT pipeline ran end-to-end on Wayline (18/18 tasks, Succeeded).
Order=priority; each chunk: governor + verified tc + idle preflight -> 20 reps -> snapshot -> clean.

| # | experiment | reps | tc | state |
|---|---|---|---|---|
| 1 | AI City MCMT fair 2x2 (hero) | 20 | both | RUNNING |
| 2..13 | E0, network-aware, baselines, Ray, ... | 20 | - | PENDING (port to wl in progress) |

## Event log
2026-05-23 18:05:09 | exp1 notc d30-jpg START
2026-05-23 19:13:32 | exp1 notc d30-jpg DONE succeeded=40/40
2026-05-23 19:15:21 | exp1 notc d30-jpg START
2026-05-23 20:23:17 | exp1 notc d30-jpg DONE succeeded=40/40
2026-05-23 20:23:38 | exp1 notc d60-jpg START
2026-05-23 21:45:43 | exp1 notc d60-jpg DONE succeeded=40/40
2026-05-23 21:45:56 | exp1 notc d120-jpg START
2026-05-23 23:08:02 | exp1 notc d120-jpg DONE succeeded=40/40
2026-05-23 23:20:59 | exp1 notc d120-png START
2026-05-23 23:21:19 | exp1 notc d120-png START
2026-05-24 00:51:12 | exp1 notc d120-png DONE succeeded=40/40
2026-05-24 00:52:00 | exp1 tc d30-jpg START
2026-05-24 02:07:54 | exp1 tc d30-jpg DONE succeeded=40/40
2026-05-24 02:08:45 | exp1 tc d60-jpg START
2026-05-24 03:43:09 | exp1 tc d60-jpg DONE succeeded=40/40
2026-05-24 03:43:46 | exp1 tc d120-jpg START
2026-05-24 05:18:21 | exp1 tc d120-jpg DONE succeeded=40/40
2026-05-24 05:18:33 | exp1 tc d120-png START
2026-05-24 07:13:46 | exp1 tc d120-png DONE succeeded=40/40
2026-05-24 07:14:45 | exp2 e0 wayline START
2026-05-24 07:15:41 | exp2 e0 wayline PARTIAL 0/8
2026-05-24 07:15:41 | exp2 e0 minio START
2026-05-24 07:16:36 | exp2 e0 minio PARTIAL 0/8
2026-05-24 07:16:37 | exp2 e0 nfs START
2026-05-24 07:25:51 | exp2 e0 wayline START
2026-05-24 08:29:03 | exp2 e0 wayline START
2026-05-24 09:06:42 | exp2 e0 wayline DONE (8/8)
2026-05-24 09:06:43 | exp2 e0 minio START
2026-05-24 10:57:43 | exp2 e0 minio DONE (8/8)
2026-05-24 10:58:18 | exp2 e0 nfs START
2026-05-24 12:23:50 | exp2 e0 nfs DONE (8/8)
2026-05-24 12:24:05 | exp3.ablation START
2026-05-24 15:02:41 | exp3.ablation DONE rows=60
2026-05-24 20:46:39 | exp4.dist START
2026-05-25 00:39:01 | exp4.dist DONE
2026-05-25 00:46:14 | exp5.nfs START
2026-05-25 02:00:50 | exp5.nfs DONE rows=20
2026-05-25 02:10:13 | exp6.na.iobt START
2026-05-25 03:00:41 | exp6.na.iobt DONE
2026-05-25 03:00:42 | exp6.na.hetero-compute START
2026-05-25 03:57:30 | exp6.na.hetero-compute DONE
2026-05-25 04:03:54 | exp6.na.wide-pipeline-flex START
2026-05-25 04:51:14 | exp6.na.wide-pipeline-flex DONE
2026-05-25 04:51:15 | exp9.e1 START
2026-05-25 08:09:45 | exp9.e1 DONE
2026-05-25 08:17:18 | exp10.e2 START
2026-05-25 10:56:03 | exp10.e2 DONE
2026-05-25 11:01:14 | exp11.ray START
2026-05-25 11:33:37 | exp11.ray DONE rows=161
2026-05-25 11:33:38 | exp12.stress START
2026-05-25 11:34:30 | exp12.stress PARTIAL
2026-05-25 12:46:35 | exp12.stress START
2026-05-25 12:52:39 | exp12.stress DONE
