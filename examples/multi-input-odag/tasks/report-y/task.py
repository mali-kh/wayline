#!/usr/bin/env python3
"""
multi-input-odag — report-y task.

Reads merge output (same-node, both anrg-3 — local file, no network).
Prints percentile statistics.  Terminal node.
"""

import time

from wl import WlTask

task = WlTask()

print(f"[{task.name}] reading merge output (same-node on anrg-3, ~250 MB local file)", flush=True)
t_recv = time.perf_counter()
data = task.recv("merge")
print(f"[{task.name}] recv() completed in {time.perf_counter() - t_recv:.3f}s  (local — no network)", flush=True)

values = sorted(data["values"])
n      = len(values)

def pct(s, p):
    return s[min(int(n * p / 100), n - 1)]

print(f"[{task.name}] ===== REPORT Y — percentiles (same-node transfer) =====", flush=True)
print(f"[{task.name}] inputs merged  : {data['inputs']}", flush=True)
print(f"[{task.name}] input counts   : {data['input_counts']}", flush=True)
print(f"[{task.name}] total values   : {data['total_count']}", flush=True)
print(f"[{task.name}] sum / mean     : {data['sum']} / {data['mean']}", flush=True)
print(f"[{task.name}] min / max      : {data['min']} / {data['max']}", flush=True)
print(f"[{task.name}] p10            : {pct(values, 10)}", flush=True)
print(f"[{task.name}] p25            : {pct(values, 25)}", flush=True)
print(f"[{task.name}] p50 (median)   : {pct(values, 50)}", flush=True)
print(f"[{task.name}] p75            : {pct(values, 75)}", flush=True)
print(f"[{task.name}] p90            : {pct(values, 90)}", flush=True)
print(f"[{task.name}] top-5          : {sorted(data['values'])[-5:][::-1]}", flush=True)
print(f"[{task.name}] =======================================================", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
