#!/usr/bin/env python3
"""
DAG pipeline — output task.

Reads the transformed dataset written by 'transform' (via file transport),
prints a summary, and exits. This is the terminal node of the pipeline.
"""

import time
from wl import WlTask

task = WlTask()

print(f"[{task.name}] waiting for data from 'transform'", flush=True)
result = task.recv("transform")

print(f"[{task.name}] ===== PIPELINE RESULT =====", flush=True)
print(f"[{task.name}] source chain : {result['original_source']} -> {result['source']} -> {task.name}", flush=True)
print(f"[{task.name}] operation    : {result['operation']}", flush=True)
print(f"[{task.name}] count        : {result['count']}", flush=True)
print(f"[{task.name}] sample (first 10):", flush=True)
for i, v in enumerate(result["values"][:10]):
    print(f"[{task.name}]   [{i}] = {v}", flush=True)

total = sum(result["values"])
avg = total / result["count"] if result["count"] > 0 else 0
print(f"[{task.name}] total        : {total:.2f}", flush=True)
print(f"[{task.name}] average      : {avg:.4f}", flush=True)
print(f"[{task.name}] ===========================", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
