"""
VecSet Conversion Service

Simple service for converting PLY files to VecSet representation.
Returns actual files instead of file paths.
"""

import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from vecset_service.services.vecset import VecSetEncoder

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VecSet Service")

# Initialize encoder on startup
encoder = None


@app.on_event("startup")
async def startup_event():
    """Initialize VecSet encoder on startup."""
    global encoder
    try:
        logger.info("Loading VecSet encoder...")
        encoder = VecSetEncoder()
        logger.info("VecSet encoder loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load encoder: {str(e)}")
        # Continue startup - will handle in endpoints


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected errors gracefully."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"VecSet conversion failed: {str(exc)}"}
    )


@app.get("/health")
async def health_check():
    """Simple health check."""
    encoder_status = "loaded" if encoder and encoder.is_ready() else "not_loaded"
    return {
        "status": "healthy" if encoder_status == "loaded" else "degraded",
        "encoder": encoder_status
    }


@app.post("/vecset")
async def convert_to_vecset(
    file: UploadFile = File(...),
    export_reconstruction: bool = Form(False)
):
    """
    Convert PLY file to VecSet representation and return the .npy file.
    
    Args:
        file: PLY file with point cloud data
        export_reconstruction: Whether to export reconstructed STL
        
    Returns:
        FileResponse: The .npy file with VecSet data
    """
    if not encoder:
        raise HTTPException(
            status_code=503,
            detail="VecSet encoder not available"
        )
    
    if not file.filename or not file.filename.lower().endswith('.ply'):
        raise HTTPException(
            status_code=400,
            detail="Only PLY files are supported"
        )
    
    conversion_id = str(uuid.uuid4())
    logger.info(f"Starting VecSet conversion {conversion_id}: {file.filename}")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"vecset_{conversion_id}_"))
    ply_file = temp_dir / file.filename
    
    try:
        # Save uploaded file
        content = await file.read()
        with open(ply_file, "wb") as f:
            f.write(content)
        
        # Convert to VecSet
        output_file = temp_dir / f"{conversion_id}.npy"
        
        result = encoder.to_vecset(
            ply_file=ply_file,
            output_path=output_file,
            export_reconstruction=export_reconstruction
        )
        
        logger.info(f"VecSet conversion {conversion_id} completed")
        
        # Return the .npy file
        return FileResponse(
            path=str(output_file),
            filename=f"{Path(file.filename).stem}.npy",
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"VecSet conversion {conversion_id} failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"VecSet conversion failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)