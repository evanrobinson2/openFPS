"""Fittings that repeat around the ship: seats, doors, ladders, lockers, rails. Each is built in a local frame
(x forward, y left, z up, origin on the floor) and placed with place()."""
import math
from kit import MB, vadd, vmul

def place(local, s, y, z, heading=(-1.0, 0.0)):
    """Copy of a local-frame builder placed at (s, y, z). heading is the local forward direction in the ship's (s, y) plane:
    (-1, 0) faces the nose, (0, 1) faces starboard, (0, -1) faces port, (1, 0) faces aft."""
    hs, hy = heading; ls, ly = -hy, hs      # local left in ship (s, y)
    return local.transformed(lambda p: (s + p[0] * hs + p[1] * ls, y + p[0] * hy + p[1] * ly, z + p[2]))

def seat(harness=True, armrests=True, swivel=False):
    """Crew seat on floor rails. Hip point about 0.50 above the floor; the occupant faces +x."""
    m = MB(); f = 'seat_fabric'; st = 'structure_steel'; dk = 'machinery_dark'
    for y in (-0.19, 0.19):                                   # floor rails
        m.box(-0.50, 0.40, y - 0.025, y + 0.025, 0.0, 0.035, st)
        for x in (-0.42, -0.12, 0.18, 0.34):
            m.bolt((x, y, 0.035), (0, 0, 1), r=0.011, h=0.007, washer=False)
    if swivel:
        m.cyl((-0.05, 0, 0.035), (-0.05, 0, 0.30), 0.085, dk, n=14); m.cyl((-0.05, 0, 0.035), (-0.05, 0, 0.07), 0.19, st, n=18)
    else:
        for y in (-0.19, 0.19):                               # carriage blocks and legs
            m.box(-0.30, -0.18, y - 0.04, y + 0.04, 0.035, 0.09, dk); m.box(0.12, 0.24, y - 0.04, y + 0.04, 0.035, 0.09, dk)
            m.obox((-0.02, y, 0.19), (0.30, 0, 0), (0, 0.018, 0), (0, 0, 0.11), st)
    m.box(-0.30, 0.26, -0.24, 0.24, 0.30, 0.36, st)           # pan frame
    m.box(-0.27, 0.25, -0.225, 0.225, 0.36, 0.45, f)          # cushion
    for y in (-0.235, 0.235):
        m.box(-0.25, 0.22, y - 0.035, y + 0.035, 0.40, 0.49, f)   # thigh bolsters
    lean = math.radians(14); c, s_ = math.cos(lean), math.sin(lean)
    up = (-s_, 0, c); fw = (c, 0, s_)
    base = (-0.27, 0, 0.42)
    def P(u, w): return vadd(base, vadd(vmul(up, u), vmul(fw, w)))
    m.obox(P(0.36, -0.045), vmul(fw, 0.035), (0, 0.24, 0), vmul(up, 0.38), st)        # back shell
    m.obox(P(0.34, 0.03), vmul(fw, 0.045), (0, 0.215, 0), vmul(up, 0.33), f)          # back cushion
    for y in (-0.225, 0.225):
        m.obox(P(0.30, 0.05), vmul(fw, 0.05), (0, 0.035, 0), vmul(up, 0.26), f)       # back bolsters
        m.V[-8:] = [(p[0], p[1] + y, p[2]) for p in m.V[-8:]]
    m.obox(P(0.85, 0.02), vmul(fw, 0.05), (0, 0.13, 0), vmul(up, 0.10), f)            # headrest
    m.obox(P(0.73, -0.03), vmul(fw, 0.02), (0, 0.04, 0), vmul(up, 0.06), st)
    if armrests:
        for y in (-0.29, 0.29):
            m.box(-0.22, 0.16, y - 0.035, y + 0.035, 0.62, 0.665, f); m.box(-0.22, -0.16, y - 0.02, y + 0.02, 0.45, 0.62, st)
    if harness:
        for y in (-0.09, 0.09):
            m.obox(P(0.42, 0.085), vmul(fw, 0.006), (0, 0.022, 0), vmul(up, 0.30), 'cable_black')
        m.box(-0.02, 0.03, -0.035, 0.035, 0.45, 0.47, 'machinery_bare')               # buckle
    return m

def ladder(height, width=0.46, rung=0.28):
    """Vertical ladder standing at the origin, climbing side facing +x."""
    m = MB(); st = 'structure_steel'
    for y in (-width / 2, width / 2):
        m.cyl((0, y, 0), (0, y, height), 0.022, st, n=10)
        for z in (0.15, height / 2, height - 0.15):
            m.box(-0.12, 0.0, y - 0.015, y + 0.015, z - 0.015, z + 0.015, st); m.bolt((-0.12, y, z), (-1, 0, 0), r=0.01, h=0.006, washer=False)
    k = int(height / rung)
    for i in range(1, k + 1):
        z = i * height / (k + 1)
        m.cyl((0, -width / 2, z), (0, width / 2, z), 0.016, 'machinery_bare', n=8)
    return m

def door_leaf(width=1.0, height=2.0, thick=0.05, m='lining_panel_dark'):
    """Sliding door leaf, lower-left corner at the origin, lying in the x = 0 plane across y."""
    d = MB()
    d.box(-thick / 2, thick / 2, 0, width, 0, height, m)
    for sx in (-1, 1):
        x = sx * thick / 2
        d.box(min(x, x + sx * 0.012), max(x, x + sx * 0.012), 0.08, width - 0.08, 1.05, 1.75, 'structure_steel')      # upper panel
        d.box(min(x, x + sx * 0.014), max(x, x + sx * 0.014), 0.28, width - 0.28, 1.20, 1.60, 'glass_port')
        d.box(min(x, x + sx * 0.012), max(x, x + sx * 0.012), 0.08, width - 0.08, 0.12, 0.92, 'structure_steel')      # lower panel
        d.box(min(x, x + sx * 0.05), max(x, x + sx * 0.05), width - 0.16, width - 0.10, 0.95, 1.15, 'hazard_yellow')  # handle
        for (y, z) in ((0.12, 0.16), (width - 0.12, 0.16), (0.12, 0.88), (width - 0.12, 0.88), (0.12, 1.09), (width - 0.12, 1.09), (0.12, 1.71), (width - 0.12, 1.71)):
            d.bolt((x + sx * 0.012, y, z), (sx, 0, 0), r=0.011, h=0.006, washer=False)
    return d

def handrail(p0, p1, mb, standoff=(0, 0, 0.0), r=0.016, m='machinery_bare'):
    mb.pipe([vadd(p0, standoff), p0, p1, vadd(p1, standoff)][1:3], r, m, n=8)
    return mb
