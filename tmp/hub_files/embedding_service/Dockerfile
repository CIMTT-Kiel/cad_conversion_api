# Dockerfile for VecSet Service with GPU support
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# # Set working directory
# WORKDIR /app

# # Copy application code and change ownership
# COPY . .

# # Create virtual environment and install dependencies
# RUN uv sync

# RUN chown -R appuser:appuser /app

# # Create model directory and set permissions
# RUN mkdir -p /models && \
#     chown -R appuser:appuser /models

# # Create directories for temporary files
# RUN mkdir -p /tmp/vecset_conversion && \
#     chown -R appuser:appuser /tmp/vecset_conversion

# # Switch to non-root user
# USER appuser



# # Expose port
# EXPOSE 8000

# # Start application
# CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]