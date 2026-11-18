#!/usr/bin/env python3
"""Game-level effects: frag damage falloff, flash blind and deafen, smoke plume. Writes effects.json.

    python3 effects/sim.py          # from assets/grenades/
    node effects/test.js            # the browser runtime against these tables

Everything here is what a player sees, hears and feels, anchored on the published effect figures in
data/grenades.json (FM 3-23.30): radii, candlepower, decibels at 5 ft, burn times. Nothing models how a device
produces them. GAME marks game tuning, PUB a published figure, EST an estimate.
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, '..', 'data', 'grenades.json')))['variants']

# ---------------------------------------------------------------- frag: damage against distance
FRAG = dict(
    killing_radius_m=DATA['frag']['killing_radius_m'], casualty_radius_m=DATA['frag']['casualty_radius_m'],     # PUB: 5 m and 15 m
    lethal_damage=100.0,        # GAME: damage at the killing radius = a full-health player
    centre_damage=400.0,        # GAME: damage at the centre
    casualty_damage=25.0,       # GAME: damage at the casualty radius (a wound)
    zero_radius_m=20.0,         # GAME: no damage beyond this. The FM warns fragments can travel 230 m; the game ignores that tail
    prone_factor=0.5,           # GAME: lying down outside the killing radius
    cover_factor=0.0,           # GAME: no line of sight to the grenade
    sound_peak_db_at_5ft=175.0, # GAME: the FM gives no sound level for the frag; the middle of the stun grenade's published 170..180 dB is borrowed
)
def frag_damage(r, P=FRAG):
    rk, rc, rz = P['killing_radius_m'], P['casualty_radius_m'], P['zero_radius_m']
    if r <= rk: return P['lethal_damage'] * (P['centre_damage'] / P['lethal_damage']) ** ((rk - r) / rk)
    if r <= rc: return P['lethal_damage'] * (P['casualty_damage'] / P['lethal_damage']) ** ((r - rk) / (rc - rk))
    if r < rz: return P['casualty_damage'] * (rz - r) / (rz - rc)
    return 0.0

# ---------------------------------------------------------------- flash: blind and deafen by distance and view angle
FT5 = 5 * 0.3048
FLASH = dict(
    candela=float(DATA['flash']['flash_candlepower_min']),      # PUB: "over one million candlepower" (1 candlepower ~ 1 candela); the lower bound is used
    bang_db_at_5ft=DATA['flash']['bang_db_at_5ft'], bang_db_default=175.0,   # PUB window 170..180 dB at 5 ft; the middle by default
    ref_distance_m=FT5, effect_radius_m=float(DATA['flash']['effect_radius_m']),   # PUB: effects within 9 m
    hearing_threshold_db=140.0,   # PUB: 140 dB peak, the unprotected impulse-noise limit of OSHA 29 CFR 1910.95 and MIL-STD-1474
    ambient_lux=dict(night=50.0, indoor=300.0, day=2000.0),     # EST: typical illuminance levels; the flash stops mattering once it adds less than this
    view_full_deg=30.0, view_edge_deg=100.0, view_behind=0.05,  # GAME: full effect inside 30 deg of the view axis, tapering to 5 % at the edge of the visual field (~100 deg, PUB) and behind
    whiteout_s=(0.5, 4.5), afterimage_s=(2.0, 6.0),             # GAME: whiteout = 0.5 + 4.5 * severity seconds, then an afterimage fading over 2 + 6 * severity
    deaf_s=(2.0, 8.0),                                          # GAME: ringing and muffled hearing for 2 + 8 * severity seconds
    wall_db=15.0, occluded_flash=0.02,                          # GAME: no line of sight
)
def spl(r, db0=None, P=FLASH): return (P['bang_db_default'] if db0 is None else db0) - 20 * math.log10(max(r, 0.05) / P['ref_distance_m'])
def illuminance(r, P=FLASH): return P['candela'] / max(r, 0.05) ** 2
def view_factor(deg, P=FLASH):
    a, b = P['view_full_deg'], P['view_edge_deg']
    if deg <= a: return 1.0
    if deg >= b: return P['view_behind']
    return P['view_behind'] + (1 - P['view_behind']) * (0.5 + 0.5 * math.cos(math.pi * (deg - a) / (b - a)))
def flash_effect(r, view_deg=0.0, ambient='indoor', occluded=False, protection_db=0.0, db0=None, P=FLASH):
    e0 = P['ambient_lux'][ambient]; e9 = illuminance(P['effect_radius_m'], P)
    e = illuminance(r, P) * view_factor(view_deg, P) * (P['occluded_flash'] if occluded else 1.0)
    sb = min(1.0, max(0.0, math.log10(e / e0) / math.log10(e9 / e0))) if e > e0 else 0.0
    L = spl(r, db0, P) - protection_db - (P['wall_db'] if occluded else 0.0); L9 = spl(P['effect_radius_m'], db0, P)
    sd = min(1.0, max(0.0, (L - P['hearing_threshold_db']) / (L9 - P['hearing_threshold_db'])))
    return dict(lux=e, blind=sb, whiteout_s=(P['whiteout_s'][0] + P['whiteout_s'][1] * sb) if sb > 0 else 0.0, afterimage_s=(P['afterimage_s'][0] + P['afterimage_s'][1] * sb) if sb > 0 else 0.0,
                spl_db=L, deafen=sd, deaf_s=(P['deaf_s'][0] + P['deaf_s'][1] * sd) if sd > 0 else 0.0)

# ---------------------------------------------------------------- smoke: emission over the burn, puffs drifting on the wind, obscuration
SMOKE = dict(
    puff_interval_s=0.5, ramp_up_s=1.5, ramp_down_s=3.0,        # GAME
    yield_m2=dict(smoke=2400.0, **{'smoke-white': 7500.0}),      # GAME: total extinction area. Coloured: tuned so the plateau plume is opaque (optical depth 4) across a 2 m wide plume in a 2 m/s wind; white is "dense" (FM) so more
    sigma0_m=0.25, diffusivity=(0.15, 0.10),                    # GAME: puff size^2 = sigma0^2 + 2 K age, K = 0.15 + 0.10 * wind speed (m^2/s)
    rise_mps=1.0, rise_tau_s=4.0,                               # GAME: warm smoke rises about 4 m in all
    lifetime_s=45.0,                                            # GAME: a puff thins out with this time constant
    opaque_optical_depth=4.0,
)
def emission(t, burn, P=SMOKE):
    """Fraction of the whole output per second, t seconds after ignition. Integrates to 1 over the burn."""
    if t < 0 or t > burn: return 0.0
    plateau = 1.0 / (burn - 0.5 * P['ramp_up_s'] - 0.5 * P['ramp_down_s'])
    if t < P['ramp_up_s']: return plateau * t / P['ramp_up_s']
    if t > burn - P['ramp_down_s']: return plateau * (burn - t) / P['ramp_down_s']
    return plateau
def emitted(t0, t1, burn, P=SMOKE, n=20):
    h = (t1 - t0) / n; return sum((emission(t0 + i * h, burn, P) + emission(t0 + (i + 1) * h, burn, P)) / 2 * h for i in range(n))

class Plume:
    def __init__(self, key, burn, origin=(0, 0.06, 0), wind=(2, 0, 0), P=SMOKE):
        self.P = P; self.Y = P['yield_m2'][key]; self.burn = burn; self.o = origin; self.wind = wind; self.t = 0.0; self.puffs = []; self.next = 0.0
        self.K = P['diffusivity'][0] + P['diffusivity'][1] * math.hypot(*wind)
    def step(self, dt):
        P = self.P; t1 = self.t + dt
        while self.next < t1 and self.next < self.burn:
            a, b = self.next, min(self.next + P['puff_interval_s'], self.burn)
            self.puffs.append(dict(born=(a + b) / 2, m0=self.Y * emitted(a, b, self.burn, P), o=tuple(self.o))); self.next += P['puff_interval_s']   # a puff starts where the grenade is at that moment
        self.t = t1
        for p in self.puffs:
            age = max(0.0, self.t - p['born']); rise = P['rise_mps'] * P['rise_tau_s'] * (1 - math.exp(-age / P['rise_tau_s']))
            p['pos'] = [p['o'][0] + self.wind[0] * age, p['o'][1] + self.wind[1] * age + rise, p['o'][2] + self.wind[2] * age]
            p['sigma'] = math.sqrt(P['sigma0_m'] ** 2 + 2 * self.K * age); p['m'] = p['m0'] * math.exp(-age / P['lifetime_s'])
    def optical_depth(self, a, b):
        d = [b[i] - a[i] for i in range(3)]; L = math.sqrt(sum(x * x for x in d)); u = [x / L for x in d]; tau = 0.0
        for p in self.puffs:
            if 'pos' not in p: continue
            w = [p['pos'][i] - a[i] for i in range(3)]; s = sum(w[i] * u[i] for i in range(3)); d2 = max(0.0, sum(x * x for x in w) - s * s); sg = p['sigma']
            tau += p['m'] / (2 * math.pi * sg * sg) * math.exp(-d2 / (2 * sg * sg)) * 0.5 * (math.erf((L - s) / (sg * math.sqrt(2))) + math.erf(s / (sg * math.sqrt(2))))
        return tau
    def transmission(self, a, b): return math.exp(-self.optical_depth(a, b))

def main():
    out = dict(_doc='Written by effects/sim.py. PUB = published (FM 3-23.30 via data/grenades.json, or as named), GAME = game tuning, EST = estimate. See effects/README.md.',
               frag=FRAG, flash=FLASH, smoke=SMOKE, colours={k: v['colours'] for k, v in DATA.items() if 'colours' in v}, checks=[], reference={})
    ok = True
    def chk(text, value, passed):
        nonlocal ok; ok &= bool(passed); out['checks'].append(dict(check=text, value=value, passed=bool(passed)))
    # frag
    chk('frag: damage at the published 5 m killing radius is exactly lethal (100)', frag_damage(5.0), abs(frag_damage(5.0) - 100) < 1e-9)
    chk('frag: damage at the published 15 m casualty radius equals the wound threshold (25)', frag_damage(15.0), abs(frag_damage(15.0) - 25) < 1e-9)
    rs = [i * 0.25 for i in range(0, 101)]; ds = [frag_damage(r) for r in rs]
    chk('frag: damage never rises with distance, lethal everywhere inside 5 m, zero from 20 m', [ds[0], ds[-1]], all(a >= b for a, b in zip(ds, ds[1:])) and all(d >= 100 for r, d in zip(rs, ds) if r <= 5) and frag_damage(20.0) == 0)
    out['reference']['frag'] = [[r, frag_damage(r)] for r in (0, 1, 2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20, 30)]
    # flash
    chk('flash: bang at 5 ft is inside the published 170..180 dB', spl(FT5), 170 <= spl(FT5) <= 180)
    chk('flash: 1,000,000 cd gives 1,000,000 lux at 1 m', illuminance(1.0), abs(illuminance(1.0) - 1e6) < 1e-6)
    for amb in FLASH['ambient_lux']:
        e = flash_effect(9.0, 0, amb); e2 = flash_effect(9.5, 0, amb)
        chk(f'flash ({amb}): blind and deafen are both at full strength at the published 9 m radius and weaker beyond', [e['blind'], e['deafen'], e2['blind'], e2['deafen']],
            abs(e['blind'] - 1) < 1e-9 and abs(e['deafen'] - 1) < 1e-9 and e2['blind'] < 1 and e2['deafen'] < 1)
    f = [flash_effect(5.0, a, 'indoor')['blind'] for a in (0, 30, 60, 90, 120, 180)]
    chk('flash: blinding falls as the player looks away (0, 30, 60, 90, 120, 180 deg at 5 m indoors)', f, all(a >= b for a, b in zip(f, f[1:])) and f[0] > f[-1])
    r140 = FT5 * 10 ** ((175 - 140) / 20)
    chk('flash: deafen ends where the bang falls to the 140 dB limit (free field)', r140, flash_effect(r140 * 1.01)['deafen'] == 0 and flash_effect(r140 * 0.9)['deafen'] > 0)
    out['reference']['flash'] = [dict(r=r, view_deg=a, ambient=amb, occluded=oc, protection_db=pr, **flash_effect(r, a, amb, oc, pr))
                                 for r in (1, 3, 9, 15, 30, 80) for a in (0, 45, 90, 170) for amb in ('night', 'indoor', 'day') for oc, pr in ((False, 0.0), (True, 0.0), (False, 25.0))]
    out['flash_radii_m'] = dict(deafen_free_field=r140, blind_facing={k: math.sqrt(FLASH['candela'] / v) for k, v in FLASH['ambient_lux'].items()})
    # smoke
    for key, burn in (('smoke', 60.0), ('smoke-white', 127.5)):
        tot = emitted(0, burn, burn, n=4000)
        chk(f'{key}: the emission curve integrates to 1 over a {burn} s burn', tot, abs(tot - 1) < 1e-6)
        pl = Plume(key, burn, wind=(2, 0, 0)); samples = []
        while pl.t < burn + 20:
            pl.step(0.25)
            if abs(pl.t % 10) < 1e-9 or abs(pl.t % 10 - 10) < 1e-9:
                samples.append(dict(t=round(pl.t, 3), puffs=len(pl.puffs), across_10m=pl.optical_depth((10, 2.5, -30), (10, 2.5, 30)), along=pl.transmission((-5, 1.6, 0), (40, 1.6, 0)), clear=pl.transmission((-5, 1.6, 15), (40, 1.6, 15))))
        m0 = sum(p['m0'] for p in pl.puffs)
        chk(f'{key}: the puffs carry the whole yield ({SMOKE["yield_m2"][key]} m2)', m0, abs(m0 - SMOKE['yield_m2'][key]) < 1e-6 * SMOKE['yield_m2'][key])
        last = pl.puffs[-1]; age = pl.t - last['born']
        chk(f'{key}: a puff drifts downwind at the wind speed (2 m/s)', last['pos'][0] / age, abs(last['pos'][0] / age - 2.0) < 1e-9)
        chk(f'{key}: emission stops at the end of the burn (last puff born before {burn} s)', last['born'], last['born'] <= burn)
        out['reference'][key] = dict(burn=burn, wind=[2, 0, 0], dt=0.25, samples=samples)
    # one puff against the closed form: a line through the centre of a Gaussian puff has optical depth m / (2 pi sigma^2)
    pl = Plume('smoke', 60.0, wind=(0, 0, 0)); pl.step(0.25); p = pl.puffs[0]; an = p['m'] / (2 * math.pi * p['sigma'] ** 2); nu = pl.optical_depth((-50, p['pos'][1], 0), (50, p['pos'][1], 0))
    chk('smoke: optical depth through one puff matches the closed form m / (2 pi sigma^2)', [nu, an], abs(nu - an) < 1e-9 * an)
    # the tuning target: optical depth 4 across the plateau plume where it is 2 m wide (sigma = 2 m), 2 m/s wind, 60 s burn
    pl = Plume('smoke', 60.0, wind=(2, 0, 0))
    while pl.t < 30: pl.step(0.25)
    age = (2.0 ** 2 - SMOKE['sigma0_m'] ** 2) / (2 * pl.K); x = 2.0 * age; rise = SMOKE['rise_mps'] * SMOKE['rise_tau_s'] * (1 - math.exp(-age / SMOKE['rise_tau_s']))
    tau = pl.optical_depth((x, 0.06 + rise, -60), (x, 0.06 + rise, 60)); tau_nodecay = tau / math.exp(-age / SMOKE['lifetime_s'])
    chk('smoke: optical depth across the plateau plume where sigma = 2 m, before thinning, is the tuning target of 4 (within 10 %)', [tau_nodecay, tau], abs(tau_nodecay - 4.0) < 0.4)
    out['all_passed'] = ok
    json.dump(out, open(os.path.join(HERE, 'effects.json'), 'w'), indent=1)
    for c in out['checks']: print('ok  ' if c['passed'] else 'FAIL', c['check'], '->', c['value'])
    print('all passed' if ok else 'FAILED')

if __name__ == '__main__':
    main()
