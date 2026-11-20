"""Mesh helpers for the UH-60 recipe. Everything is authored in the aircraft's own frame, in inches:

    STA  fuselage station, + aft          (rotor mast centre line = STA 341.2)
    BL   butt line, + = the aircraft's LEFT (port) side
    WL   water line, + up                 (static ground line = WL 183.7, cabin floor = WL 206.75)

and converted once, in `to_world`, to the export frame in metres:  X = BL (left), Y = STA aft, Z = up in Blender,
which the glTF exporter turns into  +X left, +Y up, +Z FORWARD (nose), origin on the ground under the rotor mast.
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

IN = 0.0254
STA0, WL0 = 341.2, 183.7


def to_world(p):
    p = np.asarray(p, dtype=np.float64).reshape(-1, 3)
    return np.stack([p[:, 1] * IN, (p[:, 0] - STA0) * IN, (p[:, 2] - WL0) * IN], axis=1)


# ---------------------------------------------------------------- interpolation
def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) interpolant; returns f(x) for numpy arrays."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    m[1:-1] = np.where(d[:-1] * d[1:] > 0, 2 * d[:-1] * d[1:] / (d[:-1] + d[1:] + 1e-30), 0.0)
    m[0], m[-1] = d[0], d[-1]

    def f(x):
        x = np.asarray(x, float)
        i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        t = np.clip(t, 0, 1)
        h00 = (1 + 2 * t) * (1 - t) ** 2; h10 = t * (1 - t) ** 2; h01 = t * t * (3 - 2 * t); h11 = t * t * (t - 1)
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def lin(xs, ys):
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    return lambda x: np.interp(x, xs, ys)


def resample(pts, n, closed=False):
    """Resample a polyline to n points evenly spaced by arc length."""
    pts = np.asarray(pts, float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n + (1 if closed else 0))[: n]
    return np.stack([np.interp(t, d, pts[:, k]) for k in range(pts.shape[1])], axis=1)


# ---------------------------------------------------------------- raw mesh containers
class Mesh:
    """Accumulates vertices (inches, aircraft frame) and faces."""

    def __init__(self):
        self.v = []; self.f = []; self.n = 0

    def add(self, verts, faces):
        verts = np.asarray(verts, float).reshape(-1, 3)
        self.v.append(verts)
        self.f.extend([tuple(int(i) + self.n for i in f) for f in faces])
        self.n += len(verts)
        return self

    def merge(self, other, M=None):
        if other.n == 0:
            return self
        v = np.vstack(other.v)
        if M is not None:
            v = xf(M, v)
            if np.linalg.det(np.asarray(M)[:3, :3]) < 0:
                return self.add(v, [f[::-1] for f in other.f])
        return self.add(v, other.f)

    def verts(self):
        return np.vstack(self.v) if self.v else np.zeros((0, 3))


def xf(M, v):
    M = np.asarray(M, float); v = np.asarray(v, float).reshape(-1, 3)
    return v @ M[:3, :3].T + M[:3, 3]


def T(sta=0, bl=0, wl=0):
    M = np.eye(4); M[:3, 3] = (sta, bl, wl); return M


def R(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); M = np.eye(4)
    if axis == 'sta': M[1, 1], M[1, 2], M[2, 1], M[2, 2] = c, -s, s, c
    elif axis == 'bl': M[0, 0], M[0, 2], M[2, 0], M[2, 2] = c, s, -s, c
    else: M[0, 0], M[0, 1], M[1, 0], M[1, 1] = c, -s, s, c
    return M


def S(a, b=None, c=None):
    return np.diag([a, a if b is None else b, a if c is None else c, 1.0])


def frame_to(p0, p1):
    """4x4 whose local +Z runs from p0 to p1, origin at p0."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    z = p1 - p0; L = np.linalg.norm(z); z = z / (L + 1e-12)
    a = np.array([0, 0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(a, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, p0
    return M, L


# ---------------------------------------------------------------- primitives (all return Mesh)
def loft(rings, cap0=False, cap1=False, closed=True, flip=False):
    """rings: (R, M, 3) array; quads between successive rings."""
    rings = np.asarray(rings, float); Rn, M, _ = rings.shape
    faces = []
    mm = M if closed else M - 1
    for i in range(Rn - 1):
        a = i * M; b = (i + 1) * M
        for j in range(mm):
            k = (j + 1) % M
            q = (a + j, a + k, b + k, b + j)
            faces.append(q[::-1] if flip else q)
    m = Mesh(); m.add(rings.reshape(-1, 3), faces)
    if cap0:
        i0 = m.n; m.v.append(rings[0].mean(axis=0).reshape(1, 3)); m.n += 1
        m.f.extend([((j + 1) % M, j, i0) if not flip else (j, (j + 1) % M, i0) for j in range(M)])
    if cap1:
        i0 = m.n; b = (Rn - 1) * M; m.v.append(rings[-1].mean(axis=0).reshape(1, 3)); m.n += 1
        m.f.extend([(b + j, b + (j + 1) % M, i0) if not flip else (b + (j + 1) % M, b + j, i0) for j in range(M)])
    return m


def circle(r, n, z=0.0, rx=None, phase=0.0):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False) + phase
    return np.stack([np.cos(a) * r, np.sin(a) * (r if rx is None else rx), np.full(n, z)], axis=1)


def revolve(profile, n=24, M=None, cap0=True, cap1=True):
    """profile: [(radius, z)] along local +Z. Zero radius ends are closed automatically."""
    rings = np.stack([circle(max(r, 1e-4), n, z) for r, z in profile])
    m = loft(rings, cap0=cap0 and profile[0][0] > 1e-3, cap1=cap1 and profile[-1][0] > 1e-3, flip=True)
    if M is not None:
        mm = Mesh(); mm.merge(m, M); return mm
    return m


def cyl(p0, p1, r, n=16, r1=None, cap=True):
    M, L = frame_to(p0, p1)
    return revolve([(r, 0), (r if r1 is None else r1, L)], n, M, cap, cap)


def tube(path, r, n=12, cap=True):
    """Round tube along a polyline (parallel transport frames)."""
    path = np.asarray(path, float); rr = np.broadcast_to(np.asarray(r, float), (len(path),))
    tang = np.gradient(path, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None] + 1e-12
    a = np.array([0, 0, 1.0]) if abs(tang[0][2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(a, tang[0]); x /= np.linalg.norm(x)
    rings = []
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for i, p in enumerate(path):
        t = tang[i]; x = x - t * np.dot(x, t); x /= np.linalg.norm(x) + 1e-12; y = np.cross(t, x)
        rings.append(p + rr[i] * (np.cos(ang)[:, None] * x + np.sin(ang)[:, None] * y))
    return loft(np.array(rings), cap, cap, flip=True)


def box(c, size, M=None):
    c = np.asarray(c, float); h = np.asarray(size, float) / 2
    v = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * h + c
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    m = Mesh().add(v, f)
    if M is not None:
        mm = Mesh(); mm.merge(m, M); return mm
    return m


def rrect(w, h, r, n=5):
    """Rounded rectangle outline (CCW), centred, in a 2D plane."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3); pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def prism(poly2, z0, z1, M=None, taper=1.0):
    """Extrude a CCW 2D polygon (local XY) from z0 to z1 (local Z). n-gon caps."""
    p = np.asarray(poly2, float); n = len(p)
    c = p.mean(axis=0)
    v = np.vstack([np.c_[p, np.full(n, z0)], np.c_[(p - c) * taper + c, np.full(n, z1)]])
    f = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(j, (j + 1) % n, n + (j + 1) % n, n + j) for j in range(n)]
    m = Mesh().add(v, f)
    if M is not None:
        mm = Mesh(); mm.merge(m, M); return mm
    return m


def plane_basis(view):
    """Matrix mapping local (x, y, z) to aircraft frame for a 2D sketch plane.
    'side_l': x = STA, y = WL, z = +BL (extrude outboard to port).  'top': x = STA, y = BL, z = WL."""
    M = np.eye(4)
    if view == 'side_l': M[:3, :3] = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]])
    elif view == 'side_r': M[:3, :3] = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    elif view == 'top': M[:3, :3] = np.eye(3)
    elif view == 'front': M[:3, :3] = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])   # x = BL, y = WL, z = STA
    return M


def text_mesh(body, h, depth=0.012):
    """Stencil lettering as flat geometry in the XY plane, centred, capitals h tall (Blender's built-in font)."""
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = body; cu.align_x = 'CENTER'; cu.resolution_u = 2
    o = bpy.data.objects.new('txt', cu); bpy.context.scene.collection.objects.link(o)
    me = o.to_mesh(); v = np.array([tuple(x.co) for x in me.vertices], float); f = [tuple(q.vertices) for q in me.polygons]
    o.to_mesh_clear(); bpy.data.objects.remove(o); bpy.data.curves.remove(cu)
    m = Mesh()
    if len(v):
        k = h / max(v[:, 1].max() - v[:, 1].min(), 1e-6)
        v = (v - [(v[:, 0].max() + v[:, 0].min()) / 2, (v[:, 1].max() + v[:, 1].min()) / 2, 0]) * k; v[:, 2] = depth
        m.add(v, f)
    return m


def hexnut(across, h, n_hole=0.0):
    r = across / 2 / math.cos(math.pi / 6)
    return prism(np.array([(r * math.cos(a), r * math.sin(a)) for a in np.linspace(0, 2 * np.pi, 6, endpoint=False)]), 0, h)


def bolt(p, nrm, d=0.375, head_h=None, washer=True):
    """Hex-head bolt with washer standing on point p along normal nrm (inches)."""
    M, _ = frame_to(p, np.asarray(p, float) + np.asarray(nrm, float))
    m = Mesh(); hh = head_h or d * 0.65
    if washer:
        m.merge(revolve([(d * 1.05, 0), (d * 1.05, d * 0.12)], 10), M)
    m.merge(hexnut(d * 1.5, hh), M @ T(0, 0, d * 0.12 if washer else 0))
    return m


# ---------------------------------------------------------------- Blender objects
def obj(name, mesh, mat=None, smooth=None, coll=None):
    v = to_world(mesh.verts())
    me = bpy.data.meshes.new(name); me.from_pydata(v.tolist(), [], mesh.f); me.update()
    o = bpy.data.objects.new(name, me); (coll or bpy.context.scene.collection).objects.link(o)
    if mat is not None:
        me.materials.append(mat)
    if smooth is not None:
        shade(o, smooth)
    return o


def shade(o, angle=40.0):
    me = o.data
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ca = math.cos(math.radians(angle))
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.link_faces[0].normal.dot(e.link_faces[1].normal) > ca
        else:
            e.smooth = False
    bm.to_mesh(me); bm.free(); me.update()


def active(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o


def apply_mod(o, m):
    active(o); bpy.ops.object.modifier_apply(modifier=m.name)


def boolean(o, cutter, op='DIFFERENCE', keep=False):
    m = o.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.solver = 'EXACT'; m.object = cutter
    apply_mod(o, m)
    if not keep:
        bpy.data.objects.remove(cutter, do_unlink=True)


def solidify(o, t_in, offset=-1.0):
    m = o.modifiers.new('s', 'SOLIDIFY'); m.thickness = t_in * IN; m.offset = offset; m.use_even_offset = True
    apply_mod(o, m)


def bevel(o, w_in, seg=2, angle=35.0):
    m = o.modifiers.new('bv', 'BEVEL'); m.width = w_in * IN; m.segments = seg; m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle); m.harden_normals = False
    apply_mod(o, m)


def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join()
    if name: objs[0].name = name; objs[0].data.name = name
    return objs[0]


def copy(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name
    for col in o.users_collection: col.objects.link(c)
    return c
