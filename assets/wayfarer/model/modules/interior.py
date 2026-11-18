"""Interior fittings, compartment by compartment: viewport glazing, the crew hatch, sliding doors, the vestibule
ladder, crew deck, mission bay, engineering, hold and avionics aisle. Structure (decks, bulkheads, frames, lining)
is the fuselage module's; this module only adds what is fitted to it."""
import math
import numpy as np
import spec, kit
from kit import MB, finish, empty, key, smooth_keys
import fittings
from fuselage import BULKHEADS, DOOR, LADDER

S = spec.ST
ZM, ZL = spec.Z_MAIN, spec.Z_LOWER

def wall(s, z):
    return spec.lining_half_width(s, z)

def ports(H, parent):
    g = MB(); fr = MB()
    for name in sorted(n for n in H.openings if n.startswith('port_')):
        i0, i1, j0, j1, _ = H.rect(name)
        for sd in (1, -1):
            H.slab(g, i0, i1, j0, j1, sd, -spec.WAIST['depth'] - 0.02, -spec.WAIST['depth'] - 0.07, 'glass_port', margin=0.02)
            # inner trim ring with four bolts
            A = H.nodes(i0, i1, j0, j1, spec.OFF_LINING - 0.035, sd, margin=-0.06)
            for (a, b) in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
                n = np.array(H.nrm(i0 if a == 0 else i1, j0 if b == 0 else j1, sd)) * -1
                fr.bolt(tuple(A[a, b]), tuple(n), r=0.012, h=0.008)
    finish('viewport_glazing', g, parent, group='interior'); finish('viewport_trim_bolts', fr, parent, sharp=60, group='fasteners')

def crew_hatch(H, parent):
    i0, i1, j0, j1, sd = H.rect('crew_hatch')
    d = MB()
    H.slab(d, i0, i1, j0, j1, sd, 0.03, spec.OFF_LINING + 0.02, 'armour_gunmetal_c', 'lining_panel', 'structure_steel', margin=0.022)
    B = H.nodes(i0, i1, j0, j1, 0.03, sd, margin=0.09)
    for a in range(B.shape[0]):
        for b in (0, B.shape[1] - 1):
            d.bolt(tuple(B[a, b]), H.nrm(i0 + a, j0 + b, sd), r=0.016, h=0.011)
    for b in range(1, B.shape[1] - 1):
        for a in (0, B.shape[0] - 1):
            d.bolt(tuple(B[a, b]), H.nrm(i0 + a, j0 + b, sd), r=0.016, h=0.011)
    # hand wheel inside, grab bar outside
    c = np.array(H.rect_centre(i0, i1, j0, j1, sd, spec.OFF_LINING)); n = -np.array(H.nrm((i0 + i1) // 2, (j0 + j1) // 2, sd))
    d.lathe(tuple(c), tuple(n), [(0.0, 0.03), (0.10, 0.03), (0.10, 0.17), (0.13, 0.17), (0.13, 0.03)], 'hazard_yellow', n=16)
    co = np.array(H.rect_centre(i0, i1, j0, j1, sd, 0.03))
    d.pipe([tuple(co + np.array((-0.25, 0, -0.1))), tuple(co + np.array((-0.25, 0, -0.1)) - n * 0.07), tuple(co + np.array((0.25, 0, -0.1)) - n * 0.07), tuple(co + np.array((0.25, 0, -0.1)))], 0.016, 'hazard_yellow', n=8)
    finish('crew_hatch_door', d, parent, pivot=tuple(c), group='interior')
    inb = -sd * 0.24
    key('crew_hatch_open', 'crew_hatch_door', 0, loc=(0, 0, 0)); smooth_keys('crew_hatch_open', 'crew_hatch_door', 0, 18, loc=(0, inb, 0))
    smooth_keys('crew_hatch_open', 'crew_hatch_door', 18, 54, loc=(1.22, inb, 0), loc0=(0, inb, 0))
    # boarding step outside under the hatch
    st = MB(); p = np.array(H.pt((i0 + i1) // 2, j1, 0.06, sd))
    st.box(p[0] - 0.40, p[0] + 0.40, p[1] + sd * 0.0, p[1] + sd * 0.30, p[2] - 0.10, p[2] - 0.06, 'deck_grating')
    for ds in (-0.36, 0.36):
        st.prism([(p[0] + ds - 0.02, p[1], p[2] - 0.10), (p[0] + ds - 0.02, p[1] + sd * 0.30, p[2] - 0.10), (p[0] + ds - 0.02, p[1], p[2] - 0.34)], (0.04, 0, 0), 'structure_steel')
    finish('crew_hatch_step', st, parent, group='interior')

def half_leaf(w, h, thick=0.05):
    d = MB(); d.box(-thick / 2, thick / 2, 0, w, 0, h, 'lining_panel_dark')
    for sx in (-1, 1):
        x = sx * thick / 2
        d.box(min(x, x + sx * 0.012), max(x, x + sx * 0.012), 0.06, w - 0.06, 0.12, h - 0.12, 'structure_steel')
        d.box(min(x, x + sx * 0.016), max(x, x + sx * 0.016), 0.12, w - 0.12, h * 0.62, h * 0.80, 'hazard_yellow')
        for (y, zz) in ((0.10, 0.16), (w - 0.10, 0.16), (0.10, h - 0.16), (w - 0.10, h - 0.16), (0.10, h / 2), (w - 0.10, h / 2)):
            d.bolt((x + sx * 0.012, y, zz), (sx, 0, 0), r=0.011, h=0.006, washer=False)
    return d

def doors(parent):
    names = []
    for name, st, dm, dl in BULKHEADS:
        for deck, has, z in (('main', dm, ZM), ('lower', dl, ZL)):
            if not has: continue
            s = S[st] + 0.135; h = 2.0 if deck == 'main' else 1.95
            nm = f"door_{st}_{deck}"
            wd = DOOR[1] - DOOR[0] + 0.08
            if deck == 'main':          # one leaf sliding to starboard
                leaves = [(nm, DOOR[0] - 0.04, wd, 1.02)]
            else:                       # the gear wells leave no pocket on the lower deck: two half leaves part
                leaves = [(nm + '_port', DOOR[0] - 0.04, wd / 2, -0.52), (nm + '_stbd', 0.0, wd / 2, 0.52)]
            for lname, y0, w, slide in leaves:
                leaf = fittings.door_leaf(width=w, height=h + 0.03) if deck == 'main' else half_leaf(w, h + 0.03)
                leaf = leaf.transformed(lambda p, y0=y0: (s + p[0], y0 + p[1], z + p[2]))
                finish(lname, leaf, parent, pivot=(s, y0 + w / 2, z), group='interior')
                key(f'{nm}_open', lname, 0, loc=(0, 0, 0)); smooth_keys(f'{nm}_open', lname, 0, 24, loc=(0, slide, 0))
            tr = MB(); tr.box(s - 0.045, s + 0.045, DOOR[0] - 0.60, DOOR[1] + 1.10, z + h + 0.03, z + h + 0.09, 'structure_steel')
            tr.bolt_line((s + 0.045, DOOR[0] - 0.5, z + h + 0.06), (s + 0.045, DOOR[1] + 1.0, z + h + 0.06), (1, 0, 0), pitch=0.3, r=0.01, h=0.007)
            finish(nm + '_track', tr, parent, group='interior'); names.append(nm)
    return names

def vestibule(parent):
    mb = MB()
    lad = fittings.place(fittings.ladder(ZM - ZL + 1.05), LADDER[1] - 0.06, 0.5 * (LADDER[2] + LADDER[3]), ZL, (-1, 0))
    mb.merge(lad)
    # guard rail round the well on the main deck (open on the climbing side)
    y0, y1, s0, s1 = LADDER[2], LADDER[3], LADDER[0], LADDER[1]
    for (a, b) in (((s0, y0), (s0, y1)), ((s0, y1), (s1, y1)), ((s0, y0), (s1 - 0.0, y0))):
        for z in (ZM + 0.55, ZM + 1.05):
            mb.cyl((a[0], a[1], z), (b[0], b[1], z), 0.019, 'hazard_yellow' if z > ZM + 1 else 'machinery_bare', n=8)
    for (s, y) in ((s0, y0), (s0, y1), (s1, y1), (s1, y0)):
        mb.cyl((s, y, ZM), (s, y, ZM + 1.05), 0.019, 'machinery_bare', n=8)
    # suit lockers on the starboard wall aft of the ladder, bench on the forward bulkhead
    hw = wall(7.2, ZM + 1.0)
    mb.box(S['cockpit_aft'] + 0.10, S['cockpit_aft'] + 0.50, -2.05, -0.75, ZM + 0.40, ZM + 0.46, 'seat_fabric')
    mb.box(S['cockpit_aft'] + 0.10, S['cockpit_aft'] + 0.14, -2.05, -0.75, ZM, ZM + 0.40, 'lining_panel_dark')
    finish('vestibule_ladder_and_rails', mb, parent, group='interior')

def crew_deck(parent):
    mb = MB(); s0 = S['vestibule_aft'] + 0.25
    for sd in (-1, 1):
        for lvl, z in enumerate((ZM + 0.42, ZM + 1.32)):
            w = min(wall(s0 + 1.0, z), wall(s0 + 1.0, z + 0.5)) - 0.04
            y0, y1 = sd * (w - 0.80), sd * w
            mb.box(s0, s0 + 2.02, min(y0, y1), max(y0, y1), z - 0.06, z, 'structure_steel')                 # bunk pan
            mb.box(s0 + 0.03, s0 + 1.99, min(y0, y1) + 0.03, max(y0, y1) - 0.03, z, z + 0.10, 'seat_fabric')  # mattress
            mb.box(s0 + 0.06, s0 + 0.50, min(y0, y1) + 0.10, max(y0, y1) - 0.10, z + 0.10, z + 0.17, 'placard_white')   # pillow
            mb.box(s0, s0 + 2.02, y0 - sd * 0.0 - 0.015, y0 + 0.015, z, z + 0.16, 'structure_steel')        # lee rail
            for s in (s0 + 0.02, s0 + 2.0):
                mb.box(s - 0.02, s + 0.02, min(y0, y1), max(y0, y1), z - 0.06 - (0.36 if lvl == 0 else 0.84), z - 0.06, 'structure_steel')
                mb.bolt((s, y0, z - 0.03), (0, -sd, 0), r=0.011, h=0.008)
        # lockers aft of the bunks on the port side, galley on the starboard side
    sp = s0 + 2.4
    w = wall(sp + 1.2, ZM + 1.0) - 0.04
    for k in range(5):
        a = sp + k * 0.52
        mb.box(a, a + 0.50, -w, -w + 0.55, ZM, ZM + 1.90, 'lining_panel_dark')
        mb.box(a + 0.03, a + 0.47, -w + 0.55, -w + 0.565, ZM + 0.06, ZM + 1.84, 'lining_panel')
        mb.box(a + 0.40, a + 0.43, -w + 0.565, -w + 0.60, ZM + 0.95, ZM + 1.10, 'machinery_bare')
        for z in (ZM + 0.12, ZM + 1.78):
            mb.bolt((a + 0.07, -w + 0.565, z), (0, 1, 0), r=0.009, h=0.006); mb.bolt((a + 0.43, -w + 0.565, z), (0, 1, 0), r=0.009, h=0.006)
    # galley: counter along the wall, table with two benches
    mb.box(sp, sp + 2.6, w - 0.60, w, ZM, ZM + 0.90, 'lining_panel_dark'); mb.box(sp, sp + 2.6, w - 0.62, w, ZM + 0.90, ZM + 0.94, 'machinery_bare')
    mb.box(sp + 0.3, sp + 0.9, w - 0.50, w - 0.12, ZM + 0.941, ZM + 0.95, 'machinery_dark')                 # hob
    mb.cyl((sp + 1.6, w - 0.30, ZM + 0.94), (sp + 1.6, w - 0.30, ZM + 1.20), 0.02, 'machinery_bare', n=8)   # tap
    mb.box(sp + 0.5, sp + 1.9, 0.55, 1.25, ZM + 0.72, ZM + 0.76, 'lining_panel'); mb.cyl((sp + 1.2, 0.9, ZM), (sp + 1.2, 0.9, ZM + 0.72), 0.05, 'structure_steel', n=10)
    mb.cyl((sp + 1.2, 0.9, ZM), (sp + 1.2, 0.9, ZM + 0.03), 0.22, 'structure_steel', n=16); mb.bolt_circle((sp + 1.2, 0.9, ZM + 0.03), (0, 0, 1), 0.17, 6, r=0.011, h=0.007)
    for y in (0.18, 1.32):
        mb.box(sp + 0.5, sp + 1.9, y, y + 0.30, ZM + 0.40, ZM + 0.46, 'seat_fabric'); mb.box(sp + 0.6, sp + 0.66, y + 0.05, y + 0.25, ZM, ZM + 0.40, 'structure_steel'); mb.box(sp + 1.74, sp + 1.80, y + 0.05, y + 0.25, ZM, ZM + 0.40, 'structure_steel')
    finish('crew_deck_bunks_lockers_galley', mb, parent, group='interior')

def mission_bay(parent):
    s0, s1 = S['hold_aft'] + 0.7, S['eng_fwd'] - 0.9
    n = 5
    for sd, sn in ((1, 'stbd'), (-1, 'port')):
        for k in range(n):
            s = s0 + (s1 - s0) * k / (n - 1)
            y = sd * (wall(s, ZM + 0.5) - 0.52)
            finish(f'jump_seat_{sn}_{k + 1}', fittings.place(fittings.seat(armrests=False), s, y, ZM, (0, -sd)), parent, pivot=(s, y, ZM), group='interior')
    mb = MB()
    for sd in (-1, 1):
        y = sd * 1.25; z = ZM + spec.HEAD_MAIN - 0.22
        mb.pipe([(s0 - 0.4, y, z + 0.16), (s0 - 0.4, y, z), (s1 + 0.4, y, z), (s1 + 0.4, y, z + 0.16)], 0.018, 'hazard_yellow', n=8)      # overhead grab rail
        for k in range(6):
            s = s0 - 0.4 + (s1 - s0 + 0.8) * k / 5
            mb.cyl((s, y, z), (s, y, z + 0.16), 0.012, 'machinery_bare', n=6)
    # weapon rack on the aft bulkhead, both sides of the door
    sb = S['eng_fwd'] - 0.02
    for sd in (-1, 1):
        y0 = sd * 0.85; y1 = sd * 2.0
        mb.box(sb - 0.30, sb, min(y0, y1), max(y0, y1), ZM, ZM + 0.25, 'lining_panel_dark'); mb.box(sb - 0.22, sb, min(y0, y1), max(y0, y1), ZM + 1.05, ZM + 1.12, 'structure_steel')
        for k in range(5):                         # long guns as simple stand-ins: stock, receiver, barrel
            y = y0 + (y1 - y0) * (k + 0.5) / 5
            mb.box(sb - 0.16, sb - 0.10, y - 0.025, y + 0.025, ZM + 0.25, ZM + 0.98, 'machinery_dark'); mb.cyl((sb - 0.13, y, ZM + 0.98), (sb - 0.13, y, ZM + 1.42), 0.014, 'machinery_dark', n=6)
            mb.box(sb - 0.19, sb - 0.07, y - 0.035, y + 0.035, ZM + 1.05, ZM + 1.12, 'structure_steel')
    # equipment cage on the forward bulkhead
    sf = S['hold_aft'] + 0.22
    for sd in (-1, 1):
        y0, y1 = sd * 0.9, sd * 2.1
        mb.box(sf, sf + 0.45, min(y0, y1), max(y0, y1), ZM, ZM + 1.8, 'lining_panel_dark')
        for z in (ZM + 0.45, ZM + 0.9, ZM + 1.35):
            mb.box(sf + 0.45, sf + 0.47, min(y0, y1) + 0.04, max(y0, y1) - 0.04, z - 0.01, z + 0.01, 'machinery_bare')
        for k in range(1, 8):
            y = y0 + (y1 - y0) * k / 8
            mb.cyl((sf + 0.46, y, ZM + 0.05), (sf + 0.46, y, ZM + 1.75), 0.006, 'machinery_bare', n=4)
    finish('mission_bay_fittings', mb, parent, group='interior')

def engineering(parent):
    mb = MB(); bolts = MB()
    # reactor vessel on the lower deck, lying fore and aft
    s0, s1 = S['eng_fwd'] + 0.35, 22.55; z = ZL + 1.0
    mb.lathe((s0, 0, z), (1, 0, 0), [(0, 0.30), (0.10, 0.62), (0.22, 0.74), (s1 - s0 - 0.22, 0.74), (s1 - s0 - 0.10, 0.62), (s1 - s0, 0.30)], 'machinery_bare', n=32)
    for s in (s0 + 0.24, 0.5 * (s0 + s1), s1 - 0.24):
        mb.lathe((s - 0.04, 0, z), (1, 0, 0), [(0, 0.74), (0, 0.82), (0.08, 0.82), (0.08, 0.74)], 'structure_steel', n=32, cap0=False, cap1=False)
        bolts.bolt_circle((s + 0.04, 0, z), (1, 0, 0), 0.78, 20, r=0.014, h=0.01); bolts.bolt_circle((s - 0.04, 0, z), (-1, 0, 0), 0.78, 20, r=0.014, h=0.01)
    for sd in (-1, 1):
        mb.prism([(s0 + 0.2, sd * 0.55, ZL), (s0 + 0.2, sd * 0.80, ZL), (s0 + 0.2, sd * 0.62, z - 0.35), (s0 + 0.2, sd * 0.50, z - 0.52)], (s1 - s0 - 0.4, 0, 0), 'structure_steel')   # saddles
        mb.pipe([(0.5 * (s0 + s1), sd * 0.45, z + 0.60), (0.5 * (s0 + s1), sd * 0.9, z + 0.95), (0.5 * (s0 + s1), sd * 0.9, ZM - spec.DECK_T)], 0.07, 'copper_pipe', n=10)          # coolant risers
    mb.lathe((0.5 * (s0 + s1), 0, z + 0.74), (0, 0, 1), [(0, 0.20), (0.10, 0.20), (0.10, 0.12), (0.22, 0.12)], 'hazard_yellow', n=16)
    # main deck: coolant pump skids either side, switchboard on the aft bulkhead
    for sd in (-1, 1):
        sp = S['eng_fwd'] + 0.9; y = sd * 1.25
        mb.box(sp - 0.45, sp + 0.75, y - 0.36, y + 0.36, ZM, ZM + 0.10, 'structure_steel')
        mb.cyl((sp - 0.30, y, ZM + 0.42), (sp + 0.25, y, ZM + 0.42), 0.26, 'machinery_dark', n=20)            # motor
        mb.lathe((sp + 0.25, y, ZM + 0.42), (1, 0, 0), [(0, 0.16), (0.08, 0.30), (0.30, 0.30), (0.38, 0.16)], 'machinery_bare', n=20)     # pump casing
        bolts.bolt_circle((sp + 0.33, y, ZM + 0.42), (-1, 0, 0), 0.27, 10, r=0.012, h=0.009)
        mb.pipe([(sp + 0.44, y, ZM + 0.72), (sp + 0.44, y, ZM + 1.5), (sp + 1.4, y + sd * 0.25, ZM + 1.9), (S['eng_aft'] - 0.1, y * 0.9, ZM + 1.9)], 0.06, 'copper_pipe', n=10)
        mb.pipe([(sp + 0.0, y, ZM + 0.68), (sp + 0.0, y, ZM + 0.05)], 0.05, 'copper_pipe', n=10)
        for (a, b) in ((-0.38, -0.3), (0.68, -0.3), (-0.38, 0.3), (0.68, 0.3)):
            bolts.bolt((sp + a, y + b, ZM + 0.10), (0, 0, 1), r=0.014, h=0.01)
    sb = S['eng_aft'] - 0.02
    mb.box(sb - 0.35, sb, -1.25, 1.25, ZM, ZM + 1.95, 'lining_panel_dark')
    for k in range(5):
        y = -1.0 + 0.5 * k
        mb.box(sb - 0.37, sb - 0.35, y - 0.20, y + 0.20, ZM + 1.15, ZM + 1.75, 'screen_glow' if k % 2 == 0 else 'machinery_dark')
        for q in range(4):
            mb.cyl((sb - 0.35, y - 0.15 + 0.1 * q, ZM + 0.95), (sb - 0.38, y - 0.15 + 0.1 * q, ZM + 0.95), 0.016, 'hazard_yellow' if q == 0 else 'machinery_bare', n=8)
        mb.box(sb - 0.37, sb - 0.35, y - 0.20, y + 0.20, ZM + 0.15, ZM + 0.80, 'lining_panel')
    finish('engineering_reactor_pumps_switchboard', mb, parent, group='interior'); finish('engineering_bolts', bolts, parent, sharp=60, group='fasteners')

def lower_deck(parent):
    mb = MB()
    # avionics racks either side of the forward aisle
    for sd in (-1, 1):
        for k in range(2):
            s = 4.55 + k * 0.64
            w = min(wall(s + 0.3, ZL + 0.3), 1.75) - 0.03
            y0, y1 = sd * 0.62, sd * max(w, 0.9)
            mb.box(s, s + 0.60, min(y0, y1), max(y0, y1), ZL, ZL + 1.70, 'lining_panel_dark')
            for q in range(7):
                z = ZL + 0.12 + q * 0.22
                mb.box(s + 0.03, s + 0.57, y0 - sd * 0.012 if sd > 0 else y0, y0 if sd > 0 else y0 + 0.012, z, z + 0.19, 'machinery_dark')
                mb.box(s + 0.06, s + 0.10, (y0 - sd * 0.016) if sd > 0 else y0 + 0.012, (y0 - sd * 0.012) if sd > 0 else y0 + 0.016, z + 0.08, z + 0.11, 'screen_glow' if q % 3 else 'light_red')
                mb.bolt((s + 0.045, y0 - sd * 0.012, z + 0.03), (0, -sd, 0), r=0.007, h=0.005, washer=False); mb.bolt((s + 0.555, y0 - sd * 0.012, z + 0.03), (0, -sd, 0), r=0.007, h=0.005, washer=False)
    # hold: tie-down rails along the lift opening, lift call station on the aft bulkhead
    Lf = spec.LIFT
    for sd in (-1, 1):
        y = sd * (Lf['half_w'] + 0.36)
        mb.box(Lf['s0'], Lf['s1'], y - 0.03, y + 0.03, ZL, ZL + 0.02, 'structure_steel')
        for k in range(8):
            s = Lf['s0'] + 0.25 + k * 0.44
            mb.lathe((s, y, ZL + 0.02), (0, 0, 1), [(0, 0.045), (0.012, 0.045), (0.012, 0.02)], 'machinery_bare', n=10, cap0=False, cap1=True)
    sb = S['hold_aft'] - 0.02
    mb.box(sb - 0.14, sb, 0.75, 1.15, ZL + 1.0, ZL + 1.5, 'lining_panel_dark')
    mb.cyl((sb - 0.14, 0.87, ZL + 1.35), (sb - 0.17, 0.87, ZL + 1.35), 0.035, 'armour_paint_red', n=10); mb.cyl((sb - 0.14, 1.02, ZL + 1.35), (sb - 0.165, 1.02, ZL + 1.35), 0.03, 'hazard_yellow', n=10)
    mb.box(sb - 0.145, sb - 0.14, 0.80, 1.10, ZL + 1.06, ZL + 1.22, 'screen_glow')
    finish('lower_deck_fittings', mb, parent, group='interior')

# ------------------------------------------------------------------ detail pass: what a crew would have fitted
ZC = ZM + spec.HEAD_MAIN
ZCL = ZL + spec.HEAD_LOWER

def wmin(s0, s1, z0, z1):
    """Narrowest lining half-width over a wall patch, so that a fitting never pokes through the lining."""
    return min(float(wall(s, z)) for s in (s0, 0.5 * (s0 + s1), s1) for z in (z0, 0.5 * (z0 + z1), z1))

def intercom(mb, s_face, nx, y, z):
    """Intercom station on a bulkhead face. nx = -1 on a forward face, +1 on an aft face."""
    a, b = s_face, s_face + nx * 0.04
    mb.box(min(a, b), max(a, b), y - 0.11, y + 0.11, z - 0.16, z + 0.16, 'lining_panel_dark')
    f = b; g = b + nx * 0.004
    mb.box(min(f, g), max(f, g), y - 0.07, y + 0.07, z + 0.02, z + 0.12, 'machinery_dark')
    mb.box(min(f, g), max(f, g), y - 0.08, y + 0.08, z - 0.14, z - 0.11, 'placard_white')
    for q, m in enumerate(('screen_glow', 'hazard_yellow', 'light_red')):
        mb.cyl((f, y - 0.06 + 0.06 * q, z - 0.05), (f + nx * 0.012, y - 0.06 + 0.06 * q, z - 0.05), 0.015, m, n=8)
    mb.pipe([(f + nx * 0.01, y + 0.09, z - 0.16), (f + nx * 0.03, y + 0.10, z - 0.34), (f + nx * 0.01, y + 0.12, z - 0.20)], 0.006, 'cable_black', n=5)
    for (dy, dz) in ((-0.095, -0.145), (0.095, -0.145), (-0.095, 0.145), (0.095, 0.145)):
        mb.bolt((f, y + dy, z + dz), (nx, 0, 0), r=0.006, h=0.004, washer=False)

def cable_tray(mb, s0, s1, y, zc, w=0.30):
    mb.box(s0, s1, y - w / 2, y + w / 2, zc - 0.085, zc - 0.08, 'structure_steel')
    for sy in (-1, 1):
        mb.box(s0, s1, y + sy * w / 2 - 0.004, y + sy * w / 2 + 0.004, zc - 0.085, zc - 0.05, 'structure_steel')
    n = max(2, int((s1 - s0) / 0.9) + 1)
    for k in range(n):
        s = s0 + 0.05 + (s1 - s0 - 0.1) * k / (n - 1)
        for sy in (-1, 1):
            mb.box(s - 0.012, s + 0.012, y + sy * (w / 2 + 0.004), y + sy * (w / 2 + 0.016), zc - 0.085, zc, 'structure_steel')
    for q, (r, m) in enumerate(((0.018, 'cable_black'), (0.014, 'cable_black'), (0.011, 'copper_pipe'), (0.016, 'cable_black'), (0.010, 'hazard_yellow'))):
        yy = y - w / 2 + 0.045 + q * (w - 0.09) / 4
        mb.cyl((s0, yy, zc - 0.08 + r), (s1, yy, zc - 0.08 + r), r, m, n=6)

def extinguisher(mb, s, y, z, n):
    """Wall-hung extinguisher. n = unit direction (ds, dy) pointing off the wall into the room; (s, y) is on the wall."""
    c = (s + n[0] * 0.08, y + n[1] * 0.08)
    mb.cyl((c[0], c[1], z), (c[0], c[1], z + 0.36), 0.06, 'armour_paint_red', n=14)
    mb.cyl((c[0], c[1], z + 0.36), (c[0], c[1], z + 0.42), 0.022, 'machinery_bare', n=8)
    mb.box(c[0] - 0.03, c[0] + 0.03, c[1] - 0.03, c[1] + 0.03, z + 0.42, z + 0.45, 'machinery_dark')
    mb.box(min(s, c[0]) - 0.02, max(s, c[0]) + 0.02, min(y, c[1]) - 0.02, max(y, c[1]) + 0.02, z + 0.16, z + 0.20, 'structure_steel')

def ring_down(mb, s, y, z):
    mb.lathe((s, y, z), (0, 0, 1), [(0, 0.055), (0.006, 0.055), (0.006, 0.03)], 'structure_steel', n=10, cap0=False, cap1=True)
    mb.tube((s - 0.008, y, z + 0.012), (s + 0.008, y, z + 0.012), 0.03, 0.02, 'machinery_bare', n=10)

def crew_deck_details(parent):
    mb = MB(); s0 = S['vestibule_aft'] + 0.25
    for sd in (-1, 1):
        for lvl, z in enumerate((ZM + 0.42, ZM + 1.32)):
            w = min(wall(s0 + 1.0, z), wall(s0 + 1.0, z + 0.5)) - 0.04
            yi, yo = sd * (w - 0.80), sd * w
            lo, hi = min(yi, yo), max(yi, yo)
            mb.box(s0 + 0.62, s0 + 1.96, lo + 0.035, hi - 0.035, z + 0.10, z + 0.128, 'armour_paint_red_dark')          # blanket
            mb.box(s0 + 0.62, s0 + 0.80, lo + 0.035, hi - 0.035, z + 0.128, z + 0.14, 'placard_white')                  # turned-down sheet
            zr = min(z + 0.78, ZC - 0.05)
            mb.cyl((s0, yi, zr), (s0 + 2.02, yi, zr), 0.009, 'machinery_bare', n=6)                                     # curtain rail
            for q in range(4):                                                                                          # curtain, drawn back in folds
                mb.capsule((s0 + 1.80 + 0.055 * q, yi + (0.012 if q % 2 else -0.012), z + 0.20), (s0 + 1.80 + 0.055 * q, yi + (0.012 if q % 2 else -0.012), zr - 0.03), 0.03, 'armour_gunmetal_c', n=8)
            wl = min(wall(s0 + 0.3, z + 0.45), wall(s0 + 0.3, z + 0.62)) - 0.02
            mb.box(s0 + 0.20, s0 + 0.42, sd * wl - 0.03 if sd > 0 else sd * wl, sd * wl if sd > 0 else sd * wl + 0.03, z + 0.48, z + 0.56, 'lining_panel_dark')   # reading light and socket
            mb.cyl((s0 + 0.26, sd * (wl - 0.03), z + 0.52), (s0 + 0.26, sd * (wl - 0.045), z + 0.52), 0.022, 'light_panel', n=8)
            mb.cyl((s0 + 0.36, sd * (wl - 0.03), z + 0.52), (s0 + 0.36, sd * (wl - 0.04), z + 0.52), 0.012, 'machinery_bare', n=6)
            mb.box(s0 + 0.9, s0 + 1.5, sd * wl - 0.05 if sd > 0 else sd * wl, sd * wl if sd > 0 else sd * wl + 0.05, z + 0.40, z + 0.42, 'structure_steel')      # shelf
            mb.box(s0 + 0.95, s0 + 1.15, sd * wl - 0.045 if sd > 0 else sd * wl + 0.005, sd * wl - 0.005 if sd > 0 else sd * wl + 0.045, z + 0.42, z + 0.56, 'lining_panel')  # books
            mb.box(s0 + 1.16, s0 + 1.21, sd * wl - 0.045 if sd > 0 else sd * wl + 0.005, sd * wl - 0.005 if sd > 0 else sd * wl + 0.045, z + 0.42, z + 0.54, 'armour_paint_red')
        w = min(wall(s0 + 1.0, ZM + 0.42), wall(s0 + 1.0, ZM + 0.92)) - 0.04
        yi = sd * (w - 0.80) - sd * 0.035
        for s in (s0 + 1.50, s0 + 1.80):                                                                                # ladder to the upper bunk
            mb.cyl((s, yi, ZM), (s, yi, ZM + 1.50), 0.014, 'machinery_bare', n=8)
        for k in range(4):
            mb.cyl((s0 + 1.50, yi, ZM + 0.30 + 0.32 * k), (s0 + 1.80, yi, ZM + 0.30 + 0.32 * k), 0.011, 'machinery_bare', n=6)
        mb.box(s0 + 0.2, s0 + 1.3, sd * (w - 0.74) if sd > 0 else sd * w + 0.06, sd * w - 0.06 if sd > 0 else sd * (w - 0.74), ZM, ZM + 0.28, 'lining_panel_dark')   # kit drawer under the lower bunk
        mb.box(s0 + 0.65, s0 + 0.85, yi - 0.012 + sd * 0.09, yi + 0.012 + sd * 0.09, ZM + 0.13, ZM + 0.16, 'machinery_bare')
    sp = s0 + 2.4
    w = wall(sp + 1.2, ZM + 1.0) - 0.04
    yf = -w + 0.565
    for k in range(5):                                                                                                   # lockers: vents, name cards, hinges
        a = sp + k * 0.52
        for q in range(3):
            mb.box(a + 0.12, a + 0.38, yf, yf + 0.004, ZM + 1.56 + 0.045 * q, ZM + 1.58 + 0.045 * q, 'machinery_dark')
        mb.box(a + 0.17, a + 0.33, yf, yf + 0.003, ZM + 1.36, ZM + 1.41, 'placard_white')
        for z in (ZM + 0.30, ZM + 1.00, ZM + 1.65):
            mb.cyl((a + 0.045, yf + 0.008, z - 0.04), (a + 0.045, yf + 0.008, z + 0.04), 0.008, 'machinery_bare', n=6)
    for (a, m) in ((sp + 0.10, 'seat_fabric'), (sp + 0.75, 'armour_paint_red_dark'), (sp + 1.45, 'seat_fabric')):       # kit bags on the locker tops
        if ZM + 1.90 + 0.26 < ZC and wmin(a, a + 0.5, ZM + 1.9, ZM + 2.16) > w - 0.02:
            mb.capsule((a + 0.12, -w + 0.28, ZM + 2.03), (a + 0.42, -w + 0.28, ZM + 2.03), 0.12, m, n=10)
    # galley
    mb.box(sp + 1.36, sp + 1.84, w - 0.50, w - 0.14, ZM + 0.941, ZM + 0.947, 'machinery_dark')                          # sink
    mb.tube((sp + 1.60, w - 0.32, ZM + 0.941), (sp + 1.60, w - 0.32, ZM + 0.95), 0.03, 0.018, 'machinery_bare', n=10)
    mb.pipe([(sp + 1.60, w - 0.30, ZM + 1.20), (sp + 1.60, w - 0.38, ZM + 1.22), (sp + 1.60, w - 0.40, ZM + 1.16)], 0.012, 'machinery_bare', n=6)
    for ds in (0.45, 0.75):
        mb.tube((sp + ds, w - 0.31, ZM + 0.95), (sp + ds, w - 0.31, ZM + 0.956), 0.085, 0.06, 'machinery_bare', n=14)
    mb.cyl((sp + 0.45, w - 0.31, ZM + 0.956), (sp + 0.45, w - 0.31, ZM + 1.10), 0.075, 'machinery_bare', n=14)          # pot
    mb.cyl((sp + 0.45, w - 0.31, ZM + 1.10), (sp + 0.45, w - 0.31, ZM + 1.11), 0.08, 'machinery_dark', n=14)
    mb.cyl((sp + 2.25, w - 0.30, ZM + 0.94), (sp + 2.25, w - 0.30, ZM + 1.16), 0.07, 'machinery_bare', n=14)            # kettle
    mb.cyl((sp + 2.25, w - 0.30, ZM + 1.16), (sp + 2.25, w - 0.30, ZM + 1.19), 0.05, 'machinery_dark', n=10)
    mb.pipe([(sp + 2.25, w - 0.37, ZM + 1.13), (sp + 2.25, w - 0.44, ZM + 1.08), (sp + 2.25, w - 0.37, ZM + 0.99)], 0.008, 'machinery_dark', n=5)
    for k in range(4):                                                                                                   # cupboard fronts under the counter
        a = sp + 0.04 + k * 0.64
        mb.box(a, a + 0.60, w - 0.612, w - 0.60, ZM + 0.08, ZM + 0.86, 'lining_panel' if k != 1 else 'machinery_dark')
        mb.box(a + 0.10, a + 0.50, w - 0.635, w - 0.612, ZM + 0.76, ZM + 0.785, 'machinery_bare')
        if k == 1: mb.box(a + 0.08, a + 0.52, w - 0.616, w - 0.612, ZM + 0.25, ZM + 0.66, 'glass_port')                 # oven window
    wu = wmin(sp, sp + 2.6, ZM + 1.50, ZM + 2.05) - 0.04
    mb.box(sp, sp + 2.6, wu - 0.32, wu, ZM + 1.50, ZM + 2.05, 'lining_panel_dark')                                       # wall cupboards
    for k in range(4):
        a = sp + 0.03 + k * 0.645
        mb.box(a, a + 0.61, wu - 0.332, wu - 0.32, ZM + 1.53, ZM + 2.02, 'lining_panel')
        mb.box(a + 0.26, a + 0.35, wu - 0.35, wu - 0.332, ZM + 1.55, ZM + 1.575, 'machinery_bare')
    mb.box(sp + 0.2, sp + 2.4, wu - 0.30, wu - 0.06, ZM + 1.485, ZM + 1.50, 'light_panel')                               # light under the cupboards
    mb.cyl((sp + 0.9, w - 0.05, ZM + 1.30), (sp + 2.0, w - 0.05, ZM + 1.30), 0.008, 'machinery_bare', n=6)              # mug rail
    for k in range(4):
        a = sp + 1.0 + 0.3 * k
        mb.cyl((a, w - 0.09, ZM + 1.17), (a, w - 0.09, ZM + 1.27), 0.04, ('placard_white', 'armour_paint_red', 'placard_white', 'hazard_yellow')[k], n=10)
    mb.box(sp + 0.02, sp + 0.30, w - 0.50, w - 0.10, ZM + 0.94, ZM + 1.36, 'lining_panel')                               # water dispenser
    mb.box(sp + 0.08, sp + 0.24, w - 0.512, w - 0.50, ZM + 1.16, ZM + 1.30, 'screen_glow')
    mb.cyl((sp + 0.16, w - 0.50, ZM + 1.08), (sp + 0.16, w - 0.54, ZM + 1.08), 0.012, 'machinery_bare', n=6)
    # table: two mugs, a tablet and a fiddle rail so nothing slides off
    zt = ZM + 0.76
    for (a, b) in (((sp + 0.5, 0.55), (sp + 1.9, 0.55)), ((sp + 1.9, 0.55), (sp + 1.9, 1.25)), ((sp + 1.9, 1.25), (sp + 0.5, 1.25)), ((sp + 0.5, 1.25), (sp + 0.5, 0.55))):
        mb.cyl((a[0], a[1], zt + 0.012), (b[0], b[1], zt + 0.012), 0.006, 'machinery_bare', n=5)
    mb.cyl((sp + 0.8, 0.75, zt), (sp + 0.8, 0.75, zt + 0.09), 0.038, 'placard_white', n=10)
    mb.cyl((sp + 1.55, 1.05, zt), (sp + 1.55, 1.05, zt + 0.09), 0.038, 'armour_paint_red', n=10)
    mb.box(sp + 1.05, sp + 1.33, 0.72, 0.92, zt, zt + 0.008, 'machinery_dark'); mb.box(sp + 1.06, sp + 1.32, 0.73, 0.91, zt + 0.008, zt + 0.009, 'screen_glow')
    # room fittings
    cable_tray(mb, S['vestibule_aft'] + 0.45, S['hold_aft'] - 0.35, 0.0, ZC)
    intercom(mb, S['hold_aft'], -1, -0.85, ZM + 1.40)
    intercom(mb, S['vestibule_aft'] + 0.08, 1, -0.85, ZM + 1.40)
    extinguisher(mb, S['hold_aft'], 0.80, ZM + 0.25, (-1, 0))
    mb.box(S['hold_aft'] - 0.004, S['hold_aft'], -0.30, 0.30, ZM + 2.14, ZM + 2.24, 'screen_glow')                       # exit sign over the door
    for s in (s0 + 3.0, s0 + 4.6):
        mb.cyl((s, 0.0, ZC - 0.012), (s, 0.0, ZC - 0.086), 0.06, 'machinery_dark', n=12)                                 # smoke detectors hang under the tray
    finish('crew_deck_details', mb, parent, group='interior')

def mission_bay_details(parent):
    mb = MB()
    s0, s1 = S['hold_aft'] + 0.7, S['eng_fwd'] - 0.9
    n = 5; step = (s1 - s0) / (n - 1)
    for sd in (-1, 1):
        for k in range(n):                                                                                               # pack stowage over every seat
            s = s0 + step * k
            w = wmin(s - 0.25, s + 0.25, ZM + 1.62, ZM + 1.98) - 0.03
            lo, hi = (w - 0.30, w) if sd > 0 else (-w, -w + 0.30)
            mb.box(s - 0.26, s + 0.26, lo, hi, ZM + 1.62, ZM + 1.635, 'structure_steel')
            mb.box(s - 0.21, s + 0.21, lo + 0.03, hi - 0.03, ZM + 1.635, ZM + 1.93, 'seat_fabric')
            for ds in (-0.10, 0.10):
                mb.box(s + ds - 0.02, s + ds + 0.02, lo + 0.026 if sd < 0 else lo + 0.022, hi - 0.022 if sd < 0 else hi - 0.026, ZM + 1.62, ZM + 1.94, 'hazard_yellow')   # straps
            mb.box(s - 0.07, s + 0.07, (lo - 0.002) if sd > 0 else hi, lo if sd > 0 else hi + 0.002, ZM + 1.585, ZM + 1.62, 'placard_white')                       # seat number
        gaps = [s0 + step * (k + 0.5) for k in range(n - 1)]
        def onwall(s, z0, z1, d):
            w = wmin(s - 0.2, s + 0.2, z0, z1) - 0.02
            return ((w - d, w) if sd > 0 else (-w, -w + d)), w
        (lo, hi), w = onwall(gaps[0], ZM + 1.0, ZM + 1.4, 0.13)
        if sd < 0:                                                                                                       # first aid
            mb.box(gaps[0] - 0.18, gaps[0] + 0.18, lo, hi, ZM + 1.00, ZM + 1.40, 'placard_white')
            mb.box(gaps[0] - 0.09, gaps[0] + 0.09, hi, hi + 0.003, ZM + 1.17, ZM + 1.23, 'armour_paint_red'); mb.box(gaps[0] - 0.03, gaps[0] + 0.03, hi, hi + 0.003, ZM + 1.11, ZM + 1.29, 'armour_paint_red')
            mb.box(gaps[0] + 0.13, gaps[0] + 0.16, hi, hi + 0.02, ZM + 1.16, ZM + 1.24, 'machinery_bare')
            extinguisher(mb, gaps[2], -w, ZM + 0.55, (0, 1))
            for q in range(2):                                                                                           # stretcher, folded, on the wall
                mb.cyl((gaps[1] - 0.55, -w + 0.05 + 0.07 * q, ZM + 1.10), (gaps[1] + 0.55, -w + 0.05 + 0.07 * q, ZM + 1.10), 0.02, 'machinery_bare', n=8)
            mb.box(gaps[1] - 0.50, gaps[1] + 0.50, -w + 0.03, -w + 0.14, ZM + 1.04, ZM + 1.09, 'hazard_yellow')
            for ds in (-0.4, 0.4):
                mb.box(gaps[1] + ds - 0.02, gaps[1] + ds + 0.02, -w, -w + 0.16, ZM + 1.02, ZM + 1.14, 'structure_steel')
        else:                                                                                                            # oxygen bottles, ramp and light controls
            for q in range(3):
                mb.cyl((gaps[0] - 0.14 + 0.14 * q, w - 0.08, ZM + 0.85), (gaps[0] - 0.14 + 0.14 * q, w - 0.08, ZM + 1.35), 0.055, 'hazard_yellow', n=12)
                mb.cyl((gaps[0] - 0.14 + 0.14 * q, w - 0.08, ZM + 1.35), (gaps[0] - 0.14 + 0.14 * q, w - 0.08, ZM + 1.41), 0.02, 'machinery_bare', n=8)
            mb.box(gaps[0] - 0.23, gaps[0] + 0.23, w - 0.15, w, ZM + 1.08, ZM + 1.12, 'structure_steel')
            mb.box(gaps[0] - 0.23, gaps[0] + 0.23, w - 0.15, w, ZM + 0.81, ZM + 0.85, 'structure_steel')
            (lo, hi), w2 = onwall(gaps[2], ZM + 1.05, ZM + 1.50, 0.07)
            mb.box(gaps[2] - 0.20, gaps[2] + 0.20, lo, hi, ZM + 1.05, ZM + 1.50, 'lining_panel_dark')
            mb.box(gaps[2] - 0.15, gaps[2] + 0.02, lo - 0.004, lo, ZM + 1.28, ZM + 1.45, 'screen_glow')
            for q, m in enumerate(('light_red', 'hazard_yellow', 'screen_glow')):
                mb.cyl((gaps[2] + 0.11, lo, ZM + 1.42 - 0.07 * q), (gaps[2] + 0.11, lo - 0.014, ZM + 1.42 - 0.07 * q), 0.02, m, n=8)
            for q in range(4):
                mb.cyl((gaps[2] - 0.13 + 0.085 * q, lo, ZM + 1.15), (gaps[2] - 0.13 + 0.085 * q, lo - 0.03, ZM + 1.17), 0.008, 'machinery_bare', n=6)
            mb.box(gaps[2] - 0.16, gaps[2] + 0.16, lo - 0.003, lo, ZM + 1.07, ZM + 1.10, 'placard_white')
            (lo, hi), w3 = onwall(gaps[1], ZM + 0.9, ZM + 1.5, 0.05)                                                     # whiteboard for the brief
            mb.box(gaps[1] - 0.45, gaps[1] + 0.45, lo, hi, ZM + 0.92, ZM + 1.50, 'placard_white')
            mb.box(gaps[1] - 0.47, gaps[1] + 0.47, lo - 0.01, hi, ZM + 0.90, ZM + 0.92, 'structure_steel')
            mb.box(gaps[1] - 0.30, gaps[1] + 0.05, lo - 0.002, lo, ZM + 1.15, ZM + 1.40, 'lining_panel')
        for k in range(6):                                                                                               # deck tie-down rings and a walkway line
            ring_down(mb, s0 - 0.2 + (s1 - s0 + 0.4) * k / 5, sd * 0.45, ZM)
        mb.box(s0 - 0.5, s1 + 0.5, sd * 0.72 - 0.02, sd * 0.72 + 0.02, ZM + 0.001, ZM + 0.003, 'hazard_yellow')
    # ready lights over the aft door, speakers, cable tray
    sb = S['eng_fwd']
    mb.box(sb - 0.06, sb, -0.24, 0.24, ZM + 2.13, ZM + 2.27, 'machinery_dark')
    for q, m in enumerate(('light_red', 'hazard_yellow', 'screen_glow')):
        mb.cyl((sb - 0.06, -0.15 + 0.15 * q, ZM + 2.20), (sb - 0.075, -0.15 + 0.15 * q, ZM + 2.20), 0.045, m, n=12)
    intercom(mb, sb, -1, -0.72, ZM + 1.62)
    intercom(mb, S['hold_aft'] + 0.08, 1, -0.74, ZM + 1.40)
    cable_tray(mb, S['hold_aft'] + 0.5, S['eng_fwd'] - 0.4, 0.0, ZC)
    for s in (s0 + 1.0, s1 - 1.0):
        mb.cyl((s, 0.42, ZC), (s, 0.42, ZC - 0.05), 0.09, 'machinery_dark', n=14); mb.cyl((s, 0.42, ZC - 0.05), (s, 0.42, ZC - 0.055), 0.07, 'structure_steel', n=14)
    # helmets on a shelf over the weapon rack, ammunition tins on its base
    for sd in (-1, 1):
        y0 = sd * 0.85; y1 = sd * 2.0
        mb.box(sb - 0.30, sb, min(y0, y1), max(y0, y1), ZM + 1.58, ZM + 1.60, 'structure_steel')
        for k in range(4):
            y = y0 + (y1 - y0) * (k + 0.5) / 4
            mb.sphere((sb - 0.15, y, ZM + 1.70), 0.125, 'armour_gunmetal_b', n=12, squash=(1.08, 0.95, 0.92))
            mb.box(sb - 0.275, sb - 0.268, y - 0.07, y + 0.07, ZM + 1.66, ZM + 1.72, 'glass_port')
        for k in range(3):
            y = y0 + (y1 - y0) * (k + 0.5) / 3
            mb.box(sb - 0.29, sb - 0.19, y - 0.14, y + 0.14, ZM + 0.25, ZM + 0.43, 'structure_primer'); mb.box(sb - 0.292, sb - 0.29, y - 0.08, y + 0.08, ZM + 0.31, ZM + 0.37, 'hazard_yellow')
    finish('mission_bay_details', mb, parent, group='interior')

def engineering_details(parent):
    mb = MB(); bolts = MB()
    sf = S['eng_fwd'] + 0.08
    # gauge board and valve manifold on the forward bulkhead, port of the door
    mb.box(sf, sf + 0.05, -1.85, -1.05, ZM + 1.05, ZM + 1.85, 'lining_panel_dark')
    for i in range(2):
        for j in range(3):
            y = -1.70 + 0.25 * j; z = ZM + 1.68 - 0.30 * i
            mb.cyl((sf + 0.05, y, z), (sf + 0.075, y, z), 0.085, 'machinery_dark', n=18)
            mb.cyl((sf + 0.075, y, z), (sf + 0.077, y, z), 0.072, 'placard_white', n=18)
            a = math.radians(40 + 55 * (i * 3 + j))
            mb.obox((sf + 0.079, y + 0.028 * math.cos(a), z + 0.028 * math.sin(a)), (0.001, 0, 0), (0, 0.03 * math.cos(a), 0.03 * math.sin(a)), (0, -0.004 * math.sin(a), 0.004 * math.cos(a)), 'armour_paint_red')
            bolts.bolt_circle((sf + 0.075, y, z), (1, 0, 0), 0.079, 4, r=0.005, h=0.004)
    mb.box(sf + 0.05, sf + 0.053, -1.80, -1.10, ZM + 1.08, ZM + 1.14, 'placard_white')
    for j in range(4):
        y = -1.75 + 0.2 * j
        mb.cyl((sf + 0.12, y, ZM), (sf + 0.12, y, ZM + 1.05), 0.028, 'copper_pipe' if j % 2 else 'machinery_bare', n=10)
        mb.cyl((sf + 0.12, y, ZM + 0.62), (sf + 0.12, y, ZM + 0.74), 0.045, 'machinery_bare', n=10)                     # valve body
        mb.cyl((sf + 0.12, y, ZM + 0.68), (sf + 0.22, y, ZM + 0.68), 0.012, 'machinery_bare', n=6)
        mb.tube((sf + 0.215, y, ZM + 0.68), (sf + 0.235, y, ZM + 0.68), 0.075, 0.058, 'armour_paint_red' if j < 2 else 'hazard_yellow', n=16)   # handwheel
        for q in range(3):
            a = 2 * math.pi * q / 3
            mb.cyl((sf + 0.225, y, ZM + 0.68), (sf + 0.225, y + 0.06 * math.cos(a), ZM + 0.68 + 0.06 * math.sin(a)), 0.007, 'machinery_bare', n=5)
        bolts.bolt_circle((sf + 0.12, y, ZM + 0.74), (0, 0, 1), 0.036, 4, r=0.006, h=0.005)
        mb.box(sf, sf + 0.13, y - 0.035, y + 0.035, ZM + 0.30, ZM + 0.33, 'structure_steel')
    intercom(mb, sf, 1, -0.82, ZM + 1.45)
    # hazard border round each pump skid, drip trays, local start boxes
    for sd in (-1, 1):
        sp = S['eng_fwd'] + 0.9; y = sd * 1.25
        for (a, b, c, d) in ((sp - 0.52, sp + 0.82, y - 0.43, y - 0.39), (sp - 0.52, sp + 0.82, y + 0.39, y + 0.43), (sp - 0.52, sp - 0.48, y - 0.43, y + 0.43), (sp + 0.78, sp + 0.82, y - 0.43, y + 0.43)):
            mb.box(a, b, c, d, ZM + 0.001, ZM + 0.003, 'hazard_yellow')
        mb.box(sp - 0.42, sp - 0.30, y - 0.10, y + 0.10, ZM + 0.70, ZM + 0.95, 'lining_panel_dark')                      # start box on the motor
        mb.cyl((sp - 0.42, y - 0.04, ZM + 0.88), (sp - 0.44, y - 0.04, ZM + 0.88), 0.022, 'screen_glow', n=8); mb.cyl((sp - 0.42, y + 0.04, ZM + 0.88), (sp - 0.445, y + 0.04, ZM + 0.88), 0.025, 'armour_paint_red', n=8)
        mb.box(sp - 0.38, sp - 0.34, y - 0.02, y + 0.02, ZM + 0.66, ZM + 0.70, 'structure_steel')
        for ds in (-0.20, 0.15):                                                                                         # motor feet and cooling fins
            mb.box(sp + ds - 0.04, sp + ds + 0.04, y - 0.24, y + 0.24, ZM + 0.10, ZM + 0.20, 'structure_steel')
        for q in range(7):
            mb.tube((sp - 0.24 + 0.06 * q, y, ZM + 0.42), (sp - 0.225 + 0.06 * q, y, ZM + 0.42), 0.285, 0.25, 'machinery_dark', n=20)
        mb.cyl((sp + 0.44, y, ZM + 1.10), (sp + 0.44, y, ZM + 1.20), 0.075, 'machinery_bare', n=12)                     # flange and gauge on the discharge
        bolts.bolt_circle((sp + 0.44, y, ZM + 1.20), (0, 0, 1), 0.06, 6, r=0.007, h=0.006)
        mb.cyl((sp + 0.44, y - sd * 0.06, ZM + 1.34), (sp + 0.44, y - sd * 0.085, ZM + 1.34), 0.05, 'placard_white', n=12)
    # expansion tank under the ceiling with a sight glass
    mb.lathe((22.25, 0, ZC - 0.26), (1, 0, 0), [(0, 0.08), (0.06, 0.17), (0.94, 0.17), (1.0, 0.08)], 'machinery_bare', n=20)
    for s in (22.45, 23.05):
        mb.tube((s - 0.02, 0, ZC - 0.26), (s + 0.02, 0, ZC - 0.26), 0.18, 0.17, 'structure_steel', n=20)
        mb.box(s - 0.02, s + 0.02, -0.03, 0.03, ZC - 0.09, ZC, 'structure_steel')
    mb.cyl((22.75, -0.172, ZC - 0.36), (22.75, -0.172, ZC - 0.16), 0.012, 'glass_port', n=6)
    mb.pipe([(22.35, 0, ZC - 0.43), (22.35, 0, ZC - 0.50), (22.35, 0.6, ZC - 0.50), (22.35, 1.1, ZC - 0.42)], 0.025, 'copper_pipe', n=8)
    mb.box(22.55, 22.95, 0.171, 0.174, ZC - 0.31, ZC - 0.23, 'hazard_yellow')
    # aft end, where the hull necks in: breaker cabinet to starboard, workbench to port
    a0, a1 = 23.25, 24.10
    w = wmin(a0, a1, ZM + 0.2, ZM + 1.75) - 0.03
    mb.box(a0, a1, w - 0.22, w, ZM + 0.25, ZM + 1.75, 'lining_panel_dark')
    for r in range(4):
        for c in range(7):
            s = a0 + 0.10 + 0.108 * c; z = ZM + 1.58 - 0.24 * r
            mb.box(s - 0.035, s + 0.035, w - 0.232, w - 0.22, z - 0.06, z + 0.06, 'machinery_dark')
            mb.box(s - 0.012, s + 0.012, w - 0.25, w - 0.232, z - 0.01 + (0.03 if (r * 7 + c) % 5 else -0.03), z + 0.01 + (0.03 if (r * 7 + c) % 5 else -0.03), 'placard_white' if (r * 7 + c) % 5 else 'armour_paint_red')
    mb.box(a0 + 0.05, a1 - 0.05, w - 0.224, w - 0.22, ZM + 0.38, ZM + 0.58, 'hazard_yellow')
    mb.box(a0 + 0.15, a1 - 0.15, w - 0.226, w - 0.224, ZM + 0.44, ZM + 0.52, 'machinery_dark')
    for (s, z) in ((a0 + 0.03, ZM + 0.30), (a1 - 0.03, ZM + 0.30), (a0 + 0.03, ZM + 1.70), (a1 - 0.03, ZM + 1.70)):
        bolts.bolt((s, w - 0.22, z), (0, -1, 0), r=0.01, h=0.006)
    mb.pipe([(a0 + 0.4, w - 0.11, ZM + 1.75), (a0 + 0.4, w - 0.11, ZM + 1.84), (a0 + 0.4, 0.9, ZC - 0.10), (a0 + 0.4, 0.2, ZC - 0.06)], 0.03, 'cable_black', n=8)
    wp = wmin(a0, a1, ZM, ZM + 0.95) - 0.03
    mb.box(a0, a1, -wp, -wp + 0.42, ZM + 0.86, ZM + 0.90, 'structure_steel')                                             # bench top
    mb.box(a0 + 0.02, a1 - 0.02, -wp, -wp + 0.40, ZM, ZM + 0.86, 'lining_panel_dark')
    for k in range(3):
        for q in range(3):
            s = a0 + 0.04 + 0.27 * k; z = ZM + 0.08 + 0.26 * q
            mb.box(s, s + 0.25, -wp + 0.40, -wp + 0.412, z, z + 0.23, 'armour_paint_red_dark'); mb.box(s + 0.07, s + 0.18, -wp + 0.412, -wp + 0.43, z + 0.16, z + 0.18, 'machinery_bare')
    mb.box(a0 + 0.08, a0 + 0.22, -wp + 0.22, -wp + 0.40, ZM + 0.90, ZM + 0.98, 'machinery_dark')                         # vice
    mb.box(a0 + 0.09, a0 + 0.21, -wp + 0.40, -wp + 0.46, ZM + 0.94, ZM + 1.04, 'machinery_dark'); mb.box(a0 + 0.09, a0 + 0.21, -wp + 0.30, -wp + 0.34, ZM + 0.98, ZM + 1.04, 'machinery_dark')
    mb.cyl((a0 + 0.15, -wp + 0.46, ZM + 0.96), (a0 + 0.15, -wp + 0.54, ZM + 0.96), 0.01, 'machinery_bare', n=6); mb.cyl((a0 + 0.07, -wp + 0.53, ZM + 0.96), (a0 + 0.23, -wp + 0.53, ZM + 0.96), 0.006, 'machinery_bare', n=5)
    mb.box(a0 + 0.42, a0 + 0.78, -wp + 0.08, -wp + 0.30, ZM + 0.90, ZM + 1.08, 'armour_paint_red'); mb.cyl((a0 + 0.47, -wp + 0.19, ZM + 1.11), (a0 + 0.73, -wp + 0.19, ZM + 1.11), 0.01, 'machinery_bare', n=6)   # toolbox
    wq = wmin(a0, a1, ZM + 1.15, ZM + 1.70) - 0.02
    mb.box(a0 + 0.05, a1 - 0.05, -wq, -wq + 0.015, ZM + 1.15, ZM + 1.70, 'machinery_dark')                               # shadow board
    for k in range(6):
        s = a0 + 0.13 + 0.125 * k
        mb.box(s - 0.012, s + 0.012, -wq + 0.015, -wq + 0.03, ZM + 1.25, ZM + 1.50 + 0.025 * k, 'machinery_bare')
        mb.box(s - 0.025, s + 0.025, -wq + 0.015, -wq + 0.035, ZM + 1.20, ZM + 1.26, 'machinery_bare' if k % 2 else 'hazard_yellow')
    extinguisher(mb, a0 - 0.25, -wmin(a0 - 0.4, a0 - 0.1, ZM + 0.3, ZM + 0.9) + 0.02, ZM + 0.35, (0, 1))
    mb.box(S['eng_fwd'] + 0.08, S['eng_fwd'] + 0.084, -1.02, -0.62, ZM + 1.86, ZM + 1.98, 'hazard_yellow')         # "ear protection" sign
    cable_tray(mb, S['eng_fwd'] + 0.5, 22.15, 0.0, ZC)
    # lower deck, round the reactor: local panel, radiation trefoil stand-in, floor line, drain valve
    s0, s1 = S['eng_fwd'] + 0.35, 22.55; z = ZL + 1.0
    wl = wmin(S['eng_fwd'] + 0.3, S['eng_fwd'] + 0.9, ZL + 0.9, ZL + 1.5) - 0.03
    mb.box(S['eng_fwd'] + 0.30, S['eng_fwd'] + 0.90, wl - 0.10, wl, ZL + 0.95, ZL + 1.50, 'lining_panel_dark')
    mb.box(S['eng_fwd'] + 0.36, S['eng_fwd'] + 0.62, wl - 0.105, wl - 0.10, ZL + 1.20, ZL + 1.42, 'screen_glow')
    for q in range(3):
        mb.cyl((S['eng_fwd'] + 0.72 + 0.0, wl - 0.10, ZL + 1.40 - 0.09 * q), (S['eng_fwd'] + 0.72, wl - 0.115, ZL + 1.40 - 0.09 * q), 0.022, ('light_red', 'hazard_yellow', 'screen_glow')[q], n=8)
    mb.cyl((S['eng_fwd'] + 0.78, wl - 0.10, ZL + 1.05), (S['eng_fwd'] + 0.78, wl - 0.15, ZL + 1.05), 0.035, 'armour_paint_red', n=10)           # scram button
    for sd in (-1, 1):
        mb.box(s0 + 0.1, s1 - 0.1, sd * 0.98 - 0.025, sd * 0.98 + 0.025, ZL + 0.001, ZL + 0.003, 'hazard_yellow')
        mb.cyl((0.5 * (s0 + s1) - 0.5, sd * 0.745, z), (0.5 * (s0 + s1) - 0.5, sd * 0.75, z), 0.13, 'hazard_yellow', n=16)                       # warning disc on the vessel
        mb.cyl((0.5 * (s0 + s1) - 0.5, sd * 0.749, z), (0.5 * (s0 + s1) - 0.5, sd * 0.753, z), 0.045, 'machinery_dark', n=10)
        mb.cyl((0.5 * (s0 + s1) + 0.45, sd * 0.70, z + 0.2), (0.5 * (s0 + s1) + 0.45, sd * 0.84, z + 0.2), 0.03, 'machinery_bare', n=8)          # instrument tap
        mb.cyl((0.5 * (s0 + s1) + 0.45, sd * 0.84, z + 0.2), (0.5 * (s0 + s1) + 0.45, sd * 0.865, z + 0.2), 0.055, 'placard_white', n=12)
    mb.pipe([(s0 + 0.5, 0, z - 0.74), (s0 + 0.5, 0, ZL + 0.12), (s0 + 0.5, 0.5, ZL + 0.12)], 0.03, 'copper_pipe', n=8)
    mb.tube((s0 + 0.5, 0.5, ZL + 0.12), (s0 + 0.5, 0.52, ZL + 0.12), 0.06, 0.045, 'armour_paint_red', n=12)
    finish('engineering_details', mb, parent, group='interior'); finish('engineering_detail_bolts', bolts, parent, sharp=60, group='fasteners')

def lower_deck_details(parent):
    mb = MB()
    # avionics aisle: cable tray, cable drops into each rack, battery boxes on the centreline side of the gear wells
    cable_tray(mb, 4.7, S['hold_fwd'] - 0.3, 0.0, ZCL - 0.05, w=0.26)
    for sd in (-1, 1):
        for k in range(2):
            s = 4.85 + k * 0.64
            mb.pipe([(s, 0.10 * sd, ZCL - 0.10), (s, 0.45 * sd, ZCL - 0.14), (s, 0.70 * sd, ZCL - 0.30), (s, 0.70 * sd, ZL + 1.70)], 0.016, 'cable_black', n=6)
            mb.box(s - 0.25, s + 0.25, sd * 0.62 - (0.004 if sd > 0 else 0), sd * 0.62 + (0 if sd > 0 else 0.004), ZL + 1.62, ZL + 1.68, 'placard_white')
    for k in range(3):
        s = 6.15 + 0.52 * k
        mb.box(s, s + 0.46, -1.26, -0.86, ZL, ZL + 0.42, 'machinery_dark')
        mb.box(s + 0.02, s + 0.44, -1.24, -0.88, ZL + 0.42, ZL + 0.44, 'structure_steel')
        for (ds, m) in ((0.12, 'armour_paint_red'), (0.34, 'machinery_bare')):
            mb.cyl((s + ds, -1.06, ZL + 0.44), (s + ds, -1.06, ZL + 0.49), 0.022, m, n=8)
        mb.box(s + 0.10, s + 0.36, -0.86, -0.857, ZL + 0.16, ZL + 0.28, 'hazard_yellow')
        if k < 2: mb.pipe([(s + 0.34, -1.06, ZL + 0.48), (s + 0.43, -1.06, ZL + 0.55), (s + 0.52 + 0.12, -1.06, ZL + 0.48)], 0.012, 'cable_black', n=5)
    mb.pipe([(6.27, -1.06, ZL + 0.48), (6.0, -1.06, ZL + 0.70), (5.80, -0.95, ZL + 1.20)], 0.012, 'armour_paint_red', n=5)
    intercom(mb, S['hold_fwd'], -1, -0.80, ZL + 1.40)
    extinguisher(mb, S['hold_fwd'], 0.78, ZL + 0.30, (-1, 0))
    mb.box(4.50, 4.54, -0.35, 0.35, ZL + 0.9, ZL + 1.5, 'lining_panel_dark')                                             # maintenance terminal on the forward end
    mb.box(4.54, 4.545, -0.28, 0.28, ZL + 1.12, ZL + 1.45, 'screen_glow')
    mb.obox((4.62, 0, ZL + 1.02), (0.08, 0, 0.012), (0, 0.24, 0), (-0.001, 0, 0.008), 'machinery_dark')
    # hold: on the forward bulkhead clear of the door leaves, strap racks above the gear wells; lashing points on the walls
    sa = S['hold_fwd'] + 0.08
    for sd in (-1, 1):
        y0 = sd * 1.22
        if wmin(sa, sa + 0.2, ZL + 0.2, ZL + 1.6) < 1.75: continue
        mb.box(sa, sa + 0.03, min(y0, y0 + sd * 0.45), max(y0, y0 + sd * 0.45), ZL + 1.62, ZL + 1.68, 'structure_steel')
        for q in range(4):
            y = y0 + sd * (0.06 + 0.11 * q)
            mb.cyl((sa + 0.03, y, ZL + 1.65), (sa + 0.10, y, ZL + 1.65), 0.008, 'machinery_bare', n=5)
            mb.tube((sa + 0.05, y, ZL + 1.53), (sa + 0.09, y, ZL + 1.53), 0.11 - 0.012 * (q % 2), 0.05, 'hazard_yellow', n=14)        # coiled ratchet straps
    Lf = spec.LIFT
    for sd in (-1, 1):
        for k in range(4):
            s = Lf['s0'] + 0.5 + k * 0.9
            w = wmin(s - 0.1, s + 0.1, ZL + 0.7, ZL + 0.9) - 0.02
            if abs(w) < Lf['half_w'] + 0.5: continue
            mb.box(s - 0.06, s + 0.06, sd * w - (0.03 if sd > 0 else 0), sd * w + (0 if sd > 0 else 0.03), ZL + 0.72, ZL + 0.88, 'structure_steel')
            mb.tube((s - 0.008, sd * (w - 0.05), ZL + 0.78), (s + 0.008, sd * (w - 0.05), ZL + 0.78), 0.04, 0.028, 'machinery_bare', n=10)
    sb = S['hold_aft']
    mb.box(sb - 0.004, sb, -0.30, 0.30, ZL + 2.02, ZL + 2.12, 'hazard_yellow')                                           # "lander bay" sign over the aft door
    intercom(mb, sb, -1, -0.82, ZL + 1.40)
    finish('lower_deck_details', mb, parent, group='interior')

def vestibule_details(parent):
    mb = MB()
    sa = S['cockpit_aft'] + 0.08; sb = S['vestibule_aft']
    cable_tray(mb, sa + 0.45, sb - 0.35, -0.2, ZC, w=0.26)
    intercom(mb, sb, -1, -0.82, ZM + 1.40)
    # port side: suit lockers with helmets on a shelf, boots under the bench
    w = wmin(6.5, 8.0, ZM, ZM + 1.9) - 0.04
    for k in range(3):
        a = 6.55 + 0.5 * k
        mb.box(a, a + 0.48, -w, -w + 0.42, ZM, ZM + 1.85, 'lining_panel_dark')
        mb.box(a + 0.03, a + 0.45, -w + 0.42, -w + 0.432, ZM + 0.06, ZM + 1.79, 'lining_panel')
        mb.box(a + 0.10, a + 0.38, -w + 0.432, -w + 0.436, ZM + 1.10, ZM + 1.60, 'glass_port')                           # window on the suit
        mb.box(a + 0.39, a + 0.42, -w + 0.432, -w + 0.46, ZM + 0.90, ZM + 1.04, 'machinery_bare')
        mb.box(a + 0.16, a + 0.32, -w + 0.432, -w + 0.435, ZM + 1.66, ZM + 1.71, 'placard_white')
    for (s, y, m) in ((S['cockpit_aft'] + 0.22, -1.85, 'machinery_dark'), (S['cockpit_aft'] + 0.22, -1.55, 'machinery_dark'), (S['cockpit_aft'] + 0.22, -1.15, 'structure_primer')):
        mb.box(s, s + 0.26, y - 0.05, y + 0.05, ZM, ZM + 0.24, m); mb.box(s + 0.12, s + 0.30, y - 0.05, y + 0.05, ZM, ZM + 0.09, m)   # boots
    mb.box(sa, sa + 0.02, -2.05, -0.75, ZM + 1.50, ZM + 1.52, 'structure_steel')                                         # coat hooks over the bench
    for q in range(5):
        mb.cyl((sa, -1.95 + 0.27 * q, ZM + 1.47), (sa + 0.07, -1.95 + 0.27 * q, ZM + 1.49), 0.008, 'machinery_bare', n=5)
    mb.box(sa + 0.03, sa + 0.09, -1.75, -1.45, ZM + 0.95, ZM + 1.46, 'armour_paint_red_dark')                            # a jacket left hanging
    # by the hatch and the ladder: emergency torch, placards, a hazard edge round the well
    y0, y1, s0, s1 = LADDER[2], LADDER[3], LADDER[0], LADDER[1]
    for (a, b, c, d) in ((s0 - 0.06, s0, y0 - 0.06, y1 + 0.06), (s1, s1 + 0.06, y0 - 0.06, y1 + 0.06), (s0, s1, y0 - 0.06, y0), (s0, s1, y1, y1 + 0.06)):
        mb.box(a, b, c, d, ZM + 0.001, ZM + 0.003, 'hazard_yellow')
    mb.box(sb - 0.004, sb, 0.70, 1.10, ZM + 1.50, ZM + 1.75, 'placard_white')
    mb.cyl((sb - 0.03, 0.80, ZM + 1.15), (sb - 0.03, 0.80, ZM + 1.37), 0.022, 'hazard_yellow', n=8); mb.box(sb - 0.02, sb, 0.77, 0.83, ZM + 1.20, ZM + 1.24, 'structure_steel')
    extinguisher(mb, sb, 1.45, ZM + 0.25, (-1, 0))
    finish('vestibule_details', mb, parent, group='interior')

def build(H):
    parent = empty('interior', 'wayfarer')
    ports(H, parent)
    crew_hatch(H, parent)
    dn = doors(parent)
    vestibule(parent)
    crew_deck(parent)
    mission_bay(parent)
    engineering(parent)
    lower_deck(parent)
    vestibule_details(parent); crew_deck_details(parent); mission_bay_details(parent); engineering_details(parent); lower_deck_details(parent)
    return dict(doors=len(dn), seats=14)
