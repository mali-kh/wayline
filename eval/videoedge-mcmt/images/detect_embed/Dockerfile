# vemcmt-detect-embed: OpenVINO 2024.x runtime + Intel iGPU plugin libs.
# YOLOv8n + OSNet-x0_25 IR files baked at /models.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        libva-drm2 libva2 \
        intel-media-va-driver-non-free \
        intel-opencl-icd ocl-icd-libopencl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
        openvino==2024.4.* \
        opencv-python-headless==4.10.* \
        "numpy>=1.26,<2.1"

WORKDIR /app

COPY sdk/python/dsf_sdk ./dsf_sdk
COPY eval/videoedge-mcmt/lib ./lib
COPY eval/videoedge-mcmt/dsf/tasks/detect_embed_task.py   ./dsf_detect_embed_task.py
COPY eval/videoedge-mcmt/argo/tasks/detect_embed_task.py  ./argo_detect_embed_task.py

# Models baked at known paths.
COPY eval/videoedge-mcmt/models/yolov8n.xml /models/yolov8n.xml
COPY eval/videoedge-mcmt/models/yolov8n.bin /models/yolov8n.bin
COPY eval/videoedge-mcmt/models/osnet_x0_25.xml /models/osnet_x0_25.xml
COPY eval/videoedge-mcmt/models/osnet_x0_25.bin /models/osnet_x0_25.bin

CMD ["python3", "dsf_detect_embed_task.py"]
