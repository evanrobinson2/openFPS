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
    # plan bracing, sway pads against the lander's flanks, clamp rams, status lamps at both ends
    for (sa, sb) in ((S0 + 0.9, SC), (SC, S1 - 0.9)):
        mb.cyl((sa, -JY, zf + 0.06), (sb, JY, zf + 0.06), 0.02, st, n=8); mb.cyl((sa, JY, zf + 0.06), (sb, -JY, zf + 0.06), 0.02, st, n=8)
    hwl = Ld['width'] / 2
    for (s, y) in JACKS:
        sy = math.copysign(1, y)
        for ds in (-0.55, 0.55):
            sp = s + ds if S0 + 0.6 < s + ds < S1 - 0.6 else s - ds * 0.6
            mb.box(sp - 0.03, sp + 0.03, sy * (hwl + 0.07), sy * JY, zf - 0.03, zf, st)
            mb.box(sp - 0.03, sp + 0.03, sy * (hwl + 0.07), sy * (hwl + 0.11), zt - 0.42, zf, st)
            mb.box(sp - 0.09, sp + 0.09, sy * (hwl + 0.012), sy * (hwl + 0.07), zt - 0.44, zt - 0.22, 'rubber_black')
        yc = math.copysign(abs(y) - ARM, y)
        mb.cyl((s + 0.09, yc, zt + 0.06), (s + 0.09, y - sy * 0.06, zf - 0.02), 0.022, 'machinery_dark', n=8)      # clamp ram
        mb.cyl((s + 0.09, yc, zt + 0.04), (s + 0.09, yc + sy * 0.1, zt + 0.10), 0.012, 'hydraulic_chrome', n=6)
    for s in (S0 + 0.5, S1 - 0.5):
        for q, mm in enumerate(('screen_glow', 'hazard_yellow', 'light_red')):
            mb.box(s - 0.012 if s < SC else s, s if s < SC else s + 0.012, -0.12 + 0.09 * q, -0.06 + 0.09 * q, zf + 0.03, zf + 0.09, mm)
    mb.box(SC - 0.20, SC + 0.20, -JY - 0.052, -JY - 0.05, zf + 0.02, zf + 0.10, 'placard_white')
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
    # jack drive: a motor and gearbox each side on the ceiling, a cross shaft between them, stop collars on the screws
    for sy in (-1, 1):
        y = sy * JY
        fixed.box(SC - 0.22, SC + 0.22, y - 0.13, y + 0.13, ZCEIL - 0.13, ZCEIL, 'machinery_dark')
        fixed.cyl((SC - 0.22, y, ZCEIL - 0.07), (SC - 0.50, y, ZCEIL - 0.07), 0.06, 'armour_gunmetal_c', n=14)            # motor
        fixed.cyl((SC - 0.50, y, ZCEIL - 0.07), (SC - 0.53, y, ZCEIL - 0.07), 0.045, 'machinery_bare', n=12)
        fixed.bolt_circle((SC, y, ZCEIL - 0.13), (0, 0, -1), 0.09, 6, r=0.01, h=0.007)
        fixed.box(S0 + 0.3, S1 - 0.3, sy * 1.85, sy * 2.0, ZCEIL - 0.02, ZCEIL, 'light_panel')                              # light over the catwalk
    fixed.cyl((SC + 0.12, -JY, ZCEIL - 0.07), (SC + 0.12, JY, ZCEIL - 0.07), 0.018, 'machinery_bare', n=8)
    for (s, y) in JACKS:
        fixed.cyl((s, y, zf - DROP - 0.05), (s, y, zf - DROP - 0.01), 0.05, st, n=12)
        fixed.bolt((s, y, zf - DROP - 0.05), (0, 0, -1), r=0.012, h=0.008, washer=False)
        fixed.box(s - 0.02, s + 0.02, y, math.copysign(abs(y) + 0.16, y), ZCEIL - 0.03, ZCEIL, 'cable_black')              # cable tray to the motor
    # catwalk fittings. Starboard: control pedestal forward, a refuelling hose reel amidships, maintenance trestles aft
    def wall(s, z): return float(spec.lining_half_width(s, z)) - 0.03
    ps, py = S0 + 0.45, 1.85
    fixed.box(ps - 0.12, ps + 0.12, py - 0.16, py + 0.16, ZD, ZD + 0.95, 'lining_panel_dark')
    fixed.prism([(ps - 0.16, py - 0.18, ZD + 0.95), (ps + 0.16, py - 0.18, ZD + 0.95), (ps + 0.16, py - 0.18, ZD + 1.10)], (0, 0.36, 0), 'lining_panel_dark')
    sl = kit.vnorm((0.32, 0, 0.15)); nn = (-sl[2], 0, sl[0])
    for q, mm in enumerate(('screen_glow', 'hazard_yellow', 'light_red', 'machinery_bare')):
        fixed.cyl(kit.vadd((ps - 0.05, py - 0.11 + 0.075 * q, ZD + 1.002), kit.vmul(nn, 0.0)), kit.vadd((ps - 0.05, py - 0.11 + 0.075 * q, ZD + 1.002), kit.vmul(nn, 0.02)), 0.018, mm, n=8)
    fixed.obox(kit.vadd((ps + 0.07, py, ZD + 1.058), kit.vmul(nn, 0.006)), (0, 0.11, 0), kit.vmul(sl, 0.06), kit.vmul(nn, 0.004), 'screen_glow')
    rs_ = SC; ry = wall(SC, ZD + 1.1) - 0.14
    fixed.cyl((rs_ - 0.10, ry, ZD + 1.10), (rs_ + 0.10, ry, ZD + 1.10), 0.30, 'machinery_dark', n=24)                       # hose reel
    fixed.cyl((rs_ - 0.08, ry, ZD + 1.10), (rs_ + 0.08, ry, ZD + 1.10), 0.26, 'cable_black', n=24)
    for ds in (-0.11, 0.11):
        fixed.cyl((rs_ + ds - 0.008, ry, ZD + 1.10), (rs_ + ds + 0.008, ry, ZD + 1.10), 0.34, 'armour_paint_red', n=24)
        fixed.box(rs_ + ds - 0.015, rs_ + ds + 0.015, ry - 0.03, ry + 0.14, ZD, ZD + 1.10, st)
    fixed.pipe([(rs_, ry - 0.26, ZD + 1.05), (rs_, ry - 0.30, ZD + 0.70), (rs_ + 0.25, ry - 0.22, ZD + 0.55)], 0.022, 'cable_black', n=8)
    fixed.cyl((rs_ + 0.25, ry - 0.22, ZD + 0.55), (rs_ + 0.37, ry - 0.18, ZD + 0.50), 0.028, 'machinery_bare', n=8)        # nozzle in its holster
    fixed.box(rs_ + 0.22, rs_ + 0.40, ry - 0.12, ry + 0.10, ZD + 0.42, ZD + 0.48, st)
    for q in range(2):                                                                                                      # trestles
        s = S1 - 0.9 - 0.5 * q; yy = wall(s, ZD + 0.4) - 0.22
        fixed.prism([(s - 0.03, yy - 0.18, ZD), (s - 0.03, yy + 0.18, ZD), (s - 0.03, yy + 0.05, ZD + 0.75), (s - 0.03, yy - 0.05, ZD + 0.75)], (0.06, 0, 0), 'hazard_yellow')
        fixed.box(s - 0.20, s + 0.20, yy - 0.06, yy + 0.06, ZD + 0.75, ZD + 0.80, st)
    # port: service panel with umbilical connectors, a tool board, two extinguishers
    s = SC - 1.0; yy = -wall(s, ZD + 1.2)
    fixed.box(s - 0.35, s + 0.35, yy, yy + 0.06, ZD + 0.85, ZD + 1.50, 'lining_panel_dark')
    for q in range(4):
        fixed.cyl((s - 0.24 + 0.16 * q, yy + 0.06, ZD + 1.05), (s - 0.24 + 0.16 * q, yy + 0.11, ZD + 1.05), 0.04, 'machinery_bare', n=12)
        fixed.cyl((s - 0.24 + 0.16 * q, yy + 0.11, ZD + 1.05), (s - 0.24 + 0.16 * q, yy + 0.118, ZD + 1.05), 0.028, ('copper_pipe', 'hazard_yellow', 'armour_paint_red', 'rubber_black')[q], n=12)
        fixed.box(s - 0.29 + 0.16 * q, s - 0.19 + 0.16 * q, yy + 0.06, yy + 0.062, ZD + 0.93, ZD + 0.96, 'placard_white')
    for q in range(3):
        fixed.cyl((s - 0.2 + 0.2 * q, yy + 0.06, ZD + 1.34), (s - 0.2 + 0.2 * q, yy + 0.075, ZD + 1.34), 0.055, 'machinery_dark', n=16)
        fixed.cyl((s - 0.2 + 0.2 * q, yy + 0.075, ZD + 1.34), (s - 0.2 + 0.2 * q, yy + 0.077, ZD + 1.34), 0.045, 'placard_white', n=16)
    fixed.pipe([(s + 0.24, yy + 0.115, ZD + 1.05), (s + 0.30, yy + 0.30, ZD + 0.80), (s + 0.45, yy + 0.16, ZD + 0.55), (s + 0.55, yy + 0.08, ZD + 0.95)], 0.02, 'cable_black', n=8)
    s = SC + 1.1; yy = -wall(s, ZD + 1.3)
    fixed.box(s - 0.45, s + 0.45, yy, yy + 0.02, ZD + 0.95, ZD + 1.65, 'machinery_dark')                                    # tool board
    for q in range(5):
        fixed.box(s - 0.38 + 0.17 * q, s - 0.35 + 0.17 * q, yy + 0.02, yy + 0.04, ZD + 1.10, ZD + 1.45 + 0.03 * q, 'machinery_bare')
        fixed.box(s - 0.395 + 0.17 * q, s - 0.335 + 0.17 * q, yy + 0.02, yy + 0.045, ZD + 1.02, ZD + 1.10, 'hazard_yellow' if q % 2 else 'armour_paint_red')
    fixed.cyl((s - 0.25, yy + 0.03, ZD + 1.56), (s + 0.25, yy + 0.03, ZD + 1.56), 0.012, 'machinery_bare', n=6)
    for s in (S0 + 0.35, S1 - 0.35):
        yy = -wall(s, ZD + 0.5) + 0.09
        fixed.cyl((s, yy, ZD + 0.04), (s, yy, ZD + 0.42), 0.06, 'armour_paint_red', n=14); fixed.cyl((s, yy, ZD + 0.42), (s, yy, ZD + 0.49), 0.022, 'machinery_bare', n=8)
        fixed.box(s - 0.07, s + 0.07, yy - 0.09, yy - 0.07, ZD + 0.22, ZD + 0.27, st)
    for (s, sy) in ((S0 + 0.12, 1), (S0 + 0.12, -1), (S1 - 0.12, 1), (S1 - 0.12, -1)):                                      # warning beacons
        fixed.cyl((s, sy * 1.55, ZCEIL - 0.07), (s, sy * 1.55, ZCEIL), 0.04, 'light_red', n=10)
    finish('lander_bay_fixtures', fixed, parent, group='lander_bay')
    finish('lander_cradle', cr, parent, pivot=(SC, 0, zf), group='lander_bay')
    finish('lander_stub', lander(), 'lander_cradle', pivot=(SC, 0, LANDER_Z0), group='lander_bay')
    key('lander_bay_open', 'lander_cradle', 0, loc=(0, 0, 0)); smooth_keys('lander_bay_open', 'lander_cradle', 48, 132, loc=(0, 0, -DROP))
    return dict(clip='lander_bay_open', frames=132, lander=(Ld['length'], Ld['width'], Ld['height']), drop=DROP)
