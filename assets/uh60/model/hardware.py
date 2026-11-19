"""Hardware: the fasteners and fittings, as real geometry.

LOD0 stands a head on every rivet and panel screw that skin.py paints on the body sides (same positions, so paint and
metal agree), and adds bolts to every fitting. LOD1 keeps the fittings and leaves the small heads to the normal map.
Door hardware belongs to its door's node, so it travels when the door opens.
Positions: door and window edges are the recipe's openings [F6-1]; what each fitting looks like is inferred from the
type's general arrangement [F2-1] and marked [INF] where it is a guess.
"""
import math
import numpy as np
import lib, recipe as RC, skin
from lib import Mesh, T, R, S


def surface(s, wl, sg):
    """Point and outward normal of the body skin at (STA, WL) on side sg (+1 left)."""
    f = lambda a, b: float(RC.body_surface_bl(a, b))
    bl = f(s, wl); fs = (f(s + 0.5, wl) - f(s - 0.5, wl)); fw = (f(s, wl + 0.5) - f(s, wl - 0.5))
    n = np.array((-fs, 1.0, -fw)); n /= np.linalg.norm(n)
    return np.array((s, sg * bl, wl)), n * np.array((1, sg, 1))


def instances(unit, pts, nrms):
    """Copies of a small mesh (unit, +Z up) standing on points along normals, built in one go."""
    U = unit.verts(); F = np.array(unit.f, dtype=object)
    P = np.asarray(pts, float); N = np.asarray(nrms, float)
    a = np.where(np.abs(N[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
    X = np.cross(a, N); X /= np.linalg.norm(X, axis=1, keepdims=True); Y = np.cross(N, X)
    V = P[:, None, :] + U[None, :, 0:1] * X[:, None, :] + U[None, :, 1:2] * Y[:, None, :] + U[None, :, 2:3] * N[:, None, :]
    m = Mesh(); k = len(U)
    faces = [tuple(int(i) + j * k for i in f) for j in range(len(P)) for f in unit.f]
    m.add(V.reshape(-1, 3), faces)
    return m


def skin_fasteners(ctx):
    from shapely.geometry import Polygon, Point
    P = skin.paint()
    holes = [Polygon(sp['poly']).buffer(0.6) for sp in (RC.CABIN_DOOR, RC.COCKPIT_DOOR, RC.GUNNER_WIN, RC.CHIN_WIN)]
    rivet = lib.revolve([(0.15, 0.0), (0.13, 0.04), (0.07, 0.062), (0, 0.066)], 6, cap0=False, cap1=False)
    screw = lib.revolve([(0.2, 0.0), (0.19, 0.05), (0.12, 0.075), (0.1, 0.045), (0, 0.04)], 8, cap0=False, cap1=False)
    for name, lst, unit, mat in (('skin_rivets', P.rivets, rivet, 'paint_od'), ('panel_screws', P.screws, screw, 'steel_dark')):
        pts = []; nrms = []
        for reg, s, wl in lst:
            if reg not in 'LR' or not (163.5 < s < 644.0): continue
            zb, zt, _ = skin.body_lines(s)
            if not (zb + 2.0 < wl < zt - 2.0): continue
            if any(h.contains(Point(s, wl)) for h in holes): continue
            p, n = surface(s, wl, 1 if reg == 'L' else -1)
            if abs(n[1]) < 0.35: continue
            pts.append(p - n * 0.005); nrms.append(n)
        if pts:
            ctx.part('airframe', name, instances(unit, pts, nrms), mat, 60)
            ctx.log(f'{name}: {len(pts)}')


def plate_on(s, wl, sg, w, h, t=0.12, lift=0.0):
    """A small plate lying on the skin, w along STA, h along WL."""
    p, n = surface(s, wl, sg)
    M = np.eye(4); x = np.array((1.0, 0, 0)); x -= n * x.dot(n); x /= np.linalg.norm(x); y = np.cross(n, x)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, n, p + n * lift
    return lib.prism(lib.rrect(w, h, min(w, h) * 0.22, 3), 0.0, t, M), M


def door_hardware(ctx):
    hi = ctx.lod == 0
    for sg, side in ((1, 'L'), (-1, 'R')):
        # ---- cockpit door: two hinges on the forward edge, lever handle aft, emergency jettison handle inside
        nd = f'cockpit_door_{side}'; stl, blk, yel, od = Mesh(), Mesh(), Mesh(), Mesh()
        for wl in (211.5, 229.0):
            pl, M = plate_on(208.2, wl, sg, 3.4, 2.6, 0.14); od.merge(pl)
            pl2, M2 = plate_on(205.6, wl, sg, 2.4, 2.6, 0.14); od.merge(pl2)
            p, n = surface(207.0, wl, sg)
            stl.merge(lib.cyl(p + n * 0.3 + (0, 0, -1.3), p + n * 0.3 + (0, 0, 1.3), 0.3, 10))
            for dx, MM in ((0.9, M), (-0.9, M), (0.0, M2)):
                for dy in (-0.8, 0.8):
                    stl.merge(lib.bolt((MM @ np.array((dx, dy, 0.14, 1)))[:3], MM[:3, 2], 0.19, washer=False))
        pl, M = plate_on(241.2, 229.5, sg, 5.6, 2.6, 0.1); od.merge(pl)
        stl.merge(lib.revolve([(0.6, 0), (0.6, 0.35), (0.3, 0.5), (0, 0.5)], 12), M @ T(1.6, 0, 0.1))
        blk.merge(lib.prism(lib.rrect(4.6, 1.0, 0.45, 3), 0.42, 0.72, M @ T(-0.4, 0, 0)))
        blk.merge(lib.cyl((M @ np.array((1.6, 0, 0.1, 1)))[:3], (M @ np.array((1.6, 0, 0.75, 1)))[:3], 0.34, 10))
        p, n = surface(236.0, 231.0, sg)                              # inside: jettison handle, yellow with black bands
        a = p - n * 3.2; yel.merge(lib.tube([a + (-2.5, 0, 0), a - n * 1.3 + (-2.5, 0, 0), a - n * 1.3 + (2.5, 0, 0), a + (2.5, 0, 0)], 0.3, 8))
        for dx in (-1.2, 0.0, 1.2): blk.merge(lib.cyl(a - n * 1.3 + (dx - 0.3, 0, 0), a - n * 1.3 + (dx + 0.3, 0, 0), 0.32, 8))
        for nm, m, mat in (('hinges', od, 'paint_od'), ('hardware', stl, 'steel'), ('handle', blk, 'paint_black'), ('jettison_handle', yel, 'paint_yellow')):
            ctx.part(nd, f'cockpit_door_{nm}', m, mat, 40)
        # ---- cabin door: paddle handle forward, upper rollers on the track, lower guide shoe, inside handle and latch
        nd = f'cabin_door_{side}'; stl, blk, yel, od = Mesh(), Mesh(), Mesh(), Mesh()
        pl, M = plate_on(313.5, 229.0, sg, 3.2, 6.0, 0.1); od.merge(pl)
        blk.merge(lib.prism(lib.rrect(1.3, 4.6, 0.5, 3), 0.35, 0.7, M))
        for dy in (-1.9, 1.9): stl.merge(lib.cyl((M @ np.array((0, dy, 0.1, 1)))[:3], (M @ np.array((0, dy, 0.45, 1)))[:3], 0.3, 8))
        if hi:
            for dx in (-1.2, 1.2):
                for dy in (-2.5, 2.5): stl.merge(lib.bolt((M @ np.array((dx, dy, 0.1, 1)))[:3], M[:3, 2], 0.16, washer=False))
        for s in (318.0, 366.0):
            p, n = surface(s, 261.0, sg); top = np.array((s, sg * (float(RC.body_surface_bl(s, 262.6)) + 0.9), 262.6))
            od.merge(lib.prism(lib.rrect(4.0, 2.4, 0.5, 3), -0.15, 0.15, lib.frame_to(p + n * 0.6 + (0, 0, -1.0), p + n * 1.6 + (0, 0, -1.0))[0] @ R('sta', 0)))
            stl.merge(lib.tube([p + n * 0.4 + (0, 0, -1.0), p + n * 1.2 + (0, 0, 0.6), top + (0, 0, -0.9)], 0.3, 8))
            stl.merge(lib.cyl(top + (-0.45, 0, -0.9), top + (0.45, 0, -0.9), 0.85, 12))
            pb, nb = surface(s, 208.6, sg)
            stl.merge(lib.box(pb + nb * 0.5 + (0, 0, -1.0), (2.6, 0.9, 1.8)))
            if hi:
                for dx in (-1.3, 1.3): stl.merge(lib.bolt(p + n * 0.75 + (dx, 0, -1.0), n, 0.19, washer=False))
        p, n = surface(312.5, 231.0, sg); a = p - n * 2.6                # inside handle
        yel.merge(lib.tube([a + (0, 0, -2.4), a - n * 1.4 + (0, 0, -2.4), a - n * 1.4 + (0, 0, 2.4), a + (0, 0, 2.4)], 0.3, 8))
        for nm, m, mat in (('fittings', od, 'paint_od'), ('hardware', stl, 'steel'), ('handle', blk, 'paint_black'), ('inside_handle', yel, 'paint_yellow')):
            ctx.part(nd, f'cabin_door_{nm}', m, mat, 40)


def nacelle_point(s, wl, sg):
    """Point and normal on the outboard face of an engine nacelle (superellipse of airframe.NACELLE)."""
    import airframe
    d = np.array(airframe.NACELLE); c_bl, c_wl, hw, hh, n = (float(np.interp(s, d[:, 0], d[:, k])) for k in range(1, 6))
    f = lambda w: c_bl + hw * max(1e-3, 1 - abs((w - c_wl) / hh) ** n) ** (1 / n)
    bl = f(wl); fw = f(wl + 0.4) - f(wl - 0.4)
    nn = np.array((0.0, 0.8, -fw)); nn /= np.linalg.norm(nn)
    return np.array((s, sg * bl, wl)), nn * np.array((1, sg, 1))


def fittings(ctx):
    hi = ctx.lod == 0
    stl, blk, od, yel, wire = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    red, grn = Mesh(), Mesh()
    for sg in (1, -1):
        # cowl latches along the lower edge of each engine cowl: flush plate, trigger, two screws
        for s in (360.0, 374.0, 390.0, 404.0):
            p, n = nacelle_point(s, 268.9, sg); M, _ = lib.frame_to(p, p + n)
            od.merge(lib.prism(lib.rrect(1.5, 2.4, 0.3, 3), 0.0, 0.12, M)); stl.merge(lib.prism(lib.rrect(0.7, 1.1, 0.2, 2), 0.12, 0.2, M @ T(0, 0.3, 0)))
            if hi:
                for dy in (-0.9, 0.95): stl.merge(lib.revolve([(0.13, 0.12), (0.11, 0.17), (0, 0.18)], 6, M @ T(0, dy, 0), cap0=False, cap1=False))
        # hand holds: one above each cockpit door, one on the cabin roof edge by the steps
        for (s0, s1, wl) in ((222.0, 232.0, 266.0), (396.0, 408.0, 259.0)):
            p0, n0 = surface(s0, wl, sg); p1, n1 = surface(s1, wl, sg)
            blk.merge(lib.tube(lib_path([p0, p0 + n0 * 1.7, p1 + n1 * 1.7, p1]), 0.36, 8))
            for p, n in ((p0, n0), (p1, n1)): stl.merge(lib.revolve([(0.8, 0), (0.8, 0.12), (0.45, 0.2)], 10, lib.frame_to(p, p + n)[0], cap0=False, cap1=False))
        # gunner's window: centre post and latch (the window slides in two panes)
        p, n = surface(277.0, 247.0, sg)
        od.merge(lib.tube([surface(277.0, w_, sg)[0] + surface(277.0, w_, sg)[1] * 0.05 for w_ in np.linspace(233.6, 260.4, 7)], 0.55, 8))
        blk.merge(lib.box(p - n * 1.3 + (2.0, 0, 0), (2.4, 0.8, 1.0)))
        # position lights on the stabilator tips? no: the type carries them on the main gear fairings [INF placement]
        p = np.array((RC.STA_MAIN_GEAR + 2.0, sg * (RC.BL_MAIN_GEAR - 9.0), 214.5))
        (red if sg > 0 else grn).merge(lib.revolve([(1.1, 0), (1.0, 0.9), (0.6, 1.5), (0, 1.7)], 10, lib.frame_to(p, p + (0, sg, 0.2))[0], cap0=False, cap1=False))
        stl.merge(lib.revolve([(1.35, -0.2), (1.35, 0.1), (1.1, 0.1)], 10, lib.frame_to(p, p + (0, sg, 0.2))[0], cap0=False, cap1=False))
        # static dischargers on the stabilator trailing edge
        stab = np.array(RC.STAB)
        for b in (30.0, 55.0, 80.0):
            te = float(np.interp(b, stab[:, 0], stab[:, 2]))
            wire.merge(lib.tube([(te - 0.3, sg * b, RC.WL_STAB), (te + 6.0, sg * b, RC.WL_STAB - 0.4)], [0.12, 0.05], 5))
        # tie-down / mooring rings under the body sides
        for s in (262.0, 404.0):
            p, n = surface(s, 204.5, sg)
            stl.merge(lib.revolve([(0.9, 0), (0.9, 0.15), (0.5, 0.25)], 10, lib.frame_to(p, p + n)[0], cap0=False, cap1=False))
            stl.merge(lib.tube([p + n * 0.1 + (-0.8, 0, 0), p + n * 1.3 + (-0.6, 0, -0.5), p + n * 1.3 + (0.6, 0, -0.5), p + n * 0.1 + (0.8, 0, 0)], 0.16, 6))
    # cargo hook in its well under the cabin [F2-1]: beam, load arm, keeper
    c = np.array((343.0, 0.0, 199.9))
    stl.merge(lib.box(c + (0, 0, -1.0), (7.0, 3.2, 2.2))); stl.merge(lib.cyl(c + (0, -2.2, -1.0), c + (0, 2.2, -1.0), 0.6, 10))
    stl.merge(lib.tube([c + (2.4, 0, -2.0), c + (2.8, 0, -4.6), c + (1.4, 0, -6.2), c + (-0.8, 0, -6.0), c + (-1.6, 0, -4.4)], [0.75, 0.75, 0.7, 0.6, 0.4], 10))
    yel.merge(lib.box(c + (-1.4, 0, -3.0), (0.5, 0.9, 2.6)))
    if hi:
        for dx in (-2.8, 2.8):
            for dy in (-1.1, 1.1): stl.merge(lib.bolt(c + (dx, dy, -2.1), (0, 0, -1), 0.3))
    # nose: avionics door hinge line (three hinges each side) and two quarter-turn latches at the bottom
    for sg in (1, -1):
        for s in (174.0, 185.0, 196.0):
            p, n = surface(s, 235.6 if s > 180 else 233.0, sg)
            od.merge(lib.cyl(p + n * 0.22 + (-1.1, 0, 0), p + n * 0.22 + (1.1, 0, 0), 0.26, 8))
        for s in (176.0, 194.0):
            p, n = surface(s, 210.6, sg)
            stl.merge(lib.revolve([(0.55, 0), (0.5, 0.1), (0, 0.1)], 12, lib.frame_to(p, p + n)[0], cap0=False, cap1=False))
            blk.merge(lib.box(p + n * 0.1, (0.9, 0.12, 0.14)))
    for nm, m, mat in (('latches_hinges', od, 'paint_od'), ('fittings_steel', stl, 'steel'), ('handholds', blk, 'paint_black'), ('hook_keeper', yel, 'paint_yellow'),
                       ('static_wicks', wire, 'wire'), ('position_light_left', red, 'lens_red'), ('position_light_right', grn, 'lens_green')):
        ctx.part('airframe', nm, m, mat, 40)


def lib_path(pts):
    import interior
    return interior.smooth_path(pts, 0.9, 4)


def build(ctx):
    door_hardware(ctx)
    fittings(ctx)
    if ctx.lod == 0 and not ctx.fast:
        skin_fasteners(ctx)
