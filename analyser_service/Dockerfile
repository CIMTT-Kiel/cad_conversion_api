FROM linuxserver/freecad:latest

# Set image name 
LABEL description="Analyser service with FreeCAD and python analysis tools"

ENV DEBIAN_FRONTEND=noninteractive

# Install python 
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-venv python3-pip build-essential git && \
    rm -rf /var/lib/apt/lists/*

# Create a venv with system-site-packages to access FreeCAD modules
RUN python3 -m venv /opt/freecad-venv --system-site-packages && \
    /opt/freecad-venv/bin/pip install --upgrade pip setuptools wheel

# Find FreeCAD installation path and add it to the venv's site-packages
RUN FREECAD_LIB=$(python3 -c "import sys; import os; \
    paths = ['/usr/lib/freecad/lib', '/usr/lib/freecad-python3/lib', \
             '/usr/local/lib/freecad/lib', '/opt/freecad/lib']; \
    print(next((p for p in paths if os.path.exists(p)), '/usr/lib/freecad/lib'))") && \
    SITE_PACKAGES=$(find /opt/freecad-venv/lib -type d -name "site-packages" | head -n 1) && \
    echo "$FREECAD_LIB" > "$SITE_PACKAGES/freecad.pth"

# Alternative: Set PYTHONPATH in the wrapper script (more robust)
RUN printf '%s\n' \
    '#!/bin/bash' \
    'export PYTHONPATH="/usr/lib/freecad/lib:/usr/lib/freecad-python3/lib:${PYTHONPATH}"' \
    'source /opt/freecad-venv/bin/activate' \
    'exec python3 "$@"' > /usr/local/bin/fc-python && \
    chmod +x /usr/local/bin/fc-python

# Install additional python packages needed for analysis
RUN /opt/freecad-venv/bin/pip install numpy pandas 

WORKDIR /workspace
VOLUME ["/workspace"]