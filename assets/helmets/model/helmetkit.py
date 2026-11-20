"""helmetkit: a parametric tactical-helmet generator (Blender Python).

A helmet is a shell surface plus parts that sit on it. Everything is placed in the shell's own surface coordinates
(a, t): `a` is the azimuth around the head in degrees (0 = front, +90 = the wearer's left, 180 = back) and `t` runs
down a meridian from the crown (t = 0) through the widest line (t = 1) towards the rim. A preset (presets.json) is
just numbers: shell size and curvature, the cut line, paint, and a list of accessories. `random_preset(seed)`
draws a new, plausible helmet from the same ranges, so a whole family can be generated.

Units are millimetres inside this module and metres in Blender. Blender frame: +Z up, -Y is the front (the face),
+X is the wearer's left. The glTF export turns that into +Y up and +Z forward.
"""
import json
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import textures as TX

MM = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))


# =================================================================================================================
# small maths
# =================================================================================================================

def smoothstep(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0, 1)
    return x * x * (3 - 2 * x)


def periodic_spline(points, period=360.0):
    """Catmull-Rom through (x, y) control points, periodic in x. Returns f(x) for arrays."""
    pts = sorted(points)
    xs = np.array([p[0] for p in pts], float)
    ys = np.array([p[1] for p in pts], float)
    n = len(xs)

    def f(x):
        x = np.mod(np.asarray(x, float), period)
        out = np.empty_like(x)
        for k, xv in np.ndenumerate(x):
            i = np.searchsorted(xs, xv, side='right') - 1
            i0, i1, i2, i3 = (i - 1) % n, i % n, (i + 1) % n, (i + 2) % n
            x1 = xs[i1]
            x2 = xs[i2] + (period if i2 <= i1 else 0)
            xv2 = xv + (period if xv < x1 else 0)
            u = (xv2 - x1) / (x2 - x1)
            p0, p1, p2, p3 = ys[i0], ys[i1], ys[i2], ys[i3]
            out[k] = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                            + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
        return out
    return f


def mirrored(points):
    """Control points given for 0..180 degrees, mirrored to the other side."""
    out = list(points)
    for a, v in points:
        if 0 < a < 180:
            out.append((360 - a, v))
    return out


def catmull(pts, n):
    """Open Catmull-Rom through 3D points, n samples."""
    P = [np.asarray(p, float) for p in pts]
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    segs = len(P) - 3
    out = []
    for k in range(n):
        s = k / (n - 1) * segs
        i = min(int(s), segs - 1)
        u = s - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return np.array(out)


def resample(path, n):
    """Resample a polyline to n points evenly by arc length."""
    path = np.asarray(path, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, path[:, i]) for i in range(path.shape[1])], 1)


def frames(path, up_hint):
    """Tangent, normal, binormal along a path; normal follows `up_hint` (per point or one vector)."""
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    U = np.broadcast_to(np.asarray(up_hint, float), path.shape)
    N = U - (U * T).sum(1)[:, None] * T
    N /= np.linalg.norm(N, axis=1)[:, None]
    B = np.cross(T, N)
    return T, N, B


# =================================================================================================================
# mesh helpers
# =================================================================================================================

class MeshBuilder:
    """Collects vertices, faces and per-corner UVs, then makes a Blender object."""

    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def add_v(self, p):
        self.v.append(tuple(float(c) * MM for c in p))
        return len(self.v) - 1

    def add_vs(self, ps):
        base = len(self.v)
        for p in np.asarray(ps).reshape(-1, 3):
            self.v.append(tuple(float(c) * MM for c in p))
        return base

    def face(self, idx, uvs=None):
        self.f.append(tuple(idx))
        self.uv.append(tuple(uvs) if uvs is not None else tuple((0.0, 0.0) for _ in idx))

    def grid(self, P, UV=None, close_cols=False, close_rows=False, flip=False):
        """Quads over a (rows, cols, 3) array. UV per point (rows, cols, 2); wrapped columns get u + period."""
        R, C = P.shape[:2]
        base = self.add_vs(P)
        idx = lambda r, c: base + (r % R) * C + (c % C)
        if UV is None:
            UV = np.zeros((R, C, 2))
        uper = UV[0, -1, 0] - UV[0, -2, 0] if C > 1 else 0
        for r in range(R - 1 + (1 if close_rows else 0)):
            for c in range(C - 1 + (1 if close_cols else 0)):
                cs = [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]
                ids = [idx(*q) for q in cs]
                uvs = []
                for (qr, qc) in cs:
                    u, v = UV[qr % R, qc % C]
                    if qc >= C:
                        u = UV[qr % R, C - 1, 0] + uper
                    uvs.append((float(u), float(v)))
                if flip:
                    ids, uvs = ids[::-1], uvs[::-1]
                self.face(ids, uvs)
        return base

    def cap(self, ring_ids, centre, uvs=None, flip=False):
        c = self.add_v(centre)
        n = len(ring_ids)
        for i in range(n):
            ids = [c, ring_ids[i], ring_ids[(i + 1) % n]]
            fu = [(0.5, 0.5)] * 3 if uvs is None else [uvs[0], uvs[1 + i], uvs[1 + (i + 1) % n]]
            if flip:
                ids, fu = ids[::-1], fu[::-1]
            self.face(ids, fu)

    def make(self, name, mat, smooth_angle=50, collection=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate(clean_customdata=False)
        uvl = me.uv_layers.new(name='UVMap')
        # (validate may drop degenerate faces: rebuild the uv by face order where they still match)
        if len(me.polygons) == len(self.f):
            k = 0
            data = uvl.data
            for p, uvs in zip(me.polygons, self.uv):
                for li, uv in zip(p.loop_indices, uvs):
                    data[li].uv = uv
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        if smooth_angle is not None:
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        o = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(o)
        if mat is not None:
            me.materials.append(mat)
        return o


def apply_mods(o):
    """Bake an object's modifier stack into its mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = o.data
    o.modifiers.clear()
    o.data = me
    bpy.data.meshes.remove(old)
    return o


def bevel(o, width_mm, segs=2, angle=35):
    m = o.modifiers.new('bevel', 'BEVEL')
    m.width = width_mm * MM
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = False
    return m


def boolean(o, cutter, op='DIFFERENCE'):
    m = o.modifiers.new('bool', 'BOOLEAN')
    m.operation = op
    m.object = cutter
    m.solver = 'EXACT'
    keep = o.data.copy()
    apply_mods(o)
    if len(o.data.polygons) == 0:
        print('boolean gave nothing on', o.name, '- kept the uncut part')
        o.data = keep
    else:
        bpy.data.meshes.remove(keep)
    bpy.data.objects.remove(cutter)
    return o


def place(o, origin_mm, N, T):
    """Orient a part built in a local frame (x = T along, y = B, z = N out) at a surface point."""
    N = Vector(N).normalized()
    T = (Vector(T) - Vector(T).dot(N) * N).normalized()
    B = N.cross(T)
    M = Matrix((T, B, N)).transposed().to_4x4()
    M.translation = Vector(origin_mm) * MM
    o.matrix_world = M
    return o


def bake_transform(o):
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)


def superquadric(name, size_mm, e=(0.3, 0.3), n=(48, 24), mat=None, uv_tile=30.0):
    """A rounded box / capsule / ellipsoid: |x|^(2/e2)... the classic superquadric. size = full extents (mm)."""
    rx, ry, rz = (s / 2 for s in size_mm)
    e1, e2 = e
    sp = lambda w, m: np.sign(np.sin(w)) * np.abs(np.sin(w)) ** m
    cp = lambda w, m: np.sign(np.cos(w)) * np.abs(np.cos(w)) ** m
    nu, nv = n
    eta = np.linspace(-np.pi / 2, np.pi / 2, nv + 1)[1:-1]
    om = np.linspace(-np.pi, np.pi, nu, endpoint=False)
    E, O = np.meshgrid(eta, om, indexing='ij')
    P = np.stack([rx * cp(E, e1) * cp(O, e2), ry * cp(E, e1) * sp(O, e2), rz * sp(E, e1)], -1)
    UV = np.stack([(O + np.pi) * max(rx, ry) / uv_tile, (E + np.pi / 2) * rz / uv_tile], -1)
    mb = MeshBuilder()
    base = mb.grid(P, UV, close_cols=True)
    R, C = P.shape[:2]
    mb.cap([base + c for c in range(C)][::-1], (0, 0, -rz))
    mb.cap([base + (R - 1) * C + c for c in range(C)], (0, 0, rz))
    return mb.make(name, mat, smooth_angle=60)


def lathe(name, profile, segs=48, mat=None, close_ends=True, uv_tile=30.0):
    """Revolve an (r, z) profile (mm) around local Z. End points on the axis (r ~ 0) become closed poles."""
    prof = np.asarray(profile, float)
    first_pole = prof[0, 0] < 0.05
    last_pole = prof[-1, 0] < 0.05
    ring = prof[(1 if first_pole else 0):(len(prof) - 1 if last_pole else len(prof))]
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    P = np.stack([ring[:, 0, None] * np.cos(a)[None, :], ring[:, 0, None] * np.sin(a)[None, :],
                  np.broadcast_to(ring[:, 1, None], (len(ring), segs))], -1)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
    UV = np.stack(np.meshgrid(a * ring[:, 0].max() / uv_tile, L / uv_tile, indexing='xy'), -1)
    mb = MeshBuilder()
    base = mb.grid(P, UV, close_cols=True, flip=True)
    R = len(ring)
    if first_pole:
        mb.cap([base + c for c in range(segs)], (0, 0, prof[0, 1]))
    if last_pole:
        mb.cap([base + (R - 1) * segs + c for c in range(segs)][::-1], (0, 0, prof[-1, 1]))
    return mb.make(name, mat, smooth_angle=40)


def sweep(name, path_mm, up, profile, mat=None, closed_path=False, caps=True, uv_tile=(30.0, 30.0),
          scale=None, smooth=40):
    """Sweep a closed 2D profile [(x along N, y along B)] along a 3D path. `scale` per point optional."""
    path = np.asarray(path_mm, float)
    T, N, B = frames(path, up)
    prof = np.asarray(profile, float)
    s = np.ones(len(path)) if scale is None else np.asarray(scale, float)
    P = path[:, None, :] + (prof[None, :, 0, None] * N[:, None, :] + prof[None, :, 1, None] * B[:, None, :]) * s[:, None, None]
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    per = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([prof, prof[:1]]), axis=0), axis=1))][:-1]
    UV = np.stack(np.meshgrid(per / uv_tile[0], along / uv_tile[1], indexing='xy'), -1)
    mb = MeshBuilder()
    base = mb.grid(P, UV, close_cols=True, close_rows=closed_path)
    if caps and not closed_path:
        R, C = P.shape[:2]
        mb.f.append(tuple(base + c for c in range(C))[::-1]); mb.uv.append(tuple((0.0, 0.0) for _ in range(C)))
        mb.f.append(tuple(base + (R - 1) * C + c for c in range(C))); mb.uv.append(tuple((0.0, 0.0) for _ in range(C)))
    return mb.make(name, mat, smooth_angle=smooth)


def round_rect(w, h, r, n_corner=8):
    """Closed 2D rounded rectangle, counter-clockwise."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n_corner + 1):
            a = math.radians(a0 + 90 * k / n_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# =================================================================================================================
# the shell
# =================================================================================================================

class Shell:
    """The shell's outer surface S(a, t) and its cut line.

    Planform: a superellipse (exponent `plan_n`) with the front half shorter and narrower than the back (a head is
    egg-shaped). Profile: a superellipse dome (exponent `dome_m`) down to the widest line, then a skirt that goes
    straight down with an optional flare. The crown's high point sits `crown_back` mm behind centre. The result is
    then scaled so its exterior length, width and height equal the preset's (the Army's mechanical data for the ACH
    gives these per size). The cut line is the depth of the rim below the crown, as a periodic spline over azimuth.
    """

    def __init__(self, p):
        self.p = p
        self.th = p['thickness']
        self.Hd = p['dome_height']
        cut = mirrored([tuple(c) for c in p['cut']])
        self.depth = periodic_spline(cut)
        self.sx = self.sy = 1.0
        self.zc = 0.0
        # first pass: measure, then scale to the published exterior dimensions
        self._fit()

    # -- raw surface ---------------------------------------------------------------------------------------------
    def _raw(self, a_deg, t):
        p = self.p
        a = np.radians(a_deg)
        n = p['plan_n']
        sa, ca = np.sin(a), np.cos(a)
        ex = 2.0 / n
        ux = np.sign(sa) * np.abs(sa) ** ex
        uy = np.sign(ca) * np.abs(ca) ** ex
        front = ca > 0
        half_l = np.where(front, p['length'] / 2 * (1 - p['egg']), p['length'] / 2 * (1 + p['egg']))
        half_w = p['width'] / 2 * (1 - p['front_taper'] * np.clip(ca, 0, 1) ** 2)
        m = p['dome_m']
        t = np.asarray(t, float)
        tt = np.clip(t, 0, 1) * np.pi / 2
        s_dome = np.abs(np.sin(tt)) ** (2 / m)
        z_dome = self.Hd * np.abs(np.cos(tt)) ** (2 / m)
        below = np.clip(t - 1, 0, None)
        skirt = below * self.Hd * np.pi / 2                       # (depth below the widest line)
        s = s_dome + p['flare'] * (below ** 2) + p.get('flare_back', 0.0) * (below ** 2) * np.clip(-ca, 0, 1)
        s = s - p.get('tuck', 0.0) * np.sin(np.clip(t, 0, 1) * np.pi) ** 4 * 0  # (reserved)
        x = half_w * ux * s
        y = -half_l * uy * s + p['crown_back'] * np.abs(np.cos(tt)) ** 2
        z = np.where(t <= 1, z_dome, -skirt)
        return np.stack([x, y, z], -1)

    def S(self, a_deg, t, off=0.0):
        """Outer surface point (mm), optionally offset along the normal (negative = inwards)."""
        P = self._raw(a_deg, t)
        P = P * np.array([self.sx, self.sy, 1.0]) - np.array([0, 0, self.zc])
        if np.any(off):
            P = P + self.N(a_deg, t) * np.asarray(off)[..., None]
        return P

    def N(self, a_deg, t):
        a_deg = np.asarray(a_deg, float)
        t = np.asarray(t, float)
        h = 1e-3
        Pa = self.S(a_deg + 0.05, t) - self.S(a_deg - 0.05, t)
        tp = np.maximum(t, h)
        Pt = self.S(a_deg, tp + h) - self.S(a_deg, tp - h)
        n = np.cross(Pt, Pa)
        l = np.linalg.norm(n, axis=-1, keepdims=True)
        n = np.where(l > 1e-9, n / np.maximum(l, 1e-12), np.array([0, 0, 1.0]))
        # at the crown the normal is straight up
        return np.where((t < 1e-3)[..., None], np.array([0, 0, 1.0]), n)

    def dS_dt(self, a, t):
        return (self.S(a, t + 1e-3) - self.S(a, t - 1e-3)) / 2e-3

    def t_at_depth(self, a_deg, depth):
        """t where the outer surface is `depth` mm below the crown, by bisection."""
        a_deg = np.asarray(a_deg, float)
        depth = np.broadcast_to(np.asarray(depth, float), a_deg.shape)
        top = self.crown_z
        lo = np.zeros_like(a_deg)
        hi = np.full_like(a_deg, 3.0)
        for _ in range(48):
            mid = (lo + hi) / 2
            z = self.S(a_deg, mid)[..., 2]
            deeper = (top - z) > depth
            hi = np.where(deeper, mid, hi)
            lo = np.where(deeper, lo, mid)
        return (lo + hi) / 2

    def t_cut(self, a_deg):
        return self.t_at_depth(a_deg, self.depth(a_deg))

    def _fit(self):
        self.crown_z = self.Hd
        a = np.linspace(0, 360, 721)
        tc = self.t_cut(a)
        ts = np.linspace(0, 1, 60)[None, :] * tc[:, None]
        P = self.S(np.broadcast_to(a[:, None], ts.shape), ts)
        L = P[..., 1].max() - P[..., 1].min()
        W = P[..., 0].max() - P[..., 0].min()
        self.sx = self.p['width'] / W
        self.sy = self.p['length'] / L
        # put the origin at the top of the head: the inner crown, less the crown pad
        self.zc = self.Hd - self.th - self.p.get('crown_standoff', 19.0)
        self.crown_z = self.Hd - self.zc
        P = self.S(np.broadcast_to(a[:, None], ts.shape), ts)
        self.bbox = (P[..., 0].max() - P[..., 0].min(), P[..., 1].max() - P[..., 1].min(),
                     P[..., 2].max() - P[..., 2].min())

    def grid(self, na=192, nt=72, t_end=None, t_start=0.0):
        a = np.linspace(0, 360, na, endpoint=False)
        tc = self.t_cut(a) if t_end is None else np.broadcast_to(t_end, a.shape)
        s = np.linspace(0, 1, nt)
        # denser rows near the crown (the pole) and near the rim, where the shape turns
        f = 0.65 * (1 - (1 - s) ** 1.25) + 0.35 * (0.5 - 0.5 * np.cos(np.pi * s))
        T = t_start + (tc[None, :] - t_start) * f[:, None]
        A = np.broadcast_to(a[None, :], T.shape)
        return A, T

    def area(self):
        """Outer surface area inside the cut line (cm²)."""
        A, T = self.grid(360, 160)
        P = self.S(A, T)
        Pc = np.concatenate([P, P[:, :1]], 1)
        d1 = Pc[1:, :-1] - Pc[:-1, :-1]
        d2 = Pc[:-1, 1:] - Pc[:-1, :-1]
        d3 = Pc[1:, 1:] - Pc[1:, :-1]
        d4 = Pc[1:, 1:] - Pc[:-1, 1:]
        ar = 0.5 * np.linalg.norm(np.cross(d1, d2), axis=-1) + 0.5 * np.linalg.norm(np.cross(d3, d4), axis=-1)
        return ar.sum() / 100.0

    def tangent_map(self, a0, t0, u_mm, v_mm, iters=8):
        """Lay a flat sheet on the shell: the point u mm across and v mm down in the tangent plane at (a0, t0),
        projected onto the surface along that plane's normal. Straight edges stay straight (a cut panel)."""
        u_mm, v_mm = np.asarray(u_mm, float), np.asarray(v_mm, float)
        c = self.S(a0, t0)
        n = self.N(a0, t0)
        Tu = self.S(a0 + 0.5, t0) - self.S(a0 - 0.5, t0)
        Tu = Tu - Tu.dot(n) * n; Tu /= np.linalg.norm(Tu)
        Tv = np.cross(n, Tu)                                    # (down the meridian)
        if Tv.dot(self.dS_dt(a0, t0)) < 0:
            Tv = -Tv
        q = c + u_mm[..., None] * Tu + v_mm[..., None] * Tv
        a, t = self.local(a0, t0, u_mm, v_mm)
        for _ in range(iters):
            r = self.S(a, t) - q
            Sa = (self.S(a + 0.05, t) - self.S(a - 0.05, t)) / 0.1
            St = (self.S(a, t + 1e-3) - self.S(a, t - 1e-3)) / 2e-3
            e1, e2 = (r * Tu).sum(-1), (r * Tv).sum(-1)
            j11, j12 = (Sa * Tu).sum(-1), (St * Tu).sum(-1)
            j21, j22 = (Sa * Tv).sum(-1), (St * Tv).sum(-1)
            det = j11 * j22 - j12 * j21
            det = np.where(np.abs(det) < 1e-9, 1e-9, det)
            da = (j22 * e1 - j12 * e2) / det
            dt = (-j21 * e1 + j11 * e2) / det
            a, t = a - da, np.maximum(t - dt, 1e-4)
        return a, t

    def local(self, a0, t0, u_mm, v_mm):
        """From a surface point, walk u mm around (towards +a) and v mm down the meridian: returns (a, t)."""
        u_mm, v_mm = np.asarray(u_mm, float), np.asarray(v_mm, float)
        # down the meridian first, by arc length
        ts = np.linspace(max(t0 - 1.2, 0.0), t0 + 1.2, 1200)
        P = self.S(np.full_like(ts, a0), ts)
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        s0 = np.interp(t0, ts, s)
        t = np.interp(s0 + v_mm, s, ts)
        # then around at that height (the metric of a there)
        r = np.linalg.norm((self.S(a0 + 0.5, t) - self.S(a0 - 0.5, t)), axis=-1)   # mm per degree
        a = a0 + u_mm / np.maximum(r, 1e-6)
        return a, t


# =================================================================================================================
# materials
# =================================================================================================================

class Materials:
    """One Blender material per role, with tileable maps written next to the build."""

    TILE = {'paint': 120.0, 'loop': 40.0, 'webbing': 25.4, 'braid': 12.0, 'foam_fabric': 30.0,
            'polymer': 30.0, 'metal': 30.0, 'leatherette': 30.0, 'foam_ball': 20.0, 'camo': 300.0, 'rubber': 30.0}

    def __init__(self, workdir, fast=False, tex_size=1024):
        self.dir = os.path.join(workdir, 'tex')
        os.makedirs(self.dir, exist_ok=True)
        self.fast = fast
        self.n = 256 if fast else tex_size
        self.cache = {}
        self.maps = {}

    def _maps(self, kind):
        if kind not in self.maps:
            n = self.n if kind in ('paint', 'camo') else max(self.n // 2, 256)
            if kind == 'camo':
                self.maps[kind] = None
            elif kind == 'rubber':
                self.maps[kind] = TX.polymer(n, 7)
            else:
                self.maps[kind] = TX.MAPS[kind](n)
        return self.maps[kind]

    def _img(self, name, arr, colour_space):
        path = os.path.join(self.dir, name + '.png')
        TX.save_png(path, arr)
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = colour_space
        return img

    def get(self, role, kind, colour, metallic=0.0, rough_scale=1.0, camo=None):
        key = (role, kind, colour, camo and camo.get('seed'))
        if key in self.cache:
            return self.cache[key]
        mat = bpy.data.materials.new(role)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes['Principled BSDF']
        bsdf.inputs['Metallic'].default_value = metallic
        out = nt.nodes['Material Output']
        if kind == 'camo':
            m = TX.digital_camo(self.n, seed=camo.get('seed', 81), colours=tuple(camo['colours']))
            col, nrm, rough = m['color'], m['normal'], m['rough']
        else:
            m = self._maps(kind)
            c = TX.srgb(colour)
            col = c[None, None, :] * m['tint'][..., None]
            nrm, rough = m['normal'], np.clip(m['rough'] * rough_scale, 0.05, 1)
        tag = f'{role}'
        im_c = self._img(tag + '_color', col, 'sRGB')
        im_n = self._img(tag + '_normal', nrm, 'Non-Color')
        im_r = self._img(tag + '_rough', rough, 'Non-Color')
        tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = im_c
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im_n
        tr = nt.nodes.new('ShaderNodeTexImage'); tr.image = im_r
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(tc.outputs['Color'], bsdf.inputs['Base Color'])
        nt.links.new(tr.outputs['Color'], bsdf.inputs['Roughness'])
        nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
        mat['tile_mm'] = self.TILE[kind]
        self.cache[key] = mat
        return mat


def box_uv(o, tile_mm):
    """Re-map UVs by box projection (top-down for faces facing up, cylindrical round the sides): no pinching at the
    crown. Used for the shell, whose paint grit hides the change of projection."""
    me = o.data
    uv = me.uv_layers.active.data
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3) / MM
    li = np.empty(len(me.loops), int); me.loops.foreach_get('vertex_index', li)
    out = np.zeros((len(me.loops), 2))
    for p in me.polygons:
        n = p.normal
        ids = list(p.loop_indices)
        P = co[li[ids]]
        if abs(n.z) > 0.55:
            out[ids] = P[:, :2] / tile_mm
        else:
            ang = np.arctan2(P[:, 0], -P[:, 1])
            ac = math.atan2(p.center.x, -p.center.y)
            ang = ac + ((ang - ac + np.pi) % (2 * np.pi) - np.pi)
            out[ids] = np.stack([ang * 125.0 / tile_mm, P[:, 2] / tile_mm], -1)
    uv.foreach_set('uv', out.ravel())


def tile(mat):
    return float(mat.get('tile_mm', 30.0))


# =================================================================================================================
# the helmet
# =================================================================================================================

class Helmet:
    def __init__(self, preset, workdir, fast=False):
        self.p = preset
        self.fast = fast
        self.res = 0.5 if fast else 1.0
        self.sh = Shell(preset['shell'])
        self.M = Materials(workdir, fast)
        self.col = bpy.data.collections.new(preset['id'])
        bpy.context.scene.collection.children.link(self.col)
        self.parts = []
        self.sockets = {}

    # -- material shortcuts ----------------------------------------------------------------------------------
    def mat(self, role):
        c = self.p['colours']
        spec = {
            'shell_paint': ('paint', c['shell'], 0.0, 1.0),
            'shell_laminate': ('webbing', c.get('laminate', '#2c2b27'), 0.0, 1.0),
            'edge_trim_rubber': ('rubber', c.get('trim', '#1d1d1c'), 0.0, 1.35),
            'rail_polymer': ('polymer', c.get('rails', c['shell']), 0.0, 1.0),
            'shroud_metal': ('metal', c.get('shroud', '#2a2a28'), 0.6, 1.0),
            'bolt_steel': ('metal', '#2b2c2d', 0.85, 0.9),
            'velcro_loop': ('loop', c.get('loop', c['shell']), 0.0, 1.0),
            'webbing_nylon': ('webbing', c.get('webbing', '#3b3a31'), 0.0, 1.0),
            'buckle_polymer': ('polymer', '#1b1b1b', 0.0, 0.9),
            'pad_fabric': ('foam_fabric', c.get('pads', '#2a2b2b'), 0.0, 1.0),
            'bungee_elastic': ('braid', c.get('bungee', '#1e1e1d'), 0.0, 1.0),
            'headset_polymer': ('polymer', c.get('headset', '#232425'), 0.0, 0.85),
            'ear_seal_leatherette': ('leatherette', '#161616', 0.0, 1.0),
            'mic_foam': ('foam_ball', '#141414', 0.0, 1.0),
            'pouch_fabric': ('webbing', c.get('pouch', c.get('loop', c['shell'])), 0.0, 1.0),
            'cover_fabric': ('camo', None, 0.0, 1.0),
        }[role]
        kind, colour, met, rs = spec
        if kind == 'camo':
            return self.M.get(role, 'camo', None, camo=self.p['cover'])
        return self.M.get(role, kind, colour, met, rs)

    def add(self, o, part):
        o['part'] = part
        if o.users_collection and o.users_collection[0] is not self.col:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            self.col.objects.link(o)
        self.parts.append(o)
        return o

    # -- 1. shell ---------------------------------------------------------------------------------------------
    def build_shell(self):
        sh = self.sh
        na, nt = int(224 * self.res), int(96 * self.res)
        A, T = sh.grid(na, nt)
        th = sh.th
        O = sh.S(A, T)
        g = self.p.get('comm_groove')
        if g:
            # a shallow channel over the crown, ear to ear, for an over-the-head headset band (FAST data sheets)
            d = np.abs(O[..., 1] - g['y'])
            prof = smoothstep(g['w'] / 2 + 3.0, g['w'] / 2 - 1.0, d)
            reach = smoothstep(g.get('z_min', -40.0), g.get('z_min', -40.0) + 15.0, O[..., 2])
            O = O + sh.N(A, T) * (-g['depth'] * prof * reach)[..., None]
        I = sh.S(A, T, -th)
        # the rim: a half-round across the shell's thickness
        tc = T[-1]
        a = A[-1]
        n_rim = 7
        Nr = sh.N(a, tc)
        D = sh.dS_dt(a, tc)
        D = D - (D * Nr).sum(-1, keepdims=True) * Nr
        D /= np.linalg.norm(D, axis=-1, keepdims=True)
        C = O[-1] - Nr * th / 2
        rim = []
        for k in range(1, n_rim):
            q = math.pi * k / n_rim
            rim.append(C + (th / 2) * (Nr * math.cos(q) + D * math.sin(q)))
        rows = np.concatenate([O, np.array(rim), I[::-1]], 0)
        # uv: around (integer number of tiles) x along the surface
        circ = 2 * math.pi * 120.0
        k = max(1, round(circ / tile(self.mat('shell_paint'))))
        u = (A[0] / 360.0) * k
        seg = np.linalg.norm(np.diff(rows, axis=0), axis=-1)
        v = np.r_[np.zeros((1, na)), np.cumsum(seg, axis=0)] / tile(self.mat('shell_paint'))
        UV = np.stack([np.broadcast_to(u, v.shape), v], -1)
        mb = MeshBuilder()
        base = mb.grid(rows[1:], UV[1:], close_cols=True)
        R = rows.shape[0] - 1
        mb.cap([base + c for c in range(na)][::-1], rows[0, 0], flip=False)
        mb.cap([base + (R - 1) * na + c for c in range(na)], rows[-1, 0], flip=False)
        o = mb.make('shell', self.mat('shell_paint'), smooth_angle=80)
        # the inside is bare laminate, not paint
        o.data.materials.append(self.mat('shell_laminate'))
        first_inner = (nt - 1) + (n_rim - 1)
        mi = []
        for r in range(R - 1):
            mi += [1 if r >= first_inner else 0] * na
        mi += [0] * na + [1] * na
        o.data.polygons.foreach_set('material_index', mi)
        box_uv(o, tile(self.mat('shell_paint')))
        self.add(o, 'shell')
        self.shell_obj = o
        return o

    def build_edge_trim(self):
        """Rubber edge band: a U-channel clamped over the rim."""
        sh = self.sh
        na = int(320 * self.res)
        a = np.linspace(0, 360, na, endpoint=False)
        tc = sh.t_cut(a)
        th, w, lip = sh.th, self.p.get('trim_thickness', 1.8), self.p.get('trim_lip', 7.0)
        Nr = sh.N(a, tc)
        D = sh.dS_dt(a, tc)
        D = D - (D * Nr).sum(-1, keepdims=True) * Nr
        D /= np.linalg.norm(D, axis=-1, keepdims=True)
        C = sh.S(a, tc) - Nr * th / 2
        # profile in (n, d) around C: up the outside, around the rim, up the inside, back down through the shell
        R = th / 2 + w
        prof = []
        prof.append((th / 2 + w * 0.35, -lip))                      # outside lip top (tapered)
        prof.append((th / 2 + w, -lip + 1.6))
        for k in range(0, 9):
            q = math.pi * k / 8
            prof.append((R * math.cos(q), max(0.0, R * math.sin(q))) if k not in (0, 8) else
                        ((R if k == 0 else -R), 0.0))
        prof.append((-th / 2 - w, -lip + 1.6))
        prof.append((-th / 2 - w * 0.35, -lip))
        prof.append((-th / 2 + 0.05, -lip))
        prof.append((th / 2 - 0.05, -lip))
        prof = np.array(prof)
        P = C[:, None, :] + prof[None, :, 0, None] * Nr[:, None, :] + prof[None, :, 1, None] * D[:, None, :]
        # the "-lip" rows must follow the shell surface up, not a straight tangent: re-project them
        for j in (0, 1, len(prof) - 4, len(prof) - 3, len(prof) - 2, len(prof) - 1):
            back = prof[j, 1]
            a2, t2 = a, None
        # walking up the surface: move the four lip points onto the shell's offset surfaces
        up_t = np.array([sh.local(ai, ti, 0.0, -lip)[1] for ai, ti in zip(a, tc)])
        up_t2 = np.array([sh.local(ai, ti, 0.0, -lip + 1.6)[1] for ai, ti in zip(a, tc)])
        P[:, 0] = sh.S(a, up_t, w * 0.35)
        P[:, 1] = sh.S(a, up_t2, w)
        P[:, -4] = sh.S(a, up_t2, -th - w)
        P[:, -3] = sh.S(a, up_t, -th - w * 0.35)
        P[:, -2] = sh.S(a, up_t, -th + 0.05)
        P[:, -1] = sh.S(a, up_t, -0.05)
        P = P.transpose(1, 0, 2)                                  # rows = profile, cols = around
        circ = np.linalg.norm(np.diff(np.vstack([P[3], P[3][:1]]), axis=0), axis=1).sum()
        u = np.arange(na) / na * round(circ / 30.0)
        v = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P[:, 0], axis=0), axis=1))] / 30.0
        UV = np.stack(np.meshgrid(u, v), -1)
        mb = MeshBuilder()
        mb.grid(P, UV, close_cols=True, close_rows=True, flip=True)
        o = mb.make('edge_trim', self.mat('edge_trim_rubber'), smooth_angle=60)
        return self.add(o, 'edge_trim')

    # -- conformal parts --------------------------------------------------------------------------------------
    def conformal_pad(self, name, mat, a0, t0, w, h, r_corner, thick, edge_r, inside=False, base_off=0.0,
                      dome=0.0, rot=0.0, n_bound=None, binding=None):
        """A pillow-shaped part lying on the shell: rounded-rect outline (w x h mm, around x down), thickness
        `thick`, edges rounded with radius `edge_r`, an optional dome. On the outside or the inside surface."""
        sh = self.sh
        nb = n_bound or int(max(32, 4 * (w + h) / 6) * self.res + 8)
        outline = np.array(round_rect(w, h, r_corner, max(4, int(nb / 8))))
        outline = resample(np.vstack([outline, outline[:1]]), nb + 1)[:-1]
        if rot:
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            outline = outline @ np.array([[c, s], [-s, c]])
        rad = np.linalg.norm(outline, axis=1)
        # rings: dense near the edge (distance from the edge e), then proportional to the centre
        e_edge = [0, 0.15, 0.45, 0.9, 1.5, 2.2]
        e_edge = [e * edge_r / 2.2 for e in e_edge]
        rings = []
        for e in e_edge:
            rings.append(np.clip(1 - e / np.maximum(rad, 1e-6), 0.05, 1))
        last = rings[-1]
        for f in np.linspace(1, 0, 6)[1:-1]:
            rings.append(last * f)
        rings = np.array(rings)                                     # (nr, nb) scale of the outline
        e = (1 - rings) * rad[None, :]
        prof = np.where(e < edge_r, np.sqrt(np.clip(1 - (1 - e / edge_r) ** 2, 0, 1)), 1.0)
        rr = np.clip(1 - rings, 0, 1)                               # (distance fraction towards the centre)
        hgt = thick * prof + dome * (1 - (1 - rr) ** 2) * prof
        U = outline[None, :, 0] * rings
        V = outline[None, :, 1] * rings
        sign = -1 if inside else 1
        aa, tt = sh.tangent_map(a0, t0, U.ravel(), -V.ravel())
        aa, tt = aa.reshape(U.shape), tt.reshape(U.shape)
        base = (-sh.th if inside else 0.0) + sign * base_off
        top = sh.S(aa, tt, base + sign * hgt)
        bot = sh.S(aa, tt, base + sign * 0.02)
        # centre point
        a_c, t_c = sh.local(a0, t0, np.array(0.0), np.array(0.0))
        ctop = sh.S(a_c, t_c, base + sign * (thick + dome))
        cbot = sh.S(a_c, t_c, base)
        tl = tile(mat)
        UVt = np.stack([U / tl, -V / tl], -1)
        mb = MeshBuilder()
        b1 = mb.grid(top, UVt, close_cols=True, flip=inside)
        nr = top.shape[0]
        ring_uv = [(float(U[-1, c] / tl), float(-V[-1, c] / tl)) for c in range(nb)]
        mb.cap([b1 + (nr - 1) * nb + c for c in range(nb)], ctop, uvs=[(0.0, 0.0)] + ring_uv, flip=inside)
        b2 = mb.grid(bot[:1], None, close_cols=True)
        # the bottom: one flat fan (hidden against the shell)
        mb.cap([b2 + c for c in range(nb)][::-1], cbot, flip=inside)
        o = mb.make(name, mat, smooth_angle=70)
        # weld the top's outer ring to the bottom ring (they coincide when e = 0)
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.05 * MM)
        bm.to_mesh(o.data); bm.free()
        if binding:
            # a bound edge: a soft bead stitched round the outline
            ring = top[3]
            r = binding
            prof = [(r * math.cos(q), r * 1.25 * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
            nrm = sh.N(aa[3], tt[3]) * sign
            b = sweep(name + '_binding', ring, nrm, prof, mat, closed_path=True, caps=False, uv_tile=(8.0, 8.0))
            self.add(b, 'binding')
        return o

    def socket(self, name, pos_mm, fwd=(0, -1, 0), up=(0, 0, 1)):
        e = bpy.data.objects.new(name, None)
        e.empty_display_size = 0.02
        z = Vector(up).normalized()
        y = Vector([-c for c in fwd]).normalized()      # (Blender -Y is forward)
        x = y.cross(z)
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = Vector(pos_mm) * MM
        e.matrix_world = M
        self.col.objects.link(e)
        self.sockets[name] = [round(c, 2) for c in pos_mm]
        return e

    # -- 2. bolts ---------------------------------------------------------------------------------------------
    def bolt(self, name, a, t, head_d=12.5, head_h=3.3, socket='hex'):
        """A retention bolt head (ACH hardware study: 0.492 in head, about 0.13 in high), domed, with a socket."""
        sh = self.sh
        r = head_d / 2
        prof = [(0.01, head_h), (r * 0.35, head_h), (r * 0.7, head_h * 0.88), (r * 0.92, head_h * 0.55),
                (r, head_h * 0.25), (r, 0.0), (0.01, 0.0)]
        o = lathe(name, prof, int(40 * self.res + 8), self.mat('bolt_steel'))
        if socket == 'hex':
            cut = lathe(name + '_cut', [(0.01, head_h + 1), (2.0, head_h + 1), (2.0, head_h - 1.6), (0.01, head_h - 2.2)], 6)
            boolean(o, cut)
        n = sh.N(a, t)
        p = sh.S(a, t, 0.2)
        place(o, p, n, sh.S(a + 1, t) - sh.S(a - 1, t))
        bake_transform(o)
        return self.add(o, 'bolt')

    # -- 3. rails ---------------------------------------------------------------------------------------------
    def build_rails(self):
        cfg = self.p.get('rails')
        if not cfg:
            return
        sh = self.sh
        for side in (1, -1):
            a = np.linspace(cfg['from'], cfg['to'], int(90 * self.res + 10))
            tc = sh.t_cut(a)
            # sit `above` mm up the surface from the rim, then smooth the path
            tr = np.array([sh.local(ai, ti, 0.0, -cfg['above'])[1] for ai, ti in zip(a, tc)])
            k = 9
            tr = np.convolve(np.pad(tr, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
            aa = a * side
            path = sh.S(aa, tr, 0.0)
            path = resample(path, len(a))
            # find (a, t) back for the resampled points (nearest of the original)
            nrm = sh.N(aa, tr)
            W, H = cfg['width'], cfg['height']
            r = 1.6
            # profile: x along the surface normal (out), y across the rail (towards the crown is +)
            g, gi = cfg.get('slot', 9.0), cfg.get('slot_depth', 3.2)
            prof = [(0.0, -W / 2), (H - r, -W / 2), (H, -W / 2 + r), (H, -g / 2 - 1.2), (H - 0.8, -g / 2),
                    (H - gi, -g / 2 - 1.4), (H - gi - 1.0, -g / 2 + 0.6), (H - gi - 1.0, g / 2 - 0.6),
                    (H - gi, g / 2 + 1.4), (H - 0.8, g / 2), (H, g / 2 + 1.2), (H, W / 2 - r), (H - r, W / 2),
                    (0.0, W / 2)]
            prof = [(x - 0.3, y) for x, y in prof][::-1 if side < 0 else 1]
            up = nrm
            Tn = np.gradient(path, axis=0)
            Tn /= np.linalg.norm(Tn, axis=1)[:, None]
            # taper the rail ends down into the shell
            s = np.ones(len(path))
            L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
            ramp = np.minimum(L, L[-1] - L)
            s_out = np.clip(ramp / 10.0, 0.25, 1.0) ** 0.6
            T, N, B = frames(path, up)
            prof_a = np.array(prof)
            P = path[:, None, :] + prof_a[None, :, 0, None] * s_out[:, None, None] * N[:, None, :] \
                + prof_a[None, :, 1, None] * B[:, None, :] * side
            per = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([prof_a, prof_a[:1]]), axis=0), axis=1))][:-1]
            UV = np.stack(np.meshgrid(per / 30.0, L / 30.0, indexing='xy'), -1)
            mb = MeshBuilder()
            base = mb.grid(P, UV, close_cols=True, flip=side < 0)
            Rn, Cn = P.shape[:2]
            ends = [list(range(base, base + Cn)), list(range(base + (Rn - 1) * Cn, base + Rn * Cn))]
            for ei, ring in enumerate(ends):
                ring = ring[::-1] if (ei == 0) != (side < 0) else ring
                mb.face(ring)
            o = mb.make(f'rail_{"L" if side > 0 else "R"}', self.mat('rail_polymer'), smooth_angle=35)
            # through-windows along the slot floor, between the screws
            Ltot = L[-1]
            cuts = []
            for sw in np.arange(14.0, Ltot - 12.0, cfg.get('window_pitch', 15.0)):
                i = int(np.searchsorted(L, sw))
                if any(abs(sw - f * Ltot) < 8.0 for f in cfg.get('screws', (0.12, 0.5, 0.88))):
                    continue
                c = superquadric('win', (8.5, g * 0.62, 12.0), (0.12, 0.12), (12, 6))
                place(c, path[i] + N[i] * (H - gi - 1.0), N[i], T[i])
                bake_transform(c)
                cuts.append(c)
            if cuts:
                for c in cuts[1:]:
                    cuts[0].data = cuts[0].data  # (joined below)
                bpy.ops.object.select_all(action='DESELECT')
                for c in cuts:
                    c.select_set(True)
                bpy.context.view_layer.objects.active = cuts[0]
                bpy.ops.object.join()
                boolean(o, cuts[0])
            bevel(o, 0.6, 2, 40)
            apply_mods(o)
            self.add(o, 'rail')
            # rail screws: in the slot floor
            for f in cfg.get('screws', (0.12, 0.5, 0.88)):
                i = int(f * (len(path) - 1))
                p = path[i] + N[i] * (H - gi - 1.0 - 0.3)
                hd = lathe('rail_screw', [(0.01, 1.6), (2.4, 1.4), (3.2, 0.7), (3.4, 0.0), (0.01, 0.0)], 24,
                           self.mat('bolt_steel'))
                cut = lathe('c', [(0.01, 3), (1.1, 3), (1.1, 0.9), (0.01, 0.5)], 6)
                boolean(hd, cut)
                place(hd, p, N[i], T[i]); bake_transform(hd)
                self.add(hd, 'rail_screw')
            # an accessory socket at the middle of each rail
            i = len(path) // 2
            self.socket(f'socket_rail_{"L" if side > 0 else "R"}', path[i] + N[i] * H, fwd=-T[i] * side, up=N[i])
            setattr(self, f'rail_path_{"L" if side > 0 else "R"}', (path, T, N, B, H))

    # -- 4. NVG shroud ----------------------------------------------------------------------------------------
    def build_shroud(self):
        cfg = self.p.get('shroud')
        if not cfg:
            return
        sh = self.sh
        t_brow = sh.t_cut(0.0)
        a0, t0 = sh.local(0.0, float(t_brow), 0.0, -(cfg['above_rim'] + cfg['plate_h'] / 2))
        a0, t0 = float(a0), float(t0)
        # the plate, conformal on the front
        plate = self.conformal_pad('shroud_plate', self.mat('shroud_metal' if cfg.get('metal', True) else 'rail_polymer'),
                                   a0, t0, cfg['plate_w'], cfg['plate_h'], cfg.get('plate_r', 9.0),
                                   cfg.get('plate_t', 3.2), 1.6)
        self.add(plate, 'shroud_plate')
        n = sh.N(a0, t0)
        p0 = sh.S(a0, t0, cfg.get('plate_t', 3.2))
        up = sh.S(a0, t0 - 0.02) - sh.S(a0, t0 + 0.02)
        # the receiver: a rounded block with the mount's socket opening
        rw, rh, rd = cfg['recv_w'], cfg['recv_h'], cfg['recv_d']
        rec = superquadric('shroud_receiver', (rw, rh, rd), (0.18, 0.22), (int(56 * self.res + 8), int(28 * self.res + 6)),
                           self.mat('shroud_metal' if cfg.get('metal', True) else 'rail_polymer'))
        rec.location = (0, 0, rd / 2 * MM - 1.0 * MM)
        bake_transform(rec)
        # one-hole socket: a rectangular pocket in the front face, plus a chamfered lead-in
        hole_w, hole_h = cfg.get('hole_w', 17.0), cfg.get('hole_h', 9.5)
        cut = superquadric('cut', (hole_w, hole_h, rd * 1.2), (0.1, 0.1), (24, 10))
        cut.location = (0, -rh * 0.12 * MM, rd * 0.95 * MM)
        bake_transform(cut)
        boolean(rec, cut)
        if cfg.get('three_hole'):
            for dx in (-13, 13):
                c = lathe('c', [(0.01, rd + 2), (2.6, rd + 2), (2.6, rd - 4), (0.01, rd - 4)], 20)
                c.location = (dx * MM, rh * 0.28 * MM, 0); bake_transform(c)
                boolean(rec, c)
        # place the receiver: local x = across (wearer's left), y = up the helmet, z = out
        xdir = np.cross(up, n)
        place(rec, p0, n, xdir)
        bake_transform(rec)
        self.add(rec, 'shroud_receiver')
        # the detent button on top
        btn = superquadric('shroud_detent', (8, 5, 6), (0.3, 0.3), (24, 12), self.mat('bolt_steel'))
        place(btn, p0 + n * (rd * 0.55) + up / np.linalg.norm(up) * (rh / 2 + 1.0), up, xdir)
        bake_transform(btn); self.add(btn, 'shroud_detent')
        # plate screws
        for dx, dv in ((-cfg['plate_w'] * 0.36, -cfg['plate_h'] * 0.2), (cfg['plate_w'] * 0.36, -cfg['plate_h'] * 0.2),
                       (0.0, cfg['plate_h'] * 0.36)):
            a1, t1 = sh.local(a0, t0, np.array(dx), np.array(dv))
            a1, t1 = float(a1), float(t1)
            hd = lathe('plate_screw', [(0.01, 1.7), (2.6, 1.5), (3.6, 0.6), (3.7, 0.0), (0.01, 0.0)], 24,
                       self.mat('bolt_steel'))
            cut = lathe('c', [(0.01, 3), (1.25, 3), (1.25, 0.9), (0.01, 0.5)], 6)
            boolean(hd, cut)
            place(hd, sh.S(a1, t1, cfg.get('plate_t', 3.2)), sh.N(a1, t1), sh.S(a1 + 1, t1) - sh.S(a1 - 1, t1))
            bake_transform(hd); self.add(hd, 'plate_screw')
        # bungee anchors: two posts on the plate's sides
        self.bungee_front = []
        if cfg.get('bungee'):
            for side in (1, -1):
                a1, t1 = sh.local(a0, t0, np.array(side * (cfg['plate_w'] / 2 + 2.0)), np.array(cfg['plate_h'] * 0.05))
                a1, t1 = float(a1), float(t1)
                post = lathe('bungee_post', [(0.01, 7.5), (3.6, 7.5), (4.2, 6.6), (2.4, 5.6), (2.4, 0.0), (0.01, 0.0)],
                             28, self.mat('shroud_metal'))
                place(post, sh.S(a1, t1, 0.2), sh.N(a1, t1), sh.S(a1 + 1, t1) - sh.S(a1 - 1, t1))
                bake_transform(post); self.add(post, 'bungee_post')
                self.bungee_front.append((side, a1, t1))
        # the NVG mount socket: in the receiver's opening, facing forward
        self.socket('socket_nvg', p0 + n * rd, fwd=n, up=up / np.linalg.norm(up))

    # -- 5. bungees -------------------------------------------------------------------------------------------
    def build_bungees(self):
        cfg = self.p.get('shroud', {})
        if not cfg.get('bungee') or not getattr(self, 'bungee_front', None):
            return
        sh = self.sh
        for side, a1, t1 in self.bungee_front:
            a_back = side * cfg.get('bungee_to', 152.0)
            t_back = float(sh.t_cut(a_back)) - 0.16
            pts = []
            for f in np.linspace(0, 1, 9):
                a = a1 + (a_back - a1) * f
                tt = t1 + (t_back - t1) * f - 0.16 * math.sin(math.pi * f) ** 1.5
                lift = 4.4 + 2.5 * math.sin(math.pi * f) * (1 if self.p.get('rails') else 0.3)
                pts.append(sh.S(a, tt, lift))
            path = catmull(pts, int(80 * self.res + 16))
            up = sh.N(*self._nearest_at(path))
            r = cfg.get('bungee_d', 4.0) / 2
            prof = [(r * math.cos(q), r * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
            o = sweep('bungee', path, up, prof, self.mat('bungee_elastic'), uv_tile=(12.0, 12.0))
            self.add(o, 'bungee')
            # the hook at the rear
            hook = superquadric('bungee_hook', (8, 11, 5), (0.35, 0.35), (24, 12), self.mat('buckle_polymer'))
            place(hook, path[-1], sh.N(a_back, t_back), path[-1] - path[-4])
            bake_transform(hook); self.add(hook, 'bungee_hook')

    def _nearest_at(self, path):
        """(a, t) of the shell points nearest a path (by a fine search), for normals."""
        sh = self.sh
        A, T = sh.grid(180, 90, t_end=1.6)
        P = sh.S(A, T).reshape(-1, 3)
        out_a, out_t = [], []
        for q in path:
            i = np.argmin(((P - q) ** 2).sum(1))
            out_a.append(A.ravel()[i]); out_t.append(T.ravel()[i])
        return np.array(out_a), np.array(out_t)

    # -- 6. loop panels and pouch -----------------------------------------------------------------------------
    def build_loop_panels(self):
        for i, pan in enumerate(self.p.get('loop_panels', [])):
            sh = self.sh
            t0 = pan['t'] if 't' in pan else float(sh.t_cut(pan['a'])) * pan['t_frac']
            sides = (1, -1) if pan.get('mirror') else (1,)
            for side in sides:
                o = self.conformal_pad(f'loop_panel_{i}', self.mat('velcro_loop'), pan['a'] * side, t0, pan['w'],
                                       pan['h'], pan.get('r', 8.0), 1.5, 1.4, rot=pan.get('rot', 0.0) * side,
                                       binding=1.0)
                self.add(o, 'loop_panel')

    def build_pouch(self):
        cfg = self.p.get('pouch')
        if not cfg:
            return
        sh = self.sh
        o = self.conformal_pad('counterweight_pouch', self.mat('pouch_fabric'), 180.0, cfg['t'], cfg['w'], cfg['h'],
                               14.0, cfg['d'] * 0.55, 9.0, base_off=1.8, dome=cfg['d'] * 0.45)
        self.add(o, 'pouch')
        # its lid seam and two rows of stitched webbing
        for k, dv in enumerate((-cfg['h'] * 0.18, cfg['h'] * 0.08, cfg['h'] * 0.3)):
            pts = []
            for u in np.linspace(-cfg['w'] * 0.46, cfg['w'] * 0.46, 24):
                a1, t1 = sh.local(180.0, cfg['t'], np.array(u), np.array(dv))
                prof_e = min(1.0, (cfg['w'] / 2 - abs(u)) / 9.0)
                hh = 1.8 + (cfg['d'] * 0.55 * math.sqrt(max(0, 1 - (1 - prof_e) ** 2))
                            + cfg['d'] * 0.45 * (1 - (abs(u) / (cfg['w'] / 2)) ** 2 * 0.9) * prof_e)
                pts.append(sh.S(float(a1), float(t1), hh + 0.4))
            path = np.array(pts)
            if k == 0:
                prof = [(0.0, -1.0), (0.9, -0.6), (0.9, 0.6), (0.0, 1.0)]   # a seam bead
                mat = self.mat('pouch_fabric')
            else:
                prof = [(0.0, -12.7), (1.3, -12.4), (1.3, 12.4), (0.0, 12.7)]   # 1 in webbing
                mat = self.mat('webbing_nylon')
            up = sh.N(*self._nearest_at(path))
            o = sweep('pouch_webbing', path, up, prof, mat, uv_tile=(25.4, 25.4))
            self.add(o, 'pouch_detail')

    # -- 7. liner pads (inside) -------------------------------------------------------------------------------
    def build_pads(self):
        cfg = self.p.get('pads')
        if not cfg:
            return
        sh = self.sh
        for pd in cfg:
            sides = (1, -1) if pd.get('mirror') else (1,)
            for side in sides:
                t0 = pd['t'] if 't' in pd else float(sh.t_cut(pd['a'] * side)) * pd['t_frac']
                o = self.conformal_pad('pad', self.mat('pad_fabric'), pd['a'] * side, t0, pd['w'], pd['h'],
                                       pd.get('r', 20.0), pd.get('thick', 19.05) * 0.7, 6.0, inside=True,
                                       dome=pd.get('thick', 19.05) * 0.3, rot=pd.get('rot', 0) * side)
                self.add(o, 'pad')

    # -- 8. retention -----------------------------------------------------------------------------------------
    def ladder_lock(self, pos, n_out, along):
        """A moulded ladder-lock: a rounded plate with two strap slots and a raised centre bar."""
        w = self.p['retention'].get('webbing_w', 19.0)
        bk = superquadric('ladder_lock', (w + 9, w * 0.95 + 8, 4.0), (0.12, 0.18), (36, 12), self.mat('buckle_polymer'))
        for dy in (-(w * 0.95 + 8) * 0.24, (w * 0.95 + 8) * 0.24):
            cut = superquadric('slot', (w + 1.0, 3.2, 8.0), (0.1, 0.1), (16, 6))
            cut.location = (0, dy * MM, 0); bake_transform(cut)
            boolean(bk, cut)
        place(bk, pos, n_out, along)
        bake_transform(bk)
        return self.add(bk, 'buckle')

    def build_retention(self):
        cfg = self.p.get('retention')
        if not cfg:
            return
        sh = self.sh
        anchors = {}
        for key in ('front', 'rear'):
            a, up_mm = cfg[key]
            for side in (1, -1):
                aa = a * side
                t = float(sh.t_at_depth(aa, float(sh.depth(aa)) - up_mm))
                anchors[(key, side)] = (aa, t)
                if cfg.get('bolts', True):
                    self.bolt('retention_bolt', aa, t)
        # webbing paths: a 4-point harness to a chin cup, with a nape strap. Pose 'hang' (on a stand, buckled,
        # hanging) or 'worn' (around a head, from the head landmarks).
        pose = self.p.get('strap_pose', cfg.get('pose', 'hang'))
        hd = cfg['worn'] if pose == 'worn' else cfg['hang']
        chin, jaw, nape = np.array(hd['chin']), np.array(hd['jaw']), np.array(hd['nape'])
        w = cfg.get('webbing_w', 19.0)
        prof = [(0.0, -w / 2), (1.3, -w / 2 + 0.3), (1.3, w / 2 - 0.3), (0.0, w / 2)]
        straps = []
        cw = hd.get('cup_w', 26.0)
        for side in (1, -1):
            af, tf = anchors[('front', side)]
            ar, tr = anchors[('rear', side)]
            pf = sh.S(af, tf, -sh.th - 1.0)
            pr = sh.S(ar, tr, -sh.th - 1.0)
            j = jaw * np.array([side, 1, 1])
            pf_out = sh.S(af, float(sh.t_cut(af)) + 0.04, -sh.th - 5.0)
            pr_out = sh.S(ar, float(sh.t_cut(ar)) + 0.04, -sh.th - 5.0)
            c_side = chin + np.array([side * cw, 4.0, 3.0])
            front = catmull([pf, pf_out, pf_out + (j - pf_out) * 0.5 + np.array([side * 3.0, 0, 0]), j,
                             j + (c_side - j) * 0.55, c_side], 48)
            rear = catmull([pr, pr_out, pr_out + (j - pr_out) * 0.5 + np.array([side * 4.0, 0, 0]), j], 36)
            straps += [front, rear]
            n_out = np.array([side, -0.25, 0.0])
            self.ladder_lock(j + n_out * 2.4, n_out, front[30] - front[22])
        cl = chin + np.array([cw, 4.0, 3.0]); cr = chin + np.array([-cw, 4.0, 3.0])
        mid = chin + np.array([0, -5.0, -3.0])
        straps.append(catmull([cl, mid, cr], 30))
        for s_ in straps:
            centre = np.array([0.0, chin[1] * 0.35, (chin[2] + 0.0) * 0.45])
            up = centre - s_                                            # webbing faces the head's centre
            up = up / np.linalg.norm(up, axis=1)[:, None]
            o = sweep('chin_strap', s_, -up, prof, self.mat('webbing_nylon'), uv_tile=(w, w), smooth=30)
            self.add(o, 'strap')
        # chin cup: a moulded, padded cup curved around the chin
        arc = []
        for q in np.linspace(-1, 1, 25):
            ang = q * math.radians(58)
            arc.append(chin + np.array([math.sin(ang) * 30.0, -math.cos(ang) * 30.0 + 30.0 - 8.0, -2.0]))
        arc = np.array(arc)
        cprof = [(x, y) for x, y in round_rect(9.0, 34.0, 4.2, 6)]
        thick = 1.0 - 0.0 * np.abs(np.linspace(-1, 1, len(arc)))
        sc = 0.55 + 0.45 * np.sqrt(np.clip(1 - np.linspace(-1, 1, len(arc)) ** 2, 0, 1))
        upc = arc - (chin + np.array([0, 22.0, 0]))
        upc[:, 2] = 0
        cup = sweep('chin_cup', arc, upc, cprof, self.mat('pad_fabric'), scale=sc, smooth=50)
        self.add(cup, 'chin_cup')
        # nape strap and pad, between the rear straps behind the head
        pl = sh.S(anchors[('rear', 1)][0], float(sh.t_cut(anchors[('rear', 1)][0])) + 0.03, -sh.th - 7.0)
        pr = sh.S(anchors[('rear', -1)][0], float(sh.t_cut(anchors[('rear', -1)][0])) + 0.03, -sh.th - 7.0)
        path = catmull([pl, nape + np.array([42.0, -8, 6]), nape, nape + np.array([-42.0, -8, 6]), pr], 44)
        up = path - (nape + np.array([0, -60.0, 0])); up[:, 2] = 0
        o = sweep('nape_strap', path, up, prof, self.mat('webbing_nylon'), uv_tile=(w, w))
        self.add(o, 'strap')
        npath = catmull([nape + np.array([40.0, -6, 5]), nape + np.array([0, 1.0, 0]), nape + np.array([-40.0, -6, 5])], 25)
        nup = npath - (nape + np.array([0, -60.0, 0])); nup[:, 2] = 0
        nsc = 0.6 + 0.4 * np.sqrt(np.clip(1 - np.linspace(-1, 1, 25) ** 2, 0, 1))
        npad = sweep('nape_pad', npath + nup / np.linalg.norm(nup, axis=1)[:, None] * -4.0, nup,
                     [(x, y) for x, y in round_rect(10.0, 36.0, 4.5, 6)], self.mat('pad_fabric'), scale=nsc, smooth=50)
        self.add(npad, 'nape_pad')

    # -- 9. headset -------------------------------------------------------------------------------------------
    def build_headset(self):
        cfg = self.p.get('headset')
        if not cfg:
            return
        sh = self.sh
        for side in (1, -1):
            ear = np.array(cfg['ear']) * np.array([side, 1, 1])
            out = np.array([side, 0.0, 0.0])
            # cup shell: a rounded, slightly tapered body
            cup = superquadric('ear_cup', (cfg['cup_d'], cfg['cup_h'], cfg['cup_w']), (0.5, 0.78),
                               (int(64 * self.res + 8), int(30 * self.res + 6)), self.mat('headset_polymer'))
            # (local: x = forward, y = up, z = out)
            place(cup, ear + out * (cfg['cup_w'] / 2 + 14.0), out, np.array([0, -1.0, 0]))
            # the cup's local frame: N=out, T=-Y (front) -> local y is up
            bake_transform(cup); self.add(cup, 'ear_cup')
            # the outer face plate: a raised oval with a parting line round it
            face = superquadric('ear_cup_face', (cfg['cup_d'] * 0.78, cfg['cup_h'] * 0.74, 10.0), (0.35, 0.8),
                                (int(56 * self.res + 8), 14), self.mat('headset_polymer'))
            place(face, ear + out * (cfg['cup_w'] + 9.5), out, np.array([0, -1.0, 0]))
            bake_transform(face); self.add(face, 'ear_cup')
            # ear seal: a soft ring against the head
            seal = superquadric('ear_seal', (cfg['cup_d'] * 0.98, cfg['cup_h'] * 0.98, 16.0), (0.6, 0.5),
                                (int(64 * self.res + 8), 16), self.mat('ear_seal_leatherette'))
            place(seal, ear + out * 9.0, out, np.array([0, -1.0, 0]))
            bake_transform(seal); self.add(seal, 'ear_seal')
            # a ribbed volume knob and a battery door outline on the outside
            # ribbed volume knob: radius modulated round its edge (14 ribs)
            th_ = np.linspace(0, 2 * np.pi, 112, endpoint=False)
            zs = np.array([0.0, 7.0, 8.2, 9.0])
            rr = 7.0 + 0.55 * np.clip(np.cos(th_ * 14) * 2.5, -1, 1)
            ring = []
            for zi, z in enumerate(zs):
                rz = rr * (1.0 if zi < 2 else (0.93 if zi == 2 else 0.8))
                ring.append(np.stack([rz * np.cos(th_), rz * np.sin(th_), np.full_like(th_, z)], -1))
            P = np.array(ring)
            mb = MeshBuilder()
            b0 = mb.grid(P, None, close_cols=True, flip=True)
            mb.cap([b0 + c for c in range(len(th_))], (0, 0, 0.0))
            mb.cap([b0 + 3 * len(th_) + c for c in range(len(th_))][::-1], (0, 0, 9.0))
            knob = mb.make('volume_knob', self.mat('buckle_polymer'), smooth_angle=40)
            place(knob, ear + out * (cfg['cup_w'] + 12.5) + np.array([0, 22.0, 18.0]), out, np.array([0, -1.0, 0]))
            bake_transform(knob); self.add(knob, 'headset_knob')
            # the rail arm: from the rail adapter down to the cup's top
            rp = getattr(self, f'rail_path_{"L" if side > 0 else "R"}', None)
            if rp is not None:
                path, T, N, B, H = rp
                i = int(len(path) * cfg.get('arm_at', 0.42))
                top = path[i] + N[i] * (H + 2.0)
                adp = superquadric('rail_adapter', (24, 16, 12), (0.2, 0.25), (28, 12), self.mat('headset_polymer'))
                place(adp, top - N[i] * 3.0, N[i], T[i])
                bake_transform(adp); self.add(adp, 'rail_adapter')
                cup_top = ear + out * (cfg['cup_w'] / 2 + 14.0) + np.array([0, 0, cfg['cup_h'] / 2 - 4.0])
                mid = (top + cup_top) / 2 + out * 6.0
                arm = catmull([top + N[i] * 2.0, mid, cup_top + np.array([0, 0, 6.0])], 30)
                prof = [(x, y) for x, y in round_rect(5.0, 12.0, 2.2, 4)]
                o = sweep('headset_arm', arm, np.broadcast_to(out, arm.shape), prof, self.mat('headset_polymer'))
                self.add(o, 'headset_arm')
            # the mic boom on the left side
            if side == cfg.get('mic_side', 1):
                base = ear + out * (cfg['cup_w'] / 2 + 14.0) + np.array([0, -cfg['cup_d'] * 0.38, -cfg['cup_h'] * 0.15])
                mouth = np.array(cfg['mouth'])
                boom = catmull([base, base + np.array([-side * 2.0, -40.0, -22.0]),
                                mouth + np.array([side * 32.0, 0.0, 6.0]), mouth + np.array([side * 12.0, 0, 0])], 40)
                r = 2.1
                prof = [(r * math.cos(q), r * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
                o = sweep('mic_boom', boom, np.broadcast_to(np.array([0, 0, 1.0]), boom.shape), prof,
                          self.mat('headset_polymer'))
                self.add(o, 'mic_boom')
                foam = superquadric('mic_foam', (24, 14, 15), (0.8, 0.8), (24, 14), self.mat('mic_foam'))
                place(foam, mouth + np.array([side * 8.0, 0, 0]), np.array([side, 0, 0]), np.array([0, -1.0, 0]))
                bake_transform(foam); self.add(foam, 'mic_foam')
                pivot = superquadric('boom_pivot', (16, 16, 9), (0.5, 1.0), (28, 10), self.mat('headset_polymer'))
                place(pivot, base + out * 3.0, out, np.array([0, -1.0, 0]))
                bake_transform(pivot); self.add(pivot, 'boom_pivot')

    # -- 10. cover --------------------------------------------------------------------------------------------
    def build_cover(self):
        cfg = self.p.get('cover')
        if not cfg:
            return
        sh = self.sh
        na, nt = int(240 * self.res), int(80 * self.res)
        A, T = sh.grid(na, nt)
        gap = cfg.get('gap', 2.0)
        rng = np.random.default_rng(cfg.get('seed', 5))
        # wrinkles: gathered folds near the rim (meridional), soft creases on the dome
        fold = np.zeros_like(A)
        depth_frac = T / T[-1][None, :]
        for k in range(10):
            freq = rng.integers(14, 34)
            ph = rng.uniform(0, 2 * np.pi)
            amp = rng.uniform(0.35, 0.9)
            fold += amp * np.sin(np.radians(A) * freq + ph + 2.2 * np.sin(depth_frac * 3 + k)) \
                * smoothstep(0.55, 1.0, depth_frac) ** 1.5
        for k in range(6):
            f1, f2 = rng.integers(3, 8), rng.uniform(4, 9)
            fold += 0.35 * np.sin(np.radians(A) * f1 + depth_frac * f2 + rng.uniform(0, 6)) * smoothstep(0.1, 0.6, depth_frac)
        off = gap + 0.8 + np.clip(fold, -0.9, None) * cfg.get('wrinkle', 1.0)
        O = sh.S(A, T, off)
        # over the rim and tucked inside (the edge trim is under it)
        tc = T[-1]
        a = A[-1]
        Nr = sh.N(a, tc)
        D = sh.dS_dt(a, tc)
        D = D - (D * Nr).sum(-1, keepdims=True) * Nr
        D /= np.linalg.norm(D, axis=-1, keepdims=True)
        w = self.p.get('trim_thickness', 1.8)
        Rr = sh.th / 2 + w + gap
        C = sh.S(a, tc) - Nr * sh.th / 2 + D * 1.2
        wrap = [C + Rr * (Nr * math.cos(q) + D * math.sin(q)) for q in np.linspace(0.25, math.pi - 0.15, 9)]
        tuck = []
        for s in (6.0, 13.0, cfg.get('tuck', 20.0)):
            tt = np.array([sh.local(ai, ti, 0.0, -s)[1] for ai, ti in zip(a, tc)])
            tuck.append(sh.S(a, tt, -sh.th - w - gap * 0.6 - 0.5 * math.exp(-s / 8)))
        rows = np.concatenate([O, np.array(wrap), np.array(tuck)], 0)
        # sewn from gores: each gore is mapped flat (around = arc length at that height, down = arc length
        # from the crown), so the pattern keeps its scale everywhere; seams fall between gores
        ng = cfg.get('gores', 4)
        g0 = cfg.get('gore_offset', 45.0)
        tl = tile(self.mat('cover_fabric'))
        seg = np.linalg.norm(np.diff(rows, axis=0), axis=-1)
        vdown = np.r_[np.zeros((1, na)), np.cumsum(seg, axis=0)]
        rho = np.linalg.norm(rows[..., :2], axis=-1)                   # (horizontal radius, mm)
        Rr, Cc = rows.shape[:2]
        mb = MeshBuilder()
        base = mb.add_vs(rows[1:])
        R1 = Rr - 1
        idx = lambda r, c: base + (r - 1) * Cc + (c % Cc)
        def uv_for(r, c, gc):
            ac = A[0, c % Cc] if c < Cc else A[0, 0] + 360.0
            da = ((ac - gc + 180.0) % 360.0) - 180.0
            return (math.radians(da) * rho[r, c % Cc] / tl + gc / 97.0, vdown[r, c % Cc] / tl)
        for c in range(Cc):
            ac = (A[0, c] + 180.0 / Cc) % 360.0
            gi = int(((ac - g0) % 360.0) // (360.0 / ng))
            gc = g0 + (gi + 0.5) * 360.0 / ng
            for r in range(1, Rr - 1):
                cs = [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]
                mb.face([idx(*q) for q in cs], [uv_for(*q, gc) for q in cs])
            # crown fan
            ctr = mb.add_v(rows[0, 0]) if c == 0 else ctr
            mb.face([ctr, idx(1, c + 1), idx(1, c)][::-1][::-1], [uv_for(0, c, gc), uv_for(1, c + 1, gc), uv_for(1, c, gc)])
        o = mb.make('cover', self.mat('cover_fabric'), smooth_angle=85)
        m = o.modifiers.new('cloth_thickness', 'SOLIDIFY')
        m.thickness = 0.9 * MM
        m.offset = 1.0
        apply_mods(o)
        self.add(o, 'cover')
        for gi in range(ng):
            ag = g0 + gi * 360.0 / ng
            ts = np.linspace(0.03, float(sh.t_cut(ag)) - 0.015, 50)
            pth = sh.S(np.full_like(ts, ag), ts, gap + 1.75)
            r = 0.8
            prof = [(r * math.cos(q), r * 1.7 * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
            ob = sweep('cover_seam', pth, sh.N(np.full_like(ts, ag), ts), prof, self.mat('cover_fabric'), uv_tile=(8.0, 8.0))
            self.add(ob, 'cover')
        # hem seam bead just above the rim, and the drawcord channel inside
        for frac, r in ((0.0, 0.9),):
            tt = tc - 0.012
            path = sh.S(a, tt, gap + 1.8)
            path = np.vstack([path, path[:1]])
            prof = [(r * math.cos(q), r * math.sin(q) * 1.6) for q in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
            ob = sweep('cover_hem', path[:-1], sh.N(a, tt), prof, self.mat('cover_fabric'), closed_path=True,
                       caps=False)
            self.add(ob, 'cover')

    # -- 11. front mount plate (6B47 style) -------------------------------------------------------------------
    def build_front_plate(self):
        cfg = self.p.get('front_plate')
        if not cfg:
            return
        sh = self.sh
        t_brow = float(sh.t_cut(0.0))
        a0, t0 = sh.local(0.0, t_brow, 0.0, -(cfg['above_rim'] + cfg['h'] / 2))
        a0, t0 = float(a0), float(t0)
        base_off = (self.p['cover'].get('gap', 2.0) + 1.8) if self.p.get('cover') else 0.0
        plate = self.conformal_pad('mount_plate', self.mat('shroud_metal'), a0, t0, cfg['w'], cfg['h'],
                                   cfg.get('r', 10.0), 3.0, 1.3, base_off=base_off)
        self.add(plate, 'mount_plate')
        n = sh.N(a0, t0)
        up = sh.S(a0, t0 - 0.02) - sh.S(a0, t0 + 0.02)
        up /= np.linalg.norm(up)
        xdir = np.cross(up, n)
        p0 = sh.S(a0, t0, base_off + 3.0)
        # a raised dovetail boss in the middle
        boss = superquadric('mount_boss', (cfg['boss_w'], cfg['boss_h'], cfg['boss_d']), (0.15, 0.2), (40, 16),
                            self.mat('shroud_metal'))
        boss.location = (0, 0, cfg['boss_d'] / 2 * MM - 0.6 * MM)
        bake_transform(boss)
        cut = superquadric('cut', (cfg['boss_w'] * 0.55, cfg['boss_h'] * 1.4, cfg['boss_d'] * 0.6), (0.1, 0.1), (16, 8))
        cut.location = (0, 0, cfg['boss_d'] * MM)
        bake_transform(cut)
        boolean(boss, cut)
        place(boss, p0, n, xdir); bake_transform(boss); self.add(boss, 'mount_boss')
        for dx, dv in ((-cfg['w'] * 0.38, cfg['h'] * 0.1), (cfg['w'] * 0.38, cfg['h'] * 0.1), (0.0, -cfg['h'] * 0.34)):
            a1, t1 = sh.local(a0, t0, np.array(dx), np.array(-dv))
            a1, t1 = float(a1), float(t1)
            hd = lathe('plate_screw', [(0.01, 2.2), (3.0, 2.0), (4.4, 0.8), (4.6, 0.0), (0.01, 0.0)], 28,
                       self.mat('bolt_steel'))
            cut = lathe('c', [(0.01, 3), (0.9, 3), (0.9, 1.0), (0.01, 0.8)], 12)
            cut2 = superquadric('slot', (8.0, 1.2, 3.0), (0.1, 0.1), (8, 4)); cut2.location = (0, 0, 2.4 * MM)
            bake_transform(cut2)
            boolean(hd, cut2)
            place(hd, sh.S(a1, t1, base_off + 3.0), sh.N(a1, t1), sh.S(a1 + 1, t1) - sh.S(a1 - 1, t1))
            bake_transform(hd); self.add(hd, 'plate_screw')
        self.socket('socket_nvg', p0 + n * cfg['boss_d'], fwd=n, up=up)

    # -- 12. strobe / IR marker --------------------------------------------------------------------------------
    def build_marker(self):
        cfg = self.p.get('marker')
        if not cfg:
            return
        sh = self.sh
        a0, t0 = cfg['a'], cfg['t']
        n = sh.N(a0, t0)
        p = sh.S(a0, t0, 1.6 + 0.5)
        body = superquadric('ir_marker', (34, 26, 15), (0.25, 0.3), (40, 16), self.mat('headset_polymer'))
        place(body, p + n * 7.5, n, sh.S(a0 + 1, t0) - sh.S(a0 - 1, t0))
        bake_transform(body); self.add(body, 'marker')
        lens = superquadric('ir_marker_lens', (16, 16, 6), (0.6, 1.0), (28, 10), self.mat('buckle_polymer'))
        place(lens, p + n * 15.0, n, sh.S(a0 + 1, t0) - sh.S(a0 - 1, t0))
        bake_transform(lens); self.add(lens, 'marker')

    # -- build -----------------------------------------------------------------------------------------------
    def build(self):
        self.build_shell()
        self.build_edge_trim() if not self.p.get('no_trim') else None
        self.build_rails()
        self.build_loop_panels()
        self.build_shroud()
        self.build_bungees()
        self.build_pouch()
        self.build_cover()
        self.build_front_plate()
        self.build_marker()
        self.build_pads()
        self.build_retention()
        self.build_headset()
        top = np.array([0, 0, 0.0])
        self.socket('socket_head_top', top)
        return self


# =================================================================================================================
# random family
# =================================================================================================================

def random_preset(seed, base_presets):
    """A new helmet drawn from the ranges the three presets span: mixes their cut, curvature, paint and kit."""
    rnd = random.Random(seed)
    base = json.loads(json.dumps(rnd.choice(base_presets)))
    other = rnd.choice(base_presets)
    p = base
    p['id'] = f'helmet_rand_{seed}'
    p['name'] = f'Random helmet #{seed}'
    s = p['shell']
    o = other['shell']
    mix = rnd.random()
    for k in ('plan_n', 'dome_m', 'egg', 'front_taper', 'crown_back', 'flare'):
        s[k] = s[k] * (1 - mix) + o[k] * mix
    size = rnd.choice(['M', 'L', 'L', 'XL'])
    scale = {'M': 0.975, 'L': 1.0, 'XL': 1.04}[size]
    s['length'] *= scale; s['width'] *= scale
    p['size'] = size
    cut_choice = rnd.choice(['high', 'high', 'mid'])
    if cut_choice == 'high':
        src = next(b for b in base_presets if b['shell'].get('cut_kind') == 'high')
    else:
        src = next(b for b in base_presets if b['shell'].get('cut_kind') == 'mid')
    s['cut'] = [[a, d * scale] for a, d in src['shell']['cut']]
    paints = ['#6f6450', '#7a6d55', '#4b4f3e', '#3d4134', '#26282a', '#8a7b5f', '#55594a']
    p['colours']['shell'] = rnd.choice(paints)
    p['colours']['loop'] = rnd.choice([p['colours']['shell'], '#6f6450', '#3d4134', '#262626'])
    p['colours']['rails'] = rnd.choice([p['colours']['shell'], '#2a2b2a', '#4b4f3e'])
    if cut_choice == 'mid' and rnd.random() < 0.6:
        p['cover'] = {'seed': rnd.randint(1, 9999), 'gap': 2.0, 'wrinkle': rnd.uniform(0.7, 1.3),
                      'colours': rnd.choice([['#575d47', '#3d462d', '#3f3227', '#1b1b18'],
                                             ['#77705a', '#5a5340', '#3f3a2c', '#1f1d18'],
                                             ['#5a6458', '#3f4a3c', '#2f362b', '#1a1d19']])}
    else:
        p.pop('cover', None)
    if p.get('cover'):
        p.pop('rails', None); p.pop('loop_panels', None); p.pop('shroud', None); p.pop('headset', None)
        p.pop('pouch', None)
        p['front_plate'] = next((b['front_plate'] for b in base_presets if b.get('front_plate')), None)
    else:
        p.pop('front_plate', None)
        donor = next(b for b in base_presets if b.get('rails'))
        for k in ('rails', 'shroud', 'loop_panels'):
            p[k] = json.loads(json.dumps(donor[k]))
        p['shroud']['three_hole'] = rnd.random() < 0.4
        p['shroud']['bungee'] = rnd.random() < 0.8
        if rnd.random() < 0.5:
            p['headset'] = json.loads(json.dumps(next(b['headset'] for b in base_presets if b.get('headset'))))
        else:
            p.pop('headset', None)
        if rnd.random() < 0.5:
            p['pouch'] = json.loads(json.dumps(next(b['pouch'] for b in base_presets if b.get('pouch'))))
        else:
            p.pop('pouch', None)
    return p
