"""Check the built model against HK's own dimensioned drawing (HKTD p. 12), side view and top view.

    python3 tools/fit_drawing.py refs-local/HK416_Technical_Data.pdf [work/hk416_lod0.blend] [out_dir]

Build with `--barrel 16.5` first: the drawing shows the 16.5 in barrel with the stock collapsed.
Renders the blend orthographically at 2 px per mm, rasterises the drawing's vector lines from your local copy of the
PDF (never committed: see notes/REFERENCES.md) into the same frame, and paints them red over the render.
Writes fit_left.jpg and fit_top.jpg. Where the red lines sit on the model's edges, the model matches the drawing.

Calibration (HKTD p. 12 in PDF points, origin top left; 3.682 mm per point from HKTD's A = 855 mm and C = 240 mm):
    side view:  L = (161.55 - x) * 3.682      Z = (613.125 - y) * 3.682
    top view:   L = (426.70 - x) * 3.682      S = (y - 640.52) * 3.682   (the top view shows the right side up)
"""
import math, os, sys
import numpy as np, cv2, pymupdf, bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdf = sys.argv[1]
blend = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'work', 'hk416_lod0.blend')
out_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, 'work')
SCALE, PPM = 3.682, 2.0
VIEWS = {'left': dict(x0=161.55, y0=613.125, Z=(-215.0, 75.0), sign=1), 'top': dict(x0=426.70, y0=640.52, Z=(-50.0, 50.0), sign=-1)}
L0, L1 = -425.0, 460.0

def drawing(view, W, H):
    """The drawing's ink in the render's frame (True = line)."""
    V = VIEWS[view]; z0, z1 = V['Z']
    page = pymupdf.open(pdf)[11]
    # PDF clip covering the frame, rasterised at 24 px per point
    xa, xb = V['x0'] - L1 / SCALE, V['x0'] - L0 / SCALE
    ya, yb = V['y0'] - z1 / SCALE, V['y0'] - z0 / SCALE
    R = 24
    pm = page.get_pixmap(matrix=pymupdf.Matrix(R, R), clip=pymupdf.Rect(xa, ya, xb, yb), colorspace=pymupdf.csGRAY)
    d = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width)
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    L = L1 - (u + 0.5) / PPM; Z = z1 - (v + 0.5) / PPM
    mx = ((V['x0'] - L / SCALE - xa) * R).astype(np.float32); my = ((V['y0'] - Z / SCALE - ya) * R).astype(np.float32)
    return cv2.remap(d, mx, my, cv2.INTER_AREA, borderValue=255) < 140

def render(view):
    V = VIEWS[view]; z0, z1 = V['Z']
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.device = 'CPU'
    sc.render.resolution_x = int((L1 - L0) * PPM); sc.render.resolution_y = int((z1 - z0) * PPM); sc.render.resolution_percentage = 100
    sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'
    cam = bpy.data.objects.new('fit_cam', bpy.data.cameras.new('fit_cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = (L1 - L0) / 1000.0; cam.data.clip_end = 10
    Lc, Zc = (L0 + L1) / 2000, (z0 + z1) / 2000
    if view == 'left': cam.location = (2.0, -Lc, Zc); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    else: cam.location = (-Zc, -Lc, 2.0); cam.rotation_euler = (0, 0, math.radians(90))
    if not sc.world: sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True; sc.world.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    path = os.path.join(out_dir, f'_fit_{view}.png'); sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    return path

for view in ('left', 'top'):
    r = cv2.imread(render(view), cv2.IMREAD_UNCHANGED)
    a = r[..., 3:4] / 255.0; r = (r[..., :3] * a + 235 * (1 - a)).astype(np.uint8)
    ink = drawing(view, r.shape[1], r.shape[0])
    r[ink] = (0.25 * r[ink] + 0.75 * np.array([0, 0, 255])).astype(np.uint8)
    out = os.path.join(out_dir, f'fit_{view}.jpg'); cv2.imwrite(out, r, [cv2.IMWRITE_JPEG_QUALITY, 90]); print('FIT', out)
