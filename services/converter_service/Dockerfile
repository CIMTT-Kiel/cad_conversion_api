# Dockerfile for CAD Conversion Service
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libglu1-mesa \
    libxcursor1 \
    libxinerama1 \
    libxft2 \
    libxrender1 \
    libxrandr2 \
    libxi6 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app




# Copy application code and change ownership
COPY . .
# Install dependencies
RUN uv sync 
RUN chown -R appuser:appuser /app

# Create directories for temporary files
RUN mkdir -p /tmp/cad_converter && \
    chown -R appuser:appuser /tmp/cad_converter

# Switch to non-root user
USER appuser


# Expose port
EXPOSE 8000

# Start application
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]