FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libxml2-dev \
        libxslt1-dev \
        liblzma-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements/docker-build.txt /tmp/docker-build.txt

RUN python3 -m pip install --upgrade pip setuptools wheel
RUN python3 -m pip install -r /tmp/docker-build.txt

COPY . .

RUN python3 -m pip install -e core --no-deps
RUN python3 -m pip install -e tools --no-deps

ENV PYTHONPATH=/workspace/core:/workspace/exports

CMD ["/bin/bash"]
