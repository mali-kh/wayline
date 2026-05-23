#!/usr/bin/env python3
"""
RAG KB Refresh — embed-shard-{1..4} task.

Receives chunks JSONL from chunk-shard-i, computes deterministic feature-hash
embeddings (D=128, L2-normalised), and sends an embedding blob to build-index-i.

Embedding blob format:
  [4B header_json_len][header JSON][N * D * 4 bytes float32 vectors]
"""

import array
import hashlib
import json
import math
import struct
import time

from wl import WlTask

DIM = 128


def feature_hash_embed(text, dim=DIM):
    """Deterministic feature-hash embedding into dim-dimensional unit vector."""
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


task = WlTask()
RUNTIME = task.expected_runtime or 20.0

print(f"[{task.name}] node={task.node}  dim={DIM}  runtime={RUNTIME}s", flush=True)

t0 = time.perf_counter()
chunks_raw = task.recv_raw()
elapsed_recv = time.perf_counter() - t0
print(f"[{task.name}] recv_raw() -> {len(chunks_raw)} bytes in {elapsed_recv:.3f}s", flush=True)

# Embed
t1 = time.perf_counter()
chunk_ids = []
all_vectors = array.array('f')

for line in chunks_raw.decode().strip().split('\n'):
    if not line:
        continue
    chunk = json.loads(line)
    chunk_ids.append(chunk["chunk_id"])
    all_vectors.extend(feature_hash_embed(chunk["text"]))

num_vectors = len(chunk_ids)
elapsed_embed = time.perf_counter() - t1
print(f"[{task.name}] embedded {num_vectors} chunks in {elapsed_embed:.3f}s", flush=True)

# Busy loop for remaining runtime budget
remaining = max(0, RUNTIME - elapsed_embed)
if remaining > 0:
    tb = time.perf_counter()
    while time.perf_counter() - tb < remaining:
        hashlib.sha256(b"compute").digest()
    print(f"[{task.name}] busy loop {time.perf_counter() - tb:.1f}s", flush=True)

# Pack blob
header = json.dumps({
    "num_vectors": num_vectors,
    "dim": DIM,
    "chunk_ids": chunk_ids,
}).encode()
blob = struct.pack('>I', len(header)) + header + all_vectors.tobytes()

print(f"[{task.name}] blob: {len(blob)} bytes "
      f"({num_vectors} vectors x {DIM}d)", flush=True)

t2 = time.perf_counter()
task.send_raw(blob)
print(f"[{task.name}] send_raw() completed in {time.perf_counter() - t2:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
