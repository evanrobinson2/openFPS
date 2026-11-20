"""UH-60A/L Black Hawk, boardable, built from nothing by this recipe:

    python3 build.py                       # LOD0 (with fasteners) + LOD1 (light)  -> work/uh60_lod*.glb (ignored by git)
    python3 build.py --lod 1 --fast        # one LOD, no textures (silhouette iteration)
    python3 build.py --lod 1 --blend       # also save work/uh60_lod1.blend for tools/render.py

Needs the `bpy` wheel (Blender 5.3 as a Python module). No mesh file is an input: every vertex comes from numbers in
recipe.py, which are read off TM 1-1520-237-10 (figures 2-2, 2-3, 6-1, 6-9; see notes/SOURCES.md) or marked inferred.

Authoring frame: inches, STA / BL (+ left) / WL, exactly as the manual's station diagram. Export frame: metres, glTF
+Y up, +Z forward (nose), +X left, origin on the static ground line under the rotor mast (lib.to_world).
"""
import bpy, bmesh, math, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib
from lib import Mesh, T, R, S, IN

ARGV = sys.argv[1:]
if '--' in ARGV: ARGV = ARGV[ARGV.index('--') + 1:]
FAST = '--fast' in ARGV
LODS = [int(ARGV[ARGV.index('--lod') + 1])] if '--lod' in ARGV else [0, 1]
SAVE_BLEND = '--blend' in ARGV
ONLY = ARGV[ARGV.index('--only') + 1].split(',') if '--only' in ARGV else None
LOD = 0
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


import recipe as RC          # numbers and profiles
import materials as MT       # material library + procedural textures
import airframe, rotors, gear, interior, hardware   # assemblies


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc


def build(lod):
    global LOD
    LOD = lod
    reset()
    ctx = RC.Context(lod=lod, fast=FAST, log=log, here=HERE)
    MT.setup(ctx)
    if not FAST:
        import skin, detail
        detail.materials(ctx, os.path.join(HERE, 'work', 'tex'), log)
        import floor, cockpit_floor
        floor.material(ctx, os.path.join(HERE, 'work', 'tex')); cockpit_floor.material(ctx, os.path.join(HERE, 'work', 'tex'))
        skin.material(ctx, skin.build_maps(os.path.join(HERE, 'work', 'tex', str(4096 if lod == 0 else 2048)), 4096 if lod == 0 else 2048, log))
    for name, mod in (('airframe', airframe), ('rotors', rotors), ('gear', gear), ('interior', interior), ('hardware', hardware)):
        if ONLY and name not in ONLY:
            continue
        log(f'--- {name}')
        mod.build(ctx)
    log('--- assemble')
    stats = ctx.assemble()
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    tag = f'uh60_lod{lod}'
    if SAVE_BLEND:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'work', tag + '.blend'))
    out = os.path.join(HERE, 'work', tag + '.glb')
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animations=True,
                              export_animation_mode='NLA_TRACKS', export_yup=True, export_apply=True,
                              export_image_format='JPEG', export_image_quality=88, export_extras=True,
                              export_vertex_color='MATERIAL', export_tangents=False)
    stats['glb_mb'] = round(os.path.getsize(out) / 1e6, 2)
    json.dump(stats, open(os.path.join(HERE, 'work', f'stats_lod{lod}.json'), 'w'), indent=1)
    log('wrote', out, stats['glb_mb'], 'MB', stats['tris'], 'tris')


if __name__ == '__main__':
    for l in LODS:
        build(l)
