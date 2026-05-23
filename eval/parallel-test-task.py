#!/usr/bin/env python3
"""Simple task for parallel scheduling test. Generates or consumes raw data."""
import os, time
from dsf_sdk import DSFTask

task = DSFTask()
size = int(os.environ.get("DSF_DATA_SIZE", "10000000"))

if task.is_root:
    time.sleep(task.expected_runtime or 3)
    task.send_raw(os.urandom(size))
    print(f"[{task.name}] sent {size} bytes", flush=True)
else:
    data = task.recv_all_raw()
    total = sum(len(v) for v in data.values())
    print(f"[{task.name}] received {total} bytes from {list(data.keys())}", flush=True)
    task.send_raw(b"done")

task.close()
