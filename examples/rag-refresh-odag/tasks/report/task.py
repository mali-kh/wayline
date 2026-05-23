#!/usr/bin/env python3
"""
RAG KB Refresh — report task.

Receives evaluation results and produces a formatted QA regression report
with latency stats, top-k hits per query, and execution provenance.
"""

import json
import time

from wl import WlTask

task = WlTask()
run_id = task.run_id or "unknown"

print(f"[{task.name}] node={task.node}  run_id={run_id}", flush=True)

t0 = time.perf_counter()
eval_data = task.recv()
elapsed_recv = time.perf_counter() - t0
print(f"[{task.name}] recv() completed in {elapsed_recv:.3f}s", flush=True)

# Provenance
stage_nodes = {"report": task.node}
eval_node = task.dep_node("eval-queries")
stage_nodes["eval-queries"] = eval_node

report = {
    "title": "RAG Knowledge Base Refresh - QA Regression Report",
    "run_id": run_id,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "index_summary": {
        "total_vectors": eval_data.get("num_vectors", 0),
        "dim": eval_data.get("dim", 0),
        "shard_sources": eval_data.get("shard_sources", []),
        "shard_offsets": eval_data.get("shard_offsets", []),
    },
    "eval_summary": {
        "num_queries": eval_data.get("num_queries", 0),
        "top_k": eval_data.get("top_k", 0),
        "total_eval_time_s": eval_data.get("total_eval_time_s", 0),
        "latency_p50_s": eval_data.get("latency_p50_s", 0),
        "latency_p95_s": eval_data.get("latency_p95_s", 0),
    },
    "query_results": eval_data.get("results", []),
    "provenance": stage_nodes,
}

# Print formatted report
print("", flush=True)
print("=" * 72, flush=True)
print(f"  {report['title']}", flush=True)
print(f"  Run: {report['run_id']}   Time: {report['timestamp']}", flush=True)
print("=" * 72, flush=True)
idx = report["index_summary"]
ev = report["eval_summary"]
print(f"  Index: {idx['total_vectors']} vectors, {idx['dim']}d, "
      f"{len(idx['shard_sources'])} shards", flush=True)
print(f"  Eval:  {ev['num_queries']} queries, top-{ev['top_k']}", flush=True)
print(f"  Latency: p50={ev['latency_p50_s']}s  "
      f"p95={ev['latency_p95_s']}s  "
      f"total={ev['total_eval_time_s']}s", flush=True)

print("", flush=True)
print("  Query results:", flush=True)
for qr in report["query_results"]:
    text = qr["query_text"]
    if len(text) > 50:
        text = text[:50] + "..."
    print(f"    [{qr['query_id']}] \"{text}\"", flush=True)
    for hit in qr["top_k"][:3]:
        print(f"      {hit['chunk_id']:30s}  score={hit['score']:.4f}", flush=True)

print("", flush=True)
print("  Provenance:", flush=True)
for stage, node in sorted(report["provenance"].items()):
    print(f"    {stage:20s} -> {node}", flush=True)
print("=" * 72, flush=True)

t1 = time.perf_counter()
task.send(report)
print(f"[{task.name}] send() completed in {time.perf_counter() - t1:.3f}s", flush=True)
print(f"[{task.name}] done", flush=True)
task.close()
