"""Technical Drawing Views Generator - Creates orthographic DXF projections using FreeCAD TechDraw."""

import logging, os, shutil, sys, tempfile
from pathlib import Path
from typing import List, Union
import ezdxf, FreeCAD, Part, TechDraw

logger = logging.getLogger(__name__)


class DrawingViewsError(Exception):
    """Custom exception for drawing views errors."""
    pass


class DrawingViewsGenerator:
    """Generate orthographic technical drawing views (top, front, side) from STEP files."""

    STANDARD_VIEWS = {'top': [0, 0, 1], 'front': [0, 1, 0], 'side': [1, 0, 0]}

    def __init__(self, step_file: Union[str, Path]):
        """Initialize generator with STEP file."""
        self.step_file = Path(step_file)
        if not self.step_file.exists():
            raise DrawingViewsError(f"STEP file not found: {self.step_file}")
        if self.step_file.suffix.lower() not in ['.step', '.stp']:
            raise DrawingViewsError(f"Only STEP files supported: {self.step_file.suffix}")

        self.temp_dir = self.step_file.parent / "tmp_drawing"
        self.temp_dir.mkdir(exist_ok=True)
        logger.info(f"Initialized for {self.step_file}")

    def generate_views(self, output_dir: Union[str, Path]) -> List[Path]:
        """Generate technical drawing views as DXF files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating views to {output_dir}")

        doc_name = 'TempDrawing'
        try:
            if FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.Name == doc_name:
                FreeCAD.closeDocument(doc_name)

            newdoc = FreeCAD.newDocument(doc_name)
            FreeCAD.setActiveDocument(doc_name)
            doc = FreeCAD.getDocument(doc_name)

            doc.addObject('TechDraw::DrawPage', 'Page')
            doc.addObject('TechDraw::DrawSVGTemplate', 'Template')
            doc.Page.Template = doc.Template

            shape = Part.Shape()
            shape.read(str(self.step_file))
            geom = doc.addObject('Part::Feature', 'Shape')
            geom.Shape = shape

            source = [obj for obj in doc.findObjects() if type(obj) == Part.Feature]

            doc.addObject('TechDraw::DrawViewPart', 'View')
            doc.View.Source = source
            doc.View.XDirection = FreeCAD.Vector(1.000, 0.000, 0.000)
            doc.Page.addView(doc.View)
            doc.recompute()

            output_files = []
            for view_name, direction in self.STANDARD_VIEWS.items():
                try:
                    doc.View.Direction = FreeCAD.Vector(direction[0], direction[1], direction[2])
                    doc.recompute()
                    doc.View.recompute()
                    doc.recompute()

                    temp_dxf_file = self.temp_dir / f"view_{view_name}.dxf"
                    TechDraw.writeDXFPage(doc.Page, str(temp_dxf_file))

                    output_dxf_file = output_dir / f"{view_name}_view.dxf"
                    shutil.copy2(temp_dxf_file, output_dxf_file)
                    output_files.append(output_dxf_file)

                    try:
                        dxf_doc = ezdxf.readfile(str(output_dxf_file))
                        entity_count = len(list(dxf_doc.modelspace()))
                        logger.debug(f"{view_name}: {entity_count} entities")
                    except:
                        pass

                    logger.info(f"Created {view_name} view")

                except Exception as e:
                    logger.error(f"Failed to generate {view_name}: {str(e)}")
                    raise DrawingViewsError(f"View generation failed for {view_name}: {str(e)}")

            logger.info(f"Generated {len(output_files)} DXF views")
            return output_files

        except Exception as e:
            logger.error(f"Drawing views generation failed: {str(e)}")
            raise DrawingViewsError(f"Failed to generate views: {str(e)}")

        finally:
            try:
                if FreeCAD.ActiveDocument:
                    FreeCAD.closeDocument(doc_name)
            except Exception as e:
                logger.warning(f"Failed to close FreeCAD document: {str(e)}")
