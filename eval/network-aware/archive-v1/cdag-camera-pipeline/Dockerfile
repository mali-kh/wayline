# Build from the repo root:
#   docker build -f eval/network-aware/cdag-camera-pipeline/Dockerfile -t 192.168.1.163:5000/camera-pipeline:latest .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pyzmq
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/network-aware/cdag-camera-pipeline/task.py .
CMD ["python", "task.py"]
