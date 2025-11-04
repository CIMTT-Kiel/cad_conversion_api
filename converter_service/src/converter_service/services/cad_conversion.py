"""
CAD Conversion Service

Handles conversion between different CAD formats with basic error handling.
"""

import logging
from pathlib import Path
from typing import Union

import cascadio
import open3d as o3d
import trimesh

logger = logging.getLogger(__name__)


class CADConversionError(Exception):
    """Custom exception for CAD conversion errors."""
    pass




class CADConverter:
    """
    CAD Converter for STEP, JT, OBJ, and STL files.
    Converts to STL or PLY formats.
    """

    # Supported input formats
    SUPPORTED_EXTENSIONS = {".step", ".stp", ".jt", ".obj", ".stl"}
    DEFAULT_POINT_COUNT = 8192

    def __init__(self, input_file: Union[str, Path]):
        """
        Initialize converter with input file.
        
        Args:
            input_file: Path to input CAD file
            
        Raises:
            CADConversionError: If file doesn't exist or format not supported
        """
        self.input_file = Path(input_file)
        self.file_name = self.input_file.stem
        
        # Validate input
        if not self.input_file.exists():
            raise CADConversionError(f"Input file does not exist: {self.input_file}")
        
        if self.input_file.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise CADConversionError(
                f"Unsupported file format: {self.input_file.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
        
        # Create temp directory
        self.temp_dir = self.input_file.parent / "tmp"
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized converter for {self.input_file}")

    def to_stl(self, output_path: Union[str, Path]) -> Path:
        """
        Convert CAD file to STL format.
        
        Args:
            output_path: Where to save the STL file
            
        Returns:
            Path to created STL file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {self.input_file} to STL")
        
        try:
            # Handle STEP files via cascadio
            if self.input_file.suffix.lower() in {".step", ".stp"}:
                # Convert STEP to OBJ first
                temp_obj = self.temp_dir / f"{self.file_name}_temp.obj"
                logger.debug(f"Converting STEP to OBJ: {temp_obj}")
                cascadio.step_to_obj(str(self.input_file), str(temp_obj))
                mesh = trimesh.load(str(temp_obj), file_type="obj")
            else:
                # Load directly for other formats
                mesh = trimesh.load(str(self.input_file))
            
            # Export to STL
            mesh.export(str(output_path), file_type="stl")
            
            if not output_path.exists():
                raise CADConversionError("STL file was not created")
            
            logger.info(f"STL conversion completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"STL conversion failed: {str(e)}")
            raise CADConversionError(f"STL conversion failed: {str(e)}") from e

    def to_ply(self, output_path: Union[str, Path], point_count: int = None) -> Path:
        """
        Convert CAD file to PLY point cloud format.
        
        Args:
            output_path: Where to save the PLY file
            point_count: Number of points to sample (default: 8192) # default according to 3dShapeToVecset Checkpoint.
            
        Returns:
            Path to created PLY fileget_service_status
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if point_count is None:
            point_count = self.DEFAULT_POINT_COUNT
        
        logger.info(f"Converting {self.input_file} to PLY with {point_count} points")
        
        try:
            # First convert to STL if needed
            temp_stl = self.temp_dir / f"{self.file_name}_temp.stl"
            if not temp_stl.exists():
                self.to_stl(temp_stl)
            
            # Load STL with Open3D and sample points
            mesh = o3d.io.read_triangle_mesh(str(temp_stl))
            
            if len(mesh.vertices) == 0:
                raise CADConversionError("No vertices found in mesh")
            
            # Sample point cloud
            point_cloud = mesh.sample_points_uniformly(number_of_points=point_count)
            
            if len(point_cloud.points) == 0:
                raise CADConversionError("Failed to sample points from mesh")
            
            # Save PLY
            success = o3d.io.write_point_cloud(str(output_path), point_cloud)
            
            if not success or not output_path.exists():
                raise CADConversionError("PLY file was not created")
            
            logger.info(f"PLY conversion completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"PLY conversion failed: {str(e)}")
            raise CADConversionError(f"PLY conversion failed: {str(e)}") from e

    def get_info(self) -> dict:
        """Get basic information about the input file."""
        stat = self.input_file.stat()
        return {
            "filename": self.input_file.name,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "format": self.input_file.suffix.lower(),
            "supported": self.input_file.suffix.lower() in self.SUPPORTED_EXTENSIONS
        }