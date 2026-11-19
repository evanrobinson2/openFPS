"""Pack the built model for the web: work/uh60_lod{N}.glb -> work/web/uh60_lod{N}.gltf.json (+ .bin2.json, ...).

The format is the FPS Assets page's: {"gltf": <glTF JSON>, "bin": "<base64>", "more": ["x.bin2.json", ...]}, each
extra part {"bin": "<base64>"}; the base64 strings are concatenated in order. Every file stays under 14 MB.
Also copies the sample page and the flight and sound modules next to them, so work/web/ is a complete site.

    python3 tools/pack_web.py [lod ...]
"""
import base64, json, os, shutil, struct, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'work', 'web')
PART = 13_600_000 // 4 * 4


def pack(lod):
    data = open(os.path.join(HERE, 'work', f'uh60_lod{lod}.glb'), 'rb').read()
    assert data[:4] == b'glTF'
    n = struct.unpack('<I', data[12:16])[0]; js = json.loads(data[20:20 + n]); o = 20 + n
    m = struct.unpack('<I', data[o:o + 4])[0]; b64 = base64.b64encode(data[o + 8:o + 8 + m]).decode()
    head = json.dumps(js, separators=(',', ':'))
    first = max(4, (PART - len(head)) // 4 * 4)
    parts = [b64[:first]] + [b64[i:i + PART] for i in range(first, len(b64), PART)]
    names = [f'uh60_lod{lod}.bin{i + 1}.json' for i in range(1, len(parts))]
    json.dump(dict(gltf=js, bin=parts[0], more=names), open(os.path.join(OUT, f'uh60_lod{lod}.gltf.json'), 'w'), separators=(',', ':'))
    for nm, p in zip(names, parts[1:]):
        json.dump(dict(bin=p), open(os.path.join(OUT, nm), 'w'))
    print(f'lod{lod}:', [round(os.path.getsize(os.path.join(OUT, f)) / 1e6, 2) for f in [f'uh60_lod{lod}.gltf.json'] + names], 'MB')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for lod in ([int(a) for a in sys.argv[1:]] or [0, 1]):
        pack(lod)
    root = os.path.dirname(HERE)
    for src in ('sample/index.html', 'flight/uh60-flight.js', 'sound/uh60-sound.js'):
        shutil.copy(os.path.join(root, src), OUT)
