# Build from the repo root:
#   docker build -f eval/two-hop/dsf/producer/Dockerfile \
#     -t 192.168.1.163:5000/two-hop-dsf-producer:latest .
FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/wl ./wl
COPY eval/two-hop/dsf/producer/task.py .
CMD ["python", "-u", "task.py"]
