"""Checks on a built work/wayfarer.blend:  python3 tools/checks.py   (writes work/checks.json, exit 1 on a failure)

ENVELOPE   overall size with the gear up against spec (30 x 9 x 6.75 m)
STANDING   a 1.80 m player has headroom on both decks and through every door
FITS       doors and hatches sit inside their openings; the lift deck is flush with the hold floor when stowed
CLIPS      every clip named in the build exists; the lift's belly plate reaches the ground; gear pads sit on it
"""
import bpy, sys, os, json, math
from mathutils import Vector
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path[:0] = [HERE, os.path.join(HERE, 'modules')]
import spec
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'work', 'wayfarer.blend'))
sc = bpy.context.scene
res = []; fails = 0
def check(group, name, ok, detail):
    global fails
    res.append(dict(group=group, name=name, ok=bool(ok), detail=detail)); fails += 0 if ok else 1
    print(f"{group:9s} {'ok  ' if ok else 'FAIL'} {name}: {detail}")
def ship(v): return (v.y + spec.L / 2, -v.x, v.z)
def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = [1e9] * 3; hi = [-1e9] * 3
    for o in objs:
        if o.type != 'MESH': continue
        oe = o.evaluated_get(dg); M = oe.matrix_world
        for c in oe.bound_box:
            p = ship(M @ Vector(c))
            for k in range(3): lo[k] = min(lo[k], p[k]); hi[k] = max(hi[k], p[k])
    return lo, hi
sys.path.insert(0, os.path.join(HERE, 'tools'))
import posing
clips = posing.clip_lengths()
def pose(clip=None, frame=0):
    posing.pose({clip: frame} if clip else None)
allo = [o for o in bpy.data.objects if o.type == 'MESH']
# ---- envelope, gear up
pose('gear_retract', clips.get('gear_retract', 0))
lo, hi = bounds(allo)
size = [hi[k] - lo[k] for k in range(3)]
check('ENVELOPE', 'length', abs(size[0] - spec.L) < 0.05, f'{size[0]:.2f} m (spec {spec.L:.2f})')
check('ENVELOPE', 'width', abs(size[1] - spec.W) < 0.05, f'{size[1]:.2f} m (spec {spec.W:.2f})')
check('ENVELOPE', 'height', abs(size[2] - spec.H) < 0.05, f'{size[2]:.2f} m (spec {spec.H:.2f}), z {lo[2]:.2f} to {hi[2]:.2f}')
check('ENVELOPE', 'nose at station 0', abs(lo[0]) < 0.9, f'foremost point at s = {lo[0]:.2f} (probes and gun muzzles reach ahead of the hull)')
# ---- standing room
pose()
for nm, s0, s1, z, head in (('main deck', spec.ST['cockpit_aft'], spec.ST['eng_aft'], spec.Z_MAIN, spec.HEAD_MAIN), ('lower deck', 4.6, spec.ST['eng_fwd'], spec.Z_LOWER, spec.HEAD_LOWER)):
    w = min(spec.lining_half_width(s, z + spec.PLAYER_H) for s in (s0 + 0.2, 0.5 * (s0 + s1), s1 - 0.2))
    check('STANDING', nm, head >= spec.PLAYER_H + 0.25 and w > 0.6, f'clear height {head:.2f} m; half-width at head height {w:.2f} m')
for o in bpy.data.objects:
    if o.name.startswith('door_') and not o.name.endswith('_track') and o.type == 'MESH':
        l, h = bounds([o])
        check('STANDING', o.name, h[2] - l[2] >= 1.9, f'leaf {h[1] - l[1]:.2f} x {h[2] - l[2]:.2f} m')
# ---- fits
l, h = bounds([bpy.data.objects['lift_cage']])
deck_top = None
import lift_chassis
check('FITS', 'lift deck flush with the hold floor', abs(lift_chassis.ZD - spec.Z_LOWER) < 1e-6, f'deck z {lift_chassis.ZD:.2f}, floor z {spec.Z_LOWER:.2f}')
check('FITS', 'lift cage inside its opening', l[0] >= spec.LIFT['s0'] - 0.02 and h[0] <= spec.LIFT['s1'] + 0.02 and h[1] <= spec.LIFT['half_w'] + 0.15, f's {l[0]:.2f}..{h[0]:.2f}, |y| <= {h[1]:.2f}')
check('FITS', 'lift belly plate closes the hull', abs(l[2] - (-spec.R - 0.035)) < 0.06, f'lowest point z {l[2]:.2f} (hull bottom {-spec.R:.2f})')
l, h = bounds([bpy.data.objects['lander_stub']])
check('FITS', 'lander inside the bay doors', h[1] <= spec.LANDER_BAY['door_half'] and l[0] >= spec.LANDER_BAY['s0'] and h[0] <= spec.LANDER_BAY['s1'] + 0.4, f'{h[0] - l[0]:.2f} x {h[1] - l[1]:.2f} x {h[2] - l[2]:.2f} m, opening {2 * spec.LANDER_BAY["door_half"]:.2f} m wide')
# ---- clips
need = ['gear_retract', 'lift_lower', 'lander_bay_open', 'crew_hatch_open']
for c in need:
    check('CLIPS', c, c in clips, f'{clips.get(c, 0)} frames at {sc.render.fps} fps' if c in clips else 'missing')
pose()
pads = [o for o in bpy.data.objects if o.name.endswith('_pad')]
l, h = bounds(pads)
check('CLIPS', 'gear pads on the ground (rest pose)', abs(l[2] - spec.Z_GROUND) < 0.03, f'pad underside z {l[2]:.2f}, ground {spec.Z_GROUND:.2f}')
pose('gear_retract', clips.get('gear_retract', 0))
legs = [o for o in bpy.data.objects if o.name.startswith('gear_') and ('_leg' in o.name or '_piston' in o.name or '_pad' in o.name)]
l, h = bounds(legs)
check('CLIPS', 'gear stowed inside the hull', l[2] > -spec.R + 0.25, f'lowest point of any leg z {l[2]:.2f} (belly {-spec.R:.2f})')
pose('lift_lower', clips.get('lift_lower', 0))
l, h = bounds([bpy.data.objects['lift_cage']])
check('CLIPS', 'lift belly plate on the ground', abs(l[2] - spec.Z_GROUND) < 0.06, f'lowest point z {l[2]:.2f}, ground {spec.Z_GROUND:.2f}')
l, h = bounds([bpy.data.objects['lift_ramp']])
check('CLIPS', 'ramp toe on the ground', abs(l[2] - spec.Z_GROUND) < 0.08, f'toe z {l[2]:.2f}; ramp reaches s = {l[0]:.2f}')
pose('lander_bay_open', clips.get('lander_bay_open', 0))
l, h = bounds([bpy.data.objects['lander_stub']])
check('CLIPS', 'lander clear of the ground when lowered', l[2] > spec.Z_GROUND + 0.3, f'underside z {l[2]:.2f}, ground {spec.Z_GROUND:.2f}')
json.dump(dict(fails=fails, checks=res), open(os.path.join(HERE, 'work', 'checks.json'), 'w'), indent=1)
print('CHECKS', len(res), 'run,', fails, 'failed')
sys.exit(1 if fails else 0)
