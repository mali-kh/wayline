"""
Shared-volume transport for Wayline — centralized storage baseline.

All tasks read/write through a shared NFS volume instead of Wayline's native
P2P data-agent transport. This serves as a comparison point to demonstrate
the scalability advantage of direct node-to-node data transfer.

Unlike the data-agent approach where data is pushed directly to the target
node, shared-volume requires all data to traverse the NFS server, creating
a central I/O bottleneck.

Env vars:
    WL_SHARED_DIR    — shared mount path (default: /shared/wl-outputs)
    WL_ODAG_NAME     — ODAG name (used as directory prefix)
    WL_TASK_NAME     — this task's name
    WL_DEPS          — comma-separated dependency names
    WL_SUCCESSORS    — comma-separated successor names
"""

import json
import os
import time


class SharedVolumeTransport:
    """
    Shared NFS volume transport for evaluation.

    Sender writes to /shared/wl-outputs/<odag>/<task>/output.
    Receiver polls until the file appears, then reads it.

    This is the centralized baseline — all I/O goes through NFS.
    """

    def __init__(self) -> None:
        self._shared_dir = os.environ.get("WL_SHARED_DIR", "/shared/wl-outputs")
        self._odag_name = os.environ.get("WL_ODAG_NAME", "unknown")
        self._task_name = os.environ.get("WL_TASK_NAME", "unknown")
        self._deps = [d for d in os.environ.get("WL_DEPS", "").split(",") if d]
        self._succs = [s for s in os.environ.get("WL_SUCCESSORS", "").split(",") if s]

        # Create output directory.
        self._output_dir = os.path.join(self._shared_dir, self._odag_name, self._task_name)
        os.makedirs(self._output_dir, exist_ok=True)

    def _output_path(self, odag: str, task: str) -> str:
        return os.path.join(self._shared_dir, odag, task, "output")

    def _done_path(self, odag: str, task: str) -> str:
        return os.path.join(self._shared_dir, odag, task, ".done")

    def send(self, payload: bytes) -> None:
        """Write output to the shared volume and signal completion."""
        out_path = self._output_path(self._odag_name, self._task_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(payload)
        # Write .done marker so receivers know data is complete.
        done_path = self._done_path(self._odag_name, self._task_name)
        with open(done_path, "w") as f:
            f.write("done")

    def recv(self, peer: str | None = None) -> bytes:
        """Poll the shared volume until the peer's output appears."""
        if peer is None:
            if len(self._deps) == 1:
                peer = self._deps[0]
            else:
                raise ValueError("shared_volume transport requires peer name when multiple deps exist")

        done_path = self._done_path(self._odag_name, peer)
        out_path = self._output_path(self._odag_name, peer)

        # Poll until .done marker appears.
        while not os.path.exists(done_path):
            time.sleep(0.1)

        with open(out_path, "rb") as f:
            return f.read()

    def recv_all(self) -> dict[str, bytes]:
        """Read all dependencies from the shared volume."""
        result = {}
        for dep in self._deps:
            result[dep] = self.recv(dep)
        return result

    # Streaming methods not supported for shared volume (batch only).
    def publish(self, payload: bytes, topic: bytes = b"") -> None:
        self.send(payload)

    def subscribe(self, peer: str):
        raise NotImplementedError("subscribe() not supported for shared_volume transport")

    def poll_subscribers(self, sockets, timeout_ms=-1):
        raise NotImplementedError("poll_subscribers() not supported for shared_volume transport")

    def close(self) -> None:
        pass
