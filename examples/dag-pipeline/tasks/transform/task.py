#!/usr/bin/env python3
"""
DAG pipeline — transform task.

Reads the dataset written by 'generate' (via file transport), doubles
every value to simulate 10 seconds of work, then writes the result for
'output' to consume.
"""

import time
from wl import WlTask

task = WlTask()

print(f"[{task.name}] waiting for data from 'generate'", flush=True)
dataset = task.recv("generate")
print(f"[{task.name}] received {dataset['count']} values from '{dataset['source']}'", flush=True)

print(f"[{task.name}] transforming — simulating 10s of work", flush=True)
time.sleep(10)

transformed = {
    "source": task.name,
    "original_source": dataset["source"],
    "timestamp": time.time(),
    "values": [round(v * 2, 4) for v in dataset["values"]],
    "count": dataset["count"],
    "operation": "multiply_by_2",
}

print(f"[{task.name}] transformed {transformed['count']} values", flush=True)
print(f"[{task.name}] sample: {transformed['values'][:5]}", flush=True)

print(f"[{task.name}] sending result downstream", flush=True)
task.send(transformed)

print(f"[{task.name}] done", flush=True)
task.close()
