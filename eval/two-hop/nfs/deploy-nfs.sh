#!/usr/bin/env bash
# Deploy a central NFS server (pinned to anrg-9, same node as the MinIO
# baseline) + an RWX PV/PVC in e0-bench, plus a ConfigMap with the
# producer/consumer scripts. This is the "shared filesystem (RWX PVC)"
# baseline the ATC reviewers asked for.
set -euo pipefail
NS=e0-bench

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: { name: e0-nfs, namespace: e0-bench, labels: { app: e0-nfs } }
spec:
  replicas: 1
  selector: { matchLabels: { app: e0-nfs } }
  template:
    metadata: { labels: { app: e0-nfs } }
    spec:
      nodeName: anrg-9
      tolerations: [{operator: Exists}]
      containers:
        - name: nfs
          image: itsthenetwork/nfs-server-alpine:12
          securityContext: { privileged: true }
          env:
            - { name: SHARED_DIRECTORY, value: /nfsshare }
          ports: [{ containerPort: 2049 }]
          volumeMounts: [{ name: store, mountPath: /nfsshare }]
      volumes:
        - name: store
          hostPath: { path: /var/lib/e0-nfs, type: DirectoryOrCreate }
---
apiVersion: v1
kind: Service
metadata: { name: e0-nfs, namespace: e0-bench }
spec:
  selector: { app: e0-nfs }
  ports: [{ port: 2049, targetPort: 2049 }]
YAML

echo "waiting for NFS server pod..."
kubectl -n "$NS" rollout status deploy/e0-nfs --timeout=120s
NFSIP=$(kubectl -n "$NS" get svc e0-nfs -o jsonpath='{.spec.clusterIP}')
echo "NFS ClusterIP=$NFSIP"

# PV/PVC (RWX). kubelet mounts the NFS export at the node; ClusterIP is
# routable from every node via kube-proxy.
kubectl apply -f - <<YAML
apiVersion: v1
kind: PersistentVolume
metadata: { name: e0-nfs-pv }
spec:
  capacity: { storage: 20Gi }
  accessModes: [ReadWriteMany]
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  mountOptions: [nfsvers=4.1, hard, timeo=600, actimeo=0, lookupcache=none]
  nfs: { server: "$NFSIP", path: "/" }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: e0-nfs-pvc, namespace: e0-bench }
spec:
  accessModes: [ReadWriteMany]
  storageClassName: ""
  volumeName: e0-nfs-pv
  resources: { requests: { storage: 20Gi } }
YAML

# Producer/consumer scripts (inline python; no custom image needed).
kubectl -n "$NS" create configmap e0-nfs-scripts \
  --from-file=producer.py="$(dirname "$0")/producer.py" \
  --from-file=consumer.py="$(dirname "$0")/consumer.py" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NS" get pvc e0-nfs-pvc
echo "NFS baseline deployed."
