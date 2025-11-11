"""CAD Analyser Service - Extract statistics and generate technical drawings."""

import json, logging, tempfile, uuid, zipfile
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from src.analyser_service.cad_stats import load_step_file, get_comprehensive_analysis
from src.analyser_service.drawing_views import DrawingViewsGenerator, DrawingViewsError

logger = logging.getLogger(__name__)
app = FastAPI(title="CAD Analyser Service")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": f"Analysis failed: {str(exc)}"})


def validate_step_file(filename: str) -> None:
    """Validate uploaded file is STEP format."""
    if not filename or not filename.lower().endswith(('.step', '.stp')):
        raise HTTPException(status_code=400, detail="Only STEP files supported")


async def save_upload(file: UploadFile, path: Path) -> None:
    with open(path, "wb") as f:
        f.write(await file.read())


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "cad-analyser"}


@app.post("/analyse")
async def analyse_cad_file(file: UploadFile = File(...)):
    """Analyse CAD file - returns comprehensive geometry statistics as JSON."""
    validate_step_file(file.filename)
    analysis_id = str(uuid.uuid4())
    logger.info(f"Analysis {analysis_id}: {file.filename}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"analysis_{analysis_id}_"))
    input_file = temp_dir / file.filename

    try:
        await save_upload(file, input_file)
        doc = load_step_file(str(input_file))
        analysis_result = get_comprehensive_analysis(doc)

        analysis_result['metadata'] = {
            'analysis_id': analysis_id,
            'filename': file.filename,
            'timestamp': str(input_file.stat().st_mtime)
        }

        json_output_file = temp_dir / f"{input_file.stem}_analysis.json"
        with open(json_output_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)

        logger.info(f"Analysis {analysis_id} completed")
        return FileResponse(path=str(json_output_file), filename=f"{input_file.stem}_analysis.json",
                          media_type="application/json", background=None)

    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/to_drawing_views")
async def generate_drawing_views(file: UploadFile = File(...)):
    """Generate orthographic drawing views (top, front, side) as DXF files in ZIP."""
    validate_step_file(file.filename)
    drawing_id = str(uuid.uuid4())
    logger.info(f"Drawing views {drawing_id}: {file.filename}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"drawing_{drawing_id}_"))
    input_file = temp_dir / file.filename
    output_dir = temp_dir / "views"

    try:
        await save_upload(file, input_file)
        generator = DrawingViewsGenerator(input_file)
        view_files = generator.generate_views(output_dir)

        if not view_files:
            raise DrawingViewsError("No views generated")

        zip_path = temp_dir / f"{input_file.stem}_drawing_views.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for view_file in view_files:
                zipf.write(view_file, view_file.name)

        logger.info(f"Drawing views {drawing_id} completed: {len(view_files)} views")
        return FileResponse(path=str(zip_path), filename=f"{input_file.stem}_drawing_views.zip",
                          media_type="application/zip", background=None)

    except DrawingViewsError as e:
        logger.error(f"Drawing views {drawing_id} failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Drawing views failed: {str(e)}")
    except Exception as e:
        logger.error(f"Drawing views {drawing_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drawing views failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
