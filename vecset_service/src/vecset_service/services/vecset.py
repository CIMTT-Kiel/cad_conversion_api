import logging
from pathlib import Path
from typing import Union
import numpy as np
import torch
import trimesh
import mcubes

from vecset_service.models import autoencoder 

logger = logging.getLogger(__name__)


class VecSetEncoder:
    """
    Converts PLY files into VecSet representation.
    """

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = r"src/vecset_service/models/ckpts/checkpoint-110.pth"  # mount this via Docker
        self.encoder = autoencoder.__dict__["point_vec1024x32_dim1024_depth24_nb"]()
        self.encoder.eval()
        self.encoder.load_state_dict(
            torch.load(self.model_path, map_location="cpu", weights_only=False)["model"], strict=False
        )
        self.encoder.to(self.device)

        self.density = 256
        self.gap = 2.0 / self.density
        self.grid = self._create_grid()

    def _create_grid(self):
        x = np.linspace(-1, 1, self.density + 1)
        y = np.linspace(-1, 1, self.density + 1)
        z = np.linspace(-1, 1, self.density + 1)
        xv, yv, zv = np.meshgrid(x, y, z)
        return torch.from_numpy(np.stack([xv, yv, zv]).astype(np.float32)).view(3, -1).transpose(0, 1)[None].cpu()

    def to_vecset(self, ply_file: Path, output_path: Union[str, Path], export_reconstruction: bool = False):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Converting {ply_file} to VecSet...")

        surface = trimesh.load(ply_file.as_posix()).vertices
        assert surface.shape[0] == 8192, "Point cloud must have 8192 points"

        shifts = (surface.max(axis=0) + surface.min(axis=0)) / 2
        surface = surface - shifts
        distances = np.linalg.norm(surface, axis=1)
        scale = 1 / np.max(distances)
        surface *= scale
        surface = torch.from_numpy(surface.astype(np.float32)).to(self.device)

        with torch.no_grad():
            if export_reconstruction:
                outputs = self.encoder(surface[None], self.grid.to(self.device))
                volume = outputs["o"][0].view(
                    self.density + 1, self.density + 1, self.density + 1
                ).permute(1, 0, 2).cpu().numpy() * (-1)
                verts, faces = mcubes.marching_cubes(volume, 0)
                verts *= self.gap
                verts -= 1.0
                m = trimesh.Trimesh(verts, faces)
                m.export(output_path.with_name(output_path.stem + "_reconstruction.stl"), file_type="stl")
            else:
                outputs = self.encoder.encode_to_vecset(surface[None])

            np.save(output_path.as_posix(), outputs["x"].squeeze(0).cpu().numpy())
            logger.info(f"VecSet saved at {output_path}")
