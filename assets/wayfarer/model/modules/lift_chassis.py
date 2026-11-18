"""The bottom entrance: a chassis that lowers out of the hold on four telescopic rams.

The moving part is a cage: the belly armour plate, a truss under a grating deck, corner posts, guard rails and a top
frame (the harness the rams pull on). It rides down 1.70 m until the belly plate sits on the ground, then the ramp
slides out of its drawer under the deck, drops a sill flap, rises into the flap's slot until it is flush with the deck, and tilts down. Stowed, its deck is flush with the hold floor and its belly plate closes the hull.
Rest pose is stowed; the clip 'lift_lower' takes it down."""
import math
import numpy as np
import spec, kit
from kit import MB, finish, empty, key, smooth_keys, set_rest

Lf = spec.LIFT
S0, S1, HW = Lf['s0'], Lf['s1'], Lf['half_w']
ZD = spec.Z_LOWER                 # deck level, stowed
TOP = ZD + 1.95                   # top frame
RAM_S = (S0 + 0.34, S1 - 0.34); RAM_Y = 1.02
RAMP_LEN = 2.60

def chassis(H):
    mb = MB(); bolts = MB()
    st, dk = 'structure_steel', 'machinery_dark'
    i0, i1, j0, j1, _ = H.rect('lift')
    # belly armour plate, both halves, following the hull
    for sd in (1, -1):
        H.slab(mb, i0, i1, j0, j1, sd, 0.035, -0.10, 'armour_gunmetal_b', 'structure_primer', 'structure_steel', margin=0.02)
        B = H.nodes(i0, i1, j0, j1, 0.035, sd, margin=0.10)
        for a in range(0, B.shape[0], 2):
            bolts.bolt(tuple(B[a, 0]), H.nrm(i0 + a, j0, sd), r=0.018, h=0.012)
        for b in range(0, B.shape[1], 2):
            for a in (0, B.shape[0] - 1):
                bolts.bolt(tuple(B[a, b]), H.nrm(i0 + a, j0 + b, sd), r=0.018, h=0.012)
    zb = float(H.P[i0, j1, 2]) + 0.10                      # top of the belly plate on the centreline
    y_in = HW - 0.06; s_a, s_b = S0 + 0.05, S1 - 0.05
    # deck frame: perimeter channel and cross beams, 0.12 deep
    # (no forward beam: the ramp comes up into that slot to sit flush with the deck)
    for (a0, a1, b0, b1) in ((s_a, s_b, -y_in, -y_in + 0.08), (s_a, s_b, y_in - 0.08, y_in), (s_b - 0.08, s_b, -y_in, y_in)):
        mb.box(a0, a1, b0, b1, ZD - 0.14, ZD - 0.02, st)
    nx = 7
    for k in range(1, nx):
        s = s_a + (s_b - s_a) * k / nx
        mb.box(s - 0.03, s + 0.03, -y_in + 0.08, y_in - 0.08, ZD - 0.13, ZD - 0.02, st)
    # truss between the deck frame and the belly plate: posts and diagonals on both long sides and the centreline
    for y in (-y_in + 0.04, 0.0, y_in - 0.04):
        zlow = zb + (0.0 if abs(y) < 0.1 else float(np.interp(abs(y), [0, HW], [0, 0.16])))
        ztop = ZD - 0.13 if abs(y) > 0.1 else ZD - 0.27           # the centre truss stops under the ramp drawer
        for k in range(nx + 1):
            s = s_a + 0.04 + (s_b - s_a - 0.08) * k / nx
            mb.cyl((s, y, zlow), (s, y, ztop), 0.022, st, n=8)
            if k < nx:
                s2 = s_a + 0.04 + (s_b - s_a - 0.08) * (k + 1) / nx
                mb.cyl((s, y, zlow) if k % 2 else (s, y, ztop), (s2, y, ztop) if k % 2 else (s2, y, zlow), 0.016, st, n=6)
        mb.box(s_a, s_b, y - 0.03, y + 0.03, zlow - 0.02, zlow + 0.03, st)
        if abs(y) < 0.1: mb.box(s_a, s_b, y - 0.03, y + 0.03, ztop - 0.03, ztop + 0.02, st)
    # grating deck: plates between bearer bars, with a hazard border
    mb.box(s_a + 0.08, s_b - 0.08, -y_in + 0.08, y_in - 0.08, ZD - 0.02, ZD - 0.006, 'deck_grating')
    for k in range(int((s_b - s_a - 0.2) / 0.09)):
        s = s_a + 0.12 + k * 0.09
        mb.box(s - 0.012, s + 0.012, -y_in + 0.12, y_in - 0.12, ZD - 0.006, ZD, 'deck_plate')
    for (a0, a1, b0, b1) in ((s_a, s_b, -y_in, -y_in + 0.08), (s_a, s_b, y_in - 0.08, y_in), (s_b - 0.08, s_b, -y_in + 0.08, y_in - 0.08)):
        mb.box(a0, a1, b0, b1, ZD - 0.02, ZD, 'hazard_yellow')
    bolts.bolt_line((s_a + 0.04, -y_in + 0.04, ZD), (s_b - 0.04, -y_in + 0.04, ZD), (0, 0, 1), pitch=0.22, r=0.013, h=0.008)
    bolts.bolt_line((s_a + 0.04, y_in - 0.04, ZD), (s_b - 0.04, y_in - 0.04, ZD), (0, 0, 1), pitch=0.22, r=0.013, h=0.008)
    # the harness: corner posts, top frame, guard rails down both long sides
    posts = [(s_a + 0.04, sy * (y_in - 0.04)) for s_a_ in (0,) for sy in (-1, 1)] + [(s_b - 0.04, sy * (y_in - 0.04)) for sy in (-1, 1)]
    for (s, y) in posts:
        mb.box(s - 0.04, s + 0.04, y - 0.04, y + 0.04, ZD, TOP, st)
        mb.prism([(s, y - 0.04, ZD), (s + (0.3 if s < 11 else -0.3), y - 0.04, ZD), (s, y - 0.04, ZD + 0.3)], (0, 0.08, 0), st)        # foot gusset
        for z in (ZD + 0.08, ZD + 0.22):
            bolts.bolt((s, y + math.copysign(0.04, y), z), (0, math.copysign(1, y), 0), r=0.013, h=0.008)
    for (a0, a1, b0, b1) in ((s_a, s_b, -y_in, -y_in + 0.08), (s_a, s_b, y_in - 0.08, y_in), (s_a, s_a + 0.08, -y_in, y_in), (s_b - 0.08, s_b, -y_in, y_in)):
        mb.box(a0, a1, b0, b1, TOP, TOP + 0.07, st)
    for sy in (-1, 1):
        y = sy * (y_in - 0.04)
        for z in (ZD + 0.55, ZD + 1.05):
            mb.cyl((s_a + 0.08, y, z), (s_b - 0.08, y, z), 0.021, 'hazard_yellow' if z > ZD + 1 else 'machinery_bare', n=10)
        for k in range(1, 4):
            s = s_a + (s_b - s_a) * k / 4
            mb.cyl((s, y, ZD), (s, y, ZD + 1.05), 0.018, 'machinery_bare', n=8)
        # mesh infill below the knee rail: thin bars
        for k in range(1, 16):
            s = s_a + (s_b - s_a) * k / 16
            mb.cyl((s, y, ZD + 0.03), (s, y, ZD + 0.55), 0.006, dk, n=4)
        # ram attachment brackets at deck level
        for s in RAM_S:
            mb.box(s - 0.10, s + 0.10, sy * RAM_Y - 0.09, sy * RAM_Y + 0.09, ZD - 0.02, ZD + 0.05, st)
            bolts.bolt_circle((s, sy * RAM_Y, ZD + 0.05), (0, 0, 1), 0.07, 6, r=0.012, h=0.008)
    # control pedestal on the deck
    mb.box(s_b - 0.42, s_b - 0.22, y_in - 0.36, y_in - 0.12, ZD, ZD + 1.05, 'lining_panel_dark')
    mb.obox((s_b - 0.32, y_in - 0.24, ZD + 1.09), (0.11, 0, 0), (0, 0.13, 0.0), (0, -0.01, 0.04), 'machinery_dark')
    mb.cyl((s_b - 0.36, y_in - 0.24, ZD + 1.12), (s_b - 0.36, y_in - 0.24, ZD + 1.17), 0.03, 'armour_paint_red', n=10)
    mb.cyl((s_b - 0.27, y_in - 0.24, ZD + 1.12), (s_b - 0.27, y_in - 0.24, ZD + 1.15), 0.022, 'hazard_yellow', n=10)
    # pedestal: key switch, deck-level lamps, a status display on its inboard face, conduit down to the deck
    mb.cyl((s_b - 0.32, y_in - 0.31, ZD + 1.10), (s_b - 0.32, y_in - 0.31, ZD + 1.125), 0.014, 'machinery_bare', n=8)
    for q, mm in enumerate(('screen_glow', 'hazard_yellow', 'light_red')):
        mb.cyl((s_b - 0.37 + 0.05 * q, y_in - 0.17, ZD + 1.135), (s_b - 0.37 + 0.05 * q, y_in - 0.17, ZD + 1.15), 0.012, mm, n=8)
    mb.box(s_b - 0.40, s_b - 0.24, y_in - 0.364, y_in - 0.36, ZD + 0.78, ZD + 0.98, 'screen_glow')
    mb.box(s_b - 0.41, s_b - 0.23, y_in - 0.362, y_in - 0.36, ZD + 0.55, ZD + 0.72, 'placard_white')
    for (dx, dz) in ((-0.40, 0.06), (-0.24, 0.06), (-0.40, 1.0), (-0.24, 1.0)):
        bolts.bolt((s_b + dx, y_in - 0.36, ZD + dz), (0, -1, 0), r=0.008, h=0.005, washer=False)
    # toe boards down both sides and across the aft end posts
    for sy in (-1, 1):
        y = sy * (y_in - 0.04)
        mb.box(s_a + 0.08, s_b - 0.08, y - 0.006, y + 0.006, ZD, ZD + 0.11, 'structure_steel')
        # guide shoes on the top frame that run on the rails fixed in the hold
        for s in (S0 + 0.55, S1 - 0.55):
            mb.box(s - 0.07, s + 0.07, sy * y_in, sy * (HW + 0.015), TOP + 0.005, TOP + 0.065, st)
            mb.cyl((s - 0.04, sy * (HW + 0.005), TOP + 0.035), (s + 0.04, sy * (HW + 0.005), TOP + 0.035), 0.028, 'rubber_black', n=10)
            bolts.bolt((s - 0.05, sy * (y_in + 0.03), TOP + 0.065), (0, 0, 1), r=0.008, h=0.005); bolts.bolt((s + 0.05, sy * (y_in + 0.03), TOP + 0.065), (0, 0, 1), r=0.008, h=0.005)
        # diagonal braces in the end bays of the harness, above head height
        for (sa, sb) in ((s_a + 0.04, s_a + 0.55), (s_b - 0.04, s_b - 0.55)):
            mb.cyl((sa, y, TOP - 0.42), (sb, y, TOP), 0.018, st, n=8)
        # work lights under the top frame, travel beacons on top of the aft posts
        mb.box(s_a + 0.5, s_b - 0.5, sy * (y_in - 0.07), sy * (y_in - 0.01), TOP - 0.012, TOP, 'light_panel')
        mb.cyl((s_b - 0.04, y, TOP + 0.07), (s_b - 0.04, y, TOP + 0.13), 0.035, 'light_red', n=10)
        mb.cyl((s_b - 0.04, y, TOP + 0.07), (s_b - 0.04, y, TOP + 0.085), 0.045, st, n=10)
        # deck tie-down rings, recessed pans
        for s in (s_a + 0.55, s_b - 0.55):
            mb.cyl((s, sy * 0.75, ZD - 0.004), (s, sy * 0.75, ZD + 0.002), 0.07, st, n=12)
            mb.tube((s - 0.012, sy * 0.75, ZD + 0.022), (s + 0.012, sy * 0.75, ZD + 0.022), 0.035, 0.022, 'machinery_bare', n=10)
        # rod end clevis and pin at each ram bracket
        for s in RAM_S:
            for dy in (-0.05, 0.05):
                mb.box(s - 0.035, s + 0.035, sy * RAM_Y + dy - 0.01, sy * RAM_Y + dy + 0.01, ZD + 0.05, ZD + 0.16, st)
            mb.cyl((s, sy * RAM_Y - 0.075, ZD + 0.11), (s, sy * RAM_Y + 0.075, ZD + 0.11), 0.016, 'machinery_bare', n=8)
    for q in range(6):                                # load limit chevrons at the hold-side threshold
        yq = -0.75 + 0.30 * q
        mb.prism([(s_b - 0.20, yq, ZD), (s_b - 0.10, yq + 0.10, ZD), (s_b - 0.20, yq + 0.20, ZD)], (0, 0, 0.002), 'hazard_yellow')
    return mb, bolts

RAMP_Z = ZD - 0.165               # top of the ramp while it is stored in its drawer under the deck
RAMP_S = S0 + 0.12                # forward end of the stored ramp
SILL_S = S0 + 0.13                # forward edge of the deck grating; the slot ahead of it is closed by a sill flap
RAMP_SLIDE = RAMP_S + RAMP_LEN - (SILL_S - 0.01)    # out until its hinge end is under the slot
RAMP_RISE = ZD - RAMP_Z           # then the hinge end climbs the horn slots until the ramp is flush with the deck

def ramp():
    """The ramp: stored flat in a drawer under the deck, it slides forward, rises flush with the deck and its far end drops to the ground."""
    mb = MB(); w = HW - 0.22; s0, s1 = RAMP_S, RAMP_S + RAMP_LEN
    mb.box(s0, s1, -w, w, RAMP_Z - 0.045, RAMP_Z, 'deck_plate')
    for k in range(1, 13):
        s = s0 + k * RAMP_LEN / 13.5
        mb.box(s - 0.015, s + 0.015, -w + 0.06, w - 0.06, RAMP_Z, RAMP_Z + 0.010, 'hazard_yellow' if k in (1, 12) else 'deck_grating')
    for y in (-w, w):
        mb.box(s0, s1, y - 0.03, y + 0.03, RAMP_Z - 0.075, RAMP_Z + 0.02, 'structure_steel')
        mb.bolt_line((s0 + 0.12, y, RAMP_Z + 0.02), (s1 - 0.12, y, RAMP_Z + 0.02), (0, 0, 1), pitch=0.25, r=0.011, h=0.007)
    mb.cyl((s1 - 0.02, -w - 0.02, RAMP_Z - 0.03), (s1 - 0.02, w + 0.02, RAMP_Z - 0.03), 0.028, 'machinery_bare', n=10)     # hinge barrel
    mb.box(s0, s0 + 0.05, -w + 0.1, w - 0.1, RAMP_Z - 0.06, RAMP_Z - 0.045, 'rubber_black')                              # toe strip
    return mb

def ramp_guides():
    """Drawer rails for the ramp and the horns its hinge pins climb to come flush with the deck."""
    mb = MB(); w = HW - 0.22
    for sy in (-1, 1):                                                                                           # lift horns the hinge pins climb
        y = sy * (w + 0.058)
        mb.box(S0 + 0.05, S0 + 0.17, y - 0.012, y + 0.012, RAMP_Z - 0.12, ZD - 0.004, 'structure_steel')
        mb.box(S0 + 0.075, S0 + 0.125, y - 0.014, y + 0.014, RAMP_Z - 0.06, ZD - 0.03, 'machinery_dark')          # the slot
        for z in (RAMP_Z - 0.09, ZD - 0.02):
            mb.bolt((S0 + 0.155, y + sy * 0.012, z), (0, sy, 0), r=0.009, h=0.006)
    return mb

def build(H):
    parent = empty('lift_chassis', 'wayfarer', at=(0.5 * (S0 + S1), 0, ZD))
    mb, bolts = chassis(H)
    mb.merge(bolts); mb.merge(ramp_guides())
    finish('lift_cage', mb, parent, pivot=(0.5 * (S0 + S1), 0, ZD), group='lift_chassis')
    sill = MB(); w = HW - 0.22                                        # sill flap: closes the slot when the ramp is stowed
    sill.box(S0 + 0.05, SILL_S - 0.004, -w - 0.04, w + 0.04, ZD - 0.014, ZD, 'hazard_yellow')
    sill.cyl((SILL_S - 0.004, -w - 0.04, ZD - 0.012), (SILL_S - 0.004, w + 0.04, ZD - 0.012), 0.008, 'machinery_bare', n=8)
    finish('lift_ramp_sill', sill, 'lift_cage', pivot=(SILL_S - 0.004, 0, ZD - 0.012), group='lift_chassis')
    key('lift_lower', 'lift_ramp_sill', 0, rot=(0, 0, 0)); smooth_keys('lift_lower', 'lift_ramp_sill', 96, 104, rot=(0, -math.pi / 2, 0))
    for sy, sn in ((1, 'stbd'), (-1, 'port')):                        # forward gate: a pair of swing bars that become the ramp's handrails
        g = MB(); yh = sy * (HW - 0.10)
        g.cyl((S0 + 0.09, yh, ZD + 0.50), (S0 + 0.09, yh, ZD + 1.10), 0.024, 'machinery_bare', n=10)
        for z in (ZD + 0.55, ZD + 1.05):
            g.cyl((S0 + 0.09, yh, z), (S0 + 0.09, sy * 0.04, z), 0.02, 'hazard_yellow', n=8)
        g.cyl((S0 + 0.09, sy * 0.06, ZD + 0.55), (S0 + 0.09, sy * 0.06, ZD + 1.05), 0.014, 'machinery_bare', n=8)
        finish(f'lift_gate_{sn}', g, 'lift_cage', pivot=(S0 + 0.09, yh, ZD + 0.8), group='lift_chassis')
        key('lift_lower', f'lift_gate_{sn}', 0, rot=(0, 0, 0)); smooth_keys('lift_lower', f'lift_gate_{sn}', 124, 138, rot=(0, 0, -sy * math.pi / 2))
    for sy, sn in ((1, 'stbd'), (-1, 'port')):                        # hold-side gate: open when stowed, closed for travel
        g = MB(); yh = sy * (HW - 0.14); sg = S1 - 0.09
        g.cyl((sg, yh, ZD + 0.45), (sg, yh, ZD + 1.05), 0.024, 'machinery_bare', n=10)
        for z in (ZD + 0.50, ZD + 1.00):
            g.cyl((sg, yh, z), (sg, sy * 0.04, z), 0.02, 'hazard_yellow', n=8)
        g.cyl((sg, sy * 0.06, ZD + 0.50), (sg, sy * 0.06, ZD + 1.00), 0.014, 'machinery_bare', n=8)
        name = f'lift_gate_aft_{sn}'
        finish(name, g, 'lift_cage', pivot=(sg, yh, ZD + 0.75), group='lift_chassis')
        op = -sy * math.pi / 2                                        # swung forward, lying inside the side rail
        set_rest(name, rot=(0, 0, op))
        key('lift_lower', name, 0, rot=(0, 0, 0)); smooth_keys('lift_lower', name, 0, 14, rot=(0, 0, -op))
    finish('lift_ramp', ramp(), 'lift_cage', pivot=(RAMP_S + RAMP_LEN - 0.02, 0, RAMP_Z - 0.03), group='lift_chassis')
    # rams: fixed barrel in the hold ceiling, a middle stage, and a rod pinned to the cage
    fixed = MB(); zc = spec.Z_MAIN - spec.DECK_T
    for s in RAM_S:
        fixed.box(s - 0.11, s + 0.11, -HW - 0.45, HW + 0.45, zc - 0.10, zc, 'structure_steel')                    # ceiling beam
        fixed.bolt_line((s - 0.11, -HW - 0.3, zc - 0.05), (s - 0.11, HW + 0.3, zc - 0.05), (-1, 0, 0), pitch=0.3, r=0.014, h=0.009)
    k = 0
    for s in RAM_S:
        for sy in (-1, 1):
            y = sy * RAM_Y; k += 1
            fixed.cyl((s, y, zc - 0.10), (s, y, ZD + 0.14), 0.072, 'armour_gunmetal_c', n=18)
            fixed.lathe((s, y, ZD + 0.20), (0, 0, -1), [(0, 0.072), (0, 0.088), (0.07, 0.088), (0.07, 0.060)], 'structure_steel', n=18, cap0=False, cap1=False)
            fixed.bolt_circle((s, y, zc - 0.10), (0, 0, -1), 0.10, 6, r=0.012, h=0.008)
            mid = MB(); mid.cyl((s, y, zc - 0.20), (s, y, ZD + 0.12), 0.056, 'machinery_bare', n=16)
            mid.lathe((s, y, ZD + 0.17), (0, 0, -1), [(0, 0.056), (0, 0.068), (0.05, 0.068), (0.05, 0.044)], 'structure_steel', n=16, cap0=False, cap1=False)
            rod = MB(); rod.cyl((s, y, zc - 0.30), (s, y, ZD + 0.05), 0.040, 'hydraulic_chrome', n=14)
            finish(f'lift_ram_{k}_stage', mid, parent, pivot=(s, y, ZD + 0.12), group='lift_chassis')
            finish(f'lift_ram_{k}_rod', rod, 'lift_cage', pivot=(s, y, ZD + 0.05), group='lift_chassis')
            smooth_keys('lift_lower', f'lift_ram_{k}_stage', 0, 96, loc=(0, 0, -Lf['travel'] / 2))
    # hold-side fixtures: hazard border round the opening and stanchions with a chain line
    for (a0, a1, b0, b1) in ((S0 - 0.12, S1 + 0.12, -HW - 0.12, -HW), (S0 - 0.12, S1 + 0.12, HW, HW + 0.12), (S0 - 0.12, S0, -HW, HW), (S1, S1 + 0.12, -HW, HW)):
        fixed.box(a0, a1, b0, b1, ZD, ZD + 0.006, 'hazard_yellow')
    # guide rails in the hold for the cage's shoes, ram gland rings, and the hydraulic manifold across the ceiling
    for sy in (-1, 1):
        for s in (S0 + 0.55, S1 - 0.55):
            fixed.box(s - 0.03, s + 0.03, sy * (HW + 0.035), sy * (HW + 0.075), ZD + 0.006, zc - 0.10, 'structure_steel')
            fixed.box(s - 0.06, s + 0.06, sy * (HW + 0.075), sy * (HW + 0.085), ZD + 0.006, zc - 0.10, 'structure_steel')
            for z in (ZD + 0.3, ZD + 1.0, ZD + 1.7):
                fixed.bolt((s + 0.045, sy * (HW + 0.075), z), (0, -sy, 0), r=0.009, h=0.006); fixed.bolt((s - 0.045, sy * (HW + 0.075), z), (0, -sy, 0), r=0.009, h=0.006)
            fixed.box(s - 0.06, s + 0.06, sy * (HW + 0.03), sy * (HW + 0.085), ZD + 0.006, ZD + 0.30, 'hazard_yellow')
        y = sy * RAM_Y
        fixed.pipe([(RAM_S[0], y + sy * 0.13, zc - 0.13), (RAM_S[1], y + sy * 0.13, zc - 0.13)], 0.022, 'copper_pipe', n=8)
        fixed.pipe([(RAM_S[0], y + sy * 0.19, zc - 0.13), (RAM_S[1], y + sy * 0.19, zc - 0.13)], 0.016, 'machinery_bare', n=8)
        for s in RAM_S:
            fixed.pipe([(s, y + sy * 0.13, zc - 0.13), (s, y + sy * 0.10, zc - 0.22), (s, y + sy * 0.072, zc - 0.30)], 0.014, 'copper_pipe', n=6)
            fixed.box(s - 0.05, s + 0.05, y + sy * 0.072, y + sy * 0.12, zc - 0.36, zc - 0.28, 'machinery_dark')       # valve on the barrel
            fixed.box(s - 0.012, s + 0.012, y - sy * 0.074, y - sy * 0.086, ZD + 0.30, zc - 0.20, 'placard_white')   # position sensor strip
        sm = 0.5 * (RAM_S[0] + RAM_S[1])
        fixed.box(sm - 0.16, sm + 0.16, y + sy * 0.08, y + sy * 0.26, zc - 0.24, zc - 0.10, 'machinery_dark')          # manifold block
        for q in range(3):
            fixed.cyl((sm - 0.10 + 0.10 * q, y + sy * 0.17, zc - 0.24), (sm - 0.10 + 0.10 * q, y + sy * 0.17, zc - 0.29), 0.022, 'machinery_bare', n=8)
    fixed.pipe([(0.5 * (RAM_S[0] + RAM_S[1]), -RAM_Y - 0.17, zc - 0.17), (0.5 * (RAM_S[0] + RAM_S[1]) + 0.25, -0.5, zc - 0.14), (0.5 * (RAM_S[0] + RAM_S[1]) + 0.25, 0.5, zc - 0.14), (0.5 * (RAM_S[0] + RAM_S[1]), RAM_Y + 0.17, zc - 0.17)], 0.02, 'copper_pipe', n=8)
    finish('lift_rams_fixed', fixed, parent, group='lift_chassis')
    smooth_keys('lift_lower', 'lift_cage', 0, 96, loc=(0, 0, -Lf['travel']))
    drop = (ZD - 0.06 - Lf['travel']) - spec.Z_GROUND           # how far the toe has to fall once the cage is down
    ang = -math.asin(min(drop / RAMP_LEN, 0.9))
    key('lift_lower', 'lift_ramp', 0, loc=(0, 0, 0), rot=(0, 0, 0))
    smooth_keys('lift_lower', 'lift_ramp', 96, 118, loc=(-RAMP_SLIDE, 0, 0), rot=(0, 0, 0))
    smooth_keys('lift_lower', 'lift_ramp', 118, 124, loc=(-RAMP_SLIDE, 0, RAMP_RISE), rot=(0, 0, 0), loc0=(-RAMP_SLIDE, 0, 0))
    smooth_keys('lift_lower', 'lift_ramp', 124, 138, loc=(-RAMP_SLIDE, 0, RAMP_RISE), rot=(0, ang, 0), loc0=(-RAMP_SLIDE, 0, RAMP_RISE))
    return dict(clip='lift_lower', frames=138, travel=Lf['travel'], deck=(S1 - S0 - 0.1, 2 * HW - 0.12))
