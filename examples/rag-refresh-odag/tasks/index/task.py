#!/usr/bin/env python3
"""
RAG KB Refresh — build-index-{1..4} task.

Receives embedding blob from embed-shard-i, builds a coarse token-bucket
inverted index on top of the vectors, and sends the enriched index blob
to merge-index.
"""

import array
import hashlib
import json
import struct
import time

from wl import WlTask

BUCKET_COUNT = 256

task = WlTask()

print(f"[{task.name}] node={task.node}", flush=True)

t0 = time.perf_counter()
raw = task.recv_raw()
elapsed_recv = time.perf_counter() - t0
print(f"[{task.name}] recv_raw() -> {len(raw)} bytes in {elapsed_recv:.3f}s", flush=True)

# Unpack embedding blob
header_len = struct.unpack('>I', raw[:4])[0]
header = json.loads(raw[4:4 + header_len])
vectors_raw = raw[4 + header_len:]

num_vectors = header["num_vectors"]
dim = header["dim"]
chunk_ids = header["chunk_ids"]
print(f"[{task.name}] {num_vectors} vectors x {dim}d", flush=True)

# Build coarse bucket map on chunk_id hash
t1 = time.perf_counter()
bucket_map = {}
for i, cid in enumerate(chunk_ids):
    bucket = str(hashlib.md5(cid.encode()).digest()[0])
    if bucket not in bucket_map:
        bucket_map[bucket] = []
    bucket_map[bucket].append(i)

elapsed_idx = time.perf_counter() - t1
print(f"[{task.name}] built {len(bucket_map)} buckets in {elapsed_idx:.3f}s", flush=True)

# Pack index blob (enriched header, same vectors)
index_header = json.dumps({
    "num_vectors": num_vectors,
    "dim": dim,
    "chunk_ids": chunk_ids,
    "bucket_count": BUCKET_COUNT,
    "bucket_map": bucket_map,
}).encode()
blob = struct.pack('>I', len(index_header)) + index_header + vectors_raw

print(f"[{task.name}] index blob: {len(blob)} bytes", flush=True)

t2 = time.perf_counter()
task.send_raw(blob)
print(f"[{task.name}] send_raw() completed in {time.perf_counter() - t2:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
