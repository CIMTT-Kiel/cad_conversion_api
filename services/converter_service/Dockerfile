# Dockerfile for CAD Conversion Service
FROM cimtthawk/converter-service:latest

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