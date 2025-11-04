"""
CAD File Analyser

This module provides functions to analyze CAD files and extract information
about static stats like volume, faces, face_types, etc.
"""

import FreeCAD
import Part
from collections import defaultdict
from typing import Dict, List, Tuple
from pathlib import Path
import math, logging

def load_step_file(file_path: str) -> FreeCAD.Document:
    """
    Load a STEP file into a FreeCAD document.

    Args:
        file_path: Path to the STEP file

    Returns:
        FreeCAD document containing the imported geometry from the STEP file
    """
    doc = FreeCAD.newDocument("TempDoc")
    Part.insert(file_path, doc.Name)
    return doc


def get_surface_type(face) -> str:
    """
    map the prop. freecad type of faces to basic types - just for clarity.

    Args:
        face: A FreeCAD face object

    Returns:
        String describing the surface type
    """
    surface = face.Surface
    surface_type = surface.TypeId

    # Map FreeCAD surface types to more readable names
    type_mapping = {
        'Part::GeomPlane': 'Plane',
        'Part::GeomCylinder': 'Cylinder',
        'Part::GeomSphere': 'Sphere',
        'Part::GeomCone': 'Cone',
        'Part::GeomToroid': 'Torus',
        'Part::GeomBSplineSurface': 'BSpline Surface',
        'Part::GeomBezierSurface': 'Bezier Surface',
        'Part::GeomSurfaceOfRevolution': 'Surface of Revolution',
        'Part::GeomSurfaceOfExtrusion': 'Surface of Extrusion',
        'Part::GeomOffsetSurface': 'Offset Surface',
        'Part::GeomTrimmedSurface': 'Trimmed Surface',
    }

    return type_mapping.get(surface_type, surface_type)


def analyze_surfaces(doc: FreeCAD.Document) -> Dict[str, int]:
    """
    Analyze all surfaces in a FreeCAD document and count them by type.

    Args:
        doc: FreeCAD document 

    Returns:
        Dictionary mapping surface type names to their counts
    """
    surface_counts = defaultdict(int)

    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            shape = obj.Shape
            for face in shape.Faces:
                surface_type = get_surface_type(face)
                surface_counts[surface_type] += 1

    return dict(surface_counts)


def get_detailed_surface_info(doc: FreeCAD.Document) -> List[Dict]:
    """
    Get detailed information about each surface including type and properties.

    Args:
        doc: FreeCAD document containing the geometry

    Returns:
        List of dictionaries containing detailed surface information
    """
    surfaces = []

    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            shape = obj.Shape
            for idx, face in enumerate(shape.Faces):
                surface_type = get_surface_type(face)
                surface_info = {
                    'object_name': obj.Name,
                    'face_index': idx,
                    'surface_type': surface_type,
                    'area': face.Area,
                    'center_of_mass': (face.CenterOfMass.x,
                                      face.CenterOfMass.y,
                                      face.CenterOfMass.z)
                }
                surfaces.append(surface_info)

    return surfaces