FROM continuumio/miniconda3:latest

# System dependencies (OpenGL + xvfb for headless rendering)
RUN apt-get update && apt-get install -y \
    libglu1-mesa xvfb libosmesa6 ffmpeg libgl1-mesa-dev libgles2-mesa-dev \
    && rm -rf /var/lib/apt/lists/*



# Create conda environment with Python 3.10 (better compatibility with pyrender)
RUN conda create -n rendering python=3.10 -y && \
    conda install -n rendering -c conda-forge pythonocc-core -y && \
    conda clean -a -y

# WORKDIR /app

# # Copy dependencies
# COPY requirements.txt .

# # Make conda environment active by default
# SHELL ["conda", "run", "-n", "rendering", "/bin/bash", "-c"]

# # Install other packages via pip in the conda environment
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy code
# COPY . .

# # Create render output dir
# RUN mkdir -p /tmp/renders

# ENV DISPLAY=:99
# # Use EGL instead of osmesa for better compatibility
# ENV PYOPENGL_PLATFORM=egl

# # Start Xvfb and FastAPI server
# # Using -a for auto-selecting display number and -s for screen parameters
# CMD ["bash", "-c", "conda run --no-capture-output -n rendering xvfb-run -a -s '-screen 0 1280x1024x24' uvicorn main:app --host 0.0.0.0 --port 8000"]
