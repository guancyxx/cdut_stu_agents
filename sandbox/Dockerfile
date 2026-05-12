# isolate sandbox Docker image
# Builds isolate from source; container must run with --privileged for namespace/cgroup ops

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# Build dependencies for isolate + language toolchains
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
    && rm -rf /var/lib/apt/lists/*

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

# isolate runs as root for cgroup/namespace init; non-root can use --run after --init
# The ai-agent-lite backend will invoke isolate CLI via this container
