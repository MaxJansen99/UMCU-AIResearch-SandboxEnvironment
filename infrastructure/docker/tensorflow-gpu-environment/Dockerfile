FROM nvidia/cuda:12.9.2-cudnn-devel-ubuntu24.04

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  libgl1 \
  && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
  jupyter \
  papermill \
  pandas \
  numpy \
  matplotlib \
  tensorflow \
  tensorboard

COPY . .

CMD ["/bin/sh", "-lc", "if [ -f main.ipynb ]; then mkdir -p G_Output/notebooks && papermill main.ipynb G_Output/notebooks/main.ipynb -k python3 --log-output --no-progress-bar; elif [ -f main.py ]; then python3 main.py; else exit 1; fi"]
