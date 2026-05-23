#!/usr/bin/env bash
#
# Remove all ODAG/CDAG runs + their task pods + per-run on-disk data.
# Leaves controllers, data-agents, ui-server, mqtt-broker, nfs-server,
# and any tc-setup pods intact.
#
# Run this before starting the benchmark sweep, and between sweeps if
# you want a fully-clean cluster state. It is safe to re-run.
set -euo pipefail

NS=${NS:-dsf-system}

echo "[cleanup] deleting all ODAG runs in $NS..."
kubectl delete odags.dsf.io --all -n "$NS" --ignore-not-found --wait=false >/dev/null 2>&1 || true

echo "[cleanup] deleting all CDAG runs in $NS..."
kubectl delete cdags.dsf.io --all -n "$NS" --ignore-not-found --wait=false >/dev/null 2>&1 || true

echo "[cleanup] deleting task pods (labels: dsf-odag, dsf-cdag)..."
kubectl delete pods -n "$NS" -l dsf-odag --ignore-not-found --wait=false >/dev/null 2>&1 || true
kubectl delete pods -n "$NS" -l dsf-cdag --ignore-not-found --wait=false >/dev/null 2>&1 || true

echo "[cleanup] waiting up to 60s for task pods to drain..."
for _ in $(seq 1 30); do
  remaining=$(kubectl get pods -n "$NS" -l 'dsf-odag,!app' -o name 2>/dev/null | wc -l)
  remaining2=$(kubectl get pods -n "$NS" -l 'dsf-cdag,!app' -o name 2>/dev/null | wc -l)
  [[ "$remaining" == "0" && "$remaining2" == "0" ]] && break
  sleep 2
done

echo "[cleanup] asking data-agents to purge /data/dsf-outputs subdirs..."
# Each data-agent serves DELETE on /data/<run-name>; we enumerate run
# directories and fire DELETEs. Use its pod IP via kubectl exec to
# list-and-delete inside the pod (no network hop).
for pod in $(kubectl get pods -n "$NS" -l app=data-agent -o name 2>/dev/null); do
  kubectl exec -n "$NS" "$pod" -- sh -c '
    cd /data/dsf-outputs 2>/dev/null || exit 0
    for d in */; do rm -rf "$d" 2>/dev/null; done
    echo "$(hostname): cleaned"
  ' 2>/dev/null || true
done

echo "[cleanup] done."
kubectl get odags.dsf.io -n "$NS" --no-headers 2>/dev/null | wc -l | xargs -I{} echo "[cleanup] remaining ODAGs: {}"
kubectl get cdags.dsf.io -n "$NS" --no-headers 2>/dev/null | wc -l | xargs -I{} echo "[cleanup] remaining CDAGs: {}"
kubectl get pods -n "$NS" -l 'dsf-odag,!app' --no-headers 2>/dev/null | wc -l | xargs -I{} echo "[cleanup] remaining odag pods: {}"
