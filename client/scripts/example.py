#!/usr/bin/env python3
"""
Example usage of CAD API Client

Demonstrates different ways to configure and use the client.
"""

from pathlib import Path
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
    sample_file = Path("/home/clearshape/data-repos/fabwave/1_raw/fabwave/Boxes/00d49861-3894-4531-8fc4-246a1c4852e1.stp")

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

        except CADClientError as e:
            print(f"   ✗ Error: {e}")
    else:
        print("No sample file found (sample.step)")
        print("Skipping conversion examples")
        print()
        print("To test with your own file:")
        print("  client.convert_to_stl('your_file.step', 'output.stl')")
        print("  client.analyse_cad('your_file.step')")

    print()
    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
