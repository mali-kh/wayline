#!/usr/bin/env python3
"""
Generate CDAGTemplate YAML files for scalability evaluation.

Topology:  source → worker-1..N → sink

Constraints give each task 2-3 node choices so random scheduler creates
a natural mix of same-node and cross-node communication across runs.

Usage: python3 eval/scalability/gen-templates.py
"""

import os
import random
import yaml

NAMESPACE = "dsf-system"
IMAGE = "192.168.1.163:5000/scalability-eval:latest"
SOURCE_NODE = "anrg-3"
WORKER_CANDIDATE_POOL = ["anrg-3", "anrg-4", "anrg-5", "anrg-6"]
SINK_CANDIDATES = ["anrg-4", "anrg-5"]
WORKER_COUNTS = [2, 4, 6, 8]
MSG_SIZES = [102400]  # 100KB
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "templates")

random.seed(42)


def pick_worker_constraints(worker_idx: int) -> list:
    n = random.choice([2, 3])
    return sorted(random.sample(WORKER_CANDIDATE_POOL, n))


def gen_template(n_workers: int, transport: str, msg_size: int) -> dict:
    name = f"scale-{transport}-w{n_workers}"
    if msg_size != 102400:
        name += f"-{msg_size // 1024}kb"

    transport_pattern = "pubsub" if transport == "zmq" else "mqtt"

    tasks = []

    # Source — pinned to anrg-3.
    tasks.append({
        "name": "source",
        "image": IMAGE,
        "command": ["python", "task.py"],
        "replicas": 1,
        "dependencies": [],
        "dataRate": f"{msg_size * 5}B/s",
        "env": [
            {"name": "DSF_EVAL_MSG_SIZE", "value": str(msg_size)},
            {"name": "DSF_EVAL_MSG_RATE", "value": "5"},
            {"name": "DSF_TRANSPORT_PATTERN", "value": transport_pattern},
        ],
        "resources": {"cpu": "200m", "memory": "128Mi"},
        "constraints": {"nodeNames": [SOURCE_NODE]},
    })

    # Workers — 2-3 node choices each.
    worker_deps = []
    for i in range(1, n_workers + 1):
        worker_name = f"worker-{i}"
        worker_deps.append(worker_name)
        candidates = pick_worker_constraints(i)
        tasks.append({
            "name": worker_name,
            "image": IMAGE,
            "command": ["python", "task.py"],
            "replicas": 1,
            "dependencies": ["source"],
            "dataRate": f"{msg_size * 5}B/s",
            "env": [
                {"name": "DSF_EVAL_MSG_SIZE", "value": str(msg_size)},
                {"name": "DSF_TRANSPORT_PATTERN", "value": transport_pattern},
            ],
            "resources": {"cpu": "200m", "memory": "128Mi"},
            "constraints": {"nodeNames": candidates},
        })

    # Sink — 2 choices, never just anrg-3.
    tasks.append({
        "name": "sink",
        "image": IMAGE,
        "command": ["python", "task.py"],
        "replicas": 1,
        "dependencies": worker_deps,
        "env": [
            {"name": "DSF_TRANSPORT_PATTERN", "value": transport_pattern},
        ],
        "resources": {"cpu": "300m", "memory": "256Mi"},
        "constraints": {"nodeNames": SINK_CANDIDATES},
    })

    return {
        "apiVersion": "dsf.io/v1",
        "kind": "CDAGTemplate",
        "metadata": {"name": name, "namespace": NAMESPACE},
        "spec": {
            "description": f"Scalability eval: {transport.upper()}, {n_workers} workers, {msg_size // 1024}KB, 2-3 node choices",
            "scheduler": "random",
            "restartPolicy": "Always",
            "retention": {"maxInstances": 5},
            "tasks": tasks,
        },
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for transport in ["zmq", "mqtt"]:
        for n_workers in WORKER_COUNTS:
            for msg_size in MSG_SIZES:
                tmpl = gen_template(n_workers, transport, msg_size)
                name = tmpl["metadata"]["name"]
                path = os.path.join(OUTPUT_DIR, f"{name}.yml")

                with open(path, "w") as f:
                    yaml.dump(tmpl, f, default_flow_style=False, sort_keys=False)

                print(f"  {name}:")
                print(f"    source: [{SOURCE_NODE}]")
                for t in tmpl["spec"]["tasks"][1:-1]:
                    print(f"    {t['name']}: {t['constraints']['nodeNames']}")
                print(f"    sink: {SINK_CANDIDATES}")

    print(f"\n  Total: {len(WORKER_COUNTS) * 2 * len(MSG_SIZES)} templates")
    print(f"  Apply: kubectl apply -f {OUTPUT_DIR}/")


if __name__ == "__main__":
    print("=== Generating CDAG scalability templates ===")
    main()
