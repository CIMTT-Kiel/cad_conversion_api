"""
CAD-Analyser Service

Simple microservice to analyse CAD-Files and get basic stats like Volume, Faces, Facetypes.
"""

import logging
import tempfile
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from src.cad_analyser_service.cad_stats import (load_step_file,
                                                get_detailed_surface_info)

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CAD Analyser Service")

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
    return {"status": "healthy", "service": "cad-analyser"}


@app.post("/analyse")
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
    if target_format not in {"step"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {target_format}. Use: step"
        )
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    tmp_file_id = str(uuid.uuid4())
    logger.info(f"Starting conversion {tmp_file_id}: {file.filename} -> {target_format}")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"{tmp_file_id}"))
    input_file = temp_dir / file.filename

    doc = load_step_file(input_file)

    results = get_detailed_surface_info(doc)



# @app.post("/convert")
# async def convert_cad_file(
#     file: UploadFile = File(...),
#     target_format: str = Form(...)
# ):
#     """
#     Convert CAD file to specified target format and return the file.
    
#     Args:
#         file: Uploaded CAD file (STEP, JT, OBJ, STL)
#         target_format: Target format (stl, ply, vecset)
        
#     Returns:
#         FileResponse: The converted file as download
#     """
#     # Basic validation
#     if target_format not in {"stl", "ply", "vecset"}:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Unsupported format: {target_format}. Use: stl, ply, vecset"
#         )
    
#     if not file.filename:
#         raise HTTPException(status_code=400, detail="No filename provided")
    
#     conversion_id = str(uuid.uuid4())
#     logger.info(f"Starting conversion {conversion_id}: {file.filename} -> {target_format}")
    
#     # Create temporary directory
#     temp_dir = Path(tempfile.mkdtemp(prefix=f"cad_{conversion_id}_"))
#     input_file = temp_dir / file.filename
    
#     try:
#         # Save uploaded file
#         with open(input_file, "wb") as f:
#             content = await file.read()
#             f.write(content)
        
#         # Initialize converter
#         converter = CADConverter(input_file)
        
#         # Generate output filename based on input
#         base_name = Path(file.filename).stem
        
#         # Convert based on target format
#         if target_format == "stl":
#             output_file = temp_dir / f"{conversion_id}.stl"
#             converter.to_stl(output_file)
            
#             logger.info(f"STL conversion {conversion_id} completed")
#             return FileResponse(
#                 path=str(output_file),
#                 filename=f"{base_name}.stl",
#                 media_type="application/octet-stream",
#                 background=None  # Don't delete file automatically
#             )
            
#         elif target_format == "ply":
#             output_file = temp_dir / f"{conversion_id}.ply"
#             converter.to_ply(output_file)
            
#             logger.info(f"PLY conversion {conversion_id} completed")
#             return FileResponse(
#                 path=str(output_file),
#                 filename=f"{base_name}.ply",
#                 media_type="application/octet-stream",
#                 background=None  # Don't delete file automatically
#             )
            
#         elif target_format == "vecset":
#             # Convert to PLY first
#             ply_file = temp_dir / f"{conversion_id}.ply"
#             converter.to_ply(ply_file)
            
#             # Send to VecSet service and get file back
#             logger.debug(f"Sending PLY to VecSet service")
#             with open(ply_file, "rb") as f:
#                 vecset_response = requests.post(
#                     VECSET_SERVICE_URL+"/vecset",
#                     files={"file": (ply_file.name, f)},
#                     timeout=300,
#                     stream=True  # Stream the response
#                 )
            
#             if vecset_response.status_code != 200:
#                 logger.error(f"VecSet service failed: {vecset_response.status_code}")
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"VecSet service failed: {vecset_response.text}"
#                 )
            
#             # Save the VecSet response (should be .npy file) to temp location
#             npy_file = temp_dir / f"{conversion_id}.npy"
#             with open(npy_file, "wb") as f:
#                 for chunk in vecset_response.iter_content(chunk_size=8192):
#                     if chunk:
#                         f.write(chunk)
            
#             logger.info(f"VecSet conversion {conversion_id} completed")
#             return FileResponse(
#                 path=str(npy_file),
#                 filename=f"{base_name}.npy",
#                 media_type="application/octet-stream",
#                 background=None  # Don't delete file automatically
#             )
        
#     except Exception as e:
#         logger.error(f"Conversion {conversion_id} failed: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=f"Conversion failed: {str(e)}"
#         )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)