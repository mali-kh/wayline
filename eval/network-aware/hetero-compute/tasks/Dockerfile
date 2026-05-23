FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pyzmq
COPY sdk/python/dsf_sdk ./dsf_sdk
COPY examples/heterogeneous-compute/tasks/task.py .
CMD ["python", "task.py"]
