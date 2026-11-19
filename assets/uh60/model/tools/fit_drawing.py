"""Lay the manual's station diagram (TM 1-1520-237-10 figure 6-1, a vector page) over an orthographic render of the build.

    python3 tools/fit_drawing.py work/uh60_lod1.blend side 150 810 170 345 2.5 out.jpg [--pdf refs-local/tm10.pdf] [--nodraw]
    python3 tools/fit_drawing.py work/uh60_lod1.blend top  150 810 -100 100 2.5 out.jpg

view = side (left side, nose to the left) | top (nose left, right side up, as printed) | front | any of them.
Red = the manual's drawing. The page is calibrated from its own scales: 0.5775 pt per inch,
x_pt = 157.85 + (STA - 162) * K, y_pt = 444.45 - (WL - 150) * K (side), y_pt = 142.4 + BL_right * K (top).
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Matrix, Vector
a = sys.argv[1:]
blend, view = a[0], a[1]; s0, s1, v0, v1, ppi = (float(x) for x in a[2:7]); out = a[7]
pdf = a[a.index('--pdf') + 1] if '--pdf' in a else os.path.join(os.path.dirname(__file__), '..', 'refs-local', 'tm10.pdf')
SAMPLES = int(a[a.index('--samples') + 1]) if '--samples' in a else 12
IN = 0.0254; STA0, WL0 = 341.2, 183.7; K = 0.5775
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = False
W, H = int(round((s1 - s0) * ppi)), int(round((v1 - v0) * ppi))
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = max(s1 - s0, v1 - v0) * IN; cam.clip_end = 200
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cs, cv = (s0 + s1) / 2, (v0 + v1) / 2
if view == 'side':     # camera on the left (+X), looking -X; image right = +Y (aft), up = +Z
    co.matrix_world = Matrix(((0, 0, 1, 30), (1, 0, 0, (cs - STA0) * IN), (0, 1, 0, (cv - WL0) * IN), (0, 0, 0, 1)))
elif view == 'top':    # camera above looking down; image right = +Y (aft), image up = -X (right side)
    co.matrix_world = Matrix(((0, -1, 0, -cv * IN), (1, 0, 0, (cs - STA0) * IN), (0, 0, 1, 30), (0, 0, 0, 1)))
else:                  # front: camera ahead of the nose looking aft; image right = +X?? (aircraft left appears on the right)
    co.matrix_world = Matrix(((1, 0, 0, cs * IN), (0, 0, -1, -30), (0, 1, 0, (cv - WL0) * IN), (0, 0, 0, 1)))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.9, 0.9, 0.9, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 2.5; so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(-60 if view != 'top' else 20))
sc.render.filepath = out + '.png'; sc.render.image_settings.file_format = 'PNG'; sc.render.film_transparent = False
import io, contextlib
bpy.ops.render.render(write_still=True)
from PIL import Image
im = Image.open(out + '.png').convert('RGB')
if '--nodraw' not in a and view in ('side', 'top') and os.path.exists(pdf):
    import pymupdf
    p = pymupdf.open(pdf)[382]
    sx = lambda s: 157.85 + (s - 162) * K
    if view == 'side': clip = pymupdf.Rect(sx(s0), 444.45 - (v1 - 150) * K, sx(s1), 444.45 - (v0 - 150) * K)
    else: clip = pymupdf.Rect(sx(s0) - 1.1, 142.4 - v1 * K, sx(s1) - 1.1, 142.4 - v0 * K)
    z = ppi / K
    pm = p.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip)
    d = Image.frombytes('RGB', (pm.width, pm.height), pm.samples).resize((W, H)).convert('L')
    mask = d.point(lambda v: 255 if v < 140 else 0)
    im.paste(Image.new('RGB', (W, H), (255, 0, 0)), (0, 0), mask)
im.save(out, quality=90); os.remove(out + '.png'); print('wrote', out, im.size)
