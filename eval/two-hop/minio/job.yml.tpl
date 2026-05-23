# Two paired Jobs (producer + consumer) for one E0 run of the MinIO baseline.
# Both are created together — the consumer polls until the object exists.
# Same K8s primitives, no Argo controller in the loop.
apiVersion: batch/v1
kind: Job
metadata:
  name: ${E0_RUN_NAME}-producer
  namespace: e0-bench
  labels:
    app: two-hop
    component: producer
    e0-run: ${E0_RUN_NAME}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 600
  template:
    metadata:
      labels:
        app: two-hop
        component: producer
        e0-run: ${E0_RUN_NAME}
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/hostname: ${E0_PRODUCER_NODE}
      containers:
        - name: producer
          image: 192.168.1.163:5000/two-hop-minio-producer:latest
          imagePullPolicy: Always
          env:
            - { name: E0_BYTES,      value: "${E0_BYTES}" }
            - { name: E0_COMPUTE,    value: "5.0" }
            - { name: E0_MINIO_URL,  value: "http://minio.e0-bench.svc.cluster.local:9000" }
            - { name: E0_MINIO_USER, value: "e0admin" }
            - { name: E0_MINIO_PASS, value: "e0adminpw" }
            - { name: E0_BUCKET,     value: "e0-bench" }
            - { name: E0_OBJECT,     value: "${E0_RUN_NAME}/payload" }
            - { name: NODE_NAME,     valueFrom: { fieldRef: { fieldPath: spec.nodeName } } }
          resources:
            requests: { cpu: "200m", memory: "768Mi" }
            limits:   { cpu: "1",    memory: "2Gi" }
---
apiVersion: batch/v1
kind: Job
metadata:
  name: ${E0_RUN_NAME}-consumer
  namespace: e0-bench
  labels:
    app: two-hop
    component: consumer
    e0-run: ${E0_RUN_NAME}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 600
  template:
    metadata:
      labels:
        app: two-hop
        component: consumer
        e0-run: ${E0_RUN_NAME}
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/hostname: ${E0_CONSUMER_NODE}
      containers:
        - name: consumer
          image: 192.168.1.163:5000/two-hop-minio-consumer:latest
          imagePullPolicy: Always
          env:
            - { name: E0_BYTES,      value: "${E0_BYTES}" }
            - { name: E0_MINIO_URL,  value: "http://minio.e0-bench.svc.cluster.local:9000" }
            - { name: E0_MINIO_USER, value: "e0admin" }
            - { name: E0_MINIO_PASS, value: "e0adminpw" }
            - { name: E0_BUCKET,     value: "e0-bench" }
            - { name: E0_OBJECT,     value: "${E0_RUN_NAME}/payload" }
            - { name: E0_POLL_S,     value: "0.025" }
            - { name: E0_DEADLINE_S, value: "300" }
            - { name: NODE_NAME,     valueFrom: { fieldRef: { fieldPath: spec.nodeName } } }
          resources:
            requests: { cpu: "200m", memory: "768Mi" }
            limits:   { cpu: "1",    memory: "2Gi" }
