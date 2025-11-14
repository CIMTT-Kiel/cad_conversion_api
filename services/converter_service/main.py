"""CAD Converter Service - Converts CAD files to ML-specific formats"""

import base64, io, logging, os, tempfile, uuid, zipfile
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from converter_service.services.cad_conversion import CADConverter

# Optional dependencies
try:
    import gmsh, meshio, numpy as np, quadpy
    from sklearn.decomposition import PCA
    GMSH_AVAILABLE = INVARIANTS_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = INVARIANTS_AVAILABLE = False

EMBEDDING_URL = "http://embedding-service:8000"
RENDERING_URL = "http://rendering-service:8000"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format=os.getenv("LOG_FORMAT", "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"),
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CAD Converter Service")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": f"Conversion failed: {str(exc)}"})


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "cad-converter"}


def _validate_file(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")


async def _save_uploaded_file(file: UploadFile, path: Path):
    with open(path, "wb") as f:
        f.write(await file.read())


@app.post("/convert")
async def convert_cad_file(file: UploadFile = File(...), target_format: str = Form(...)):
    """Convert CAD file to STL, PLY, or VecSet format."""
    if target_format not in {"stl", "ply", "vecset"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {target_format}. Use: stl, ply, vecset")

    _validate_file(file)
    conversion_id = str(uuid.uuid4())
    logger.info(f"Conversion {conversion_id}: {file.filename} -> {target_format}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"cad_{conversion_id}_"))
    input_file = temp_dir / file.filename

    try:
        await _save_uploaded_file(file, input_file)
        converter = CADConverter(input_file)
        output_file = temp_dir / f"{conversion_id}.{target_format if target_format != 'vecset' else 'ply'}"

        if target_format == "stl":
            converter.to_stl(output_file)
        elif target_format == "ply":
            converter.to_ply(output_file)
        elif target_format == "vecset":
            converter.to_ply(output_file)
            logger.debug("Sending PLY to VecSet service")
            with open(output_file, "rb") as f:
                vecset_response = requests.post(f"{EMBEDDING_URL}/vecset",
                                              files={"file": (output_file.name, f)},
                                              timeout=300, stream=True)

            if vecset_response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"VecSet service failed: {vecset_response.text}")

            output_file = temp_dir / f"{conversion_id}.npy"
            with open(output_file, "wb") as f:
                for chunk in vecset_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        logger.info(f"{target_format.upper()} conversion {conversion_id} completed")
        return FileResponse(path=str(output_file), filename=f"{Path(file.filename).stem}.{output_file.suffix[1:]}",
                          media_type="application/octet-stream", background=None)

    except Exception as e:
        logger.error(f"Conversion {conversion_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.post("/multiview")
async def generate_multiview(file: UploadFile = File(...), resolution: int = Form(448),
                            background: str = Form("White"), art_styles: str = Form("5")):
    """Generate multiple orthographic views. Styles: 2=wireframe, 5=flat_lines, 6=shaded."""
    _validate_file(file)
    multiview_id = str(uuid.uuid4())
    logger.info(f"Multiview {multiview_id}: {file.filename}")

    style_to_mode = {"2": "wireframe", "5": "shaded_with_edges", "6": "shaded"}
    try:
        styles = [s.strip() for s in art_styles.split(",")]
        render_modes = [(s, style_to_mode.get(s, "shaded_with_edges")) for s in styles]
        logger.info(f"Rendering {len(render_modes)} style(s)")

        content = await file.read()
        temp_dir = Path(tempfile.mkdtemp(prefix=f"multiview_{multiview_id}_"))
        zip_path = temp_dir / f"{Path(file.filename).stem}_multiviews.zip"
        total_images = 0

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for style_id, render_mode in render_modes:
                response = requests.post(f"{RENDERING_URL}/render",
                                       files={"file": (file.filename, io.BytesIO(content), file.content_type)},
                                       data={"part_number": f"multiview_{style_id}", "render_mode": render_mode, "total_imgs": "20"},
                                       timeout=600)

                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"Rendering service failed: {response.text}")

                images = response.json().get("images", [])
                logger.info(f"Style {style_id}: {len(images)} images")

                for img_data in images:
                    filename = f"style_{style_id}_{img_data.get('filename', f'image_{total_images}.png')}"
                    zipf.writestr(filename, base64.b64decode(img_data.get("data", "")))
                    total_images += 1

        logger.info(f"Multiview {multiview_id} completed: {total_images} images")
        return FileResponse(path=str(zip_path), filename=f"{Path(file.filename).stem}_multiviews.zip",
                          media_type="application/zip", background=None)

    except requests.exceptions.RequestException as e:
        logger.error(f"Multiview generation {multiview_id} failed: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Rendering service communication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Multiview generation {multiview_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Multiview generation failed: {str(e)}")


@app.post("/to_voxel")
async def convert_to_voxel(file: UploadFile = File(...), resolution: int = Form(128)):
    """Convert CAD file to sparse voxel representation (.npz)."""
    _validate_file(file)
    if not 16 <= resolution <= 512:
        raise HTTPException(status_code=400, detail="Resolution must be between 16 and 512")

    voxel_id = str(uuid.uuid4())
    logger.info(f"Voxel {voxel_id}: {file.filename} (resolution: {resolution})")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"voxel_{voxel_id}_"))
    input_file = temp_dir / file.filename

    try:
        await _save_uploaded_file(file, input_file)
        converter = CADConverter(input_file)
        output_file = temp_dir / f"{voxel_id}.npz"
        converter.to_voxel(output_file, resolution=resolution)

        logger.info(f"Voxel {voxel_id} completed")
        return FileResponse(path=str(output_file), filename=f"{Path(file.filename).stem}_voxel_{resolution}.npz",
                          media_type="application/octet-stream", background=None)

    except Exception as e:
        logger.error(f"Voxel {voxel_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voxel conversion failed: {str(e)}")


@app.post("/mesh")
async def generate_3d_mesh(file: UploadFile = File(...), mesh_size: float = Form(None)):
    """Generate 3D mesh from STEP file using Gmsh."""
    if not GMSH_AVAILABLE:
        raise HTTPException(status_code=501, detail="Gmsh not available")
    _validate_file(file)
    if Path(file.filename).suffix.lower() not in [".step", ".stp"]:
        raise HTTPException(status_code=400, detail="Only STEP files supported")

    mesh_id = str(uuid.uuid4())
    logger.info(f"Mesh {mesh_id}: {file.filename}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"mesh_{mesh_id}_"))
    step_file_path = temp_dir / file.filename
    msh_file_path = temp_dir / f"{Path(file.filename).stem}.msh"

    try:
        await _save_uploaded_file(file, step_file_path)

        gmsh.initialize(interruptible=False)
        gmsh.option.setNumber("General.Terminal", 1)

        try:
            gmsh.model.add("3DMesh")
            gmsh.model.occ.importShapes(str(step_file_path))
            gmsh.model.occ.synchronize()

            gmsh.option.setNumber("Geometry.OCCSewFaces", 1)
            gmsh.model.occ.synchronize()

            if mesh_size is not None and mesh_size > 0:
                gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size)
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)

            gmsh.model.mesh.generate(3)

            elem_types, _, _ = gmsh.model.mesh.getElements(dim=3)
            if not elem_types:
                raise ValueError("No 3D mesh generated")

            gmsh.write(str(msh_file_path))
            logger.info(f"Mesh {mesh_id} completed")

        finally:
            gmsh.finalize()

        return FileResponse(path=str(msh_file_path), filename=f"{Path(file.filename).stem}.msh",
                          media_type="application/octet-stream", background=None)

    except ValueError as e:
        logger.error(f"Mesh generation {mesh_id} failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Mesh generation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Mesh generation {mesh_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Mesh generation failed: {str(e)}")


@app.post("/invariants")
async def calculate_invariants(file: UploadFile = File(...), normalized: bool = Form(False)):
    """Calculate geometric invariants from 3D mesh (.msh)."""
    if not INVARIANTS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Invariants not available")
    _validate_file(file)
    invariants_id = str(uuid.uuid4())
    logger.info(f"Invariants {invariants_id}: {file.filename}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"invariants_{invariants_id}_"))
    mesh_file_path = temp_dir / file.filename

    try:
        await _save_uploaded_file(file, mesh_file_path)

        # Moment permutations up to order 4
        moment_permutations = [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1),
            (3, 0, 0), (0, 3, 0), (0, 0, 3), (2, 1, 0), (2, 0, 1), (1, 2, 0),
            (0, 2, 1), (1, 0, 2), (0, 1, 2), (1, 1, 1),
            (4, 0, 0), (0, 4, 0), (0, 0, 4), (3, 1, 0), (3, 0, 1), (1, 3, 0),
            (0, 3, 1), (1, 0, 3), (0, 1, 3), (2, 2, 0), (2, 0, 2), (0, 2, 2),
            (2, 1, 1), (1, 2, 1), (1, 1, 2)
        ]

        inmsh = meshio.read(str(mesh_file_path))
        if 'tetra' not in inmsh.cells_dict:
            raise ValueError("Mesh must contain tetrahedral elements")

        tetras_idxs = inmsh.cells_dict['tetra']

        pca = PCA(n_components=3)
        pca.fit(inmsh.points)
        inmsh.points = pca.transform(inmsh.points)

        if normalized:
            max_expansion = np.max(inmsh.points[:, 0]) - np.min(inmsh.points[:, 0])
            if max_expansion > 0:
                inmsh.points = inmsh.points / max_expansion

        tetras = inmsh.points[tetras_idxs]
        tetras_s = np.stack(tetras, axis=-2)
        scheme = quadpy.t3.get_good_scheme(4)

        mues = {}
        for mp in moment_permutations:
            moment_key = f'mue_{mp[0]}{mp[1]}{mp[2]}'
            l = lambda x, p=mp: x[0]**p[0] * x[1]**p[1] * x[2]**p[2]
            mues[moment_key] = float(scheme.integrate(l, tetras_s).sum())

        eps = 1e-10
        mue_200 = mues['mue_200'] if mues['mue_200'] > 0 else eps
        mue_020 = mues['mue_020'] if mues['mue_020'] > 0 else eps
        mue_002 = mues['mue_002'] if mues['mue_002'] > 0 else eps

        pis = {}
        for mp in moment_permutations:
            p, q, r = int(mp[0]), int(mp[1]), int(mp[2])
            mue_key = f'mue_{p}{q}{r}'
            pi_key = f'pi_{p}{q}{r}'
            mue_var = mues[mue_key]
            denominator = (mue_200 ** ((4*p - q - r + 2) / 10) *
                          mue_020 ** ((4*q - p - r + 2) / 10) *
                          mue_002 ** ((4*r - q - p + 2) / 10))
            pis[pi_key] = float(mue_var / denominator) if denominator != 0 else 0.0

        logger.info(f"Invariants {invariants_id} completed: {len(mues)} moments, {len(pis)} invariants")

        return JSONResponse(content={
            "filename": file.filename,
            "normalized": normalized,
            "total_moments": len(mues),
            "total_invariants": len(pis),
            "moments": mues,
            "invariants": pis
        })

    except ValueError as e:
        logger.error(f"Invariants calculation {invariants_id} failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invariants calculation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Invariants calculation {invariants_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Invariants calculation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)