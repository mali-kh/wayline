#!/usr/bin/env python3
"""
RAG KB Refresh — ingest-shard task.

Generates a synthetic document corpus and packs it into N_SHARDS=4 partitions.
Sends a single blob containing all shards to the chunk-shard tasks.

Blob format:
  [4B num_shards] + ([4B shard_len][shard JSONL bytes]) * N
"""

import json
import os
import random
import struct
import time

from wl import WlTask

VOCAB = [
    "neural", "network", "gradient", "descent", "loss", "function",
    "optimization", "learning", "rate", "batch", "epoch", "training",
    "validation", "overfitting", "regularization", "dropout", "weight",
    "bias", "activation", "sigmoid", "softmax", "relu", "parameter",
    "hyperparameter", "convergence", "backpropagation", "forward",
    "transformer", "attention", "token", "embedding", "vocabulary",
    "sequence", "encoder", "decoder", "language", "model", "generation",
    "translation", "sentiment", "classification", "entity", "recognition",
    "parsing", "tokenization", "subword", "positional", "encoding",
    "distributed", "cluster", "node", "partition", "replication",
    "consensus", "fault", "tolerance", "latency", "throughput",
    "balancing", "sharding", "consistency", "availability", "scalability",
    "convolutional", "recurrent", "pooling", "feature", "extraction",
    "pretrained", "fine-tuning", "transfer", "representation", "layer",
    "architecture", "residual", "normalization", "inference", "prediction",
    "pipeline", "ingestion", "preprocessing", "indexing", "retrieval",
    "vector", "database", "storage", "compute", "memory", "cache",
    "query", "search", "similarity", "nearest", "neighbor", "dense",
    "sparse", "hybrid", "ranking", "relevance", "document", "passage",
    "chunk", "knowledge", "base", "augmented", "context", "prompt",
    "algorithm", "complexity", "efficient", "parallel", "concurrent",
    "process", "thread", "synchronization", "lock", "atomic", "queue",
    "stack", "tree", "graph", "matrix", "tensor", "dimension",
    "performance", "benchmark", "evaluation", "metric", "accuracy",
    "precision", "recall", "score", "threshold", "configuration",
    "deployment", "monitoring", "logging", "debugging", "profiling",
]

N_SHARDS = 4

task = WlTask()
DATA_SIZE = task.expected_data_size or 20_000_000
RUNTIME = task.expected_runtime or 5.0
run_id = task.run_id or "0"

print(f"[{task.name}] node={task.node}  data_size={DATA_SIZE}  runtime={RUNTIME}s", flush=True)

shard_target = DATA_SIZE // N_SHARDS
rng = random.Random(f"{task.name}-{run_id}")

t0 = time.perf_counter()

shards = []
doc_counter = 0
for s in range(N_SHARDS):
    lines = []
    current_size = 0
    while current_size < shard_target:
        doc_id = f"doc-{doc_counter:06d}"
        n_words = rng.randint(100, 200)
        words = [rng.choice(VOCAB) for _ in range(n_words)]
        text = " ".join(words)
        line = json.dumps({"doc_id": doc_id, "text": text})
        lines.append(line)
        current_size += len(line) + 1
        doc_counter += 1
    shard_bytes = ("\n".join(lines) + "\n").encode()
    shards.append(shard_bytes)
    print(f"[{task.name}] shard {s+1}: {len(lines)} docs, {len(shard_bytes)} bytes", flush=True)

elapsed_gen = time.perf_counter() - t0
print(f"[{task.name}] generated {doc_counter} total docs in {elapsed_gen:.3f}s", flush=True)

remaining = max(0, RUNTIME - elapsed_gen)
if remaining > 0:
    time.sleep(remaining)

# Pack blob
blob = bytearray(struct.pack('>I', N_SHARDS))
for shard_bytes in shards:
    blob.extend(struct.pack('>I', len(shard_bytes)))
    blob.extend(shard_bytes)

print(f"[{task.name}] blob: {len(blob)} bytes", flush=True)

t1 = time.perf_counter()
task.send_raw(bytes(blob))
print(f"[{task.name}] send_raw() completed in {time.perf_counter() - t1:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
