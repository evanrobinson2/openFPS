"""Cabin and cockpit: floors, liners, bulkheads, 14 cabin seats, two armoured crew seats, instrument panel, consoles,
flight controls. Compartment sizes are from the manual (cabin STA 247 to 398, floor WL 206.75, ceiling WL 261 with the
drip pan 2 in lower, cockpit floor WL 215 [F6-1, F6-9]; instrument panel tilted back 30 deg [TM 2.10.1]). Seat
arrangement follows figure 2-10; each fitting's own size is inferred from what it has to hold [INF].
"""
import math
import numpy as np
import lib, recipe as RC, floor as FL, cockpit_floor as CK, panel as PN
from lib import Mesh, T, R, S

INSET = RC.SHELL_T + 0.05
FLOOR, CEIL, CFLOOR = RC.WL_CABIN_FLOOR, RC.WL_CABIN_CEIL, RC.WL_COCKPIT_FLOOR


def wall_bl(s, wl, inset=INSET):
    return float(RC.body_surface_bl(s, wl)) - inset


def slab(stations, wl_top, thick, inset=INSET, w_fn=None):
    """Horizontal slab between the walls, following the wall line at wl_top."""
    rings = []
    for s in stations:
        w = w_fn(s) if w_fn else wall_bl(s, wl_top, inset)
        rings.append([(s, w, wl_top), (s, -w, wl_top), (s, -w, wl_top - thick), (s, w, wl_top - thick)])
    return lib.loft(np.array(rings, float), cap0=True, cap1=True)


def wall_panel(s0, s1, wl0, wl1, sg, inset0=INSET - 0.1, thick=0.9, ns=8, nw=8):
    rings = []
    for s in np.linspace(s0, s1, ns):
        wls = np.linspace(wl0, wl1, nw)
        a = [(s, sg * wall_bl(s, w, inset0), w) for w in wls]
        b = [(s, sg * wall_bl(s, w, inset0 + thick), w) for w in wls[::-1]]
        rings.append(a + b)
    return lib.loft(np.array(rings, float), cap0=True, cap1=True)


def bulkhead(s, thick, wl0, wl1, inset=INSET - 0.3):
    h = RC.body_half(s, 300); h = h[(h[:, 1] >= wl0 - 3) & (h[:, 1] <= wl1 + 3)]
    left = [(max(x - inset, 0.5), min(max(z, wl0), wl1)) for x, z in h]
    poly = left + [(-x, z) for x, z in left[::-1]]
    return lib.prism(np.array(poly), s, s + thick, lib.plane_basis('front'))


def seat_frame(facing):
    """Local seat axes (x forward as the occupant faces, y to the occupant's left, z up) -> aircraft axes."""
    M = np.eye(4)
    if facing == 'fwd': M[:3, 0], M[:3, 1] = (-1, 0, 0), (0, 1, 0)
    elif facing == 'aft': M[:3, 0], M[:3, 1] = (1, 0, 0), (0, -1, 0)
    elif facing == 'left': M[:3, 0], M[:3, 1] = (0, 1, 0), (1, 0, 0)
    else: M[:3, 0], M[:3, 1] = (0, -1, 0), (-1, 0, 0)
    return M


def ribbon(pts, width, thick, side=(0, 1, 0)):
    """Flat webbing along a path: a width x thick rectangle swept with its width along `side`."""
    pts = np.array(pts, float); side = np.array(side, float); rings = []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]; t /= np.linalg.norm(t)
        w = side - t * side.dot(t); w /= np.linalg.norm(w); u = np.cross(t, w)
        rings.append([p + w * width / 2 + u * thick / 2, p - w * width / 2 + u * thick / 2, p - w * width / 2 - u * thick / 2, p + w * width / 2 - u * thick / 2])
    return lib.loft(np.array(rings), cap0=True, cap1=True)


def smooth_path(pts, r, k=5):
    """Round the corners of a polyline with radius r (k points per bend), as a bent tube would be."""
    pts = [np.array(p, float) for p in pts]; out = [pts[0]]
    for a, b, c in zip(pts[:-2], pts[1:-1], pts[2:]):
        u = (a - b) / np.linalg.norm(a - b); v = (c - b) / np.linalg.norm(c - b)
        d = min(r, 0.45 * np.linalg.norm(a - b), 0.45 * np.linalg.norm(c - b))
        p0 = b + u * d; p1 = b + v * d
        for t in np.linspace(0, 1, k):
            out.append((1 - t) ** 2 * p0 + 2 * t * (1 - t) * b + t ** 2 * p1)
    out.append(pts[-1]); return out


def fabric_sheet(grid, thick=0.14):
    """A thin sheet through a (rows, cols, 3) grid of points: both faces and a hemmed edge."""
    g = np.array(grid, float)
    du = np.gradient(g, axis=0); dv = np.gradient(g, axis=1); nrm = np.cross(dv, du); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-9
    top = g + nrm * thick / 2; bot = g - nrm * thick / 2
    return lib.loft(np.concatenate([top, bot[:, ::-1]], axis=1), cap0=True, cap1=True)


def troop_seat(ctx, out, M, hi, studs=()):
    """Troop seat [F2-10]: bent-tube frame with a laced fabric pan and back, hung from the cabin ceiling on two
    tubes and held to the floor by two cables, with lap belt and shoulder straps to a rotary buckle.
    Origin: floor under the pan centre; local x = the way the occupant faces."""
    al, fab, belt, st = out; n = ctx.n(10, 8); pan_z = 16.5; w = 9.4; rt = 0.42
    top_z = pan_z + 25.0; ceil_z = CEIL - FLOOR - 0.4
    # frame: one tube round the pan, one up and over the back
    loop = [(float(x), float(y), pan_z) for x, y in lib.rrect(15.2, 2 * w, 2.2, 4)]
    al.merge(lib.tube(loop + loop[:2], rt, n, cap=False), M)
    back = smooth_path([(-7.6, w, pan_z), (-9.0, w, pan_z + 12.0), (-9.6, w, top_z), (-9.6, -w, top_z), (-9.0, -w, pan_z + 12.0), (-7.6, -w, pan_z)], 2.4)
    al.merge(lib.tube(back, rt, n), M)
    for sy in (1, -1):
        al.merge(lib.tube([(-9.6, sy * (w - 2.6), top_z), (-9.3, sy * (w - 2.6), ceil_z)], 0.3, n), M)           # ceiling hangers
        st.merge(lib.revolve([(0.75, 0), (0.75, 0.5), (0.4, 0.9), (0, 0.9)], n), M @ T(-9.3, sy * (w - 2.6), ceil_z + 0.4) @ S(1, 1, -1))
        st.merge(lib.revolve([(0.5, 0), (0.5, 1.6), (0, 1.6)], n), M @ T(-9.6, sy * (w - 2.6), top_z - 0.8))     # wire-bender energy attenuator housing
        for (x0, x1) in ((6.6, 10.5), (-7.6, -12.0)):                                                              # floor cables to the seat studs
            top = (M @ np.array((x0, sy * w, pan_z - rt, 1.0)))[:3]; foot = None
            for (ss, sb) in studs:
                d = math.hypot(ss - top[0], sb - top[1])
                if d < 11.0 and (foot is None or d < foot[0]): foot = (d, ss, sb)
            if foot:                                                                                               # quick-release fitting on the floor stud
                p = np.array((foot[1], foot[2], FLOOR - FL.PAN_DEPTH + 0.74))
                st.merge(lib.revolve([(0.55, -0.1), (0.62, 0.25), (0.5, 0.7), (0.3, 0.95), (0, 0.95)], n), T(*p))
                st.merge(lib.tube([p + (0, 0, 0.9), p + (top - p) * 0.25 + (0, 0, 0.4), top], 0.09, 5))
                st.merge(lib.revolve([(0.2, 0), (0.2, 1.3), (0, 1.3)], 6, lib.frame_to(p + (top - p) * 0.2 + (0, 0, 0.5), top)[0]))
            else:                                                                                                  # outboard legs: fitting on the floor by the wall
                st.merge(lib.tube([(x0, sy * w, pan_z - rt), (x1, sy * (w + 0.8), 0.5)], 0.09, 5), M)
                st.merge(lib.revolve([(0.85, 0), (0.85, 0.22), (0.4, 0.5), (0, 0.5)], n), M @ T(x1, sy * (w + 0.8), 0))
            st.merge(lib.revolve([(0.22, 0), (0.22, 1.1), (0, 1.1)], 6), M @ T(x0 + (x1 - x0) * 0.12, sy * (w + 0.1), pan_z - rt - 1.5))
    # pan: sagged between the tubes, wrapped over them at the sides
    ys = np.linspace(-(w + 0.1), w + 0.1, ctx.n(13, 9)); xs = np.linspace(-7.5, 7.5, ctx.n(11, 7)); g = []
    for x in xs:
        row = []
        for y in ys:
            e = abs(y) / (w + 0.1); sag = 1.7 * (1 - e ** 2.2) * (1 - (x / 8.6) ** 2)
            z = pan_z + rt + 0.1 - sag + 0.10 * math.sin(3.1 * x + 1.3 * y) * (1 - e)
            row.append((x, y, z))
        g.append(row)
    fab.merge(fabric_sheet(g), M)
    # back: sagged, with a lumbar curve
    ts = np.linspace(0.02, 0.985, ctx.n(13, 8)); g = []
    for t in ts:
        cx = -7.6 - 2.0 * t; z = pan_z + 1.2 + (top_z - pan_z - 1.0) * t
        row = []
        for y in ys:
            e = abs(y) / (w + 0.1); sag = 1.5 * (1 - e ** 2.2) * math.sin(math.pi * min(1, t * 1.02)) ** 0.7
            row.append((cx - rt - 0.1 + (0.0 if e > 0.97 else -sag) + 0.08 * math.sin(2.6 * z + 1.7 * y) * (1 - e), y, z))
        g.append(row)
    fab.merge(fabric_sheet(g), M)
    # hems laced round the side tubes: a sleeve every few inches
    for sy in (1, -1):
        for x in np.linspace(-6.0, 6.0, 5):
            fab.merge(lib.tube([(x - 0.7, sy * w, pan_z), (x + 0.7, sy * w, pan_z)], rt + 0.09, n, cap=False), M)
        for t in np.linspace(0.12, 0.9, 6):
            z = pan_z + (top_z - pan_z) * t; x = -7.6 - 2.0 * t + (0.25 if t < 0.5 else 0.0)
            fab.merge(lib.tube([(x, sy * w, z - 0.7), (x - 0.06, sy * w, z + 0.7)], rt + 0.09, n, cap=False), M)
    # restraint: lap belt halves lying on the pan, shoulder straps down the back, rotary buckle
    for sy in (1, -1):
        belt.merge(ribbon([(-6.8, sy * (w - 0.3), pan_z + 0.6), (-5.0, sy * 6.5, pan_z - 0.3), (-3.6, sy * 3.2, pan_z - 0.75), (-3.2, sy * 1.0, pan_z - 0.8)], 1.75, 0.09, (1, 0, 0)), M)
        belt.merge(ribbon([(-10.0, sy * 3.0, top_z + 0.4), (-9.9, sy * 3.0, top_z - 1.0), (-9.6, sy * 2.9, pan_z + 14.0), (-9.0, sy * 2.6, pan_z + 5.0), (-7.4, sy * 1.6, pan_z + 0.4), (-4.0, sy * 0.9, pan_z - 0.7)], 1.75, 0.09, (0, 1, 0)), M)
        st.merge(lib.box((-9.8, sy * 3.0, top_z - 2.4), (0.5, 2.1, 1.3)), M)                                     # strap adjusters
    st.merge(lib.revolve([(1.25, 0), (1.25, 0.45), (0.9, 0.7), (0, 0.7)], ctx.n(16, 10)), M @ T(-3.2, 0, pan_z - 0.85))
    st.merge(lib.box((-3.2, 0, pan_z - 0.05), (0.5, 1.6, 0.25)), M)


def gauge(out, M, r, hi, n=18):
    blk, face, lens = out
    blk.merge(lib.revolve([(r, 0), (r, 0.35), (r - 0.22, 0.35), (r - 0.22, 0.12)], n, M, cap0=False, cap1=False))
    face.merge(lib.revolve([(r - 0.22, 0.1), (0, 0.1)], n, M, cap0=False, cap1=False))
    if hi:
        for i in range(4):
            a = math.pi / 4 + i * math.pi / 2
            blk.merge(lib.revolve([(0.14, 0), (0.14, 0.18), (0, 0.18)], 6), M @ T((r + 0.32) * math.cos(a), (r + 0.32) * math.sin(a), 0))


UP_AFT, UP_TILT = (246.5, 0.0, 265.0), 0.0


def cockpit(ctx):
    hi = ctx.lod == 0
    arm, fab, belt, st, al, blk, face, grey, yel, red = (Mesh() for _ in range(10))
    # ---- instrument panel: one piece across the cockpit, tilted back 30 deg, glare shield on top
    Mp = T(207.0, 0, 235.0) @ R('bl', -30.0)     # panel plane: local y = BL, local z = up along the panel face, local x = normal (aft)
    art = getattr(ctx, 'art', None); knb = Mesh()
    PN.panel(ctx, Mp, art['panel'], (blk, knb))
    # ---- lower console: straight top from the foot of the panel aft; the manual's drawn console top takes its aft end
    A = np.array((CK.CON_A[0], 0, CK.CON_A[1])); B = np.array((CK.CON_B[0], 0, CK.CON_B[1])); L = np.linalg.norm(B - A)
    ang = math.degrees(math.atan2(A[2] - B[2], B[0] - A[0])); u = (B - A) / L
    Mc = T(*(A + u * 0.5)) @ R('bl', -ang)
    assert abs(L - art['console']['l'] - 1.0) < 1.2, (L, art['console']['l'])
    PN.console_top(ctx, Mc, art['console'], (blk, knb))
    # parking brake lever in the slot the drawing letters PARKING BRAKE [F2-8; lever shape F2-4 item 16]
    p0 = (Mc @ np.array((27.6, -2.35, 0.0, 1.0)))[:3]; p1 = (Mc @ np.array((26.4, -2.35, 3.4, 1.0)))[:3]
    st.merge(lib.cyl(p0, p1, 0.2, 6)); yel.merge(lib.cyl(p1 + (0, -1.2, 0), p1 + (0, 1.2, 0), 0.36, ctx.n(12, 8)))
    # ---- upper console and engine control quadrant [F2-7 plan, F2-13]; where it hangs is read from figure 2-4 [EST]
    th = math.radians(UP_TILT); Mu = np.eye(4)
    Mu[:3, 0] = (-math.cos(th), 0, -math.sin(th)); Mu[:3, 2] = (math.sin(th), 0, -math.cos(th)); Mu[:3, 3] = UP_AFT
    PN.upper_console(ctx, Mu, art['upper'], (blk, knb, st))
    ctx.part('airframe', 'cockpit_knobs', knb, 'paint_black', 40)
    # ---- flight controls: cyclic, collective and pedals for each seat (own nodes so the sim can move them)
    for sg, side in ((1, 'L'), (-1, 'R')):
        cy = sg * CK.SEAT_BL
        nd = ctx.node(f'cyclic_{side}', 'airframe', pivot=(222.0, cy, CFLOOR + 1.0))
        m = Mesh(); g = Mesh()
        m.merge(lib.tube(smooth_path([(222.0, cy, CFLOOR + 1.0), (220.9, cy, CFLOOR + 6.0), (221.2, cy, CFLOOR + 10.5), (223.6, cy, CFLOOR + 13.8), (225.6, cy, CFLOOR + 15.4)], 3.0), 0.55, 10))   # bowed forward [TM 55-1520-237-23 fig 11-34]
        g.merge(PN.cyclic_grip(ctx, art['cyclic'], (225.6, cy, CFLOOR + 15.2)))
        ctx.part(nd, 'cyclic_tube', m, 'steel_dark', 40); ctx.part(nd, 'cyclic_grip', g, 'paint_black', 40)
        bl_c = CK.collective_bl(sg); p0 = np.array((241.5, bl_c, CFLOOR + 3.6)); g0 = np.array((229.0, bl_c, CFLOOR + 9.6))
        nd = ctx.node(f'collective_{side}', 'airframe', pivot=tuple(p0))
        m = Mesh(); g = Mesh(); d = g0 - p0; Ls = np.linalg.norm(d); dd = d / Ls
        m.merge(lib.tube([p0, g0], 0.6, 8)); Mg = np.eye(4)
        Mg[:3, 0] = (0, -1, 0); Mg[:3, 1] = (dd[2], 0, -dd[0]); Mg[:3, 2] = dd; Mg[:3, 3] = g0
        gb, gf, gk = PN.collective_grip(ctx, art['collective'], Mg); g.merge(gb); g.merge(gk)
        of = ctx.part(nd, 'collective_face', gf, 'collective_art' if 'collective_art' in ctx.mats else 'paint_black', 40)
        if of is not None and 'collective_art' in ctx.mats: PN.collective_uv(of, art['collective'], Mg)
        # the thicker sleeve ahead of the boot; the pilot's is the fluted friction grip [TM 55-1520-237-23 fig 11-40 sheet 1, para 11-7.4]
        fr = Mesh(); a, b = p0 + dd * (Ls - 4.6), p0 + dd * (Ls - 0.9)
        fr.merge(lib.cyl(a, b, 0.82, ctx.n(14, 10)))
        if sg < 0:
            Mf, _ = lib.frame_to(a + dd * 0.5, b)
            for i in range(12):
                t = i * math.tau / 12; fr.merge(lib.box((0.9 * math.cos(t), 0.9 * math.sin(t), 1.0), (0.16, 0.16, 2.0), lib.R('z', math.degrees(t))), Mf)
        ctx.part(nd, 'collective_tube', m, 'steel_dark', 40); ctx.part(nd, 'collective_grip', g, 'paint_black', 40)
        ctx.part(nd, 'collective_friction', fr, 'paint_black', 40)
        cov, cfab, cst, cwht = CK.collective_cover(ctx, sg, p0, g0)
        ctx.part('airframe', f'collective_cover_{side}', cov, 'paint_black', 40)
        ctx.part('airframe', f'collective_boot_{side}', cfab, 'fabric_boot' if 'fabric_boot' in ctx.mats else 'rubber', 40)
        ctx.part('airframe', f'collective_cover_screws_{side}', cst, 'steel', 40)
        if cwht.n: ctx.part('airframe', f'collective_no_step_{side}', cwht, 'paint_white' if 'paint_white' in ctx.mats else 'steel', 40)
    CK.build(ctx, wall_bl, (arm, fab, belt))
    for name, m, mat in (('crew_seat_armour', arm, 'armor'), ('crew_seat_cushions', fab, 'fabric_seat'), ('crew_harness', belt, 'fabric_belt'),
                         ('cockpit_steel', st, 'steel'), ('cockpit_brackets', al, 'frame_grey'), ('instrument_panel', blk, 'panel_face'),
                         ('instrument_faces', face, 'instrument'), ('console_panels', grey, 'paint_grey'),
                         ('cockpit_yellow', yel, 'paint_yellow'), ('cockpit_red', red, 'paint_red')):
        o = ctx.part('airframe', name, m, mat, 35)
        if name == 'instrument_faces' and o is not None and getattr(ctx, 'box_uv', None) is not None:
            import detail; detail.instrument_uv(o, Mp, np.eye(4))


def cabin(ctx):
    hi = ctx.lod == 0
    quilt, od, al, fab, belt, st, lens, grey = (Mesh() for _ in range(8))
    cs = np.arange(RC.STA_CABIN[0], RC.STA_CABIN[1] + 0.1, 151.0 / 16)
    FL.build(ctx, wall_bl)
    quilt.merge(slab(cs, CEIL + 0.9, 0.9))
    quilt.merge(lib.box((342.0, 0, CEIL - 1.0), (46.0, 32.0, 2.0)))        # transmission drip pan, 2 in lower [F6-9]
    od.merge(bulkhead(RC.STA_CABIN[1], 1.5, FLOOR - 1.0, CEIL + 1.5))
    quilt.merge(bulkhead(RC.STA_CABIN[1] - 0.8, 0.8, FLOOR + 1.0, CEIL - 0.5, INSET + 1.0))
    od.merge(bulkhead(192.5, 1.2, 203.0, 243.5))                           # nose avionics bay bulkhead
    # frames and quilted soundproofing on the side walls, around the openings
    for sg in (1, -1):
        for s in (249.5, 302.5, 381.0, 395.5):
            al.merge(wall_panel(s - 1.0, s + 1.0, FLOOR, CEIL, sg, INSET - 0.2, 1.9, 2, 10))
        for s0, s1, w0, w1 in ((251.0, 256.5, FLOOR + 0.5, CEIL - 0.3), (257.5, 296.5, FLOOR + 0.5, 231.0), (297.5, 301.5, FLOOR + 0.5, CEIL - 0.3),
                               (382.5, 394.5, FLOOR + 0.5, CEIL - 0.3)):
            quilt.merge(wall_panel(s0, s1, w0, w1, sg, ns=max(2, int((s1 - s0) / 6)), nw=10))
    # dome lights
    for s in (270.0, 305.0, 385.0):
        grey.merge(lib.revolve([(2.6, 0), (2.6, 0.5)], 14, T(s, 0, CEIL - 0.5), cap0=False, cap1=False))
        lens.merge(lib.revolve([(2.4, 0.1), (1.6, -0.5), (0, -0.7)], 14, T(s, 0, CEIL - 0.35), cap0=False, cap1=False))
    # ---- seats [figure 2-10]
    troop = (al, fab, belt, st)
    seats = [(270.0, 27.0, 'left'), (270.0, -27.0, 'right'), (266.0, 0.0, 'fwd')]
    seats += [(301.0, bl, 'aft') for bl in (-20.0, 0.0, 20.0)]
    seats += [(341.5, bl, 'fwd') for bl in (-30.0, -10.0, 10.0, 30.0)]
    seats += [(387.0, bl, 'fwd') for bl in (-30.0, -10.0, 10.0, 30.0)]
    studs = FL.stud_points()
    for s, bl, facing in seats:
        troop_seat(ctx, troop, T(s, bl, FLOOR) @ seat_frame(facing), hi, studs)
    # first-aid kits and a fire extinguisher on the aft bulkhead
    for bl in (-22.0, 22.0):
        od.merge(lib.box((396.2, bl, 250.0), (2.0, 9.0, 6.0)))
    rd = Mesh(); rd.merge(lib.revolve([(1.7, 0), (1.7, 9.0), (0.9, 10.5), (0.6, 12.0), (0, 12.0)], 12, T(253.5, -33.0, FLOOR + 14.0)))
    ctx.part('airframe', 'fire_extinguisher', rd, 'paint_red', 40)
    for name, m, mat in (('soundproofing', quilt, 'quilt'), ('bulkheads', od, 'paint_od_interior'), ('cabin_frames', al, 'aluminium'),
                         ('troop_seat_fabric', fab, 'fabric_seat'), ('troop_belts', belt, 'fabric_belt'), ('cabin_steel', st, 'steel'),
                         ('dome_lenses', lens, 'glass_lens'), ('cabin_grey', grey, 'paint_grey')):
        ctx.part('airframe', name, m, mat, 35)
    ctx.socket('eye_pilot', (229.0, -CK.SEAT_BL, 258.0)); ctx.socket('eye_copilot', (229.0, CK.SEAT_BL, 258.0))
    ctx.socket('spawn_cabin', (330.0, 0.0, FLOOR)); ctx.socket('spawn_ground_left', (330.0, 110.0, RC.WL_GROUND))
    ctx.socket('seat_gunner_left', (270.0, 27.0, FLOOR + 16.5)); ctx.socket('seat_gunner_right', (270.0, -27.0, FLOOR + 16.5))


def build(ctx):
    cabin(ctx); cockpit(ctx)
