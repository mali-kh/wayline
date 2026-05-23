#!/usr/bin/env bash
# Remove NFS overlay and restore local storage.
# Unmounts NFS from /data/dsf-outputs on all worker nodes,
# then restarts data-agents to use local disk again.
#
# Usage: ./eval/scalability/teardown-nfs-overlay.sh

set -euo pipefail
cd "$(dirname "$0")/../.."

echo "[nfs] Deleting NFS overlay DaemonSet..."
kubectl delete daemonset nfs-overlay -n dsf-system --ignore-not-found

echo "[nfs] Unmounting NFS on all nodes (if still mounted)..."
# The DaemonSet deletion kills the pods, but the mount may persist.
# Use a one-shot job to unmount on each node.
for node in $(kubectl get nodes -o name --no-headers | sed 's/node\///'); do
    kubectl run "nfs-umount-${node}" -n dsf-system --rm -i --restart=Never \
        --image=alpine:3.19 --overrides="{
            \"spec\": {
                \"nodeName\": \"$node\",
                \"containers\": [{
                    \"name\": \"umount\",
                    \"image\": \"alpine:3.19\",
                    \"securityContext\": {\"privileged\": true},
                    \"command\": [\"sh\", \"-c\", \"umount /host-root/data/dsf-outputs 2>/dev/null; echo done\"],
                    \"volumeMounts\": [{\"name\": \"hr\", \"mountPath\": \"/host-root\", \"mountPropagation\": \"Bidirectional\"}]
                }],
                \"volumes\": [{\"name\": \"hr\", \"hostPath\": {\"path\": \"/\"}}]
            }
        }" 2>/dev/null || true
done

echo "[nfs] Restarting data-agents to use local storage..."
kubectl rollout restart daemonset/data-agent -n dsf-system
sleep 10

echo "[nfs] NFS overlay removed. /data/dsf-outputs is back on local disk."
