# Build from the repo root:
#   docker build -f examples/dag-pipeline/tasks/generate/Dockerfile -t dag-pipeline-generate:latest .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pyzmq
COPY sdk/python/wl ./wl
COPY examples/dag-pipeline/tasks/generate/task.py .
CMD ["python", "task.py"]
