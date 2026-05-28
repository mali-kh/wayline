"""
E0 two-hop microbenchmark — Wayline producer.

Reads:
    WL_E0_BYTES   : payload size in bytes (e.g. "104857600" for 100 MiB)
    WL_E0_COMPUTE : compute-sleep seconds (default 5.0)

Emits one tagged JSON line to stdout for the harvester:

    WL_E0_TIMESTAMPS {"role":"producer","pod":"...","node":"...",
                       "t0_wall":<seconds since epoch>,
                       "t1_wall":<seconds since epoch>,
                       "bytes":<int>}

t0 is taken immediately on entry, t1 immediately before task.send_raw().
The data-agent handoff cost is included in t2 - t1 (where t2 is the pod
terminated timestamp, read from the Kubernetes API by the driver).
"""

import json
import os
import sys
import time

from wl import WlTask


PAYLOAD_BYTES = int(os.environ.get("WL_E0_BYTES", "1048576"))
COMPUTE_SEC   = float(os.environ.get("WL_E0_COMPUTE", "5.0"))


def emit(role: str, **fields) -> None:
    record = {"role": role, **fields}
    sys.stdout.write("WL_E0_TIMESTAMPS " + json.dumps(record) + "\n")
    sys.stdout.flush()


def main() -> int:
    t0_wall = time.time()
    task = WlTask()

    # Compute phase — fixed sleep keeps cells comparable without
    # introducing CPU variance.
    if COMPUTE_SEC > 0:
        time.sleep(COMPUTE_SEC)

    # Materialize the payload. Deterministic content (zeros) so we are
    # measuring transfer cost, not generation cost.
    payload = b"\x00" * PAYLOAD_BYTES

    t1_wall = time.time()

    # The send_raw() call routes to all successors; for E0 there is
    # exactly one (consumer). For same-node the data-agent writes a
    # local file; for cross-node it writes locally and asks its peer
    # data-agent to pull/push. Producer pod exits as soon as send_raw
    # returns — that's the architectural property under test.
    task.send_raw(payload)

    emit(
        "producer",
        pod=os.environ.get("HOSTNAME", "?"),
        node=os.environ.get("NODE_NAME", "?"),
        t0_wall=t0_wall,
        t1_wall=t1_wall,
        bytes=PAYLOAD_BYTES,
    )

    task.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
