"""Airframe: body skin (nose to fold hinge), upper deck, engine nacelles, tailcone, tail pylon, stabilator."""
import math
import numpy as np
import lib, recipe as RC
from lib import Mesh, T, R, S


def naca(c):
    """Unit half-thickness distribution (peak = 1) of a NACA 4-digit section."""
    return (0.2969 * np.sqrt(c) - 0.1260 * c - 0.3516 * c ** 2 + 0.2843 * c ** 3 - 0.1036 * c ** 4) / 0.3001


def airfoil_loop(le, te, t, k):
    """Closed loop in a local (chordwise, thickness) plane: upper surface LE->TE then lower TE->LE."""
    c = 0.5 * (1 - np.cos(np.linspace(0, np.pi, k)))
    y = t * naca(c)
    x = le + (te - le) * c
    return np.vstack([np.stack([x, y], 1), np.stack([x[-2:0:-1], -y[-2:0:-1]], 1)])


def build_body(ctx):
    m = ctx.n(144, 72)
    st = RC.body_stations(ctx.n(1.6, 3.6) if not ctx.fast else 5.0)
    rings = np.stack([RC.body_ring(s, m) for s in st])
    mesh = lib.loft(rings, cap0=True, cap1=True)
    return mesh


def half_super(s, zb, zt, w, n, k):
    a = np.linspace(0, np.pi, 240)
    x = w * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / n); z = zb + (zt - zb) * np.sin(a) ** (2 / n)
    p = lib.resample(np.stack([x, z], 1), k)
    return np.stack([np.full(k, s), p[:, 0], p[:, 1]], 1)


def build_deck(ctx):
    d = np.array(RC.DECK); u = np.sqrt(d[:, 0] - d[0, 0])
    fzt = lib.pchip(u, d[:, 1]); fw = lib.pchip(u, d[:, 2])
    st = [d[0, 0] + 0.1]
    ds = ctx.n(1.6, 3.6)
    while st[-1] < d[-1, 0]:
        st.append(min(d[-1, 0], st[-1] + float(np.clip(0.25 * (st[-1] - d[0, 0]) + 0.15, 0.15, ds))))
    k = ctx.n(64, 36); rings = []
    for s in st:
        uu = math.sqrt(s - d[0, 0]); zt = float(fzt(uu)); w = max(float(fw(uu)), 0.05)
        zb = min(float(RC.body_params(s)[1]) - 3.5, zt - 0.5)
        rings.append(half_super(s, zb, zt, w, 3.0, k))
    return lib.loft(np.array(rings), cap0=True, cap1=True)


def build_shaft_cover(ctx):
    d = np.array(RC.SHAFT_COVER); k = ctx.n(20, 12); rings = []
    for s in np.arange(d[0, 0], d[-1, 0] + 0.1, 5.0):
        zt = np.interp(s, d[:, 0], d[:, 1]); w = np.interp(s, d[:, 0], d[:, 2])
        zb = float(RC.body_params(s)[1]) - 2.0
        rings.append(half_super(s, zb, zt, w, 2.6, k))
    return lib.loft(np.array(rings), cap0=True, cap1=True)


def build_pylon(ctx):
    d = np.array(RC.PYLON)
    fle, fte, ft = (lib.pchip(d[:, 0], d[:, k]) for k in (1, 2, 3))
    k = ctx.n(28, 16); rings = []
    for z in np.arange(d[0, 0], d[-1, 0] + 0.01, ctx.n(1.5, 3.0)):
        lp = airfoil_loop(float(fle(z)), float(fte(z)), float(ft(z)), k)
        rings.append(np.stack([lp[:, 0], lp[:, 1], np.full(len(lp), z)], 1))
    return lib.loft(np.array(rings), cap0=True, cap1=True)


def build_stabilator(ctx):
    d = np.array(RC.STAB); k = ctx.n(24, 14)
    bls = np.r_[-d[::-1, 0][:-1], d[:, 0]]
    rings = []
    for bl in np.r_[np.linspace(-86, -83, 4), np.linspace(-82, 82, ctx.n(42, 22)), np.linspace(83, 86, 4)]:
        a = abs(bl); le = np.interp(a, d[:, 0], d[:, 1]); te = np.interp(a, d[:, 0], d[:, 2])
        t = 0.06 * (te - le) * (1.0 if a < 83 else max(0.25, math.sqrt(max(0.0, 1 - ((a - 83) / 3.2) ** 2))))
        lp = airfoil_loop(le, te, t, k)
        rings.append(np.stack([lp[:, 0], np.full(len(lp), bl), RC.WL_STAB + lp[:, 1]], 1))
    return lib.loft(np.array(rings), cap0=True, cap1=True, flip=True)


def nacelle_ring(s, c_bl, c_wl, hw, hh, n, k, sign):
    a = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    x = hw * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / n); z = hh * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** (2 / n)
    p = lib.resample(np.stack([x, z], 1), k, closed=True)
    return np.stack([np.full(k, s), sign * (c_bl + p[:, 0]), c_wl + p[:, 1]], 1)


# engine nacelle [F6-1]: STA -> (centre BL, centre WL, half width, half height, exponent)
NACELLE = [
    (338.0, 35.5, 279.5, 8.6, 9.2, 2.0), (339.2, 35.5, 279.5, 10.2, 10.8, 2.0), (342.0, 35.3, 279.4, 11.6, 12.2, 2.1),
    (351.0, 34.8, 279.2, 12.6, 13.2, 2.6), (366.0, 34.5, 279.0, 12.8, 13.3, 3.0), (398.0, 34.5, 279.0, 12.8, 13.3, 3.0),
    (410.0, 34.8, 279.0, 12.8, 13.0, 2.8), (430.0, 35.2, 278.5, 12.2, 12.2, 2.4), (446.0, 35.0, 277.8, 10.0, 9.8, 2.1),
    (453.0, 34.5, 277.5, 6.5, 6.4, 2.0), (455.5, 34.2, 277.4, 2.0, 2.0, 2.0),
]


def build_nacelle(ctx, sign):
    d = np.array(NACELLE); f = [lib.pchip(d[:, 0], d[:, k]) for k in range(1, 6)]
    k = ctx.n(56, 32); rings = []
    st = np.unique(np.r_[np.linspace(338, 351, 9), np.arange(351, 440, ctx.n(2.5, 5.0)), np.linspace(440, 455.5, 10)])
    for s in st:
        rings.append(nacelle_ring(s, *(float(g(s)) for g in f), k, sign))
    return lib.loft(np.array(rings), cap0=False, cap1=True, flip=(sign < 0))


def rounded(poly, r, grow=0.0):
    """Round a polygon's corners with radius r and offset it by grow (shapely buffers)."""
    from shapely.geometry import Polygon
    p = Polygon(poly)
    if r > 0: p = p.buffer(-r, quad_segs=6).buffer(r, quad_segs=6)
    if grow: p = p.buffer(grow, quad_segs=6)
    c = np.array(p.exterior.coords)[:-1]
    if p.exterior.is_ccw is False: c = c[::-1]
    return c


def side_cutter(poly, bl0=6.0, bl1=62.0, sides=(1, -1)):
    m = Mesh()
    for sg in sides:
        m.merge(lib.prism(poly, bl0, bl1, lib.plane_basis('side_l' if sg > 0 else 'side_r')))
    return m


def front_cutter(poly, sta, sides=(1, -1)):
    m = Mesh()
    for sg in sides:
        M = lib.plane_basis('front') @ S(sg, 1, 1)
        m.merge(lib.prism(poly, sta[0], sta[1]), M)
    return m


def top_cutter(poly, wl, sides=(1, -1)):
    m = Mesh()
    for sg in sides:
        m.merge(lib.prism(poly, wl[0], wl[1]), S(1, sg, 1))
    return m


def cutobj(mesh, name='cut'):
    o = lib.obj(name, mesh); lib.shade(o, 30); return o


def offset_shell(src, name, offset_in, thick_in):
    """A thin shell parallel to the body skin: displaced along the normals, then given thickness inward."""
    o = lib.copy(src, name)
    d = o.modifiers.new('d', 'DISPLACE'); d.strength = offset_in * lib.IN; d.mid_level = 0.0; lib.apply_mod(o, d)
    lib.solidify(o, thick_in)
    return o


def build_shell(ctx):
    """Body shell with every opening cut, plus glazing, gaskets and the four doors."""
    RCn = RC
    skin = lib.obj('body_skin', build_body(ctx)); lib.shade(skin, 60)
    glass_src = offset_shell(skin, 'glass_src', -0.7, 0.22)
    gasket_src = offset_shell(skin, 'gasket_src', 0.12, 0.9)
    shell = lib.copy(skin, 'body_shell'); lib.solidify(shell, RC.SHELL_T)
    door_src = lib.copy(skin, 'door_src'); lib.solidify(door_src, 2.2)
    import bpy
    bpy.data.objects.remove(skin, do_unlink=True)
    glass_parts = []; gasket_parts = []

    def glazing(cut_fn, poly, r, **kw):
        g = lib.copy(glass_src, 'glass'); lib.boolean(g, cutobj(cut_fn(rounded(poly, r, 0.5), **kw)), 'INTERSECT')
        glass_parts.append(g)
        k = lib.copy(gasket_src, 'gasket'); lib.boolean(k, cutobj(cut_fn(rounded(poly, r, 1.0), **kw)), 'INTERSECT')
        lib.boolean(k, cutobj(cut_fn(rounded(poly, r, -0.35), **kw)), 'DIFFERENCE')
        gasket_parts.append(k)

    # ---- doors first, from the uncut shell
    doors = {}
    for sg, side in ((1, 'L'), (-1, 'R')):
        d = lib.copy(door_src, f'cabin_door_{side}')
        lib.boolean(d, cutobj(side_cutter(rounded(RC.CABIN_DOOR['poly'], RC.CABIN_DOOR['r'], -0.3), sides=(sg,))), 'INTERSECT')
        cd = lib.copy(shell, f'cockpit_door_{side}')
        lib.boolean(cd, cutobj(side_cutter(rounded(RC.COCKPIT_DOOR['poly'], RC.COCKPIT_DOOR['r'], -0.25), sides=(sg,))), 'INTERSECT')
        doors[side] = [d, cd]
    # door windows (glass + gasket travel with the door)
    door_glass = {}
    for sg, side in ((1, 'L'), (-1, 'R')):
        d, cd = doors[side]; gl = []; gk = []
        for wdef, target in [(w, d) for w in RC.DOOR_WINDOWS] + [(RC.COCKPIT_DOOR_WIN, cd)]:
            p, r = wdef['poly'], wdef['r']
            g = lib.copy(glass_src, 'g'); lib.boolean(g, cutobj(side_cutter(rounded(p, r, 0.5), sides=(sg,))), 'INTERSECT')
            k = lib.copy(gasket_src, 'k'); lib.boolean(k, cutobj(side_cutter(rounded(p, r, 1.0), sides=(sg,))), 'INTERSECT')
            lib.boolean(k, cutobj(side_cutter(rounded(p, r, -0.35), sides=(sg,))), 'DIFFERENCE')
            lib.boolean(target, cutobj(side_cutter(rounded(p, r), sides=(sg,))), 'DIFFERENCE')
            (gl if target is d else gk).append((g, k))
        door_glass[side] = (gl, gk)
    # ---- cut the shell
    for spec in (RC.CABIN_DOOR, RC.COCKPIT_DOOR):
        lib.boolean(shell, cutobj(side_cutter(rounded(spec['poly'], spec['r']))), 'DIFFERENCE')
    for spec in (RC.GUNNER_WIN, RC.CHIN_WIN):
        glazing(side_cutter, spec['poly'], spec['r'])
        lib.boolean(shell, cutobj(side_cutter(rounded(spec['poly'], spec['r']))), 'DIFFERENCE')
    glazing(front_cutter, RC.WINDSHIELD['poly'], RC.WINDSHIELD['r'], sta=RC.WINDSHIELD['sta'])
    lib.boolean(shell, cutobj(front_cutter(rounded(RC.WINDSHIELD['poly'], RC.WINDSHIELD['r']), RC.WINDSHIELD['sta'])), 'DIFFERENCE')
    glazing(front_cutter, RC.WINDSHIELD_CTR['poly'], RC.WINDSHIELD_CTR['r'], sta=RC.WINDSHIELD_CTR['sta'], sides=(1,))
    lib.boolean(shell, cutobj(front_cutter(rounded(RC.WINDSHIELD_CTR['poly'], RC.WINDSHIELD_CTR['r']), RC.WINDSHIELD_CTR['sta'], sides=(1,))), 'DIFFERENCE')
    glazing(top_cutter, RC.EYEBROW_WIN['poly'], RC.EYEBROW_WIN['r'], wl=RC.EYEBROW_WIN['wl'])
    lib.boolean(shell, cutobj(top_cutter(rounded(RC.EYEBROW_WIN['poly'], RC.EYEBROW_WIN['r']), RC.EYEBROW_WIN['wl'])), 'DIFFERENCE')
    for o in (glass_src, gasket_src, door_src):
        bpy.data.objects.remove(o, do_unlink=True)
    ctx.part('airframe', 'body_shell', shell, 'paint_od', 50)
    for g in glass_parts: ctx.part('airframe', 'glazing', g, 'glass', 50)
    for k in gasket_parts: ctx.part('airframe', 'window_seal', k, 'rubber', 50)
    # ---- door nodes
    for sg, side in ((1, 'L'), (-1, 'R')):
        d, cd = doors[side]; gl, gk = door_glass[side]
        n = ctx.node(f'cabin_door_{side}', 'airframe', pivot=(342.0, sg * 46.5, 234.0))
        ctx.part(n, 'cabin_door_panel', d, 'paint_od', 50)
        for g, k in gl:
            ctx.part(n, 'cabin_door_glass', g, 'glass', 50); ctx.part(n, 'cabin_door_seal', k, 'rubber', 50)
        ctx.clip(n, f'cabin_door_{side}_open', [(1, (0, 0, 0), None), (8, (2.0, sg * 3.2, 0), None), (40, (66.0, sg * 3.6, 0), None)])
        # cockpit door: hinged on its forward edge, swings outboard
        n = ctx.node(f'cockpit_door_{side}', 'airframe', pivot=(207.8, sg * float(RC.body_surface_bl(207.8, 236.0)), 220.0))
        ctx.part(n, 'cockpit_door_panel', cd, 'paint_od', 50)
        for g, k in gk:
            ctx.part(n, 'cockpit_door_glass', g, 'glass', 50); ctx.part(n, 'cockpit_door_seal', k, 'rubber', 50)
        ctx.clip(n, f'cockpit_door_{side}_open', [(1, None, ('z', 0.0)), (40, None, ('z', -sg * 78.0))])


def engine_ends(ctx, sign):
    """Inlet lip, duct and bullet at the front of a nacelle; exhaust ejector at the back."""
    od, dark, stl = Mesh(), Mesh(), Mesh(); n = ctx.n(36, 18)
    c0 = np.array((338.0, sign * 35.5, 279.5)); M, _ = lib.frame_to(c0, c0 + np.array((1.0, 0, 0)))
    od.merge(lib.revolve([(8.4, 0.25), (8.9, -0.9), (8.5, -1.9), (7.5, -2.2), (6.9, -1.4), (6.6, 0.5)], n, M, cap0=False, cap1=False))
    dark.merge(lib.revolve([(6.7, 0.3), (6.3, 4.0), (5.6, 9.0), (0, 9.0)], n, M, cap0=False, cap1=False))
    stl.merge(lib.revolve([(0.0, -0.6), (1.2, 0.2), (2.6, 2.6), (3.3, 6.0), (3.4, 9.0)], n, M, cap0=False, cap1=False))
    for i in range(12):                                   # inlet struts / swirl vanes
        a = 2 * math.pi * i / 12
        stl.merge(lib.box((4.9, 0, 6.5), (3.4, 0.16, 3.0)), M @ R('wl', math.degrees(a)) @ R('sta', 18))
    # exhaust ejector: an oval duct turned outboard and aft, standing proud of the cowl
    e0 = np.array((425.0, sign * 37.0, 278.5)); d = np.array((0.52, sign * 0.84, 0.12)); d /= np.linalg.norm(d)
    Me, _ = lib.frame_to(e0, e0 + d)
    Me = Me @ S(1.0, 1.0, 1.0)
    od.merge(lib.revolve([(11.2, 7.0), (11.4, 12.6), (11.0, 13.3), (10.4, 13.3)], n, Me, cap0=False, cap1=False))
    dark.merge(lib.revolve([(10.4, 13.3), (10.0, 6.0), (0, 5.0)], n, Me, cap0=False, cap1=False))
    return od, dark, stl


def equipment(ctx):
    """Exterior equipment named on the general arrangement [F2-1] and antenna figure: positions read off [F6-1]."""
    od, blk, stl, al = Mesh(), Mesh(), Mesh(), Mesh(); n = ctx.n(20, 10)
    # tail rotor gearbox fairing on top of the pylon and the intermediate gearbox fairing at its base
    od.merge(lib.revolve([(0, -1), (0.55, -0.82), (0.86, -0.5), (1, 0), (0.86, 0.5), (0.55, 0.82), (0, 1)], ctx.n(28, 14)),
             T(731.5, -2.5, 320.0) @ S(17.0, 6.6, 12.0))
    od.merge(lib.revolve([(0, -1), (0.55, -0.82), (0.86, -0.5), (1, 0), (0.86, 0.5), (0.55, 0.82), (0, 1)], ctx.n(24, 12)),
             T(652.0, 0, 244.5) @ S(11.0, 9.0, 6.5))
    # pitot tubes above the cockpit doors (two), and the pylon-mounted upper anti-collision light
    for sg in (1, -1):
        b = np.array((252.0, sg * 24.0, 270.5))
        od.merge(lib.tube([b, b + (-0.5, 0, 3.6), b + (-2.2, 0, 4.9), b + (-9.0, 0, 5.0)], [0.9, 0.8, 0.6, 0.45], 10))
        stl.merge(lib.cyl(b + (-9.0, 0, 5.0), b + (-11.0, 0, 5.0), 0.3, 8))
    # upper cabin door tracks and the lower sill step rail
    for sg in (1, -1):
        for wl, s0, s1, h in ((262.6, 300.0, 444.0, 1.5), (207.0, 300.0, 444.0, 1.2)):
            pts = [(s, sg * (float(RC.body_surface_bl(s, wl)) + 0.9), wl) for s in np.linspace(s0, s1, 16)]
            al.merge(lib.tube(pts, h * 0.5, 6))
    # antennas: blade antennas on the belly and tailcone, towel-bar ADF sense on the tailcone sides, whip base
    for s, wl, up in ((300.0, 200.0, -1), (452.0, 201.4, -1), (590.0, 208.0, -1), (560.0, 247.7, 1)):
        prof = [(s - 4.5, 0), (s + 5.0, 0), (s + 3.6, up * 8.5), (s - 0.6, up * 8.5)]
        m = lib.prism(np.array([(p[0], p[1]) for p in prof]) if up > 0 else np.array([(p[0], p[1]) for p in prof])[::-1], -0.35, 0.35, lib.plane_basis('side_l') @ T(0, wl, 0))
        blk.merge(m)
    # anti-collision lights (upper on the pylon top fairing, lower under the cabin) and tail position light
    red, wht = Mesh(), Mesh()
    red.merge(lib.revolve([(1.9, 0), (1.9, 1.6), (1.4, 2.6), (0, 3.0)], n), T(741.0, -2.5, 331.5))
    red.merge(lib.revolve([(1.9, 0), (1.9, 1.6), (1.4, 2.6), (0, 3.0)], n), T(352.0, 0, 199.9) @ S(1, 1, -1))
    wht.merge(lib.revolve([(1.1, 0), (0.9, 1.2), (0, 1.5)], 10), lib.frame_to((759.0, -2.5, 318.0), (761.0, -2.5, 318.0))[0])
    # windshield wipers
    for sg in (1, -1):
        base = np.array((193.5, sg * 22.0, float(RC.body_params(193.5)[1]) + 0.3))
        tip = np.array((211.0, sg * 13.0, 262.0))
        blk.merge(lib.cyl(base, tip, 0.28, 6)); blk.merge(lib.box((base + tip) / 2 + (0.3, sg * -1.6, 0.8), (0.5, 0.5, 15.0), lib.frame_to(base, tip)[0] @ T(0, 0, 0) ) if False else lib.cyl(base + (tip - base) * 0.45 + (-0.3, 0, 0.3), tip + (-0.3, 0, 0.3), 0.36, 6))
        stl.merge(lib.revolve([(1.0, 0), (1.0, 0.8), (0, 0.8)], 10), T(*base))
    # APU exhaust on the left, oil-cooler exhaust grille on top of the deck, engine work platforms
    od.merge(lib.revolve([(5.6, 0), (5.6, 1.4), (5.0, 1.4)], n, lib.frame_to((470.0, 24.5, 265.5), (470.0, 26.5, 266.5))[0] @ S(1.0, 0.62, 1), cap0=False, cap1=False))
    drk = Mesh(); drk.merge(lib.revolve([(5.0, 1.4), (4.6, -3.0), (0, -3.0)], n, lib.frame_to((470.0, 24.5, 265.5), (470.0, 26.5, 266.5))[0] @ S(1.0, 0.62, 1), cap0=False, cap1=False))
    od.merge(lib.prism(lib.rrect(13.0, 14.0, 2.5), 291.5, 297.5, T(398.0, 0, 0)))
    for i in range(7):
        blk.merge(lib.box((392.8 + i * 1.75, 0, 298.0), (0.5, 11.0, 1.4)))
    # door handles (cabin doors and cockpit doors) are added with their doors in hardware.py
    for name, m, mat in (('fairings', od, 'paint_od'), ('antennas_wipers', blk, 'paint_black'), ('equipment_steel', stl, 'steel'),
                         ('door_tracks', al, 'aluminium'), ('anticollision_lenses', red, 'lens_red'), ('tail_light', wht, 'glass_lens'),
                         ('apu_exhaust', drk, 'exhaust_dark')):
        ctx.part('airframe', name, m, mat, 40)


def build(ctx):
    build_shell(ctx)
    ctx.part('airframe', 'upper_deck', build_deck(ctx), 'paint_od', 50)
    ctx.part('airframe', 'tail_shaft_cover', build_shaft_cover(ctx), 'paint_od', 50)
    ctx.part('airframe', 'tail_pylon', build_pylon(ctx), 'paint_od', 50)
    ctx.node('stabilator', 'airframe', pivot=(712.0, 0.0, RC.WL_STAB))
    ctx.part('stabilator', 'stabilator_skin', build_stabilator(ctx), 'paint_od', 50)
    for sign, side in ((1, 'L'), (-1, 'R')):
        ctx.part('airframe', f'nacelle_{side}', build_nacelle(ctx, sign), 'paint_od', 50)
        od, dark, stl = engine_ends(ctx, sign)
        ctx.part('airframe', f'engine_ends_{side}', od, 'paint_od', 40)
        ctx.part('airframe', f'engine_ducts_{side}', dark, 'exhaust_dark', 40)
        ctx.part('airframe', f'engine_inlet_parts_{side}', stl, 'steel_dark', 40)
    equipment(ctx)
