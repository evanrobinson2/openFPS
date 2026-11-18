"""External gadgets: nose sensor cap and probes, the chin cannon turret (yaw and elevation nodes), the ventral gun pod,
keel tanks and plumbing, the dorsal spine with its antennas, heat exchanger and escape hatch, the contents of the
equipment bays, conduits in the waist channel, thruster quads and navigation lights. Each is its own object."""
import math, random
import numpy as np
import spec, kit
from kit import MB, finish, empty

def nose(H):
    mb = MB()
    a, zt, zb, c, n = [float(v) for v in spec.hull_params(0.06)]
    zc = 0.5 * (zt + zb)
    mb.sphere((0.31, 0, zc), 1.0, 'glass_port', n=20, squash=(0.30, a * 1.02, (zt - zb) * 0.52))            # sensor window
    mb.lathe((0.30, 0, zc), (-1, 0, 0), [(0.0, 0.30), (0.20, 0.26), (0.25, 0.20)], 'machinery_dark', n=20, cap0=False, cap1=True)
    mb.sphere((0.06, 0, zc), 0.05, 'light_red', n=10)
    for sy in (-1, 1):                                                                                      # air-data probes and whisker antennas
        mb.pipe([(0.55, sy * 1.05, zc - 0.05), (0.34, sy * 1.18, zc - 0.05), (0.02, sy * 1.18, zc - 0.05)], 0.016, 'machinery_bare', n=8)
        mb.cyl((0.50, sy * 1.05, zc - 0.05), (0.60, sy * 1.02, zc - 0.05), 0.04, 'structure_steel', n=10)
        mb.pipe([(1.05, sy * 1.55, zc - 0.55), (0.70, sy * 1.75, zc - 0.62), (0.10, sy * 1.80, zc - 0.68)], 0.011, 'machinery_bare', n=6)
        mb.pipe([(0.80, sy * 0.55, zb + 0.10), (0.45, sy * 0.60, zb - 0.12), (0.03, sy * 0.60, zb - 0.14)], 0.013, 'machinery_bare', n=6)
    return mb

def chin_cannon(parent):
    C = spec.CHIN_CANNON; s, zc = C['s'], C['z']
    zh = float(spec.hull_params(s)[2])                         # hull bottom at the turret
    base = MB()
    base.lathe((s, 0, zh + 0.10), (0, 0, -1), [(0, 0.62), (0.16, 0.62), (0.16, 0.50), (0.24, 0.48)], 'armour_gunmetal_d', n=32, cap0=False, cap1=False)
    base.bolt_circle((s, 0, zh - 0.06), (0, 0, -1), 0.56, 24, r=0.018, h=0.012)
    finish('chin_turret_ring', base, parent, group='gadgets')
    yaw = MB()
    yaw.lathe((s, 0, zh - 0.14), (0, 0, -1), [(0, 0.47), (0.06, 0.47), (0.14, 0.40)], 'armour_gunmetal_b', n=32, cap0=False, cap1=True)
    for sy in (-1, 1):                                         # trunnion cheeks
        yaw.prism([(s - 0.30, sy * 0.36, zh - 0.20), (s + 0.34, sy * 0.36, zh - 0.20), (s + 0.26, sy * 0.36, zc - 0.20), (s - 0.20, sy * 0.36, zc - 0.20)], (0, sy * 0.07, 0), 'armour_gunmetal_c')
        yaw.bolt_circle((s, sy * 0.43, zc), (0, sy, 0), 0.10, 8, r=0.014, h=0.01)
        yaw.cyl((s, sy * 0.36, zc), (s, sy * 0.45, zc), 0.07, 'machinery_bare', n=14)
    finish('chin_turret_yaw', yaw, 'chin_turret_ring', pivot=(s, 0, zh - 0.14), group='gadgets')
    gun = MB()
    gun.lathe((s + 0.42, 0, zc), (-1, 0, 0), [(0, 0.16), (0.10, 0.27), (0.70, 0.29), (0.86, 0.22)], 'armour_gunmetal_a', n=24, cap0=True, cap1=True)     # receiver housing
    gun.box(s - 0.40, s + 0.30, -0.33, 0.33, zc - 0.05, zc + 0.05, 'armour_gunmetal_d')
    L = C['barrel_len']; r = C['barrel_r']
    for sy in (-1, 1):
        y = sy * C['twin']
        gun.lathe((s - 0.40, y, zc), (-1, 0, 0), [(0, r * 1.9), (0.30, r * 1.9), (0.32, r * 1.5), (0.95, r * 1.5), (0.97, r), (L - 0.36, r), (L - 0.36, r * 1.7), (L - 0.06, r * 1.7), (L - 0.06, r * 1.25), (L, r * 1.25), (L, r * 0.55), (L - 0.3, r * 0.55)],
                  'machinery_dark', n=16, cap0=True, cap1=False, mats=['machinery_dark'] * 4 + ['machinery_bare'] * 2 + ['armour_paint_red'] * 3 + ['machinery_dark'] * 3)
        for k in range(6):                                     # cooling jacket slots
            gun.box(s - 0.40 - 0.38 - 0.09 * k, s - 0.40 - 0.34 - 0.09 * k, y - r * 1.56, y + r * 1.56, zc - 0.02, zc + 0.02, 'substructure_dark')
        gun.cyl((s - 0.75, y, zc - r * 1.5), (s - 0.75, y, zc - r * 1.5 - 0.10), 0.03, 'machinery_bare', n=8)         # recoil buffer
    gun.box(s - 1.25, s - 1.17, -C['twin'] - 0.12, C['twin'] + 0.12, zc - 0.11, zc + 0.11, 'structure_steel')         # barrel clamp
    for sy in (-1, 1):
        for dz in (-0.075, 0.075):
            gun.bolt((s - 1.25, sy * (C['twin'] + 0.07), zc + dz), (-1, 0, 0), r=0.012, h=0.009)
    gun.pipe([(s + 0.25, 0.0, zc + 0.20), (s + 0.42, 0.0, zc + 0.36), (s + 0.42, 0.0, zh - 0.20)], 0.085, 'machinery_dark', n=8)        # feed chute
    finish('chin_gun_cradle', gun, 'chin_turret_yaw', pivot=(s, 0, zc), group='gadgets')

def belly_pod():
    mb = MB(); B = spec.BELLY_POD; s, z = B['s'], B['z']; L = B['len']
    prof = [(s - L / 2, z + 0.10), (s - L / 2 + 0.35, z - 0.30), (s + L / 2 - 0.6, z - 0.30), (s + L / 2, z + 0.10)]
    mb.prism([(a, -0.42, b) for a, b in prof], (0, 0.84, 0), 'armour_gunmetal_b')
    for sy in (-1, 1):
        mb.prism([(a, sy * 0.42, b * 0.97 + 0.0) for a, b in [(prof[0][0] + 0.25, prof[0][1]), (prof[1][0] + 0.1, prof[1][1] + 0.1), (prof[2][0] - 0.1, prof[2][1] + 0.1), (prof[3][0] - 0.3, prof[3][1])]], (0, sy * 0.10, 0), 'armour_gunmetal_d')
        mb.bolt_line((s - L / 2 + 0.5, sy * 0.52, z - 0.10), (s + L / 2 - 0.7, sy * 0.52, z - 0.10), (0, sy, 0), pitch=0.2, r=0.016, h=0.01)
        y = sy * 0.20                                           # two short barrels with red muzzles, as in the concept
        mb.lathe((s - L / 2 + 0.25, y, z - 0.16), (-1, 0, 0), [(0, 0.085), (0.55, 0.085), (0.55, 0.06), (0.95, 0.06), (0.95, 0.085), (1.15, 0.085), (1.15, 0.035)], 'machinery_dark', n=14, cap0=False, cap1=True,
                 mats=['machinery_dark'] * 4 + ['armour_paint_red'] * 3)
    mb.box(s - 0.2, s + 0.5, -0.15, 0.15, z - 0.345, z - 0.30, 'machinery_dark')                # sensor fairing
    mb.sphere((s + 0.15, 0, z - 0.33), 0.045, 'glass_port', n=12)
    return mb

def keel():
    """Tanks and plumbing on the belly beside the lift, where nothing has to open."""
    mb = MB(); Lf = spec.LIFT
    for sy in (-1, 1):
        y = sy * 1.86; z = -2.98
        for (a, b) in ((Lf['s0'] + 0.10, Lf['s0'] + 1.65), (Lf['s0'] + 1.90, Lf['s1'] - 0.10)):
            mb.lathe((a, y, z), (1, 0, 0), [(0, 0.10), (0.10, 0.20), (b - a - 0.10, 0.20), (b - a, 0.10)], 'machinery_bare', n=18)
            for s in (a + 0.35, b - 0.35):                      # straps with a bolt each side
                mb.lathe((s - 0.03, y, z), (1, 0, 0), [(0, 0.20), (0, 0.215), (0.06, 0.215), (0.06, 0.20)], 'structure_steel', n=18, cap0=False, cap1=False)
                mb.box(s - 0.04, s + 0.04, y - 0.26, y + 0.26, z + 0.16, z + 0.22, 'structure_steel')
                mb.bolt((s, y - 0.23, z + 0.16), (0, 0, -1), r=0.012, h=0.008); mb.bolt((s, y + 0.23, z + 0.16), (0, 0, -1), r=0.012, h=0.008)
        for k, yy in enumerate((sy * 1.52, sy * 1.60)):
            mb.pipe([(Lf['s0'] - 0.25, yy, -3.03), (Lf['s0'] + 0.2, yy, -3.07), (Lf['s1'] - 0.2, yy, -3.07), (Lf['s1'] + 0.3, yy, -3.03)], 0.028 if k else 0.036, 'copper_pipe' if k else 'machinery_dark', n=8)
            for s in np.arange(Lf['s0'] + 0.4, Lf['s1'], 0.8):
                mb.box(s - 0.025, s + 0.025, yy - 0.05, yy + 0.05, -3.06, -2.98, 'structure_steel')
    return mb

def dorsal(H):
    mb = MB(); bolts = MB()
    def top(s): return float(spec.hull_params(s)[1])
    # spine: a segmented cable duct down the centreline
    s = 7.6
    while s < 21.2:
        e = min(s + 1.15, 21.2); z = top(0.5 * (s + e)) + 0.03
        mb.prism([(s, -0.26, z), (s, -0.18, z + 0.16), (s, 0.18, z + 0.16), (s, 0.26, z)], (e - s - 0.04, 0, 0), 'armour_gunmetal_d' if int(s * 2) % 3 else 'armour_gunmetal_b')
        for sy in (-1, 1):
            bolts.bolt_line((s + 0.12, sy * 0.22, z + 0.08), (e - 0.16, sy * 0.22, z + 0.08), (0, sy * 0.9, 0.45), pitch=0.3, r=0.014, h=0.01)
        s = e
    # comms dome, escape hatch, heat exchanger, blade antennas, sensor mast
    z = top(9.6)
    mb.lathe((9.6, 0, z + 0.16), (0, 0, 1), [(0, 0.46), (0.05, 0.46), (0.05, 0.40), (0.16, 0.34), (0.22, 0.20), (0.24, 0.0)], 'armour_gunmetal_c', n=24, cap0=False, cap1=False)
    bolts.bolt_circle((9.6, 0, z + 0.21), (0, 0, 1), 0.43, 16, r=0.013, h=0.009)
    z = top(17.0)
    for sy in (-1, 1):                                          # heat exchanger banks: finned boxes
        y0, y1 = sy * 0.36, sy * 1.02
        mb.box(15.2, 18.8, min(y0, y1), max(y0, y1), z - 0.12, z + 0.04, 'machinery_dark')
        for k in range(30):
            sf = 15.26 + k * 0.12
            mb.box(sf, sf + 0.03, min(y0, y1) + 0.03, max(y0, y1) - 0.03, z + 0.04, z + 0.15, 'machinery_bare')
        mb.pipe([(15.0, sy * 0.30, z + 0.06), (15.15, sy * 0.60, z + 0.02), (15.2, sy * 0.60, z + 0.02)], 0.035, 'copper_pipe', n=8)
        bolts.bolt_line((15.3, sy * 1.02, z + 0.0), (18.7, sy * 1.02, z + 0.0), (0, sy, 0.3), pitch=0.3, r=0.013, h=0.009)
    for (s, y) in ((8.4, 0.75), (8.4, -0.75), (20.2, 0.0)):     # blade antennas
        z = top(s) - (0.10 if y else -0.02)
        mb.prism([(s, y - 0.012, z), (s + 0.34, y - 0.012, z), (s + 0.26, y - 0.012, z + 0.34), (s + 0.14, y - 0.012, z + 0.34)], (0, 0.024, 0), 'machinery_dark')
    z = top(13.6)
    mb.cyl((13.6, 0, z + 0.18), (13.6, 0, z + 0.28), 0.035, 'machinery_bare', n=10); mb.sphere((13.6, 0, z + 0.30), 0.074, 'glass_port', n=10)
    return mb, bolts

def bay_contents(H):
    """Something different bolted into each equipment bay, in a frame local to the bay."""
    rng = random.Random(41)
    mb = MB(); bolts = MB()
    names = sorted(n for n in H.openings if n.startswith('bay_'))
    for name in names:
        i0, i1, j0, j1, _ = H.rect(name)
        kind = int(name.split('_')[1]) % 4
        for sd in (1, -1):
            G = H.nodes(i0, i1, j0, j1, -spec.BAYS['depth'], sd, margin=0.10)
            p00, p10, p01 = G[0, 0], G[-1, 0], G[0, -1]       # top-forward, top-aft, bottom-forward
            es = (p10 - p00); Ls = float(np.linalg.norm(es)); es = es / Ls
            ev = (p00 - p01); Lv = float(np.linalg.norm(ev)); ev = ev / Lv          # up the bay
            en = np.cross(es, ev) * (1 if sd > 0 else -1)
            en = en / np.linalg.norm(en)
            if np.dot(en, np.array((0, sd, 0))) < 0: en = -en
            def P(a, b, c):                                    # a along the bay (0..Ls), b up it (0..Lv), c out of the hull
                return tuple(p01 + es * a + ev * b + en * c)
            def obox(a0, a1, b0, b1, c0, c1, m):
                mb.obox(P((a0 + a1) / 2, (b0 + b1) / 2, (c0 + c1) / 2), tuple(es * (a1 - a0) / 2), tuple(ev * (b1 - b0) / 2), tuple(en * (c1 - c0) / 2 * (1 if np.dot(np.cross(es, ev), en) > 0 else -1)), m)
            if kind == 0:                                      # louvre vents
                obox(0.05, Ls - 0.05, 0.05, Lv - 0.05, 0.0, 0.03, 'machinery_dark')
                nl = 9
                for k in range(nl):
                    b = 0.10 + (Lv - 0.2) * k / (nl - 1)
                    mb.obox(P(Ls / 2, b, 0.055), tuple(es * (Ls / 2 - 0.09)), tuple((ev * 0.030 + en * 0.022)), tuple((en * 0.004 - ev * 0.003) * (1 if np.dot(np.cross(es, ev), en) > 0 else -1)), 'machinery_bare')
                for (a, b) in ((0.08, 0.08), (Ls - 0.08, 0.08), (0.08, Lv - 0.08), (Ls - 0.08, Lv - 0.08), (Ls / 2, 0.08), (Ls / 2, Lv - 0.08)):
                    bolts.bolt(P(a, b, 0.03), tuple(en), r=0.014, h=0.01)
            elif kind == 1:                                    # pipe manifold with valves
                for k in range(4):
                    b = 0.14 + (Lv - 0.28) * k / 3; r = 0.045 if k % 2 else 0.032
                    mb.pipe([P(0.0, b, 0.07), P(Ls * 0.3, b, 0.07), P(Ls * 0.42, b + 0.04, 0.09), P(Ls, b + 0.04, 0.09)], r, 'copper_pipe' if k == 2 else 'machinery_bare', n=8)
                    c = P(Ls * 0.68, b + 0.04, 0.09)
                    mb.cyl(c, tuple(np.array(c) + en * 0.12), r * 0.9, 'structure_steel', n=8)
                    mb.cyl(tuple(np.array(c) + en * 0.12), tuple(np.array(c) + en * 0.135), r * 1.9, 'armour_paint_red', n=10)
                for a in (Ls * 0.18, Ls * 0.86):
                    obox(a - 0.025, a + 0.025, 0.06, Lv - 0.06, 0.0, 0.05, 'structure_steel')
                    for b in (0.09, Lv - 0.09):
                        bolts.bolt(P(a, b, 0.05), tuple(en), r=0.013, h=0.009)
            elif kind == 2:                                    # access hatch with grab handles and a placard
                obox(0.10, Ls - 0.10, 0.10, Lv - 0.10, 0.0, 0.035, 'armour_gunmetal_c')
                obox(0.16, Ls - 0.16, 0.16, Lv - 0.16, 0.035, 0.05, 'armour_gunmetal_a')
                nb = 7
                for k in range(nb + 1):
                    a = 0.13 + (Ls - 0.26) * k / nb
                    bolts.bolt(P(a, 0.13, 0.035), tuple(en), r=0.014, h=0.01); bolts.bolt(P(a, Lv - 0.13, 0.035), tuple(en), r=0.014, h=0.01)
                for k in range(1, 5):
                    b = 0.13 + (Lv - 0.26) * k / 5
                    bolts.bolt(P(0.13, b, 0.035), tuple(en), r=0.014, h=0.01); bolts.bolt(P(Ls - 0.13, b, 0.035), tuple(en), r=0.014, h=0.01)
                for a in (Ls * 0.3, Ls * 0.7):
                    mb.pipe([P(a, Lv * 0.40, 0.05), P(a, Lv * 0.40, 0.11), P(a, Lv * 0.62, 0.11), P(a, Lv * 0.62, 0.05)], 0.014, 'hazard_yellow', n=6)
                obox(Ls * 0.42, Ls * 0.58, Lv * 0.74, Lv * 0.82, 0.05, 0.054, 'placard_white')
            else:                                              # two pressure bottles and a regulator
                for k in range(2):
                    a = Ls * (0.28 + 0.44 * k)
                    mb.lathe(P(a, 0.10, 0.15), tuple(ev), [(0, 0.06), (0.08, 0.125), (Lv - 0.36, 0.125), (Lv - 0.28, 0.05), (Lv - 0.22, 0.05)], 'machinery_bare' if k else 'hazard_yellow', n=14)
                    for b in (Lv * 0.3, Lv * 0.65):
                        mb.lathe(P(a, b, 0.15), tuple(ev), [(0, 0.125), (0, 0.137), (0.04, 0.137), (0.04, 0.125)], 'structure_steel', n=14, cap0=False, cap1=False)
                        bolts.bolt(P(a + 0.16, b + 0.02, 0.02), tuple(en), r=0.012, h=0.009)
                mb.pipe([P(Ls * 0.28, Lv - 0.14, 0.15), P(Ls * 0.5, Lv - 0.08, 0.10), P(Ls * 0.72, Lv - 0.14, 0.15)], 0.018, 'copper_pipe', n=6)
                obox(Ls * 0.44, Ls * 0.56, Lv - 0.14, Lv - 0.04, 0.02, 0.12, 'machinery_dark')
    return mb, bolts

def waist_conduits(H):
    mb = MB(); bolts = MB()
    i0, i1, j0, j1, _ = H.rect('waist')
    for sd in (1, -1):
        for j, r, m in ((j0, 0.030, 'machinery_dark'), (j1, 0.022, 'copper_pipe')):
            off = -spec.WAIST['depth'] + 0.05; dj = 0.25 if j == j0 else -0.25
            pts = []
            for i in range(i0, i1 + 1):
                a = np.array(H.pt(i, j, off, sd)); b = np.array(H.pt(i, j + (1 if j == j0 else -1), off, sd))
                pts.append(tuple(a + (b - a) * abs(dj)))
            mb.pipe(pts, r, m, n=6)
            for k in range(2, len(pts) - 1, 5):
                p = pts[k]; nn = H.nrm(i0 + k, j, sd)
                mb.cyl((p[0] - 0.03, p[1], p[2]), (p[0] + 0.03, p[1], p[2]), r + 0.012, 'structure_steel', n=8)
                bolts.bolt((p[0], p[1] + nn[1] * (r + 0.012), p[2] + nn[2] * (r + 0.012) + 0.0), nn, r=0.009, h=0.007, washer=False)
    return mb, bolts

def thrusters_and_lights(H):
    mb = MB()
    quads = [(3.9, 5), (3.6, 30), (20.9, 3), (20.9, 33)]
    for (s, j) in quads:
        i = H.si(s)
        for sd in (1, -1):
            p = np.array(H.pt(i, j, 0.06, sd)); n = np.array(H.nrm(i, j, sd))
            u, v = kit.basis(tuple(n))
            mb.obox(tuple(p + n * 0.04), tuple(np.array(u) * 0.20), tuple(np.array(v) * 0.20), tuple(n * 0.05), 'armour_gunmetal_d')
            for (a, b) in ((-0.09, -0.09), (0.09, -0.09), (-0.09, 0.09), (0.09, 0.09)):
                c = p + np.array(u) * a + np.array(v) * b + n * 0.09
                mb.lathe(tuple(c), tuple(n), [(0, 0.035), (0.07, 0.065), (0.07, 0.052), (0.0, 0.022)], 'machinery_heat', n=10, cap0=False, cap1=False)
            for (a, b) in ((-0.17, -0.17), (0.17, -0.17), (-0.17, 0.17), (0.17, 0.17)):
                mb.bolt(tuple(p + np.array(u) * a + np.array(v) * b + n * 0.09), tuple(n), r=0.012, h=0.008)
    # navigation lights: red to port, a white pair on the tail cowl, a beacon under the nose
    for sd, m in ((1, 'light_panel'), (-1, 'light_red')):
        p = H.pt(H.si(14.0), 18, 0.07, sd)
        mb.sphere(p, 0.07, m, n=10); mb.cyl((p[0] - 0.1, p[1], p[2]), (p[0] + 0.1, p[1], p[2]), 0.05, 'structure_steel', n=8)
    return mb

def build(H):
    parent = empty('gadgets', 'wayfarer')
    allb = MB()
    finish('nose_sensor_cap', nose(H), parent, group='gadgets')
    chin_cannon(parent)
    finish('ventral_gun_pod', belly_pod(), parent, group='gadgets')
    finish('keel_tanks', keel(), parent, group='gadgets')
    mb, b = dorsal(H); finish('dorsal_spine_and_arrays', mb, parent, group='gadgets'); allb.merge(b)
    mb, b = bay_contents(H); finish('equipment_bay_contents', mb, parent, group='gadgets'); allb.merge(b)
    mb, b = waist_conduits(H); finish('waist_conduits', mb, parent, group='gadgets'); allb.merge(b)
    finish('thruster_quads_and_lights', thrusters_and_lights(H), parent, group='gadgets')
    finish('gadget_bolts', allb, parent, sharp=60, group='fasteners')
    return dict(bays=len([n for n in H.openings if n.startswith('bay_')]) * 2)
