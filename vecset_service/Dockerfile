FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip build-essential \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip3 install uv

# Copy pyproject.toml
COPY pyproject.toml .

# Create venv and install dependencies via uv
RUN python3 -m venv .venv && \
    .venv/bin/uv install

# Copy source code
COPY . .

EXPOSE 8001

CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

