# Build from the repo root:
#   docker build -f examples/multi-input-odag/tasks/merge/Dockerfile -t 192.168.1.163:5000/multi-input-merge:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/wl ./wl
COPY examples/multi-input-odag/tasks/merge/task.py .
CMD ["python", "task.py"]
