#!/usr/bin/env python3
"""
RAG KB Refresh — merge-index task.

Fan-in: receives 4 index blobs from build-index-1..4 and merges them into a
single global index with concatenated vectors and unified chunk_id list.
"""

import array
import json
import struct
import time

from wl import WlTask

task = WlTask()

print(f"[{task.name}] node={task.node}", flush=True)
print(f"[{task.name}] dependencies={task.dependencies}", flush=True)

t0 = time.perf_counter()
inputs = task.recv_all_raw()
elapsed_recv = time.perf_counter() - t0
print(f"[{task.name}] recv_all_raw() -> {len(inputs)} inputs "
      f"in {elapsed_recv:.3f}s", flush=True)

# Merge
t1 = time.perf_counter()
all_chunk_ids = []
all_vectors = array.array('f')
shard_offsets = [0]
shard_sources = []
dim = None
total_bytes_in = 0

for dep_name in sorted(inputs.keys()):
    raw = inputs[dep_name]
    total_bytes_in += len(raw)

    header_len = struct.unpack('>I', raw[:4])[0]
    header = json.loads(raw[4:4 + header_len])
    vectors_raw = raw[4 + header_len:]

    n = header["num_vectors"]
    d = header["dim"]
    if dim is None:
        dim = d

    arr = array.array('f')
    arr.frombytes(vectors_raw)
    all_vectors.extend(arr)
    all_chunk_ids.extend(header["chunk_ids"])
    shard_offsets.append(len(all_chunk_ids))
    shard_sources.append(dep_name)

    dep_node = task.dep_node(dep_name)
    print(f"[{task.name}] merged {dep_name} ({dep_node}): "
          f"{n} vectors, {len(raw)} bytes", flush=True)

total_vectors = len(all_chunk_ids)
elapsed_merge = time.perf_counter() - t1
print(f"[{task.name}] merged {total_vectors} vectors in {elapsed_merge:.3f}s", flush=True)

# Pack global index
global_header = json.dumps({
    "num_vectors": total_vectors,
    "dim": dim,
    "chunk_ids": all_chunk_ids,
    "shard_offsets": shard_offsets,
    "shard_sources": shard_sources,
}).encode()
blob = struct.pack('>I', len(global_header)) + global_header + all_vectors.tobytes()

print(f"[{task.name}] global index: {len(blob)} bytes "
      f"({total_vectors} vectors x {dim}d)", flush=True)
print(f"[{task.name}] total bytes received: {total_bytes_in}", flush=True)

t2 = time.perf_counter()
task.send_raw(blob)
print(f"[{task.name}] send_raw() completed in {time.perf_counter() - t2:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
