import json
import math
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import Counter


class AdvancedComplexityMetrics:
    """
    Calculates advanced complexity metrics for geometries based on STEP analysis data.

    Based on research from:
        - Armillotta (2021): "On the role of complexity in machining time estimation"
        - Li et al. (2014): "Complexity analysis for sculptured surface in multi-axis CNC machining"
        - Fictiv/Prolean: "Complex Parts: A Geometry Perspective"
    """

    def __init__(self, json_file: str):
        """Loads STEP analysis data from JSON file."""
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.summary = self.data.get('summary', {})
        self.bbox = self.data.get('bounding_box', {})
        self.dims = self.data.get('dimensions', {})
        self.obj = self.data.get('objects', [{}])[0] if self.data.get('objects') else {}
        self.complexity = self.obj.get('complexity', {})
        self.edge_stats = self.data.get('edge_statistics', {})

    # ========================================================================
    # 1. GEOMETRIC COMPLEXITY
    # ========================================================================

    def calc_feature_count_index(self) -> float:
        """
        Feature Count Index (FCI)
        Counts the number of geometric features.

        Source: Fictiv - "What are Complex Parts"
        """
        faces = self.summary.get('total_faces', 0)
        edges = self.summary.get('total_edges', 0)
        vertices = self.summary.get('total_vertices', 0)

        # Weighted sum: faces more important than edges, edges more important than vertices
        fci = faces * 1.0 + edges * 0.3 + vertices * 0.1

        return fci

    def calc_surface_diversity_index(self) -> float:
        """
        Surface Diversity Index (SDI)
        Measures the variety of surface types.

        Source: Li et al. (2014) - Surface Machining Complexity
        """
        surface_counts = self.data.get('surface_type_counts', {})

        if not surface_counts:
            return 0.0

        total = sum(surface_counts.values())

        # Shannon entropy for diversity
        entropy = 0.0
        for count in surface_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # Normalized by number of unique types
        num_types = len(surface_counts)
        max_entropy = math.log2(num_types) if num_types > 1 else 1.0

        sdi = (entropy / max_entropy) * num_types * 10  # Scaled to meaningful range

        return sdi

    def calc_curvature_complexity(self) -> float:
        """
        Curvature Complexity Index (CCI)
        Ratio of curved to straight edges.

        Source: Prolean/TiRapid - Complex CNC Machining
        """
        curved = self.complexity.get('num_curved_edges', 0)
        straight = self.complexity.get('num_straight_edges', 0)
        total = curved + straight

        if total == 0:
            return 0.0

        # Curved edges are significantly more complex
        curvature_ratio = curved / total

        # Non-linear scaling: more curvature = disproportionately more complex
        cci = curvature_ratio ** 0.7 * 100

        return cci

    def calc_freeform_surface_factor(self) -> float:
        """
        Freeform Surface Factor (FSF)
        Accounts for B-Spline and complex surfaces.

        Source: Li et al. (2014)
        """
        bspline_surfaces = self.complexity.get('num_bspline_surfaces', 0)
        bspline_edges = self.complexity.get('num_bspline_edges', 0)

        # B-Splines require 5-axis machining
        fsf = bspline_surfaces * 20 + bspline_edges * 5

        # Also consider cylinders (simpler than B-Splines but more complex than planes)
        surface_counts = self.data.get('surface_type_counts', {})
        cylinders = surface_counts.get('Cylinder', 0)

        fsf += cylinders * 2

        return fsf

    # ========================================================================
    # 2. SIZE AND VOLUME COMPLEXITY
    # ========================================================================

    def calc_envelope_volume(self) -> float:
        """
        Envelope Volume (VE)
        Bounding box volume of the part in cm³.

        Source: Armillotta (2021)
        """
        length = self.dims.get('length', 0)
        width = self.dims.get('width', 0)
        height = self.dims.get('height', 0)

        # Volume in mm³, converted to cm³
        ve = (length * width * height) / 1000

        return ve

    def calc_volume_ratio(self) -> float:
        """
        Volume Ratio (VR)
        Ratio of actual volume to envelope volume.

        Source: Armillotta (2021)
        """
        actual_volume = self.summary.get('total_volume', 0) / 1000  # cm³
        envelope_volume = self.calc_envelope_volume()

        if envelope_volume == 0:
            return 0.0

        vr = actual_volume / envelope_volume

        return vr

    def calc_material_removal_rate_factor(self) -> float:
        """
        Material Removal Rate Factor (MRRF)
        Estimates the material that needs to be removed.

        Source: Feature-based machining time estimation
        """
        envelope_volume = self.calc_envelope_volume()
        actual_volume = self.summary.get('total_volume', 0) / 1000

        # Material that needs to be removed
        removed_volume = envelope_volume - actual_volume

        if removed_volume < 0:
            removed_volume = 0

        # More material removal = higher complexity
        mrrf = removed_volume / 100  # Scaled

        return mrrf

    def calc_compactness_factor(self) -> float:
        """
        Compactness Factor (CF)
        Ratio of volume to surface area.

        Source: Geometric complexity metrics
        """
        volume = self.summary.get('total_volume', 0)
        area = self.summary.get('total_surface_area', 0)

        if area == 0:
            return 0.0

        # Compactness: V^(2/3) / A
        # Values near 0: complex, branched geometry
        # Values near 1: simple, compact form (sphere = 1)
        cf = (volume ** (2/3)) / area

        # Inverse for complexity: less compact = more complex
        complexity_cf = (1 - cf) * 100 if cf < 1 else 0

        return complexity_cf

    # ========================================================================
    # 3. DETAIL COMPLEXITY
    # ========================================================================

    def calc_edge_complexity_index(self) -> float:
        """
        Edge Complexity Index (ECI)
        Based on edge length distribution.

        Source: Geometric feature analysis
        """
        min_len = self.edge_stats.get('min_length', 0)
        max_len = self.edge_stats.get('max_length', 1)
        avg_len = self.edge_stats.get('avg_length', 1)

        if max_len == 0 or avg_len == 0:
            return 0.0

        # Ratio of smallest to largest edge
        length_range = max_len / min_len if min_len > 0 else 100

        # Standard deviation proxy: large range = high complexity
        eci = math.log10(length_range) * 10

        return eci

    def calc_face_density_index(self) -> float:
        """
        Face Density Index (FDI)
        Number of faces per surface unit.

        Source: Manufacturing complexity evaluation
        """
        faces = self.summary.get('total_faces', 0)
        area = self.summary.get('total_surface_area', 0) / 100  # cm²

        if area == 0:
            return 0.0

        # Faces per 100 cm²
        fdi = (faces / area) * 100

        return fdi

    def calc_feature_size_ratio(self) -> float:
        """
        Feature Size Ratio (FSR)
        Ratio of smallest to largest features.

        Source: Deep cavity and small feature complexity
        """
        min_len = self.edge_stats.get('min_length', 0)
        max_dim = max(
            self.dims.get('length', 0),
            self.dims.get('width', 0),
            self.dims.get('height', 0)
        )

        if max_dim == 0 or min_len == 0:
            return 0.0

        # Small features in large parts = high complexity
        fsr = max_dim / min_len

        # Log scaling for better representation
        return math.log10(fsr) * 20 if fsr > 1 else 0

    # ========================================================================
    # 4. TOPOLOGICAL COMPLEXITY
    # ========================================================================

    def calc_euler_characteristic(self) -> int:
        """
        Euler Characteristic χ = V - E + F
        Topological measure for complexity.

        Source: Topology theory
        """
        V = self.summary.get('total_vertices', 0)
        E = self.summary.get('total_edges', 0)
        F = self.summary.get('total_faces', 0)

        euler = V - E + F

        return euler

    def calc_topological_complexity_index(self) -> float:
        """
        Topological Complexity Index (TCI)
        Combines all topological elements.

        Source: CAD complexity metrics
        """
        solids = self.summary.get('total_solids', 0)
        shells = self.summary.get('total_shells', 0)
        wires = self.summary.get('total_wires', 0)
        faces = self.summary.get('total_faces', 0)
        edges = self.summary.get('total_edges', 0)
        vertices = self.summary.get('total_vertices', 0)

        # Weighted sum: higher level elements are more important
        tci = (solids * 10 + shells * 5 + wires * 2 +
               faces * 1 + edges * 0.5 + vertices * 0.2)

        return tci

    def calc_connectivity_index(self) -> float:
        """
        Connectivity Index (CI)
        Ratio of edges to vertices.

        Source: Graph-theoretic complexity
        """
        edges = self.summary.get('total_edges', 0)
        vertices = self.summary.get('total_vertices', 0)

        if vertices == 0:
            return 0.0

        # Average connectivity per vertex
        ci = edges / vertices

        # High connectivity = complex topology
        return ci * 10

    # ========================================================================
    # 5. MACHINING-SPECIFIC COMPLEXITY
    # ========================================================================

    def calc_axis_requirement_score(self) -> float:
        """
        Axis Requirement Score (ARS)
        Estimates required number of CNC axes.

        Score ranges:
        - 3-axis: 0-30 points
        - 4-axis: 30-60 points
        - 5-axis: 60+ points

        Source: Multi-axis machining requirements
        """
        curved = self.complexity.get('num_curved_edges', 0)
        bspline_surfaces = self.complexity.get('num_bspline_surfaces', 0)

        score = 0

        # Base complexity
        faces = self.summary.get('total_faces', 0)
        score += min(faces * 2, 30)

        # Curved features require more axes
        score += curved * 3

        # B-Splines definitely require 5-axis
        score += bspline_surfaces * 20

        return min(score, 100)

    def calc_setup_complexity_score(self) -> float:
        """
        Setup Complexity Score (SCS)
        Estimates number of required setups/fixturing operations.

        Source: Manufacturing setup requirements
        """
        # Based on surface orientations
        surface_types = len(self.data.get('surface_type_counts', {}))
        faces = self.summary.get('total_faces', 0)

        # More different surface types = more setups
        scs = surface_types * 5 + faces * 0.5

        return scs

    def calc_tool_variety_index(self) -> float:
        """
        Tool Variety Index (TVI)
        Estimates number of required tools.

        Source: Tool selection in CNC machining
        """
        # Different edge types require different tools
        unique_edge_types = self.complexity.get('num_unique_edge_types', 0)
        unique_surface_types = self.complexity.get('num_unique_surface_types', 0)

        # Small features require small tools
        min_len = self.edge_stats.get('min_length', 10)
        max_len = self.edge_stats.get('max_length', 100)

        # Tool range
        if max_len > 0 and min_len > 0:
            tool_range = max_len / min_len
        else:
            tool_range = 1

        tvi = unique_edge_types * 5 + unique_surface_types * 3 + math.log10(tool_range) * 2

        return tvi

    def calc_tolerance_complexity_factor(self) -> float:
        """
        Tolerance Complexity Factor (TCF)
        Based on feature sizes (proxy for tolerances).

        Source: Armillotta (2021) - Information content
        """
        # Smaller features require tighter tolerances
        avg_edge = self.edge_stats.get('avg_length', 100)
        min_edge = self.edge_stats.get('min_length', 10)

        # Assumption: features < 10mm require precision machining
        if min_edge < 10:
            precision_factor = 2.0
        elif min_edge < 20:
            precision_factor = 1.5
        else:
            precision_factor = 1.0

        # Complexity increases with number of faces and precision requirement
        faces = self.summary.get('total_faces', 0)

        tcf = faces * precision_factor

        return tcf

    # ========================================================================
    # 6. COMPOSITE SCORES - Overall Complexity
    # ========================================================================

    def calc_geometric_complexity_score(self) -> float:
        """
        Geometric Complexity Score (GCS)
        Combines all geometric metrics.
        """
        gcs = (
            self.calc_feature_count_index() * 0.15 +
            self.calc_surface_diversity_index() * 0.20 +
            self.calc_curvature_complexity() * 0.25 +
            self.calc_freeform_surface_factor() * 0.20 +
            self.calc_edge_complexity_index() * 0.10 +
            self.calc_face_density_index() * 0.10
        )
        return gcs

    def calc_size_complexity_score(self) -> float:
        """
        Size Complexity Score (SCS_V)
        Combines volume-based metrics.
        """
        scs = (
            math.log10(self.calc_envelope_volume() + 1) * 20 +
            self.calc_material_removal_rate_factor() * 0.3 +
            self.calc_compactness_factor() * 0.5
        )
        return scs

    def calc_machining_complexity_score(self) -> float:
        """
        Machining Complexity Score (MCS)
        Machining-specific complexity.
        """
        mcs = (
            self.calc_axis_requirement_score() * 0.35 +
            self.calc_setup_complexity_score() * 0.25 +
            self.calc_tool_variety_index() * 0.20 +
            self.calc_tolerance_complexity_factor() * 0.20
        )
        return mcs

    def calc_overall_complexity_index(self) -> float:
        """
        Overall Complexity Index (OCI)
        Total complexity for NC programming.

        Weighting based on literature:
        - Geometry: 40%
        - Machining: 35%
        - Size: 15%
        - Topology: 10%
        """
        oci = (
            self.calc_geometric_complexity_score() * 0.40 +
            self.calc_machining_complexity_score() * 0.35 +
            self.calc_size_complexity_score() * 0.15 +
            self.calc_topological_complexity_index() * 0.10
        )
        return oci

    # ========================================================================
    # CLASSIFICATION AND REPORTING
    # ========================================================================

    def classify_complexity(self, score: float) -> str:
        """Classifies complexity based on score."""
        if score < 50:
            return "VERY SIMPLE"
        elif score < 100:
            return "SIMPLE"
        elif score < 200:
            return "MEDIUM"
        elif score < 400:
            return "COMPLEX"
        elif score < 700:
            return "VERY COMPLEX"
        else:
            return "EXTREMELY COMPLEX"

    def estimate_machining_time_category(self, oci: float) -> str:
        """
        Estimates machining time category based on OCI.

        Source: Empirical estimates from literature
        """
        if oci < 50:
            return "< 30 min (3-axis standard)"
        elif oci < 100:
            return "30-60 min (3-axis)"
        elif oci < 200:
            return "1-3 hours (3/4-axis)"
        elif oci < 400:
            return "3-8 hours (4/5-axis)"
        elif oci < 700:
            return "8-24 hours (5-axis)"
        else:
            return "> 24 hours (5-axis, multiple setups)"

    def export_metrics_dict(self) -> Dict[str, float]:
        """
        Exports all metrics as flat dictionary for further processing.

        Returns:
            Dictionary with all calculated metrics (flattened structure)
        """
        return {
            # Geometric metrics
            'feature_count_index': self.calc_feature_count_index(),
            'surface_diversity_index': self.calc_surface_diversity_index(),
            'curvature_complexity': self.calc_curvature_complexity(),
            'freeform_surface_factor': self.calc_freeform_surface_factor(),
            'edge_complexity_index': self.calc_edge_complexity_index(),
            'face_density_index': self.calc_face_density_index(),
            'geometric_complexity_score': self.calc_geometric_complexity_score(),

            # Size metrics
            'envelope_volume': self.calc_envelope_volume(),
            'volume_ratio': self.calc_volume_ratio(),
            'material_removal_factor': self.calc_material_removal_rate_factor(),
            'compactness_factor': self.calc_compactness_factor(),
            'feature_size_ratio': self.calc_feature_size_ratio(),
            'size_complexity_score': self.calc_size_complexity_score(),

            # Topological metrics
            'euler_characteristic': self.calc_euler_characteristic(),
            'topological_complexity_index': self.calc_topological_complexity_index(),
            'connectivity_index': self.calc_connectivity_index(),

            # Machining metrics
            'axis_requirement_score': self.calc_axis_requirement_score(),
            'setup_complexity_score': self.calc_setup_complexity_score(),
            'tool_variety_index': self.calc_tool_variety_index(),
            'tolerance_complexity_factor': self.calc_tolerance_complexity_factor(),
            'machining_complexity_score': self.calc_machining_complexity_score(),

            # Overall
            'overall_complexity_index': self.calc_overall_complexity_index(),
        }


def main():
    """Main function for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python complexity_metrics.py <json_file> [--export-json output.json]")
        print("\nExample:")
        print("  python complexity_metrics.py geometry_00000005.json")
        print("  python complexity_metrics.py geometry_00000005.json --export-json metrics.json")
        sys.exit(1)

    json_file = sys.argv[1]

    if not Path(json_file).exists():
        print(f"Error: File '{json_file}' not found!")
        sys.exit(1)

    try:
        calculator = AdvancedComplexityMetrics(json_file)

        # Calculate and display metrics
        metrics = calculator.export_metrics_dict()
        oci = metrics['overall_complexity_index']
        classification = calculator.classify_complexity(oci)
        time_estimate = calculator.estimate_machining_time_category(oci)

        print("\n" + "=" * 80)
        print("COMPLEXITY METRICS ANALYSIS".center(80))
        print("=" * 80)
        print(f"\nOverall Complexity Index (OCI): {oci:.2f}")
        print(f"Classification: {classification}")
        print(f"Estimated Machining Time: {time_estimate}")
        print("\n" + "=" * 80 + "\n")

        # Optional: Export as JSON
        if len(sys.argv) >= 4 and sys.argv[2] == '--export-json':
            output_file = sys.argv[3]

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            print(f"✓ Metrics exported to: {output_file}\n")

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
