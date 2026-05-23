#!/usr/bin/env python3
"""
RAG KB Refresh — eval-queries task.

Loads the global index from merge-index, embeds each evaluation query with
the same feature-hash method, runs brute-force cosine retrieval, and outputs
evaluation results JSON to report.
"""

import array
import hashlib
import json
import math
import os
import struct
import time

from wl import WlTask

DIM = 128
TOP_K = 5


def feature_hash_embed(text, dim=DIM):
    """Deterministic feature-hash embedding (must match embed task)."""
    vec = [0.0] * dim
    for token in text.lower().split():
        h = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(h[:4], 'big') % dim
        sign = 1.0 if h[4] & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def load_queries():
    """Load eval queries from embedded file or generate defaults."""
    path = os.path.join(os.path.dirname(__file__) or ".", "data",
                        "eval_queries.jsonl")
    if os.path.exists(path):
        queries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    queries.append(json.loads(line))
        return queries
    return [
        {"query_id": "q01", "text": "neural network training optimization"},
        {"query_id": "q02", "text": "transformer attention encoder decoder"},
        {"query_id": "q03", "text": "distributed cluster fault tolerance"},
        {"query_id": "q04", "text": "vector similarity nearest neighbor"},
        {"query_id": "q05", "text": "language model generation tokenization"},
    ]


task = WlTask()

print(f"[{task.name}] node={task.node}", flush=True)

# Receive global index
t0 = time.perf_counter()
raw = task.recv_raw()
elapsed_recv = time.perf_counter() - t0
print(f"[{task.name}] recv_raw() -> {len(raw)} bytes in {elapsed_recv:.3f}s", flush=True)

# Unpack
header_len = struct.unpack('>I', raw[:4])[0]
header = json.loads(raw[4:4 + header_len])
vectors_raw = raw[4 + header_len:]

num_vectors = header["num_vectors"]
dim = header["dim"]
chunk_ids = header["chunk_ids"]

vectors = array.array('f')
vectors.frombytes(vectors_raw)
print(f"[{task.name}] index: {num_vectors} vectors x {dim}d", flush=True)

# Load queries
queries = load_queries()
print(f"[{task.name}] loaded {len(queries)} eval queries", flush=True)

# Retrieval
t1 = time.perf_counter()
results = []
latencies = []

for q in queries:
    tq = time.perf_counter()
    qvec = feature_hash_embed(q["text"], dim)

    # Brute-force dot product (vectors are L2-normalised → cosine = dot)
    scores = []
    for i in range(num_vectors):
        off = i * dim
        dot = sum(qvec[d] * vectors[off + d] for d in range(dim))
        scores.append((dot, i))
    scores.sort(key=lambda x: x[0], reverse=True)
    top = scores[:TOP_K]

    lat = time.perf_counter() - tq
    latencies.append(lat)

    hits = [{"chunk_id": chunk_ids[idx], "score": round(sc, 4)}
            for sc, idx in top]
    results.append({
        "query_id": q["query_id"],
        "query_text": q["text"],
        "latency_s": round(lat, 4),
        "top_k": hits,
    })
    print(f"[{task.name}] {q['query_id']}: top1={hits[0]['chunk_id']} "
          f"score={hits[0]['score']:.4f}  lat={lat:.3f}s", flush=True)

elapsed_eval = time.perf_counter() - t1

latencies.sort()
n = len(latencies)
p50 = latencies[n // 2]
p95 = latencies[int(n * 0.95)]

eval_output = {
    "source": task.name,
    "node": task.node,
    "num_queries": len(queries),
    "num_vectors": num_vectors,
    "dim": dim,
    "top_k": TOP_K,
    "total_eval_time_s": round(elapsed_eval, 3),
    "latency_p50_s": round(p50, 4),
    "latency_p95_s": round(p95, 4),
    "results": results,
    "shard_offsets": header.get("shard_offsets"),
    "shard_sources": header.get("shard_sources"),
}

print(f"[{task.name}] eval done: {len(queries)} queries in {elapsed_eval:.3f}s "
      f"(p50={p50:.3f}s  p95={p95:.3f}s)", flush=True)

t2 = time.perf_counter()
task.send(eval_output)
print(f"[{task.name}] send() completed in {time.perf_counter() - t2:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
