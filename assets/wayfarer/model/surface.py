"""The surface layer: three small tiling textures made by rule at build time, never committed.

    surface_base.png    multiplies the role colour: blotchy grime, bright scratches down to bare metal, dirt specks
    surface_orm.png     glTF occlusion/roughness/metallic: roughness varies, scratches and rubbed patches are shinier
    surface_normal.png  fine dents, scratches and paint texture

One 2 m tile, box-projected in the ship frame (kit.finish writes the UVs), shared by every painted or bare-metal role.
The wear colour attribute (wear.py) rides on top and gives the large-scale variation, so the tile does not read as a
repeat. Seeds are fixed: a rebuild gives the same pixels.

    make(dir)                    write the three PNGs, return their paths
    patch_glb(path, pngs, ...)   embed them in an exported GLB and point the listed materials at them
    wire_blender(pngs, ...)      the same hook-up as Cycles nodes, for the renders
"""
import os, json, struct, zlib
import numpy as np

SIZE = 1024

def _png(path, a):
    """Write an 8-bit RGB PNG with nothing but zlib."""
    h, w, c = a.shape
    raw = b''.join(b'\x00' + a[y].tobytes() for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

def _pnoise(n, cells, rng):
    """Tileable value noise, n x n, on a lattice of cells x cells."""
    g = rng.random((cells, cells))
    x = np.arange(n) * cells / n; i = np.floor(x).astype(int); f = x - i; f = f * f * (3 - 2 * f)
    i1 = (i + 1) % cells
    a = g[np.ix_(i, i)]; b = g[np.ix_(i, i1)]; c = g[np.ix_(i1, i)]; d = g[np.ix_(i1, i1)]
    fx = f[None, :]; fy = f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

def _fbm(n, cells, rng, octaves=4):
    out = np.zeros((n, n)); amp = 0.5; tot = 0
    for k in range(octaves):
        out += amp * _pnoise(n, cells * 2 ** k, rng); tot += amp; amp *= 0.5
    return out / tot

def _blur(a):
    return (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5

def fields(n=SIZE, seed=27):
    rng = np.random.default_rng(seed)
    blotch = _fbm(n, 4, rng, 5)                       # 0..1, large soft patches
    grain = _fbm(n, 64, rng, 3)                       # paint texture
    scr = np.zeros((n, n))                            # scratches: thin bright lines, mostly along one axis
    for k in range(520):
        x, y = rng.random(2) * n
        ang = rng.normal(0.0, 0.22) + (np.pi / 2 if rng.random() < 0.25 else 0.0)
        L = int(rng.gamma(2.0, 28.0)) + 6; w = rng.random() ** 2
        t = np.arange(L)
        xs = (x + np.cos(ang) * t + rng.normal(0, 0.15, L).cumsum() * 0.3).astype(int) % n
        ys = (y + np.sin(ang) * t).astype(int) % n
        np.maximum.at(scr, (ys, xs), (0.35 + 0.65 * w) * np.sin(np.pi * t / L) ** 0.5)
    scr = np.maximum(scr, _blur(scr) * 0.8)
    dent = np.zeros((n, n))                           # dings
    yy, xx = np.mgrid[0:n, 0:n]
    for k in range(70):
        cx, cy = rng.random(2) * n; r = rng.uniform(3, 14)
        dx = (xx - cx + n / 2) % n - n / 2; dy = (yy - cy + n / 2) % n - n / 2
        dent += np.exp(-(dx * dx + dy * dy) / (r * r)) * rng.uniform(0.3, 1.0)
    speck = (_pnoise(n, 256, rng) > 0.93).astype(float); speck = _blur(_blur(speck))
    rub = np.clip((_fbm(n, 6, rng, 3) - 0.58) / 0.2, 0, 1)        # rubbed, polished patches
    return dict(blotch=blotch, grain=grain, scr=scr, dent=np.clip(dent, 0, 1), speck=speck, rub=rub)

def make(out_dir, n=SIZE):
    os.makedirs(out_dir, exist_ok=True)
    F = fields(n)
    base = 0.86 + 0.10 * (F['blotch'] - 0.5) * 2 * 0.9 + 0.03 * (F['grain'] - 0.5)
    base = base * (1 - 0.30 * F['speck']) * (1 - 0.10 * F['dent'])
    base = np.clip(base + 0.22 * F['scr'] + 0.05 * F['rub'], 0, 1)
    warm = np.clip((0.86 - base) * 3, 0, 1)                         # darker reads warmer
    rgb = np.stack([base, base * (1 - 0.05 * warm), base * (1 - 0.12 * warm)], axis=2)
    rough = 0.90 + 0.10 * (F['blotch'] - 0.5) * 2 + 0.05 * (F['grain'] - 0.5) - 0.42 * F['scr'] - 0.30 * F['rub'] + 0.10 * F['speck']
    rough = np.clip(rough, 0.25, 1.0)
    orm = np.stack([np.ones_like(rough), rough, np.ones_like(rough)], axis=2)
    hgt = 0.6 * (F['grain'] - 0.5) * 0.25 - 0.9 * F['scr'] * 0.5 - 1.2 * F['dent'] + 0.15 * (F['blotch'] - 0.5)
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)); dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0))
    nx, ny = -dx * 2.2, dy * 2.2; nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / ln, ny / ln, nz / ln], axis=2) * 0.5 + 0.5
    paths = {}
    for key, a in (('base', rgb), ('orm', orm), ('normal', nrm)):
        p = os.path.join(out_dir, f'surface_{key}.png')
        _png(p, (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)); paths[key] = p
    return paths

def patch_glb(path, pngs, material_names, normal_scale=0.7):
    """Embed the textures in a GLB and attach them to the named materials. Returns how many materials were changed."""
    d = open(path, 'rb').read()
    jl = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + jl]); o = 20 + jl
    bl = struct.unpack('<I', d[o:o + 4])[0]; b = bytearray(d[o + 8:o + 8 + bl])
    j.setdefault('images', []); j.setdefault('textures', []); j.setdefault('samplers', [])
    j['samplers'].append(dict(magFilter=9729, minFilter=9987, wrapS=10497, wrapT=10497)); smp = len(j['samplers']) - 1
    tex = {}
    for key in ('base', 'orm', 'normal'):
        data = open(pngs[key], 'rb').read()
        while len(b) % 4: b.append(0)
        j['bufferViews'].append(dict(buffer=0, byteOffset=len(b), byteLength=len(data))); b.extend(data)
        j['images'].append(dict(bufferView=len(j['bufferViews']) - 1, mimeType='image/png', name=f'surface_{key}'))
        j['textures'].append(dict(sampler=smp, source=len(j['images']) - 1, name=f'surface_{key}')); tex[key] = len(j['textures']) - 1
    while len(b) % 4: b.append(0)
    j['buffers'][0]['byteLength'] = len(b)
    n = 0
    for m in j.get('materials', []):
        if m.get('name') in material_names:
            pbr = m.setdefault('pbrMetallicRoughness', {})
            pbr['baseColorTexture'] = dict(index=tex['base']); pbr['metallicRoughnessTexture'] = dict(index=tex['orm'])
            m['normalTexture'] = dict(index=tex['normal'], scale=normal_scale); n += 1
    js = json.dumps(j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(b)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(b), 0x004E4942) + bytes(b)
    open(path, 'wb').write(out)
    return n

def wire_blender(pngs, material_names, normal_scale=0.7):
    """Hook the same textures into the Cycles materials (after the GLB is written: the exporter reads the plain graph)."""
    import bpy
    img = {k: bpy.data.images.load(p) for k, p in pngs.items()}
    img['orm'].colorspace_settings.name = 'Non-Color'; img['normal'].colorspace_settings.name = 'Non-Color'
    for im in img.values():
        try: im.pack()
        except Exception: pass
    n = 0
    for m in bpy.data.materials:
        if m.name not in material_names or not m.use_nodes: continue
        nt = m.node_tree; N = nt.nodes; L = nt.links
        bsdf = next(x for x in N if x.type == 'BSDF_PRINCIPLED')
        def tex(key):
            t = N.new('ShaderNodeTexImage'); t.image = img[key]; return t
        tb, to, tn = tex('base'), tex('orm'), tex('normal')
        src = bsdf.inputs['Base Color'].links[0].from_socket if bsdf.inputs['Base Color'].links else None
        mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
        A = next(s for s in mix.inputs if s.identifier == 'A_Color'); B = next(s for s in mix.inputs if s.identifier == 'B_Color')
        if src is not None: L.new(src, A)
        else: A.default_value = bsdf.inputs['Base Color'].default_value
        L.new(tb.outputs['Color'], B)
        L.new(next(s for s in mix.outputs if s.identifier == 'Result_Color'), bsdf.inputs['Base Color'])
        sep = N.new('ShaderNodeSeparateColor'); L.new(to.outputs['Color'], sep.inputs['Color'])
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = bsdf.inputs['Roughness'].default_value
        L.new(sep.outputs['Green'], mul.inputs[0]); L.new(mul.outputs['Value'], bsdf.inputs['Roughness'])
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_scale
        L.new(tn.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
        n += 1
    return n
