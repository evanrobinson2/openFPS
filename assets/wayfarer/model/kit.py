"""Mesh kit for the Wayfarer recipe. Everything is written in the ship frame (s aft, y starboard, z up, metres)
and converted to Blender's frame (X port, -Y forward, Z up) when an object is finished.

MB collects vertices and faces as plain lists (fast for the hull's hundreds of thousands of faces); primitives are
wound so their normals point outward without a recalculation pass.
"""
import math
import bpy
import numpy as np
from mathutils import Vector, Matrix
import spec

OBJ = {}          # name -> object
MATS = {}         # name -> material
STATS = {}        # name -> dict(tris, group)
LOD = 0

def bl(p):
    return Vector((-p[1], p[0] - spec.L / 2, p[2]))

def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vmul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def vdot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def vcross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def vlen(a): return math.sqrt(vdot(a, a))
def vnorm(a):
    l = vlen(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else (0.0, 0.0, 1.0)
def vlerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def basis(d):
    """Two unit vectors u, v with u x v = d (d unit)."""
    d = vnorm(d)
    ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = vnorm(vcross(ref, d))
    v = vcross(d, u)
    return u, v

def SEG(n):
    return n if LOD == 0 else max(6, n // 2)

# ------------------------------------------------------------------ materials (named by role; the game reads the names)
PALETTE = {
    # name: (r, g, b, metallic, roughness, emission strength, alpha)
    'armour_gunmetal_a': (0.215, 0.225, 0.240, 0.60, 0.56, 0, 1),
    'armour_gunmetal_b': (0.165, 0.172, 0.185, 0.60, 0.62, 0, 1),
    'armour_gunmetal_c': (0.275, 0.285, 0.300, 0.65, 0.50, 0, 1),
    'armour_gunmetal_d': (0.120, 0.125, 0.135, 0.55, 0.68, 0, 1),
    'hull_skin': (0.090, 0.094, 0.102, 0.45, 0.66, 0, 1),
    'armour_paint_red': (0.520, 0.060, 0.035, 0.35, 0.50, 0, 1),
    'armour_paint_red_dark': (0.300, 0.040, 0.030, 0.35, 0.55, 0, 1),
    'substructure_dark': (0.030, 0.031, 0.034, 0.60, 0.70, 0, 1),
    'structure_steel': (0.300, 0.310, 0.325, 0.80, 0.50, 0, 1),
    'structure_primer': (0.430, 0.455, 0.400, 0.20, 0.65, 0, 1),
    'lining_panel': (0.560, 0.575, 0.590, 0.10, 0.60, 0, 1),
    'lining_panel_dark': (0.220, 0.230, 0.245, 0.20, 0.60, 0, 1),
    'deck_plate': (0.150, 0.155, 0.165, 0.70, 0.60, 0, 1),
    'deck_grating': (0.100, 0.105, 0.110, 0.80, 0.55, 0, 1),
    'glass_canopy': (0.060, 0.090, 0.110, 0.00, 0.04, 0, 0.30),
    'glass_port': (0.080, 0.120, 0.140, 0.00, 0.04, 0, 0.35),
    'machinery_dark': (0.070, 0.072, 0.078, 0.85, 0.50, 0, 1),
    'machinery_bare': (0.480, 0.490, 0.500, 1.00, 0.32, 0, 1),
    'machinery_heat': (0.260, 0.190, 0.140, 0.90, 0.45, 0, 1),
    'hydraulic_chrome': (0.800, 0.810, 0.820, 1.00, 0.12, 0, 1),
    'fastener_steel': (0.420, 0.430, 0.445, 1.00, 0.35, 0, 1),
    'rubber_black': (0.020, 0.020, 0.022, 0.00, 0.85, 0, 1),
    'hazard_yellow': (0.750, 0.520, 0.040, 0.20, 0.55, 0, 1),
    'seat_fabric': (0.085, 0.090, 0.100, 0.00, 0.90, 0, 1),
    'copper_pipe': (0.620, 0.330, 0.180, 1.00, 0.35, 0, 1),
    'cable_black': (0.030, 0.030, 0.032, 0.00, 0.70, 0, 1),
    'placard_white': (0.820, 0.820, 0.800, 0.00, 0.60, 0, 1),
    'screen_glow': (0.150, 0.550, 0.650, 0.00, 0.30, 2.5, 1),
    'light_panel': (1.000, 0.960, 0.880, 0.00, 0.40, 6.0, 1),
    'light_red': (1.000, 0.150, 0.080, 0.00, 0.40, 4.0, 1),
    'engine_glow': (1.000, 0.420, 0.120, 0.00, 0.50, 12.0, 1),
    'figure_grey': (0.700, 0.420, 0.120, 0.00, 0.70, 0, 1),
    'blockout_a': (0.55, 0.57, 0.60, 0.0, 0.8, 0, 1),
    'blockout_b': (0.75, 0.30, 0.22, 0.0, 0.8, 0, 1),
    'blockout_c': (0.25, 0.45, 0.70, 0.0, 0.8, 0, 1),
    'blockout_d': (0.35, 0.62, 0.40, 0.0, 0.8, 0, 1),
    'blockout_e': (0.80, 0.68, 0.25, 0.0, 0.8, 0, 1),
    'blockout_f': (0.55, 0.40, 0.70, 0.0, 0.8, 0, 1),
    'blockout_shell': (0.60, 0.62, 0.66, 0.0, 0.7, 0, 0.22),
}

SURFACED = ('armour_gunmetal_a', 'armour_gunmetal_b', 'armour_gunmetal_c', 'armour_gunmetal_d', 'hull_skin', 'armour_paint_red',
            'armour_paint_red_dark', 'substructure_dark', 'structure_steel', 'structure_primer', 'lining_panel', 'lining_panel_dark',
            'deck_plate', 'machinery_dark', 'machinery_heat', 'hazard_yellow')      # roles that carry the surface tile (surface.py)
SURFACE_TILE = 2.0      # metres per repeat
WEAR_CLEAN = ('placard_white', 'figure_grey', 'seat_fabric')     # kept clean by the wear layer

def mat(name):
    if name in MATS:
        return MATS[name]
    r, g, b, me, ro, em, al = PALETTE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1)
    bsdf.inputs['Metallic'].default_value = me
    bsdf.inputs['Roughness'].default_value = ro
    if em:
        bsdf.inputs['Emission Color'].default_value = (r, g, b, 1)
        bsdf.inputs['Emission Strength'].default_value = em
    if al < 1:
        bsdf.inputs['Alpha'].default_value = al
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    if not em and al >= 1 and name not in WEAR_CLEAN:
        # role colour x the 'wear' colour attribute (see wear.py). The glTF exporter reads this as baseColorFactor x COLOR_0.
        vc = m.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'wear'
        mix = m.node_tree.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        mix.inputs['B'].default_value = (r, g, b, 1)
        m.node_tree.links.new(vc.outputs['Color'], mix.inputs['A'])
        m.node_tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    m.use_backface_culling = al >= 1          # exported single-sided, except glass
    m.diffuse_color = (r, g, b, al)
    MATS[name] = m
    return m

# ------------------------------------------------------------------ mesh builder
class MB:
    def __init__(self):
        self.V = []; self.F = []; self.FM = []; self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def v(self, p):
        self.V.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.V) - 1

    def vs(self, pts):
        return [self.v(p) for p in pts]

    def f(self, idx, m):
        self.F.append(tuple(idx)); self.FM.append(self.mi(m))

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    # ---- primitives
    def box(self, s0, s1, y0, y1, z0, z1, m):
        s0, s1 = min(s0, s1), max(s0, s1); y0, y1 = min(y0, y1), max(y0, y1); z0, z1 = min(z0, z1), max(z0, z1)
        a = self.vs([(s0, y0, z0), (s1, y0, z0), (s1, y1, z0), (s0, y1, z0), (s0, y0, z1), (s1, y0, z1), (s1, y1, z1), (s0, y1, z1)])
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f([a[i] for i in q], m)

    def obox(self, c, ax, ay, az, m):
        """Oriented box: centre c, half-extent vectors ax, ay, az (right-handed)."""
        pts = []
        for kz in (-1, 1):
            for ky, kx in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
                pts.append(vadd(c, vadd(vmul(ax, kx), vadd(vmul(ay, ky), vmul(az, kz)))))
        a = self.vs(pts)
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f([a[i] for i in q], m)

    def ring(self, c, u, v, r, n, ph=0.0, ry=None):
        ry = r if ry is None else ry
        return [self.v(vadd(c, vadd(vmul(u, r * math.cos(ph + 2 * math.pi * k / n)), vmul(v, ry * math.sin(ph + 2 * math.pi * k / n))))) for k in range(n)]

    def band(self, r0, r1, m):
        n = len(r0)
        for k in range(n):
            self.f((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]), m)

    def cyl(self, p0, p1, r, m, n=16, r1=None, cap0=True, cap1=True, ph=0.0, mcap=None):
        d = vnorm(vsub(p1, p0)); u, v = basis(d)
        a = self.ring(p0, u, v, r, n, ph); b = self.ring(p1, u, v, r if r1 is None else r1, n, ph)
        self.band(a, b, m)
        if cap0: self.f(a[::-1], mcap or m)
        if cap1: self.f(b, mcap or m)

    def tube(self, p0, p1, r, ri, m, n=16, mi=None):
        """Hollow cylinder (open bore)."""
        d = vnorm(vsub(p1, p0)); u, v = basis(d)
        a = self.ring(p0, u, v, r, n); b = self.ring(p1, u, v, r, n)
        c = self.ring(p0, u, v, ri, n); e = self.ring(p1, u, v, ri, n)
        self.band(a, b, m); self.band(e, c, mi or m)
        self.band(c, a, m); self.band(b, e, m)

    def lathe(self, p0, d, prof, m, n=24, cap0=True, cap1=True, mats=None, ph=0.0):
        """Profile [(distance along d, radius)] revolved about the axis through p0."""
        d = vnorm(d); u, v = basis(d)
        rings = [self.ring(vadd(p0, vmul(d, t)), u, v, max(r, 1e-4), n, ph) for t, r in prof]
        for k in range(len(rings) - 1):
            self.band(rings[k], rings[k + 1], mats[k] if mats else m)
        if cap0: self.f(rings[0][::-1], mats[0] if mats else m)
        if cap1: self.f(rings[-1], mats[-1] if mats else m)

    def ngon_prism(self, p0, p1, r, sides, m, ph=0.0, r1=None):
        self.cyl(p0, p1, r, m, n=sides, r1=r1, ph=ph)

    def prism(self, pts, e, m, mside=None):
        """Planar polygon pts (3D) extruded by vector e."""
        nx = ny = nz = 0.0
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            nx += (a[1] - b[1]) * (a[2] + b[2]); ny += (a[2] - b[2]) * (a[0] + b[0]); nz += (a[0] - b[0]) * (a[1] + b[1])
        if vdot((nx, ny, nz), e) < 0:
            pts = pts[::-1]
        a = self.vs(pts); b = self.vs([vadd(p, e) for p in pts])
        self.f(a[::-1], m); self.f(b, m)
        self.band(a, b, mside or m)

    def pipe(self, pts, r, m, n=10, caps=True):
        """Round tube along a polyline with mitred corners."""
        pts = [tuple(p) for p in pts]
        dirs = [vnorm(vsub(pts[i + 1], pts[i])) for i in range(len(pts) - 1)]
        u, v = basis(dirs[0])
        rings = []
        for i, p in enumerate(pts):
            if i == 0: t = dirs[0]
            elif i == len(pts) - 1: t = dirs[-1]
            else: t = vnorm(vadd(dirs[i - 1], dirs[i]))
            # carry the frame: re-orthogonalise u against the new tangent
            u = vnorm(vsub(u, vmul(t, vdot(u, t)))); v = vcross(t, u)
            k = 1.0
            if 0 < i < len(pts) - 1:
                c = max(vdot(dirs[i - 1], t), 0.5); k = 1.0 / c
            rings.append(self.ring(p, u, v, r * k, n))
        for a, b in zip(rings, rings[1:]):
            self.band(a, b, m)
        if caps:
            self.f(rings[0][::-1], m); self.f(rings[-1], m)

    def sphere(self, c, r, m, n=12, squash=(1, 1, 1)):
        rows = max(4, n // 2)
        rings = []
        for i in range(1, rows):
            th = math.pi * i / rows
            rings.append([self.v((c[0] + squash[0] * r * math.sin(th) * math.cos(2 * math.pi * k / n),
                                  c[1] + squash[1] * r * math.sin(th) * math.sin(2 * math.pi * k / n),
                                  c[2] + squash[2] * r * math.cos(th))) for k in range(n)])
        top = self.v((c[0], c[1], c[2] + squash[2] * r)); bot = self.v((c[0], c[1], c[2] - squash[2] * r))
        for k in range(n):
            self.f((top, rings[0][k], rings[0][(k + 1) % n]), m)
            self.f((bot, rings[-1][(k + 1) % n], rings[-1][k]), m)
        for a, b in zip(rings, rings[1:]):
            for k in range(n):
                self.f((a[k], b[k], b[(k + 1) % n], a[(k + 1) % n]), m)

    def capsule(self, p0, p1, r, m, n=10):
        self.cyl(p0, p1, r, m, n=n, cap0=False, cap1=False)
        self.sphere(p0, r, m, n=n); self.sphere(p1, r, m, n=n)

    def bolt(self, p, nrm, r=0.020, h=0.012, m='fastener_steel', washer=True):
        """Hex bolt head (with a washer) seated at p, standing along nrm. LOD 1 leaves fasteners out."""
        if LOD >= 1:
            return
        nrm = vnorm(nrm); u, v = basis(nrm)
        if washer:
            w0 = self.ring(p, u, v, r * 1.55, 8); w1 = self.ring(vadd(p, vmul(nrm, h * 0.25)), u, v, r * 1.55, 8)
            self.band(w0, w1, m); self.f(w1, m)
            p = vadd(p, vmul(nrm, h * 0.25))
        a = self.ring(p, u, v, r, 6); b = self.ring(vadd(p, vmul(nrm, h)), u, v, r * 0.92, 6)
        self.band(a, b, m); self.f(b, m)

    def bolt_circle(self, c, axis, R_, count, r=0.020, h=0.012, ph=0.0, m='fastener_steel'):
        axis = vnorm(axis); u, v = basis(axis)
        for k in range(count):
            a = ph + 2 * math.pi * k / count
            self.bolt(vadd(c, vadd(vmul(u, R_ * math.cos(a)), vmul(v, R_ * math.sin(a)))), axis, r, h, m)

    def bolt_line(self, p0, p1, nrm, pitch=0.25, r=0.020, h=0.012, ends=True, m='fastener_steel'):
        ln = vlen(vsub(p1, p0)); k = max(1, int(round(ln / pitch)))
        for i in range(0 if ends else 1, k + 1 if ends else k):
            self.bolt(vlerp(p0, p1, i / k), nrm, r, h, m)

    def merge(self, other):
        o = len(self.V)
        self.V.extend(other.V)
        remap = [self.mi(m) for m in other.mats]
        self.F.extend(tuple(i + o for i in f) for f in other.F)
        self.FM.extend(remap[k] for k in other.FM)

    def mirrored(self):
        """Copy mirrored across the centre plane (y -> -y), winding fixed."""
        o = MB(); o.mats = list(self.mats)
        o.V = [(p[0], -p[1], p[2]) for p in self.V]
        o.F = [tuple(reversed(f)) for f in self.F]; o.FM = list(self.FM)
        return o

    def transformed(self, fn):
        o = MB(); o.mats = list(self.mats); o.V = [fn(p) for p in self.V]; o.F = list(self.F); o.FM = list(self.FM)
        return o

# ------------------------------------------------------------------ objects
def empty(name, parent=None, at=None):
    """A named transform node. at (ship frame) is where its origin sits; default is the parent's origin."""
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = 0.2
    bpy.context.scene.collection.objects.link(o)
    par = OBJ[parent] if isinstance(parent, str) else parent
    pw = _world_loc(par) if par is not None else Vector((0, 0, 0))
    o.parent = par
    o.location = (bl(at) - pw) if at is not None else Vector((0, 0, 0))
    OBJ[name] = o
    return o

def _world_loc(o):
    loc = Vector((0, 0, 0))
    while o is not None:
        loc = loc + o.location
        o = o.parent
    return loc

def finish(name, mb, parent, pivot=None, sharp=35.0, group=None):
    """Turn a builder into a named object under parent. pivot (ship frame) becomes the object's origin.
    Objects only ever translate relative to their parents at build time (no rotations), so a pivot is a plain offset."""
    if not mb.F:
        return None
    par = OBJ[parent] if isinstance(parent, str) else parent
    pw = bl(pivot) if pivot is not None else (_world_loc(par) if par is not None else Vector((0, 0, 0)))
    V = np.asarray(mb.V, dtype=np.float64)
    Vb = np.stack([-V[:, 1] - pw.x, V[:, 0] - spec.L / 2 - pw.y, V[:, 2] - pw.z], axis=1)
    me = bpy.data.meshes.new(name)
    nloops = sum(len(f) for f in mb.F)
    me.vertices.add(len(Vb)); me.loops.add(nloops); me.polygons.add(len(mb.F))
    me.vertices.foreach_set('co', Vb.astype(np.float32).ravel())
    starts = np.zeros(len(mb.F), dtype=np.int32); tot = np.fromiter((len(f) for f in mb.F), dtype=np.int32, count=len(mb.F))
    starts[1:] = np.cumsum(tot)[:-1]
    me.loops.foreach_set('vertex_index', np.fromiter((i for f in mb.F for i in f), dtype=np.int32, count=nloops))
    me.polygons.foreach_set('loop_start', starts)
    if hasattr(me.polygons[0], 'loop_total'):
        try: me.polygons.foreach_set('loop_total', tot)
        except Exception: pass
    for m in mb.mats:
        me.materials.append(mat(m))
    me.polygons.foreach_set('material_index', np.asarray(mb.FM, dtype=np.int32))
    if any(m in SURFACED for m in mb.mats):
        # box-projected UVs in the ship frame for the shared surface tile (surface.py): the face's dominant axis picks the plane
        li = np.fromiter((i for f in mb.F for i in f), dtype=np.int64, count=nloops)
        i0, i1, i2 = li[starts], li[starts + 1], li[starts + 2]
        fnrm = np.abs(np.cross(V[i1] - V[i0], V[i2] - V[i0])); ax = np.argmax(fnrm, axis=1)
        la = np.repeat(ax, tot); P = V[li]
        uu = np.where(la == 0, P[:, 1], P[:, 0]); vv = np.where(la == 2, P[:, 1], P[:, 2])
        uvl = me.uv_layers.new(name='surface')
        uvl.data.foreach_set('uv', (np.stack([uu, vv], axis=1) / SURFACE_TILE).astype(np.float32).ravel())
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), dtype=bool))
    try:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    except Exception:
        pass
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.parent = par
    o.location = pw - (_world_loc(par) if par is not None else Vector((0, 0, 0)))
    OBJ[name] = o
    STATS[name] = dict(tris=mb.tris(), group=group or (par.name if par is not None else ''))
    return o

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    OBJ.clear(); MATS.clear(); STATS.clear(); _KEYS.clear()

# ------------------------------------------------------------------ animation clips (24 fps; one NLA track per clip per object)
FPS = 24
_KEYS = {}        # (clip, object name) -> list of (frame, loc offset in ship frame or None, rot (about s, about y, about z) in radians or None)

def key(clip, obj, frame, loc=None, rot=None):
    o = OBJ[obj] if isinstance(obj, str) else obj
    _KEYS.setdefault((clip, o.name), []).append((frame, loc, rot))

def set_rest(obj, loc=None, rot=None):
    """Pose an object for the rest state (the pose the file is saved and exported in)."""
    o = OBJ[obj] if isinstance(obj, str) else obj
    if loc is not None:
        o.location = o.location + Vector((-loc[1], loc[0], loc[2]))
    if rot is not None:
        o.rotation_euler = (-rot[1], rot[0], rot[2])

def bake_clips():
    """Write the keyed clips as actions on NLA tracks named after the clip. Keys are relative to the rest pose."""
    sc = bpy.context.scene; sc.render.fps = FPS
    rest = {}
    names = sorted(set(c for c, _ in _KEYS))
    for (clip, oname), keys in sorted(_KEYS.items()):
        o = bpy.data.objects[oname]
        if oname not in rest:
            rest[oname] = (o.location.copy(), tuple(o.rotation_euler))
        l0, r0 = rest[oname]
        o.animation_data_create(); o.animation_data.action = None
        for frame, loc, rot in sorted(keys, key=lambda k: k[0]):
            if loc is not None:
                o.location = l0 + Vector((-loc[1], loc[0], loc[2])); o.keyframe_insert('location', frame=frame)
            if rot is not None:
                o.rotation_euler = (r0[0] - rot[1], r0[1] + rot[0], r0[2] + rot[2]); o.keyframe_insert('rotation_euler', frame=frame)
        act = o.animation_data.action
        act.name = f'{clip}__{oname}'
        tr = o.animation_data.nla_tracks.new(); tr.name = clip
        tr.strips.new(clip, 0, act)
        tr.mute = True
        o.animation_data.action = None
        o.location = l0; o.rotation_euler = r0
    return names

def smooth_keys(clip, obj, f0, f1, loc=None, rot=None, loc0=(0, 0, 0), rot0=(0, 0, 0), steps=8):
    """Ease in and out from (loc0, rot0) to (loc, rot) between two frames."""
    for k in range(steps + 1):
        t = k / steps; e = t * t * (3 - 2 * t)
        l = None if loc is None else tuple(loc0[i] + (loc[i] - loc0[i]) * e for i in range(3))
        r = None if rot is None else tuple(rot0[i] + (rot[i] - rot0[i]) * e for i in range(3))
        key(clip, obj, f0 + (f1 - f0) * t, l, r)
