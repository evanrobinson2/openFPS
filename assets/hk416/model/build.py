"""HK416 D14.5RS, first-person hero weapon. Rebuilds everything from nothing:

    blender -b --python build.py                 # LOD0 + LOD1, baked 2048 px textures  (the deliverable)
    blender -b --python build.py -- --fast       # LOD0 only, flat materials, no bake    (silhouette iteration)
    blender -b --python build.py -- --lod 1      # one LOD only

Frame (mm while modelling): L along the bore, + toward the muzzle, L = 0 at the upper receiver's front face;
S lateral, + = the rifle's left side; Z up, Z = 0 on the bore axis.
Blender / export frame (metres, Z up, the weapon's front faces -Y as MODELER.md asks): X = S, Y = -L, Z = Z.
Every outline traced from refs-local/profile-right-photo.png (notes/REFERENCES.md) is written in that photo's pixel coordinates and converted
with LX / ZY below, so each number in P can be checked against the image (see NOTES.md for the ruler).
"""
import bpy, bmesh, math, json, os, sys, time
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in ARGV
LODS = [int(ARGV[ARGV.index('--lod') + 1])] if '--lod' in ARGV else ([0] if FAST else [0, 1])
MM = 0.001
LOD = 0

# ------------------------------------------------------------------ the ruler (see NOTES.md)
PX_PER_MM = 0.897          # 32 rail pitches (10.0 mm each) span 287 px in profile-right-photo.png
K = 1.0 / PX_PER_MM        # mm per photo pixel
X0, Y0 = 372.0, 69.0       # photo pixel of L = 0 (upper receiver front face) and of the bore axis
def LX(x): return (x - X0) * K
def ZY(y): return (Y0 - y) * K
def PX(pts): return [(LX(x), ZY(y)) for x, y in pts]

# ------------------------------------------------------------------ shape numbers
P = dict(
    # scale
    barrel_len=14.5 * 25.4, barrel_breech=-5.0, rail_pitch=10.0, rail_lug=4.77,
    # rails (photo: lug tops y=36, slot floors y=39.2, bottom lugs y=97, bottom floors y=93.8)
    rail_top=ZY(36.0), rail_floor=ZY(39.2), rail_bot=ZY(97.0), rail_bot_floor=ZY(93.8),
    rail_half_top=7.8, rail_half=10.6, rail_flank=2.8,
    upper_lug0=LX(272.0), hg_lug0=LX(388.5), n_upper_lugs=10, n_hg_lugs=19,
    # handguard
    hg_l0=0.0, hg_l1=LX(577.0), hg_side=26.4, hg_side_lug=30.0, hg_side_zc=0.5, hg_wall=3.0,
    hg_vents=[(419.0, 434.5), (449.5, 478.5), (493.5, 522.5), (530.5, 543.5)],      # photo x spans
    hg_vent_up=(ZY(60.3), ZY(56.6)), hg_vent_lo=(ZY(82.4), ZY(78.6)),
    hg_qd=(LX(557.5), ZY(81.0)),
    # barrel assembly (photo: barrel y 61..77, neck y 63..76, flash hider y 60..79)
    barrel_r=8.9, barrel_neck_r=7.25, barrel_hg_r=9.3, fh_r=10.6, fh_l0=LX(690.5), fh_l1=LX(729.0),
    neck=(LX(614.0), LX(636.0)), gas_block=(LX(577.0), LX(593.0)), piston_z=18.5, piston_r=4.9,
    # upper receiver
    up_l0=LX(201.0), up_l1=0.0, split_z=-14.0, bore_r=12.9, carrier_r=12.6,
    up_deck=ZY(42.0), port=(-86.0, -21.0, -6.0, 10.0), cover=(-89.5, -17.5, -6.9, 11.7),
    hinge=(-18.6, -8.6), ch_floor=17.9, ch_roof=23.2, ch_half=6.3, ch_travel=75.0, carrier_travel=80.0,
    # lower receiver
    lo_half=11.3, mw_half=14.0, mw_cav_half=11.4, mag_half=11.2, mw_l0=LX(302.0), mw_l1=LX(358.0),
    selector=(LX(240.0), ZY(100.0)), trigger_pin=(LX(271.0), ZY(103.0)), hammer_pin=(LX(283.0), ZY(93.0)),
    sear_pin=(LX(228.5), ZY(89.0)), pivot_pin=(LX(364.5), ZY(87.5)), takedown_pin=(LX(223.0), ZY(88.0)),
    button=(LX(292.6), LX(300.8), ZY(108.0), ZY(94.0)), catch_z=ZY(101.0),
    # stock / buffer
    tube_r=14.6, tube_l1=-352.0, stock_half=19.0, butt_half=21.0, stock_steps=[0, -15, -30, -45, -60, -75],
    # sights
    fs_pivot=(LX(584.2), 27.5), fs_top=ZY(6.0), rs_pivot=(-122.0, 47.0), rs_top=ZY(7.0), sight_line=65.5,
    grip_half=14.5,
)

# ------------------------------------------------------------------ registries
OBJ, W, GROUP_OF, CLIPS, MATS = {}, {}, {}, {}, {}
GROUPS = ['upper', 'lower', 'handguard', 'barrel_assembly', 'stock', 'grip', 'magazine', 'sights', 'controls', 'fasteners']

def SEG(n):
    """Round-part segment count, halved for LOD1."""
    return int(n * 1.5) // 2 * 2 if LOD == 0 else max(8, int(n * 0.75) // 2 * 2)

# ------------------------------------------------------------------ mesh kit (all in model mm: Vector(L, S, Z))
def _map(ax):
    if ax == 'S': return lambda u, v, w: (u, w, v)      # outline (L, Z) extruded along S
    if ax == 'L': return lambda u, v, w: (w, u, v)      # outline (S, Z) extruded along L
    return lambda u, v, w: (u, v, w)                    # outline (L, S) extruded along Z

def area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))

def inset(poly, d):
    """Offset a closed outline inward by d (mitred, clamped), keeping the vertex count."""
    if d == 0: return list(poly)
    sgn = 1.0 if area2(poly) > 0 else -1.0
    n = len(poly); out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized(); e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * sgn; n1 = Vector((-e1.y, e1.x)) * sgn
        b = n0 + n1
        if b.length < 1e-6: b = n0
        b.normalize()
        k = min(1.0 / max(b.dot(n0), 0.35), 2.2)
        out.append(tuple(p1 + b * d * k))
    return out

def bm_prism(poly, a, b, ax='S'):
    return bm_loft(poly, [(a, 0.0), (b, 0.0)], ax)

def bm_loft(poly, stations, ax='S'):
    """Outline swept through stations [(w, inset)]: gives rounded slabs (grip, stock, magazine)."""
    M = _map(ax); bm = bmesh.new(); rings = []
    for w, d in stations:
        rings.append([bm.verts.new(M(u, v, w)) for u, v in inset(poly, d)])
    n = len(poly)
    bm.faces.new(rings[0]); bm.faces.new(rings[-1][::-1])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    return bm

def rounded(half, edge, ins):
    """Loft stations for a slab of half-width `half` whose edges are rounded over `edge` mm, inset `ins`."""
    n = 4 if LOD == 0 else 2; ang = [math.pi / 2 * i / n for i in range(n + 1)]
    left = [(-(half - edge * (1 - math.cos(a))), ins * (1 - math.sin(a))) for a in ang]
    return left + [(-w, d) for w, d in reversed(left)]

def bm_box(l0, l1, s0, s1, z0, z1):
    return bm_prism([(l0, z0), (l1, z0), (l1, z1), (l0, z1)], s0, s1, 'S')

def _basis(d):
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized(); v = d.cross(u).normalized()
    return d, u, v

def bm_cyl(p0, p1, r, n=24, r1=None, r_in=0.0, ph=0.0):
    """Cylinder / cone / tube from p0 to p1 (model mm). r_in > 0 makes it a hollow tube."""
    n = SEG(n) if n > 8 else n
    p0, p1 = Vector(p0), Vector(p1); d, u, v = _basis(p1 - p0); r1 = r if r1 is None else r1
    bm = bmesh.new()
    def ring(c, rr):
        return [bm.verts.new(c + (u * math.cos(ph + 2 * math.pi * i / n) + v * math.sin(ph + 2 * math.pi * i / n)) * rr) for i in range(n)]
    a, b = ring(p0, r), ring(p1, r1)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if r_in > 0:
        ai, bi = ring(p0, r_in), ring(p1, r_in)
        for i in range(n):
            bm.faces.new((ai[i], bi[i], bi[(i + 1) % n], ai[(i + 1) % n]))
            bm.faces.new((a[i], ai[i], ai[(i + 1) % n], a[(i + 1) % n]))
            bm.faces.new((b[i], b[(i + 1) % n], bi[(i + 1) % n], bi[i]))
    else:
        bm.faces.new(a); bm.faces.new(b[::-1])
    return bm

def cylS(l, z, s0, s1, r, n=24, **kw): return bm_cyl((l, s0, z), (l, s1, z), r, n, **kw)
def cylL(s, z, l0, l1, r, n=24, **kw): return bm_cyl((l0, s, z), (l1, s, z), r, n, **kw)
def cylZ(l, s, z0, z1, r, n=24, **kw): return bm_cyl((l, s, z0), (l, s, z1), r, n, **kw)

def bm_lathe(loop, n=48, s0=0.0, z0=0.0):
    """Closed (L, r) outline revolved about the L axis through (s0, z0). r may be 0 on the axis."""
    n = SEG(n); bm = bmesh.new(); rings = []
    for l, r in loop:
        if r < 1e-6: rings.append([bm.verts.new((l, s0, z0))] * n)
        else: rings.append([bm.verts.new((l, s0 + r * math.cos(2 * math.pi * i / n), z0 + r * math.sin(2 * math.pi * i / n))) for i in range(n)])
    m = len(loop)
    for j in range(m):
        a, b = rings[j], rings[(j + 1) % m]
        for i in range(n):
            vs = []
            for v in (a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]):
                if v not in vs: vs.append(v)
            if len(vs) >= 3:
                try: bm.faces.new(vs)
                except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return bm

def join(*bms):
    out = bms[0]; tmp = bpy.data.meshes.new('tmp')
    for b in bms[1:]:
        b.to_mesh(tmp); out.from_mesh(tmp); b.free()
    bpy.data.meshes.remove(tmp)
    return out

def rot(bm, origin, axis, deg):
    """Rotate a bmesh (model mm) about a model axis vector through origin."""
    bmesh.ops.rotate(bm, verts=bm.verts, cent=Vector(origin), matrix=Matrix.Rotation(math.radians(deg), 3, Vector(axis)))
    return bm

def stadium(l0, l1, z0, z1, n=6):
    r = (z1 - z0) / 2; zc = (z0 + z1) / 2; pts = []
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n; pts.append((l1 - r + r * math.cos(a), zc + r * math.sin(a)))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n; pts.append((l0 + r + r * math.cos(a), zc + r * math.sin(a)))
    return pts

def to_blender(bm, pivot):
    for v in bm.verts:
        l, s, z = v.co
        v.co = Vector((s * MM, -l * MM, z * MM)) - pivot

def bl(p): return Vector((p[1] * MM, -p[0] * MM, p[2] * MM))

def _raw(name, bm, pivot):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    to_blender(bm, pivot)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = pivot
    return o

def _apply(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = o.data; o.modifiers.clear(); o.data = me; bpy.data.meshes.remove(old); me.name = o.name

def finish(name, bm, mat, group, pivot=None, bevel=0.3, seg=2, cuts=(), parent=None, sharp=40, polish=0.0, stipple=0.0, wear=1.0):
    """Turn a bmesh (model mm) into a named object: boolean cuts, bevel, weighted normals, parenting.
    pivot (model mm) is the object's origin: the hinge or slide axis for a moving part."""
    assert name not in OBJ, name
    if pivot is None:
        cs = [v.co.copy() for v in bm.verts]
        pivot = (sum(c.x for c in cs) / len(cs), sum(c.y for c in cs) / len(cs), sum(c.z for c in cs) / len(cs))
    wp = bl(pivot)
    o = _raw(name, bm, wp)
    for c in cuts:
        co = _raw('cutter', c, Vector((0, 0, 0)))
        m = o.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.use_self = True; m.object = co
        _apply(o); bpy.data.objects.remove(co)
    me = o.data
    for p in me.polygons: p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(sharp))
    if bevel and (LOD == 0 or bevel >= 0.4):          # LOD1 keeps a single chamfer on the larger edges only
        b = o.modifiers.new('bevel', 'BEVEL'); b.limit_method = 'ANGLE'; b.angle_limit = math.radians(sharp)
        b.width = bevel * MM; b.segments = seg if LOD == 0 else 1; b.harden_normals = False; b.use_clamp_overlap = True
    wn = o.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.weight = 60
    me.materials.clear(); me.materials.append(MATS[mat])
    for p in me.polygons: p.material_index = 0
    o['polish'] = float(polish); o['stipple'] = float(stipple); o['wear'] = float(wear)
    par = OBJ[parent] if parent else OBJ[group]
    o.parent = par; o.location = wp - W[par.name]
    OBJ[name] = o; W[name] = wp; GROUP_OF[name] = group
    return o

def screw(name, c, d, r, h, group, kind='hex', mat='Steel', parent=None, sink=0.4, n=20):
    """A fastener head sitting flush in its hole: c = point on the host surface, d = outward direction.
    kind: hex (socket head), slot, pin (solid pin end with a dimple), roll (roll pin end), plain."""
    c = Vector(c); d = Vector(d).normalized()
    bm = bm_cyl(c - d * sink, c + d * h, r, n)
    cuts = []
    if LOD == 0:
        if kind == 'hex': cuts.append(bm_cyl(c + d * (h - 0.9), c + d * (h + 0.5), r * 0.55, 6))
        elif kind == 'pin': cuts.append(bm_cyl(c + d * (h - 0.25), c + d * (h + 0.5), r * 0.4, 12))
        elif kind == 'roll': cuts.append(bm_cyl(c + d * (h - 0.6), c + d * (h + 0.5), r * 0.62, 12))
        elif kind == 'slot':
            dd, u, v = _basis(d); q = bm_cyl(c + d * (h - 0.6), c + d * (h + 0.5), r * 1.2, 4, ph=math.pi / 4)
            for vv in q.verts:
                rel = vv.co - c; vv.co = c + d * rel.dot(d) + u * rel.dot(u) + v * rel.dot(v) * 0.18
            cuts.append(q)
    return finish(name, bm, mat, group, bevel=min(0.2, r * 0.12), seg=1, cuts=cuts, parent=parent)

A, ST, PO = 'Anodized', 'Steel', 'Polymer'

# ================================================================== barrel assembly
def build_barrel():
    g = 'barrel_assembly'
    b0 = P['barrel_breech']; b1 = b0 + P['barrel_len']; gb0, gb1 = P['gas_block']; n0, n1 = P['neck']
    r, rn, rh = P['barrel_r'], P['barrel_neck_r'], P['barrel_hg_r']; sh = LX(685.0)
    finish('barrel', bm_lathe([(b0, 0), (b0, 11.0), (2, 11.0), (2, 10.0), (60, 10.0), (62, rh), (gb1, rh), (gb1, r), (n0 - 0.5, r),
                               (n0 + 0.6, rn), (n1 - 0.6, rn), (n1 + 0.7, r), (sh, r), (sh, 6.35), (b1, 6.35), (b1, 0)], 40), ST, g, pivot=(0, 0, 0), bevel=0.25)
    finish('barrel_nut', bm_cyl((0.0, 0, 0), (22.0, 0, 0), 14.5, 32, r_in=9.9), ST, g, bevel=0.4)
    # gas block: clamps the barrel, carries the piston and the front sight
    gb = [(-7, -13.5), (7, -13.5), (11, -9.5), (11, 8), (9, 10), (9, ZY(48.0)), (-9, ZY(48.0)), (-9, 10), (-11, 8), (-11, -9.5)]
    finish('gas_block', bm_prism(gb, gb0, gb1, 'L'), ST, g, bevel=0.5)
    for i, l in enumerate((gb0 + 5.0, gb1 - 5.0)):
        finish(f'gas_block_pin_{i + 1}', join(cylS(l, -11.0, -9.75, -9.3, 1.6, 12), cylS(l, -11.0, 9.3, 9.75, 1.6, 12)), ST, 'fasteners', bevel=0.12, seg=1)
    finish('gas_regulator', join(cylL(0, P['piston_z'], gb1 - 0.3, gb1 + 0.9, 4.4, 20), cylL(0, P['piston_z'], gb1 + 0.8, gb1 + 1.5, 2.2, 6)), ST, g, bevel=0.2, seg=1)
    finish('gas_piston_tube', cylL(0, P['piston_z'], 18.0, gb0 + 0.3, P['piston_r'], 24), ST, g, bevel=0.3)
    finish('bayonet_lug', bm_box(LX(579.0), LX(590.5), -4.0, 4.0, ZY(88.0), -13.3), ST, g, bevel=0.4)
    a, b = P['fh_l0'], P['fh_l1']; fr = P['fh_r']
    finish('muzzle_jam_ring', bm_lathe([(sh, 6.4), (sh, 9.7), (LX(688.0), 9.7), (LX(688.0), 6.4)], 32), ST, g, bevel=0.3)
    finish('crush_washer', bm_lathe([(LX(688.0), 6.4), (LX(688.0), 9.4), (a + 0.1, 8.5), (a + 0.1, 6.4)], 32), ST, g, bevel=0.15, seg=1)
    cuts = []
    for k in range(6):
        cuts.append(rot(bm_prism(stadium(a + 19.5, b - 5.5, -1.7, 1.7), 5.0, 13.0, 'Z'), (0, 0, 0), (1, 0, 0), 30 + 60 * k))
    cuts.append(bm_box(a + 8.0, a + 13.0, 9.9, 13.0, -9.0, 9.0)); cuts.append(bm_box(a + 8.0, a + 13.0, -13.0, -9.9, -9.0, 9.0))
    fh = bm_lathe([(a, 6.3), (a, 9.8), (a + 1, fr), (a + 3.5, fr), (a + 4, 9.4), (a + 6.5, 9.4), (a + 7, fr), (b - 1.5, fr), (b, 9.6), (b, 7.8), (a + 13, 7.8), (a + 12, 6.3)], 36)
    finish('flash_hider', fh, ST, g, bevel=0.3, cuts=cuts if LOD == 0 else cuts[:6])
    finish('muzzle_bore', cylL(0, 0, b1 - 0.4, b1 + 0.3, 6.25, 20), 'Cavity', g, bevel=0)

def arm_outline(pl, pz, r, top_pts, n=10):
    """Side outline of a folding sight arm: a half-round foot centred on the pivot, then the given top points."""
    foot = [(pl + r * math.cos(a), pz + r * math.sin(a)) for a in [math.pi + math.pi * i / n for i in range(n + 1)]]
    return foot + list(top_pts)

# ================================================================== front sight (folds forward over the barrel)
def build_front_sight():
    g = 'sights'; pl, pz = P['fs_pivot']; top = P['fs_top']; gz = ZY(48.0)
    ears = bm_prism([(pl - 7.1, -7.5), (pl + 5.4, -7.5), (pl + 5.4, -4.9), (pl - 4.0, -4.9), (pl - 4.0, 4.9), (pl + 5.4, 4.9), (pl + 5.4, 7.5), (pl - 7.1, 7.5)],
                    gz - 0.2, pz + 3.5, 'Z')                                    # one U-shaped piece: two ears and the rear bridge
    finish('front_sight_base', ears, A, g, bevel=0.4)
    arm = bm_prism(arm_outline(pl, pz, 3.5, [(pl + 3.5, top - 12.4), (pl + 3.2, top - 11.0), (pl - 3.2, top - 11.0), (pl - 3.5, top - 12.4)]), -4.7, 4.7, 'S')
    finish('front_sight_arm', arm, A, g, pivot=(pl, 0, pz), bevel=0.3)
    finish('front_sight_post', join(cylZ(pl, 0, top - 11.2, P['sight_line'], 1.0, 12), cylZ(pl, 0, top - 11.2, top - 9.5, 2.3, 12)), ST, g, parent='front_sight_arm', bevel=0.1, seg=1)
    for s, sg in (('l', 1), ('r', -1)):
        ear = bm_prism([(pl - 3.2, top - 11.2), (pl + 3.2, top - 11.2), (pl + 3.2, top - 2.0), (pl + 1.6, top), (pl - 1.6, top), (pl - 3.2, top - 2.0)], sg * 3.2, sg * 4.7, 'S')
        finish(f'front_sight_ear_{s}', ear, A, g, parent='front_sight_arm', bevel=0.25)
        screw(f'front_sight_pivot_head_{s}', (pl, sg * 7.5, pz), (0, sg, 0), 2.4, 0.8, 'fasteners', kind='pin')
    screw('front_sight_detent', (pl - 5.4, 7.5, gz + 2.3), (0, 1, 0), 1.4, 0.9, g, kind='plain')
    screw('front_sight_base_screw', (pl - 5.4, -7.5, gz + 2.3), (0, -1, 0), 1.6, 0.8, 'fasteners', kind='hex')

# ================================================================== handguard
def lug_profile(side):
    T, F, Tb, Fb = P['rail_top'], P['rail_floor'] - 0.15, P['rail_bot'], P['rail_bot_floor'] + 0.15
    h, w, fl = P['rail_half_top'], P['rail_half'], P['rail_flank']; zc = P['hg_side_zc']; To, Fo = P['hg_side_lug'], P['hg_side'] - 0.15
    if side == 'top': return [(-h, T), (h, T), (w, T - fl), (w - 0.3, F), (-(w - 0.3), F), (-w, T - fl)]
    if side == 'bottom': return [(-h, Tb), (h, Tb), (w, Tb + fl), (w - 0.3, Fb), (-(w - 0.3), Fb), (-w, Tb + fl)]
    sg = 1 if side == 'left' else -1
    return [(sg * To, zc - h), (sg * To, zc + h), (sg * (To - fl), zc + w), (sg * Fo, zc + w - 0.3), (sg * Fo, zc - (w - 0.3)), (sg * (To - fl), zc - w)]

def hg_outline(top=None):
    w = P['rail_half'] - 0.3; zc = P['hg_side_zc']; sd = P['hg_side']; Ft, Fb = P['rail_floor'], P['rail_bot_floor']
    if top is None:
        return [(w, Ft), (sd, zc + w), (sd, zc - w), (w, Fb), (-w, Fb), (-sd, zc - w), (-sd, zc + w), (-w, Ft)]
    st = w + (Ft - top) * (sd - w) / (Ft - (zc + w))
    return [(st, top), (sd, zc + w), (sd, zc - w), (w, Fb), (-w, Fb), (-sd, zc - w), (-sd, zc + w), (-st, top)]

def diag_point(z, sg):
    """Point and outward normal on the handguard's diagonal wall at height z (upper wall if z > centre)."""
    w = P['rail_half'] - 0.3; zc = P['hg_side_zc']; sd = P['hg_side']
    if z > zc: a, b = Vector((w, P['rail_floor'])), Vector((sd, zc + w))
    else: a, b = Vector((w, P['rail_bot_floor'])), Vector((sd, zc - w))
    t = (z - a.y) / (b.y - a.y); p = a + (b - a) * t; e = (b - a).normalized()
    n = Vector((e.y, -e.x));  n = n if n.x > 0 else -n
    return (p.x * sg, z), (n.x * sg, n.y)

def build_handguard():
    g = 'handguard'; l0, l1 = P['hg_l0'], P['hg_l1']; out = hg_outline()
    cuts = [bm_prism(inset(out, P['hg_wall']), l0 - 1, l1 + 1, 'L')]
    for x0, x1 in P['hg_vents']:
        for z0, z1 in (P['hg_vent_up'], P['hg_vent_lo']):
            cuts.append(bm_prism(stadium(LX(x0), LX(x1), z0, z1), -40, 40, 'S'))
    ql, qz = P['hg_qd']
    cuts.append(cylS(ql, qz, -40, 40, 3.4, 16))
    cres = [(ql + rr * math.cos(math.radians(a)), qz + rr * math.sin(math.radians(a))) for rr, aa in ((7.0, range(200, 345, 14)), (10.5, range(340, 195, -14))) for a in aa]
    cuts.append(bm_prism(cres, -40, 40, 'S'))
    cuts.append(bm_prism([(LX(570.0), ZY(39.2)), (LX(578.5), ZY(48.9)), (LX(578.5), ZY(28.0)), (LX(570.0), ZY(28.0))], -40, 40, 'S'))
    finish('handguard_body', bm_prism(out, l0, l1 - 1.0, 'L'), A, g, pivot=(0, 0, 0), bevel=0.35, cuts=cuts)
    cap = hg_outline(top=ZY(47.0))
    finish('hg_front_cap', bm_prism(inset(cap, 0.5), l1 - 1.1, l1, 'L'), A, g, bevel=0.3, cuts=[bm_prism(inset(cap, 3.3), l1 - 3, l1 + 1, 'L')])
    n = P['n_hg_lugs']; pitch, lw = P['rail_pitch'], P['rail_lug']; first = P['hg_lug0']
    blocks = dict(top=((0.0, LX(383.0)), (LX(559.0), LX(569.5))), bottom=((LX(376.0), LX(384.0)), (LX(559.0), LX(566.5))),
                  left=((LX(376.0), LX(384.0)), (LX(559.0), LX(568.0))), right=((LX(376.0), LX(384.0)), (LX(559.0), LX(568.0))))
    for side in ('top', 'bottom', 'left', 'right'):
        prof = lug_profile(side); (r0, r1), (f0, f1) = blocks[side]
        finish(f'hg_rail_{side}_rear_block', bm_prism(prof, r0, r1, 'L'), A, g, bevel=0.25, seg=2)
        for i in range(n):
            a = first + pitch * i
            finish(f'hg_rail_{side}_lug_{i + 1:02d}', bm_prism(prof, a, a + lw, 'L'), A, g, bevel=0.25, seg=2)
        finish(f'hg_rail_{side}_front_block', bm_prism(prof, f0, f1, 'L'), A, g, bevel=0.25, seg=2)
    # retaining bolt bosses (the HK416's captive cross bolt) and their hardware
    bl0, bl1, bz0, bz1 = LX(388.0), LX(407.0), ZY(89.0), ZY(79.5); bc = ((bl0 + bl1) / 2, (bz0 + bz1) / 2)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'hg_bolt_boss_{s}', bm_box(bl0, bl1, sg * 17.5, sg * 25.0, bz0, bz1), A, g, bevel=0.5)
    screw('hg_retaining_bolt', (bc[0], -25.0, bc[1]), (0, -1, 0), 3.3, 1.6, g, kind='hex')
    screw('hg_retaining_bolt_nut', (bc[0], 25.0, bc[1]), (0, 1, 0), 3.0, 1.0, g, kind='slot')
    for s, sg in (('l', 1), ('r', -1)):
        (ps, pz), (ns, nz) = diag_point(qz, sg)
        finish(f'hg_qd_cup_{s}', bm_cyl((ql, sg * 21.5, qz), (ql, sg * 27.3, qz), 5.4, 24, r_in=3.4), ST, g, bevel=0.3)
        (ps, pz), (ns, nz) = diag_point(24.0, sg)
        screw(f'hg_index_screw_{s}', (32.0, ps, pz), (0, ns, nz), 2.1, 0.7, 'fasteners', kind='hex')
        (ps, pz), (ns, nz) = diag_point(-20.5, sg)
        screw(f'hg_front_screw_{s}', (LX(540.0), ps, pz), (0, ns, nz), 1.6, 0.6, 'fasteners', kind='hex')

# ================================================================== upper receiver
def build_upper():
    g = 'upper'; l0, l1 = P['up_l0'], P['up_l1']; dz = P['up_deck']; sz = P['split_z']; F = P['rail_floor']
    half = [(7.8, dz), (12.0, 26.0), (15.2, 20.0), (16.5, 13.0), (16.5, -7.0), (15.0, -11.0), (12.7, sz)]
    sec = half + [(-s, z) for s, z in reversed(half)]
    body = bm_prism(sec, l0, l1, 'L')
    w = P['rail_half'] - 0.3
    base = bm_prism([(-w, F), (w, F), (7.9, F - 2.5), (7.9, dz - 0.3), (-7.9, dz - 0.3), (-7.9, F - 2.5)], LX(231.0), l1, 'L')
    pl0, pl1, pz0, pz1 = P['port']
    cuts = [cylL(0, 0, l0 - 1, -5.0, P['bore_r'], 40),                                                # bolt carrier bore
            bm_box(l0 - 1, -12.0, -P['ch_half'], P['ch_half'], P['ch_floor'], P['ch_roof']),         # charging handle channel
            bm_box(l0 - 1, LX(210.0), -22, 22, P['ch_floor'], 45),                                   # notch for the T handle
            bm_box(pl0, pl1, -22, -9, pz0, pz1)]                                                     # ejection port
    finish('upper_body', join(body, base), A, g, pivot=(0, 0, 0), bevel=0.4, cuts=cuts)
    prof = lug_profile('top'); pitch, lw = P['rail_pitch'], P['rail_lug']
    finish('upper_rail_rear_block', bm_prism(prof, LX(231.5), LX(269.5), 'L'), A, g, bevel=0.25)
    for i in range(P['n_upper_lugs']):
        a = P['upper_lug0'] + pitch * i
        finish(f'upper_rail_lug_{i + 1:02d}', bm_prism(prof, a, a + lw, 'L'), A, g, bevel=0.25)
    finish('upper_rail_front_block', bm_prism(prof, LX(361.5), l1, 'L'), A, g, bevel=0.25)
    # right side furniture
    finish('brass_deflector', bm_prism([(LX(271.0), -16.2), (pl0 - 3.2, -16.2), (pl0 - 3.2, -23.0)], ZY(66.0), ZY(51.0), 'Z'), A, g, bevel=0.5)
    fa0, fa1 = (-122.0, -18.2, 1.0), (-174.0, -22.0, 1.0); d = (Vector(fa1) - Vector(fa0)).normalized()
    finish('forward_assist_housing', bm_cyl(fa0, fa1, 5.0, 24), A, g, bevel=0.5)
    finish('forward_assist_button', join(bm_cyl(Vector(fa1) - d * 0.5, Vector(fa1) + d * 3.2, 4.1, 24), bm_cyl(Vector(fa1) + d * 3.0, Vector(fa1) + d * 4.6, 5.3, 24)), ST, 'controls',
           bevel=0.5, polish=1.0)
    pm = Vector(fa0) + d * 30
    finish('forward_assist_pin', cylZ(pm.x, pm.y - 1.5, pm.z - 5.2, pm.z + 5.2, 1.1, 10), ST, 'fasteners', bevel=0.1, seg=1)
    finish('upper_rib_r', bm_box(l0 + 1, pl0 - 7.5, -17.2, -15.0, -10.6, -8.0), A, g, bevel=0.4)
    finish('upper_rib_l', bm_box(l0 + 1, -89.5, 15.0, 17.2, -10.6, -8.0), A, g, bevel=0.4)
    tear = [(-140 + 7 * math.cos(a), 4 + 5.5 * math.sin(a)) for a in [math.radians(x) for x in range(-90, 91, 30)]] + [(-158, 4)]
    finish('upper_left_boss', bm_prism(tear, 16.2, 17.7, 'S'), A, g, bevel=0.4)
    # dust cover and its hinge (hinge along the bottom of the port; the cover swings down)
    hs, hz = P['hinge']; c0, c1, cz0, cz1 = P['cover']
    finish('upper_hinge_lug_rear', bm_box(c0 - 3.6, c0 - 0.4, -20.6, -15.3, hz - 2.2, hz + 2.2), A, g, bevel=0.3)
    finish('upper_hinge_lug_front', bm_box(c1 + 0.4, c1 + 3.6, -20.6, -15.3, hz - 2.2, hz + 2.2), A, g, bevel=0.3)
    finish('dust_cover_hinge_rod', cylL(hs, hz, c0 - 5.0, c1 + 4.6, 1.0, 12), ST, 'fasteners', bevel=0.1, seg=1)
    finish('dust_cover_rod_clip', cylL(hs, hz, c0 - 5.6, c0 - 5.0, 1.9, 12, r_in=0.9), ST, 'fasteners', bevel=0.1, seg=1)
    finish('dust_cover', bm_box(c0, c1, -17.95, -16.75, cz0, cz1), ST, g, pivot=(0.5 * (c0 + c1), hs, hz), bevel=0.3, polish=0.5)
    finish('dust_cover_knuckle_1', cylL(hs, hz, c1 - 22.0, c1, 2.0, 16, r_in=1.15), ST, g, parent='dust_cover', bevel=0.15, seg=1)
    finish('dust_cover_knuckle_2', cylL(hs, hz, c0, c0 + 22.0, 2.0, 16, r_in=1.15), ST, g, parent='dust_cover', bevel=0.15, seg=1)
    finish('dust_cover_latch', bm_box(LX(318.0), LX(328.0), -19.6, -17.85, ZY(72.0), ZY(60.5)), ST, g, parent='dust_cover', bevel=0.4, polish=1.0)
    finish('dust_cover_rib_1', bm_box(c1 - 27.0, c1 - 5.0, -18.6, -17.85, -2.0, 7.0), ST, g, parent='dust_cover', bevel=0.3)
    finish('dust_cover_rib_2', bm_box(c0 + 5.0, c0 + 25.0, -18.6, -17.85, -2.0, 7.0), ST, g, parent='dust_cover', bevel=0.3)
    sp = [(c0 + 22.6, 1.15)]
    for i in range(12):
        a = c0 + 22.6 + i * 2.2; sp += [(a, 1.9), (a + 1.1, 1.9), (a + 1.1, 1.5), (a + 2.2, 1.5)]
    sp += [(c0 + 22.6 + 26.4, 1.15)]
    finish('dust_cover_spring', bm_lathe(sp, 12, s0=hs, z0=hz), ST, g, bevel=0)
    # bolt carrier group: only the outer face that shows through the port
    cr = P['carrier_r']
    finish('bolt_carrier', cylL(0, 0, -152.0, -30.0, cr, 40), ST, g, pivot=(-91.0, 0, 0), bevel=0.5, polish=0.6)
    ser = None
    for i in range(9):
        a0 = -66.0 + i * 3.0; b = rot(bm_box(a0, a0 + 1.6, -1.6, 1.6, cr - 0.5, cr + 0.22), (0, 0, 0), (1, 0, 0), 105)
        ser = b if ser is None else join(ser, b)
    finish('bolt_carrier_serrations', ser, ST, g, parent='bolt_carrier', bevel=0.1, seg=1)
    for i, l in enumerate((-36.0, -46.0)):
        finish(f'bolt_carrier_vent_{i + 1}', rot(cylZ(l, 0, cr - 0.4, cr + 0.12, 1.5, 12), (0, 0, 0), (1, 0, 0), 72), 'Cavity', g, parent='bolt_carrier', bevel=0)
    finish('bolt_head', join(cylL(0, 0, -30.5, -22.0, 9.6, 24), cylL(0, 0, -22.5, -14.0, 8.4, 24)), ST, g, parent='bolt_carrier', bevel=0.4, polish=1.0)

# ================================================================== rear sight (folds forward over the rail)
def build_rear_sight():
    g = 'sights'; pl, pz = P['rs_pivot']; T = P['rail_top']; top = P['rs_top']; b0, b1 = LX(236.0), LX(269.0); deck = 41.0
    base = bm_prism([(-12.5, T - 5.3), (-10.7, T - 5.3), (-10.7, T - 0.2), (10.7, T - 0.2), (10.7, T - 5.3), (12.5, T - 5.3), (12.5, deck), (-12.5, deck)], b0, b1, 'L')
    finish('rear_sight_base', base, A, g, bevel=0.4)
    for s, sg in (('l', 1), ('r', -1)):
        lug = bm_prism([(b0 + 0.5, deck - 0.2), (b1, deck - 0.2), (b1, pz + 1.0), (pl + 3.0, ZY(22.0)), (b0 + 3.0, ZY(22.0)), (b0 + 0.5, ZY(25.0))], sg * 8.0, sg * 11.5, 'S')
        finish(f'rear_sight_lug_{s}', lug, A, g, bevel=0.4)
        screw(f'rear_sight_pivot_head_{s}', (pl, sg * 11.5, pz), (0, sg, 0), 2.5, 0.9, 'fasteners', kind='pin')
    sl = P['sight_line']
    arm = bm_prism(arm_outline(pl, pz, 5.5, [(pl + 5.5, top - 2.0), (pl + 3.5, top), (pl - 3.5, top), (pl - 5.5, top - 2.0)]), -7.8, 7.8, 'S')
    finish('rear_sight_arm', arm, A, g, pivot=(pl, 0, pz), bevel=0.35, cuts=[cylL(0, sl, pl - 8, pl + 8, 2.7, 20)])
    finish('rear_sight_aperture', cylL(0, sl, pl - 5.75, pl - 5.0, 4.3, 24, r_in=2.3), ST, g, parent='rear_sight_arm', bevel=0.15, seg=1)
    finish('rear_sight_windage_knob', cylS(pl, sl - 5.0, -12.3, -7.7, 5.4, 18), ST, g, parent='rear_sight_arm', bevel=0.4, polish=1.0)
    screw('rear_sight_windage_screw', (pl, 7.8, sl - 5.0), (0, 1, 0), 2.2, 1.2, g, kind='slot', parent='rear_sight_arm')
    finish('rear_sight_clamp_bar', bm_box(b0 + 4, b1 - 4, 12.3, 14.4, T - 5.3, T + 0.5), A, g, bevel=0.4)
    screw('rear_sight_clamp_screw', (0.5 * (b0 + b1) - 6, 14.4, T - 2.4), (0, 1, 0), 2.6, 1.6, 'fasteners', kind='hex')
    finish('rear_sight_clamp_nut', cylS(0.5 * (b0 + b1) - 6, T - 2.4, -14.6, -12.3, 3.0, 6), ST, 'fasteners', bevel=0.2, seg=1)
    screw('rear_sight_detent', (b1 - 2.6, 11.5, deck + 2.6), (0, 1, 0), 1.4, 0.8, g, kind='plain')

# ================================================================== charging handle
def build_charging_handle():
    g = 'controls'; l0 = P['up_l0']; f, r = P['ch_floor'], P['ch_roof']
    tz1 = ZY(44.0)
    ch = join(bm_prism([(l0 + 1.5, -22), (l0 + 5.5, -22), (l0 + 9.8, -17.4), (l0 + 9.8, 17.4), (l0 + 5.5, 22), (l0 + 1.5, 22), (l0, 19), (l0, 9), (l0 + 2.0, 6), (l0 + 2.0, -6), (l0, -9), (l0, -19)], f + 0.3, tz1, 'Z'),
              bm_box(l0 + 9.0, -20.0, -P['ch_half'] + 0.3, P['ch_half'] - 0.3, f + 0.2, r - 0.4))
    finish('charging_handle', ch, A, g, pivot=(l0 + 5.0, 0, 0.5 * (f + tz1)), bevel=0.4, polish=1.0)
    latch = bm_prism([(l0 + 1.0, 17.0), (l0 + 17.5, 17.0), (l0 + 18.6, 15.9), (l0 + 20.0, 17.6), (l0 + 18.0, 19.6), (l0 + 1.0, 19.6)], f + 1.2, tz1 - 1.2, 'Z')
    finish('charging_handle_latch', latch, ST, g, parent='charging_handle', bevel=0.3, polish=1.0, cuts=[bm_box(l0 - 1, l0 + 9.9, 16.0, 22.1, f - 1, tz1 + 1)])
    screw('charging_handle_latch_pin', (l0 + 5.0, 18.5, tz1), (0, 0, 1), 1.0, 0.25, 'fasteners', kind='roll', parent='charging_handle', n=10)

# ================================================================== lower receiver
def build_lower():
    g = 'lower'; hw, mw, cav = P['lo_half'], P['mw_half'], P['mw_cav_half']; ys = Y0 - P['split_z'] / K
    Aout = PX([(193, ys), (290.5, ys), (290.5, 113), (216, 113), (214, 108), (212, 105), (207, 102), (196, 100.5), (193, 98)])
    Bout = PX([(290, ys), (361, ys), (369, 84.5), (369, 95.8), (361, 95.8), (361, 134.2), (298, 134.2), (298, 120.5), (291, 113.5), (290, 113)])
    body = join(bm_prism(Aout, -hw, hw, 'S'), bm_prism(Bout, -mw, mw, 'S'))
    m0, m1 = P['mw_l0'] - 0.2, P['mw_l1'] + 0.2
    bl0, bl1, bz0, bz1 = P['button']; cz = P['catch_z']; shaft_l = 0.5 * (bl0 + bl1)
    cuts = [bm_box(m0, m1, -cav, cav, ZY(150), P['split_z'] + 2),                                     # magazine well
            bm_box(LX(226), LX(288), -7.5, 7.5, ZY(108), P['split_z'] + 2),                           # fire-control pocket
            bm_box(LX(262), LX(277.5), -3.4, 3.4, ZY(116), ZY(106)),                                  # trigger slot
            bm_box(bl0 - 0.2, bl1 + 0.2, -mw - 2, -9.8, bz0 - 0.2, bz1 + 0.2),                        # mag button pocket
            cylS(shaft_l, cz, -12, mw + 2, 2.2, 16),                                                  # mag catch shaft hole
            bm_box(bl0 - 0.2, LX(316.6), 12.7, mw + 2, cz - 3.6, cz + 3.6),                           # mag catch recess
            bm_box(LX(305.7), LX(312.3), 10, 13.5, cz - 2.7, cz + 2.7),                               # catch tooth window
            bm_box(-85.7, -74.3, 12.5, mw + 2, -31.5, -19.5)]                                         # bolt catch relief
    finish('lower_body', body, A, g, pivot=(LX(280), 0, ZY(100)), bevel=0.4, cuts=cuts)
    t0, t1 = LX(193.5), P['up_l0']
    finish('lower_buffer_tower', join(bm_cyl((t0, 0, 0), (t1, 0, 0), 17.5, 40, r_in=P['tube_r']), bm_box(t0, t1, -hw, hw, -19.5, -13.0)), A, g, bevel=0.4)
    fl = PX([(292, 141.5), (365, 141.5), (365, 136.5), (361.3, 134), (297.7, 134), (292, 137)])
    finish('magwell_flare', bm_prism(fl, -mw - 1.5, mw + 1.5, 'S'), A, g, bevel=0.5, cuts=[bm_box(m0, m1, -cav, cav, ZY(150), ZY(120))])
    finish('trigger_guard', bm_prism(PX([(255.3, 131.5), (259.8, 135), (261.5, 136.6), (297.5, 136.6), (297.5, 141.5), (260.5, 141.8), (250, 142.5), (246, 144), (251.5, 139)]), -5.5, 5.5, 'S'), A, g, bevel=0.6)
    fence = join(bm_box(bl0 - 2.0, bl0 - 0.2, -mw - 1.7, -mw + 0.2, bz0 - 2.0, bz1 + 2.0), bm_box(bl0 - 2.0, bl1 + 0.2, -mw - 1.7, -mw + 0.2, bz0 - 2.0, bz0 - 0.2),
                 bm_box(bl0 - 2.0, bl1 + 0.2, -mw - 1.7, -mw + 0.2, bz1 + 0.2, bz1 + 2.0))
    finish('mag_release_fence', fence, A, g, bevel=0.3)
    finish('bolt_catch_ear_front', bm_box(-74.3, -71.5, mw - 0.2, 17.0, -22.5, -14.6), A, g, bevel=0.3)
    finish('bolt_catch_ear_rear', bm_box(-88.5, -85.7, mw - 0.2, 17.0, -22.5, -14.6), A, g, bevel=0.3)
    sl, sz = P['selector']
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'lower_selector_stop_safe_{s}', bm_box(sl + 6.5, sl + 11.5, sg * (hw - 0.2), sg * (hw + 1.4), sz + 7.2, sz + 10.2), A, g, bevel=0.3)
        finish(f'lower_selector_stop_fire_{s}', bm_box(sl - 11.5, sl - 6.5, sg * (hw - 0.2), sg * (hw + 1.4), sz + 7.2, sz + 10.2), A, g, bevel=0.3)
        finish(f'magwell_rib_{s}', bm_box(LX(301.0), LX(303.6), sg * (mw - 0.2), sg * (mw + 0.9), ZY(133.0), ZY(112.5)), A, g, bevel=0.3)
    finish('marking_panel_r', bm_box(LX(312), LX(354), -mw - 0.15, -mw + 0.1, ZY(126), ZY(99)), A, g, bevel=0, wear=0.15)
    finish('marking_panel_l', bm_box(LX(322), LX(354), mw - 0.1, mw + 0.15, ZY(126), ZY(99)), A, g, bevel=0, wear=0.15)

# ================================================================== controls
def glyph(kind, cl, cz, s, sg):
    """Fire-control pictogram as paint 0.12 mm proud of the receiver wall: a frame plus its symbol."""
    w, h, t = 3.6, 2.4, 0.45; s0, s1 = sg * (s - 0.05), sg * (s + 0.12)
    bars = [(cl - w, cl + w, cz + h - t, cz + h), (cl - w, cl + w, cz - h, cz - h + t), (cl - w, cl - w + t, cz - h + t, cz + h - t), (cl + w - t, cl + w, cz - h + t, cz + h - t)]
    bms = [bm_box(a, b, s0, s1, c, d) for a, b, c, d in bars]
    if kind == 'safe':
        for sgn in (1, -1):
            bms.append(rot(bm_box(cl - 3.1, cl + 3.1, s0 + sg * 0.02 * sgn, s1 + sg * 0.02 * sgn, cz - 0.22, cz + 0.22), (cl, 0, cz), (0, 1, 0), sgn * 31))
    else:
        for k in ([0] if kind == 'semi' else [-1, 0, 1]):
            bms.append(bm_box(cl - 1.9, cl + 1.2, s0, s1, cz + k * 1.05 - 0.32, cz + k * 1.05 + 0.32))
            bms.append(bm_box(cl + 1.2, cl + 2.1, s0, s1, cz + k * 1.05 - 0.2, cz + k * 1.05 + 0.2))
    return join(*bms)

def build_controls():
    g = 'controls'; hw, mw = P['lo_half'], P['mw_half']; sl, sz = P['selector']
    # selector: thumb paddle to the rear at safe; the pointer on the hub faces the pictogram
    lev = join(cylS(sl, sz, hw + 0.2, hw + 2.3, 5.2, 28), bm_prism([(sl + 1, sz - 2.6), (sl - 13.3, sz - 2.2), (sl - 13.3, sz + 2.2), (sl + 1, sz + 2.6)], hw + 0.2, hw + 3.9, 'S'))
    finish('selector_lever_l', lev, ST, g, pivot=(sl, 0, sz), bevel=0.4, polish=1.0)
    lev = join(cylS(sl, sz, -hw - 2.3, -hw - 0.2, 5.2, 28), bm_prism([(sl + 1, sz - 2.4), (sl - 10.0, sz - 2.0), (sl - 10.0, sz + 2.0), (sl + 1, sz + 2.4)], -hw - 3.5, -hw - 0.2, 'S'))
    finish('selector_lever_r', lev, ST, g, parent='selector_lever_l', bevel=0.4, polish=1.0)
    finish('selector_index_l', bm_box(sl + 1.6, sl + 4.9, hw + 2.25, hw + 2.42, sz - 0.4, sz + 0.4), 'PaintWhite', g, parent='selector_lever_l', bevel=0)
    finish('selector_index_r', bm_box(sl + 1.6, sl + 4.9, -hw - 2.42, -hw - 2.25, sz - 0.4, sz + 0.4), 'PaintWhite', g, parent='selector_lever_l', bevel=0)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'pictogram_safe_{s}', glyph('safe', sl + 11.0, sz - 1.0, hw, sg), 'PaintWhite', g, bevel=0)
        finish(f'pictogram_semi_{s}', glyph('semi', sl, sz + 13.6, hw, sg), 'PaintRed', g, bevel=0)
        finish(f'pictogram_auto_{s}', glyph('auto', sl - 12.2, sz + 3.2 - 9.0, hw, sg), 'PaintRed', g, bevel=0)
    # bolt catch: rocks on a fore-aft pin; lower pad sits in a relief in the receiver wall
    pv = (-80.0, 15.3, -18.5)
    bc = join(bm_box(-85.5, -74.5, mw + 0.2, 17.2, -31.0, -12.0), bm_box(-86.5, -73.5, 16.75, 19.0, -13.0, -5.5))
    finish('bolt_catch', bc, ST, g, pivot=pv, bevel=0.4, polish=1.0)
    ribs = join(*[bm_box(-86.0, -74.0, 18.9, 19.5, z, z + 0.8) for z in (-12.2, -10.4, -8.6, -6.8)])
    finish('bolt_catch_ribs', ribs, ST, g, parent='bolt_catch', bevel=0.15, seg=1, polish=1.0)
    # magazine release: button (right), shaft, catch bar and tooth (left) move together along S
    bl0, bl1, bz0, bz1 = P['button']; cz = P['catch_z']; shaft_l = 0.5 * (bl0 + bl1)
    finish('mag_release_button', join(bm_box(bl0, bl1, -mw - 1.6, -11.5, bz0, bz1), cylS(shaft_l, cz, -11.6, 13.0, 2.0, 16)), ST, g, pivot=(shaft_l, 0, cz), bevel=0.3, polish=1.0)
    for i in range(3):
        a = bl0 + 1.2 + i * 2.6
        finish(f'mag_button_rib_{i + 1}', bm_box(a, a + 1.4, -mw - 2.1, -mw - 1.5, bz0 + 1.0, bz1 - 1.0), ST, g, parent='mag_release_button', bevel=0.15, seg=1, polish=1.0)
    catch = join(bm_box(bl0, LX(316.4), 12.9, mw + 0.6, cz - 3.4, cz + 3.4), bm_box(LX(306.0), LX(312.0), 11.0, 13.0, cz - 2.4, cz + 2.4))
    finish('mag_catch', catch, ST, g, parent='mag_release_button', bevel=0.3)
    # trigger
    tl, tz = P['trigger_pin']
    tr = PX([(266, 101), (276, 101), (276, 112), (274, 114), (271, 118), (269.2, 123), (268.3, 128), (269.5, 133), (271.2, 136.6), (268.6, 136.6),
             (265.6, 131), (264.2, 125), (263.8, 119), (264.5, 114), (264.6, 108)])
    finish('trigger', bm_loft(tr, [(-3.2, 0.9), (-2.4, 0.0), (2.4, 0.0), (3.2, 0.9)], 'S'), ST, g, pivot=(tl, 0, tz), bevel=0.2, seg=1, polish=1.0)

def build_pins():
    g = 'fasteners'; hw, mw = P['lo_half'], P['mw_half']
    pl, pz = P['pivot_pin']; tl, tz = P['takedown_pin']
    screw('pivot_pin_head_r', (pl, -mw, pz), (0, -1, 0), 3.6, 1.3, g, kind='plain'); screw('pivot_pin_end_l', (pl, mw, pz), (0, 1, 0), 2.9, 0.6, g, kind='pin')
    screw('takedown_pin_head_r', (tl, -hw, tz), (0, -1, 0), 3.6, 1.3, g, kind='plain'); screw('takedown_pin_end_l', (tl, hw, tz), (0, 1, 0), 2.9, 0.6, g, kind='pin')
    for nm, key, r in (('trigger_pin', 'trigger_pin', 2.0), ('hammer_pin', 'hammer_pin', 2.0), ('sear_pin', 'sear_pin', 1.6)):
        l, z = P[key]
        screw(f'{nm}_l', (l, hw, z), (0, 1, 0), r, 0.3, g, kind='pin', n=14); screw(f'{nm}_r', (l, -hw, z), (0, -1, 0), r, 0.3, g, kind='pin', n=14)
    finish('bolt_catch_pin', join(cylL(15.3, -18.5, -71.6, -70.9, 1.1, 10), cylL(15.3, -18.5, -89.1, -88.4, 1.1, 10)), ST, g, bevel=0.1, seg=1)

def interp(pts, y):
    """x on a traced edge [(x, y)...] (y increasing) at height y, extrapolating the end segments."""
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if y <= yb or (xb, yb) == pts[-1]:
            return xa + (xb - xa) * (y - ya) / (yb - ya)

def strip(edge, d0, d1):
    """Thin band along a traced edge, between x offsets d0 and d1 (photo px)."""
    return PX([(x + d0, y) for x, y in edge] + [(x + d1, y) for x, y in reversed(edge)])

# ================================================================== pistol grip
GRIP_REAR = [(216, 112), (216, 123), (214, 126.5), (211, 132), (206, 138), (201, 144), (197, 150), (194, 156), (191, 162), (188, 168), (186, 174),
             (184, 180), (182.5, 188), (180.8, 195), (179.5, 202)]
GRIP_FRONT = [(263, 112), (261.3, 114), (257.3, 117), (255.8, 120), (254.8, 123), (254.8, 128), (255.5, 133), (252, 140), (245, 144.5), (243, 149), (241.3, 153), (241, 157), (240, 164.5), (238, 168), (236, 174), (234, 180), (231.5, 185.5),
              (229.5, 191), (228.4, 197), (228.6, 202)]
def build_grip():
    g = 'grip'; hw = P['grip_half']
    finish('grip_body', bm_loft(PX(GRIP_REAR + GRIP_FRONT[::-1]), rounded(hw, 5.0, 2.2), 'S'), PO, g, pivot=(LX(215), 0, ZY(160)), bevel=0, sharp=50, polish=0.7)
    panel = [(203, 152), (237, 152), (231, 174), (225.5, 197), (186, 197), (190, 174)]
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'grip_panel_{s}', bm_prism(PX(panel), sg * (hw - 0.25), sg * (hw + 0.45), 'S'), PO, g, bevel=0.3, stipple=1.0, polish=1.0)
    finish('grip_backstrap_pad', bm_prism(strip([p for p in GRIP_REAR if 152 <= p[1] <= 196], -0.5, 1.8), -8.5, 8.5, 'S'), PO, g, bevel=0.25, stipple=1.0, polish=1.0)
    finish('grip_frontstrap_pad', bm_prism(strip([p for p in GRIP_FRONT if 168 <= p[1] <= 197], -1.8, 0.5), -8.5, 8.5, 'S'), PO, g, bevel=0.25, stipple=0.6, polish=1.0)
    finish('grip_finger_bump', bm_prism(PX([(239.6, 157.2), (245.8, 161.6), (245.5, 164), (239.4, 166.2)]), -7.5, 7.5, 'S'), PO, g, bevel=0.6, polish=1.0)
    finish('grip_cap', bm_prism(PX([(179.3, 201.7), (228.7, 201.7), (228, 205), (218, 207.6), (182.5, 207.6), (179.2, 205)]), -12.6, 12.6, 'S'), PO, g, bevel=0.8)
    finish('grip_cap_latch', bm_box(LX(177.9), LX(179.7), -4, 4, ZY(206), ZY(203)), PO, g, bevel=0.3)

# ================================================================== magazine
MAG_REAR = [(302, 141), (303, 160), (306, 180), (310, 198), (315, 216), (320, 231), (325, 247.5)]
MAG_FRONT = [(358, 141), (359, 160), (362, 180), (364.5, 190), (367, 198), (370, 207), (373, 216), (377.5, 225.5)]
MAG_TOP = 88.0
def build_magazine():
    g = 'magazine'; hw = P['mag_half']; top = ZY(MAG_TOP); cz = P['catch_z']
    out = [(302, MAG_TOP), (358, MAG_TOP)] + MAG_FRONT[:-1] + [(376, 222), (323.7, 243.8)] + MAG_REAR[-2::-1]
    finish('mag_body', bm_loft(PX(out), rounded(hw, 1.6, 1.0), 'S'), PO, g, pivot=(LX(330), 0, top), bevel=0, sharp=50, polish=0.5,
           cuts=[bm_box(LX(305.5), LX(312.5), 10.3, 12.5, cz - 2.9, cz + 2.9)])
    ybot = lambda x: 247.5 - (x - 325) * 22.0 / 52.5
    for s, sg in (('l', 1), ('r', -1)):
        for i, fr in enumerate((0.22, 0.5, 0.78)):
            edge = []; y = 147.0
            while True:
                x = interp(MAG_REAR, y) + fr * (interp(MAG_FRONT, y) - interp(MAG_REAR, y))
                if y > ybot(x) - 7: break
                edge.append((x, y)); y += 8.0
            finish(f'mag_rib_{s}_{i + 1}', bm_prism(strip(edge, -1.5, 1.5), sg * (hw - 0.3), sg * (hw + 0.5), 'S'), PO, g, parent='mag_body', bevel=0.25)
    finish('mag_spine_front', bm_prism(strip([(interp(MAG_FRONT, y), y) for y in range(147, 222, 9)], -1.0, 0.55), -4.0, 4.0, 'S'), PO, g, parent='mag_body', bevel=0.2)
    finish('mag_spine_rear', bm_prism(strip([(interp(MAG_REAR, y), y) for y in range(147, 241, 9)], -0.55, 1.0), -4.0, 4.0, 'S'), PO, g, parent='mag_body', bevel=0.2)
    finish('mag_floorplate', bm_prism(PX([(323.0, 242.6), (376.3, 220.2), (378, 225.8), (325.3, 248)]), -hw - 0.9, hw + 0.9, 'S'), PO, g, parent='mag_body', bevel=0.6)
    finish('mag_floorplate_latch', bm_prism(PX([(346, 233.0), (354, 229.6), (354.4, 230.6), (346.4, 234.0)]), -3.5, 3.5, 'S'), PO, g, parent='mag_body', bevel=0.15, seg=1)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'mag_feed_lip_{s}', bm_box(LX(303.5), LX(346), sg * 6.6, sg * 10.9, top - 0.3, top + 5.0), PO, g, parent='mag_body', bevel=0.3)
    finish('mag_follower', bm_box(LX(304.5), LX(355.5), -6.4, 6.4, top - 0.3, top + 0.7), PO, g, parent='mag_body', bevel=0.2, seg=1)
    r0 = LX(305.5)
    for i, (s, z) in enumerate(((2.4, top + 2.0), (-2.4, top - 2.1))):
        finish(f'mag_round_{i + 1}_case', bm_lathe([(r0, 0), (r0, 4.3), (r0 + 0.8, 4.75), (r0 + 36.5, 4.6), (r0 + 40.5, 3.2), (r0 + 44.7, 3.2), (r0 + 44.7, 0)], 20, s0=s, z0=z), 'Brass', g, parent='mag_body', bevel=0)
        finish(f'mag_round_{i + 1}_bullet', bm_lathe([(r0 + 44.5, 0), (r0 + 44.5, 2.85), (r0 + 49, 2.8), (r0 + 53.5, 1.9), (r0 + 56.3, 0.8), (r0 + 57.2, 0)], 20, s0=s, z0=z), 'Copper', g, parent='mag_body', bevel=0)

# ================================================================== buffer tube, stock, buttpad
BUTT_ARC = [(20, 48), (17.5, 51), (15.5, 56), (14, 63), (12.5, 70), (11, 77), (9.5, 84), (8.3, 91), (8, 100), (8.3, 115), (9, 121), (10, 128), (11, 135),
            (12.5, 141), (14, 146), (16, 153), (18, 160), (20.5, 164)]
def build_stock():
    g = 'stock'; tr = P['tube_r']; l0 = P['up_l0']; t1 = P['tube_l1']; hw = P['stock_half']; bh = P['butt_half']
    finish('buffer_tube', bm_lathe([(l0, 13.2), (l0, tr), (t1, tr), (t1, 0), (t1 + 2.5, 0), (t1 + 2.5, 13.2)], 40), A, g, pivot=(0.5 * (l0 + t1), 0, 0), bevel=0.3)
    c0, c1, e1 = LX(186.3), LX(191.3), LX(193.5)
    cuts = [rot(bm_box(c0 - 1, c0 + 2.2, -2.2, 2.2, 13.0, 19.0), (0, 0, 0), (1, 0, 0), 45 + 90 * k) for k in range(4)]
    finish('castle_nut', bm_cyl((c0, 0, 0), (c1, 0, 0), 16.6, 40, r_in=tr), ST, g, bevel=0.3, cuts=cuts)
    finish('receiver_end_plate', join(bm_cyl((c1, 0, 0), (e1, 0, 0), 17.5, 40, r_in=tr), bm_box(c1, e1, -9, 9, -24.0, -15.0)), ST, g, bevel=0.3)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'end_plate_sling_eye_{s}', bm_cyl((c1, sg * 12.5, -21.5), (e1, sg * 12.5, -21.5), 4.4, 20, r_in=2.3), ST, g, bevel=0.3)
    # ---- sliding stock (rest pose = collapsed, as in the right profile photo)
    body = PX([(42, 53), (182, 53), (185, 84), (185, 91.5), (166, 91.5), (161.5, 93), (158, 96), (157, 110), (156.5, 113.8), (109, 113.8),
               (59.3, 163.8), (44.5, 163.8), (43, 100)])
    sf = LX(185.0)
    cuts = [cylL(0, 0, sf + 1, -358.0, tr + 0.2, 40), bm_prism(stadium(LX(51), LX(83), ZY(101.0), ZY(97.5)), -30, 30, 'S')]
    finish('stock_body', bm_loft(body, rounded(hw, 5.0, 2.0), 'S'), PO, g, pivot=(sf, 0, 0), bevel=0, sharp=50, cuts=cuts, polish=0.6)
    finish('stock_front_collar', bm_cyl((sf - 0.2, 0, 0), (sf + 1.0, 0, 0), 17.6, 40, r_in=tr + 0.2), PO, g, parent='stock_body', bevel=0.2, seg=1)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'stock_ridge_{s}', bm_box(LX(50), LX(180), sg * (hw - 0.3), sg * (hw + 0.9), ZY(72.5), ZY(70)), PO, g, parent='stock_body', bevel=0.4, polish=1.0)
        finish(f'stock_label_plate_{s}', bm_box(LX(120), LX(150), sg * (hw - 0.2), sg * (hw + 0.3), ZY(105), ZY(98.5)), PO, g, parent='stock_body', bevel=0.12, seg=1)
        for i in range(5):
            sx, sy = 99.0 - 8.0 * i, 119.0; t = min(158.0 - sy, sx - 50.0)
            rib = PX([(sx, sy), (sx + 2.6, sy), (sx + 2.6 - t, sy + t), (sx - t, sy + t)])
            finish(f'stock_web_rib_{s}_{i + 1}', bm_prism(rib, sg * (hw - 0.3), sg * (hw + 0.7), 'S'), PO, g, parent='stock_body', bevel=0.25)
    lp = (LX(135.0), 0, ZY(113.4))
    finish('stock_latch', bm_prism(PX([(124, 113.9), (135.5, 113.9), (135.5, 116.6), (126, 116.6)]), -6.5, 6.5, 'S'), PO, g, parent='stock_body', pivot=lp, bevel=0.4, polish=1.0)
    finish('stock_latch_pin', join(cylS(LX(134.0), ZY(111.0), hw - 0.4, hw + 0.25, 1.3, 10), cylS(LX(134.0), ZY(111.0), -hw - 0.25, -hw + 0.4, 1.3, 10)), ST, 'fasteners', parent='stock_body', bevel=0.1, seg=1)
    arc5 = [(x + 5.0, y) for x, y in BUTT_ARC]
    plate = [(31, 48), (33, 50), (47, 50), (48, 53), (43, 53.5), (44, 100), (45.5, 163.8)] + arc5[::-1]
    finish('buttplate', bm_loft(PX(plate), rounded(bh, 3.0, 1.5), 'S'), PO, g, parent='stock_body', bevel=0, sharp=50)
    pad = [(x + 1.8, y) for x, y in BUTT_ARC] + [(x + 5.3, y) for x, y in BUTT_ARC[::-1]]
    finish('buttpad', bm_loft(PX(pad), rounded(bh - 1.0, 4.0, 1.2), 'S'), PO, g, parent='stock_body', bevel=0, sharp=50, stipple=0.8, polish=0.3)
    for i in range(22):
        y = 54.0 + i * 4.95; x = interp(BUTT_ARC, y)
        finish(f'buttpad_rib_{i + 1:02d}', bm_box(LX(x), LX(x + 2.5), -bh + 2.0, bh - 2.0, ZY(y + 1.15), ZY(y - 1.15)), PO, g, parent='stock_body', bevel=0.3, seg=1, stipple=0.5)
    for s, sg in (('l', 1), ('r', -1)):
        for i in range(7):
            ya, yb = 60.0 + i * 13.7, 60.0 + (i + 1) * 13.7
            xa, xb = interp(BUTT_ARC, ya) + (8.0 if i % 2 == 0 else 20.0), interp(BUTT_ARC, yb) + (20.0 if i % 2 == 0 else 8.0)
            tr_ = PX([(xa - 1.1, ya), (xa + 1.1, ya), (xb + 1.1, yb), (xb - 1.1, yb)])
            finish(f'buttpad_truss_{s}_{i + 1}', bm_prism(tr_, sg * (bh - 0.3), sg * (bh + 0.8), 'S'), PO, g, parent='stock_body', bevel=0.25, seg=1)
    finish('stock_sling_loop', bm_cyl((LX(37.3), -3.2, ZY(47.6)), (LX(37.3), 3.2, ZY(47.6)), 5.0, 24, r_in=1.9), ST, g, parent='stock_body', bevel=0.4)

# ================================================================== sockets
def build_sockets():
    def sock(name, p, group):
        e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.02
        bpy.context.scene.collection.objects.link(e); e.parent = OBJ[group]; e.location = bl(p); OBJ[name] = e; W[name] = bl(p); GROUP_OF[name] = group
    sock('socket_optic', (-60.0, 0, P['rail_top']), 'upper')
    sock('socket_muzzle', (P['fh_l1'], 0, 0), 'barrel_assembly')
    sock('socket_magazine', (LX(330), 0, ZY(MAG_TOP)), 'lower')
    sock('socket_hand_right', (LX(212), 0, ZY(165)), 'grip')
    sock('socket_hand_left', (110.0, 0, P['rail_bot']), 'handguard')
    sock('socket_ads_eye', (P['up_l0'] - 70.0, 0, P['sight_line']), 'sights')
    sock('socket_eject', (-53.0, -17.0, 2.0), 'upper')

# ================================================================== materials
PROC = dict(  # base colour, worn-edge colour, roughness, metallic, metallic at worn edges, grain height (m), stipple height (m)
    Anodized=((0.034, 0.035, 0.038), (0.36, 0.36, 0.38), 0.50, 0.80, 1.0, 0.000012, 0.0),
    Polymer=((0.028, 0.028, 0.030), (0.085, 0.085, 0.088), 0.62, 0.0, 0.0, 0.000022, 0.00030),
    Steel=((0.150, 0.150, 0.156), (0.50, 0.50, 0.52), 0.56, 0.90, 1.0, 0.000016, 0.0),
)
FLAT = dict(PaintWhite=((0.85, 0.85, 0.83), 0.0, 0.6), PaintRed=((0.55, 0.02, 0.025), 0.0, 0.6), Brass=((0.70, 0.54, 0.20), 1.0, 0.35),
            Copper=((0.56, 0.44, 0.20), 1.0, 0.4), Cavity=((0.004, 0.004, 0.004), 0.0, 0.9))
BAKE = {}

def make_materials():
    for name, (col, metal, rough) in FLAT.items():
        m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
        MATS[name] = m
    for name, (base, wearc, rough, metal, metalw, gh, sh) in PROC.items():
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, Lk = nt.nodes, nt.links; b = N['Principled BSDF']
        MATS[name] = m
        b.inputs['Base Color'].default_value = (*base, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
        if name == 'Polymer': b.inputs['Specular IOR Level'].default_value = 0.3
        if FAST: continue
        tc = N.new('ShaderNodeTexCoord')
        def noise(scale, detail=3.0):
            n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
            Lk.new(tc.outputs['Object'], n.inputs['Vector']); return n.outputs['Fac']
        def mth(op, a, c=None, clamp=False):
            n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
            for i, v in enumerate((a, c)):
                if v is None: continue
                if isinstance(v, (int, float)): n.inputs[i].default_value = v
                else: Lk.new(v, n.inputs[i])
            return n.outputs[0]
        def ramp(v, lo, hi):
            n = N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.inputs[1].default_value = lo; n.inputs[2].default_value = hi
            Lk.new(v, n.inputs[0]); return n.outputs[0]
        def attr(nm):
            a = N.new('ShaderNodeAttribute'); a.attribute_type = 'OBJECT'; a.attribute_name = nm; return a.outputs['Fac']
        def mixc(f, ca, cb):
            n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'
            if isinstance(f, float): n.inputs[0].default_value = f
            else: Lk.new(f, n.inputs[0])
            for i, c in ((6, ca), (7, cb)):
                if isinstance(c, tuple): n.inputs[i].default_value = (*c, 1)
                else: Lk.new(c, n.inputs[i])
            return n.outputs[2]
        grain, mid, blotch = noise(2600.0, 2.0), noise(260.0, 4.0), noise(34.0, 3.0)
        bev = N.new('ShaderNodeBevel'); bev.samples = 8; bev.inputs['Radius'].default_value = 0.0011
        geo = N.new('ShaderNodeNewGeometry'); dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
        Lk.new(bev.outputs['Normal'], dot.inputs[0]); Lk.new(geo.outputs['True Normal'], dot.inputs[1])
        edge = ramp(mth('SUBTRACT', 1.0, dot.outputs['Value']), 0.03, 0.30)
        wear = mth('MULTIPLY', mth('MULTIPLY', edge, ramp(mid, 0.30, 0.62)), attr('wear'), clamp=True)
        pol = mth('MULTIPLY', attr('polish'), ramp(blotch, 0.25, 0.75))
        shade = mixc(blotch, tuple(c * 0.82 for c in base), tuple(c * 1.22 for c in base))
        colr = mixc(mth('MULTIPLY', wear, 0.85), shade, wearc)
        colr = mixc(mth('MULTIPLY', pol, 0.35), colr, tuple(min(1.0, c * 1.6 + 0.012) for c in base))
        r = mth('ADD', rough, mth('MULTIPLY', mth('SUBTRACT', grain, 0.5), 0.14))
        r = mth('ADD', r, mth('MULTIPLY', mth('SUBTRACT', blotch, 0.5), 0.10))
        r = mth('SUBTRACT', r, mth('MULTIPLY', pol, 0.20))
        r = mth('SUBTRACT', r, mth('MULTIPLY', wear, 0.22), clamp=True)
        mt = mth('ADD', metal, mth('MULTIPLY', wear, metalw - metal), clamp=True)
        h = mth('MULTIPLY', grain, gh)
        if sh:
            vor = N.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 1500.0; Lk.new(tc.outputs['Object'], vor.inputs['Vector'])
            h = mth('ADD', h, mth('MULTIPLY', mth('MULTIPLY', mth('SUBTRACT', 0.6, vor.outputs['Distance']), attr('stipple')), sh))
        bump = N.new('ShaderNodeBump'); bump.inputs['Distance'].default_value = 1.0; bump.inputs['Strength'].default_value = 1.0
        Lk.new(h, bump.inputs['Height'])
        Lk.new(colr, b.inputs['Base Color']); Lk.new(r, b.inputs['Roughness']); Lk.new(mt, b.inputs['Metallic']); Lk.new(bump.outputs['Normal'], b.inputs['Normal'])
        em = N.new('ShaderNodeEmission')
        BAKE[name] = dict(mat=m, bsdf=b, em=em, out=N['Material Output'], col=colr, rough=r, metal=mt)

def bake_group(name, objs, res):
    """Unwrap one material group into a shared atlas and bake base colour, roughness, metallic, normal and AO."""
    t0 = time.time(); sc = bpy.context.scene; B = BAKE[name]; nt = B['mat'].node_tree; N, Lk = nt.nodes, nt.links
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.0012, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f'  [{name}] unwrap {len(objs)} objects: {time.time() - t0:.1f}s', flush=True)
    img = bpy.data.images.new(f'{name}_bake', res, res, alpha=False, float_buffer=False); img.colorspace_settings.name = 'Non-Color'
    tex = N.new('ShaderNodeTexImage'); tex.image = img; N.active = tex; tex.select = True
    sc.render.bake.margin = max(2, res // 512); sc.render.bake.use_clear = True; sc.render.bake.use_selected_to_active = False
    def grab():
        a = np.empty(res * res * 4, dtype=np.float32); img.pixels.foreach_get(a); return a.reshape(res, res, 4).copy()
    out = {}
    for key, samples in (('col', 12), ('rough', 6), ('metal', 12)):
        Lk.new(B[key], B['em'].inputs['Color']); Lk.new(B['em'].outputs[0], B['out'].inputs['Surface'])
        sc.cycles.samples = samples; bpy.ops.object.bake(type='EMIT'); out[key] = grab()
    Lk.new(B['bsdf'].outputs[0], B['out'].inputs['Surface'])
    sc.cycles.samples = 8; bpy.ops.object.bake(type='NORMAL'); out['normal'] = grab()
    sc.cycles.samples = 24; bpy.ops.object.bake(type='AO'); out['ao'] = grab()
    N.remove(tex)
    def image(suffix, arr, srgb):
        im = bpy.data.images.new(f'{name}_{suffix}', res, res, alpha=False); im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        a = np.ones((res, res, 4), np.float32); a[..., :3] = arr; im.pixels.foreach_set(a.ravel()); im.pack(); return im
    lin = out['col'][..., :3]
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, 1), 1 / 2.4) - 0.055)   # emit bakes are scene-linear
    ims = dict(base=image('basecolor', srgb, True),
               orm=image('orm', np.stack([out['ao'][..., 0], out['rough'][..., 0], out['metal'][..., 0]], -1), False),
               normal=image('normal', out['normal'][..., :3], False))
    bpy.data.images.remove(img)
    cover = float((out['ao'][..., 0] > 0).mean())
    print(f'  [{name}] baked {res}px in {time.time() - t0:.1f}s, atlas coverage {cover:.2f}', flush=True)
    return ims

def final_material(name, ims):
    """Replace the procedural node tree with the baked PBR texture set (what the GLB carries)."""
    m = MATS[name]; nt = m.node_tree; nt.nodes.clear(); N, Lk = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial'); b = N.new('ShaderNodeBsdfPrincipled'); Lk.new(b.outputs[0], out.inputs['Surface'])
    def tex(im):
        t = N.new('ShaderNodeTexImage'); t.image = im; return t
    Lk.new(tex(ims['base']).outputs['Color'], b.inputs['Base Color'])
    orm = tex(ims['orm']); sep = N.new('ShaderNodeSeparateColor'); Lk.new(orm.outputs['Color'], sep.inputs[0])
    Lk.new(sep.outputs[1], b.inputs['Roughness']); Lk.new(sep.outputs[2], b.inputs['Metallic'])
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree'); grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gn = N.new('ShaderNodeGroup'); gn.node_tree = grp; Lk.new(sep.outputs[0], gn.inputs['Occlusion'])
    if name == 'Polymer': b.inputs['Specular IOR Level'].default_value = 0.3      # black glass-filled polymer: weaker, untinted highlight
    nm = N.new('ShaderNodeNormalMap'); Lk.new(tex(ims['normal']).outputs['Color'], nm.inputs['Color']); Lk.new(nm.outputs['Normal'], b.inputs['Normal'])

def texture_all(res):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False
    w = bpy.data.worlds.new('w'); sc.world = w; w.light_settings.distance = 0.04
    mag = OBJ['mag_body']; rest = mag.location.copy(); mag.location = rest + Vector((0, 0, -0.25))      # bake the magazine out of the well
    sets = {}
    for name in PROC:
        objs = [o for o in OBJ.values() if o.type == 'MESH' and o.data.materials[0] == MATS[name]]
        sets[name] = bake_group(name, objs, res)
    mag.location = rest
    for name, ims in sets.items(): final_material(name, ims)

# ================================================================== animation clips (24 fps, one NLA track per clip)
def key(clip, name, chan, keys):
    """chan: ('loc', 'L'|'S'|'Z') offset in mm from rest, or ('rot', 'X'|'Y') degrees about the Blender axis through the pivot."""
    CLIPS.setdefault(clip, {}).setdefault(name, []).append((chan, keys))

def define_clips():
    ct, st = P['ch_travel'], P['stock_steps']
    key('charge', 'charging_handle', ('loc', 'L'), [(1, 0), (10, -ct), (14, -ct), (22, 0), (30, 0)])
    key('charge', 'bolt_carrier', ('loc', 'L'), [(1, 0), (10, -ct), (14, -ct), (19, 0), (30, 0)])
    key('charge', 'dust_cover', ('rot', 'Y'), [(1, 0), (5, -175), (30, -175)])
    key('dust_cover_open', 'dust_cover', ('rot', 'Y'), [(1, 0), (6, -175), (8, -168), (10, -175)])
    key('mag_release', 'mag_release_button', ('loc', 'S'), [(1, 0), (4, 1.5), (7, 1.5), (10, 0)])
    key('mag_out', 'mag_release_button', ('loc', 'S'), [(1, 0), (3, 1.5), (16, 1.5), (20, 0), (24, 0)])
    key('mag_out', 'mag_body', ('loc', 'Z'), [(1, 0), (3, 0), (14, -80), (24, -200)])
    key('mag_out', 'mag_body', ('loc', 'L'), [(1, 0), (16, 0), (24, -30)])
    key('mag_out', 'mag_body', ('rot', 'X'), [(1, 0), (16, 0), (24, -12)])
    key('mag_in', 'mag_body', ('loc', 'Z'), [(1, -200), (10, -80), (18, 0), (22, 0)])
    key('mag_in', 'mag_body', ('loc', 'L'), [(1, -30), (8, 0), (22, 0)])
    key('mag_in', 'mag_body', ('rot', 'X'), [(1, -12), (8, 0), (22, 0)])
    key('mag_in', 'mag_release_button', ('loc', 'S'), [(1, 0), (10, 0), (13, 1.5), (18, 1.5), (20, 0), (22, 0)])
    key('bolt_catch', 'bolt_catch', ('rot', 'Y'), [(1, 0), (5, 5.5), (8, 5.5), (12, 0)])
    key('safety_to_fire', 'selector_lever_l', ('rot', 'X'), [(1, 0), (6, -90)])
    key('safety_to_safe', 'selector_lever_l', ('rot', 'X'), [(1, -90), (6, 0)])
    key('trigger_pull', 'trigger', ('rot', 'X'), [(1, 0), (4, 6), (6, 6), (10, 0)])
    ext, lat = [(1, 0)], [(1, 0)]; f = 1
    for a, b in zip(st, st[1:]):
        ext += [(f + 5, b), (f + 9, b)]; lat += [(f + 1, -10), (f + 4, -10), (f + 5, 0), (f + 9, 0)]; f += 9
    key('stock_extend', 'stock_body', ('loc', 'L'), ext); key('stock_extend', 'stock_latch', ('rot', 'X'), lat)
    key('stock_collapse', 'stock_body', ('loc', 'L'), [(fr, st[::-1][st.index(v)]) for fr, v in ext])
    key('stock_collapse', 'stock_latch', ('rot', 'X'), lat)
    key('sights_down', 'front_sight_arm', ('rot', 'X'), [(1, 0), (8, 90)]); key('sights_down', 'rear_sight_arm', ('rot', 'X'), [(1, 0), (8, 90)])
    key('sights_up', 'front_sight_arm', ('rot', 'X'), [(1, 90), (8, 0)]); key('sights_up', 'rear_sight_arm', ('rot', 'X'), [(1, 90), (8, 0)])

def bake_clips():
    reg = {}
    for clip, objs in CLIPS.items():
        for name, chans in objs.items():
            o = OBJ[name]; rest = o.location.copy(); o.rotation_mode = 'XYZ'
            ad = o.animation_data_create(); act = bpy.data.actions.new(f'{clip}.{name}'); ad.action = act
            for (kind, ax), keys in chans:
                for fr, v in keys:
                    if kind == 'loc':
                        d = {'L': Vector((0, -v * MM, 0)), 'S': Vector((v * MM, 0, 0)), 'Z': Vector((0, 0, v * MM))}[ax]
                        i = {'L': 1, 'S': 0, 'Z': 2}[ax]; o.location = rest + d; o.keyframe_insert('location', index=i, frame=fr)
                        o.location = rest
                    else:
                        i = 'XYZ'.index(ax); e = [0.0, 0.0, 0.0]; e[i] = math.radians(v); o.rotation_euler = e
                        o.keyframe_insert('rotation_euler', index=i, frame=fr); o.rotation_euler = (0, 0, 0)
            tr = ad.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 1, act); tr.mute = True     # muted: the rest pose stays the rest pose; the exporter still writes every track
            ad.action = None; o.location = rest; o.rotation_euler = (0, 0, 0)
            reg.setdefault(clip, {})[name] = act.name
    return reg

# ================================================================== assemble, export
def build(lod):
    global LOD
    LOD = lod
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for d in (OBJ, W, GROUP_OF, CLIPS, MATS, BAKE): d.clear()
    sc = bpy.context.scene; sc.render.fps = 24; sc.unit_settings.system = 'METRIC'
    make_materials()
    root = bpy.data.objects.new('HK416', None); sc.collection.objects.link(root); OBJ['HK416'] = root; W['HK416'] = Vector((0, 0, 0))
    for gname in GROUPS:
        e = bpy.data.objects.new(gname, None); sc.collection.objects.link(e); e.parent = root; OBJ[gname] = e; W[gname] = Vector((0, 0, 0))
    t0 = time.time()
    for fn in (build_barrel, build_front_sight, build_handguard, build_upper, build_rear_sight, build_charging_handle, build_lower, build_controls,
               build_pins, build_grip, build_magazine, build_stock, build_sockets):
        fn(); print(f'  {fn.__name__}: {len(OBJ)} objects, {time.time() - t0:.1f}s', flush=True)
    meshes = [o for o in OBJ.values() if o.type == 'MESH']
    for o in meshes: _apply(o)
    tris = {}
    for o in meshes:
        o.data.calc_loop_triangles(); tris[o.name] = len(o.data.loop_triangles)
    region = {gname: sum(n for nm, n in tris.items() if GROUP_OF[nm] == gname) for gname in GROUPS}
    print(f'LOD{lod}: {len(meshes)} mesh parts, {sum(tris.values())} triangles', region, flush=True)
    if not FAST: texture_all(2048 if lod == 0 else 1024)
    define_clips(); reg = bake_clips()
    sc.frame_start = 1; sc.frame_end = 60
    sc['hk416_clips'] = json.dumps(reg); sc['hk416_groups'] = json.dumps(GROUP_OF)
    name = 'hk416.glb' if lod == 0 else 'hk416_lod1.glb'
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'work', f'hk416_lod{lod}.blend'))
    bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, name), export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_apply=False, export_yup=True, export_image_format='JPEG', export_jpeg_quality=92)
    json.dump(dict(lod=lod, parts=len(meshes), triangles=sum(tris.values()), by_region=region, by_part=tris, fast=FAST,
                   clips={c: sorted(v) for c, v in reg.items()}), open(os.path.join(HERE, 'work', f'stats_lod{lod}.json'), 'w'), indent=1)

if __name__ == '__main__':
    for lod in LODS:
        t = time.time(); build(lod); print(f'LOD{lod} done in {time.time() - t:.0f}s', flush=True)
