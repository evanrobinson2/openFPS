"""Pilot's and copilot's armoured crashworthy seat, from the maintenance manual's drawings.

Source: TM 1-1520-237-23 (17 April 2006), work package 0231 00:
  figure 28 sheet 1  'seat looking to front' rear view: widths and heights of the bucket, headrest, guide tubes,
                     attenuators, yoke, stowage panel band, crossed lower braces, base tube and track fittings
  figures 7, 9, 24   whole-seat perspectives: bucket with cushions and five-strap harness, headrest pad, guide
                     tubes with caps, diagonal struts down to the front track fittings, track tubes
  figure 14          the bare seat bucket: pan with side walls sweeping up into a flanged back
  figure 27          armoured wings on the outboard side: stationary wing, movable wing, upper and lower tubes

Scale: the rear view carries routing dimensions (7 in, 5-3/4 in, 3 in, 4-1/16 in) that give 16 to 22 px per inch
on a 3.6x render, so the view is read at 18 px per inch [fitted, about +/-15 %]. Everything along the seat's
fore-aft axis comes from the perspectives and is estimated [EST]. Not built: the three openings at the top of
the bare bucket (behind the headrest), the frangible strut, inertia reel, ICS cables and the vertical adjust spring.
Local frame: x forward, y to the occupant's left, z up from the cockpit floor.
"""
import math
import numpy as np
import lib
from lib import Mesh, T

PAN_Z = 10.5            # bucket underside above the floor at mid travel [F28 rear view]
BACK_LEAN = 10.0        # deg [EST from figures 7 and 14]
XZ = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])    # sketch (x, z) extruded along y


def _u(hw, h, t=0.45, r=1.4, k=3):
    """U section: a = across the seat, b = up the wall. Outer then inner outline (closed ring)."""
    out = [(-hw, h)]
    for i in range(k + 1):
        a = math.pi + (math.pi / 2) * i / k; out.append((-hw + r + r * math.cos(a), r + r * math.sin(a)))
    for i in range(k + 1):
        a = 1.5 * math.pi + (math.pi / 2) * i / k; out.append((hw - r + r * math.cos(a), r + r * math.sin(a)))
    out.append((hw, h))
    ri = max(0.2, r - t); inn = [(hw - t, h)]
    for i in range(k + 1):
        a = 2 * math.pi - (math.pi / 2) * i / k; inn.append((hw - t - ri + ri * math.cos(a), t + ri + ri * math.sin(a)))
    for i in range(k + 1):
        a = 1.5 * math.pi - (math.pi / 2) * i / k; inn.append((-hw + t + ri + ri * math.cos(a), t + ri + ri * math.sin(a)))
    inn.append((-hw + t, h))
    return out + inn


def bucket(ctx):
    """One shell swept from the front of the pan, round the corner and up the back [F14, widths F28]."""
    from cockpit_floor import outward
    # (distance along the spine, half width, wall height)
    st = [(0.0, 9.3, 1.6), (0.6, 9.5, 2.4), (5.0, 10.2, 4.2), (10.0, 10.8, 6.6), (14.0, 10.9, 7.6),          # pan, front to rear
          (15.7, 10.9, 7.9), (17.4, 10.9, 7.8), (19.0, 10.9, 7.3),                                             # the corner
          (25.0, 10.6, 5.6), (32.0, 9.4, 4.0), (39.0, 7.6, 2.6), (44.5, 7.0, 1.8), (46.5, 6.8, 1.4)]           # up the back, top 40.8 in above the floor [F28]
    rings = []; p = np.array((8.0, 0.0, PAN_Z)); s_prev = 0.0; phi_end = math.radians(90.0 - BACK_LEAN)
    for (s, hw, h) in st:
        phi0 = 0.0 if s_prev <= 14.0 else (phi_end if s_prev >= 19.0 else phi_end * (s_prev - 14.0) / 5.0)
        phi1 = 0.0 if s <= 14.0 else (phi_end if s >= 19.0 else phi_end * (s - 14.0) / 5.0)
        pm = (phi0 + phi1) / 2; p = p + np.array((-math.cos(pm), 0, math.sin(pm))) * (s - s_prev); s_prev = s
        n = np.array((math.sin(phi1), 0, math.cos(phi1)))
        rings.append([p + np.array((0, a, 0)) + n * b for a, b in _u(hw, h)])
    return outward(lib.loft(np.array(rings), cap0=True, cap1=True)), rings


def build(ctx, M, out, outboard):
    """outboard: +1 if the seat's left side is toward the door (copilot), -1 for the pilot."""
    from cockpit_floor import outward, screw
    import interior
    arm, fab, belt, st, frm, dull, trk, blk = out; n = ctx.n(12, 8)
    shell, rings = bucket(ctx); arm.merge(shell, M)
    lean = math.radians(BACK_LEAN); up = np.array((-math.sin(lean), 0, math.cos(lean))); fw = np.array((math.cos(lean), 0, math.sin(lean)))
    c0 = np.array(rings[7]).mean(axis=0)                           # top of the corner: the back starts here
    back = lambda s, f=0.0, y=0.0: c0 + up * s + fw * (f - 3.2) + np.array((0, y, 0))
    Mb = np.eye(4); Mb[:3, 0] = (0, 1, 0); Mb[:3, 1] = up; Mb[:3, 2] = fw
    # cushions [F7, F9]
    cush = Mesh(); cush.merge(lib.prism(lib.rrect(16.5, 16.0, 2.5, 4), PAN_Z + 0.45, PAN_Z + 2.6), T(0.6, 0, 0)); fab.merge(cush, M)
    bc = Mb.copy(); bc[:3, 3] = back(13.5, 0.5); bk = Mesh(); bk.merge(lib.prism(lib.rrect(15.0, 23.0, 2.5, 4), 0.0, 1.7), bc); fab.merge(outward(bk), M)
    hr = Mb.copy(); hr[:3, 3] = back(30.3, 0.3); hd = Mesh(); hd.merge(lib.prism(lib.rrect(10.4, 5.2, 1.2, 4), -1.2, 2.2), hr); fab.merge(outward(hd), M)    # headrest pad, 10.4 in wide [F28]
    # harness: two shoulder straps, two lap straps and a crotch strap into a rotary buckle [F7]
    bp = np.array((2.5, 0.0, PAN_Z + 4.6))
    for sy in (1, -1):
        sh = [back(27.4, -0.3, sy * 2.6), back(27.2, 1.3, sy * 2.6), back(18.0, 2.6, sy * 3.0), back(8.0, 3.2, sy * 2.6), bp + (-1.0, sy * 0.9, 0.3)]
        belt.merge(interior.ribbon(interior.smooth_path(sh, 2.0), 1.9, 0.12, (0, 1, 0)), M)
        ad = Mb.copy(); ad[:3, 3] = back(18.0, 2.75, sy * 3.0); st.merge(lib.box((0, 0, 0), (2.4, 1.5, 0.3), ad), M)                                           # strap adjuster
        lap = [np.array((-4.5, sy * 10.0, PAN_Z + 3.4)), np.array((-2.0, sy * 6.0, PAN_Z + 4.4)), bp + (-0.3, sy * 1.0, 0)]
        belt.merge(interior.ribbon(lap, 1.9, 0.12, (1, 0, 0)), M)
    belt.merge(interior.ribbon([np.array((7.6, 0, PAN_Z + 2.4)), np.array((5.0, 0, PAN_Z + 3.4)), bp + (0.9, 0, 0)], 1.9, 0.12, (0, 1, 0)), M)
    st.merge(lib.revolve([(1.45, 0), (1.45, 0.5), (0.8, 0.65), (0.8, 1.0), (0, 1.0)], n, lib.frame_to(bp - (0, 0, 0.3), bp + (0.25, 0, 0.9))[0]), M)
    # frame behind the bucket [F28 rear view for y and z; F7 for x]
    xg = -16.2
    for sy in (1, -1):
        y = sy * 9.4
        frm.merge(lib.cyl((xg, y, 2.2), (xg, y, 43.2), 0.75, n), M)                                              # up-and-down guide tube
        dull.merge(lib.revolve([(0.9, 0), (0.9, 1.3), (0.6, 1.6), (0, 1.6)], n, T(xg, y, 43.2)), M)             # its cap
        for z in (37.5, 22.5): dull.merge(lib.cyl((xg, y, z - 1.0), (xg, y, z + 1.0), 1.05, n), M)               # mounts sliding on it
        ya = sy * 5.0
        frm.merge(lib.cyl((xg + 0.9, ya, 28.3), (xg + 0.9, ya, 38.9), 0.85, n), M)                              # attenuator [F9, F28]
        st.merge(lib.cyl((xg + 0.9, ya, 38.9), (xg + 0.9, ya, 41.0), 0.3, 8), M)
        st.merge(lib.cyl((xg + 0.9, ya, 26.6), (xg + 0.9, ya, 28.3), 0.3, 8), M)
        # diagonal strut from the upper frame down to the front track fitting [F7, F24]
        yt = sy * 11.6; a = np.array((xg + 0.4, yt, 23.0)); b = np.array((8.2, yt, 2.4)); d = (b - a) / np.linalg.norm(b - a)
        Ms = np.eye(4); Ms[:3, 0] = np.cross((0, 1, 0), d); Ms[:3, 2] = d; Ms[:3, 3] = a; L = np.linalg.norm(b - a)
        frm.merge(lib.box((0, 0, L / 2), (1.9, 0.9, L), Ms), M)
        st.merge(lib.cyl(a - (0, 0.8, 0), a + (0, 0.8, 0), 0.32, 8), M); st.merge(lib.cyl(b - (0, 0.8, 0), b + (0, 0.8, 0), 0.32, 8), M)
        dull.merge(lib.box((xg + 0.2, sy * 10.5, 23.0), (1.6, 2.6, 2.6)), M)                                     # strut support on the guide tube
        # track tube with front and rear fittings, on the floor track [F24]
        frm.merge(lib.cyl((xg, yt, 1.9), (8.2, yt, 1.9), 0.62, n), M)
        for x in (xg, 8.2):
            dull.merge(outward(lib.prism(lib.rrect(2.6, 2.0, 0.3, 2), 0.75, 3.3, T(x, yt, 0))), M)
            st.merge(lib.cyl((x, yt - 1.25, 1.4), (x, yt + 1.25, 1.4), 0.3, 8), M)
        prof = [(-0.85, 0.0), (0.85, 0.0), (0.85, 0.75), (0.3, 0.75), (0.3, 0.45), (-0.3, 0.45), (-0.3, 0.75), (-0.85, 0.75)]
        trk.merge(outward(lib.loft(np.array([[(x, yt + py, 0.05 + pz) for py, pz in prof] for x in (xg - 0.6, 11.5)], float), cap0=True, cap1=True)), M)
        trk.merge(lib.box(((xg - 0.6 + 11.5) / 2, yt, 0.03), (11.5 - xg + 0.6, 2.9, 0.06)), M)
        if ctx.lod == 0:
            for x in np.arange(xg, 11.4, 2.9):
                for e in (-1.15, 1.15): st.merge(screw((x, yt + e, 0.06), (0, 0, 1), 0.18, 0.1), M)
        # crossed lower braces [F28]
        p0 = np.array((xg, sy * 8.4, 0.9)); p1 = np.array((xg, -sy * 6.1, 15.6)); d = (p1 - p0) / np.linalg.norm(p1 - p0)
        Mx = np.eye(4); Mx[:3, 0] = (1, 0, 0); Mx[:3, 1] = np.cross(d, (1, 0, 0)); Mx[:3, 2] = d; Mx[:3, 3] = p0 + np.array((sy * 0.25, 0, 0))
        frm.merge(lib.box((0, 0, np.linalg.norm(p1 - p0) / 2), (0.4, 1.3, np.linalg.norm(p1 - p0)), Mx), M)
    frm.merge(lib.cyl((xg, -9.4, 41.6), (xg, 9.4, 41.6), 0.62, n), M)                                            # support tube across the top
    frm.merge(lib.box((xg, 0, 0.85), (1.5, 11.6, 1.7)), M)                                                       # base tube
    frm.merge(lib.box((xg, 0, 1.9), (1.2, 23.2, 1.0)), M)                                                        # rear cross member between the track fittings
    frm.merge(lib.box((xg + 0.2, 0, 18.5), (0.7, 24.6, 6.2)), M)                                                 # stowage panel band, 24.6 x 6.2 in [F28]
    frm.merge(lib.cyl((xg + 0.5, 0, 22.8), (xg + 0.5, 0, 29.5), 0.75, n), M)                                     # centre tube under the yoke
    yoke = np.array([(-4.4, 28.3), (4.4, 28.3), (1.3, 24.4), (-1.3, 24.4)])
    yk = Mesh(); yk.merge(lib.prism(yoke, -0.2, 0.2), np.array([[0, 0, 1, xg + 1.3], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])); dull.merge(outward(yk), M)
    # armoured wings on the outboard side [F27]: stationary wing aft, movable wing forward, on an upper and a lower tube
    yw = outboard * 12.6
    stat = np.array([(-9.5, PAN_Z + 1.0), (-0.5, PAN_Z + 1.0), (-0.5, PAN_Z + 9.0), (-5.5, PAN_Z + 15.0), (-8.5, PAN_Z + 27.0), (-13.5, PAN_Z + 27.0), (-12.0, PAN_Z + 12.0)])
    move = np.array([(-0.2, PAN_Z + 0.6), (9.2, PAN_Z + 0.6), (9.2, PAN_Z + 3.4), (6.6, PAN_Z + 9.0), (5.0, PAN_Z + 20.6), (-0.2, PAN_Z + 20.6)])
    for poly, dy in ((stat, 0.0), (move, outboard * 0.75)):
        w = Mesh(); w.merge(lib.prism(poly, -0.32, 0.32), XZ @ T(0, 0, yw + dy)); arm.merge(outward(w), M)
    frm.merge(lib.cyl((-12.5, yw + outboard * 0.4, PAN_Z + 21.4), (6.0, yw + outboard * 0.4, PAN_Z + 21.4), 0.4, 8), M)       # upper tube
    frm.merge(lib.cyl((-9.0, yw + outboard * 0.4, PAN_Z + 0.2), (9.0, yw + outboard * 0.4, PAN_Z + 0.2), 0.4, 8), M)          # lower tube
    for x in (-9.0, -1.5):
        dull.merge(lib.box((x, (yw + outboard * 10.9) / 2 + outboard * 0.2, PAN_Z + 0.4), (1.2, abs(yw) - 10.5, 0.5)), M)    # brackets to the bucket
    # adjust handles on the bucket side by the occupant's right knee [F7 detail B]
    for i, zz in enumerate((PAN_Z + 3.0, PAN_Z + 1.2)):
        blk.merge(lib.box((7.6 + i * 0.9, -10.9, zz + 0.4), (2.6, 0.5, 1.1)), M)
