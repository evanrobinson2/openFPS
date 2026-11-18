"""Cockpit: the wraparound canopy (glazing, pillars, brow and sill rails) and everything on the flight deck:
glare shield, instrument panel, pedestal, side consoles, two pilot seats, two rear stations, controls."""
import math
import numpy as np
import spec, kit
from kit import MB, finish, empty
from structure import deck_slab
import fittings

S = spec.ST
ZF = spec.Z_MAIN
PILOT_S, PILOT_Y = 2.95, 0.72
REAR_S, REAR_Y = 4.95, 1.05

def build_canopy(H, parent):
    i0, i1, jb, js, _ = H.rect('canopy')
    pill = [H.si(s) for s in spec.CANOPY['pillars']]
    glass = MB(); frame = MB(); bolts = MB()
    for side in (1, -1):
        for a, b in zip(pill, pill[1:]):
            H.slab(glass, a, b, jb, js, side, -0.035, -0.085, 'glass_canopy', margin=0.045)
        for i in pill[1:]:
            H.rib_s(frame, i, jb, js, side, 0.06, spec.OFF_LINING - 0.02, 0.075, 'structure_steel')
            for j in range(jb, js + 1):
                for ds in (-0.045, 0.045):
                    p = H.pt(i, j, 0.06, side); bolts.bolt((p[0] + ds, p[1], p[2]), H.nrm(i, j, side), r=0.013, h=0.008, washer=False)
        for j, hw in ((jb, 0.085), (js, 0.085)):
            H.rib_j(frame, j, i0, i1, side, 0.07, spec.OFF_LINING - 0.02, hw, 'structure_steel')
            for i in range(i0, i1 + 1, 2):
                bolts.bolt(H.pt(i, j, 0.07, side), H.nrm(i, j, side), r=0.014, h=0.009, washer=False)
        # armoured brow: a visor plate standing proud above the glazing
        H.slab(frame, H.si(1.6), i1, max(jb - 2, 1), jb, side, 0.16, 0.07, 'armour_gunmetal_d', margin=0.02)
    finish('canopy_glazing', glass, parent, group='cockpit')
    finish('canopy_frame', frame, parent, group='cockpit')
    finish('canopy_bolts', bolts, parent, sharp=60, group='fasteners')

def _screen(mb, c, right, up, w, h, bezel=0.018, glow='screen_glow'):
    """A display: bezel box with a glowing face. c = centre of the face, right/up = unit vectors in its plane."""
    n = kit.vcross(right, up)
    mb.obox(kit.vadd(c, kit.vmul(n, -0.02)), kit.vmul(right, w / 2 + bezel), kit.vmul(up, h / 2 + bezel), kit.vmul(n, 0.02), 'machinery_dark')
    mb.obox(kit.vadd(c, kit.vmul(n, 0.002)), kit.vmul(right, w / 2), kit.vmul(up, h / 2), kit.vmul(n, 0.002), glow)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.bolt(kit.vadd(c, kit.vadd(kit.vmul(right, sx * (w / 2 + bezel * 0.5)), kit.vmul(up, sy * (h / 2 + bezel * 0.5)))), n, r=0.006, h=0.004, washer=False)

def build_flight_deck(H, parent):
    con = MB()
    # glare shield under the windscreen, cut to the hull
    deck_slab(con, 0.64, 0.05, 0.80, 1.85, 'machinery_dark', clear=0.03, step=0.15)
    con.box(1.80, 1.86, -1.55, 1.55, 0.60, 0.70, 'rubber_black')                       # padded lip
    # main instrument panel: a sloped face from the glare shield down to knee height
    top, bot = (1.84, 0.60), (2.04, ZF + 0.30)
    for y0, y1 in ((-1.55, -0.26), (-0.26, 0.26), (0.26, 1.55)):
        con.prism([(top[0] - 0.10, y0, top[1]), (top[0], y0, top[1]), (bot[0], y0, bot[1]), (bot[0] - 0.14, y0, bot[1])], (0, y1 - y0, 0), 'lining_panel_dark')
    sl = kit.vnorm((bot[0] - top[0], 0, bot[1] - top[1])); upv = kit.vmul(sl, -1); right = (0, 1, 0)
    nrm = kit.vcross(right, upv)           # points aft and up, toward the pilots
    def on_panel(y, t):                    # t = 0 at the top edge, 1 at the bottom
        p = kit.vlerp((top[0], y, top[1]), (bot[0], y, bot[1]), t); return kit.vadd(p, kit.vmul(nrm, 0.004))
    for y in (-PILOT_Y - 0.38, -PILOT_Y + 0.02, PILOT_Y - 0.02, PILOT_Y + 0.38):
        _screen(con, on_panel(y, 0.42), right, upv, 0.34, 0.24)
    _screen(con, on_panel(0.0, 0.36), right, upv, 0.40, 0.20)
    for y in (-1.36, 1.36):
        _screen(con, on_panel(y, 0.40), right, upv, 0.16, 0.22, glow='light_red')
    for k in range(9):                     # switch row along the bottom of the panel
        for side in (-1, 1):
            p = on_panel(side * (0.36 + 0.115 * k), 0.84)
            con.cyl(p, kit.vadd(p, kit.vmul(nrm, 0.022)), 0.008, 'machinery_bare', n=6)
    # pedestal between the seats: throttles, a display, a trim wheel
    con.box(2.04, 3.30, -0.20, 0.20, ZF, ZF + 0.50, 'lining_panel_dark')
    con.prism([(2.04, -0.20, ZF + 0.50), (2.04, -0.20, ZF + 0.62), (2.40, -0.20, ZF + 0.50)], (0, 0.40, 0), 'lining_panel_dark')
    _screen(con, (2.70, 0.0, ZF + 0.502), (0, 1, 0), (-1, 0, 0), 0.26, 0.20)
    for y in (-0.10, -0.035, 0.035, 0.10):
        con.box(2.96, 3.16, y - 0.012, y + 0.012, ZF + 0.50, ZF + 0.515, 'machinery_dark')       # throttle slots
        con.cyl((3.05, y, ZF + 0.50), (3.02, y, ZF + 0.62), 0.010, 'machinery_bare', n=8)
        con.sphere((3.02, y, ZF + 0.63), 0.024, 'hazard_yellow' if abs(y) > 0.05 else 'armour_paint_red', n=8)
    con.cyl((3.24, -0.215, ZF + 0.40), (3.24, -0.20, ZF + 0.40), 0.07, 'machinery_bare', n=16)
    con.bolt_line((2.10, -0.201, ZF + 0.06), (3.24, -0.201, ZF + 0.06), (0, -1, 0), pitch=0.19, r=0.009, h=0.005)
    con.bolt_line((2.10, 0.201, ZF + 0.06), (3.24, 0.201, ZF + 0.06), (0, 1, 0), pitch=0.19, r=0.009, h=0.005)
    # side consoles along both walls
    deck_slab(con, ZF + 0.62, 0.62 - 0.001, 2.04, 3.70, 'lining_panel_dark', holes=[(2.0, 3.75, -1.18, 1.18)], step=0.2, clear=0.02)
    for side in (-1, 1):
        y = side * 1.30
        con.cyl((2.62, y, ZF + 0.62), (2.60, y, ZF + 0.80), 0.016, 'machinery_dark', n=8)           # side stick
        con.capsule((2.60, y, ZF + 0.80), (2.585, y, ZF + 0.90), 0.024, 'rubber_black', n=8)
        _screen(con, (3.15, side * 1.36, ZF + 0.622), (0, 1, 0), (-1, 0, 0), 0.20, 0.30)
        for k in range(5):
            con.cyl((2.20 + 0.07 * k, side * 1.28, ZF + 0.62), (2.20 + 0.07 * k, side * 1.28, ZF + 0.645), 0.009, 'machinery_bare', n=6)
        # rudder pedals
        for dy in (-0.13, 0.13):
            py = side * PILOT_Y + dy
            con.obox((2.16, py, ZF + 0.16), (0.012, 0, 0.0), (0, 0.055, 0), (0.03, 0, 0.085), 'machinery_bare')
            con.cyl((2.10, py, ZF + 0.03), (2.16, py, ZF + 0.10), 0.012, 'machinery_dark', n=6)
    # overhead switch panel
    zt = float(spec.hull_params(3.7)[1]) + spec.OFF_LINING - 0.10
    con.box(3.35, 4.05, -0.34, 0.34, zt - 0.06, zt, 'lining_panel_dark')
    for k in range(6):
        for y in (-0.24, -0.12, 0.0, 0.12, 0.24):
            con.cyl((3.42 + 0.105 * k, y, zt - 0.06), (3.42 + 0.105 * k, y, zt - 0.082), 0.008, 'machinery_bare', n=6)
    con.box(3.40, 4.00, -0.42, -0.36, zt - 0.03, zt, 'light_panel'); con.box(3.40, 4.00, 0.36, 0.42, zt - 0.03, zt, 'light_panel')
    finish('flight_deck_consoles', con, parent, group='cockpit')
    # seats
    for name, s, y, hd in (('seat_pilot', PILOT_S, -PILOT_Y, (-1, 0)), ('seat_copilot', PILOT_S, PILOT_Y, (-1, 0)),
                           ('seat_engineer', REAR_S, -REAR_Y, (0, -1)), ('seat_gunner', REAR_S, REAR_Y, (0, 1))):
        finish(name, fittings.place(fittings.seat(swivel=name in ('seat_engineer', 'seat_gunner')), s, y, ZF, hd), parent, pivot=(s, y, ZF), group='cockpit')
    # rear stations: wall consoles facing the two swivel seats
    rs = MB()
    deck_slab(rs, ZF + 0.74, 0.74 - 0.001, 4.35, 5.55, 'lining_panel_dark', holes=[(4.3, 5.6, -1.72, 1.72)], step=0.2, clear=0.02)
    for side in (-1, 1):
        for k, s in enumerate((4.62, 4.95, 5.28)):
            _screen(rs, (s, side * 2.02, ZF + 1.08), (side, 0, 0), (0, side * 0.34, 0.94), 0.26, 0.30, glow='screen_glow' if k != 1 else 'light_red')
        _screen(rs, (4.95, side * 1.90, ZF + 0.742), (side, 0, 0), (0, side, 0), 0.50, 0.16)
        rs.cyl((4.95, side * 1.80, ZF + 0.74), (4.95, side * 1.78, ZF + 0.88), 0.014, 'machinery_dark', n=8)
        rs.capsule((4.95, side * 1.78, ZF + 0.88), (4.95, side * 1.775, ZF + 0.96), 0.022, 'rubber_black', n=8)
    finish('rear_stations', rs, parent, group='cockpit')

def build(H):
    parent = empty('cockpit', 'wayfarer', at=(S['cockpit_fwd'], 0, ZF))
    build_canopy(H, parent)
    build_flight_deck(H, parent)
    return dict(pilot_eye=(PILOT_S - 0.12, PILOT_Y, ZF + 1.22))
