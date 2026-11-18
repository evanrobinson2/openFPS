"""F-27 Wayfarer, boardable gunship. Rebuilds everything from nothing:

    python3 build.py                    # needs the bpy module (pip install bpy); or: blender -b --python build.py --
    python3 build.py --only fuselage,cockpit      # build some modules only
    python3 build.py --glb              # also export out/wayfarer.glb (a build output: never committed)
    python3 build.py --figures          # add 1.80 m scale figures (for renders)

Each module in modules/ builds one part of the ship under its own node: fuselage, cockpit, engines, landing_gear,
lift_chassis, lander_bay, gadgets. They share one hull definition (spec.py, hullgrid.py), so a door always fits its opening.
Writes work/wayfarer.blend and work/stats.json.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, 'modules')]
import bpy
import spec, kit
from kit import empty
from hullgrid import Hull

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
def arg(k, d=None): return ARGV[ARGV.index(k) + 1] if k in ARGV else d
MODULES = ['fuselage', 'cockpit', 'engines', 'landing_gear', 'lift_chassis', 'lander_bay', 'gadgets', 'interior']

def build():
    t0 = time.time()
    only = arg('--only'); mods = only.split(',') if only else MODULES
    kit.reset_scene()
    empty('wayfarer')
    H = Hull()
    import fuselage
    fuselage.layout(H)
    info = {}
    for name in mods:
        try:
            m = __import__(name)
        except ModuleNotFoundError as e:
            if e.name != name: raise
            print('SKIP (not written yet)', name); continue
        t1 = time.time()
        info[name] = m.build(H) or {}
        print(f'BUILT {name} in {time.time() - t1:.1f} s', info[name], flush=True)
    if '--figures' in ARGV:
        import figure
        figure.scene_figures()
    clips = kit.bake_clips()
    print('CLIPS', clips)
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    tag = arg('--tag', 'wayfarer')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'work', tag + '.blend'))
    groups = {}
    for k, v in kit.STATS.items():
        g = groups.setdefault(v['group'], dict(objects=0, tris=0)); g['objects'] += 1; g['tris'] += v['tris']
    stats = dict(objects=len(kit.STATS), tris=sum(v['tris'] for v in kit.STATS.values()), groups=groups, info=info,
                 clips=clips, parts={k: v['tris'] for k, v in sorted(kit.STATS.items())})
    json.dump(stats, open(os.path.join(HERE, 'work', tag + '_stats.json'), 'w'), indent=1)
    print('TOTAL', stats['objects'], 'objects', stats['tris'], 'tris', {k: v['tris'] for k, v in groups.items()}, f'{time.time() - t0:.1f} s')
    if '--glb' in ARGV:
        os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
        out = os.path.join(HERE, 'out', tag + '.glb')
        bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_apply=True, export_yup=True, export_animations=True,
                                  export_animation_mode='NLA_TRACKS', export_extras=True)
        print('GLB', out, round(os.path.getsize(out) / 1e6, 1), 'MB')

if __name__ == '__main__':
    build()
