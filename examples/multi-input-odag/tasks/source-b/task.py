#!/usr/bin/env python3
"""
multi-input-odag — source-b task.

Generates a dataset of 30 random floats plus a ~30 MB padding field.
Runs in parallel with source-a. Cross-node to merge (anrg-5 → anrg-3).
"""

import os
import random
import time

from wl import WlTask

task = WlTask()

DATA_SIZE = int(os.environ.get("WL_DATA_SIZE", "30000000"))

print(f"[{task.name}] generating dataset B (30 values + {DATA_SIZE} B padding)", flush=True)

values = [round(random.uniform(100, 200), 2) for _ in range(30)]
dataset = {
    "source":  task.name,
    "values":  values,
    "count":   len(values),
    "sum":     round(sum(values), 2),
    "padding": "B" * DATA_SIZE,
}

print(f"[{task.name}] generated {dataset['count']} values  sum={dataset['sum']}  sample={values[:4]}", flush=True)
print(f"[{task.name}] payload ~30 MB — sending to merge (cross-node anrg-5 → anrg-3)", flush=True)

t0 = time.perf_counter()
task.send(dataset)
print(f"[{task.name}] send() completed in {time.perf_counter() - t0:.3f}s", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
