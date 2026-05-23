# Build from the repo root:
#   docker build -f eval/two-hop/minio/consumer/Dockerfile \
#     -t 192.168.1.163:5000/two-hop-minio-consumer:latest .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir boto3==1.34.* botocore==1.34.*
COPY eval/two-hop/minio/consumer/task.py .
CMD ["python", "-u", "task.py"]
