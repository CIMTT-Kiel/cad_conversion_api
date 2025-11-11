# Fix for Python 3.10+ compatibility with older packages
import collections
import collections.abc
for name in dir(collections.abc):
    if not name.startswith('_'):
        setattr(collections, name, getattr(collections.abc, name))

# Fix gcd import for older packages
import fractions
import math
if not hasattr(fractions, 'gcd'):
    fractions.gcd = math.gcd

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import tempfile
import os
import base64
from src.rendering_service.services.multiview_renderer import step_to_images

app = FastAPI(title="STEP Rendering Service", version="1.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/render")
async def render_step_file(
    file: UploadFile = File(...),
    part_number: str = Form(...),
    render_mode: str = Form("shaded_with_edges"),
    total_imgs: int = Form(3),
):
    tmp_path = None
    output_dir = None

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".step") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        # Create temporary output directory
        output_dir = tempfile.mkdtemp()

        # Call rendering function with correct parameters
        result = step_to_images(
            step_file=tmp_path,
            part_number=part_number,
            output_dir=output_dir,
            resolution=(1280, 720),
            stl_deflection=0.1,
            cleanup_stl=True,
            render_mode=render_mode,
            edge_color=(0.1, 0.1, 0.1),
            edge_width=2.0,
            transparency=1.0,
            total_imgs=total_imgs
        )

        # Read images and encode as base64
        images_data = []
        for img_filename in result.get("images", []):
            # Construct full path to image
            img_path = os.path.join(output_dir, part_number, img_filename)
            if os.path.exists(img_path):
                with open(img_path, "rb") as img_file:
                    img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                    images_data.append({
                        "filename": os.path.basename(img_path),
                        "data": img_base64
                    })
                # Clean up the image file
                os.remove(img_path)

        # Get perspective data
        perspectives = result.get("perspectives", [])

        # Clean up output directories
        part_output_dir = os.path.join(output_dir, part_number)
        if os.path.exists(part_output_dir):
            try:
                os.rmdir(part_output_dir)
            except:
                pass

        if output_dir and os.path.exists(output_dir):
            try:
                os.rmdir(output_dir)
            except:
                pass

        # Return result with base64-encoded images
        return JSONResponse(content={
            "success": result.get("success", False),
            "images": images_data,
            "perspectives": perspectives,
            "total_images": len(images_data)
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        # Clean up temporary STEP file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
