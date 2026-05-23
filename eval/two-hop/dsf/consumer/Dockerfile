# Build from the repo root:
#   docker build -f eval/two-hop/dsf/consumer/Dockerfile \
#     -t 192.168.1.163:5000/two-hop-dsf-consumer:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/two-hop/dsf/consumer/task.py .
CMD ["python", "-u", "task.py"]
