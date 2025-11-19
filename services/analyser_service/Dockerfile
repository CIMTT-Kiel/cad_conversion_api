FROM cimtthawk/analyser-service:latest

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