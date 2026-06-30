# isolate sandbox Docker image
# Builds isolate from source; container must run with --privileged for namespace/cgroup ops
# Exposes FastAPI HTTP API on port 8899 for ai-agent-lite to call

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# Switch to Tsinghua mirror for reliable apt in China
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i 's|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources

# Build dependencies for isolate + language toolchains + Python web server
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Isolate build dependencies
    build-essential \
    pkg-config \
    libcap-dev \
    libsystemd-dev \
    libseccomp-dev \
    git \
    ca-certificates \
    # Language toolchains
    gcc \
    g++ \
    python3 \
    python3-pip \
    openjdk-21-jdk-headless \
    # Runtime
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python web framework for API server
RUN pip3 install --break-system-packages --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn==0.34.0

# Build isolate from source
WORKDIR /tmp/isolate-build
RUN git clone --depth 1 https://github.com/ioi/isolate.git . && \
    make install && \
    cd / && rm -rf /tmp/isolate-build

# Ensure isolate binary is available
RUN which isolate

# Create sandbox working directory
RUN mkdir -p /var/local/lib/isolate && chmod 755 /var/local/lib/isolate

# Create isolate system user (required by isolate sandbox)
RUN useradd -r -m -s /bin/bash isolate && \
    usermod -aG sudo isolate && \
    echo 'isolate ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    # Add subordinate UID/GID mapping for isolate (user namespaces)
    echo 'isolate:100000:65536' >> /etc/subuid && \
    echo 'isolate:100000:65536' >> /etc/subgid

# Create admin user for running isolate operations
RUN useradd -m -s /bin/bash sandbox && \
    usermod -aG sudo sandbox && \
    echo 'sandbox ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

WORKDIR /workspace

# Copy sandbox module and API server
COPY enums.py /workspace/enums.py
COPY sandbox.py /workspace/sandbox.py
COPY api_server.py /workspace/api_server.py

# isolate runs as root for cgroup/namespace init
EXPOSE 8899

CMD ["python3", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8899"]
