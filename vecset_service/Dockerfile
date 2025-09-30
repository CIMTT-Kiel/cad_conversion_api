FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip build-essential \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

# Copy code
COPY . .

# Install dependencies via uv inside venv
RUN uv sync

EXPOSE 8001

CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

