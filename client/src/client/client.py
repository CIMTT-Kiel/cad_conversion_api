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
        timeout: Optional[int] = None,
        config_file: Optional[str] = None
    ):
        """
        Initialize client with configuration.

        Args:
            host: Server IP or hostname (e.g., "172.20.0.1")
            converter_url: Full converter service URL (overrides host)
            embedding_url: Full embedding service URL (overrides host)
            analyser_url: Full analyser service URL (overrides host)
            timeout: Request timeout in seconds
            config_file: Path to custom config file
        """
        # Load configuration
        self.config = ClientConfig(
            host=host,
            converter_url=converter_url,
            embedding_url=embedding_url,
            analyser_url=analyser_url,
            timeout=timeout,
            config_file=config_file
        )

        # Set instance variables
        self.converter_url = self.config.converter_url
        self.embedding_url = self.config.embedding_url
        self.analyser_url = self.config.analyser_url
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

    def analyse_cad(
        self,
        input_file: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Analyse CAD file and get geometry statistics.

        Args:
            input_file: Input STEP file (.step, .stp)

        Returns:
            Analysis results as dictionary with:
            - analysis_id: Unique analysis ID
            - filename: Input filename
            - total_surfaces: Number of surfaces
            - total_area: Total surface area
            - surface_type_counts: Dict of surface types and counts
            - surfaces: List of detailed surface information
        """
        if not self.analyser_url:
            raise CADClientError("Analyser service URL not configured")

        input_path = Path(input_file)

        if not input_path.exists():
            raise CADClientError(f"File not found: {input_path}")

        if not input_path.suffix.lower() in [".step", ".stp"]:
            raise CADClientError("Analyser only supports STEP files (.step, .stp)")

        logger.info(f"Analysing: {input_path}")

        try:
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.analyser_url}/analyse",
                    files={"file": (input_path.name, f)},
                    timeout=self.timeout
                )

            response.raise_for_status()

            result = response.json()
            logger.info(f"Analysis completed: {result.get('total_surfaces', 0)} surfaces found")
            return result

        except requests.RequestException as e:
            raise CADClientError(f"Analysis request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise CADClientError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            raise CADClientError(f"Analysis failed: {str(e)}") from e

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

        return status