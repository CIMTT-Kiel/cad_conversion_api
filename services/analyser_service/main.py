"""
CAD-Analyser Service

Simple microservice to analyse CAD-Files and get basic stats like Volume, Faces, Facetypes.
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from src.analyser_service.cad_stats import (load_step_file,
                                            get_detailed_surface_info,
                                            get_comprehensive_analysis)
from src.analyser_service.drawing_views import DrawingViewsGenerator, DrawingViewsError

# Simple logging setup from environment variables
# logging.basicConfig(
#     level=os.getenv("LOG_LEVEL", "INFO"),
#     format=os.getenv("LOG_FORMAT", "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"),
#     datefmt="%Y-%m-%d %H:%M:%S"
# )

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
async def analyse_cad_file(
    file: UploadFile = File(...)
):
    """
    Analyse CAD file and return comprehensive geometry information as JSON file.

    Args:
        file: Uploaded CAD file (STEP format)

    Returns:
        FileResponse: JSON file containing comprehensive analysis results
    """
    # Basic validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith('.step') and not file.filename.lower().endswith('.stp'):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only STEP files (.step, .stp) are supported"
        )

    analysis_id = str(uuid.uuid4())
    logger.info(f"Starting analysis {analysis_id}: {file.filename}")

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"cad_analysis_{analysis_id}_"))
    input_file = temp_dir / file.filename

    try:
        # Save uploaded file
        with open(input_file, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved to {input_file}, loading with FreeCAD")

        # Load and analyse STEP file
        doc = load_step_file(str(input_file))

        # Get comprehensive analysis
        analysis_result = get_comprehensive_analysis(doc)

        # Add metadata
        analysis_result['metadata'] = {
            'analysis_id': analysis_id,
            'filename': file.filename,
            'timestamp': str(Path(input_file).stat().st_mtime)
        }

        # Save analysis to JSON file
        import json
        json_output_file = temp_dir / f"{Path(file.filename).stem}_analysis.json"
        with open(json_output_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)

        logger.info(f"Analysis {analysis_id} completed successfully")

        # Return JSON file
        return FileResponse(
            path=str(json_output_file),
            filename=f"{Path(file.filename).stem}_analysis.json",
            media_type="application/json",
            background=None
        )

    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/to_drawing_views")
async def generate_drawing_views(
    file: UploadFile = File(...)
):
    """
    Generate technical drawing views from STEP file as DXF files.

    Creates orthographic projections similar to technical drawings:
    - Top view
    - Front view
    - Side view

    Args:
        file: Uploaded STEP file (.step, .stp)

    Returns:
        FileResponse: ZIP file containing DXF files of all views
    """
    import zipfile
    import shutil

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith('.step') and not file.filename.lower().endswith('.stp'):
        raise HTTPException(
            status_code=400,
            detail="Only STEP files (.step, .stp) are supported"
        )

    drawing_id = str(uuid.uuid4())
    logger.info(f"Starting drawing views generation {drawing_id}: {file.filename}")

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"drawing_views_{drawing_id}_"))
    input_file = temp_dir / file.filename
    output_dir = temp_dir / "views"

    try:
        # Save uploaded file
        with open(input_file, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved to {input_file}, generating views")

        # Generate drawing views
        generator = DrawingViewsGenerator(input_file)
        view_files = generator.generate_views(output_dir)

        if not view_files:
            raise DrawingViewsError("No views were generated")

        # Create ZIP file with all views
        zip_path = temp_dir / f"{Path(file.filename).stem}_drawing_views.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for view_file in view_files:
                zipf.write(view_file, view_file.name)

        logger.info(f"Drawing views generation {drawing_id} completed: {len(view_files)} views")

        return FileResponse(
            path=str(zip_path),
            filename=f"{Path(file.filename).stem}_drawing_views.zip",
            media_type="application/zip",
            background=None
        )

    except DrawingViewsError as e:
        logger.error(f"Drawing views generation {drawing_id} failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Drawing views generation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Drawing views generation {drawing_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Drawing views generation failed: {str(e)}"
        )


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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)