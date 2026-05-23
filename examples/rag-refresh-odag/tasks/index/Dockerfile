# Build from the repo root:
#   docker build -f examples/rag-refresh-odag/tasks/index/Dockerfile \
#     -t <REGISTRY>/wl-rag-index:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/wl ./wl
COPY examples/rag-refresh-odag/tasks/index/task.py .
CMD ["python", "task.py"]
