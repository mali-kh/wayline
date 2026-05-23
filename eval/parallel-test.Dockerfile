FROM python:3.11-slim
WORKDIR /app
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/parallel-test-task.py task.py
CMD ["python", "task.py"]
