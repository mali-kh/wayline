#!/usr/bin/env python3
"""
multi-input-odag — report-x task.

Reads merge output (cross-node, anrg-3 → anrg-7, ~250 MB).
Prints a histogram report.  Terminal node.
"""

import time

from wl import WlTask

task = WlTask()

print(f"[{task.name}] reading merge output (cross-node from anrg-3, ~250 MB)", flush=True)
t_recv = time.perf_counter()
data = task.recv("merge")
print(f"[{task.name}] recv() completed in {time.perf_counter() - t_recv:.3f}s", flush=True)

values = data["values"]
mn     = data["min"]
mx     = data["max"]

width   = (mx - mn) / 5
buckets = [0] * 5
labels  = []
for i in range(5):
    lo = round(mn + i * width, 1)
    hi = round(mn + (i + 1) * width, 1)
    labels.append(f"[{lo}, {hi})")
for v in values:
    i = min(int((v - mn) / width), 4)
    buckets[i] += 1

print(f"[{task.name}] ===== REPORT X — histogram (cross-node transfer) =====", flush=True)
print(f"[{task.name}] inputs merged  : {data['inputs']}", flush=True)
print(f"[{task.name}] input counts   : {data['input_counts']}", flush=True)
print(f"[{task.name}] total values   : {data['total_count']}", flush=True)
print(f"[{task.name}] sum / mean     : {data['sum']} / {data['mean']}", flush=True)
print(f"[{task.name}] min / max      : {data['min']} / {data['max']}", flush=True)
print(f"[{task.name}] histogram (5 buckets):", flush=True)
for label, count in zip(labels, buckets):
    bar = "█" * (count // 2)
    print(f"[{task.name}]   {label:20s}  {count:3d}  {bar}", flush=True)
print(f"[{task.name}] ======================================================", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
