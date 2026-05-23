# Build from the repo root:
#   docker build -f eval/scalability/Dockerfile -t 192.168.1.163:5000/scalability-eval:latest .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pyzmq paho-mqtt
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/scalability/task.py .
COPY eval/scalability/odag-task.py .
CMD ["python", "task.py"]
