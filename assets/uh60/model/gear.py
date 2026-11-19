"""Landing gear: two main gears on drag beams with air-oil shock struts, and the tail gear on its yoke.
Wheel positions are from the manual (wheel base 29 ft, tread 8 ft 10.6 in [F2-2]; tail wheel STA 644.6 [F6-1]).
Tyre sizes are the type's published 26 x 10.0-11 mains and 15 x 6.0-6 tail wheel [PUB]; strut geometry is read off the
front view of [F2-2] and the side view of [F6-1] and otherwise inferred [INF]."""
import math
import numpy as np
import lib, recipe as RC
from lib import Mesh, T, R, S


def wheel(ctx, c, sg, r_t, w, r_rim, hi):
    """Returns (tyre, rim, steel) meshes; axle along BL, outboard = sg."""
    p0 = np.array(c) - np.array((0, sg * w / 2, 0)); p1 = np.array(c) + np.array((0, sg * w / 2, 0))
    M, L = lib.frame_to(p0, p1); n = ctx.n(40, 20); h = w / 2
    prof = [(r_rim, 0.12 * w), (r_rim + 0.35 * (r_t - r_rim), 0.02 * w), (r_t - 0.9, 0.03 * w), (r_t - 0.25, 0.2 * w), (r_t, 0.5 * w),
            (r_t - 0.25, 0.8 * w), (r_t - 0.9, 0.97 * w), (r_rim + 0.35 * (r_t - r_rim), 0.98 * w), (r_rim, 0.88 * w)]
    tyre = lib.revolve(prof, n, M, cap0=False, cap1=False)
    rim = lib.revolve([(r_rim + 0.25, 0.88 * w), (r_rim + 0.25, 0.80 * w), (r_rim - 0.8, 0.74 * w), (0.45 * r_rim, 0.66 * w), (0.36 * r_rim, 0.86 * w), (0, 0.86 * w)], n, M, cap0=False, cap1=False)
    rim.merge(lib.revolve([(0, 0.2 * w), (0.5 * r_rim, 0.2 * w), (r_rim - 0.8, 0.28 * w), (r_rim + 0.25, 0.2 * w), (r_rim + 0.25, 0.12 * w)], n, M, cap0=False, cap1=False))
    rim.merge(lib.revolve([(r_rim + 0.25, 0.12 * w), (r_rim + 0.25, 0.88 * w)], n, M, cap0=False, cap1=False))
    st = Mesh()
    if hi:
        nb = 8
        for i in range(nb):
            a = 2 * math.pi * i / nb
            st.merge(lib.bolt((0.62 * r_rim * math.cos(a), 0.62 * r_rim * math.sin(a), 0.69 * w), (0, 0, 1), 0.5), M)
        st.merge(lib.revolve([(1.5, 0.86 * w), (1.5, 0.95 * w), (0.9, 1.0 * w), (0, 1.0 * w)], 12, M))
    return tyre, rim, st


def strut_loft(p0, p1, w0, h0, w1, h1, r=0.8, up=(0, 0, 1)):
    M, L = lib.frame_to(p0, p1); rings = []
    for t, w, h in ((0, w0, h0), (1, w1, h1)):
        p = lib.rrect(w, h, r, 3); rings.append(np.stack([p[:, 0], p[:, 1], np.full(len(p), t * L)], 1))
    m = Mesh(); m.merge(lib.loft(np.array(rings), cap0=True, cap1=True), M); return m


def build(ctx):
    hi = ctx.lod == 0
    od, rub, al, st, ch, sd = Mesh(), Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    for sg in (1, -1):
        c = (RC.STA_MAIN_GEAR, sg * RC.BL_MAIN_GEAR, RC.WL_AXLE)
        ty, rim, bolts = wheel(ctx, c, sg, 12.8, 10.0, 5.6, hi)
        rub.merge(ty); od.merge(rim); st.merge(bolts)
        ax_in = np.array((RC.STA_MAIN_GEAR, sg * 43.5, RC.WL_AXLE))
        st.merge(lib.cyl(ax_in, c, 1.7, ctx.n(16, 10)))
        # brake housing inboard of the wheel
        sd.merge(lib.cyl((c[0], sg * (RC.BL_MAIN_GEAR - 5.6), c[2]), (c[0], sg * (RC.BL_MAIN_GEAR - 3.4), c[2]), 5.0, ctx.n(24, 12)))
        # drag beam: pivots on the fuselage ahead of the wheel, carries the axle
        piv = np.array((259.0, sg * 41.0, 205.5))
        od.merge(strut_loft(piv, ax_in + np.array((0, sg * 1.5, 0.3)), 5.2, 7.0, 4.2, 5.0, 1.2))
        od.merge(lib.cyl(piv - np.array((0, sg * 3.5, 0)), piv + np.array((0, sg * 3.5, 0)), 2.6, ctx.n(16, 8)))
        od.merge(lib.box((ax_in[0], sg * 45.5, ax_in[2]), (6.5, 5.0, 6.0)))
        # shock strut: cylinder fixed to the fuselage side, chromed piston down to the axle fitting
        top = np.array((292.5, sg * 44.6, 229.0)); low = np.array((RC.STA_MAIN_GEAR - 0.3, sg * 47.6, RC.WL_AXLE + 3.2))
        mid = top + (low - top) * 0.62
        od.merge(lib.cyl(top, mid, 2.5, ctx.n(18, 10))); ch.merge(lib.cyl(mid, low, 1.75, ctx.n(16, 10)))
        od.merge(lib.cyl(mid - (mid - top) * 0.05, mid + (low - mid) * 0.04, 2.9, ctx.n(18, 10)))
        od.merge(lib.box(top + np.array((0, sg * -0.6, 1.0)), (6.0, 3.6, 7.0)))
        od.merge(lib.box(low, (4.6, 3.2, 4.6)))
        # brake line down the strut
        rub.merge(lib.tube([top + np.array((2.6, 0, -2)), mid + np.array((3.1, 0, 0)), low + np.array((2.6, 0, 3)), (c[0] + 2, sg * (RC.BL_MAIN_GEAR - 5.2), c[2] + 3)], 0.22, 6))
        if hi:
            for dz in (-2.0, 2.0):
                st.merge(lib.bolt(top + np.array((2.0, sg * 1.3, 1.0 + dz)), (0, sg, 0), 0.5))
                st.merge(lib.bolt(top + np.array((-2.0, sg * 1.3, 1.0 + dz)), (0, sg, 0), 0.5))
            st.merge(lib.bolt(piv + np.array((0, sg * 3.5, 0)), (0, sg, 0), 1.1))
            st.merge(lib.bolt(low + np.array((0, sg * 1.6, 0)), (0, sg, 0), 0.8))
    # ---- tail gear
    c = (RC.STA_TAIL_GEAR, 0.0, 191.3)
    ty, rim, bolts = wheel(ctx, c, 1, 7.5, 6.0, 3.1, False)
    rub.merge(ty); od.merge(rim)
    piv = np.array((611.0, 0, 211.5))
    for sg in (1, -1):
        od.merge(strut_loft(piv + np.array((0, sg * 4.3, 0)), np.array(c) + np.array((0, sg * 4.3, 0)), 1.3, 4.6, 1.3, 3.4, 0.5))
        if hi:
            st.merge(lib.bolt(np.array(c) + np.array((0, sg * 4.95, 0)), (0, sg, 0), 0.9))
            st.merge(lib.bolt(piv + np.array((0, sg * 4.95, 0)), (0, sg, 0), 0.9))
    st.merge(lib.cyl((c[0], -4.6, c[2]), (c[0], 4.6, c[2]), 0.9, 12))
    od.merge(lib.cyl(piv - np.array((0, 5.4, 0)), piv + np.array((0, 5.4, 0)), 1.9, ctx.n(16, 8)))
    od.merge(lib.box((628.0, 0, 201.6), (5.0, 9.6, 2.6), ) )
    top = np.array((640.5, 0, 214.5)); low = np.array((629.5, 0, 202.4)); mid = top + (low - top) * 0.58
    od.merge(lib.cyl(top, mid, 2.0, ctx.n(16, 8))); ch.merge(lib.cyl(mid, low, 1.35, ctx.n(14, 8)))
    od.merge(lib.box(piv + np.array((0, 0, 1.5)), (9.0, 12.5, 3.0)))
    for name, m, mat in (('gear_structure', od, 'paint_od'), ('tyres', rub, 'rubber'), ('gear_steel', st, 'steel'),
                         ('oleo_pistons', ch, 'chrome'), ('brakes', sd, 'steel_dark')):
        ctx.part('airframe', name, m, mat, 35)
