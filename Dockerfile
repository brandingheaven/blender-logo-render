FROM nvidia/cuda:11.8.0-base-ubuntu20.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget curl bzip2 python3 python3-pip git \
    libx11-6 libxi6 libxxf86vm1 libxcursor1 \
    libxrandr2 libxinerama1 libgl1-mesa-glx libegl1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Install Blender
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz \
    && tar -xJf blender-3.6.0-linux-x64.tar.xz -C /opt \
    && ln -s /opt/blender-3.6.0-linux-x64/blender /usr/local/bin/blender \
    && rm blender-3.6.0-linux-x64.tar.xz

# Install Python dependencies
RUN pip3 install fastapi uvicorn python-multipart aiofiles

# Create workspace directory
WORKDIR /workspace

# Copy application files
COPY render_logo.py /workspace/render_logo.py
COPY server.py /workspace/server.py

# Create output directory
RUN mkdir -p /workspace/output

# Expose port for API
EXPOSE 8000

# Start the API server
CMD ["python3", "server.py"]
