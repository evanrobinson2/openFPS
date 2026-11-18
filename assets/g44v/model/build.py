"""G44 V (.22 LR blowback pistol): parametric recipe. Rebuilds every part from numbers:

    blender -b --python build.py            # writes <repo>/build/g44v/g44v.glb and .blend (ignored), and inventory.json (committed)

Model frame (mm while modelling): L along the bore, + toward the muzzle, L = 0 at the slide's rear face in battery;
S lateral, + = the pistol's left side; Z up, Z = 0 on the bore axis.
Export frame (glTF, metres): +X = S (shooter's left), +Y up, +Z toward the muzzle, origin on the bore axis at the slide's
rear face.  (In Blender, Z up: X = S, Y = -L, Z = Z.)

Sources.  Outlines in outlines.json were traced from the maker's dimension image (notes/REFERENCES.md, ruler in
outlines.json) by tools/trace_ref.py + tools/outline.py.  Part numbers are those of the manual's component list and exploded
drawing (pp. 36-37).  Every entry of P and every part carries where it came from: 'traced' (outline polygon), 'measured'
(read off a named photo with the stated ruler), 'published' (maker's specification table), or 'inferred' (stated reason).
"""
import bpy, bmesh, math, json, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'build', 'g44v'))     # meshes are build outputs: outside assets/, ignored by git
MM = 0.001
OUT = json.load(open(os.path.join(HERE, 'outlines.json')))
O = OUT['mm']
K_PX, XR, YB = OUT['ruler']['px_per_mm'], OUT['ruler']['x_slide_rear'], OUT['ruler']['y_bore']
def LX(x): return (XR - x) / K_PX        # dimension-image pixel -> L
def ZY(y): return (YB - y) / K_PX        # dimension-image pixel -> Z

# ------------------------------------------------------------------ numbers (value, status, source)
RAKE = math.atan(0.4)                    # 21.8 deg: front strap slope 14.0 mm in 35 mm of height (traced frame outline, Z -55..-90)
UX, UZ = math.sin(RAKE), math.cos(RAKE)  # unit vector up the magazine axis in (L, Z)
P = dict(
    slide_len=(174.0, 'published', 'spec table dim 2; traced 173.6'),
    slide_half_w=(12.75, 'published', 'spec table dim 4: 25.5 mm'),
    slide_top=(ZY(170.0), 'traced', 'dimension image y = 170'),
    slide_bot=(-9.2, 'traced', 'parting line y = 291 (ZY = -9.16)'),
    frame_top=(-9.6, 'traced', 'parting line, 0.4 mm running gap (inferred gap)'),
    frame_half_w=(14.6, 'measured', 'rear view: 163-168 px at 5.647 px/mm (slide width 144 px = 25.5 mm) -> 29.0-29.8 mm'),
    breech_face=(73.0, 'measured', 'slide underside photo (manual p. 27 picture 30): 1500-1560 px of 3610 px = 174 mm; agrees with muzzle - barrel length'),
    port_front=(105.0, 'measured', 'slide top view (manual p. 23 picture 27): 397 px at 3.494 px/mm'),
    port_left=(7.7, 'measured', 'slide top view: hood visible to 27 px left of the centre line'),
    port_bottom=(-1.0, 'inferred', 'right-side port lower edge about mid height (manual p. 23 picture 26, oblique)'),
    barrel_len=(102.0, 'published', 'spec table'),
    muzzle=(174.3, 'measured', 'dimension image: muzzle at px 150, 0.6 mm proud of the traced slide face (px 153.5)'),
    barrel_od=(13.0, 'measured', 'lock-open photo: exposed tube 36 px at 2.78 px/mm'),
    bore_groove_d=(5.6, 'published', '.22 LR groove diameter 0.2205 in nominal (SAAMI Z299.1 rimfire)'),
    chamber_block_top=(9.5, 'inferred', 'hood sits recessed below the slide top (close-up, manual p. 8 pictures 2-3); must pass under the slide roof in recoil'),
    rsa_axis=(-11.3, 'inferred', 'guide rod under the barrel, seated on the barrel lug (manual p. 32 pictures 38-40); height from the nose ring in p. 23 picture 26'),
    lock_open_travel=(42.0, 'measured', 'lock-open photo p. 21 picture 18: slide face 110 px behind the frame face at 2.78 px/mm + 2.6 mm; rear check 42.4'),
    full_travel=(45.0, 'inferred', 'lock-open + 3 mm over-travel so the stop can rise into its notch; not measurable from the photos'),
    takedown_retract=(3.0, 'published', 'manual p. 22 step 8: about 1/8 in / 3 mm'),
    slide_lock_pull=(2.6, 'inferred', 'enough for the plate to clear the barrel lug in this model'),
    trigger_pin=((LX(682.0), ZY(350.0)), 'measured', 'dimension image: pin centre px (682, 350)'),
    housing_pin=((LX(1047.0), ZY(440.0)), 'measured', 'dimension image: pin centre px (1047, 440)'),
    trigger_break_deg=(7.5, 'inferred', 'the traced blade can swing 7.75 deg before it meets the traced guard opening (inventory.json kinematics.trigger_max_deg); real travel is not published'),
    trigger_takeup_deg=(4.5, 'inferred', 'Safe Action pattern: take-up to a wall, then break'),
    trigger_safety_deg=(10.0, 'inferred', 'blade tip flush with the trigger face when pressed'),
    bar_link_r=(9.0, 'inferred', 'trigger bar pinned 9 mm below the trigger pin'),
    striker_precock=(7.5, 'inferred', 'firing pin held part-cocked by the trigger bar with the trigger forward (Safe Action, manual p. 7)'),
    bar_drop=(0.9, 'inferred', 'the bar\'s tab overlaps the firing pin lug by 0.7 mm in this model; the drop clears it by 0.2 mm'),
    fp_safety_lift=(1.5, 'inferred', 'manual p. 7: the trigger bar pushes the firing pin safety up'),
    stop_lift_deg=(3.7, 'inferred', '2 mm rise at the nose, 31 mm behind the pivot'),
    mag_catch_press=(2.4, 'inferred', 'nib must leave the corner notch of the magazine'),
    follower_travel=(78.0, 'inferred', 'count windows 5 / 10 / 15 on the tube in the exploded drawing: about 27 mm per 5 rounds'),
    mag_capacity=(15, 'published', 'spec table: standard 15, optional 10'),
    sight_radius=(158.0, 'published', 'spec table dim 6, adjustable polymer rear sight; dimension line measures 157.6'),
    eye_relief=(450.0, 'inferred', 'eye to rear sight at arm\'s length'),
)
def p(k): return P[k][0]
SL, SW, ZT, ZB, FT, FW, BF = p('slide_len'), p('slide_half_w'), p('slide_top'), p('slide_bot'), p('frame_top'), p('frame_half_w'), p('breech_face')
RSA_Z = p('rsa_axis'); TP = p('trigger_pin'); HP = p('housing_pin')
FP_Z = 2.6                               # firing pin axis: strikes the rim at 12 o'clock (inferred; rim radius 3.5 mm)
FOL_D = 1.6                              # an empty magazine's follower is held this far down by the slide stop lever while the slide is forward (inferred)
CAV = 11.9                               # frame cavity half width (inferred: 2.7 mm walls)
MAGW = 9.6                               # magazine tube half width (inferred: must sit between trigger bar and slide stop arm)
def mag_front(z): return 50.1 + 0.4 * (z + 60.0)     # traced front strap at Z = -60 is L = 57.6; 7.5 mm in front of the tube for the catch bar, which the photograph shows hidden under its pad (v2; v1 had 4.5)
def mag_rear(z): return mag_front(z) - 31.0          # tube depth 31 mm horizontally (inferred from the floor plate length, 43 mm)

MAGWW = 11.0                             # magazine tube half width below its neck (22 mm, the size of the maker's double-stack tubes; inferred, v2)
NECK_Z = -24.0                           # above this the tube is necked to MAGW so the trigger bar and slide stop arms pass beside it (inferred)
def clipz(poly, zmax):
    """the part of a side-view polygon below zmax"""
    out = []
    for (l0, z0), (l1, z1) in zip(poly, poly[1:] + poly[:1]):
        if z0 <= zmax: out.append((l0, z0))
        if (z0 - zmax) * (z1 - zmax) < 0: out.append((l0 + (l1 - l0) * (zmax - z0) / (z1 - z0), zmax))
    return out
def shrink(poly, d):
    cl = sum(q[0] for q in poly) / len(poly); cz = sum(q[1] for q in poly) / len(poly)
    return [(l + math.copysign(d, cl - l), z + math.copysign(d, cz - z)) for l, z in poly]
def hull(pts):
    pts = sorted(set(pts))
    def half(ps):
        h = []
        for q in ps:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0: h.pop()
            h.append(q)
        return h
    lo, up = half(pts), half(pts[::-1]); return lo[:-1] + up[:-1]
def sphere(c, R):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=R)
    for v_ in bm.verts: v_.co = v_.co + Vector(c)
    return bm
def strap(z, rear):
    """L of the traced frame outline's back strap (rear) or front strap at height z, grip only"""
    fr = O['frame']; xs = [l0 + (l1 - l0) * (z - z0) / (z1 - z0) for (l0, z0), (l1, z1) in zip(fr, fr[1:] + fr[:1]) if (z0 - z) * (z1 - z) <= 0 and z0 != z1]
    return min(xs) if rear else max(x for x in xs if x < 66.0)
# ------------------------------------------------------------------ registries
OBJ, W, META, CLIPS, MATS = {}, {}, {}, {}, {}
ATTACH = []      # pairs fixed to each other that touch or embed by design: [a, b, why]; tools/checks.py skips them
def attach(a, b, why): ATTACH.append([a, b, why])

# ------------------------------------------------------------------ mesh kit (model mm; Vector(L, S, Z))
def area2(poly): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
def prism(poly, s0, s1):
    """side-view polygon [(L, Z)...] extruded along S"""
    poly = [tuple(q) for q in poly]
    if area2(poly) < 0: poly = poly[::-1]
    bm = bmesh.new()
    a = [bm.verts.new((l, s0, z)) for l, z in poly]; b = [bm.verts.new((l, s1, z)) for l, z in poly]; n = len(poly)
    bm.faces.new(a); bm.faces.new(b[::-1])
    for i in range(n): bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm
def xsec(poly, l0, l1, taper=None):
    """cross-section polygon [(S, Z)...] extruded along L; taper = (dl, inset) chamfers the l1 end"""
    st = [(l0, 0.0), (l1, 0.0)] if not taper else [(l0, 0.0), (l1 - taper[0], 0.0), (l1, taper[1])]
    bm = bmesh.new(); rings = []
    cs = sum(q[0] for q in poly) / len(poly); cz = sum(q[1] for q in poly) / len(poly)
    for l, ins in st:
        rings.append([bm.verts.new((l, s - math.copysign(min(abs(s - cs), ins), s - cs), z - math.copysign(min(abs(z - cz), ins), z - cz))) for s, z in poly])
    n = len(poly)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n): bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm
def box(l0, l1, s0, s1, z0, z1): return prism([(l0, z0), (l1, z0), (l1, z1), (l0, z1)], s0, s1)
def _basis(d):
    d = Vector(d).normalized(); a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized(); return d, u, d.cross(u)
def cyl(p0, p1, r, n=24, r_in=0.0, r1=None):
    p0, p1 = Vector(p0), Vector(p1); d, u, v = _basis(p1 - p0); r1 = r if r1 is None else r1
    bm = bmesh.new()
    def ring(c, rr): return [bm.verts.new(c + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * rr) for i in range(n)]
    a, b = ring(p0, r), ring(p1, r1)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if r_in > 0:
        c, e = ring(p0, r_in), ring(p1, r_in)
        for i in range(n):
            bm.faces.new((c[i], e[i], e[(i + 1) % n], c[(i + 1) % n]))
            bm.faces.new((a[i], c[i], c[(i + 1) % n], a[(i + 1) % n])); bm.faces.new((b[i], b[(i + 1) % n], e[(i + 1) % n], e[i]))
    else: bm.faces.new(a[::-1]); bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm
def cylS(l, z, s0, s1, r, **kw): return cyl((l, s0, z), (l, s1, z), r, **kw)
def cylL(s, z, l0, l1, r, **kw): return cyl((l0, s, z), (l1, s, z), r, **kw)
def cylZ(l, s, z0, z1, r, **kw): return cyl((l, s, z0), (l, s, z1), r, **kw)
def tube_path(pts, r, n=8):
    """a round wire along a polyline (springs)"""
    pts = [Vector(q) for q in pts]; bm = bmesh.new(); rings = []
    for i, c in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]); d, u, v = _basis(d)
        rings.append([bm.verts.new(c + (u * math.cos(2 * math.pi * j / n) + v * math.sin(2 * math.pi * j / n)) * r) for j in range(n)])
    for r0, r1 in zip(rings, rings[1:]):
        # match the ring phase so the tube does not twist
        k = min(range(n), key=lambda s: sum((r0[j].co - r1[(j + s) % n].co).length for j in range(n)))
        for j in range(n): bm.faces.new((r0[j], r0[(j + 1) % n], r1[(j + 1 + k) % n], r1[(j + k) % n]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm
def helix(p0, axis, length, R, wire, turns, n=14):
    p0 = Vector(p0); d, u, v = _basis(axis); N = int(turns * n)
    return tube_path([p0 + d * (wire + (length - 2 * wire) * i / N) + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * R for i in range(N + 1)], wire / 2, 6)
def join(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new('t'); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out
def union(*bms):
    """boolean union of overlapping solids (join() is only for solids that do not overlap)"""
    o = _raw('u', bms[0], Vector((0, 0, 0)))
    for b in bms[1:]:
        co = _raw('c', b, Vector((0, 0, 0))); m = o.modifiers.new('b', 'BOOLEAN'); m.operation = 'UNION'; m.solver = 'EXACT'; m.object = co
        _apply(o); bpy.data.objects.remove(co)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts: v.co = Vector((-v.co.y / MM, v.co.x / MM, v.co.z / MM))
    me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me); return bm
def bl(q): return Vector((q[1] * MM, -q[0] * MM, q[2] * MM))
def _raw(name, bm, pivot):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for v in bm.verts:
        l, s, z = v.co; v.co = Vector((s * MM, -l * MM, z * MM)) - pivot
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = pivot; return o
def _apply(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = o.data; o.modifiers.clear(); o.data = me; bpy.data.meshes.remove(old); me.name = o.name
def boolean(o, cutter_bm, op='DIFFERENCE'):
    co = _raw('cutter', cutter_bm, Vector((0, 0, 0)))
    m = o.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.solver = 'EXACT'; m.object = co
    _apply(o); bpy.data.objects.remove(co)
def part(name, bm, mat, parent, pivot=None, no=None, src='', status='inferred', cuts=(), adds=(), inter=(), bevel=0.25, seg=2, pre_bevel=None, density=None):
    """bmesh (model mm) -> named object.  pivot (model mm) = the object's origin: the hinge or slide axis of a moving part."""
    assert name not in OBJ, name
    if pivot is None:
        cs = [v.co.copy() for v in bm.verts]; pivot = tuple(sum(c[i] for c in cs) / len(cs) for i in range(3))
    wp = bl(pivot); o = _raw(name, bm, wp)
    if pre_bevel:
        b = o.modifiers.new('pb', 'BEVEL'); b.limit_method = 'ANGLE'; b.angle_limit = math.radians(60); b.width = pre_bevel[0] * MM; b.segments = pre_bevel[1]; _apply(o)
    for a in inter: boolean(o, a, 'INTERSECT')
    for a in adds: boolean(o, a, 'UNION')
    for c in cuts: boolean(o, c)
    me = o.data
    for f in me.polygons: f.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(35))
    if bevel:
        b = o.modifiers.new('bevel', 'BEVEL'); b.limit_method = 'ANGLE'; b.angle_limit = math.radians(35); b.width = bevel * MM; b.segments = seg; b.use_clamp_overlap = True
    wn = o.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True
    me.materials.clear(); me.materials.append(MATS[mat])
    par = OBJ[parent]; o.parent = par; o.location = wp - W[parent]
    OBJ[name] = o; W[name] = wp
    META[name] = dict(part_no=no, material=mat, parent=parent, source=src, status=status, pivot_mm=[round(float(x), 3) for x in pivot],
                      density_g_cm3=density if density is not None else DENS[mat])
    return o
def empty(name, parent, q=(0, 0, 0), kind='PLAIN_AXES'):
    e = bpy.data.objects.new(name, None); e.empty_display_type = kind; e.empty_display_size = 0.01
    bpy.context.scene.collection.objects.link(e); wp = bl(q)
    if parent: e.parent = OBJ[parent]; e.location = wp - W[parent]
    else: e.location = wp
    OBJ[name] = e; W[name] = wp; return e

DENS = dict(Polymer=1.38, PolymerSlide=1.38, Steel=7.85, SteelDark=7.85, Spring=7.85, FollowerOrange=1.38, SightWhite=1.38, Placeholder=1.38)
def make_materials():
    def m(name, col, metal, rough):
        mt = bpy.data.materials.new(name); mt.use_nodes = True; b = mt.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
        mt.diffuse_color = (*col, 1); MATS[name] = mt
    m('Polymer', (0.022, 0.022, 0.024), 0.0, 0.62)          # frame, magazine tube, sights: black glass-filled polymer
    m('PolymerSlide', (0.030, 0.030, 0.032), 0.0, 0.50)     # slide body: matte black polymer (manual p. 8)
    m('SteelDark', (0.045, 0.045, 0.050), 1.0, 0.42)        # treated steel: guide rails, barrel
    m('Steel', (0.42, 0.42, 0.44), 1.0, 0.35)               # bright internal steel
    m('Spring', (0.30, 0.30, 0.32), 1.0, 0.30)
    m('FollowerOrange', (0.85, 0.25, 0.02), 0.0, 0.55)      # orange follower (manual p. 11 picture 4)
    m('SightWhite', (0.85, 0.85, 0.82), 0.0, 0.6)
    m('Placeholder', (0.060, 0.060, 0.064), 0.0, 0.40)      # plain panels where the real pistol carries markings

# ================================================================== slide group (parts 1, 4-16)
def build_slide():
    ch = 3.3                                                 # top chamfer (measured on the rear view: slide shoulder 22 px below the top)
    sec = [(-SW, ZB), (SW, ZB), (SW, ZT - ch), (SW - ch * 1.35, ZT), (-SW + ch * 1.35, ZT), (-SW, ZT - ch)]
    body = xsec(sec, 0.0, SL, taper=(2.5, 1.6))
    tab = box(166.5, 171.0, -5.5, 5.5, -17.5, ZB + 0.5)      # nose lug that carries the recoil spring (measured: ring below the nose, p. 23 picture 26)
    cuts = [box(BF, 171.0, -9.6, 9.6, ZB - 0.5, 9.7),                                      # barrel tunnel, open underneath
            box(BF, p('port_front'), -SW - 1, p('port_left'), p('port_bottom'), ZT + 1),   # ejection port: top and right side
            box(BF - 0.01, 77.0, -2.6, 2.6, 5.0, ZT + 1),                                  # room for the loaded chamber indicator notch
            cylL(0, 0, 169.0, SL + 1, 7.3, n=40),                                          # muzzle hole (0.8 mm radial clearance so the barrel can tilt out, inferred)
            cylL(0, RSA_Z, 165.0, 172.0, 2.4, n=20),                                       # guide rod hole in the nose lug
            box(-1, BF + 0.5, 8.3, 9.6, ZB - 0.5, -6.2), box(-1, BF + 0.5, -9.6, -8.3, ZB - 0.5, -6.2),   # channels for the frame guides
            box(-1, SL + 1, 9.5, 11.1, -8.2, -6.4), box(-1, SL + 1, -11.1, -9.5, -8.2, -6.4),             # rail cuts (manual p. 27 picture 30)
            cylL(0, FP_Z, 1.7, 56.0, 3.0, n=24), cylL(0, FP_Z, 55.9, BF + 0.1, 2.2, n=20),                # firing pin channel
            box(3.0, 26.0, -2.2, 2.2, ZB - 0.5, FP_Z),                                     # slot for the firing pin lug (measured 3-25 mm, p. 27)
            cylZ(66.0, -4.4, ZB - 0.5, 6.0, 2.55, n=20),                                   # firing pin safety bore (measured L 64-68.5, 4.4 mm right of centre)
            cylL(-8.0, 5.5, 1.7, 57.1, 1.7, n=16),                                         # extractor depressor plunger channel (inferred position)
            box(57.2, BF + 0.7, -SW - 1, -9.2, -0.3, 4.7),   # extractor pocket
            box(-1.0, BF + 0.5, 2.8, 5.8, ZB - 0.5, 0.2),                                  # ejector slot, open to the rear so the slide can run forward off the frame
            box(-0.1, 1.8, -7.8, 7.8, ZB - 0.5, 7.0),                                      # slide cover plate seat
            prism([(25.0, ZT - 0.4), (50.0, ZT - 0.4), (50.0, ZT + 1), (25.0, ZT + 1)], -6.5, 6.5),      # recessed top panel
            box(3.0, 15.0, -SW - 1, SW + 1, ZT - 1.2, ZT + 1),                                # rear sight dovetail across the slide (v2)
            box(159.6, 168.0, -2.3, 2.3, ZT - 0.6, ZT + 1),                                    # front sight seat (v2)
            xsec([(-SW - 0.01, -2.8), (-SW + 1.8, -1.0), (-SW - 0.01, -1.0)], 74.0, 104.0)]              # relief along the port's lower edge (v2) (measured, top view 118-205 px)
    for sgn in (1, -1):
        s0, s1 = (SW - 0.8, SW + 1) if sgn > 0 else (-SW - 1, -SW + 0.8)
        for i in range(6):                                   # front serrations: 6 grooves, 6.05 mm pitch (measured px 258 + 35 i, 18 px wide)
            cuts.append(box(LX(276 + 35 * i), LX(258 + 35 * i), s0, s1, ZY(256), ZY(182)))
        for i in range(7):                                   # rear serrations: 7 grooves (px 878 + 35 i)
            cuts.append(box(LX(896 + 35 * i), LX(878 + 35 * i), s0, s1, ZY(256), ZY(182)))
        n0, n1 = (10.9, SW + 1) if sgn > 0 else (-SW - 1, -10.9)
        cuts.append(box(93.0, 106.0, n0, n1, ZB - 0.5, -7.6))  # slide stop notch (measured px 545-618 on the left; mirrored for the ambidextrous lever)
    side = prism([(max(l, 0.0), ZB if z < -8.5 else z) for l, z in O['slide']], -SW - 1, SW + 1)      # the traced side profile gives the nose its shape
    part('p01_slide', body, 'PolymerSlide', 'slide_group', pivot=(0, 0, 0), no='1', inter=[side], adds=[tab], cuts=cuts, bevel=0.35,
         src='traced: outlines.json slide; underside p. 27 picture 30; top view p. 23 picture 27', status='traced', density=2.6)
    # the steel guide rail strips seen along the slide's lower flank (px y 258-288, x 222-1157), serial numbered (manual p. 8)
    for sgn, nm in ((1, 'l'), (-1, 'r')):
        s0, s1 = (SW - 0.05, SW + 0.12) if sgn > 0 else (-SW - 0.12, -SW + 0.05)
        part('p01_slide_guide_rail_' + nm, box(LX(1157), LX(222), s0, s1, ZY(288), ZY(258)), 'SteelDark', 'p01_slide', no='1', bevel=0.05, seg=1,
             src='dimension image px x 222-1157, y 258-288', status='measured')
    # placeholder panels where the slide carries the maker's mark and model text (left side)
    part('placeholder_panel_slide_logo', box(LX(560), LX(493), SW - 0.05, SW + 0.1, ZY(248), ZY(197)), 'Placeholder', 'p01_slide', bevel=0.05, seg=1,
         src='dimension image px 493-560, 197-248: maker\'s mark replaced by a plain panel', status='measured')
    part('placeholder_panel_slide_text', box(LX(835), LX(585), SW - 0.05, SW + 0.1, ZY(240), ZY(205)), 'Placeholder', 'p01_slide', bevel=0.05, seg=1,
         src='dimension image px 585-835, 205-240: model and calibre text replaced by a plain panel', status='measured')
    # 16a front sight, 16b its screw, 15 rear sight
    part('p16a_front_sight', prism([(l, z if z > 12.4 else ZT - 0.55) for l, z in O['front_sight']], -1.9, 1.9), 'Polymer', 'p01_slide', no='16a', src='traced: outlines.json front_sight', status='traced', bevel=0.15)
    part('p16a_front_sight_dot', cylL(0, 14.0, 160.2, 160.5, 1.0, n=16), 'SightWhite', 'p16a_front_sight', no='16a', bevel=0, src='white dot (manual p. 23 picture 27)', status='measured')
    part('p16b_front_sight_screw', union(cylZ(163.8, 0, 8.2, 9.65, 2.1, n=6), cylZ(163.8, 0, 9.6, ZT - 0.05, 1.2, n=12)), 'Steel', 'p01_slide', no='16b',
         src='exploded drawing: screw under the front sight', status='inferred', bevel=0.1, seg=1)
    rs = part('p15_rear_sight', prism([(l, z if z > 12.4 else ZT - 0.05) for l, z in O['rear_sight']], -6.5, 6.5), 'Polymer', 'p01_slide', no='15', src='traced: outlines.json rear_sight; width 13 mm from the top view (p. 23 picture 27; v1 had 17); dovetail base and the two adjusting screws from the top view and p. 10', status='traced',
              adds=[box(3.2, 14.8, -SW + 0.25, SW - 0.25, ZT - 1.15, ZT + 0.02), cylS(9.0, 13.2, -7.1, -6.4, 1.3, n=12), cylZ(11.5, 0.0, 14.0, 14.4 + 0.0, 1.6, n=12)],
              cuts=[box(0, 20, -1.9, 1.9, 13.6, 17.5), box(8.0, 10.0, -7.3, -6.8, 13.0, 13.4), box(10.5, 12.5, -0.25, 0.25, 14.2, 15.0)], bevel=0.15)
    part('p15_rear_sight_outline', join(box(2.6, 2.75, -3.0, -1.95, 13.4, 15.9), box(2.6, 2.75, 1.95, 3.0, 13.4, 15.9), box(2.6, 2.75, -3.0, 3.0, 12.9, 13.55)), 'SightWhite', 'p15_rear_sight',
         no='15', bevel=0, src='white notch outline (rear view)', status='measured')
    # 14 slide cover plate
    part('p14_slide_cover_plate', box(0.0, 1.7, -7.7, 7.7, ZB, 6.9), 'Polymer', 'p01_slide', no='14', src='rear view; exploded drawing', status='measured', bevel=0.3,
         cuts=[box(-0.1, 0.35, -5.5, 5.5, 0.0 + 1.4 * i, 0.7 + 1.4 * i) for i in range(4)] + [box(-1, 3, 2.5, 6.1, ZB - 1, 0.5), box(-1, 3, -2.3, 2.3, ZB - 1, -7.0)])
    # 4 firing pin (moves along L), 5 spacer sleeve, 6 spring, 7 spring cups
    fp = union(cylL(0, FP_Z, 19.0, 56.0, 1.5, n=16), box(19.0, 23.0, -1.9, 1.9, -11.6, FP_Z), cylL(0, FP_Z, 56.0, 72.4, 1.9, n=16),
              prism([(72.4, FP_Z - 0.2), (73.8, FP_Z + 0.1), (73.8, FP_Z + 0.7), (72.4, FP_Z + 1.2)], -0.6, 0.6))
    fo = part('p04_firing_pin', fp, 'Steel', 'p01_slide', pivot=(19.0, 0, FP_Z), no='4', bevel=0.1, seg=1,
              src='lug measured in the underside photo (L 19-23 in the fired position, p. 27); manual p. 30 picture 34; shaft and tip inferred', status='measured')
    fo.location += bl((-p('striker_precock'), 0, 0))     # rest pose: held part-cocked by the trigger bar
    part('p05_spacer_sleeve', cylL(0, FP_Z, 2.2, 30.0, 2.75, n=20, r_in=1.75), 'Polymer', 'p01_slide', no='5', bevel=0, cuts=[box(2.0, 26.5, -2.1, 2.1, -4.0, FP_Z + 0.6)],
         src='exploded drawing item 5', status='inferred')
    part('p06_firing_pin_spring', helix((30.2, 0, FP_Z), (1, 0, 0), 21.6 - p('striker_precock'), 2.25, 0.5, 14), 'Spring', 'p01_slide', pivot=(30.2, 0, FP_Z), no='6', bevel=0,
         src='exploded drawing item 6', status='inferred')
    part('p07_spring_cups', join(cylL(0, FP_Z, 52.0, 54.5, 2.7, n=20, r_in=1.55)), 'Steel', 'p04_firing_pin', no='7', bevel=0, cuts=[box(51, 56, -0.25, 0.25, -2, 8)],
         src='exploded drawing item 7 (two half cups)', status='inferred')
    # 8 firing pin safety (moves up), 9 its spring
    part('p08_firing_pin_safety', cylZ(66.0, -4.4, ZB - 0.4, -3.6, 2.4, n=20), 'Steel', 'p01_slide', pivot=(66.0, -4.4, ZB - 0.4), no='8', bevel=0.3,
         src='underside photo: plunger at L 64-68.5, 4.4 mm right of centre', status='measured')
    part('p09_firing_pin_safety_spring', helix((66.0, -4.4, -3.5), (0, 0, 1), 9.0, 1.5, 0.4, 6), 'Spring', 'p01_slide', pivot=(66.0, -4.4, 5.5), no='9', bevel=0,
         src='exploded drawing item 9', status='inferred')
    # 10 extractor, 11 depressor plunger, 12 its spring, 13 spring-loaded bearing
    ex = union(box(57.5, BF + 0.4, -SW - 0.05, -9.45, 0.0, 4.4), box(BF + 0.05, BF + 1.3, -9.46, -3.3, 0.0, 1.8))        # the bar seen behind the port on the right side (p. 8 picture 1: L 57-76, Z -0.2..4.3)
    part('p10_extractor', ex, 'Steel', 'p01_slide', pivot=(62.0, -11.0, 3.0), no='10', bevel=0.12, seg=1,
         src='right side photo p. 8 picture 1 (bar L 57-76, Z -0.2..4.3); claw named in manual p. 30 picture 34', status='measured')
    part('p11_extractor_depressor_plunger', union(cylL(-8.0, 5.5, 22.0, 55.5, 1.0, n=12), cylL(-8.0, 5.5, 55.3, 56.9, 1.45, n=12), cylL(-8.0, 5.5, 20.5, 22.1, 1.45, n=12)), 'Steel', 'p01_slide',
         no='11', bevel=0, src='exploded drawing item 11', status='inferred')
    part('p12_extractor_depressor_plunger_spring', helix((8.0, -8.0, 5.5), (1, 0, 0), 12.4, 1.15, 0.35, 10), 'Spring', 'p01_slide', no='12', bevel=0, src='exploded drawing item 12', status='inferred')
    part('p13_spring_loaded_bearing', join(cylL(-8.0, 5.5, 1.9, 8.0, 1.45, n=12)), 'Polymer', 'p01_slide', no='13', bevel=0, src='exploded drawing item 13', status='inferred')

# ================================================================== barrel (2) and recoil spring assembly (3)
def build_barrel():
    m = p('muzzle'); r = p('barrel_od') / 2; top = p('chamber_block_top')
    b = cylL(0, 0, p('port_front') - 0.5, m, r, n=40)
    lugs = union(box(BF + 0.05, p('port_front'), -9.3, 9.3, -6.5, top), box(78.0, 92.0, -5.0, 5.0, -15.2, -6.4), box(91.9, 96.5, -4.5, 4.5, -12.6, -6.4))
    cuts = [cylL(0, 0, BF - 1, m + 1, p('bore_groove_d') / 2, n=24),                 # bore
            cylL(0, 0, BF, BF + 1.15, 3.65, n=24),                                   # rim seat
            box(BF, 76.5, -2.2, 2.2, 5.5, top + 1),                                  # loaded chamber indicator notch (manual p. 8)
            box(BF, 75.0, -9.4, -3.0, -2.0, 2.5),                                    # extractor cut
            prism([(BF, -6.6), (BF + 7.0, -6.6), (BF, -1.6)], -2.6, 2.6),            # feed ramp
            cyl((m - 1.0, 0, 0), (m + 0.5, 0, 0), 3.6, n=32, r1=5.2)]                 # recessed muzzle crown (v2; visible in p. 21 picture 18)
    part('p02_barrel', b, 'SteelDark', 'frame_group', pivot=(161.5, 0, 0),      # pivot: where the tube sits in the nose hole once pushed 10 mm forward for removal
         no='2', adds=[lugs], cuts=cuts, bevel=0.3,
         src='length published; tube diameter and muzzle measured (p. 21 picture 18); hood measured in the top view; lugs inferred from the exploded drawing and p. 32', status='measured')
    part('placeholder_panel_barrel_hood', box(80.0, 101.0, -7.0, 5.5, top - 0.05, top + 0.08), 'Placeholder', 'p02_barrel', bevel=0,
         src='hood markings (manual p. 8 pictures 2-3) replaced by a plain panel', status='measured')
    rod = union(cylL(0, RSA_Z, 96.65, 98.0, 3.8, n=24), cylL(0, RSA_Z, 97.9, 165.5, 1.9, n=16))
    part('p03_recoil_spring_assembly', rod, 'Steel', 'frame_group', pivot=(96.5, 0, RSA_Z), no='3', bevel=0.15, seg=1,
         src='exploded drawing item 3; manual p. 23 pictures 24-25; a dual captive spring simplified to one rod and one spring', status='inferred')
    part('p03_recoil_spring', join(helix((98.1, 0, RSA_Z), (1, 0, 0), 20.0, 2.75, 0.8, 8), helix((118.1, 0, RSA_Z), (1, 0, 0), 48.3, 3.55, 0.8, 16)), 'Spring', 'p03_recoil_spring_assembly', pivot=(98.1, 0, RSA_Z), no='3', bevel=0,
         src='exploded drawing item 3: a small-diameter section at the flange end and a larger one toward the muzzle (v2); coil counts are a modelling choice', status='measured')

# ================================================================== frame (17) and what lives in it
TRIGGER_MAX = [None]
def _sl_poly():
    top, bot = Vector((95.35, -13.6)), Vector((91.5, -20.6)); d = (bot - top).normalized(); n = Vector((-d.y, d.x)) * 1.1      # centre line read off the dimension image, 2.2 mm thick
    return [tuple(top - n), tuple(top + n), tuple(bot + n), tuple(bot - n)]
SL_POLY = _sl_poly()
def build_frame():
    fr = [(l, min(z, FT)) for l, z in O['frame']]
    # cavities
    cavA = prism([(4.5, FT + 2), (99.0, FT + 2), (99.0, -24.0), (36.0, -24.0), (31.0, -39.0), (18.2, -39.0), (18.2, -30.0), (16.2, -25.0), (12.5, -20.5), (8.0, -17.5), (4.5, -14.0)], -CAV, CAV)
    well = [(mag_rear(-112) - 0.4, -112.0), (mag_front(-112) + 0.4, -112.0), (mag_front(FT + 2) + 0.4, FT + 2), (mag_rear(FT + 2) - 0.4, FT + 2)]
    gm = lambda z: (mag_front(z) + mag_rear(z)) / 2
    groove = [(gm(-112) - 5.5, -112.0), (gm(-112) + 5.5, -112.0), (gm(-20) + 5.5, -20.0), (gm(-20) - 5.5, -20.0)]
    tpl, tpz = TP; hpl, hpz = HP
    cuts = [cavA,
            box(98.9, 174.0, -7.6, 7.6, -21.0, FT + 2),                                # dust cover channel: recoil spring, slide nose lug
            prism(well, -10.0, 10.0), prism(groove, -12.4, 12.4),                        # magazine well, with side grooves for the loading assists
            prism([(mag_front(-36.0) + 1.9, -36.0), (mag_front(-23.9) + 1.9, -23.9), (95.0, -23.9), (95.0, -31.0), (80.0, -31.0), (72.0, -36.0)], -5.8, 5.8),   # trigger slot, its rear wall parallel to the magazine well
            prism(O['guard_hole'], -FW - 1, FW + 1),                                   # trigger guard opening (traced)
            box(-12.0, 4.6, -2.4, 2.4, -12.2, FT + 2),                                 # notch for the firing pin lug in the rear wall (rear view)
            box(48.5, 60.5, CAV - 0.1, FW + 1, -21.5, FT + 2), box(48.5, 60.5, -FW - 1, -CAV + 0.1, -21.5, FT + 2),   # slide stop lever windows
            box(56.2, 61.7, -FW - 1, FW + 1, -46.0, -39.0),                            # magazine catch hole
            prism(shrink(clipz(well, NECK_Z + 0.6), 0.03), -MAGWW - 0.4, MAGWW + 0.4),                # the well widens below the magazine's neck (v2)
            prism([(LX(883), ZY(508)), (LX(797), ZY(519)), (LX(797), ZY(466)), (LX(878), ZY(451))], FW - 2.5, FW + 1),      # recess the magazine catch pad sinks into
            cylS(tpl, tpz, -FW - 1, FW + 1, 2.15, n=20), cylS(hpl, hpz, -FW - 1, FW + 1, 1.65, n=16),
            cyl((mag_front(-46.5) + 3.0, 0, -46.5), (mag_front(-82.0) + 3.0, 0, -82.0), 0.75, n=10)]     # channel for the magazine catch spring
    cuts.append(prism([(mag_rear(-44) - 2.6, -44.0), (mag_rear(-112) - 2.6, -112.0), (-30.0, -112.0), (-4.3, -90.0), (-2.5, -80.0), (5.0, -65.0), (11.1, -55.0), (15.9, -45.0)], -CAV, CAV))   # hollow backstrap (manual p. 39: modular backstrap frame), 3 mm walls inferred
    for sgn in (1, -1):                                                                # accessory rail groove (px x 200-480, y 350-372) and one cross slot
        s0, s1 = (FW - 2.6, FW + 1) if sgn > 0 else (-FW - 1, -FW + 2.6)
        cuts.append(box(LX(480), LX(200), s0, s1, ZY(372), ZY(350)))
    cuts.append(box(LX(214), LX(196), -FW - 1, FW + 1, -40.0, ZY(395)))                   # rail cross slot (px 196-214)
    seam = [(strap(z, True) + 5.0, z) for z in range(-94, -31, 2)]
    for sgn in (1, -1):
        s0, s1 = (FW - 0.45, FW + 1) if sgn > 0 else (-FW - 1, -FW + 0.45)
        t0, t1 = (8.0, FW + 1) if sgn > 0 else (-FW - 1, -8.0); u0, u1 = (11.0, FW + 1) if sgn > 0 else (-FW - 1, -11.0); d0, d1 = (FW - 0.9, FW + 1) if sgn > 0 else (-FW - 1, -FW + 0.9)
        cuts += [prism(seam + [(l + 0.6, z) for l, z in seam[::-1]], s0, s1),                                   # backstrap seam (v2)
                 prism([(67.5, -29.5), (125.0, -29.5), (125.0, -53.0), (66.0, -53.0), (66.0, -44.0), (67.5, -40.0)], t0, t1),      # the trigger guard is 16 mm wide, the frame 29 (v2)
                 prism([(67.5, -27.5), (125.0, -27.5), (125.0, -29.6), (67.5, -29.6)], u0, u1),
                 prism([(LX(500), -9.0), (175.0, -9.0), (175.0, -24.6), (LX(480), -24.6)], d0, d1),             # dust cover stepped in 0.9 mm ahead of px 480-500 (v2)
                 sphere((62.0, sgn * (FW + 40.0 - 0.8), -30.0), 40.0),                                         # thumb rest: a shallow spherical dish, 16 mm across, 0.8 mm deep (v2; size inferred from p. 8 picture 1)
                 prism(hull([(l + a_, z + b_) for l, z in SL_POLY for a_ in (-0.7, 0.7) for b_ in (0.7, -3.1)]), (FW - 0.86) if sgn > 0 else (-FW - 1), (FW + 1) if sgn > 0 else (-FW + 0.86)),            # recess the slide lock's finger tab moves in (v2)
                 cylS(tpl, tpz, (FW - 0.35) if sgn > 0 else (-FW - 1), (FW + 1) if sgn > 0 else (-FW + 0.35), 2.8, n=20),               # pin heads sit in shallow counterbores (v2)
                 cylS(hpl, hpz, (FW - 0.35) if sgn > 0 else (-FW - 1), (FW + 1) if sgn > 0 else (-FW + 0.35), 2.2, n=16)]
    # the round recess low in the back strap (rear view) is not cut: every cutter tried there left the frame mesh open (v2, omitted)
    nose = prism([(169.0, FT), (172.9, FT), (172.9, -16.5), (172.5, -18.5), (171.0, -21.0), (169.0, -22.9)], -FW, FW)     # front of the dust cover (outlines.json outer_smooth; the frame polygon was cropped at px 168)
    part('p17_frame', prism(fr, -FW, FW), 'Polymer', 'frame_group', pivot=(0, 0, 0), no='17', adds=[nose], cuts=cuts, pre_bevel=(3.2, 4), bevel=0.3,
         src='traced: outlines.json frame and guard_hole; width from the rear view; cavities inferred', status='traced')
    part('placeholder_panel_grip_l', box(LX(1095), LX(1030), FW - 0.05, FW + 0.1, ZY(715), ZY(660)), 'Placeholder', 'p17_frame', bevel=0.05, seg=1,
         src='dimension image px 1030-1095, 660-715: maker\'s mark on the grip replaced by a plain panel', status='measured')
    part('placeholder_panel_grip_r', box(10.9, 32.6, -FW - 0.1, -FW + 0.05, -83.9, -74.9), 'Placeholder', 'p17_frame', bevel=0.05, seg=1,
         src='right side photo p. 8 picture 1: two-line text plate low on the grip replaced by a plain panel (v2)', status='measured')
    part('placeholder_panel_frame_mark_l', box(LX(508), LX(483), FW - 0.95, FW - 0.8, ZY(342), ZY(317)), 'Placeholder', 'p17_frame', bevel=0.05, seg=1,
         src='dimension image px 483-508, 317-342: model mark on the dust cover replaced by a plain panel (v2)', status='measured')
    for sgn, nm in ((1, 'l'), (-1, 'r')):
        # hardened steel guides (manual p. 6), four tabs that run in the slide's rail cuts
        for l0, l1, tag in ((30.0, 42.0, 'rear'), (108.0, 118.0, 'front')):
            g = union(box(l0, l1, sgn * 9.0, sgn * 12.6, FT - 1.0, FT), box(l0, l1, sgn * 8.55, sgn * 9.35, FT - 0.01, -6.6), box(l0, l1, sgn * 9.34, sgn * 10.9, -7.9, -6.7)) if sgn > 0 else \
                union(box(l0, l1, -12.6, -9.0, FT - 1.0, FT), box(l0, l1, -9.35, -8.55, FT - 0.01, -6.6), box(l0, l1, -10.9, -9.34, -7.9, -6.7))
            part(f'p17_frame_guide_{tag}_{nm}', g, 'SteelDark', 'p17_frame', no='17', bevel=0.08, seg=1, src='manual p. 6 (steel guides in the polymer frame); position inferred', status='inferred')
    # 28 trigger pin, 29 trigger housing pin (short)
    part('p28_trigger_pin', cylS(tpl, tpz, -FW + 0.2, FW - 0.2, 2.0, n=20), 'SteelDark', 'p17_frame', no='28', bevel=0.15, seg=1, src='dimension image px (682, 350)', status='measured')
    part('p29_trigger_housing_pin', cylS(hpl, hpz, -FW + 0.3, FW - 0.3, 1.5, n=16), 'Polymer', 'p17_frame', no='29', bevel=0.15, seg=1, src='dimension image px (1047, 440); manual p. 38', status='measured')
    # 22 locking block
    ck = [(76.0, -10.2), (98.6, -10.2), (98.6, -23.5), (97.4, -23.5), (97.4, -12.2), (89.6, -12.2), (89.6, -23.5), (76.0, -23.5)]
    lb = union(prism(ck, 6.0, 9.9), prism(ck, -9.9, -6.0), box(97.4, 98.6, -6.01, 6.01, -23.5, -16.5))
    part('p22_locking_block', lb, 'SteelDark', 'p17_frame', no='22', cuts=[cylS(tpl, tpz, -12, 12, 2.15, n=20)], bevel=0.2, seg=1,
         src='exploded drawing item 22; position from the trigger pin and slide lock in the dimension image', status='inferred')
    # 21 slide lock (pulled down to strip), 20 its spring
    part('p21_slide_lock', join(prism(SL_POLY, -11.6, 11.6), prism(SL_POLY, FW - 0.85, FW + 0.25), prism(SL_POLY, -FW - 0.25, -FW + 0.85)), 'SteelDark', 'p17_frame', pivot=(93.4, 0, -17.0), no='21', bevel=0.12, seg=1,
         src='dimension image px 600-632, 310-360: a thin bar leaning 29 deg, top toward the muzzle, in a recess (v2; v1 drew a square pad); manual p. 22 picture 23. The necks that join the two finger tabs to the plate through the frame walls are not modelled, so the walls need no see-through slot', status='measured')
    part('p20_slide_lock_spring', helix((95.9, 0, -23.8), (0, 0, 1), 7.5, 0.6, 0.3, 5.0), 'Spring', 'p17_frame', pivot=(95.9, 0, -23.8), no='20', bevel=0,
         src='exploded drawing item 20', status='inferred', )
    # 23 trigger mechanism housing with ejector
    hs = prism([(11.0, -18.5), (34.0, -18.5), (32.3, -24.0), (27.1, -38.5), (18.7, -38.5), (18.7, -30.0), (17.2, -25.5), (13.8, -21.3), (11.0, -19.0)], -11.4, 11.4)
    ej = prism([(20.0, -18.6), (29.0, -18.6), (36.0, -11.2), (58.0, -3.5), (58.0, -0.8), (55.5, -0.8), (34.0, -9.9), (26.0, -12.2), (20.0, -12.2)], 3.4, 5.2)
    part('p23_trigger_mechanism_housing', hs, 'Polymer', 'p17_frame', no='23', adds=[ej], cuts=[cylS(hpl, hpz, -12, 12, 1.65, n=16)], bevel=0.2, seg=1,
         src='exploded drawing item 23; ejector named in manual p. 31 picture 35; shape inferred', status='inferred')
    # 24 connector
    part('p24_connector', box(14.0, 23.0, -11.3, -10.5, -18.3, -16.2), 'Steel', 'p17_frame', no='24', bevel=0.1, seg=1,
         src='exploded drawing item 24; manual p. 28 picture 32 (right rear corner of the frame); simplified to a strip', status='inferred')
    # 26 trigger with trigger bar: the trigger (pivots on the trigger pin), its safety blade, the bar (slides, then drops)
    tr = [tuple(q) for q in O['trigger']]
    hub = union(cylS(tpl, tpz, -4.0, 4.0, 3.2, n=24), prism([(tpl - 2.6, tpz - 2.2), (tpl + 3.0, tpz - 1.5), (86.0, -29.5), (76.0, -29.5)], -3.4, 3.4))
    def face(z):                                            # front face of the traced trigger at height z
        xs = [l0 + (l1 - l0) * (z - z0) / (z1 - z0) for (l0, z0), (l1, z1) in zip(tr, tr[1:] + tr[:1]) if (z0 - z) * (z1 - z) <= 0 and z0 != z1]
        return max(xs)
    zs = [-45.0 + 0.5 * i for i in range(23)]                # the blade spans Z -45 .. -34
    cl_ = lambda z: min(max(z, zs[0]), zs[-1])
    saf_poly = [(face(z), z) for z in zs] + [(face(z) - 4.0, z) for z in zs[::-1]]       # the traced face is the proud safety blade; the trigger face lies 2 mm behind it
    recess = [(face(cl_(z)) + 3.0, z) for z in [zs[0] - 0.6] + zs + [zs[-1] + 0.6]] + [(face(cl_(z)) - 2.0, z) for z in ([zs[0] - 0.6] + zs + [zs[-1] + 0.6])[::-1]]
    ze = [zs[0] - 4.0] + zs + [zs[-1] + 1.5]; cl = lambda z: min(max(z, zs[0]), zs[-1])
    slot_poly = [(face(cl(z)) + 4.0, z) for z in ze] + [(face(cl(z)) - 6.4, z) for z in ze[::-1]]
    part('p26_trigger', prism(tr, -3.4, 3.4), 'Polymer', 'p17_frame', pivot=(tpl, 0, tpz), no='26', adds=[hub], cuts=[prism(slot_poly, -1.0, 1.0), prism(recess, -5, 5), cylS(tpl, tpz, -5, 5, 2.15, n=20)],
         bevel=0.5, src='traced: outlines.json trigger; hub to the pin inferred', status='traced')
    part('p26_trigger_safety', prism(saf_poly, -0.8, 0.8), 'Polymer', 'p26_trigger', pivot=(face(-34.0) - 3.0, 0, -34.0), no='26', bevel=0.15, seg=1,
         src='manual p. 7 and p. 9 (trigger safety lever in the trigger); the traced outline is the blade, 2 mm proud of the trigger face', status='inferred')
    leg = [(72.8, -11.9), (76.5, -11.9), (80.6, -26.5), (81.0, -29.8), (78.0, -29.8), (77.0, -26.5), (73.5, -14.4), (72.8, -14.4)]
    bar = union(prism(leg, -5.6, -4.3), box(72.8, 75.5, -11.6, -4.3, -14.4, -11.9), box(9.0, 75.5, -11.6, -10.2, -13.6, -11.1),       # leg, jog, run on the right side
               box(9.0, 17.7, -11.6, 3.0, -13.2, -11.9), box(15.7, 17.7, -1.5, 1.5, -11.91, -10.9),                              # cruciform plate and the tab that holds the firing pin lug
               box(64.5, 67.5, -10.21, -3.2, -11.5, -9.9))                                                                       # finger under the firing pin safety
    part('p26_trigger_bar', bar, 'Steel', 'p17_frame', pivot=(79.5, -5.0, -28.2), no='26', bevel=0.1, seg=1,
         src='manual p. 7 (trigger bar: holds the firing pin, lifts the firing pin safety, drops on the ramp); exploded drawing item 26; routing inferred', status='inferred')
    # 27 slide stop lever (both sides), pivots on the trigger pin
    arms = []
    for sgn in (1, -1):
        a, b = (10.4, 11.6) if sgn > 0 else (-11.6, -10.4)
        w0, w1 = (10.4, FW + 1.5) if sgn > 0 else (-FW - 1.5, -10.4)
        arms += [box(50.0, tpl, a, b, -20.5, -18.3), cylS(tpl, tpz, a, b, 3.4, n=20),
                 box(50.0, 59.2, w0, w1, -20.5, -15.0 if sgn > 0 else -16.8),                                       # through the window (lower on the right, under the trigger bar)
                 box(LX(870), LX(815), sgn * (FW + 0.05) if sgn > 0 else -FW - 1.5, FW + 1.5 if sgn > 0 else -FW - 0.05, ZY(325) if sgn > 0 else -16.9, FT - 0.3)]   # thumb pad (px 815-870, 290-325)
    arms += [box(51.0, 54.0, 11.0, 12.5, -15.1, FT - 0.3), box(56.0, 59.0, 10.4, 11.6, -18.4, -13.8), box(56.0, 59.0, 7.5, 10.41, -14.8, -13.8)]     # nose under the slide notch; nub over the follower
    part('p27_slide_stop_lever', union(*arms), 'SteelDark', 'p17_frame', pivot=(tpl, 0, tpz), no='27', bevel=0.12, seg=1,
         cuts=[cylS(tpl, tpz, -17, 17, 2.15, n=20)] + [box(LX(872), LX(813), a, b, z, z + 0.6) for z in (-11.6, -13.3) for a, b in ((FW + 1.0, FW + 2), (-FW - 2, -FW - 1.0))],    # three ribs on each pad
        
         src='dimension image px 815-870, 290-325 (pad); rear view shows a pad on each side; arms inferred', status='measured')
    # 19 magazine catch (reversible, button on the left), 18 its spring
    mc = union(box(58.8, 61.4, -FW + 0.3, FW + 0.1, -45.5, -39.5), box(56.6, 58.81, -10.8, -9.0, -44.8, -40.6),
              prism([(LX(880), ZY(505)), (LX(800), ZY(515)), (LX(800), ZY(470)), (LX(875), ZY(455))], FW + 0.05, FW + 1.6))
    part('p19_magazine_catch', mc, 'Polymer', 'p17_frame', pivot=(60.0, 0, -42.5), no='19', bevel=0.12, seg=1,
         cuts=[box(l, l + 0.7, FW + 1.05, FW + 2, -52.0, -36.0) for l in (49.5, 51.4, 53.3, 55.2, 57.1, 59.0, 60.9)],          # vertical ribs on the pad
        
         src='dimension image px 800-880, 455-515 (pad); manual p. 40; bar and nib inferred', status='measured')
    part('p18_magazine_catch_spring', cyl((mag_front(-46.6) + 3.0, 0, -46.6), (mag_front(-81.0) + 3.0, 0, -81.0), 0.4, n=8), 'Spring', 'p17_frame', no='18', bevel=0,
         src='manual p. 40 pictures 53-54: a straight wire in the front strap', status='inferred')

def build_grip_texture():
    # raised square studs over the whole grip (v2): side panels, front strap and back strap.  Pitch 2.4 mm (14 px in the dimension image), rows
    # along the grip axis.  Side panels run from 3.5 mm inside the front strap to 6 mm inside the back strap (the seam), from Z -93 up to a top edge
    # that falls toward the front (dimension image px (1030, 470) to (880, 500)); the marking panels and the magazine catch are left clear.
    def side_ok(l, z, sgn):
        if not (-93.0 < z < -40.0 - max(l - 22.0, 0.0) * 0.2): return False
        if not (strap(z, True) + 6.2 < l < strap(z, False) - 3.5): return False
        if sgn > 0 and LX(1100) < l < LX(1025) and ZY(720) < z < ZY(655): return False
        if sgn < 0 and 9.9 < l < 33.6 and -84.9 < z < -73.9: return False
        if sgn > 0 and LX(890) < l < LX(790) and ZY(525) < z < ZY(445): return False
        if sgn < 0 and 54.0 < l < 63.5 and -47.5 < z < -37.5: return False
        return True
    grid = [(30.0 + i * 2.4 * UZ + j * 2.4 * UX, -60.0 - i * 2.4 * UX + j * 2.4 * UZ) for i in range(-40, 60) for j in range(-70, 10)]
    def add(bm, t):
        me = bpy.data.meshes.new('t'); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    for sgn, nm in ((1, 'l'), (-1, 'r')):
        bm = bmesh.new(); s0, s1 = (FW - 0.1, FW + 0.45) if sgn > 0 else (-FW - 0.45, -FW + 0.1); d = 0.6
        for l, z in grid:
            if side_ok(l, z, sgn): add(bm, prism([(l + a * d * UZ + b * d * UX, z - a * d * UX + b * d * UZ) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))], s0, s1))
        part('p17_frame_grip_texture_' + nm, bm, 'Polymer', 'p17_frame', pivot=(0, 0, 0), no='17', bevel=0,
             src='dimension image and right side photo (p. 8 picture 1): studded grip side, marking panel and magazine catch left clear', status='measured')
        attach('p17_frame_grip_texture_' + nm, 'p17_frame', 'moulded texture')
    for rear, nm, zr in ((False, 'front', (-92, -53)), (True, 'back', (-92, -42))):
        bm = bmesh.new(); z = float(zr[0])
        while z < zr[1]:
            p0 = (strap(z - 1.0, rear), z - 1.0); p1 = (strap(z + 1.0, rear), z + 1.0); c = (strap(z, rear), z)
            tl, tz = p1[0] - p0[0], p1[1] - p0[1]; n = math.hypot(tl, tz); tl, tz = tl / n, tz / n
            nl, nz = (-tz, tl) if rear else (tz, -tl)                    # outward normal: rearward on the back strap, forward on the front strap
            quad = [(c[0] + tl * a * 0.6 + nl * b, c[1] + tz * a * 0.6 + nz * b) for a, b in ((-1, -0.25), (1, -0.25), (1, 0.45), (-1, 0.45))]
            for k in range(-4, 5): add(bm, prism(quad, k * 2.4 - 0.6, k * 2.4 + 0.6))
            z += 2.4 / max(abs(tz), 0.5)
        part('p17_frame_grip_texture_' + nm, bm, 'Polymer', 'p17_frame', pivot=(0, 0, 0), no='17', bevel=0,
             src='dimension image and rear view: studs on the %s strap, nine across (v2)' % nm, status='measured')
        attach('p17_frame_grip_texture_' + nm, 'p17_frame', 'moulded texture')

def declare_attached():
    attach('placeholder_panel_frame_mark_l', 'p17_frame', 'placeholder panel set into the surface')
    for a, b in (('placeholder_panel_slide_logo', 'p01_slide'), ('placeholder_panel_slide_text', 'p01_slide'), ('placeholder_panel_barrel_hood', 'p02_barrel'),
                 ('placeholder_panel_grip_l', 'p17_frame'), ('placeholder_panel_grip_r', 'p17_frame'), ('placeholder_panel_magazine', 'p31_magazine_tube')):
        attach(a, b, 'placeholder panel set into the surface')
    for a, b, w in (('p01_slide_guide_rail_l', 'p01_slide', 'steel rail moulded into the slide'), ('p01_slide_guide_rail_r', 'p01_slide', 'steel rail moulded into the slide'),
                    ('p16a_front_sight', 'p01_slide', 'sight seated on the slide'), ('p15_rear_sight', 'p01_slide', 'sight seated on the slide'),
                    ('p16a_front_sight_dot', 'p16a_front_sight', 'painted dot'), ('p15_rear_sight_outline', 'p15_rear_sight', 'painted outline'),
                    ('p16b_front_sight_screw', 'p01_slide', 'screw through the slide roof'), ('p16b_front_sight_screw', 'p16a_front_sight', 'screw into the sight'),
                    ('p35_magazine_floor_plate', 'p31_magazine_tube', 'floor plate slid onto the tube'), ('p34_magazine_insert', 'p35_magazine_floor_plate', 'insert locks the floor plate'),
                    ('p34_magazine_insert', 'p31_magazine_tube', 'insert seated in the tube'),
                    ('p48_loading_assist_right', 'p32_follower', 'button fixed to the follower'), ('p49_loading_assist_left', 'p32_follower', 'button fixed to the follower'),
                    ('p33_magazine_spring', 'p34_magazine_insert', 'spring seated on the insert'), ('p33_magazine_spring', 'p32_follower', 'spring seated under the follower'),
                    ('p07_spring_cups', 'p04_firing_pin', 'cups clipped onto the firing pin')):
        attach(a, b, w)
    for nm in ('l', 'r'):
        for tag in ('rear', 'front'): attach(f'p17_frame_guide_{tag}_{nm}', 'p17_frame', 'steel guide moulded into the frame')

def build_backstraps():
    # 17c / 17d beavertail backstraps, medium (+2 mm) and large (+4 mm): shown detached behind the grip as on manual p. 9
    for key, nm, off in (('backstrap_m', 'p17c_beavertail_backstrap_m', 26.0), ('backstrap_l', 'p17d_beavertail_backstrap_l', 44.0)):
        poly = [(l - off, z) for l, z in O[key]]
        shell = prism(poly, -FW - 0.6, FW + 0.6)
        inner = prism([(l - off, min(z, FT)) for l, z in O['frame']], -FW - 0.1, FW + 0.1)
        part(nm, shell, 'Polymer', 'accessories', pivot=(-off, 0, 0), no=key[-1] == 'm' and '17c' or '17d', cuts=[inner], pre_bevel=(1.5, 3), bevel=0.2,
             src='constructed: the traced rear strap grown by 2 / 4 mm (manual p. 38) with the beavertail of p. 9; not traced', status='inferred')
        e = empty('socket_' + nm[5:], 'frame_group', (0, 0, 0)); META_S[e.name] = 'installed position of ' + nm

# ================================================================== magazine (31-35, 48, 49)
def build_magazine():
    ax = (UX, 0, UZ)
    tube_poly = [(2.70, -101.01), (32.13, -104.92), (mag_front(-18.0), -18.0), (mag_rear(-12.0), -12.0)]      # bottom corners: where the tube's faces meet the traced floor plate's top
    ins = 1.2
    inner = [(2.70 + ins + 0.5, -101.01 + ins), (32.13 - ins + 0.2, -104.92 + ins + 0.15), (mag_front(-10.0) - ins, -10.0), (mag_rear(-10.0) + ins, -10.0)]
    gm = lambda z: (mag_front(z) + mag_rear(z)) / 2
    slot = [(gm(-92) - 2.1, -92.0), (gm(-92) + 2.1, -92.0), (gm(-22) + 2.1, -22.0), (gm(-22) - 2.1, -22.0)]
    cuts = [prism(inner, -MAGW + ins, MAGW - ins), prism(shrink(clipz(inner, NECK_Z - ins), 0.03), -MAGWW + ins, MAGWW - ins), prism(slot, -MAGWW - 1, MAGWW + 1),
            box(0.0, 80.0, MAGW, MAGWW + 1, NECK_Z, 0.0), box(0.0, 80.0, -MAGWW - 1, -MAGW, NECK_Z, 0.0)]                    # the neck (v2)
    for sgn in (1, -1):                                       # catch notches at both front corners (reversible catch)
        cuts.append(box(mag_front(-45.5) - 1.6, mag_front(-40.0) + 1, sgn * 5.5 if sgn > 0 else -MAGWW - 1, MAGWW + 1 if sgn > 0 else -5.5, -45.5, -40.0))
    for zc in (-46.0, -68.0, -90.0):                          # count windows 5 / 10 / 15 on the right rear (exploded drawing) (v2)
        c = Vector((mag_rear(zc) + 4.5, 0, zc)); A_ = Vector(ax); N_ = Vector((UZ, 0, -UX))
        cuts.append(prism([((c + A_ * a * 2.5 + N_ * b * 1.4).x, (c + A_ * a * 2.5 + N_ * b * 1.4).z) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))], -MAGWW - 1, -MAGWW + 2.0))
    part('p31_magazine_tube', prism(tube_poly, -MAGWW, MAGWW), 'Polymer', 'magazine_group', pivot=(gm(-60), 0, -60.0), no='31', cuts=cuts, bevel=0.3,
         src='exploded drawing item 31 (slots, count windows); rake from the traced front strap; 22 mm wide below a 19.2 mm neck, depth 31 mm: inferred', status='inferred')
    part('placeholder_panel_magazine', box(gm(-95) - 2, gm(-95) + 8, -MAGWW - 0.1, -MAGWW + 0.05, -99.0, -91.0), 'Placeholder', 'p31_magazine_tube', bevel=0,
         src='maker\'s mark on the tube in the exploded drawing replaced by a plain panel', status='measured')
    # 35 floor plate (traced), 34 insert
    part('p35_magazine_floor_plate', prism(O['floor_plate'], -15.75, 15.75), 'Polymer', 'p31_magazine_tube', no='35', pre_bevel=(1.2, 3), bevel=0.2,
         src='traced: outlines.json floor_plate; width 31.5 mm from the rear view', status='traced')
    b0 = Vector((3.75, 0, -99.9)); b1 = Vector((31.05, 0, -103.5)); up = Vector((0.131, 0, 0.991))
    q = lambda a, h: tuple((b0 + (b1 - b0) * a + up * h)[i] for i in (0, 2))
    part('p34_magazine_insert', union(prism([q(0.03, 0.15), q(0.97, 0.15), q(0.97, 1.6), q(0.03, 1.6)], -9.5, 9.5), cyl((18.0, 0, -109.4), (18.0, 0, -100.9), 1.6, n=14)),      # its button shows through the floor plate (v2)
        
         'Polymer', 'p31_magazine_tube', no='34', bevel=0.1, seg=1, src='exploded drawing item 34', status='inferred')
    # 32 follower (empty magazine: at the top, held 2 mm down by the slide stop lever while the slide is forward)
    d = FOL_D                                                # mm down the axis from its free top position
    tr, tf = Vector((mag_rear(-12.6) + ins + 0.35, 0, -12.6)), Vector((mag_front(-18.6) - ins - 0.35, 0, -18.6))
    A = Vector(ax)
    fpoly = [tr, tf, tf - A * 9.0, tr - A * 12.0]
    fol = union(prism([(v.x, v.z) for v in fpoly], -8.1, 8.1), box(56.3, 58.7, 7.6, 8.11, -19.5, -15.0 + UZ * d))
    fo = part('p32_follower', fol, 'FollowerOrange', 'p31_magazine_tube', pivot=(gm(-20), 0, -20.0), no='32', bevel=0.2, seg=1,
              src='manual p. 11 picture 4 (orange) and p. 31 picture 36; the shelf that lifts the slide stop lever is inferred', status='measured')
    fo.location += Vector(bl((-UX * d, 0, -UZ * d)))
    # 48 / 49 loading assists: buttons through the tube's side slots, fixed to the follower
    c = Vector((gm(-27.5), 0, -27.5))
    for sgn, nm, no in ((-1, 'p48_loading_assist_right', '48'), (1, 'p49_loading_assist_left', '49')):
        bt = union(cylS(c.x, c.z, sgn * (MAGWW + 0.25), sgn * 12.1, 4.3, n=24), cylS(c.x, c.z, sgn * 8.0, sgn * (MAGWW + 0.26), 1.7, n=12))
        o0, o1 = (11.85, 13.0) if sgn > 0 else (-13.0, -11.85)
        part(nm, bt, 'Polymer', 'p32_follower', no=no, bevel=0.1, seg=1, cuts=[box(c.x - 5, c.x + 5, o0, o1, c.z - 0.4, c.z + 0.4), box(c.x - 0.4, c.x + 0.4, o0, o1, c.z - 5, c.z + 5)],     # cross grip (drawing)
             src='exploded drawing items 48 / 49; manual p. 11 pictures 4-5', status='measured')
    # 33 magazine spring: a flat zig-zag wire from the insert to the follower; scaled along the axis as the follower moves
    base = Vector((gm(-98.5), 0, -98.5)); top = Vector((gm(-30.0), 0, -30.0)) - A * d; n = 10
    N = Vector((UZ, 0, -UX)); pts = []
    for i in range(2 * n + 1):
        c = base + (top - base) * (i / (2 * n)); pts.append(c + N * (11.0 if i % 2 else -11.0) * (1 if i not in (0, 2 * n) else 0.6))
    sp = part('p33_magazine_spring', tube_path(pts, 0.55, 6), 'Spring', 'p31_magazine_tube', pivot=tuple(base), no='33', bevel=0,
              src='exploded drawing item 33: about ten zig-zags', status='measured')
    META['p33_magazine_spring']['axis'] = [UX, 0, UZ]; META['p33_magazine_spring']['free_len_mm'] = round((top - base).length + d, 2)

META_S = {}
def build_sockets():
    def sock(name, q, parent, why):
        empty(name, parent, q, 'ARROWS'); META_S[name] = why
    sock('socket_muzzle', (p('muzzle'), 0, 0), 'frame_group', 'bore axis at the muzzle crown')
    sock('socket_chamber', (BF, 0, 0), 'frame_group', 'bore axis at the breech face in battery')
    sock('socket_eject', (89.0, -SW, 3.0), 'frame_group', 'centre of the ejection port, right side')
    sock('socket_ads_eye', (2.6 - p('eye_relief'), 0, 15.9), 'frame_group', 'on the sight line (top of the front and rear sights), arm\'s length behind the rear sight (inferred 450 mm)')
    sock('socket_front_sight', (160.3, 0, 15.9), 'slide_group', 'top rear edge of the front sight')
    sock('socket_rear_sight', (2.6, 0, 15.9), 'slide_group', 'top rear edge of the rear sight')
    sock('socket_hand_right', (16.0, 0, -52.0), 'frame_group', 'firing hand: middle of the grip, web of the hand under the tang')
    sock('socket_hand_left', (40.0, 0, -62.0), 'frame_group', 'support hand: wrapped over the firing hand on the front strap')
    sock('socket_trigger_finger', (LX(672), 0, ZY(415)), 'frame_group', 'trigger face where the spec table measures the trigger distance (px 672, 415)')
    sock('socket_magazine', ((mag_front(-106) + mag_rear(-106)) / 2, 0, -106.0), 'frame_group', 'mouth of the magazine well; +Y of the magazine axis is tilted 21.8 deg')
    sock('socket_rail', (LX(340), 0, ZY(372)), 'frame_group', 'accessory rail under the dust cover (manual p. 9: mounting rail)')

# ================================================================== clips (30 fps, one NLA track per clip)
def key(clip, name, chan, keys): CLIPS.setdefault(clip, {}).setdefault(name, []).append((chan, keys))
def define_clips():
    T, TL, br, tk, sd = p('full_travel'), p('lock_open_travel'), p('trigger_break_deg'), p('trigger_takeup_deg'), p('trigger_safety_deg')
    pc, r = p('striker_precock'), p('bar_link_r'); rad = math.radians
    a0 = math.atan2(TP[0] - 79.5, TP[1] + 28.2)             # bar link: angle behind straight-down at rest
    def bar_at(deg): return r * (math.sin(a0 + rad(deg)) - math.sin(a0))
    bt, bb = bar_at(tk), bar_at(br)
    KIN.update(bar_travel_takeup_mm=round(bt, 3), bar_travel_break_mm=round(bb, 3), striker_break_mm=round(pc + bb, 3))
    spring_free = 68.3
    def slide(clip, keys, with_pin=True):
        key(clip, 'p01_slide', ('loc', 'L'), [(f, -x) for f, x in keys])
        key(clip, 'p03_recoil_spring', ('scale', 'L'), [(f, (spring_free - x) / spring_free) for f, x in keys])
    def striker(clip, keys):                                  # keys: rearward travel of the firing pin from its fired position
        key(clip, 'p04_firing_pin', ('loc', 'L'), [(f, pc - x) for f, x in keys])      # rest pose = part-cocked
        key(clip, 'p06_firing_pin_spring', ('scale', 'L'), [(f, (21.6 - x) / (21.6 - pc)) for f, x in keys])
    # 1 trigger safety: press the blade, let it go
    key('trigger_safety', 'p26_trigger_safety', ('rot', 'X'), [(1, 0), (5, sd), (12, sd), (16, 0), (20, 0)])
    # 2 trigger pull (dry fire): safety in, take-up, break; the trigger stays back until the slide is cycled (manual p. 33)
    key('trigger_pull', 'p26_trigger_safety', ('rot', 'X'), [(1, 0), (4, sd), (30, sd)])
    key('trigger_pull', 'p26_trigger', ('rot', 'X'), [(1, 0), (4, 0), (12, tk), (16, tk), (19, br), (30, br)])
    key('trigger_pull', 'p26_trigger_bar', ('loc', 'L'), [(1, 0), (4, 0), (12, -bt), (16, -bt), (19, -bb), (30, -bb)])
    key('trigger_pull', 'p26_trigger_bar', ('loc', 'Z'), [(1, 0), (18, 0), (19, -p('bar_drop')), (30, -p('bar_drop'))])
    key('trigger_pull', 'p08_firing_pin_safety', ('loc', 'Z'), [(1, 0), (4, 0), (12, p('fp_safety_lift')), (30, p('fp_safety_lift'))])
    key('trigger_pull', 'p09_firing_pin_safety_spring', ('scale', 'Z'), [(1, 1), (4, 1), (12, (9.0 - p('fp_safety_lift')) / 9.0), (30, (9.0 - p('fp_safety_lift')) / 9.0)])
    striker('trigger_pull', [(1, pc), (4, pc), (12, pc + bt), (16, pc + bt), (19, pc + bb), (20, 0), (30, 0)])
    # 3 slide cycle by hand from the ready state
    slide('slide_cycle', [(1, 0), (10, T), (13, T), (17, 0), (24, 0)])
    striker('slide_cycle', [(1, pc), (24, pc)])
    # 4 lock-open on an empty magazine: back to the stop, forward onto the slide stop lever lifted by the follower
    slide('slide_lock_open', [(1, 0), (10, T), (13, T), (15, TL), (24, TL)])
    key('slide_lock_open', 'p27_slide_stop_lever', ('rot', 'X'), [(1, 0), (9, 0), (11, p('stop_lift_deg')), (24, p('stop_lift_deg'))])
    key('slide_lock_open', 'p32_follower', ('loc', 'A'), [(1, 0), (9, 0), (11, FOL_D), (24, FOL_D)])
    key('slide_lock_open', 'p33_magazine_spring', ('scale', 'A'), [(1, 1), (9, 1), (11, 1 + FOL_D / 73.5), (24, 1 + FOL_D / 73.5)])
    # 5 slide release with the lever (a loaded magazine has been inserted: the follower no longer holds the lever)
    slide('slide_release', [(1, TL), (4, TL), (8, 0), (16, 0)])
    key('slide_release', 'p27_slide_stop_lever', ('rot', 'X'), [(1, p('stop_lift_deg')), (4, 0), (16, 0)])
    # 6 / 7 magazine out and in
    mp_ = p('mag_catch_press')
    key('magazine_out', 'p19_magazine_catch', ('loc', 'S'), [(1, 0), (4, -mp_), (16, -mp_), (20, 0), (30, 0)])
    key('magazine_out', 'p31_magazine_tube', ('loc', 'A'), [(1, 0), (4, 0), (16, -60.0), (30, -180.0)])
    key('magazine_out', 'p32_follower', ('loc', 'A'), [(1, 0), (4, 0), (6, FOL_D), (30, FOL_D)])
    key('magazine_out', 'p33_magazine_spring', ('scale', 'A'), [(1, 1), (4, 1), (6, 1 + FOL_D / 73.5), (30, 1 + FOL_D / 73.5)])
    key('magazine_in', 'p31_magazine_tube', ('loc', 'A'), [(1, -180.0), (14, -60.0), (22, 0), (30, 0)])
    key('magazine_in', 'p32_follower', ('loc', 'A'), [(1, FOL_D), (20, FOL_D), (22, 0), (30, 0)])
    key('magazine_in', 'p33_magazine_spring', ('scale', 'A'), [(1, 1 + FOL_D / 73.5), (20, 1 + FOL_D / 73.5), (22, 1), (30, 1)])
    key('magazine_in', 'p19_magazine_catch', ('loc', 'S'), [(1, 0), (14, 0), (18, -mp_), (21, -mp_), (24, 0), (30, 0)])
    # 8 field strip (manual pp. 21-23; magazine already out, chamber checked): trigger pulled, slide back 3 mm, slide lock down,
    #   slide forward off the frame with barrel and spring, spring out, barrel out
    c = 'field_strip'; rt, sp = p('takedown_retract'), p('slide_lock_pull')
    key(c, 'p31_magazine_tube', ('loc', 'A'), [(1, -180.0), (150, -180.0)])
    key(c, 'p32_follower', ('loc', 'A'), [(1, FOL_D), (150, FOL_D)]); key(c, 'p33_magazine_spring', ('scale', 'A'), [(1, 1 + FOL_D / 73.5), (150, 1 + FOL_D / 73.5)])
    key(c, 'p26_trigger_safety', ('rot', 'X'), [(1, 0), (4, sd), (150, sd)])
    key(c, 'p26_trigger', ('rot', 'X'), [(1, 0), (4, 0), (12, br), (150, br)])
    key(c, 'p26_trigger_bar', ('loc', 'L'), [(1, 0), (4, 0), (12, -bb), (150, -bb)]); key(c, 'p26_trigger_bar', ('loc', 'Z'), [(1, 0), (11, 0), (12, -p('bar_drop')), (150, -p('bar_drop'))])
    key(c, 'p08_firing_pin_safety', ('loc', 'Z'), [(1, 0), (4, 0), (10, p('fp_safety_lift')), (16, p('fp_safety_lift')), (20, 0), (150, 0)])
    key(c, 'p09_firing_pin_safety_spring', ('scale', 'Z'), [(1, 1), (4, 1), (10, (9.0 - 1.5) / 9.0), (16, (9.0 - 1.5) / 9.0), (20, 1), (150, 1)])
    striker(c, [(1, pc), (4, pc), (12, pc + bb), (13, 0), (150, 0)])
    OFF = 190.0
    sl_keys = [(1, 0), (20, 0), (28, -rt), (40, -rt), (46, 0), (70, OFF), (150, OFF)]                 # + = forward here
    key(c, 'p01_slide', ('loc', 'L'), sl_keys)
    key(c, 'p21_slide_lock', ('loc', 'Z'), [(1, 0), (30, 0), (38, -sp), (62, -sp), (68, 0), (150, 0)])
    key(c, 'p20_slide_lock_spring', ('scale', 'Z'), [(1, 1), (30, 1), (38, 0.64), (62, 0.64), (68, 1), (150, 1)])
    fwd = [(1, 0), (46, 0), (70, OFF), (150, OFF)]
    key(c, 'p03_recoil_spring', ('scale', 'L'), [(1, 1), (20, 1), (28, (spring_free - rt) / spring_free), (40, (spring_free - rt) / spring_free), (46, 1), (150, 1)])
    key(c, 'p03_recoil_spring_assembly', ('loc', 'L'), fwd + []); key(c, 'p03_recoil_spring_assembly', ('loc', 'Z'), [(1, 0), (80, 0), (100, -45.0), (150, -45.0)])
    # barrel: forward 10 mm (manual p. 23 step 12: at least 1 cm), breech end tilted out of the slide about the nose hole, then drawn out along its own axis
    tilt = 13.0; back = 115.0
    key(c, 'p02_barrel', ('loc', 'L'), [(1, 0), (46, 0), (70, OFF), (110, OFF), (116, OFF + 10.0), (124, OFF + 10.0), (150, OFF + 10.0 - back * math.cos(rad(tilt)))])
    key(c, 'p02_barrel', ('rot', 'X'), [(1, 0), (116, 0), (124, -tilt), (150, -tilt)])
    key(c, 'p02_barrel', ('loc', 'Z'), [(1, 0), (124, 0), (150, -back * math.sin(rad(tilt)))])

def bake_clips():
    reg = {}; A = Vector((0, -UX * MM, UZ * MM))
    for clip, objs in CLIPS.items():
        for name, chans in objs.items():
            o = OBJ[name]; rest = o.location.copy(); o.rotation_mode = 'XYZ'
            ad = o.animation_data_create(); act = bpy.data.actions.new(f'{clip}.{name}'); ad.action = act
            merged = {}
            for (kind, ax), keys in chans:
                for fr, v in keys: merged.setdefault(fr, []).append((kind, ax, v))
            for fr in sorted(merged):
                loc = rest.copy(); rot = [0.0, 0.0, 0.0]; scl = [1.0, 1.0, 1.0]; has = set()
                # channels not keyed at this frame hold their interpolated value: evaluate each channel's own keys
                for (kind, ax), keys in chans:
                    ks = sorted(keys); v = ks[0][1]
                    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
                        if f0 <= fr <= f1: v = v0 + (v1 - v0) * (fr - f0) / max(f1 - f0, 1e-9)
                        elif fr > f1: v = v1
                    if kind == 'loc':
                        loc += {'L': Vector((0, -v * MM, 0)), 'S': Vector((v * MM, 0, 0)), 'Z': Vector((0, 0, v * MM)), 'A': A * v}[ax]; has.add('loc')
                    elif kind == 'rot': rot['XYZ'.index(ax)] = math.radians(v); has.add('rot')
                    else:
                        if ax == 'L': scl[1] = v
                        elif ax == 'Z' or ax == 'A': scl[2] = v
                        has.add('scale')
                if 'loc' in has: o.location = loc; o.keyframe_insert('location', frame=fr)
                if 'rot' in has: o.rotation_euler = rot; o.keyframe_insert('rotation_euler', frame=fr)
                if 'scale' in has: o.scale = scl; o.keyframe_insert('scale', frame=fr)
            for fc in _fcurves(act):
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            tr = ad.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 1, act); tr.mute = True
            ad.action = None; o.location = rest; o.rotation_euler = (0, 0, 0); o.scale = (1, 1, 1)
            reg.setdefault(clip, {})[name] = act.name
    return reg
def _fcurves(act):
    try: return list(act.fcurves)
    except Exception: pass
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags: out += list(bag.fcurves)
    return out

# ================================================================== assemble, export
KIN = {}
def trigger_max_deg():
    """how far the traced trigger can swing back before its outline leaves the traced guard opening / enters the frame"""
    import numpy as np
    tr = np.array(O['trigger']); gh = np.array(O['guard_hole']); c = np.array(TP)
    def inside(pt, poly):
        x, y = pt; ins = False
        for (x0, y0), (x1, y1) in zip(poly, np.roll(poly, -1, axis=0)):
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): ins = not ins
        return ins
    below = tr[tr[:, 1] < -38.0]                         # the blade; the upper part swings up into the frame slot            # the part of the trigger that is inside the guard opening
    for deg in [x * 0.25 for x in range(0, 160)]:
        a = math.radians(deg); d = below - c
        rot = np.c_[d[:, 0] * math.cos(a) + d[:, 1] * math.sin(a), -d[:, 0] * math.sin(a) + d[:, 1] * math.cos(a)] + c     # blade swings toward -L
        if not all(inside(q, gh) for q in rot): return deg - 0.25
    return 40.0

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.fps = 30; sc.unit_settings.system = 'METRIC'
    make_materials()
    empty('g44v', None)
    for g, par in (('frame_group', 'g44v'), ('slide_group', 'frame_group'), ('magazine_group', 'frame_group'), ('accessories', 'g44v')): empty(g, par)
    KIN['trigger_max_deg'] = trigger_max_deg()
    for fn in (build_slide, build_barrel, build_frame, build_grip_texture, build_backstraps, build_magazine, build_sockets, declare_attached):
        fn(); print(f'  {fn.__name__}: {len(OBJ)} objects', flush=True)
    meshes = [o for o in OBJ.values() if o.type == 'MESH']
    for o in meshes: _apply(o)
    define_clips(); reg = bake_clips()
    sc.frame_start = 1; sc.frame_end = 150
    # inventory: every part with its number, source, pivot, size, volume and estimated mass
    inv = dict(asset='g44v', frame='metres in the export: +X shooter\'s left, +Y up, +Z muzzle; origin on the bore axis at the slide\'s rear face. mm in this file: L (muzzle), S (left), Z (up)',
               ruler=OUT['ruler'], params={k: dict(value=v[0], status=v[1], source=v[2]) for k, v in P.items()}, kinematics=KIN, parts=[], sockets=[], clips={})
    for o in meshes:
        bm = bmesh.new(); bm.from_mesh(o.data); vol = abs(bm.calc_volume()) * 1e9
        closed = all(e.is_manifold for e in bm.edges); bm.free()
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = [min(w[i] for w in ws) for i in range(3)]; hi = [max(w[i] for w in ws) for i in range(3)]
        mm = lambda v: [round(-v[1] * 1e3, 2), round(v[0] * 1e3, 2), round(v[2] * 1e3, 2)]
        l0, l1 = sorted((mm(lo)[0], mm(hi)[0]))
        m = META[o.name]; o.data.calc_loop_triangles()
        o['part_no'] = m['part_no'] or ''; o['source'] = m['source']; o['status'] = m['status']
        inv['parts'].append(dict(name=o.name, **m, bbox_mm=dict(L=[l0, l1], S=[mm(lo)[1], mm(hi)[1]], Z=[mm(lo)[2], mm(hi)[2]]),
                                 volume_mm3=round(vol, 1), closed=closed, mass_g=round(vol * 1e-3 * m['density_g_cm3'], 2), triangles=len(o.data.loop_triangles)))
    for n, why in META_S.items():
        w = OBJ[n].matrix_world.translation
        inv['sockets'].append(dict(name=n, parent=OBJ[n].parent.name, pos_mm=dict(L=round(-w[1] * 1e3, 2), S=round(w[0] * 1e3, 2), Z=round(w[2] * 1e3, 2)),
                                   pos_m_export=[round(w[0], 5), round(w[2], 5), round(-w[1], 5)], note=why))
    inv['clips'] = {c: dict(nodes=sorted(v), fps=30) for c, v in reg.items()}
    inv['attached'] = ATTACH
    inv['hierarchy'] = {o.name: (o.parent.name if o.parent else None) for o in OBJ.values()}
    json.dump(inv, open(os.path.join(HERE, 'inventory.json'), 'w'), indent=1)
    os.makedirs(BUILD, exist_ok=True); open(os.path.join(BUILD, '.gitignore'), 'w').write('*\n')      # build outputs are never committed
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, 'g44v.blend'))
    bpy.ops.export_scene.gltf(filepath=os.path.join(BUILD, 'g44v.glb'), export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_apply=False, export_yup=True, export_extras=True)
    print(f'G44V: {len(meshes)} mesh parts, {sum(q["triangles"] for q in inv["parts"])} triangles, {len(META_S)} sockets, {len(reg)} clips', flush=True)

if __name__ == '__main__':
    build()
