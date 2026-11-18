"""Fuselage: the layered armour plating, the substructure shell under it, every opening and its coaming, ring frames
and longerons, the pressure-hull lining, the decks and the bulkheads.

Openings are cut here and filled by the module that owns the door: cockpit (canopy), landing_gear (gear doors),
lift_chassis (belly plate), lander_bay (bay doors). layout() is the single place that says where they are.
"""
import math, random
import numpy as np
import spec, kit
from kit import MB, finish, empty
from structure import deck_slab, bulkhead

S = spec.ST
GUNMETAL = ['armour_gunmetal_a', 'armour_gunmetal_a', 'armour_gunmetal_b', 'armour_gunmetal_b', 'armour_gunmetal_c', 'armour_gunmetal_d']

def layout(H):
    """Tag every opening and recess on the hull grid. Returns nothing; read H.openings afterwards."""
    C = spec.CANOPY
    H.open('canopy', H.si(C['s0']), H.si(C['s1']), H.rows['brow'], H.rows['sill'], 0)
    ch = spec.CREW_HATCH; i0, i1 = H.si(ch['s0']), H.si(ch['s1']); im = (i0 + i1) // 2
    H.open('crew_hatch', i0, i1, H.row_z(im, ch['z1']), H.row_z(im, ch['z0']), ch['side'])
    # waist channel (tag 2) and the viewports in it
    W = spec.WAIST; i0, i1 = H.si(W['s0']), H.si(W['s1']); im = H.si(12.0)
    jw0, jw1 = H.row_z(im, W['z1']), H.row_z(im, W['z0'])
    H.open('waist', i0, i1, jw0, jw1, 0, tag=2)
    Pp = spec.PORTS
    jp0 = jw0 + 1 if jw1 - jw0 >= 3 else jw0; jp1 = jw1 - 1 if jw1 - jw0 >= 3 else jw1
    for k, s in enumerate(Pp['stations']):
        a, b = H.si(s - Pp['width'] / 2), H.si(s + Pp['width'] / 2)
        H.open(f'port_{k}', a, max(b, a + 1), jp0, max(jp1, jp0 + 1), 0)
    # equipment bays (tag 3)
    B = spec.BAYS; jb0, jb1 = H.row_z(im, B['z1']), H.row_z(im, B['z0'])
    pitch = (B['s1'] - B['s0']) / B['n']
    for k in range(B['n']):
        a = B['s0'] + k * pitch + 0.18; b = a + pitch - 0.36
        H.open(f'bay_{k}', H.si(a), H.si(b), jb0, jb1, 0, tag=3)
    # belly: lift, lander bay doors, gear doors
    Lf = spec.LIFT; i0, i1 = H.si(Lf['s0']), H.si(Lf['s1'])
    H.open('lift', i0, i1, H.row_y_belly(im, Lf['half_w']), H.nr, 0)
    Lb = spec.LANDER_BAY; i0, i1 = H.si(Lb['s0']), H.si(Lb['s1'])
    jl = H.row_y_belly(im, Lb['door_half'])
    H.open('lander_doors', i0, i1, jl, H.nr, 0)
    G = spec.GEAR
    for key in ('fwd', 'aft'):
        w0, w1 = G[key]['well']; y = G[key]['y']
        j0 = H.row_y_belly(im, y + 0.50); j1 = min(H.row_y_belly(im, y - 0.42), jl)
        H.open(f'gear_{key}', H.si(w0 - 0.1), H.si(w1 + 0.1), j0, max(j1, j0 + 2), 0)
    # paint and longeron lines
    H.j_split.update((H.rows['brow'], H.rows['sill'], H.row_z(im, 2.2), H.row_z(im, -2.1)))
    H.chin = (H.rows['sill'] + 3, H.rows['sill'] + 5)
    H.j_split.update(H.chin)

def _perimeter(G):
    ni, nj, _ = G.shape
    idx = [(a, 0) for a in range(ni)] + [(ni - 1, b) for b in range(1, nj)] + [(a, nj - 1) for a in range(ni - 2, -1, -1)] + [(0, b) for b in range(nj - 2, 0, -1)]
    return [G[a, b] for a, b in idx]

def _loop_band(mb, La, Lb, m, flip=False):
    ia = [mb.v(p) for p in La]; ib = [mb.v(p) for p in Lb]; n = len(La)
    for k in range(n):
        k2 = (k + 1) % n
        if np.linalg.norm(La[k] - La[k2]) < 1e-5 and np.linalg.norm(Lb[k] - Lb[k2]) < 1e-5:
            continue
        q = (ia[k], ib[k], ib[k2], ia[k2])
        mb.f(q[::-1] if flip else q, m)

def coaming(mb, bolts, H, rect, m='structure_steel', lip=0.07, width=0.11, o_in=None):
    """Raised frame around an opening, with a wall down through the hull thickness and a bolt at every node."""
    i0, i1, j0, j1, side = rect
    o_in = spec.OFF_LINING - 0.03 if o_in is None else o_in
    for sd in ((1, -1) if side == 0 else (side,)):
        fl = sd < 0
        A0 = _perimeter(H.nodes(i0, i1, j0, j1, lip, sd)); A1 = _perimeter(H.nodes(i0, i1, j0, j1, lip, sd, margin=-width))
        B1 = _perimeter(H.nodes(i0, i1, j0, j1, spec.OFF_BASE, sd, margin=-width)); B0 = _perimeter(H.nodes(i0, i1, j0, j1, o_in, sd))
        _loop_band(mb, A0, A1, m, flip=not fl)      # top of the lip (A1 is outside A0)
        _loop_band(mb, A1, B1, m, flip=not fl)      # outer wall
        _loop_band(mb, A0, B0, m, flip=fl)          # wall facing into the opening
        Mid = _perimeter(H.nodes(i0, i1, j0, j1, lip, sd, margin=-width * 0.5))
        Nn = _perimeter(H.N[i0:i1 + 1, j0:j1 + 1] * np.array([1, sd, 1]))
        for k in range(0, len(Mid)):
            bolts.bolt(tuple(Mid[k]), tuple(Nn[k]), r=0.018, h=0.012)

def _split(rng, i0, i1, j0, j1, H, out, max_len, max_rows):
    ls = H.st[i1] - H.st[i0]; nj = j1 - j0; ni = i1 - i0
    lim = rng.uniform(*max_len); rl = rng.randint(*max_rows)
    if ls > lim and ni >= 4:
        k = rng.randint(i0 + 2, i1 - 2)
        _split(rng, i0, k, j0, j1, H, out, max_len, max_rows); _split(rng, k, i1, j0, j1, H, out, max_len, max_rows); return
    if nj > rl and nj >= 4:
        k = rng.randint(j0 + 2, j1 - 2)
        _split(rng, i0, i1, j0, k, H, out, max_len, max_rows); _split(rng, i0, i1, k, j1, H, out, max_len, max_rows); return
    out.append((i0, i1, j0, j1))

def _plate(mb, bolts, H, r, side, off, h, m, bolt_every=2):
    i0, i1, j0, j1 = r; fl = side < 0
    A = H.nodes(i0, i1, j0, j1, off + h, side, margin=spec.PANEL_GAP)
    if np.linalg.norm(A[0, 0] - A[-1, -1]) < 0.12:
        return 0
    B = H.nodes(i0, i1, j0, j1, min(spec.OFF_BASE, off - 0.12) - 0.02, side, margin=spec.PANEL_GAP)
    H.sheet(mb, A, m, flip=fl); H.skirt(mb, A, B, m, flip=fl)
    if bolts is None:
        return 1
    Bn = H.nodes(i0, i1, j0, j1, off + h, side, margin=0.075)
    ni, nj, _ = Bn.shape
    if np.linalg.norm(Bn[0, 0] - Bn[0, -1]) < 0.22 or np.linalg.norm(Bn[0, 0] - Bn[-1, 0]) < 0.22:
        return 1
    for a in range(ni):
        for b in range(nj):
            edge = a in (0, ni - 1) or b in (0, nj - 1)
            corner = a in (0, ni - 1) and b in (0, nj - 1)
            if not edge or not (corner or (a + b) % bolt_every == 0):
                continue
            bolts.bolt(tuple(Bn[a, b]), H.nrm(i0 + a, j0 + b, side), r=0.016, h=0.010, washer=False)
    return 1

def build_plating(H, parent):
    rng = random.Random(27)
    frame_i = sorted(set(H.si(s) for s in np.arange(2.0, 28.5, 2.0)))
    s_lines = sorted(H.s_split | set(frame_i) | {0, H.ni - 1})
    j_lines = sorted(H.j_split | {0, H.nr})
    counts = dict(plates=0, bolts=0)
    for side, sname in ((1, 'stbd'), (-1, 'port')):
        plates = MB(); bolts = MB(); recess = MB()
        for a in range(len(s_lines) - 1):
            for b in range(len(j_lines) - 1):
                i0, i1, j0, j1 = s_lines[a], s_lines[a + 1], j_lines[b], j_lines[b + 1]
                if i1 <= i0 or j1 <= j0:
                    continue
                tag = int(H.tag[side][i0, j0])
                if tag == 1:
                    continue
                if tag == 2:        # waist channel floor: long red plates
                    m = 'armour_paint_red' if rng.random() < 0.8 else 'armour_paint_red_dark'
                    counts['plates'] += _plate(recess, bolts, H, (i0, i1, j0, j1), side, -spec.WAIST['depth'], 0.0, m)
                    continue
                if tag == 3:        # equipment bay floor
                    counts['plates'] += _plate(recess, bolts, H, (i0, i1, j0, j1), side, -spec.BAYS['depth'], 0.0, 'machinery_dark')
                    continue
                rects = []
                _split(rng, i0, i1, j0, j1, H, rects, (1.1, 2.6), (3, 6))
                for r in rects:
                    h = rng.choice(spec.PANEL_LAYERS)
                    m = rng.choice(GUNMETAL)
                    chin = (H.chin[0] <= r[2] and r[3] <= H.chin[1] and H.st[r[1]] <= 5.3)
                    if chin:
                        m = 'armour_paint_red'; h = 0.03
                    elif rng.random() < 0.025:
                        m = 'armour_paint_red_dark'
                    counts['plates'] += _plate(plates, bolts, H, r, side, 0.0, h, m)
                    # applique armour: a second, smaller plate bolted on top
                    if not chin and r[1] - r[0] >= 5 and r[3] - r[2] >= 4 and rng.random() < 0.16:
                        counts['plates'] += _plate(plates, bolts, H, (r[0] + 1, r[1] - 1, r[2] + 1, r[3] - 1), side, 0.0, h + 0.04, rng.choice(GUNMETAL))
        finish(f'armour_plates_{sname}', plates, parent, group='fuselage')
        finish(f'recess_floors_{sname}', recess, parent, group='fuselage')
        finish(f'armour_bolts_{sname}', bolts, parent, sharp=60, group='fasteners')
        counts['bolts'] += len(bolts.F) // 7
    return counts

def build_shells(H, parent):
    """Substructure shell under the plates (seen in the gaps) and the pressure-hull lining (seen from inside)."""
    for side, sname in ((1, 'stbd'), (-1, 'port')):
        fl = side < 0
        base = MB(); lining = MB()
        for off, mb, m, inward in ((spec.OFF_BASE, base, 'substructure_dark', False), (spec.OFF_LINING, lining, 'lining_panel', True)):
            G = H.nodes(0, H.ni - 1, 0, H.nr, off, side)
            idx = [[mb.v(G[a, b]) for b in range(H.nr + 1)] for a in range(H.ni)]
            for a in range(H.ni - 1):
                for b in range(H.nr):
                    if H.tag[side][a, b] == 1:
                        continue
                    if np.linalg.norm(np.cross(G[a + 1, b + 1] - G[a, b], G[a, b + 1] - G[a + 1, b])) < 1e-6:
                        continue
                    q = (idx[a][b], idx[a + 1][b], idx[a + 1][b + 1], idx[a][b + 1])
                    mb.f(q[::-1] if (fl != inward) else q, m)
        finish(f'substructure_shell_{sname}', base, parent, group='fuselage')
        finish(f'pressure_hull_lining_{sname}', lining, parent, group='fuselage')

def build_coamings(H, parent):
    mb = MB(); bolts = MB()
    for name, rect in H.openings.items():
        if name in ('canopy', 'waist') or name.startswith('bay_'):
            continue
        coaming(mb, bolts, H, rect, lip=0.075 if not name.startswith('port_') else -spec.WAIST['depth'] + 0.05, width=0.11 if not name.startswith('port_') else 0.07)
    # bay surrounds: a low wall around each recessed bay
    for name, rect in H.openings.items():
        if name.startswith('bay_'):
            coaming(mb, bolts, H, rect, m='armour_gunmetal_d', lip=0.065, width=0.07, o_in=-spec.BAYS['depth'])
    finish('opening_coamings', mb, parent, group='fuselage')
    finish('coaming_bolts', bolts, parent, sharp=60, group='fasteners')

def build_frames(H, parent):
    """Ring frames every metre and six longerons a side, standing 0.10 m proud of the lining so the inside reads as built."""
    fr = MB(); lo = MB(); d = 0.10; w = 0.045
    frames = [H.si(s) for s in np.arange(math.ceil(S['cockpit_fwd']), S['hull_aft'] + 0.01, spec.FRAME_PITCH)]
    for side in (1, -1):
        fl = side < 0
        for i in sorted(set(frames)):
            runs = []; cur = []
            for j in range(H.nr + 1):
                cut = any(H.tag[side][min(max(ii, 0), H.ni - 2), min(max(jj, 0), H.nr - 1)] == 1 for ii in (i - 1, i) for jj in (j - 1, j))
                if cut:
                    if len(cur) > 1: runs.append(cur)
                    cur = []
                else:
                    cur.append(j)
            if len(cur) > 1: runs.append(cur)
            for run in runs:
                def ring(off, ds):
                    return [np.array(H.pt(i, j, off, side)) + np.array((ds, 0, 0)) for j in run]
                a0, a1 = ring(spec.OFF_BASE, -w), ring(spec.OFF_BASE, w); b0, b1 = ring(spec.OFF_LINING - d, -w), ring(spec.OFF_LINING - d, w)
                for (p, q, flip) in ((a0, b0, False), (b0, b1, False), (b1, a1, False)):
                    ip = [fr.v(x) for x in p]; iq = [fr.v(x) for x in q]
                    for k in range(len(run) - 1):
                        quad = (ip[k], iq[k], iq[k + 1], ip[k + 1])
                        fr.f(quad[::-1] if (flip != fl) else quad, 'structure_steel')
        for j in (4, 10, 16, 21, 27, 32):
            runs = []; cur = []
            for i in range(H.si(S['cockpit_fwd']), H.si(S['hull_aft']) + 1):
                cut = any(H.tag[side][min(max(ii, 0), H.ni - 2), min(max(jj, 0), H.nr - 1)] == 1 for ii in (i - 1, i) for jj in (j - 1, j))
                if cut:
                    if len(cur) > 1: runs.append(cur)
                    cur = []
                else:
                    cur.append(i)
            if len(cur) > 1: runs.append(cur)
            for run in runs:
                def rail(off, k):
                    out = []
                    for i in run:
                        t = H.P[i, min(j + 1, H.nr)] - H.P[i, max(j - 1, 0)]; t = t / max(np.linalg.norm(t), 1e-9)
                        p = H.P[i, j] + off * H.N[i, j] + k * w * t
                        out.append(np.array((p[0], side * p[1], p[2])))
                    return out
                a0, a1 = rail(spec.OFF_LINING, -1), rail(spec.OFF_LINING, 1); b0, b1 = rail(spec.OFF_LINING - 0.06, -1), rail(spec.OFF_LINING - 0.06, 1)
                for (p, q) in ((a0, b0), (b0, b1), (b1, a1)):
                    ip = [lo.v(x) for x in p]; iq = [lo.v(x) for x in q]
                    for k in range(len(run) - 1):
                        quad = (ip[k], ip[k + 1], iq[k + 1], iq[k])
                        lo.f(quad[::-1] if fl else quad, 'structure_steel')
    finish('ring_frames', fr, parent, group='fuselage'); finish('longerons', lo, parent, group='fuselage')
    return len(set(frames))

# ------------------------------------------------------------------ decks and bulkheads
DOOR = (-0.50, 0.50)       # clear door width
LADDER = (6.90, 7.70, 0.62, 1.28)      # ladder well in the vestibule, starboard side (s0, s1, y0, y1)

def build_decks(H, parent):
    Lf = spec.LIFT; Lb = spec.LANDER_BAY; G = spec.GEAR
    d = MB()
    deck_slab(d, spec.Z_MAIN, spec.DECK_T, S['cockpit_fwd'], S['eng_aft'], 'deck_plate', holes=[LADDER], m_under='lining_panel_dark', m_edge='structure_steel')
    finish('deck_main', d, parent, group='fuselage')
    d = MB()
    import landing_gear
    holes = [(Lf['s0'], Lf['s1'], -Lf['half_w'], Lf['half_w']), (Lb['s0'], Lb['s1'], -Lb['door_half'], Lb['door_half'])] + landing_gear.well_holes()
    deck_slab(d, spec.Z_LOWER, 0.10, 4.4, 22.6, 'deck_plate', holes=holes, m_under='substructure_dark', m_edge='structure_steel')
    finish('deck_lower', d, parent, group='fuselage')
    # ceilings: a flat soffit with light strips
    c = MB(); zc = spec.Z_MAIN + spec.HEAD_MAIN
    deck_slab(c, zc + 0.06, 0.06, S['cockpit_aft'], S['eng_aft'], 'lining_panel', m_under='lining_panel')
    for (s0, s1) in ((S['cockpit_aft'] + 0.3, S['vestibule_aft'] - 0.3), (S['vestibule_aft'] + 0.3, S['hold_aft'] - 0.3), (S['hold_aft'] + 0.3, S['eng_fwd'] - 0.3), (S['eng_fwd'] + 0.3, S['eng_aft'] - 0.3)):
        for y in (-0.75, 0.75):
            c.box(s0, s1, y - 0.07, y + 0.07, zc - 0.03, zc + 0.01, 'light_panel')
    zl = spec.Z_LOWER + spec.HEAD_LOWER
    for (s0, s1) in ((4.8, S['hold_fwd'] - 0.3), (S['hold_fwd'] + 0.2, S['hold_aft'] - 0.3), (S['hold_aft'] + 0.3, S['eng_fwd'] - 0.3)):
        for y in (-1.55, 1.55):
            c.box(s0, s1, y - 0.06, y + 0.06, zl - 0.04, zl, 'light_panel')
    finish('ceilings_and_lights', c, parent, group='fuselage')

BULKHEADS = (
    # name, station, doors on the main deck, doors on the lower deck
    ('bulkhead_cockpit_fwd', 'cockpit_fwd', False, False),
    ('bulkhead_cockpit_aft', 'cockpit_aft', True, False),
    ('bulkhead_vestibule_aft', 'vestibule_aft', True, False),
    ('bulkhead_hold_fwd', 'hold_fwd', False, True),
    ('bulkhead_hold_aft', 'hold_aft', True, True),
    ('bulkhead_eng_fwd', 'eng_fwd', True, True),
    ('bulkhead_eng_aft', 'eng_aft', False, False),
)

def build_bulkheads(H, parent):
    bolts = MB()
    for name, st, dm, dl in BULKHEADS:
        b = MB(); s = S[st]; doors = []
        if dm: doors.append((DOOR[0], DOOR[1], spec.Z_MAIN, spec.Z_MAIN + 2.0))
        if dl: doors.append((DOOR[0], DOOR[1], spec.Z_LOWER, spec.Z_LOWER + 1.95))
        z0 = None; z1 = None
        if st == 'hold_fwd': z1 = spec.Z_MAIN - spec.DECK_T       # lower deck only
        if st == 'cockpit_fwd': z1 = 0.60                         # stops under the glare shield
        if st in ('cockpit_aft', 'vestibule_aft'): z0 = spec.Z_MAIN - spec.DECK_T
        bulkhead(b, s, 0.08, 'lining_panel', doors=doors, z0=z0, z1=z1, m_edge='structure_steel')
        # door frames with a bolt circle of sorts: bolts up the jambs and across the head
        for (y0, y1, zz0, zz1) in doors:
            fr = 0.09
            for (sa, sb, face, nx) in ((s - 0.024, s, s - 0.024, -1), (s + 0.08, s + 0.104, s + 0.104, 1)):
                for (a, c, e, f) in ((y0 - fr, y0, zz0, zz1 + fr), (y1, y1 + fr, zz0, zz1 + fr), (y0, y1, zz1, zz1 + fr)):
                    b.box(sa, sb, a, c, e, f, 'structure_steel')
                for y in (y0 - fr / 2, y1 + fr / 2):
                    bolts.bolt_line((face, y, zz0 + 0.12), (face, y, zz1), (nx, 0, 0), pitch=0.22, r=0.014, h=0.008)
                bolts.bolt_line((face, y0, zz1 + fr / 2), (face, y1, zz1 + fr / 2), (nx, 0, 0), pitch=0.2, r=0.014, h=0.008)
        finish(name, b, parent, group='fuselage')
    finish('bulkhead_bolts', bolts, parent, sharp=60, group='fasteners')

def build(H):
    parent = empty('fuselage', 'wayfarer')
    info = build_plating(H, parent)
    build_shells(H, parent)
    build_coamings(H, parent)
    info['frames'] = build_frames(H, parent)
    build_decks(H, parent)
    build_bulkheads(H, parent)
    return info
