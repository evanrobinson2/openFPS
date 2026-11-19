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

class Face:
    """A flat panel face to place controls on: origin c, unit vectors right and up; the normal is right x up."""
    def __init__(self, c, right, up):
        self.c, self.r, self.u = c, kit.vnorm(right), kit.vnorm(up); self.n = kit.vcross(self.r, self.u)
    def at(self, u, v, h=0.0):
        return kit.vadd(self.c, kit.vadd(kit.vmul(self.r, u), kit.vadd(kit.vmul(self.u, v), kit.vmul(self.n, h))))
    def plate(self, mb, u, v, w, h, t, m):
        mb.obox(self.at(u, v, t / 2), kit.vmul(self.r, w / 2), kit.vmul(self.u, h / 2), kit.vmul(self.n, t / 2), m)
    def toggle(self, mb, u, v, m='machinery_bare'):
        mb.cyl(self.at(u, v), self.at(u, v, 0.005), 0.0075, 'machinery_dark', n=6)
        mb.cyl(self.at(u, v, 0.005), self.at(u, v + 0.007, 0.026), 0.0032, m, n=6)
    def guard(self, mb, u, v):
        self.toggle(mb, u, v)
        mb.obox(self.at(u, v + 0.004, 0.018), kit.vmul(self.r, 0.011), kit.vmul(self.u, 0.017), kit.vmul(self.n, 0.014), 'armour_paint_red')
    def knob(self, mb, u, v, r=0.012, h=0.016, m='machinery_dark'):
        mb.cyl(self.at(u, v), self.at(u, v, h * 0.35), r * 1.25, m, n=12)
        mb.cyl(self.at(u, v, h * 0.35), self.at(u, v, h), r, m, n=12)
        self.plate(mb, u, v + r * 0.5, 0.003, r, h + 0.001, 'placard_white')
    def key_grid(self, mb, u0, v0, cols, rows, pitch=0.017, size=0.011, m='machinery_bare'):
        for a in range(cols):
            for b in range(rows):
                mb.obox(self.at(u0 + a * pitch, v0 - b * pitch, 0.003), kit.vmul(self.r, size / 2), kit.vmul(self.u, size / 2), kit.vmul(self.n, 0.003), m)
    def gauge(self, mb, u, v, r=0.034, ang=0.6):
        mb.cyl(self.at(u, v), self.at(u, v, 0.012), r, 'machinery_dark', n=18)
        mb.cyl(self.at(u, v, 0.012), self.at(u, v, 0.0135), r * 0.86, 'rubber_black', n=18)
        d = kit.vadd(kit.vmul(self.r, math.sin(ang)), kit.vmul(self.u, math.cos(ang)))
        mb.obox(kit.vadd(self.at(u, v, 0.015), kit.vmul(d, r * 0.36)), kit.vmul(kit.vcross(d, self.n), 0.002), kit.vmul(d, r * 0.38), kit.vmul(self.n, 0.001), 'placard_white')
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            mb.bolt(self.at(u + r * 1.12 * math.cos(a), v + r * 1.12 * math.sin(a)), self.n, r=0.004, h=0.003, washer=False)
    def mfd(self, mb, u, v, w, h, glow='screen_glow', keys=(5, 4)):
        """A display with a row of bezel keys under it and a column down each side."""
        _screen(mb, self.at(u, v, 0.02), self.r, self.u, w, h, bezel=0.024, glow=glow)
        for k in range(keys[0]):
            self.plate(mb, u - w / 2 + (k + 0.5) * w / keys[0], v - h / 2 - 0.012, 0.016, 0.010, 0.025, 'machinery_bare')
        for k in range(keys[1]):
            for sx in (-1, 1):
                self.plate(mb, u + sx * (w / 2 + 0.012), v + h / 2 - (k + 0.5) * h / keys[1], 0.010, 0.016, 0.025, 'machinery_bare')
        for sx in (-1, 1):
            self.knob(mb, u + sx * (w / 2 + 0.012), v + h / 2 + 0.012, r=0.007, h=0.032)
    def placard(self, mb, u, v, w, h=0.010):
        self.plate(mb, u, v, w, h, 0.0012, 'placard_white')

def pilot_seat():
    """Flight seat: a shaped shell on a height-adjust base and floor rails, five-point harness with an inertia reel,
    armrests that pivot on the shell. Local frame: occupant faces +x, y to their left, floor at z = 0."""
    m = MB(); f = 'seat_fabric'; st = 'structure_steel'; dk = 'machinery_dark'
    def prof(pts, y0, y1, mat):
        m.prism([(x, y0, z) for x, z in pts], (0, y1 - y0, 0), mat)
    for y in (-0.20, 0.20):                                               # floor rails with stop blocks
        m.box(-0.62, 0.46, y - 0.028, y + 0.028, 0.0, 0.03, st)
        m.box(-0.62, 0.46, y - 0.012, y + 0.012, 0.03, 0.042, 'machinery_bare')
        for x in (-0.56, -0.30, -0.04, 0.22, 0.42):
            m.bolt((x, y + 0.02, 0.03), (0, 0, 1), r=0.008, h=0.005, washer=False)
        m.box(0.42, 0.46, y - 0.035, y + 0.035, 0.03, 0.07, 'hazard_yellow')
        m.box(-0.30, -0.16, y - 0.045, y + 0.045, 0.03, 0.10, dk); m.box(0.10, 0.24, y - 0.045, y + 0.045, 0.03, 0.10, dk)   # carriages
    m.box(-0.26, 0.20, -0.17, 0.17, 0.10, 0.27, dk)                       # height-adjust base
    for y in (-0.172, 0.172):                                             # scissor links
        m.obox((-0.03, y, 0.185), (0.20, 0, 0.07), (0, 0.008, 0), (-0.008, 0, 0.022), st)
        m.obox((-0.03, y, 0.185), (0.20, 0, -0.07), (0, 0.008, 0), (0.008, 0, 0.022), st)
        m.cyl((-0.03, y - 0.012, 0.185), (-0.03, y + 0.012, 0.185), 0.016, 'machinery_bare', n=10)
    prof([(-0.31, 0.27), (0.27, 0.29), (0.31, 0.35), (0.28, 0.41), (-0.29, 0.38)], -0.25, 0.25, st)                        # pan
    prof([(-0.26, 0.38), (0.26, 0.41), (0.30, 0.45), (0.25, 0.49), (-0.22, 0.455)], -0.20, 0.20, f)                        # cushion
    for y0, y1 in ((-0.25, -0.20), (0.20, 0.25)):
        prof([(-0.24, 0.38), (0.25, 0.41), (0.28, 0.47), (0.22, 0.52), (-0.20, 0.49)], y0, y1, f)                          # thigh bolsters
    shell = [(-0.31, 0.33), (-0.37, 0.60), (-0.43, 0.95), (-0.47, 1.22), (-0.455, 1.31), (-0.41, 1.31), (-0.40, 1.22), (-0.37, 0.95), (-0.315, 0.60), (-0.275, 0.40)]
    prof(shell, -0.255, 0.255, dk)
    prof([(-0.275, 0.42), (-0.315, 0.60), (-0.37, 0.95), (-0.392, 1.09), (-0.345, 1.10), (-0.305, 0.95), (-0.25, 0.62), (-0.22, 0.46)], -0.19, 0.19, f)   # back cushion
    for y0, y1 in ((-0.25, -0.19), (0.19, 0.25)):
        prof([(-0.30, 0.52), (-0.37, 0.95), (-0.385, 1.04), (-0.31, 1.03), (-0.275, 0.93), (-0.215, 0.56)], y0, y1, f)     # back bolsters
    prof([(-0.398, 1.11), (-0.412, 1.30), (-0.36, 1.33), (-0.335, 1.13)], -0.13, 0.13, f)                                 # headrest
    for y0, y1 in ((-0.19, -0.13), (0.13, 0.19)):
        prof([(-0.398, 1.12), (-0.41, 1.29), (-0.32, 1.30), (-0.30, 1.15)], y0, y1, f)                                    # headrest wings
    # the back of the shell: spine rib, inertia reel, strap guides, survival pack
    prof([(-0.33, 0.36), (-0.39, 0.60), (-0.45, 0.95), (-0.48, 1.16), (-0.46, 1.16), (-0.43, 0.95), (-0.37, 0.60)], -0.03, 0.03, st)
    for z, x in ((0.55, -0.375), (0.82, -0.42), (1.08, -0.465)):
        m.box(x - 0.012, x + 0.006, -0.255, 0.255, z - 0.012, z + 0.012, st)
        for y in (-0.22, -0.11, 0.11, 0.22):
            m.bolt((x - 0.012, y, z), (-1, 0, 0.17), r=0.006, h=0.004, washer=False)
    m.cyl((-0.50, -0.07, 1.20), (-0.50, 0.07, 1.20), 0.038, 'machinery_bare', n=14)                                        # inertia reel
    m.box(-0.50, -0.455, -0.085, -0.07, 1.16, 1.24, st); m.box(-0.50, -0.455, 0.07, 0.085, 1.16, 1.24, st)
    m.obox((-0.435, 0.0, 0.68), (0.03, 0, 0.005), (0, 0.16, 0), (-0.02, 0, 0.11), 'cable_black')                           # survival pack
    m.box(-0.47, -0.455, -0.03, 0.03, 0.70, 0.74, 'hazard_yellow')
    for y in (-0.085, 0.085):                                                                                             # shoulder straps
        prof([(-0.412, 1.305), (-0.40, 1.315), (-0.33, 1.105), (-0.342, 1.10)], y - 0.022, y + 0.022, 'cable_black')
        prof([(-0.342, 1.10), (-0.336, 1.105), (-0.205, 0.50), (-0.215, 0.495)], y - 0.022, y + 0.022, 'cable_black')
        m.box(-0.21, -0.19, y - 0.026, y + 0.026, 0.60, 0.64, 'machinery_bare')                                            # adjusters
    for y0, y1 in ((-0.20, -0.04), (0.04, 0.20)):                                                                         # lap straps
        m.box(-0.10, -0.055, y0, y1, 0.488, 0.494, 'cable_black')
    m.box(0.05, 0.095, -0.02, 0.02, 0.488, 0.494, 'cable_black')                                                           # crotch strap
    m.cyl((-0.08, 0, 0.488), (-0.08, 0, 0.512), 0.042, 'machinery_bare', n=14)                                             # rotary buckle
    m.cyl((-0.08, 0, 0.512), (-0.08, 0, 0.520), 0.022, 'armour_paint_red', n=10)
    for sy in (-1, 1):                                                                                                    # armrests
        y = sy * 0.30
        prof([(-0.33, 0.615), (0.16, 0.625), (0.19, 0.645), (0.16, 0.67), (-0.33, 0.66)], y - 0.035, y + 0.035, f)
        m.box(-0.34, 0.12, y - 0.022, y + 0.022, 0.595, 0.62, st)
        m.cyl((-0.33, y - 0.04, 0.63), (-0.33, y + 0.04, 0.63), 0.022, 'machinery_bare', n=10)
        m.box(-0.40, -0.31, sy * 0.255 - 0.012, sy * 0.255 + 0.012 + sy * 0.03, 0.60, 0.66, st)
    m.cyl((0.08, -0.26, 0.33), (0.22, -0.275, 0.36), 0.008, 'machinery_bare', n=6)                                        # slide and height levers
    m.capsule((0.22, -0.275, 0.36), (0.26, -0.275, 0.365), 0.012, 'hazard_yellow', n=6)
    m.cyl((0.08, 0.26, 0.33), (0.22, 0.275, 0.36), 0.008, 'machinery_bare', n=6)
    m.capsule((0.22, 0.275, 0.36), (0.26, 0.275, 0.365), 0.012, 'rubber_black', n=6)
    return m

THR_S, THR_Z = 3.06, ZF + 0.47          # throttle axle
STICK_S = 2.62

def build_flight_deck(H, parent):
    con = MB(); bolts = MB()
    P = 'lining_panel_dark'
    # glare shield under the windscreen, cut to the hull, with a padded hood over the panel
    deck_slab(con, 0.64, 0.05, 0.80, 1.85, 'machinery_dark', clear=0.03, step=0.15)
    con.prism([(1.70, -1.58, 0.64), (1.88, -1.58, 0.70), (1.88, -1.58, 0.775), (1.70, -1.58, 0.69)], (0, 3.16, 0), 'rubber_black')
    # main instrument panel: a sloped face from under the hood down to knee height
    top, bot = (1.84, 0.70), (2.02, ZF + 0.24)
    for y0, y1 in ((-1.58, -0.26), (-0.26, 0.26), (0.26, 1.58)):
        con.prism([(top[0] - 0.12, y0, top[1]), (top[0], y0, top[1]), (bot[0], y0, bot[1]), (bot[0] - 0.16, y0, bot[1])], (0, y1 - y0, 0), P)
    L = math.hypot(bot[0] - top[0], bot[1] - top[1])
    upv = kit.vnorm((top[0] - bot[0], 0, top[1] - bot[1]))
    M = Face((top[0], 0.0, top[1]), (0, 1, 0), upv)                      # u = y, v = 0 at the top edge, -L at the bottom
    for side in (-1, 1):
        yc = side * PILOT_Y
        M.mfd(con, yc - 0.20, -0.165, 0.30, 0.215)                       # primary flight display
        M.mfd(con, yc + 0.20, -0.165, 0.30, 0.215)                       # navigation display
        for k in range(8):                                               # switch row under the displays
            (M.guard if k in (2, 5) else M.toggle)(con, yc - 0.33 + 0.058 * k, -L + 0.055)
            M.placard(con, yc - 0.33 + 0.058 * k, -L + 0.028, 0.034, 0.008)
        M.knob(con, yc + 0.20, -L + 0.055, r=0.014); M.knob(con, yc + 0.27, -L + 0.055, r=0.014)
        yo = side * 1.33                                                 # outboard: warning display, clock, vents
        M.mfd(con, yo, -0.13, 0.15, 0.17, glow='light_red', keys=(3, 3))
        M.gauge(con, yo - 0.045, -0.305, r=0.036, ang=0.9); M.gauge(con, yo + 0.045, -0.305, r=0.036, ang=-0.5)
        M.plate(con, side * 1.50, -0.09, 0.07, 0.07, 0.012, 'machinery_dark')
        for k in range(4):
            M.plate(con, side * 1.50, -0.064 - 0.017 * k, 0.058, 0.006, 0.016, 'machinery_bare')
        bolts.bolt_line(M.at(side * 0.30, -0.012), M.at(side * 1.55, -0.012), M.n, pitch=0.16, r=0.006, h=0.004)
        bolts.bolt_line(M.at(side * 0.30, -L + 0.012), M.at(side * 1.55, -L + 0.012), M.n, pitch=0.16, r=0.006, h=0.004)
    M.mfd(con, 0.0, -0.058, 0.36, 0.085, keys=(0, 2))                    # centre: engine strip, clear of the pedestal
    M.gauge(con, -0.265, -0.17, r=0.034, ang=0.4)                        # standby instruments down the strips beside the pedestal
    M.gauge(con, 0.265, -0.255, r=0.034, ang=-0.7); M.gauge(con, 0.265, -0.335, r=0.034, ang=1.2)
    M.plate(con, -0.265, -0.30, 0.05, 0.12, 0.010, 'machinery_dark')     # landing gear lever in its gate
    con.cyl(M.at(-0.265, -0.27, 0.01), M.at(-0.265, -0.285, 0.075), 0.006, 'machinery_bare', n=6)
    con.cyl(M.at(-0.29, -0.285, 0.075), M.at(-0.24, -0.285, 0.075), 0.017, 'placard_white', n=10)
    for k in range(3):
        M.plate(con, -0.265, -0.323 - 0.012 * k, 0.010, 0.008, 0.012, 'light_red' if k else 'screen_glow')
    for k in range(3):                                                   # annunciator block
        for b in range(3):
            M.plate(con, 0.239 + 0.026 * k, -0.14 - 0.02 * b, 0.022, 0.016, 0.006, ('hazard_yellow', 'light_red', 'machinery_bare')[(k + b) % 3])
    # mode control panel on the face of the hood
    Hd = Face((1.881, 0.0, 0.7375), (0, 1, 0), (0, 0, 1))
    Hd.plate(con, 0.0, 0.0, 0.92, 0.062, 0.006, 'machinery_dark')
    for k in range(6):
        u = -0.385 + 0.154 * k
        Hd.knob(con, u - 0.03, -0.004, r=0.011, h=0.020)
        Hd.plate(con, u + 0.022, 0.006, 0.05, 0.020, 0.008, 'screen_glow')
        Hd.plate(con, u + 0.022, -0.018, 0.016, 0.010, 0.011, 'machinery_bare')
    for side in (-1, 1):
        Hd.plate(con, side * 0.62, 0.0, 0.07, 0.045, 0.010, 'armour_paint_red')          # master warning
        Hd.plate(con, side * 0.71, 0.0, 0.07, 0.045, 0.010, 'hazard_yellow')             # master caution
    # pedestal between the seats
    con.box(2.02, 3.30, -0.20, 0.20, ZF, ZF + 0.50, P)
    con.prism([(2.02, -0.20, ZF + 0.50), (2.02, -0.20, ZF + 0.54), (2.44, -0.20, ZF + 0.50)], (0, 0.40, 0), P)
    Sl = Face((2.44, 0.0, ZF + 0.50), (0, 1, 0), (2.02 - 2.44, 0, 0.04))                 # sloped front of the pedestal
    for side in (-1, 1):                                                 # two keypad units
        Sl.plate(con, side * 0.10, 0.21, 0.175, 0.40, 0.004, 'machinery_dark')
        _screen(con, Sl.at(side * 0.10, 0.325, 0.006), Sl.r, Sl.u, 0.13, 0.10, bezel=0.010)
        Sl.key_grid(con, side * 0.10 - 0.0595, 0.235, 8, 5, pitch=0.017, size=0.011)
        Sl.key_grid(con, side * 0.10 - 0.06, 0.135, 4, 3, pitch=0.026, size=0.019, m='placard_white')
        Sl.knob(con, side * 0.10 + 0.055, 0.105, r=0.012)
        Sl.plate(con, side * 0.10 + 0.05, 0.142, 0.03, 0.014, 0.008, 'hazard_yellow')
        for (u, v) in ((-0.08, 0.02), (0.08, 0.02), (-0.08, 0.40), (0.08, 0.40)):
            bolts.bolt(Sl.at(side * 0.10 + u, v, 0.004), Sl.n, r=0.005, h=0.003, washer=False)
    T = Face((2.44, 0.0, ZF + 0.50), (0, 1, 0), (-1, 0, 0))                              # pedestal top: u = y, v = -(s - 2.44)
    T.mfd(con, 0.0, -0.20, 0.24, 0.17, keys=(5, 3))                                      # systems display
    con.box(2.90, 3.20, -0.17, 0.17, ZF + 0.50, ZF + 0.53, 'machinery_dark')              # throttle quadrant
    for y in (-0.105, -0.035, 0.035, 0.105):
        con.box(2.93, 3.17, y - 0.011, y + 0.011, ZF + 0.53, ZF + 0.532, 'rubber_black')
        for k in range(5):
            con.box(2.95 + 0.05 * k, 2.953 + 0.05 * k, y + 0.014, y + 0.03, ZF + 0.53, ZF + 0.5315, 'placard_white')
    for sy in (-1, 1):
        con.cyl((3.05, sy * 0.20, ZF + 0.40), (3.05, sy * 0.222, ZF + 0.40), 0.075, 'machinery_bare', n=20)   # trim wheels
        con.cyl((3.05, sy * 0.222, ZF + 0.40), (3.05, sy * 0.228, ZF + 0.40), 0.05, 'rubber_black', n=20)
        bolts.bolt_line((2.10, sy * 0.201, ZF + 0.06), (3.24, sy * 0.201, ZF + 0.06), (0, sy, 0), pitch=0.19, r=0.009, h=0.005)
        bolts.bolt_line((2.50, sy * 0.19, ZF + 0.50), (2.86, sy * 0.19, ZF + 0.50), (0, 0, 1), pitch=0.12, r=0.005, h=0.003)
    # radio panel at the back of the pedestal
    T.plate(con, 0.0, -0.81, 0.34, 0.085, 0.004, 'machinery_dark')
    for k in range(4):
        T.plate(con, -0.12 + 0.08 * k, -0.795, 0.06, 0.022, 0.008, 'screen_glow')
        T.knob(con, -0.12 + 0.08 * k, -0.832, r=0.010)
    con.cyl((2.84, 0.15, ZF + 0.50), (2.84, 0.15, ZF + 0.58), 0.008, 'machinery_bare', n=6)     # park brake handle
    con.cyl((2.84, 0.125, ZF + 0.585), (2.84, 0.175, ZF + 0.585), 0.012, 'hazard_yellow', n=8)
    con.cyl((3.36, 0.0, ZF + 0.02), (3.36, 0.0, ZF + 0.36), 0.055, 'armour_paint_red', n=14)    # fire extinguisher on the aft face
    con.cyl((3.36, 0.0, ZF + 0.36), (3.36, 0.0, ZF + 0.42), 0.022, 'machinery_bare', n=8)
    con.box(3.30, 3.36, -0.065, 0.065, ZF + 0.22, ZF + 0.26, 'structure_steel')
    # side consoles along both walls
    deck_slab(con, ZF + 0.62, 0.62 - 0.001, 2.04, 3.70, P, holes=[(2.0, 3.75, -1.18, 1.18)], step=0.2, clear=0.02)
    for side in (-1, 1):
        C = Face((2.04, side * 1.18, ZF + 0.62), (0, 1, 0), (-1, 0, 0))              # u = y from the inboard edge, v = -(s - 2.04)
        o = side                                                                    # outboard direction in u
        for a in range(4):                                                           # forward switch panel
            for b in range(4):
                (C.guard if (a, b) in ((0, 0), (3, 3)) else C.toggle)(con, o * (0.06 + 0.045 * a), -0.10 - 0.05 * b)
        C.plate(con, o * 0.13, -0.19, 0.22, 0.26, 0.002, 'machinery_dark')
        for k in range(3):
            C.knob(con, o * 0.29, -0.10 - 0.07 * k, r=0.013)
        con.box(STICK_S - 0.07, STICK_S + 0.07, side * 1.30 - 0.07, side * 1.30 + 0.07, ZF + 0.62, ZF + 0.632, 'machinery_dark')    # stick base
        con.sphere((STICK_S, side * 1.30, ZF + 0.632), 0.048, 'rubber_black', n=12, squash=(1, 1, 0.55))                             # gaiter
        con.prism([(2.72, side * 1.22, ZF + 0.62), (2.72, side * 1.22, ZF + 0.67), (3.02, side * 1.22, ZF + 0.66), (3.04, side * 1.22, ZF + 0.62)], (0, side * 0.14, 0), 'seat_fabric')   # forearm rest
        C.mfd(con, o * 0.20, -1.24, 0.19, 0.22, keys=(4, 4))                         # side display
        C.plate(con, o * 0.17, -1.50, 0.26, 0.18, 0.003, 'machinery_dark')           # circuit breakers
        C.key_grid(con, o * 0.17 - 0.105, -1.43, 10, 6, pitch=0.0235, size=0.012, m='rubber_black')
        C.placard(con, o * 0.17, -1.405, 0.22, 0.008)
        con.pipe([(2.36, side * 1.42, ZF + 0.62), (2.36, side * 1.42, ZF + 0.86), (2.30, side * 1.34, ZF + 0.95), (2.26, side * 1.24, ZF + 0.94)], 0.006, 'machinery_bare', n=6)   # map light
        con.cyl((2.27, side * 1.25, ZF + 0.945), (2.245, side * 1.20, ZF + 0.925), 0.02, 'machinery_dark', n=10)
        bolts.bolt_line((2.10, side * 1.181, ZF + 0.54), (3.64, side * 1.181, ZF + 0.54), (0, -side, 0), pitch=0.22, r=0.008, h=0.005)
        con.box(2.20, 3.50, side * 1.181 - 0.004, side * 1.181 + 0.004, ZF + 0.10, ZF + 0.40, 'machinery_dark')                    # stowage net frame
        for k in range(6):
            con.box(2.22 + 0.25 * k, 2.225 + 0.25 * k, side * 1.176 - 0.004, side * 1.176 + 0.004, ZF + 0.10, ZF + 0.40, 'cable_black')
        # rudder pedals on a hanging bar, heel plates on the floor
        con.cyl((2.10, side * PILOT_Y - 0.22, ZF + 0.30), (2.10, side * PILOT_Y + 0.22, ZF + 0.30), 0.014, 'machinery_bare', n=8)
        for dy in (-0.13, 0.13):
            py = side * PILOT_Y + dy
            con.cyl((2.10, py, ZF + 0.30), (2.17, py, ZF + 0.14), 0.011, 'machinery_dark', n=6)
            con.obox((2.18, py, ZF + 0.15), (0.012, 0, 0.004), (0, 0.055, 0), (-0.03, 0, 0.085), 'machinery_bare')
            for k in range(4):
                con.obox((2.19 + 0.002, py, ZF + 0.10 + 0.035 * k), (0.004, 0, 0), (0, 0.05, 0), (0, 0, 0.004), 'rubber_black')
            con.box(2.22, 2.50, py - 0.07, py + 0.07, ZF, ZF + 0.006, 'deck_grating')
            for k in range(5):
                con.box(2.24 + 0.055 * k, 2.25 + 0.055 * k, py - 0.06, py + 0.06, ZF + 0.006, ZF + 0.010, 'machinery_bare')
    # overhead panel: guarded rows, rotary selectors, two engine fire handles
    zt = float(spec.hull_params(3.7)[1]) + spec.OFF_LINING - 0.10
    con.box(3.20, 4.05, -0.36, 0.36, zt - 0.07, zt, P)
    O = Face((3.20, 0.0, zt - 0.07), (0, 1, 0), (1, 0, 0))                           # faces down; v = s - 3.20
    for a in range(9):
        for b in range(6):
            u = -0.28 + 0.07 * a; v = 0.20 + 0.10 * b
            if (a, b) in ((0, 0), (8, 0), (4, 3)): O.guard(con, u, v)
            elif b == 5 and a % 2 == 0: O.knob(con, u, v, r=0.012)
            else: O.toggle(con, u, v)
        O.placard(con, -0.28 + 0.07 * a, 0.15, 0.04, 0.007)
    for sy in (-1, 1):
        con.cyl(O.at(sy * 0.10, 0.07), O.at(sy * 0.10, 0.07, 0.05), 0.008, 'machinery_bare', n=6)       # fire handles
        con.cyl(O.at(sy * 0.10 - 0.035, 0.07, 0.055), O.at(sy * 0.10 + 0.035, 0.07, 0.055), 0.013, 'armour_paint_red', n=8)
        con.box(3.25, 4.00, sy * 0.36, sy * 0.44, zt - 0.03, zt, 'light_panel')
        bolts.bolt_line(O.at(sy * 0.345, 0.03), O.at(sy * 0.345, 0.82), O.n, pitch=0.13, r=0.006, h=0.004)
    # standby compass hanging from the roof on the centreline, and grab handles on the brow rail
    i0, i1, jb, js, _ = H.rect('canopy')
    pr = H.pt(H.si(2.15), 0, spec.OFF_LINING, 1)
    con.cyl((pr[0], 0.0, pr[2]), (pr[0], 0.0, pr[2] - 0.07), 0.008, 'machinery_dark', n=6)
    con.sphere((pr[0], 0.0, pr[2] - 0.11), 0.045, 'machinery_dark', n=12)
    con.cyl((pr[0] + 0.03, 0.0, pr[2] - 0.11), (pr[0] + 0.047, 0.0, pr[2] - 0.11), 0.03, 'screen_glow', n=12)
    for side in (-1, 1):
        ia = H.si(2.75); a = H.pt(ia, jb, spec.OFF_LINING - 0.03, side); b = H.pt(ia + 2, jb, spec.OFF_LINING - 0.03, side)
        na = H.nrm(ia, jb, side); ins = kit.vmul(na, -0.07)
        con.pipe([a, kit.vadd(a, ins), kit.vadd(b, ins), b], 0.011, 'hazard_yellow', n=8)
    finish('flight_deck_consoles', con, parent, group='cockpit')
    finish('flight_deck_bolts', bolts, parent, sharp=60, group='fasteners')
    # moving controls, each its own object pivoted where it turns
    for name, side in (('stick_pilot', -1), ('stick_copilot', 1)):
        st = MB(); y = side * 1.30; z0 = ZF + 0.632
        st.cyl((STICK_S, y, z0), (STICK_S - 0.012, y, z0 + 0.13), 0.011, 'machinery_dark', n=8)
        st.capsule((STICK_S - 0.012, y, z0 + 0.13), (STICK_S - 0.03, y, z0 + 0.25), 0.021, 'rubber_black', n=10)
        st.obox((STICK_S - 0.034, y, z0 + 0.265), (0.02, 0, 0.004), (0, 0.022, 0), (-0.004, 0, 0.02), 'machinery_dark')
        st.cyl((STICK_S - 0.038, y - side * 0.008, z0 + 0.285), (STICK_S - 0.040, y - side * 0.008, z0 + 0.295), 0.007, 'armour_paint_red', n=8)
        st.cyl((STICK_S - 0.034, y + side * 0.010, z0 + 0.285), (STICK_S - 0.036, y + side * 0.010, z0 + 0.292), 0.006, 'placard_white', n=8)
        st.obox((STICK_S - 0.05, y, z0 + 0.20), (0.008, 0, 0), (0, 0.005, 0), (0, 0, 0.02), 'machinery_bare')                 # trigger
        finish(name, st, parent, pivot=(STICK_S, y, z0), group='cockpit')
    for name, ys in (('throttle_port', (-0.105, -0.035)), ('throttle_stbd', (0.035, 0.105))):
        th = MB()
        for y in ys:
            th.obox((THR_S - 0.012, y, THR_Z + 0.075), (0.007, 0, 0), (0, 0.004, 0), (-0.012, 0, 0.075), 'machinery_bare')
            th.cyl((THR_S - 0.024, y - 0.022, THR_Z + 0.16), (THR_S - 0.024, y + 0.022, THR_Z + 0.16), 0.016, 'hazard_yellow' if abs(y) > 0.05 else 'placard_white', n=10)
        finish(name, th, parent, pivot=(THR_S, 0.0, THR_Z), group='cockpit')
    # seats
    for name, s, y, hd in (('seat_pilot', PILOT_S, -PILOT_Y, (-1, 0)), ('seat_copilot', PILOT_S, PILOT_Y, (-1, 0))):
        finish(name, fittings.place(pilot_seat(), s, y, ZF, hd), parent, pivot=(s, y, ZF), group='cockpit')
    for name, s, y, hd in (('seat_engineer', REAR_S, -REAR_Y, (0, -1)), ('seat_gunner', REAR_S, REAR_Y, (0, 1))):
        finish(name, fittings.place(fittings.seat(swivel=True), s, y, ZF, hd), parent, pivot=(s, y, ZF), group='cockpit')
    # rear stations: wall consoles facing the two swivel seats
    rs = MB()
    deck_slab(rs, ZF + 0.74, 0.74 - 0.001, 4.35, 5.55, P, holes=[(4.3, 5.6, -1.72, 1.72)], step=0.2, clear=0.02)
    for side in (-1, 1):
        for k, s in enumerate((4.62, 4.95, 5.28)):
            _screen(rs, (s, side * 2.02, ZF + 1.08), (side, 0, 0), (0, side * 0.34, 0.94), 0.26, 0.30, glow='screen_glow' if k != 1 else 'light_red')
        _screen(rs, (4.95, side * 1.90, ZF + 0.742), (side, 0, 0), (0, side, 0), 0.50, 0.16)
        rs.cyl((4.95, side * 1.80, ZF + 0.74), (4.95, side * 1.78, ZF + 0.88), 0.014, 'machinery_dark', n=8)
        rs.capsule((4.95, side * 1.78, ZF + 0.88), (4.95, side * 1.775, ZF + 0.96), 0.022, 'rubber_black', n=8)
        R = Face((4.35, side * 1.72, ZF + 0.74), (0, 1, 0), (-1, 0, 0))
        R.key_grid(rs, side * 0.07 - 0.04, -0.10, 5, 4, pitch=0.022, size=0.015)
        R.key_grid(rs, side * 0.07 - 0.04, -1.02, 5, 4, pitch=0.022, size=0.015)
        for k in range(4):
            R.toggle(rs, side * 0.06, -0.30 - 0.05 * k)
        R.knob(rs, side * 0.06, -0.80, r=0.012)
    finish('rear_stations', rs, parent, group='cockpit')

def build(H):
    parent = empty('cockpit', 'wayfarer', at=(S['cockpit_fwd'], 0, ZF))
    build_canopy(H, parent)
    build_flight_deck(H, parent)
    return dict(pilot_eye=(PILOT_S - 0.12, PILOT_Y, ZF + 1.22))
