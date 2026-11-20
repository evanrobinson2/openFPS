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
SEAT_STA, SEAT_BL = 232.5, 21.0
CYC_STA = 222.0
PED_STA = 204.0
CON_HW = 8.6
CON_TOP = [(212.0, 226.5), (218.0, 228.0), (224.0, 229.5), (235.0, 226.25), (246.0, 223.0)]   # (STA, WL) of the console top
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
        covers.append((213.6, 218.6, b[0], b[1]))                        # flight control access cover ahead of the cyclic
        b2 = sorted((sg * 31.0, sg * 41.0)); covers.append((236.0, 245.0, b2[0], b2[1]))
        plates.append((205.2, 213.0, cy - 8.8, cy + 8.8))                # heel plate under the pedals
        wear += [(209.0, cy, 6.0, 8.0, 255), (226.0, sg * 38.0, 12.0, 7.0, 210), (224.0, sg * 11.5, 16.0, 4.0, 140)]
        pans.append(circle(CYC_STA, cy, 3.3))
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
def pedals(ctx, cy, out):
    blk, frm, stl, dull = out; n = ctx.n(10, 7)
    B = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])     # pad local: x = BL, y = up the pad, z = toward the pilot
    for dy in (-4.6, 4.6):
        y0 = cy + dy
        Mp = T(PED_STA, y0, CF + 8.2) @ R('bl', -22.0) @ B
        if (Mp @ np.array((0, 0, 1.0, 0)))[2] < 0: Mp = T(PED_STA, y0, CF + 8.2) @ R('bl', 22.0) @ B
        pad = Mesh()
        pad.merge(lib.prism(lib.rrect(4.4, 5.9, 0.9, 3), -0.32, 0.0))
        for sx in (-1, 1): pad.merge(lib.box((sx * 2.02, 0, 0.1), (0.24, 4.3, 0.26)))                 # side cheeks keep the boot on
        pad.merge(lib.box((0, 2.72, 0.14), (3.2, 0.3, 0.34)))                                         # toe lip
        for yy in np.linspace(-2.3, 2.1, 7): pad.merge(lib.box((0, yy, 0.06), (3.55, 0.3, 0.14)))     # ribs
        pad.merge(lib.box((0, -0.3, -0.75), (1.7, 2.6, 0.9)))                                         # boss on the back
        blk.merge(pad, Mp)
        P = lambda x, y, z: (Mp @ np.array((x, y, z, 1.0)))[:3]
        stl.merge(lib.cyl(P(-2.45, -3.0, -0.4), P(2.45, -3.0, -0.4), 0.3, n))                         # toe-brake hinge pin
        for sx in (-1, 1): frm.merge(lib.cyl(P(sx * 1.9, -3.0, -0.4), P(sx * 1.9, -1.6, -0.5), 0.34, 6))
        foot = np.array((PED_STA - 3.6, y0, CF + 1.5))
        arm = [P(0, -3.0, -0.45), np.array((PED_STA - 1.0, y0, CF + 3.4)), foot]
        import interior
        frm.merge(lib.tube(interior.smooth_path(arm, 2.2), 0.52, n))
        # brake master cylinder from the back of the pad down to the arm
        a = P(0, 1.3, -1.1); b = np.array((PED_STA - 2.2, y0, CF + 2.6)); d = b - a
        dull.merge(lib.cyl(a, a + d * 0.58, 0.46, n)); stl.merge(lib.cyl(a + d * 0.58, b, 0.16, 6))
        dull.merge(lib.cyl(a + d * 0.52, a + d * 0.6, 0.56, n))
        # pivot bracket: two lugs on a base plate, bolted to the floor
        for sy in (-0.82, 0.82):
            lug = [(foot[0] - 1.5, CF), (foot[0] + 1.5, CF), (foot[0] + 0.7, CF + 2.2), (foot[0] - 0.7, CF + 2.2)]
            frm.merge(outward(lib.prism(np.array(lug), y0 + sy - 0.13, y0 + sy + 0.13, lib.plane_basis('side_l'))))
        frm.merge(lib.box((foot[0], y0, CF + 0.07), (3.8, 3.0, 0.14)))
        for sx in (-1.5, 1.5):
            for sy in (-1.15, 1.15): stl.merge(screw((foot[0] + sx, y0 + sy, CF + 0.14), (0, 0, 1), 0.2, 0.12))
    # torque tube joining the pair, and the pedal adjuster between them
    frm.merge(lib.cyl((PED_STA - 3.6, cy - 6.0, CF + 1.5), (PED_STA - 3.6, cy + 6.0, CF + 1.5), 0.42, n))
    for sy in (-6.0, 6.0): stl.merge(lib.cyl((PED_STA - 3.6, cy + sy - 0.2, CF + 1.5), (PED_STA - 3.6, cy + sy + 0.2, CF + 1.5), 0.62, n))
    frm.merge(lib.prism(lib.rrect(2.6, 2.2, 0.4, 3), CF, CF + 2.3, T(PED_STA - 1.4, cy, 0)))
    stem0 = np.array((PED_STA - 0.9, cy, CF + 2.2)); stem1 = stem0 + (1.5, 0, 1.3)
    stl.merge(lib.cyl(stem0, stem1, 0.2, 6))
    M, _ = lib.frame_to(stem1, stem1 + (1.5, 0, 1.3))
    blk.merge(lib.revolve([(0.5, 0), (0.95, 0.15), (0.95, 0.5), (0.6, 0.7), (0, 0.7)], n, M))


# ------------------------------------------------------------------ lower console
def console(ctx, out):
    body, frm, stl, grey, blk, yel, red, dull = out; hi = ctx.lod == 0; n = ctx.n(12, 8); hw = CON_HW
    rings = []
    for s, h in CON_TOP:
        rings.append([(s, hw - 0.5, h), (s, -hw + 0.5, h), (s, -hw, h - 0.5), (s, -hw, CF), (s, hw, CF), (s, hw, h - 0.5)])
    body.merge(outward(lib.loft(np.array(rings, float), cap0=True, cap1=True)))
    # plinth, bolted down
    for sg in (1, -1):
        frm.merge(lib.box((229.0, sg * (hw + 0.35), CF + 0.75), (34.6, 0.7, 1.5)))
        for s in np.arange(214.0, 246.0, 4.0): stl.merge(screw((s, sg * (hw + 0.7), CF + 0.75), (0, sg, 0), 0.2, 0.1))
        # side access panels with quarter-turn fasteners
        for (s0, s1, z0, z1) in ((214.0, 226.5, CF + 2.6, CF + 9.6), (228.5, 244.5, CF + 2.6, CF + 6.4)):
            grey.merge(lib.prism(lib.rrect(s1 - s0, z1 - z0, 0.8, 3), sg * hw if sg > 0 else -hw - 0.07, hw + 0.07 if sg > 0 else -hw,
                                 lib.plane_basis('side_l') @ T((s0 + s1) / 2, (z0 + z1) / 2, 0)))
            pts = [(s0 + 0.7, z0 + 0.7), (s0 + 0.7, z1 - 0.7), (s1 - 0.7, z0 + 0.7), (s1 - 0.7, z1 - 0.7), ((s0 + s1) / 2, z0 + 0.7), ((s0 + s1) / 2, z1 - 0.7)]
            for (s, z) in pts: stl.merge(screw((s, sg * (hw + 0.07), z), (0, sg, 0), 0.24, 0.06, 8))
    frm.merge(lib.box((246.3, 0, CF + 0.75), (0.7, 2 * hw + 1.4, 1.5)))
    # battery / battery utility bus circuit breaker panel on the aft face [F2-4 item 41]
    grey.merge(lib.box((246.08, 0, CF + 4.4), (0.16, 13.0, 4.6)))
    for row, z in enumerate((CF + 5.4, CF + 3.4)):
        for k in range(7):
            p = (246.16, -5.4 + k * 1.8, z)
            blk.merge(lib.revolve([(0.36, 0), (0.36, 0.12), (0.24, 0.14), (0.24, 0.5), (0, 0.5)], 8, lib.frame_to(p, (247.0, p[1], z))[0], cap0=False))
    for (y, z) in ((-6.1, CF + 2.5), (6.1, CF + 2.5), (-6.1, CF + 6.3), (6.1, CF + 6.3)): stl.merge(screw((246.16, y, z), (1, 0, 0), 0.2, 0.06))
    # parking brake lever at the right aft corner [item 16]
    a = np.array((241.5, -hw - 0.1, CF + 5.2)); b = a + (2.2, -0.9, 4.4)
    stl.merge(lib.cyl(a, b, 0.2, 6)); frm.merge(lib.box(a, (1.6, 0.5, 1.8)))
    yel.merge(lib.cyl(b + (0, -1.3, 0), b + (0, 1.3, 0), 0.38, n))
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


def console_rails(Mc, L, out):
    """Mounting rails the control heads fasten to, along the sloped top (Mc: interior's console-top frame)."""
    frm, stl = out
    for y, w in ((-7.55, 0.9), (0.0, 1.9), (7.55, 0.9)):
        frm.merge(lib.box((L / 2, y, 0.05), (L - 0.3, w, 0.1)), Mc)
        for x in np.arange(0.9, L - 0.5, 1.5):
            stl.merge(lib.revolve([(0.13, 0.1), (0.1, 0.14), (0, 0.14)], 6, cap0=False, cap1=False), Mc @ T(x, y + (0.6 if w > 1 else 0.0), 0))
            if w > 1: stl.merge(lib.revolve([(0.13, 0.1), (0.1, 0.14), (0, 0.14)], 6, cap0=False, cap1=False), Mc @ T(x, y - 0.6, 0))


# ------------------------------------------------------------------ crew seat frame and tracks
def seat_mount(ctx, M, out):
    """Tracks bolted to the floor, a carriage on four roller blocks, two guide tubes the bucket rides down in a
    crash, a diagonal energy attenuator each side. Local: x forward, y to the occupant's left, z up from the floor."""
    frm, trk, stl, dull, blk = out; n = ctx.n(12, 8); hi = ctx.lod == 0
    prof = [(-0.85, 0.0), (0.85, 0.0), (0.85, 0.85), (0.3, 0.85), (0.3, 0.5), (-0.3, 0.5), (-0.3, 0.85), (-0.85, 0.85)]
    for sy in (1, -1):
        y = sy * 7.0
        rings = [[(x, y + py, 0.1 + pz) for py, pz in prof] for x in (-15.5, 9.5)]
        trk.merge(outward(lib.loft(np.array(rings, float), cap0=True, cap1=True)), M)
        trk.merge(lib.box((-3.0, y, 0.05), (26.4, 3.1, 0.1)), M)
        for x in np.arange(-15.0, 9.6, 2.7):
            for e in (-1.22, 1.22): stl.merge(screw((x, y + e, 0.1), (0, 0, 1), 0.2, 0.13), M)
        for x in (-15.2, 9.2): dull.merge(lib.box((x, y, 0.75), (0.6, 1.9, 1.3)), M)
        for x in (-12.0, 6.0):                                                        # roller blocks
            dull.merge(outward(lib.prism(lib.rrect(3.0, 2.3, 0.45, 3), 0.75, 2.2, T(x, y, 0))), M)
            stl.merge(lib.cyl((x, y - 1.3, 1.5), (x, y + 1.3, 1.5), 0.3, 8), M)
        frm.merge(lib.tube([(-12.0, y, 2.5), (6.0, y, 2.5)], 0.5, n), M)
        g0 = np.array((-12.0, y, 2.2)); g1 = np.array((-12.5, y, 9.0)); g2 = np.array((-13.6, y, PAN_Z + 22.5))
        frm.merge(lib.tube([g0, g1, g2], 0.8, n), M)
        dull.merge(lib.revolve([(0.86, 0), (0.86, 0.5), (0.5, 0.8), (0, 0.8)], n, lib.frame_to(g2, g2 + (g2 - g1))[0]), M)
        for t in (0.22, 0.72):                                                       # bucket carriers sliding on the guide tube
            c = g1 + (g2 - g1) * t; u = (g2 - g1) / np.linalg.norm(g2 - g1)
            dull.merge(lib.cyl(c - u * 1.1, c + u * 1.1, 1.14, n), M)
            dull.merge(lib.box(c + (1.3, -sy * 0.2, 0), (2.4, 1.3, 1.6)), M)
            stl.merge(lib.cyl(c + (0.6, -0.9, 0), c + (0.6, 0.9, 0), 0.22, 6), M)
        # diagonal energy attenuator, outboard of the armour wing
        a = np.array((6.0, sy * 10.6, 2.6)); b = np.array((-13.2, sy * 12.2, PAN_Z + 19.0)); d = b - a
        frm.merge(lib.cyl(a, b, 0.48, n), M); dull.merge(lib.cyl(a + d * 0.06, a + d * 0.3, 0.86, n), M)
        dull.merge(lib.cyl(a + d * 0.3, a + d * 0.33, 0.62, n), M)
        for p in (a, b): stl.merge(lib.cyl(p - (0, 0.75, 0), p + (0, 0.75, 0), 0.3, 8), M)
        for x, s in ((8.6, 1), (8.6, -1)):                                           # height and fore-aft adjust levers under the pan
            pass
    frm.merge(lib.tube([(6.0, -11.3, 2.6), (6.0, 11.3, 2.6)], 0.55, n), M)
    frm.merge(lib.tube([(-12.1, -7.0, 3.4), (-12.1, 7.0, 3.4)], 0.55, n), M)
    frm.merge(lib.tube([(-13.3, -12.9, PAN_Z + 19.4), (-13.3, 12.9, PAN_Z + 19.4)], 0.6, n), M)
    for sy in (1, -1):
        p0 = np.array((7.2, sy * 5.5, PAN_Z - 3.1)); p1 = p0 + (3.6, sy * 0.6, -0.3)
        stl.merge(lib.cyl(p0, p1, 0.2, 6), M)
        blk.merge(lib.revolve([(0.3, 0), (0.5, 0.3), (0.5, 1.1), (0.3, 1.4), (0, 1.4)], 8, lib.frame_to(p1, p1 + (p1 - p0))[0]), M)
    # under-pan beam the bucket sits on
    frm.merge(lib.box((0.0, 0.0, PAN_Z - 3.0), (3.0, 16.0, 0.8)), M)


def collective_mount(pivot, out):
    """Clevis bracket for the collective's torque tube, bolted to the floor."""
    frm, stl = out; s, bl, wl = pivot
    for sy in (-1.0, 1.0):
        lug = [(s - 1.6, CF), (s + 1.6, CF), (s + 0.8, wl + 0.9), (s - 0.8, wl + 0.9)]
        frm.merge(outward(lib.prism(np.array(lug), bl + sy - 0.14, bl + sy + 0.14, lib.plane_basis('side_l'))))
    frm.merge(lib.box((s, bl, CF + 0.08), (4.2, 3.4, 0.16)))
    stl.merge(lib.cyl((s, bl - 1.35, wl), (s, bl + 1.35, wl), 0.34, 8))
    for sx in (-1.6, 1.6):
        for sy in (-1.3, 1.3): stl.merge(screw((s + sx, bl + sy, CF + 0.16), (0, 0, 1), 0.2, 0.12))


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


def build(ctx, wall_bl, Mc, Lc):
    hi = ctx.lod == 0; textured = 'cockpit_floor' in ctx.mats
    half = lambda s: float(wall_bl(s, CF)) + 0.4
    sts = np.linspace(C0, C1, 10)
    top = [(s, half(s)) for s in sts] + [(s, -half(s)) for s in sts[::-1]]
    o = ctx.part('airframe', 'cockpit_floor', outward(lib.prism(np.array(top), CF - 1.2, CF)), 'cockpit_floor' if textured else 'floor', 30)
    if textured: FL.planar_uv(o, C0, C1, CHALF)
    blk, frm, stl, dull, trk, body, grey, yel, red, rub, od = (Mesh() for _ in range(11))
    for sg in (1, -1):
        cy = sg * SEAT_BL
        pedals(ctx, cy, (blk, frm, stl, dull))
        seat_mount(ctx, T(SEAT_STA, cy, CF) @ np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]]), (frm, trk, stl, dull, blk))
        # cyclic boot: retaining ring screwed to the floor, convoluted boot up the stick
        dull.merge(lib.revolve([(3.25, 0.0), (3.25, 0.12), (2.7, 0.16), (2.7, 0.0)], ctx.n(20, 12), T(CYC_STA, cy, CF), cap0=False, cap1=False))
        for k in range(8):
            a = k * math.pi / 4 + 0.39; stl.merge(screw((CYC_STA + 2.98 * math.cos(a), cy + 2.98 * math.sin(a), CF + 0.13), (0, 0, 1), 0.15, 0.06))
        rub.merge(bellows((CYC_STA, cy, CF + 0.12), (CYC_STA, cy, CF + 5.2), 2.65, 0.95, 5, ctx.n(18, 12)))
    console(ctx, (body, frm, stl, grey, blk, yel, red, dull))
    console_rails(Mc, Lc, (frm, stl))
    door_sill(ctx, wall_bl, (od, dull, stl))
    for name, m, mat in (('pedal_pads', blk, 'paint_black'), ('cockpit_frames', frm, 'frame_grey'), ('cockpit_floor_steel', stl, 'steel'),
                         ('cockpit_fittings', dull, 'alu_dull'), ('seat_tracks', trk, 'steel_dark'), ('lower_console', body, 'panel_face'),
                         ('console_side_panels', grey, 'frame_grey'), ('cockpit_floor_yellow', yel, 'paint_yellow'), ('fire_bottle', red, 'paint_red'),
                         ('cyclic_boots', rub, 'rubber'), ('cockpit_sills', od, 'paint_od_interior')):
        ctx.part('airframe', name, m, mat, 40)
