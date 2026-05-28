# vemcmt-track: numpy + scipy for IoU-greedy + Hungarian. CPU.
FROM python:3.12-slim

RUN pip install --no-cache-dir numpy==2.1.* scipy==1.14.*

WORKDIR /app

COPY sdk/python/wl ./wl
COPY eval/videoedge-mcmt/lib ./lib
COPY eval/videoedge-mcmt/dsf/tasks/track_task.py   ./dsf_track_task.py
COPY eval/videoedge-mcmt/argo/tasks/track_task.py  ./argo_track_task.py

CMD ["python", "dsf_track_task.py"]
