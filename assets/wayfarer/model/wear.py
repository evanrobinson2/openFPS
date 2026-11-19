"""The wear layer: one colour attribute ('wear') on every mesh, computed from where a vertex is on the ship.

It is a multiplier on the role colour of the material, so the materials stay the flat, named roles the game reads and
the wear travels with the geometry (glTF COLOR_0). Nothing here is painted or sampled from an image: every term is a
rule (belly grime, rain streaks down the flanks, soot aft, plate-to-plate variation, scuffing near the decks) driven by
lattice noise with fixed seeds, so a rebuild gives the same ship.

    exterior   tone variation, per-plate tint, belly grime, streaks, soot towards the nozzles, bleaching on top
    interior   light tone variation and scuffing just above the decks

Lights, screens, glass and placards are left clean. Turn it off with  build.py --no-wear.
"""
import zlib
import numpy as np
import bpy
import spec, kit

NAME = 'wear'
EXTERIOR = kit.EXTERIOR
CLEAN = kit.WEAR_CLEAN
NOMINAL = 0.82          # a clean vertex sits a little under 1 so that lighter patches have room

def clean(material_name):
    r, g, b, me, ro, em, al = kit.PALETTE[material_name]
    return em > 0 or al < 1 or material_name in CLEAN

def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.uint64) * np.uint64(374761393) + iy.astype(np.uint64) * np.uint64(668265263)
         + iz.astype(np.uint64) * np.uint64(2147483647) + np.uint64(seed * 1274126177 + 12345)) & np.uint64(0xffffffff)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xffffffff)
    h = h ^ (h >> np.uint64(16))
    return h.astype(np.float64) / 4294967296.0

def vnoise(P, freq, seed=0):
    """Value noise in 0..1 on a lattice of pitch 1/freq (freq may be a 3-tuple to stretch it)."""
    Q = P * np.asarray(freq, dtype=np.float64) + 1000.0
    I = np.floor(Q).astype(np.int64); F = Q - I
    F = F * F * (3 - 2 * F)
    out = np.zeros(len(P))
    for dx in (0, 1):
        wx = F[:, 0] if dx else 1 - F[:, 0]
        for dy in (0, 1):
            wy = F[:, 1] if dy else 1 - F[:, 1]
            for dz in (0, 1):
                wz = F[:, 2] if dz else 1 - F[:, 2]
                out += wx * wy * wz * _hash(I[:, 0] + dx, I[:, 1] + dy, I[:, 2] + dz, seed)
    return out

def fbm(P, freq, seed=0, octaves=3):
    out = np.zeros(len(P)); amp = 0.5; tot = 0.0
    for k in range(octaves):
        out += amp * vnoise(P, np.asarray(freq, dtype=np.float64) * 2 ** k, seed + 17 * k); tot += amp; amp *= 0.5
    return out / tot

def _islands(nv, lv, lf, starts):
    """Label of the connected piece each vertex belongs to (a plate, a bolt). Capped: long parts keep partial labels."""
    lab = np.arange(nv, dtype=np.int64)
    for _ in range(24):
        fmin = np.minimum.reduceat(lab[lv], starts)
        new = lab.copy(); np.minimum.at(new, lv, fmin[lf])
        if np.array_equal(new, lab): break
        lab = new
    return lab

def colours(o, exterior):
    me = o.data
    nv, nl, nf = len(me.vertices), len(me.loops), len(me.polygons)
    co = np.empty(nv * 3, dtype=np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3).astype(np.float64)
    M = np.array(o.matrix_world); W = co @ M[:3, :3].T + M[:3, 3]
    P = np.stack([W[:, 1] + spec.L / 2, -W[:, 0], W[:, 2]], axis=1)                     # ship frame: s, y, z
    lv = np.empty(nl, dtype=np.int32); me.loops.foreach_get('vertex_index', lv)
    starts = np.empty(nf, dtype=np.int32); me.polygons.foreach_get('loop_start', starts)
    tot = np.empty(nf, dtype=np.int32); me.polygons.foreach_get('loop_total', tot)
    fm = np.empty(nf, dtype=np.int32); me.polygons.foreach_get('material_index', fm)
    fn = np.empty(nf * 3, dtype=np.float32); me.polygons.foreach_get('normal', fn); fn = fn.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T
    lf = np.repeat(np.arange(nf), tot)
    vn = np.zeros((nv, 3)); np.add.at(vn, lv, fn[lf]); vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
    nz = vn[:, 2]
    names = [m.name for m in me.materials]
    tone = fbm(P, 0.45, 1); fine = vnoise(P, 6.0, 2)
    f = np.ones(nv)
    if exterior:
        f *= 1 + 0.30 * (tone - 0.5)
        f *= 1 + 0.03 * (fine - 0.5)
        if o.name.startswith(('armour_plates', 'recess_floors')) or 'bolts' in o.name:
            lab = _islands(nv, lv, lf, starts)
            isl = _hash(lab, lab * 0 + 7, lab * 0 + 3, zlib.crc32(o.name.encode()) % 1000)
            f *= 1 + 0.14 * (isl - 0.5)
            f *= np.where(isl > 0.95, 1.10, np.where(isl < 0.05, 0.86, 1.0))            # the odd replaced plate, the odd scorched one
        belly = np.clip((-0.8 - P[:, 2]) / 2.2, 0, 1)
        f *= 1 - 0.40 * belly * (0.4 + 0.6 * fbm(P, 0.9, 3))
        side = 1 - np.abs(nz)
        streak = np.clip((vnoise(P, (1.6, 0.0, 0.30), 4) - 0.52) / 0.48, 0, 1)
        f *= 1 - 0.10 * streak * side
        soot = np.clip((P[:, 0] - 25.2) / 3.6, 0, 1)
        f *= 1 - 0.50 * soot * (0.55 + 0.45 * tone)
        f *= 1 + 0.05 * np.clip(nz, 0, 1)
    else:
        f *= 1 + 0.07 * (tone - 0.5) + 0.03 * (fine - 0.5)
        dz = np.minimum(np.where(P[:, 2] >= spec.Z_MAIN - 0.02, P[:, 2] - spec.Z_MAIN, 9.0), np.where(P[:, 2] >= spec.Z_LOWER - 0.02, P[:, 2] - spec.Z_LOWER, 9.0))
        f *= 1 - 0.10 * np.clip(1 - dz / 0.35, 0, 1) * (0.5 + 0.5 * fine)
    f = np.clip(NOMINAL * f, 0.30, 1.0)
    d = np.clip((NOMINAL - f) * 2.5, 0, 1)                                              # darker reads warmer: dust and oil, not grey paint
    C = np.stack([f, f * (1 - 0.07 * d), f * (1 - 0.16 * d), np.ones(nv)], axis=1)
    L = C[lv]
    skip = np.array([clean(n) for n in names] or [False], dtype=bool)
    L[skip[np.minimum(fm, len(skip) - 1)][lf]] = 1.0
    return L

def apply():
    bpy.context.view_layer.update()
    n = 0
    for o in bpy.data.objects:
        if o.type != 'MESH' or not len(o.data.polygons): continue
        me = o.data
        L = colours(o, o.name.startswith(EXTERIOR))
        a = me.color_attributes.get(NAME) or me.color_attributes.new(NAME, 'BYTE_COLOR', 'CORNER')
        a.data.foreach_set('color', L.astype(np.float32).ravel())
        me.color_attributes.active_color = a
        try: me.color_attributes.render_color_index = list(me.color_attributes).index(a)
        except Exception: pass
        n += 1
    return n
