import requests
from pathlib import Path
import shutil
import tempfile

class CADConverterClient:
    """
    Provides functions to convert CAD data for ML Pipelines via FastAPI Services. 

    Args:
        cad_url (str): URL of the CAD conversion service.
        vecset_url (str): URL of the VecSet conversion service.
    Example:
        client = CADClient(cad_url="http://localhost:8000", vecset_url="http://localhost:8001")
        stl_file = client.convert_to_stl("model.step", "target_path/model.stl")
    """

    def __init__(self, cad_url: str, vecset_url: str):
        self.cad_url = cad_url.rstrip("/")
        self.vecset_url = vecset_url.rstrip("/")

    def _upload_file(self, url: str, file_path: Path, params: dict = None):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"{file_path} does not exist")

        with open(file_path, "rb") as f:
            response = requests.post(url, files={"file": f}, params=params)
        response.raise_for_status()
        return response.json()
    
    def _extract_filename(self, file_path: str, suffix : str) -> str:
        return Path("./") / Path(file_path).with_suffix(suffix).name

    def convert_to_stl(self, input_file: str, output_file: str = None):
        """
        Convert CAD-Geometry file to STL.
        """
        result = self._upload_file(f"{self.cad_url}/convert", input_file, params={"target_format": "stl"})
        converted_file = Path(result["file"])

        output_file = Path(output_file) if output_file else self._extract_filename(input_file, ".stl")
        assert output_file.suffix == ".stl", "Output file must have .stl extension"

        shutil.copy(converted_file, output_file)

        return output_file

    def convert_to_ply(self, input_file: str, output_file: str = None):
        """
        Convert CAD file to PLY.
        """
        
        result = self._upload_file(f"{self.cad_url}/convert", input_file, params={"target_format": "ply"})
        converted_file = Path(result["file"])

        output_file = Path(output_file) if output_file else self._extract_filename(input_file, ".ply")
        assert output_file.suffix == ".ply", "Output file must have .ply extension"

        shutil.copy(converted_file, output_file)
        return output_file

    def convert_to_vecset(self, input_file: str, output_file: str = None, export_reconstruction: bool = False):
        """
        Convert CAD file (STEP, JT, OBJ, STL) to VecSet (.npy).
        Optionally export reconstructed STL.
        """
        output_file = Path(output_file) if output_file else self._extract_filename(input_file, ".npy")
        assert output_file.suffix == ".npy", "Output file must have .ply extension"

        result = self._upload_file(
            f"{self.cad_url}/convert",
            input_file,
            params={"target_format": "vecset"}
        )

        # The response may contain path to npy file from VecSet service
        npy_file = Path(result["file"])

        shutil.copy(npy_file, output_file)
        return output_file
