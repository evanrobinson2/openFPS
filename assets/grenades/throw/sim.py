#!/usr/bin/env python3
"""Grenade throw, bounce, roll and fuse timing. Writes throw.json (tables, calibration and reference runs).

    python3 throw/sim.py            # from assets/grenades/
    node throw/test.js              # the browser runtime against these tables and the published figures

Frame: metres, seconds, +Y up, the ground is y = 0. A grenade is a point mass with quadratic drag and a contact
radius; spin is not simulated. Sources: data/grenades.json (FM 3-23.30 tables) for weight, throwing distance and
delay windows; everything marked EST or GAME below is an estimate or game tuning and says so in throw.json.
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, '..', 'data', 'grenades.json')))
G, RHO, DT = 9.80665, 1.225, 1.0 / 240.0          # standard gravity, ISA sea-level air density, fixed step
THROW = dict(angle_deg=40.0, height_m=1.8)        # EST: standing overhand throw; FM 3-23.30 gives distances, not release conditions
REST_SPEED = 0.35                                 # GAME: a rebound slower than this (m/s) becomes a roll
# EST: restitution e, sliding friction mu, rolling resistance mu_r (for a sphere). Labelled estimates, not measurements.
SURFACES = dict(
    concrete=dict(e=0.50, mu=0.45, mu_r=0.05), packed_dirt=dict(e=0.30, mu=0.55, mu_r=0.12), grass=dict(e=0.20, mu=0.60, mu_r=0.25),
    sand=dict(e=0.05, mu=0.70, mu_r=0.60), mud=dict(e=0.02, mu=0.80, mu_r=0.90), wood_floor=dict(e=0.45, mu=0.40, mu_r=0.06),
    steel_plate=dict(e=0.55, mu=0.35, mu_r=0.04))
ROLL_FACTOR = dict(sphere=1.0, cylinder=3.0, hex=4.0)   # EST: a can tumbles end over end, the hexagon ends stop a roll sooner
CD = dict(sphere=0.47, cylinder=0.80)                   # EST: smooth sphere below the drag crisis; tumbling short cylinder (Hoerner, Fluid-Dynamic Drag)

def mulberry32(seed):
    a = seed & 0xFFFFFFFF
    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF; t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rnd

def body(key):
    v = DATA['variants'][key]; s = v['shape']; m = v['weight_oz'] * DATA['oz_to_kg']; r = s['diameter_mm'] / 2000.0
    if s['kind'] == 'sphere': area = math.pi * r * r; cd = CD['sphere']; roll = ROLL_FACTOR['sphere']
    else:
        L = s['length_mm'] / 1000.0; area = (2 * math.pi * r * r + 2 * math.pi * r * L) / 4.0      # mean projected area of a tumbling convex body = surface / 4 (Cauchy)
        cd = CD['cylinder']; roll = ROLL_FACTOR['hex' if key == 'flash' else 'cylinder']
    return dict(mass_kg=m, radius_m=r, cd=cd, area_m2=area, k=RHO * cd * area / (2 * m), roll_factor=roll)

def acc(v, k):
    s = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return [-k * s * v[0], -G - k * s * v[1], -k * s * v[2]]

def rk4(p, v, k, dt):
    a1 = acc(v, k); v2 = [v[i] + a1[i] * dt / 2 for i in range(3)]
    a2 = acc(v2, k); v3 = [v[i] + a2[i] * dt / 2 for i in range(3)]
    a3 = acc(v3, k); v4 = [v[i] + a3[i] * dt for i in range(3)]
    a4 = acc(v4, k)
    p1 = [p[i] + dt * (v[i] + 2 * v2[i] + 2 * v3[i] + v4[i]) / 6 for i in range(3)]
    v1 = [v[i] + dt * (a1[i] + 2 * a2[i] + 2 * a3[i] + a4[i]) / 6 for i in range(3)]
    return p1, v1

def simulate(b, p, v, surface, t_max=30.0, first_only=False):
    """Fly, bounce on the ground plane y = 0 and roll to rest. Returns events and 0.1 s samples."""
    sf = SURFACES[surface]; rc = b['radius_m']; t = 0.0; mode = 'air'; ev = []; samples = []; apex = p[1]; n = 0
    while t < t_max and mode != 'rest':
        if n % 24 == 0: samples.append([round(t, 6)] + [round(x, 6) for x in p])
        n += 1
        if mode == 'air':
            p1, v1 = rk4(p, v, b['k'], DT); s0, s1 = p[1] - rc, p1[1] - rc
            if s1 < 0 <= s0:
                f = s0 / (s0 - s1); p = [p[i] + (p1[i] - p[i]) * f for i in range(3)]; v = [v[i] + (v1[i] - v[i]) * f for i in range(3)]; t += f * DT
                vn = v[1]; vt = [v[0], 0.0, v[2]]; vtl = math.hypot(vt[0], vt[2]); jn = -(1 + sf['e']) * vn
                ev.append(dict(type='bounce', t=t, pos=list(p), speed=math.sqrt(vn * vn + vtl * vtl), normal_speed=-vn, surface=surface))
                keep = max(0.0, 1.0 - sf['mu'] * jn / vtl) if vtl > 1e-9 else 0.0
                up = -sf['e'] * vn; v = [vt[0] * keep, up, vt[2] * keep]; p[1] = rc
                if first_only: return ev, samples, apex
                if up < REST_SPEED: mode = 'roll'; v[1] = 0.0
            else:
                p, v = p1, v1; t += DT; apex = max(apex, p[1])
        else:
            s = math.hypot(v[0], v[2]); a = sf['mu_r'] * b['roll_factor'] * G; s1 = max(0.0, s - a * DT)
            if s > 1e-12:
                d = (s + s1) / 2 * DT; p = [p[0] + v[0] / s * d, p[1], p[2] + v[2] / s * d]; v = [v[0] / s * s1, 0.0, v[2] / s * s1]
            t += DT
            if s1 <= 0.0: mode = 'rest'; ev.append(dict(type='rest', t=t, pos=list(p)))
    return ev, samples, apex

def launch(speed, angle_deg, height):
    a = math.radians(angle_deg); return [0.0, height, 0.0], [speed * math.cos(a), speed * math.sin(a), 0.0]

def first_landing(b, speed):
    p, v = launch(speed, THROW['angle_deg'], THROW['height_m']); ev, _, apex = simulate(b, p, v, 'packed_dirt', first_only=True)
    return ev[0]['pos'][0], ev[0]['t'], apex

def calibrate(b, dist):
    lo, hi = 5.0, 60.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if first_landing(b, mid)[0] < dist: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def sample_delay(win, rnd): return win[0] + (win[1] - win[0]) * (rnd() + rnd()) / 2          # GAME: triangular inside the published window
def sample_burn(v, rnd):
    a, b = v['burn_s']
    if 'burn_mean_s' in v:                                                                    # published mean -> a power law with that mean
        kpow = (b - a) / (v['burn_mean_s'] - a) - 1.0; return a + (b - a) * rnd() ** kpow
    return a + (b - a) * (rnd() + rnd()) / 2

def main():
    out = dict(_doc='Written by throw/sim.py. Published figures from data/grenades.json (FM 3-23.30); EST = estimate, GAME = game tuning.',
               constants=dict(g=G, air_density=RHO, dt=DT, rest_speed=REST_SPEED, throw=THROW,
                              notes=dict(throw='EST: release 40 deg above the horizon from 1.8 m; the FM publishes distances only',
                                         distance='taken to the first landing on level ground', surfaces='EST', rest_speed='GAME', drag='EST (Cd) on measured exterior size and published weight')),
               surfaces=SURFACES, variants={}, checks=[])
    ok = True
    for key, v in DATA['variants'].items():
        b = body(key); vref = calibrate(b, v['throw_m']); dist, tof, apex = first_landing(b, vref)
        vac = vref * math.cos(math.radians(40)) * (vref * math.sin(math.radians(40)) + math.sqrt((vref * math.sin(math.radians(40))) ** 2 + 2 * G * (1.8 - b['radius_m']))) / G
        ref = {}
        for sname in ('packed_dirt', 'concrete', 'grass'):
            p, vel = launch(vref, THROW['angle_deg'], THROW['height_m']); ev, samples, _ = simulate(b, p, vel, sname)
            ref[sname] = dict(bounces=sum(1 for e in ev if e['type'] == 'bounce'), rest=ev[-1], first_bounce=ev[0], samples=samples if sname == 'packed_dirt' else None)
        e = dict(body=b, release_speed_mps=vref, published_throw_m=v['throw_m'], sim_first_landing_m=dist, time_of_flight_s=tof, apex_m=apex,
                 vacuum_distance_m=vac, kinetic_energy_J=0.5 * b['mass_kg'] * vref ** 2, reference=ref)
        if 'delay_s' in v:
            rnd = mulberry32(1234); ds = [sample_delay(v['delay_s'], rnd) for _ in range(20000)]
            e['delay_window_s'] = v['delay_s']; e['delay_stats'] = dict(n=len(ds), min=min(ds), max=max(ds), mean=sum(ds) / len(ds), first8=ds[:8])
            c = v['delay_s'][0] <= min(ds) and max(ds) <= v['delay_s'][1]; ok &= c
            out['checks'].append(dict(check=f'{key}: 20000 sampled delays inside the published window {v["delay_s"]} s', value=[min(ds), max(ds)], passed=c))
        if 'burn_s' in v:
            rnd = mulberry32(4321); bs = [sample_burn(v, rnd) for _ in range(20000)]
            e['burn_window_s'] = v['burn_s']; e['burn_mean_s'] = v.get('burn_mean_s'); e['burn_stats'] = dict(n=len(bs), min=min(bs), max=max(bs), mean=sum(bs) / len(bs), first8=bs[:8])
            c = v['burn_s'][0] <= min(bs) and max(bs) <= v['burn_s'][1]; ok &= c
            out['checks'].append(dict(check=f'{key}: 20000 sampled burn times inside the published window {v["burn_s"]} s', value=[min(bs), max(bs)], passed=c))
            if 'burn_mean_s' in v:
                c = abs(sum(bs) / len(bs) - v['burn_mean_s']) < 0.5; ok &= c
                out['checks'].append(dict(check=f'{key}: mean sampled burn time equals the published average {v["burn_mean_s"]} s within 0.5 s', value=sum(bs) / len(bs), passed=c))
        if 'game' in v: e['game'] = v['game']
        if 'throw_source' in v: e['throw_inferred'] = v['throw_source']
        c = abs(dist - v['throw_m']) < 0.01; ok &= c
        kind = 'inferred (Table A-5 publishes none)' if 'throw_source' in v else 'game-only' if key == 'impact' else 'published'
        out['checks'].append(dict(check=f'{key}: first landing equals the {kind} throwing distance {v["throw_m"]} m (release speed calibrated to it)', value=dist, passed=c))
        c = 14.0 < vref < 24.0; ok &= c
        out['checks'].append(dict(check=f'{key}: calibrated release speed is a human throw (14 to 24 m/s; plausibility band, EST)', value=vref, passed=c))
        out['variants'][key] = e
    # an independent check, not a calibration: throw the white can with the release energy calibrated on the coloured can
    s, w = out['variants']['smoke'], out['variants']['smoke-white']
    v_pred = math.sqrt(2 * s['kinetic_energy_J'] / w['body']['mass_kg']); d_pred = first_landing(w['body'], v_pred)[0]
    c = abs(d_pred - 30.0) < 1.0; ok &= c
    out['cross_check'] = dict(note='The coloured can (19 oz, 35 m) and the white can (24 oz, 30 m) are separate published rows. Giving the white can the release energy calibrated on the coloured can predicts its distance.',
                              smoke_energy_J=s['kinetic_energy_J'], white_energy_J=w['kinetic_energy_J'], frag_energy_J=out['variants']['frag']['kinetic_energy_J'],
                              white_predicted_m=d_pred, white_published_m=30, limit='The lighter frag and flash are released with less energy (69 J and 72 J): a light object is limited by arm speed, not by work, so this rule only links the two heavy cans.')
    out['checks'].append(dict(check='smoke-white: distance predicted from the coloured can at equal release energy is within 1 m of the published 30 m', value=d_pred, passed=c))
    out['all_passed'] = ok
    json.dump(out, open(os.path.join(HERE, 'throw.json'), 'w'), indent=1)
    for key, e in out['variants'].items():
        print(f"{key:12s} v0 {e['release_speed_mps']:.2f} m/s  lands {e['sim_first_landing_m']:.2f} m (published {e['published_throw_m']})  tof {e['time_of_flight_s']:.2f} s  apex {e['apex_m']:.1f} m  rest on dirt {e['reference']['packed_dirt']['rest']['pos'][0]:.1f} m, concrete {e['reference']['concrete']['rest']['pos'][0]:.1f} m")
    print('white can predicted from equal energy:', round(out['cross_check']['white_predicted_m'], 2), 'm;', 'all passed' if ok else 'FAILED')

if __name__ == '__main__':
    main()
