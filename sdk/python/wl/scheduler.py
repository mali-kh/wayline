"""
Wayline Scheduler interface.

A scheduler is a Python callable with this signature:

    def schedule(dag: dict, cluster_state: dict) -> dict:
        ...

Input/output shapes are defined in api/scheduler/schema.json.

Built-in schedulers are in wl/schedulers/.
To use a built-in:

    from wl.schedulers.heft import schedule

To run as a subprocess (called by the controller via stdin/stdout):

    if __name__ == "__main__":
        from wl.scheduler import run_as_subprocess
        from wl.schedulers.heft import schedule
        run_as_subprocess(schedule)
"""

import json
import sys
from typing import Callable


SchedulerFn = Callable[[dict, dict], dict]


def run_as_subprocess(scheduler_fn: SchedulerFn) -> None:
    """
    Run a scheduler function as a subprocess.
    Reads JSON input from stdin, writes JSON output to stdout.
    Called by the controller when scheduler = path/to/script.py.
    """
    raw = sys.stdin.read()
    inp = json.loads(raw)
    dag = inp["dag"]
    cluster_state = inp["clusterState"]
    result = scheduler_fn(dag, cluster_state)
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
