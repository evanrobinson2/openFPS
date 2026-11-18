"""F-27 Wayfarer (1.25 scale), the master numbers. Pure Python + numpy: no Blender needed to read it.

Ship frame (metres):
    s   station, metres aft of the nose tip (0 = nose, 30 = nozzle exit plane)
    y   lateral, + = starboard
    z   up, 0 = the barrel axis of the hull
Blender / export frame (Z up, the ship's front faces -Y, port is +X):  X = -y, Y = s - 15, Z = z.

Every number here is a design decision for a fictional ship, read off the concept image by proportion and then
fixed so that a 1.80 m player fits everywhere they are meant to walk. Nothing is measured from a real vehicle.
"""
import math
import numpy as np

# ------------------------------------------------------------------ envelope
L = 30.0            # overall length (24 m spec x 1.25)
W = 9.0             # overall width, over the engine pods
H = 6.75            # overall height, hull + dorsal and ventral fittings, gear up
R = 3.0             # barrel half-width and half-height
PLAYER_H = 1.80

# ------------------------------------------------------------------ decks (z of the walking surface)
Z_MAIN = 0.10       # main deck: cockpit, vestibule, crew deck, mission bay, engineering gallery
Z_LOWER = -2.30     # lower deck: avionics aisle, hold with the lift, lander bay, reactor floor
DECK_T = 0.25       # structural depth between the main deck floor and the lower deck ceiling
HEAD_MAIN = 2.30    # clear height, main deck
HEAD_LOWER = 2.20   # clear height, lower deck
Z_GROUND = -4.70    # ground plane with the gear down (belly clearance 1.70 m)

# ------------------------------------------------------------------ hull shell build-up (offsets along the outward normal)
OFF_SKIN = 0.0      # nominal outer armour surface
OFF_BASE = -0.30    # substructure shell seen in the panel gaps
OFF_LINING = -0.40  # pressure hull / interior lining surface
PANEL_GAP = 0.012   # half-gap between armour plates
PANEL_LAYERS = (0.0, 0.03, 0.06)   # plates sit at one of these heights: the layered-armour look

# ------------------------------------------------------------------ stations (frames) that matter
ST = dict(
    nose_cap=0.06,
    cockpit_fwd=1.20,       # forward console bulkhead
    canopy_aft=4.40,        # last side window ends
    cockpit_aft=6.20,       # cockpit / vestibule bulkhead
    vestibule_aft=8.20,     # vestibule (crew hatch, ladder well) / crew deck bulkhead
    hold_fwd=8.80,
    lift_fwd=9.60, lift_aft=13.20,
    hold_aft=13.80,         # hold / lander bay bulkhead (lower deck); crew deck / mission bay (main deck)
    lander_fwd=14.20, lander_aft=20.60,
    eng_fwd=21.20,          # engineering forward bulkhead (both decks)
    barrel_aft=21.50,       # hull starts to neck in for the engine section
    nacelle_fwd=23.20,      # intake faces
    eng_aft=24.60,          # engineering aft bulkhead; thrust structure behind it
    hull_aft=28.40,         # aft closure of the hull; main nozzles behind
    tail=30.00,
)
FRAME_PITCH = 1.0           # ring frames every metre from cockpit_fwd to hull_aft

# ------------------------------------------------------------------ nose and canopy
NOSE_Z = -0.80              # height of the nose tip: the nose droops, the canopy sits above it
CANOPY = dict(s0=0.62, s1=4.40, blend_to=6.40,
              sill=lambda s: 0.62 + 0.06 * s,      # lower edge of the glazing, z
              brow=lambda s: 1.42 + 0.06 * s,      # upper edge of the glazing, z: a 0.80 m slit under an armoured brow
              pillars=(0.62, 1.60, 2.55, 3.50, 4.40))

# ------------------------------------------------------------------ waist channel and bays (per side)
WAIST = dict(s0=7.2, s1=21.0, z0=0.22, z1=1.02, depth=0.20)          # the recessed red channel
BAYS = dict(s0=7.8, s1=20.6, z0=-1.35, z1=-0.30, depth=0.16, n=8)   # row of recessed equipment bays under it
PORTS = dict(z0=0.42, z1=0.82, width=0.60, stations=(9.4, 11.4, 13.0, 15.4, 17.4, 19.4))   # viewports in the channel

# ------------------------------------------------------------------ openings
CREW_HATCH = dict(side=-1, s0=6.55, s1=7.65, z0=Z_MAIN, z1=Z_MAIN + 2.0)     # port side, main deck, in the vestibule
LIFT = dict(s0=9.60, s1=13.20, half_w=1.30, travel=1.70, chassis_depth=0.65) # the bottom entrance: a chassis that lowers
LANDER_BAY = dict(s0=14.20, s1=20.60, half_w=1.45, door_half=1.35)           # internal landing array
LANDER = dict(length=5.6, width=2.2, height=1.7)                             # stowed lander envelope
GEAR = dict(                                                                 # four legs, pads, all retract into wells
    fwd=dict(s=6.00, y=1.80, fold=+1, well=(6.0, 9.2)),                      # fold = +1 swings aft, -1 swings forward
    aft=dict(s=21.00, y=1.80, fold=-1, well=(17.8, 21.0)),
    trunnion_z=-1.70, strut_len=3.00, pad_r=0.42, stroke=0.35)

# ------------------------------------------------------------------ engines
ENG = dict(
    pod_y=3.20, pod_z=-0.45, pod_r=1.30, pod_s0=23.20, pod_s1=29.60,     # lower main pod, per side (gives W = 9.0)
    top_y=2.35, top_z=1.75, top_r=0.85, top_s0=24.20, top_s1=29.20,      # upper pod, per side, under the armoured cowl
    core_r=1.25, core_s0=28.40, core_s1=30.00,                           # centre main nozzle
    cowl_s0=21.60, cowl_s1=27.20)

# ------------------------------------------------------------------ weapons and gadgets
CHIN_CANNON = dict(s=2.30, z=-3.02, barrel_len=1.86, barrel_r=0.07, twin=0.20)
BELLY_POD = dict(s=7.4, y=0.0, z=-3.00, len=2.6)

# ------------------------------------------------------------------ hull shape
def _E(t, p):
    """Blunt ogive: 0 at t = 0, 1 at t >= 1, vertical tangent at 0 (super-ellipse quarter)."""
    t = np.clip(t, 0.0, 1.0)
    return (1.0 - (1.0 - t) ** p) ** (1.0 / p)

def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def hull_params(s):
    """Half-width a, top z, bottom z, z of the widest point c, super-ellipse exponent n at station s."""
    s = np.asarray(s, dtype=float)
    a = R * _E(s / 6.5, 2.2)
    zt = NOSE_Z + (R - NOSE_Z) * _E(s / 7.6, 1.85)
    zb = NOSE_Z - (R + NOSE_Z) * _E(s / 4.6, 2.3)
    c = NOSE_Z * (1.0 - _ss(0.0, 5.0, s))
    n = 2.25 + 0.95 * _ss(1.0, 7.0, s)
    # engine section: the barrel necks in between barrel_aft and the intakes, then runs nearly straight
    k = _ss(21.3, 23.4, s)
    a = a * (1 - k) + (2.05 - 0.15 * _ss(24.0, 28.4, s)) * k
    zt = zt * (1 - k) + (2.55 - 0.25 * _ss(24.0, 28.4, s)) * k
    zb = zb * (1 - k) + (-2.50 + 0.30 * _ss(24.0, 28.4, s)) * k
    n = n + 0.5 * k
    return a, zt, zb, c, n

def section(s, m=181):
    """Starboard half of the hull section at station s, top centre to bottom centre: arrays y, z (m points)."""
    a, zt, zb, c, n = [float(v) for v in hull_params(s)]
    ph = np.linspace(0.0, math.pi, m)
    sn, cs = np.sin(ph), np.cos(ph)
    y = a * np.abs(sn) ** (2.0 / n)
    z = np.where(cs >= 0, c + (zt - c) * np.abs(cs) ** (2.0 / n), c - (c - zb) * np.abs(cs) ** (2.0 / n))
    return y, z

def half_width_at(s, z):
    """Outer half-width of the hull at station s and height z (0 if z is outside the section)."""
    y, zz = section(s, 361)
    if z > zz[0] or z < zz[-1]:
        return 0.0
    return float(np.interp(-z, -zz, y))

def stations():
    """Loft stations: dense on the nose, 0.25 m on the barrel, plus every frame that matters."""
    base = [0.06, 0.14, 0.26, 0.42, 0.62, 0.85] + list(np.arange(1.0, 28.41, 0.25))
    extra = [v for v in ST.values() if isinstance(v, float) and 0.06 <= v <= 28.4]
    extra += list(CANOPY['pillars']) + [WAIST['s0'], WAIST['s1'], CREW_HATCH['s0'], CREW_HATCH['s1']]
    out = sorted(set(round(v, 3) for v in base + extra))
    # drop near-duplicates (closer than 6 cm) keeping the named ones
    keep = [out[0]]
    named = set(round(v, 3) for v in extra)
    for v in out[1:]:
        if v - keep[-1] < 0.06:
            if v in named and keep[-1] not in named:
                keep[-1] = v
            continue
        keep.append(v)
    return keep

NR = 36   # rows per half section (top centre to bottom centre)

def hull_grid(nr=NR, st=None):
    """Outer hull surface as a grid P[i, j] (station i, row j) for the starboard half, with unit normals N.

    Rows are spaced by arc length. Over the cockpit two rows are pinned to the canopy brow and sill so the
    glazing has clean edges; the pin fades out between CANOPY['s1'] and CANOPY['blend_to'].
    Returns st (list), P (ni, nr+1, 3), N (ni, nr+1, 3), rows dict(brow=j, sill=j).
    """
    st = st or stations()
    ni = len(st)
    P = np.zeros((ni, nr + 1, 3))
    u_nat = np.linspace(0.0, 1.0, nr + 1)
    # choose the pinned rows from the natural position of the brow and sill at the last window
    def arc(s):
        y, z = section(s, 721)
        d = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(y), np.diff(z)))])
        return y, z, d / d[-1]
    def u_of_z(s, zq):
        y, z, u = arc(s)
        if zq >= z[0]:
            return 0.0
        return float(np.interp(-zq, -z, u))
    sref = CANOPY['s1']
    jb = max(2, int(round(u_of_z(sref, CANOPY['brow'](sref)) * nr)))
    js = max(jb + 3, int(round(u_of_z(sref, CANOPY['sill'](sref)) * nr)))
    for i, s in enumerate(st):
        y, z, u = arc(s)
        w = 1.0 - _ss(CANOPY['s1'], CANOPY['blend_to'], s)
        uq = u_nat.copy()
        if w > 0:
            ub = u_of_z(s, CANOPY['brow'](s)); us = u_of_z(s, CANOPY['sill'](s))
            ub = (1 - w) * u_nat[jb] + w * ub; us = (1 - w) * u_nat[js] + w * us
            us = max(us, ub + 1e-4)
            uq = np.interp(u_nat, [0.0, u_nat[jb], u_nat[js], 1.0], [0.0, ub, us, 1.0])
        P[i, :, 0] = s
        P[i, :, 1] = np.interp(uq, u, y)
        P[i, :, 2] = np.interp(uq, u, z)
    P[:, 0, 1] = 0.0; P[:, nr, 1] = 0.0
    N = grid_normals(P)
    return st, P, N, dict(brow=jb, sill=js)

def grid_normals(P):
    ni, nj, _ = P.shape
    ds = np.zeros_like(P); du = np.zeros_like(P)
    ds[1:-1] = P[2:] - P[:-2]; ds[0] = P[1] - P[0]; ds[-1] = P[-1] - P[-2]
    du[:, 1:-1] = P[:, 2:] - P[:, :-2]; du[:, 0] = P[:, 1] - P[:, 0]; du[:, -1] = P[:, -1] - P[:, -2]
    # where rows collapse (above the nose top) fall back to a radial direction
    N = np.cross(du, ds)
    ln = np.linalg.norm(N, axis=2, keepdims=True)
    a, zt, zb, c, n = hull_params(P[:, 0, 0])
    rad = P - np.stack([P[:, 0, 0], np.zeros(ni), c], axis=1)[:, None, :]
    rad[:, :, 0] = 0.0
    rl = np.linalg.norm(rad, axis=2, keepdims=True)
    rad = rad / np.maximum(rl, 1e-9)
    bad = (ln[:, :, 0] < 1e-7)
    N = N / np.maximum(ln, 1e-12)
    flip = (np.sum(N * rad, axis=2) < 0)
    N[flip] *= -1
    N[bad] = rad[bad]
    # centreline rows: no lateral component
    for j in (0, nj - 1):
        N[:, j, 1] = 0.0
        N[:, j] /= np.maximum(np.linalg.norm(N[:, j], axis=1, keepdims=True), 1e-9)
    return N

def lining_half_width(s, z, off=OFF_LINING):
    """Inner half-width (lining surface) at station s, height z: what the decks and bulkheads are cut to."""
    y, zz = section(s, 361)
    # offset the polyline inward
    dy = np.gradient(y); dz = np.gradient(zz)
    ln = np.maximum(np.hypot(dy, dz), 1e-9)
    ny, nz = -dz / ln, dy / ln            # outward for a top-to-bottom starboard polyline
    yo, zo = y + off * ny, zz + off * nz
    k = np.argsort(zo)
    if z < zo[k][0] or z > zo[k][-1]:
        return 0.0
    return max(0.0, float(np.interp(z, zo[k], yo[k])))

if __name__ == '__main__':
    st, P, N, rows = hull_grid()
    print('stations', len(st), 'rows', rows)
    for s in (0.5, 2, 4, 6, 10, 22, 24, 28):
        print(s, [round(float(v), 2) for v in hull_params(s)], 'main deck half-width', round(lining_half_width(s, Z_MAIN), 2),
              'lower', round(lining_half_width(s, Z_LOWER), 2), 'ceil', round(lining_half_width(s, Z_MAIN + HEAD_MAIN), 2))

def lining_section(s, off=OFF_LINING, m=241):
    """Starboard half of the inner (lining) section at station s, top centre to bottom centre: arrays y, z.
    Points are kept monotonic in z so the outline never folds back on itself in a tight corner."""
    y, zz = section(s, m)
    dy = np.gradient(y); dz = np.gradient(zz)
    ln = np.maximum(np.hypot(dy, dz), 1e-9)
    yo, zo = y + off * (-dz / ln), zz + off * (dy / ln)
    keep = [0]
    for k in range(1, m):
        if zo[k] < zo[keep[-1]] - 1e-5 and yo[k] >= 0:
            keep.append(k)
    yo, zo = yo[keep], zo[keep]
    yo[0] = 0.0; yo[-1] = 0.0
    return yo, zo
