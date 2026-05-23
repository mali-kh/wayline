# Build from the repo root:
#   docker build -f examples/iobt-mission-snapshot-odag/tasks/report/Dockerfile \
#     -t <REGISTRY>/dsf-iobt-report:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY examples/iobt-mission-snapshot-odag/tasks/report/task.py .
CMD ["python", "task.py"]
