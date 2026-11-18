"""Lander bay, the internal landing array: two belly doors, an overhead cradle on four jack screws, and a small
lander stowed in it. Rest pose is closed and stowed; the clip 'lander_bay_open' opens the doors and lowers the
cradle until the lander hangs clear below the belly.

The lander here is a stub at the right size and mass points (hull, four folded legs, canopy, thrusters): it is its
own object under the cradle so a full lander asset can replace it later without touching the bay."""
import math
import numpy as np
import spec, kit
from kit import MB, finish, empty, key, smooth_keys

Lb = spec.LANDER_BAY; Ld = spec.LANDER
S0, S1 = Lb['s0'], Lb['s1']; SC = 0.5 * (S0 + S1)
ZD = spec.Z_LOWER
ZCEIL = spec.Z_MAIN - spec.DECK_T
LANDER_Z0 = ZD + 0.06                 # underside of the stowed lander
DROP = 1.45
DOOR_OPEN = math.radians(100)
JY = 1.22
JACKS = [(S0 + 0.9, JY), (S0 + 0.9, -JY), (S1 - 0.9, JY), (S1 - 0.9, -JY)]
ARM = 0.39

def lander():
    mb = MB(); L, W, Hh = Ld['length'], Ld['width'], Ld['height']
    s0 = SC - L / 2; z0 = LANDER_Z0 + 0.22
    # hull: a faceted lifting body, side profile extruded across the beam, with chamfered chines
    prof = [(0.0, 0.45), (0.55, 0.12), (1.6, 0.0), (L - 0.9, 0.0), (L, 0.30), (L, Hh * 0.62), (L - 0.5, Hh * 0.80), (2.3, Hh * 0.80), (1.45, Hh * 0.60), (0.25, 0.72)]
    for (y0, y1, k) in ((-W / 2 + 0.22, W / 2 - 0.22, 1.0),):
        mb.prism([(s0 + a, y0, z0 + b) for a, b in prof], (0, y1 - y0, 0), 'armour_gunmetal_c')
    for sy in (-1, 1):                                      # chine blisters
        yy = sy * (W / 2 - 0.22)
        mb.prism([(s0 + a, yy, z0 + b * 0.82 + 0.06) for a, b in prof[1:8]], (0, sy * 0.20, 0), 'armour_gunmetal_b')
        mb.box(s0 + 1.9, s0 + L - 1.2, yy + sy * 0.20, yy + sy * 0.215, z0 + 0.34, z0 + 0.52, 'armour_paint_red')
    # canopy
    mb.prism([(s0 + 0.45, -0.55, z0 + 0.76), (s0 + 1.42, -0.55, z0 + Hh * 0.62), (s0 + 1.42, -0.55, z0 + 0.80), (s0 + 0.5, -0.55, z0 + 0.74)], (0, 1.1, 0), 'glass_canopy')
    # four thruster pods at the corners
    for (a, sy) in ((1.5, 1), (1.5, -1), (L - 1.1, 1), (L - 1.1, -1)):
        c = (s0 + a, sy * (W / 2 - 0.02), z0 + 0.42)
        mb.cyl((c[0] - 0.30, c[1], c[2]), (c[0] + 0.30, c[1], c[2]), 0.17, 'machinery_dark', n=14)
        mb.lathe((c[0], c[1], c[2] - 0.10), (0, 0, -1), [(0, 0.12), (0.10, 0.10), (0.26, 0.17), (0.26, 0.15), (0.10, 0.08)], 'machinery_heat', n=14, cap0=False, cap1=False)
    # folded landing legs under the body
    for (a, sy) in ((1.3, 1), (1.3, -1), (L - 1.4, 1), (L - 1.4, -1)):
        p0 = (s0 + a, sy * 0.70, z0 + 0.02); p1 = (s0 + a + 0.75, sy * 0.78, z0 - 0.10)
        mb.cyl(p0, p1, 0.04, 'structure_steel', n=8); mb.cyl((p1[0], p1[1], p1[2] - 0.05), (p1[0], p1[1], p1[2] - 0.01), 0.14, 'armour_gunmetal_d', n=12)
    # main engine bell at the tail
    mb.lathe((s0 + L, 0, z0 + 0.48), (1, 0, 0), [(0, 0.20), (0.06, 0.18), (0.34, 0.34), (0.34, 0.31), (0.06, 0.14)], 'machinery_heat', n=20, cap0=False, cap1=False)
    # hard points the cradle clamps onto
    for (s, y) in JACKS:
        mb.box(s - 0.10, s + 0.10, math.copysign(abs(y) - ARM, y) - 0.06, math.copysign(abs(y) - ARM, y) + 0.06, z0 + Hh * 0.80, z0 + Hh * 0.80 + 0.05, 'hazard_yellow')
    return mb

def cradle():
    mb = MB(); st = 'structure_steel'
    zt = LANDER_Z0 + 0.22 + Ld['height'] * 0.80 + 0.05          # top of the lander's hard points
    zf = zt + 0.16                                              # underside of the cradle frame
    for y in (-JY, JY):
        mb.box(S0 + 0.5, S1 - 0.5, y - 0.05, y + 0.05, zf, zf + 0.12, st)
    for s in (S0 + 0.9, SC, S1 - 0.9):
        mb.box(s - 0.05, s + 0.05, -JY, JY, zf, zf + 0.12, st)
    for (s, y) in JACKS:                                        # clamp arms and jaws
        yc = math.copysign(abs(y) - ARM, y)
        mb.box(s - 0.06, s + 0.06, yc - 0.05, yc + 0.05, zt + 0.02, zf, st)
        mb.box(s - 0.05, s + 0.05, min(yc, y), max(yc, y), zf - 0.06, zf, st)
        mb.box(s - 0.13, s + 0.13, yc - 0.10, yc + 0.10, zt - 0.02, zt + 0.02, 'machinery_bare')
        mb.bolt_circle((s, y, zf + 0.12), (0, 0, 1), 0.085, 6, r=0.013, h=0.009)
        mb.cyl((s, y, zf + 0.12), (s, y, zf + 0.20), 0.065, 'machinery_dark', n=14)       # jack nut housing
    # umbilical loom
    mb.pipe([(SC + 0.3, 0.2, zf + 0.12), (SC + 0.3, 0.2, zf + 0.02), (SC + 0.1, 0.1, zt + 0.0)], 0.03, 'cable_black', n=8)
    return mb, zf

def build(H):
    parent = empty('lander_bay', 'wayfarer', at=(SC, 0, ZD))
    i0, i1, j0, j1, _ = H.rect('lander_doors')
    for sd, sn in ((1, 'stbd'), (-1, 'port')):
        d = MB()
        H.slab(d, i0, i1, j0, j1, sd, 0.035, -0.09, 'armour_gunmetal_b', 'structure_primer', 'structure_steel', margin=0.018)
        for i in range(i0 + 2, i1 - 1, 4):
            H.rib_s(d, i, j0, j1, sd, -0.09, -0.16, 0.025, 'structure_steel')
        for i in range(i0 + 1, i1, 5):
            p = H.pt(i, j0, 0.05, sd); d.cyl((p[0] - 0.12, p[1], p[2]), (p[0] + 0.12, p[1], p[2]), 0.035, 'machinery_bare', n=8)
        B = H.nodes(i0, i1, j0, j1, 0.035, sd, margin=0.10)
        for a in range(0, B.shape[0], 2):
            d.bolt(tuple(B[a, 0]), H.nrm(i0 + a, j0, sd), r=0.018, h=0.012)
        hinge = H.nodes(i0, i1, j0, j0, 0.0, sd).reshape(-1, 3); hp = tuple(hinge.mean(axis=0))
        name = f'lander_door_{sn}'
        finish(name, d, parent, pivot=hp, group='lander_bay')
        ang = math.copysign(DOOR_OPEN, sd)        # free edge is inboard of the hinge: starboard opens with +, port with -
        key('lander_bay_open', name, 0, rot=(0, 0, 0)); smooth_keys('lander_bay_open', name, 0, 48, rot=(ang, 0, 0))
        # door actuators (fixed stubs on the catwalk edge)
    fixed = MB(); st = 'structure_steel'
    cr, zf = cradle()
    for (s, y) in JACKS:                                         # jack screws from the ceiling
        fixed.cyl((s, y, zf - DROP - 0.05), (s, y, ZCEIL - 0.08), 0.032, 'machinery_bare', n=12)
        fixed.box(s - 0.14, s + 0.14, y - 0.14, y + 0.14, ZCEIL - 0.10, ZCEIL, st)
        fixed.cyl((s, y, ZCEIL - 0.26), (s, y, ZCEIL - 0.10), 0.09, 'machinery_dark', n=14)   # gearbox
        fixed.bolt_circle((s, y, ZCEIL - 0.10), (0, 0, -1), 0.115, 4, r=0.014, h=0.009)
    for y in (-JY, JY):                                      # drive shaft linking the jacks on each side
        fixed.cyl((S0 + 0.9, y + 0.0, ZCEIL - 0.18), (S1 - 0.9, y, ZCEIL - 0.18), 0.02, 'machinery_bare', n=8)
    # guard rails along both catwalks, facing the opening
    hw = Lb['door_half'] + 0.04
    for sy in (-1, 1):
        y = sy * hw
        for z in (ZD + 0.55, ZD + 1.05):
            fixed.cyl((S0 + 0.05, y, z), (S1 - 0.05, y, z), 0.02, 'hazard_yellow' if z > ZD + 1 else 'machinery_bare', n=8)
        for k in range(9):
            s = S0 + 0.05 + k * (S1 - S0 - 0.1) / 8
            fixed.cyl((s, y, ZD), (s, y, ZD + 1.05), 0.018, 'machinery_bare', n=8)
            fixed.bolt((s + 0.04, y, ZD), (0, 0, 1), r=0.01, h=0.007); fixed.bolt((s - 0.04, y, ZD), (0, 0, 1), r=0.01, h=0.007)
        fixed.box(S0, S1, y - 0.05, y + 0.05, ZD, ZD + 0.006, 'hazard_yellow')
    finish('lander_bay_fixtures', fixed, parent, group='lander_bay')
    finish('lander_cradle', cr, parent, pivot=(SC, 0, zf), group='lander_bay')
    finish('lander_stub', lander(), 'lander_cradle', pivot=(SC, 0, LANDER_Z0), group='lander_bay')
    key('lander_bay_open', 'lander_cradle', 0, loc=(0, 0, 0)); smooth_keys('lander_bay_open', 'lander_cradle', 48, 132, loc=(0, 0, -DROP))
    return dict(clip='lander_bay_open', frames=132, lander=(Ld['length'], Ld['width'], Ld['height']), drop=DROP)
