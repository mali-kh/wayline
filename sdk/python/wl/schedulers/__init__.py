"""
Built-in Wayline schedulers.

Available:
    heft   — Heterogeneous Earliest Finish Time
    cpop   — Critical Path on a Processor (planned)
    maxmin — Max-min heuristic (planned)

Usage:
    from wl.schedulers.heft import schedule
    result = schedule(dag, cluster_state)
"""
