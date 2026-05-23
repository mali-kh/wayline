# Build from the repo root:
#   docker build -f examples/rag-refresh-odag/tasks/chunk/Dockerfile \
#     -t <REGISTRY>/wl-rag-chunk:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/wl ./wl
COPY examples/rag-refresh-odag/tasks/chunk/task.py .
CMD ["python", "task.py"]
