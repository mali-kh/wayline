#!/usr/bin/env python3
"""
Auto-generate template.yml (ODAGTemplate) for the RAG KB Refresh example.

Queries the cluster for schedulable nodes and assigns them to roles:
  - First node           -> data-local (ingest + chunk)
  - Last 4 nodes         -> embedding-capable (embed-shard tasks)
  - Last 2 of those      -> merge + eval
  - Last node            -> gateway (report)

Usage:
  python gen_odag.py
  python gen_odag.py --registry 192.168.1.163:5000
  python gen_odag.py --output template-generated.yml
  python gen_odag.py --name my-rag-refresh
"""

import argparse
import json
import subprocess
import sys

TEMPLATE_HEADER = """\
apiVersion: wl.io/v1
kind: ODAGTemplate
metadata:
  name: {name}
  namespace: wl-system
spec:
  description: "RAG KB refresh: ingest -> chunk -> embed -> index -> merge -> eval -> report"
  scheduler: heft
  profiling:
    enabled: true
    warmupRuns: 0
    minSamples: 2
    emaAlpha: 0.3
    maxSamples: 50
  defaults:
    runtime: 10
    dataSize: "5MB"
  retention:
    maxRuns: 10
  tasks:
    # ====================================================================
    # Layer 0 - Ingest & Shard (data-local)
    # ====================================================================
{ingest_task}
    # ====================================================================
    # Layer 1 - Chunk (co-located with ingest)
    # ====================================================================
{chunk_tasks}
    # ====================================================================
    # Layer 2 - Embed (feasible-node constraint)
    # ====================================================================
{embed_tasks}
    # ====================================================================
    # Layer 3 - Build Index (unconstrained)
    # ====================================================================
{index_tasks}
    # ====================================================================
    # Layer 4 - Merge Index (fan-in)
    # ====================================================================
{merge_task}
    # ====================================================================
    # Layer 5 - Eval Queries
    # ====================================================================
{eval_task}
    # ====================================================================
    # Layer 6 - Report (gateway)
    # ====================================================================
{report_task}"""


def get_schedulable_nodes():
    try:
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json"],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        print("error: kubectl not found in PATH", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"error: kubectl failed: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    nodes = []
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        spec = item.get("spec", {})
        taints = spec.get("taints", [])
        unschedulable = spec.get("unschedulable", False)
        has_noschedule = any(
            t.get("effect") == "NoSchedule" for t in taints
        )
        if not has_noschedule and not unschedulable:
            nodes.append(name)
    nodes.sort()
    return nodes


def task_block(name, image, deps, data_size_mb, runtime, cpu, memory, node_names=None):
    deps_str = "[" + ", ".join(f'"{d}"' for d in deps) + "]" if deps else "[]"
    ds = f'"{data_size_mb}MB"' if data_size_mb > 0 else '"0"'
    block = f"""\
    - name: {name}
      image: {image}
      command: ["python", "task.py"]
      dependencies: {deps_str}
      dataSize: {ds}
      runtime: {runtime}
      resources:
        cpu: "{cpu}"
        memory: "{memory}"
"""
    if node_names:
        nodes_str = "[" + ", ".join(node_names) + "]"
        block += f"""\
      constraints:
        nodeNames: {nodes_str}
"""
    return block


def generate(nodes, registry, template_name):
    if len(nodes) < 4:
        print(f"error: need >= 4 schedulable nodes, found {len(nodes)}: {nodes}",
              file=sys.stderr)
        sys.exit(1)

    data_node = nodes[0]
    embed_nodes = nodes[-4:] if len(nodes) >= 8 else nodes[-min(4, len(nodes)):]
    merge_nodes = embed_nodes[-2:]
    gateway = nodes[-1]

    print(f"Data-local node (ingest+chunk): {data_node}", file=sys.stderr)
    print(f"Embedding nodes:                {embed_nodes}", file=sys.stderr)
    print(f"Merge/eval nodes:               {merge_nodes}", file=sys.stderr)
    print(f"Gateway node (report):          {gateway}", file=sys.stderr)

    ingest = task_block("ingest-shard", f"{registry}/wl-rag-ingest:latest",
                        [], 20, 5, "300m", "256Mi", [data_node])

    chunks = ""
    embeds = ""
    indices = ""
    for i in range(1, 5):
        chunks += task_block(f"chunk-shard-{i}", f"{registry}/wl-rag-chunk:latest",
                             ["ingest-shard"], 6, 5, "300m", "256Mi", [data_node])
        embeds += task_block(f"embed-shard-{i}", f"{registry}/wl-rag-embed:latest",
                             [f"chunk-shard-{i}"], 5, 20, "500m", "256Mi", embed_nodes)
        indices += task_block(f"build-index-{i}", f"{registry}/wl-rag-index:latest",
                              [f"embed-shard-{i}"], 6, 3, "300m", "256Mi")

    merge = task_block("merge-index", f"{registry}/wl-rag-merge:latest",
                       [f"build-index-{i}" for i in range(1, 5)],
                       22, 5, "300m", "256Mi", merge_nodes)

    ev = task_block("eval-queries", f"{registry}/wl-rag-eval:latest",
                    ["merge-index"], 1, 15, "500m", "256Mi", merge_nodes)

    rpt = task_block("report", f"{registry}/wl-rag-report:latest",
                     ["eval-queries"], 0, 2, "200m", "128Mi", [gateway])

    return TEMPLATE_HEADER.format(
        name=template_name,
        ingest_task=ingest,
        chunk_tasks=chunks,
        embed_tasks=embeds,
        index_tasks=indices,
        merge_task=merge,
        eval_task=ev,
        report_task=rpt,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate RAG KB Refresh ODAGTemplate with real node names",
    )
    parser.add_argument("--registry", default="192.168.1.163:5000")
    parser.add_argument("--output", default="template.yml")
    parser.add_argument("--name", default="rag-refresh")
    args = parser.parse_args()

    nodes = get_schedulable_nodes()
    print(f"Found {len(nodes)} schedulable nodes: {nodes}", file=sys.stderr)

    yaml_str = generate(nodes, args.registry, args.name)
    with open(args.output, "w") as f:
        f.write(yaml_str)
    print(f"\nWrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
