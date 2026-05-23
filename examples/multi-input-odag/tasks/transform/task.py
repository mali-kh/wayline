#!/usr/bin/env python3
"""
multi-input-odag — transform task.

Reads source-a (same-node, local file). Squares each value.
Outputs ~60 MB payload for cross-node transfer to merge (anrg-1 → anrg-3).
"""

import os
import time

from wl import WlTask

task = WlTask()

DATA_SIZE = int(os.environ.get("WL_DATA_SIZE", "60000000"))

print(f"[{task.name}] reading source-a output (same-node)", flush=True)
t_recv = time.perf_counter()
upstream = task.recv("source-a")
print(f"[{task.name}] recv() completed in {time.perf_counter() - t_recv:.3f}s", flush=True)

print(f"[{task.name}] received {upstream['count']} values from {upstream['source']}", flush=True)
print(f"[{task.name}] squaring values", flush=True)

squared = [round(v ** 2, 2) for v in upstream["values"]]
result = {
    "source":    task.name,
    "upstream":  upstream["source"],
    "values":    squared,
    "count":     len(squared),
    "sum":       round(sum(squared), 2),
    "operation": "square",
    "padding":   "T" * DATA_SIZE,
}

print(f"[{task.name}] transformed {result['count']} values  sum={result['sum']}  sample={squared[:4]}", flush=True)
print(f"[{task.name}] payload ~60 MB — sending to merge (cross-node anrg-1 → anrg-3)", flush=True)

t0 = time.perf_counter()
task.send(result)
print(f"[{task.name}] send() completed in {time.perf_counter() - t0:.3f}s", flush=True)

print(f"[{task.name}] done", flush=True)
task.close()
