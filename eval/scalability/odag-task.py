#!/usr/bin/env python3
"""
ODAG Scalability evaluation task — P2P (data-agent) vs NFS (shared volume).

Topology:  source → worker-1..N → sink

- source: generates a large payload and sends it to all workers
- worker-N: receives from source, minimal compute, sends to sink
- sink: fans in from all workers, logs total elapsed time

Data size configurable via DSF_EVAL_DATA_SIZE (default 50MB).
Works with both file transport (P2P) and shared_volume transport (NFS).
"""

import os
import time
import json
from dsf_sdk import DSFTask

task = DSFTask()
role = os.environ.get("DSF_TASK_NAME", "unknown")

DATA_SIZE = int(os.environ.get("DSF_EVAL_DATA_SIZE", str(50_000_000)))  # 50MB default


def run_source():
    """Generate a large payload and send to all workers."""
    print(f"[{task.name}] source: generating {DATA_SIZE} bytes, node={task.node}", flush=True)

    t0 = time.perf_counter()
    payload = os.urandom(DATA_SIZE)
    t_gen = time.perf_counter() - t0

    t1 = time.perf_counter()
    task.send_raw(payload)
    t_send = time.perf_counter() - t1

    print(f"[{task.name}] generated in {t_gen:.3f}s, send_raw in {t_send:.3f}s", flush=True)
    print(f"[{task.name}] done", flush=True)
    task.close()


def run_worker():
    """Receive from source, minimal compute, send to sink."""
    print(f"[{task.name}] worker: node={task.node}", flush=True)

    t0 = time.perf_counter()
    data = task.recv_raw()
    t_recv = time.perf_counter() - t0

    # Minimal compute — just pass through with a small sleep.
    time.sleep(0.1)

    # Generate output of same size.
    t1 = time.perf_counter()
    output = os.urandom(DATA_SIZE)
    t_gen = time.perf_counter() - t1

    t2 = time.perf_counter()
    task.send_raw(output)
    t_send = time.perf_counter() - t2

    print(
        f"[{task.name}] recv={t_recv:.3f}s gen={t_gen:.3f}s send={t_send:.3f}s "
        f"({len(data)} bytes in, {len(output)} bytes out)",
        flush=True,
    )
    print(f"[{task.name}] done", flush=True)
    task.close()


def run_sink():
    """Fan-in from all workers. Log total time."""
    print(f"[{task.name}] sink: node={task.node}, deps={task.dependencies}", flush=True)

    t0 = time.perf_counter()
    inputs = task.recv_all_raw()
    t_recv = time.perf_counter() - t0

    total_bytes = sum(len(v) for v in inputs.values())

    print(
        f"[{task.name}] RESULT recv_all={t_recv:.3f}s "
        f"total_bytes={total_bytes} workers={len(inputs)}",
        flush=True,
    )
    # Send empty result (leaf task).
    task.send({"total_bytes": total_bytes, "recv_time": t_recv, "workers": len(inputs)})
    print(f"[{task.name}] done", flush=True)
    task.close()


# ── Dispatch ────────────────────────────────────────────────────────────
if role == "source":
    run_source()
elif role == "sink":
    run_sink()
elif role.startswith("worker-"):
    run_worker()
else:
    print(f"[{role}] unknown role", flush=True)
    exit(1)
