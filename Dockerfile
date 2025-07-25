FROM nvidia/cuda:11.8.0-base-ubuntu20.04

RUN apt-get update && apt-get install -y \
    wget curl bzip2 python3 python3-pip git \
    libx11-6 libxi6 libxxf86vm1 libxcursor1 \
    libxrandr2 libxinerama1 libgl1-mesa-glx libegl1-mesa \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz \
    && tar -xJf blender-3.6.0-linux-x64.tar.xz -C /opt \
    && ln -s /opt/blender-3.6.0-linux-x64/blender /usr/local/bin/blender

COPY render_logo.py /workspace/render_logo.py
WORKDIR /workspace

CMD ["blender", "-b", "-P", "/workspace/render_logo.py", "--", "/workspace/logo.png"]
