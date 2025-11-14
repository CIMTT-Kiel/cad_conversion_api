"""CAD Converter Client - Interface for CAD-preprocessing-microservices"""

import json
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any

import requests

from client.config.config import ClientConfig

logger = logging.getLogger(__name__)


class CADClientError(Exception):
    """CAD client operation error."""
    pass


class CADConverterClient:
    """
    Client for CAD preprocessing microservices.

    Parameters are set by the config file. Given parameters override config file values.

    Parameters
    ----------
    host : Optional[str]
        Base host for services (overridden by individual service URLs).
    converter_url : Optional[str]
    embedding_url : Optional[str]
    analyser_url : Optional[str]
    rendering_url : Optional[str]
    timeout : Optional[int]
        Request timeout in seconds.
    config_file : Optional[str]
        Path to YAML config file.
    """

    def __init__(self, host: Optional[str] = None, converter_url: Optional[str] = None,
                 embedding_url: Optional[str] = None, analyser_url: Optional[str] = None,
                 rendering_url: Optional[str] = None, timeout: Optional[int] = None,
                 config_file: Optional[str] = None):
        """Initialize client with configuration from params, env vars, or config file."""
        config = ClientConfig(host, converter_url, embedding_url, analyser_url,
                            rendering_url, timeout, config_file)

        self.converter_url = config.converter_url
        self.embedding_url = config.embedding_url
        self.analyser_url = config.analyser_url
        self.rendering_url = config.rendering_url
        self.timeout = config.timeout

        logger.info("CAD client initialized")

    def _upload_and_download(
        self,
        url: str,
        file_path: Union[str, Path],
        output_path: Path,
        params: dict = None
    ) -> Path:
        """Upload file and download the result."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise CADClientError(f"File not found: {file_path}")

        logger.info(f"Uploading {file_path.name} to {url}")

        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    url,
                    files={"file": (file_path.name, f)},
                    data=params or {},
                    timeout=self.timeout,
                    stream=True
                )

            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if not output_path.exists():
                raise CADClientError(f"Failed to save result to {output_path}")

            logger.info(f"Result saved: {output_path}")
            return output_path

        except requests.RequestException as e:
            raise CADClientError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise CADClientError(f"Download failed: {str(e)}") from e

    def _convert_format(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]],
        target_format: str,
        extension: str
    ) -> Path:
        """Generic conversion method for different formats."""
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}.{extension}")

        if output_path.suffix.lower() != f".{extension}":
            raise CADClientError(f"Output file must have .{extension} extension")

        logger.info(f"Converting to {target_format.upper()}: {input_path} -> {output_path}")

        try:
            return self._upload_and_download(
                f"{self.converter_url}/convert",
                input_path,
                output_path,
                {"target_format": target_format}
            )
        except Exception as e:
            raise CADClientError(f"{target_format.upper()} conversion failed: {str(e)}") from e

    def convert_to_stl(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Path:
        """Convert CAD file to STL format."""
        return self._convert_format(input_file, output_file, "stl", "stl")

    def convert_to_ply(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Path:
        """Convert CAD file to PLY format."""
        return self._convert_format(input_file, output_file, "ply", "ply")

    def convert_to_vecset(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        export_reconstruction: bool = False
    ) -> Path:
        """Convert CAD file to VecSet (as defined in 3dShapeToVecset Paper)."""
        return self._convert_format(input_file, output_file, "vecset", "npy")

    def to_voxel(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        resolution: int = 128
    ) -> Path:
        """Convert CAD file to sparse voxel representation (.npz)"""
        if not self.converter_url:
            raise CADClientError("Converter service URL not configured")

        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}_voxel.npz")

        if output_path.suffix.lower() != ".npz":
            raise CADClientError("Output file must have .npz extension")

        if not 16 <= resolution <= 512:
            raise CADClientError("Resolution must be between 16 and 512")

        logger.info(f"Converting to voxel: {input_path} -> {output_path} (resolution: {resolution})")

        try:
            return self._upload_and_download(
                f"{self.converter_url}/to_voxel",
                input_path,
                output_path,
                {"resolution": str(resolution)}
            )
        except Exception as e:
            raise CADClientError(f"Voxel conversion failed: {str(e)}") from e

    def analyse_cad(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Analyse CAD file - returns geometry statistics, such as bounding box, dimensions, surface types etc."""
        if not self.analyser_url:
            raise CADClientError("Analyser service URL not configured")

        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if input_path.suffix.lower() not in [".step", ".stp"]:
            raise CADClientError("Analyser only supports STEP files (.step, .stp)")

        output_path = Path(output_file) if output_file else input_path.parent / f"{input_path.stem}_analysis.json"
        logger.info(f"Analysing: {input_path}")

        try:
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.analyser_url}/analyse",
                    files={"file": (input_path.name, f)},
                    timeout=self.timeout,
                    stream=True
                )

            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            with open(output_path, "r") as f:
                result = json.load(f)

            logger.info(f"Analysis completed and saved to: {output_path}")
            logger.info(f"Total volume: {result.get('summary', {}).get('total_volume', 0)}")
            logger.info(f"Total surfaces: {result.get('summary', {}).get('total_faces', 0)}")

            return result

        except requests.RequestException as e:
            raise CADClientError(f"Analysis request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise CADClientError(f"Invalid JSON in analysis file: {str(e)}") from e
        except Exception as e:
            raise CADClientError(f"Analysis failed: {str(e)}") from e

    def to_drawing_views(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path]
    ) -> Dict[str, Any]:
        """Generate orthographic drawing views (top, front, side) as DXF files."""
        import zipfile

        if not self.analyser_url:
            raise CADClientError("Analyser service URL not configured")

        input_path = Path(input_file)
        output_path = Path(output_dir)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if input_path.suffix.lower() not in [".step", ".stp"]:
            raise CADClientError("Drawing views only support STEP files (.step, .stp)")

        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating drawing views: {input_path}")

        try:
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.analyser_url}/to_drawing_views",
                    files={"file": (input_path.name, f)},
                    timeout=self.timeout,
                    stream=True
                )

            response.raise_for_status()

            zip_file = output_path / f"{input_path.stem}_drawing_views.zip"
            with open(zip_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(output_path)

            extracted_files = list(output_path.glob("*.dxf"))
            view_names = [f.stem for f in extracted_files]

            try:
                zip_file.unlink()
                logger.debug(f"Removed ZIP file: {zip_file}")
            except Exception as e:
                logger.warning(f"Failed to remove ZIP file: {str(e)}")

            logger.info(f"Drawing views generated: {len(view_names)} DXF views saved to {output_path}")

            return {
                "success": True,
                "views": view_names,
                "output_dir": str(output_path),
                "total_views": len(view_names)
            }

        except requests.RequestException as e:
            raise CADClientError(f"Drawing views request failed: {str(e)}") from e
        except zipfile.BadZipFile as e:
            raise CADClientError(f"Invalid ZIP file received: {str(e)}") from e
        except Exception as e:
            raise CADClientError(f"Drawing views generation failed: {str(e)}") from e

    def to_multiview(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        render_mode: str = "shaded_with_edges",
        total_imgs: int = 20,
        part_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate multiple views. Modes: shaded_with_edges, shaded, wireframe."""
        import base64

        if not self.rendering_url:
            raise CADClientError("Rendering service URL not configured")

        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if input_path.suffix.lower() not in [".step", ".stp"]:
            raise CADClientError("Rendering service only supports STEP files (.step, .stp)")

        part_number = part_number or input_path.stem
        logger.info(f"Generating multiview: {input_path} (mode: {render_mode}, views: {total_imgs})")

        try:
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.rendering_url}/render",
                    files={"file": (input_path.name, f)},
                    data={
                        "part_number": part_number,
                        "render_mode": render_mode,
                        "total_imgs": total_imgs
                    },
                    timeout=self.timeout
                )

            response.raise_for_status()
            result = response.json()

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            saved_images = []
            perspectives = result.get("perspectives", [])

            for img_data in result.get("images", []):
                filename = img_data.get("filename")
                img_base64 = img_data.get("data")

                if filename and img_base64:
                    img_path = output_path / filename
                    img_bytes = base64.b64decode(img_base64)
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    saved_images.append(str(img_path))
                    logger.info(f"Saved image: {img_path}")

            if perspectives:
                camera_data_path = output_path / "camera_data.json"
                with open(camera_data_path, "w") as f:
                    json.dump({
                        "total_images": len(perspectives),
                        "render_mode": render_mode,
                        "part_number": part_number,
                        "perspectives": perspectives
                    }, f, indent=2)
                logger.info(f"Saved camera data: {camera_data_path}")

            result["images"] = saved_images
            result["output_dir"] = str(output_path)

            logger.info(f"Multiview generation completed: {result.get('total_images', 0)} images saved to {output_path}")
            return result

        except requests.RequestException as e:
            raise CADClientError(f"Multiview generation request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise CADClientError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            raise CADClientError(f"Multiview generation failed: {str(e)}") from e

    def to_3d_mesh(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        mesh_size: Optional[float] = None
    ) -> Path:
        """Generate a 3D mesh from a STEP file using Gmsh."""
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}.msh")

        if output_path.suffix.lower() != ".msh":
            raise CADClientError("Output file must have .msh extension")

        logger.info(f"Generating 3D mesh: {input_path} -> {output_path}")

        params = {"mesh_size": str(mesh_size)} if mesh_size is not None else {}

        try:
            return self._upload_and_download(
                f"{self.converter_url}/mesh",
                input_path,
                output_path,
                params
            )
        except Exception as e:
            raise CADClientError(f"3D mesh generation failed: {str(e)}") from e

    def to_invariants(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        normalized: bool = False
    ) -> Dict[str, Any]:
        """Calculate geometric invariants from .msh file - returns moments and invariants with trivial second moments to validate conversion."""
        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if input_path.suffix.lower() != ".msh":
            raise CADClientError("Input file must have .msh extension (use to_3d_mesh() first)")

        logger.info(f"Calculating invariants: {input_path}")

        try:
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.converter_url}/invariants",
                    files={"file": (input_path.name, f)},
                    data={"normalized": str(normalized).lower()},
                    timeout=self.timeout
                )

            response.raise_for_status()
            result = response.json()

            if output_file:
                output_path = Path(output_file)
                if output_path.suffix.lower() != ".json":
                    output_path = output_path.with_suffix(".json")

                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w") as f:
                    json.dump(result, f, indent=2)

                logger.info(f"Invariants saved to: {output_path}")

            logger.info(f"Calculated {result.get('total_moments', 0)} moments and {result.get('total_invariants', 0)} invariants")
            return result

        except requests.RequestException as e:
            raise CADClientError(f"Invariants calculation request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise CADClientError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            raise CADClientError(f"Invariants calculation failed: {str(e)}") from e

    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured services."""
        status = {}
        services = [
            ("converter_service", self.converter_url),
            ("embedding_service", self.embedding_url),
            ("analyser_service", self.analyser_url),
            ("rendering_service", self.rendering_url)
        ]

        for name, url in services:
            if url:
                try:
                    response = requests.get(f"{url}/health", timeout=10)
                    status[name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "url": url
                    }
                except Exception as e:
                    status[name] = {"status": "unreachable", "url": url, "error": str(e)}

        return status