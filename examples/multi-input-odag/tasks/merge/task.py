#!/usr/bin/env python3
"""
multi-input-odag — merge task.

Reads all three upstream deps at once via recv_all():
  - source-a  (~30 MB, pushed from anrg-1)
  - transform (~60 MB, pushed from anrg-1)
  - source-b  (~30 MB, pushed from anrg-5)

Produces a ~250 MB output so that the cross-node transfer to
report-x (anrg-3 → anrg-7) takes ~2 s on a 1 Gbps link.
report-y is on the same node so it reads the file locally.
"""

import os
import time

from wl import WlTask

task = WlTask()

# --- helper properties smoke-test ---
print(f"[{task.name}] node             : {task.node}", flush=True)
print(f"[{task.name}] dependencies     : {task.dependencies}", flush=True)
print(f"[{task.name}] successors       : {task.successors}", flush=True)
print(f"[{task.name}] is_root          : {task.is_root}", flush=True)
print(f"[{task.name}] is_leaf          : {task.is_leaf}", flush=True)
print(f"[{task.name}] expected_runtime : {task.expected_runtime}s", flush=True)
print(f"[{task.name}] expected_data_size: {task.expected_data_size} bytes", flush=True)
for dep in task.dependencies:
    dn = task.dep_node(dep)
    locality = "same-node" if dn == task.node else "cross-node"
    print(f"[{task.name}] dep_node({dep}) -> {dn} ({locality})", flush=True)
# ------------------------------------

DATA_SIZE = int(os.environ.get("WL_DATA_SIZE", "250000000"))

print(f"[{task.name}] reading all inputs via recv_all()", flush=True)
t_recv = time.perf_counter()
inputs = task.recv_all()   # {"source-a": ..., "transform": ..., "source-b": ...}
print(f"[{task.name}] recv_all() completed in {time.perf_counter() - t_recv:.3f}s", flush=True)

src_a   = inputs["source-a"]
xformed = inputs["transform"]
src_b   = inputs["source-b"]

print(f"[{task.name}] source-a  : {src_a['count']} values  sum={src_a['sum']}", flush=True)
print(f"[{task.name}] transform : {xformed['count']} values  sum={xformed['sum']}  op={xformed['operation']}", flush=True)
print(f"[{task.name}] source-b  : {src_b['count']} values  sum={src_b['sum']}", flush=True)

print(f"[{task.name}] merging inputs", flush=True)

all_values = src_a["values"] + xformed["values"] + src_b["values"]
total  = sum(all_values)
count  = len(all_values)
result = {
    "source":       task.name,
    "inputs":       ["source-a", "transform", "source-b"],
    "input_counts": {
        "source-a":  src_a["count"],
        "transform": xformed["count"],
        "source-b":  src_b["count"],
    },
    "total_count": count,
    "sum":         round(total, 2),
    "mean":        round(total / count, 4),
    "min":         min(all_values),
    "max":         max(all_values),
    "values":      all_values,
    "padding":     "M" * DATA_SIZE,
}

print(f"[{task.name}] merged {count} values  sum={result['sum']}  mean={result['mean']}", flush=True)
print(f"[{task.name}] payload ~250 MB — sending (report-x=cross-node ~2s, report-y=same-node)", flush=True)

t0 = time.perf_counter()
task.send(result)
print(f"[{task.name}] send() completed in {time.perf_counter() - t0:.3f}s", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
