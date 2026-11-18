"""Gloved hands, first person: build the model from the recipe.  Rebuilds everything from nothing:

    blender -b --python model/build.py

Reads model/handlib.py (numbers, skeleton, glove shells, skinning), model/glove.py (materials and sewn-on parts) and
hands-gloved.json (grips and clips, written by clips/make.py).  Writes hands-gloved.glb and hands-gloved.blend into
refs-local/build/ (build outputs: ignored by git, never committed) and model/inventory.json (what was built, and how
closely Blender's skinning reproduces the recipe's).

Frame of the export: the rifle's (assets/hk416): metres, +X shooter's left, +Y up, +Z to the muzzle.  In Blender the
whole rig hangs under one empty that turns that frame into Blender's Z-up.  Each hand is one armature (21 bones) with
the shells skinned to it; forearm and hand are both root bones and are keyed in rifle space, the finger bones in
their own rest frames.  One NLA track per clip, 24 fps, the names of hands-gloved.json."""
import bpy, os, sys, json, math
import numpy as np
from mathutils import Matrix, Vector
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model'))
import handlib as hl, glove
OUT = os.path.join(HERE, 'refs-local', 'build'); os.makedirs(OUT, exist_ok=True); MM = 0.001
RT = json.load(open(os.path.join(HERE, 'hands-gloved.json')))
COL = dict(glove_back_knit=((0.36, 0.26, 0.15), 0.92), glove_palm_synthetic_leather=((0.30, 0.21, 0.12), 0.70), glove_fingertip=((0.22, 0.15, 0.09), 0.62),
           glove_flex_rib=((0.27, 0.19, 0.105), 0.8), glove_terry=((0.40, 0.29, 0.17), 1.0), glove_cuff=((0.045, 0.045, 0.05), 0.85), sleeve_fabric=((0.55, 0.56, 0.55), 0.95),
           glove_seam=((0.20, 0.14, 0.08), 0.9), glove_tab=((0.30, 0.22, 0.13), 0.55))
def mat(name):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; c, r = COL[name]
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = r; return m
def M(a): return Matrix([[float(v) for v in row] for row in a])
def metres(m4): m = np.array(m4, float).copy(); m[:3, 3] *= MM; return m
def pq_matrix(p):
    x, y, z, w = p[3:]; R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4); m[:3, :3] = R; m[:3, 3] = p[:3]; return m

bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; sc.render.fps = RT['fps']; sc.unit_settings.system = 'METRIC'
root = bpy.data.objects.new('hands_gloved', None); sc.collection.objects.link(root)
root.matrix_world = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))        # asset frame (Y up, Z muzzle) -> Blender (Z up, -Y muzzle)
h = hl.Hand(); details = glove.detail_parts(h); inv = dict(asset='hands-gloved', parts={}, bones=hl.ORDER, materials=glove.MATERIALS, clips={}, sockets=[])
rigs = {}
for side in 'LR':
    sfx = '_left' if side == 'L' else '_right'; mir = side == 'R'
    rest = {n: metres(hl.mirror_mats(h.rest[i]) if mir else h.rest[i]) for i, n in enumerate(hl.ORDER)}
    ad = bpy.data.armatures.new('armature' + sfx); arm = bpy.data.objects.new('armature' + sfx, ad); sc.collection.objects.link(arm); arm.parent = root
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    for n in hl.ORDER:
        eb = ad.edit_bones.new(n); m = rest[n]; L = max(h.J[n][2] * MM, 0.004)
        eb.head = Vector(m[:3, 3]); eb.tail = Vector(m[:3, 3] + m[:3, 1] * L); eb.align_roll(Vector(m[:3, 2]))
    for n in hl.ORDER:
        p = h.J[n][0]
        if p and n != 'hand': ad.edit_bones[n].parent = ad.edit_bones[p]            # forearm and hand stay roots: both are keyed in rifle space
    bpy.ops.object.mode_set(mode='OBJECT')
    restB = {n: np.array(ad.bones[n].matrix_local) for n in hl.ORDER}                # what Blender actually built (its roll can differ by a sign convention)
    objs = []
    def add_mesh(name, V, F, W=None, bone=None, mats=None, midx=None, smooth=True):
        V = np.asarray(V, float) * MM; F = np.asarray(F)
        if mir: V = V * [-1, 1, 1]; F = F[:, ::-1]
        me = bpy.data.meshes.new(name + sfx); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
        o = bpy.data.objects.new(name + sfx, me); sc.collection.objects.link(o); o.parent = arm
        for mn in (mats or []): me.materials.append(mat(mn))
        if midx is not None: me.polygons.foreach_set('material_index', np.asarray(midx, np.int32)); me.update()
        me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
        if W is not None:
            for bi, bn in enumerate(hl.ORDER):
                idx = np.where(W[:, bi] > 1e-6)[0]
                if len(idx):
                    g = o.vertex_groups.new(name=bn)
                    for i in idx: g.add([int(i)], float(W[i, bi]), 'REPLACE')
        else: o.vertex_groups.new(name=bone).add(list(range(len(V))), 1.0, 'REPLACE')
        md = o.modifiers.new('armature', 'ARMATURE'); md.object = arm
        me.calc_loop_triangles(); inv['parts'][name + sfx] = dict(vertices=len(V), triangles=len(me.loop_triangles), skinned_to=sorted({bn for bi, bn in enumerate(hl.ORDER) if W is not None and W[:, bi].max() > 1e-6} or {bone}))
        objs.append((name, o)); return o
    for n, sh in h.shells.items(): add_mesh(n, sh['V'], sh['F'], W=sh['W'], mats=glove.MATERIALS, midx=glove.face_materials(sh))
    for n, d in details.items(): add_mesh(n, d['V'], d['F'], bone=d['bone'], mats=[d['mat']], midx=np.zeros(len(d['F'])), smooth=False)
    for sock, lmk in (('socket_palm', 'palm_centre'), ('socket_index_tip', 'index_tip'), ('socket_thumb_tip', 'thumb_tip'), ('socket_wrist', 'wrist')):
        bone, p = h.landmarks[lmk]; p = p * MM * ([-1, 1, 1] if mir else [1, 1, 1]); e = bpy.data.objects.new(sock + sfx, None); e.empty_display_size = 0.01; sc.collection.objects.link(e)
        e.parent = arm; e.parent_type = 'BONE'; e.parent_bone = bone; e.matrix_world = root.matrix_world @ Matrix.Translation(Vector(p)); inv['sockets'].append(sock + sfx)
    rigs[side] = dict(arm=arm, rest=rest, restB=restB, objs=objs)

def set_pose(side, hand_pq, fore_pq, q):
    """Pose one armature from a runtime record.  Returns nothing; works for any Blender roll because it goes through world matrices."""
    rg = rigs[side]; arm = rg['arm']; mir = side == 'R'
    H = pq_matrix(hand_pq); F = pq_matrix(fore_pq); Hc = hl.mirror_mats(H) if mir else H; Fc = hl.mirror_mats(F) if mir else F; Hc[:3, 3] /= MM; Fc[:3, 3] /= MM
    Wd = h.fk(np.array(q, float), Hc, Fc); S = h.skin_mats(Wd)
    for i, n in enumerate(hl.ORDER):
        Sk = metres(hl.mirror_mats(S[i]) if mir else S[i]); pb = arm.pose.bones[n]; pb.rotation_mode = 'QUATERNION'
        world = Sk @ rg['restB'][n]; par = arm.pose.bones[n].parent
        if par is None: basis = np.linalg.inv(rg['restB'][n]) @ world
        else:
            j = hl.BI[par.name]; Sp = metres(hl.mirror_mats(S[j]) if mir else S[j]); pw = Sp @ rg['restB'][par.name]
            basis = np.linalg.inv(np.linalg.inv(rg['restB'][par.name]) @ rg['restB'][n]) @ np.linalg.inv(pw) @ world
        pb.matrix_basis = M(basis)
    return S

# ---- skinning parity: Blender's armature deform against the recipe's linear-blend skinning, in every grip
worst = 0.0; dg = bpy.context.evaluated_depsgraph_get()
for gname, g in RT['grips'].items():
    side = g['side']; S = set_pose(side, g['hand'], g['forearm'], g['angles']); bpy.context.view_layer.update(); dg.update(); mir = side == 'R'
    for n, o in rigs[side]['objs']:
        if n not in h.shells: continue
        ref = h.pose_shell(n, S) * MM * ([-1, 1, 1] if mir else [1, 1, 1]); ev = o.evaluated_get(dg); Mw = np.array(root.matrix_world.inverted() @ ev.matrix_world)
        V = np.array([v.co for v in ev.data.vertices]); V = V @ Mw[:3, :3].T + Mw[:3, 3]; worst = max(worst, float(np.abs(V - ref).max()))
inv['skinning_parity'] = dict(grips=len(RT['grips']), worst_vertex_difference_mm=round(worst / MM, 5), note="Blender's armature modifier against handlib's linear-blend skinning, every shell vertex, every grip")
print('PARITY worst vertex difference %.5f mm' % (worst / MM), flush=True)

# ---- clips: one action per clip and hand, pushed to NLA tracks named after the clip
for cname, c in RT['clips'].items():
    for side in 'LR':
        arm = rigs[side]['arm']; ad = arm.animation_data_create(); act = bpy.data.actions.new(f"{cname}.{arm.name}"); ad.action = act
        if hasattr(ad, 'action_slot') and len(getattr(act, 'slots', [])): ad.action_slot = act.slots[0]
        for f, fr in enumerate(c[side]):
            set_pose(side, fr['hand'], fr['forearm'], fr['angles'])
            for n in hl.ORDER:
                pb = arm.pose.bones[n]; pb.keyframe_insert('rotation_quaternion', frame=f + 1)
                if pb.parent is None: pb.keyframe_insert('location', frame=f + 1)
        tr = ad.nla_tracks.new(); tr.name = cname; tr.strips.new(cname, 1, act); tr.mute = True; ad.action = None
    inv['clips'][cname] = dict(frames=c['frames'], rifle_clip=c['rifle_clip'], pre_roll=c['pre_roll'])
for side in 'LR':
    g = RT['grips']['fire_indexed' if side == 'R' else 'support']; set_pose(side, g['hand'], g['forearm'], g['angles'])     # leave the rig in its idle grips
sc.frame_start = 1; sc.frame_end = max(c['frames'] for c in RT['clips'].values())
inv['totals'] = dict(parts=len(inv['parts']), triangles=sum(p['triangles'] for p in inv['parts'].values()), bones_per_hand=len(hl.ORDER), clips=len(inv['clips']))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'hands-gloved.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'hands-gloved.glb'), export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS', export_yup=True, export_skins=True)
json.dump(inv, open(os.path.join(HERE, 'model', 'inventory.json'), 'w'), indent=1)
print('BUILT', inv['totals'], flush=True)
