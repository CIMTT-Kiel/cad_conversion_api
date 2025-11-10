"""
CAD Converter Service

Simple microservice for converting CAD files to STL, PLY, and VecSet formats.
Returns actual files instead of file paths.
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from converter_service.services.cad_conversion import CADConverter

EMBEDDING_URL = "http://embedding-service:8000"
RENDERING_URL = "http://rendering-service:8000"


# Simple logging setup from environment variables
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format=os.getenv("LOG_FORMAT", "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"),
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CAD Converter Service")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected errors gracefully."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Conversion failed: {str(exc)}"}
    )


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "cad-converter"}


@app.post("/convert")
async def convert_cad_file(
    file: UploadFile = File(...),
    target_format: str = Form(...)
):
    """
    Convert CAD file to specified target format and return the file.
    
    Args:
        file: Uploaded CAD file (STEP, JT, OBJ, STL)
        target_format: Target format (stl, ply, vecset)
        
    Returns:
        FileResponse: The converted file as download
    """
    # Basic validation
    if target_format not in {"stl", "ply", "vecset"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {target_format}. Use: stl, ply, vecset"
        )
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    conversion_id = str(uuid.uuid4())
    logger.info(f"Starting conversion {conversion_id}: {file.filename} -> {target_format}")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"cad_{conversion_id}_"))
    input_file = temp_dir / file.filename
    
    try:
        # Save uploaded file
        with open(input_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Initialize converter
        converter = CADConverter(input_file)
        
        # Generate output filename based on input
        base_name = Path(file.filename).stem
        
        # Convert based on target format
        if target_format == "stl":
            output_file = temp_dir / f"{conversion_id}.stl"
            converter.to_stl(output_file)
            
            logger.info(f"STL conversion {conversion_id} completed")
            return FileResponse(
                path=str(output_file),
                filename=f"{base_name}.stl",
                media_type="application/octet-stream",
                background=None  # Don't delete file automatically
            )
            
        elif target_format == "ply":
            output_file = temp_dir / f"{conversion_id}.ply"
            converter.to_ply(output_file)
            
            logger.info(f"PLY conversion {conversion_id} completed")
            return FileResponse(
                path=str(output_file),
                filename=f"{base_name}.ply",
                media_type="application/octet-stream",
                background=None  # Don't delete file automatically
            )
            
        elif target_format == "vecset":
            # Convert to PLY first
            ply_file = temp_dir / f"{conversion_id}.ply"
            converter.to_ply(ply_file)
            
            # Send to VecSet service and get file back
            logger.debug(f"Sending PLY to VecSet service")
            with open(ply_file, "rb") as f:
                vecset_response = requests.post(
                    EMBEDDING_URL+"/vecset",
                    files={"file": (ply_file.name, f)},
                    timeout=300,
                    stream=True  # Stream the response
                )
            
            if vecset_response.status_code != 200:
                logger.error(f"VecSet service failed: {vecset_response.status_code}")
                raise HTTPException(
                    status_code=502,
                    detail=f"VecSet service failed: {vecset_response.text}"
                )
            
            # Save the VecSet response (should be .npy file) to temp location
            npy_file = temp_dir / f"{conversion_id}.npy"
            with open(npy_file, "wb") as f:
                for chunk in vecset_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"VecSet conversion {conversion_id} completed")
            return FileResponse(
                path=str(npy_file),
                filename=f"{base_name}.npy",
                media_type="application/octet-stream",
                background=None  # Don't delete file automatically
            )
        
    except Exception as e:
        logger.error(f"Conversion {conversion_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Conversion failed: {str(e)}"
        )


@app.post("/multiview")
async def generate_multiview(
    file: UploadFile = File(...),
    resolution: int = Form(448),
    background: str = Form("White"),
    art_styles: str = Form("5")
):
    """
    Generate multiple orthographic views from a CAD file.

    This endpoint uses the rendering service to generate 20 views for each art style.

    Args:
        file: Uploaded CAD file (STEP, IGES, BREP, STL)
        resolution: Image resolution in pixels (default: 448)
        background: Background color - 'White', 'Black', 'Transparent' (default: "White")
        art_styles: Comma-separated list of rendering modes (default: "5")
                   5 = Flat Lines (shaded_with_edges)
                   2 = Wireframe (wireframe)
                   6 = Shaded (shaded)

    Returns:
        FileResponse: ZIP file containing all generated views (20 views per style)
    """
    import zipfile
    import base64
    import io

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    multiview_id = str(uuid.uuid4())
    logger.info(f"Starting multiview generation {multiview_id}: {file.filename}")

    # Map art styles to render modes
    style_to_mode = {
        "2": "wireframe",      # Wireframe
        "5": "shaded_with_edges",  # Flat Lines
        "6": "shaded"          # Shaded
    }

    try:
        # Parse art styles
        styles = [s.strip() for s in art_styles.split(",")]
        render_modes = []
        for style in styles:
            mode = style_to_mode.get(style, "shaded_with_edges")
            render_modes.append((style, mode))

        logger.info(f"Rendering {len(render_modes)} style(s): {[m[1] for m in render_modes]}")

        # Read file content once
        content = await file.read()

        # Create temp directory for ZIP
        temp_dir = Path(tempfile.mkdtemp(prefix=f"multiview_{multiview_id}_"))
        zip_path = temp_dir / f"{Path(file.filename).stem}_multiviews.zip"

        total_images = 0

        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Generate 20 views for each render mode
            for style_id, render_mode in render_modes:
                logger.info(f"Generating 20 views with render_mode: {render_mode}")

                # Prepare request to rendering service
                files = {"file": (file.filename, io.BytesIO(content), file.content_type)}
                data = {
                    "part_number": f"multiview_{style_id}",
                    "render_mode": render_mode,
                    "total_imgs": "20"
                }

                rendering_response = requests.post(
                    RENDERING_URL + "/render",
                    files=files,
                    data=data,
                    timeout=600
                )

                if rendering_response.status_code != 200:
                    logger.error(f"Rendering service failed: {rendering_response.status_code}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"Rendering service failed: {rendering_response.text}"
                    )

                # Parse response
                result = rendering_response.json()
                images = result.get("images", [])

                logger.info(f"Received {len(images)} images for style {style_id}")

                # Add images to ZIP
                for img_data in images:
                    filename = img_data.get("filename", f"image_{total_images}.png")
                    # Add style prefix to filename
                    filename = f"style_{style_id}_{filename}"
                    img_base64 = img_data.get("data", "")

                    # Decode base64 and add to ZIP
                    img_bytes = base64.b64decode(img_base64)
                    zipf.writestr(filename, img_bytes)
                    total_images += 1

        logger.info(f"Multiview generation {multiview_id} completed: {total_images} images")

        return FileResponse(
            path=str(zip_path),
            filename=f"{Path(file.filename).stem}_multiviews.zip",
            media_type="application/zip",
            background=None
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Multiview generation {multiview_id} failed: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Rendering service communication failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Multiview generation {multiview_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Multiview generation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)