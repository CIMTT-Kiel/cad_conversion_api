#!/usr/bin/env python3
"""
Example usage of CAD API Client

Demonstrates different ways to configure and use the client.
"""

from pathlib import Path as P 
from client.client import CADConverterClient, CADClientError
import logging

# Setup logging (optional - client.py already does this, but you can override)
logger = logging.getLogger(__name__)


def main():
    """Main example function."""

    print("=" * 60)
    print("CAD API Client - Example Usage")
    print("=" * 60)
    print()

    # ==================================================
    # Method 1: Using config.yaml (Recommended)
    # ==================================================
    print("Method 1: Using config.yaml")
    print("-" * 40)

    try:
        # config.yaml should have host: "172.20.0.1"
        client = CADConverterClient()

        # Check service status
        status = client.get_service_status()
        print("Service Status:")
        for service, info in status.items():
            print(f"  {service}: {info['status']} ({info['url']})")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

    # ==================================================
    # Method 2: With Host IP
    # ==================================================
    print("Method 2: With Host IP")
    print("-" * 40)

    try:
        # Simple: just provide the server IP
        client = CADConverterClient(host="172.20.0.1")
        print(f"Converter URL: {client.converter_url}")
        print(f"Embedding URL: {client.embedding_url}")
        print(f"Analyser URL: {client.analyser_url}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

    # ==================================================
    # Method 3: With Full URLs
    # ==================================================
    print("Method 3: With Full URLs")
    print("-" * 40)

    try:
        # More control: specify each service URL
        client = CADConverterClient(
            converter_url="http://172.20.0.1:8001",
            embedding_url="http://172.20.0.1:8003",
            analyser_url="http://172.20.0.1:8002"
        )
        print("Client initialized with custom URLs")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

    # ==================================================
    # Example Operations (wenn Services laufen)
    # ==================================================
    print("Example Operations")
    print("-" * 40)

    # Verwende client aus Method 1
    client = CADConverterClient(host="172.20.0.1")

    # Check if we have a sample STEP file
    sample_file = P("/home/clearshape/repos/cad_conversion_api/client/scripts/geometry_00000005.STEP")

    if sample_file.exists():
        print(f"Using sample file: {sample_file}")

        try:
            # 1. Convert to STL
            print("\n1. Converting to STL...")
            stl_file = client.convert_to_stl(sample_file, "output.stl")
            print(f"   ✓ STL created: {stl_file}")

            # 2. Convert to PLY
            print("\n2. Converting to PLY...")
            ply_file = client.convert_to_ply(sample_file, "output.ply")
            print(f"   ✓ PLY created: {ply_file}")

            # 2. Convert to PLY
            print("\n2. Converting to Vecset...")
            v_file = client.convert_to_vecset(sample_file, "output.npy")
            print(f"   ✓ VECSET created: {v_file}")

            # 3. Analyse CAD
            print("\n3. Analysing CAD geometry...")
            analysis = client.analyse_cad(sample_file)
            print(f"   ✓ Analysis completed:")
            print(f"     - Total surfaces: {analysis['total_surfaces']}")
            print(f"     - Total area: {analysis['total_area']:.2f}")
            print(f"     - Surface types: {analysis['surface_type_counts']}")

            # 4. Generate Multiview (20 orthographic views)
            print("\n4. Generating multiview images...")
            print("   This may take 30-60 seconds depending on model complexity...")

            # Example 4a: Default multiview (Flat Lines style)
            multiview_file = client.generate_multiview(
                sample_file,
                "output_multiviews.zip"
            )
            print(f"   ✓ Multiview ZIP created: {multiview_file}")
            print(f"     - Contains 20 orthographic views")
            print(f"     - Style: Flat Lines (default)")

            # Example 4b: Multiview with multiple art styles
            print("\n5. Generating multiview with multiple styles...")
            multiview_multi = client.generate_multiview(
                sample_file,
                "output_multiviews_multi.zip",
                resolution=448,
                background="White",
                art_styles="5,2"  # Flat Lines + Wireframe
            )
            print(f"   ✓ Multi-style multiview created: {multiview_multi}")
            print(f"     - Contains 40 views (20 per style)")
            print(f"     - Styles: Flat Lines + Wireframe")

            # Example 4c: Wireframe with transparent background
            print("\n6. Generating wireframe multiview...")
            multiview_wireframe = client.generate_multiview(
                sample_file,
                "output_multiviews_wireframe.zip",
                resolution=448,
                background="Transparent",
                art_styles="2"  # Wireframe only
            )
            print(f"   ✓ Wireframe multiview created: {multiview_wireframe}")
            print(f"     - Contains 20 wireframe views")
            print(f"     - Background: Transparent")

            # 5. Test Rendering Service
            print("\n7. Testing Rendering Service...")
            print("   Generating multiview renders (3 views)...")

            # Create output directory for rendered images
            from pathlib import Path
            output_dir = Path(__file__).parent / "example_rendered_images"

            render_result = client.render_multiview(
                sample_file,
                part_number="test_part_001",
                render_mode="shaded_with_edges",
                total_imgs=3,
                output_dir=output_dir
            )
            print(f"   ✓ Rendering completed:")
            print(f"     - Success: {render_result.get('success', False)}")
            print(f"     - Images generated: {render_result.get('total_images', 0)}")
            print(f"     - Output directory: {render_result.get('output_dir', 'N/A')}")
            if render_result.get('images'):
                import os
                print(f"     - First image: {os.path.basename(render_result['images'][0])}")

            # Example 5b: More views
            print("\n8. Generating more multiview renders (5 views)...")
            result_2 = client.render_multiview(
                sample_file,
                part_number="test_part_002",
                render_mode="shaded",
                total_imgs=10,
                output_dir=OUTPUT_DIR / "test_2"
        )
            print(f"   ✓ Rendering completed:")
            print(f"     - Images generated: {render_result_5.get('total_images', 0)}")

        except CADClientError as e:
            print(f"   ✗ Error: {e}")
    else:
        print("No sample file found (sample.step)")
        print("Skipping conversion examples")
        print()
        print("To test with your own file:")
        print("  client.convert_to_stl('your_file.step', 'output.stl')")
        print("  client.convert_to_ply('your_file.step', 'output.ply')")
        print("  client.convert_to_vecset('your_file.step', 'output.npy')")
        print("  client.analyse_cad('your_file.step')")
        print("  client.generate_multiview('your_file.step', 'output_multiviews.zip')")

    print()
    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
