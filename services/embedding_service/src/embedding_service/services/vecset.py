"""
VecSet Encoder Service

Converts PLY point cloud files to VecSet representation using pre-trained models.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Union

import mcubes
import numpy as np
import torch
import trimesh

from embedding_service.models import autoencoder

logger = logging.getLogger(__name__)

# configure logger
logging.basicConfig(level=logging.INFO)



class VecSetError(Exception):
    """Custom exception for VecSet conversion errors."""
    pass


class VecSetEncoder:
    """
    Converts PLY files to VecSet representation using deep learning models.
    """

    REQUIRED_POINT_COUNT = 8192
    DEFAULT_DENSITY = 256

    def __init__(self, model_path: Optional[Union[str, Path]] = None):
        """
        Initialize VecSet encoder.
        
        Args:
            model_path: Path to model checkpoint (optional)
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Set model path
        if model_path:
            self.model_path = Path(model_path)
        else:            
            self.model_path = "src/embedding_service/models/ckpts/checkpoint-110.pth"

            
        if not self.model_path:
            raise VecSetError(f"Vecset Encoder-Model not found!")
        
        # Load model
        self._load_model()
        
        # Setup grid for reconstruction
        self.density = self.DEFAULT_DENSITY
        self.gap = 2.0 / self.density
        self.grid = self._create_grid()
        
        logger.info("VecSet encoder initialized successfully")

    def _load_model(self):
        """Load the pre-trained model."""
        try:
            # Create model
            self.encoder = autoencoder.point_vec1024x32_dim1024_depth24_nb(
                pc_size=self.REQUIRED_POINT_COUNT
            )
            self.encoder.eval()
            
            # Load weights
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
            
            if "model" in checkpoint:
                state_dict = checkpoint["model"]
            else:
                state_dict = checkpoint
            
            self.encoder.load_state_dict(state_dict, strict=False)
            self.encoder.to(self.device)
            
            self.model_loaded = True
            logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            raise VecSetError(f"Failed to load model: {str(e)}") from e

    def _create_grid(self) -> torch.Tensor:
        """Create 3D grid for reconstruction."""
        x = np.linspace(-1, 1, self.density + 1)
        y = np.linspace(-1, 1, self.density + 1)
        z = np.linspace(-1, 1, self.density + 1)
        xv, yv, zv = np.meshgrid(x, y, z)
        
        return torch.from_numpy(
            np.stack([xv, yv, zv]).astype(np.float32)
        ).view(3, -1).transpose(0, 1)[None]

    def _preprocess_point_cloud(self, surface: np.ndarray) -> torch.Tensor:
        """
        Preprocess point cloud for model input.
        
        Args:
            surface: Point cloud vertices
            
        Returns:
            Preprocessed tensor
        """
        if surface.shape[0] != self.REQUIRED_POINT_COUNT:
            raise VecSetError(
                f"Point cloud must have {self.REQUIRED_POINT_COUNT} points, got {surface.shape[0]}"
            )
        
        # Center and normalize
        shifts = (surface.max(axis=0) + surface.min(axis=0)) / 2
        surface = surface - shifts
        
        distances = np.linalg.norm(surface, axis=1)
        scale = 1 / np.max(distances)
        surface *= scale
        
        return torch.from_numpy(surface.astype(np.float32)).to(self.device)

    def to_vecset(
        self,
        ply_file: Union[str, Path],
        output_path: Union[str, Path],
        export_reconstruction: bool = False
    ) -> Dict:
        """
        Convert PLY file to VecSet representation.
        
        Args:
            ply_file: Input PLY file
            output_path: Output .npy file path
            export_reconstruction: Whether to export reconstructed STL
            
        Returns:
            Conversion results and metadata
        """
        ply_file = Path(ply_file)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting PLY to VecSet: {ply_file}")
        
        try:
            # Load PLY file
            mesh = trimesh.load(str(ply_file))
            
            if not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
                raise VecSetError("PLY file contains no vertices")
            
            surface = mesh.vertices
            
            if len(surface) != self.REQUIRED_POINT_COUNT:
                raise VecSetError(f"Expected {self.REQUIRED_POINT_COUNT} points, got {len(surface)}")
            
            # Preprocess
            surface_tensor = self._preprocess_point_cloud(surface)
            
            # Generate VecSet
            with torch.no_grad():
                if export_reconstruction:
                    # Full forward pass with reconstruction
                    outputs = self.encoder(surface_tensor[None], self.grid.to(self.device))
                    vecset_data = outputs["x"].squeeze(0).cpu().numpy()
                    
                    # Generate reconstruction
                    volume = outputs["o"][0].view(
                        self.density + 1, self.density + 1, self.density + 1
                    ).permute(1, 0, 2).cpu().numpy() * (-1)
                    
                    verts, faces = mcubes.marching_cubes(volume, 0)
                    verts *= self.gap
                    verts -= 1.0
                    
                    # Save reconstruction
                    reconstruction_file = output_path.with_name(
                        output_path.stem + "_reconstruction.stl"
                    )
                    reconstruction_mesh = trimesh.Trimesh(verts, faces)
                    reconstruction_mesh.export(str(reconstruction_file), file_type="stl")
                    
                else:
                    # Just encode to VecSet
                    outputs = self.encoder.encode_to_vecset(surface_tensor[None])
                    vecset_data = outputs["x"].squeeze(0).cpu().numpy()
                    reconstruction_file = None
            
            # Save VecSet
            np.save(str(output_path), vecset_data)
            
            # Prepare result
            result = {
                "metadata": {
                    "shape": vecset_data.shape,
                    "dtype": str(vecset_data.dtype),
                    "point_count": len(surface)
                }
            }
            
            if reconstruction_file:
                result["reconstruction_file"] = str(reconstruction_file)
            
            logger.info(f"VecSet conversion completed: {output_path}")
            return result
            
        except Exception as e:
            logger.error(f"VecSet conversion failed: {str(e)}")
            raise VecSetError(f"VecSet conversion failed: {str(e)}") from e

    def is_ready(self) -> bool:
        """Check if encoder is ready."""
        return hasattr(self, 'model_loaded') and self.model_loaded