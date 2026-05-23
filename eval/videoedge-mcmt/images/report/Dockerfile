# vemcmt-report: pure Python aggregation.
FROM python:3.12-slim

WORKDIR /app

COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/videoedge-mcmt/lib ./lib
COPY eval/videoedge-mcmt/dsf/tasks/report_task.py   ./dsf_report_task.py
COPY eval/videoedge-mcmt/argo/tasks/report_task.py  ./argo_report_task.py

CMD ["python", "dsf_report_task.py"]
