"""
E0 two-hop microbenchmark — Wayline consumer.

Reads:
    WL_E0_BYTES   : expected payload size in bytes (for sanity check)

Emits one tagged JSON line:

    WL_E0_TIMESTAMPS {"role":"consumer","pod":"...","node":"...",
                       "t3_wall":<seconds since epoch>,
                       "t4_wall":<seconds since epoch>,
                       "bytes":<int>,
                       "ok":<bool>}

t3 is captured immediately before recv_raw() — the moment the consumer
"can start" waiting on data. t4 is when the full payload is in memory.

The driver later combines this with the producer's t1 and the Pod API
finishedAt timestamp to compute E2E and the architectural deltas.
"""

import json
import os
import sys
import time

from wl import WlTask


EXPECTED_BYTES = int(os.environ.get("WL_E0_BYTES", "1048576"))


def emit(role: str, **fields) -> None:
    record = {"role": role, **fields}
    sys.stdout.write("WL_E0_TIMESTAMPS " + json.dumps(record) + "\n")
    sys.stdout.flush()


def main() -> int:
    task = WlTask()

    t3_wall = time.time()
    payload = task.recv_raw("producer")
    t4_wall = time.time()

    ok = len(payload) == EXPECTED_BYTES

    emit(
        "consumer",
        pod=os.environ.get("HOSTNAME", "?"),
        node=os.environ.get("NODE_NAME", "?"),
        t3_wall=t3_wall,
        t4_wall=t4_wall,
        bytes=len(payload),
        expected_bytes=EXPECTED_BYTES,
        ok=ok,
    )

    task.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
