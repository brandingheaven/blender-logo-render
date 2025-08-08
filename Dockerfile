FROM ubuntu:20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget curl bzip2 python3 python3-pip git \
    libx11-6 libxi6 libxxf86vm1 libxcursor1 \
    libxrandr2 libxinerama1 libgl1-mesa-glx libegl1-mesa \
    libglu1-mesa libxss1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Blender for ARM64 (or use x86_64 with emulation)
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz \
    && tar -xJf blender-3.6.0-linux-x64.tar.xz -C /opt \
    && ln -s /opt/blender-3.6.0-linux-x64/blender /usr/local/bin/blender \
    && rm blender-3.6.0-linux-x64.tar.xz

# Install Python dependencies
COPY requirements.txt /workspace/requirements.txt
RUN pip3 install -r /workspace/requirements.txt

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
