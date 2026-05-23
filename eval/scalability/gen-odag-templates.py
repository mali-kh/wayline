#!/usr/bin/env python3
"""
Generate ODAGTemplate YAML files for scalability evaluation.

Topology:  source → worker-1..N → sink

Constraints give each task 2-3 node choices (NOT all, NOT pinned to one).
Random scheduler picks from the candidates, creating a natural mix of
same-node (local) and cross-node (network) transfers across runs.

Source is pinned to anrg-3 (fixed reference point).
Workers get 2-3 random nodes from [anrg-4, anrg-5, anrg-6] — guarantees
at least some cross-node transfers since source is on anrg-3.
Sink gets [anrg-4, anrg-5] — always cross-node from source.

Usage: python3 eval/scalability/gen-odag-templates.py
"""

import os
import random
import yaml

NAMESPACE = "dsf-system"
IMAGE = "192.168.1.163:5000/scalability-eval:latest"
NODES = ["anrg-3", "anrg-4", "anrg-5", "anrg-6"]
SOURCE_NODE = "anrg-3"
WORKER_CANDIDATE_POOL = ["anrg-3", "anrg-4", "anrg-5", "anrg-6"]
SINK_CANDIDATES = ["anrg-4", "anrg-5"]
WORKER_COUNTS = [2, 4, 6, 8]
DATA_SIZE = 50_000_000  # 50MB
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "odag-templates")

random.seed(42)  # reproducible constraints


def pick_worker_constraints(worker_idx: int) -> list:
    """Pick 2-3 random nodes for a worker from the pool."""
    n = random.choice([2, 3])
    return sorted(random.sample(WORKER_CANDIDATE_POOL, n))


def gen_template(n_workers: int) -> dict:
    name = f"scale-odag-p2p-w{n_workers}"

    tasks = []

    # Source — pinned to anrg-3.
    tasks.append({
        "name": "source",
        "image": IMAGE,
        "command": ["python", "odag-task.py"],
        "dependencies": [],
        "dataSize": f"{DATA_SIZE}",
        "runtime": 2,
        "env": [{"name": "DSF_EVAL_DATA_SIZE", "value": str(DATA_SIZE)}],
        "resources": {"cpu": "300m", "memory": "256Mi"},
        "constraints": {"nodeNames": [SOURCE_NODE]},
    })

    # Workers — each gets 2-3 node choices.
    worker_names = []
    for i in range(1, n_workers + 1):
        wname = f"worker-{i}"
        worker_names.append(wname)
        candidates = pick_worker_constraints(i)
        tasks.append({
            "name": wname,
            "image": IMAGE,
            "command": ["python", "odag-task.py"],
            "dependencies": ["source"],
            "dataSize": f"{DATA_SIZE}",
            "runtime": 2,
            "env": [{"name": "DSF_EVAL_DATA_SIZE", "value": str(DATA_SIZE)}],
            "resources": {"cpu": "300m", "memory": "256Mi"},
            "constraints": {"nodeNames": candidates},
        })

    # Sink — 2 candidates, never just anrg-3.
    tasks.append({
        "name": "sink",
        "image": IMAGE,
        "command": ["python", "odag-task.py"],
        "dependencies": worker_names,
        "dataSize": "0",
        "runtime": 1,
        "resources": {"cpu": "300m", "memory": "512Mi"},
        "constraints": {"nodeNames": SINK_CANDIDATES},
    })

    return {
        "apiVersion": "dsf.io/v1",
        "kind": "ODAGTemplate",
        "metadata": {"name": name, "namespace": NAMESPACE},
        "spec": {
            "description": f"Scalability eval: {n_workers} workers, {DATA_SIZE // 1_000_000}MB, 2-3 node choices per worker",
            "scheduler": "random",
            "profiling": {"enabled": False},
            "defaults": {"runtime": 2, "dataSize": f"{DATA_SIZE}"},
            "retention": {"maxRuns": 15},
            "tasks": tasks,
        },
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for n_workers in WORKER_COUNTS:
        tmpl = gen_template(n_workers)
        name = tmpl["metadata"]["name"]
        path = os.path.join(OUTPUT_DIR, f"{name}.yml")

        with open(path, "w") as f:
            yaml.dump(tmpl, f, default_flow_style=False, sort_keys=False)

        print(f"  {name}:")
        print(f"    source: [{SOURCE_NODE}]")
        for t in tmpl["spec"]["tasks"][1:-1]:
            print(f"    {t['name']}: {t['constraints']['nodeNames']}")
        print(f"    sink: {SINK_CANDIDATES}")

    print(f"\n  Total: {len(WORKER_COUNTS)} templates")
    print(f"  Apply: kubectl apply -f {OUTPUT_DIR}/")


if __name__ == "__main__":
    print("=== Generating ODAG scalability templates ===")
    main()
