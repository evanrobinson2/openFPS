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


DOME_H = 0.45           # [INF] the dome light unit stands proud of the console; figure 2-7 is a plan and gives no height
Q_DZ = 1.3              # [EST F2-13] quadrant cover: a drum whose axis lies this far inside the console face
Q_RK, Q_RF = 4.8, 4.5   # [EST F2-13] power lever and fuel selector knob distance from the drum axis


def _clusters(knobs, tol=0.12):
    """Concentric circles drawn for one switch -> one entry (centre, largest radius)."""
    out = []
    for x, y, r in sorted(knobs, key=lambda k: -k[2]):
        if all((x - a) ** 2 + (y - b) ** 2 > tol ** 2 for a, b, _ in out): out.append((x, y, r))
    return out


def upper_console(ctx, Mu, art, out):
    """Upper console from figure 2-7 (plan seen from below) with the engine control quadrant of figure 2-13.
    Mu: origin on the centre line at the console's aft edge, x forward along its face, y = BL, z out of the face (down)."""
    import cockpit_floor as CK
    blk, knb, st = out; textured = 'upper_art' in ctx.mats
    w, l = art['w'], art['l']; outline = _ccw(art['outline']); n = len(outline)
    blk.merge(lib.prism(outline, -2.4, -0.01), Mu)
    face = Mesh(); face.add([(x, y, 0.03) for x, y in outline], [tuple(range(n))])
    a0, a1, b0, b1 = art['dome']; dq = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
    face.add([(x, y, DOME_H) for x, y in dq], [(0, 1, 2, 3)])
    side = Mesh(); side.add([(x, y, 0.03) for x, y in dq] + [(x, y, DOME_H) for x, y in dq], [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)])
    blk.merge(side, Mu)
    fm = Mesh(); fm.merge(face, Mu)
    o = ctx.part('airframe', 'upper_console_face', fm, 'upper_art' if textured else 'panel_face', 30)
    if o is not None: tri(o)
    if textured and o is not None:
        Mi = np.linalg.inv(Mu).T
        MA.set_uv(o, lambda a: np.stack([(w / 2 - (a @ Mi)[:, 1]) / w, 1 - (a @ Mi)[:, 0] / l], 1))
    for (x, y, r) in _clusters(art['knobs']):
        if r < 0.18:
            if ctx.lod == 0: blk.merge(lib.revolve([(r, 0), (r, 0.05), (r * 0.7, 0.08), (0, 0.08)], 6), Mu @ T(x, y, 0.03))
        elif r < 0.25:                                            # toggle switch: nut and bat lever, drawn end on
            st.merge(lib.revolve([(r, 0), (r, 0.07), (r * 0.5, 0.1), (r * 0.5, 0.18), (0, 0.18)], 6), Mu @ T(x, y, 0.03))
            st.merge(lib.revolve([(0.06, 0.1), (0.1, 0.66), (0.085, 0.74), (0, 0.76)], ctx.n(8, 6)), Mu @ T(x, y, 0.03))
        else:                                                     # breaker buttons and rotary knobs
            knb.merge(knob(r, max(0.3, min(0.62, 1.25 * r + 0.08)), ctx.n(12, 8)), Mu @ T(x, y, 0.03))
    # ---- engine control quadrant: positions from the plan (figure 2-7), shapes from figure 2-13
    q = art['quad']; x0, x1, y0, y1 = q['drum']; xc = (x0 + x1) / 2; Rd = math.hypot((x1 - x0) / 2, Q_DZ)
    ph = math.acos(Q_DZ / Rd) + 0.06; k = ctx.n(28, 14)
    arc = [(xc + Rd * math.sin(t), -Q_DZ + Rd * math.cos(t)) for t in np.linspace(-ph, ph, k)]
    v = [(x, y0, z) for x, z in arc] + [(x, y1, z) for x, z in arc]
    m = Mesh(); m.add(v, [tuple(range(k)), tuple(range(k, 2 * k))[::-1]] + [(i, i + 1, k + i + 1, k + i) for i in range(k - 1)])
    blk.merge(CK.outward(m), Mu)

    def pos(xk, y, rk, r):
        s = (xc - xk) / rk; c = math.sqrt(1 - s * s)
        return np.array((xc - r * s, y, -Q_DZ + r * c)), s, c

    for (xk, yk) in q['power']:                                   # power control levers: flat lever, thick disc knob
        p0, s, c = pos(xk, yk, Q_RK, Rd - 0.1); pk = pos(xk, yk, Q_RK, Q_RK)[0]
        M = np.eye(4); M[:3, 0] = (c, 0, s); M[:3, 2] = (-s, 0, c); M[:3, 3] = p0; L = Q_RK - Rd
        st.merge(lib.box((0, 0, L / 2), (0.7, 0.14, L)), Mu @ M)
        t, r = q['power_size'][0], q['power_size'][1] / 2
        Mk, _ = lib.frame_to(pk - (0, t / 2, 0), pk + (0, t / 2, 0))
        knb.merge(lib.revolve([(r * 0.8, 0), (r, t * 0.16), (r, t * 0.84), (r * 0.8, t)], ctx.n(24, 14)), Mu @ Mk)
    for (xk, yk), ya in zip(q['fuel'], q['fuel_arm']):            # fuel system selector levers: arm cranked outboard to a round knob
        a = pos(xk, ya, Q_RF, Rd - 0.1)[0]; b = pos(xk, ya, Q_RF, Q_RF - 0.9)[0]; pk = pos(xk, yk, Q_RF, Q_RF)[0]
        st.merge(lib.tube([a, b, pk], 0.14, 8), Mu)
        u = (pk - b) / np.linalg.norm(pk - b); r = q['fuel_r']; Mk, _ = lib.frame_to(pk - u * 0.4, pk + u * 0.6)
        knb.merge(lib.revolve([(r * 0.7, 0), (r, 0.14), (r, 0.72), (r * 0.72, 0.94), (0, 1.0)], ctx.n(18, 10)), Mu @ Mk)
    (sx0, sy), (sx1, _) = q['tee_stem']; L, wd = q['tee_size']; wd = min(wd, 0.58)
    for (tx, ty) in q['tee']:                                     # engine emergency off T-handles
        sg = 1 if ty > 0 else -1; z0 = -Q_DZ + math.sqrt(max(0.01, Rd * Rd - (sx0 - xc) ** 2))
        st.merge(lib.tube([(sx0, sg * sy, z0 - 0.1), (sx1, sg * sy, z0 + 0.5), (tx, ty, z0 + 0.9)], 0.15, 8), Mu)
        d = np.array((q['tee_dir'][0], -sg * q['tee_dir'][1], 0.0)); d /= np.linalg.norm(d)
        M = np.eye(4); M[:3, 0] = d; M[:3, 1] = (-d[1], d[0], 0); M[:3, 3] = (tx, ty, z0 + 0.9)
        knb.merge(lib.box((0, 0, 0), (L, wd, wd)), Mu @ M)


COLLECTIVE_H = 6.9      # in, grip length [EST: figure 2-14 has no dimensions; sets the grip tube at 1.5 in]


def collective_grip(ctx, art, M):
    """Collective grip from figure 2-14 sheet 1: the outline of its one view, with the drawing itself on the switch face.
    The figure shows no side view, so the head is given the thickness of the grip tube [EST].
    M: local x = the drawing's right, y = out of the switch face, z = up the grip. Returns (body, face) meshes."""
    import cockpit_floor as CK
    H = COLLECTIVE_H; prof = art['profile']; k = len(prof); t = (prof[0][1] - prof[0][0]) * H; n = ctx.n(6, 4); rings = []; strip = []
    for i, (lo, hi) in enumerate(prof):
        z = H * i / (k - 1); a, b = lo * H, hi * H; w = b - a; rc = min(t / 2, w / 2) if w < t * 1.25 else max(0.3, t / 2 - (w - t * 1.25) * 0.6)
        rc = min(rc, w / 2 - 1e-3, t / 2 - 1e-3); ring = []
        for cx, cy, a0 in ((b - rc, t / 2 - rc, 0), (a + rc, t / 2 - rc, 90), (a + rc, -t / 2 + rc, 180), (b - rc, -t / 2 + rc, 270)):
            for j in range(n + 1):
                an = math.radians(a0 + 90.0 * j / n); ring.append((cx + rc * math.cos(an), cy + rc * math.sin(an), z))
        rings.append(ring); strip.append((a + rc, b - rc, z))
    body = Mesh(); body.merge(lib.loft(np.array(rings), cap0=True, cap1=True), M); body = CK.outward(body)
    v = []; f = []; flip = np.linalg.det(M[:3, :3]) < 0
    for i, (a, b, z) in enumerate(strip):
        v += [(a, t / 2 + 0.012, z), (b, t / 2 + 0.012, z)]
        if i and min(b - a, strip[i - 1][1] - strip[i - 1][0]) > 0.25:
            q = (2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1); f.append(q if flip else q[::-1])
    face = Mesh(); fl = Mesh(); fl.add(v, f); face.merge(fl, M)
    kn = Mesh(); seen = []
    for (x, z, r) in sorted(art['knobs'], key=lambda q: -q[2]):
        if r > 0.045 and all((x - a) ** 2 + (z - b) ** 2 > 0.03 ** 2 for a, b in seen):
            seen.append((x, z)); Mk = np.array([[1, 0, 0, x * H], [0, 0, 1, t / 2], [0, -1, 0, z * H], [0, 0, 0, 1.0]])
            kn.merge(knob(r * H * 0.62, 0.3, ctx.n(12, 8)), M @ Mk)
    return body, face, CK.outward(kn) if kn.v else kn


def collective_uv(o, art, M):
    H = COLLECTIVE_H; Mi = np.linalg.inv(M).T; x0, x1 = art['x0'], art['x1']
    MA.set_uv(o, lambda a: np.stack([((a @ Mi)[:, 0] / H - x0) / (x1 - x0), (a @ Mi)[:, 2] / H], 1))
