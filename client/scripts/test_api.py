#!/usr/bin/env python3
"""
Comprehensive API Test Suite
Tests all CAD Conversion API functionalities in a structured manner.
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


def test_cad_analysis(client, results):
    """Test CAD analysis."""
    print_header("5. CAD ANALYSIS")

    def analyse():
        analysis = client.analyse_cad(SAMPLE_FILE)

        print("\n      Analysis Results:")
        print(f"        Total surfaces: {analysis.get('total_surfaces', 'N/A')}")
        print(f"        Total area: {analysis.get('total_area', 0):.2f}")
        print(f"        Surface types: {analysis.get('surface_type_counts', {})}")

        if 'total_surfaces' not in analysis:
            raise Exception("Analysis result missing 'total_surfaces'")

        return analysis

    return run_test(analyse, results, "CAD Geometry Analysis")


def test_multiview_generation(client, results):
    """Test multiview generation."""
    print_header("6. MULTIVIEW GENERATION (ORTHOGRAPHIC)")

    # Test 6a: Default multiview (Flat Lines)
    def gen_multiview_default():
        output_file = OUTPUT_DIR / "multiview_default.zip"
        result = client.generate_multiview(SAMPLE_FILE, output_file)

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        print(f"      Contains 20 orthographic views (Flat Lines style)")
        return result

    run_test(gen_multiview_default, results, "Default Multiview (Flat Lines)")

    # Test 6b: Wireframe
    def gen_multiview_wireframe():
        output_file = OUTPUT_DIR / "multiview_wireframe.zip"
        result = client.generate_multiview(
            SAMPLE_FILE,
            output_file,
            resolution=448,
            background="White",
            art_styles="2"  # Wireframe
        )

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        print(f"      Contains 20 orthographic views (Wireframe style)")
        return result

    run_test(gen_multiview_wireframe, results, "Wireframe Multiview")

    # Test 6c: Multi-style
    def gen_multiview_multi():
        output_file = OUTPUT_DIR / "multiview_multi.zip"
        result = client.generate_multiview(
            SAMPLE_FILE,
            output_file,
            resolution=448,
            background="White",
            art_styles="5,2"  # Flat Lines + Wireframe
        )

        if not output_file.exists():
            raise Exception(f"Output file not created: {output_file}")

        file_size = output_file.stat().st_size
        print(f"\n      File created: {output_file.name} ({file_size} bytes)")
        print(f"      Contains 40 views (20 per style: Flat Lines + Wireframe)")
        return result

    run_test(gen_multiview_multi, results, "Multi-Style Multiview")


def test_rendering_service(client, results):
    """Test rendering service."""
    print_header("7. RENDERING SERVICE (3D)")

    # Test 7a: Shaded with edges
    def render_shaded_edges():
        output_dir = OUTPUT_DIR / "renders" / "shaded_edges"
        result = client.render_multiview(
            SAMPLE_FILE,
            part_number="test_shaded_edges",
            render_mode="shaded_with_edges",
            total_imgs=5,
            output_dir=output_dir
        )

        if not result.get('success'):
            raise Exception("Rendering failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: shaded_with_edges")
        print(f"      Output: {output_dir}")
        return result

    run_test(render_shaded_edges, results, "Shaded with Edges Rendering (5 views)")

    # Test 7b: Shaded only
    def render_shaded():
        output_dir = OUTPUT_DIR / "renders" / "shaded"
        result = client.render_multiview(
            SAMPLE_FILE,
            part_number="test_shaded",
            render_mode="shaded",
            total_imgs=5,
            output_dir=output_dir
        )

        if not result.get('success'):
            raise Exception("Rendering failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: shaded")
        print(f"      Output: {output_dir}")
        return result

    run_test(render_shaded, results, "Shaded Rendering (5 views)")

    # Test 7c: Wireframe
    def render_wireframe():
        output_dir = OUTPUT_DIR / "renders" / "wireframe"
        result = client.render_multiview(
            SAMPLE_FILE,
            part_number="test_wireframe",
            render_mode="wireframe",
            total_imgs=5,
            output_dir=output_dir
        )

        if not result.get('success'):
            raise Exception("Rendering failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: wireframe")
        print(f"      Output: {output_dir}")
        return result

    run_test(render_wireframe, results, "Wireframe Rendering (5 views)")

    # Test 7d: High volume test
    def render_many():
        output_dir = OUTPUT_DIR / "renders" / "many_views"
        result = client.render_multiview(
            SAMPLE_FILE,
            part_number="test_many",
            render_mode="shaded_with_edges",
            total_imgs=20,
            output_dir=output_dir
        )

        if not result.get('success'):
            raise Exception("Rendering failed")

        img_count = result.get('total_images', 0)
        print(f"\n      Images generated: {img_count}")
        print(f"      Mode: shaded_with_edges")
        print(f"      Output: {output_dir}")
        return result

    run_test(render_many, results, "High Volume Rendering (20 views)")


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

        # 3. Analysis tests
        test_cad_analysis(client, results)

        # 4. Multiview generation tests
        test_multiview_generation(client, results)

        # 5. Rendering service tests
        test_rendering_service(client, results)

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
