"""
CAD File Analyser

Provides functions to analyze CAD files and extract statistics such as volume, faces, bounding boxes etc.
"""

import logging
from collections import Counter, defaultdict
from typing import Dict, List

import FreeCAD
import Part

logger = logging.getLogger(__name__)


def load_step_file(file_path: str) -> FreeCAD.Document:
    """Load a STEP file into a FreeCAD document."""
    doc = FreeCAD.newDocument("TempDoc")
    Part.insert(file_path, doc.Name)
    return doc

# for cleaner outputs 
SURFACE_TYPE_MAPPING = {
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


def get_surface_type(face) -> str:
    """Map FreeCAD surface type to readable name."""
    surface_type = face.Surface.TypeId
    return SURFACE_TYPE_MAPPING.get(surface_type, surface_type)


def get_edge_type(edge) -> str:
    """Classify edge type based on curve type."""
    if not hasattr(edge.Curve, 'TypeId'):
        return 'Other'

    curve_type = edge.Curve.TypeId
    if 'Line' in curve_type:
        return 'Line'
    elif 'Circle' in curve_type:
        return 'Circle'
    elif 'BSpline' in curve_type:
        return 'BSpline'
    elif 'Bezier' in curve_type:
        return 'Bezier'
    elif 'Ellipse' in curve_type:
        return 'Ellipse'
    return 'Other'


def calculate_center_of_mass(solids: List) -> Dict[str, float]:
    """Calculate weighted center of mass from list of solids."""
    total_volume = weighted_x = weighted_y = weighted_z = 0.0

    for solid in solids:
        volume = solid.Volume
        if volume > 0:
            com = solid.CenterOfMass
            weighted_x += com.x * volume
            weighted_y += com.y * volume
            weighted_z += com.z * volume
            total_volume += volume

    if total_volume > 0:
        return {
            'x': weighted_x / total_volume,
            'y': weighted_y / total_volume,
            'z': weighted_z / total_volume
        }
    return {}


def get_comprehensive_analysis(doc: FreeCAD.Document) -> Dict:
    """
    Get comprehensive analysis of the CAD geometry including volume, bounding box,
    edges, vertices, topology, and other geometric properties.

    Args:
        doc: FreeCAD document containing the geometry

    Returns:
        Dictionary containing comprehensive analysis results
    """
    analysis = {
        'objects': [],
        'summary': {
            'total_volume': 0.0,
            'total_surface_area': 0.0,
            'total_faces': 0,
            'total_edges': 0,
            'total_vertices': 0,
            'total_solids': 0,
            'total_shells': 0,
            'total_wires': 0,
        },
        'bounding_box': {},
        'dimensions': {},
        'center_of_mass': {},
        'surface_type_counts': {},
        'edge_statistics': {},
        'topology': {},
        'validity': {}
    }

    all_shapes = []

    # Analyze each object
    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            shape = obj.Shape
            all_shapes.append(shape)

            # Object-specific analysis
            obj_analysis = analyze_shape(obj.Name, shape)
            analysis['objects'].append(obj_analysis)

            # Accumulate summary statistics
            analysis['summary']['total_volume'] += obj_analysis['volume']
            analysis['summary']['total_surface_area'] += obj_analysis['surface_area']
            analysis['summary']['total_faces'] += obj_analysis['topology']['num_faces']
            analysis['summary']['total_edges'] += obj_analysis['topology']['num_edges']
            analysis['summary']['total_vertices'] += obj_analysis['topology']['num_vertices']
            analysis['summary']['total_solids'] += obj_analysis['topology']['num_solids']
            analysis['summary']['total_shells'] += obj_analysis['topology']['num_shells']
            analysis['summary']['total_wires'] += obj_analysis['topology']['num_wires']

    # Overall bounding box
    if all_shapes:
        import Part
        compound = Part.makeCompound(all_shapes)
        bbox = compound.BoundBox

        analysis['bounding_box'] = {
            'x_min': bbox.XMin,
            'x_max': bbox.XMax,
            'y_min': bbox.YMin,
            'y_max': bbox.YMax,
            'z_min': bbox.ZMin,
            'z_max': bbox.ZMax,
        }

        analysis['dimensions'] = {
            'length': bbox.XLength,
            'width': bbox.YLength,
            'height': bbox.ZLength,
            'diagonal': bbox.DiagonalLength
        }

        # Overall center of mass (calculate from solids)
        if compound.Solids:
            try:
                # Calculate weighted center of mass from all solids
                total_volume = 0
                weighted_x = 0
                weighted_y = 0
                weighted_z = 0

                for solid in compound.Solids:
                    volume = solid.Volume
                    if volume > 0:
                        com = solid.CenterOfMass
                        weighted_x += com.x * volume
                        weighted_y += com.y * volume
                        weighted_z += com.z * volume
                        total_volume += volume

                if total_volume > 0:
                    analysis['center_of_mass'] = {
                        'x': weighted_x / total_volume,
                        'y': weighted_y / total_volume,
                        'z': weighted_z / total_volume
                    }
            except Exception as e:
                logger.warning(f"Could not calculate center of mass: {e}")

        # Collect surface type statistics
        from collections import Counter
        all_surface_types = []
        for obj_data in analysis['objects']:
            all_surface_types.extend(obj_data['surface_types'])
        analysis['surface_type_counts'] = dict(Counter(all_surface_types))

        # Edge length statistics
        all_edge_lengths = []
        for obj_data in analysis['objects']:
            all_edge_lengths.extend(obj_data['edge_lengths'])

        if all_edge_lengths:
            analysis['edge_statistics'] = {
                'min_length': min(all_edge_lengths),
                'max_length': max(all_edge_lengths),
                'avg_length': sum(all_edge_lengths) / len(all_edge_lengths),
                'total_edge_length': sum(all_edge_lengths)
            }

        # Overall validity check
        analysis['validity'] = {
            'is_valid': compound.isValid(),
            'is_closed': all(s.isClosed() for s in compound.Solids) if compound.Solids else False,
            'is_null': compound.isNull()
        }

    return analysis


def analyze_shape(name: str, shape) -> Dict:
    """
    Analyze a single shape and extract all relevant geometric properties.

    Args:
        name: Name of the object
        shape: FreeCAD Shape object

    Returns:
        Dictionary containing detailed shape analysis
    """
    analysis = {
        'name': name,
        'volume': 0.0,
        'surface_area': 0.0,
        'bounding_box': {},
        'dimensions': {},
        'center_of_mass': {},
        'topology': {},
        'surface_types': [],
        'edge_lengths': [],
        'edge_types': [],
        'validity': {},
        'complexity': {}
    }

    # Volume (only for solids)
    if shape.Solids:
        analysis['volume'] = shape.Volume

    # Surface area
    analysis['surface_area'] = shape.Area

    # Bounding box
    bbox = shape.BoundBox
    analysis['bounding_box'] = {
        'x_min': bbox.XMin,
        'x_max': bbox.XMax,
        'y_min': bbox.YMin,
        'y_max': bbox.YMax,
        'z_min': bbox.ZMin,
        'z_max': bbox.ZMax,
    }

    analysis['dimensions'] = {
        'length': bbox.XLength,
        'width': bbox.YLength,
        'height': bbox.ZLength,
        'diagonal': bbox.DiagonalLength
    }

    # Center of mass
    if shape.Solids:
        com = shape.CenterOfMass
        analysis['center_of_mass'] = {
            'x': com.x,
            'y': com.y,
            'z': com.z
        }

    # Topology counts
    analysis['topology'] = {
        'num_solids': len(shape.Solids),
        'num_shells': len(shape.Shells),
        'num_faces': len(shape.Faces),
        'num_wires': len(shape.Wires),
        'num_edges': len(shape.Edges),
        'num_vertices': len(shape.Vertexes)
    }

    # Surface types
    for face in shape.Faces:
        surface_type = get_surface_type(face)
        analysis['surface_types'].append(surface_type)

    # Edge analysis
    for edge in shape.Edges:
        analysis['edge_lengths'].append(edge.Length)

        # Classify edge type
        if hasattr(edge.Curve, 'TypeId'):
            curve_type = edge.Curve.TypeId
            if 'Line' in curve_type:
                analysis['edge_types'].append('Line')
            elif 'Circle' in curve_type:
                analysis['edge_types'].append('Circle')
            elif 'BSpline' in curve_type:
                analysis['edge_types'].append('BSpline')
            elif 'Bezier' in curve_type:
                analysis['edge_types'].append('Bezier')
            elif 'Ellipse' in curve_type:
                analysis['edge_types'].append('Ellipse')
            else:
                analysis['edge_types'].append('Other')

    # Validity checks
    analysis['validity'] = {
        'is_valid': shape.isValid(),
        'is_closed': all(s.isClosed() for s in shape.Solids) if shape.Solids else False,
        'is_null': shape.isNull()
    }

    # Complexity metrics
    from collections import Counter
    surface_type_counts = Counter(analysis['surface_types'])
    edge_type_counts = Counter(analysis['edge_types'])

    analysis['complexity'] = {
        'num_unique_surface_types': len(surface_type_counts),
        'num_unique_edge_types': len(edge_type_counts),
        'num_bspline_surfaces': surface_type_counts.get('BSpline Surface', 0),
        'num_bspline_edges': edge_type_counts.get('BSpline', 0),
        'num_curved_edges': (edge_type_counts.get('Circle', 0) +
                            edge_type_counts.get('BSpline', 0) +
                            edge_type_counts.get('Bezier', 0) +
                            edge_type_counts.get('Ellipse', 0)),
        'num_straight_edges': edge_type_counts.get('Line', 0)
    }

    return analysis