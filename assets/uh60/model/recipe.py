"""Numbers for the UH-60A/L recipe and the build context.

Source tags used in comments (full citations in ../notes/SOURCES.md):
  [F2-2]  TM 1-1520-237-10 figure 2-2, Principal Dimensions (dimensioned)
  [F2-3]  figure 2-3, Turning Radius and Clearance (dimensioned)
  [F6-1]  figure 6-1, Helicopter Compartment and Station Diagram (vector drawing with STA / BL / WL scales;
          0.5775 pt per inch, read with tools/gridview.py; reading accuracy about +-1.5 in)
  [F6-9]  figure 6-9, Cabin Dimensions (dimensioned)
  [TM]    a number stated in the manual's text
  [PUB]   a widely published figure for the type (named in SOURCES.md)
  [INF]   inferred: not in a source; chosen to look and fit right
"""
import bpy, math, os
import numpy as np
import lib
from lib import IN, Mesh

# ------------------------------------------------------------------ datums
STA_MAST = 341.2            # [F6-1] main rotor centre line
WL_HUB = 315.0              # [F6-1] main rotor hub
WL_GROUND = 183.7           # [F6-1] static ground line, measured on the drawing's WL scale
WL_CABIN_FLOOR = 206.75     # [F6-9]
WL_COCKPIT_FLOOR = 215.0    # [F6-1]
WL_CABIN_CEIL = 261.0       # [F6-9]
STA_CABIN = (247.0, 398.0)  # [F6-9] cabin compartment, 151 in long
STA_NOSE = 162.0            # [F6-1]
STA_FOLD = 645.0            # [F6-1] tail pylon fold hinge line (tailcone end)
STA_TR, WL_TR, BL_TR = 732.0, 324.7, -14.0   # [F6-1] tail rotor centre; it sits on the right side (BL from top view)
TR_CANT = 20.0              # [F2-2] tail rotor canted 20 deg
MAST_TILT = 3.0             # [PUB] main rotor shaft tilted 3 deg forward
R_MAIN = 322.0              # [F2-2] 53 ft 8 in diameter
R_TAIL = 66.0               # [F2-2] 11 ft diameter
CHORD_MAIN = 20.76          # [PUB] 1.73 ft
CHORD_TAIL = 9.72           # [PUB] 0.81 ft
STA_MAIN_GEAR = 296.6       # [F2-2] wheel base 29 ft ahead of the tail wheel
STA_TAIL_GEAR = 644.6       # [F6-1]
BL_MAIN_GEAR = 53.3         # [F2-2] tread 8 ft 10.6 in
WL_AXLE = 196.5             # [F6-1] main wheel centre (26 x 10.0-11 tyre, 12.8 in static radius)
HALF_WIDTH = 46.5           # [F2-2] fuselage width 7 ft 9 in
STAB_HALF_SPAN = 86.0       # [F2-2] stabilator width 14 ft 4 in

# ------------------------------------------------------------------ fuselage body (nose to fold hinge), read off [F6-1]
# STA: (WL bottom, WL top, half width, n_lower, n_upper)   n = superellipse exponent of the cross-section
# The cabin section agrees with [F6-9]: inside 72 in at the floor, 85 in at WL 234, 69 in at the ceiling, plus 4 in walls.
BODY = [
    (162.0, 220.0, 220.0, 0.0, 2.2, 2.2),
    (165.0, 212.0, 228.0, 12.0, 2.2, 2.2),
    (170.0, 208.0, 233.0, 21.0, 2.2, 2.2),
    (175.0, 206.0, 235.5, 27.0, 2.3, 2.2),
    (180.0, 204.5, 237.5, 31.5, 2.4, 2.2),
    (190.0, 203.0, 241.0, 36.5, 2.6, 2.3),
    (193.0, 202.7, 243.0, 37.5, 2.7, 2.4),
    (200.0, 202.0, 250.5, 40.0, 2.9, 2.6),
    (210.0, 201.5, 261.5, 42.5, 3.2, 2.9),
    (218.0, 201.2, 270.0, 44.0, 3.4, 3.2),
    (226.0, 201.0, 271.3, 45.2, 3.6, 3.5),
    (240.0, 200.5, 271.0, 46.5, 3.8, 3.8),
    (260.0, 200.2, 269.5, 46.5, 3.8, 3.9),
    (300.0, 200.0, 267.0, 46.5, 3.8, 3.9),
    (345.0, 199.8, 266.0, 46.5, 3.8, 3.9),
    (366.0, 199.5, 265.5, 46.5, 3.8, 3.9),
    (400.0, 200.0, 264.0, 46.5, 3.8, 3.9),
    (430.0, 200.8, 263.0, 44.0, 3.6, 3.6),
    (448.0, 201.3, 262.0, 39.0, 3.3, 3.3),
    (470.0, 202.2, 260.5, 31.0, 3.0, 3.0),
    (488.0, 203.0, 257.0, 22.5, 2.8, 2.8),
    (504.0, 203.8, 253.0, 19.5, 2.7, 2.7),
    (560.0, 206.2, 247.7, 15.0, 2.6, 2.6),
    (600.0, 208.0, 244.0, 12.5, 2.6, 2.6),
    (645.0, 213.0, 240.0, 9.5, 2.6, 2.6),
]
_b = np.array(BODY)
_u = np.sqrt(_b[:, 0] - STA_NOSE)            # interpolate in sqrt(distance from the nose): gives a round, blunt nose
body_zb, body_zt, body_w, body_nl, body_nu = (lib.pchip(_u, _b[:, k]) for k in range(1, 6))


def body_params(s):
    u = np.sqrt(np.maximum(np.asarray(s, float) - STA_NOSE, 0.0))
    return body_zb(u), body_zt(u), body_w(u), body_nl(u), body_nu(u)


def body_zw(s):
    """Water line of maximum width: WL 234 through the cabin [F6-9], mid-height at the nose and on the tailcone."""
    zb, zt, w, nl, nu = body_params(s)
    mid = 0.5 * (zb + zt)
    k = np.clip((np.asarray(s, float) - 200.0) / 40.0, 0, 1) * np.clip((500.0 - np.asarray(s, float)) / 60.0, 0, 1)
    return mid * (1 - k) + 234.0 * k


def body_half(s, n=400):
    """Left half of the body cross-section at station s as (BL, WL) points, bottom centre to top centre."""
    zb, zt, w, nl, nu = (float(v) for v in body_params(s)); zw = float(body_zw(s))
    a = np.linspace(-np.pi / 2, np.pi / 2, n)
    c, sn = np.cos(a), np.sin(a)
    ex = np.where(a < 0, 2 / nl, 2 / nu)
    x = w * np.abs(c) ** ex
    z = np.where(a < 0, zw - (zw - zb) * np.abs(sn) ** (2 / nl), zw + (zt - zw) * np.abs(sn) ** (2 / nu))
    return np.stack([x, z], axis=1)


def body_ring(s, m):
    """Closed ring of m points (m even): bottom centre, up the left side, top centre, down the right side."""
    h = lib.resample(body_half(s), m // 2 + 1)
    left = h[:-1]; right = h[:0:-1] * np.array([-1, 1])
    p = np.vstack([left, right])
    return np.stack([np.full(len(p), s), p[:, 0], p[:, 1]], axis=1)


def body_surface_bl(s, wl):
    """Half width of the body skin at station s and water line wl (vectorised over wl)."""
    h = body_half(s, 600)
    i = int(np.argmax(h[:, 0]))
    wl = np.asarray(wl, float)
    lo = np.interp(wl, h[: i + 1, 1], h[: i + 1, 0]); up = np.interp(wl, h[i:, 1], h[i:, 0])
    return np.where(wl < h[i, 1], lo, up)


def body_stations(ds):
    s = [STA_NOSE + 0.12]
    while s[-1] < STA_FOLD:
        s.append(min(STA_FOLD, s[-1] + float(np.clip(0.22 * (s[-1] - STA_NOSE) + 0.15, 0.15, ds))))
    return np.array(s)


# ------------------------------------------------------------------ upper deck (pylon fairing, transmission cowl, APU bay) [F6-1]
# STA: (WL top, half width). Sits on the cabin roof; plan shape from the top view, height from the side view.
DECK = [
    (242.0, 271.5, 0.0), (246.0, 274.0, 7.5), (250.0, 276.0, 10.8), (260.0, 281.0, 17.0), (280.0, 286.0, 25.0),
    (300.0, 289.5, 30.0), (316.0, 291.5, 32.0), (340.0, 294.0, 31.0), (360.0, 294.5, 30.0), (400.0, 291.5, 30.0),
    (420.0, 289.5, 31.0), (448.0, 283.5, 33.0), (470.0, 274.5, 27.5), (488.0, 268.5, 19.5), (504.0, 264.0, 9.0),
]
SHAFT_COVER = [(498.0, 264.5, 6.0), (525.0, 261.0, 3.6), (643.0, 246.3, 3.4)]   # tail drive shaft cover on the tailcone

# ------------------------------------------------------------------ tail pylon planform in the side view [F6-1]: WL -> (STA lead, STA trail, half thickness)
PYLON = [
    (214.0, 645.0, 652.0, 8.6), (219.0, 644.3, 690.0, 8.8), (224.0, 643.6, 711.0, 8.8), (229.0, 643.0, 713.5, 8.6),
    (240.0, 641.5, 712.5, 8.2), (243.0, 641.0, 716.0, 8.0), (247.0, 652.0, 722.0, 7.6), (256.0, 661.5, 730.0, 7.2),
    (268.0, 674.0, 739.0, 6.6), (290.0, 696.5, 741.0, 5.8), (305.0, 712.0, 752.5, 5.4), (311.0, 718.0, 757.0, 5.3),
    (318.0, 722.0, 759.5, 5.6), (325.0, 724.0, 757.0, 5.2), (331.0, 731.0, 746.0, 3.0),
]
# stabilator [F6-1 top view]: BL -> (STA lead, STA trail); symmetric airfoil, pivot near 30 percent chord
STAB = [(0.0, 696.0, 745.0), (8.0, 698.5, 744.0), (83.0, 705.0, 731.5), (86.0, 708.0, 729.5)]
WL_STAB = 240.5

# ------------------------------------------------------------------ openings, [F6-1] unless noted
# Side-view outlines are (STA, WL) polygons, cut straight through one side; corner radius r in inches.
SHELL_T = 3.0                                                            # [INF] structural shell depth (frames + skin)
CABIN_DOOR = dict(poly=[(308.0, 207.5), (376.0, 207.5), (376.0, 261.5), (308.0, 261.5)], r=5.0)   # 68 x 54 in [F6-9]
DOOR_WINDOWS = [dict(poly=[(316.5, 233.0), (340.5, 233.0), (340.5, 256.0), (316.5, 256.0)], r=3.5),
                dict(poly=[(346.5, 233.0), (371.0, 233.0), (371.0, 256.0), (346.5, 256.0)], r=3.5)]
GUNNER_WIN = dict(poly=[(257.5, 233.0), (296.5, 233.0), (296.5, 261.0), (257.5, 261.0)], r=3.5)
COCKPIT_DOOR = dict(poly=[(207.5, 204.8), (246.0, 204.8), (246.0, 263.5), (227.5, 263.5), (207.5, 233.0)], r=2.0)
COCKPIT_DOOR_WIN = dict(poly=[(213.5, 234.5), (243.0, 234.5), (243.0, 260.5), (229.5, 260.5)], r=3.0)
CHIN_WIN = dict(poly=[(176.0, 222.0), (177.5, 229.5), (181.0, 233.5), (188.0, 235.3), (206.0, 235.6), (207.5, 233.0),
                      (207.5, 211.5), (205.5, 208.8), (198.0, 210.6), (190.0, 214.0), (182.0, 218.6)], r=1.5)
# Front-view outlines are (BL, WL) polygons, cut along the station axis between two stations [F2-2 front view, F6-1 top view]
WINDSHIELD = dict(poly=[(8.0, 246.5), (38.5, 244.0), (36.0, 262.0), (30.0, 268.5), (8.0, 269.0)], r=3.0, sta=(186.0, 219.5))
WINDSHIELD_CTR = dict(poly=[(-5.6, 247.0), (5.6, 247.0), (5.6, 269.0), (-5.6, 269.0)], r=2.0, sta=(186.0, 219.5))
# Top-view outline (STA, BL), cut down through the roof
EYEBROW_WIN = dict(poly=[(222.0, 6.0), (241.0, 6.0), (241.0, 29.5), (232.0, 30.5), (224.0, 22.0)], r=2.5, wl=(262.0, 280.0))

# flight instruments on each pilot's side of the panel [F2-9]: (BL offset from the seat centre line, height up the panel
# face, case radius) for airspeed, vertical situation indicator, altimeter, radar altimeter, HSI, vertical speed, clock,
# standby attitude
FLIGHT_GAUGES = ((-6.2, 11.0, 1.7), (0.0, 10.6, 2.45), (6.2, 11.0, 1.7), (-6.2, 5.0, 1.7), (0.0, 4.3, 2.45), (6.2, 5.0, 1.7),
                 (-9.6, 8.0, 1.0), (9.6, 8.0, 1.0))

# ------------------------------------------------------------------ build context
class Context:
    def __init__(self, lod, fast, log, here):
        self.lod = lod; self.fast = fast; self.log = log; self.here = here
        self.nodes = {}          # name -> dict(parent, pivot (sta, bl, wl), rot (3x3 in aircraft frame), objs, clips)
        self.mats = {}
        self.sockets = {}
        self.shared = {}
        self.node('airframe')

    # geometry density helpers
    def n(self, hi, lo=None):
        return hi if self.lod == 0 else (lo if lo is not None else max(6, int(hi * 0.6)))

    def node(self, name, parent=None, pivot=(STA_MAST, 0.0, WL_GROUND), rot=None):
        self.nodes[name] = dict(parent=parent, pivot=np.array(pivot, float), rot=np.eye(3) if rot is None else np.asarray(rot, float),
                                objs=[], clips=[])
        return name

    def part(self, node, name, mesh, mat, smooth=40.0):
        """mesh: lib.Mesh in inches, or an existing Blender object (already in world metres)."""
        if isinstance(mesh, Mesh):
            if mesh.n == 0:
                return None
            o = lib.obj(name, mesh, self.mats[mat], smooth)
        else:
            o = mesh
            if mat is not None:
                o.data.materials.clear(); o.data.materials.append(self.mats[mat])
                o.data.polygons.foreach_set('material_index', [0] * len(o.data.polygons))
            if smooth is not None:
                lib.shade(o, smooth)
        tile = getattr(self, 'box_uv', {}).get(mat)
        if tile:
            import detail; detail.box_uv(o, tile)
        o['uh60_part'] = name
        self.nodes[node]['objs'].append(o)
        return o

    def clip(self, node, name, frames):
        """frames: list of (frame, dloc (sta, bl, wl) inches or None, rot (axis 'x'|'y'|'z' of the node, degrees) or None)."""
        self.nodes[node]['clips'].append((name, frames))

    def socket(self, name, p, node='airframe'):
        self.sockets[name] = (node, np.array(p, float))

    def assemble(self):
        from mathutils import Matrix, Vector
        sc = bpy.context.scene
        empties = {}; tris = 0; parts = 0
        for name, nd in self.nodes.items():
            e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
            Rw = np.eye(4)
            # aircraft (sta, bl, wl) axes -> Blender (x = bl, y = sta, z = wl)
            A = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1.0]])
            Rw[:3, :3] = A @ nd['rot'] @ A.T
            Rw[:3, 3] = lib.to_world(nd['pivot'])[0]
            e.matrix_world = Matrix(Rw.tolist())
            empties[name] = e
        bpy.context.view_layer.update()
        for name, nd in self.nodes.items():
            e = empties[name]
            if nd['parent']:
                mw = e.matrix_world.copy(); e.parent = empties[nd['parent']]; e.matrix_world = mw
        bpy.context.view_layer.update()
        for name, nd in self.nodes.items():
            e = empties[name]
            objs = [o for o in nd['objs'] if o is not None and o.name in bpy.data.objects]
            parts += len(objs)
            if objs:
                for o in objs:
                    for m in list(o.modifiers):
                        lib.apply_mod(o, m)
                j = lib.join(objs, name + '_mesh')
                inv = e.matrix_world.inverted()
                j.data.transform(inv @ j.matrix_world); j.matrix_world = e.matrix_world.copy()
                j.parent = e; j.matrix_parent_inverse = Matrix.Identity(4)
                j.matrix_world = e.matrix_world.copy()
                j.data.update(); j.data.calc_loop_triangles(); tris += len(j.data.loop_triangles)
            if objs and nd.get('morph'):
                kname, fn = nd['morph']
                j.shape_key_add(name='Basis'); sk = j.shape_key_add(name=kname)
                co = np.zeros(len(j.data.vertices) * 3); j.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
                # node-local Blender axes are (bl, sta, wl) of the node frame: hand the function (radial, lead, up)
                loc = co[:, [1, 0, 2]]; d = fn(loc)
                sk.data.foreach_set('co', (co + d[:, [1, 0, 2]]).ravel()); sk.value = 0.0
            for cname, frames in nd['clips']:
                axes = [f[2][0] for f in frames if f[2] is not None]
                mw = e.matrix_world.copy()
                e.rotation_mode = {'x': 'XYZ', 'y': 'YXZ', 'z': 'ZYX'}[axes[0]] if axes else 'XYZ'
                e.matrix_world = mw; bpy.context.view_layer.update()
                base_loc = e.location.copy(); base_rot = e.rotation_euler.copy()
                e.animation_data_create()
                act = bpy.data.actions.new(f'{cname}__{name}')
                e.animation_data.action = act
                for fr, dloc, rot in frames:
                    if dloc is not None:
                        d = Vector((dloc[1] * IN, dloc[0] * IN, dloc[2] * IN))
                        if e.parent:
                            d = e.parent.matrix_world.to_3x3().inverted() @ d
                        e.location = base_loc + d
                        e.keyframe_insert('location', frame=fr)
                    if rot is not None:
                        ax, deg = rot
                        r = base_rot.copy(); setattr(r, ax, getattr(r, ax) + math.radians(deg)); e.rotation_euler = r
                        e.keyframe_insert('rotation_euler', frame=fr)
                e.location = base_loc; e.rotation_euler = base_rot
                try:
                    for fc in _fcurves(act):
                        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR' if cname.endswith('_spin') else 'BEZIER'
                except Exception:
                    pass
                tr = e.animation_data.nla_tracks.new(); tr.name = cname
                tr.strips.new(cname, int(frames[0][0]), act)
                e.animation_data.action = None
        for sname, (node, p) in self.sockets.items():
            s = bpy.data.objects.new(sname, None); sc.collection.objects.link(s)
            s.matrix_world = Matrix.Translation(Vector(lib.to_world(p)[0].tolist()))
            bpy.context.view_layer.update()
            mw = s.matrix_world.copy(); s.parent = empties[node]; s.matrix_world = mw
        return dict(lod=self.lod, tris=tris, parts=parts, nodes=list(self.nodes), sockets=list(self.sockets))


def _fcurves(act):
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, 'layers', []):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', []):
                out.extend(bag.fcurves)
    return out
