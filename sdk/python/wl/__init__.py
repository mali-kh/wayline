"""
Wayline Python SDK.

Usage in task images:

    from wl import WlTask

    task = WlTask()
    data = task.recv("upstream-task-name")   # blocks until data arrives
    result = process(data)
    task.send("downstream-task-name", result)

The controller injects peer configuration as environment variables:
    WL_TASK_NAME=<this-task-name>
    WL_PEER_<NAME>=<transport>://<endpoint>

The SDK reads these env vars automatically.
"""

from wl.api import WlTask

__all__ = ["WlTask"]
