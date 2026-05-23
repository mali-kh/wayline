"""
HEFT — Heterogeneous Earliest Finish Time scheduler.

Reference: Topcuoglu, Hariri & Wu (2002).

Input/output follow the schema defined in api/scheduler/schema.json.
"""

from __future__ import annotations
from typing import Any


def schedule(dag: dict, cluster_state: dict) -> dict:
    """
    Compute a HEFT schedule.

    Args:
        dag:           DAG spec (tasks with name, dependencies, runtime, dataSize, constraints).
        cluster_state: Cluster state (nodes with available resources, optional bandwidth matrix).

    Returns:
        dict with 'assignments' list and 'estimatedMakespan'.
    """
    tasks = {t["name"]: t for t in dag["tasks"]}
    nodes = [n for n in cluster_state["nodes"] if n.get("ready", True)]
    bandwidth_matrix = _build_bandwidth_matrix(cluster_state.get("bandwidth", []))

    if not nodes:
        raise ValueError("No ready nodes available for scheduling.")

    # Compute average computation cost per task per node.
    avg_comp = _avg_computation_costs(tasks, nodes)

    # Compute average bandwidth (bytes/sec) across all node pairs.
    avg_bw = _avg_bandwidth(bandwidth_matrix, nodes) or 1e9  # default 1 GB/s if unknown

    # Compute upward rank for each task (critical path weight).
    ranks = _compute_ranks(tasks, avg_comp, avg_bw)

    # Sort tasks by descending rank (HEFT priority list).
    priority_order = sorted(tasks.keys(), key=lambda t: ranks[t], reverse=True)

    # Schedule tasks onto processors using EFT.
    node_available: dict[str, float] = {n["name"]: 0.0 for n in nodes}
    task_finish: dict[str, float] = {}
    task_node: dict[str, str] = {}
    task_start: dict[str, float] = {}

    for task_name in priority_order:
        task = tasks[task_name]
        allowed_nodes = _allowed_nodes(task, nodes)

        best_node, best_start, best_finish = None, float("inf"), float("inf")

        for node in allowed_nodes:
            node_name = node["name"]
            comp_cost = _computation_cost(task, node)

            # Earliest time this node is free.
            ready = node_available[node_name]

            # Earliest time all dependencies have finished and data has arrived.
            for dep in task.get("dependencies", []):
                dep_finish = task_finish.get(dep, 0.0)
                dep_node = task_node.get(dep, node_name)
                comm_cost = _communication_cost(tasks[dep], node_name, dep_node, bandwidth_matrix, avg_bw)
                ready = max(ready, dep_finish + comm_cost)

            finish = ready + comp_cost
            if finish < best_finish:
                best_node, best_start, best_finish = node_name, ready, finish

        assert best_node is not None
        task_node[task_name] = best_node
        task_start[task_name] = best_start
        task_finish[task_name] = best_finish
        node_available[best_node] = best_finish

    makespan = max(task_finish.values()) if task_finish else 0.0

    assignments = [
        {
            "task": name,
            "node": task_node[name],
            "estimatedStart": task_start[name],
            "estimatedFinish": task_finish[name],
        }
        for name in tasks
    ]

    return {"assignments": assignments, "estimatedMakespan": makespan}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _avg_computation_costs(tasks: dict, nodes: list) -> dict[str, float]:
    """Average runtime per task across all nodes (uniform for now; extend with node perf model)."""
    return {name: task.get("runtime", 1) for name, task in tasks.items()}


def _avg_bandwidth(matrix: dict, nodes: list) -> float:
    if not matrix:
        return 0.0
    values = list(matrix.values())
    return sum(values) / len(values) if values else 0.0


def _build_bandwidth_matrix(bandwidth_list: list) -> dict[tuple[str, str], float]:
    return {(e["from"], e["to"]): e["bytesPerSec"] for e in bandwidth_list}


def _computation_cost(task: dict, node: dict) -> float:
    return float(task.get("runtime", 1))


def _communication_cost(
    src_task: dict,
    dst_node: str,
    src_node: str,
    matrix: dict,
    avg_bw: float,
) -> float:
    if dst_node == src_node:
        return 0.0
    data_bytes = _parse_data_size(src_task.get("dataSize", "0"))
    bw = matrix.get((src_node, dst_node), avg_bw)
    return data_bytes / bw if bw > 0 else 0.0


def _compute_ranks(tasks: dict, avg_comp: dict, avg_bw: float) -> dict[str, float]:
    ranks: dict[str, float] = {}

    def rank(name: str) -> float:
        if name in ranks:
            return ranks[name]
        task = tasks[name]
        successors = [t for t, td in tasks.items() if name in td.get("dependencies", [])]
        if not successors:
            ranks[name] = avg_comp[name]
        else:
            data_bytes = _parse_data_size(task.get("dataSize", "0"))
            comm = data_bytes / avg_bw if avg_bw > 0 else 0.0
            ranks[name] = avg_comp[name] + max(comm + rank(s) for s in successors)
        return ranks[name]

    for name in tasks:
        rank(name)
    return ranks


def _allowed_nodes(task: dict, nodes: list) -> list:
    allowed = task.get("constraints", {}).get("nodeNames")
    if allowed:
        return [n for n in nodes if n["name"] in allowed]
    return nodes


def _parse_data_size(s: str) -> float:
    """Parse data size string like '100MB', '1GB', '512KB' to bytes."""
    if not s:
        return 0.0
    s = s.strip().upper()
    units = {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}
    for suffix, mult in sorted(units.items(), key=lambda x: -len(x[0])):
        if s.endswith(suffix):
            return float(s[: -len(suffix)]) * mult
    return float(s)
