#!/usr/bin/env python3
"""
Scalability evaluation task — P2P (ZMQ/data-agent) vs Centralized (MQTT).

Topology (parameterized by N):
    source → worker-1..N → sink

- source: generates payloads of configurable size at a fixed rate
- worker-N: receives from source, simulates compute, forwards to sink
- sink: fans in from all workers, measures throughput and latency

For CDAG (streaming): continuous flow, measures steady-state throughput + latency
For ODAG (batch): single burst of data, measures total makespan

Role determined by DSF_TASK_NAME. Data size controlled by DSF_EVAL_MSG_SIZE (bytes).
"""

import os
import time
import json
from dsf_sdk import DSFTask

task = DSFTask()
role = os.environ.get("DSF_TASK_NAME", "unknown")

# Eval parameters from environment.
MSG_SIZE = int(os.environ.get("DSF_EVAL_MSG_SIZE", "102400"))  # default 100KB
MSG_RATE = float(os.environ.get("DSF_EVAL_MSG_RATE", "5"))     # messages/sec (CDAG only)
REPORT_EVERY = int(os.environ.get("DSF_EVAL_REPORT", "50"))


def run_source():
    """Generate messages and broadcast to all workers."""
    print(f"[{task.name}] source: msg_size={MSG_SIZE} rate={MSG_RATE}/s successors={task.successors}", flush=True)
    counter = 0
    interval = 1.0 / MSG_RATE

    while True:
        counter += 1
        payload_data = os.urandom(MSG_SIZE)
        header = json.dumps({
            "id": counter,
            "ts": time.time(),
            "size": MSG_SIZE,
            "source_node": task.node,
        }).encode()
        task.publish_raw(header + b"\n" + payload_data)

        if counter % REPORT_EVERY == 0:
            print(f"[{task.name}] published {counter} messages ({MSG_SIZE}B each)", flush=True)

        time.sleep(interval)


def run_worker():
    """Receive from source, simulate processing, forward to sink."""
    print(f"[{task.name}] worker: subscribing to source, forwarding to sink", flush=True)
    processed = 0

    for raw in task.subscribe_raw("source"):
        processed += 1
        # Parse header to preserve timestamps.
        header_end = raw.index(b"\n")
        meta = json.loads(raw[:header_end])
        data = raw[header_end + 1:]

        # Simulate compute (5ms).
        time.sleep(0.005)

        # Forward with worker metadata added.
        out_meta = {
            "id": meta["id"],
            "ts_source": meta["ts"],
            "ts_worker": time.time(),
            "worker": task.name,
            "worker_node": task.node,
            "size": len(data),
        }
        task.publish_raw(json.dumps(out_meta).encode() + b"\n" + data)

        if processed % REPORT_EVERY == 0:
            print(f"[{task.name}] forwarded {processed} messages", flush=True)


def run_sink():
    """Fan-in from all workers. Measure throughput and end-to-end latency."""
    print(f"[{task.name}] sink: subscribing to all workers (fan-in)", flush=True)

    received = 0
    latencies = []
    window_start = time.time()
    window_count = 0

    for peer, raw in task.subscribe_all_raw():
        now = time.time()
        received += 1
        window_count += 1

        header_end = raw.index(b"\n")
        meta = json.loads(raw[:header_end])
        e2e = now - meta["ts_source"]
        latencies.append(e2e)

        if received % REPORT_EVERY == 0:
            elapsed = now - window_start
            rate = window_count / elapsed if elapsed > 0 else 0

            lats = sorted(latencies[-500:])  # last 500 for percentiles
            p50 = lats[len(lats) // 2]
            p95 = lats[int(len(lats) * 0.95)]
            p99 = lats[int(len(lats) * 0.99)] if len(lats) >= 100 else lats[-1]
            avg = sum(lats) / len(lats)

            print(
                f"[{task.name}] STATS n={received} rate={rate:.1f}msg/s "
                f"lat_avg={avg:.4f}s p50={p50:.4f}s p95={p95:.4f}s p99={p99:.4f}s",
                flush=True,
            )
            window_start = now
            window_count = 0


# ── Dispatch ────────────────────────────────────────────────────────────
if role == "source":
    run_source()
elif role == "sink":
    run_sink()
elif role.startswith("worker-"):
    run_worker()
else:
    print(f"[{role}] unknown role (expected source, worker-N, or sink)", flush=True)
    exit(1)
