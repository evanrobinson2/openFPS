"""Main rotor head and blades, flight-control hardware above the deck, tail rotor and its gearbox.

Rotor-local frame (inches): origin at the hub centre, z up the shaft, x radial. The fully articulated head with
elastomeric bearings, one damper per blade, pitch horns on the leading side, a swashplate under the hub and a
four-arm bifilar absorber on top follows the manual's top view [F6-1] and general arrangement [F2-1]; sizes of the
individual fittings are read off those drawings where they show and are otherwise inferred [INF].
"""
import math
import numpy as np
import lib, recipe as RC
from lib import Mesh, T, R, S
from airframe import naca

HINGE = 15.0          # [PUB] flap / lag hinge offset, 4.7 percent of the radius
R_CUFF0, R_BLADE0 = 30.0, 44.0
SWEEP_R, SWEEP_DEG = 0.93 * RC.R_MAIN, 20.0    # [PUB] swept tip from 93 percent radius
TWIST = [(0.13, 9.0), (0.20, 8.2), (0.50, 3.0), (0.75, -1.3), (0.865, -3.6), (0.93, -5.6), (0.96, -4.6), (1.0, -2.6)]   # [PUB approx] deg
TC_MAIN = 0.095       # [PUB] SC1095 thickness


def M_hub():
    return T(RC.STA_MAST, 0, RC.WL_HUB) @ R('bl', -RC.MAST_TILT)


def blade_frame(psi_deg):
    """Local (radial, toward leading edge, up) -> rotor frame, for a counter-clockwise rotor seen from above."""
    a = math.radians(psi_deg); M = np.eye(4)
    M[:3, 0] = (math.cos(a), -math.sin(a), 0); M[:3, 1] = (-math.sin(a), -math.cos(a), 0); M[:3, 2] = (0, 0, 1)
    return M


def section(chord, tc, k, c0=0.0, c1=1.0, camber=0.012, grow=1.0):
    """Airfoil loop in (y toward the leading edge, z up); pitch axis at quarter chord."""
    c = c0 + (c1 - c0) * 0.5 * (1 - np.cos(np.linspace(0, np.pi, k)))
    t = 0.5 * tc * chord * naca(c) * grow
    zc = camber * chord * 4 * c * (1 - c) * (1 - c)
    y = (0.25 - c) * chord
    up = np.stack([y, zc + t], 1); lo = np.stack([y, zc - t], 1)
    return np.vstack([up, lo[-2:0:-1]]) if c0 == 0.0 and c1 == 1.0 else np.vstack([up, lo[::-1]])


def blade_mesh(ctx, r0, r1, chord, tc, twist_fn, sweep=True, k=None, c0=0.0, c1=1.0, grow=1.0, nr=None):
    k = k or ctx.n(26, 12); rings = []
    rs = np.unique(np.r_[np.linspace(r0, min(SWEEP_R, r1) if sweep else r1, nr or ctx.n(40, 14)),
                         np.linspace(SWEEP_R, r1, ctx.n(10, 5)) if sweep and r1 > SWEEP_R else []])
    for r in rs:
        lp = section(chord, tc, k, c0, c1, grow=grow)
        th = math.radians(float(twist_fn(r)))
        y = lp[:, 0] * math.cos(th) - lp[:, 1] * math.sin(th); z = lp[:, 0] * math.sin(th) + lp[:, 1] * math.cos(th)
        if sweep and r > SWEEP_R:
            y = y - math.tan(math.radians(SWEEP_DEG)) * (r - SWEEP_R)
        rings.append(np.stack([np.full(len(lp), r), y, z], 1))
    return lib.loft(np.array(rings), cap0=True, cap1=True)


def bolt_ring(n, radius, z, d=0.5, up=True, phase=0.0):
    m = Mesh()
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        m.merge(lib.bolt((radius * math.cos(a), radius * math.sin(a), z), (0, 0, 1 if up else -1), d))
    return m


def main_rotor(ctx):
    Mh = M_hub(); hi = ctx.lod == 0
    ctx.node('main_rotor', 'airframe', pivot=(RC.STA_MAST, 0, RC.WL_HUB), rot=Mh[:3, :3])
    ti, st, sd, el, bk = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()     # titanium, steel, steel_dark, elastomer, black
    n = ctx.n(32, 16)
    # shaft and hub barrel
    st.merge(lib.revolve([(4.6, -24), (4.6, -6), (5.6, -5), (5.6, -4.4)], n))
    ti.merge(lib.revolve([(7.5, -4.6), (9.4, -4.2), (9.8, -3.2), (9.8, 3.2), (9.4, 4.2), (7.2, 4.8), (6.2, 5.2), (0, 5.2)], n))
    if hi:
        st.merge(bolt_ring(12, 7.9, 4.55, 0.55)); st.merge(bolt_ring(12, 7.9, -4.5, 0.55, up=False))
    # bifilar absorber: four-arm plate between the blades, a tungsten weight on a pin pair at each arm end
    arm = lib.rrect(26.0, 6.4, 3.0)
    for q in range(4):
        Mq = R('wl', 45 + 90 * q)
        ti.merge(lib.prism(arm, 5.2, 6.4), Mq @ T(9.0, 0, 0))
        sd.merge(lib.revolve([(3.5, 6.4), (3.9, 6.8), (3.9, 9.6), (3.5, 10.0), (0, 10.0)], ctx.n(20, 10)), Mq @ T(18.2, 0, 0))
        sd.merge(lib.revolve([(3.6, 5.2), (3.6, 3.4), (0, 3.4)], ctx.n(20, 10)), Mq @ T(18.2, 0, 0))
        if hi:
            for dy in (-1.6, 1.6):
                st.merge(lib.bolt((18.2, dy, 10.0), (0, 0, 1), 0.6), Mq)
    # slip ring / de-ice distributor on top
    bk.merge(lib.revolve([(5.2, 6.4), (5.2, 9.0), (4.2, 11.6), (2.6, 12.6), (0, 12.8)], n))
    # swashplate (rotating ring) and scissors
    ti.merge(lib.revolve([(7.0, -15.6), (13.6, -15.6), (14.2, -14.9), (14.2, -13.5), (13.6, -12.8), (7.0, -12.8)], n))
    for q in range(2):
        Mq = R('wl', 45 + 180 * q)
        ti.merge(lib.box((6.5, 0, -9.0), (4.0, 2.2, 2.2)), Mq)
        ti.merge(lib.cyl((7.6, 0, -9.0), (11.2, 0, -12.8), 0.9, 10), Mq)
        ti.merge(lib.cyl((7.6, 0, -9.0), (5.2, 0, -6.0), 1.0, 10), Mq)
    for q in range(4):
        Mb = blade_frame(90 * q)
        # hub arm (yoke) holding the elastomeric bearing
        rings = []
        for r, w, h in ((7.0, 15.0, 8.4), (11.0, 13.6, 8.8), (15.0, 12.8, 9.0), (19.0, 12.4, 9.0), (21.0, 11.4, 8.2)):
            p = lib.rrect(w, h, 2.6, ctx.n(5, 3)); rings.append(np.stack([np.full(len(p), r), p[:, 0], p[:, 1]], 1))
        ti.merge(lib.loft(np.array(rings), cap0=True, cap1=True), Mb)
        # elastomeric bearing stack, spindle, damper lug, cuff
        Mx, _ = lib.frame_to((0, 0, 0), (1, 0, 0))
        for i in range(5):
            el.merge(lib.revolve([(4.6 - 0.25 * i, 0), (4.6 - 0.25 * i, 0.55)], ctx.n(20, 10)), Mb @ T(21.2 + 0.85 * i, 0, 0) @ Mx)
            st.merge(lib.revolve([(4.7 - 0.25 * i, 0), (4.7 - 0.25 * i, 0.22)], ctx.n(20, 10)), Mb @ T(21.78 + 0.85 * i, 0, 0) @ Mx)
        ti.merge(lib.revolve([(3.4, 25.0), (3.4, 30.0), (4.4, 31.0), (4.4, 33.0)], ctx.n(20, 10)), Mb @ Mx)
        rings = []
        for r, w, h, y0 in ((31.0, 9.0, 8.0, 0), (36.0, 12.5, 5.6, -0.6), (41.0, 15.5, 3.4, -1.6), (48.0, 17.0, 2.4, -2.4)):
            p = lib.rrect(w, h, 1.1, ctx.n(4, 2)); rings.append(np.stack([np.full(len(p), r), p[:, 0] + y0, p[:, 1]], 1))
        ti.merge(lib.loft(np.array(rings), cap0=True, cap1=True), Mb)
        for dy in (2.6, -5.4):      # the two blade attachment pins
            st.merge(lib.cyl((42.5, dy, -2.6), (42.5, dy, 2.6), 1.15, ctx.n(14, 8)), Mb)
            if hi:
                st.merge(lib.bolt((42.5, dy, 2.6), (0, 0, 1), 0.9), Mb); st.merge(lib.bolt((42.5, dy, -2.6), (0, 0, -1), 0.9), Mb)
        # pitch horn on the leading side and the pitch control rod down to the swashplate
        ti.merge(lib.box((27.5, 5.6, -0.4), (5.0, 8.0, 2.4)), Mb)
        ti.merge(lib.cyl((27.5, 9.6, -1.6), (27.5, 9.6, 0.8), 1.5, 12), Mb)
        horn = np.array((27.5, 9.6, -1.0)); sw = np.array((12.6 * math.cos(math.radians(38)), 12.6 * math.sin(math.radians(38)), -12.6))
        st.merge(lib.cyl(horn, sw, 0.62, 10), Mb)
        sd.merge(lib.cyl(horn + (sw - horn) * 0.12, horn + (sw - horn) * 0.88, 0.95, 10), Mb)
        ti.merge(lib.cyl(sw + (0, 0, -1.2), sw + (0, 0, 1.2), 1.3, 10), Mb)
        # lead-lag damper on the trailing side: body on the hub arm, rod to the spindle
        d0 = np.array((11.5, -8.4, 0.0)); d1 = np.array((33.0, -6.4, 0.0))
        ti.merge(lib.box((11.5, -7.2, 0.0), (3.6, 3.0, 3.0)), Mb)
        sd.merge(lib.cyl(d0, d0 + (d1 - d0) * 0.62, 1.9, ctx.n(16, 8)), Mb)
        st.merge(lib.cyl(d0 + (d1 - d0) * 0.6, d1, 0.75, 10), Mb)
        ti.merge(lib.box((33.0, -5.4, 0.0), (2.6, 3.2, 2.4)), Mb)
        if hi:
            st.merge(lib.bolt(d0 + (0, 0, 1.5), (0, 0, 1), 0.5), Mb); st.merge(lib.bolt(d1 + (0, 0, 1.2), (0, 0, 1), 0.5), Mb)
            st.merge(lib.bolt(horn + (0, 0, 1.8), (0, 0, 1), 0.5), Mb)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    st.merge(lib.bolt((15.0 + 3.6 * sx, 4.6 * sy, 4.5), (0, 0, 1), 0.45), Mb)
    for name, m, mat in (('hub', ti, 'titanium'), ('hub_steel', st, 'steel'), ('hub_dark', sd, 'steel_dark'),
                         ('hub_bearings', el, 'elastomer'), ('hub_distributor', bk, 'paint_black')):
        mm = Mesh(); mm.merge(m, Mh); ctx.part('main_rotor', name, mm, mat, 35)
    # ---- blades: one node each, pivot on the flap hinge, with a 'droop' morph for the parked shape
    tw = lib.lin([t[0] * RC.R_MAIN for t in TWIST], [t[1] for t in TWIST])
    for q in range(4):
        Mb = blade_frame(90 * q); Mw = Mh @ Mb
        nd = ctx.node(f'main_blade_{q + 1}', 'main_rotor', pivot=tuple(lib.xf(Mw, [(HINGE, 0, 0)])[0]), rot=Mw[:3, :3])
        ctx.nodes[nd]['morph'] = ('droop', lambda v: _droop(v))
        b = Mesh(); b.merge(blade_mesh(ctx, R_BLADE0, RC.R_MAIN, RC.CHORD_MAIN, TC_MAIN, tw), Mw)
        ctx.part(nd, 'blade', b, 'paint_black', 28)
        e = Mesh(); e.merge(blade_mesh(ctx, R_BLADE0 + 6, RC.R_MAIN - 0.4, RC.CHORD_MAIN, TC_MAIN, tw, c1=0.13, grow=1.035, k=ctx.n(9, 5)), Mw @ T(0, 0.05, 0))
        ctx.part(nd, 'blade_abrasion_strip', e, 'titanium', 35)
        tab = Mesh()
        for ra, rb in ((0.73, 0.795), (0.80, 0.865)):
            rm = 0.5 * (ra + rb) * RC.R_MAIN; th = math.radians(float(tw(rm)))
            tab.merge(lib.box((rm, -0.75 * RC.CHORD_MAIN - 0.5, 0), ((rb - ra) * RC.R_MAIN, 1.6, 0.07)), Mw @ R('sta', math.degrees(th)))
        ctx.part(nd, 'blade_trim_tab', tab, 'aluminium', 30)


def _droop(v_local_m):
    """Parked blade: elastic droop of 37 in at the tip relative to the hinge [F2-3: tip 7 ft 7 in above ground]."""
    r = np.clip(v_local_m[:, 0] / ((RC.R_MAIN - HINGE) * lib.IN), 0, 1)
    d = np.zeros_like(v_local_m); d[:, 2] = -37.0 * lib.IN * r ** 1.9
    return d


def tail_rotor(ctx):
    hi = ctx.lod == 0
    cant = math.radians(RC.TR_CANT)
    axis = np.array((0.0, -math.cos(cant), math.sin(cant)))        # points right and up
    c = np.array((RC.STA_TR, RC.BL_TR, RC.WL_TR))
    # node frame: local z = axis, local x = aft
    x = np.array((1.0, 0, 0)); y = np.cross(axis, x); y /= np.linalg.norm(y)
    Mt = np.eye(4); Mt[:3, 0], Mt[:3, 1], Mt[:3, 2], Mt[:3, 3] = x, y, axis, c
    ctx.node('tail_rotor', 'airframe', pivot=tuple(c), rot=Mt[:3, :3])
    ti, st, bl, sd = Mesh(), Mesh(), Mesh(), Mesh()
    n = ctx.n(24, 12)
    # gearbox output housing and shaft from the pylon centre line to the hub (airframe side, does not turn)
    gb = Mesh(); gb.merge(lib.revolve([(5.6, -12.5), (5.6, -9.0), (4.2, -7.5), (3.4, -3.0), (3.4, -1.6)], n), Mt)
    ctx.part('airframe', 'tail_gearbox_output', gb, 'paint_od', 40)
    st.merge(lib.revolve([(1.9, -1.8), (1.9, 6.4), (1.2, 6.8), (0, 6.8)], n))
    ti.merge(lib.revolve([(6.2, -1.4), (6.6, -1.0), (6.6, 1.0), (6.2, 1.4), (0, 1.4)], n))
    ti.merge(lib.revolve([(6.2, -1.4), (0, -1.4)], n))
    if hi:
        st.merge(bolt_ring(8, 5.0, 1.4, 0.5, phase=math.pi / 8)); st.merge(bolt_ring(8, 5.0, -1.4, 0.5, up=False, phase=math.pi / 8))
    # pitch beam (spider) outboard of the hub with four pitch links
    ti.merge(lib.revolve([(2.6, 5.2), (2.6, 6.6)], n))
    tw = lib.lin([14, 66], [7.0, -9.0])             # [PUB] about -18 deg equivalent linear twist
    for q in range(4):
        Mq = R('wl', 90 * q)
        Mb = np.eye(4); Mb[:3, 0] = Mq[:3, 0]; Mb[:3, 1] = Mq[:3, 1]; Mb[:3, 2] = (0, 0, 1)
        k = ctx.n(20, 10); rings = []
        for r in np.r_[np.linspace(9, 15, 4), np.linspace(17, 65.6, ctx.n(16, 7))]:
            f = np.clip((r - 9) / 8.0, 0, 1)
            chord = 5.2 + (RC.CHORD_TAIL - 5.2) * f; tc = 0.30 - 0.20 * f
            lp = section(chord, tc, k, camber=0.0); th = math.radians(float(tw(max(r, 14))))
            yy = lp[:, 0] * math.cos(th) - lp[:, 1] * math.sin(th); zz = lp[:, 0] * math.sin(th) + lp[:, 1] * math.cos(th)
            rings.append(np.stack([np.full(len(lp), r), yy, zz], 1))
        bl.merge(lib.loft(np.array(rings), cap0=True, cap1=True), Mb)
        e = blade_mesh(ctx, 18, 65.4, RC.CHORD_TAIL, 0.10, tw, sweep=False, c1=0.14, grow=1.05, k=ctx.n(8, 5), nr=ctx.n(12, 6))
        tim = Mesh(); tim.merge(e, Mb @ T(0, 0.04, 0)); ti.merge(tim)
        ti.merge(lib.box((4.4, 0, 6.0), (4.6, 1.4, 0.9)), Mb)
        st.merge(lib.cyl((6.4, 0, 6.0), (11.5, 2.6, 0.9), 0.38, 8), Mb)
        ti.merge(lib.box((11.5, 2.4, 0.6), (1.6, 2.2, 1.0)), Mb)
        if hi:
            st.merge(lib.bolt((6.4, 0, 6.45), (0, 0, 1), 0.38), Mb)
    for name, m, mat in (('tail_hub', ti, 'titanium'), ('tail_hub_steel', st, 'steel'), ('tail_blades', bl, 'paint_black')):
        mm = Mesh(); mm.merge(m, Mt); ctx.part('tail_rotor', name, mm, mat, 32)


def controls(ctx):
    """Stationary swashplate, three primary servos and the mast base, on the airframe."""
    Mh = M_hub(); n = ctx.n(28, 14)
    ti, st, ch = Mesh(), Mesh(), Mesh()
    ti.merge(lib.revolve([(6.6, -18.4), (12.6, -18.4), (13.0, -17.8), (13.0, -16.4), (12.6, -15.9), (6.6, -15.9)], n))
    ti.merge(lib.revolve([(6.8, -26.0), (9.5, -25.0), (7.4, -21.5), (6.2, -18.4)], n))      # mast base / upper bearing housing
    for a in (0, 120, 240):
        Mq = R('wl', a + 60)
        ti.merge(lib.box((12.6, 0, -17.2), (3.0, 2.4, 2.0)), Mq)
        ch.merge(lib.cyl((13.4, 0, -17.6), (13.6, 0, -22.0), 0.65, 10), Mq)
        ti.merge(lib.cyl((13.6, 0, -22.0), (13.8, 0, -29.0), 1.7, ctx.n(16, 8)), Mq)
    for name, m, mat in (('swashplate_stationary', ti, 'titanium'), ('servo_rods', ch, 'chrome')):
        mm = Mesh(); mm.merge(m, Mh); ctx.part('airframe', name, mm, mat, 35)


def build(ctx):
    main_rotor(ctx); controls(ctx); tail_rotor(ctx)
    ctx.clip('main_rotor', 'rotor_spin', [(1, None, ('z', 0.0)), (25, None, ('z', 360.0))])
    ctx.clip('tail_rotor', 'rotor_spin', [(1, None, ('z', 0.0)), (25, None, ('z', 1440.0))])
