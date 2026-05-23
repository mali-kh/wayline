#!/usr/bin/env python3
"""
DAG pipeline — generate task.

Simulates 10 seconds of computation, then writes a dataset to the
output file via the Wayline file transport. The odag-controller launches
transform only after this pod succeeds.
"""

import time
import random
from wl import WlTask

task = WlTask()

print(f"[{task.name}] starting — simulating 10s of work", flush=True)
time.sleep(10)

# Generate a dataset: list of 100 random numbers.
dataset = {
    "source": task.name,
    "timestamp": time.time(),
    "values": [round(random.uniform(0, 100), 4) for _ in range(100)],
    "count": 100,
}

print(f"[{task.name}] generated dataset with {dataset['count']} values", flush=True)
print(f"[{task.name}] sample: {dataset['values'][:5]}", flush=True)

print(f"[{task.name}] sending dataset downstream", flush=True)
task.send(dataset)

print(f"[{task.name}] done", flush=True)
task.close()
