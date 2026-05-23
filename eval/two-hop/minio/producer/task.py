"""
E0 two-hop microbenchmark — MinIO baseline producer.

Reads:
    E0_BYTES        : payload size in bytes
    E0_COMPUTE      : compute-sleep seconds (default 5.0)
    E0_MINIO_URL    : http://minio.e0-bench.svc.cluster.local:9000
    E0_MINIO_USER   : MinIO root user
    E0_MINIO_PASS   : MinIO root password
    E0_BUCKET       : object bucket (e.g. e0-bench)
    E0_OBJECT       : object key for this run

Emits one tagged JSON line to stdout:

    DSF_E0_TIMESTAMPS {"role":"producer","pod":"...","node":"...",
                       "t0_wall":..., "t1_wall":..., "t1p_wall":...,
                       "bytes":<int>}

t0 is on entry, t1 is right before put_object, t1' is right after
put_object returns. The producer pod terminates as soon as t1' is
emitted — but unlike the DSF case, the pod was holding compute for
(t1' − t1), the upload window. That difference is what E0 measures.
"""

import json
import os
import sys
import time

import boto3
from botocore.client import Config


def env_required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"missing env: {name}")
    return v


PAYLOAD_BYTES = int(os.environ.get("E0_BYTES", "1048576"))
COMPUTE_SEC   = float(os.environ.get("E0_COMPUTE", "5.0"))
MINIO_URL     = env_required("E0_MINIO_URL")
MINIO_USER    = env_required("E0_MINIO_USER")
MINIO_PASS    = env_required("E0_MINIO_PASS")
BUCKET        = env_required("E0_BUCKET")
OBJECT        = env_required("E0_OBJECT")


def emit(role: str, **fields) -> None:
    record = {"role": role, **fields}
    sys.stdout.write("DSF_E0_TIMESTAMPS " + json.dumps(record) + "\n")
    sys.stdout.flush()


def main() -> int:
    t0_wall = time.time()

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=MINIO_USER,
        aws_secret_access_key=MINIO_PASS,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        region_name="us-east-1",
    )

    if COMPUTE_SEC > 0:
        time.sleep(COMPUTE_SEC)

    payload = b"\x00" * PAYLOAD_BYTES

    t1_wall = time.time()
    s3.put_object(Bucket=BUCKET, Key=OBJECT, Body=payload)
    t1p_wall = time.time()

    emit(
        "producer",
        pod=os.environ.get("HOSTNAME", "?"),
        node=os.environ.get("NODE_NAME", "?"),
        t0_wall=t0_wall,
        t1_wall=t1_wall,
        t1p_wall=t1p_wall,
        bytes=PAYLOAD_BYTES,
        bucket=BUCKET,
        object=OBJECT,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
