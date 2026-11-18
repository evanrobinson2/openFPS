"""openFPS grenades: frag, impact (game-only), flash, smoke (red/yellow/green/violet) and smoke-white.
Rebuilds every variant from nothing. Exterior only: every body is a solid placeholder, nothing inside is modelled.

    blender -b --python build.py                              # all variants, LOD0 + LOD1  -> work/*.glb (ignored by git)
    blender -b --python build.py -- --only frag,flash --lod 0
    blender -b --python build.py -- --m18-livery figure       # M18 paint as Fig. B-3 shows it (dark body, light marks)
    blender -b --python build.py -- --flash-holes 12          # Table A-5 hole count (6 columns x 2 rows) instead of Fig. A-12's 6 x 3

Modelling frame (mm): Z up along the grenade's axis, +X = the side the safety lever runs down, -Y = the side the pull
ring hangs on. The origin is the body centre (sphere centre, or the middle of the can or tube).
Export frame (metres, glTF Y up): X = X, Y = Z, Z = -Y, so the lever is on +X and the pull ring on +Z.

Every number in P names its source: FM = FM 3-23.30 (2009) table or figure, PX = measured in the named figure crop
(notes/DECOMPOSITION.md gives the pixel landmarks and the ruler), PUB = a named public figure, INF = inferred,
GAME = game-only. See notes/NOTES.md for the full ledger.
"""
import bpy, bmesh, math, json, os, sys, time
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d): return ARGV[ARGV.index(k) + 1] if k in ARGV else d
ONLY = [s for s in arg('--only', '').split(',') if s]
LODS = [int(arg('--lod', 0))] if '--lod' in ARGV else [0, 1]
M18_LIVERY = arg('--m18-livery', 'table')
FLASH_HOLES = int(arg('--flash-holes', 18))
MM = 0.001
LOD = 0
IN = 25.4

# ------------------------------------------------------------------ shape numbers
P = dict(
    # ---- frag (Fig. A-2, ruler: sphere diameter 570 px = 63.5 mm -> 0.1114 mm/px)
    frag_d=2.5 * IN,            # PUB: body diameter 2.5 in (not in Table A-1); the limb fits a circle of R = 285 px
    frag_len=84.5,              # PX: plate 210 px above the collar at 20 deg elevation. PUB gives 3.53 in (89.7 mm): NOTES.md
    frag_flat_r=11.0,           # PX: flat base, the limb leaves the fitted circle 18 px above its lowest point
    frag_collar_r=10.6,         # PX: bright collar ring, 190 px wide
    frag_collar_h=2.4,          # PX: ~20 px band
    frag_cone_r0=10.2, frag_cone_r1=9.2,     # PX: fuze tower 180 px wide at the collar; right edge leans in ~10 px over 110 px
    frag_head=(-14.6, 17.9),    # PX: lever top plate, hinge end to bend, after removing the 8 deg lean and 8 % perspective
    frag_lever_w=24.0,          # PX: plate depth 85 px seen at 20 deg elevation, less perspective. +/- 4 mm
    frag_lever_tip_w=15.0,      # INF: the spoon's taper is not resolved in the photo
    frag_lever_t=1.2,           # INF: sheet thickness
    frag_lever_end_lat=-22.0,   # PX: spoon tip 29 deg below the centre in the picture, less the 8 deg lean, over cos(20 deg)
    frag_ear=(5.0, 17.9, 22.5), # PX: lever ear, x from, x to, drop below the plate (bottom edge level with the collar)
    frag_pin=(13.0, -12.0),     # INF: pin axis (x, z below the plate); only its end loop is visible in the photo
    frag_clip=(22.0, 36.0, 26.0, 31.5),      # PX: safety clip loop x from, x to; INF depth in Y; PX height above the centre
    frag_text_lat=(2.0, -15.0), # PX: marking lines, latitude after removing the 20 deg camera elevation
    frag_text_h=(6.0, 5.0),     # PX: 55 px and 45 px cap heights
    # ---- shared pull ring and pin (Figs. B-3 and A-12)
    ring_d=29.5,                # PX: 29.4 mm in Fig. B-3 (green can); used for frag too, whose ring Fig. A-2 hides
    flash_ring_d=30.5,          # PX: 134 px in Fig. A-12
    ring_wire=1.0,              # PX/INF: two turns of ~2 mm wire read as one 4 mm band at this resolution
    pin_r=1.1,                  # INF
    # ---- flash (Fig. A-12, ruler: overall 585 px = 5.25 in -> 0.228 mm/px)
    flash_len=5.25 * IN,        # FM Table A-5. The photo's proportions put the fuze inside this length (NOTES.md)
    flash_hex_ac=1.73 * IN,     # FM Table A-5: across the corners of the hexagon
    flash_bot_h=23.3,           # PX: 102 px
    flash_bot_chamfer=4.5,      # PX: 20 px shoulder
    flash_top_h=14.8,           # PX: 65 px
    flash_tube_d=32.3,          # PX: 142 px. Round between the hexagons (see NOTES.md on "hexagon tube")
    flash_tube_wall=3.0,        # INF
    flash_core_r=8.0,           # placeholder solid, INF radius (must clear the sight lines through the side holes)
    flash_hole_d=11.5,          # PX: 52 x 48 px
    flash_hole_z=(33.1, 52.9, 73.0),         # PX: rows at y = 462, 375, 287 -> height above the base
    flash_fuze_h=25.8,          # PX: 113 px
    flash_lever_x=(20.5, 31.0, 32.5, 28.6),  # PX: lever stand-off from the axis at the four path heights below
    flash_lever_z=(129.0, 111.0, 97.0, 34.7),
    flash_lever_hook=8.0,       # PX: tip turned in 36 px
    # ---- smoke cans (Figs. B-3 and B-5)
    can_d=2.5 * IN,             # FM Table B-3 gives 2.5 in for the M83, the same can family; INF that M18 and AN-M8 match
    can_h=117.5,                # PX: green can, 493 px between rim centres at 9 deg elevation (the four photos give 116..132)
    can_rim=(0.5, 2.4),         # INF: rolled seam stand-out and height (visible, not measurable)
    can_fuze_h=25.0,            # PX: 115 px above the can top in the green photo, less the elevation's lift of the far rim
    can_band=(27.6, 40.3),      # PX: light band, height above the base, corrected for the 9 deg elevation (M18 only)
    can_text_z=(24.0, 39.6, 59.1),           # PX: three marking lines, depth below the can top, same correction
    can_text_h=(13.0, 13.0, 14.0),           # PX: 55, 55 and ~60 px
    can_lot_z=103.4,            # PX: lot line below the band (replaced by a plain bar)
    # the fuze screws in, so each photographed unit has its markings at a different angle to the lever (deg from the ring side)
    can_mark_az=dict(violet=-6.0, yellow=17.0, green=-36.0, red=-26.0, white=131.0),   # PX: text centre and lever offsets
    # pull-ring rest pose (hang direction, plane normal). A free-hanging part: one pose per figure
    ring_pose=dict(frag=((0.0, -0.35, -0.94), (0.3, -0.9, 0.3)),             # INF: hidden in Fig. A-2
                   flash=((0.35, -0.10, -0.93), (0.0, -1.0, 0.0)),            # PX Fig. A-12
                   smoke=((0.57, -0.48, -0.66), (-0.64, -0.77, 0.0)),         # PX Fig. B-3 green can
                   white=((0.30, -0.90, 0.30), (0.95, 0.30, 0.0))),           # PX Fig. B-5: ring standing out sideways
    can_lever_drop=74.0,        # PX: lever tip 72.6 (violet), 74 (yellow), 78 mm (Fig. B-5) below the can top
    can_lever_w=16.0,           # PX: 11 mm (Fig. B-5) to 26 mm (yellow can) depending on the angle assumed; +/- 6 mm
    can_dome_h=3.0,             # PX: green can, the fuze seat sits above where a flat lid would put it; +/- 2 mm
    can_hole_r=(20.0, 4.5),     # INF: the four top emission holes (FM Table B-2) are not visible in any figure
    fuze_block=(25.0, 20.0),    # PX width (109 px in Fig. A-12); INF depth in Y
)

# ------------------------------------------------------------------ variants
SMOKE = dict(red=(0.60, 0.03, 0.03), yellow=(0.80, 0.62, 0.04), green=(0.07, 0.36, 0.10), violet=(0.30, 0.08, 0.45))
VARIANTS = ['frag', 'impact', 'flash'] + [f'smoke-{c}' for c in SMOKE] + ['smoke-white']

# name: base colour (linear), metallic, roughness
MAT = dict(
    PaintOliveDrab=((0.070, 0.078, 0.040), 0.0, 0.62),      # FM Table A-1 "olive drab"; hue not measurable (greyscale figure)
    PaintFuze=((0.150, 0.165, 0.115), 0.0, 0.60),           # lighter than the body in Fig. A-2; hue INF
    PaintLightGreen=((0.330, 0.450, 0.300), 0.0, 0.60),     # FM Tables B-2 and B-4 "light green"
    PaintDarkGreen=((0.060, 0.075, 0.045), 0.0, 0.62),      # Fig. B-3 tone (figure livery)
    PaintFlashBody=((0.030, 0.034, 0.024), 0.0, 0.55),      # FM Table A-5 "olive drab"; Fig. A-12 reads near black
    MarkYellow=((0.800, 0.640, 0.060), 0.0, 0.60),          # FM Table A-1 "yellow markings"
    MarkBlack=((0.012, 0.012, 0.012), 0.0, 0.60),
    MarkLight=((0.700, 0.760, 0.660), 0.0, 0.60),           # Fig. B-3 light marks; FM Table A-5 "white markings"
    LabelPanel=((0.160, 0.170, 0.150), 0.0, 0.50),         # Fig. A-12: a dark label with small light print, replaced by a plain panel
    Tape=((0.780, 0.770, 0.720), 0.0, 0.70),                # Fig. B-3 light band, hue unknown
    Steel=((0.420, 0.420, 0.430), 0.9, 0.38),
    Wire=((0.300, 0.300, 0.310), 0.9, 0.45),
    LeverTipBrown=((0.170, 0.085, 0.035), 0.0, 0.60),       # FM Table A-5 "brown band on the tip end of the safety lever"
    Cavity=((0.004, 0.004, 0.004), 0.0, 0.90),
    Placeholder=((0.020, 0.020, 0.020), 0.0, 0.90),
    TopWhite=((0.820, 0.820, 0.790), 0.0, 0.60),            # FM Table B-4 "white top"
    BandImpact=((0.800, 0.020, 0.450), 0.0, 0.55),          # GAME: magenta, chosen because no real colour code uses it
    **{f'Top{c.capitalize()}': (rgb, 0.0, 0.60) for c, rgb in SMOKE.items()},
)

OBJ, W, CLIPS, MATS, SOCK = {}, {}, {}, {}, {}

def SEG(n): return n if LOD == 0 else max(8, n // 2 // 2 * 2)

# ------------------------------------------------------------------ mesh kit (mm, Blender axes)
def lathe(prof, n=48):
    """Revolve a profile [(r, z), ...] about Z. Points with r == 0 become poles."""
    bm = bmesh.new(); n = SEG(n); rings = []
    for r, z in prof:
        if r <= 1e-9: rings.append([bm.verts.new((0, 0, z))])
        else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z)) for i in range(n)])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1 and len(b) == 1: continue
            if len(a) == 1: bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1: bm.faces.new((a[i], b[0], a[j]))
            else: bm.faces.new((a[i], b[i], b[j], a[j]))
    for ring, flip in ((rings[0], True), (rings[-1], False)):
        if len(ring) > 1: bm.faces.new(ring[::-1] if flip else ring)
    return bm

def _basis(d):
    d = Vector(d).normalized(); a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized(); return d, u, d.cross(u)

def cyl(p0, p1, r, n=24, r1=None):
    bm = bmesh.new(); n = SEG(n); p0, p1 = Vector(p0), Vector(p1); d, u, v = _basis(p1 - p0); r1 = r if r1 is None else r1
    a = [bm.verts.new(p0 + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * r) for i in range(n)]
    b = [bm.verts.new(p1 + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * r1) for i in range(n)]
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    return bm

def box(x0, x1, y0, y1, z0, z1):
    bm = bmesh.new()
    v = [bm.verts.new((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): bm.faces.new([v[i] for i in f])
    return bm

def loft(stations):
    """stations: [(z, [(x, y), ...]), ...] with equal vertex counts; capped at both ends."""
    bm = bmesh.new(); rings = [[bm.verts.new((x, y, z)) for x, y in poly] for z, poly in stations]; n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return bm

def hexagon(ac, rot=0.0, scale=1.0):
    """Regular hexagon, across corners ac; rot = 0 puts a corner on -Y (towards the camera of Fig. A-12)."""
    return [(scale * ac / 2 * math.sin(math.radians(rot + 60 * i)), -scale * ac / 2 * math.cos(math.radians(rot + 60 * i))) for i in range(6)]

def fillet(pts, rad, n=5):
    """Round the interior corners of an open 2D polyline. rad: one radius or one per interior point."""
    out = [Vector(pts[0])]
    for k in range(1, len(pts) - 1):
        r = rad[k - 1] if isinstance(rad, (list, tuple)) else rad
        p0, p1, p2 = Vector(pts[k - 1]), Vector(pts[k]), Vector(pts[k + 1]); a, b = (p0 - p1), (p2 - p1)
        ang = a.angle(b)
        if r <= 0 or ang > math.pi - 1e-3: out.append(p1); continue
        t = min(r / math.tan(ang / 2), a.length * 0.45, b.length * 0.45)
        q0, q1 = p1 + a.normalized() * t, p1 + b.normalized() * t
        for i in range(n + 1):
            s = i / n; out.append((1 - s) ** 2 * q0 + 2 * s * (1 - s) * p1 + s * s * q1)
    out.append(Vector(pts[-1])); return out

def strip(path, widths, t):
    """Sheet-metal strip: path [(x, z)] is the outer face in the XZ plane, width along Y, thickness t to the left of travel."""
    bm = bmesh.new(); rows = []; n = len(path)
    for k in range(n):
        p = Vector(path[k]); d = (Vector(path[min(k + 1, n - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
        nrm = Vector((-d.y, d.x)); q = p + nrm * t; w = widths[k] / 2 if isinstance(widths, (list, tuple)) else widths / 2
        rows.append([bm.verts.new((p.x, -w, p.y)), bm.verts.new((p.x, w, p.y)), bm.verts.new((q.x, w, q.y)), bm.verts.new((q.x, -w, q.y))])
    for a, b in zip(rows, rows[1:]):
        for i in range(4): bm.faces.new((a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]))
    bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1])
    return bm

def wire(path, r, n=8, closed=False):
    """Round wire along a 3D polyline (parallel-transport frames)."""
    bm = bmesh.new(); n = SEG(n) if n > 8 else n; pts = [Vector(p) for p in path]; m = len(pts); rings = []
    d0 = ((pts[1] - pts[0]) if not closed else (pts[1] - pts[-1])).normalized(); _, u, _v = _basis(d0)
    for k in range(m):
        a = pts[k - 1] if (k > 0 or closed) else pts[k]; b = pts[(k + 1) % m] if (k < m - 1 or closed) else pts[k]
        d = (b - a).normalized(); u = (u - d * u.dot(d)).normalized(); v = d.cross(u)
        rings.append([bm.verts.new(pts[k] + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * r) for i in range(n)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if not closed: bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return bm

def circle3(c, r, normal, n=40, a0=0.0, a1=360.0):
    d, u, v = _basis(normal); k = max(3, int(SEG(n) * abs(a1 - a0) / 360))
    full = abs(a1 - a0) >= 360
    return [Vector(c) + (u * math.cos(math.radians(a0 + (a1 - a0) * i / k)) + v * math.sin(math.radians(a0 + (a1 - a0) * i / k))) * r for i in range(k if full else k + 1)]

def join(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new('tmp'); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out

def _apply(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = o.data; o.modifiers.clear(); o.data = me; bpy.data.meshes.remove(old); me.name = o.name

def finish(name, bm, mat, parent, pivot=(0, 0, 0), bevel=0.3, cuts=(), sharp=35, smooth=True):
    """bmesh (mm) -> named object in metres, origin at pivot (the hinge or slide axis of a moving part)."""
    assert name not in OBJ, name
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    wp = Vector(pivot) * MM
    for v in bm.verts: v.co = v.co * MM - wp
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = wp
    for c in cuts:
        for v in c.verts: v.co = v.co * MM
        cm = bpy.data.meshes.new('cutter'); c.to_mesh(cm); c.free(); co = bpy.data.objects.new('cutter', cm); bpy.context.scene.collection.objects.link(co)
        m = o.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.object = co
        _apply(o); bpy.data.objects.remove(co); bpy.data.meshes.remove(cm)
    me = o.data
    for p in me.polygons: p.use_smooth = smooth
    if smooth: me.set_sharp_from_angle(angle=math.radians(sharp))
    if bevel and LOD == 0:
        b = o.modifiers.new('bevel', 'BEVEL'); b.limit_method = 'ANGLE'; b.angle_limit = math.radians(sharp); b.width = bevel * MM; b.segments = 2
    if smooth: wn = o.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True
    me.materials.clear(); me.materials.append(MATS[mat])
    par = OBJ[parent]; o.parent = par; o.location = wp - W[parent]
    OBJ[name] = o; W[name] = wp
    return o

def empty(name, parent, p=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.01
    bpy.context.scene.collection.objects.link(e); wp = Vector(p) * MM
    if parent: e.parent = OBJ[parent]; e.location = wp - W[parent]
    OBJ[name] = e; W[name] = wp
    return e

def socket(name, parent, p):
    empty(name, parent, p); SOCK[name] = [round(c, 3) for c in p]

# ------------------------------------------------------------------ markings: placeholder words and plain bars
def text_mesh(s, cap):
    """Flat outline text, centred on (0, 0), cap height `cap` mm. Returns [(verts2d, faces)]."""
    cu = bpy.data.curves.new('t', 'FONT'); cu.body = s; cu.align_x = 'CENTER'; cu.size = 1.0; cu.resolution_u = 2 if LOD else 3
    o = bpy.data.objects.new('t', cu); bpy.context.scene.collection.objects.link(o)
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces)
    ys = [v.co.y for v in bm.verts]; k = cap / (max(ys) - min(ys)); y0 = (max(ys) + min(ys)) / 2
    long_edges = [e for e in bm.edges if e.calc_length() * k > 3.0]
    if long_edges: bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=2, use_grid_fill=True); bmesh.ops.triangulate(bm, faces=bm.faces)
    for v in bm.verts: v.co = Vector((v.co.x * k, (v.co.y - y0) * k, 0))
    bpy.data.objects.remove(o); bpy.data.curves.remove(cu); bpy.data.meshes.remove(me)
    return bm

def bar_mesh(w, h, nx=24):
    bm = bmesh.new(); top = [bm.verts.new((-w / 2 + w * i / nx, h / 2, 0)) for i in range(nx + 1)]; bot = [bm.verts.new((-w / 2 + w * i / nx, -h / 2, 0)) for i in range(nx + 1)]
    for i in range(nx): bm.faces.new((bot[i], bot[i + 1], top[i + 1], top[i]))
    return bm

def wrap_cyl(bm, R, az, z, lift=0.35):
    """Wrap a flat mark (u along the surface, v up) on a cylinder of radius R; az = 0 faces -Y, positive towards +X."""
    for v in bm.verts:
        a = math.radians(az) + v.co.x / R
        v.co = Vector(((R + lift) * math.sin(a), -(R + lift) * math.cos(a), z + v.co.y))
    return bm

def wrap_sphere(bm, R, az, lat, slant=0.0, lift=0.35):
    """Wrap a flat mark on a sphere at latitude lat (deg); az = 0 faces -Y. slant rotates the line in the surface."""
    cs, sn = math.cos(math.radians(slant)), math.sin(math.radians(slant))
    for v in bm.verts:
        u, w = v.co.x * cs - v.co.y * sn, v.co.x * sn + v.co.y * cs
        la = math.radians(lat) + w / R; a = math.radians(az) + u / (R * math.cos(math.radians(lat)))
        v.co = Vector(((R + lift) * math.cos(la) * math.sin(a), -(R + lift) * math.cos(la) * math.cos(a), (R + lift) * math.sin(la)))
    return bm

def mark(name, bm, mat, parent):
    return finish(name, bm, mat, parent, bevel=0, smooth=False)

# ------------------------------------------------------------------ pull ring, pin
def build_pin(parent, eye, y_tail, pose, ring_d=None):
    """Safety pin along Y with its eye at `eye` (on the -Y side) and the pull ring hanging from the eye.
    The pin slides out along -Y; the ring swings about the eye. pose = (hang direction, ring plane normal)."""
    ex, ey, ez = eye; r = P['pin_r']
    shaft = cyl((ex, ey, ez), (ex, y_tail, ez), r, 10)
    eye_loop = wire(circle3((ex, ey - 2.6, ez), 2.6, (1, 0, 0), 16), r * 0.9, 6, closed=True)
    tail = join(wire([(ex, y_tail, ez), (ex + 1.6, y_tail + 3.0, ez + 0.8)], r * 0.7, 6), wire([(ex, y_tail, ez), (ex - 1.6, y_tail + 3.0, ez - 0.8)], r * 0.7, 6))
    finish('safety_pin', join(shaft, eye_loop, tail), 'Wire', parent, pivot=(ex, ey, ez), bevel=0)
    R = (ring_d or P['ring_d']) / 2; d = Vector(pose[0]).normalized(); nrm = Vector(pose[1]); nrm = (nrm - d * nrm.dot(d)).normalized()
    top = Vector((ex, ey - 4.2, ez)); c = top + d * (R - 1.0)
    bm = join(wire(circle3(c, R - P['ring_wire'], nrm, 44), P['ring_wire'], 8, closed=True),
              wire(circle3(c + nrm * 2.0 * P['ring_wire'], R - P['ring_wire'], nrm, 44), P['ring_wire'], 8, closed=True))
    finish('pull_ring', bm, 'Wire', 'safety_pin', pivot=tuple(top), bevel=0)
    socket('socket_pin_ring', 'pull_ring', tuple(c))
    return c

# ------------------------------------------------------------------ frag fuze (Fig. A-2) and body
def build_frag(impact=False):
    R = P['frag_d'] / 2; zf = -math.sqrt(R * R - P['frag_flat_r'] ** 2); ztop = zf + P['frag_len']
    cr = P['frag_collar_r']; zc = math.sqrt(R * R - cr * cr) - 0.6
    n = 28; prof = [(0, zf), (P['frag_flat_r'], zf)]
    a0 = math.asin(zf / R); a1 = math.asin((zc + 0.4) / R)
    prof += [(R * math.cos(a0 + (a1 - a0) * i / n), R * math.sin(a0 + (a1 - a0) * i / n)) for i in range(1, n + 1)]
    prof += [(cr - 1.0, zc + 0.8), (0, zc + 0.8)]
    finish('body', lathe(prof, 64), 'PaintOliveDrab', 'body_group', bevel=0, sharp=50)
    # collar ring (bright steel in the photo)
    h = P['frag_collar_h']
    finish('neck_collar', lathe([(cr - 2.5, zc), (cr, zc), (cr + 0.3, zc + h / 2), (cr, zc + h), (cr - 2.5, zc + h)], 40), 'Steel', 'fuze', bevel=0.2)
    # fuze tower and head under the lever
    x0, x1 = P['frag_head']; w = P['frag_lever_w']; t = P['frag_lever_t']; zp = ztop - t           # underside of the lever plate
    zh = zp - 3.0
    tower = lathe([(P['frag_cone_r0'], zc + h), (P['frag_cone_r1'], zh), (P['frag_cone_r1'] - 0.8, zh + 0.8), (0, zh + 0.8)], 36)
    head = box(x0 + 3.0, x1 - 3.5, -w / 2 + 2.2, w / 2 - 2.2, zp - 6.0, zp - 0.3)
    finish('fuze_body', join(tower, head), 'PaintFuze', 'fuze', bevel=0.6)
    # hinge lug on the -X side: a cross pin the lever hooks under
    hx, hz = x0 + 1.5, zp - 4.5
    finish('hinge_lug', join(cyl((hx, -w / 2 - 1.5, hz), (hx, w / 2 + 1.5, hz), 2.3, 16), box(hx, x0 + 6.0, -5.0, 5.0, hz - 3.0, hz + 3.0)), 'PaintFuze', 'fuze', bevel=0.25)
    # safety lever: curls under the hinge pin, covers the top, bends down the +X side and follows the sphere
    lat1 = P['frag_lever_end_lat']; Rs = R + 1.6 + t
    path = [(hx + 2.4, hz - 3.6), (hx - 3.6, hz - 3.0), (hx - 3.9, hz + 2.0), (hx - 1.0, ztop), (x1, ztop), (x1 + 6.5, zc + h + 1.0)]
    a_top = math.degrees(math.atan2(zc + h - 6.0, x1 + 8.0))
    m = 18; arc = [(Rs * math.cos(math.radians(a_top + (lat1 - a_top) * i / m)), Rs * math.sin(math.radians(a_top + (lat1 - a_top) * i / m))) for i in range(m + 1)]
    tipd = math.radians(lat1); arc.append((arc[-1][0] + 1.2 * math.cos(tipd) + 1.6 * math.sin(tipd), arc[-1][1] + 1.2 * math.sin(tipd) - 1.6 * math.cos(tipd)))
    pts = fillet(path + arc, [1.8, 2.0, 2.2, 3.0, 5.0] + [0] * (len(arc) - 1), 5)
    k_bend = next(i for i, p in enumerate(pts) if p.x >= x1 - 1e-6 and p.y < ztop - 2.0)
    wt = P['frag_lever_tip_w']; widths = [w if i <= k_bend else w + (wt - w) * min(1.0, (i - k_bend) / max(1, len(pts) - 1 - k_bend) * 1.6) for i in range(len(pts))]
    lever = strip([(p.x, p.y) for p in pts], widths, -t)
    e0, e1, ed = P['frag_ear']
    ears = []
    for sy in (-1, 1):
        y = sy * (w / 2 - t / 2)
        ears.append(_ear(e0, e1, ztop - 0.2, ed, y, t))
    finish('lever', join(lever, *ears), 'PaintFuze', 'fuze', pivot=(hx, 0, hz), bevel=0.15, sharp=30)
    socket('socket_lever_hinge', 'fuze', (hx, 0, hz))
    socket('socket_thumb', 'lever', (Rs + 0.5, 0, 6.0))
    # safety pin through the ears; the ring is hidden in Fig. A-2 (it hangs on the far side), so its pose is inferred
    px, pdz = P['frag_pin']; pz = ztop + pdz
    build_pin('fuze', (px, -w / 2 - 1.2, pz), w / 2 + 1.5, P['ring_pose']['frag'])
    # safety clip (Fig. A-2: a wire loop round the lever, an arm up to the pin tail on the +Y ear)
    c0, c1, cd, cz = P['frag_clip']; rw = 0.9
    loop = fillet([(c0, 4.0), (c0, cd / 2), (c1, cd / 2), (c1, -cd / 2), (c0, -cd / 2), (c0, 4.0)], 3.0, 4)
    loop3 = [(p.x, p.y, cz + 0.05 * (p.x - c0)) for p in loop][:-1]
    arm = [(c0, cd / 2 - 3.0, cz), (c0 - 3.0, w / 2 + 2.2, cz + 5.0), (px + 1.0, w / 2 + 2.4, pz - 2.4)]
    eye = circle3((px, w / 2 + 2.4, pz), 2.4, (0, 1, 0), 14)
    finish('safety_clip', join(wire(loop3, rw, 6, closed=True), wire(arm, rw, 6), wire(eye, rw, 6, closed=True)), 'Wire', 'fuze', pivot=(px, w / 2 + 2.4, pz), bevel=0)
    # markings on the +Y side (the side Fig. A-2 shows): a placeholder word and plain bars, no designation or lot number
    la, lb = P['frag_text_lat']; ha, hb = P['frag_text_h']; mk = 'MarkYellow'
    word = 'IMPACT' if impact else 'FRAG'
    tm = text_mesh(word, ha); wd = max(v.co.x for v in tm.verts) * 2
    for v in tm.verts: v.co.x += 12.0
    mark('marking_word', wrap_sphere(tm, R, 180, la), mk, 'body')
    bar = bar_mesh(20.0, ha * 0.8, 10)
    for v in bar.verts: v.co.x -= wd / 2 + 2.0
    mark('marking_bar_designation', wrap_sphere(bar, R, 180, la), mk, 'body')
    mark('marking_bar_lot', wrap_sphere(bar_mesh(40.0, hb * 0.8, 20), R, 180, lb), mk, 'body')
    if impact:   # GAME: a paint band round the body, above the equator so the word stays readable
        b0, b1 = math.radians(22), math.radians(34)
        finish('band_impact', lathe([((R + 0.25) * math.cos(b0 + (b1 - b0) * i / 6), (R + 0.25) * math.sin(b0 + (b1 - b0) * i / 6)) for i in range(7)], 64), 'BandImpact', 'body', bevel=0)
    socket('socket_grip', 'body_group', (0, 0, 0)); socket('socket_effect', 'body_group', (0, 0, 0))
    return dict(length=P['frag_len'], width=P['frag_d'], base_z=zf, top_z=ztop)

def _ear(x0, x1, ztop, drop, y, t):
    """Lever ear: a flat plate in the XZ plane hanging from the top plate (trapezoid, narrower at the bottom)."""
    poly = [(x0 - 5.0, ztop), (x1, ztop), (x1 + 3.5, ztop - drop * 0.55), (x1 + 2.0, ztop - drop), (x0 + 2.0, ztop - drop)]
    bm = bmesh.new(); a = [bm.verts.new((x, y - t / 2, z)) for x, z in poly]; b = [bm.verts.new((x, y + t / 2, z)) for x, z in poly]; n = len(poly)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    return bm

# ------------------------------------------------------------------ block fuze shared by flash and smoke (Figs. A-12, B-3, B-5)
def build_block_fuze(z0, h, lever_pts, lever_w, pose, tip_mat=None, ring_d=None, flange_r=11.5):
    """z0: seat height, h: fuze height. lever_pts: [(x, z)] from the bend at the top down to the tip."""
    bw, bd = P['fuze_block']; t = 1.2; ztop = z0 + h; zp = ztop - t
    parts = []
    parts.append(lathe([(flange_r, z0 - 0.5), (flange_r, z0 + 4.0), (0, z0 + 4.0)], 32))                 # round seat / neck
    parts.append(box(-bw / 2, bw / 2, -bd / 2, bd / 2, z0 + 3.5, zp - 0.3))                              # the block, up to the lever plate
    finish('fuze_body', join(*parts), 'PaintOliveDrab', 'fuze', bevel=0.7)
    hx, hz = -bw / 2 + 0.5, zp - 5.0
    finish('hinge_lug', join(cyl((hx, -bd / 2 - 2.0, hz), (hx, bd / 2 + 2.0, hz), 2.2, 16), box(hx, hx + 4.0, -4.5, 4.5, hz - 2.8, hz + 2.8)), 'PaintOliveDrab', 'fuze', bevel=0.25)
    wtop = bd + 3.0
    path = [(hx + 2.3, hz - 3.4), (hx - 3.4, hz - 2.8), (hx - 3.7, hz + 2.0), (hx - 0.8, ztop), (bw / 2 - 1.0, ztop)] + list(lever_pts)
    pts = fillet(path, [1.8, 2.0, 2.2, 3.5] + [6.0] * (len(lever_pts) - 1), 5)
    k_bend = next(i for i, p in enumerate(pts) if p.x >= bw / 2 - 1.0 - 1e-6)
    widths = [wtop if i <= k_bend else max(lever_w, wtop - (wtop - lever_w) * (i - k_bend) / 8.0) for i in range(len(pts))]
    lever = strip([(p.x, p.y) for p in pts], widths, -t)
    side = []
    for sy in (-1, 1):   # short skirts either side of the head, the pin passes through them
        side.append(_ear(1.0, bw / 2 - 1.5, ztop - 0.2, h * 0.42, sy * (wtop / 2 - t / 2), t))
    finish('lever', join(lever, *side), 'PaintOliveDrab', 'fuze', pivot=(hx, 0, hz), bevel=0.15, sharp=30)
    if tip_mat:
        tail = [p for p in pts if p.y <= lever_pts[-2][1] + 14.0][-12:]
        finish('lever_tip_band', strip([(p.x + 0.12, p.y) for p in tail], lever_w + 0.3, -(t + 0.24)), tip_mat, 'lever', bevel=0)
    socket('socket_lever_hinge', 'fuze', (hx, 0, hz))
    mid = lever_pts[len(lever_pts) // 2]; socket('socket_thumb', 'lever', (mid[0] + 0.5, 0, (lever_pts[1][1] + lever_pts[-2][1]) / 2))
    eye = (bw / 2 - 5.5, -wtop / 2 - 1.2, zp - h * 0.46)
    build_pin('fuze', eye, wtop / 2 + 1.5, pose, ring_d)
    return ztop

# ------------------------------------------------------------------ flash (Fig. A-12, Table A-5)
def build_flash():
    L = P['flash_len']; fh = P['flash_fuze_h']; bh = P['flash_bot_h']; ch = P['flash_bot_chamfer']; th = P['flash_top_h']
    body_h = L - fh; zb = -body_h / 2; ac = P['flash_hex_ac']; rt = P['flash_tube_d'] / 2
    z_t0 = zb + body_h - th                                               # underside of the top hexagon
    k = (rt * 2 + 3.0) / ac
    finish('hex_base', loft([(zb, hexagon(ac, 0, 0.97)), (zb + 1.2, hexagon(ac)), (zb + bh - ch, hexagon(ac)), (zb + bh, hexagon(ac, 0, k))]), 'PaintFlashBody', 'body_group', bevel=0.5, smooth=False)
    finish('hex_top', loft([(z_t0, hexagon(ac, 0, k)), (z_t0 + 2.5, hexagon(ac)), (zb + body_h - 1.2, hexagon(ac)), (zb + body_h, hexagon(ac, 0, 0.96))]), 'PaintFlashBody', 'body_group', bevel=0.5, smooth=False)
    # perforated tube; Fig. A-12 shows three rows on each of the three visible columns, 60 deg apart
    rows = P['flash_hole_z'] if FLASH_HOLES == 18 else (P['flash_hole_z'][0] + 10.0, P['flash_hole_z'][2] - 10.0)
    tube = lathe([(rt, zb + bh - 0.5), (rt, z_t0 + 0.5), (rt - P['flash_tube_wall'], z_t0 + 0.5), (rt - P['flash_tube_wall'], zb + bh - 0.5)], 48)
    cuts = []
    for c in range(6):
        a = math.radians(60 * c)
        for z in rows:
            ri = rt - P['flash_tube_wall'] - 1.5; cuts.append(cyl((ri * math.sin(a), -ri * math.cos(a), zb + z), ((rt + 2) * math.sin(a), -(rt + 2) * math.cos(a), zb + z), P['flash_hole_d'] / 2, 24 if LOD == 0 else 12))
    finish('tube', tube, 'PaintFlashBody', 'body_group', bevel=0.25, cuts=[join(*cuts)])
    finish('core_placeholder', cyl((0, 0, zb + bh - 0.5), (0, 0, z_t0 + 0.5), P['flash_core_r'], 20), 'Placeholder', 'body_group', bevel=0)
    # maker's label panels on the top hexagon: plain placeholder panels on the two faces towards -Y
    af = ac / 2 * math.cos(math.radians(30))
    for i, az in enumerate((-30, 30)):
        a = math.radians(az); n = Vector((math.sin(a), -math.cos(a), 0)); tng = Vector((math.cos(a), math.sin(a), 0)); c = n * (af + 0.15) + Vector((0, 0, z_t0 + th / 2 + 0.4))
        bm = bmesh.new(); q = [bm.verts.new(c + tng * sx * 8.0 + Vector((0, 0, sz * 4.2))) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]; bm.faces.new(q)
        mark(f'label_panel_{i + 1}', bm, 'LabelPanel', 'hex_top')
    z0 = zb + body_h
    lx, lz = P['flash_lever_x'], [zb + z for z in P['flash_lever_z']]       # heights above the base -> about the centre
    pts = [(lx[0], lz[0]), (lx[1], lz[1]), (lx[2], lz[2]), (lx[3], lz[3]), (lx[3] - P['flash_lever_hook'], lz[3] - 2.0)]
    ztop = build_block_fuze(z0, fh, pts, 14.0, P['ring_pose']['flash'], tip_mat='LeverTipBrown', ring_d=P['flash_ring_d'], flange_r=13.5)
    socket('socket_grip', 'body_group', (0, 0, 0)); socket('socket_effect', 'body_group', (0, 0, 0))
    return dict(length=L, width=ac, base_z=zb, top_z=ztop, holes=6 * len(rows))

# ------------------------------------------------------------------ smoke cans (Figs. B-3, B-5; Tables B-2, B-4)
def build_smoke(colour):
    white = colour == 'white'; R = P['can_d'] / 2; H = P['can_h']; zb = -H / 2; zt = H / 2; ro, rh = P['can_rim']
    figure = (M18_LIVERY == 'figure') and not white
    body_mat = 'PaintDarkGreen' if figure else 'PaintLightGreen'; mk = 'MarkLight' if figure else 'MarkBlack'
    prof = [(0, zb + 1.5), (R - 1.5, zb + 1.5), (R - 1.5, zb), (R + ro, zb), (R + ro, zb + rh), (R, zb + rh + 0.6), (R, zt - rh - 0.6), (R + ro, zt - rh), (R + ro, zt), (R - 1.5, zt), (R - 1.5, zt - 1.8)]
    finish('body', lathe(prof + [(0, zt - 1.8)], 64), body_mat, 'body_group', bevel=0.25, sharp=40)
    dh = P['can_dome_h']; zs = zt - 1.3 + dh                                  # fuze seat on the low dome of the lid
    finish('top_cover', lathe([(0, zt - 1.8), (R - 1.6, zt - 1.8), (R - 1.6, zt - 1.3), (14.0, zs), (0, zs)], 64), 'TopWhite' if white else f'Top{colour.capitalize()}', 'body', bevel=0)
    hr, hd = P['can_hole_r']
    for i in range(4):   # FM Table B-2: four emission holes at the top. Not visible in the figures: position and size inferred
        a = math.radians(45 + 90 * i); c = (hr * math.cos(a), hr * math.sin(a))
        zh = zt - 1.3 + dh * (R - 1.6 - hr) / (R - 1.6 - 14.0)
        finish(f'emission_hole_{i + 1}', cyl((c[0], c[1], zh - 1.5), (c[0], c[1], zh + 0.75), hd, 16), 'Cavity', 'top_cover', bevel=0)
        socket(f'socket_emit_{i + 1}', 'body_group', (c[0], c[1], zh + 0.8))
    if not white:
        b0, b1 = P['can_band']
        finish('band_tape', lathe([(R + 0.2, zb + b0), (R + 0.2, zb + b1)], 64), 'Tape', 'body', bevel=0)
    words = ['SMOKE', 'WHITE' if white else colour.upper()]; maz = P['can_mark_az'][colour]
    tz, thh = P['can_text_z'], P['can_text_h']
    mark('marking_bar_designation', wrap_cyl(bar_mesh(26.0, thh[0] * 0.8, 14), R, maz, zt - tz[0]), mk, 'body')
    for i, wd in enumerate(words):
        mark(f'marking_word_{i + 1}', wrap_cyl(text_mesh(wd, thh[i + 1]), R, maz, zt - tz[i + 1]), mk, 'body')
    if not white:
        mark('marking_bar_lot', wrap_cyl(bar_mesh(46.0, 6.0, 24), R, maz, zt - P['can_lot_z']), mk, 'body')
    zl = zt - P['can_lever_drop']
    fz = P['can_fuze_h'] - (zs - zt)                                           # the fuze stands on the dome; its top stays can_fuze_h above the rim
    pts = [(P['fuze_block'][0] / 2 + 5.0, zt + P['can_fuze_h'] - 5.0), (R + 2.2, zt + 1.0), (R + 2.0, (zt + zl) / 2), (R + 2.6, zl + 3.0), (R + 4.2, zl)]
    ztop = build_block_fuze(zs, fz, pts, P['can_lever_w'], P['ring_pose']['white' if white else 'smoke'])
    socket('socket_grip', 'body_group', (0, 0, 0)); socket('socket_effect', 'body_group', (0, 0, zt))
    return dict(length=H + P['can_fuze_h'], width=P['can_d'], base_z=zb, top_z=ztop, livery='figure' if figure else 'table')

# ------------------------------------------------------------------ clips (24 fps). loc in mm along Blender axes, rot in degrees
def key(clip, name, chan, keys): CLIPS.setdefault(clip, {}).setdefault(name, []).append((chan, keys))

def define_clips(variant):
    key('lever_squeeze', 'lever', ('rot', 'Y'), [(1, 0), (4, 2.5), (8, 2.5), (12, 0)])                 # the hand presses the lever home
    key('pin_pull', 'pull_ring', ('rot', 'X'), [(1, 0), (5, 80), (16, 85)])                            # ring swings up into the pull
    key('pin_pull', 'safety_pin', ('loc', 'Y'), [(1, 0), (5, 0), (8, -6), (12, -45), (16, -90)])       # pin slides out along -Y
    key('lever_release', 'lever', ('rot', 'Y'), [(1, 0), (3, -35), (5, -80), (7, -115)])               # lever swings up about the hinge
    key('lever_release', 'lever', ('loc', 'Z'), [(1, 0), (5, 0), (7, 12), (12, 70), (20, 150)])        # then leaves the hinge and flies
    key('lever_release', 'lever', ('loc', 'X'), [(1, 0), (5, 0), (7, -8), (12, -50), (20, -120)])
    if 'safety_clip' in OBJ:
        key('safety_clip_off', 'safety_clip', ('rot', 'Y'), [(1, 0), (4, 20), (8, 20)])
        key('safety_clip_off', 'safety_clip', ('loc', 'X'), [(1, 0), (4, 6), (8, 30), (12, 70)])
        key('safety_clip_off', 'safety_clip', ('loc', 'Y'), [(1, 0), (4, 2), (8, 14), (12, 40)])

def bake_clips():
    reg = {}
    for clip, objs in CLIPS.items():
        for name, chans in objs.items():
            o = OBJ[name]; rest = o.location.copy(); o.rotation_mode = 'XYZ'
            ad = o.animation_data_create(); act = bpy.data.actions.new(f'{clip}.{name}'); ad.action = act
            for (kind, ax), keys in chans:
                i = 'XYZ'.index(ax)
                for fr, v in keys:
                    if kind == 'loc':
                        d = Vector((0, 0, 0)); d[i] = v * MM; o.location = rest + d; o.keyframe_insert('location', index=i, frame=fr); o.location = rest
                    else:
                        e = [0.0, 0.0, 0.0]; e[i] = math.radians(v); o.rotation_euler = e; o.keyframe_insert('rotation_euler', index=i, frame=fr); o.rotation_euler = (0, 0, 0)
            tr = ad.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 1, act); tr.mute = True
            ad.action = None; o.location = rest; o.rotation_euler = (0, 0, 0)
            reg.setdefault(clip, []).append(name)
    return reg

# ------------------------------------------------------------------ assemble, export
def build(variant, lod):
    global LOD
    LOD = lod
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for d in (OBJ, W, CLIPS, MATS, SOCK): d.clear()
    sc = bpy.context.scene; sc.render.fps = 24; sc.unit_settings.system = 'METRIC'
    for name, (col, metal, rough) in MAT.items():
        m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
        MATS[name] = m
    root = 'grenade_' + variant.replace('-', '_')
    empty(root, None); empty('body_group', root); empty('fuze', root)
    if variant in ('frag', 'impact'): info = build_frag(impact=variant == 'impact')
    elif variant == 'flash': info = build_flash()
    else: info = build_smoke(variant.split('-')[1])
    meshes = [o for o in OBJ.values() if o.type == 'MESH']
    for o in meshes: _apply(o)
    tris = {}
    for o in meshes:
        o.data.calc_loop_triangles(); tris[o.name] = len(o.data.loop_triangles)
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in meshes:
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            for i in range(3): lo[i] = min(lo[i], p[i]); hi[i] = max(hi[i], p[i])
    define_clips(variant); reg = bake_clips()
    sc.frame_start = 1; sc.frame_end = 24
    work = os.path.join(HERE, 'work'); os.makedirs(work, exist_ok=True)
    stem = f'grenade_{variant}' + ('_figurelivery' if info.get('livery') == 'figure' else '') + ('_h12' if variant == 'flash' and FLASH_HOLES != 18 else '') + ('' if lod == 0 else f'_lod{lod}')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(work, stem + '.blend'))
    bpy.ops.export_scene.gltf(filepath=os.path.join(work, stem + '.glb'), export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_apply=False, export_yup=True)
    hier = {o.name: (o.parent.name if o.parent else None) for o in OBJ.values()}
    stats = dict(variant=variant, lod=lod, parts=len(meshes), triangles=sum(tris.values()), by_part=tris,
                 bbox_mm=dict(x=[round(lo.x / MM, 2), round(hi.x / MM, 2)], y_front_back=[round(lo.y / MM, 2), round(hi.y / MM, 2)], z_up=[round(lo.z / MM, 2), round(hi.z / MM, 2)]),
                 overall_length_mm=round((hi.z - lo.z) / MM, 2), info=info, hierarchy=hier,
                 sockets_mm_model_frame=dict(SOCK), sockets_m_export_frame={k: [round(v[0] * MM, 5), round(v[2] * MM, 5), round(-v[1] * MM, 5)] for k, v in SOCK.items()},
                 clips=reg, options=dict(m18_livery=M18_LIVERY, flash_holes=FLASH_HOLES))
    json.dump(stats, open(os.path.join(work, f'stats_{stem}.json'), 'w'), indent=1)
    print(f'BUILT {stem}: {len(meshes)} parts, {sum(tris.values())} triangles, length {stats["overall_length_mm"]} mm', flush=True)

if __name__ == '__main__':
    for v in VARIANTS:
        if ONLY and v not in ONLY: continue
        for lod in LODS:
            build(v, lod)
