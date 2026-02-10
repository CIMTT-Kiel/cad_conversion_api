"""
Embedding Service

Service for converting CAD files into ML-generated embeddings
"""

import asyncio
import gc
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from embedding_service.services.vecset import VecSetEncoder

# -----------------------------
# Config
# -----------------------------
ENCODER_IDLE_SECONDS = int(os.getenv("ENCODER_IDLE_SECONDS", "300"))  # 5 min default
ENCODER_SWEEP_INTERVAL_SECONDS = int(os.getenv("ENCODER_SWEEP_INTERVAL_SECONDS", "15"))

# Simple logging setup from environment variables
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format=os.getenv("LOG_FORMAT", "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"),
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Embedding Service")

# -----------------------------
# Encoder lifecycle state
# -----------------------------
encoder = None
_encoder_lock = asyncio.Lock()
_last_used_ts = 0.0
_sweeper_task: asyncio.Task | None = None


def _touch_encoder_usage():
    global _last_used_ts
    _last_used_ts = time.time()


def _try_empty_cuda_cache():
    """
    Best-effort VRAM release for PyTorch users.
    If torch isn't installed or CUDA isn't available, it's a no-op.
    """
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            # Optional: synchronize to flush kernels; can add overhead
            # torch.cuda.synchronize()
    except Exception:
        # Don't fail the service if torch isn't present or something goes wrong
        pass


def _unload_encoder():
    """
    Best-effort encoder unload.
    For deterministic VRAM release, run model in a separate process and exit it.
    """
    global encoder
    if encoder is None:
        return

    logger.info("Unloading VecSet encoder (idle timeout reached)...")
    try:
        # If your encoder exposes explicit cleanup, call it here:
        # if hasattr(encoder, "close"):
        #     encoder.close()
        # if hasattr(encoder, "shutdown"):
        #     encoder.shutdown()
        pass
    finally:
        encoder = None
        gc.collect()
        _try_empty_cuda_cache()
        logger.info("VecSet encoder unloaded")


async def _ensure_encoder_loaded() -> VecSetEncoder:
    """
    Lazily load the encoder when needed, with a lock to prevent duplicate loads.
    """
    global encoder

    # Fast path
    if encoder is not None and encoder.is_ready():
        _touch_encoder_usage()
        return encoder

    async with _encoder_lock:
        # Re-check inside lock
        if encoder is not None and encoder.is_ready():
            _touch_encoder_usage()
            return encoder

        try:
            logger.info("Loading VecSet encoder (lazy-load)...")
            encoder = VecSetEncoder()
            if not encoder.is_ready():
                # Some encoders may load async or partially - treat as failure
                raise RuntimeError("VecSet encoder initialized but not ready")

            logger.info("VecSet encoder loaded successfully")
            _touch_encoder_usage()
            return encoder

        except Exception as e:
            encoder = None
            logger.error(f"Failed to load encoder: {str(e)}", exc_info=True)
            raise


async def _idle_sweeper_loop():
    """
    Background loop that unloads the encoder after ENCODER_IDLE_SECONDS of inactivity.
    """
    global encoder
    logger.info(
        f"Idle sweeper started (idle={ENCODER_IDLE_SECONDS}s, interval={ENCODER_SWEEP_INTERVAL_SECONDS}s)"
    )
    try:
        while True:
            await asyncio.sleep(ENCODER_SWEEP_INTERVAL_SECONDS)

            # If encoder isn't loaded, nothing to do
            if encoder is None:
                continue

            idle_for = time.time() - _last_used_ts
            if idle_for >= ENCODER_IDLE_SECONDS:
                # Ensure no one is loading/using it while we unload
                async with _encoder_lock:
                    # Re-check after acquiring lock
                    if encoder is None:
                        continue
                    idle_for = time.time() - _last_used_ts
                    if idle_for >= ENCODER_IDLE_SECONDS:
                        _unload_encoder()

    except asyncio.CancelledError:
        logger.info("Idle sweeper cancelled")
        raise
    except Exception as e:
        logger.error(f"Idle sweeper crashed: {str(e)}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """
    Start background sweeper.
    NOTE: We do NOT load the encoder here anymore (lazy-load instead).
    """
    global _sweeper_task, _last_used_ts
    _last_used_ts = time.time()
    _sweeper_task = asyncio.create_task(_idle_sweeper_loop())


@app.on_event("shutdown")
async def shutdown_event():
    """
    Graceful shutdown: stop sweeper and unload encoder.
    """
    global _sweeper_task
    if _sweeper_task is not None:
        _sweeper_task.cancel()
        try:
            await _sweeper_task
        except Exception:
            pass
        _sweeper_task = None

    # Unload encoder on shutdown
    async with _encoder_lock:
        _unload_encoder()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected errors gracefully."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"VecSet conversion failed: {str(exc)}"},
    )


@app.get("/health")
async def health_check():
    """Simple health check."""
    enc = encoder
    encoder_status = "loaded" if (enc is not None and enc.is_ready()) else "not_loaded"
    idle_for = max(0, int(time.time() - _last_used_ts))
    return {
        "status": "healthy" if encoder_status == "loaded" else "degraded",
        "encoder": encoder_status,
        "encoder_idle_for_seconds": idle_for,
        "encoder_idle_timeout_seconds": ENCODER_IDLE_SECONDS,
    }


@app.post("/vecset")
async def convert_to_vecset(
    file: UploadFile = File(...),
    export_reconstruction: bool = Form(False),
):
    """
    Convert PLY file to VecSet representation and return the .npy file.
    """
    if not file.filename or not file.filename.lower().endswith(".ply"):
        raise HTTPException(status_code=400, detail="Only PLY files are supported")

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

        # Ensure encoder loaded (lazy-load)
        try:
            enc = await _ensure_encoder_loaded()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"VecSet encoder not available: {str(e)}")

        # Convert to VecSet
        output_file = temp_dir / f"{conversion_id}.npy"

        result = enc.to_vecset(
            ply_file=ply_file,
            output_path=output_file,
            export_reconstruction=export_reconstruction,
        )

        _touch_encoder_usage()

        logger.info(f"VecSet conversion {conversion_id} completed")

        return FileResponse(
            path=str(output_file),
            filename=f"{Path(file.filename).stem}.npy",
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VecSet conversion {conversion_id} failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"VecSet conversion failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
