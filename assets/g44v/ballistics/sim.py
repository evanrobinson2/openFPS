#!/usr/bin/env python3
"""G44 V exterior ballistics: .22 LR point-mass trajectories with the G1 drag function for three named CCI loads.
    python3 sim.py   -> ballistics.json, plots/, and the DATA block of g44v-ballistics.js

Sources.  Ballistic coefficients, test-barrel velocities, downrange velocities and trajectory heights: CCI's product pages
(cci-ammunition.com, parts 35, 30 and 960, retrieved 2026-11-17).  Pistol muzzle velocities: ../action/action.json (the
102 mm barrel, simulated).  G1 drag function: the standard projectile table (Ingalls / BRL, as tabulated by McCoy).
Atmosphere: ICAO standard sea level.  Twist: 1 turn in 16 in, the SAAMI standard for .22 Long Rifle (the maker's table does not
give the G44 V's twist; inferred).  Dispersion: inferred, not measured.  Sport and range simulation only.
"""
import json, math, os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ACT = json.load(open(os.path.join(HERE, '..', 'action', 'action.json')))
INV = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
FPS, YD, IN, GR = 0.3048, 0.9144, 0.0254, 64.79891e-6
G0, BC_SI, RHO0, A0 = 9.80665, 703.0696, 1.225, 340.294
G1 = [[0.00, 0.2629], [0.05, 0.2558], [0.10, 0.2487], [0.15, 0.2413], [0.20, 0.2344], [0.25, 0.2278], [0.30, 0.2214], [0.35, 0.2155], [0.40, 0.2104], [0.45, 0.2061], [0.50, 0.2032],
      [0.55, 0.2020], [0.60, 0.2034], [0.70, 0.2165], [0.725, 0.2230], [0.75, 0.2313], [0.775, 0.2417], [0.80, 0.2546], [0.825, 0.2706], [0.85, 0.2901], [0.875, 0.3136], [0.90, 0.3415],
      [0.925, 0.3734], [0.95, 0.4084], [0.975, 0.4448], [1.00, 0.4805], [1.025, 0.5136], [1.05, 0.5427], [1.075, 0.5677], [1.10, 0.5883], [1.125, 0.6053], [1.15, 0.6191], [1.20, 0.6393],
      [1.25, 0.6518], [1.30, 0.6589], [1.35, 0.6621], [1.40, 0.6625], [1.45, 0.6607], [1.50, 0.6573], [1.55, 0.6528], [1.60, 0.6474], [1.65, 0.6413], [1.70, 0.6347], [1.75, 0.6280],
      [1.80, 0.6210], [1.85, 0.6141], [1.90, 0.6072], [1.95, 0.6003], [2.00, 0.5934]]
sock = {s['name']: s['pos_mm'] for s in INV['sockets']}
SIGHT_H = sock['socket_rear_sight']['Z'] * 1e-3            # line of sight above the bore, from the model: 15.9 mm
MUZZLE_Z = sock['socket_muzzle']['L'] * 1e-3
AMMO = dict(
    cci_standard_velocity=dict(label='CCI Standard Velocity 40 gr LRN (part 35)', bc=0.120, mv_test=1070 * FPS, pub=dict(v_fps={50: 977, 75: 940, 100: 908}, path_in={25: 2.2, 50: 3.8, 75: 3.1}), sigma_moa=3.0),
    cci_mini_mag=dict(label='CCI Mini-Mag 40 gr CPRN (part 30)', bc=0.130, mv_test=1235 * FPS, pub=dict(v_fps={50: 1092, 75: 1040, 100: 998}, path_in={25: 1.5, 50: 2.9, 75: 2.4}), sigma_moa=3.5),
    cci_quiet_22=dict(label='CCI Quiet-22 40 gr LRN (part 960)', bc=0.120, mv_test=710 * FPS, pub=dict(v_fps={50: 674, 75: 656, 100: 640}, path_in={25: 6.0, 50: 8.9, 75: 7.0}), sigma_moa=4.0))
for k, a in AMMO.items():
    a['mass'] = 40 * GR; a['diameter'] = 5.66e-3; a['length'] = 11.6e-3
    a['mv'] = ACT['loads'][k]['pistol']['muzzle_velocity_mps']
H = 0.001      # integrator step, s (RK4); the JS runtime uses the same step and arithmetic
def cd_g1(m):
    if m >= 2.0: return G1[-1][1]
    lo, hi = 0, len(G1) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if G1[mid][0] <= m: lo = mid
        else: hi = mid
    return G1[lo][1] + (G1[hi][1] - G1[lo][1]) * (m - G1[lo][0]) / (G1[hi][0] - G1[lo][0])
def accel(vel, bc, wind=(0.0, 0.0, 0.0), rho=RHO0, a_snd=A0):
    rx, ry, rz = vel[0] - wind[0], vel[1] - wind[1], vel[2] - wind[2]; s = math.sqrt(rx * rx + ry * ry + rz * rz)
    k = rho * s * cd_g1(s / a_snd) * math.pi / (8 * bc * BC_SI)
    return (-k * rx, -k * ry - G0, -k * rz)
def step(pos, vel, bc, wind, h=H):
    def f(v_): return accel(v_, bc, wind)
    k1v = f(vel); v2 = [vel[i] + k1v[i] * h / 2 for i in range(3)]; k2v = f(v2); v3 = [vel[i] + k2v[i] * h / 2 for i in range(3)]; k3v = f(v3)
    v4 = [vel[i] + k3v[i] * h for i in range(3)]; k4v = f(v4)
    npos = [pos[i] + h * (vel[i] + 2 * v2[i] + 2 * v3[i] + v4[i]) / 6 for i in range(3)]
    nvel = [vel[i] + h * (k1v[i] + 2 * k2v[i] + 2 * k3v[i] + k4v[i]) / 6 for i in range(3)]
    return npos, nvel
def fly(mv, bc, elev, X, wind=(0.0, 0.0, 0.0), y0=0.0):
    """flat-fire states at the downrange distances X (ascending): (y, x_lateral, speed, tof). +Z downrange, +Y up, +X left."""
    pos = [0.0, y0, 0.0]; vel = [0.0, mv * math.sin(elev), mv * math.cos(elev)]; t = 0.0; out = []; j = 0
    while j < len(X) and t < 30:
        npos, nvel = step(pos, vel, bc, wind)
        while j < len(X) and npos[2] >= X[j]:
            f = (X[j] - pos[2]) / (npos[2] - pos[2])
            out.append((pos[1] + (npos[1] - pos[1]) * f, pos[0] + (npos[0] - pos[0]) * f, math.sqrt(sum((vel[i] + (nvel[i] - vel[i]) * f) ** 2 for i in range(3))), t + H * f)); j += 1
        pos, vel = npos, nvel; t += H
        if vel[2] <= 1.0: break
    while len(out) < len(X): out.append((float('nan'),) * 4)
    return out
def zero_angle(mv, bc, sight_h, zero):
    """bore elevation above the line of sight so the bullet crosses the line of sight at `zero` metres (bisection, 40 steps)"""
    lo, hi = -0.02, 0.2
    for _ in range(40):
        mid = (lo + hi) / 2
        y = fly(mv, bc, mid, [zero], y0=-sight_h)[0][0]
        if y < 0: lo = mid
        else: hi = mid
    return (lo + hi) / 2
def max_range(mv, bc):
    best = (0, 0)
    for deg in range(20, 41, 1):
        e = math.radians(deg); pos = [0.0, 1.5, 0.0]; vel = [0.0, mv * math.sin(e), mv * math.cos(e)]
        while pos[1] > 0: pos, vel = step(pos, vel, bc, (0, 0, 0), 0.005)
        if pos[2] > best[0]: best = (pos[2], deg)
    return best
def miller_sg(a, mv, twist_in=16.0):
    d = a['diameter'] / IN; l = a['length'] / IN / d; m = a['mass'] / GR; t = twist_in / d
    return 30 * m / (t * t * d ** 3 * l * (1 + l * l)) * (mv / FPS / 2800) ** (1 / 3)

def main():
    D = dict(meta=dict(title='G44 V exterior ballistics', credit='carpetshark', generator='sim.py', frame='metres, seconds, +Y up, +Z downrange, +X left',
                       drag='G1 point mass, RK4 at 1 ms', atmosphere=dict(rho=RHO0, sound=A0, note='ICAO standard sea level'), sight_height_m=SIGHT_H,
                       twist='1 in 16 in (SAAMI standard for .22 LR; the G44 V figure is not in the maker\'s table)', default_zero_m=25.0,
                       default_zero_note='inferred: the manual gives no zero distance; sights are user adjustable (manual p. 10: screwdriver for the adjustable rear sight)'),
             ammo={}, validation={})
    worst_v = 0.0; worst_p = 0.0
    for k, a in AMMO.items():
        # ---- check against CCI's own table: test-barrel velocity, 100 yd zero, sights 1.5 in above the bore
        Xv = [50 * YD, 75 * YD, 100 * YD]; e = zero_angle(a['mv_test'], a['bc'], 1.5 * IN, 100 * YD)
        fl = fly(a['mv_test'], a['bc'], e, [25 * YD, 50 * YD, 75 * YD, 100 * YD], y0=-1.5 * IN)
        vv = {yd: fl[i + 1][2] / FPS for i, yd in enumerate((50, 75, 100))}; pp = {yd: fl[i][0] / IN for i, yd in enumerate((25, 50, 75))}
        rows_v = [dict(range_yd=yd, model_fps=round(vv[yd], 1), published_fps=a['pub']['v_fps'][yd], diff_fps=round(vv[yd] - a['pub']['v_fps'][yd], 1)) for yd in (50, 75, 100)]
        rows_p = [dict(range_yd=yd, model_in=round(pp[yd], 2), published_in=a['pub']['path_in'][yd], diff_in=round(pp[yd] - a['pub']['path_in'][yd], 2)) for yd in (25, 50, 75)]
        worst_v = max(worst_v, max(abs(r['diff_fps']) for r in rows_v)); worst_p = max(worst_p, max(abs(r['diff_in']) for r in rows_p))
        D['validation'][k] = dict(source='CCI product page: muzzle %d fps, BC %.3f, 100 yd zero, sights 1.5 in above the bore' % (round(a['mv_test'] / FPS), a['bc']), velocity=rows_v, path=rows_p)
        # ---- the pistol
        zero = 25.0; ez = zero_angle(a['mv'], a['bc'], SIGHT_H, zero); X = [float(x) for x in range(0, 105, 5)]; X[0] = 0.001
        f0 = fly(a['mv'], a['bc'], ez, X, y0=-SIGHT_H); fw = fly(a['mv'], a['bc'], ez, X, wind=(4.4704, 0.0, 0.0), y0=-SIGHT_H)
        tab = [dict(range_m=round(x), v_mps=round(s[2], 2), energy_J=round(0.5 * a['mass'] * s[2] ** 2, 2), path_mm=round(s[0] * 1e3, 2), tof_s=round(s[3], 5), drift_10mph_mm=round(w[1] * 1e3, 2), mach=round(s[2] / A0, 3))
               for x, s, w in zip(X, f0, fw)]
        mr = max_range(a['mv'], a['bc'])
        D['ammo'][k] = dict(label=a['label'], bc_g1=a['bc'], mass_kg=a['mass'], diameter_m=a['diameter'], length_m=a['length'], mv=a['mv'], mv_test_barrel=round(a['mv_test'], 2),
                            mv_source='../action/action.json: simulated 102 mm barrel', supersonic_at_muzzle=bool(a['mv'] > A0), sigma_moa=a['sigma_moa'],
                            sigma_note='inferred standard deviation per axis for pistol and load together; not measured', sg_miller=round(miller_sg(a, a['mv']), 2),
                            zero_25m_elevation_rad=ez, table_zero_25m=tab, max_range_m=round(mr[0]), max_range_elevation_deg=mr[1])
    D['validation']['summary'] = dict(worst_velocity_diff_fps=worst_v, worst_path_diff_in=worst_p,
                                      note='the model flown from CCI\'s test-barrel velocity with CCI\'s G1 coefficient, against CCI\'s downrange table. CCI gives path to 0.1 in and velocity to 1 fps')
    D['validation']['max_range'] = dict(model_m={k: D['ammo'][k]['max_range_m'] for k in AMMO}, reference='.22 LR boxes warn of a range of 1.5 miles (about 2.4 km); manual p. 13 warns of up to about 3 km for GLOCK pistols in general',
                                        note='from the 102 mm barrel, sea level, no wind; an upper bound check only')
    # parity cases for the JS runtime
    par = []
    for k, a in AMMO.items():
        for zero, dist, wind in ((25.0, 50.0, 0.0), (15.0, 75.0, 3.0), (50.0, 10.0, -2.0)):
            ez = zero_angle(a['mv'], a['bc'], SIGHT_H, zero); s = fly(a['mv'], a['bc'], ez, [dist], wind=(wind, 0.0, 0.0), y0=-SIGHT_H)[0]
            par.append(dict(ammo=k, zero=zero, distance=dist, wind_x=wind, y=s[0], x=s[1], v=s[2], tof=s[3], elevation=ez))
    D['parity'] = dict(note='poi() cases computed by sim.py; test.js must reproduce them with g44v-ballistics.js', cases=par)
    json.dump(D, open(os.path.join(HERE, 'ballistics.json'), 'w'), indent=1)
    # the runtime's DATA block
    data = dict(g1=G1, ammo={k: dict(label=a['label'], bc=a['bc'], mass=a['mass'], diameter=a['diameter'], mv=a['mv'], sigma_moa=a['sigma_moa']) for k, a in AMMO.items()},
                sight_height=SIGHT_H, muzzle_z=MUZZLE_Z, rho0=RHO0, sound0=A0, default_zero=25.0)
    js = os.path.join(HERE, 'g44v-ballistics.js')
    if os.path.exists(js):
        src = open(js).read(); src = re.sub(r'/\*DATA-BEGIN.*?\*/.*?/\*DATA-END\*/', lambda m_: '/*DATA-BEGIN (written by sim.py; do not edit by hand)*/\nconst DATA = ' + json.dumps(data, separators=(',', ':')) + ';\n/*DATA-END*/', src, flags=re.S)
        open(js, 'w').write(src)
    for k in AMMO:
        vd = D['validation'][k]; a = D['ammo'][k]; t = a['table_zero_25m']
        print('%-22s CCI check: v diff %s fps, path diff %s in | pistol mv %.1f m/s, at 25 m %.1f m/s, at 50 m path %.0f mm, max range %d m, Sg %.2f' % (
            k, [r['diff_fps'] for r in vd['velocity']], [r['diff_in'] for r in vd['path']], a['mv'], t[5]['v_mps'], t[10]['path_mm'], a['max_range_m'], a['sg_miller']))
    if '--noplots' not in sys.argv:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        os.makedirs(os.path.join(HERE, 'plots'), exist_ok=True); col = dict(cci_standard_velocity='#1f6fb4', cci_mini_mag='#c0392b', cci_quiet_22='#2e8b57')
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        for k, a in D['ammo'].items():
            t = a['table_zero_25m']; ax[0].plot([r['range_m'] for r in t], [r['path_mm'] for r in t], color=col[k], label=a['label']); ax[1].plot([r['range_m'] for r in t], [r['v_mps'] for r in t], color=col[k])
        ax[0].axhline(0, color='k', lw=0.6); ax[0].set_xlabel('range, m'); ax[0].set_ylabel('bullet above the line of sight, mm'); ax[0].set_title('Pistol, 25 m zero'); ax[0].legend(fontsize=7)
        ax[1].axhline(A0, color='k', ls=':', lw=0.8); ax[1].set_xlabel('range, m'); ax[1].set_ylabel('velocity, m/s'); ax[1].set_title('Velocity (dotted: speed of sound)')
        fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', 'trajectory_zero_25m.png'), dpi=110); plt.close(fig)
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        for k in AMMO:
            vd = D['validation'][k]
            ax[0].plot([r['range_yd'] for r in vd['velocity']], [r['published_fps'] for r in vd['velocity']], 'o', color=col[k]); ax[0].plot([r['range_yd'] for r in vd['velocity']], [r['model_fps'] for r in vd['velocity']], '-', color=col[k], label=k)
            ax[1].plot([r['range_yd'] for r in vd['path']], [r['published_in'] for r in vd['path']], 'o', color=col[k]); ax[1].plot([r['range_yd'] for r in vd['path']], [r['model_in'] for r in vd['path']], '-', color=col[k])
        ax[0].set_xlabel('range, yd'); ax[0].set_ylabel('velocity, fps'); ax[0].set_title('Model (lines) against CCI\'s table (points)'); ax[0].legend(fontsize=7)
        ax[1].set_xlabel('range, yd'); ax[1].set_ylabel('path above the line of sight, in'); ax[1].set_title('100 yd zero, sights 1.5 in above the bore')
        fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', 'validation_cci.png'), dpi=110); plt.close(fig)
if __name__ == '__main__':
    main()
