"""
CAD Converter Client

Simple client for interacting with CAD conversion services.
Downloads actual files from the services.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union

import requests

logger = logging.getLogger(__name__)


class CADClientError(Exception):
    """Exception for CAD client errors."""
    pass


class CADConverterClient:
    """
    Simple client for CAD conversion services.
    
    Example:
        client = CADConverterClient(
            converter_url="http://localhost:8001",
            embedding_url="http://localhost:8002"
        )
        stl_file = client.convert_to_stl("model.step", "output.stl")
    """

    def __init__(self, converter_url: str, embedding_url: Optional[str] = None, timeout: int = 300):
        """
        Initialize client.
        
        Args:
            converter_url: CAD service URL
            embedding_url: VecSet service URL (optional)
            timeout: Request timeout in seconds
        """
        self.converter_url = converter_url.rstrip("/")
        self.embedding_url = embedding_url.rstrip("/") if embedding_url else None
        self.timeout = timeout
        
        logger.info(f"CAD client initialized: {self.converter_url}")

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

    def get_service_status(self) -> dict:
        """
        Get status of connected services.
        
        Returns:
            Service status information
        """
        status = {}
        
        # Check CAD service
        try:
            response = requests.get(f"{self.converter_url}/health", timeout=10)
            status["cad_service"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "url": self.converter_url
            }
        except Exception as e:
            status["cad_service"] = {
                "status": "unreachable",
                "url": self.converter_url,
                "error": str(e)
            }
        
        # Check VecSet service if configured
        if self.embedding_url:
            try:
                response = requests.get(f"{self.embedding_url}/health", timeout=10)
                status["vecset_service"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": self.embedding_url
                }
            except Exception as e:
                status["vecset_service"] = {
                    "status": "unreachable",
                    "url": self.embedding_url,
                    "error": str(e)
                }
        
        return status