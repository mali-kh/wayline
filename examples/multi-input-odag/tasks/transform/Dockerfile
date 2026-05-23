# Build from the repo root:
#   docker build -f examples/multi-input-odag/tasks/transform/Dockerfile -t 192.168.1.163:5000/multi-input-transform:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/wl ./wl
COPY examples/multi-input-odag/tasks/transform/task.py .
CMD ["python", "task.py"]
