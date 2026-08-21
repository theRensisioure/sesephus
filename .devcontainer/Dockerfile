# Sesefus dev image: Zig 0.16 + Python 3.11 + Node 20 + Rust (optional dashboard)
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG ZIG_VERSION=0.16.0
ARG DEBIAN_FRONTEND=noninteractive

# Native deps for Zig builds, Python audio stack, and Rust dashboard
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        jq \
        libasound2-dev \
        libportaudio2 \
        pkg-config \
        unzip \
        xz-utils \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Zig (matches core/sesephus build.zig expectations)
RUN curl -fsSL "https://ziglang.org/download/${ZIG_VERSION}/zig-linux-x86_64-${ZIG_VERSION}.tar.xz" \
        -o /tmp/zig.tar.xz \
    && tar -xJf /tmp/zig.tar.xz -C /usr/local \
    && ln -sf "/usr/local/zig-linux-x86_64-${ZIG_VERSION}/zig" /usr/local/bin/zig \
    && rm /tmp/zig.tar.xz

# Node.js 20 LTS (dashboard/ui)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Rust toolchain (dashboard/aether-dashboard-v2)
USER vscode
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/home/vscode/.cargo/bin:${PATH}"
USER root

WORKDIR /workspaces/sesefus