apiVersion: dsf.io/v1
kind: ODAGTemplate
metadata:
  name: ${E0_TEMPLATE_NAME}
  namespace: dsf-system
spec:
  description: "E0 two-hop microbenchmark — ${E0_COLOCATION}, ${E0_PAYLOAD_LABEL}."
  scheduler: random
  profiling:
    enabled: false
  retention:
    maxRuns: 25
    data:
      policy: immediate
  defaults:
    runtime: 6
    dataSize: "${E0_PAYLOAD_LABEL}"
  tasks:
    - name: producer
      image: 192.168.1.163:5000/two-hop-dsf-producer:latest
      command: ["python", "-u", "task.py"]
      dependencies: []
      dataSize: "${E0_PAYLOAD_LABEL}"
      runtime: 6
      resources:
        cpu: "200m"
        memory: "768Mi"
      env:
        - { name: DSF_E0_BYTES,   value: "${E0_BYTES}" }
        - { name: DSF_E0_COMPUTE, value: "5.0" }
      constraints:
        nodeNames: [${E0_PRODUCER_NODE}]
    - name: consumer
      image: 192.168.1.163:5000/two-hop-dsf-consumer:latest
      command: ["python", "-u", "task.py"]
      dependencies: [producer]
      dataSize: "1KB"
      runtime: 2
      resources:
        cpu: "200m"
        memory: "768Mi"
      env:
        - { name: DSF_E0_BYTES, value: "${E0_BYTES}" }
      constraints:
        nodeNames: [${E0_CONSUMER_NODE}]
