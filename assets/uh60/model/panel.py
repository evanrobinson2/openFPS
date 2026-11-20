"""Instrument panel and lower console top, built on the manual's own drawings (manual_art.py: figures 2-9 and 2-8).

The panel face outline, each instrument's outline and every dial, legend and knob position are the manual's. The
glare shield's front outline follows the panel outline (figure 2-9's silhouette shows it wrapping the top and both
sides); how far it stands out is read from the perspective view in figure 2-4 and is an estimate [EST F2-4].
Plate and knob heights are nominal [INF]: the front views do not give them.
"""
import math
import numpy as np
import lib, manual_art as MA
from lib import Mesh, T, R

PLATE_H = 0.12          # [INF]
SK = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])    # sketch (BL, up) -> panel local (normal, BL, up)
KN = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1.0]])   # +Z -> panel normal


def _ccw(poly):
    p = np.asarray(poly, float); a = np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p if a > 0 else p[::-1]


def tri(o):
    """Triangulate n-gons properly: several instrument outlines are concave, and a fan would spill outside them."""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:], ngon_method='EAR_CLIP'); bm.to_mesh(o.data); bm.free()


def knob(r, h, n):
    return lib.revolve([(r, 0), (r, h * 0.16), (r * 0.8, h * 0.24), (r * 0.74, h * 0.9), (r * 0.6, h), (0, h)], n)


def panel(ctx, Mp, art, out):
    blk, knb = out; textured = 'panel_art' in ctx.mats
    W, Hh = art['w'], art['h']; outline = _ccw(art['outline'])
    blk.merge(lib.prism(outline, -2.2, -0.01), Mp @ SK)
    face = Mesh(); face.add([(0.0, y, z) for y, z in outline], [tuple(range(len(outline)))])
    for pl in art['plates']:
        p = _ccw(pl); n = len(p)
        face.add([(PLATE_H, y, z) for y, z in p], [tuple(range(n))])
        side = Mesh(); side.add([(0.0, y, z) for y, z in p] + [(PLATE_H, y, z) for y, z in p], [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)])
        blk.merge(side, Mp)
    for (y, z, r) in art['knobs']:
        knb.merge(knob(r, max(0.35, min(0.7, 1.3 * r)), ctx.n(14, 9)), Mp @ T(PLATE_H, y, z) @ KN)
    fm = Mesh(); fm.merge(face, Mp)
    o = ctx.part('airframe', 'instrument_panel_face', fm, 'panel_art' if textured else 'panel_face', 30)
    if o is not None: tri(o)
    if textured and o is not None:
        Mi = np.linalg.inv(Mp).T
        MA.set_uv(o, lambda a: np.stack([(W / 2 - (a @ Mi)[:, 1]) / W, (a @ Mi)[:, 2] / Hh], 1))
    # ---- glare shield: a padded hood round the top and both sides of the panel
    o_ = art['outline']; ys = [p[0] for p in o_]; zs = [p[1] for p in o_]
    ymax, zmax = max(ys), max(zs); zc = 14.6; zlow = 1.9
    path = [(ymax, zlow), (ymax, zc - 2.0), (ymax - 0.9, zc), (0.0, zmax), (-ymax + 0.9, zc), (-ymax, zc - 2.0), (-ymax, zlow)]
    import interior
    pts = interior.smooth_path([(0.0, y, z) for y, z in path], 3.0, 6)
    dense = [np.array(pts[0], float)]
    for q in pts[1:]:                                             # a ring every 1.5 in so the hood never twists across a long span
        q = np.array(q, float); k = max(1, int(np.linalg.norm(q - dense[-1]) / 1.5)); p0 = dense[-1]
        dense += [p0 + (q - p0) * (i + 1) / k for i in range(k)]
    pts = dense
    d = (np.linalg.inv(Mp) @ np.array((1.0, 0, 0.0, 0)))[:3]; d /= np.linalg.norm(d)      # toward the crew, drooping slightly
    rings = []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]; t /= np.linalg.norm(t)
        nrm = np.cross(t, (1.0, 0, 0)); nrm /= np.linalg.norm(nrm)
        if nrm.dot(p - np.array((0, 0, 7.0))) < 0: nrm = -nrm                                  # outward from the panel centre
        k = max(0.0, min(1.0, (p[2] - zlow) / (zc - 2.0 - zlow)))                              # 0 at the foot of each side, 1 over the top
        dep = 1.8 + 2.9 * k ** 0.7                                                              # [EST F2-4]
        a = p + nrm * 0.05; b = p + nrm * 1.35
        rings.append([a - d * 0.4, b - d * 2.0, b + d * dep * 0.9, (a + b) / 2 + d * (dep + 0.25), a + d * dep * 0.9])
    m = lib.loft(np.array(rings), cap0=True, cap1=True)
    import cockpit_floor as CK
    blk.merge(CK.outward(m), Mp)


def console_top(ctx, Mc, art, out):
    """Mc: origin at the forward edge of the drawn console top on the centre line, x aft along the slope, y = BL, z up."""
    blk, knb = out; textured = 'console_art' in ctx.mats
    w, l = art['w'], art['l']
    face = Mesh(); face.add([(0, w / 2, 0.03), (0, -w / 2, 0.03), (l, -w / 2, 0.03), (l, w / 2, 0.03)], [(0, 1, 2, 3)])
    fm = Mesh(); fm.merge(face, Mc)
    import cockpit_floor as CK
    o = ctx.part('airframe', 'console_top_face', fm, 'console_art' if textured else 'panel_face', 30)
    if textured and o is not None:
        Mi = np.linalg.inv(Mc).T
        MA.set_uv(o, lambda a: np.stack([(w / 2 - (a @ Mi)[:, 1]) / w, 1 - (a @ Mi)[:, 0] / l], 1))
    for (x, y, r) in art['knobs']:
        if r < 0.25:
            if ctx.lod == 0: blk.merge(lib.revolve([(r, 0), (r, 0.05), (r * 0.7, 0.08), (0, 0.08)], 6), Mc @ T(x, y, 0.03))   # quarter-turn fastener heads
        elif r < 0.62:
            knb.merge(knob(r, max(0.3, min(0.62, 1.25 * r + 0.08)), ctx.n(12, 8)), Mc @ T(x, y, 0.03))


CYCLIC_H = 6.2          # in, grip height [EST: figure 2-14 has no dimensions]


def cyclic_grip(ctx, art, base):
    """The cyclic grip lofted through figure 2-14's side view (fore-aft extent at each height) and front view (width
    at each height). base: aircraft (STA, BL, WL) of the grip's foot. The drawing's left is forward."""
    n = ctx.n(16, 10); ang = np.linspace(0, 2 * np.pi, n, endpoint=False); rings = []
    for (s0, s1), (f0, f1) in zip(art['side'], art['front']):
        pass
    k = len(art['side'])
    for i, ((s0, s1), (f0, f1)) in enumerate(zip(art['side'], art['front'])):
        z = CYCLIC_H * i / (k - 1); cs, rs = (s0 + s1) / 2 * CYCLIC_H, max(0.12, (s1 - s0) / 2 * CYCLIC_H)
        cf, rf = (f0 + f1) / 2 * CYCLIC_H, max(0.12, (f1 - f0) / 2 * CYCLIC_H)
        ce, se = np.cos(ang), np.sin(ang); e = 2.0 / 2.6
        x = cs + rs * np.sign(ce) * np.abs(ce) ** e; y = cf + rf * np.sign(se) * np.abs(se) ** e
        rings.append(np.stack([base[0] + x, base[1] - y, np.full(n, base[2] + z)], 1))       # drawing left (-x) is forward (-STA)
    import cockpit_floor as CK
    return CK.outward(lib.loft(np.array(rings), cap0=True, cap1=True))
