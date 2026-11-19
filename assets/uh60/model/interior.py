"""Cabin and cockpit: floors, liners, bulkheads, 14 cabin seats, two armoured crew seats, instrument panel, consoles,
flight controls. Compartment sizes are from the manual (cabin STA 247 to 398, floor WL 206.75, ceiling WL 261 with the
drip pan 2 in lower, cockpit floor WL 215 [F6-1, F6-9]; instrument panel tilted back 30 deg [TM 2.10.1]). Seat
arrangement follows figure 2-10; each fitting's own size is inferred from what it has to hold [INF].
"""
import math
import numpy as np
import lib, recipe as RC
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


def troop_seat(ctx, out, M, hi):
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
        for (x0, x1) in ((6.6, 10.5), (-7.6, -12.0)):                                                              # floor cables and fittings
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


def crew_seat(ctx, out, M, hi):
    """Armoured, crash-attenuating crew seat on floor rails. Origin: cockpit floor under the pan centre."""
    arm, fab, belt, st, al = out; pan_z = 12.5
    bucket = lib.rrect(19.5, 18.5, 2.5, 4)
    arm.merge(lib.prism(bucket, pan_z - 2.6, pan_z), M)
    back = lib.rrect(19.5, 27.0, 3.0, 4)
    # back plate: local sketch (y, z) -> seat (bl, wl), extruded along seat x
    Mb = M @ T(-9.6, 0, pan_z - 2.0) @ R('bl', 12.0)
    plate = Mesh(); plate.merge(lib.prism(back, -1.2, 0.0), np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 13.5], [0, 0, 0, 1.0]]))
    arm.merge(plate, Mb)
    for sy in (1, -1):                                   # side armour wings
        arm.merge(lib.box((-2.5, sy * 10.3, pan_z + 6.0), (15.0, 0.9, 13.0)), M)
    hr = Mesh(); hr.merge(lib.prism(lib.rrect(9.0, 6.5, 2.0, 4), -1.6, 0.6), np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 30.5], [0, 0, 0, 1.0]]))
    fab.merge(hr, Mb)
    cush = Mesh(); cush.merge(lib.prism(lib.rrect(16.5, 22.0, 2.5, 4), 0.0, 1.8), np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 13.0], [0, 0, 0, 1.0]]))
    fab.merge(cush, Mb)
    fab.merge(lib.prism(lib.rrect(16.5, 16.5, 2.5, 4), pan_z, pan_z + 2.2), M @ T(0.5, 0, 0))
    # harness: two shoulder straps, lap belt, rotary buckle
    for sy in (1, -1):
        belt.merge(lib.tube([(-11.5, sy * 3.2, pan_z + 27.0), (-8.6, sy * 3.4, pan_z + 16.0), (-5.2, sy * 2.2, pan_z + 6.0), (-1.5, sy * 0.6, pan_z + 3.2)], 0.55, 4), M)
        belt.merge(lib.tube([(-6.5, sy * 9.0, pan_z + 1.8), (-3.5, sy * 5.0, pan_z + 2.9), (-1.5, sy * 0.8, pan_z + 3.1)], 0.55, 4), M)
    st.merge(lib.revolve([(1.5, 0), (1.5, 0.7), (0, 0.7)], 12), M @ T(-1.5, 0, pan_z + 2.9))
    # frame: two vertical guide tubes behind the bucket, floor rails
    for sy in (1, -1):
        al.merge(lib.tube([(-12.5, sy * 7.0, 0.8), (-13.5, sy * 7.0, pan_z + 22.0)], 0.9, 8), M)
        al.merge(lib.box((-2.0, sy * 7.0, 0.5), (26.0, 1.6, 1.0)), M)
        al.merge(lib.tube([(6.0, sy * 7.0, 1.0), (-11.0, sy * 7.0, pan_z - 2.4)], 0.6, 6), M)


def gauge(out, M, r, hi, n=18):
    blk, face, lens = out
    blk.merge(lib.revolve([(r, 0), (r, 0.35), (r - 0.22, 0.35), (r - 0.22, 0.12)], n, M, cap0=False, cap1=False))
    face.merge(lib.revolve([(r - 0.22, 0.1), (0, 0.1)], n, M, cap0=False, cap1=False))
    if hi:
        for i in range(4):
            a = math.pi / 4 + i * math.pi / 2
            blk.merge(lib.revolve([(0.14, 0), (0.14, 0.18), (0, 0.18)], 6), M @ T((r + 0.32) * math.cos(a), (r + 0.32) * math.sin(a), 0))


def cockpit(ctx):
    hi = ctx.lod == 0
    arm, fab, belt, st, al, blk, face, grey, yel, red = (Mesh() for _ in range(10))
    for sg in (1, -1):
        M = T(232.5, sg * 21.0, CFLOOR) @ seat_frame('fwd')
        crew_seat(ctx, (arm, fab, belt, st, al), M, hi)
    # ---- instrument panel: one piece across the cockpit, tilted back 30 deg, glare shield on top
    Mp = T(207.0, 0, 235.0) @ R('bl', -30.0)     # panel plane: local y = BL, local z = up along the panel face, local x = normal (aft)
    def P(y, z, x=0.0):     # panel-local to a placement matrix whose +Z is the panel normal facing the crew
        return Mp @ T(x, y, z) @ np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1.0]])
    outline = [(-33.5, 0.0), (-9.0, 0.0), (-9.0, -9.5), (9.0, -9.5), (9.0, 0.0), (33.5, 0.0), (33.5, 12.5), (30.5, 16.0), (-30.5, 16.0), (-33.5, 12.5)]
    pm = Mesh(); pm.merge(lib.prism(np.array(outline), -2.5, 0.0), np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]))
    blk.merge(pm, Mp)
    blk.merge(lib.box((200.5, 0, 249.9), (8.5, 67.0, 0.6)))            # glare shield
    for sg in (1, -1):
        cy = sg * 21.0
        # flight instruments: airspeed, attitude (VSI), altimeter over clock, HSI, vertical speed, radar altimeter
        for (dy, z, r) in RC.FLIGHT_GAUGES:
            gauge((blk, face, None), P(cy + dy, z), r, hi)
        for dy in (-7.5, -4.5):                                      # mode select / CIS panels under the flight instruments
            grey.merge(lib.box((0.12, cy + dy * sg, 1.3), (0.25, 2.4, 1.6)), Mp)
    # centre: caution/advisory panel, central display unit (vertical-scale engine instruments), pilot display units
    face.merge(lib.box((0.08, 0, 12.6), (0.16, 13.5, 4.2)), Mp)
    grey.merge(lib.box((0.05, 0, 12.6), (0.14, 14.3, 5.0)), Mp)
    for i in range(13):
        face.merge(lib.box((0.1, -6.0 + i * 1.0, 6.0), (0.2, 0.62, 7.0)), Mp)
    grey.merge(lib.box((0.04, 0, 6.0), (0.12, 14.3, 7.8)), Mp)
    for dy in (-11.2, 11.2):
        face.merge(lib.box((0.1, dy, 9.0), (0.2, 2.6, 5.6)), Mp); grey.merge(lib.box((0.04, dy, 9.0), (0.12, 3.2, 6.2)), Mp)
    red.merge(lib.box((0.2, -11.2, 14.4), (0.3, 3.0, 1.0)), Mp); yel.merge(lib.box((0.2, 11.2, 14.4), (0.3, 3.0, 1.0)), Mp)   # master warning panels
    # ---- lower console between the seats: radios on rails
    con = [(212.0, 226.5), (224.0, 229.5), (246.0, 223.0), (246.0, CFLOOR), (212.0, CFLOOR)]
    blk.merge(lib.prism(np.array(con)[::-1], -8.6, 8.6, lib.plane_basis('side_l')))
    top0 = np.array((224.0, 0, 229.5)); top1 = np.array((246.0, 0, 223.0)); L = np.linalg.norm(top1 - top0)
    ang = math.degrees(math.atan2(top0[2] - top1[2], top1[0] - top0[0]))
    Mc = T(*top0) @ R('bl', -ang)
    y_cols = (-4.1, 4.1); x = 0.6
    heights = (2.6, 2.2, 3.4, 2.2, 2.6, 3.0, 2.2, 2.6)
    for hgt in heights:
        if x + hgt > L - 0.4: break
        for yc in y_cols:
            grey.merge(lib.box((x + hgt / 2, yc, 0.08), (hgt - 0.25, 5.75, 0.16)), Mc)
            face.merge(lib.box((x + hgt / 2, yc + 1.2, 0.18), (min(1.0, hgt - 0.9), 2.4, 0.1)), Mc)
            if hi:
                for k in range(3):
                    blk.merge(lib.revolve([(0.36, 0), (0.3, 0.55), (0, 0.55)], 8), Mc @ T(x + hgt / 2, yc - 2.2 + k * 0.95, 0.16))
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        st.merge(lib.revolve([(0.16, 0), (0.16, 0.08), (0, 0.08)], 6), Mc @ T(x + hgt / 2 + sx * (hgt / 2 - 0.35), yc + sy * 2.6, 0.16))
        x += hgt
    # ---- upper (overhead) console and the engine control quadrant
    grey.merge(lib.box((234.0, 0, 266.2), (25.0, 18.0, 2.4)))
    for i, sx in enumerate(np.linspace(226.0, 243.0, 6)):
        for yc in (-4.4, 4.4):
            face.merge(lib.box((sx, yc, 264.9), (2.4, 7.4, 0.14)))
            if hi:
                for k in range(5):
                    st.merge(lib.cyl((sx, yc - 2.8 + k * 1.4, 264.9), (sx + 0.2, yc - 2.8 + k * 1.4, 264.1), 0.12, 6))
    for sg in (1, -1):                                               # power control levers, fuel selectors, fire T-handles
        blk.merge(lib.cyl((222.5, sg * 2.2, 265.2), (220.5, sg * 2.2, 260.6), 0.3, 8))
        yel.merge(lib.revolve([(0.75, 0), (0.75, 1.5), (0, 1.5)], 10, lib.frame_to((220.6, sg * 2.2, 260.8), (220.0, sg * 2.2, 259.4))[0]))
        blk.merge(lib.cyl((222.5, sg * 5.0, 265.2), (221.0, sg * 5.0, 261.8), 0.25, 8))
        red.merge(lib.box((220.9, sg * 5.0, 261.4), (0.9, 2.6, 0.9)))
        yel.merge(lib.cyl((222.5, sg * 7.4, 265.2), (221.4, sg * 7.4, 262.6), 0.25, 8))
    # ---- flight controls: cyclic, collective and pedals for each seat (own nodes so the sim can move them)
    for sg, side in ((1, 'L'), (-1, 'R')):
        cy = sg * 21.0
        nd = ctx.node(f'cyclic_{side}', 'airframe', pivot=(222.0, cy, CFLOOR + 1.0))
        m = Mesh(); g = Mesh(); boot = Mesh()
        m.merge(lib.tube([(222.0, cy, CFLOOR + 1.0), (222.0, cy, CFLOOR + 9.0), (223.4, cy, CFLOOR + 13.0), (225.6, cy, CFLOOR + 15.5)], 0.55, 8))
        g.merge(lib.tube([(225.6, cy, CFLOOR + 15.5), (226.4, cy, CFLOOR + 17.5), (226.6, cy, CFLOOR + 20.4)], [0.75, 0.85, 0.8], 10))
        g.merge(lib.box((226.2, cy, CFLOOR + 21.0), (1.9, 1.7, 1.5)))
        boot.merge(lib.revolve([(2.6, 0), (1.6, 1.6), (0.8, 2.8)], 12, T(222.0, cy, CFLOOR + 0.2), cap0=False, cap1=False))
        ctx.part(nd, 'cyclic_tube', m, 'steel_dark', 40); ctx.part(nd, 'cyclic_grip', g, 'paint_black', 40)
        ctx.part('airframe', 'cyclic_boot', boot, 'rubber', 40)
        bl_c = cy + 10.6
        nd = ctx.node(f'collective_{side}', 'airframe', pivot=(240.0, bl_c, CFLOOR + 4.0))
        m = Mesh(); g = Mesh()
        m.merge(lib.tube([(240.0, bl_c, CFLOOR + 4.0), (229.0, bl_c, CFLOOR + 9.4)], 0.6, 8))
        g.merge(lib.tube([(229.0, bl_c, CFLOOR + 9.4), (224.6, bl_c, CFLOOR + 11.6)], 0.85, 10))
        g.merge(lib.box((223.8, bl_c, CFLOOR + 12.3), (2.6, 2.2, 2.0)))
        ctx.part(nd, 'collective_tube', m, 'steel_dark', 40); ctx.part(nd, 'collective_grip', g, 'paint_black', 40)
        for dy in (-4.6, 4.6):
            al.merge(lib.box((203.5, cy + dy, CFLOOR + 6.4), (0.8, 4.4, 5.0), None))
            al.merge(lib.tube([(203.9, cy + dy, CFLOOR + 4.2), (205.5, cy + dy, CFLOOR + 0.6)], 0.4, 6))
    for name, m, mat in (('crew_seat_armour', arm, 'armor'), ('crew_seat_cushions', fab, 'fabric_seat'), ('crew_harness', belt, 'fabric_belt'),
                         ('cockpit_steel', st, 'steel'), ('cockpit_frames', al, 'aluminium'), ('instrument_panel', blk, 'panel_face'),
                         ('instrument_faces', face, 'instrument'), ('console_panels', grey, 'paint_grey'),
                         ('cockpit_yellow', yel, 'paint_yellow'), ('cockpit_red', red, 'paint_red')):
        o = ctx.part('airframe', name, m, mat, 35)
        if name == 'instrument_faces' and o is not None and getattr(ctx, 'box_uv', None) is not None:
            import detail; detail.instrument_uv(o, Mp, Mc)


def cabin(ctx):
    hi = ctx.lod == 0
    fl, quilt, od, al, fab, belt, st, lens, grey = (Mesh() for _ in range(9))
    cs = np.arange(RC.STA_CABIN[0], RC.STA_CABIN[1] + 0.1, 151.0 / 16)
    fl.merge(slab(cs, FLOOR, 1.4))
    fl.merge(slab(np.linspace(194.0, 247.0, 10), CFLOOR, 1.2))
    grey.merge(lib.box((246.6, 0, (FLOOR + CFLOOR) / 2 - 0.6), (0.8, 2 * wall_bl(247.0, FLOOR) - 0.5, CFLOOR - FLOOR + 0.1)))   # step riser
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
    # cargo tiedown fittings: recessed rings in the floor on a 20 in grid [figure 6-11 shows the grid; spacing inferred]
    for s in np.arange(257.0, 392.0, 19.0):
        for bl in (-30.0, -10.0, 10.0, 30.0):
            if abs(bl) > wall_bl(s, FLOOR) - 3: continue
            st.merge(lib.revolve([(1.9, 0.02), (1.9, 0.1), (1.5, 0.1), (1.5, 0.02)], 12, T(s, bl, FLOOR), cap0=False, cap1=False))
            if hi:
                a = np.linspace(0, math.pi, 7)
                st.merge(lib.tube([(s + 1.1 * math.cos(t), bl, FLOOR + 0.1 + 0.9 * math.sin(t)) for t in a], 0.16, 5))
    # ---- seats [figure 2-10]
    troop = (al, fab, belt, st)
    seats = [(270.0, 27.0, 'left'), (270.0, -27.0, 'right'), (266.0, 0.0, 'fwd')]
    seats += [(301.0, bl, 'aft') for bl in (-20.0, 0.0, 20.0)]
    seats += [(349.0, bl, 'fwd') for bl in (-30.0, -10.0, 10.0, 30.0)]
    seats += [(385.5, bl, 'fwd') for bl in (-30.0, -10.0, 10.0, 30.0)]
    for s, bl, facing in seats:
        troop_seat(ctx, troop, T(s, bl, FLOOR) @ seat_frame(facing), hi)
    # first-aid kits and a fire extinguisher on the aft bulkhead
    for bl in (-22.0, 22.0):
        od.merge(lib.box((396.2, bl, 250.0), (2.0, 9.0, 6.0)))
    rd = Mesh(); rd.merge(lib.revolve([(1.7, 0), (1.7, 9.0), (0.9, 10.5), (0.6, 12.0), (0, 12.0)], 12, T(253.5, -33.0, FLOOR + 14.0)))
    ctx.part('airframe', 'fire_extinguisher', rd, 'paint_red', 40)
    for name, m, mat in (('floors', fl, 'floor'), ('soundproofing', quilt, 'quilt'), ('bulkheads', od, 'paint_od_interior'), ('cabin_frames', al, 'aluminium'),
                         ('troop_seat_fabric', fab, 'fabric_seat'), ('troop_belts', belt, 'fabric_belt'), ('cabin_steel', st, 'steel'),
                         ('dome_lenses', lens, 'glass_lens'), ('cabin_grey', grey, 'paint_grey')):
        ctx.part('airframe', name, m, mat, 35)
    ctx.socket('eye_pilot', (229.0, -21.0, 258.0)); ctx.socket('eye_copilot', (229.0, 21.0, 258.0))
    ctx.socket('spawn_cabin', (330.0, 0.0, FLOOR)); ctx.socket('spawn_ground_left', (330.0, 110.0, RC.WL_GROUND))
    ctx.socket('seat_gunner_left', (270.0, 27.0, FLOOR + 16.5)); ctx.socket('seat_gunner_right', (270.0, -27.0, FLOOR + 16.5))


def build(ctx):
    cabin(ctx); cockpit(ctx)
