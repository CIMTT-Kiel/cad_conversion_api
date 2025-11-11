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

# Try to import gmsh for 3D meshing
try:
    import gmsh
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False

# Try to import libraries for invariants calculation
try:
    import meshio
    import numpy as np
    import quadpy
    from sklearn.decomposition import PCA
    INVARIANTS_AVAILABLE = True
except ImportError:
    INVARIANTS_AVAILABLE = False

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


@app.post("/to_voxel")
async def convert_to_voxel(
    file: UploadFile = File(...),
    resolution: int = Form(128)
):
    """
    Convert CAD file to voxel representation.

    Args:
        file: Uploaded CAD file (STEP, JT, OBJ, STL)
        resolution: Voxel grid resolution (default: 128)

    Returns:
        FileResponse: Sparse voxel file (.npz format)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if resolution < 16 or resolution > 512:
        raise HTTPException(
            status_code=400,
            detail="Resolution must be between 16 and 512"
        )

    voxel_id = str(uuid.uuid4())
    logger.info(f"Starting voxel conversion {voxel_id}: {file.filename} (resolution: {resolution})")

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"voxel_{voxel_id}_"))
    input_file = temp_dir / file.filename

    try:
        # Save uploaded file
        with open(input_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # Initialize converter
        converter = CADConverter(input_file)

        # Generate output filename
        base_name = Path(file.filename).stem
        output_file = temp_dir / f"{voxel_id}.npz"

        # Convert to voxel
        converter.to_voxel(output_file, resolution=resolution)

        logger.info(f"Voxel conversion {voxel_id} completed")
        return FileResponse(
            path=str(output_file),
            filename=f"{base_name}_voxel_{resolution}.npz",
            media_type="application/octet-stream",
            background=None
        )

    except Exception as e:
        logger.error(f"Voxel conversion {voxel_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Voxel conversion failed: {str(e)}"
        )


@app.post("/mesh")
async def generate_3d_mesh(
    file: UploadFile = File(...),
    mesh_size: float = Form(None)
):
    """
    Generate a 3D mesh from a STEP file using Gmsh.

    Args:
        file: Uploaded STEP file
        mesh_size: Optional mesh size parameter for controlling mesh density

    Returns:
        FileResponse: The generated .msh file
    """
    if not GMSH_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Gmsh is not available. Please install gmsh to use this feature."
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".step", ".stp"]:
        raise HTTPException(
            status_code=400,
            detail="Only STEP files (.step, .stp) are supported for meshing"
        )

    mesh_id = str(uuid.uuid4())
    logger.info(f"Starting mesh generation {mesh_id}: {file.filename}")

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"mesh_{mesh_id}_"))
    step_file_path = temp_dir / file.filename
    msh_file_path = temp_dir / f"{Path(file.filename).stem}.msh"

    try:
        # Save uploaded file
        with open(step_file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Initialize Gmsh
        gmsh.initialize(interruptible=False)
        gmsh.option.setNumber("General.Terminal", 1)

        try:
            gmsh.model.add("3DMesh")
            gmsh.model.occ.importShapes(str(step_file_path))
            gmsh.model.occ.synchronize()

            # Enable face sewing for better mesh quality
            gmsh.option.setNumber("Geometry.OCCSewFaces", 1)
            gmsh.model.occ.synchronize()

            # Set mesh size if provided
            if mesh_size is not None and mesh_size > 0:
                gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size)
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)

            # Generate 3D mesh
            gmsh.model.mesh.generate(3)

            # Verify that a 3D mesh was generated
            elem_types, _, _ = gmsh.model.mesh.getElements(dim=3)
            if not elem_types:
                raise ValueError("No 3D mesh generated. Only 2D mesh may have been created.")

            # Write mesh file
            gmsh.write(str(msh_file_path))

            logger.info(f"Mesh generation {mesh_id} completed: {msh_file_path}")

        finally:
            gmsh.finalize()

        # Return the mesh file
        base_name = Path(file.filename).stem
        return FileResponse(
            path=str(msh_file_path),
            filename=f"{base_name}.msh",
            media_type="application/octet-stream",
            background=None
        )

    except ValueError as e:
        logger.error(f"Mesh generation {mesh_id} failed: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Mesh generation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Mesh generation {mesh_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Mesh generation failed: {str(e)}"
        )


@app.post("/invariants")
async def calculate_invariants(
    file: UploadFile = File(...),
    normalized: bool = Form(False)
):
    """
    Calculate geometric invariants from a 3D mesh file.

    Args:
        file: Uploaded mesh file (.msh format from Gmsh)
        normalized: If True, scale mesh to unit cube (default: False)

    Returns:
        JSON with moments (mues) and invariants (pis)
    """
    if not INVARIANTS_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Invariants calculation not available. Required libraries: meshio, quadpy, scikit-learn"
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    invariants_id = str(uuid.uuid4())
    logger.info(f"Starting invariants calculation {invariants_id}: {file.filename}")

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"invariants_{invariants_id}_"))
    mesh_file_path = temp_dir / file.filename

    try:
        # Save uploaded file
        with open(mesh_file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Define moment permutations (up to order 4)
        moment_permutations = [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1),
            (3, 0, 0), (0, 3, 0), (0, 0, 3), (2, 1, 0), (2, 0, 1), (1, 2, 0),
            (0, 2, 1), (1, 0, 2), (0, 1, 2), (1, 1, 1),
            (4, 0, 0), (0, 4, 0), (0, 0, 4), (3, 1, 0), (3, 0, 1), (1, 3, 0),
            (0, 3, 1), (1, 0, 3), (0, 1, 3), (2, 2, 0), (2, 0, 2), (0, 2, 2),
            (2, 1, 1), (1, 2, 1), (1, 1, 2)
        ]

        eps = 1e-10

        # Read mesh file
        inmsh = meshio.read(str(mesh_file_path))

        # Check if mesh has tetrahedrons
        if 'tetra' not in inmsh.cells_dict:
            raise ValueError("Mesh file must contain tetrahedral elements (3D mesh required)")

        tetras_idxs = inmsh.cells_dict['tetra']

        # Apply PCA transformation
        pca = PCA(n_components=3)
        pca.fit(inmsh.points)
        inmsh.points = pca.transform(inmsh.points)

        # Optional normalization
        if normalized:
            max_expension = (np.max(inmsh.points[:, 0]) - np.min(inmsh.points[:, 0]))
            if max_expension > 0:
                inmsh.points = inmsh.points / max_expension

        # Prepare tetrahedrons for integration
        tetras = inmsh.points[tetras_idxs]
        tetras_s = np.stack(tetras, axis=-2)

        # Initialize quadpy integration scheme (order 4)
        scheme = quadpy.t3.get_good_scheme(4)

        # Calculate moments (mues)
        mues = {}
        for mp in moment_permutations:
            moment_key = f'mue_{mp[0]}{mp[1]}{mp[2]}'
            # Define lambda for current moment permutation
            l = lambda x, p=mp: x[0]**p[0] * x[1]**p[1] * x[2]**p[2]
            # Integrate over all tetrahedrons
            mues[moment_key] = float(scheme.integrate(l, tetras_s).sum())

        # Calculate invariants (pis)
        pis = {}
        mue_200 = mues['mue_200'] if mues['mue_200'] > 0 else eps
        mue_020 = mues['mue_020'] if mues['mue_020'] > 0 else eps
        mue_002 = mues['mue_002'] if mues['mue_002'] > 0 else eps

        for mp in moment_permutations:
            p, q, r = int(mp[0]), int(mp[1]), int(mp[2])
            mue_key = f'mue_{p}{q}{r}'
            pi_key = f'pi_{p}{q}{r}'

            mue_var = mues[mue_key]
            denominator = (mue_200 ** ((4*p - q - r + 2) / 10) *
                          mue_020 ** ((4*q - p - r + 2) / 10) *
                          mue_002 ** ((4*r - q - p + 2) / 10))

            pis[pi_key] = float(mue_var / denominator) if denominator != 0 else 0.0

        # Combine results
        result = {
            "filename": file.filename,
            "normalized": normalized,
            "total_moments": len(mues),
            "total_invariants": len(pis),
            "moments": mues,
            "invariants": pis
        }

        logger.info(f"Invariants calculation {invariants_id} completed: {len(mues)} moments, {len(pis)} invariants")

        return JSONResponse(content=result)

    except ValueError as e:
        logger.error(f"Invariants calculation {invariants_id} failed: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Invariants calculation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Invariants calculation {invariants_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Invariants calculation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)