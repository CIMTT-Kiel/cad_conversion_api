"""
STEP to Image Renderer
Konvertiert STEP-Dateien in orthogonale PNG-Ansichten mittels pythonocc und pyrender.
Unterstützt drei Rendering-Modi: shaded, wireframe, shaded_with_edges
"""

import os
import tempfile
import gc
import numpy as np

# OCC imports
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.GCPnts import GCPnts_UniformDeflection
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

# Rendering imports
try:
    import trimesh
    import pyrender
    import imageio
    RENDERING_AVAILABLE = True
except ImportError as e:
    RENDERING_AVAILABLE = False
    IMPORT_ERROR = str(e)


def extract_edges_from_step(step_file, deflection=0.1):
    """
    Extrahiert geometrische Kanten direkt aus der STEP-Datei.

    Args:
        step_file: Pfad zur STEP-Eingabedatei
        deflection: Genauigkeit der Kantendiskretisierung

    Returns:
        tuple: (edge_lines, bounds) - Liste von Linien und Bounding Box
    """
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)

    if status != 1:
        raise RuntimeError(f"STEP-Datei konnte nicht gelesen werden: {step_file}")

    reader.TransferRoots()
    shape = reader.OneShape()

    # Bounding Box
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    bounds = np.array([[xmin, ymin, zmin], [xmax, ymax, zmax]])

    # Extrahiere Kanten
    edge_explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    edge_lines = []

    while edge_explorer.More():
        edge = edge_explorer.Current()
        curve_adaptor = BRepAdaptor_Curve(edge)
        discretizer = GCPnts_UniformDeflection(curve_adaptor, deflection)

        if discretizer.IsDone():
            n_points = discretizer.NbPoints()
            for i in range(1, n_points):
                p1 = discretizer.Value(i)
                p2 = discretizer.Value(i + 1)
                edge_lines.append([
                    [p1.X(), p1.Y(), p1.Z()],
                    [p2.X(), p2.Y(), p2.Z()]
                ])

        edge_explorer.Next()

    print(f"Extrahiert: {len(edge_lines)} geometrische Kantensegmente")
    return edge_lines, bounds


def convert_step_to_stl(step_file, stl_path, linear_deflection=0.1):
    """Konvertiert STEP zu STL."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)

    if status != 1:
        raise RuntimeError(f"STEP-Datei konnte nicht gelesen werden: {step_file}")

    reader.TransferRoots()
    shape = reader.OneShape()

    BRepMesh_IncrementalMesh(shape, linear_deflection)

    writer = StlAPI_Writer()
    writer.Write(shape, stl_path)

    return stl_path


def filter_silhouette_edges(edge_lines, edge_face_data, view_direction, box_center):
    """
    Filtert Kanten, die Silhouetten bilden (wo angrenzende Flächen in unterschiedliche Richtungen zeigen).

    Args:
        edge_lines: Liste aller Kantensegmente
        edge_face_data: Liste mit (edge_idx, face_normals) für jede Kante
        view_direction: Kamera-Blickrichtung (normalisiert)
        box_center: Zentrum des Objekts

    Returns:
        list: Gefilterte Liste von Kantensegmenten (nur Silhouetten)
    """
    silhouette_edges = []

    for seg_idx, face_normals in edge_face_data:
        if len(face_normals) == 0:
            # Freie Kante (nur eine Fläche) -> immer Silhouette
            silhouette_edges.append(edge_lines[seg_idx])
        elif len(face_normals) == 1:
            # Randkante -> immer sichtbar
            silhouette_edges.append(edge_lines[seg_idx])
        elif len(face_normals) >= 2:
            # Innere Kante: Prüfe ob die Flächen in unterschiedliche Richtungen zeigen
            # Eine Fläche zeigt zur Kamera, die andere weg -> Silhouette
            dot_products = [np.dot(n, view_direction) for n in face_normals]

            # Silhouette wenn die Flächen in unterschiedliche Richtungen zeigen
            # (eine zur Kamera, eine weg)
            if any(d > 0.01 for d in dot_products) and any(d < -0.01 for d in dot_products):
                silhouette_edges.append(edge_lines[seg_idx])

    return silhouette_edges


def generate_camera_positions(num_views, box_center, cam_distance):
    """
    Generiert gleichmäßig verteilte Kamerapositionen auf einer Sphäre.

    Args:
        num_views: Anzahl der gewünschten Ansichten
        box_center: Zentrum des Objekts
        cam_distance: Abstand der Kamera vom Zentrum

    Returns:
        list: Liste von (name, position, up_vector) Tupeln
    """
    positions = []

    # Fibonacci-Spirale auf Sphäre für gleichmäßige Verteilung
    golden_ratio = (1 + np.sqrt(5)) / 2

    for i in range(num_views):
        # Theta (Polarwinkel): 0 bis pi
        theta = np.arccos(1 - 2 * (i + 0.5) / num_views)

        # Phi (Azimutwinkel): 0 bis 2*pi
        phi = 2 * np.pi * i / golden_ratio

        # Sphärische zu kartesische Koordinaten
        x = np.sin(theta) * np.cos(phi)
        y = np.sin(theta) * np.sin(phi)
        z = np.cos(theta)

        direction = np.array([x, y, z])
        cam_pos = box_center + direction * cam_distance

        # Up-Vektor: Standard ist Z-up, aber anpassen wenn nötig
        up = np.array([0, 0, 1])

        # Wenn Kamera von oben oder unten schaut, nutze Y als Up
        if abs(z) > 0.9:
            up = np.array([0, 1, 0])

        # Name basierend auf Position
        angle_deg = int(np.degrees(phi) % 360)
        elev_deg = int(np.degrees(theta))
        name = f"view_{i:03d}_az{angle_deg:03d}_el{elev_deg:03d}"

        positions.append({
            'name': name,
            'position': cam_pos,
            'direction': -direction,  # Schaut zum Zentrum
            'up_vector': up,
            'azimuth': angle_deg,
            'elevation': elev_deg
        })

    return positions


def create_camera_pose(cam_pos, target, up_vector):
    """Erstellt Kamera-Transformationsmatrix."""
    forward = target - cam_pos
    forward = forward / np.linalg.norm(forward)

    right = np.cross(forward, up_vector)
    right = right / np.linalg.norm(right)

    up = np.cross(right, forward)
    up = up / np.linalg.norm(up)

    camera_pose = np.eye(4)
    camera_pose[:3, 0] = right
    camera_pose[:3, 1] = up
    camera_pose[:3, 2] = -forward
    camera_pose[:3, 3] = cam_pos

    return camera_pose


def render_geometry(stl_path, edge_lines, output_dir, basename,
                   resolution=(1280, 720), render_mode='shaded_with_edges',
                   edge_color=(0.1, 0.1, 0.1), edge_width=2.0, transparency=1.0,
                   total_imgs=3, edge_face_data=None):
    """
    Rendert Geometrie in verschiedenen Modi.

    Args:
        stl_path: Pfad zur STL-Datei
        edge_lines: Geometrische Kanten aus STEP
        output_dir: Ausgabeverzeichnis
        basename: Basisname der Dateien
        resolution: Bildgröße (width, height)
        render_mode: 'shaded', 'wireframe', 'shaded_with_edges'
        edge_color: RGB-Farbe für Kanten (0-1)
        edge_width: Kantenbreite in Pixeln
        transparency: Transparenz 0.0 (durchsichtig) bis 1.0 (opak)
        total_imgs: Anzahl der Perspektiven (gleichmäßig verteilt)
        edge_face_data: Optional - Face-Daten für Silhouetten-Erkennung (nur für 'shaded' Modus)

    Returns:
        dict: {'images': list, 'perspectives': list}
    """
    if not RENDERING_AVAILABLE:
        raise RuntimeError(f"Rendering nicht verfügbar: {IMPORT_ERROR}")

    w, h = resolution

    # Lade Mesh nur wenn benötigt (shaded Modi)
    mesh = None
    if render_mode in ['shaded', 'shaded_with_edges']:
        mesh = trimesh.load_mesh(stl_path, force='mesh')
        bounds = mesh.bounds
    else:
        # Für Wireframe: Bounds aus Edge-Lines berechnen
        all_points = []
        for line in edge_lines:
            all_points.extend(line)
        all_points = np.array(all_points)
        bounds = np.array([all_points.min(axis=0), all_points.max(axis=0)])

    box_center = (bounds[0] + bounds[1]) / 2
    box_size = np.linalg.norm(bounds[1] - bounds[0])

    print(f"Rendering-Modus: {render_mode}")
    print(f"Bounding Box: {bounds[0]} bis {bounds[1]}")

    # Szene erstellen
    scene = pyrender.Scene(bg_color=[1.0, 1.0, 1.0, 1.0], ambient_light=[0.3, 0.3, 0.3])

    # Füge Geometrie basierend auf Modus hinzu
    if render_mode in ['shaded', 'shaded_with_edges']:
        # Material mit Transparenz
        alpha = max(0.0, min(1.0, transparency))  # Clamp auf [0, 1]
        material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[0.6, 0.6, 0.65, alpha],  # Alpha-Kanal für Transparenz
            metallicFactor=0.8,
            roughnessFactor=0.3,
            alphaMode='BLEND' if alpha < 1.0 else 'OPAQUE'
        )
        pmesh = pyrender.Mesh.from_trimesh(mesh, material=material, smooth=False)
        scene.add(pmesh)

        # Beleuchtung
        scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=4.0),
                 pose=np.array([[1,0,0,3],[0,1,0,-3],[0,0,1,5],[0,0,0,1]]))
        scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.5),
                 pose=np.array([[1,0,0,-5],[0,1,0,0],[0,0,1,3],[0,0,0,1]]))
        scene.add(pyrender.DirectionalLight(color=[0.9, 0.9, 1.0], intensity=1.5),
                 pose=np.array([[1,0,0,0],[0,1,0,5],[0,0,1,2],[0,0,0,1]]))

    # Renderer erstellen
    renderer = pyrender.OffscreenRenderer(viewport_width=w, viewport_height=h)

    # Generiere Kamerapositionen
    cam_distance = box_size * 2.5
    camera_views = generate_camera_positions(total_imgs, box_center, cam_distance)

    rendered_images = []
    perspectives = []

    for view_data in camera_views:
        view_name = view_data['name']
        cam_pos = view_data['position']
        up_vector = view_data['up_vector']
        view_direction = view_data['direction']

        camera_pose = create_camera_pose(cam_pos, box_center, up_vector)

        print(f"Rendering {view_name} (Azimuth: {view_data['azimuth']}°, Elevation: {view_data['elevation']}°)...")

        camera = pyrender.PerspectiveCamera(yfov=np.pi / 4.0, aspectRatio=w/h)
        cam_node = scene.add(camera, pose=camera_pose)

        # Render
        color, depth = renderer.render(scene)

        # Füge Kanten hinzu
        edges_to_draw = edge_lines
        if render_mode == 'shaded' and edge_lines and edge_face_data:
            # Filtere Silhouetten-Kanten
            edges_to_draw = filter_silhouette_edges(edge_lines, edge_face_data, view_direction, box_center)
            if edges_to_draw:
                color = draw_edges_on_image(color, edges_to_draw, camera_pose,
                                           w, h, box_center, cam_distance,
                                           edge_color, edge_width)
        elif render_mode in ['wireframe', 'shaded_with_edges'] and edge_lines:
            # Projiziere alle 3D-Kanten auf 2D-Bildebene
            color = draw_edges_on_image(color, edge_lines, camera_pose,
                                       w, h, box_center, cam_distance,
                                       edge_color, edge_width)

        # Speichern
        output_path = os.path.join(output_dir, f"{basename}_{view_name}.png")
        imageio.imwrite(output_path, color)
        print(f"✅ Gespeichert: {output_path}")

        rendered_images.append(f"{basename}_{view_name}.png")
        perspectives.append({
            'filename': f"{basename}_{view_name}.png",
            'azimuth': view_data['azimuth'],
            'elevation': view_data['elevation'],
            'camera_position': cam_pos.tolist(),
            'camera_direction': view_data['direction'].tolist()
        })

        scene.remove_node(cam_node)

    renderer.delete()

    return {
        'images': rendered_images,
        'perspectives': perspectives
    }


def draw_edges_on_image(image, edge_lines, camera_pose, width, height,
                        center, distance, edge_color, edge_width):
    """Zeichnet 3D-Kanten auf 2D-Bild durch Projektion."""
    from scipy import ndimage

    # Erstelle View- und Projection-Matrix
    view_matrix = np.linalg.inv(camera_pose)
    fov = np.pi / 4.0
    aspect = width / height
    near, far = 0.1, distance * 10

    f = 1.0 / np.tan(fov / 2.0)
    proj_matrix = np.array([
        [f/aspect, 0, 0, 0],
        [0, f, 0, 0],
        [0, 0, -(far+near)/(far-near), -(2*far*near)/(far-near)],
        [0, 0, -1, 0]
    ])

    # Maske für Kanten
    edge_mask = np.zeros((height, width), dtype=bool)

    for line in edge_lines:
        p1, p2 = np.array(line[0]), np.array(line[1])

        # Transformiere zu Clip-Space
        p1_clip = proj_matrix @ view_matrix @ np.append(p1, 1)
        p2_clip = proj_matrix @ view_matrix @ np.append(p2, 1)

        # Perspective Division
        if abs(p1_clip[3]) > 1e-6 and abs(p2_clip[3]) > 1e-6:
            p1_ndc = p1_clip[:3] / p1_clip[3]
            p2_ndc = p2_clip[:3] / p2_clip[3]

            # Zu Screen-Space
            x1 = int((p1_ndc[0] + 1) * width / 2)
            y1 = int((1 - p1_ndc[1]) * height / 2)
            x2 = int((p2_ndc[0] + 1) * width / 2)
            y2 = int((1 - p2_ndc[1]) * height / 2)

            # Zeichne Linie (Bresenham-ähnlich)
            if 0 <= x1 < width and 0 <= y1 < height and 0 <= x2 < width and 0 <= y2 < height:
                draw_line(edge_mask, x1, y1, x2, y2)

    # Verdicke Kanten
    if edge_width > 1:
        edge_mask = ndimage.binary_dilation(edge_mask, iterations=int(edge_width))

    # Überlage auf Bild
    edge_color_rgb = (np.array(edge_color) * 255).astype(np.uint8)
    image[edge_mask] = edge_color_rgb

    return image


def draw_line(mask, x0, y0, x1, y1):
    """Bresenham-Linienalgorithmus."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < mask.shape[1] and 0 <= y0 < mask.shape[0]:
            mask[y0, x0] = True

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def step_to_images(step_file, part_number, output_dir="./renders",
                   resolution=(1280, 720), stl_deflection=0.1,
                   cleanup_stl=True, render_mode='shaded_with_edges',
                   edge_color=(0.1, 0.1, 0.1), edge_width=2.0, transparency=1.0,
                   total_imgs=3):
    """
    Hauptfunktion: Konvertiert STEP-Datei zu PNG-Ansichten.

    Args:
        step_file: Pfad zur STEP-Datei
        part_number: Teil-Identifikator
        output_dir: Ausgabeverzeichnis
        resolution: Bildgröße (width, height)
        stl_deflection: Tessellierungs-Genauigkeit
        cleanup_stl: STL nach Rendering löschen
        render_mode: 'shaded', 'wireframe', 'shaded_with_edges'
        edge_color: RGB-Farbe für Kanten (0-1)
        edge_width: Kantenbreite in Pixeln
        transparency: Transparenz 0.0 (durchsichtig) bis 1.0 (opak/undurchsichtig)
        total_imgs: Anzahl der Perspektiven (gleichmäßig verteilt auf Sphäre)

    Returns:
        dict: {'success': bool, 'output_dir': str, 'images': list, 'perspectives': list}
    """
    # os.makedirs(output_dir, exist_ok=True)
    # part_output_dir = os.path.join(output_dir, part_number)
    # os.makedirs(part_output_dir, exist_ok=True)

    stl_path = os.path.join(tempfile.gettempdir(), f"{part_number}.stl")

    try:
        print(f"\n{'='*60}")
        print(f"Konvertiere: {step_file}")
        print(f"{'='*60}")

        # Extrahiere geometrische Kanten
        edge_lines = None
        edge_face_data = None

        if render_mode in ['wireframe', 'shaded_with_edges']:
            # Vollständige Kanten ohne Face-Info
            edge_lines, _ = extract_edges_from_step(step_file, deflection=stl_deflection)
        elif render_mode == 'shaded':
            # Kanten mit Face-Info für Silhouetten-Erkennung
            edge_lines, _ = extract_edges_from_step(step_file,
                                                                     deflection=stl_deflection
                                                                    )

        # Erstelle STL (außer bei reinem Wireframe)
        if render_mode != 'wireframe':
            convert_step_to_stl(step_file, stl_path, linear_deflection=stl_deflection)
            print(f"✅ STL erstellt: {stl_path}")

        # Render
        print(f"\nRendere {total_imgs} Ansichten...")
        render_result = render_geometry(stl_path, edge_lines, part_output_dir, part_number,
                                       resolution, render_mode, edge_color, edge_width,
                                       transparency, total_imgs)

        # Speichere Perspektiven-Daten als JSON
        # import json
        # perspectives_file = os.path.join(part_output_dir, f"{part_number}_perspectives.json")
        # with open(perspectives_file, 'w') as f:
        #     json.dump(render_result['perspectives'], f, indent=2)
        # print(f"💾 Perspektiven gespeichert: {perspectives_file}")

        print(f"\n{'='*60}")
        print(f"✅ Erfolgreich abgeschlossen!")
        print(f"   Modus: {render_mode}")
        print(f"   Ansichten: {total_imgs}")
        print(f"   Ausgabe: {part_output_dir}")
        print(f"{'='*60}\n")

        return {
            'success': True,
            'images': render_result['images'],
            'perspectives': render_result['perspectives']
        }

    except Exception as e:
        raise RuntimeError(f"Fehler: {e}") from e

    finally:
        if cleanup_stl and os.path.exists(stl_path):
            try:
                os.remove(stl_path)
                print(f"🗑️  STL gelöscht: {stl_path}")
            except:
                pass
        gc.collect()


if __name__ == "__main__":
    # Test-STEP-Datei erstellen
    test_step_file = "example.step"

    if not os.path.exists(test_step_file):
        print(f"Erstelle Test-STEP-Datei: {test_step_file}")
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCC.Extend.DataExchange import write_step_file

        box = BRepPrimAPI_MakeBox(100, 50, 30).Shape()
        write_step_file(box, test_step_file)
        print("✅ Test-STEP-Datei erstellt\n")

    # Rendering durchführen
    try:
        result = step_to_images(
            step_file=test_step_file,
            part_number="part_001",
            output_dir="./renders",
            resolution=(1280, 720),
            stl_deflection=0.1,
            cleanup_stl=True,
            render_mode='shaded_with_edges',  # 'shaded', 'wireframe', 'shaded_with_edges'
            edge_color=(0.1, 0.1, 0.1),
            edge_width=2.0,
            transparency=1.0,  # 0.0 = durchsichtig, 1.0 = opak
            total_imgs=22  # Anzahl der Perspektiven
        )

        result = step_to_images(
            step_file=test_step_file,
            part_number="part_003",
            output_dir="./renders",
            resolution=(1280, 720),
            stl_deflection=0.1,
            cleanup_stl=False,
            render_mode='wireframe',  # 'shaded', 'wireframe', 'shaded_with_edges'
            edge_color=(0.1, 0.1, 0.1),
            edge_width=2.0,
            transparency=1.0,  # 0.0 = durchsichtig, 1.0 = opak
            total_imgs=12  # Anzahl der Perspektiven
        )

        result = step_to_images(
            step_file=test_step_file,
            part_number="part_002",
            output_dir="./renders",
            resolution=(1280, 720),
            stl_deflection=0.1,
            cleanup_stl=False,
            render_mode='shaded',  # 'shaded', 'wireframe', 'shaded_with_edges'
            edge_color=(0.1, 0.1, 0.1),
            edge_width=2.0,
            transparency=1.0,  # 0.0 = durchsichtig, 1.0 = opak
            total_imgs=12  # Anzahl der Perspektiven
        )



        print(f"Erfolgreich gerendert:")
        for img in result['images']:
            print(f"  - {img}")

    except Exception as e:
        print(f"❌ Fehler: {e}")
