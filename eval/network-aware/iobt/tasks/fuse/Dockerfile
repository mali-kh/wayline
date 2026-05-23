# Build from the repo root:
#   docker build -f examples/iobt-mission-snapshot-odag/tasks/fuse/Dockerfile \
#     -t <REGISTRY>/dsf-iobt-fuse:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY examples/iobt-mission-snapshot-odag/tasks/fuse/task.py .
CMD ["python", "task.py"]
