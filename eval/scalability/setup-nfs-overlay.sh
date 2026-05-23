#!/usr/bin/env bash
# Enable NFS overlay for scalability evaluation.
# Mounts NFS over /data/dsf-outputs on all worker nodes, then restarts
# data-agents so they see the NFS mount. After this, the normal file
# transport writes go through NFS instead of local disk.
#
# Usage: ./eval/scalability/setup-nfs-overlay.sh

set -euo pipefail
cd "$(dirname "$0")/../.."

echo "[nfs] Ensuring NFS server is running..."
kubectl apply -f eval/scalability/nfs-server.yml
sleep 5
kubectl wait --for=condition=ready pod -l app=nfs-server -n dsf-system --timeout=60s

echo "[nfs] Deploying NFS overlay on all nodes..."
kubectl apply -f eval/scalability/nfs-overlay-daemonset.yml
sleep 15

echo "[nfs] Checking mounts..."
NFS_READY=$(kubectl get pods -n dsf-system -l app=nfs-overlay --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
echo "[nfs] $NFS_READY NFS overlay pods running"

echo "[nfs] Restarting data-agents to see NFS mount..."
kubectl rollout restart daemonset/data-agent -n dsf-system
sleep 10
kubectl wait --for=condition=ready pod -l app=data-agent -n dsf-system --timeout=60s

echo "[nfs] NFS overlay active. All /data/dsf-outputs I/O now goes through NFS."
echo "[nfs] To tear down: ./eval/scalability/teardown-nfs-overlay.sh"
