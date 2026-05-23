# Paired producer+consumer Jobs for one E0 run of the shared-FS (RWX NFS)
# baseline. Both mount the same RWX PVC at /shared; inline python scripts
# come from the e0-nfs-scripts ConfigMap. Same K8s primitives as the MinIO
# and DSF variants; no Argo controller in the loop.
apiVersion: batch/v1
kind: Job
metadata:
  name: ${E0_RUN_NAME}-producer
  namespace: e0-bench
  labels: { app: two-hop, component: producer, e0-run: ${E0_RUN_NAME} }
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 600
  template:
    metadata:
      labels: { app: two-hop, component: producer, e0-run: ${E0_RUN_NAME} }
    spec:
      restartPolicy: Never
      nodeSelector: { kubernetes.io/hostname: ${E0_PRODUCER_NODE} }
      containers:
        - name: producer
          image: python:3.11-slim
          imagePullPolicy: IfNotPresent
          command: ["python3", "/scripts/producer.py"]
          env:
            - { name: E0_BYTES,   value: "${E0_BYTES}" }
            - { name: E0_COMPUTE, value: "5.0" }
            - { name: E0_PATH,    value: "/shared/${E0_RUN_NAME}/payload" }
            - { name: NODE_NAME,  valueFrom: { fieldRef: { fieldPath: spec.nodeName } } }
          volumeMounts:
            - { name: shared,  mountPath: /shared }
            - { name: scripts, mountPath: /scripts }
          resources:
            requests: { cpu: "200m", memory: "768Mi" }
            limits:   { cpu: "1",    memory: "2Gi" }
      volumes:
        - { name: shared,  persistentVolumeClaim: { claimName: e0-nfs-pvc } }
        - { name: scripts, configMap: { name: e0-nfs-scripts } }
---
apiVersion: batch/v1
kind: Job
metadata:
  name: ${E0_RUN_NAME}-consumer
  namespace: e0-bench
  labels: { app: two-hop, component: consumer, e0-run: ${E0_RUN_NAME} }
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 600
  template:
    metadata:
      labels: { app: two-hop, component: consumer, e0-run: ${E0_RUN_NAME} }
    spec:
      restartPolicy: Never
      nodeSelector: { kubernetes.io/hostname: ${E0_CONSUMER_NODE} }
      containers:
        - name: consumer
          image: python:3.11-slim
          imagePullPolicy: IfNotPresent
          command: ["python3", "/scripts/consumer.py"]
          env:
            - { name: E0_BYTES,  value: "${E0_BYTES}" }
            - { name: E0_PATH,   value: "/shared/${E0_RUN_NAME}/payload" }
            - { name: NODE_NAME, valueFrom: { fieldRef: { fieldPath: spec.nodeName } } }
          volumeMounts:
            - { name: shared,  mountPath: /shared }
            - { name: scripts, mountPath: /scripts }
          resources:
            requests: { cpu: "200m", memory: "768Mi" }
            limits:   { cpu: "1",    memory: "2Gi" }
      volumes:
        - { name: shared,  persistentVolumeClaim: { claimName: e0-nfs-pvc } }
        - { name: scripts, configMap: { name: e0-nfs-scripts } }
