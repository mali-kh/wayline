#!/usr/bin/env python3
"""
Ray-native E0 microbenchmark: producer-consumer object handoff.

Run inside the ray-head pod (where Ray is already initialized via
the cluster's GCS). Sweeps payload size and producer/consumer
co-location and prints CSV rows.

  python3 microbench.py --reps 5

Each rep does:
  producer task: sleep ~5s of synthetic compute, then return a
    payload of P bytes via Ray's object store.
  consumer task: take the producer's ObjectRef and ray.get() it
    on the consumer's node — Ray fetches locally if same-node,
    over the network if cross-node.

We measure four timestamps per rep:
  t0: just before producer task is launched
  t1: producer task done (the ObjectRef is ready)
  t2: just before consumer task is launched
  t3: consumer task done (payload fully materialized)

Output CSV columns:
  rep, coloc, payload_bytes, t0, t1_t0, t2_t1, t3_t2, e2e
"""
import argparse
import csv
import sys
import time
import ray


@ray.remote(num_cpus=1)
def producer(size: int) -> bytes:
    # Mirror Wayline E0 producer: 5s of synthetic compute then payload.
    deadline = time.time() + 5.0
    x = 0
    while time.time() < deadline:
        x += 1
    # Return the payload — Ray stores it in the local object store.
    # Use bytes() so it's not all-zeros (Ray may special-case).
    pat = bytes([(i & 0xff) for i in range(min(size, 256))])
    return (pat * (size // 256 + 1))[:size]


@ray.remote(num_cpus=1)
def consumer(payload: bytes) -> int:
    # Touch every byte so the network/local fetch actually completes.
    n = len(payload)
    s = 0
    for i in range(0, n, 4096):
        s += payload[i]
    return n


def run_one(coloc: str, payload_bytes: int) -> dict:
    """One paired run. coloc is 'same' or 'cross'."""
    # Pin producer to anrg-3 always; consumer to anrg-3 (same) or anrg-6 (cross).
    prod_resource = {"node_anrg3": 0.001}
    cons_resource = {"node_anrg3": 0.001} if coloc == "same" else {"node_anrg6": 0.001}

    t0 = time.time()
    obj_ref = producer.options(resources=prod_resource).remote(payload_bytes)
    # Wait for producer to be done — wait, not get, so we don't pull bytes
    # to the driver. ray.wait returns when ObjectRef is ready in object store.
    ray.wait([obj_ref], num_returns=1, fetch_local=False)
    t1 = time.time()

    t2 = time.time()
    # Pass ObjectRef to consumer. ray.get inside the consumer will fetch
    # bytes from producer's object store (locally if same-node, over the
    # network if cross-node).
    n = ray.get(consumer.options(resources=cons_resource).remote(obj_ref))
    t3 = time.time()
    assert n == payload_bytes, f"size mismatch: got {n} vs {payload_bytes}"
    return {
        "t0": round(t0, 4),
        "t1_t0": round(t1 - t0, 4),  # producer compute + store-put time
        "t2_t1": round(t2 - t1, 4),  # idle (driver scheduling)
        "t3_t2": round(t3 - t2, 4),  # consumer fetch+touch
        "e2e":   round(t3 - t0, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default="/tmp/ray-e0.csv")
    args = ap.parse_args()

    payloads = [
        (1 << 20,  "1MB"),
        (10 << 20, "10MB"),
        (100 << 20, "100MB"),
        (500 << 20, "500MB"),
    ]
    colocs = ["same", "cross"]

    ray.init(address="auto", ignore_reinit_error=True)
    print(f"Ray cluster: {ray.cluster_resources()}", file=sys.stderr)

    # Warmup: one cross-node small-payload run to prime Ray's
    # cross-node object-manager / connection caches. Without this the
    # first cross-node run includes unrepresentative connection-setup
    # latency (we observed 180s for 1MB on the first cross-node call).
    print("warmup (cross-node 1MB)...", file=sys.stderr)
    try:
        run_one("cross", 1 << 20)
    except Exception as e:
        print(f"warmup failed: {e}", file=sys.stderr)

    rows = []
    for coloc in colocs:
        for size, label in payloads:
            for r in range(1, args.reps + 1):
                try:
                    out = run_one(coloc, size)
                    print(f"{coloc:<5} {label:>5} rep {r}  e2e={out['e2e']:.2f}s "
                          f"(prod {out['t1_t0']:.2f}, cons {out['t3_t2']:.2f})",
                          file=sys.stderr)
                    out.update({"rep": r, "coloc": coloc, "payload": label,
                                "payload_bytes": size})
                    rows.append(out)
                except Exception as e:
                    print(f"{coloc:<5} {label:>5} rep {r}  ERROR: {e}", file=sys.stderr)
                    rows.append({"rep": r, "coloc": coloc, "payload": label,
                                 "payload_bytes": size, "e2e": -1,
                                 "t0": 0, "t1_t0": 0, "t2_t1": 0, "t3_t2": 0})

    cols = ["rep", "coloc", "payload", "payload_bytes", "t0",
            "t1_t0", "t2_t1", "t3_t2", "e2e"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
