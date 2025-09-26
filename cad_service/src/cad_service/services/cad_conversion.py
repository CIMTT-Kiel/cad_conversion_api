import logging
from pathlib import Path
from typing import Union

import trimesh
import open3d as o3d
import cascadio

logger = logging.getLogger(__name__)


class CADConverter:
    """
    CAD Converter handling STEP, JT, OBJ, and STL as input.
    Converts into STL or PLY.
    """

    def __init__(self, input_file: Path, skip_existing: bool = False):
        self.input_file = Path(input_file)
        self.file_name = self.input_file.stem
        self.skip_existing = skip_existing
        self.tmp_dir = self.input_file.parent / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def to_stl(self, output_path: Union[str, Path]):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and self.skip_existing:
            logger.info(f"STL exists, skipping: {output_path}")
            return

        logger.info(f"Converting {self.input_file} to STL...")

        # STEP -> OBJ via cascadio, then to STL
        if self.input_file.suffix.lower() == ".step":
            tmp_obj = self.tmp_dir / "tmp.obj"
            cascadio.step_to_obj(str(self.input_file), str(tmp_obj))
            mesh = trimesh.load(tmp_obj, file_type="obj")
        else:
            mesh = trimesh.load(self.input_file)

        mesh.export(str(output_path), file_type="stl")
        logger.info(f"Saved STL at {output_path}")

    def to_ply(self, output_path: Union[str, Path]):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and self.skip_existing:
            logger.info(f"PLY exists, skipping: {output_path}")
            return

        tmp_stl = self.tmp_dir / "tmp.stl"
        if not tmp_stl.exists():
            self.to_stl(tmp_stl)

        mesh = o3d.io.read_triangle_mesh(str(tmp_stl))
        pcd = o3d.geometry.TriangleMesh.sample_points_uniformly(mesh, number_of_points=8192)
        o3d.io.write_point_cloud(str(output_path), pcd)
        logger.info(f"Saved PLY at {output_path}")
