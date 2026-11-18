"""Engines: two main pods (octagonal intake face, ribbed barrel, nozzle), two upper pods under an armoured cowl,
the centre main nozzle on the aft thrust plate, the pylons and the plumbing between them. Each pod is its own object,
so it can be swapped, damaged or animated on its own."""
import math
import numpy as np
from mathutils import geometry, Vector
import spec, kit
from kit import MB, finish, empty
from structure import section_outline

E = spec.ENG

def flange(mb, bolts, s, y, z, r, w=0.07, t=0.06, nb=24, m='machinery_bare', br=0.018):
    """Bolted flange ring around a pod barrel at station s."""
    mb.lathe((s - t / 2, y, z), (1, 0, 0), [(0, r), (0, r + w), (t, r + w), (t, r)], m, n=40, cap0=False, cap1=False)
    bolts.bolt_circle((s + t / 2, y, z), (1, 0, 0), r + w * 0.5, nb, r=br, h=0.012)
    bolts.bolt_circle((s - t / 2, y, z), (-1, 0, 0), r + w * 0.5, nb, r=br, h=0.012, ph=math.pi / nb)

def ribbed(mb, s0, s1, y, z, r, pitch=0.16, depth=0.05, m='machinery_dark', n=40):
    prof = []; s = s0; k = 0
    while s < s1 - 1e-6:
        e = min(s + pitch * 0.55, s1); prof += [(s - s0, r), (e - s0, r)]
        g = min(s + pitch, s1)
        if g > e + 1e-6: prof += [(e - s0 + 0.012, r - depth), (g - s0 - 0.012, r - depth)]
        s = g
    mb.lathe((s0, y, z), (1, 0, 0), prof, m, n=n, cap0=False, cap1=False)

def nozzle(mb, s0, s1, y, z, r0, r1, petals=16, m='machinery_heat'):
    """Convergent nozzle with separate petals, a glowing throat and a plug."""
    L = s1 - s0
    mb.lathe((s0, y, z), (1, 0, 0), [(0, r0), (L * 0.15, r0 * 0.995), (L, r1), (L, r1 - 0.035), (L * 0.2, r0 - 0.06), (0.0, r0 - 0.06)], m, n=petals * 3, cap0=False, cap1=False)
    for k in range(petals):                      # petal stiffeners and their actuator rods
        a = 2 * math.pi * (k + 0.5) / petals; c, sn = math.cos(a), math.sin(a)
        p0 = (s0 + L * 0.12, y + c * (r0 + 0.012), z + sn * (r0 + 0.012)); p1 = (s0 + L * 0.94, y + c * (r1 + 0.02), z + sn * (r1 + 0.02))
        mb.cyl(p0, p1, 0.022, 'machinery_dark', n=6)
        mb.bolt(kit.vlerp(p0, p1, 0.5), (0, c, sn), r=0.014, h=0.012, washer=False)
    mb.lathe((s0 - 0.3, y, z), (1, 0, 0), [(0, r0 - 0.07), (0.3 + L * 0.5, r0 * 0.80), (0.3 + L * 0.5, 0.0)], 'engine_glow', n=petals * 2, cap0=False, cap1=False)
    mb.lathe((s0 - 0.2, y, z), (1, 0, 0), [(0, r0 * 0.34), (0.2 + L * 0.55, r0 * 0.30), (0.2 + L * 1.02, 0.02)], 'machinery_dark', n=petals * 2, cap0=False, cap1=True)

def main_pod(side):
    mb = MB(); bolts = MB()
    y = side * E['pod_y']; z = E['pod_z']; r = E['pod_r']; s0 = E['pod_s0']; s1 = E['pod_s1']
    # octagonal intake housing with a rectangular intake cut into its face
    ro = r / math.cos(math.pi / 8) * 0.985
    oct_ = [(ro * math.cos(math.pi / 8 + k * math.pi / 4), ro * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    hw, hh, ch = 0.50, 0.72, 0.14
    hole = [(-hw + ch, -hh), (hw - ch, -hh), (hw, -hh + ch), (hw, hh - ch), (hw - ch, hh), (-hw + ch, hh), (-hw, hh - ch), (-hw, -hh + ch)]
    loops = [[Vector((a, b, 0)) for a, b in oct_], [Vector((a, b, 0)) for a, b in hole]]
    flat = [p for lp in loops for p in lp]
    idx = [mb.v((s0, y + p.x, z + p.y)) for p in flat]
    for tri in geometry.tessellate_polygon(loops):
        p0, p1, p2 = flat[tri[0]], flat[tri[1]], flat[tri[2]]
        cr = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x)
        q = tri if cr < 0 else tri[::-1]          # the face looks forward (-s)
        mb.f([idx[i] for i in q], 'armour_paint_red')
    back = [mb.v((s0 + 1.45, y + a, z + b)) for a, b in oct_]
    for k in range(8):
        mb.f((idx[k], idx[(k + 1) % 8], back[(k + 1) % 8], back[k]), 'armour_gunmetal_b' if k % 2 else 'armour_gunmetal_a')
    mb.f(back, 'armour_gunmetal_b')
    # intake duct: walls, a dark back and five guide vanes
    hin = [mb.v((s0 + 0.85, y + a * 0.86, z + b * 0.9)) for a, b in hole]
    for k in range(8):
        mb.f((idx[8 + k], hin[k], hin[(k + 1) % 8], idx[8 + (k + 1) % 8]), 'machinery_dark')
    mb.f(hin[::-1], 'substructure_dark')
    for k in range(5):
        yy = y + (-0.36 + 0.18 * k)
        mb.box(s0 + 0.10, s0 + 0.60, yy - 0.012, yy + 0.012, z - hh * 0.93, z + hh * 0.93, 'machinery_bare')
    # raised intake frame, bolted on
    for (a0, a1, b0, b1) in ((-hw - 0.09, hw + 0.09, hh, hh + 0.09), (-hw - 0.09, hw + 0.09, -hh - 0.09, -hh), (-hw - 0.09, -hw, -hh, hh), (hw, hw + 0.09, -hh, hh)):
        mb.box(s0 - 0.05, s0, y + a0, y + a1, z + b0, z + b1, 'armour_paint_red_dark')
    for a in (-hw - 0.045, hw + 0.045):
        bolts.bolt_line((s0 - 0.05, y + a, z - hh), (s0 - 0.05, y + a, z + hh), (-1, 0, 0), pitch=0.18, r=0.016, h=0.01)
    for b in (-hh - 0.045, hh + 0.045):
        bolts.bolt_line((s0 - 0.05, y - hw, z + b), (s0 - 0.05, y + hw, z + b), (-1, 0, 0), pitch=0.18, r=0.016, h=0.01)
    for k in range(8):                              # bolts round the edge of the octagon face
        a = kit.vlerp((s0, y + oct_[k][0], z + oct_[k][1]), (s0, y + oct_[(k + 1) % 8][0], z + oct_[(k + 1) % 8][1]), 0.0)
        b = (s0, y + oct_[(k + 1) % 8][0], z + oct_[(k + 1) % 8][1])
        ca = (s0, y, z)
        bolts.bolt_line(kit.vlerp(a, ca, 0.06), kit.vlerp(b, ca, 0.06), (-1, 0, 0), pitch=0.2, r=0.018, h=0.012, ends=False)
    # armour straps over the octagon
    for ds in (0.35, 1.05):
        mb.ngon_prism((s0 + ds, y, z), (s0 + ds + 0.18, y, z), ro + 0.035, 8, 'armour_gunmetal_d', ph=math.pi / 8)
    # ribbed barrel between two flanges
    rb = r * 0.93
    flange(mb, bolts, s0 + 1.50, y, z, rb, nb=32)
    ribbed(mb, s0 + 1.53, s0 + 4.10, y, z, rb, pitch=0.17, depth=0.055)
    flange(mb, bolts, s0 + 2.80, y, z, rb, nb=32, w=0.05, t=0.05)
    flange(mb, bolts, s0 + 4.13, y, z, rb, nb=32)
    # armour saddles: three plates over the top outboard quarter of the barrel
    for k, (a0, a1) in enumerate(((1.62, 2.70), (2.92, 4.02))):
        for (t0, t1) in ((20, 80), (86, 150)):
            sh = MB()
            n = 10; pts_o = []; pts_i = []
            for q in range(n + 1):
                t = math.radians(t0 + (t1 - t0) * q / n); c, sn = math.cos(t), math.sin(t) * 1.0
                pts_o.append((side * c * (rb + 0.085), sn * (rb + 0.085))); pts_i.append((side * c * (rb + 0.03), sn * (rb + 0.03)))
            poly = [(s0 + a0, y + a, z + b) for a, b in pts_o] + [(s0 + a0, y + a, z + b) for a, b in reversed(pts_i)]
            mb.prism(poly, (a1 - a0, 0, 0), 'armour_gunmetal_c' if (k + t0) % 3 else 'armour_gunmetal_a')
            for q in (1, n - 1):
                t = math.radians(t0 + (t1 - t0) * q / n); c, sn = math.cos(t), math.sin(t)
                bolts.bolt_line((s0 + a0 + 0.08, y + side * c * (rb + 0.085), z + sn * (rb + 0.085)), (s0 + a1 - 0.08, y + side * c * (rb + 0.085), z + sn * (rb + 0.085)), (0, side * c, sn), pitch=0.22, r=0.016, h=0.01)
    # convergent section and nozzle
    mb.lathe((s0 + 4.16, y, z), (1, 0, 0), [(0, rb), (0.25, rb), (1.05, rb * 0.90), (1.05, rb * 0.90 + 0.05), (1.12, rb * 0.90 + 0.05), (1.12, rb * 0.88)], 'armour_gunmetal_b', n=40, cap0=False, cap1=False)
    bolts.bolt_circle((s0 + 5.28, y, z), (1, 0, 0), rb * 0.90 + 0.025, 28, r=0.016, h=0.01)
    nozzle(mb, s0 + 5.28, s1, y, z, rb * 0.88, rb * 0.74, petals=18)
    return mb, bolts

def upper_pod(side):
    mb = MB(); bolts = MB()
    y = side * E['top_y']; z = E['top_z']; r = E['top_r']; s0 = E['top_s0']; s1 = E['top_s1']
    # round intake lip
    mb.lathe((s0, y, z), (1, 0, 0), [(0.10, r * 0.80), (0.0, r * 0.90), (0.06, r * 0.99), (0.35, r), (0.60, r)], 'armour_paint_red_dark', n=32, cap0=False, cap1=False)
    mb.lathe((s0 + 0.10, y, z), (1, 0, 0), [(0.0, r * 0.80), (0.55, r * 0.70), (0.55, 0.0)], 'machinery_dark', n=32, cap0=False, cap1=False)
    mb.lathe((s0 - 0.12, y, z), (1, 0, 0), [(0.0, 0.03), (0.30, r * 0.26), (0.70, r * 0.30)], 'machinery_bare', n=20, cap0=True, cap1=False)   # centre spike
    flange(mb, bolts, s0 + 0.62, y, z, r * 0.97, nb=24, w=0.05)
    ribbed(mb, s0 + 0.65, s0 + 3.70, y, z, r * 0.97, pitch=0.15, depth=0.045)
    flange(mb, bolts, s0 + 3.72, y, z, r * 0.97, nb=24, w=0.05)
    mb.lathe((s0 + 3.75, y, z), (1, 0, 0), [(0, r * 0.97), (0.45, r * 0.88)], 'armour_gunmetal_b', n=32, cap0=False, cap1=False)
    nozzle(mb, s0 + 4.20, s1, y, z, r * 0.88, r * 0.72, petals=14)
    return mb, bolts

def cowl(side):
    """Armoured cowl over an upper pod: four overlapping plates stepping down toward the tail, as in the concept."""
    mb = MB(); bolts = MB()
    y = side * E['top_y']; z = E['top_z']; r = E['top_r'] + 0.16
    seg = [(E['cowl_s0'] + 0.9, 23.9, 0.10), (23.7, 25.1, 0.05), (24.9, 26.3, 0.0), (26.1, E['cowl_s1'], -0.05)]
    for k, (a0, a1, lift) in enumerate(seg):
        rr = r + lift; n = 14; t0, t1 = -8, 172
        po = []; pi_ = []
        for q in range(n + 1):
            t = math.radians(t0 + (t1 - t0) * q / n); c, sn = math.cos(t), math.sin(t)
            po.append((side * c * rr, sn * rr * 0.92)); pi_.append((side * c * (rr - 0.07), sn * (rr - 0.07) * 0.92))
        poly = [(a0, y + a, z + b) for a, b in po] + [(a0, y + a, z + b) for a, b in reversed(pi_)]
        mb.prism(poly, (a1 - a0, 0, 0), ('armour_gunmetal_a', 'armour_gunmetal_c', 'armour_gunmetal_b', 'armour_gunmetal_d')[k])
        for q in (1, n // 2, n - 1):
            t = math.radians(t0 + (t1 - t0) * q / n); c, sn = math.cos(t), math.sin(t)
            p = lambda s: (s, y + side * c * rr, z + sn * rr * 0.92)
            bolts.bolt_line(p(a0 + 0.1), p(a1 - 0.1), (0, side * c, sn), pitch=0.24, r=0.018, h=0.012)
        for s in (a0 + 0.07, a1 - 0.07):
            for q in range(1, n, 2):
                t = math.radians(t0 + (t1 - t0) * q / n); c, sn = math.cos(t), math.sin(t)
                bolts.bolt((s, y + side * c * rr, z + sn * rr * 0.92), (0, side * c, sn), r=0.018, h=0.012)
    # red recognition stripe on the second plate
    a0, a1, lift = seg[1]; rr = r + lift + 0.012
    po = []; pi_ = []
    for q in range(5):
        t = math.radians(52 + 40 * q / 4); c, sn = math.cos(t), math.sin(t)
        po.append((side * c * rr, sn * rr * 0.92)); pi_.append((side * c * (rr - 0.02), sn * (rr - 0.02) * 0.92))
    mb.prism([(a0 + 0.15, y + a, z + b) for a, b in po] + [(a0 + 0.15, y + a, z + b) for a, b in reversed(pi_)], (a1 - a0 - 0.3, 0, 0), 'armour_paint_red')
    return mb, bolts

def pylons(side):
    mb = MB(); bolts = MB()
    y0 = side * 1.85; y1 = side * (E['pod_y'] - E['pod_r'] * 0.80); z = E['pod_z']
    for (s0, s1) in ((24.9, 25.7), (26.6, 27.3)):
        mb.prism([(s0, y0, z - 0.42), (s0 + 0.12, y0, z + 0.42), (s1 - 0.12, y0, z + 0.42), (s1, y0, z - 0.42)], (0, y1 - y0, 0), 'structure_steel')
        for zz in (z - 0.30, z + 0.30):
            bolts.bolt_line((s0 + 0.14, y1, zz), (s1 - 0.14, y1, zz), (0, -side, 0), pitch=0.16, r=0.018, h=0.012)
    # plumbing between the hull and the pod, and up to the upper pod
    for k, zz in enumerate((z + 0.75, z + 0.92, z - 0.85)):
        yy = side * (2.02 + 0.05 * k)
        mb.pipe([(23.9, yy, zz), (24.6, yy + side * 0.10, zz), (26.4, yy + side * 0.10, zz), (27.4, yy + side * 0.02, zz - 0.1), (28.0, side * 1.9, zz - 0.1)], 0.045 if k else 0.065, 'copper_pipe' if k == 1 else 'machinery_bare', n=10)
        for s in (24.9, 26.0, 27.0):
            mb.cyl((s - 0.03, yy + side * 0.10, zz), (s + 0.03, yy + side * 0.10, zz), 0.075 if not k else 0.058, 'machinery_dark', n=10)
    mb.pipe([(25.3, side * 2.6, z + 0.9), (25.3, side * 2.45, z + 1.25), (25.3, side * 2.35, E['top_z'] - E['top_r'] * 0.9)], 0.07, 'machinery_bare', n=10)
    mb.pipe([(26.9, side * 2.6, z + 0.9), (26.9, side * 2.45, z + 1.25), (26.9, side * 2.35, E['top_z'] - E['top_r'] * 0.9)], 0.07, 'machinery_bare', n=10)
    return mb, bolts

def core():
    mb = MB(); bolts = MB()
    s0 = E['core_s0']
    # aft thrust plate: the hull's closing bulkhead
    outer = section_outline(s0, clear=spec.OFF_LINING)          # outer skin outline
    loops = [[Vector((a, b, 0)) for a, b in outer]]
    flat = loops[0]
    ia = [mb.v((s0, p.x, p.y)) for p in flat]; ib = [mb.v((s0 + 0.12, p.x, p.y)) for p in flat]
    area = sum(flat[i].x * flat[(i + 1) % len(flat)].y - flat[(i + 1) % len(flat)].x * flat[i].y for i in range(len(flat)))
    order = list(range(len(flat))) if area > 0 else list(range(len(flat)))[::-1]
    mb.f([ib[i] for i in order], 'armour_gunmetal_d'); mb.f([ia[i] for i in order[::-1]], 'substructure_dark')
    for k in range(len(order)):
        a, b = order[k], order[(k + 1) % len(order)]
        mb.f((ia[a], ia[b], ib[b], ib[a]), 'armour_gunmetal_d')
    for k in range(0, len(flat), 2):
        p = flat[k]; c = Vector((0, 0, 0)); q = p + (c - p).normalized() * 0.12
        bolts.bolt((s0 + 0.12, q.x, q.y), (1, 0, 0), r=0.022, h=0.014)
    # centre main engine: gimbal ring, bell, glow
    r = E['core_r']
    mb.lathe((s0 + 0.12, 0, 0), (1, 0, 0), [(0, 0.95), (0.10, 0.95), (0.10, 0.62), (0.34, 0.55)], 'machinery_bare', n=40, cap0=False, cap1=False)
    bolts.bolt_circle((s0 + 0.22, 0, 0), (1, 0, 0), 0.80, 28, r=0.022, h=0.014)
    mb.lathe((s0 + 0.40, 0, 0), (1, 0, 0), [(0, 0.50), (0.25, 0.72), (0.65, 1.00), (1.20, r), (1.20, r - 0.04), (0.65, 0.95), (0.25, 0.67), (0.0, 0.44)], 'machinery_heat', n=48, cap0=False, cap1=False)
    for k in range(6):                                           # stiffening hoops on the bell
        t = 0.30 + 0.16 * k; rr = 0.50 + (r - 0.50) * (t / 1.20) ** 0.65
        mb.lathe((s0 + 0.40 + t, 0, 0), (1, 0, 0), [(0, rr), (0.0, rr + 0.035), (0.04, rr + 0.035), (0.04, rr)], 'machinery_dark', n=48, cap0=False, cap1=False)
    mb.lathe((s0 + 0.30, 0, 0), (1, 0, 0), [(0.0, 0.44), (0.9, 0.9), (0.9, 0.0)], 'engine_glow', n=32, cap0=False, cap1=False)
    for k in range(4):                                           # gimbal actuators
        a = math.pi / 4 + k * math.pi / 2; c, sn = math.cos(a), math.sin(a)
        mb.cyl((s0 + 0.12, 1.25 * c, 1.25 * sn), (s0 + 0.75, 0.86 * c, 0.86 * sn), 0.05, 'machinery_dark', n=10)
        mb.cyl((s0 + 0.55, 0.985 * c, 0.985 * sn), (s0 + 0.95, 0.735 * c, 0.735 * sn), 0.028, 'hydraulic_chrome', n=10)
        bolts.bolt_circle((s0 + 0.12, 1.25 * c, 1.25 * sn), (1, 0, 0), 0.09, 6, r=0.014, h=0.01)
    # four verniers in the corners of the thrust plate
    for (yy, zz) in ((1.25, 1.55), (-1.25, 1.55), (1.2, -1.5), (-1.2, -1.5)):
        mb.lathe((s0 + 0.12, yy, zz), (1, 0, 0), [(0, 0.16), (0.12, 0.14), (0.42, 0.24), (0.42, 0.21), (0.12, 0.11)], 'machinery_heat', n=16, cap0=False, cap1=False)
        mb.lathe((s0 + 0.2, yy, zz), (1, 0, 0), [(0.0, 0.11), (0.2, 0.17), (0.2, 0.0)], 'engine_glow', n=12, cap0=False, cap1=False)
        bolts.bolt_circle((s0 + 0.12, yy, zz), (1, 0, 0), 0.21, 8, r=0.012, h=0.009)
    return mb, bolts

def build(H):
    parent = empty('engines', 'wayfarer', at=(E['pod_s0'], 0, 0))
    allb = MB()
    for side, sn in ((1, 'stbd'), (-1, 'port')):
        for name, fn, piv in ((f'engine_main_pod_{sn}', main_pod, (E['pod_s0'], side * E['pod_y'], E['pod_z'])),
                              (f'engine_upper_pod_{sn}', upper_pod, (E['top_s0'], side * E['top_y'], E['top_z'])),
                              (f'engine_cowl_{sn}', cowl, (E['cowl_s0'], side * E['top_y'], E['top_z'])),
                              (f'engine_pylons_{sn}', pylons, (25.3, side * 1.85, E['pod_z']))):
            mb, bolts = fn(side)
            finish(name, mb, parent, pivot=piv, group='engines'); allb.merge(bolts)
    mb, bolts = core()
    finish('engine_core_and_thrust_plate', mb, parent, pivot=(E['core_s0'], 0, 0), group='engines'); allb.merge(bolts)
    finish('engine_bolts', allb, parent, sharp=60, group='fasteners')
    return dict(pods=5)
