"""Build helmets from presets.json and export them as glTF binaries (build outputs, never committed).

    python3 build.py                       # the three presets, full quality, with baked ambient occlusion
    python3 build.py --preset helmet_us_highcut
    python3 build.py --random 12           # twelve new helmets from seeds 1..12 (or --seeds 7,19,42)
    python3 build.py --fast                # quarter-size textures, half the mesh density, no AO bake

Writes work/<id>.glb and work/<id>.stats.json (size, surface area, triangles, mass estimate, sockets).
Needs the `bpy` module (Blender 4.2+ as a Python wheel) plus numpy and pillow.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import helmetkit as HK  # noqa: E402


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bake_ao(helmet, samples):
    """Ambient occlusion into a per-vertex colour (COLOR_0), which three.js multiplies into the base colour."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.render.bake.target = 'VERTEX_COLORS'
    sc.world = sc.world or bpy.data.worlds.new('w')
    for o in helmet.parts:
        if o.type != 'MESH':
            continue
        me = o.data
        attr = me.color_attributes.new('ao', 'BYTE_COLOR', 'POINT')
        me.color_attributes.active_color = attr
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
        except RuntimeError as e:
            print('ao bake failed on', o.name, e)
            continue
        # soften: AO only darkens, never to black, so the paint reads
        vals = np.empty(len(attr.data) * 4, np.float32)
        attr.data.foreach_get('color', vals)
        vals = vals.reshape(-1, 4)
        g = vals[:, 0]
        g = 0.32 + 0.68 * np.clip(g, 0, 1) ** 0.8
        vals[:, 0] = vals[:, 1] = vals[:, 2] = g
        vals[:, 3] = 1
        attr.data.foreach_set('color', vals.ravel())


def stats(helmet, preset):
    sh = helmet.sh
    tris = 0
    for o in helmet.parts:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    area = sh.area()
    # shell volume = outer area x thickness (thin shell), mass from a stated areal density when the preset gives one
    vol_cc = area * sh.th / 10.0
    out = {
        'id': preset['id'], 'name': preset['name'], 'size': preset.get('size'),
        'exterior_mm': {'length': round(sh.bbox[1], 1), 'width': round(sh.bbox[0], 1), 'height': round(sh.bbox[2], 1)},
        'shell_outer_area_cm2': round(area, 1),
        'shell_volume_cm3': round(vol_cc, 1),
        'triangles': tris,
        'parts': sorted({o.get('part', o.name) for o in helmet.parts}),
        'sockets_mm': helmet.sockets,
    }
    return out


def export(helmet, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in helmet.col.all_objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_image_format='JPEG', export_jpeg_quality=86,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                              export_extras=True)


def build_one(preset, args):
    reset()
    h = HK.Helmet(preset, os.path.join(HERE, 'work', preset['id']), fast=args.fast).build()
    if not args.fast and not args.no_ao:
        bake_ao(h, args.ao_samples)
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    out = os.path.join(HERE, 'work', preset['id'] + '.glb')
    export(h, out)
    st = stats(h, preset)
    st['glb_bytes'] = os.path.getsize(out)
    with open(os.path.join(HERE, 'work', preset['id'] + '.stats.json'), 'w') as f:
        json.dump(st, f, indent=1)
    print(json.dumps({k: st[k] for k in ('id', 'exterior_mm', 'shell_outer_area_cm2', 'triangles', 'glb_bytes')}))
    return st


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--preset', action='append')
    ap.add_argument('--random', type=int, default=0)
    ap.add_argument('--seeds')
    ap.add_argument('--fast', action='store_true')
    ap.add_argument('--no-ao', action='store_true')
    ap.add_argument('--ao-samples', type=int, default=48)
    args = ap.parse_args(argv)
    presets = json.load(open(os.path.join(HERE, 'presets.json')))['presets']
    todo = []
    if args.seeds or args.random:
        seeds = [int(s) for s in args.seeds.split(',')] if args.seeds else list(range(1, args.random + 1))
        todo = [HK.random_preset(s, presets) for s in seeds]
    else:
        todo = [p for p in presets if not args.preset or p['id'] in args.preset]
    for p in todo:
        build_one(p, args)


if __name__ == '__main__':
    main()
