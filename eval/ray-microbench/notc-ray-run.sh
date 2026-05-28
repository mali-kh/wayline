#!/usr/bin/env bash
# Run the Ray E0 microbench on the unshaped LAN (no-tc), automatically,
# once the MCMT no-tc sweep has finished and the cluster is idle.
# Ray pins head->anrg-3, worker->anrg-6 (the former 50Mbit bottleneck pair),
# so it MUST NOT overlap the MCMT sweep that uses those nodes.
set -uo pipefail
REPO=/home/anrg/wayline
RAY="$REPO/eval/ray-microbench"
OUT="$RAY/ray-e0-notc.csv"

echo "[$(date '+%F %T')] waiting for MCMT sweep (notc-sweep.sh) to finish..."
while pgrep -f notc-sweep.sh >/dev/null 2>&1; do sleep 30; done
echo "[$(date '+%F %T')] sweep finished. waiting for cluster idle..."
for i in $(seq 1 60); do
  n=$(kubectl get pods -n wl-system -l wl-odag --field-selector=status.phase!=Succeeded,status.phase!=Failed --no-headers 2>/dev/null | wc -l)
  m=$(kubectl -n argo get pods --no-headers 2>/dev/null | grep -ivE 'argo-server|workflow-controller|httpbin' | grep -vcE 'Succeeded|Completed')
  [ "${n:-0}" = 0 ] && [ "${m:-0}" = 0 ] && { echo "[idle ok]"; break; }
  sleep 15
done

echo "[$(date '+%F %T')] deploying ray-bench cluster (head=anrg-3, worker=anrg-6)..."
kubectl delete ns ray-bench --ignore-not-found --wait=true >/dev/null 2>&1
kubectl apply -f "$RAY/ray-cluster.yml"
if ! kubectl -n ray-bench wait --for=condition=Ready pod/ray-head pod/ray-worker --timeout=360s; then
  echo "[ERROR] ray pods not ready; dumping state"; kubectl -n ray-bench get pods -o wide
  echo "RAY NOTC FAILED (pods not ready)"; exit 1
fi

echo "[$(date '+%F %T')] copying microbench + running (reps=20)..."
kubectl -n ray-bench cp "$RAY/microbench.py" ray-head:/tmp/microbench.py
kubectl -n ray-bench exec ray-head -- python3 /tmp/microbench.py --reps 20 --out /tmp/ray-e0-notc.csv
kubectl -n ray-bench cp ray-head:/tmp/ray-e0-notc.csv "$OUT"

echo "[$(date '+%F %T')] harvested -> $OUT"
column -t -s, "$OUT" 2>/dev/null || cat "$OUT"

echo "[$(date '+%F %T')] tearing down ray-bench..."
kubectl delete ns ray-bench --wait=false >/dev/null 2>&1
echo "RAY NOTC DONE"
