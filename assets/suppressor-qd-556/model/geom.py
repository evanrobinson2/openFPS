"""Generic quick-detach 5.56 mm suppressor: the single source of every dimension.

Pure Python, no dependencies. Used by build.py (Blender: meshes, sockets, clips, renders) and by ../sim/sim.py
(chamber volumes, wall areas, apertures, masses).

    python3 geom.py        # prints the chambers and masses and writes inventory.json

Axis: s in millimetres along the bore, s = 0 at the rear face of the can, increasing down-range; r is the radius in mm.
The tip of the rifle's flash hider (the HK416 `socket_muzzle`) is at s = S_MOUNT, which is the asset's origin
(`socket_mount`). Every lathed part is a closed (s, r) polygon revolved about the bore.

Source tags
  [class]    a figure typical of fielded 5.56 mm QD cans (makers' published specifications: about 6 to 7 in long,
             1.5 in diameter, 14 to 21 oz). This is a generic can: no single product was measured or copied.
  [rifle]    taken from the HK416 recipe (assets/hk416/model/build.py: flash hider 42.9 mm long, 21.2 mm diameter,
             15.6 mm bore ahead of the threads; barrel crown 34.7 mm behind the hider tip)
  [inferred] my own engineering choice, not measured from anything
"""
import json, math, os

G = dict(
    length=174.0,          # [class] overall length, 6.85 in
    tube_od=38.1,          # [class] 1.5 in
    s_mount=52.0,          # [inferred] 52 mm of the can sits over the muzzle device; 122 mm is added ahead of it
    hider_len=42.9,        # [rifle]
    hider_r=10.6,          # [rifle]
    hider_bore_r=7.8,      # [rifle] inside radius ahead of the threaded part
    hider_thread_r=6.3,    # [rifle] inside radius of the first 12 mm
    hider_slot_cm3=1.03,   # [rifle] six slots 3.4 mm wide, 18 mm long, through a 2.8 mm wall: open volume
    crown_back=34.7,       # [rifle] barrel crown behind the hider tip
    jam_ring_r=9.7,        # [rifle] the jam ring and crush washer behind the hider: what the jaws close on
    tube_wall=1.5,         # [inferred]
    bore_r=3.6,            # [class] baffle and end-cap aperture radius: 7.2 mm for a 5.70 mm bullet
    n_baffles=6,           # [class]
    baffle_first=71.0,     # [inferred] apex of the blast baffle
    baffle_pitch=15.5,     # [inferred]
    cone_depth=11.0,       # [inferred] apex to rim: a 50 degree half angle (a "60 degree class" cone baffle)
    baffle_t=1.6,          # [inferred] wall of a baffle cone
    blast_baffle_t=2.4,    # [inferred] the blast baffle is thicker: it takes the uncorking jet
    skirt_t=1.0,           # [inferred] spacer skirt of each baffle
    clip_w_deg=50.0,       # [inferred] width of the clip (a scallop cut in the apex lip of baffles 2..6)
    clip_depth=2.0,        # [inferred] how far the clip opens the lip, mm
    cap_t=4.5,             # [inferred] end cap thickness
    collar_flutes=14,      # [inferred]
    cap_notches=6,         # [inferred]
    jaws=3,                # [inferred] locking jaws under the collar
    jaw_travel=1.3,        # [inferred] radial travel of a jaw between open and locked, mm
    collar_turn_deg=60.0,  # [inferred] collar rotation between open and locked
    rho_tube=7800.0,       # 17-4 PH stainless steel (tube, mount, collar, jaws, cap): handbook density
    rho_baffle=8190.0,     # Inconel 718 (blast sleeve and baffles): handbook density
    cp_steel=500.0,        # J/kg/K near 400 C, handbook order (460 at 20 C rising to 560 at 600 C)
    cp_inconel=480.0,      # J/kg/K near 400 C, handbook order (435 at 20 C rising to 560 at 600 C)
)
S_MOUNT = G['s_mount']
R_OUT = G['tube_od'] / 2                 # 19.05
R_IN = R_OUT - G['tube_wall']            # 17.55
R_SK = R_IN - G['skirt_t']               # 16.55
RB = G['bore_r']
L = G['length']
S_CROWN = S_MOUNT - G['crown_back']      # 17.3
S_HIDER0 = S_MOUNT - G['hider_len']      # 9.1
S_CAP_IN = L - G['cap_t']                # 169.5: inner face of the end cap
S_SPIGOT = 165.0                         # rear of the end-cap spigot
S_BODY_F = 30.0                          # front shoulder of the mount body at the wall
S_BODY_N = 35.0                          # nose of the mount body at the bore
R_SEAT = 11.0                            # bore of the mount body over the hider (0.4 mm clearance)
R_LIP = 11.6                             # bore of the collar's rear lip (passes over the hider)
R_POCKET = 14.3                          # bore of the collar's jaw pocket (the cam surface, drawn at its open radius)


def baffle_apex(i): return G['baffle_first'] + i * G['baffle_pitch']


def cone_s(i, r):
    """Axial position of baffle i's rear (upstream) cone surface at radius r."""
    return baffle_apex(i) + G['cone_depth'] * (r - RB - 1.0) / (R_IN - RB - 1.0)


def baffle_name(i): return 'blast_baffle' if i == 0 else 'baffle_%d' % (i + 1)


def baffle_poly(i):
    a, d = baffle_apex(i), G['cone_depth']
    t = G['blast_baffle_t'] if i == 0 else G['baffle_t']
    phi = math.atan2(R_IN - RB - 1.0, d)
    ta = t / math.sin(phi)                                   # axial thickness of the cone wall
    slope = d / (R_IN - RB - 1.0)
    end = baffle_apex(i + 1) + d if i < G['n_baffles'] - 1 else S_SPIGOT
    return [(a, RB), (a, RB + 1.0), (a + d, R_IN), (end, R_IN), (end, R_SK),
            (a + ta + slope * (R_SK - RB - 1.0), R_SK), (a + ta - slope * 1.0, RB)]


def parts():
    """name -> dict(poly, mat, rho, cp, role, group). Lathed parts only, rear to front."""
    P = {}
    st = dict(rho=G['rho_tube'], cp=G['cp_steel']); inc = dict(rho=G['rho_baffle'], cp=G['cp_inconel'])
    P['lock_collar'] = dict(mat='CanCollar', group='lock', role='locking collar: a 60 degree turn cams the three jaws shut behind the flash hider', **st,
        poly=[(0, R_LIP), (0, 17.2), (1.2, 18.4), (14.6, 18.4), (15.6, 17.6), (15.6, 16.3), (9.0, 16.3), (9.0, R_POCKET), (1.5, R_POCKET), (1.5, R_LIP)])
    P['mount_body'] = dict(mat='CanBody', group='body', role='mount: seats over the flash hider and closes the rear of the blast chamber', **st,
        poly=[(9.2, R_SEAT), (9.2, 16.1), (16, 16.1), (16, R_IN), (S_BODY_F, R_IN), (S_BODY_N, 12.2), (S_BODY_N, R_SEAT)])
    P['tube'] = dict(mat='CanBody', group='body', role='outer tube', **st,
        poly=[(16, R_IN), (16, 18.3), (17.5, R_OUT), (62.0, R_OUT), (62.0, R_OUT - 0.25), (63.2, R_OUT - 0.25), (63.2, R_OUT),
              (171, R_OUT), (171, R_IN)])
    P['blast_sleeve'] = dict(mat='Baffle', group='body', role='liner of the blast chamber', **inc,
        poly=[(S_BODY_F, R_SK), (S_BODY_F, R_IN), (baffle_apex(0) + G['cone_depth'], R_IN), (baffle_apex(0) + G['cone_depth'], R_SK)])
    for i in range(G['n_baffles']):
        P[baffle_name(i)] = dict(mat='Baffle', group='body', **inc,
            role='blast baffle: the first and thickest cone, no clip' if i == 0 else
                 'cone baffle %d of %d with its spacer skirt; clip at %d degrees' % (i + 1, G['n_baffles'], clip_angle_deg(i)),
            poly=baffle_poly(i))
    P['end_cap'] = dict(mat='CanBody', group='body', role='end cap with the exit aperture and six spanner notches', **st,
        poly=[(S_SPIGOT, 15.6), (S_SPIGOT, R_IN), (171, R_IN), (171, R_OUT), (L - 0.8, R_OUT), (L, R_OUT - 0.8), (L, 16.2), (L, 12.0), (L, 9.0),
              (L - 1.5, 7.5), (L - 1.5, RB), (S_CAP_IN, RB), (S_CAP_IN, 15.6)])
    return P


def clip_angle_deg(i):
    """Clips alternate top and bottom down the stack so the cross-flow they set up reverses at each baffle."""
    return 90 if i % 2 == 1 else 270


def jaw():
    """One locking jaw: an arc segment (s0, s1, r_in locked, r_out, arc degrees). Open = r + jaw_travel."""
    return dict(s0=2.0, s1=8.6, r_in=G['jam_ring_r'] + 0.15, r_out=12.9, arc_deg=96.0, rho=G['rho_tube'], cp=G['cp_steel'],
                mat='CanCollar', role='locking jaw: closes on the jam ring behind the flash hider, so the hider cannot pull out')


def panels():
    """Plain placeholder panels where a maker's marks would be. No names, no logos."""
    return dict(
        marking_panel=dict(s0=82.0, s1=132.0, th_deg=118.0, arc_deg=40.0, role='plain placeholder panel (no maker, model or serial marks)'),
        index_panel=dict(s0=20.0, s1=30.0, th_deg=90.0, arc_deg=10.0, role='plain index mark: lines up with the collar mark when locked'),
        collar_index=dict(s0=3.0, s1=13.0, th_deg=90.0, arc_deg=8.0, role='plain index mark on the collar', on='lock_collar'),
    )


# ---- non-axisymmetric detail: displacement of a profile vertex as a function of angle
def detail(name, s, r, th):
    if name == 'lock_collar' and r > 18.0:                           # scalloped grip flutes
        n = G['collar_flutes']; u = (th * n / (2 * math.pi)) % 1.0
        return s, r - 0.9 * max(0.0, math.cos(2 * math.pi * (u - 0.5))) ** 2
    if name == 'end_cap' and abs(s - L) < 1e-6 and 11.9 < r < 16.3:  # spanner notches in the front face
        n = G['cap_notches']; u = (th * n / (2 * math.pi)) % 1.0
        return (s - 1.4, r) if u < 0.22 else (s, r)
    if name.startswith('baffle_') and r <= RB + 1.0 + 1e-6:          # the clip: a scallop in the apex lip
        i = int(name.split('_')[1]) - 1
        d = (math.degrees(th) - clip_angle_deg(i) + 180.0) % 360.0 - 180.0
        w = G['clip_w_deg'] / 2
        if abs(d) < w: return s, r + G['clip_depth'] * math.cos(math.pi / 2 * d / w) ** 2
    return s, r


def clip_area_mm2():
    """Extra open area a clip adds to a baffle aperture (the scallop, integrated over its width)."""
    w = math.radians(G['clip_w_deg']); n = 400; acc = 0.0
    for k in range(n):
        d = (k + 0.5) / n * w - w / 2; dr = G['clip_depth'] * math.cos(math.pi / 2 * d / (w / 2)) ** 2
        acc += 0.5 * ((RB + dr) ** 2 - RB ** 2) * (w / n)
    return acc


# ---- measures
def poly_volume_mm3(poly):
    """Volume of the solid of revolution of a closed (s, r) polygon, mm^3."""
    acc = 0.0
    for (s0, r0), (s1, r1) in zip(poly, poly[1:] + poly[:1]):
        acc += (s0 * r1 - s1 * r0) * (r0 + r1)
    return abs(acc) * math.pi / 3.0


def point_in_poly(s, r, poly):
    inside = False
    for (s0, r0), (s1, r1) in zip(poly, poly[1:] + poly[:1]):
        if (r0 > r) != (r1 > r) and s < s0 + (r - r0) * (s1 - s0) / (r1 - r0): inside = not inside
    return inside


def hider_poly():
    return [(S_HIDER0, G['hider_thread_r']), (S_HIDER0, G['hider_r']), (S_MOUNT, G['hider_r']), (S_MOUNT, G['hider_bore_r']),
            (S_HIDER0 + 13.0, G['hider_bore_r']), (S_HIDER0 + 12.0, G['hider_thread_r'])]


def solid_at(s, r, P=None):
    P = P or parts()
    for nm, p in P.items():
        if point_in_poly(s, r, p['poly']): return nm
    if point_in_poly(s, r, hider_poly()): return 'rifle_flash_hider'
    if s < S_CROWN and r < G['hider_thread_r']: return 'rifle_barrel'
    return None


def chamber_at(s, r, P=None):
    """Index of the gas chamber holding point (s, r): 0 = blast chamber, i = the space ahead of baffle i, or None."""
    if r >= R_IN or s <= S_CROWN or s >= S_CAP_IN: return None
    if s < S_BODY_N and r > G['hider_r'] and not (s >= S_BODY_F and r > R_SEAT): return None      # behind the mount body
    if solid_at(s, r, P): return None
    k = 0
    for i in range(G['n_baffles']):
        if s > cone_s(i, max(r, RB)) + 0.5: k = i + 1
    return k


def chamber_names():
    return ['blast chamber'] + ['ahead of %s' % baffle_name(i).replace('_', ' ') for i in range(G['n_baffles'])]


def chambers(ds=0.1):
    """Gas volume (m^3), wetted wall area (m^2) and aperture positions of every chamber."""
    P = parts(); n = G['n_baffles'] + 1
    vol = [0.0] * n; area = [0.0] * n
    ns, nr = int(L / ds), int(R_IN / ds)
    for i in range(ns):
        s = (i + 0.5) * ds
        for j in range(nr):
            r = (j + 0.5) * ds
            k = chamber_at(s, r, P)
            if k is not None: vol[k] += 2 * math.pi * r * ds * ds
    vol[0] += G['hider_slot_cm3'] * 1e3                                 # the hider is counted solid above; its slots are open
    polys = [p['poly'] for p in P.values()]
    polys.append(hider_poly())
    polys.append([(16, R_IN), (16, R_IN + 0.01), (171, R_IN + 0.01), (171, R_IN)])        # tube bore, where no skirt covers it
    for poly in polys:
        for (s0, r0), (s1, r1) in zip(poly, poly[1:] + poly[:1]):
            ln = math.hypot(s1 - s0, r1 - r0)
            if ln < 1e-9: continue
            nseg = max(1, int(ln / 0.5))
            for q in range(nseg):
                f = (q + 0.5) / nseg; sm, rm = s0 + (s1 - s0) * f, r0 + (r1 - r0) * f
                nx, ny = -(r1 - r0) / ln, (s1 - s0) / ln
                for sg in (1, -1):
                    k = chamber_at(sm + sg * 0.06 * nx, rm + sg * 0.06 * ny, P)
                    if k is not None: area[k] += 2 * math.pi * rm * ln / nseg; break
    ap = [baffle_apex(i) for i in range(G['n_baffles'])] + [S_CAP_IN]
    a0 = math.pi * RB * RB
    ap_area = [a0] + [a0 + clip_area_mm2()] * (G['n_baffles'] - 1) + [a0]
    lens = [baffle_apex(0) - S_MOUNT] + [G['baffle_pitch']] * (G['n_baffles'] - 1) + [S_CAP_IN - baffle_apex(G['n_baffles'] - 1)]
    return dict(names=chamber_names(), volume_m3=[v * 1e-9 for v in vol], wall_area_m2=[a * 1e-6 for a in area],
                aperture_s_mm=ap, aperture_from_crown_m=[(a - S_CROWN) * 1e-3 for a in ap],
                aperture_area_m2=[a * 1e-6 for a in ap_area], aperture_d_m=2 * RB * 1e-3,
                jet_run_m=[l * 1e-3 for l in lens], web_t_m=[G['blast_baffle_t'] * 1e-3] + [G['baffle_t'] * 1e-3] * (G['n_baffles'] - 1) + [G['cap_t'] * 1e-3])


def masses():
    """kg per part (jaws and panels included), and the heat capacity J/K."""
    P = parts(); out = {}; C = 0.0
    for nm, p in P.items():
        out[nm] = poly_volume_mm3(p['poly']) * 1e-9 * p['rho']; C += out[nm] * p['cp']
    j = jaw()
    mj = math.radians(j['arc_deg']) / 2 * (j['r_out'] ** 2 - j['r_in'] ** 2) * (j['s1'] - j['s0']) * 1e-9 * j['rho']
    for k in range(G['jaws']): out['jaw_%d' % (k + 1)] = mj; C += mj * j['cp']
    return out, C


def sockets():
    """Metres in the asset frame: +Z down-range, +Y up, +X to the shooter's left, origin at socket_mount."""
    return dict(
        socket_mount=dict(pos=[0.0, 0.0, 0.0], note='mates to the rifle\'s socket_muzzle (the tip of the flash hider) with an identity transform'),
        socket_exit=dict(pos=[0.0, 0.0, round((L - S_MOUNT) * 1e-3, 5)], note='centre of the end-cap aperture: the new muzzle for flash, smoke, sound and the bullet'),
        socket_thermal=dict(pos=[0.0, round(R_OUT * 1e-3, 5), round((baffle_apex(0) - S_MOUNT) * 1e-3, 5)], note='top of the tube over the blast baffle: the hottest skin, for glow and mirage'),
    )


def hierarchy():
    return dict(suppressor=dict(children=['can_body', 'lock_collar', 'jaw_1', 'jaw_2', 'jaw_3', 'socket_mount', 'socket_exit', 'socket_thermal'],
                                note='root; parent it to the rifle\'s socket_muzzle. The qd clips move it along the bore.'),
                can_body=dict(children=['mount_body', 'tube', 'blast_sleeve'] + [baffle_name(i) for i in range(G['n_baffles'])] + ['end_cap', 'marking_panel', 'index_panel'],
                              note='everything rigid with the tube'),
                lock_collar=dict(children=['collar_index'], note='turns about the bore: 0 degrees locked, %g degrees open' % G['collar_turn_deg']),
                jaws=dict(note='jaw_1..3 slide radially %.1f mm: in = locked on the jam ring, out = clear of the flash hider' % G['jaw_travel']))


def clips():
    """Keys at 24 fps. slide_mm: how far down-range of its seated position the can is (0 = seated)."""
    t = G['collar_turn_deg']; j = G['jaw_travel']
    att = dict(fps=24, frames=[1, 36], seconds=1.5,
               suppressor_slide_mm=[(1, 75.0), (16, 6.0), (20, 0.0), (36, 0.0)],
               suppressor_roll_deg=[(1, -25.0), (16, 0.0), (36, 0.0)],
               lock_collar_turn_deg=[(1, t), (22, t), (31, 0.0), (36, 0.0)],
               jaw_out_mm=[(1, j), (22, j), (31, 0.0), (36, 0.0)],
               note='the open can is slid back over the flash hider until the mount seats on the hider shoulder, then the collar is turned %g degrees: its cam drives the three jaws in behind the hider' % t)
    det = dict(fps=24, frames=[1, 36], seconds=1.5,
               suppressor_slide_mm=[(1, 0.0), (15, 0.0), (19, 6.0), (36, 75.0)],
               suppressor_roll_deg=[(1, 0.0), (19, 0.0), (36, 25.0)],
               lock_collar_turn_deg=[(1, 0.0), (4, 0.0), (13, t), (36, t)],
               jaw_out_mm=[(1, 0.0), (4, 0.0), (13, j), (36, j)],
               note='the reverse: collar turned open, jaws out, can drawn forward off the hider')
    return dict(qd_attach=att, qd_detach=det)


def fit_checks():
    """Clearances of the mount on the HK416 muzzle device and of the bullet through the stack, mm."""
    j = jaw(); t = G['jaw_travel']
    c = dict(
        mount_bore_over_hider=round(R_SEAT - G['hider_r'], 3),
        jaw_locked_behind_hider=round(G['hider_r'] - j['r_in'], 3),        # > 0: the hider cannot pull out through the closed jaws
        jaw_locked_on_jam_ring=round(j['r_in'] - G['jam_ring_r'], 3),      # >= 0: closed jaws do not cut into the jam ring
        jaw_open_over_hider=round(j['r_in'] + t - G['hider_r'], 3),        # > 0: open jaws pass over the hider
        jaw_inside_collar=round(R_POCKET - (j['r_out'] + t), 3),           # > 0: open jaws fit inside the collar's pocket
        collar_lip_over_hider=round(R_LIP - G['hider_r'], 3),
        jaw_behind_hider_rear=round(S_HIDER0 - j['s1'], 3),                # > 0: the jaws sit behind the hider's rear face
        bullet_in_aperture_radial=round(RB - 2.85, 3),
        hider_tip_to_blast_baffle=round(baffle_apex(0) - S_MOUNT, 3),
        collar_to_tube_gap=round(16.0 - 15.6, 3))
    c['passed'] = all(v > 0 for k, v in c.items() if k != 'jaw_locked_on_jam_ring') and c['jaw_locked_on_jam_ring'] >= 0
    return c


def inventory():
    ch = chambers(); m, C = masses(); P = parts()
    inv = dict(
        asset='suppressor-qd-556', credit='carpetshark',
        frame='metres, +Z down-range, +Y up, +X to the shooter\'s left; origin at socket_mount (the rifle\'s socket_muzzle). s = z*1000 + %g mm is the recipe\'s axis' % S_MOUNT,
        dimensions_mm={k: v for k, v in G.items()},
        length_mm=L, diameter_mm=G['tube_od'], added_length_mm=L - S_MOUNT, mass_kg=round(sum(m.values()), 4), heat_capacity_J_per_K=round(C, 1),
        parts=[dict(name=nm, material=p['mat'], group=p['group'], role=p['role'], mass_g=round(m[nm] * 1e3, 1)) for nm, p in P.items()]
              + [dict(name='jaw_%d' % (k + 1), material='CanCollar', group='lock', role=jaw()['role'], mass_g=round(m['jaw_%d' % (k + 1)] * 1e3, 1)) for k in range(G['jaws'])]
              + [dict(name=nm, material='Panel', group='lock' if p.get('on') else 'body', role=p['role'], mass_g=0.0) for nm, p in panels().items()],
        chambers=[dict(name=ch['names'][k], volume_cm3=round(ch['volume_m3'][k] * 1e6, 2), wall_cm2=round(ch['wall_area_m2'][k] * 1e4, 1),
                       exit_aperture_mm2=round(ch['aperture_area_m2'][k] * 1e6, 2), exit_aperture_s_mm=ch['aperture_s_mm'][k]) for k in range(len(ch['names']))],
        gas_volume_cm3=round(sum(ch['volume_m3']) * 1e6, 1), wall_area_cm2=round(sum(ch['wall_area_m2']) * 1e4, 0),
        sockets=sockets(), hierarchy=hierarchy(), clips=clips(), fit_checks_mm=fit_checks())
    return inv


if __name__ == '__main__':
    inv = inventory()
    for c in inv['chambers']: print('%-24s %6.2f cm3  %6.1f cm2  aperture %5.1f mm2' % (c['name'], c['volume_cm3'], c['wall_cm2'], c['exit_aperture_mm2']))
    print('total gas volume %.1f cm3, wall %.0f cm2' % (inv['gas_volume_cm3'], inv['wall_area_cm2']))
    for p in inv['parts']: print('%-14s %6.1f g' % (p['name'], p['mass_g']))
    print('fit', inv['fit_checks_mm'])
    print('mass %.0f g (%.1f oz), heat capacity %.0f J/K' % (inv['mass_kg'] * 1e3, inv['mass_kg'] / 0.0283495, inv['heat_capacity_J_per_K']))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.json'), 'w') as f: json.dump(inv, f, indent=1)
    print('wrote inventory.json')
