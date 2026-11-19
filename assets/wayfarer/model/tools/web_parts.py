"""Split a GLB into JSON parts small enough for a static page host (each under a size cap).

    python3 tools/web_parts.py out/wayfarer_lod1.glb DIR [--cap-mb 14] [--name wayfarer]

Writes DIR/<name>.gltf.json = {"gltf": <the glTF JSON>, "bin": "<base64>", "more": ["<name>.bin2.json", ...]} and each
"more" file = {"bin": "<base64>"}. A page decodes the bin parts in order, joins them and has the GLB's one buffer back.
The parts are build outputs: never committed.
"""
import sys, os, json, struct, base64

def split(glb, out_dir, cap_mb=14.0, name='wayfarer'):
    d = open(glb, 'rb').read()
    jl = struct.unpack('<I', d[12:16])[0]; gltf = json.loads(d[20:20 + jl]); o = 20 + jl
    bl = struct.unpack('<I', d[o:o + 4])[0]; b = d[o + 8:o + 8 + bl]
    head = len(json.dumps(gltf, separators=(',', ':')))
    cap = int(cap_mb * 1e6); raw = (cap - 200) // 4 * 3
    first = max(3, (cap - head - 400) // 4 * 3)
    chunks = [b[:first]]; p = first
    while p < len(b):
        chunks.append(b[p:p + raw]); p += raw
    more = [f'{name}.bin{k + 2}.json' for k in range(len(chunks) - 1)]
    os.makedirs(out_dir, exist_ok=True)
    files = [(f'{name}.gltf.json', dict(gltf=gltf, bin=base64.b64encode(chunks[0]).decode(), more=more))]
    files += [(m, dict(bin=base64.b64encode(c).decode())) for m, c in zip(more, chunks[1:])]
    for fn, obj in files:
        p = os.path.join(out_dir, fn); json.dump(obj, open(p, 'w'), separators=(',', ':'))
        print(fn, round(os.path.getsize(p) / 1e6, 2), 'MB')
    return [f for f, _ in files]

if __name__ == '__main__':
    a = sys.argv[1:]
    cap = float(a[a.index('--cap-mb') + 1]) if '--cap-mb' in a else 14.0
    nm = a[a.index('--name') + 1] if '--name' in a else 'wayfarer'
    split(a[0], a[1], cap, nm)
