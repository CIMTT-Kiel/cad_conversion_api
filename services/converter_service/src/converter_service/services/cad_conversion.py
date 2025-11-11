"""CAD Conversion Service - Handles conversion between CAD formats."""

import glob
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Union

import cascadio
import numpy as np
import open3d as o3d
import trimesh
from PIL import Image
from scipy import sparse
import stltovoxel

logger = logging.getLogger(__name__)


class CADConversionError(Exception):
    """Custom exception for CAD conversion errors."""
    pass


class CADConverter:
    """CAD Converter for STEP, JT, OBJ, and STL files to STL, PLY, or voxel formats."""

    SUPPORTED_EXTENSIONS = {".step", ".stp", ".jt", ".obj", ".stl"}
    DEFAULT_POINT_COUNT = 8192

    def __init__(self, input_file: Union[str, Path]):
        """Initialize converter with input file."""
        self.input_file = Path(input_file)
        self.file_name = self.input_file.stem

        if not self.input_file.exists():
            raise CADConversionError(f"Input file does not exist: {self.input_file}")

        if self.input_file.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise CADConversionError(
                f"Unsupported file format: {self.input_file.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        self.temp_dir = self.input_file.parent / "tmp"
        self.temp_dir.mkdir(exist_ok=True)
        logger.info(f"Initialized converter for {self.input_file}")

    def to_stl(self, output_path: Union[str, Path]) -> Path:
        """Convert CAD file to STL format."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Converting to STL: {self.input_file}")

        try:
            if self.input_file.suffix.lower() in {".step", ".stp"}:
                temp_obj = self.temp_dir / f"{self.file_name}_temp.obj"
                cascadio.step_to_obj(str(self.input_file), str(temp_obj))
                mesh = trimesh.load(str(temp_obj), file_type="obj")
            else:
                mesh = trimesh.load(str(self.input_file))

            mesh.export(str(output_path), file_type="stl")

            if not output_path.exists():
                raise CADConversionError("STL file was not created")

            logger.info(f"STL completed: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"STL conversion failed: {str(e)}")
            raise CADConversionError(f"STL conversion failed: {str(e)}") from e

    def to_ply(self, output_path: Union[str, Path], point_count: int = None) -> Path:
        """Convert CAD file to PLY point cloud (default: 8192 points)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if point_count is None:
            point_count = self.DEFAULT_POINT_COUNT

        logger.info(f"Converting to PLY: {point_count} points")

        try:
            temp_stl = self.temp_dir / f"{self.file_name}_temp.stl"
            if not temp_stl.exists():
                self.to_stl(temp_stl)

            mesh = o3d.io.read_triangle_mesh(str(temp_stl))
            if len(mesh.vertices) == 0:
                raise CADConversionError("No vertices found in mesh")

            point_cloud = mesh.sample_points_uniformly(number_of_points=point_count)
            if len(point_cloud.points) == 0:
                raise CADConversionError("Failed to sample points from mesh")

            success = o3d.io.write_point_cloud(str(output_path), point_cloud)
            if not success or not output_path.exists():
                raise CADConversionError("PLY file was not created")

            logger.info(f"PLY completed: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"PLY conversion failed: {str(e)}")
            raise CADConversionError(f"PLY conversion failed: {str(e)}") from e

    def to_voxel(self, output_path: Union[str, Path], resolution: int = 128) -> Path:
        """Convert CAD file to sparse voxel representation (.npz format)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Converting to voxels: resolution {resolution}")

        try:
            temp_stl = self.temp_dir / f"{self.file_name}_temp.stl"
            if not temp_stl.exists():
                self.to_stl(temp_stl)

            slices_dir = self.temp_dir / "slices_temp"
            slices_dir.mkdir(exist_ok=True)
            temp_slice_pattern = slices_dir / "slice.png"

            try:
                old_stdout = sys.stdout
                sys.stdout = open(os.devnull, 'w')
                stltovoxel.convert_file(str(temp_stl), str(temp_slice_pattern), resolution)
                sys.stdout.close()
                sys.stdout = old_stdout
            except Exception as e:
                sys.stdout = old_stdout
                raise CADConversionError(f"Voxel slice generation failed: {str(e)}")

            slice_files = sorted(glob.glob(str(slices_dir / "*.png")))
            if not slice_files:
                raise CADConversionError("No voxel slices generated")

            logger.info(f"Generated {len(slice_files)} slices")

            voxel_slices = []
            for slice_file in slice_files:
                image = Image.open(slice_file)
                image = self._expand_to_square(image, 0)
                image = image.resize((resolution, resolution), Image.Resampling.NEAREST)
                voxel_slices.append(np.array(image, dtype=np.uint8))

            voxel_array = np.array(voxel_slices, dtype=np.uint8)
            voxel_binary = (voxel_array > 0).astype(np.uint8)
            occupied_indices = np.argwhere(voxel_binary)

            np.savez_compressed(output_path, indices=occupied_indices, shape=voxel_binary.shape,
                              resolution=resolution, format_version="1.0")

            shutil.rmtree(slices_dir, ignore_errors=True)

            if not output_path.exists():
                raise CADConversionError("Voxel file was not created")

            occupancy = len(occupied_indices) / np.prod(voxel_binary.shape) * 100
            logger.info(f"Voxel completed: {output_path} (shape: {voxel_binary.shape}, occupancy: {occupancy:.2f}%)")
            return output_path

        except Exception as e:
            logger.error(f"Voxel conversion failed: {str(e)}")
            if 'slices_dir' in locals():
                shutil.rmtree(slices_dir, ignore_errors=True)
            raise CADConversionError(f"Voxel conversion failed: {str(e)}") from e

    @staticmethod
    def _expand_to_square(pil_img: Image.Image, background_color) -> Image.Image:
        """Expand image to square with padding."""
        width, height = pil_img.size
        if width == height:
            return pil_img
        elif width > height:
            result = Image.new(pil_img.mode, (width, width), background_color)
            result.paste(pil_img, (0, (width - height) // 2))
            return result
        else:
            result = Image.new(pil_img.mode, (height, height), background_color)
            result.paste(pil_img, ((height - width) // 2, 0))
            return result

    def get_info(self) -> dict:
        """Get basic information about the input file."""
        stat = self.input_file.stat()
        return {
            "filename": self.input_file.name,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "format": self.input_file.suffix.lower(),
            "supported": self.input_file.suffix.lower() in self.SUPPORTED_EXTENSIONS
        }