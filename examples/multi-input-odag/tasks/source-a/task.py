#!/usr/bin/env python3
"""
multi-input-odag — source-a task.

Generates a dataset of 50 random floats plus a ~30 MB padding field so
cross-node transfers are non-trivial on a 1 Gbps link (~0.24 s).
"""

import os
import random
import time

from wl import WlTask

task = WlTask()

DATA_SIZE = int(os.environ.get("WL_DATA_SIZE", "30000000"))

print(f"[{task.name}] generating dataset A (50 values + {DATA_SIZE} B padding)", flush=True)

values = [round(random.uniform(1, 50), 2) for _ in range(50)]
dataset = {
    "source":  task.name,
    "values":  values,
    "count":   len(values),
    "sum":     round(sum(values), 2),
    "padding": "A" * DATA_SIZE,
}

print(f"[{task.name}] generated {dataset['count']} values  sum={dataset['sum']}  sample={values[:4]}", flush=True)
print(f"[{task.name}] payload ~30 MB — sending to successors (transform=same-node, merge=cross-node)", flush=True)

t0 = time.perf_counter()
task.send(dataset)
print(f"[{task.name}] send() completed in {time.perf_counter() - t0:.3f}s", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
