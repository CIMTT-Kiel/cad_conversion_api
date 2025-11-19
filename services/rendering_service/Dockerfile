FROM cimtthawk/rendering-service:latest

WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Make conda environment active by default
SHELL ["conda", "run", "-n", "rendering", "/bin/bash", "-c"]

# Install other packages via pip in the conda environment
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create render output dir
RUN mkdir -p /tmp/renders

ENV DISPLAY=:99
# Use EGL instead of osmesa for better compatibility
ENV PYOPENGL_PLATFORM=egl

# Start Xvfb and FastAPI server
# Using -a for auto-selecting display number and -s for screen parameters
CMD ["bash", "-c", "conda run --no-capture-output -n rendering xvfb-run -a -s '-screen 0 1280x1024x24' uvicorn main:app --host 0.0.0.0 --port 8000"]
