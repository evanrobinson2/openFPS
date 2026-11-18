"""Mesh kit shared by the optic recipes (Blender Python). The same file sits in each optic's model/ folder.

Modelling frame, millimetres: (l, s, z) = along the optical axis (+ toward the muzzle), sideways (+ = the shooter's
left), up. The origin is socket_mount: the point that sits on the rifle's socket_optic (rail top, on the centreline).
Blender / export frame, metres: X = s, Y = -l, Z = z, so the glTF comes out +Y up, +Z toward the muzzle, +X left:
the HK416's frame.
"""
import bpy, bmesh, math, json, os
from mathutils import Vector, Matrix

MM = 0.001
OBJ, W, CLIPS, MATS, INV, SOCK = {}, {}, {}, {}, [], {}
ROOT = [None]


def bl(p):
    return Vector((p[1] * MM, -p[0] * MM, p[2] * MM))


def reset(root_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for d in (OBJ, W, CLIPS, MATS, SOCK): d.clear()
    INV.clear()
    sc = bpy.context.scene; sc.render.fps = 24; sc.unit_settings.system = 'METRIC'
    root = bpy.data.objects.new(root_name, None); sc.collection.objects.link(root)
    OBJ[root_name] = root; W[root_name] = Vector((0, 0, 0)); ROOT[0] = root_name
    return root


def group(name, parent=None, pivot=(0, 0, 0)):
    """An empty that parts hang from (a kinematic node). pivot in model mm."""
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    par = OBJ[parent or ROOT[0]]; e.parent = par; wp = bl(pivot); e.location = wp - W[par.name]
    OBJ[name] = e; W[name] = wp
    return e


def material(name, base, rough, metal, alpha=1.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        try: m.surface_render_method = 'BLENDED'
        except Exception: m.blend_method = 'BLEND'
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = emit_strength
    MATS[name] = m
    return m


# ------------------------------------------------------------------ primitives (model mm)
def _basis(d):
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized(); v = d.cross(u).normalized()
    return d, u, v


def turned(origin, axis, loop, n=48, teeth=None):
    """A closed (h, r) outline revolved about `axis` through `origin`: h along the axis, r the radius (0 = on the axis).
    teeth = (count, depth, h0, h1): the outer surface between h0 and h1 gets `count` straight flutes `depth` deep (a knurled grip)."""
    o = Vector(origin); d, u, v = _basis(axis)
    if teeth: n = teeth[0] * 2
    rmax = max(r for h, r in loop)
    if teeth:           # put outline points at the ends of the fluted band, so the flutes start and stop there
        new = []
        for k in range(len(loop)):
            (ha, ra), (hb, rb) = loop[k], loop[(k + 1) % len(loop)]
            new.append((ha, ra))
            if min(ra, rb) > 0.92 * rmax and abs(hb - ha) > 1e-6:
                cuts = []
                for hc, out in ((teeth[2], -0.3), (teeth[3], 0.3)):
                    for hh in (hc + out, hc):
                        if min(ha, hb) + 1e-6 < hh < max(ha, hb) - 1e-6: cuts.append(hh)
                for hh in sorted(cuts, reverse=hb < ha): new.append((hh, ra + (rb - ra) * (hh - ha) / (hb - ha)))
        loop = new
    bm = bmesh.new(); rings = []
    for h, r in loop:
        if r < 1e-6:
            rings.append([bm.verts.new(o + d * h)] * n)
        else:
            row = []
            for i in range(n):
                rr = r
                if teeth and teeth[2] - 1e-6 <= h <= teeth[3] + 1e-6 and i % 2 == 1 and r > 0.92 * rmax: rr = r - teeth[1]
                a = 2 * math.pi * i / n
                row.append(bm.verts.new(o + d * h + (u * math.cos(a) + v * math.sin(a)) * rr))
            rings.append(row)
    m = len(loop)
    for j in range(m):
        a, b = rings[j], rings[(j + 1) % m]
        for i in range(n):
            vs = []
            for q in (a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]):
                if q not in vs: vs.append(q)
            if len(vs) >= 3:
                try: bm.faces.new(vs)
                except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return bm


def lathe(loop, n=48, s0=0.0, z0=0.0, teeth=None):
    """Closed (l, r) outline revolved about the line parallel to the optical axis through (s0, z0)."""
    return turned((0, s0, z0), (1, 0, 0), loop, n, teeth)


def cyl(p0, p1, r, n=24, r1=None, r_in=0.0):
    """Cylinder, cone or tube from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1); h = (p1 - p0).length; r1 = r if r1 is None else r1
    if r_in > 0: loop = [(0, r_in), (0, r), (h, r1), (h, r_in)]
    else: loop = [(0, 0), (0, r), (h, r1), (h, 0)]
    return turned(p0, p1 - p0, loop, n)


def box(l0, l1, s0, s1, z0, z1):
    bm = bmesh.new()
    vs = [bm.verts.new((l, s, z)) for l in (l0, l1) for s in (s0, s1) for z in (z0, z1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): bm.faces.new([vs[i] for i in f])
    return bm


def prism(outline, a, b, ax='l'):
    """Outline extruded from a to b along an axis: ax='l' takes (s, z) points, 's' takes (l, z), 'z' takes (l, s)."""
    mp = {'l': lambda u, v, w: (w, u, v), 's': lambda u, v, w: (u, w, v), 'z': lambda u, v, w: (u, v, w)}[ax]
    bm = bmesh.new()
    lo = [bm.verts.new(mp(u, v, a)) for u, v in outline]; hi = [bm.verts.new(mp(u, v, b)) for u, v in outline]
    n = len(outline)
    bm.faces.new(lo); bm.faces.new(hi[::-1])
    for i in range(n): bm.faces.new((lo[i], hi[i], hi[(i + 1) % n], lo[(i + 1) % n]))
    return bm


def join(*bms):
    out = bms[0]; tmp = bpy.data.meshes.new('tmp')
    for b in bms[1:]:
        b.to_mesh(tmp); out.from_mesh(tmp); b.free()
    bpy.data.meshes.remove(tmp)
    return out


def rotate(bm, origin, axis, deg):
    bmesh.ops.rotate(bm, verts=bm.verts, cent=Vector(origin), matrix=Matrix.Rotation(math.radians(deg), 3, Vector(axis)))
    return bm


# ------------------------------------------------------------------ parts
def _raw(name, bm, pivot):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts:
        l, s, z = v.co
        v.co = Vector((s * MM, -l * MM, z * MM)) - pivot
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location = pivot
    return o


def _apply(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = o.data; o.modifiers.clear(); o.data = me; bpy.data.meshes.remove(old); me.name = o.name


def part(name, bm, mat, parent=None, pivot=None, bevel=0.3, cuts=(), sharp=35, what='', dims=None, source='inferred'):
    """Turn a bmesh (model mm) into a named part. pivot (model mm) is its origin: the axis of a part that turns.
    what / dims / source go to inventory.json: what the part is, its governing dimensions in mm, and where they come from."""
    assert name not in OBJ, name
    if pivot is None:
        cs = [v.co.copy() for v in bm.verts]
        pivot = (sum(c.x for c in cs) / len(cs), sum(c.y for c in cs) / len(cs), sum(c.z for c in cs) / len(cs))
    wp = bl(pivot)
    o = _raw(name, bm, wp)
    for c in cuts:
        co = _raw('cutter', c, Vector((0, 0, 0)))
        m = o.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.object = co
        _apply(o); bpy.data.objects.remove(co)
    me = o.data
    for p in me.polygons: p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(sharp))
    if bevel:
        b = o.modifiers.new('bevel', 'BEVEL'); b.limit_method = 'ANGLE'; b.angle_limit = math.radians(sharp); b.width = bevel * MM; b.segments = 2; b.use_clamp_overlap = True
    wn = o.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.weight = 60
    me.materials.clear(); me.materials.append(MATS[mat])
    par = OBJ[parent or ROOT[0]]
    o.parent = par; o.location = wp - W[par.name]
    OBJ[name] = o; W[name] = wp
    INV.append(dict(part=name, parent=par.name, material=mat, what=what, dims_mm=dims or {}, source=source))
    return o


def socket(name, p, parent=None):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.01
    bpy.context.scene.collection.objects.link(e); par = OBJ[parent or ROOT[0]]; e.parent = par; e.location = bl(p) - W[par.name]
    OBJ[name] = e; W[name] = bl(p); SOCK[name] = [round(p[1] * MM, 6), round(p[2] * MM, 6), round(p[0] * MM, 6)]     # asset frame: +X left, +Y up, +Z muzzle
    return e


# ------------------------------------------------------------------ clips (24 fps, one NLA track per clip)
def key(clip, name, chan, keys, note=''):
    """chan: ('loc', 'l'|'s'|'z') offset in mm from rest, or ('rot', 'l'|'s'|'z') degrees about that model axis through the part's pivot."""
    CLIPS.setdefault(clip, dict(note=note, parts={}))['parts'].setdefault(name, []).append((chan, keys))
    if note: CLIPS[clip]['note'] = note


def bake_clips():
    reg = {}
    for clip, c in CLIPS.items():
        last = 1
        for name, chans in c['parts'].items():
            o = OBJ[name]; rest = o.location.copy(); o.rotation_mode = 'XYZ'
            ad = o.animation_data_create(); act = bpy.data.actions.new(f'{clip}.{name}'); ad.action = act
            for (kind, ax), keys in chans:
                for fr, v in keys:
                    last = max(last, fr)
                    if kind == 'loc':
                        d = {'l': Vector((0, -v * MM, 0)), 's': Vector((v * MM, 0, 0)), 'z': Vector((0, 0, v * MM))}[ax]; i = {'l': 1, 's': 0, 'z': 2}[ax]
                        o.location = rest + d; o.keyframe_insert('location', index=i, frame=fr); o.location = rest
                    else:
                        i = {'s': 0, 'l': 1, 'z': 2}[ax]; e = [0.0, 0.0, 0.0]; e[i] = math.radians(v) * (-1 if ax == 'l' else 1)     # +l is Blender -Y
                        o.rotation_euler = e; o.keyframe_insert('rotation_euler', index=i, frame=fr); o.rotation_euler = (0, 0, 0)
            for fc in _fcurves(act):
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            tr = ad.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 1, act); tr.mute = True
            ad.action = None; o.location = rest; o.rotation_euler = (0, 0, 0)
        reg[clip] = dict(parts=sorted(c['parts']), frames=last, note=c['note'])
    return reg


def _fcurves(act):
    try:
        return list(act.fcurves)
    except Exception:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags: out.extend(bag.fcurves)
        return out


# ------------------------------------------------------------------ export
def finish_build(here, name, extra=None):
    """Apply modifiers, bake clips, write work/<name>.glb and .blend (ignored by git), stats.json and inventory.json (committed)."""
    sc = bpy.context.scene
    meshes = [o for o in OBJ.values() if o.type == 'MESH']
    for o in meshes: _apply(o)
    tris = {}
    for o in meshes:
        o.data.calc_loop_triangles(); tris[o.name] = len(o.data.loop_triangles)
    reg = bake_clips()
    sc.frame_start = 1; sc.frame_end = max([c['frames'] for c in reg.values()] + [2])
    work = os.path.join(here, 'work'); os.makedirs(work, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(work, name + '.blend'))
    bpy.ops.export_scene.gltf(filepath=os.path.join(work, name + '.glb'), export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_apply=False, export_yup=True)
    bb = [[min((o.matrix_world @ Vector(c))[i] for o in meshes for c in o.bound_box) for i in range(3)], [max((o.matrix_world @ Vector(c))[i] for o in meshes for c in o.bound_box) for i in range(3)]]
    stats = dict(asset=name, parts=len(meshes), triangles=sum(tris.values()), clips=reg, sockets=SOCK,
                 size_mm=dict(length=round((bb[1][1] - bb[0][1]) * 1000, 1), width=round((bb[1][0] - bb[0][0]) * 1000, 1), height=round((bb[1][2] - bb[0][2]) * 1000, 1)),
                 hierarchy={o.name: o.parent.name for o in OBJ.values() if o.parent}, triangles_by_part=tris, **(extra or {}))
    json.dump(stats, open(os.path.join(here, 'stats.json'), 'w'), indent=1)
    json.dump(INV, open(os.path.join(here, 'inventory.json'), 'w'), indent=1)
    print(f'BUILT {name}: {len(meshes)} parts, {sum(tris.values())} triangles, {len(reg)} clips, {len(SOCK)} sockets, size {stats["size_mm"]}', flush=True)
    return stats
