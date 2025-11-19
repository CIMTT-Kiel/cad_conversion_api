# Dockerfile for VecSet Service with GPU support
FROM cimtthawk/embedding-service:latest

# Set working directory
WORKDIR /app

# Copy application code and change ownership
COPY . .

# Create virtual environment and install dependencies
RUN uv sync

RUN chown -R appuser:appuser /app

# Create model directory and set permissions
RUN mkdir -p /models && \
    chown -R appuser:appuser /models

# Create directories for temporary files
RUN mkdir -p /tmp/vecset_conversion && \
    chown -R appuser:appuser /tmp/vecset_conversion

# Switch to non-root user
USER appuser



# Expose port
EXPOSE 8000

# Start application
CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]