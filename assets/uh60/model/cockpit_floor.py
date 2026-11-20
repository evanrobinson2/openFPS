"""Cockpit floor and everything standing on it, from TM 1-1520-237-10 figure 2-4 (Cockpit Diagram, two sheets).

Figure 2-4 is an undimensioned perspective view from behind the seats. Read off it [F2-4]: the directional control
pedals (32) are ribbed pads on arms, one pair per seat; the lower console (40) is a wide pedestal with a sloped top
of control heads, the battery / utility bus circuit breaker panel (41) at its aft foot, the parking brake lever (16)
at its right aft corner, the lower console utility light (18) and the fire extinguisher (42) on its left side; each
crew seat stands on a tubular frame with corner guide tubes, diagonal struts and feet on the floor; the collective
(37, 38) runs through a ribbed boot beside the seat.
Not in the figure and so inferred [INF]: every size here, the floor panel joints and covers, the heel plates, the
seat track section and bolt pitch, the pedal linkage under the pad, the cyclic boot, all wear.
"""
import math
import numpy as np
import lib, recipe as RC, floor as FL
from lib import Mesh, T, R, S

CF = RC.WL_COCKPIT_FLOOR
C0, C1, CHALF = 194.0, 247.0, 47.0
SEAT_STA, SEAT_BL = 230.5, 24.2     # BL leaves room for the pilot's collective cover between seat and console [EST]
CYC_STA = 222.0
PED_STA = 204.0
CON_HW = 9.25                              # the drawn console top is 18.0 in wide [F2-8 at 5.75 in per control head]
CON_A, CON_B = (209.6, 234.5), (246.3, 223.5)   # (STA, WL): foot of the instrument panel, aft end of the console top
PAN_Z = 12.5


def outward(m):
    """Make a closed mesh's faces point outward (signed volume positive)."""
    V = m.verts(); vol = 0.0
    for f in m.f:
        a = V[f[0]]
        for i in range(1, len(f) - 1):
            vol += np.dot(a, np.cross(V[f[i]], V[f[i + 1]]))
    if vol < 0: m.f = [f[::-1] for f in m.f]
    return m


def circle(s, bl, r, n=20):
    return np.array([(s + r * math.cos(a), bl + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def spec():
    lines = [((s, -CHALF), (s, CHALF)) for s in (212.0, 228.0)] + [((C0, b), (C1, b)) for b in (-12.5, 12.5)]
    covers, plates, wear, pans = [], [], [], []
    for sg in (1, -1):
        cy = sg * SEAT_BL
        b = sorted((cy - 7.5, cy + 7.5))
        wear += [(209.0, cy, 6.0, 8.0, 255), (226.0, sg * 38.0, 12.0, 7.0, 210), (224.0, sg * 11.5, 16.0, 4.0, 140)]
    return dict(lines=lines, covers=covers, plates=plates, wear=wear, pans=pans)


def material(ctx, out_dir):
    FL.material(ctx, out_dir, 'cockpit_floor', FL.paint('cockpit_floor', out_dir, C0, C1, CHALF, spec(), ctx.log, seed=37))


def bellows(p0, p1, r0, r1, folds, n=14, depth=0.42):
    """Convoluted boot from p0 (radius r0) to p1 (radius r1)."""
    M, L = lib.frame_to(p0, p1); prof = [(r0 + 0.1, 0.0)]
    for i in range(folds):
        t0 = i / folds; t1 = (i + 0.5) / folds
        prof += [(r0 + (r1 - r0) * t0, L * t0 + 0.02), (r0 + (r1 - r0) * t1 - depth, L * t1)]
    prof += [(r1, L - 0.25), (r1 - 0.12, L)]
    return lib.revolve(prof, n, M, cap0=False, cap1=False)


def screw(p, nrm, r=0.16, h=0.07, n=6):
    M, _ = lib.frame_to(p, np.asarray(p, float) + np.asarray(nrm, float))
    return lib.revolve([(r, 0), (r * 0.85, h), (0, h * 1.1)], n, M, cap0=False, cap1=False)


# ------------------------------------------------------------------ pedals
def rect_ring(cx, cy, lx, ly, z, k=4, e=8.0):
    """Superellipse ring (lx along STA, ly along BL); e = 2 is an ellipse, large e a rounded rectangle."""
    out = []
    for t in np.linspace(0, 2 * math.pi, 4 * k, endpoint=False):
        c, s_ = math.cos(t), math.sin(t)
        out.append((cx + lx / 2 * math.copysign(abs(c) ** (2 / e), c), cy + ly / 2 * math.copysign(abs(s_) ** (2 / e), s_), z))
    return out


def boot(ctx, cx, cy, lx, ly, top, h, r_top, out, screws):
    """Zippered fabric boot on a screwed-down retainer frame [TM 55-1520-237-23 figs 11-22 (pedal) and 11-34 (cyclic)].
    cx, cy: centre of the base; top: (STA, BL) the boot closes round at height h. Sizes are not dimensioned [EST]."""
    fab, frame, stl = out; k = ctx.n(6, 4); z0 = CF
    frame.merge(outward(lib.prism(np.array([p[:2] for p in rect_ring(cx, cy, lx, ly, 0, 2, 14.0)]), z0, z0 + 0.1)))
    frame.merge(outward(lib.prism(np.array([p[:2] for p in rect_ring(cx, cy, lx - 0.5, ly - 0.5, 0, 2, 14.0)]), z0 + 0.1, z0 + 0.2)))
    nx, ny = screws
    pts = [(cx + sx * (lx / 2 - 0.3), cy - ly / 2 + 0.3 + (ly - 0.6) * i / (ny - 1)) for sx in (-1, 1) for i in range(ny)]
    pts += [(cx - lx / 2 + 0.3 + (lx - 0.6) * i / (nx - 1), cy + sy * (ly / 2 - 0.3)) for sy in (-1, 1) for i in range(1, nx - 1)]
    for (x, y) in pts: stl.merge(screw((x, y, z0 + 0.1), (0, 0, 1), 0.13, 0.06))
    rings = []
    for t in (0.0, 0.1, 0.3, 0.55, 0.8, 0.94, 1.0):
        u = t ** 0.8; e = 8.0 - 6.0 * u
        rings.append(rect_ring(cx + (top[0] - cx) * u, cy + (top[1] - cy) * u, (lx - 1.3) * (1 - u) + 2 * r_top * u, (ly - 1.3) * (1 - u) + 2 * r_top * u,
                               z0 + 0.2 + (h - 0.2) * t + 0.25 * math.sin(math.pi * t), k, e))
    fab.merge(outward(lib.loft(np.array(rings), cap0=False, cap1=True)))
    zip_ = [np.array(r[0]) + (0.05, 0, 0.02) for r in rings]                      # zipper up the aft face
    stl.merge(lib.tube(zip_, 0.06, 5))


PED_W, PED_H = 4.4, 5.9      # in, pedal plate [EST: figures 11-23 and 11-27 are undimensioned perspectives]


def pedals(ctx, cy, out):
    """Yaw pedals as TM 55-1520-237-23 figures 11-22, 11-23 and 11-27 draw them: a cast plate with six lightening
    pockets, pivoted on the top of a tubular pedal support that comes up through its own zippered boot in the floor.
    The master cylinders, pivot shaft and control rods of figure 11-27 are under the floor and boot, and not built."""
    blk, frm, stl, dull, fab = out; n = ctx.n(10, 7)
    B = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])     # plate local: x = BL, y = up the plate, z = toward the pilot
    for dy in (-4.6, 4.6):
        y0 = cy + dy
        Mp = T(PED_STA, y0, CF + 8.2) @ R('bl', -22.0) @ B
        if (Mp @ np.array((0, 0, 1.0, 0)))[2] < 0: Mp = T(PED_STA, y0, CF + 8.2) @ R('bl', 22.0) @ B
        pad = Mesh(); w, h = PED_W, PED_H
        pad.merge(lib.prism(lib.rrect(w, h, 0.35, 3), -0.3, -0.12))
        for x in (-w / 2 + 0.15, -w / 6, w / 6, w / 2 - 0.15): pad.merge(lib.box((x, 0, -0.03), (0.3, h, 0.2)))         # ribs between the three columns of pockets
        for y in (-h / 2 + 0.15, 0.0, h / 2 - 0.15): pad.merge(lib.box((0, y, -0.03), (w, 0.3, 0.2)))                   # and the two rows
        for sx in (-1, 1): pad.merge(lib.box((sx * 1.2, -1.2, -0.62), (0.3, 1.5, 0.7)))                                 # pivot lugs on the back
        blk.merge(pad, Mp)
        P = lambda x, y, z: (Mp @ np.array((x, y, z, 1.0)))[:3]
        hp = P(0, -1.2, -0.85); post = np.array((hp[0], y0, CF))
        stl.merge(lib.cyl(P(-1.75, -1.2, -0.85), P(1.75, -1.2, -0.85), 0.2, n))                                         # pivot bolt
        frm.merge(lib.cyl(P(-0.95, -1.2, -0.85), P(0.95, -1.2, -0.85), 0.5, n))                                         # boss on the pedal support
        frm.merge(lib.cyl(post + (0, 0, 3.6), hp, 0.62, n))                                                             # pedal support tube
        boot(ctx, post[0] + 1.6, y0, 8.0, 4.4, (post[0], y0), 4.4, 0.8, (fab, dull, stl), (5, 3))


# ------------------------------------------------------------------ lower console
def console(ctx, out):
    body, frm, stl, grey, blk, yel, red, dull = out; hi = ctx.lod == 0; n = ctx.n(12, 8); hw = CON_HW
    top = lambda s: CON_A[1] + (CON_B[1] - CON_A[1]) * (s - CON_A[0]) / (CON_B[0] - CON_A[0])
    rings = []
    for s in (CON_A[0], 212.0, 222.0, 234.0, CON_B[0]):
        h = top(s); z0 = CF if s >= 212.0 else h - 3.2
        rings.append([(s, hw - 0.4, h), (s, -hw + 0.4, h), (s, -hw, h - 0.4), (s, -hw, z0), (s, hw, z0), (s, hw, h - 0.4)])
    body.merge(outward(lib.loft(np.array(rings, float), cap0=True, cap1=True)))
    # lower console utility light on a gooseneck, left side [item 18]
    import interior
    neck = interior.smooth_path([(236.0, hw, CF + 8.2), (236.0, hw + 1.8, CF + 8.6), (234.6, hw + 2.6, CF + 11.8), (232.6, hw + 2.0, CF + 13.0)], 1.6, 5)
    stl.merge(lib.tube(neck, 0.22, 6)); frm.merge(lib.box((236.0, hw + 0.1, CF + 8.2), (1.4, 0.3, 1.4)))
    M, _ = lib.frame_to(neck[-1], np.array(neck[-1]) + (np.array(neck[-1]) - np.array(neck[-2])))
    blk.merge(lib.revolve([(0.3, -0.3), (0.45, 0.0), (0.75, 1.2), (0.75, 1.5), (0.6, 1.5), (0.55, 1.25), (0, 1.2)], n, M))
    # fire extinguisher in its bracket, left of the console [item 42]
    fx = (227.0, hw + 2.4, CF)
    red.merge(lib.revolve([(1.55, 0.3), (1.7, 0.6), (1.7, 8.4), (1.35, 9.5), (0.7, 10.1), (0.7, 10.8)], n, T(*fx)))
    blk.merge(lib.revolve([(0.85, 10.8), (0.85, 11.6), (0.5, 11.9), (0, 11.9)], n, T(*fx)))
    blk.merge(lib.box((fx[0] - 1.2, fx[1], fx[2] + 12.3), (3.4, 0.7, 0.5))); blk.merge(lib.cyl((fx[0] + 0.8, fx[1], fx[2] + 11.2), (fx[0] + 2.4, fx[1], fx[2] + 10.6), 0.3, 6))
    for z in (2.6, 7.2):
        dull.merge(lib.revolve([(1.78, z - 0.4), (1.82, z - 0.3), (1.82, z + 0.3), (1.78, z + 0.4)], n, T(*fx), cap0=False, cap1=False))
        dull.merge(lib.box((fx[0], fx[1] - 1.5, fx[2] + z), (1.0, 1.6, 0.8)))
    dull.merge(lib.box((fx[0], fx[1], fx[2] + 0.15), (4.0, 4.0, 0.3))); dull.merge(lib.box((fx[0], hw + 0.5, fx[2] + 5.0), (1.2, 0.5, 10.0)))


# ------------------------------------------------------------------ crew seat frame and tracks
COLL_K = 1.55                              # stick centre line off the console side / the seat's wing [EST]


def collective_bl(sg):
    """Both sticks are at the crew member's left: the pilot's between the console and the seat, the copilot's
    outboard of the seat by the door [TM 55-1520-237-23 fig 11-40 sheet 1, locators A and B]."""
    return -(CON_HW + COLL_K) if sg < 0 else SEAT_BL + 15.5


def _sleeve(p, d, r0, r1, L, n):
    """Fabric top panel: a cone of cloth round the stick, gathered under a cord at the small end [F11-40 sheet 2]."""
    M, _ = lib.frame_to(p, np.asarray(p) + np.asarray(d))
    prof = [(r0, 0.0), (r0 * 0.97, L * 0.12), (r1 + (r0 - r1) * 0.45, L * 0.55), (r1 + 0.1, L * 0.9), (r1 + 0.16, L * 0.94), (r1 + 0.1, L), (r1 - 0.12, L)]
    return lib.revolve(prof, n, M, cap0=False, cap1=False)


def collective_cover(ctx, sg, p0, g0):
    """Cover and boot over the collective's support [TM 55-1520-237-23 fig 11-40, both sheets]. Pilot: a box screwed to
    the side of the centre console, NO STEP on top, open at the front top corner where two fabric half panels and a
    conical top panel close it round the stick. Copilot: a taller box with a sloped front screwed to the floor and the
    rear bulkhead; on the slope a bottom panel under a retainer, a fabric centre panel and the conical top panel.
    The drawing gives no dimensions and no colours: every size here is scaled off the stick [EST]."""
    cov, fab, stl, wht = (Mesh() for _ in range(4)); n = ctx.n(18, 10); hi = ctx.lod == 0
    p0 = np.asarray(p0, float); d = np.asarray(g0, float) - p0; d /= np.linalg.norm(d); bl = p0[1]
    at = lambda s: p0 + d * ((s - p0[0]) / d[0])                    # point on the stick axis at a station
    if sg < 0:
        s0, s1, H = 235.2, 243.6, 5.8; y0 = -CON_HW; W = 2 * (abs(bl) - CON_HW) - 0.3; yc = y0 - W / 2; sm = 239.0
        cov.merge(lib.box(((sm + s1) / 2, yc, CF + H / 2), (s1 - sm, W, H)))                          # closed aft part, NO STEP on top
        cov.merge(lib.box(((s0 + sm) / 2, yc, CF + 0.3), (sm - s0, W, 0.6)))                          # sill under the opening
        cov.merge(lib.box(((s0 + sm) / 2, yc - W / 2 + 0.06, CF + H / 2), (sm - s0, 0.12, H)))        # outboard wall carries forward
        cov.merge(lib.box(((s0 + s1) / 2, y0 - 0.05, CF + H / 2 + 0.35), (s1 - s0 + 1.4, 0.1, H + 0.7)))   # flange on the console side
        for s in np.linspace(s0 + 0.3, s1 - 0.3, 4): stl.merge(screw((s, y0 - 0.1, CF + H + 0.4), (0, -1, 0), 0.17, 0.06))
        for s in (s0 - 0.4, s1 + 0.4):
            for z in (1.4, 4.2): stl.merge(screw((s, y0 - 0.1, CF + z), (0, -1, 0), 0.17, 0.06))
        # fabric: bottom half panel across the front, top half panel over the top, both cut round the stick
        e = at(s0 + 1.5); ring_n = 12
        fab.merge(lib.box((s0 + 0.05, yc + 0.03, CF + 0.6 + (e[2] - CF - 0.6) / 2 - 0.5), (0.1, W - 0.2, max(e[2] - CF - 1.6, 0.5))))
        fab.merge(lib.box(((s0 + 2.7 + sm) / 2, yc + 0.03, CF + H - 0.05), (sm - s0 - 2.7, W - 0.2, 0.1)))
        rect = [(s0 + 0.05, yc + sy * (W / 2 - 0.12), z) for sy, z in ((1, CF + 0.9), (-1, CF + 0.9))] + [(s0 + 3.4, yc - (W / 2 - 0.12), CF + H - 0.05), (s0 + 3.4, yc + (W / 2 - 0.12), CF + H - 0.05)]
        c = at(s0 + 1.2); M, _ = lib.frame_to(c, c + d)
        ra = np.array(lib.resample(np.array(rect + rect[:1], float), ring_n + 1)[:-1]); ctr = ra.mean(0)
        ang = lambda q: math.atan2(*(np.linalg.inv(M) @ np.append(q, 1.0))[[1, 0]])
        ra = ra[np.argsort([ang(q) for q in ra])]
        rb = np.array([(M @ np.array((1.3 * math.cos(a), 1.3 * math.sin(a), 0.6, 1.0)))[:3] for a in sorted(ang(q) for q in ra)])
        fab.merge(outward(lib.loft(np.array([ra, rb]), cap0=False, cap1=False)))
        fab.merge(_sleeve(c + d * 0.6, d, 1.3, 0.72, 3.6, n))
        if hi: wht.merge(lib.text_mesh('NO STEP', 0.6), T((sm + s1) / 2, yc, CF + H) @ lib.S(-1, 1, 1))
    else:
        W, H, s1, st, sf = 3.6, 8.2, C1 - 0.2, 240.0, 235.8
        side = np.array([(sf, CF), (s1, CF), (s1, CF + H), (st, CF + H)])
        cov.merge(outward(lib.prism(side, bl - W / 2, bl + W / 2, lib.plane_basis('side_l'))))
        cov.merge(lib.box(((sf - 0.9 + s1) / 2, bl, CF + 0.05), (s1 - sf + 0.9, W + 1.1, 0.1)))            # floor flange
        for s in (sf - 0.5, sf + 2.6, sf + 5.4, s1 - 1.4):
            for sy in (-1, 1): stl.merge(screw((s, bl + sy * (W / 2 + 0.3), CF + 0.1), (0, 0, 1), 0.17, 0.06))
        for sy in (-1, 1):                                                                                # tabs on to the rear bulkhead
            for z in (2.4, 6.2):
                cov.merge(lib.box((s1 + 0.05, bl + sy * (W / 2 + 0.5), CF + z), (0.1, 1.3, 1.5)))
                stl.merge(screw((s1, bl + sy * (W / 2 + 0.6), CF + z), (-1, 0, 0), 0.17, 0.06))
        v = np.array((st - sf, 0.0, H)); Ls = np.linalg.norm(v); v /= Ls; nr = np.array((-v[2], 0.0, v[0]))
        x = np.array((sf, bl, CF)) + v * (p0[2] - CF + (sf - p0[0]) * d[2] / d[0]) / (v[2] - v[0] * d[2] / d[0])   # stick through the slope
        Ms = np.eye(4); Ms[:3, 0] = (0, 1, 0); Ms[:3, 1] = v; Ms[:3, 2] = nr; Ms[:3, 3] = x
        fw, fl = W - 0.5, min(2 * (Ls - np.dot(x - (sf, bl, CF), v)) - 0.8, 5.6)
        fab.merge(lib.box((0, 0, 0.03), (fw - 0.2, fl - 0.2, 0.06)), Ms)                                  # bottom panel
        for sx in (-1, 1): cov.merge(lib.box((sx * (fw / 2 - 0.25), 0, 0.09), (0.5, fl, 0.1)), Ms)       # retainer
        cov.merge(lib.box((0, -(fl / 2 - 0.25), 0.09), (fw - 1.0, 0.5, 0.1)), Ms)
        for sx in (-1, 1):
            for y in (-(fl / 2 - 0.25), 0.0, fl / 2 - 0.25): stl.merge(screw((Ms @ np.array((sx * (fw / 2 - 0.25), y, 0.14, 1.0)))[:3], nr, 0.14, 0.05))
        ring_n = 12; rect = [(-(fw / 2 - 0.55), -(fl / 2 - 0.6), 0.1), (fw / 2 - 0.55, -(fl / 2 - 0.6), 0.1), (fw / 2 - 0.55, fl / 2 - 0.3, 0.1), (-(fw / 2 - 0.55), fl / 2 - 0.3, 0.1)]
        ra = np.array([(Ms @ np.append(q, 1.0))[:3] for q in lib.resample(np.array(rect + rect[:1], float), ring_n + 1)[:-1]])
        c = x + d * 2.4; M, _ = lib.frame_to(c, c + d)
        ang = lambda q: math.atan2(*(np.linalg.inv(M) @ np.append(q, 1.0))[[1, 0]])
        ra = ra[np.argsort([ang(q) for q in ra])]
        rb = np.array([(M @ np.array((1.45 * math.cos(a), 1.45 * math.sin(a), 0.0, 1.0)))[:3] for a in sorted(ang(q) for q in ra)])
        fab.merge(outward(lib.loft(np.array([ra, rb]), cap0=False, cap1=False)))                          # centre panel
        fab.merge(_sleeve(c, d, 1.45, 0.72, 3.0, n))
        if hi: wht.merge(lib.text_mesh('NO STEP', 0.7), T((st + s1) / 2, bl, CF + H) @ lib.R('z', 90.0) @ lib.S(-1, 1, 1))
    return cov, fab, stl, wht


def door_sill(ctx, wall_bl, out):
    """The cockpit door opening reaches below the floor [F6-1 side view]: close it with the floor-edge beam the crew
    step over, a ribbed tread on top."""
    od, dull, stl = out
    d = RC.COCKPIT_DOOR['poly']; s0, s1, z0 = d[0][0] - 1.0, d[1][0] + 0.8, d[0][1] - 1.5
    for sg in (1, -1):
        ss = np.linspace(s0, s1, 9); rings = []
        for s in ss:
            wt = wall_bl(s, CF) + 0.45; wb = wall_bl(s, z0) + 0.45
            rings.append([(s, sg * wt, CF - 0.05), (s, sg * (wt - 0.5), CF - 0.05), (s, sg * (wb - 0.5), z0), (s, sg * wb, z0)])
        od.merge(outward(lib.loft(np.array(rings, float), cap0=True, cap1=True)))
        prof = [(-3.2, 0.0), (-3.0, 0.14)]
        for i in range(7): prof += [(-2.8 + i * 0.42, 0.14), (-2.74 + i * 0.42, 0.26), (-2.62 + i * 0.42, 0.26), (-2.56 + i * 0.42, 0.14)]
        prof += [(0.2, 0.14), (0.25, 0.5), (0.4, 0.5), (0.4, -0.6), (0.25, -0.6), (0.2, 0.0)]
        rings = []
        for s in np.linspace(d[0][0] + 0.4, d[1][0] - 0.4, 7):
            w = wall_bl(s, CF) + 0.3
            rings.append([(s, sg * (w + x), CF + z) for x, z in prof])
        dull.merge(outward(lib.loft(np.array(rings, float), cap0=True, cap1=True)))
        for s in np.arange(d[0][0] + 2.5, d[1][0] - 1.0, 5.0):
            stl.merge(screw((s, sg * (wall_bl(s, CF) + 0.3 - 2.9), CF + 0.14), (0, 0, 1), 0.2, 0.06, 8))


def build(ctx, wall_bl, seat_out):
    hi = ctx.lod == 0; textured = 'cockpit_floor' in ctx.mats
    half = lambda s: float(wall_bl(s, CF)) + 0.4
    sts = np.linspace(C0, C1, 10)
    top = [(s, half(s)) for s in sts] + [(s, -half(s)) for s in sts[::-1]]
    o = ctx.part('airframe', 'cockpit_floor', outward(lib.prism(np.array(top), CF - 1.2, CF)), 'cockpit_floor' if textured else 'floor', 30)
    if textured: FL.planar_uv(o, C0, C1, CHALF)
    blk, frm, stl, dull, trk, body, grey, yel, red, rub, od = (Mesh() for _ in range(11))
    for sg in (1, -1):
        cy = sg * SEAT_BL
        pedals(ctx, cy, (blk, frm, stl, dull, rub))
        import crew_seat
        crew_seat.build(ctx, T(SEAT_STA, cy, CF) @ np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]]), seat_out + (stl, frm, dull, trk, blk), 1 if sg > 0 else -1)
        boot(ctx, CYC_STA, cy, 7.0, 7.0, (CYC_STA - 0.6, cy), 5.6, 0.95, (rub, dull, stl), (5, 5))     # cyclic boot and retainer [F11-34]
    console(ctx, (body, frm, stl, grey, blk, yel, red, dull))
    door_sill(ctx, wall_bl, (od, dull, stl))
    for name, m, mat in (('pedal_pads', blk, 'paint_black'), ('cockpit_frames', frm, 'frame_grey'), ('cockpit_floor_steel', stl, 'steel'),
                         ('cockpit_fittings', dull, 'alu_dull'), ('seat_tracks', trk, 'steel_dark'), ('lower_console', body, 'panel_face'),
                         ('console_side_panels', grey, 'frame_grey'), ('cockpit_floor_yellow', yel, 'paint_yellow'), ('fire_bottle', red, 'paint_red'),
                         ('control_boots', rub, 'fabric_boot' if 'fabric_boot' in ctx.mats else 'rubber'), ('cockpit_sills', od, 'paint_od_interior')):
        ctx.part('airframe', name, m, mat, 40)
