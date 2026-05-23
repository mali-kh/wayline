# Build from the repo root:
#   docker build -f examples/dag-pipeline/tasks/output/Dockerfile -t dag-pipeline-output:latest .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pyzmq
COPY sdk/python/wl ./wl
COPY examples/dag-pipeline/tasks/output/task.py .
CMD ["python", "task.py"]
