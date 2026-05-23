"""E0 two-hop microbenchmark -- shared-filesystem (RWX NFS) producer.

Mirrors the MinIO producer but writes the payload to a node-shared NFS
mount instead of uploading to an object store. t1->t1' is the NFS write
(the upload-equivalent). Atomic publish via rename so the consumer never
sees a partial file. Emits the same DSF_E0_TIMESTAMPS schema.
"""
import json, os, sys, time

PAYLOAD = int(os.environ.get("E0_BYTES", "1048576"))
COMPUTE = float(os.environ.get("E0_COMPUTE", "5.0"))
PATH    = os.environ["E0_PATH"]            # e.g. /shared/<run>/payload


def emit(role, **f):
    sys.stdout.write("DSF_E0_TIMESTAMPS " + json.dumps({"role": role, **f}) + "\n")
    sys.stdout.flush()


def main():
    t0 = time.time()
    time.sleep(COMPUTE)                    # synthetic compute, matches other systems
    t1 = time.time()
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    block = os.urandom(1 << 20)            # 1 MiB random block, repeated
    tmp = PATH + ".tmp"
    with open(tmp, "wb") as fh:
        written = 0
        while written < PAYLOAD:
            n = min(len(block), PAYLOAD - written)
            fh.write(block[:n]); written += n
        fh.flush(); os.fsync(fh.fileno())  # force bytes to the NFS server
    os.rename(tmp, PATH)                    # atomic publish
    t1p = time.time()
    emit("producer", pod=os.environ.get("HOSTNAME"), node=os.environ.get("NODE_NAME"),
         t0_wall=t0, t1_wall=t1, t1p_wall=t1p, bytes=PAYLOAD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
