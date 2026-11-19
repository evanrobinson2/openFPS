"""Put a loaded build into the pose at a frame of one or more clips (NLA tracks named after the clip)."""
import bpy
_REST = {}

def clip_lengths():
    out = {}
    for o in bpy.data.objects:
        if o.animation_data:
            for tr in o.animation_data.nla_tracks:
                out[tr.name] = max(out.get(tr.name, 0), max(int(s.frame_end) for s in tr.strips))
    return out

def pose(clips=None):
    """clips: dict clip -> frame (or None for the rest pose). Objects not in those clips return to rest."""
    clips = clips or {}
    sc = bpy.context.scene
    anim = [o for o in bpy.data.objects if o.animation_data]
    if not _REST:
        for o in anim:
            _REST[o.name] = (o.location.copy(), o.rotation_euler.copy())
    for o in anim:
        for tr in o.animation_data.nla_tracks:
            tr.mute = True
        o.location, o.rotation_euler = _REST[o.name][0].copy(), _REST[o.name][1].copy()
    bpy.context.view_layer.update()
    # one clip at a time: an object only ever belongs to one of the clips being shown
    for clip, frame in clips.items():
        objs = [o for o in anim if any(tr.name == clip for tr in o.animation_data.nla_tracks)]
        for o in objs:
            for tr in o.animation_data.nla_tracks:
                tr.mute = tr.name != clip
        sc.frame_set(int(frame)); sc.frame_set(int(frame))
        vals = {o.name: (o.location.copy(), o.rotation_euler.copy()) for o in objs}
        for o in objs:
            for tr in o.animation_data.nla_tracks:
                tr.mute = True
        sc.frame_set(int(frame)); sc.frame_set(int(frame))
        for o in objs:
            o.location, o.rotation_euler = vals[o.name]
    bpy.context.view_layer.update()
