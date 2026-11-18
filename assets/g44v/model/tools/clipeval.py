"""Pose the model at a frame of a clip by evaluating the clip's f-curves directly (no NLA evaluation, so nothing is left over
from the previous clip).  Used by render.py and checks.py."""
import bpy
REST = {}
def _fcurves(act):
    try: return list(act.fcurves)
    except Exception: pass
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags: out += list(bag.fcurves)
    return out
def remember():
    for o in bpy.data.objects:
        o.rotation_mode = 'XYZ'; REST[o.name] = (o.location.copy(), o.rotation_euler.copy(), o.scale.copy())
        if o.animation_data:
            o.animation_data.action = None
            for t in o.animation_data.nla_tracks: t.mute = True
def clip_len(name):
    n = 1
    for o in bpy.data.objects:
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                if t.name == name: n = max(n, int(t.strips[0].action.frame_range[1]))
    return n
def pose(name, frame):
    if not REST: remember()
    for o in bpy.data.objects:
        l, r, s = REST[o.name]; o.location = l.copy(); o.rotation_euler = r.copy(); o.scale = s.copy()
        if name and o.animation_data:
            for t in o.animation_data.nla_tracks:
                if t.name != name: continue
                for fc in _fcurves(t.strips[0].action):
                    getattr(o, fc.data_path)[fc.array_index] = fc.evaluate(frame)
    bpy.context.view_layer.update()
