# vemcmt-cross-camera-match: numpy + scipy for Hungarian + union-find. CPU.
FROM python:3.12-slim

RUN pip install --no-cache-dir numpy==2.1.* scipy==1.14.*

WORKDIR /app

COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/videoedge-mcmt/lib ./lib
COPY eval/videoedge-mcmt/dsf/tasks/cross_camera_match_task.py   ./dsf_cross_camera_match_task.py
COPY eval/videoedge-mcmt/argo/tasks/cross_camera_match_task.py  ./argo_cross_camera_match_task.py

CMD ["python", "dsf_cross_camera_match_task.py"]
