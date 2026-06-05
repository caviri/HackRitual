FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install Python, pip, Node.js, npm, and essential tools for HTTP development
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    openssh-server \
    tmux \
    curl \
    git \
    sudo \
    iproute2 \
    ca-certificates \
    nano \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with UID/GID commonly used by VS Code (1000:1000)
RUN useradd -ms /bin/bash -u 1000 vscode 

# Configure SSH daemon and vscode sudo/password access for SSH login
RUN mkdir -p /run/sshd \
    && usermod -aG sudo vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode \
    && echo "vscode:vscode" | chpasswd \
    && sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# Set Python 3.12 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

# Switch to vscode user for CLI installations
USER vscode
WORKDIR /workspaces

# Configure npm to install global packages in user directory
RUN mkdir -p ~/.npm-global && npm config set prefix '~/.npm-global' && echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc

# Install Gemini CLI as vscode user
RUN npm install -g @google/gemini-cli

# Install Pi Coding Agent
RUN npm install -g @mariozechner/pi-coding-agent

# Install Claude CLI (as vscode user)
RUN curl -fsSL https://claude.ai/install.sh | bash

RUN curl -fsSL https://ampcode.com/install.sh | bash
