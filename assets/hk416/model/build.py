"""HK416 (HK GmbH configuration, 14.5 in barrel by default), first-person hero weapon. Rebuilds everything from nothing:

    blender -b --python build.py                      # LOD0 + LOD1, baked 2048 px textures  (the deliverable)
    blender -b --python build.py -- --fast            # LOD0 only, flat materials, no bake    (silhouette iteration)
    blender -b --python build.py -- --barrel 16.5     # the 16.5 in barrel exactly as HK's technical drawing shows it
    (or, with Blender as a Python module: python3 build.py -- --fast)

Sources (cited, never committed; see notes/SOURCES.md):
  HKTD   Heckler & Koch, "HK416 Cal. 5.56 mm x 45" technical data brochure, Ident-No. 968 071, V003.12.08, p. 12:
         the dimensioned vector drawing (side view and top view) plus the dimension table (A, B, C, D, E).
  HKA5   Heckler & Koch, "HK416 A5" technical data sheet, Id.Nr. 975584, V002.03.13 (dimensions per barrel length).
  HKMM   Heckler & Koch GmbH, "Rifle HK416 Calibre 5.56 mm x 45" Maintenance Manual (HK416 10/14.5/16.5/20 in),
         Fig. 1a "Illustration of individual components" (97 parts) and Part III disassembly/assembly figures.
  HKUS   Heckler & Koch USA, "Maintenance Manual for HK416 Enhanced Carbine & Rifle System" (2013): specs, tolerances.
  1913   MIL-STD-1913 (Picatinny rail): 10.0 mm pitch, 5.23 mm slot, 21.2 mm rail width, 15.7 mm top flat.

Every outline and position below is in model millimetres measured on HKTD's vector drawing (its lines are vector
paths, so they can be measured to about 0.3 mm on the paper, about 1 mm on the rifle). The drawing shows the
rifle's LEFT side, muzzle left, 16.5 in barrel, stock collapsed. Scale 3.682 mm per drawing point (A = 855 mm and
C = 240 mm from HKTD's table; E and D agree within 1 %). On HKTD p. 12 (PDF points, origin top left):
    side view:  L = (161.55 - x) * 3.682      Z = (613.125 - y) * 3.682
    top view:   L = (426.70 - x) * 3.682      S = (y - 640.52) * 3.682       (the top view shows the right side up)
so every number here can be checked against the drawing. tools/trace_drawing.py re-measures the traced outlines
(drawing_trace.json) from a local copy of HKTD. Numbers that the drawing cannot show (hidden widths, the right
side) come from HKMM's figures, the HK documents above, or MIL-STD-1913, and say so; the few inferences are
marked INFERRED.

Frame (mm while modelling): L along the bore, + toward the muzzle, L = 0 at the upper receiver's front face;
S lateral, + = the rifle's left side; Z up, Z = 0 on the bore axis.
Blender / export frame (metres, Z up, the weapon's front faces -Y as MODELER.md asks): X = S, Y = -L, Z = Z.
"""
import bpy, bmesh, math, json, os, sys, time
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in ARGV
LODS = [int(ARGV[ARGV.index('--lod') + 1])] if '--lod' in ARGV else ([0] if FAST else [0, 1])
BARREL_IN = float(ARGV[ARGV.index('--barrel') + 1]) if '--barrel' in ARGV else 14.5
MM = 0.001
LOD = 0
TRACE = json.load(open(os.path.join(HERE, 'drawing_trace.json')))     # outlines traced from HKTD p. 12 (side view)

# ------------------------------------------------------------------ barrel length (HKTD / HKA5 tables: D = 368 mm at 14.5 in, 419 mm at 16.5 in)
BARREL_D = {10.0: 264.0, 11.0: 279.0, 14.5: 368.0, 16.5: 419.0, 20.0: 505.0}[BARREL_IN]
MUZZLE = 417.8 - (419.0 - BARREL_D)   # HKTD: the D dimension runs from the barrel's muzzle (inside the flash hider) at L = 417.8 to the receiver face
GAS_DL = 0.0                          # the gas block and front sight sit at the handguard's front on the 14.5 and 16.5 in (HKMM Fig. 1a, HKTD)

# ------------------------------------------------------------------ shape numbers (mm, model frame, measured on HKTD unless marked)
P = dict(
    # rails (HKTD side view: lug tops Z 37.1, slot floors 34.4, rail base 32.0; bottom rail -31.1 / -28.5 / -25.4;
    # top view: side-rail lug tops S 28.1, floors 25.5, base 22.4).  1913: 10.0 pitch, 5.23 slot, 21.2 wide, 15.7 top flat.
    rail_pitch=10.0, rail_lug=4.77, rail_top=37.1, rail_floor=34.4, rail_base=32.0, rail_bot=-31.1, rail_bot_floor=-28.5, rail_bot_base=-25.4,
    rail_half_top=7.85, rail_half=10.6, rail_flank=2.0, side_lug=28.1, side_floor=25.5, side_base=22.4,
    upper_lug0=-112.2, hg_lug0=18.0, n_upper_lugs=10, n_hg_lugs=19,     # HKTD: lugs at 18.0 + 10 k (handguard), -22.1 + 10 k (upper)
    # handguard (HKTD: front face 232; side face S 22.4 between Z 24.8 and -20.6; vents in every face, 15.3 either side of its rail)
    hg_l0=0.0, hg_l1=232.0, hg_top=32.0, hg_bot=-25.4, hg_side=22.4, hg_edge_up=24.8, hg_edge_lo=-20.6, hg_face=18.6, hg_wall=3.0,
    hg_vents=[(217.7, 183.5), (168.6, 134.5), (119.7, 85.5), (70.6, 51.4)], hg_vent_off=15.3, hg_vent_h=3.4,
    hg_qd=(211.0, -13.8),
    # barrel assembly (HKTD: barrel 17.6 to 17.8 mm across; flash hider 21.4 across, 47.4 long; gas block 231 to 245.8)
    barrel_r=8.85, barrel_r_rear=9.3, fh_r=10.7, fh_len=47.4, gas_block=(231.0, 245.8), gb_half=10.0, gb_top=25.0, gb_bot=-13.5, gb_lug_bot=-21.5,
    piston_z=15.5, piston_r=4.9, reg_r=4.5, sling_eye=(238.5, 16.5, 6.6, 2.8),
    # upper receiver (HKTD: body S 15.2, rail base 32.0, flank edges Z 27.2 and 21.6, parting line Z -15.9, rear end -152.7)
    up_l0=-152.7, up_l1=0.0, split_z=-15.9, up_half=15.2, bore_r=12.9, carrier_r=12.6,
    port=(-86.0, -21.0, -7.0, 10.0), cover=(-89.5, -17.5, -7.9, 11.7),          # right side: AR-15 pattern port (HKMM Fig. 1a part 2, figs. 52-54) INFERRED size
    hinge=(-18.6, -8.6), ch_floor=17.0, ch_roof=23.2, ch_half=6.3, ch_travel=75.0, carrier_travel=80.0,
    # lower receiver (HKTD side view; widths from the top view: receiver S 15.2, magazine well S 18.0 with a 19.0 flare)
    lo_half=15.2, mw_half=18.0, mw_flare=19.0, mw_cav_half=11.6, mag_half=11.0, mw_l0=-81.0, mw_l1=-13.5,
    selector=(-131.0, -31.0), trigger_pin=(-111.5, -38.5), hammer_pin=(-97.0, -31.0), takedown_pin=(-169.5, -22.5), pivot_pin=(-5.5, -22.5),
    button=(-71.0, -59.0, -27.5, -36.0), catch_z=-31.5, bolt_catch=(-85.0, -9.0),
    guard=(-82.6, -138.4, -50.0, -82.6), guard_in=(-84.5, -132.3, -50.0, -78.6),
    # stock and buffer (HKTD: castle nut -201..-210, Z +-17.5; end plate -193.5..-200.5; stock body S +-29 from -250 back;
    # butt S +-39 (B = 78 mm); buttstock travel 96 mm in 6 positions: HKTD notes)
    tube_r=15.0, tube_l1=-395.0, stock_half=29.0, butt_half=39.0, pad_half=29.6, stock_steps=[0, -19.2, -38.4, -57.6, -76.8, -96.0],
    # sights (HKTD: front sight tower L 234.6..241.8 up to Z 65; rear sight base -116.5..-152.5, drum (-134.4, 37.5); E = 371 mm)
    fs_pivot=(238.2, 26.0), fs_top=65.0, rs_base=(-116.5, -152.5), rs_drum=(-134.4, 37.5), sight_line=57.5,
    grip_half=14.5,                                                              # INFERRED: grip width is hidden in both views (HKMM figs. 18, 20 show it about as wide as the receiver)
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

A, ST, PO = 'Anodized', 'Steel', 'Polymer'

def T(name):
    """A traced HKTD outline (side view), as (L, Z) tuples, counter-clockwise."""
    pts = [tuple(p) for p in TRACE[name]]
    return pts if area2(pts) > 0 else pts[::-1]

def clip_z(poly, zmin=None, zmax=None):
    """Clip a closed (L, Z) outline to a band of heights (Sutherland-Hodgman)."""
    def cut(pts, keep, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            if keep(b):
                if not keep(a): out.append(inter(a, b))
                out.append(b)
            elif keep(a): out.append(inter(a, b))
        return out
    def at(z):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]), z)
    if zmin is not None: poly = cut(poly, lambda p: p[1] >= zmin, at(zmin))
    if zmax is not None: poly = cut(poly, lambda p: p[1] <= zmax, at(zmax))
    return poly

def rail_section(kind):
    """MIL-STD-1913 section in local (u across, v up from the rail base): 'strip' = the continuous dovetail base, 'lug' = one lug."""
    if kind == 'strip': return [(-9.4, 0.0), (9.4, 0.0), (10.6, 1.2), (9.9, 2.4), (-9.9, 2.4), (-10.6, 1.2)]
    return [(-9.9, 2.25), (9.9, 2.25), (10.6, 3.0), (P['rail_half_top'], 5.1), (-P['rail_half_top'], 5.1), (-10.6, 3.0)]

def rail_prism(face, kind, l0, l1):
    """A rail strip or lug between l0 and l1 on one face: top, bottom (handguard), left, right (side rails)."""
    sec = rail_section(kind)
    if face == 'top':    pts = [(u, P['rail_base'] + v) for u, v in sec]
    elif face == 'bottom': pts = [(u, P['rail_bot_base'] - v) for u, v in sec]
    elif face == 'left': pts = [(P['side_base'] + v, u) for u, v in sec]
    else:                pts = [(-(P['side_base'] + v), u) for u, v in sec]
    return bm_prism(pts, l0, l1, 'L')

def rail(face, group, prefix, l0, l1, lug0, n, front_block=None, rear_block=None):
    finish(f'{prefix}_strip', rail_prism(face, 'strip', l0, l1), A, group, bevel=0.25)
    for i in range(n):
        a = lug0 + P['rail_pitch'] * i
        finish(f'{prefix}_lug_{i + 1:02d}', rail_prism(face, 'lug', a, a + 4.6), A, group, bevel=0.22, seg=2)
    if rear_block: finish(f'{prefix}_rear_block', rail_prism(face, 'lug', *rear_block), A, group, bevel=0.22)
    if front_block: finish(f'{prefix}_front_block', rail_prism(face, 'lug', *front_block), A, group, bevel=0.22)

# ================================================================== barrel assembly
def build_barrel():
    g = 'barrel_assembly'; gb0, gb1 = P['gas_block']; m = MUZZLE; sh = m - 16.2; step = m - 47.0
    r, rr = P['barrel_r'], P['barrel_r_rear']
    finish('barrel', bm_lathe([(-20.0, 0), (-20.0, 11.0), (2.0, 11.0), (2.0, rr), (step - 0.6, rr), (step + 0.6, r), (sh, r), (sh, 6.35), (m, 6.35), (m, 0)], 40),
           ST, g, pivot=(0, 0, 0), bevel=0.25)
    finish('barrel_nut', bm_cyl((0.0, 0, 0), (24.0, 0, 0), 14.5, 32, r_in=10.2), ST, g, bevel=0.4)
    # gas block (HKTD side + top: L 231..245.8, S +-10, Z -13.5..25 with the bayonet / GLM lug below to -21.5); HKMM Fig. 1a part 3
    gb = [(-P['gb_half'], P['gb_bot']), (P['gb_half'], P['gb_bot']), (P['gb_half'], P['gb_top'] - 2.0), (P['gb_half'] - 2.0, P['gb_top']),
          (-P['gb_half'] + 2.0, P['gb_top']), (-P['gb_half'], P['gb_top'] - 2.0)]
    finish('gas_block', bm_prism(gb, gb0, gb1, 'L'), ST, g, bevel=0.6, cuts=[cylL(0, 0, gb0 - 1, gb1 + 1, rr + 0.1, 32)])
    finish('gas_block_lug', bm_prism([(-4.0, P['gb_lug_bot']), (4.0, P['gb_lug_bot']), (4.0, P['gb_bot'] + 0.5), (-4.0, P['gb_bot'] + 0.5)], 236.5, gb1, 'L'), ST, g, bevel=0.5)
    for i, l in enumerate((gb0 + 4.0, gb1 - 4.5)):
        finish(f'gas_block_pin_{i + 1}', join(cylS(l, -10.0, P['gb_half'] - 0.4, P['gb_half'] + 0.25, 1.6, 12), cylS(l, -10.0, -P['gb_half'] - 0.25, -P['gb_half'] + 0.4, 1.6, 12)), ST, 'fasteners', bevel=0.12, seg=1)
    # two-position gas regulator (HKMM part 15) at the block's front, on the piston axis
    pz = P['piston_z']; rg = P['reg_r']
    finish('gas_regulator', join(cylL(0, pz, gb1 - 0.3, gb1 + 3.7, rg, 24), cylL(0, pz, gb1 + 3.5, gb1 + 4.3, rg - 0.8, 24)), ST, g, bevel=0.3, polish=0.6,
           cuts=[bm_box(gb1 + 2.4, gb1 + 5, -0.7, 0.7, pz - rg - 1, pz + rg + 1)])
    finish('gas_piston_tube', cylL(0, pz, 24.0, gb0 + 0.3, P['piston_r'], 24), ST, g, bevel=0.3)
    # front sling eyes (HKTD top view: rings centred (238.5, +-16.5), 13.2 mm across, 5.6 mm hole; seen edge-on in the side view at Z -1.4..2.6)
    el, es, eo, ei = P['sling_eye']
    for s, sg in (('l', 1), ('r', -1)):
        eye = join(cylZ(el, sg * es, -1.4, 2.6, eo, 28), bm_box(el - eo, el + eo, sg * (P['gb_half'] - 0.5), sg * es, -1.4, 2.6))
        finish(f'sling_eye_{s}', eye, ST, g, bevel=0.5, cuts=[cylZ(el, sg * es, -3, 5, ei, 20)])
    # flash hider (HKTD: 47.4 long, 21.4 across, three slots visible per side, two rings and a wrench section at the rear); HKMM part 1
    a, b, fr = sh, sh + P['fh_len'], P['fh_r']
    cuts = []
    for k in range(6):
        cuts.append(rot(bm_prism(stadium(a + 20.0, b - 3.0, -1.6, 1.6), 5.0, 13.0, 'Z'), (0, 0, 0), (1, 0, 0), 30 + 60 * k))
    cuts.append(bm_box(a + 1.0, a + 8.5, 9.4, 13.0, -9.0, 9.0)); cuts.append(bm_box(a + 1.0, a + 8.5, -13.0, -9.4, -9.0, 9.0))     # wrench flats
    fh = bm_lathe([(a, 6.3), (a, 9.9), (a + 0.8, fr), (a + 8.0, fr), (a + 8.6, 9.5), (a + 10.4, 9.5), (a + 11.0, fr), (a + 17.4, fr), (a + 18.0, 9.5), (a + 19.6, 9.5),
                   (a + 20.2, fr), (b - 1.2, fr), (b, 9.9), (b, 7.6), (a + 14, 7.6), (a + 12, 6.3)], 36)
    finish('flash_hider', fh, ST, g, bevel=0.3, cuts=cuts if LOD == 0 else cuts[:6])
    finish('crush_washer', bm_lathe([(a - 1.2, 6.4), (a - 1.2, 9.2), (a, 9.4), (a, 6.4)], 32), ST, g, bevel=0.15, seg=1)
    finish('muzzle_bore', cylL(0, 0, m - 0.4, m + 0.3, 2.85, 20), 'Cavity', g, bevel=0)

# ================================================================== front sight (HKTD shows it standing; it folds forward over the gas block)
def build_front_sight():
    g = 'sights'; pl, pz = P['fs_pivot']; top = P['fs_top']; sl = P['sight_line']; bz = P['gb_top']
    base = bm_prism([(pl - 5.8, -8.5), (pl + 5.8, -8.5), (pl + 5.8, -5.0), (pl - 3.6, -5.0), (pl - 3.6, 5.0), (pl + 5.8, 5.0), (pl + 5.8, 8.5), (pl - 5.8, 8.5)],
                    bz - 0.3, pz + 4.0, 'Z')
    finish('front_sight_base', base, ST, g, bevel=0.4)
    tower = [(pl + 3.6 * math.cos(t), pz + 3.6 * math.sin(t)) for t in [math.pi + math.pi * i / 10 for i in range(11)]] + \
            [(pl + 3.6, top - 3.0), (pl + 2.2, top), (pl - 2.2, top), (pl - 3.6, top - 3.0)]
    win = bm_prism([(pl - 1.7, sl - 7.5), (pl + 1.7, sl - 7.5), (pl + 1.7, top - 1.6), (pl - 1.7, top - 1.6)], -9, 9, 'S')
    finish('front_sight_arm', bm_prism(tower, -6.0, 6.0, 'S'), ST, g, pivot=(pl, 0, pz), bevel=0.35,
           cuts=[win, bm_box(pl - 4.5, pl + 4.5, -3.2, 3.2, sl - 7.4, top - 1.5)])
    finish('front_sight_post', join(cylZ(pl, 0, sl - 7.6, sl, 0.85, 12), bm_box(pl - 0.85, pl + 0.85, -0.6, 0.6, sl - 0.8, sl + 0.15)), ST, g, parent='front_sight_arm', bevel=0.1, seg=1, polish=1.0)
    finish('front_sight_detent', cylS(pl, 33.5, 6.0, 7.6, 2.2, 16), ST, g, parent='front_sight_arm', bevel=0.3, polish=1.0)
    for s, sg in (('l', 1), ('r', -1)):
        screw(f'front_sight_pivot_head_{s}', (pl, sg * 8.5, pz), (0, sg, 0), 2.2, 0.7, 'fasteners', kind='pin')

# ================================================================== handguard (HKTD side and top views; HKMM parts 32 to 34)
def hg_outline(inset_d=0.0):
    f, s, t, b, eu, el = P['hg_face'], P['hg_side'], P['hg_top'], P['hg_bot'], P['hg_edge_up'], P['hg_edge_lo']
    pts = [(f, t), (s, eu), (s, el), (f, b), (-f, b), (-s, el), (-s, eu), (-f, t)]
    pts = [(x, z) for x, z in pts]
    return inset(pts[::-1], inset_d)[::-1] if inset_d else pts

def build_handguard():
    g = 'handguard'; l0, l1 = P['hg_l0'], P['hg_l1']; out = hg_outline(); off = P['hg_vent_off']; vh = P['hg_vent_h'] / 2
    cuts = [bm_prism(inset(out, P['hg_wall']), l0 - 1, l1 + 1, 'L')]
    for k, (va, vb) in enumerate(P['hg_vents']):
        for zc in (off, -off):
            vb2 = 190.7 if (k == 0 and zc < 0) else va                       # the lower first vent stops short of the sling cup
            cuts.append(bm_prism(stadium(vb, vb2, zc - vh, zc + vh), -40, 40, 'S'))        # side faces
        for sc in (off, -off):
            cuts.append(bm_prism(stadium(vb, va, sc - vh, sc + vh), -40, 40, 'Z') if False else
                        bm_prism([(vb + vh, sc - vh), (va - vh, sc - vh), (va, sc), (va - vh, sc + vh), (vb + vh, sc + vh), (vb, sc)], -40, 45, 'Z'))   # top and bottom faces
    ql, qz = P['hg_qd']
    cuts.append(cylS(ql, qz, -40, 40, 3.3, 16))
    cres = [(ql + rr * math.cos(math.radians(a)), qz + rr * math.sin(math.radians(a))) for rr, aa in ((6.6, range(200, 345, 14)), (9.6, range(340, 195, -14))) for a in aa]
    cuts.append(bm_prism(cres, -40, 40, 'S'))
    finish('handguard_body', bm_prism(out, l0, l1 - 1.2, 'L'), A, g, pivot=(0, 0, 0), bevel=0.4, cuts=cuts)
    # front cap: the drawing's 45-degree chamfers run from the front face (232) back to the first lugs (222)
    cap = hg_outline(0.6)
    finish('hg_front_cap', bm_prism(cap, l1 - 1.3, l1, 'L'), A, g, bevel=0.35, cuts=[bm_prism(inset(cap, 3.0), l1 - 3, l1 + 1, 'L'), cylL(0, 0, l1 - 3, l1 + 1, 12.0, 32)])
    for face, prefix, fb in (('top', 'hg_rail_top', (208.0, 221.0)), ('bottom', 'hg_rail_bottom', (208.0, 219.5)), ('left', 'hg_rail_left', (208.4, 221.0)), ('right', 'hg_rail_right', (208.4, 221.0))):
        rail(face, g, prefix, l0 + 0.2, fb[1], P['hg_lug0'], P['n_hg_lugs'], front_block=fb, rear_block=(l0 + 0.2, 12.5))
    # retaining bolt boss (HKTD: L 18.7..39.8, Z -12.5..-22; HKMM part 33, the handguard locking screw) and hardware
    bl0, bl1, bz0, bz1 = 18.7, 39.8, -22.0, -12.5; bc = (29.3, -17.3)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'hg_bolt_boss_{s}', bm_box(bl0, bl1, sg * (P['hg_side'] - 2.0), sg * (P['hg_side'] + 1.6), bz0, bz1), A, g, bevel=0.6)
    screw('hg_retaining_bolt', (bc[0], P['hg_side'] + 1.6, bc[1]), (0, 1, 0), 3.4, 1.8, g, kind='hex')
    screw('hg_retaining_bolt_nut', (bc[0], -P['hg_side'] - 1.6, bc[1]), (0, -1, 0), 3.0, 1.0, g, kind='slot')
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'hg_qd_cup_{s}', bm_cyl((ql, sg * (P['hg_side'] - 1.0), qz), (ql, sg * (P['hg_side'] + 3.6), qz), 5.2, 24, r_in=3.3), ST, g, bevel=0.3)
        screw(f'hg_front_screw_{s}', (226.0, sg * P['hg_side'], -16.0), (0, sg, 0), 1.6, 0.6, 'fasteners', kind='hex')

# ================================================================== upper receiver (HKTD; HKMM part 2)
def build_upper():
    g = 'upper'; l0, l1 = P['up_l0'], P['up_l1']; sz = P['split_z']; h = P['up_half']
    half = [(11.2, P['rail_base']), (12.8, 27.2), (h, 21.6), (h, -10.5), (h - 1.4, -13.8), (h - 2.2, sz)]
    sec = half + [(-s, z) for s, z in reversed(half)]
    pl0, pl1, pz0, pz1 = P['port']
    cuts = [cylL(0, 0, l0 - 1, -5.0, P['bore_r'], 40),
            bm_box(l0 - 1, -12.0, -P['ch_half'], P['ch_half'], P['ch_floor'], P['ch_roof']),
            bm_box(pl0, pl1, -22, -9, pz0, pz1)]
    finish('upper_body', bm_prism(sec, l0, l1, 'L'), A, g, pivot=(0, 0, 0), bevel=0.45, cuts=cuts)
    rail('top', g, 'upper_rail', l0 + 0.5, l1, P['upper_lug0'], P['n_upper_lugs'], front_block=(-12.2, l1), rear_block=(-117.7, -113.0))
    # left flank rib with a rounded front (HKTD: L -12..-90, Z -6.1..-15.9)
    rib = [(-90.0, -15.2), (-16.5, -15.2)] + [(-16.5 + 4.5 * math.cos(a), -10.7 + 4.5 * math.sin(a)) for a in [math.radians(-90 + 30 * i) for i in range(7)]] + [(-90.0, -6.2)]
    finish('upper_rib_l', bm_prism(rib, h - 0.3, h + 1.2, 'S'), A, g, bevel=0.45)
    finish('upper_rib_r', bm_box(l0 + 3, pl0 - 6.0, -h - 1.2, -h + 0.3, -15.2, -12.0), A, g, bevel=0.4)
    # right side (HKTD top view): brass deflector apex at L -106, S 31.8 to the right; forward assist housing angled out, its button cap at L -181..-193, S -22.5..-37.5
    finish('brass_deflector', bm_prism([(-91.0, -h + 0.5), (-104.0, -30.8), (-106.0, -31.8), (-108.5, -31.0), (-113.5, -h + 0.5)], 0.5, 13.5, 'Z'), A, g, bevel=0.6)
    fa0, fa1 = (-124.0, -h + 1.0, 6.0), (-180.0, -29.5, 6.0); d = (Vector(fa1) - Vector(fa0)).normalized()
    finish('forward_assist_housing', bm_cyl(fa0, fa1, 5.6, 24), A, g, bevel=0.5)
    finish('forward_assist_button', join(bm_cyl(Vector(fa1) - d * 0.5, Vector(fa1) + d * 3.4, 4.6, 24), bm_cyl(Vector(fa1) + d * 3.2, Vector(fa1) + d * 9.0, 7.2, 28)), ST, 'controls',
           bevel=0.5, polish=1.0)
    pm = Vector(fa0) + d * 32
    finish('forward_assist_pin', cylZ(pm.x, pm.y, pm.z - 5.7, pm.z + 5.7, 1.1, 10), ST, 'fasteners', bevel=0.1, seg=1)
    # dust cover (right side, HKMM parts 18 to 20) and its hinge along the port's lower edge
    hs, hz = P['hinge']; c0, c1, cz0, cz1 = P['cover']
    finish('upper_hinge_lug_rear', bm_box(c0 - 3.6, c0 - 0.4, -h - 4.0, -h + 0.5, hz - 2.2, hz + 2.2), A, g, bevel=0.3)
    finish('upper_hinge_lug_front', bm_box(c1 + 0.4, c1 + 3.6, -h - 4.0, -h + 0.5, hz - 2.2, hz + 2.2), A, g, bevel=0.3)
    hs = -h - 2.0
    finish('dust_cover_hinge_rod', cylL(hs, hz, c0 - 5.0, c1 + 4.6, 1.0, 12), ST, 'fasteners', bevel=0.1, seg=1)
    finish('dust_cover', bm_box(c0, c1, -h - 1.45, -h - 0.25, cz0, cz1), ST, g, pivot=(0.5 * (c0 + c1), hs, hz), bevel=0.3, polish=0.5)
    finish('dust_cover_knuckle_1', cylL(hs, hz, c1 - 22.0, c1, 2.0, 16, r_in=1.15), ST, g, parent='dust_cover', bevel=0.15, seg=1)
    finish('dust_cover_knuckle_2', cylL(hs, hz, c0, c0 + 22.0, 2.0, 16, r_in=1.15), ST, g, parent='dust_cover', bevel=0.15, seg=1)
    finish('dust_cover_latch', bm_box(-61.0, -51.0, -h - 3.1, -h - 1.35, 2.0, 8.5), ST, g, parent='dust_cover', bevel=0.4, polish=1.0)
    finish('dust_cover_rib_1', bm_box(c1 - 27.0, c1 - 5.0, -h - 2.1, -h - 1.35, -3.0, 7.0), ST, g, parent='dust_cover', bevel=0.3)
    finish('dust_cover_rib_2', bm_box(c0 + 5.0, c0 + 25.0, -h - 2.1, -h - 1.35, -3.0, 7.0), ST, g, parent='dust_cover', bevel=0.3)
    sp = [(c0 + 22.6, 1.15)]
    for i in range(12):
        a = c0 + 22.6 + i * 2.2; sp += [(a, 1.9), (a + 1.1, 1.9), (a + 1.1, 1.5), (a + 2.2, 1.5)]
    sp += [(c0 + 22.6 + 26.4, 1.15)]
    finish('dust_cover_spring', bm_lathe(sp, 12, s0=hs, z0=hz), ST, g, bevel=0)
    # bolt carrier group: the outer face that shows through the port (HKMM parts 35 to 46)
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

# ================================================================== rear sight (HKTD: base on the rail L -116.5..-152.5 to Z 50; windage drum (-134.4, 37.5) r 5.6;
# protective ears behind the leaf rising to Z 67 at L -141; the diopter leaf stands leaning 14 degrees forward, L -115..-138, Z 51..67)
def build_rear_sight():
    g = 'sights'; b0, b1 = P['rs_base']; T_ = P['rail_top']; dl, dz = P['rs_drum']; sl = P['sight_line']; top = 50.0
    base = bm_prism([(-12.5, T_ - 5.4), (-10.9, T_ - 5.4), (-10.9, T_ - 0.2), (10.9, T_ - 0.2), (10.9, T_ - 5.4), (12.5, T_ - 5.4), (12.5, top - 1.5), (11.0, top), (-11.0, top), (-12.5, top - 1.5)], b1, b0, 'L')
    finish('rear_sight_base', base, A, g, bevel=0.5, cuts=[bm_box(b0 - 25.0, b0 - 1.5, -8.6, 8.6, top - 3.5, top + 1), cylS(dl, dz, -5, 5, 3.2, 20)])
    ear = [(-136.5, top - 1.0), (-136.5, 64.5), (-139.0, 66.8), (-143.0, 67.0), (-147.5, 64.5), (-151.0, 59.5), (-152.5, 53.0), (-152.5, top - 1.0)]
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'rear_sight_ear_{s}', bm_prism(ear, sg * 8.8, sg * 12.0, 'S'), A, g, bevel=0.5)
        finish(f'rear_sight_drum_{s}', cylS(dl, dz, sg * 12.3, sg * 15.4, 5.6, 32), ST, g, bevel=0.4, polish=1.0)
        knurl = None
        for i in range(18):
            k = rot(bm_box(dl - 0.35, dl + 0.35, sg * 14.0, sg * 15.55, dz + 5.35, dz + 5.85), (dl, 0, dz), (0, 1, 0), i * 20.0)
            knurl = k if knurl is None else join(knurl, k)
        finish(f'rear_sight_drum_knurl_{s}', knurl, ST, g, bevel=0, polish=1.0)
        finish(f'rear_sight_drum_index_{s}', bm_box(dl - 0.4, dl + 0.4, sg * 15.35, sg * 15.5, dz + 1.0, dz + 4.0), 'PaintWhite', g, bevel=0)
    finish('rear_sight_ear_bridge', bm_box(-152.5, -147.0, -12.0, 12.0, top - 1.0, 54.0), A, g, bevel=0.5)
    finish('rear_sight_elevation_knob', cylZ(-145.0, 0, top - 1.0, 55.5, 2.6, 20), ST, g, bevel=0.3, polish=1.0)
    # leaf: drawn in its HKTD pose (leaning 14 degrees forward about its pivot); the aperture is bored along the sight line
    pl, pz = -128.5, top - 0.5
    leaf = rot(bm_prism([(pl + 9.5, pz), (pl - 9.5, pz), (pl - 9.5, pz + 14.5), (pl - 7.0, pz + 16.5), (pl + 7.0, pz + 16.5), (pl + 9.5, pz + 14.5)], -8.2, 8.2, 'S'),
               (pl, 0, pz), (0, 1, 0), 14.0)
    finish('rear_sight_arm', leaf, A, g, pivot=(pl, 0, pz), bevel=0.45, cuts=[cylL(0, sl, pl - 20, pl + 20, 1.0, 20), cylL(0, sl, pl + 1.5, pl + 20, 4.6, 28),
                                                                             cylL(0, sl, pl - 20, pl - 3.0, 4.0, 24)])
    finish('rear_sight_aperture_ring', cylL(0, sl, pl - 4.2, pl - 3.0, 4.0, 24, r_in=1.0), ST, g, parent='rear_sight_arm', bevel=0.15, seg=1)
    screw('rear_sight_clamp_screw', (-122.0, 12.5, T_ - 2.7), (0, 1, 0), 2.6, 1.6, 'fasteners', kind='hex')
    finish('rear_sight_clamp_nut', cylS(-122.0, T_ - 2.7, -14.6, -12.3, 3.0, 6), ST, 'fasteners', bevel=0.2, seg=1)

# ================================================================== charging handle (HKTD: L -152.7..-188, Z 17..31; T bar S +-26 in the top view; HKMM parts 28 to 31)
def build_charging_handle():
    g = 'controls'; l0 = P['up_l0']; f, r = P['ch_floor'], P['ch_roof']; tz1 = 30.5; tb = -188.0
    t_bar = [(tb + 1.5, -26), (tb + 7.0, -26), (tb + 12.0, -18.5), (tb + 12.0, 18.5), (tb + 7.0, 26), (tb + 1.5, 26), (tb, 22), (tb, 9), (tb + 2.0, 6), (tb + 2.0, -6), (tb, -9), (tb, -22)]
    ch = join(bm_prism(t_bar, f + 0.3, tz1, 'Z'), bm_box(tb + 11.0, -20.0, -P['ch_half'] + 0.3, P['ch_half'] - 0.3, f + 0.2, r - 0.4))
    finish('charging_handle', ch, A, g, pivot=(tb + 6.0, 0, 0.5 * (f + tz1)), bevel=0.5, polish=1.0)
    latch = bm_prism([(tb + 1.0, 18.5), (tb + 19.5, 18.5), (tb + 20.6, 17.4), (tb + 22.0, 19.1), (tb + 20.0, 26.5), (tb + 1.0, 26.5)], f + 1.2, tz1 - 1.2, 'Z')
    finish('charging_handle_latch', latch, ST, g, parent='charging_handle', bevel=0.35, polish=1.0, cuts=[bm_box(tb - 1, tb + 12.1, 17.5, 27, f - 1, tz1 + 1)])
    screw('charging_handle_latch_pin', (tb + 5.5, 22.0, tz1), (0, 0, 1), 1.0, 0.25, 'fasteners', kind='roll', parent='charging_handle', n=10)

# ================================================================== lower receiver (HKTD side view; widths from the top view; HKMM part 75)
LOWER_REAR = [(-81.0, -15.9), (-152.7, -15.9), (-152.7, 18.2), (-186.5, 18.2), (-188.5, 15.5), (-188.5, -3.0), (-185.5, -13.0), (-180.0, -23.5),
              (-174.5, -34.0), (-170.0, -45.0), (-167.0, -55.0), (-165.1, -65.5), (-141.5, -82.6), (-138.4, -82.6), (-138.4, -50.0), (-81.0, -50.0)]
LOWER_WELL = [(2.6, -15.9), (-81.0, -15.9), (-81.0, -82.6), (-10.5, -78.0), (-12.5, -71.0), (-12.5, -31.0), (-9.5, -28.6), (-2.0, -28.6), (2.6, -24.5)]
def build_lower():
    g = 'lower'; hw, mw, cav = P['lo_half'], P['mw_half'], P['mw_cav_half']
    body = join(bm_prism(LOWER_REAR, -hw, hw, 'S'), bm_prism(LOWER_WELL, -mw, mw, 'S'))
    m0, m1 = P['mw_l0'] + 0.8, P['mw_l1'] - 0.8
    bl0, bl1, bz0, bz1 = P['button']; cz = P['catch_z']; shaft_l = 0.5 * (bl0 + bl1)
    cuts = [bm_box(m0, m1, -cav, cav, -90.0, P['split_z'] + 2),                        # magazine well
            bm_box(-140.0, -84.0, -8.5, 8.5, -52.0, P['split_z'] + 2),               # fire-control pocket
            bm_box(-124.0, -108.0, -3.6, 3.6, -56.0, -45.0),                          # trigger slot
            bm_box(bl0 - 0.2, bl1 + 0.2, -hw - 2, -hw + 2.2, bz0 - 0.2, bz1 + 0.2),   # magazine button pocket (right)
            cylS(shaft_l, cz, -hw, hw + 2, 2.2, 16)]
    finish('lower_body', body, A, g, pivot=(-80.0, 0, -45.0), bevel=0.45, cuts=cuts)
    # magazine well flare (HKTD: the hook at the well's front foot; top view S 19.0)
    fl = [(-81.0, -82.6), (-10.5, -78.0), (-8.6, -76.6), (-9.2, -73.2), (-12.4, -71.0), (-81.0, -76.0)]
    finish('magwell_flare', bm_prism(fl, -P['mw_flare'], P['mw_flare'], 'S'), A, g, bevel=0.6, cuts=[bm_box(m0, m1, -cav, cav, -95.0, -60.0)])
    # trigger guard ("winter" bow, HKTD: outer L -82.6..-138.4, Z -50..-82.6; opening -84.5..-132.3, -50..-78.6); HKMM part 70
    o0, o1, oz0, oz1 = P['guard']; i0, i1, iz0, iz1 = P['guard_in']
    guard = join(bm_box(o1, o0, -6.0, 6.0, oz1, iz1), bm_box(o1, i1, -6.0, 6.0, iz1 - 0.1, oz0 + 0.5))
    finish('trigger_guard', guard, A, g, bevel=0.7)
    finish('trigger_guard_pin', join(cylS(-134.8, -78.0, 5.5, 6.3, 1.5, 12), cylS(-134.8, -78.0, -6.3, -5.5, 1.5, 12)), ST, 'fasteners', bevel=0.1, seg=1)
    # buffer tower ring at the rear of the lower (HKTD: rear face -188.5)
    finish('lower_buffer_tower', bm_cyl((-186.5, 0, 0), (-188.6, 0, 0), 17.8, 40, r_in=P['tube_r']), A, g, bevel=0.4)
    fence = join(bm_box(bl0 - 2.0, bl0 - 0.2, -hw - 1.8, -hw + 0.2, bz0 - 2.0, bz1 + 2.0), bm_box(bl0 - 2.0, bl1 + 0.2, -hw - 1.8, -hw + 0.2, bz0 - 2.0, bz0 - 0.2),
                 bm_box(bl0 - 2.0, bl1 + 0.2, -hw - 1.8, -hw + 0.2, bz1 + 0.2, bz1 + 2.0))
    finish('mag_release_fence', fence, A, g, bevel=0.3)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'magwell_rib_{s}', bm_box(-79.5, -76.5, sg * (mw - 0.2), sg * (mw + 0.9), -74.0, -36.0), A, g, bevel=0.3)
        finish(f'marking_panel_{s}', bm_box(-72.0, -22.0, sg * (mw - 0.1), sg * (mw + 0.15), -66.0, -40.0), A, g, bevel=0, wear=0.15)

# ================================================================== controls (HKTD side view positions)
def glyph(kind, cl, cz, s, sg):
    """Fire-control pictogram as paint 0.12 mm proud of the receiver wall: a frame plus its symbol."""
    w, h, t = 2.6, 4.2, 0.45; s0, s1 = sg * (s - 0.05), sg * (s + 0.12)
    bars = [(cl - w, cl + w, cz + h - t, cz + h), (cl - w, cl + w, cz - h, cz - h + t), (cl - w, cl - w + t, cz - h + t, cz + h - t), (cl + w - t, cl + w, cz - h + t, cz + h - t)]
    bms = [bm_box(a, b, s0, s1, c, d) for a, b, c, d in bars]
    if kind == 'safe':
        for sgn in (1, -1):
            bms.append(rot(bm_box(cl - 0.22, cl + 0.22, s0 + sg * 0.02 * sgn, s1 + sg * 0.02 * sgn, cz - 3.4, cz + 3.4), (cl, 0, cz), (0, 1, 0), sgn * 28))
    else:
        for k in ([0] if kind == 'semi' else [-1, 0, 1]):
            bms.append(bm_box(cl + k * 1.25 - 0.36, cl + k * 1.25 + 0.36, s0, s1, cz - 2.2, cz + 1.6))
            bms.append(bm_box(cl + k * 1.25 - 0.22, cl + k * 1.25 + 0.22, s0, s1, cz + 1.6, cz + 2.7))
    return join(*bms)

TRIGGER = [(-107.5, -44.0), (-116.0, -44.0), (-120.8, -50.0), (-123.3, -57.5), (-123.0, -65.5), (-120.8, -72.0), (-117.6, -77.0), (-115.4, -76.0),
           (-117.4, -70.5), (-119.0, -63.5), (-118.6, -56.5), (-116.2, -50.5), (-111.0, -46.5)]
def build_controls():
    g = 'controls'; hw, mw = P['lo_half'], P['mw_half']; sl, sz = P['selector']
    # selector (HKTD: hub (-131, -31), lever to the rear reaching L -152); ambidextrous, HKMM parts 57 and 58
    lev = join(cylS(sl, sz, hw + 0.2, hw + 2.4, 5.4, 28), bm_prism([(sl + 1, sz - 2.8), (sl - 21.0, sz - 2.4), (sl - 21.0, sz + 2.4), (sl + 1, sz + 2.8)], hw + 0.2, hw + 4.0, 'S'))
    finish('selector_lever_l', lev, ST, g, pivot=(sl, 0, sz), bevel=0.45, polish=1.0)
    lev = join(cylS(sl, sz, -hw - 2.4, -hw - 0.2, 5.4, 28), bm_prism([(sl + 1, sz - 2.6), (sl - 15.0, sz - 2.2), (sl - 15.0, sz + 2.2), (sl + 1, sz + 2.6)], -hw - 3.6, -hw - 0.2, 'S'))
    finish('selector_lever_r', lev, ST, g, parent='selector_lever_l', bevel=0.45, polish=1.0)
    finish('selector_index_l', bm_box(sl + 1.6, sl + 4.9, hw + 2.35, hw + 2.52, sz - 0.4, sz + 0.4), 'PaintWhite', g, parent='selector_lever_l', bevel=0)
    finish('selector_index_r', bm_box(sl + 1.6, sl + 4.9, -hw - 2.52, -hw - 2.35, sz - 0.4, sz + 0.4), 'PaintWhite', g, parent='selector_lever_l', bevel=0)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'pictogram_safe_{s}', glyph('safe', -136.5, -21.5, hw, sg), 'PaintWhite', g, bevel=0)      # HKTD: framed symbols at (-136.5, -21.5) and (-118.5, -31.5)
        finish(f'pictogram_semi_{s}', glyph('semi', -118.5, -31.5, hw, sg), 'PaintRed', g, bevel=0)
        finish(f'pictogram_auto_{s}', glyph('auto', -121.0, -43.5, hw, sg), 'PaintRed', g, bevel=0)       # INFERRED position (third symbol, hidden behind the hub in HKTD)
    # bolt catch (HKTD: upper paddle (-85, -9), stem down to -32, enlarged lower paddle L -57..-90, Z -32.5..-38; HKMM parts 53 to 56)
    bl, bz = P['bolt_catch']; s0 = hw + 0.15
    bc = join(cylS(bl, bz, s0, s0 + 2.2, 4.9, 24), bm_box(bl - 2.4, bl + 2.4, s0, s0 + 1.8, -33.0, bz), bm_prism(stadium(-90.0, -57.0, -38.0, -32.5), s0, s0 + 1.8, 'S'))
    finish('bolt_catch', bc, ST, g, pivot=(bl, s0, -20.0), bevel=0.45, polish=1.0)
    ribs = join(*[bm_box(-88.0 + 4.2 * i, -86.6 + 4.2 * i, s0 + 1.75, s0 + 2.25, -37.3, -33.2) for i in range(7)])
    finish('bolt_catch_ribs', ribs, ST, g, parent='bolt_catch', bevel=0.15, seg=1, polish=1.0)
    # magazine release (right side, AR-15 pattern, HKMM parts 66 to 69): button, shaft and catch move together along S
    bl0, bl1, bz0, bz1 = P['button']; cz = P['catch_z']; shaft_l = 0.5 * (bl0 + bl1)
    finish('mag_release_button', join(bm_box(bl0, bl1, -hw - 1.8, -hw + 1.0, bz0, bz1), cylS(shaft_l, cz, -hw + 0.5, hw - 1.0, 2.0, 16)), ST, g, pivot=(shaft_l, 0, cz), bevel=0.35, polish=1.0)
    for i in range(3):
        a = bl0 + 1.2 + i * 2.3
        finish(f'mag_button_rib_{i + 1}', bm_box(a, a + 1.2, -hw - 2.3, -hw - 1.7, bz0 + 1.0, bz1 - 1.0), ST, g, parent='mag_release_button', bevel=0.15, seg=1, polish=1.0)
    finish('mag_catch', join(bm_box(bl0, -78.0, hw - 2.6, hw - 0.6, cz - 3.0, cz + 3.0), bm_box(-82.0, -78.6, P['mw_cav_half'] - 0.4, hw - 2.5, cz - 2.2, cz + 2.2)),
           ST, g, parent='mag_release_button', bevel=0.3)
    tl, tz = P['trigger_pin']
    finish('trigger', bm_loft(TRIGGER, [(-3.2, 0.9), (-2.4, 0.0), (2.4, 0.0), (3.2, 0.9)], 'S'), ST, g, pivot=(tl, 0, tz), bevel=0.2, seg=1, polish=1.0)

def build_pins():
    g = 'fasteners'; hw, mw = P['lo_half'], P['mw_half']
    pl, pz = P['pivot_pin']; tl, tz = P['takedown_pin']
    screw('pivot_pin_head_r', (pl, -mw, pz), (0, -1, 0), 3.6, 1.3, g, kind='plain'); screw('pivot_pin_end_l', (pl, mw, pz), (0, 1, 0), 2.9, 0.6, g, kind='pin')
    screw('takedown_pin_head_r', (tl, -hw, tz), (0, -1, 0), 3.6, 1.3, g, kind='plain'); screw('takedown_pin_end_l', (tl, hw, tz), (0, 1, 0), 2.9, 0.6, g, kind='pin')
    for nm, key, r in (('trigger_pin', 'trigger_pin', 1.9), ('hammer_pin', 'hammer_pin', 1.9)):
        l, z = P[key]
        screw(f'{nm}_l', (l, hw, z), (0, 1, 0), r, 0.3, g, kind='pin', n=14); screw(f'{nm}_r', (l, -hw, z), (0, -1, 0), r, 0.3, g, kind='pin', n=14)
    bl, bz = P['bolt_catch']
    finish('bolt_catch_pin', join(cylL(hw + 1.0, -20.0, bl + 4.0, bl + 4.6, 1.1, 10), cylL(hw + 1.0, -20.0, bl - 4.6, bl - 4.0, 1.1, 10)), ST, g, bevel=0.1, seg=1)

def interp(pts, y):
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if (ya - y) * (yb - y) <= 0 and ya != yb:
            return xa + (xb - xa) * (y - ya) / (yb - ya)
    return None

# ================================================================== pistol grip (HKTD traced outline and side panel; HKMM parts 86 to 92)
def build_grip():
    g = 'grip'; hw = P['grip_half']; out = T('grip')
    finish('grip_body', bm_loft(out, rounded(hw, 5.0, 2.2), 'S'), PO, g, pivot=(-180.0, 0, -110.0), bevel=0, sharp=50, polish=0.7)
    panel = T('grip_panel')
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'grip_panel_{s}', bm_prism(inset(panel, 0.4), sg * (hw - 0.25), sg * (hw + 0.5), 'S'), PO, g, bevel=0.35, stipple=1.0, polish=1.0)
    cap = clip_z(out, zmax=-149.0)
    finish('grip_cap', bm_prism(cap, -hw + 1.2, hw - 1.2, 'S'), PO, g, bevel=0.6)
    finish('grip_cap_latch', join(bm_box(-191.0, -176.0, -hw + 0.8, hw - 0.8, -153.4, -151.0), cylS(-181.0, -152.0, -hw + 0.4, hw - 0.4, 1.0, 12)), PO, g, bevel=0.3)

# ================================================================== magazine (HKTD traced outline; HK steel magazine: depth 22 mm, empty 250 g; HKMM parts 93 to 97)
def build_magazine():
    g = 'magazine'; hw = P['mag_half']; cz = P['catch_z']
    out = T('magazine')
    zt = max(p[1] for p in out)
    top = [p for p in out if p[1] > zt - 6.0]; lf, lr = max(p[0] for p in top), min(p[0] for p in top)
    hidden = [(lf - 0.8, zt - 1.0), (lf - 0.8, -33.0), (lr + 0.8, -33.0), (lr + 0.8, zt - 1.0)]       # the part inside the well (hidden; follows the well, HKTD)
    finish('mag_body', bm_loft(out, rounded(hw, 1.6, 1.0), 'S'), ST, g, pivot=(-45.0, 0, -80.0), bevel=0, sharp=50, polish=0.3)
    finish('mag_body_top', bm_prism(hidden, -hw, hw, 'S'), ST, g, parent='mag_body', bevel=0.5, cuts=[bm_box(-82.0, -76.0, hw - 1.6, hw + 1, cz - 2.6, cz + 2.6)])
    # stamped ribs: every traced strip of the drawing is a panel pressed 0.5 mm proud, so the drawing's lines become the grooves between them
    for i in range(8):
        k = f'mag_strip_{i}'
        if k not in TRACE: continue
        st = clip_z(T(k), zmin=-199.0, zmax=zt - 2.0)
        if len(st) < 3: continue
        for s, sg in (('l', 1), ('r', -1)):
            finish(f'mag_panel_{s}_{i + 1}', bm_prism(inset(st, 0.75), sg * (hw - 0.3), sg * (hw + 0.5), 'S'), ST, g, parent='mag_body', bevel=0.35, polish=0.4)
    bot = clip_z(out, zmax=min(p[1] for p in out) + 9.0)
    finish('mag_floorplate', bm_prism(bot, -hw - 1.0, hw + 1.0, 'S'), ST, g, parent='mag_body', bevel=0.7, polish=0.5)
    for s, sg in (('l', 1), ('r', -1)):
        finish(f'mag_feed_lip_{s}', bm_box(lr + 2.0, lf - 20.0, sg * 6.4, sg * 10.6, -34.0, -29.0), ST, g, parent='mag_body', bevel=0.3)
    finish('mag_follower', bm_box(lr + 1.5, lf - 2.0, -6.2, 6.2, -34.5, -33.5), PO, g, parent='mag_body', bevel=0.2, seg=1)
    r0 = lr + 2.0
    for i, (s, z) in enumerate(((2.4, -30.0), (-2.4, -34.1))):
        finish(f'mag_round_{i + 1}_case', bm_lathe([(r0, 0), (r0, 4.3), (r0 + 0.8, 4.75), (r0 + 36.5, 4.6), (r0 + 40.5, 3.2), (r0 + 44.7, 3.2), (r0 + 44.7, 0)], 20, s0=s, z0=z), 'Brass', g, parent='mag_body', bevel=0)
        finish(f'mag_round_{i + 1}_bullet', bm_lathe([(r0 + 44.5, 0), (r0 + 44.5, 2.85), (r0 + 49, 2.8), (r0 + 53.5, 1.9), (r0 + 56.3, 0.8), (r0 + 57.2, 0)], 20, s0=s, z0=z), 'Copper', g, parent='mag_body', bevel=0)

# ================================================================== buffer tube, stock, buttplate and pad (HKTD side + top views; HKMM parts 81 to 83)
STOCK_SIDE = [(-212.0, 19.0), (-366.0, 19.0), (-375.0, -100.0), (-372.0, -106.0), (-351.5, -106.0), (-300.0, -54.5), (-292.5, -49.5), (-287.0, -46.5),
              (-246.5, -46.5), (-243.5, -38.0), (-239.0, -31.5), (-233.0, -27.5), (-226.0, -26.5), (-212.0, -26.5)]
STOCK_TOP = [(-212.0, 19.0), (-222.0, 20.0), (-240.0, 25.8), (-250.0, 29.0), (-372.0, 29.0)]       # (L, half width), HKTD top view
BUTT_SIDE = [(-366.0, 19.0), (-369.0, 26.0), (-376.0, 29.5), (-383.0, 27.0), (-397.5, 26.0), (-401.5, 16.0), (-404.5, -40.0), (-404.5, -92.0), (-401.0, -104.0),
             (-376.0, -106.0), (-372.0, -100.0)]
def build_stock():
    g = 'stock'; tr = P['tube_r']; t1 = P['tube_l1']; hw = P['stock_half']
    finish('buffer_tube', bm_lathe([(-186.0, 13.6), (-186.0, tr), (t1, tr), (t1, 0), (t1 + 2.5, 0), (t1 + 2.5, 13.6)], 40), A, g, pivot=(0.5 * (-186.0 + t1), 0, 0), bevel=0.3)
    c0, c1 = -201.0, -210.0                                 # castle nut (HKTD: -201..-210, Z +-17.5); end plate -193.5..-200.5 with its sling tab to Z -35
    cuts = [rot(bm_box(c1 - 1, c1 + 2.4, -2.4, 2.4, 14.0, 19.0), (0, 0, 0), (1, 0, 0), 45 + 90 * k) for k in range(4)]
    finish('castle_nut', bm_cyl((c0, 0, 0), (c1, 0, 0), 17.5, 40, r_in=tr), ST, g, bevel=0.3, cuts=cuts)
    finish('receiver_end_plate', join(bm_cyl((-193.5, 0, 0), (-200.5, 0, 0), 17.6, 40, r_in=tr), bm_box(-201.5, -194.5, -7.0, 7.0, -35.0, -12.0)), ST, g, bevel=0.35,
           cuts=[cylS(-198.0, -29.5, -10, 10, 2.4, 16)])
    # ---- sliding stock (rest pose = collapsed, as HKTD draws it)
    sf = -212.0
    taper = []
    for sg in (1, -1):
        edge = [(l, sg * w) for l, w in STOCK_TOP]
        outer = [(l, sg * 60.0) for l, w in STOCK_TOP[::-1]]
        taper.append(bm_prism(edge + outer if sg > 0 else (edge + outer)[::-1], -120, 40, 'Z'))
    cuts = [cylL(0, 0, sf + 1, t1 - 5, tr + 0.3, 40)] + taper + [bm_prism(stadium(-365.0, -326.0, -36.2, -32.6), -40, 40, 'S')]
    # side recesses: the drawing's inner lines (cheek rib from (-213, -11) to (-250, -30); lower web)
    for sg in (1, -1):
        cuts.append(bm_prism([(-216.0, -12.5), (-249.0, -28.5), (-249.0, -44.0), (-286.0, -44.0), (-295.0, -50.0), (-344.0, -98.0), (-363.0, -98.0), (-360.0, -30.0), (-268.0, -17.0)],
                             sg * (hw - 2.2), sg * (hw + 5), 'S'))
    finish('stock_body', bm_loft(STOCK_SIDE, rounded(hw, 4.0, 1.6), 'S'), PO, g, pivot=(sf, 0, 0), bevel=0, sharp=50, cuts=cuts, polish=0.6)
    finish('stock_front_collar', bm_cyl((sf - 0.2, 0, 0), (sf + 1.0, 0, 0), 18.6, 40, r_in=tr + 0.3), PO, g, parent='stock_body', bevel=0.2, seg=1)
    # adjustment latch under the stock (HKTD: bar L -245..-290, Z -46.5..-51, pivot knob (-268, -49))
    lp = (-247.0, 0, -48.0)
    finish('stock_latch', bm_prism([(-245.0, -46.3), (-290.0, -46.3), (-290.0, -48.5), (-286.0, -51.2), (-249.0, -51.2), (-245.0, -49.5)], -7.0, 7.0, 'S'), PO, g, parent='stock_body', pivot=lp, bevel=0.5, polish=1.0)
    finish('stock_latch_pin', join(cylS(-268.0, -49.0, 6.9, 7.6, 1.6, 12), cylS(-268.0, -49.0, -7.6, -6.9, 1.6, 12)), ST, 'fasteners', parent='stock_body', bevel=0.1, seg=1)
    # buttplate: HKTD side outline; flange +-39 (B = 78 mm) at its front, rubber pad +-29.6 behind
    bh, ph = P['butt_half'], P['pad_half']
    flange = clip_z([(-366.0, 19.0), (-369.0, 26.0), (-376.0, 29.5), (-372.0, -106.0), (-366.0, -106.0)], zmin=-106.0)
    finish('buttplate_flange', bm_loft([(-363.5, 19.0), (-369.5, 24.0), (-376.0, 25.5), (-381.5, -100.0), (-375.0, -105.5), (-370.0, -103.0)], rounded(bh, 4.0, 1.5), 'S'),
           PO, g, parent='stock_body', bevel=0, sharp=50)
    finish('buttplate', bm_loft(BUTT_SIDE, rounded(ph, 3.0, 1.2), 'S'), PO, g, parent='stock_body', bevel=0, sharp=50,
           cuts=[cylS(-376.0, 23.0, -40, 40, 3.2, 20)] + [bm_prism(tri, sg * (ph - 2.5), sg * (ph + 5), 'S') for sg in (1, -1) for tri in butt_trusses()])
    finish('buttplate_hinge_pin', cylS(-376.0, 23.0, -ph - 0.3, ph + 0.3, 3.1, 20, r_in=1.6), ST, g, parent='stock_body', bevel=0.3)
    # rubber pad ribs on the rear face (HKTD: wavy profile, 4.9 mm pitch from Z 12 down to -100)
    rear = [(-401.5, 16.0), (-404.5, -40.0), (-404.5, -92.0), (-401.0, -104.0)]
    for i in range(23):
        z = 12.0 - i * 4.9; l = interp(rear, z)
        if l is None: continue
        finish(f'buttpad_rib_{i + 1:02d}', bm_prism([(l + 0.5, z - 1.25), (l - 2.0, z - 0.9), (l - 2.0, z + 0.9), (l + 0.5, z + 1.25)], -ph + 2.0, ph - 2.0, 'S'), PO, g,
               parent='stock_body', bevel=0.4, seg=2, stipple=0.5)
    finish('stock_sling_slot_frame', bm_prism(inset(stadium(-365.5, -325.5, -36.7, -32.1), -0.8), -hw - 0.4, hw + 0.4, 'S'), PO, g, parent='stock_body', bevel=0.3,
           cuts=[bm_prism(stadium(-365.0, -326.0, -36.2, -32.6), -40, 40, 'S')])

def butt_trusses():
    """The triangular windows in the buttplate's sides (HKTD: two columns, apex alternating, Z +7 down to -97)."""
    tris = []
    for i in range(9):
        z0 = 7.0 - i * 11.6; z1 = z0 - 10.4
        fl = lambda z: -383.5 - (z - 7.0) * (-6.0 / 107.0)       # the windows lean with the plate
        a, b = fl(z0), fl(z1)
        if i % 2 == 0: tris.append([(a, z0), (a - 9.5, z0), (b - 4.8, z1)])
        else:          tris.append([(a - 4.8, z0), (b - 9.5, z1), (b, z1)])
    return tris

# ================================================================== sockets
def build_sockets():
    def sock(name, p, group):
        e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.02
        bpy.context.scene.collection.objects.link(e); e.parent = OBJ[group]; e.location = bl(p); OBJ[name] = e; W[name] = bl(p); GROUP_OF[name] = group
    sock('socket_optic', (-60.0, 0, P['rail_top']), 'upper')
    sock('socket_muzzle', (MUZZLE - 16.2 + P['fh_len'], 0, 0), 'barrel_assembly')
    sock('socket_magazine', (-45.0, 0, -33.0), 'lower')
    sock('socket_hand_right', (-170.0, 0, -100.0), 'grip')
    sock('socket_hand_left', (110.0, 0, P['rail_bot']), 'handguard')
    sock('socket_ads_eye', (-200.0, 0, P['sight_line']), 'sights')
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
