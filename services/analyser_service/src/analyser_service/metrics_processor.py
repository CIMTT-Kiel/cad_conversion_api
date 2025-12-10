#!/usr/bin/env python3
"""
CAD Metrics Processor

Processes STEP analysis files and generates:
1. Complexity metrics for statistical analyses
2. VLM prompt building blocks with context information
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any
from collections import Counter
import statistics
from src.analyser_service.complexity_metrics import AdvancedComplexityMetrics


class CADMetricsProcessor:
    """Processes CAD analysis data and computes metrics."""

    def __init__(self, analysis_file: Path):
        """
        Initializes the processor with an analysis file.

        Args:
            analysis_file: Path to the STEP analysis JSON file
        """
        self.analysis_file = analysis_file
        self.data = self._load_analysis()
        self.complexity_calc = AdvancedComplexityMetrics(str(analysis_file))

    def _load_analysis(self) -> Dict[str, Any]:
        """Loads the analysis file."""
        with open(self.analysis_file, 'r') as f:
            return json.load(f)

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculates global complexity metrics.

        Returns:
            Dictionary containing all metrics
        """
        metrics = {}

        # Basic information
        metrics['filename'] = self.data.get('metadata', {}).get('filename', 'unknown')
        metrics['analysis_id'] = self.data.get('metadata', {}).get('analysis_id', '')
        metrics['timestamp'] = self.data.get('metadata', {}).get('timestamp', '')

        # Global geometric properties
        summary = self.data.get('summary', {})
        metrics['total_volume'] = summary.get('total_volume', 0)
        metrics['total_surface_area'] = summary.get('total_surface_area', 0)

        # Dimensions
        dims = self.data.get('dimensions', {})
        metrics['length'] = dims.get('length', 0)
        metrics['width'] = dims.get('width', 0)
        metrics['height'] = dims.get('height', 0)
        metrics['diagonal'] = dims.get('diagonal', 0)

        # Topological complexity
        metrics['total_faces'] = summary.get('total_faces', 0)
        metrics['total_edges'] = summary.get('total_edges', 0)
        metrics['total_vertices'] = summary.get('total_vertices', 0)
        metrics['total_solids'] = summary.get('total_solids', 0)
        metrics['total_shells'] = summary.get('total_shells', 0)
        metrics['total_wires'] = summary.get('total_wires', 0)

        # Surface type statistics
        surface_counts = self.data.get('surface_type_counts', {})
        metrics['num_surface_types'] = len(surface_counts)
        metrics['surface_type_distribution'] = surface_counts

        # Calculate surface type ratios
        total_faces = sum(surface_counts.values()) if surface_counts else 1
        for surf_type, count in surface_counts.items():
            metrics[f'surface_type_{surf_type.lower()}_ratio'] = count / total_faces

        # Edge statistics
        edge_stats = self.data.get('edge_statistics', {})
        metrics['edge_min_length'] = edge_stats.get('min_length', 0)
        metrics['edge_max_length'] = edge_stats.get('max_length', 0)
        metrics['edge_avg_length'] = edge_stats.get('avg_length', 0)
        metrics['edge_total_length'] = edge_stats.get('total_edge_length', 0)

        # Object-specific metrics (aggregated)
        objects = self.data.get('objects', [])
        metrics['num_objects'] = len(objects)

        if objects:
            # Aggregate complexity metrics from objects
            all_curved_edges = []
            all_straight_edges = []
            all_unique_surface_types = []
            all_unique_edge_types = []
            all_bspline_surfaces = []
            all_bspline_edges = []

            for obj in objects:
                complexity = obj.get('complexity', {})
                all_curved_edges.append(complexity.get('num_curved_edges', 0))
                all_straight_edges.append(complexity.get('num_straight_edges', 0))
                all_unique_surface_types.append(complexity.get('num_unique_surface_types', 0))
                all_unique_edge_types.append(complexity.get('num_unique_edge_types', 0))
                all_bspline_surfaces.append(complexity.get('num_bspline_surfaces', 0))
                all_bspline_edges.append(complexity.get('num_bspline_edges', 0))

            metrics['total_curved_edges'] = sum(all_curved_edges)
            metrics['total_straight_edges'] = sum(all_straight_edges)
            metrics['total_bspline_surfaces'] = sum(all_bspline_surfaces)
            metrics['total_bspline_edges'] = sum(all_bspline_edges)

            # Ratios
            total_edges = metrics['total_edges']
            if total_edges > 0:
                metrics['curved_edges_ratio'] = metrics['total_curved_edges'] / total_edges
                metrics['straight_edges_ratio'] = metrics['total_straight_edges'] / total_edges
                metrics['bspline_edges_ratio'] = metrics['total_bspline_edges'] / total_edges
            else:
                metrics['curved_edges_ratio'] = 0
                metrics['straight_edges_ratio'] = 0
                metrics['bspline_edges_ratio'] = 0

            # Average complexity per object
            metrics['avg_unique_surface_types_per_object'] = statistics.mean(all_unique_surface_types)
            metrics['avg_unique_edge_types_per_object'] = statistics.mean(all_unique_edge_types)

        # ======================================================================
        # Advanced Complexity Metrics from AdvancedComplexityMetrics
        # ======================================================================
        advanced_metrics = self.complexity_calc.export_metrics_dict()

        # Geometric complexity
        metrics['feature_count_index'] = advanced_metrics['feature_count_index']
        metrics['surface_diversity_index'] = advanced_metrics['surface_diversity_index']
        metrics['curvature_complexity'] = advanced_metrics['curvature_complexity']
        metrics['freeform_surface_factor'] = advanced_metrics['freeform_surface_factor']
        metrics['edge_complexity_index'] = advanced_metrics['edge_complexity_index']
        metrics['face_density_index'] = advanced_metrics['face_density_index']
        metrics['geometric_complexity_score'] = advanced_metrics['geometric_complexity_score']

        # Size metrics
        metrics['envelope_volume'] = advanced_metrics['envelope_volume']
        metrics['volume_ratio'] = advanced_metrics['volume_ratio']
        metrics['material_removal_factor'] = advanced_metrics['material_removal_factor']
        metrics['compactness_factor'] = advanced_metrics['compactness_factor']
        metrics['feature_size_ratio'] = advanced_metrics['feature_size_ratio']
        metrics['size_complexity_score'] = advanced_metrics['size_complexity_score']

        # Topological metrics
        metrics['euler_characteristic'] = advanced_metrics['euler_characteristic']
        metrics['topological_complexity_index'] = advanced_metrics['topological_complexity_index']
        metrics['connectivity_index'] = advanced_metrics['connectivity_index']

        # Machining metrics
        metrics['axis_requirement_score'] = advanced_metrics['axis_requirement_score']
        metrics['setup_complexity_score'] = advanced_metrics['setup_complexity_score']
        metrics['tool_variety_index'] = advanced_metrics['tool_variety_index']
        metrics['tolerance_complexity_factor'] = advanced_metrics['tolerance_complexity_factor']
        metrics['machining_complexity_score'] = advanced_metrics['machining_complexity_score']

        # Overall Complexity Index (OCI)
        metrics['overall_complexity_index'] = advanced_metrics['overall_complexity_index']
        metrics['complexity_classification'] = self.complexity_calc.classify_complexity(
            metrics['overall_complexity_index']
        )

        # CNC axis recommendation
        ars = metrics['axis_requirement_score']
        if ars < 30:
            metrics['recommended_cnc_axes'] = '3-axis'
        elif ars < 60:
            metrics['recommended_cnc_axes'] = '4-axis'
        else:
            metrics['recommended_cnc_axes'] = '5-axis'

        # Validity
        validity = self.data.get('validity', {})
        metrics['is_valid'] = validity.get('is_valid', False)
        metrics['is_closed'] = validity.get('is_closed', False)

        return metrics

    def generate_vlm_context(self) -> str:
        """
        Generates a structured context building block for VLM prompts.

        Returns:
            Human-readable context string with all available information
        """
        metrics = self.calculate_metrics()

        context_parts = []

        # Header
        context_parts.append("# CAD Model Analysis Context")
        context_parts.append("")

        # Basic information
        context_parts.append("## Basic Information")
        context_parts.append(f"Filename: {metrics['filename']}")
        context_parts.append(f"Analysis ID: {metrics['analysis_id']}")
        context_parts.append("")

        # Geometric properties
        context_parts.append("## Geometric Properties")
        context_parts.append(f"Volume: {metrics['total_volume']:.2f} mm^3")
        context_parts.append(f"Surface Area: {metrics['total_surface_area']:.2f} mm^2")
        context_parts.append(f"Volume Ratio: {metrics['volume_ratio']:.4f}")
        context_parts.append("")

        # Dimensions
        context_parts.append("## Dimensions")
        context_parts.append(f"Length: {metrics['length']:.2f} mm")
        context_parts.append(f"Width: {metrics['width']:.2f} mm")
        context_parts.append(f"Height: {metrics['height']:.2f} mm")
        context_parts.append(f"Diagonal: {metrics['diagonal']:.2f} mm")
        context_parts.append("")

        # Topological structure
        context_parts.append("## Topological Structure")
        context_parts.append(f"Number of Objects: {metrics['num_objects']}")
        context_parts.append(f"Number of Solids: {metrics['total_solids']}")
        context_parts.append(f"Number of Shells: {metrics['total_shells']}")
        context_parts.append(f"Number of Faces: {metrics['total_faces']}")
        context_parts.append(f"Number of Edges: {metrics['total_edges']}")
        context_parts.append(f"Number of Vertices: {metrics['total_vertices']}")
        context_parts.append(f"Number of Wires: {metrics['total_wires']}")
        context_parts.append("")

        # Surface type distribution
        context_parts.append("## Surface Type Distribution")
        surface_dist = metrics['surface_type_distribution']
        for surf_type, count in sorted(surface_dist.items(), key=lambda x: x[1], reverse=True):
            ratio = metrics.get(f'surface_type_{surf_type.lower()}_ratio', 0)
            context_parts.append(f"{surf_type}: {count} ({ratio*100:.1f}%)")
        context_parts.append("")

        # Edge statistics
        context_parts.append("## Edge Statistics")
        context_parts.append(f"Minimum Edge Length: {metrics['edge_min_length']:.2f} mm")
        context_parts.append(f"Maximum Edge Length: {metrics['edge_max_length']:.2f} mm")
        context_parts.append(f"Average Edge Length: {metrics['edge_avg_length']:.2f} mm")
        context_parts.append(f"Total Edge Length: {metrics['edge_total_length']:.2f} mm")
        context_parts.append(f"Straight Edges: {metrics['total_straight_edges']} ({metrics['straight_edges_ratio']*100:.1f}%)")
        context_parts.append(f"Curved Edges: {metrics['total_curved_edges']} ({metrics['curved_edges_ratio']*100:.1f}%)")
        context_parts.append(f"B-Spline Edges: {metrics['total_bspline_edges']} ({metrics['bspline_edges_ratio']*100:.1f}%)")
        context_parts.append("")

        # Complexity metrics (OCI and advanced metrics)
        context_parts.append("## Complexity Metrics")
        context_parts.append(f"Overall Complexity Index (OCI): {metrics['overall_complexity_index']:.2f} ({metrics['complexity_classification']})")
        context_parts.append("")
        context_parts.append("Component Scores:")
        context_parts.append(f"  Geometric Complexity: {metrics['geometric_complexity_score']:.2f}")
        context_parts.append(f"    - Feature Count Index: {metrics['feature_count_index']:.1f}")
        context_parts.append(f"    - Surface Diversity Index: {metrics['surface_diversity_index']:.1f}")
        context_parts.append(f"    - Curvature Complexity: {metrics['curvature_complexity']:.1f}")
        context_parts.append(f"    - Freeform Surface Factor: {metrics['freeform_surface_factor']:.1f}")
        context_parts.append(f"    - Edge Complexity Index: {metrics['edge_complexity_index']:.1f}")
        context_parts.append(f"    - Face Density Index: {metrics['face_density_index']:.2f}")
        context_parts.append("")
        context_parts.append(f"  Machining Complexity: {metrics['machining_complexity_score']:.2f}")
        context_parts.append(f"    - Axis Requirement Score: {metrics['axis_requirement_score']:.1f} ({metrics['recommended_cnc_axes']})")
        context_parts.append(f"    - Tool Variety Index: {metrics['tool_variety_index']:.1f}")
        context_parts.append(f"    - Setup Complexity: {metrics['setup_complexity_score']:.1f}")
        context_parts.append(f"    - Tolerance Complexity: {metrics['tolerance_complexity_factor']:.1f}")
        context_parts.append("")
        context_parts.append(f"  Size Complexity: {metrics['size_complexity_score']:.2f}")
        context_parts.append(f"    - Envelope Volume: {metrics['envelope_volume']:.1f} cm³")
        context_parts.append(f"    - Volume Ratio: {metrics['volume_ratio']:.3f}")
        context_parts.append(f"    - Material Removal Factor: {metrics['material_removal_factor']:.1f}")
        context_parts.append(f"    - Compactness Factor: {metrics['compactness_factor']:.2f}")
        context_parts.append(f"    - Feature Size Ratio: {metrics['feature_size_ratio']:.1f}")
        context_parts.append("")
        context_parts.append(f"  Topological Complexity: {metrics['topological_complexity_index']:.2f}")
        context_parts.append(f"    - Euler Characteristic: {metrics['euler_characteristic']}")
        context_parts.append(f"    - Connectivity Index: {metrics['connectivity_index']:.2f}")
        context_parts.append("")
        context_parts.append("Additional Metrics:")
        context_parts.append(f"  Number of Different Surface Types: {metrics['num_surface_types']}")
        context_parts.append(f"  B-Spline Surfaces: {metrics['total_bspline_surfaces']}")
        context_parts.append(f"  Average Surface Types per Object: {metrics['avg_unique_surface_types_per_object']:.1f}")
        context_parts.append(f"  Average Edge Types per Object: {metrics['avg_unique_edge_types_per_object']:.1f}")
        context_parts.append("")

        # Detailed object information
        if self.data.get('objects'):
            context_parts.append("## Detailed Object Information")
            for i, obj in enumerate(self.data['objects'], 1):
                context_parts.append(f"### Object {i}: {obj.get('name', 'unnamed')}")
                context_parts.append(f"Volume: {obj.get('volume', 0):.2f} mm^3")
                context_parts.append(f"Surface Area: {obj.get('surface_area', 0):.2f} mm^2")

                topo = obj.get('topology', {})
                context_parts.append(f"Faces: {topo.get('num_faces', 0)}, "
                                   f"Edges: {topo.get('num_edges', 0)}, "
                                   f"Vertices: {topo.get('num_vertices', 0)}")

                # Surface types for this object
                surface_types = obj.get('surface_types', [])
                if surface_types:
                    surface_counter = Counter(surface_types)
                    surf_str = ", ".join([f"{k}: {v}" for k, v in surface_counter.items()])
                    context_parts.append(f"Surface Types: {surf_str}")

                # Edge types for this object
                edge_types = obj.get('edge_types', [])
                if edge_types:
                    edge_counter = Counter(edge_types)
                    edge_str = ", ".join([f"{k}: {v}" for k, v in edge_counter.items()])
                    context_parts.append(f"Edge Types: {edge_str}")

                context_parts.append("")

        # Validity
        context_parts.append("## Validity")
        context_parts.append(f"Valid: {'Yes' if metrics['is_valid'] else 'No'}")
        context_parts.append(f"Closed: {'Yes' if metrics['is_closed'] else 'No'}")

        return "\n".join(context_parts)

    def save_metrics(self, output_file: Path, format: str = 'json'):
        """
        Saves the calculated metrics.

        Args:
            output_file: Path to output file
            format: Format ('json' or 'csv')
        """
        metrics = self.calculate_metrics()

        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        elif format == 'csv':
            import csv
            with open(output_file, 'w', newline='') as f:
                # Flatten nested structures
                flat_metrics = {}
                for key, value in metrics.items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            flat_metrics[f"{key}_{subkey}"] = subvalue
                    else:
                        flat_metrics[key] = value

                writer = csv.DictWriter(f, fieldnames=flat_metrics.keys())
                writer.writeheader()
                writer.writerow(flat_metrics)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save_vlm_context(self, output_file: Path):
        """
        Saves the VLM context building block.

        Args:
            output_file: Path to output file
        """
        context = self.generate_vlm_context()
        with open(output_file, 'w') as f:
            f.write(context)


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(
        description='Process CAD analysis files and generate metrics or VLM context'
    )

    parser.add_argument(
        'analysis_file',
        type=Path,
        help='Path to analysis JSON file'
    )

    parser.add_argument(
        '--mode',
        choices=['metrics', 'vlm', 'both'],
        default='both',
        help='Processing mode: metrics (metrics), vlm (VLM context), both (both)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output file (default: derived from input name)'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'csv'],
        default='json',
        help='Output format for metrics (only with --mode metrics or both)'
    )

    args = parser.parse_args()

    # Validation
    if not args.analysis_file.exists():
        print(f"Error: File {args.analysis_file} not found")
        return 1

    # Create processor
    processor = CADMetricsProcessor(args.analysis_file)

    # Determine output file(s)
    base_name = args.analysis_file.stem

    if args.mode in ['metrics', 'both']:
        if args.output and args.mode == 'metrics':
            metrics_file = args.output
        else:
            ext = 'json' if args.format == 'json' else 'csv'
            metrics_file = args.analysis_file.parent / f"{base_name}_metrics.{ext}"

        print(f"Calculating metrics...")
        processor.save_metrics(metrics_file, format=args.format)
        print(f"Metrics saved: {metrics_file}")

    if args.mode in ['vlm', 'both']:
        if args.output and args.mode == 'vlm':
            vlm_file = args.output
        else:
            vlm_file = args.analysis_file.parent / f"{base_name}_vlm_context.txt"

        print(f"Generating VLM context...")
        processor.save_vlm_context(vlm_file)
        print(f"VLM context saved: {vlm_file}")

    print("Done.")
    return 0


if __name__ == '__main__':
    exit(main())
