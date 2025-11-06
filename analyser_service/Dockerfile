FROM python:3.11-slim-bookworm

LABEL description="Lightweight CAD analyser service with FreeCAD headless"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies 
RUN apt-get update && apt-get install -y --no-install-recommends \
    freecad-python3 \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set FreeCAD Python path
ENV PYTHONPATH="/usr/lib/freecad-python3/lib:/usr/lib/freecad/lib:$PYTHONPATH"

# Set working directory
WORKDIR /app

# Copy application code and change ownership
COPY . .

# Install dependencies using uv
RUN uv sync
RUN chown -R appuser:appuser /app

# Create directories for temporary files
RUN mkdir -p /tmp/cad_analyser && \
    chown -R appuser:appuser /tmp/cad_analyser

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Start application
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]