"""
E0 two-hop microbenchmark — MinIO baseline consumer.

Both Jobs are created at the same time (the *pre-staged* variant). The
consumer polls HEAD on the expected object key, then GETs once it
appears. Polling is at 25 ms intervals so the contribution of polling
to the measured t3..t4 interval is bounded.

Reads:
    E0_BYTES        : expected payload size (for sanity check)
    E0_MINIO_URL
    E0_MINIO_USER
    E0_MINIO_PASS
    E0_BUCKET
    E0_OBJECT
    E0_POLL_S       : poll interval seconds (default 0.025)
    E0_DEADLINE_S   : give up after this many seconds (default 300)

Emits two timestamps:
    t3_wall: just before the first poll (consumer enters "waiting on
             data" — comparable to DSF consumer entering recv_raw)
    t4_wall: right after the object is fully downloaded
"""

import json
import os
import sys
import time

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def env_required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"missing env: {name}")
    return v


EXPECTED_BYTES = int(os.environ.get("E0_BYTES", "1048576"))
MINIO_URL      = env_required("E0_MINIO_URL")
MINIO_USER     = env_required("E0_MINIO_USER")
MINIO_PASS     = env_required("E0_MINIO_PASS")
BUCKET         = env_required("E0_BUCKET")
OBJECT         = env_required("E0_OBJECT")
POLL_S         = float(os.environ.get("E0_POLL_S", "0.025"))
DEADLINE_S     = float(os.environ.get("E0_DEADLINE_S", "300"))


def emit(role: str, **fields) -> None:
    record = {"role": role, **fields}
    sys.stdout.write("DSF_E0_TIMESTAMPS " + json.dumps(record) + "\n")
    sys.stdout.flush()


def main() -> int:
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=MINIO_USER,
        aws_secret_access_key=MINIO_PASS,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        region_name="us-east-1",
    )

    # t3 — consumer enters waiting-for-data state.
    t3_wall = time.time()
    deadline = t3_wall + DEADLINE_S

    # Poll HEAD until the object appears. This isolates poll-wait from
    # actual download cost.
    while time.time() < deadline:
        try:
            s3.head_object(Bucket=BUCKET, Key=OBJECT)
            break
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                time.sleep(POLL_S)
                continue
            raise

    # t_found — object now exists on the store.
    t_found_wall = time.time()

    # GET the object.
    resp = s3.get_object(Bucket=BUCKET, Key=OBJECT)
    data = resp["Body"].read()

    # t4 — full payload in memory.
    t4_wall = time.time()
    body_len = len(data)
    ok = (body_len == EXPECTED_BYTES)

    emit(
        "consumer",
        pod=os.environ.get("HOSTNAME", "?"),
        node=os.environ.get("NODE_NAME", "?"),
        t3_wall=t3_wall,
        t_found_wall=t_found_wall,
        t4_wall=t4_wall,
        bytes=body_len,
        expected_bytes=EXPECTED_BYTES,
        ok=ok,
        poll_s=POLL_S,
    )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
