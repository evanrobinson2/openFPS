"""Landing gear: four retractable legs with pads, hidden behind doors that follow the hull. Each leg is a small
hierarchy (leg > piston > pad, plus a retraction actuator and two doors), posed down in the rest state and keyed
by the 'gear_retract' clip. The wells are real cavities boxed off from the lower deck."""
import math
import numpy as np
import spec, kit
from kit import MB, finish, empty, key, smooth_keys, set_rest
from structure import deck_slab

G = spec.GEAR
ZT = G['trunnion_z']
WELL_Y = 1.33            # inboard wall of every well
WELL_TOP = -1.22
DOOR_OPEN = math.radians(96)
STOW = math.radians(88)

def well_holes():
    """Holes the lower deck needs so the legs can pass (s0, s1, y0, y1), both sides."""
    out = []
    for k in ('fwd', 'aft'):
        w0, w1 = G[k]['well']
        out += [(w0 - 0.12, w1 + 0.12, WELL_Y, 9.0), (w0 - 0.12, w1 + 0.12, -9.0, -WELL_Y)]
    return out

def build_wells(parent):
    mb = MB(); bolts = MB()
    for k in ('fwd', 'aft'):
        w0, w1 = G[k]['well']; w0 -= 0.12; w1 += 0.12
        # ceiling, cut to the hull, both sides at once
        deck_slab(mb, WELL_TOP + 0.04, 0.04, w0, w1, 'structure_primer', holes=[(w0 - 1, w1 + 1, -WELL_Y, WELL_Y)], step=0.4)
        for sd in (1, -1):
            y = sd * WELL_Y
            mb.box(w0, w1, y - 0.02 if sd > 0 else y, y if sd > 0 else y + 0.02, spec.Z_LOWER - 0.10, WELL_TOP + 0.04, 'structure_primer')
            for s in np.arange(w0 + 0.3, w1, 0.5):                 # stiffeners on the aisle side
                mb.box(s - 0.02, s + 0.02, y - sd * 0.06, y - sd * 0.02, spec.Z_LOWER, WELL_TOP, 'structure_steel')
                bolts.bolt_line((s, y - sd * 0.06, spec.Z_LOWER + 0.12), (s, y - sd * 0.06, WELL_TOP - 0.1), (0, -sd, 0), pitch=0.3, r=0.012, h=0.008)
            for s in (w0, w1):                                     # end walls, cut to the lining
                yl, zl = spec.lining_section(s)
                zz = np.linspace(WELL_TOP + 0.04, spec.Z_LOWER - 0.10, 9); yy = np.interp(-zz, -zl, yl)
                poly = [(s, sd * WELL_Y, zz[0])] + [(s, sd * float(a), float(b)) for a, b in zip(yy, zz)] + [(s, sd * WELL_Y, zz[-1])]
                mb.prism(poly, (0.04 if s == w0 else -0.04, 0, 0), 'structure_primer')
            # trunnion bearing blocks and the actuator anchor
            s, yc = G[k]['s'], sd * G[k]['y']; fold = G[k]['fold']
            for dy in (-0.40, 0.40):
                mb.box(s - 0.13, s + 0.13, yc + dy - 0.05, yc + dy + 0.05, ZT - 0.13, WELL_TOP, 'structure_steel')
                bolts.bolt_circle((s, yc + dy + (0.05 if dy > 0 else -0.05), ZT), (0, 1 if dy > 0 else -1, 0), 0.095, 6, r=0.014, h=0.01)
            ya = yc - sd * 0.24
            mb.box(s + fold * 1.9 - 0.08, s + fold * 1.9 + 0.08, ya - 0.07, ya + 0.07, ZT + 0.20, WELL_TOP, 'structure_steel')
            mb.box(w0 + 0.3, w1 - 0.3, sd * (WELL_Y + 0.03), sd * (WELL_Y + 0.07), WELL_TOP - 0.10, WELL_TOP - 0.05, 'light_panel')
            # hydraulics on the well ceiling: accumulator, valve block, lines to the actuator anchor and along the wall
            zc = WELL_TOP; ya2 = sd * 2.05
            mb.cyl((s + fold * 0.45, ya2, zc - 0.10), (s + fold * 1.15, ya2, zc - 0.10), 0.085, 'machinery_bare', n=16)
            mb.sphere((s + fold * 0.45, ya2, zc - 0.10), 0.085, 'machinery_bare', n=14); mb.sphere((s + fold * 1.15, ya2, zc - 0.10), 0.085, 'machinery_bare', n=14)
            mb.cyl((s + fold * 0.76, ya2, zc - 0.10), (s + fold * 0.84, ya2, zc - 0.10), 0.088, 'hazard_yellow', n=16)
            for f in (0.58, 1.02):
                mb.box(s + fold * f - 0.02, s + fold * f + 0.02, ya2 - 0.095, ya2 + 0.095, zc - 0.195, zc, 'structure_steel')
                bolts.bolt((s + fold * f, ya2 - 0.08, zc - 0.195), (0, 0, -1), r=0.009, h=0.006); bolts.bolt((s + fold * f, ya2 + 0.08, zc - 0.195), (0, 0, -1), r=0.009, h=0.006)
            mb.box(s + fold * 1.30, s + fold * 1.55, ya2 - 0.10, ya2 + 0.10, zc - 0.13, zc, 'machinery_dark')                   # valve block
            for q in range(3):
                sv = s + fold * (1.35 + 0.075 * q)
                mb.cyl((sv, ya2 - 0.05, zc - 0.13), (sv, ya2 - 0.05, zc - 0.175), 0.022, 'machinery_bare', n=8)                  # solenoids
                mb.cyl((sv, ya2 + 0.05, zc - 0.13), (sv, ya2 + 0.05, zc - 0.16), 0.014, 'copper_pipe', n=6)
            mb.pipe([(s + fold * 1.235, ya2, zc - 0.10), (s + fold * 1.30, ya2, zc - 0.07)], 0.016, 'copper_pipe', n=6)
            mb.pipe([(s + fold * 1.55, ya2 - sd * 0.05, zc - 0.05), (s + fold * 1.75, ya2 - sd * 0.05, zc - 0.05), (s + fold * 1.9, ya + sd * 0.09, zc - 0.06), (s + fold * 1.9, ya + sd * 0.09, ZT + 0.22)], 0.014, 'copper_pipe', n=6)
            for q, (zz, mm) in enumerate(((zc - 0.20, 'copper_pipe'), (zc - 0.25, 'machinery_bare'), (zc - 0.30, 'cable_black'))):
                yw = sd * (WELL_Y + 0.035)
                mb.pipe([(w0 + 0.12, yw, zz), (w1 - 0.12, yw, zz)], 0.013, mm, n=6)
            for sc in np.arange(w0 + 0.35, w1 - 0.2, 0.55):
                mb.box(sc - 0.02, sc + 0.02, sd * WELL_Y, sd * (WELL_Y + 0.055), zc - 0.325, zc - 0.175, 'structure_steel')
            mb.pipe([(s + fold * 1.42, ya2 - sd * 0.10, zc - 0.03), (s + fold * 1.42, sd * (WELL_Y + 0.035), zc - 0.03), (s + fold * 1.42, sd * (WELL_Y + 0.035), zc - 0.20)], 0.013, 'copper_pipe', n=6)
            # uplock: a jaw on the ceiling that catches the roller on the leg when it is stowed
            su = s + fold * 1.40; yu = yc + 0.04
            for dy in (-0.062, 0.062):
                mb.box(su - 0.07, su + 0.07, yu + dy - 0.012, yu + dy + 0.012, ZT + 0.17, zc, 'structure_steel')
            mb.box(su - 0.07, su + 0.07, yu - 0.075, yu + 0.075, zc - 0.07, zc, 'structure_steel')
            mb.cyl((su - fold * 0.05, yu - 0.075, ZT + 0.26), (su - fold * 0.05, yu + 0.075, ZT + 0.26), 0.016, 'machinery_bare', n=8)
            mb.box(su + fold * 0.07, su + fold * 0.20, yu - 0.03, yu + 0.03, zc - 0.10, zc - 0.03, 'machinery_dark')              # release ram
            bolts.bolt_circle((su, yu, zc - 0.07), (0, 0, -1), 0.055, 4, r=0.009, h=0.006)
            mb.box(s + fold * 0.5, s + fold * 0.9, sd * (WELL_Y + 0.001), sd * (WELL_Y + 0.004), zc - 0.60, zc - 0.45, 'placard_white')   # servicing placard
    finish('gear_wells', mb, parent, group='landing_gear'); finish('gear_well_bolts', bolts, parent, sharp=60, group='fasteners')

def leg_parts(s, y, fold):
    """Leg, piston and pad builders for a leg whose trunnion is at (s, y, ZT), in the down position."""
    k = -fold
    leg = MB(); pis = MB(); pad = MB()
    st, dk, ch = 'structure_steel', 'machinery_dark', 'hydraulic_chrome'
    leg.cyl((s, y - 0.37, ZT), (s, y + 0.37, ZT), 0.075, 'machinery_bare', n=18)                 # trunnion tube
    leg.box(s - 0.15, s + 0.15, y - 0.17, y + 0.17, ZT - 0.24, ZT + 0.11, st)                    # head forging
    for dy in (-0.171, 0.171):
        leg.bolt_circle((s, y + dy, ZT - 0.06), (0, 1 if dy > 0 else -1, 0), 0.10, 6, r=0.013, h=0.009)
    leg.lathe((s, y, ZT - 0.24), (0, 0, -1), [(0, 0.135), (0.02, 0.125), (1.26, 0.125), (1.26, 0.150), (1.34, 0.150), (1.34, 0.105)], 'armour_gunmetal_c', n=24, cap0=False, cap1=False)
    leg.lathe((s, y, ZT - 0.62), (0, 0, -1), [(0, 0.125), (0, 0.152), (0.07, 0.152), (0.07, 0.125)], st, n=24, cap0=False, cap1=False)
    leg.bolt_circle((s, y, ZT - 1.58), (0, 0, -1), 0.128, 10, r=0.011, h=0.008)
    leg.cyl((s + k * 0.125, y + 0.05, ZT - 0.80), (s + k * 0.185, y + 0.05, ZT - 0.80), 0.016, 'machinery_bare', n=8)   # charging valve
    # hydraulic line down the leg
    leg.pipe([(s + fold * 0.13, y - 0.07, ZT - 0.20), (s + fold * 0.145, y - 0.07, ZT - 0.60), (s + fold * 0.145, y - 0.07, ZT - 1.40)], 0.012, 'copper_pipe', n=6)
    # upper torque link (two plates and a cross pin)
    A = (s + k * 0.17, y, ZT - 1.50); K = (s + k * 0.50, y, ZT - 1.93); B = (s + k * 0.15, y, ZT - 2.42)
    for dy in (-0.07, 0.07):
        leg.cyl((A[0], y + dy, A[2]), (K[0], y + dy, K[2]), 0.028, st, n=8)
        pis.cyl((K[0], y + dy, K[2]), (B[0], y + dy, B[2]), 0.028, st, n=8)
    leg.cyl((A[0], y - 0.10, A[2]), (A[0], y + 0.10, A[2]), 0.034, 'machinery_bare', n=10)
    leg.cyl((K[0], y - 0.10, K[2]), (K[0], y + 0.10, K[2]), 0.030, 'machinery_bare', n=10)
    leg.box(s + k * 0.10, s + k * 0.19, y - 0.09, y + 0.09, ZT - 1.56, ZT - 1.44, st)
    # uplock roller on the side that faces up when the leg is stowed
    leg.box(s + fold * 0.12, s + fold * 0.21, y + 0.012, y + 0.068, ZT - 1.445, ZT - 1.355, st)
    leg.cyl((s + fold * 0.20, y - 0.005, ZT - 1.40), (s + fold * 0.20, y + 0.085, ZT - 1.40), 0.026, 'machinery_bare', n=10)
    # landing light on the forward face, electrical conduit, line clamps, wiper ring, servicing placard
    leg.cyl((s - 0.12, y, ZT - 0.46), (s - 0.20, y, ZT - 0.46), 0.062, dk, n=14)
    leg.cyl((s - 0.20, y, ZT - 0.46), (s - 0.206, y, ZT - 0.46), 0.052, 'light_panel', n=14)
    leg.pipe([(s + fold * 0.13, y + 0.07, ZT - 0.20), (s + fold * 0.142, y + 0.07, ZT - 0.60), (s + fold * 0.142, y + 0.07, ZT - 1.30)], 0.009, 'cable_black', n=6)
    for zz in (ZT - 0.40, ZT - 0.80, ZT - 1.20):
        leg.box(s + fold * 0.118, s + fold * 0.165, y - 0.095, y + 0.095, zz - 0.015, zz + 0.015, st) if fold > 0 else leg.box(s - 0.165, s - 0.118, y - 0.095, y + 0.095, zz - 0.015, zz + 0.015, st)
    leg.lathe((s, y, ZT - 1.58), (0, 0, -1), [(0, 0.105), (0.025, 0.105), (0.025, 0.09)], 'rubber_black', n=24, cap0=False, cap1=False)
    sdo = 1 if y > 0 else -1
    leg.box(s - 0.05, s + 0.05, y + sdo * 0.122, y + sdo * 0.128, ZT - 1.08, ZT - 0.94, 'placard_white')
    for a_ in range(4):                                                                            # grease points on the head
        leg.bolt((s + (-0.09 + 0.06 * a_), y, ZT + 0.11), (0, 0, 1), r=0.008, h=0.01, washer=False)
    # actuator lug on the inboard side
    sd = 1 if y > 0 else -1
    leg.box(s + fold * 0.06, s + fold * 0.22, y - sd * 0.30, y - sd * 0.12, ZT - 0.78, ZT - 0.62, st)
    # piston
    pis.cyl((s, y, ZT - 1.30), (s, y, ZT - 2.64), 0.088, ch, n=24)
    pis.cyl((B[0], y - 0.10, B[2]), (B[0], y + 0.10, B[2]), 0.034, 'machinery_bare', n=10)
    pis.box(s - 0.11, s + 0.11, y - 0.10, y + 0.10, ZT - 2.50, ZT - 2.36, st) if False else pis.lathe((s, y, ZT - 2.34), (0, 0, -1), [(0, 0.088), (0, 0.12), (0.16, 0.12), (0.22, 0.10)], st, n=20, cap0=False, cap1=False)
    pis.sphere((s, y, ZT - 2.68), 0.125, 'machinery_bare', n=14)                                   # ball joint
    for zz in (ZT - 1.80, ZT - 1.95, ZT - 2.10):                                                   # stroke marks
        pis.lathe((s, y, zz), (0, 0, -1), [(0, 0.0892), (0.02, 0.0892)], 'hazard_yellow', n=24, cap0=False, cap1=False)
    # pad
    z0 = ZT - 2.74; R_ = G['pad_r']
    pad.lathe((s, y, z0), (0, 0, -1), [(0, 0.16), (0.05, 0.17), (0.13, R_ * 0.92), (0.19, R_), (0.24, R_), (0.26, R_ * 0.96)], 'armour_gunmetal_b', n=28, cap0=True, cap1=True)
    pad.lathe((s, y, z0 - 0.02), (0, 0, 1), [(0, 0.17), (0.07, 0.15), (0.07, 0.135)], st, n=20, cap0=False, cap1=False)                       # socket collar
    for a in range(8):
        t = 2 * math.pi * a / 8; c, sn = math.cos(t), math.sin(t)
        pad.prism([(s + c * 0.17, y + sn * 0.17, z0 - 0.05), (s + c * R_ * 0.9, y + sn * R_ * 0.9, z0 - 0.19), (s + c * R_ * 0.9, y + sn * R_ * 0.9, z0 - 0.13)], (-sn * 0.025, c * 0.025, 0), st)   # gusset
        pad.bolt((s + c * R_ * 0.82, y + sn * R_ * 0.82, z0 - 0.165), (c * 0.25, sn * 0.25, 1), r=0.013, h=0.009)
    for a in range(4):                                                                             # centring springs from the pad to the piston collar
        tq = math.pi / 4 + a * math.pi / 2; c, sn = math.cos(tq), math.sin(tq)
        pad.cyl((s + c * 0.30, y + sn * 0.30, z0 - 0.10), (s + c * 0.115, y + sn * 0.115, z0 + 0.22), 0.012, 'machinery_bare', n=6)
        pad.cyl((s + c * 0.30, y + sn * 0.30, z0 - 0.115), (s + c * 0.30, y + sn * 0.30, z0 - 0.085), 0.024, st, n=8)
    pad.tube((s + R_ * 0.99, y - 0.02, z0 - 0.215), (s + R_ * 0.99, y + 0.02, z0 - 0.215), 0.04, 0.022, 'hazard_yellow', n=10)   # tie-down ring
    for a in range(5):                                                                             # tread bars
        x = -R_ * 0.7 + a * R_ * 0.35; hw = math.sqrt(max(R_ * R_ * 0.9 - x * x, 0.0))
        pad.box(s + x - 0.03, s + x + 0.03, y - hw, y + hw, z0 - 0.275, z0 - 0.26, 'rubber_black')
    return leg, pis, pad

def build(H):
    parent = empty('landing_gear', 'wayfarer')
    build_wells(parent)
    for kname in ('fwd', 'aft'):
        g = G[kname]; fold = g['fold']
        i0, i1, j0, j1, _ = H.rect(f'gear_{kname}'); jm = (j0 + j1) // 2
        for sd, sn in ((1, 'stbd'), (-1, 'port')):
            base = f'gear_{kname}_{sn}'; s, y = g['s'], sd * g['y']
            node = empty(base, parent, at=(s, y, ZT))
            leg, pis, pad = leg_parts(s, y, fold)
            finish(base + '_leg', leg, node, pivot=(s, y, ZT), group='landing_gear')
            finish(base + '_piston', pis, base + '_leg', pivot=(s, y, ZT - 1.30), group='landing_gear')
            finish(base + '_pad', pad, base + '_piston', pivot=(s, y, ZT - 2.68), group='landing_gear')
            # retraction actuator: body anchored in the well, rod pinned to the leg
            ya = y - sd * 0.21
            A0 = (s + fold * 1.9, ya, ZT + 0.12); L0 = (s + fold * 0.14, ya, ZT - 0.70)
            d0 = kit.vnorm(kit.vsub(L0, A0)); len0 = kit.vlen(kit.vsub(L0, A0))
            body = MB(); rod = MB()
            body.cyl(A0, kit.vadd(A0, kit.vmul(d0, 1.02)), 0.055, 'armour_gunmetal_c', n=14); body.cyl(kit.vadd(A0, kit.vmul(d0, 0.98)), kit.vadd(A0, kit.vmul(d0, 1.06)), 0.065, 'structure_steel', n=14)
            body.cyl((A0[0], ya - 0.06, A0[2]), (A0[0], ya + 0.06, A0[2]), 0.04, 'machinery_bare', n=10)
            rod.cyl(kit.vadd(L0, kit.vmul(d0, -1.0)), L0, 0.030, 'hydraulic_chrome', n=12); rod.cyl((L0[0], ya - 0.05, L0[2]), (L0[0], ya + 0.05, L0[2]), 0.045, 'machinery_bare', n=10)
            finish(base + '_actuator', body, node, pivot=A0, group='landing_gear')
            finish(base + '_actuator_rod', rod, base + '_actuator', pivot=L0, group='landing_gear')
            # doors: outboard and inboard halves, hinged on their outer edges
            for dn, ja, jb_, jh in (('outboard', j0, jm, j0), ('inboard', jm, j1, j1)):
                d = MB()
                H.slab(d, i0, i1, ja, jb_, sd, 0.035, -0.09, 'armour_gunmetal_b', 'structure_primer', 'structure_steel', margin=0.018)
                for i in range(i0 + 1, i1, 3):                                   # stiffeners inside
                    H.rib_s(d, i, ja, jb_, sd, -0.09, -0.15, 0.02, 'structure_steel')
                hinge = H.nodes(i0, i1, jh, jh, 0.0, sd).reshape(-1, 3); free = H.nodes(i0, i1, jb_ if jh == ja else ja, jb_ if jh == ja else ja, 0.0, sd).reshape(-1, 3)
                hp = tuple(hinge.mean(axis=0)); dy = float(free.mean(axis=0)[1] - hp[1])
                for i in range(i0, i1 + 1, 4):                                   # hinge knuckles
                    p = H.pt(i, jh, 0.05, sd); d.cyl((p[0] - 0.09, p[1], p[2]), (p[0] + 0.09, p[1], p[2]), 0.03, 'machinery_bare', n=8)
                name = f'{base}_door_{dn}'
                finish(name, d, node, pivot=hp, group='landing_gear')
                ang = -math.copysign(DOOR_OPEN, dy)
                set_rest(name, rot=(ang, 0, 0))
                key('gear_retract', name, 0, rot=(0, 0, 0)); smooth_keys('gear_retract', name, 56, 84, rot=(-ang, 0, 0))
            # the clip: legs swing up, actuators follow, doors close last
            phi1 = -fold * STOW
            steps = 14
            for q in range(steps + 1):
                t = q / steps; e = t * t * (3 - 2 * t); phi = phi1 * e; f = 4 + 56 * t
                key('gear_retract', base + '_leg', f, rot=(0, phi, 0))
                rs, rz = L0[0] - s, L0[2] - ZT
                Ls = s + rs * math.cos(phi) + rz * math.sin(phi); Lz = ZT - rs * math.sin(phi) + rz * math.cos(phi)
                ds, dz = Ls - A0[0], Lz - A0[2]; ln = math.hypot(ds, dz)
                a0 = math.atan2(d0[2], d0[0]); a1 = math.atan2(dz, ds)
                dphi = -(a1 - a0)
                while dphi > math.pi: dphi -= 2 * math.pi
                while dphi < -math.pi: dphi += 2 * math.pi
                key('gear_retract', base + '_actuator', f, rot=(0, dphi, 0))
                key('gear_retract', base + '_actuator_rod', f, loc=kit.vmul(d0, ln - len0))
            key('gear_retract', base + '_leg', 0, rot=(0, 0, 0)); key('gear_retract', base + '_actuator', 0, rot=(0, 0, 0)); key('gear_retract', base + '_actuator_rod', 0, loc=(0, 0, 0))
    return dict(legs=4, clip='gear_retract', frames=84)
