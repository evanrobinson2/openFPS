#!/usr/bin/env python3
"""12 gauge exterior ballistics for the shotgun-590 asset: a 1 oz rifled slug and nine-pellet 00 buckshot.

    python3 ballistics/sim.py      # writes ballistics.json and plots/

Point-mass flight with drag, gravity and wind. The slug uses the maker's published G1 ballistic coefficient and is
checked against the maker's published downrange table. Buckshot pellets are lead spheres with a sphere drag curve;
the pattern is a seeded angular scatter calibrated to a published rule of thumb for a cylinder bore.
Every number in LOADS, GUN and PATTERN carries its source.
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IN, FT, YD, GR, LB = 0.0254, 0.3048, 0.9144, 64.79891e-6, 0.45359237
G = 9.80665
RHO0, C0 = 1.2250, 340.294            # ICAO standard atmosphere at sea level, 15 C
BC_SI = LB / IN ** 2                   # 1 lb/in^2 in kg/m^2 (703.07)

# Standard G1 drag function (Cd versus Mach), the BRL table as distributed with JBM and py-ballisticcalc
# (the same table as assets/hk416/ballistics/sim.py).
G1 = np.array([
 (0.00,.2629),(0.05,.2558),(0.10,.2487),(0.15,.2413),(0.20,.2344),(0.25,.2278),(0.30,.2214),(0.35,.2155),
 (0.40,.2104),(0.45,.2061),(0.50,.2032),(0.55,.2020),(0.60,.2034),(0.70,.2165),(0.725,.2230),(0.75,.2313),
 (0.775,.2417),(0.80,.2546),(0.825,.2706),(0.85,.2901),(0.875,.3136),(0.90,.3415),(0.925,.3734),(0.95,.4084),
 (0.975,.4448),(1.0,.4805),(1.025,.5136),(1.05,.5427),(1.075,.5677),(1.10,.5883),(1.125,.6053),(1.15,.6191),
 (1.20,.6393),(1.25,.6518),(1.30,.6589),(1.35,.6621),(1.40,.6625),(1.45,.6607),(1.50,.6573),(1.55,.6528),
 (1.60,.6474),(1.65,.6413),(1.70,.6347),(1.75,.6280),(1.80,.6210),(1.85,.6141),(1.90,.6072),(1.95,.6003),
 (2.00,.5934)])
# Drag of a smooth sphere versus Mach at Reynolds numbers near 1e5. Approximate values recalled from the published
# sphere-drag literature (Bailey and Hiatt 1972; Miller and Bailey 1979), not re-read for this build: treat as
# +/- 10 %. A pellet deformed by firing has more drag than this.
SPHERE = np.array([(0.0, .47), (0.3, .47), (0.5, .50), (0.6, .52), (0.7, .56), (0.8, .62), (0.9, .72), (1.0, .84), (1.1, .92), (1.2, .96), (1.4, 1.00), (1.6, 1.00), (2.0, .98)])

LOADS = {
    'slug': dict(
        name='1 oz rifled slug, 2 3/4 in', kind='slug', count=1,
        mass_kg=438 * GR, muzzle_velocity=1610 * FT, drag='G1', bc_lb_in2=0.110, diameter_m=0.0185,
        source=dict(all='published: Federal Premium, Power-Shok Rifled Slug F127 RS product page (438 gr, 1610 ft/s, BC .110), read 2026-11-17',
                    diameter_m='nominal 12 gauge bore, 18.5 mm (not on the page)')),
    'buck00': dict(
        name='00 buckshot, nine pellets, 2 3/4 in', kind='shot', count=9,
        pellet_diameter_m=0.33 * IN, pellet_density=11350.0, muzzle_velocity=1325 * FT, drag='sphere',
        source=dict(muzzle_velocity='published: Federal Premium, Power-Shok Buckshot F127 00 product page (9 pellets, 1325), read 2026-11-17',
                    pellet_density='published: the same page (lead, 11.35 g/cc)',
                    pellet_diameter_m='published: 00 buck is .33 caliber (R. Mann, "Buckshot Basics", Shooting Illustrated, 31 Jan 2012)',
                    mass_kg='derived: sphere volume x density = 3.50 g (54.0 gr)')),
}
LOADS['buck00']['mass_kg'] = math.pi / 6 * LOADS['buck00']['pellet_diameter_m'] ** 3 * LOADS['buck00']['pellet_density']

MODEL = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
_p = MODEL['params']; _K = MODEL['ruler']['mm_per_px']
_bead_top = (_p['barrel_r'] + _p['bead'][1] * 1.8) * 1e-3; _bead_z = _p['bead'][0] * 1e-3
_rear_z = (409 - 577) * _K * 1e-3; _rear_y = _p['recv_top'] * 1e-3
GUN = dict(
    muzzle_z=_p['muzzle'] * 1e-3,
    sights=dict(
        bead_flat=dict(rear=[_rear_z, _rear_y], front=[_bead_z, _bead_top],
                       note='line of sight from the rear edge of the receiver\'s flat top over the bead (model geometry, traced from the profile photo). An inference: the manual says nothing about the sight picture.'),
        bore=dict(rear=[0.0, 0.0], front=[1.0, 0.0], note='along the bore axis (no sights)')),
    velocity_note='Published shotshell velocities are test-barrel figures. This simulation uses them unchanged as the muzzle velocity; action/sim.py estimates what a 20 in barrel loses.',
)
PATTERN = dict(
    spread_in_per_yd=1.0,
    source='published rule of thumb for a 12 gauge cylinder bore: about 1 in of pattern spread per yard (R. Mann, "Buckshot Basics", Shooting Illustrated, 31 Jan 2012). The same article reports loads patterning at half that; this is a nominal, not a measurement of this load.',
    definition='spread = the largest distance between any two of the nine pellet holes (extreme spread), averaged over shots',
    model='each pellet leaves with an independent angular error, normal on each axis with standard deviation sigma; sigma is set so the mean extreme spread of nine pellets equals the rule',
)

def cd(model, mach):
    t = G1 if model == 'G1' else SPHERE
    return float(np.interp(mach, t[:, 0], t[:, 1]))

def k_drag(load):
    """deceleration = k * rho * Cd(M) * v^2"""
    if load['drag'] == 'G1': return math.pi / (8 * load['bc_lb_in2'] * BC_SI)
    d = load['pellet_diameter_m']; return (math.pi * d * d / 4) / (2 * load['mass_kg'])

def fly(load, elev=0.0, v0=None, wind_x=0.0, x_max=200.0, dt=2.5e-4, rho=RHO0, c=C0):
    """state (z downrange, y up, x cross) and velocity; wind_x is a crosswind in m/s (+x). Returns sampled arrays."""
    k = k_drag(load) * rho; v0 = v0 or load['muzzle_velocity']
    s = np.array([0.0, 0.0, 0.0, v0 * math.cos(elev), v0 * math.sin(elev), 0.0])
    def f(s):
        rv = np.array([s[3], s[4], s[5] - wind_x]); sp = math.sqrt(rv @ rv); a = -k * cd(load['drag'], sp / c) * sp * rv
        return np.array([s[3], s[4], s[5], a[0], a[1] - G, a[2]])
    out = [(0.0, *s)]; t = 0.0
    while s[0] < x_max and t < 3.0:
        k1 = f(s); k2 = f(s + 0.5 * dt * k1); k3 = f(s + 0.5 * dt * k2); k4 = f(s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4); t += dt; out.append((t, *s))
    return np.array(out)          # t, z, y, x, vz, vy, vx

def at(tr, z):
    i = np.searchsorted(tr[:, 1], z); i = min(max(i, 1), len(tr) - 1); a, b = tr[i - 1], tr[i]; u = (z - a[1]) / (b[1] - a[1]); return a + (b - a) * u

def zero_elev(load, zero_m, sight_h, sight_slope=0.0):
    """bore elevation above the sight line that puts the shot on the line of sight at zero_m"""
    lo, hi = -0.01, 0.05
    for _ in range(50):
        mid = (lo + hi) / 2; y = at(fly(load, mid, x_max=zero_m + 1), zero_m)[2] - sight_h
        lo, hi = (mid, hi) if y < 0 else (lo, mid)
    return (lo + hi) / 2

def rng(seed):                    # mulberry32, the same sequence as the JavaScript module
    s = seed & 0xFFFFFFFF
    def r():
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF; z = s
        z = ((z ^ (z >> 15)) * (z | 1)) & 0xFFFFFFFF
        z = (z ^ ((z + (((z ^ (z >> 7)) * (z | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return r

def gauss2(r):
    u = max(r(), 1e-12); v = r(); m = math.sqrt(-2 * math.log(u)); return m * math.cos(2 * math.pi * v), m * math.sin(2 * math.pi * v)

def extreme_spread(pts):
    return max(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(pts) for b in pts[i + 1:])

def main():
    out = dict(units='SI: metres, seconds, kilograms, radians unless a key says otherwise', atmosphere=dict(rho=RHO0, c=C0, note='ICAO standard, sea level, 15 C'),
               gravity=G, loads=LOADS, gun=GUN, pattern=PATTERN, drag_tables=dict(G1=G1.tolist(), sphere=SPHERE.tolist()), checks={})
    # ---- slug against Federal's table: 100 yd zero, sights 0.5 in above the bore, 10 mph crosswind
    slug = LOADS['slug']; el = zero_elev(slug, 100 * YD, 0.5 * IN)
    tr = fly(slug, el); trw = fly(slug, el, wind_x=10 * 0.44704)
    pub = {0: (1610, 2521, 0.0, None), 25: (1467, 2092, 0.3, 1.4), 50: (1340, 1746, 1.6, 2.2), 75: (1229, 1469, 3.7, 1.8), 100: (1139, 1262, 6.6, 0.0), 125: (1068, 1110, 10.4, -3.5)}
    rows = []
    for yd, (v, e, wd, tj) in pub.items():
        a = at(tr, yd * YD) if yd else tr[0]; w = at(trw, yd * YD) if yd else trw[0]
        sv = math.hypot(a[4], a[5]) / FT; se = 0.5 * slug['mass_kg'] * (sv * FT) ** 2 / 1.3558179
        rows.append(dict(range_yd=yd, v_fps_pub=v, v_fps_sim=round(sv, 1), energy_ftlb_pub=e, energy_ftlb_sim=round(se, 0), drift_in_pub=wd, drift_in_sim=round(float(w[3]) / IN, 2),
                         path_in_pub=tj, path_in_sim=round(float(a[2] - 0.5 * IN) / IN, 2) if yd else -0.5))
    ev = max(abs(r['v_fps_sim'] - r['v_fps_pub']) / r['v_fps_pub'] for r in rows)
    ep = max(abs(r['path_in_sim'] - r['path_in_pub']) for r in rows if r['path_in_pub'] is not None)
    ed = max(abs(r['drift_in_sim'] - r['drift_in_pub']) for r in rows)
    out['checks']['slug_vs_federal_table'] = dict(
        source='published: Federal Premium F127 RS ballistics table (100 yd zero, sights 0.5 in above the bore, 10 mph crosswind), read 2026-11-17. The page shows no path value at 100 yd; 0.0 is implied by the zero.',
        rows=rows, max_velocity_error_pct=round(100 * ev, 2), max_path_error_in=round(float(ep), 2), max_drift_error_in=round(float(ed), 2),
        passed=bool(ev < 0.02 and ep < 0.5 and ed < 1.0), tolerance='velocity 2 %, path 0.5 in, drift 1.0 in')
    # ---- tables for both loads: velocity, energy, time of flight, drop from the bore line
    ranges = [0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
    tables = {}
    for key, L in LOADS.items():
        t0 = fly(L, 0.0, x_max=101)
        tables[key] = [dict(range_m=r, v=round(float(math.hypot(a[4], a[5])), 2), energy_j=round(0.5 * L['mass_kg'] * float(a[4] ** 2 + a[5] ** 2), 1), tof_s=round(float(a[0]), 5), drop_m=round(float(-a[2]), 5))
                       for r in ranges for a in [at(t0, r) if r else t0[0]]]
    out['tables'] = tables
    # ---- point of impact with the bead: the bore is tilted up from the sight line by the sights' geometry
    s = GUN['sights']['bead_flat']; slope = (s['front'][1] - s['rear'][1]) / (s['front'][0] - s['rear'][0])
    bore_up = -math.atan(slope); h_muzzle = s['rear'][1] + slope * (GUN['muzzle_z'] - s['rear'][0])
    poi = {}
    for key, L in LOADS.items():
        t0 = fly(L, bore_up, x_max=101)
        poi[key] = [dict(range_m=r, above_sight_line_m=round(float(at(t0, r)[2] - h_muzzle), 4)) for r in ranges[1:]]     # frame: sight line horizontal, muzzle h_muzzle below it
    out['sight_bead_flat'] = dict(bore_above_sight_line_rad=round(bore_up, 5), sight_line_height_at_muzzle_m=round(h_muzzle, 5), poi=poi,
                                  note='With the bead seen resting on the receiver\'s flat top, the bore points up by this angle and shots land high. Model-derived from the traced receiver top and a bead that is 2 px tall in the photo (about +/- 1.5 mrad), not a published figure. A shooter whose eye sits above the receiver sees more barrel and shoots flatter: a game may aim along the bore instead.')
    # ---- pattern: calibrate sigma, then seeded samples for the JavaScript parity test
    r = rng(590); n = LOADS['buck00']['count']; es = []
    for _ in range(4000): es.append(extreme_spread([gauss2(r) for _ in range(n)]))
    es_unit = float(np.mean(es)); target = PATTERN['spread_in_per_yd'] * IN / YD
    sigma = round(target / es_unit, 9)
    PATTERN.update(sigma_rad=sigma, mean_extreme_spread_in_sigmas=round(es_unit, 4), calibration='4000 seeded nine-pellet shots (seed 590)')
    r = rng(12); chk = []
    for yd in (7, 15, 25, 40):
        sp = [extreme_spread([[g * sigma * yd * YD for g in gauss2(r)] for _ in range(n)]) / IN for _ in range(1500)]
        chk.append(dict(range_yd=yd, mean_spread_in=round(float(np.mean(sp)), 2), p10_in=round(float(np.percentile(sp, 10)), 2), p90_in=round(float(np.percentile(sp, 90)), 2), rule_in=yd * PATTERN['spread_in_per_yd']))
    out['checks']['pattern_vs_rule'] = dict(source=PATTERN['source'], rows=chk, passed=all(abs(c['mean_spread_in'] - c['rule_in']) / c['rule_in'] < 0.05 for c in chk),
                                            note='a calibration check: sigma was fitted to this rule, so this shows the fit and the shot-to-shot scatter, not an independent validation')
    # the article's qualitative statements, on an 18 in x 30 in upright rectangle aimed at its centre
    r = rng(77); tgt = []
    for yd in (10, 20, 30, 40):
        hits = []
        for _ in range(3000):
            hits.append(sum(1 for _ in range(n) for gx, gy in [gauss2(r)] if abs(gx * sigma * yd * YD) < 9 * IN and abs(gy * sigma * yd * YD) < 15 * IN))
        hits = np.array(hits); tgt.append(dict(range_yd=yd, mean_pellets_on=round(float(hits.mean()), 2), p_all_nine_on=round(float((hits == n).mean()), 3)))
    out['checks']['pattern_on_torso_plate'] = dict(target='18 in wide x 30 in tall, centred aim (our choice of plate)', rows=tgt,
        article='"beyond 20 yards at least one pellet will likely miss a human-size target; beyond 30, half will be hard to keep on a silhouette" (paraphrase of the same article)',
        reading='at 20 yd the model drops at least one pellet off the plate in about 60 % of shots, and at 40 yd it keeps about half on: the same picture as the article, a little kinder at 30 yd. A normal scatter has no fliers; real patterns do')
    # seeded reference shots for the JS test: pellet positions on a plane at 20 m, bore along +z, no gravity term (pure scatter) and with drop
    r = rng(2026); ref = []
    for _ in range(3):
        ref.append([[round(g * sigma, 9) for g in gauss2(r)] for _ in range(n)])
    out['reference_scatter_rad'] = dict(seed=2026, shots=ref)
    out['pattern'] = PATTERN
    # ---- muzzle energy summary
    out['muzzle'] = {k: dict(v=round(L['muzzle_velocity'], 2), energy_j=round(0.5 * L['mass_kg'] * L['muzzle_velocity'] ** 2 * L['count'], 1), momentum=round(L['mass_kg'] * L['muzzle_velocity'] * L['count'], 3)) for k, L in LOADS.items()}
    json.dump(out, open(os.path.join(HERE, 'ballistics.json'), 'w'), indent=1)
    plots(out, tr)
    for k, c in out['checks'].items(): print(k, 'PASS' if c.get('passed', True) else 'FAIL', {a: b for a, b in c.items() if a.startswith('max_')})
    print('sigma', sigma, 'bore up mrad', bore_up * 1e3, 'poi', poi['slug'][5], poi['buck00'][5])

def plots(out, tr):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    rows = out['checks']['slug_vs_federal_table']['rows']
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    yd = tr[:, 1] / YD; m = yd <= 130
    ax[0].plot(yd[m], np.hypot(tr[m, 4], tr[m, 5]) / FT, label='simulation (G1 0.110)'); ax[0].plot([r['range_yd'] for r in rows], [r['v_fps_pub'] for r in rows], 'o', label='Federal table')
    ax[0].set(xlabel='range (yd)', ylabel='velocity (ft/s)', title='Slug velocity'); ax[0].legend()
    ax[1].plot(yd[m], (tr[m, 2] - 0.5 * IN) / IN); ax[1].plot([r['range_yd'] for r in rows[1:]], [r['path_in_pub'] for r in rows[1:]], 'o')
    ax[1].set(xlabel='range (yd)', ylabel='path above line of sight (in)', title='Slug path, 100 yd zero'); ax[1].axhline(0, color='k', lw=0.5)
    ax[2].plot([r['range_yd'] for r in rows], [r['drift_in_sim'] for r in rows], label='simulation'); ax[2].plot([r['range_yd'] for r in rows], [r['drift_in_pub'] for r in rows], 'o', label='Federal table')
    ax[2].set(xlabel='range (yd)', ylabel='drift in a 10 mph crosswind (in)', title='Slug wind drift'); ax[2].legend()
    fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', 'slug_vs_federal.png'), dpi=90); plt.close(fig)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for k, L in LOADS.items():
        t = out['tables'][k]; ax[0].plot([r['range_m'] for r in t], [r['v'] for r in t], 'o-', label=L['name']); ax[1].plot([r['range_m'] for r in t], [r['energy_j'] * L['count'] for r in t], 'o-', label=L['name'])
    ax[0].set(xlabel='range (m)', ylabel='velocity (m/s)', title='Velocity'); ax[1].set(xlabel='range (m)', ylabel='energy of the whole load (J)', title='Energy'); ax[0].legend()
    fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', 'velocity_energy.png'), dpi=90); plt.close(fig)
    fig, ax = plt.subplots(1, 3, figsize=(12, 4.2)); r = rng(5); s = out['pattern']['sigma_rad']
    for a_, yd_ in zip(ax, (7, 15, 25)):
        for shot in range(5):
            pts = np.array([[g * s * yd_ * YD / IN for g in gauss2(r)] for _ in range(9)]); a_.plot(pts[:, 0], pts[:, 1], 'o', ms=5)
        a_.add_patch(plt.Rectangle((-9, -15), 18, 30, fill=False, ec='k')); a_.set(xlim=(-22, 22), ylim=(-22, 22), aspect='equal', title=f'{yd_} yd: five shots, 18 x 30 in plate', xlabel='in')
    fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', 'buckshot_pattern.png'), dpi=90); plt.close(fig)

if __name__ == '__main__':
    main()
