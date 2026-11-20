"""Cabin floor and lower interior, from TM 1-1520-237-10 figure 6-11 (Cargo Tiedown Arrangement) and figure 6-9.

Figure 6-11 is a dimensioned plan of the cargo floor: STA 247 to 398, BL 36.5 left to 36.5 right, compartment lines at
STA 288 and 343, every tie-down fitting and seat-stud pan drawn in place, and the cargo hook access door on the
centre line. Positions below are read off that figure against its own STA and BL scales (about +-0.5 in).
The manual's text (6.18): the fittings are rated 5,000 lb and "incorporate studs that are used to install the troop
seats"; eight net restraint rings sit on the walls at STA 308 and 379; the floor is rated 300 lb per square foot.

Drawn in the figure: floor outline, fitting positions and which are ring / stud pans, pan orientation, hook door.
Inferred [INF]: pan depth and section, ring and stud sizes, panel joints other than the two compartment lines, screw
pitch, sill and kick-strip sections, all wear.
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw
import lib, recipe as RC, skin
from lib import Mesh, T, R, S

FLOOR = RC.WL_CABIN_FLOOR
S0, S1 = 247.0, 398.0          # [F6-11]
HALF = 36.5                    # [F6-11]
PAN_DEPTH = 1.05               # [INF]
# (STA, BL, kind, angle of the pan's long axis from the STA axis in degrees). BL + = left. [F6-11]
FITTINGS = [
    (255.0, 4.5, 'ring', 0), (254.0, -13.0, 'ring', 0),
    (274.0, 27.7, 'ring', 0), (273.0, 8.0, 'oval_ring', 65), (273.5, -11.0, 'oval_ring', -65), (274.0, -28.8, 'ring', 0),
    (292.5, 29.8, 'oval_ring', 20), (292.5, 9.8, 'studs', 90), (292.5, -10.5, 'studs', 90), (292.5, -30.5, 'oval_ring', -20),
    (313.0, 29.0, 'oval_ring', 90), (313.0, 9.7, 'oval_ring', 90), (313.0, -10.3, 'oval_ring', 90), (313.0, -29.8, 'oval_ring', 90),
    (331.3, 30.0, 'oval_ring', 20), (331.0, 9.8, 'oval_ring', 0), (331.0, -10.3, 'oval_ring', 0), (331.3, -30.7, 'oval_ring', -20),
    (332.6, 20.0, 'studs', 90), (332.6, 0.0, 'studs', 90), (332.6, -20.7, 'studs', 90),
    (349.4, 20.0, 'studs', 90), (349.0, 0.0, 'studs', 90), (349.4, -20.3, 'studs', 90),
    (367.2, 30.0, 'ring', 0), (367.2, 10.0, 'ring', 0), (367.2, -10.0, 'ring', 0), (367.2, -30.7, 'ring', 0),
    (379.0, 20.0, 'triple', 90), (379.0, 0.0, 'triple', 90), (379.0, -20.0, 'triple', 90),
    (394.6, 20.0, 'studs', 90), (394.6, 0.0, 'studs', 90), (394.6, -20.5, 'studs', 90),
]
SIZE = {'ring': (4.4, 4.4), 'oval_ring': (7.0, 4.2), 'studs': (6.2, 3.4), 'triple': (8.4, 4.0)}   # pan length, width [F6-11 scaled]
HOOK_DOOR = (351.5, 362.0, 9.5)   # STA fwd, STA aft, half width [F6-11]
JOINTS_STA = [288.0, 343.0]        # compartment lines [F6-11]
JOINTS_STA_INF = [267.5, 315.5, 370.5]
JOINTS_BL = [-18.25, 18.25]        # [INF]
PPI = 13.5


def stadium(L, W, k=8):
    r = W / 2; h = max(L / 2 - r, 0.0); pts = []
    for cx, a0 in ((h, -90), (-h, 90)):
        for i in range(k + 1):
            a = math.radians(a0 + 180 * i / k); pts.append((cx + r * math.cos(a), r * math.sin(a)))
    return np.array(pts)


def pan_outline(f, grow=0.0):
    s, bl, kind, ang = f; L, W = SIZE[kind]
    o = stadium(L + 2 * grow, W + 2 * grow); a = math.radians(ang); c, sn = math.cos(a), math.sin(a)
    return np.stack([s + o[:, 0] * c - o[:, 1] * sn, bl + o[:, 0] * sn + o[:, 1] * c], 1)


def stud_points():
    """Aircraft (STA, BL) of every seat stud on the floor, for the troop-seat cables."""
    out = []
    for s, bl, kind, ang in FITTINGS:
        a = math.radians(ang); c, sn = math.cos(a), math.sin(a)
        offs = {'studs': (-1.25, 1.25), 'triple': (-2.9, 2.9), 'oval_ring': (SIZE['oval_ring'][0] / 2 - 1.6,)}.get(kind, ())
        out += [(s + d * c, bl + d * sn) for d in offs]
    return out


# ------------------------------------------------------------------ the maps
INK = (205, 200, 170)


def paint(prefix, out_dir, s0, s1, half, spec, log=print, seed=11):
    """Paint one floor's colour, normal and ORM maps. The image has STA along +x and the aircraft's left side at the
    bottom, as the floor reads from above with the nose to the left. spec keys:
      lines  [((sta, bl), (sta, bl))]  panel joints, each with a screw row either side
      covers [(sta0, sta1, bl0, bl1)]  removable covers: groove, corner fasteners, chipped edge
      pans   [polygon (n, 2)]          recesses: paint worn round them
      wear   [(sta, bl, r_sta, r_bl, strength 0..255)]
      text   [(sta, bl, string, size)]
      plates [(sta0, sta1, bl0, bl1)]  bare metal tread plates (ribbed)
      mask   fn(sta, bl) -> bool array, True where the floor exists (screws only there)"""
    os.makedirs(out_dir, exist_ok=True)
    pc, pn, po = (os.path.join(out_dir, f'{prefix}_{k}') for k in ('color.jpg', 'normal.png', 'orm.png'))
    if all(os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(__file__) for p in (pc, pn, po)):
        return pc, pn, po
    TW, TH = int(round((s1 - s0) * PPI)), int(round(2 * half * PPI))
    fpx = lambda sta, bl: ((sta - s0) * PPI, (half + bl) * PPI)
    rng = np.random.default_rng(seed)
    L = lambda: Image.new('L', (TW, TH), 0)
    groove, screw, chip, scuff, plate, rib, ink_im = L(), L(), L(), L(), L(), L(), Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    dg, ds, dc, dsf, dp, dr, di = (ImageDraw.Draw(i) for i in (groove, screw, chip, scuff, plate, rib, ink_im))
    dot = lambda q, r=2.6: ds.ellipse([fpx(*q)[0] - r, fpx(*q)[1] - r, fpx(*q)[0] + r, fpx(*q)[1] + r], fill=255)
    for a, b in spec.get('lines', ()):
        dg.line([fpx(*a), fpx(*b)], fill=255, width=2)
        n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 2.0)
        for i in range(n):                                          # a screw row either side of every joint, 2 in pitch
            t = (i + 0.5) / n; p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            for off in (-0.75, 0.75):
                dot((p[0] + off, p[1]) if a[0] == b[0] else (p[0], p[1] + off))
    for (a0, a1, b0, b1) in spec.get('covers', ()):
        x0, y0 = fpx(a0, b0); x1, y1 = fpx(a1, b1)
        dg.rounded_rectangle([x0, y0, x1, y1], 8, outline=255, width=3); dc.rounded_rectangle([x0, y0, x1, y1], 8, outline=120, width=4)
        for q in ((a0 + 1, b0 + 1), (a0 + 1, b1 - 1), (a1 - 1, b0 + 1), (a1 - 1, b1 - 1), ((a0 + a1) / 2, b0 + 1), ((a0 + a1) / 2, b1 - 1)): dot(q, 4.2)
    for poly in spec.get('pans', ()):                                # paint wears away round every pan
        pts = [fpx(*p) for p in poly]
        dc.line(pts + pts[:1], fill=255, width=6); dsf.polygon(pts, fill=110, outline=110, width=int(4.4 * PPI))
    for (s, b, rs, rb, v) in spec.get('wear', ()):
        x, y = fpx(s, b); dsf.ellipse([x - rs * PPI, y - rb * PPI, x + rs * PPI, y + rb * PPI], fill=v)
    for (a0, a1, b0, b1) in spec.get('plates', ()):
        x0, y0 = fpx(a0, b0); x1, y1 = fpx(a1, b1)
        dp.rounded_rectangle([x0, y0, x1, y1], 5, fill=255); dg.rounded_rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1], 5, outline=255, width=2)
        for bb in np.arange(b0 + 0.6, b1 - 0.4, 0.55):
            xa, ya = fpx(a0 + 0.9, bb); xb, _ = fpx(a1 - 0.9, bb); dr.line([xa, ya, xb, ya], fill=255, width=3)
        for q in ((a0 + 0.45, b0 + 0.6), (a0 + 0.45, b1 - 0.6), (a1 - 0.45, b0 + 0.6), (a1 - 0.45, b1 - 0.6), (a0 + 0.45, (b0 + b1) / 2), (a1 - 0.45, (b0 + b1) / 2)): dot(q, 3.0)
    for (s, b, txt, size) in spec.get('text', ()):
        x, y = fpx(s, b); di.text((x, y), txt, font=skin._font(skin.FONT_C, size), fill=INK + (200,), anchor='mm')
    A = lambda im: np.asarray(im, np.float32) / 255.0
    groove, screw, chipm, scuff, plate, rib = skin.blur(A(groove), 0.8), skin.blur(A(screw), 0.7), skin.blur(A(chip), 1.6), skin.blur(A(scuff), 22.0), skin.blur(A(plate), 0.6), skin.blur(A(rib), 0.9)
    ink = np.asarray(ink_im, np.float32) / 255.0
    n_big, n_mid, n_fine = skin.noise((TH, TW), 300, seed + 10, 4), skin.noise((TH, TW), 60, seed + 11, 4), skin.noise((TH, TW), 9, seed + 12, 3)
    n_px = rng.random((TH, TW)).astype(np.float32)
    grit = skin.blur((n_px > 0.82).astype(np.float32), 0.75) * (1 - plate)     # non-skid: sharp grit in the coating
    sc = Image.new('L', (TW, TH), 0); dsc = ImageDraw.Draw(sc)              # scratches: long thin drags, mostly fore and aft
    for _ in range(int(420 * TW * TH / 2.0e6)):
        x = rng.random() * TW; y = rng.random() * TH; ln = 20 + rng.random() ** 2 * 420; a = rng.normal(0, 0.16) + (math.pi / 2 if rng.random() < 0.25 else 0)
        dsc.line([x, y, x + ln * math.cos(a), y + ln * math.sin(a)], fill=int(60 + rng.random() * 160), width=1)
    scratch = skin.blur(A(sc), 0.6) * (0.4 + 0.9 * n_mid)
    edge = np.clip(1 - np.minimum(np.arange(TH)[:, None], TH - 1 - np.arange(TH)[:, None]) / (3.5 * PPI), 0, 1) * np.ones((1, TW), np.float32)
    worn = np.clip(scuff * (0.35 + 1.1 * n_mid) * (0.7 + 0.6 * n_big), 0, 1)        # where the grit is polished down
    bare = ((chipm * (0.5 + n_fine) * (0.5 + n_px) > 0.6) | (worn * (0.4 + n_fine) * (0.55 + 0.9 * n_px) > 1.22) | (scratch * (0.6 + n_px) > 0.86)).astype(np.float32)
    bare = skin.blur(bare, 0.5)
    base = np.array((0.105, 0.110, 0.100), np.float32)                              # dark grey non-skid walkway coating
    col = base[None, None] * (0.85 + 0.3 * n_big)[..., None] * (0.75 + 0.5 * grit)[..., None]
    col = col * (1 + 0.45 * worn)[..., None] + np.array((0.035, 0.035, 0.032), np.float32) * worn[..., None]
    dirt = np.clip(edge * 0.8 + skin.blur(groove, 3.0) * 1.2 + 0.25 * (n_mid - 0.4), 0, 1)
    col = col * (1 - 0.45 * dirt)[..., None] + np.array((0.16, 0.14, 0.10), np.float32) * (0.22 * dirt * (0.5 + n_fine))[..., None]
    a = ink[..., 3:4] * (0.55 + 0.45 * n_fine)[..., None] * (1 - 0.75 * worn)[..., None]
    col = col * (1 - a) + ink[..., :3] * a
    # tread plates: dull anodised aluminium, bright where boots polish the rib tops
    pcol = np.array((0.20, 0.205, 0.21), np.float32)[None, None] * (0.8 + 0.4 * n_mid)[..., None] + (0.10 * rib * (0.3 + worn + 0.5 * n_fine))[..., None]
    col = col * (1 - plate)[..., None] + pcol * plate[..., None]
    col *= (1 - 0.6 * np.clip(groove * 1.2, 0, 1))[..., None]
    col = col * (1 - 0.35 * screw)[..., None] + np.array((0.30, 0.31, 0.32), np.float32) * (0.35 * screw)[..., None]
    bare *= (1 - plate)
    col = col * (1 - bare)[..., None] + np.array((0.34, 0.345, 0.35), np.float32) * (0.75 + 0.5 * n_fine)[..., None] * bare[..., None]
    h = 0.9 * grit * (1 - 0.75 * worn) - 1.0 * groove + 0.35 * screw - 0.25 * bare - 0.3 * scratch + 0.05 * (n_fine - 0.5) + 1.2 * rib + 0.4 * plate
    gx = np.zeros_like(h); gy = np.zeros_like(h); gx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5; gy[1:-1] = (h[2:] - h[:-2]) * 0.5
    nx, ny, nz = -gx * 1.3, gy * 1.3, np.ones_like(h); ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
    rough = np.clip(0.92 - 0.30 * worn - 0.1 * scratch + 0.05 * dirt, 0.2, 1) * (1 - bare) + 0.38 * bare
    rough = rough * (1 - plate) + (0.5 - 0.15 * rib) * plate
    orm = np.stack([np.clip(1 - 0.5 * groove, 0, 1), rough, np.maximum(bare, plate)], -1)
    sv = lambda a, p, **kw: Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p, **kw)
    sv(col, pc, quality=92); sv(nrm, pn); sv(orm, po)
    log(prefix + ' map', (TW, TH))
    return pc, pn, po


def cabin_spec():
    lines = [((s, -HALF), (s, HALF)) for s in JOINTS_STA + JOINTS_STA_INF] + [((S0, b), (S1, b)) for b in JOINTS_BL]
    lines += [((S0, sg * (HALF - 0.9)), (S1, sg * (HALF - 0.9))) for sg in (1, -1)]
    a, b, hw = HOOK_DOOR
    text = [(s + 4.5, sg * (HALF - 3.4), f'STA {int(s)}', 15) for s in (288.0, 343.0) for sg in (1, -1)]
    text += [(302.0, 0.0, 'MAX FLOOR LOAD 300 LB / SQ FT', 22), (356.7, -1.2, 'CARGO HOOK', 15), (356.7, 0.6, 'ACCESS', 15)]
    # boot traffic: in at each door, along the cabin between the seat rows, heaviest on the sills
    wear = [(342, 30, 34, 9, 255), (342, -30, 34, 9, 255), (320, 0, 60, 9, 150), (342, 14, 26, 12, 160), (342, -14, 26, 12, 160), (262, 0, 12, 20, 120)]
    return dict(lines=lines, covers=[(a, b, -hw, hw)], pans=[pan_outline(f, 0.5) for f in FITTINGS], wear=wear, text=text)


def material(ctx, out_dir, name='cabin_floor', maps=None):
    import bpy
    pc, pn, po = maps or paint('cabin_floor', out_dir, S0, S1, HALF, cabin_spec(), ctx.log)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')

    def tex(p, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(p); t.image.colorspace_settings.name = cs; return t
    nt.links.new(tex(pc, 'sRGB').outputs['Color'], b.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tex(po, 'Non-Color').outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness']); nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex(pn, 'Non-Color').outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    ctx.mats[name] = m


def planar_uv(o, s0=S0, s1=S1, half=HALF):
    from lib import IN
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    nv = len(me.vertices); co = np.zeros(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    sta = co[:, 1] / IN + RC.STA_MAST; bl = co[:, 0] / IN
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    uv = np.stack([(sta - s0) / (s1 - s0), 1 - (half + bl) / (2 * half)], 1)[lv]
    me.uv_layers[0].data.foreach_set('uv', uv.ravel())


# ------------------------------------------------------------------ geometry
def ring(M, r=1.2, bar=0.2, n=18, k=6):
    """A round tie-down ring lying in its pan (local XY), with its hinge lug at -X."""
    a = np.linspace(0, 2 * np.pi, n + 1)
    return lib.tube([(r * math.cos(t), r * math.sin(t), 0) for t in a], bar, k, cap=False), M


def stud(n=10):
    return lib.revolve([(0.46, 0), (0.46, 0.1), (0.22, 0.18), (0.22, 0.46), (0.38, 0.54), (0.38, 0.68), (0.3, 0.74), (0, 0.74)], n, cap0=False, cap1=False)


def fitting(f, hi, pan, stl, dark):
    """Pan liner, ring and studs of one fitting; the hole is cut in the floor by build()."""
    s, bl, kind, ang = f; L, W = SIZE[kind]; n = 8 if hi else 6
    M = T(s, bl, FLOOR) @ R('wl', ang)
    rim = stadium(L, W, n); wall = stadium(L - 0.9, W - 0.9, n); low = stadium(L - 1.5, W - 1.5, n)
    rings = [np.c_[stadium(L + 1.3, W + 1.3, n), np.full(len(rim), 0.0)], np.c_[stadium(L + 1.2, W + 1.2, n), np.full(len(rim), 0.07)],
             np.c_[stadium(L - 0.1, W - 0.1, n), np.full(len(rim), 0.07)], np.c_[rim, np.full(len(rim), -0.02)],
             np.c_[wall, np.full(len(rim), -PAN_DEPTH * 0.72)], np.c_[low, np.full(len(rim), -PAN_DEPTH)]]
    m = lib.loft(np.array(rings), cap0=False, cap1=True, flip=True); pan.merge(m, M)
    if hi:                                                        # flange screws
        fl = stadium(L + 0.55, W + 0.55, 3)
        for p in fl[::2]:
            stl.merge(lib.revolve([(0.17, 0.07), (0.15, 0.11), (0, 0.12)], 6, cap0=False, cap1=False), M @ T(p[0], p[1], 0))
    zb = -PAN_DEPTH
    if kind == 'ring':
        m, _ = ring(None); stl.merge(m, M @ T(0.25, 0, zb + 0.24) @ R('bl', 5))
        dark.merge(lib.box((-1.15, 0, zb + 0.3), (0.7, 1.0, 0.6)), M); stl.merge(lib.cyl((-1.15, -0.62, zb + 0.34), (-1.15, 0.62, zb + 0.34), 0.13, 6), M)
    elif kind == 'oval_ring':
        m, _ = ring(None); stl.merge(m, M @ T(-0.9, 0, zb + 0.24) @ R('bl', 4))
        dark.merge(lib.box((-2.3, 0, zb + 0.3), (0.7, 1.0, 0.6)), M); stl.merge(lib.cyl((-2.3, -0.62, zb + 0.34), (-2.3, 0.62, zb + 0.34), 0.13, 6), M)
        stl.merge(stud(10 if hi else 6), M @ T(L / 2 - 1.6, 0, zb))
    elif kind == 'studs':
        for dx in (-1.25, 1.25): stl.merge(stud(10 if hi else 6), M @ T(dx, 0, zb))
    else:
        m, _ = ring(None, r=1.05); stl.merge(m, M @ T(0.2, 0, zb + 0.24) @ R('bl', 5))
        dark.merge(lib.box((-0.95, 0, zb + 0.3), (0.6, 1.0, 0.6)), M)
        for dx in (-2.9, 2.9): stl.merge(stud(10 if hi else 6), M @ T(dx, 0, zb))


def build(ctx, wall_bl):
    """wall_bl(sta, wl) -> BL of the inside wall (interior.wall_bl)."""
    hi = ctx.lod == 0
    textured = 'cabin_floor' in ctx.mats
    # ---- floor panel with every pan and the hook door gap cut through it
    half = lambda s: float(wall_bl(s, FLOOR)) + 0.4
    sts = np.linspace(S0, S1, 17)
    top = [(s, half(s)) for s in sts] + [(s, -half(s)) for s in sts[::-1]]
    slab = lib.obj('cabin_floor', lib.prism(np.array(top), FLOOR - 1.4, FLOOR), None, 30)
    cut = Mesh()
    for f in FITTINGS:
        cut.merge(lib.prism(pan_outline(f, 0.0), FLOOR - 1.2, FLOOR + 0.5))
    co = lib.obj('cut', cut); lib.shade(co, 30); lib.boolean(slab, co, 'DIFFERENCE')
    o = ctx.part('airframe', 'cabin_floor', slab, 'cabin_floor' if textured else 'floor', 30)
    if textured: planar_uv(o)
    pan, stl, dark, al, od, blk, yel = (Mesh() for _ in range(7))
    for f in FITTINGS:
        fitting(f, hi, pan, stl, dark)
    # ---- cargo hook access door: lid standing 0.06 proud, two hinges forward, two flush latches aft [F6-11]
    a, b, hw = HOOK_DOOR
    for sg in (1, -1):
        al.merge(lib.box((a + 0.6, sg * (hw - 1.6), FLOOR + 0.06), (1.6, 2.2, 0.12)))
        stl.merge(lib.cyl((a + 0.1, sg * (hw - 2.6), FLOOR + 0.16), (a + 0.1, sg * (hw - 0.6), FLOOR + 0.16), 0.16, 8))
        dark.merge(lib.prism(lib.rrect(1.9, 1.0, 0.4, 3), FLOOR - 0.05, FLOOR + 0.05, T(b - 1.6, sg * (hw - 2.2), 0)))
        stl.merge(lib.prism(lib.rrect(1.2, 0.5, 0.2, 2), FLOOR + 0.05, FLOOR + 0.12, T(b - 1.6, sg * (hw - 2.2), 0)))
        if hi:
            for dx in (0.2, 1.0):
                for dy in (-0.7, 0.7): stl.merge(lib.revolve([(0.14, 0.12), (0.12, 0.16), (0, 0.17)], 6, cap0=False, cap1=False), T(a + dx, sg * (hw - 1.6) + dy, FLOOR))
    # ---- door sills: ribbed tread extrusion across each door opening, lip outboard, scuff plate on the jamb ends
    d0, d1 = RC.CABIN_DOOR['poly'][0][0], RC.CABIN_DOOR['poly'][1][0]
    for sg in (1, -1):
        w = float(wall_bl(342.0, FLOOR)); out = float(RC.body_surface_bl(342.0, FLOOR + 0.6))
        zj = RC.CABIN_DOOR['poly'][0][1] - FLOOR + 0.03                 # top of the door jamb the tread sits on
        prof = [(w - 3.9, 0.0), (w - 2.4, zj + 0.16)]
        for i in range(9):                                            # nine anti-slip ribs
            x = w - 2.2 + i * (out - w + 2.0) / 9
            prof += [(x, zj + 0.16), (x + 0.07, zj + 0.3), (x + 0.2, zj + 0.3), (x + 0.27, zj + 0.16)]
        prof += [(out - 0.15, zj + 0.16), (out - 0.1, zj + 0.5), (out + 0.05, zj + 0.5), (out + 0.05, zj - 0.9), (out - 0.1, zj - 0.9), (out - 0.1, zj), (w - 2.4, zj), (w - 3.9, -0.1)]
        P = np.array(prof)
        rings = [np.stack([np.full(len(P), s), sg * P[:, 0], FLOOR + P[:, 1]], 1) for s in (d0 + 0.3, d1 - 0.3)]
        al.merge(lib.loft(np.array(rings), cap0=True, cap1=True, flip=(sg > 0)))
        for s in np.arange(d0 + 3.0, d1 - 1.0, 6.0):                  # countersunk sill screws
            stl.merge(lib.revolve([(0.2, 0.3), (0.17, 0.33), (0, 0.33)], 8, cap0=False, cap1=False), T(s, sg * (w - 1.2), FLOOR + zj))
        # kick strips: an angle along the foot of the wall fore and aft of the door, screwed every 3 in
        for (s_a, s_b) in ((S0 + 0.6, d0 - 1.5), (d1 + 1.5, S1 - 1.0)):
            ss = np.linspace(s_a, s_b, max(3, int((s_b - s_a) / 6)))
            ang = [(0.0, 0.0), (-2.2, 0.0), (-2.2, 0.1), (-0.12, 0.1), (-0.12, 2.6), (0.0, 2.6)]
            rings = []
            for s in ss:
                wb = float(wall_bl(s, FLOOR + 1.3)) - 0.15
                rings.append([(s, sg * (wb + x), FLOOR + z) for x, z in ang])
            od.merge(lib.loft(np.array(rings), cap0=True, cap1=True, flip=(sg > 0)))
            for s in np.arange(s_a + 1.5, s_b - 0.5, 3.0):
                wb = float(wall_bl(s, FLOOR + 1.3)) - 0.15
                stl.merge(lib.revolve([(0.16, 0), (0.14, 0.05), (0, 0.06)], 6, cap0=False, cap1=False), lib.frame_to((s, sg * (wb - 0.12), FLOOR + 1.6), (s, sg * (wb - 1.12), FLOOR + 1.6))[0])
                if hi: stl.merge(lib.revolve([(0.16, 0.1), (0.14, 0.14), (0, 0.15)], 6, cap0=False, cap1=False), T(s + 1.5, sg * (wb - 1.3), FLOOR))
        # cargo-net restraint rings on the walls at STA 308 and 379, low and high [F6-11 sections]
        for s in (306.0, 379.5):
            for wl in (FLOOR + 5.0, 252.0):
                wb = float(wall_bl(s, wl)) - 0.3; M, _ = lib.frame_to((s, sg * wb, wl), (s, sg * (wb - 1.0), wl))
                dark.merge(lib.prism(lib.rrect(2.6, 2.6, 0.5, 3), 0.0, 0.14, M))
                stl.merge(lib.tube([(0.0, -0.75, 0.2), (0.0, -0.75, 0.55), (0.0, -0.45, 1.0), (0.0, 0.45, 1.0), (0.0, 0.75, 0.55), (0.0, 0.75, 0.2)], 0.15, 6), M)
                if hi:
                    for dx in (-0.95, 0.95):
                        for dy in (-0.95, 0.95): stl.merge(lib.revolve([(0.14, 0.14), (0.12, 0.19), (0, 0.2)], 6, cap0=False, cap1=False), M @ T(dx, dy, 0))
    # ---- step up to the cockpit at STA 247: kick plate with a non-skid nosing; aft bulkhead foot angle
    wf = float(wall_bl(247.0, FLOOR)) - 0.3; rise = RC.WL_COCKPIT_FLOOR - FLOOR
    al.merge(lib.box((S0 + 0.45, 0, FLOOR + rise / 2), (0.14, 2 * wf, rise - 0.2)))
    blk.merge(lib.box((S0 - 0.3, 0, RC.WL_COCKPIT_FLOOR + 0.03), (2.2, 2 * wf, 0.1)))
    yel.merge(lib.box((S0 + 0.56, 0, RC.WL_COCKPIT_FLOOR - 0.5), (0.05, 2 * wf, 0.9)))
    for bl in np.arange(-wf + 1.5, wf, 3.0):
        stl.merge(lib.revolve([(0.16, 0), (0.14, 0.05), (0, 0.06)], 6, cap0=False, cap1=False), lib.frame_to((S0 + 0.52, bl, FLOOR + 1.0), (S0 + 1.5, bl, FLOOR + 1.0))[0])
    wa = float(wall_bl(S1 - 1.0, FLOOR)) - 0.3
    od.merge(lib.box((S1 - 1.75, 0, FLOOR + 1.3), (0.12, 2 * wa, 2.6))); od.merge(lib.box((S1 - 2.8, 0, FLOOR + 0.05), (2.2, 2 * wa, 0.1)))
    for bl in np.arange(-wa + 1.5, wa, 3.0):
        stl.merge(lib.revolve([(0.16, 0), (0.14, 0.05), (0, 0.06)], 6, cap0=False, cap1=False), lib.frame_to((S1 - 1.81, bl, FLOOR + 1.6), (S1 - 2.8, bl, FLOOR + 1.6))[0])
    for name, m, mat in (('tiedown_pans', pan, 'alu_dull'), ('tiedown_rings_studs', stl, 'steel'), ('floor_fittings_dark', dark, 'steel_dark'),
                         ('door_sills', al, 'alu_dull'), ('kick_strips', od, 'paint_od_interior'), ('step_nosing', blk, 'floor'), ('step_marking', yel, 'paint_yellow')):
        ctx.part('airframe', name, m, mat, 40)
