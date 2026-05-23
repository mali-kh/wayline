"""E0 two-hop microbenchmark -- shared-filesystem (RWX NFS) consumer.

Mirrors the MinIO consumer: t3 = enter wait; poll the shared mount until
the payload appears at full size (t_found); then read it fully (t4). The
read t_found->t4 is the NFS download-equivalent. Same DSF_E0_TIMESTAMPS
schema as the other systems so harvest.py is unchanged.
"""
import json, os, sys, time

PATH     = os.environ["E0_PATH"]
EXPECT   = int(os.environ.get("E0_BYTES", "1048576"))
POLL     = float(os.environ.get("E0_POLL_S", "0.025"))
DEADLINE = float(os.environ.get("E0_DEADLINE_S", "300"))


def emit(role, **f):
    sys.stdout.write("DSF_E0_TIMESTAMPS " + json.dumps({"role": role, **f}) + "\n")
    sys.stdout.flush()


def main():
    t3 = time.time()
    deadline = t3 + DEADLINE
    t_found = None
    while time.time() < deadline:
        try:
            if os.path.exists(PATH) and os.path.getsize(PATH) >= EXPECT:
                t_found = time.time(); break
        except OSError:
            pass
        time.sleep(POLL)
    if t_found is None:
        emit("consumer", pod=os.environ.get("HOSTNAME"), node=os.environ.get("NODE_NAME"),
             t3_wall=t3, t_found_wall=None, t4_wall=None, bytes=0, error="timeout")
        return 1
    n = 0
    with open(PATH, "rb") as fh:           # blocking read = NFS download
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
    t4 = time.time()
    emit("consumer", pod=os.environ.get("HOSTNAME"), node=os.environ.get("NODE_NAME"),
         t3_wall=t3, t_found_wall=t_found, t4_wall=t4, bytes=n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
