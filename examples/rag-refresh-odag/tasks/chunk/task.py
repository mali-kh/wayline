#!/usr/bin/env python3
"""
RAG KB Refresh — chunk-shard-{1..4} task.

Receives the full shard blob from ingest-shard, extracts this task's shard,
splits documents into ~500-char passages with 100-char overlap, and sends
chunks JSONL to embed-shard-i.
"""

import json
import struct
import time

from wl import WlTask

CHUNK_SIZE = 500
OVERLAP = 100

task = WlTask()
shard_idx = int(task.name.rsplit('-', 1)[1]) - 1  # chunk-shard-1 → 0

print(f"[{task.name}] node={task.node}  shard_idx={shard_idx}", flush=True)

# Receive full blob from ingest-shard
t0 = time.perf_counter()
raw = task.recv_raw()
elapsed_recv = time.perf_counter() - t0
print(f"[{task.name}] recv_raw() -> {len(raw)} bytes in {elapsed_recv:.3f}s", flush=True)

# Extract our shard
num_shards = struct.unpack('>I', raw[:4])[0]
offset = 4
shard_data = None
for i in range(num_shards):
    shard_len = struct.unpack('>I', raw[offset:offset + 4])[0]
    offset += 4
    if i == shard_idx:
        shard_data = raw[offset:offset + shard_len]
    offset += shard_len

print(f"[{task.name}] extracted shard {shard_idx + 1}/{num_shards}: "
      f"{len(shard_data)} bytes", flush=True)

# Parse and chunk
t1 = time.perf_counter()
chunks = []
for line in shard_data.decode().strip().split('\n'):
    if not line:
        continue
    doc = json.loads(line)
    text = doc["text"]
    doc_id = doc["doc_id"]
    start = 0
    ci = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(json.dumps({
            "chunk_id": f"{doc_id}-c{ci}",
            "doc_id": doc_id,
            "text": text[start:end],
        }))
        ci += 1
        start += CHUNK_SIZE - OVERLAP
        if end == len(text):
            break

chunks_bytes = ("\n".join(chunks) + "\n").encode()
elapsed = time.perf_counter() - t1
print(f"[{task.name}] {len(chunks)} chunks ({len(chunks_bytes)} bytes) "
      f"in {elapsed:.3f}s", flush=True)

t2 = time.perf_counter()
task.send_raw(chunks_bytes)
print(f"[{task.name}] send_raw() completed in {time.perf_counter() - t2:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
