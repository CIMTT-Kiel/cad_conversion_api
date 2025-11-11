"""
CAD Converter Client

Simple client for interacting with CAD conversion services.
Downloads actual files from the services.

Configuration via:
1. Config file (config.yaml)
2. Environment variables
3. Direct parameters
"""

import json
from pathlib import Path
from typing import Optional, Union, Dict, Any

import requests, logging

from client.config.config import ClientConfig


# Setup client logging (call once at module level)

logger = logging.getLogger(__name__)


class CADClientError(Exception):
    """Exception for CAD client errors."""
    pass


class CADConverterClient:
    """
    Client for CAD conversion, embedding, and analysis services.

    Configuration methods (in priority order):
    1. Direct parameters
    2. Environment variables
    3. Config file (config.yaml or config.local.yaml)
    4. Defaults (localhost)

    Examples:
        # Method 1: Using config.yaml (einfachste Methode)
        client = CADConverterClient()

        # Method 2: Mit Host-IP
        client = CADConverterClient(host="172.20.0.1")

        # Method 3: Mit vollständigen URLs
        client = CADConverterClient(
            converter_url="http://172.20.0.1:8001",
            embedding_url="http://172.20.0.1:8002",
            analyser_url="http://172.20.0.1:8003"
        )

        # Method 4: Mit eigener Config-Datei
        client = CADConverterClient(config_file="my_config.yaml")
    """

    def __init__(
        self,
        host: Optional[str] = None,
        converter_url: Optional[str] = None,
        embedding_url: Optional[str] = None,
        analyser_url: Optional[str] = None,
        rendering_url: Optional[str] = None,
        timeout: Optional[int] = None,
        config_file: Optional[str] = None
    ):
        """
        Initialize client with configuration.

        Args:
            host: Server IP or hostname
            converter_url: Full converter service URL (overrides host)
            embedding_url: Full embedding service URL (overrides host)
            analyser_url: Full analyser service URL (overrides host)
            rendering_url: Full rendering service URL (overrides host)
            timeout: Request timeout in seconds
            config_file: Path to custom config file
        """
        # Load configuration
        self.config = ClientConfig(
            host=host,
            converter_url=converter_url,
            embedding_url=embedding_url,
            analyser_url=analyser_url,
            rendering_url=rendering_url,
            timeout=timeout,
            config_file=config_file
        )

        # Set instance variables
        self.converter_url = self.config.converter_url
        self.embedding_url = self.config.embedding_url
        self.analyser_url = self.config.analyser_url
        self.rendering_url = self.config.rendering_url
        self.timeout = self.config.timeout

        logger.info("CAD client initialized successfully")

    def _upload_and_download(
        self,
        url: str,
        file_path: Union[str, Path],
        output_path: Path,
        params: dict = None
    ) -> Path:
        """
        Upload file and download the converted result.
        
        Args:
            url: Service endpoint
            file_path: File to upload
            output_path: Where to save the result
            params: Additional parameters
            
        Returns:
            Path to downloaded file
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise CADClientError(f"File not found: {file_path}")
        
        logger.info(f"Uploading {file_path.name} to {url}")
        
        try:
            # Upload file
            with open(file_path, "rb") as f:
                response = requests.post(
                    url,
                    files={"file": (file_path.name, f)},
                    data=params or {},
                    timeout=self.timeout,
                    stream=True  # Stream for large files
                )
            
            response.raise_for_status()
            
            # Save response to output file
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

    def convert_to_stl(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Convert CAD file to STL format.
        
        Args:
            input_file: Input CAD file
            output_file: Output STL file (optional)
            
        Returns:
            Path to STL file
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}.stl")
        
        if output_path.suffix.lower() != ".stl":
            raise CADClientError("Output file must have .stl extension")
        
        logger.info(f"Converting to STL: {input_path} -> {output_path}")
        
        try:
            return self._upload_and_download(
                f"{self.converter_url}/convert",
                input_path,
                output_path,
                {"target_format": "stl"}
            )
        except Exception as e:
            raise CADClientError(f"STL conversion failed: {str(e)}") from e

    def convert_to_ply(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Convert CAD file to PLY format.
        
        Args:
            input_file: Input CAD file
            output_file: Output PLY file (optional)
            
        Returns:
            Path to PLY file
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}.ply")
        
        if output_path.suffix.lower() != ".ply":
            raise CADClientError("Output file must have .ply extension")
        
        logger.info(f"Converting to PLY: {input_path} -> {output_path}")
        
        try:
            return self._upload_and_download(
                f"{self.converter_url}/convert",
                input_path,
                output_path,
                {"target_format": "ply"}
            )
        except Exception as e:
            raise CADClientError(f"PLY conversion failed: {str(e)}") from e

    def convert_to_vecset(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        export_reconstruction: bool = False
    ) -> Path:
        """
        Convert CAD file to VecSet (Vecset as defined in 3dShapeToVecset Paper).
        
        Args:
            input_file: Input CAD file
            output_file: Output .npy file (optional)
            export_reconstruction: Export reconstructed STL (not supported via CAD service)
            
        Returns:
            Path to .npy file
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}.npy")
        
        if output_path.suffix.lower() != ".npy":
            raise CADClientError("Output file must have .npy extension")
        
        logger.info(f"Converting to VecSet: {input_path} -> {output_path}")
        
        try:
            return self._upload_and_download(
                f"{self.converter_url}/convert",
                input_path,
                output_path,
                {"target_format": "vecset"}
            )
        except Exception as e:
            raise CADClientError(f"VecSet conversion failed: {str(e)}") from e

    def to_voxel(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        resolution: int = 128
    ) -> Path:
        """
        Convert CAD file to voxel representation (sparse format).

        Args:
            input_file: Input CAD file
            output_file: Output .npz file (optional)
            resolution: Voxel grid resolution (default: 128)

        Returns:
            Path to .npz file containing sparse voxel data

        Note:
            The output file contains:
            - indices: Coordinates of occupied voxels (N x 3 array)
            - shape: Shape of the voxel grid (tuple)
            - resolution: Grid resolution

            To load the voxel data:
            ```python
            import numpy as np
            data = np.load('voxel_file.npz')
            indices = data['indices']
            shape = tuple(data['shape'])
            resolution = int(data['resolution'])
            ```
        """
        if not self.converter_url:
            raise CADClientError("Converter service URL not configured")

        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}_voxel.npz")

        if output_path.suffix.lower() != ".npz":
            raise CADClientError("Output file must have .npz extension")

        if resolution < 16 or resolution > 512:
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
        """
        Analyse CAD file and get comprehensive geometry statistics.

        Args:
            input_file: Input STEP file (.step, .stp)
            output_file: Optional output JSON file path. If not provided,
                        will save to same directory as input with _analysis.json suffix

        Returns:
            Analysis results as dictionary containing:
            - metadata: Analysis metadata (id, filename, timestamp)
            - summary: Overall statistics (volume, area, faces, edges, vertices, etc.)
            - bounding_box: Min/max coordinates
            - dimensions: Length, width, height, diagonal
            - center_of_mass: X, Y, Z coordinates
            - surface_type_counts: Dictionary of surface types and their counts
            - edge_statistics: Min/max/average edge lengths
            - validity: Validation checks
            - objects: List of per-object detailed analysis
        """
        if not self.analyser_url:
            raise CADClientError("Analyser service URL not configured")

        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if input_path.suffix.lower() not in [".step", ".stp"]:
            raise CADClientError("Analyser only supports STEP files (.step, .stp)")

        # Determine output file path
        if output_file is None:
            output_path = input_path.parent / f"{input_path.stem}_analysis.json"
        else:
            output_path = Path(output_file)

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

            # Save the JSON file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Load and return the JSON content
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

    def to_multiview(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        render_mode: str = "shaded_with_edges",
        total_imgs: int = 20,
        part_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate multiple views from a CAD file and save them to a directory.

        Args:
            input_file: Input CAD file (STEP format)
            output_dir: Directory to save rendered images
            render_mode: Rendering mode - "shaded_with_edges", "shaded", or "wireframe" (default: "shaded_with_edges")
            total_imgs: Number of views to generate (default: 20)
            part_number: Part number or identifier (optional, defaults to filename)

        Returns:
            Dictionary with rendering results:
            - success: Boolean indicating success
            - images: List of paths to saved images
            - total_images: Number of images generated
            - output_dir: Directory where images were saved

        Example:
            result = client.to_multiview(
                "model.step",
                "./output/renders",
                render_mode="shaded_with_edges",
                total_imgs=20
            )
            print(f"Generated {result['total_images']} views in {result['output_dir']}")
        """
        if not self.rendering_url:
            raise CADClientError("Rendering service URL not configured")

        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if not input_path.suffix.lower() in [".step", ".stp"]:
            raise CADClientError("Rendering service only supports STEP files (.step, .stp)")

        # Use filename as part_number if not provided
        if part_number is None:
            part_number = input_path.stem

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

            # Save images and perspective data to output directory
            import base64
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            saved_images = []
            perspectives = result.get("perspectives", [])

            # Save all images
            for img_data in result.get("images", []):
                filename = img_data.get("filename")
                img_base64 = img_data.get("data")

                if filename and img_base64:
                    # Save image
                    img_path = output_path / filename
                    img_bytes = base64.b64decode(img_base64)
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    saved_images.append(str(img_path))
                    logger.info(f"Saved image: {img_path}")

            # Save all camera/perspective data in a single JSON file
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
        """
        Generate a 3D mesh from a STEP file using Gmsh.

        Args:
            input_file: Input STEP file
            output_file: Output .msh file (optional)
            mesh_size: Optional mesh size parameter for controlling mesh density

        Returns:
            Path to .msh file

        Example:
            # Generate mesh with default settings
            client.to_3d_mesh("model.step", "output.msh")

            # Generate mesh with custom mesh size
            client.to_3d_mesh("model.step", "output.msh", mesh_size=0.5)
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else Path(f"./{input_path.stem}.msh")

        if output_path.suffix.lower() != ".msh":
            raise CADClientError("Output file must have .msh extension")

        logger.info(f"Generating 3D mesh: {input_path} -> {output_path}")

        params = {}
        if mesh_size is not None:
            params["mesh_size"] = str(mesh_size)

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
        """
        Calculate geometric invariants from a 3D mesh file.

        Args:
            input_file: Input mesh file (.msh format)
            output_file: Optional JSON file to save results
            normalized: If True, scale mesh to unit cube (default: False)

        Returns:
            Dictionary with moments and invariants:
            - filename: Input filename
            - normalized: Whether mesh was normalized
            - total_moments: Number of moments calculated
            - total_invariants: Number of invariants calculated
            - moments: Dictionary of moment values (mue_pqr)
            - invariants: Dictionary of invariant values (pi_pqr)

        Example:
            # Calculate invariants from mesh file
            result = client.to_invariants("model.msh")

            # Save to JSON file
            result = client.to_invariants("model.msh", "invariants.json", normalized=True)
        """
        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if input_path.suffix.lower() != ".msh":
            raise CADClientError("Input file must have .msh extension (use to_3d_mesh() first)")

        logger.info(f"Calculating invariants: {input_path}")

        try:
            # Upload mesh file and get invariants
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.converter_url}/invariants",
                    files={"file": (input_path.name, f)},
                    data={"normalized": str(normalized).lower()},
                    timeout=self.timeout
                )

            response.raise_for_status()
            result = response.json()

            # Save to file if requested
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
        """
        Get status of all configured services.

        Returns:
            Service status information for each service
        """
        status = {}

        # Check Converter service
        try:
            response = requests.get(f"{self.converter_url}/health", timeout=10)
            status["converter_service"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "url": self.converter_url
            }
        except Exception as e:
            status["converter_service"] = {
                "status": "unreachable",
                "url": self.converter_url,
                "error": str(e)
            }

        # Check Embedding service if configured
        if self.embedding_url:
            try:
                response = requests.get(f"{self.embedding_url}/health", timeout=10)
                status["embedding_service"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": self.embedding_url
                }
            except Exception as e:
                status["embedding_service"] = {
                    "status": "unreachable",
                    "url": self.embedding_url,
                    "error": str(e)
                }

        # Check Analyser service if configured
        if self.analyser_url:
            try:
                response = requests.get(f"{self.analyser_url}/health", timeout=10)
                status["analyser_service"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": self.analyser_url
                }
            except Exception as e:
                status["analyser_service"] = {
                    "status": "unreachable",
                    "url": self.analyser_url,
                    "error": str(e)
                }

        # Check Rendering service if configured
        if self.rendering_url:
            try:
                response = requests.get(f"{self.rendering_url}/health", timeout=10)
                status["rendering_service"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": self.rendering_url
                }
            except Exception as e:
                status["rendering_service"] = {
                    "status": "unreachable",
                    "url": self.rendering_url,
                    "error": str(e)
                }

        return status