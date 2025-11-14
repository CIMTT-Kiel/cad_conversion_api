from pathlib import Path
from client.client import CADConverterClient
from client.constants import PATHS
import logging
import time

logging.basicConfig(level=logging.WARNING)


SAMPLE_FILE = PATHS.ROOT / "testdata/geometry_00000005.STEP"
OUTPUT_DIR = PATHS.ROOT / "testdata/test_outputs"


class TestResults:
    """Track and report test results."""
    def __init__(self):
        self.total = self.passed = self.failed = self.skipped = 0
        self.tests = []

    def add_result(self, name, status, message="", duration=0):
        """Add test result and update counters."""
        self.total += 1
        setattr(self, status, getattr(self, status) + 1)
        self.tests.append({"name": name, "status": status, "message": message, "duration": duration})

    def print_summary(self):
        print(f"\n{'=' * 70}\nTEST SUMMARY\n{'=' * 70}")
        print(f"Total Tests:    {self.total}")
        print(f"Passed:         {self.passed} ")
        print(f"Failed:         {self.failed} ")
        print("=" * 70)

        if self.failed > 0:
            print("\nFailed Tests:")
            for test in [t for t in self.tests if t["status"] == "failed"]:
                print(f"  ✗ {test['name']}")
                if test["message"]:
                    print(f"    Error: {test['message']}")


def print_header(title):
    """Print section header."""
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def run_test(func, results, test_name):
    """Execute test function and track result."""
    print(f"  Testing: {test_name}...", end=" ", flush=True)
    start_time = time.time()

    try:
        result = func()
        duration = time.time() - start_time
        print(f"✓ PASSED ({duration:.2f}s)")
        results.add_result(test_name, "passed", duration=duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        print(f"✗ FAILED ({duration:.2f}s)")
        if error_msg:
            print(f"      {error_msg}")
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

        if not all(info.get('status') == 'healthy' for info in status.values()):
            raise Exception("Not all services are healthy")
        return status

    return run_test(check_health, results, "Service Health Check")


def test_format_conversion(client, results, format_name, method, output_ext, header_num):
    """Generic format conversion test."""
    print_header(f"{header_num}. {format_name.upper()} CONVERSION")

    def convert():
        output_file = OUTPUT_DIR / f"test_output.{output_ext}"
        result = method(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        return result

    return run_test(convert, results, f"STEP to {format_name.upper()} Conversion")


def test_voxel_conversion(client, results):
    """Test voxel conversion with data verification."""
    print_header("5. VOXEL CONVERSION")

    def convert_voxel():
        import numpy as np

        output_file = OUTPUT_DIR / "test_voxel.npz"
        result = client.to_voxel(SAMPLE_FILE, output_file, resolution=64)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        data = np.load(output_file)
        shape = tuple(data['shape'])
        occupied_voxels = len(data['indices'])
        occupancy = occupied_voxels / np.prod(shape) * 100

        print(f"\n      File created: {output_file.name} ({output_file.stat().st_size} bytes)")
        print(f"      Voxel grid: {shape}, Resolution: {int(data['resolution'])}")
        print(f"      Occupied voxels: {occupied_voxels}, Occupancy: {occupancy:.2f}%")
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

        print(f"\n      File created: {output_file.name} ({output_file.stat().st_size} bytes)")
        return result

    return run_test(generate_mesh, results, "STEP to 3D Mesh Conversion")


def test_invariants_calculation(client, results):
    """Test geometric invariants calculation."""
    print_header("7. GEOMETRIC INVARIANTS")

    def calculate_invariants():
        mesh_file = OUTPUT_DIR / "test_output.msh"
        if not mesh_file.exists():
            client.to_3d_mesh(SAMPLE_FILE, mesh_file)

        output_file = OUTPUT_DIR / "test_invariants.json"
        result = client.to_invariants(mesh_file, output_file, normalized=True)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        if 'moments' not in result or 'invariants' not in result:
            raise Exception("Result missing moments or invariants")

        if result['total_moments'] == 0 or result['total_invariants'] == 0:
            raise Exception("No moments or invariants calculated")

        print(f"\n      File created: {output_file.name} ({output_file.stat().st_size} bytes)")
        print(f"      Moments: {result['total_moments']}, Invariants: {result['total_invariants']}")
        print(f"      Normalized: {result['normalized']}")
        return result

    return run_test(calculate_invariants, results, "Geometric Invariants Calculation")


def test_cad_analysis(client, results):
    """Test comprehensive CAD analysis."""
    print_header("8. CAD ANALYSIS")

    def analyse():
        output_file = OUTPUT_DIR / "analysis_result.json"
        analysis = client.analyse_cad(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Analysis JSON file not created: {output_file}")

        for key in ['summary', 'bounding_box', 'dimensions']:
            if key not in analysis:
                raise Exception(f"Analysis result missing '{key}'")

        summary = analysis.get('summary', {})
        dims = analysis.get('dimensions', {})
        validity = analysis.get('validity', {})

        print(f"\n      Analysis JSON created: {output_file.name} ({output_file.stat().st_size} bytes)")
        print(f"\n      Summary: Volume={summary.get('total_volume', 0):.2f}, "
              f"Surface Area={summary.get('total_surface_area', 0):.2f}")
        print(f"        Geometry: {summary.get('total_faces', 0)} faces, "
              f"{summary.get('total_edges', 0)} edges, {summary.get('total_vertices', 0)} vertices, "
              f"{summary.get('total_solids', 0)} solids")
        print(f"      Dimensions: {dims.get('length', 0):.2f} x {dims.get('width', 0):.2f} x "
              f"{dims.get('height', 0):.2f}")
        print(f"      Surface Types: {analysis.get('surface_type_counts', {})}")
        print(f"      Validity: Valid={validity.get('is_valid', False)}, "
              f"Closed={validity.get('is_closed', False)}")
        return analysis

    return run_test(analyse, results, "Comprehensive CAD Geometry Analysis")


def test_drawing_views(client, results):
    """Test technical drawing views generation."""
    print_header("9. TECHNICAL DRAWING VIEWS (DXF)")

    def generate_drawing_views():
        output_dir = OUTPUT_DIR / "drawing_views"
        result = client.to_drawing_views(SAMPLE_FILE, output_dir)

        if not result.get('success'):
            raise Exception("Drawing views generation failed")

        total_views = result.get('total_views', 0)
        dxf_files = list(output_dir.glob("*.dxf"))
        if len(dxf_files) != total_views:
            raise Exception(f"Expected {total_views} DXF files, found {len(dxf_files)}")

        print(f"\n      DXF views generated: {total_views}")
        print(f"      Views: {', '.join(result.get('views', []))}")
        print(f"      Output: {output_dir}")
        return result

    return run_test(generate_drawing_views, results, "Technical Drawing Views (DXF) Generation")


def test_multiview(client, results):
    """Test multiview generation with different render modes."""
    print_header("10. MULTIVIEW GENERATION")

    def test_render_mode(mode, mode_name):
        """Test specific render mode."""
        def generate_multiview():
            output_dir = OUTPUT_DIR / "multiview" / mode.replace('_', '')
            result = client.to_multiview(SAMPLE_FILE, output_dir, render_mode=mode, total_imgs=5)

            if not result.get('success'):
                raise Exception("Multiview generation failed")

            print(f"\n      Images: {result.get('total_images', 0)}, Mode: {mode}")
            print(f"      Output: {output_dir}")
            return result

        run_test(generate_multiview, results, f"{mode_name} (5 views)")

    test_render_mode("shaded_with_edges", "Shaded with Edges")
    test_render_mode("shaded", "Shaded")
    test_render_mode("wireframe", "Wireframe")


def main():
    """Main test execution."""
    print(f"\n{'=' * 70}\nCAD CONVERSION API - COMPREHENSIVE TEST SUITE\n{'=' * 70}\n")

    if not SAMPLE_FILE.exists():
        print(f"ERROR: Sample file not found: {SAMPLE_FILE}")
        print("Please provide a valid STEP file for testing.")
        return 1

    print(f"Sample file: {SAMPLE_FILE}\nOutput directory: {OUTPUT_DIR}\n")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        client = CADConverterClient(host="172.20.0.1")
    except Exception as e:
        print(f"ERROR: Failed to initialize client: {e}")
        return 1

    results = TestResults()

    try:
        # Run all test suites
        service_status = test_service_health(client, results)
        if service_status is None:
            print("\nWARNING: Some services unhealthy. Continuing with available services...")

        # Format conversions
        test_format_conversion(client, results, "STL", client.convert_to_stl, "stl", 2)
        test_format_conversion(client, results, "PLY", client.convert_to_ply, "ply", 3)
        test_format_conversion(client, results, "Vecset", client.convert_to_vecset, "npy", 4)
        test_voxel_conversion(client, results)
        test_3d_mesh_generation(client, results)
        test_invariants_calculation(client, results)
        test_cad_analysis(client, results)
        test_drawing_views(client, results)
        test_multiview(client, results)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    results.print_summary()
    print(f"\nAll outputs saved to: {OUTPUT_DIR}\n")
    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    exit(main())
