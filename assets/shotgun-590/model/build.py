"""Pump shotgun, 12 gauge, 20 in barrel, full-length tube (asset shotgun-590). Rebuilds the model from nothing:

    blender -b --python model/build.py            # writes model/masters/shotgun590.glb and .blend (ignored by git)

Every traced number is a pixel of refs-local/commons-atf-mossberg-590.jpg (public domain, see notes/REFERENCES.md),
converted with GZ / GY below; the buttstock outline comes from model/reference_trace.json, which
model/tools/trace_reference.py measures from the same photo. Numbers marked "inferred" have no reference view
(there is no top or front reference: every lateral dimension is inferred) and are listed in notes/NOTES.md.

Modelling frame (mm): Z along the bore, + towards the muzzle, Z = 0 at the receiver's front face; Y up, 0 on the
bore axis; X lateral, + = the shooter's left. Export (glTF, metres): the same axes, +Y up.
Blender scene (Z up): x = X, y = -Z, z = Y.
"""
import bpy, bmesh, math, json, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'masters')
MM = 0.001
TRACE = json.load(open(os.path.join(HERE, 'reference_trace.json')))
K = TRACE['frame']['mm_per_px']                      # 0.9039 mm per photo pixel (ruler: published 20 in barrel; notes/NOTES.md, change request 1)
SC = K / 0.9563                                      # lengths first fitted under the version 1 ruler (0.9563 mm per px) are carried over by this factor
X0, Y0 = TRACE['anchors_px']['receiver_front_x'], TRACE['frame']['y_axis0']
def GZ(x): return (x - X0) * K
def GY(y): return (Y0 - y) * K
def PX(pts): return [(GZ(x), GY(y)) for x, y in pts]

# ------------------------------------------------------------------ shape numbers (photo pixels unless noted)
P = dict(
    muzzle=GZ(1117), breech=GZ(555),                        # breech = front edge of the ejection port
    barrel_r=10.8 * SC, bore_r=9.25,
    barrel_top=[(577, 38), (588, 38), (588, 39), (665, 39.3), (689, 40), (737, 42), (773, 43), (809, 44.3)],   # the barrel's top edge: collar, chamber, taper
      # bore: nominal 12 ga, 18.5 mm
    tube_y=(GY(72) + GY(97.6)) / 2, tube_r=12.25 * SC, tube_z=(-12.0, GZ(1083)), tube_wall=0.5,   # wall inferred
    recv_top=GY(30.5), recv_bot=GY(98.6), recv_half=20.0 * SC,                                       # half width inferred
    recv_top_pts=[(352, 56), (358, 53), (368, 47.6), (376, 44.2), (389, 41.5), (400, 38.5), (405, 34.5), (409, 30.5), (569, 30.5), (577, 38)],   # the surface under the safety button
    safety_top=[(376, 42), (398, 38)],
    recv_rear=(GZ(358), GZ(368)),                                                             # joint: top, bottom
    port=(GZ(484), GZ(555), GY(70.7), GY(47.7)), load_port=(-97.0 * SC, -21.0 * SC, 11.0),              # loading port from the left photo; half width inferred
    safety=(GZ(376), GZ(398), 7.0),                                                           # travel inferred
    housing_pin=(GZ(396.7), GY(85), 2.2), side_plug=(GZ(408.3), GY(65), 3.0), stud_hole=(GZ(495), GY(87.3), 3.2),
    top_screws=[GZ(446), GZ(510)], ejector_screw=(-55.0 * SC, 7.5 * SC),                                # left photo, by proportion
    guard=[(397, 98), (398, 108), (400, 116), (404, 122), (410, 127.5), (441, 127.5), (450, 124), (456, 118), (460.5, 110), (464, 98)],
    guard_wall=3.6, guard_half=6.0, housing=(GZ(366), GZ(470), GY(103), GY(96)),              # half widths inferred
    trigger=[(406, 99), (409.8, 99), (410.8, 108), (413.2, 116), (417.2, 122), (414, 122.8), (409, 116), (406.6, 108)], trigger_pivot=(409, 95),
    lock_lever=(-183.0 * SC, -177.0 * SC, GY(104), GY(98)),                                             # left photo, by proportion
    forend=(GZ(682), GZ(902)), forend_r=23.0 * SC, ribs=(GZ(735), GZ(850), 19), forend_top=-11.6 * SC,
    bar=(GY(79), GY(70.5), 12.6 * SC, 15.4 * SC), stroke=92.0, lost_motion=9.5,                 # stroke: the forend's rear is 94.9 mm from the receiver face, less clearance (inferred); lost motion is a guess
    lug_band=(GZ(951), GZ(985), GY(113), 13.8 * SC, GZ(939)), ring=(GZ(1057), GZ(1089), 15.7 * SC, GZ(1047)), cap=(GZ(1089), GZ(1104), GZ(1112), 12.9 * SC),
    bead=(GZ(1103.3), 1.5),
    pad_joint=((GZ(54), GY(104)), (GZ(75), GY(215))), stud=(GZ(134), GY(196.5)),
    stock_front=-196.0 * SC, butt_half=22.0 * SC, wrist_half=18.5 * SC,                                       # widths inferred
    bolt=(-101.0, 11.8), bolt_slide=(-91.5, -38.0), cavity_wall=5.0, elevator_len=66.0, elevator_lift=22.0,   # inferred: sized so the bolt and bolt slide stay inside the receiver at full stroke (model/tools/checks.py)
)
SHELL = dict(rim_r=11.15, body_r=10.15, head=16.0, length=59.0)   # nominal 12 ga 2 3/4 in loaded shell (see notes/NOTES.md)

OBJ, W, META, CLIPS, MATS = {}, {}, {}, {}, {}

# ------------------------------------------------------------------ mesh kit (bmesh in model mm: Vector(X, Y, Z))
def new(): return bmesh.new()

def ring_pts(z, ytop, ybot, hw, n_top=2.5, n_bot=2.5, yc=None, N=40):
    """one closed cross-section in the X-Y plane at z: superellipse halves above and below yc"""
    yc = (ytop + ybot) / 2 if yc is None else yc
    out = []
    for i in range(N):
        a = 2 * math.pi * i / N; c, s = math.cos(a), math.sin(a)
        n = n_top if s >= 0 else n_bot; ry = (ytop - yc) if s >= 0 else (yc - ybot)
        out.append(Vector((hw * math.copysign(abs(c) ** (2 / n), c), yc + ry * math.copysign(abs(s) ** (2 / n), s), z)))
    return out

def loft(stations):
    """stations: list of rings (same point count) -> closed solid"""
    bm = new(); rings = [[bm.verts.new(p) for p in r] for r in stations]; n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return bm

def prism(poly_zy, x0, x1):
    bm = new(); a = [bm.verts.new((x0, y, z)) for z, y in poly_zy]; b = [bm.verts.new((x1, y, z)) for z, y in poly_zy]; n = len(a)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    return bm

def box(x0, x1, y0, y1, z0, z1): return prism([(z0, y0), (z1, y0), (z1, y1), (z0, y1)], x0, x1)

def lathe(profile, yc=0.0, xc=0.0, n=40):
    """profile: closed loop of (z, r) around the axis parallel to Z through (xc, yc)"""
    bm = new(); rings = []
    for z, r in profile:
        rings.append([bm.verts.new((xc + r * math.cos(2 * math.pi * i / n), yc + r * math.sin(2 * math.pi * i / n), z)) for i in range(n)])
    m = len(rings)
    for j in range(m):
        a, b = rings[j], rings[(j + 1) % m]
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    return bm

def solid_lathe(profile, yc=0.0, xc=0.0, n=40):
    """profile: open list of (z, r) -> capped solid of revolution"""
    bm = new(); rings = [[bm.verts.new((xc + r * math.cos(2 * math.pi * i / n), yc + r * math.sin(2 * math.pi * i / n), z)) for i in range(n)] for z, r in profile]
    for a, b in zip(rings, rings[1:]):
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return bm

def cyl_x(z, y, x0, x1, r, n=20):
    bm = new(); a = [bm.verts.new((x0, y + r * math.sin(2 * math.pi * i / n), z + r * math.cos(2 * math.pi * i / n))) for i in range(n)]
    b = [bm.verts.new((x1, v.co.y, v.co.z)) for v in a]
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    return bm

def cyl_y(z, x, y0, y1, r, n=20):
    bm = new(); a = [bm.verts.new((x + r * math.cos(2 * math.pi * i / n), y0, z + r * math.sin(2 * math.pi * i / n))) for i in range(n)]
    b = [bm.verts.new((v.co.x, y1, v.co.z)) for v in a]
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    return bm

def loop_prism(outer, wall, x0, x1):
    """a closed band of thickness `wall` following the open polyline `outer` (z, y), inset on its left side"""
    inner = []
    for i, (z, y) in enumerate(outer):
        z0, y0 = outer[max(i - 1, 0)]; z1, y1 = outer[min(i + 1, len(outer) - 1)]
        d = math.hypot(z1 - z0, y1 - y0); inner.append((z - (y1 - y0) / d * wall, y + (z1 - z0) / d * wall))
    return prism(outer + inner[::-1], x0, x1)

def join(*bms):
    out = new()
    for b in bms:
        me = bpy.data.meshes.new('t'); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out

def cut_plane(bm, co, no, keep_positive):
    """keep the half of bm on one side of the plane and cap the cut"""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(co), plane_no=Vector(no), clear_inner=keep_positive, clear_outer=not keep_positive)
    edges = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    if edges: bmesh.ops.holes_fill(bm, edges=edges)
    return bm

def bl(p): return Vector((p[0] * MM, -p[2] * MM, p[1] * MM))

def _obj(name, bm, pivot):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts: v.co = bl(v.co) - pivot
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = pivot
    return o

def _apply(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
    old = o.data; o.modifiers.clear(); o.data = me; bpy.data.meshes.remove(old); me.name = o.name

def part(name, bm, mat, parent, src, basis, pivot=None, bevel=0.4, cuts=(), sharp=35, density=None):
    """bmesh (model mm) -> named object. pivot (X, Y, Z mm) is the hinge or slide origin of a moving part.
    src: decomposition ids (model/decomposition.json). basis: traced | manual | inferred."""
    assert name not in OBJ, name
    wp = bl(pivot) if pivot else Vector((0, 0, 0))
    o = _obj(name, bm, wp)
    for c in cuts:
        co = _obj('cutter', c, Vector((0, 0, 0)))
        m = o.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.object = co
        _apply(o); bpy.data.objects.remove(co)
    for p in o.data.polygons: p.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(sharp))
    if bevel:
        b = o.modifiers.new('bevel', 'BEVEL'); b.limit_method = 'ANGLE'; b.angle_limit = math.radians(sharp); b.width = bevel * MM; b.segments = 2
    o.data.materials.clear(); o.data.materials.append(MATS[mat])          # a boolean cut leaves an empty slot behind
    for p in o.data.polygons: p.material_index = 0
    o.parent = OBJ[parent]; o.location = wp - W[parent]
    OBJ[name] = o; W[name] = wp; META[name] = dict(group=parent, material=mat, source=src, basis=basis, density=density or DENSITY[mat])
    return o

def empty(name, parent, p=(0, 0, 0), src=None):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.02
    bpy.context.scene.collection.objects.link(e); wp = bl(p)
    e.parent = OBJ[parent] if parent else None; e.location = wp - (W[parent] if parent else Vector((0, 0, 0)))
    OBJ[name] = e; W[name] = wp
    if src: META[name] = dict(group=parent, source=src, basis='inferred', socket=True)
    return e

# ------------------------------------------------------------------ materials (flat PBR; no textures, no markings)
DENSITY = dict(SteelParkerized=7850, SteelDark=7850, Alloy=2700, Polymer=1150, Rubber=1100, Brass=8500, PaintRed=1000, ShellHull=950)
def make_materials():
    spec = dict(SteelParkerized=((0.060, 0.062, 0.060), 1.0, 0.62), SteelDark=((0.035, 0.035, 0.038), 1.0, 0.48), Alloy=((0.030, 0.031, 0.034), 0.85, 0.55),
                Polymer=((0.018, 0.018, 0.019), 0.0, 0.66), Rubber=((0.012, 0.012, 0.012), 0.0, 0.9), Brass=((0.78, 0.57, 0.20), 1.0, 0.32),
                PaintRed=((0.60, 0.02, 0.02), 0.0, 0.5), ShellHull=((0.45, 0.03, 0.03), 0.0, 0.5))
    for n, (col, metal, rough) in spec.items():
        m = bpy.data.materials.new(n); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; m.diffuse_color = (*col, 1)
        b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
        MATS[n] = m

# ------------------------------------------------------------------ parts
def col_runs(z):
    k = f'{round(z / 2) * 2:.0f}'; return TRACE['runs_mm'].get(k) or TRACE['runs_mm'].get(k.replace('-0', '0'))

def JOINT():
    """the slanted stock-to-receiver joint: (point, normal towards the muzzle)"""
    zt, zb = P['recv_rear']; yt, yb = recv_top(zt), P['recv_bot']; n = Vector((0, -(zb - zt), (yb - yt))).normalized()
    return (0, yt, zt), (n if n.z > 0 else -n)

def build_stock():
    zs = list(range(int(TRACE['extent_mm']['z_min']), int(P['stock_front']), 4)) + [P['stock_front']]
    tops, bots = [], []
    for z in zs:
        r = col_runs(z); tops.append(r[0][0]); bots.append(min(b for _, b in r if b > -180) if z < -212 * SC else r[0][1])
    # the swivel stud and the trigger guard sit in the lower outline: take the stud out with a 5-point median, cap the wrist at the receiver's underside
    med = lambda v, i: sorted(v[max(0, i - 2):i + 3])[len(v[max(0, i - 2):i + 3]) // 2]
    bots = [med(bots, i) for i in range(len(bots))]
    rings = []
    for z, t, b in zip(zs, tops, bots):
        u = min(1.0, max(0.0, (z - zs[0]) / (250.0 * SC))); hw = P['butt_half'] + (P['wrist_half'] - P['butt_half']) * u
        if z > -230 * SC: hw = P['wrist_half'] + (P['recv_half'] - P['wrist_half']) * (z + 230 * SC) / (P['stock_front'] + 230 * SC)
        if z > -212 * SC: t, b = max(t, recv_top(z)) if z > P['recv_rear'][0] else t, min(b, P['recv_bot'])
        if t - b < 4: t, b = (t + b) / 2 + 2, (t + b) / 2 - 2
        rings.append(ring_pts(z, t, b, hw, 2.6, 2.6, N=36))
    (z0, y0), (z1, y1) = P['pad_joint']; no = Vector((0, -(z1 - z0), (y1 - y0))).normalized()     # plane normal in (X, Y, Z), pointing to the muzzle
    if no.z < 0: no = -no
    stock = cut_plane(cut_plane(loft(rings), (0, y0, z0), no, True), *JOINT(), False)
    pad = cut_plane(loft(rings), (0, y0, z0), no, False)
    part('stock', stock, 'Polymer', 'receiver_group', ['P01', 'P23'], 'traced', bevel=0, density=420)     # hollow moulding: effective density inferred
    part('recoil_pad', pad, 'Rubber', 'receiver_group', ['P02'], 'traced', bevel=0)
    sz, sy = P['stud']
    part('rear_swivel_stud', join(cyl_y(sz, 0, sy - 1.5, sy + 9, 2.4), cyl_x(sz, sy - 1.5, -3.2, 3.2, 3.6)), 'SteelDark', 'receiver_group', ['P04'], 'traced', bevel=0.2)

def recv_top(z):
    pts = PX(P['recv_top_pts'])
    for (za, ya), (zb, yb) in zip(pts, pts[1:]):
        if za <= z <= zb: return ya + (yb - ya) * (z - za) / (zb - za)
    return pts[0][1] if z < pts[0][0] else pts[-1][1]

def build_receiver():
    hw, bot = P['recv_half'], P['recv_bot']
    zr_top, zr_bot = P['recv_rear']
    zs = sorted(set([z for z, _ in PX(P['recv_top_pts'])] + list(range(-184, 0, 12)) + [0.0]))
    rings = [ring_pts(z, recv_top(z), bot, hw, 3.2, 9.0, yc=recv_top(z) - 17.0 * SC, N=44) for z in zs]
    px0, px1, py0, py1 = P['port']; l0, l1, lh = P['load_port']
    cav = box(-hw + 3.0, hw - 3.0, bot + 3.0, 14.0 * SC, zr_bot + P['cavity_wall'], 1.0)                 # inside of the receiver (inferred wall 3 mm)
    port = box(-hw - 2, -hw + 6, py0, py1, px0, px1); lport = box(-lh, lh, bot - 2, bot + 6, l0, l1)
    part('receiver', cut_plane(loft(rings), *JOINT(), True), 'Alloy', 'receiver_group', ['P05', 'P07', 'P23', 'L05'], 'traced', bevel=0.5, cuts=(cav, port, lport))
    z, y, r = P['housing_pin']; part('trigger_housing_pin', cyl_x(z, y, -hw - 0.3, hw + 0.3, r), 'SteelDark', 'receiver_group', ['P09'], 'traced', pivot=(0, y, z), bevel=0.2)
    z, y, r = P['side_plug']
    part('receiver_side_plug_r', cyl_x(z, y, -hw - 0.2, -hw + 2, r), 'SteelDark', 'receiver_group', ['P11'], 'traced', bevel=0.15)
    part('receiver_side_plug_l', cyl_x(z, y, hw - 2, hw + 0.2, r), 'SteelDark', 'receiver_group', ['L04'], 'traced', bevel=0.15)
    z, y, r = P['stud_hole']
    part('elevator_stud_r', cyl_x(z, y, -hw - 0.1, -hw + 5, r), 'SteelDark', 'elevator_group', ['P10', 'M04'], 'traced', bevel=0.15)
    part('elevator_stud_l', cyl_x(z, y, hw - 5, hw + 0.1, r), 'SteelDark', 'elevator_group', ['P10', 'M04'], 'inferred', bevel=0.15)
    for i, z in enumerate(P['top_screws']):
        part(f'receiver_top_screw_{i + 1}', cyl_y(z, 0, P['recv_top'] - 2, P['recv_top'] + 0.3, 2.3), 'SteelDark', 'receiver_group', ['P12'], 'traced', bevel=0.15)
    ez, ey = P['ejector_screw']
    part('ejector_screw', cyl_x(ez, ey, hw - 2, hw + 0.3, 2.0), 'SteelDark', 'receiver_group', ['L02'], 'traced', bevel=0.15)
    part('ejector', box(hw - 3.4, hw - 5.0, ey - 2, ey + 2, P['bolt'][0] + 4, P['breech'] - 4), 'SteelDark', 'receiver_group', ['L02', 'M06'], 'manual', bevel=0.2)
    # safety: rests rearward (SAFE), covering the red dot; slides forward to FIRE
    s0, s1, _ = P['safety']; yt = lambda z: recv_top(z); (za, ya), (zb_, yb_) = PX(P['safety_top']); st = lambda z: ya + (yb_ - ya) * (z - za) / (zb_ - za)
    btn = prism([(s0, yt(s0) - 1), (s0, st(s0) - 0.8), (s1, st(s1) - 0.8), (s1, yt(s1) - 1)], -6.0, 6.0)
    ribs = [prism([(z, st(z) - 0.8), (z, st(z)), (z + 1.4, st(z + 1.4)), (z + 1.4, st(z + 1.4) - 0.8)], -5.0, 5.0) for z in [s0 + 1.5 + 3.2 * i for i in range(6)]]
    part('safety_button', join(btn, *ribs), 'Polymer', 'receiver_group', ['P06', 'M01'], 'traced', pivot=(0, yt(s0), s0), bevel=0.2)
    zd = s0 + 3.5
    part('safety_red_dot', cyl_y(zd, 0, yt(zd) - 1.0, yt(zd) + 0.25, 1.6), 'PaintRed', 'receiver_group', ['M01'], 'manual', bevel=0)
    # the shell stops on the inner walls (manual Fig. 17 and 23: stop on the right, interrupter on the left)
    ty = P['tube_y']
    part('cartridge_stop', join(box(-hw + 3.0, -hw + 4.6, ty - 2, ty + 5, -94, -6), box(-hw + 4.6, -hw + 7.2, ty - 1, ty + 3, -14, -8)), 'SteelDark', 'receiver_group', ['M03'], 'manual', pivot=(-hw + 3.0, ty, -94), bevel=0.2)
    part('cartridge_interrupter', join(box(hw - 4.6, hw - 3.0, ty - 2, ty + 5, -94, -6), box(hw - 7.2, hw - 4.6, ty - 1, ty + 3, -12, -6)), 'SteelDark', 'receiver_group', ['M03'], 'manual', pivot=(hw - 3.0, ty, -94), bevel=0.2)

def build_trigger_group():
    h0, h1, hy0, hy1 = P['housing']; g = P['guard_half']
    body = box(-P['recv_half'] + 3.4, P['recv_half'] - 3.4, P['recv_bot'] - 0.5, P['recv_bot'] + 22.0, h0 + 9, h1)        # inside the receiver (inferred)
    skirt = box(-P['recv_half'] + 0.6, P['recv_half'] - 0.6, P['recv_bot'] - 0.6, P['recv_bot'] + 0.5, h0, h1)             # flush with the receiver's underside
    web = prism(PX([(449, 98), (466, 98), (461, 110), (456, 118), (452, 112)]), -g, g)                                   # the filled corner where the guard's front meets the housing
    boss = prism(PX([(366, 98), (400, 98), (399, 102), (368, 103)]), -g - 4, g + 4)                                       # the housing's rear end, seen under the receiver
    part('trigger_housing', join(body, skirt, web, boss), 'Polymer', 'trigger_housing_group', ['P13', 'M07'], 'traced', bevel=0.4)
    part('trigger_guard', loop_prism(PX(P['guard']), P['guard_wall'], -g, g), 'Polymer', 'trigger_housing_group', ['P13'], 'traced', bevel=0.8)
    pz, py = PX([P['trigger_pivot']])[0]
    part('trigger', prism(PX(P['trigger']), -3.2, 3.2), 'SteelDark', 'trigger_housing_group', ['P14'], 'traced', pivot=(0, py, pz), bevel=0.5)
    l0, l1, ly0, ly1 = P['lock_lever']
    part('action_lock_lever', box(g + 1.0, P['recv_half'] - 1.0, ly0, ly1 + 1.5, l0, l1), 'SteelDark', 'trigger_housing_group', ['L01', 'M02'], 'traced', pivot=(g + 1, ly1, l0), bevel=0.3)

def build_barrel():
    br = P['barrel_r']; b = P['bore_r']; top = PX(P['barrel_top'])
    prof = [(P['breech'], top[2][1])] + [(z, max(y, br)) for z, y in top] + [(P['muzzle'], br), (P['muzzle'], b), (P['breech'], b + 1.0)]
    part('barrel', lathe(prof, n=48), 'SteelParkerized', 'barrel_assembly', ['P15'], 'traced', bevel=0.3)
    ty, tr = P['tube_y'], P['tube_r']
    def clamp(z0, z1, ro, zw):      # a ring around the tube, joined to the barrel's underside by a web that starts at zw (the photo shows no hoop over the barrel)
        return join(lathe([(z0, tr + 0.15), (z0, ro), (z1, ro), (z1, tr + 0.15)], yc=ty, n=40), prism([(zw, -br + 2), (z1, -br + 2), (z1, ty + tr + 0.5), (z0, ty + tr + 0.5), (zw, GY(70))], -6.0, 6.0))
    z0, z1, ro, zw = P['ring']; part('barrel_ring', clamp(z0, z1, ro, zw), 'SteelParkerized', 'barrel_assembly', ['P21'], 'traced', bevel=0.3)
    z0, z1, yb, ro, zw = P['lug_band']
    lug = prism([(z0 + 5, ty - tr - 1), (z1 - 6, ty - tr - 1), (z1 - 6, yb + 7), (z1 - 11, yb + 7), (z1 - 11, yb + 2), (z1 - 14, yb), (z0 + 8, yb), (z0 + 5, yb + 5)], -4.5, 4.5)
    part('lug_band', join(clamp(z0, z1, ro, zw), lug), 'SteelParkerized', 'barrel_assembly', ['P20'], 'traced', bevel=0.3)
    bz, r = P['bead']
    bm = new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    for v in bm.verts: v.co = Vector((v.co.x, v.co.z + br + r * 0.8, v.co.y + bz))
    part('front_bead', join(bm, cyl_y(bz, 0, br - 0.5, br + r * 0.8, 0.8, n=10)), 'Brass', 'barrel_assembly', ['P16'], 'traced', bevel=0)

def build_magazine():
    ty, tr, w = P['tube_y'], P['tube_r'], P['tube_wall']; z0, z1 = P['tube_z']
    part('magazine_tube', lathe([(z0, tr), (z1, tr), (z1, tr - w), (z0, tr - w)], yc=ty, n=40), 'SteelParkerized', 'receiver_group', ['P17'], 'traced', bevel=0)
    fl = 24.0
    part('magazine_follower', solid_lathe([(z0 + 2, tr - w - 1.5), (z0 + 2.8, tr - w - 0.4), (z0 + fl, tr - w - 0.4), (z0 + fl, tr - w - 2.2)], yc=ty, n=28), 'Polymer', 'receiver_group', ['M08'], 'manual',
         pivot=(0, ty, z0 + 2), bevel=0.2)
    c0, c1, c2, cr = P['cap']
    part('magazine_cap', solid_lathe([(c0, cr), (c1 - 5, cr), (c1 - 1.5, cr - 1.5), (c1, cr - 4.0)], yc=ty, n=40), 'SteelParkerized', 'magazine_cap_group', ['P22'], 'traced', pivot=(0, ty, c0), bevel=0.4)
    part('front_swivel_stud', join(solid_lathe([(c1 - 1, 5.5), (c2 - 3, 5.5), (c2, 3.8)], yc=ty, n=20), cyl_x(c2 - 3.5, ty, -4.6, 4.6, 1.3, n=12)), 'SteelDark', 'magazine_cap_group', ['P22'], 'traced', pivot=(0, ty, c0), bevel=0.2)

def build_slide():
    ty, tr = P['tube_y'], P['tube_r']; f0, f1 = P['forend']; R = P['forend_r']; r0, r1, n = P['ribs']
    prof = [(f0, R - 0.6), (f0 + 1.5, R + 0.4), (f0 + 6, R + 0.4), (f0 + 7.5, R), (r0 - 0.5, R)]
    pitch = (r1 - r0) / n
    for i in range(n):
        z = r0 + i * pitch; prof += [(z, R - 1.4), (z + pitch * 0.25, R), (z + pitch * 0.6, R), (z + pitch * 0.85, R - 1.4)]
    prof += [(r1 + 0.5, R - 0.4), (f1 - 16, R), (f1 - 8, R - 1.5), (f1 - 3, R - 5), (f1, R - 10)]
    inner = [(f1, tr + 1.6), (f0, tr + 1.6)]
    forend = cut_plane(lathe(prof + inner, yc=ty, n=48), (0, P['forend_top'], 0), (0, -1, 0), True)
    part('forend', forend, 'Polymer', 'slide_assembly', ['P19'], 'traced', bevel=0)
    part('action_slide_tube', lathe([(f0 - 3, tr + 0.3), (f0 - 3, tr + 1.5), (f1 - 2, tr + 1.5), (f1 - 2, tr + 0.3)], yc=ty, n=36), 'SteelDark', 'slide_assembly', ['M10'], 'manual', bevel=0)
    by0, by1, bx0, bx1 = P['bar']; zb = P['bolt_slide'][0] + 6
    for side, sx in (('right', -1), ('left', 1)):
        bar = join(box(sx * bx0, sx * bx1, by0, by1, zb, f0 + 4), box(sx * (bx0 - 3.0), sx * bx0, by0 + 1, by1 - 1, zb + 2, zb + 12))        # the drive lug that sits in the bolt slide's notch
        part(f'action_bar_{side}', bar, 'SteelDark', 'slide_assembly', ['P18'], 'traced' if side == 'right' else 'inferred', bevel=0.2)

def build_bolt():
    zb, r = P['bolt']; zf = P['breech']
    body = cut_plane(solid_lathe([(zb, r - 1.2), (zb + 2, r), (zf - 1, r), (zf, r - 1.0)], n=36), (0, -9.5, 0), (0, 1, 0), False)
    part('bolt', body, 'SteelDark', 'bolt_group', ['P07', 'M06'], 'manual', bevel=0.3)
    px0, px1, py0, py1 = P['port']
    part('extractor', box(-r - 0.5, -r + 2.0, GY(61), GY(55), GZ(535), zf + 0.6), 'SteelParkerized', 'bolt_group', ['P08'], 'traced', bevel=0.2)
    part('bolt_lock', box(-5.0, 5.0, r - 3.5, r + 1.2, zb + 34, zf - 8), 'SteelDark', 'bolt_group', ['M05'], 'manual', pivot=(0, r - 2, zb + 34), bevel=0.3)
    s0, s1 = P['bolt_slide']
    part('bolt_slide', join(box(-9.5, 9.5, -15.5, -9.5, s0, s1), box(-P['bar'][2] - 0.2, P['bar'][2] + 0.2, -19.0, -15.5, s0 + 6, s0 + 20)), 'SteelDark', 'bolt_slide_group', ['M05'], 'manual', bevel=0.3)

def build_elevator():
    z, y, _ = P['stud_hole']; L = P['elevator_len']; hw = P['recv_half']
    arms = [box(sx * 8.0, sx * 10.0, y - 3.0, y + 3.0, z - 4, z + L - 14) for sx in (-1, 1)]
    plate = box(-10.0, 10.0, y - 3.0, y - 1.0, z + L - 30, z + L)
    part('elevator', join(*arms, plate), 'SteelDark', 'elevator_group', ['M04', 'L05'], 'manual', bevel=0.2)

def build_shell():
    s = SHELL; ty = P['tube_y']
    head = solid_lathe([(0, s['rim_r']), (1.4, s['rim_r']), (1.4, s['body_r'] + 0.1), (s['head'], s['body_r'] + 0.1)], n=28)
    hull = solid_lathe([(s['head'], s['body_r']), (s['length'] - 3, s['body_r']), (s['length'], s['body_r'] - 2.5)], n=28)
    # template shell, drawn chambered (head against the bolt face); the game instances it at socket_chamber, socket_lifter, socket_load
    for bm in (head, hull):
        for v in bm.verts: v.co.z += P['breech']
    part('shell_head', head, 'Brass', 'shell_template', ['M08'], 'inferred', bevel=0.15)
    part('shell_hull', hull, 'ShellHull', 'shell_template', ['M08'], 'inferred', bevel=0.3)

def build_sockets():
    ty = P['tube_y']; px0, px1, py0, py1 = P['port']; l0, l1, lh = P['load_port']; f0, f1 = P['forend']
    zr = PX([P['recv_top_pts'][6]])[0][0]; bz, br = P['bead']; yb = P['barrel_r'] + br * 1.8; yr = P['recv_top']
    slope = (yb - yr) / (bz - zr)                                    # sight line: receiver top rear edge over the bead
    empty('socket_muzzle', 'barrel_assembly', (0, 0, P['muzzle']), ['P15'])
    empty('socket_ads_eye', 'receiver_group', (0, yr + slope * (-312 - zr), -312.0), ['P05', 'P16'])
    empty('socket_hand_right', 'receiver_group', (0, -66.0, -248.0), ['P01'])
    empty('socket_trigger_finger', 'receiver_group', (0, GY(112), GZ(411)), ['P14'])
    empty('socket_hand_left', 'slide_assembly', (0, ty - P['forend_r'], (f0 + f1) / 2), ['P19'])
    empty('socket_shoulder', 'receiver_group', (0, GY(165), GZ(33)), ['P02'])
    empty('socket_eject', 'receiver_group', (-P['recv_half'], (py0 + py1) / 2, (px0 + px1) / 2), ['P07'])
    empty('socket_load', 'receiver_group', (0, P['recv_bot'], (l0 + l1) / 2), ['L05'])
    empty('socket_chamber', 'barrel_assembly', (0, 0, P['breech']), ['P15'])
    empty('socket_lifter', 'elevator_group', (0, ty, -8.0 - SHELL['length']), ['M04'])
    empty('socket_magazine_mouth', 'receiver_group', (0, ty, P['tube_z'][0]), ['P17'])
    empty('socket_sling_front', 'magazine_cap_group', (0, ty, P['cap'][2] - 3.5), ['P22'])
    empty('socket_bayonet_lug', 'barrel_assembly', (0, P['lug_band'][2], (P['lug_band'][0] + P['lug_band'][1]) / 2), ['P20'])
    empty('socket_sling_rear', 'receiver_group', (0, P['stud'][1] - 1.5, P['stud'][0]), ['P04'])

# ------------------------------------------------------------------ clips (24 fps, one NLA track per clip)
def key(clip, name, chan, keys): CLIPS.setdefault(clip, {}).setdefault(name, []).append((chan, keys))

def define_clips():
    S, lm, lift = P['stroke'], P['lost_motion'], P['elevator_lift']
    def pump(clip, frames, back=True, fwd=True, f0=1):
        fb, ff = frames
        ks, kb, kl, ke = [(f0, 0)], [(f0, 0)], [(f0, 0)], [(f0, 0)]
        f = f0
        if back:
            fu = f + max(1, round(fb * lm / S))
            ks += [(f + fb, -S)]; kb += [(fu, 0), (f + fb, -(S - lm))]; kl += [(fu, 7.0), (f + fb, 7.0)]; ke += [(f + fb, 0)]; f += fb
        else:
            ks, kb, kl, ke = [(f0, -S)], [(f0, -(S - lm))], [(f0, 7.0)], [(f0, 0)]
        if fwd:
            fl_ = f + max(1, round(ff * 0.3)); fu = f + ff - max(1, round(ff * lm / S))
            ks += [(f + ff, 0)]; kb += [(fu, 0), (f + ff, 0)]; kl += [(fu, 7.0), (f + ff, 0)]; ke += [(fl_, -lift), (fu, -lift), (f + ff, 0)]
        key(clip, 'slide_assembly', ('loc', 'Z'), ks); key(clip, 'bolt_slide_group', ('loc', 'Z'), ks)
        key(clip, 'bolt_group', ('loc', 'Z'), kb); key(clip, 'bolt_lock', ('rot', 'X'), kl); key(clip, 'elevator_group', ('rot', 'X'), ke)
    pump('pump_stroke', (5, 5)); pump('pump_back', (5, 5), fwd=False); pump('pump_forward', (5, 5), back=False)
    key('trigger_pull', 'trigger', ('rot', 'X'), [(1, 0), (3, 9), (6, 9), (9, 0)])
    key('safety_to_fire', 'safety_button', ('loc', 'Z'), [(1, 0), (4, P['safety'][2])]); key('safety_to_safe', 'safety_button', ('loc', 'Z'), [(1, P['safety'][2]), (4, 0)])
    key('action_release', 'action_lock_lever', ('loc', 'Y'), [(1, 0), (3, 3.0), (8, 3.0), (10, 0)])
    key('shell_insert', 'elevator_group', ('rot', 'X'), [(1, 0), (4, -lift), (10, -lift), (13, 0)])
    key('shell_insert', 'magazine_follower', ('loc', 'Z'), [(1, 0), (6, 0), (11, SHELL['length']), (13, SHELL['length'])])
    key('dry_fire', 'trigger', ('rot', 'X'), [(1, 0), (3, 9), (5, 9), (8, 0)])
    # takedown in the manual's order (pp. 10 to 14): cap, barrel, trigger housing, stops, bolt slide, bolt, elevator, slide
    key('takedown', 'slide_assembly', ('loc', 'Z'), [(1, 0), (8, -S / 2), (80, -S / 2), (96, 260)]); key('takedown', 'bolt_slide_group', ('loc', 'Z'), [(1, 0), (8, -S / 2), (56, -S / 2)])
    key('takedown', 'bolt_group', ('loc', 'Z'), [(1, 0), (2, 0), (8, -(S / 2 - lm)), (60, -(S / 2 - lm)), (72, 150)]); key('takedown', 'bolt_lock', ('rot', 'X'), [(1, 0), (2, 7), (96, 7)])
    key('takedown', 'magazine_cap_group', ('rot', 'Z'), [(8, 0), (20, 1080)]); key('takedown', 'magazine_cap_group', ('loc', 'Z'), [(8, 0), (20, 18), (24, 90)])
    key('takedown', 'barrel_assembly', ('loc', 'Z'), [(20, 0), (34, 190)]); key('takedown', 'barrel_assembly', ('loc', 'Y'), [(20, 0), (34, 0), (40, 70)])
    key('takedown', 'trigger_housing_pin', ('loc', 'X'), [(34, 0), (40, -60)])
    key('takedown', 'trigger_housing_group', ('rot', 'X'), [(40, 0), (46, -14)]); key('takedown', 'trigger_housing_group', ('loc', 'Y'), [(40, 0), (46, -20), (52, -90)])
    key('takedown', 'cartridge_stop', ('loc', 'Y'), [(46, 0), (52, 0), (58, -70)]); key('takedown', 'cartridge_stop', ('loc', 'X'), [(52, 0), (58, -30)])
    key('takedown', 'cartridge_interrupter', ('loc', 'Y'), [(46, 0), (52, 0), (58, -70)]); key('takedown', 'cartridge_interrupter', ('loc', 'X'), [(52, 0), (58, 30)])
    key('takedown', 'bolt_slide_group', ('loc', 'Y'), [(56, 0), (64, -75)])
    key('takedown', 'elevator_group', ('rot', 'X'), [(72, 0), (78, 25)]); key('takedown', 'elevator_group', ('loc', 'Y'), [(72, 0), (78, 0), (84, -60)])

def bake_clips():
    reg = {}
    for clip, objs in CLIPS.items():
        for name, chans in objs.items():
            o = OBJ[name]; rest = o.location.copy(); o.rotation_mode = 'XYZ'
            ad = o.animation_data_create(); act = bpy.data.actions.new(f'{clip}.{name}'); ad.action = act
            for (kind, ax), keys in chans:
                for fr, v in keys:
                    if kind == 'loc':       # model axis -> Blender axis: X -> x, Y -> z, Z -> -y
                        d = {'X': Vector((v * MM, 0, 0)), 'Y': Vector((0, 0, v * MM)), 'Z': Vector((0, -v * MM, 0))}[ax]; i = {'X': 0, 'Y': 2, 'Z': 1}[ax]
                        o.location = rest + d; o.keyframe_insert('location', index=i, frame=fr); o.location = rest
                    else:                   # degrees about the model axis through the pivot (model X = Blender x, model Z = Blender -y)
                        i = {'X': 0, 'Z': 1}[ax]; e = [0.0, 0.0, 0.0]; e[i] = math.radians(v if ax == 'X' else -v); o.rotation_euler = e
                        o.keyframe_insert('rotation_euler', index=i, frame=fr); o.rotation_euler = (0, 0, 0)
            tr = ad.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 1, act); tr.mute = True
            ad.action = None; o.location = rest; o.rotation_euler = (0, 0, 0)
            reg.setdefault(clip, []).append(name)
    return reg

# ------------------------------------------------------------------ assemble, export
GROUPS = [('receiver_group', 'shotgun_590', (0, 0, 0)), ('barrel_assembly', 'shotgun_590', (0, 0, 0)), ('magazine_cap_group', 'shotgun_590', (0, P['tube_y'], P['cap'][0])),
          ('slide_assembly', 'shotgun_590', (0, 0, 0)), ('bolt_group', 'shotgun_590', (0, 0, 0)), ('bolt_slide_group', 'shotgun_590', (0, 0, 0)),
          ('trigger_housing_group', 'receiver_group', (0, P['recv_bot'], P['housing'][1])), ('elevator_group', 'receiver_group', (0, P['stud_hole'][1], P['stud_hole'][0])),
          ('shell_template', 'shotgun_590', (0, 0, P['breech']))]

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.fps = 24; sc.unit_settings.system = 'METRIC'
    make_materials()
    empty('shotgun_590', None)
    for g, par, piv in GROUPS: empty(g, par, piv)
    for fn in (build_receiver, build_stock, build_trigger_group, build_barrel, build_magazine, build_slide, build_bolt, build_elevator, build_shell, build_sockets):
        fn(); print(f'  {fn.__name__}: {len(OBJ)} objects', flush=True)
    meshes = [o for o in OBJ.values() if o.type == 'MESH']
    for o in meshes: _apply(o)
    stats = {}
    for o in meshes:
        o.data.calc_loop_triangles(); bm = bmesh.new(); bm.from_mesh(o.data); vol = abs(bm.calc_volume()); bm.free()
        cs = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = [min(c[i] for c in cs) for i in range(3)]; hi = [max(c[i] for c in cs) for i in range(3)]
        m = META[o.name]
        stats[o.name] = dict(group=m['group'], material=m['material'], source=m['source'], basis=m['basis'], triangles=len(o.data.loop_triangles),
                             bbox_mm=dict(x=[round(lo[0] * 1e3, 1), round(hi[0] * 1e3, 1)], y=[round(lo[2] * 1e3, 1), round(hi[2] * 1e3, 1)], z=[round(-hi[1] * 1e3, 1), round(-lo[1] * 1e3, 1)]),
                             volume_cm3=round(vol * 1e6, 2), mass_g=round(vol * m['density'] * 1e3, 1))
    define_clips(); reg = bake_clips()
    sc.frame_start = 1; sc.frame_end = 96
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'shotgun590.blend'))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'shotgun590.glb'), export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS', export_apply=False, export_yup=True)
    sockets = {n: [round(W[n].x * 1e3, 1), round(W[n].z * 1e3, 1), round(-W[n].y * 1e3, 1)] for n, m in META.items() if m.get('socket')}
    inv = dict(asset='shotgun-590', frame='mm; X = shooter\'s left, Y = up, Z = muzzle; origin on the bore axis at the receiver front face',
               ruler=dict(mm_per_px=K, source=TRACE['source']), parts=stats, sockets=sockets, clips={c: sorted(v) for c, v in reg.items()},
               hierarchy={n: (o.parent.name if o.parent else None) for n, o in OBJ.items()},
               totals=dict(parts=len(meshes), triangles=sum(s['triangles'] for s in stats.values()), mass_g_from_volumes=round(sum(s['mass_g'] for n, s in stats.items() if not n.startswith('shell_')), 0)),
               params={k: v for k, v in P.items()}, shell=SHELL)
    json.dump(inv, open(os.path.join(HERE, 'inventory.json'), 'w'), indent=1)
    print(f"BUILT {len(meshes)} parts, {inv['totals']['triangles']} triangles, {len(reg)} clips, {len(sockets)} sockets, volume mass {inv['totals']['mass_g_from_volumes']} g", flush=True)

if __name__ == '__main__':
    build()
