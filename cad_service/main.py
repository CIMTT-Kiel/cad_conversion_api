from fastapi import FastAPI, UploadFile, HTTPException
from pathlib import Path
import tempfile
import shutil
import uuid
import requests

from cad_service.services.cad_conversion import CADConverter

app = FastAPI(title="CAD Converter Service")

# Internal URL for VecSet service (in Docker network)
VECSET_SERVICE_URL = "http://0.0.0.0:8000/vecset"


@app.post("/convert")
async def convert(file: UploadFile, target_format: str):
    """
    Convert CAD file to STL, PLY, or VecSet.
    """
    if target_format not in {"stl", "ply", "vecset"}:
        raise HTTPException(status_code=400, detail="Unsupported target format")

    tmpdir = Path(tempfile.mkdtemp())
    input_file = tmpdir / file.filename
    with open(input_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    converter = CADConverter(input_file)

    if target_format == "stl":
        out = tmpdir / f"{uuid.uuid4().hex}.stl"
        converter.to_stl(out)
        return {"file": str(out)}

    if target_format == "ply":
        out = tmpdir / f"{uuid.uuid4().hex}.ply"
        converter.to_ply(out)
        return {"file": str(out)}

    if target_format == "vecset":
        # first create PLY locally
        ply_file = tmpdir / f"{uuid.uuid4().hex}.ply"
        converter.to_ply(ply_file)

        # send PLY to VecSet-Service
        with open(ply_file, "rb") as f:
            resp = requests.post(VECSET_SERVICE_URL, files={"file": f})
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="VecSet service failed")
        return resp.json()

    return {"detail": "Conversion finished"}
