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
    return dict(doors=len(dn), seats=14)
