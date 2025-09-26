from fastapi import FastAPI, UploadFile, HTTPException
from pathlib import Path
import tempfile
import shutil
import uuid

from vecset_service.services.vecset import VecSetEncoder

app = FastAPI(title="VecSet Service")

encoder = VecSetEncoder()


@app.post("/vecset")
async def convert_to_vecset(file: UploadFile, export_reconstruction: bool = False):
    """
    Convert PLY file to VecSet (.npy).
    Optionally export reconstructed STL.
    """
    tmpdir = Path(tempfile.mkdtemp())
    ply_file = tmpdir / file.filename
    with open(ply_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        out_file = tmpdir / f"{uuid.uuid4().hex}.npy"
        encoder.to_vecset(ply_file, out_file, export_reconstruction)
        return {"file": str(out_file)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
