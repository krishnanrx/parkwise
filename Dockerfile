FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv python3-opencv libglib2.0-0 libsm6 libxrender1 libxext6 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip3 install --upgrade pip && \
    pip3 install ultralytics onnxruntime-gpu onnx opencv-python-headless easyocr pyyaml fastapi uvicorn numpy pillow

EXPOSE 8000
CMD ["uvicorn", "src.fastapi_server:app", "--host", "0.0.0.0", "--port", "8000"]


