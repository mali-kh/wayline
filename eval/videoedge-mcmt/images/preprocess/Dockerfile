# vemcmt-preprocess: OpenCV resize + letterbox. CPU only.
FROM python:3.12-slim

RUN pip install --no-cache-dir opencv-python-headless==4.10.* numpy==2.1.*

WORKDIR /app

COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/videoedge-mcmt/lib ./lib
COPY eval/videoedge-mcmt/dsf/tasks/preprocess_task.py   ./dsf_preprocess_task.py
COPY eval/videoedge-mcmt/argo/tasks/preprocess_task.py  ./argo_preprocess_task.py

CMD ["python", "dsf_preprocess_task.py"]
