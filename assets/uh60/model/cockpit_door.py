"""Cockpit door, inside face: what the crew sees from the seats.

Every part here is drawn in the 2006 maintenance manual TM 1-1520-237-23 (door work packages, volume 5). The drawings
are isometric and carry no dimensions, so each part's EXISTENCE, SHAPE and ARRANGEMENT are sourced and every SIZE and
exact position is estimated by proportion against the door opening [F6-1]. Colours are not given by the manual.

  [D0201] WP 0201 fig 1  jettison components: jettison handle (round knob on a lever), control rod, jettison lever,
                         upper and lower arms on arm pins A and B, tube assembly between them, springs, jettison pin
                         and clevis, gaskets under the hinges
  [D0203] WP 0203 fig 1  stationary window: forward doubler, rear doubler, screw rows, seal round the door, lockwire
                         clip on the lower forward edge of the window frame
  [D0204] WP 0204 fig 1  vent window: plastic pane sliding on an upper and a lower track with seals, doubler round
                         the cut-out, upper and lower vent window retainers
  [D0206] WP 0206 fig 1  front crank mechanism: inside handle on a shaft, doubler, bearing, cam, front crank
  [D0207] WP 0207 fig 1  latches: upper and lower latch housings with latch bolts and bellcranks on the rear edge,
                         upper and lower horizontal rods, vertical rod
  [D0208] WP 0208 fig 1  rear crank mechanism: support, bellcrank, rear crank and link behind the outside door handle

Built once for the left door and mirrored for the right.
"""
import math
import numpy as np
import lib, recipe as RC
from lib import Mesh, T, R, S
from hardware import surface, instances

D_IN = RC.SHELL_T        # the door's inner face, inches below the outer skin
G_IN = 0.92              # the window's inner face
WIN = RC.COCKPIT_DOOR_WIN['poly']; DOOR = RC.COCKPIT_DOOR['poly']
VENT = [(217.6, 237.6), (231.0, 237.6), (231.0, 248.4), (224.3, 248.4)]   # [est] vent cut-out, from [D0204] proportions


def at(s, wl, depth):
    p, n = surface(s, wl, 1); return p - n * depth


def frame(s, wl, depth):
    """Local frame on the door: x aft, y up, z inboard."""
    p, n = surface(s, wl, 1); z = -n; x = np.array((1.0, 0, 0)); x -= z * x.dot(z); x /= np.linalg.norm(x); y = np.cross(z, x)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, p - n * depth
    return M


def ring(poly, r, grow, pitch):
    import airframe
    c = airframe.rounded(poly, r, grow); L = np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1).sum()
    return lib.resample(c, max(8, int(round(L / pitch))), closed=True)


def widen(A, w, closed=True):
    """Second polyline, w to the right of A's direction of travel (outward for a CCW ring)."""
    A = np.asarray(A, float)
    t = (np.roll(A, -1, 0) - np.roll(A, 1, 0)) if closed else np.gradient(A, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    return A + w * np.c_[t[:, 1], -t[:, 0]]


def band(A, B, depth, h, closed=True, sink=0.05):
    """A strip of plate lying on the door between two matched 2D polylines, h proud of the surface at depth."""
    m = Mesh(); n = len(A)
    V = np.array([[at(*A[i], depth + h), at(*B[i], depth + h), at(*A[i], depth - sink), at(*B[i], depth - sink)] for i in range(n)])
    faces = []
    for i in range(n if closed else n - 1):
        j = (i + 1) % n; a, b = i * 4, j * 4; ref = (V[i].mean(0) + V[j].mean(0)) / 2
        quads = [(a, b, b + 1, a + 1), (a + 2, b + 2, b, a), (a + 1, b + 1, b + 3, a + 3)]
        if not closed and i == 0: quads.append((a, a + 1, a + 3, a + 2))
        if not closed and i == n - 2: quads.append((b, b + 1, b + 3, b + 2))
        for q in quads:
            P = V.reshape(-1, 3)[list(q)]; nr = np.cross(P[1] - P[0], P[2] - P[0])
            faces.append(q if nr.dot(P.mean(0) - ref) > 0 else q[::-1])
    return m.add(V.reshape(-1, 3), faces)


def line(p0, p1, step=1.5):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); k = max(2, int(np.linalg.norm(p1 - p0) / step) + 1)
    return np.linspace(p0, p1, k)


def bar(p0, p1, w, depth, h):
    c = line(p0, p1); return band(widen(c, -w / 2, False), widen(c, w / 2, False), depth, h, closed=False)


def rod(p0, p1, r, depth, n=8):
    return lib.cyl(at(*p0, depth), at(*p1, depth), r, n)


def heads(pts, depth, unit):
    P = [at(s, wl, depth) for s, wl in pts]; N = [-surface(s, wl, 1)[1] for s, wl in pts]
    return instances(unit, P, N)


def build_left(ctx):
    hi = ctx.lod == 0; nt = 10 if hi else 6
    od, alu, stl, blk, yel, rub, gls = (Mesh() for _ in range(7))
    screw = lib.revolve([(0.17, 0.0), (0.16, 0.05), (0.09, 0.07), (0, 0.07)], 8 if hi else 5, cap0=False)
    rivet = lib.revolve([(0.11, 0.0), (0.09, 0.04), (0, 0.05)], 6 if hi else 4, cap0=False)

    # ---- window frame doublers and their screw rows [D0203]; the forward doubler is the wider one
    A = ring(WIN, 3.0, 0.25, 1.0)
    wid = np.where(A[:, 0] < 213.5 + (A[:, 1] - 234.5) * 0.615 + 0.6, 2.3, 1.6)                 # wider along the sloped forward edge
    wid = np.convolve(np.r_[wid[-3:], wid, wid[:3]], np.ones(7) / 7, 'valid')
    od.merge(band(A, A + (widen(A, 1.0) - A) * wid[:, None], D_IN, 0.08))
    if hi:
        stl.merge(heads(ring(WIN, 3.0, 1.15, 1.7), D_IN + 0.08, screw))
    # ---- seal round the door's edge [D0203 "SEAL"]
    c = ring(DOOR, 2.0, -0.75, 1.2)
    rub.merge(lib.tube([at(s, wl, D_IN - 0.05) for s, wl in np.vstack([c, c[:1]])], 0.3, 6, cap=False))

    # ---- vent window [D0204]: doubler round the cut-out, sliding plastic pane, upper and lower tracks, seals, retainers
    V = ring(VENT, 0.8, 0.0, 0.9)
    od.merge(band(V, widen(V, 0.85), G_IN, 0.07))
    if hi:
        stl.merge(heads(ring(VENT, 0.8, 0.45, 1.5), G_IN + 0.07, rivet))
    P = ring(VENT, 0.8, 0.35, 1.2); pc = P.mean(0)
    top = [at(*p, G_IN + 0.32) for p in P]; bot = [at(*p, G_IN + 0.2) for p in P]; k = len(P)
    gls.add(np.array(top + bot + [at(*pc, G_IN + 0.32), at(*pc, G_IN + 0.2)]),
            [(2 * k, i, (i + 1) % k) for i in range(k)] + [(2 * k + 1, k + (i + 1) % k, k + i) for i in range(k)] +
            [(i, k + i, k + (i + 1) % k, (i + 1) % k) for i in range(k)])
    for wl, s0 in ((236.85, 216.4), (249.15, 224.0)):
        rub.merge(bar((s0, wl), (241.9, wl), 0.95, G_IN, 0.06))                                    # seal under the track
        alu.merge(bar((s0, wl - 0.33), (241.9, wl - 0.33), 0.14, G_IN + 0.05, 0.5))                # channel walls
        alu.merge(bar((s0, wl + 0.33), (241.9, wl + 0.33), 0.14, G_IN + 0.05, 0.5))
        alu.merge(bar((s0, wl), (241.9, wl), 0.66, G_IN + 0.05, 0.1))
        if hi:
            stl.merge(heads([(s, wl) for s in np.arange(s0 + 1.2, 241.5, 2.6)], G_IN + 0.15, rivet))
    for wl, dy in ((247.3, 1), (238.7, -1)):                                                      # vent window retainers
        M = frame(230.1, wl, G_IN + 0.32)
        alu.merge(lib.prism(lib.rrect(1.5, 1.1, 0.25, 3), 0.0, 0.1, M))
        alu.merge(lib.prism(lib.rrect(0.5, 1.3, 0.15, 2), 0.0, 0.5, M @ T(0.2, dy * 0.75, 0)))     # leg up to the track
        blk.merge(lib.revolve([(0.3, 0.1), (0.36, 0.14), (0.36, 0.52), (0.3, 0.58), (0, 0.58)], nt, M @ T(-0.3, 0, 0)))  # knurled knob

    # ---- front crank [D0206]: doubler, bearing boss, shaft and the inside handle
    FC = (231.0, 231.5); M = frame(*FC, D_IN)
    od.merge(lib.prism(lib.rrect(1.8, 4.8, 0.45, 3), 0.0, 0.1, M))
    alu.merge(lib.revolve([(0.8, 0.1), (0.8, 0.22), (0.58, 0.3), (0.58, 0.5), (0, 0.5)], nt, M))
    stl.merge(lib.cyl(M[:3, 3] + M[:3, 2] * 0.5, M[:3, 3] + M[:3, 2] * 1.5, 0.27, nt))
    blk.merge(lib.revolve([(0.52, 1.0), (0.56, 1.1), (0.56, 1.62), (0.48, 1.72), (0, 1.72)], nt, M))
    grip = [(0, 0, 1.36), (-0.9, -0.05, 1.36), (-2.0, -0.3, 1.42), (-3.3, -0.75, 1.5), (-4.4, -1.0, 1.52)]
    gp = lib.resample(np.array(grip), 12 if hi else 6)
    rings = []
    for i, q in enumerate(gp):
        t = gp[min(i + 1, len(gp) - 1)] - gp[max(i - 1, 0)]; t /= np.linalg.norm(t); u = np.cross(t, (0, 0, 1.0)); u /= np.linalg.norm(u)
        w = 0.42 - 0.1 * abs(i / (len(gp) - 1) - 0.7); rings.append([q + u * w * math.cos(a) + np.array((0, 0, 0.27)) * math.sin(a) for a in np.linspace(0, 2 * np.pi, nt, endpoint=False)])
    g = lib.loft(rings, cap0=True, cap1=True); blk.merge(g, M)
    if hi:
        stl.merge(heads([(FC[0] + dx, FC[1] + dy) for dx in (-0.5, 0.5) for dy in (-1.9, 1.9)], D_IN + 0.1, screw))
    # ---- rear crank behind the outside handle [D0208]: support, bellcrank and link
    RCK = (241.2, 229.5); M2 = frame(*RCK, D_IN)
    od.merge(lib.prism(lib.rrect(1.7, 3.3, 0.4, 3), 0.0, 0.1, M2))
    alu.merge(lib.revolve([(0.5, 0.1), (0.5, 0.75), (0.34, 0.85), (0, 0.85)], nt, M2))
    alu.merge(lib.prism(np.array([(-0.3, -0.35), (0.3, -0.35), (0.22, 1.5), (-0.22, 1.5)]), 0.55, 0.7, M2))      # bellcrank arm, up
    alu.merge(lib.prism(np.array([(-0.3, 0.35), (0.3, 0.35), (0.22, -1.3), (-0.22, -1.3)]), 0.55, 0.7, M2))      # and down
    if hi:
        stl.merge(heads([(RCK[0] + dx, RCK[1] + dy) for dx in (-0.5, 0.5) for dy in (-1.3, 1.3)], D_IN + 0.1, screw))
    # ---- upper and lower horizontal rods from the front crank to the rear bellcrank [D0207]
    for wl0, wl1 in ((FC[1] + 0.9, RCK[1] + 1.3), (FC[1] - 0.9, RCK[1] - 1.1)):
        a, b = (FC[0] + 0.3, wl0), (RCK[0], wl1)
        alu.merge(rod(a, b, 0.2, D_IN + 0.72, nt))
        for e, o in ((a, b), (b, a)):                                                             # clevis ends with headed pins
            d = np.array(o) - np.array(e); d /= np.linalg.norm(d)
            stl.merge(rod(e, tuple(np.array(e) + d * 0.9), 0.28, D_IN + 0.72, 6))
            stl.merge(lib.cyl(at(*e, D_IN + 0.4), at(*e, D_IN + 1.02), 0.11, 6))
    # ---- latch housings on the rear edge with bolts into the frame, bellcranks, and the vertical rod between them [D0207]
    for wl in (230.2, 254.6):
        M3 = frame(244.3, wl, D_IN)
        od.merge(lib.prism(lib.rrect(1.9, 1.9, 0.3, 3), 0.0, 0.12, M3))
        alu.merge(lib.cyl(at(243.3, wl, D_IN + 0.7), at(245.3, wl, D_IN + 0.7), 0.56, nt, r1=0.44))
        alu.merge(lib.cyl(at(245.3, wl, D_IN + 0.7), at(245.75, wl, D_IN + 0.7), 0.44, nt))
        stl.merge(lib.cyl(at(245.7, wl, D_IN + 0.7), at(246.45, wl, D_IN + 0.7), 0.24, 8))         # latch bolt
        alu.merge(lib.prism(np.array([(-1.4, -0.3), (-0.8, -0.45), (-0.8, 0.9), (-1.2, 0.9)]), 0.55, 0.7, M3))    # bellcrank
        if hi:
            stl.merge(heads([(244.3 + dx, wl + dy) for dx in (-0.65, 0.65) for dy in (-0.65, 0.65)], D_IN + 0.12, screw))
    alu.merge(rod((243.2, 231.0), (243.2, 255.4), 0.19, D_IN + 0.74, nt))
    alu.merge(rod((RCK[0], RCK[1] + 1.3), (243.2, 231.0), 0.16, D_IN + 0.72, 6))                  # link
    for wl in (231.0, 255.4):
        stl.merge(lib.cyl(at(243.2, wl, D_IN + 0.4), at(243.2, wl, D_IN + 1.0), 0.11, 6))

    # ---- emergency jettison [D0201]: handle at the window's lower forward corner, control rod, lever, arms, tube, pin
    JH = (213.4, 232.3); HU, HL = (209.4, 229.0), (209.4, 211.5)                                  # hinge heights = hardware.py's hinges
    M4 = frame(*JH, D_IN)
    yel.merge(lib.revolve([(0.0, 0.75), (0.8, 0.75), (0.95, 0.85), (0.95, 1.05), (0.8, 1.15), (0, 1.15)], nt + 4, M4))   # round knob
    stl.merge(lib.cyl(M4[:3, 3] + M4[:3, 2] * 0.1, M4[:3, 3] + M4[:3, 2] * 0.8, 0.16, 6))
    alu.merge(lib.prism(np.array([(-1.9, -1.25), (-1.5, -1.6), (0.3, -0.2), (-0.1, 0.25)]), 0.1, 0.25, M4))    # handle arm to its pivot
    alu.merge(lib.prism(lib.rrect(1.3, 1.0, 0.2, 2), 0.0, 0.1, M4 @ T(-1.7, -1.4, 0)))
    jl = (210.3, 231.2)                                                                          # jettison lever, top
    alu.merge(rod((JH[0] - 1.7, JH[1] - 1.4), jl, 0.15, D_IN + 0.45, 6))                          # control rod
    alu.merge(bar(jl, (HU[0] + 0.2, HU[1]), 0.6, D_IN + 0.3, 0.14))                               # jettison lever
    for hp, nm in ((HU, 'upper'), (HL, 'lower')):
        Mh = frame(*hp, D_IN)
        rub.merge(lib.prism(lib.rrect(1.5, 3.4, 0.6, 4), 0.0, 0.06, Mh @ T(-0.5, 0, 0)))          # gasket
        alu.merge(lib.prism(lib.rrect(1.2, 3.0, 0.5, 4), 0.06, 0.16, Mh @ T(-0.5, 0, 0)))
        alu.merge(lib.prism(np.array([(-0.5, -0.4), (1.0, -0.3), (1.0, 0.3), (-0.5, 0.4)]), 0.3, 0.45, Mh))   # arm
        stl.merge(lib.cyl(Mh[:3, 3] + Mh[:3, 2] * 0.16, Mh[:3, 3] + Mh[:3, 2] * 0.62, 0.2, 8))    # arm pin
        if hi:
            stl.merge(heads([(hp[0] - 0.5, hp[1] + dy) for dy in (-1.1, 1.1)], D_IN + 0.16, screw))
    ts = HU[0] + 0.8
    alu.merge(rod((ts, HU[1] - 0.2), (ts, HL[1] + 0.2), 0.22, D_IN + 0.5, nt))                    # tube assembly
    for wl in (HU[1] - 1.1, HL[1] + 1.1):
        stl.merge(rod((ts, wl - 0.45), (ts, wl + 0.45), 0.3, D_IN + 0.5, 6))                      # clevis and nut
    stl.merge(rod((ts + 0.6, 222.5), (ts + 0.6, 218.0), 0.1, D_IN + 0.4, 6))                      # spring
    stl.merge(rod((ts, 219.6), (ts + 1.1, 219.0), 0.13, D_IN + 0.5, 6))
    stl.merge(rod((ts + 1.1, 219.3), (ts + 1.1, 205.5), 0.13, D_IN + 0.5, 6))                     # jettison pin to the fitting at the door's foot
    alu.merge(lib.prism(lib.rrect(1.2, 1.0, 0.2, 2), 0.0, 0.5, frame(ts + 1.1, 206.0, D_IN)))
    stl.merge(lib.prism(lib.rrect(0.5, 0.7, 0.1, 2), 0.0, 0.05, frame(215.0, 233.6, D_IN + 0.08)))   # lockwire clip [D0203]
    return (('inside_doublers', od, 'paint_od_interior'), ('inside_mechanism', alu, 'aluminium'), ('inside_pins', stl, 'steel'),
            ('inside_handle', blk, 'paint_black'), ('jettison_handle', yel, 'paint_yellow'), ('inside_seal', rub, 'rubber'),
            ('vent_window', gls, 'glass'))


def build(ctx):
    parts = build_left(ctx)
    for sg, side in ((1, 'L'), (-1, 'R')):
        for nm, m, mat in parts:
            mm = Mesh(); mm.merge(m, None if sg > 0 else S(1, -1, 1))
            ctx.part(f'cockpit_door_{side}', f'cockpit_door_{nm}', mm, mat, 40)
