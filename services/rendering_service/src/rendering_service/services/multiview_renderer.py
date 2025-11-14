"""
STEP to Image Renderer
Renders multiple PNG images from a STEP file using OCC and Pyrender according to the RotationNet Approach - with angle information and render modi.
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
    extract  edges from the STEP file.

    Args:
        step_file: path to file
        deflection: tesselation accuracy

    Returns:
        tuple: (edge_lines, bounds) - list of edge segments and bounding box
    """
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)

    if status != 1:
        raise RuntimeError(f"STEP-file not found: {step_file}")

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

    return edge_lines, bounds


def convert_step_to_stl(step_file, stl_path, linear_deflection=0.1):
    """Konvertiert STEP zu STL."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file)

    if status != 1:
        raise RuntimeError(f"STEP-file not found: {step_file}")

    reader.TransferRoots()
    shape = reader.OneShape()

    BRepMesh_IncrementalMesh(shape, linear_deflection)

    writer = StlAPI_Writer()
    writer.Write(shape, stl_path)

    return stl_path


def filter_silhouette_edges(edge_lines, edge_face_data, view_direction, box_center):
    """
    filter silhouette edges based on view direction.

    Args:
        edge_lines: list of edge segments
        edge_face_data: list of (segment_index, [face_normals])
        view_direction: camera view direction
        box_center: center of the object bounding box

    Returns:
        list: silhouette edge segments only
    """
    silhouette_edges = []

    for seg_idx, face_normals in edge_face_data:
        if len(face_normals) == 0:
            # always visible
            silhouette_edges.append(edge_lines[seg_idx])
        elif len(face_normals) == 1:
            # always visible 
            silhouette_edges.append(edge_lines[seg_idx])
        elif len(face_normals) >= 2:
            # inner angle between face normals and view direction
            dot_products = [np.dot(n, view_direction) for n in face_normals]

            # if signs differ, it's a silhouette edge
            if any(d > 0.01 for d in dot_products) and any(d < -0.01 for d in dot_products):
                silhouette_edges.append(edge_lines[seg_idx])

    return silhouette_edges


def generate_camera_positions(num_views, box_center, cam_distance):
    """
    generate camera positions on a sphere around the object with regulized patterns according to total positions by fibonacci-spiral.

    Args:
        num_views: total number of views
        box_center: center of the object bounding box
        cam_distance: distance from box center

    Returns:
        list: camera position dicts with 'name', 'position', 'direction', 'up_vector', 'azimuth', 'elevation'
    """
    positions = []


    golden_ratio = (1 + np.sqrt(5)) / 2

    for i in range(num_views):
        # Theta elevation in rad
        theta = np.arccos(1 - 2 * (i + 0.5) / num_views)

        # Phi azimuth in rad
        phi = 2 * np.pi * i / golden_ratio

        #  spherical to Cartesian coordiates
        x = np.sin(theta) * np.cos(phi)
        y = np.sin(theta) * np.sin(phi)
        z = np.cos(theta)

        direction = np.array([x, y, z])
        cam_pos = box_center + direction * cam_distance

        # define default up direction by z axis
        up = np.array([0, 0, 1])

        # avoid singularity at poles with the up vector
        if abs(z) > 0.9:
            up = np.array([0, 1, 0])

        # compute angle and elevation in degrees for file name
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
    """generate camera pose matrix from position, target and up vector."""
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
    render multiple images from different perspectives.

    Args:
        stl_path: path to STL file
        edge_lines: list of edge segments
        output_dir: directory to save images
        basename: base name for image files
        resolution: (width, height) of images
        render_mode: 'shaded', 'wireframe', 'shaded_with_edges'
        edge_color: RGB color for edges (0-1)
        edge_width: width of edges in pixels
        transparency: transparency 0.0 (transparent) to 1.0 (opaque)
        total_imgs: total number of images to render
        edge_face_data: list of (segment_index, [face_normals]) for silhouette detection
    Returns:
        dict: {'images': list, 'perspectives': list}
    """
    if not RENDERING_AVAILABLE:
        raise RuntimeError(f"Rendering was not successfull!")

    w, h = resolution

    # load file
    mesh = None
    if render_mode in ['shaded', 'shaded_with_edges']:
        mesh = trimesh.load_mesh(stl_path, force='mesh')
        bounds = mesh.bounds
    else:
        # only edges for wireframe modus
        all_points = []
        for line in edge_lines:
            all_points.extend(line)
        all_points = np.array(all_points)
        bounds = np.array([all_points.min(axis=0), all_points.max(axis=0)])

    box_center = (bounds[0] + bounds[1]) / 2
    box_size = np.linalg.norm(bounds[1] - bounds[0])

    print(f"modus: {render_mode}")
    print(f"bb: {bounds[0]} to {bounds[1]}")

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

        # Lightning 
        scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=4.0),
                 pose=np.array([[1,0,0,3],[0,1,0,-3],[0,0,1,5],[0,0,0,1]]))
        scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.5),
                 pose=np.array([[1,0,0,-5],[0,1,0,0],[0,0,1,3],[0,0,0,1]]))
        scene.add(pyrender.DirectionalLight(color=[0.9, 0.9, 1.0], intensity=1.5),
                 pose=np.array([[1,0,0,0],[0,1,0,5],[0,0,1,2],[0,0,0,1]]))

    # initialize renderer
    renderer = pyrender.OffscreenRenderer(viewport_width=w, viewport_height=h)

    # get camera positions
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

        color, depth = renderer.render(scene)

        # add edges
        edges_to_draw = edge_lines
        if render_mode == 'shaded' and edge_lines and edge_face_data:
            # filter silhouette edges only
            edges_to_draw = filter_silhouette_edges(edge_lines, edge_face_data, view_direction, box_center)
            if edges_to_draw:
                color = draw_edges_on_image(color, edges_to_draw, camera_pose,
                                           w, h, box_center, cam_distance,
                                           edge_color, edge_width)
        elif render_mode in ['wireframe', 'shaded_with_edges'] and edge_lines:
            # process all edges on image
            color = draw_edges_on_image(color, edge_lines, camera_pose,
                                       w, h, box_center, cam_distance,
                                       edge_color, edge_width)

        # sace to image file
        output_path = os.path.join(output_dir, f"{basename}_{view_name}.png")
        imageio.imwrite(output_path, color)
        print(f"Saved file: {output_path}")

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
    """Draw edges on rendered image."""
    from scipy import ndimage

    # Create a writable copy of the image
    image = np.array(image, copy=True)

    # generate view and projection matrices
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

    # get mask for edges
    edge_mask = np.zeros((height, width), dtype=bool)

    for line in edge_lines:
        p1, p2 = np.array(line[0]), np.array(line[1])

        # transform to clip space
        p1_clip = proj_matrix @ view_matrix @ np.append(p1, 1)
        p2_clip = proj_matrix @ view_matrix @ np.append(p2, 1)

        # perspective divide
        if abs(p1_clip[3]) > 1e-6 and abs(p2_clip[3]) > 1e-6:
            p1_ndc = p1_clip[:3] / p1_clip[3]
            p2_ndc = p2_clip[:3] / p2_clip[3]

            # to screen space
            x1 = int((p1_ndc[0] + 1) * width / 2)
            y1 = int((1 - p1_ndc[1]) * height / 2)
            x2 = int((p2_ndc[0] + 1) * width / 2)
            y2 = int((1 - p2_ndc[1]) * height / 2)

            # draw lines
            if 0 <= x1 < width and 0 <= y1 < height and 0 <= x2 < width and 0 <= y2 < height:
                draw_line(edge_mask, x1, y1, x2, y2)

    # thicken the edges
    if edge_width > 1:
        edge_mask = ndimage.binary_dilation(edge_mask, iterations=int(edge_width))

    # project to image
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
    Render multiple images from a STEP file.

    Args:
        step_file: path to STEP file
        part_number: identifier for the part
        output_dir: directory to save images
        resolution: (width, height) of images
        stl_deflection: tesselation accuracy for STL conversion
        cleanup_stl: whether to delete temporary STL file after rendering
        render_mode: 'shaded', 'wireframe', 'shaded_with_edges'
        edge_color: RGB color for edges (0-1)
        edge_width: width of edges in pixels
        transparency: transparency 0.0 (transparent) to 1.0 (opaque)
        total_imgs: total number of images to render
    Returns:
        dict: {'success': bool, 'output_dir': str, 'images': list, 'perspectives': list}
    """
    os.makedirs(output_dir, exist_ok=True)
    part_output_dir = os.path.join(output_dir, part_number)
    os.makedirs(part_output_dir, exist_ok=True)

    stl_path = os.path.join(tempfile.gettempdir(), f"{part_number}.stl")

    try:
        print(f"\n{'='*60}")
        print(f"Konvertiere: {step_file}")
        print(f"{'='*60}")

        # extract edges and face data
        edge_lines = None
        edge_face_data = None

        if render_mode in ['wireframe', 'shaded_with_edges']:
            # all edges without face info
            edge_lines, _ = extract_edges_from_step(step_file, deflection=stl_deflection)
        elif render_mode == 'shaded':
            # edges with face info for silhouette detection
            edge_lines, _ = extract_edges_from_step(step_file,
                                                                     deflection=stl_deflection
                                                                    )

        # generate STL for rendering
        if render_mode != 'wireframe':
            convert_step_to_stl(step_file, stl_path, linear_deflection=stl_deflection)
            print(f"✅ STL erstellt: {stl_path}")

        # start actual rendering
        print(f"\nRendere {total_imgs} Ansichten...")
        render_result = render_geometry(stl_path, edge_lines, part_output_dir, part_number,
                                       resolution, render_mode, edge_color, edge_width,
                                       transparency, total_imgs)

        # save perspectives metadata
        import json
        perspectives_file = os.path.join(part_output_dir, f"{part_number}_perspectives.json")
        with open(perspectives_file, 'w') as f:
            json.dump(render_result['perspectives'], f, indent=2)
        print(f"💾 Perspektiven gespeichert: {perspectives_file}")

        return {
            'success': True,
            'output_dir': part_output_dir,
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
