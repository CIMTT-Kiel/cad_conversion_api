#!/usr/bin/env python3
"""
Test script specifically for the Rendering Service
"""

from pathlib import Path
from client.client import CADConverterClient, CADClientError
import logging
import os

# Setup logging
logger = logging.getLogger(__name__)

# Get scripts directory
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "rendered_images"


def main():
    """Test the rendering service."""

    print("=" * 60)
    print("Rendering Service Test")
    print("=" * 60)
    print()

    # Initialize client
    client = CADConverterClient(host="172.20.0.1")

    # Check service status
    print("Checking service status...")
    status = client.get_service_status()
    rendering_status = status.get("rendering_service", {})
    print(f"Rendering Service: {rendering_status.get('status', 'unknown')} ({rendering_status.get('url', 'N/A')})")
    print()

    if rendering_status.get('status') != 'healthy':
        print("Rendering service is not healthy. Exiting.")
        return

    # Test with sample file
    sample_file = Path("/home/clearshape/repos/cad_conversion_api/client/scripts/geometry_00000005.STEP")

    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        print("Please provide a valid STEP file path.")
        return

    print(f"Using sample file: {sample_file}")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    try:
        # Test 1: Basic rendering with 3 views
        print("Test 1: Rendering with 3 views")
        print("-" * 40)
        result_1 = client.render_multiview(
            sample_file,
            part_number="test_part_001",
            render_mode="shaded_with_edges",
            total_imgs=10,
            output_dir=OUTPUT_DIR / "test_1"
        )
        print(f"✓ Success: {result_1.get('success', False)}")
        print(f"  Images generated: {result_1.get('total_images', 0)}")
        print(f"  Output directory: {result_1.get('output_dir', 'N/A')}")
        if result_1.get('images'):
            print(f"  Sample image: {os.path.basename(result_1['images'][0])}")
        print()

        # Test 2: Rendering with 5 views
        print("Test 2: Rendering with 5 views")
        print("-" * 40)
        result_2 = client.render_multiview(
            sample_file,
            part_number="test_part_002",
            render_mode="shaded",
            total_imgs=10,
            output_dir=OUTPUT_DIR / "test_2"
        )
        print(f"✓ Success: {result_2.get('success', False)}")
        print(f"  Images generated: {result_2.get('total_images', 0)}")
        print(f"  Output directory: {result_2.get('output_dir', 'N/A')}")
        print()

        # Test 3: Rendering with 10 views
        print("Test 3: Rendering with 10 views")
        print("-" * 40)
        result_3 = client.render_multiview(
            sample_file,
            part_number="test_part_003",
            render_mode="wireframe",
            total_imgs=10,
            output_dir=OUTPUT_DIR / "test_3"
        )
        print(f"✓ Success: {result_3.get('success', False)}")
        print(f"  Images generated: {result_3.get('total_images', 0)}")
        print(f"  Output directory: {result_3.get('output_dir', 'N/A')}")
        print()

        print("=" * 60)
        print("All rendering tests completed successfully!")
        print("=" * 60)

    except CADClientError as e:
        print(f"✗ Error: {e}")
        print()
        print("=" * 60)
        print("Rendering tests failed!")
        print("=" * 60)


if __name__ == "__main__":
    main()
