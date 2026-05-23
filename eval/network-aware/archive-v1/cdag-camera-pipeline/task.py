#!/usr/bin/env python3
"""
Camera Fusion Pipeline — evaluation CDAG for Experiment 1.

Topology:
    camera-1..4 → preprocess → detector → tracker → alert-sink + log-sink

Each camera generates ~5MB synthetic frames at 1Hz. The large frame size
ensures that cross-node transfers on bandwidth-constrained links (100Mbps)
take measurable time (~400ms), making placement decisions visible in the
latency metrics.

Role is determined by DSF_TASK_NAME environment variable.
"""

import os
import time
import random
import json
from dsf_sdk import DSFTask

task = DSFTask()
role = os.environ.get("DSF_TASK_NAME", "unknown")

FRAME_SIZE = 5_000_000  # 5MB per frame (high-res camera)
CAMERA_HZ = 1           # 1 frame per second


# ── camera-N: generate synthetic frames ─────────────────────────────────
def run_camera():
    """Publish ~500KB synthetic camera frames at 2Hz."""
    camera_id = role  # e.g. "camera-1"
    print(f"[{camera_id}] starting camera ({FRAME_SIZE} bytes at {CAMERA_HZ}Hz)", flush=True)

    frame_num = 0
    interval = 1.0 / CAMERA_HZ
    report_every = 20

    while True:
        frame_num += 1
        # Generate synthetic frame: random bytes with metadata header.
        frame_data = os.urandom(FRAME_SIZE)
        msg = {
            "camera": camera_id,
            "frame": frame_num,
            "ts": time.time(),
            "size": len(frame_data),
            "node": task.node,
        }
        # Publish raw frame + JSON metadata as combined payload.
        payload = json.dumps(msg).encode() + b"\n" + frame_data
        task.publish_raw(payload)

        if frame_num % report_every == 0:
            print(f"[{camera_id}] published {frame_num} frames", flush=True)

        time.sleep(interval)


# ── preprocess: fan-in from 4 cameras ───────────────────────────────────
def run_preprocess():
    """Subscribe to all cameras, 'resize' frames, publish downstream."""
    print(f"[{task.name}] starting preprocess (subscribe_all)", flush=True)

    processed = 0
    report_every = 50

    for camera, payload in task.subscribe_all_raw():
        processed += 1

        # Parse metadata from header line.
        header_end = payload.index(b"\n")
        meta = json.loads(payload[:header_end])

        # Simulate resize: output is 40% of input.
        resized_size = int(meta["size"] * 0.4)
        resized_data = os.urandom(resized_size)

        out_meta = {
            "camera": meta["camera"],
            "frame": meta["frame"],
            "ts_camera": meta["ts"],
            "ts_preprocess": time.time(),
            "size": resized_size,
            "node": task.node,
        }
        out_payload = json.dumps(out_meta).encode() + b"\n" + resized_data
        task.publish_raw(out_payload)

        if processed % report_every == 0:
            print(f"[{task.name}] preprocessed {processed} frames", flush=True)


# ── detector: object detection on preprocessed frames ───────────────────
def run_detector():
    """Subscribe to preprocess, simulate detection, publish results."""
    print(f"[{task.name}] starting detector (subscribe)", flush=True)

    detected = 0
    report_every = 50

    for payload in task.subscribe_raw("preprocess"):
        detected += 1

        header_end = payload.index(b"\n")
        meta = json.loads(payload[:header_end])

        # Simulate detection compute (~20ms).
        time.sleep(0.02)

        num_detections = random.randint(0, 5)
        out = {
            "camera": meta["camera"],
            "frame": meta["frame"],
            "ts_camera": meta["ts_camera"],
            "ts_preprocess": meta["ts_preprocess"],
            "ts_detect": time.time(),
            "detections": num_detections,
            "node": task.node,
        }
        task.publish(out)

        if detected % report_every == 0:
            print(f"[{task.name}] detected {detected} frames ({num_detections} objects in last)", flush=True)


# ── tracker: track objects across frames ────────────────────────────────
def run_tracker():
    """Subscribe to detector, simulate tracking, broadcast to both sinks."""
    print(f"[{task.name}] starting tracker (subscribe + broadcast)", flush=True)

    tracked = 0
    report_every = 50

    for det in task.subscribe("detector"):
        tracked += 1

        # Simulate tracking compute (~10ms).
        time.sleep(0.01)

        out = {
            "camera": det["camera"],
            "frame": det["frame"],
            "ts_camera": det["ts_camera"],
            "ts_preprocess": det["ts_preprocess"],
            "ts_detect": det["ts_detect"],
            "ts_track": time.time(),
            "tracks": det["detections"],
            "node": task.node,
        }
        # Broadcast to both alert-sink and log-sink.
        task.publish(out)

        if tracked % report_every == 0:
            print(f"[{task.name}] tracked {tracked} frames", flush=True)


# ── alert-sink: receives tracks, measures latency for anomalies ─────────
def run_alert_sink():
    """Callback-style sink for alert events. Logs latency stats."""
    print(f"[{task.name}] starting alert sink (@task.on callback)", flush=True)
    stats = {"count": 0, "total_latency": 0.0, "latencies": []}

    @task.on("tracker")
    def handle(track):
        now = time.time()
        e2e_latency = now - track["ts_camera"]
        stats["count"] += 1
        stats["total_latency"] += e2e_latency
        stats["latencies"].append(e2e_latency)

        if stats["count"] % 50 == 0:
            lats = stats["latencies"]
            lats.sort()
            p50 = lats[len(lats) // 2]
            p95 = lats[int(len(lats) * 0.95)]
            p99 = lats[int(len(lats) * 0.99)] if len(lats) >= 100 else lats[-1]
            avg = stats["total_latency"] / stats["count"]
            print(
                f"[{task.name}] LATENCY n={stats['count']} "
                f"avg={avg:.3f}s p50={p50:.3f}s p95={p95:.3f}s p99={p99:.3f}s",
                flush=True,
            )

    task.run()


# ── log-sink: receives all tracks, measures throughput ──────────────────
def run_log_sink():
    """Iterator-style sink for all events. Logs throughput stats."""
    print(f"[{task.name}] starting log sink (subscribe iterator)", flush=True)

    received = 0
    window_start = time.time()
    window_count = 0
    latencies = []
    report_every = 50

    for track in task.subscribe("tracker"):
        now = time.time()
        received += 1
        window_count += 1
        e2e_latency = now - track["ts_camera"]
        latencies.append(e2e_latency)

        if received % report_every == 0:
            elapsed = now - window_start
            rate = window_count / elapsed if elapsed > 0 else 0

            lats = sorted(latencies)
            p50 = lats[len(lats) // 2]
            p95 = lats[int(len(lats) * 0.95)]
            avg = sum(latencies) / len(latencies)

            print(
                f"[{task.name}] THROUGHPUT n={received} rate={rate:.1f}msg/s "
                f"LATENCY avg={avg:.3f}s p50={p50:.3f}s p95={p95:.3f}s",
                flush=True,
            )
            window_start = now
            window_count = 0


# ── dispatch ────────────────────────────────────────────────────────────
ROLES = {
    "camera-1": run_camera,
    "camera-2": run_camera,
    "camera-3": run_camera,
    "camera-4": run_camera,
    "preprocess": run_preprocess,
    "detector": run_detector,
    "tracker": run_tracker,
    "alert-sink": run_alert_sink,
    "log-sink": run_log_sink,
}

if role not in ROLES:
    print(f"[{role}] unknown role, expected one of: {list(ROLES.keys())}", flush=True)
    exit(1)

ROLES[role]()
