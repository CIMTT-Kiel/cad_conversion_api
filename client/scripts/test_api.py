"""
API Testing Script
Tests all CAD Conversion API functionalities 
"""

from pathlib import Path
from client.client import CADConverterClient, CADClientError
import logging
import time

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Get scripts directory and setup paths
SCRIPT_DIR = Path(__file__).parent
SAMPLE_FILE = SCRIPT_DIR / "geometry_00000005.STEP"
OUTPUT_DIR = SCRIPT_DIR / "test_outputs"


class TestResults:
    """Track test results."""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.tests = []

    def add_result(self, name, status, message="", duration=0):
        """Add a test result."""
        self.total += 1
        if status == "passed":
            self.passed += 1
        elif status == "failed":
            self.failed += 1
        elif status == "skipped":
            self.skipped += 1

        self.tests.append({
            "name": name,
            "status": status,
            "message": message,
            "duration": duration
        })

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests:    {self.total}")
        print(f"Passed:         {self.passed} ✓")
        print(f"Failed:         {self.failed} ✗")
        print(f"Skipped:        {self.skipped} ○")
        print("=" * 70)

        if self.failed > 0:
            print("\nFailed Tests:")
            for test in self.tests:
                if test["status"] == "failed":
                    print(f"  ✗ {test['name']}")
                    if test["message"]:
                        print(f"    Error: {test['message']}")


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_test(name, indent=0):
    """Print test name."""
    prefix = "  " * indent
    print(f"{prefix}Testing: {name}...", end=" ", flush=True)


def print_result(status, message="", duration=0):
    """Print test result."""
    if status == "passed":
        symbol = "✓"
        msg = f"PASSED ({duration:.2f}s)"
    elif status == "failed":
        symbol = "✗"
        msg = f"FAILED ({duration:.2f}s)"
    elif status == "skipped":
        symbol = "○"
        msg = "SKIPPED"

    print(f"{symbol} {msg}")
    if message:
        print(f"      {message}")


def run_test(func, results, test_name, *args, **kwargs):
    """Run a test and track results."""
    print_test(test_name, indent=1)
    start_time = time.time()

    try:
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        print_result("passed", duration=duration)
        results.add_result(test_name, "passed", duration=duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        print_result("failed", message=error_msg, duration=duration)
        results.add_result(test_name, "failed", message=error_msg, duration=duration)
        return None


def test_service_health(client, results):
    """Test service health endpoints."""
    print_header("1. SERVICE HEALTH CHECKS")

    def check_health():
        status = client.get_service_status()
        print("\n      Service Status:")
        for service, info in status.items():
            health = info.get('status', 'unknown')
            url = info.get('url', 'N/A')
            symbol = "✓" if health == 'healthy' else "✗"
            print(f"        {symbol} {service}: {health} ({url})")

        # Check if all services are healthy
        all_healthy = all(info.get('status') == 'healthy' for info in status.values())
        if not all_healthy:
            raise Exception("Not all services are healthy")
        return status

    return run_test(check_health, results, "Service Health Check")


def test_stl_conversion(client, results):
    """Test STL conversion."""
    print_header("2. STL CONVERSION")

    def convert_stl():
        output_file = OUTPUT_DIR / "test_output.stl"
        result = client.convert_to_stl(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        return result

    return run_test(convert_stl, results, "STEP to STL Conversion")


def test_ply_conversion(client, results):
    """Test PLY conversion."""
    print_header("3. PLY CONVERSION")

    def convert_ply():
        output_file = OUTPUT_DIR / "test_output.ply"
        result = client.convert_to_ply(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        return result

    return run_test(convert_ply, results, "STEP to PLY Conversion")


def test_vecset_conversion(client, results):
    """Test Vecset conversion."""
    print_header("4. VECSET CONVERSION")

    def convert_vecset():
        output_file = OUTPUT_DIR / "test_output.npy"
        result = client.convert_to_vecset(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        return result

    return run_test(convert_vecset, results, "STEP to Vecset Conversion")


def test_voxel_conversion(client, results):
    """Test Voxel conversion."""
    print_header("5. VOXEL CONVERSION")

    def convert_voxel():
        import numpy as np

        output_file = OUTPUT_DIR / "test_voxel.npz"
        result = client.to_voxel(SAMPLE_FILE, output_file, resolution=64)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        # Load and verify voxel data
        data = np.load(output_file)
        shape = tuple(data['shape'])
        resolution = int(data['resolution'])
        occupied_voxels = len(data['indices'])
        occupancy = occupied_voxels / np.prod(shape) * 100

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        print(f"      Voxel grid shape: {shape}")
        print(f"      Resolution: {resolution}")
        print(f"      Occupied voxels: {occupied_voxels}")
        print(f"      Occupancy: {occupancy:.2f}%")
        return result

    return run_test(convert_voxel, results, "STEP to Voxel Conversion")


def test_3d_mesh_generation(client, results):
    """Test 3D mesh generation."""
    print_header("6. 3D MESH GENERATION")

    def generate_mesh():
        output_file = OUTPUT_DIR / "test_output.msh"
        result = client.to_3d_mesh(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        return result

    return run_test(generate_mesh, results, "STEP to 3D Mesh Conversion")


def test_invariants_calculation(client, results):
    """Test geometric invariants calculation."""
    print_header("7. GEOMETRIC INVARIANTS")

    def calculate_invariants():
        # First ensure we have a mesh file
        mesh_file = OUTPUT_DIR / "test_output.msh"
        if not mesh_file.exists():
            # Generate mesh if it doesn't exist
            client.to_3d_mesh(SAMPLE_FILE, mesh_file)

        # Calculate invariants
        output_file = OUTPUT_DIR / "test_invariants.json"
        result = client.to_invariants(mesh_file, output_file, normalized=True)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        # Verify result structure
        if 'moments' not in result or 'invariants' not in result:
            raise Exception("Result missing moments or invariants")

        if result['total_moments'] == 0 or result['total_invariants'] == 0:
            raise Exception("No moments or invariants calculated")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        print(f"      Moments calculated: {result['total_moments']}")
        print(f"      Invariants calculated: {result['total_invariants']}")
        print(f"      Normalized: {result['normalized']}")

        return result

    return run_test(calculate_invariants, results, "Geometric Invariants Calculation")


def test_cad_analysis(client, results):
    """Test comprehensive CAD analysis."""
    print_header("8. CAD ANALYSIS")

    def analyse():
        output_file = OUTPUT_DIR / "analysis_result.json"
        analysis = client.analyse_cad(SAMPLE_FILE, output_file)

        # Verify JSON file was created
        if not output_file.exists():
            raise Exception(f"Analysis JSON file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      Analysis JSON created: {output_file.name} ({file_size} bytes)")

        # Print comprehensive analysis results
        print("\n      Analysis Summary:")
        summary = analysis.get('summary', {})
        print(f"        Total Volume: {summary.get('total_volume', 0):.2f}")
        print(f"        Total Surface Area: {summary.get('total_surface_area', 0):.2f}")
        print(f"        Total Faces: {summary.get('total_faces', 0)}")
        print(f"        Total Edges: {summary.get('total_edges', 0)}")
        print(f"        Total Vertices: {summary.get('total_vertices', 0)}")
        print(f"        Total Solids: {summary.get('total_solids', 0)}")

        # Print dimensions
        dims = analysis.get('dimensions', {})
        print(f"\n      Dimensions:")
        print(f"        Length: {dims.get('length', 0):.2f}")
        print(f"        Width: {dims.get('width', 0):.2f}")
        print(f"        Height: {dims.get('height', 0):.2f}")

        # Print surface types
        surface_types = analysis.get('surface_type_counts', {})
        print(f"\n      Surface Types: {surface_types}")

        # Print validity
        validity = analysis.get('validity', {})
        print(f"\n      Validity:")
        print(f"        Is Valid: {validity.get('is_valid', False)}")
        print(f"        Is Closed: {validity.get('is_closed', False)}")

        # Verify essential fields exist
        if 'summary' not in analysis:
            raise Exception("Analysis result missing 'summary'")
        if 'bounding_box' not in analysis:
            raise Exception("Analysis result missing 'bounding_box'")
        if 'dimensions' not in analysis:
            raise Exception("Analysis result missing 'dimensions'")

        return analysis

    return run_test(analyse, results, "Comprehensive CAD Geometry Analysis")


def test_multiview(client, results):
    """Test multiview generation."""
    print_header("9. MULTIVIEW GENERATION")

    # Test 6a: Shaded with edges
    def multiview_shaded_edges():
        output_dir = OUTPUT_DIR / "multiview" / "shaded_edges"
        result = client.to_multiview(
            SAMPLE_FILE,
            output_dir,
            render_mode="shaded_with_edges",
            total_imgs=5
        )

        if not result.get('success'):
            raise Exception("Multiview generation failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: shaded_with_edges")
        print(f"      Output: {output_dir}")
        return result

    run_test(multiview_shaded_edges, results, "Shaded with Edges (5 views)")

    # Test 6b: Shaded only
    def multiview_shaded():
        output_dir = OUTPUT_DIR / "multiview" / "shaded"
        result = client.to_multiview(
            SAMPLE_FILE,
            output_dir,
            render_mode="shaded",
            total_imgs=5
        )

        if not result.get('success'):
            raise Exception("Multiview generation failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: shaded")
        print(f"      Output: {output_dir}")
        return result

    run_test(multiview_shaded, results, "Shaded (5 views)")

    # Test 6c: Wireframe
    def multiview_wireframe():
        output_dir = OUTPUT_DIR / "multiview" / "wireframe"
        result = client.to_multiview(
            SAMPLE_FILE,
            output_dir,
            render_mode="wireframe",
            total_imgs=5
        )

        if not result.get('success'):
            raise Exception("Multiview generation failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: wireframe")
        print(f"      Output: {output_dir}")
        return result

    run_test(multiview_wireframe, results, "Wireframe (5 views)")


def main():
    """Main test function."""

    print("\n" + "=" * 70)
    print("CAD CONVERSION API - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print()

    # Check if sample file exists
    if not SAMPLE_FILE.exists():
        print(f"ERROR: Sample file not found: {SAMPLE_FILE}")
        print("Please provide a valid STEP file for testing.")
        return 1

    print(f"Sample file: {SAMPLE_FILE}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize client
    try:
        client = CADConverterClient(host="172.20.0.1")
    except Exception as e:
        print(f"ERROR: Failed to initialize client: {e}")
        return 1

    # Initialize results tracker
    results = TestResults()

    # Run all tests
    try:
        # 1. Health checks
        service_status = test_service_health(client, results)
        if service_status is None:
            print("\nWARNING: Some services are not healthy. Continuing with available services...")

        # 2. Conversion tests
        test_stl_conversion(client, results)
        test_ply_conversion(client, results)
        test_vecset_conversion(client, results)
        test_voxel_conversion(client, results)

        # 3. 3D Mesh generation
        test_3d_mesh_generation(client, results)

        # 4. Geometric Invariants
        test_invariants_calculation(client, results)

        # 5. Analysis tests
        test_cad_analysis(client, results)

        # 6. Multiview generation tests
        test_multiview(client, results)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    results.print_summary()

    print(f"\nAll outputs saved to: {OUTPUT_DIR}")
    print()

    # Return exit code
    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    exit(main())
