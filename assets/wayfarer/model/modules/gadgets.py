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
        kind = (0, 4, 1, 2, 4, 0, 3, 2)[int(name.split('_')[1]) % 8]      # not a repeating row: two bays are closed by armoured covers
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
            D = spec.BAYS['depth']
            if kind == 4:                                      # closed bay: an armoured cover flush with the hull, hinged below, latched above
                obox(-0.085, Ls + 0.085, -0.085, Lv + 0.085, D - 0.05, D + 0.012, 'armour_gunmetal_a')
                obox(0.03, Ls - 0.03, 0.03, Lv - 0.03, D + 0.012, D + 0.034, 'armour_gunmetal_c')
                for k in range(3):
                    a = Ls * (0.18 + 0.32 * k)
                    mb.cyl(P(a - 0.07, -0.085, D + 0.02), P(a + 0.07, -0.085, D + 0.02), 0.02, 'machinery_bare', n=8)
                    obox(a - 0.05, a + 0.05, -0.085, 0.02, D + 0.012, D + 0.02, 'structure_steel')
                    c = P(a, Lv + 0.02, D + 0.012)
                    mb.cyl(c, tuple(np.array(c) + en * 0.012), 0.03, 'machinery_bare', n=10)
                    obox(a - 0.022, a + 0.022, Lv + 0.016, Lv + 0.024, D + 0.024, D + 0.028, 'machinery_dark')
                nb = 6
                for k in range(nb + 1):
                    a = 0.0 + Ls * k / nb
                    bolts.bolt(P(a, 0.0, D + 0.034), tuple(en), r=0.014, h=0.01); bolts.bolt(P(a, Lv, D + 0.034), tuple(en), r=0.014, h=0.01)
                for k in range(1, 4):
                    bolts.bolt(P(0.0, Lv * k / 4, D + 0.034), tuple(en), r=0.014, h=0.01); bolts.bolt(P(Ls, Lv * k / 4, D + 0.034), tuple(en), r=0.014, h=0.01)
                obox(Ls * 0.36, Ls * 0.64, Lv * 0.70, Lv * 0.78, D + 0.034, D + 0.037, 'placard_white')
                obox(Ls * 0.10, Ls * 0.90, Lv * 0.16, Lv * 0.22, D + 0.034, D + 0.037, 'hazard_yellow')
                for k in range(6):
                    obox(Ls * (0.14 + 0.14 * k), Ls * (0.14 + 0.14 * k) + 0.05, Lv * 0.16, Lv * 0.22, D + 0.037, D + 0.039, 'machinery_dark')
                continue
            if kind in (1, 3):                                 # open bays get a guard: bars across at the hull line
                for f in (0.22, 0.5, 0.78):
                    mb.cyl(P(-0.09, Lv * f, D + 0.02), P(Ls + 0.09, Lv * f, D + 0.02), 0.016, 'structure_steel', n=8)
                for a in (-0.06, Ls + 0.06):
                    obox(a - 0.025, a + 0.025, 0.0, Lv, D - 0.005, D + 0.012, 'structure_steel')
                    for f in (0.22, 0.5, 0.78):
                        bolts.bolt(P(a, Lv * f + 0.05, D + 0.012), tuple(en), r=0.010, h=0.007)
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

# ------------------------------------------------------------------ outer hull detail: what a ground crew touches
SEG = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg',
       '9': 'abcdfg', 'F': 'aefg', '-': 'g'}

def hull_details(H):
    """Seam straps, access panels with latches, a rung ladder, lifting lugs, louvres, walkway rails, belly fittings and
    the hull number. Everything stands on a pad that starts at the nominal skin, because the armour plates sit at three
    heights and a fitting must not float over a low one."""
    mb = MB(); bolts = MB()
    TOPP = spec.PANEL_LAYERS[-1] + 0.025          # just proud of the highest plate

    def frame(i, j, sd, off=0.0):
        p = np.array(H.pt(i, j, off, sd)); n = np.array(H.nrm(i, j, sd)); n = n / np.linalg.norm(n)
        u = np.array((1.0, 0.0, 0.0)) - n * n[0]; u = u / np.linalg.norm(u)
        v = np.cross(n, u)
        if v[2] < 0 and abs(n[2]) < 0.9: v = -v                     # v points up the flank
        return p, n, u, v

    def clear(i, j, sd, ri=2, rj=1):
        a = H.tag[sd][max(i - ri, 0):min(i + ri, H.ni - 1), max(j - rj, 0):min(j + rj, H.nr)]
        return a.size > 0 and not a.any()

    def slab(p, n, u, v, hu, hv, z0, z1, m):
        """Box on the hull: centre p on the skin, half sizes hu x hv, from height z0 to z1 along the normal."""
        c = p + n * 0.5 * (z0 + z1); a, b, d = u * hu, v * hv, n * 0.5 * (z1 - z0)
        if np.dot(np.cross(a, b), d) < 0: b = -b
        mb.obox(tuple(c), tuple(a), tuple(b), tuple(d), m)

    # ---- A. seam straps round the barrel at the three main joints
    for s in (6.55, 13.8, 21.3):
        i = H.si(s)
        for sd in (1, -1):
            j = 1
            while j < 27:
                k = j
                while k < 27 and not H.tag[sd][i - 1, k] and not H.tag[sd][i, k]: k += 1
                if k > j:
                    H.rib_s(mb, i, j, k, sd, TOPP, 0.0, 0.07, 'armour_gunmetal_d')
                    for q in range(j, k + 1):
                        for ds in (-0.04, 0.04):
                            pp, n, u, v = frame(i, q, sd, TOPP)
                            bolts.bolt(tuple(pp + np.array((ds, 0, 0))), tuple(n), r=0.013, h=0.009)
                j = k + 1

    # ---- B. access panels: pad, door, four quarter-turn latches, hinge, placard
    panels = [(6.0, 7, 0.34, 0.22), (11.4, 7, 0.40, 0.24), (14.6, 8, 0.30, 0.20), (19.6, 7, 0.40, 0.24), (12.6, 5, 0.26, 0.26), (20.4, 5, 0.30, 0.20),
              (5.7, 25, 0.30, 0.20), (9.8, 25, 0.36, 0.22), (13.6, 25, 0.26, 0.26), (16.0, 25, 0.40, 0.22), (19.2, 25, 0.30, 0.20), (3.3, 21, 0.26, 0.18), (3.6, 9, 0.24, 0.18)]
    for q, (s, j, hu, hv) in enumerate(panels):
        i = H.si(s)
        for sd in (1, -1):
            if not clear(i, j, sd): continue
            p, n, u, v = frame(i, j, sd)
            slab(p, n, u, v, hu + 0.04, hv + 0.04, 0.0, TOPP, 'armour_gunmetal_d')
            slab(p, n, u, v, hu, hv, TOPP, TOPP + 0.012, ('armour_gunmetal_c', 'armour_gunmetal_a', 'armour_paint_red_dark')[q % 3])
            for (a, b) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                c = p + u * a * (hu - 0.05) + v * b * (hv - 0.05) + n * (TOPP + 0.012)
                mb.cyl(tuple(c), tuple(c + n * 0.008), 0.022, 'machinery_bare', n=10)
                slab(c - n * 0.0, n, u, v, 0.017, 0.003, 0.008, 0.011, 'machinery_dark')
                bolts.bolt(tuple(p + u * a * (hu + 0.02) + v * b * (hv + 0.02) + n * TOPP), tuple(n), r=0.010, h=0.007)
            for a in (-0.5, 0.5):                                                                      # hinge barrels on the lower edge
                c = p + u * a * hu - v * (hv + 0.012) + n * (TOPP + 0.008)
                mb.cyl(tuple(c - u * 0.05), tuple(c + u * 0.05), 0.011, 'machinery_bare', n=6)
            slab(p + v * (hv * 0.35), n, u, v, hu * 0.45, 0.022, TOPP + 0.012, TOPP + 0.014, 'placard_white')
            if q % 3 == 2:
                slab(p - v * (hv * 0.3), n, u, v, hu * 0.6, 0.018, TOPP + 0.012, TOPP + 0.014, 'hazard_yellow')

    # ---- C. rung ladder up the flank just aft of the canopy, both sides
    i = H.si(4.55)
    for sd in (1, -1):
        for j in range(3, 26):
            if not clear(i, j, sd, ri=1, rj=0) and H.tag[sd][i, j]: continue
            p, n, u, v = frame(i, j, sd)
            slab(p, n, u, v, 0.24, 0.035, 0.0, TOPP, 'armour_gunmetal_d')
            a, b = p - u * 0.19, p + u * 0.19
            m = 'hazard_yellow' if j in (3, 25) else 'machinery_bare'
            mb.pipe([tuple(a + n * TOPP), tuple(a + n * (TOPP + 0.085)), tuple(b + n * (TOPP + 0.085)), tuple(b + n * TOPP)], 0.013, m, n=6)
            for c in (a, b):
                bolts.bolt(tuple(c + u * 0.035 * (1 if c is b else -1) + n * TOPP), tuple(n), r=0.009, h=0.006, washer=False)

    # ---- D. lifting lugs on the shoulders
    for s in (7.0, 12.0, 14.4, 20.0):
        i = H.si(s)
        for sd in (1, -1):
            if not clear(i, 6, sd): continue
            p, n, u, v = frame(i, 6, sd)
            slab(p, n, u, v, 0.16, 0.12, 0.0, TOPP + 0.01, 'structure_steel')
            c = p + n * (TOPP + 0.07)
            mb.tube(tuple(c - v * 0.02), tuple(c + v * 0.02), 0.065, 0.03, 'hazard_yellow', n=14)
            slab(p, n, u, v, 0.07, 0.02, TOPP + 0.01, TOPP + 0.04, 'structure_steel')
            for (a, b) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                bolts.bolt(tuple(p + u * a * 0.12 + v * b * 0.085 + n * (TOPP + 0.01)), tuple(n), r=0.013, h=0.009)

    # ---- E. louvred vents low on the flank
    for s in (11.5, 17.3, 7.4):
        i = H.si(s)
        for sd in (1, -1):
            if not clear(i, 24, sd, ri=3): continue
            p, n, u, v = frame(i, 24, sd)
            slab(p, n, u, v, 0.36, 0.17, 0.0, TOPP + 0.02, 'armour_gunmetal_d')
            slab(p, n, u, v, 0.31, 0.12, TOPP + 0.02, TOPP + 0.022, 'substructure_dark')
            for k in range(5):
                c = p + v * (-0.096 + 0.048 * k) + n * (TOPP + 0.03)
                a, b, d = u * 0.31, (v * 0.6 + n * 0.8) / 1.0 * 0.022, (n * 0.6 - v * 0.8) * 0.003
                if np.dot(np.cross(a, b), d) < 0: b = -b
                mb.obox(tuple(c), tuple(a), tuple(b), tuple(d), 'machinery_dark')
            for (a, b) in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1)):
                bolts.bolt(tuple(p + u * a * 0.335 + v * b * 0.145 + n * (TOPP + 0.02)), tuple(n), r=0.010, h=0.007)

    # ---- I. walkway rails and non-slip pads either side of the spine
    ia, ib = H.si(10.4), H.si(14.7)
    for sd in (1, -1):
        pts = []
        for i in range(ia, ib + 1, 3):
            p, n, u, v = frame(i, 4, sd)
            pts.append(tuple(p + n * 0.42))
            mb.cyl(tuple(p), tuple(p + n * 0.42), 0.014, 'machinery_bare', n=6)
            slab(p, n, u, v, 0.05, 0.05, 0.0, TOPP, 'structure_steel')
        mb.pipe(pts, 0.016, 'hazard_yellow', n=6)
        for i in range(ia + 1, ib, 4):
            p, n, u, v = frame(i, 2, sd)
            slab(p, n, u, v, 0.26, 0.11, 0.0, TOPP + 0.004, 'rubber_black')

    # ---- F. formation light strips between the waist and the bays; flood lamps over the lift
    for s in (10.2, 17.9):
        i = H.si(s)
        for sd in (1, -1):
            if not clear(i, 18, sd, ri=3, rj=0): continue
            p, n, u, v = frame(i, 18, sd)
            slab(p, n, u, v, 0.34, 0.035, 0.0, TOPP, 'armour_gunmetal_d'); slab(p, n, u, v, 0.30, 0.018, TOPP, TOPP + 0.008, 'screen_glow')
    for s in (9.25, 13.5):
        i = H.si(s)
        for sd in (1, -1):
            if not clear(i, 32, sd, ri=1): continue
            p, n, u, v = frame(i, 32, sd)
            slab(p, n, u, v, 0.11, 0.08, 0.0, TOPP + 0.05, 'machinery_dark'); slab(p, n, u, v, 0.085, 0.055, TOPP + 0.05, TOPP + 0.056, 'light_panel')

    # ---- G. belly: drain masts, ground power receptacle, a blade antenna
    for (s, j, kind) in ((4.4, 33, 'mast'), (8.95, 33, 'mast'), (4.9, 31, 'gpu'), (3.7, 34, 'blade')):
        i = H.si(s)
        for sd in ((1, -1) if kind != 'gpu' else (-1,)):
            if not clear(i, min(j, H.nr - 1), sd, ri=1): continue
            p, n, u, v = frame(i, j, sd)
            slab(p, n, u, v, 0.10, 0.06, 0.0, TOPP, 'structure_steel')
            if kind == 'mast':
                mb.cyl(tuple(p + n * TOPP), tuple(p + n * (TOPP + 0.16) + u * 0.06), 0.014, 'machinery_bare', n=6)
            elif kind == 'blade':
                a, b, c, d = p - u * 0.14 + n * TOPP, p + u * 0.14 + n * TOPP, p + u * 0.16 + n * (TOPP + 0.26), p + u * 0.06 + n * (TOPP + 0.26)
                e = v * 0.022
                mb.prism([tuple(x - e * 0.5) for x in (a, b, c, d)], tuple(e), 'machinery_dark')
            else:
                slab(p, n, u, v, 0.22, 0.14, 0.0, TOPP + 0.012, 'armour_gunmetal_c')
                for a in (-0.10, 0.02, 0.12):
                    c = p + u * a + n * (TOPP + 0.012)
                    mb.cyl(tuple(c), tuple(c + n * 0.03), 0.035 if a < 0 else 0.022, 'machinery_bare', n=10)
                    mb.cyl(tuple(c + n * 0.03), tuple(c + n * 0.033), 0.026 if a < 0 else 0.015, 'copper_pipe' if a < 0 else 'hazard_yellow', n=10)
                slab(p + v * 0.09, n, u, v, 0.16, 0.02, TOPP + 0.012, TOPP + 0.014, 'placard_white')

    # ---- H. hull number forward of the waist, reading nose-to-tail from outside on both sides
    segs = dict(a=(0, 1, 1, 0), d=(0, -1, 1, 0), g=(0, 0, 1, 0), f=(-1, 0.5, 0, 1), b=(1, 0.5, 0, 1), e=(-1, -0.5, 0, 1), c=(1, -0.5, 0, 1))
    hh = 0.20; ww = 0.11; pitch = 0.36; text = 'F-27'
    i = H.si(5.62)
    for sd in (1, -1):
        p, n, u, v = frame(i, 17, sd)
        slab(p, n, u, v, 0.76, 0.32, 0.0, TOPP, 'armour_gunmetal_d')
        rd = u if sd < 0 else -u                    # reading direction as seen from outside
        for k, ch in enumerate(text):
            c0 = p + rd * (k - (len(text) - 1) / 2) * pitch
            for sg in SEG[ch]:
                cx, cy, hor, ver = segs[sg]
                c = c0 + rd * cx * ww + v * cy * hh * 1.0
                slab(c, n, rd, v, (ww * (0.6 if ch == '-' else 1.0)) if hor else 0.022, 0.022 if hor else hh / 2, TOPP, TOPP + 0.004, 'placard_white')
    return mb, bolts

def strakes(H):
    """The bare strakes between the armour belts carry the ship's services: conduit runs clamped to the skin that
    disappear into junction boxes, and ribbed stiffener panels between them."""
    mb = MB(); bolts = MB()
    def pt(i, jf, off, sd):
        j = int(math.floor(jf)); f = jf - j
        a = np.array(H.pt(i, j, off, sd)); b = np.array(H.pt(i, min(j + 1, H.nr), off, sd))
        n = np.array(H.nrm(i, j, sd)) * (1 - f) + np.array(H.nrm(i, min(j + 1, H.nr), sd)) * f
        return a + (b - a) * f, n / np.linalg.norm(n)
    def free(i, jf, sd):
        j = int(math.floor(jf))
        return 0 <= i < H.ni - 1 and not H.tag[sd][i, j] and not H.tag[sd][max(i - 1, 0), j]
    def box(c, n, u, v, hu, hv, z0, z1, m):
        cc = c + n * 0.5 * (z0 + z1); a, b, d = u * hu, v * hv, n * 0.5 * (z1 - z0)
        if np.dot(np.cross(a, b), d) < 0: b = -b
        mb.obox(tuple(cc), tuple(a), tuple(b), tuple(d), m)
    runs = (   # row (fractional), pipes as (offset across in rows, radius, material), from s, to s, junction box pitch
        (10.5, ((-0.22, 0.026, 'machinery_dark'), (0.0, 0.019, 'copper_pipe'), (0.20, 0.022, 'machinery_bare')), 4.9, 21.2, 3.2),
        (27.0, ((-0.30, 0.030, 'machinery_dark'), (-0.05, 0.020, 'machinery_bare'), (0.22, 0.017, 'copper_pipe')), 5.0, 21.2, 4.0),
        (18.0, ((-0.62, 0.018, 'machinery_dark'), (0.46, 0.018, 'machinery_bare')), 7.4, 20.9, 0.0),
    )
    for jf, pipes, sa, sb, pitch in runs:
        ia, ib = H.si(sa), H.si(sb)
        jb = set(H.si(sa + 0.6 + k * pitch) for k in range(int((sb - sa) / pitch) + 1)) if pitch else set()
        for sd in (1, -1):
            for (dj, r, m) in pipes:
                seg = []
                def flush():
                    if len(seg) >= 2:
                        mb.pipe([tuple(x) for x in seg], r, m, n=6)
                    seg.clear()
                for i in range(ia, ib + 1):
                    if not free(i, jf + dj, sd): flush(); continue
                    p, n = pt(i, jf + dj, r + 0.014, sd)
                    seg.append(p)
                    if (i - ia) % 4 == 2 and i not in jb:                    # saddle clamp
                        p0, _ = pt(i, jf + dj, 0.0, sd)
                        u = np.array((1.0, 0, 0)); v = np.cross(n, u); v /= np.linalg.norm(v)
                        box(p0, n, u, v, 0.022, r + 0.022, 0.0, 2 * r + 0.022, 'structure_steel')
                        for sg in (-1, 1):
                            bolts.bolt(tuple(p0 + v * sg * (r + 0.012) + n * (2 * r + 0.022)), tuple(n), r=0.007, h=0.005, washer=False)
                flush()
            for i in jb:                                                    # junction boxes the runs pass through
                if not all(free(i + d, jf + dj, sd) for d in (-1, 0, 1) for dj in (-0.3, 0.3)): continue
                p0, n = pt(i, jf, 0.0, sd)
                u = np.array((1.0, 0, 0)) - n * n[0]; u /= np.linalg.norm(u); v = np.cross(n, u)
                hv = 0.5 * np.linalg.norm(np.array(H.pt(i, int(jf) + 1, 0, sd)) - np.array(H.pt(i, int(jf), 0, sd))) * 0.86
                box(p0, n, u, v, 0.20, hv, 0.0, 0.085, 'armour_gunmetal_d')
                box(p0, n, u, v, 0.17, hv - 0.03, 0.085, 0.097, 'armour_gunmetal_c')
                box(p0 + u * 0.06, n, u, v, 0.06, 0.02, 0.097, 0.099, 'placard_white')
                for (a, b) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    bolts.bolt(tuple(p0 + u * a * 0.15 + v * b * (hv - 0.05) + n * 0.097), tuple(n), r=0.010, h=0.007)
                for sg in (-1, 1):                                          # glands where the pipes enter
                    for (dj, r, m) in pipes:
                        g, gn = pt(i, jf + dj, r + 0.014, sd)
                        mb.cyl(tuple(g + u * sg * 0.20), tuple(g + u * sg * 0.235), r + 0.012, 'machinery_bare', n=8)
    # ribbed stiffener panels on the waistline strake, between the bays' pillars
    for s in np.arange(8.3, 20.4, 1.6):
        if min(abs(s - x) for x in (10.2, 14.0, 17.9)) < 0.95: continue          # leave the lights clear
        i = H.si(float(s))
        for sd in (1, -1):
            if not all(free(i + d, 17.2, sd) and free(i + d, 18.6, sd) for d in (-2, 0, 2)): continue
            p0, n = pt(i, 18.0, 0.0, sd)
            u = np.array((1.0, 0, 0)) - n * n[0]; u /= np.linalg.norm(u); v = np.cross(n, u)
            box(p0, n, u, v, 0.36, 0.10, 0.0, 0.02, 'armour_gunmetal_d')
            for k in range(7):
                box(p0 + u * (-0.30 + 0.10 * k), n, u, v, 0.022, 0.085, 0.02, 0.038, 'armour_gunmetal_b')
            for (a, b) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                bolts.bolt(tuple(p0 + u * a * 0.335 + v * b * 0.075 + n * 0.02), tuple(n), r=0.008, h=0.006, washer=False)
    return mb, bolts

def markings(H):
    """Stencilled paint and hand-holds, sized to people: frame numbers at every ring frame, a dashed no-step line along
    the roof walkway, a number under every equipment bay, a rescue arrow at the crew hatch, grab handles between
    the bays. Paint is 3 mm of geometry standing on whatever plate is there."""
    import fuselage
    mb = MB(); bolts = MB()
    segs = dict(a=(0, 1, 1, 0), d=(0, -1, 1, 0), g=(0, 0, 1, 0), f=(-1, 0.5, 0, 1), b=(1, 0.5, 0, 1), e=(-1, -0.5, 0, 1), c=(1, -0.5, 0, 1))
    def top(j):
        bt = fuselage.belt(j + 0.01); return (bt[0] if bt else 0.0) + 0.002
    def heavy(i, j):
        s = H.st[i]; return (11 <= j < 14 or 23 <= j < 26) and (4.2 < s < 7.4 or 18.8 < s < 21.8)
    def free(i, j, sd, di=1):
        return all(0 <= a < H.ni - 1 and not H.tag[sd][a, b] for a in range(i - di, i + di + 1) for b in (j - 1, j)) and not heavy(i, j)
    def frame(i, j, sd):
        p = np.array(H.pt(i, j, 0.0, sd)); n = np.array(H.nrm(i, j, sd)); n = n / np.linalg.norm(n)
        u = np.array((1.0, 0.0, 0.0)) - n * n[0]; u = u / np.linalg.norm(u)
        v = np.cross(n, u)
        if v[2] < 0 and abs(n[2]) < 0.9: v = -v
        return p, n, u, v
    def slab(c, n, u, v, hu, hv, z0, m):
        P = [c + u * a * hu + v * b * hv + n * z for z in (z0, z0 + 0.003) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ix = [mb.v(tuple(q)) for q in P]
        for q in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            a, b, c2 = P[q[0]], P[q[1]], P[q[2]]
            f = [ix[t] for t in q]
            mb.f(f if np.dot(np.cross(b - a, c2 - a), (a + c2) / 2 - (c - n)) > 0 else f[::-1], m)
    def text(c, n, rd, v, s, hh, z0, m='stencil_white'):
        ww = hh * 0.55; pitch = hh * 1.8; t = max(0.012, hh * 0.13)
        for k, ch in enumerate(s):
            c0 = c + rd * (k - (len(s) - 1) / 2) * pitch
            for sg in SEG[ch]:
                cx, cy, hor, ver = segs[sg]
                slab(c0 + rd * cx * ww + v * cy * hh, n, rd, v, ww * 0.8 if hor else t, t if hor else hh * 0.42, z0, m)
    frames = [(s, H.si(s)) for s in np.arange(2.0, 28.5, 2.0)]
    for sd in (1, -1):
        # frame numbers, just aft of each ring frame on the upper flank and the lower flank
        for s, i in frames:
            for j in (12,):
                ii = i + 1
                if not free(ii, j, sd): continue
                p, n, u, v = frame(ii, j, sd); rd = u if sd < 0 else -u
                text(p + u * 0.10, n, rd, v, 'F%d' % int(round(s)), 0.045, top(j))
        # the no-step line along the edge of the roof walkway: dashes, and a red block at each frame
        for i in range(H.si(3.0), H.si(27.0)):
            if not free(i, 5, sd, 0) or i % 2: continue
            p, n, u, v = frame(i, 5, sd)
            slab(p, n, u, v, 0.09, 0.016, top(5), 'stencil_red')
        # a number under every equipment bay
        nb = 0
        for name, r in sorted(H.openings.items()):
            if not name.startswith('bay_'): continue
            i0, i1, j0, j1 = H.rect(name)[:4]; nb += 1
            im = i0 + 1; j = j1 + 1
            if j < H.nr and not H.tag[sd][im, j] and not H.tag[sd][im, j - 1] and fuselage.belt(j + 0.01):
                p, n, u, v = frame(im, j, sd); rd = u if sd < 0 else -u
                text(p - v * 0.06, n, rd, v, '%d-%d' % (2 if sd > 0 else 1, nb), 0.04, top(j))
            # a grab handle each side of the bay, for whoever is up on a stand
            jm = (j0 + j1) // 2
            for i in (i1 + 1,):
                if not (1 < i < H.ni - 2) or any(H.tag[sd][a, b] for a in (i - 1, i) for b in (jm - 1, jm)): continue
                p, n, u, v = frame(i, jm, sd); z = top(jm) - 0.002
                a = p + v * 0.16 + n * z; b = p - v * 0.16 + n * z
                mb.cyl(tuple(a), tuple(a + n * 0.07), 0.011, 'machinery_bare', n=8); mb.cyl(tuple(b), tuple(b + n * 0.07), 0.011, 'machinery_bare', n=8)
                mb.cyl(tuple(a + n * 0.07), tuple(b + n * 0.07), 0.014, 'hazard_yellow', n=8)
                for q in (a, b):
                    slab(q - n * 0.0, n, u, v, 0.035, 0.035, 0.0, 'machinery_dark')
                    bolts.bolt(tuple(q + u * 0.024 + n * 0.003), tuple(n), r=0.007, h=0.005, washer=False)
                    bolts.bolt(tuple(q - u * 0.024 + n * 0.003), tuple(n), r=0.007, h=0.005, washer=False)
    # rescue arrow pointing at the crew hatch (port side), from forward of it
    if 'crew_hatch' in H.openings:
        i0, i1, j0, j1 = H.rect('crew_hatch')[:4]; sd = spec.CREW_HATCH['side'] if hasattr(spec, 'CREW_HATCH') else -1
        i = i0 - 3; j = (j0 + j1) // 2
        if i > 2 and not H.tag[sd][i, j]:
            p, n, u, v = frame(i, j, sd); z = top(j) + (0.036 if heavy(i, j) else 0.0)
            slab(p - u * 0.06, n, u, v, 0.14, 0.022, z, 'stencil_red')
            for sgn in (1, -1):
                d = (u * 0.75 + v * sgn * 0.66); d = d / np.linalg.norm(d); w = np.cross(n, d)
                slab(p + u * 0.10 - d * 0.07 + v * 0.0, n, d, w, 0.08, 0.02, z, 'stencil_red')
    return mb, bolts

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
    mb, b = hull_details(H); finish('hull_details', mb, parent, group='gadgets'); allb.merge(b)
    mb, b = strakes(H); finish('hull_strakes', mb, parent, group='gadgets'); allb.merge(b)
    mb, b = markings(H); finish('hull_markings', mb, parent, group='gadgets'); allb.merge(b)
    finish('gadget_bolts', allb, parent, sharp=60, group='fasteners')
    return dict(bays=len([n for n in H.openings if n.startswith('bay_')]) * 2)
