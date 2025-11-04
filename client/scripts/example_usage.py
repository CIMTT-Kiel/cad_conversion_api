from client import CADConverterClient
import numpy as np

converter = CADConverterClient(
    converter_url="http://localhost:8001",
    embedding_url="http://localhost:8002"
)

#print(converter.get_service_status())

# Convert STEP file to STL
path = converter.convert_to_stl("/Users/mkruse/Documents/repos/cad_preprocessing_api/data/testpart.step")
print(f"STL saved at {path.absolute()}")

