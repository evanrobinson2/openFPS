"""Decks and bulkheads cut to the inside of the hull."""
import math
import numpy as np
from mathutils import geometry, Vector
import spec
from kit import MB

BIG = 99.0

def deck_slab(mb, z, t, s0, s1, m, holes=(), step=0.25, m_under=None, m_edge=None, clear=0.0, max_half=None):
    """Flat deck, top surface at z, thickness t, from s0 to s1, cut to the lining and around holes (s0, s1, y0, y1).
    clear pulls the edge in from the lining; max_half caps the half-width."""
    ss = set([s0, s1])
    for h in holes:
        ss.update(v for v in h[:2] if s0 < v < s1)
    k = math.ceil(s0 / step) * step
    while k < s1 - 1e-6:
        if k > s0 + 1e-6: ss.add(round(k, 4))
        k += step
    ss = sorted(ss)
    ys = sorted(set(v for h in holes for v in h[2:4]))
    E = [-BIG] + ys + [BIG]
    def hw(s):
        w = min(spec.lining_half_width(s, z), spec.lining_half_width(s, z - t)) - clear
        return min(w, max_half) if max_half else w
    W = [hw(s) for s in ss]
    def exists(k, l):
        if k < 0 or k >= len(ss) - 1 or l < 0 or l >= len(E) - 1: return False
        sm = 0.5 * (ss[k] + ss[k + 1]); ym = 0.5 * (max(E[l], -BIG / 2) + min(E[l + 1], BIG / 2))
        if l == 0: ym = E[1] - 0.01 if len(E) > 2 else 0.0
        if l == len(E) - 2 and len(E) > 2: ym = E[-2] + 0.01
        for h in holes:
            if h[0] <= sm <= h[1] and h[2] <= ym <= h[3]: return False
        wa, wb = W[k], W[k + 1]
        a0, a1 = max(E[l], -wa), min(E[l + 1], wa); b0, b1 = max(E[l], -wb), min(E[l + 1], wb)
        return (a1 - a0 > 0.02) or (b1 - b0 > 0.02)
    for k in range(len(ss) - 1):
        for l in range(len(E) - 1):
            if not exists(k, l): continue
            wa, wb = W[k], W[k + 1]
            a0, a1 = max(E[l], -wa), min(E[l + 1], wa); b0, b1 = max(E[l], -wb), min(E[l + 1], wb)
            a1 = max(a1, a0); b1 = max(b1, b0)
            sa, sb = ss[k], ss[k + 1]
            top = mb.vs([(sa, a0, z), (sb, b0, z), (sb, b1, z), (sa, a1, z)])
            bot = mb.vs([(sa, a0, z - t), (sb, b0, z - t), (sb, b1, z - t), (sa, a1, z - t)])
            mb.f(top, m); mb.f(bot[::-1], m_under or m)
            me = m_edge or m
            if not exists(k - 1, l): mb.f((top[0], top[3], bot[3], bot[0]), me)
            if not exists(k + 1, l): mb.f((top[2], top[1], bot[1], bot[2]), me)
            if not exists(k, l - 1): mb.f((top[1], top[0], bot[0], bot[1]), me)
            if not exists(k, l + 1): mb.f((top[3], top[2], bot[2], bot[3]), me)

def section_outline(s, z0=None, z1=None, clear=0.0, max_half=None):
    """Closed outline (list of (y, z)) of the inside of the hull at station s, optionally between two heights."""
    y, z = spec.lining_section(s, spec.OFF_LINING - clear)
    lo = z[-1] if z0 is None else max(z0, z[-1]); hi = z[0] if z1 is None else min(z1, z[0])
    pts = []
    zz = np.linspace(hi, lo, 41)
    yy = np.interp(-zz, -z, y)
    if max_half: yy = np.minimum(yy, max_half)
    st = [(float(a), float(b)) for a, b in zip(yy, zz)]
    if st[0][0] < 1e-4: st[0] = (0.0, st[0][1])
    out = st + [(-a, b) for a, b in reversed(st) if a > 1e-4]
    return out

def bulkhead(mb, s, t, m, doors=(), z0=None, z1=None, m_edge=None, clear=0.0, max_half=None):
    """Bulkhead at station s (forward face at s, thickness t aft), with rectangular openings doors (y0, y1, z0, z1)."""
    outer = section_outline(s, z0, z1, clear, max_half)
    loops = [[Vector((y, z, 0.0)) for y, z in outer]]
    for d in doors:
        loops.append([Vector((d[0], d[2], 0)), Vector((d[1], d[2], 0)), Vector((d[1], d[3], 0)), Vector((d[0], d[3], 0))])
    flat = [p for lp in loops for p in lp]
    tris = geometry.tessellate_polygon(loops)
    a = [mb.v((s, p.x, p.y)) for p in flat]; b = [mb.v((s + t, p.x, p.y)) for p in flat]
    for tri in tris:
        p0, p1, p2 = flat[tri[0]], flat[tri[1]], flat[tri[2]]
        # forward face must look toward -s: in (y, z) that is clockwise seen from the front... decide by sign
        cr = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x)
        # normal of (s, y, z) triangle with y,z counter-clockwise is +s
        q = tri if cr > 0 else tri[::-1]
        mb.f([b[i] for i in q], m)
        mb.f([a[i] for i in q[::-1]], m)
    o = 0
    for li, lp in enumerate(loops):
        n = len(lp)
        area = sum(lp[i].x * lp[(i + 1) % n].y - lp[(i + 1) % n].x * lp[i].y for i in range(n))
        ccw = area > 0
        for i in range(n):
            i2 = (i + 1) % n
            q = (a[o + i], a[o + i2], b[o + i2], b[o + i])
            # outer loop ccw -> outward rim; holes need the opposite of the outer rule
            good = ccw if li == 0 else (not ccw)
            mb.f(q if good else q[::-1], m_edge or m)
        o += n
