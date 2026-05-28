#!/usr/bin/env bash
# Build + push wl-native network-aware synthetic images from the Wayline repo root.
set -uo pipefail
cd /home/anrg/wayline
R=192.168.1.163:5000
build(){ # <dockerfile> <image>
  echo "[$(date +%T)] building $2 ..."
  if docker build -q -f "$1" -t "$R/$2:latest" . >/tmp/wlna-$2.log 2>&1; then
    docker push -q "$R/$2:latest" >/dev/null 2>&1 && echo "[$(date +%T)] $2 OK"
  else echo "[$(date +%T)] $2 FAILED"; tail -5 /tmp/wlna-$2.log; fi
}
build eval/network-aware/iobt/tasks/capture/Dockerfile     wl-iobt-capture
build eval/network-aware/iobt/tasks/preprocess/Dockerfile  wl-iobt-preprocess
build eval/network-aware/iobt/tasks/infer/Dockerfile       wl-iobt-infer
build eval/network-aware/iobt/tasks/fuse/Dockerfile        wl-iobt-fuse
build eval/network-aware/iobt/tasks/report/Dockerfile      wl-iobt-report
build eval/network-aware/hetero-compute/tasks/Dockerfile   wl-hetero-compute-task
build eval/network-aware/wide-pipeline-flex/tasks/Dockerfile wl-multi-odag-task
echo "[$(date +%T)] ALL NETWORK-AWARE IMAGE BUILDS DONE"
