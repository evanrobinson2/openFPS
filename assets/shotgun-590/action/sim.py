#!/usr/bin/env python3
"""Action and recoil of the shotgun-590 asset: the shot inside the barrel, the recoil it puts into a shooter, the
pump stroke with its events, and the flight of the ejected hull.

    python3 action/sim.py        # writes action.json and plots/

Lumped-parameter physics: a few ordinary differential equations. What the manual says about the mechanism is used
as written (pages in MANUAL below); everything the manual does not give is marked inferred or guess in PARAMS.
Nothing here describes how to build or alter a firearm: it is timing and motion for a game to play back.
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IN, FT, GR, LB = 0.0254, 0.3048, 64.79891e-6, 0.45359237
MODEL = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
MP = MODEL['params']

def P(value, unit, basis, source): return dict(value=value, unit=unit, basis=basis, source=source)
PARAMS = dict(
    bore_d=P(0.0185, 'm', 'published', 'nominal 12 gauge bore, 18.5 mm (0.729 in)'),
    barrel_length=P(20 * IN, 'm', 'published', 'maker\'s specification for the 20 in model (notes/REFERENCES.md)'),
    test_barrel_length=P(30 * IN, 'm', 'inferred', 'published shotshell velocities are taken to be 30 in test-barrel figures (industry practice; the load pages do not say)'),
    gun_mass=P(7.25 * LB, 'kg', 'published', 'maker\'s specification, 7.25 lb unloaded'),
    shell_mass=P(0.045, 'kg', 'guess', 'one loaded 2 3/4 in shell: payload + wad + charge + about 9 g of hull and head'),
    payload_start=P(0.025, 'm', 'guess', 'distance from the breech face to the base of the wad before firing'),
    chamber_len_equiv=P(0.030, 'm', 'guess', 'gas volume behind the wad at shot start, as a length of bore'),
    gamma=P(1.25, '-', 'inferred', 'ratio of specific heats of propellant gas, a usual textbook value'),
    p_peak=P(62.0e6, 'Pa', 'guess', 'peak pressure of the fitting curve, 9,000 psi (the tracks scale it up by about 14 % so the 20 in barrel delivers the published speed): below the 11,500 psi maximum average pressure of the industry standard for 12 gauge 2 3/4 in (figure recalled from ANSI/SAAMI Z299.2, not re-read)'),
    p_start=P(5.0e6, 'Pa', 'guess', 'pressure at which the payload starts to move'),
    gas_velocity_factor=P(1.5, '-', 'published', 'SAAMI "Gun Recoil Formulae" (2018): propellant gas leaves at 1.5 x muzzle velocity for shotguns of average barrel length'),
    lock_time=P(0.006, 's', 'guess', 'sear release to ignition; the manual gives no figure'),
    stroke=P(MP['stroke'] * 1e-3, 'm', 'inferred', 'forend lip to receiver face in the profile photo is 103 mm; 100 mm used (model/build.py)'),
    lost_motion=P(MP['lost_motion'] * 1e-3, 'm', 'guess', 'slide travel that unlocks the bolt before the bolt moves'),
    hull_fired_len=P(2.75 * IN, 'm', 'published', 'a 2 3/4 in shell is 2 3/4 in long after firing (the nominal length)'),
    shell_loaded_len=P(MODEL['shell']['length'] * 1e-3, 'm', 'guess', 'typical loaded length of a 2 3/4 in shell'),
    tube_capacity=P(8, 'shells', 'published', 'maker\'s specification: 9 rounds in all with 2 3/4 in shells, one of them chambered; manual p8: one fewer with 3 in shells'),
    stroke_time_back=P(0.14, 's', 'guess', 'game tuning: a brisk rearward stroke'),
    stroke_dwell=P(0.02, 's', 'guess', 'game tuning'),
    stroke_time_forward=P(0.16, 's', 'guess', 'game tuning: a brisk forward stroke'),
    stroke_exponent=P(1.6, '-', 'guess', 'slide position = stroke x (t / T)^1.6: the hand accelerates into the stop'),
)
LOADS = dict(
    buck00=dict(name='00 buckshot, nine pellets, 2 3/4 in', payload=9 * math.pi / 6 * (0.33 * IN) ** 3 * 11350.0, wad=0.0035, charge=0.00175, v_pub=1325 * FT,
                source=dict(payload='published: Federal Power-Shok F127 00, nine lead .33 in pellets at 11.35 g/cc = 31.5 g', v_pub='published: the same page, 1325 ft/s',
                            wad='guess: wad and buffer', charge='guess: a typical charge for this class of load; makers do not publish it')),
    slug=dict(name='1 oz rifled slug, 2 3/4 in', payload=438 * GR, wad=0.0020, charge=0.0022, v_pub=1610 * FT,
              source=dict(payload='published: Federal Power-Shok F127 RS, 438 gr', v_pub='published: the same page, 1610 ft/s', wad='guess', charge='guess')),
)
MANUAL = {
    'safety': 'p5: the button on the top rear of the receiver; rearward is ON (SAFE), forward is OFF (FIRE). p20: with the safety ON the hammer does not fall when the trigger is pulled',
    'action_lock': 'p6: the action lock lever, left side behind the trigger guard, lets the action be opened without pulling the trigger. p9: it must be depressed to eject an unfired shell',
    'loading': 'p8: open the action and put the first shell through the ejection port (into the chamber or onto the elevator), then close it. p9: load the magazine with the action closed, pushing each shell in until its rim snaps past the cartridge stop',
    'cycling': 'p9: pulling the forearm completely rearward ejects the case through the ejection port. p10: pulling it completely rearward releases the next shell onto the elevator; pushing it fully forward chambers the shell',
    'unloading': 'p10: with the action closed, depressing the cartridge stop through the loading port releases shells from the magazine one at a time',
    'function_test': 'p20: safety ON, pull: no fire. Release, safety OFF: no fire. Pull: the hammer falls. Open the action, safety ON',
    'takedown': 'pp. 10 to 14: magazine cap and barrel; trigger housing pin and housing; cartridge interrupter and stop; bolt slide; bolt; elevator; forearm and action slide',
}
STANCES = dict(   # shooter coupling, all guesses tuned to look right: see README "Limits"
    shoulder=dict(body_mass=5.0, pad_k=40e3, pad_c=250.0, body_k=2500.0, body_zeta=0.9, arm=None, pitch_k=120.0, pitch_zeta=0.9),
    hip=dict(body_mass=3.0, pad_k=25e3, pad_c=200.0, body_k=1200.0, body_zeta=0.8, arm=0.070, pitch_k=70.0, pitch_zeta=0.8),
)
V = lambda k: PARAMS[k]['value']
AREA = math.pi / 4 * V('bore_d') ** 2

# ----------------------------------------------------------------------------- the shot inside the barrel
def pressure(x, x_pk):
    """base pressure against payload travel x: a linear rise to the peak at x_pk, then adiabatic expansion"""
    if x < x_pk: return V('p_start') + (V('p_peak') - V('p_start')) * x / x_pk
    x0 = V('chamber_len_equiv'); return V('p_peak') * ((x_pk + x0) / (x + x0)) ** V('gamma')

def work(x_end, x_pk, n=4000):
    xs = np.linspace(0, x_end, n); return float(np.trapezoid([pressure(x, x_pk) for x in xs], xs)) * AREA

def solve_load(L):
    m_eff = L['payload'] + L['wad'] + L['charge'] / 3            # Lagrange: a third of the charge moves with the payload
    travel_test = V('test_barrel_length') - V('payload_start'); travel = V('barrel_length') - V('payload_start')
    need = 0.5 * m_eff * L['v_pub'] ** 2
    lo, hi = 0.002, 0.4
    for _ in range(60):
        mid = (lo + hi) / 2; lo, hi = (mid, hi) if work(travel_test, mid) < need else (lo, mid)
    x_pk = (lo + hi) / 2
    v_barrel = math.sqrt(2 * work(travel, x_pk) / m_eff)
    return m_eff, x_pk, travel, v_barrel

def shot(L, use_published_velocity=True, dt=5e-6):
    """time history from ignition: payload travel, speed, pressure, and the force the shot puts on the gun"""
    m_eff, x_pk, travel, v_barrel = solve_load(L)
    scale = (L['v_pub'] / v_barrel) ** 2 if use_published_velocity else 1.0     # the game's muzzle velocity is the published one: scale the curve to deliver it in this barrel
    m_e = L['payload'] + L['wad']; m_mom = m_e + L['charge'] / 2
    t = x = v = 0.0; T, X, Vv, Pp, F = [], [], [], [], []
    while x < travel:
        p = pressure(x, x_pk) * scale; a = AREA * p / m_eff
        T.append(t); X.append(x); Vv.append(v); Pp.append(p); F.append(m_mom * a)
        v += a * dt; x += v * dt; t += dt
    v_m, t_exit, p_exit = v, t, pressure(travel, x_pk) * scale
    j_gas = L['charge'] * (V('gas_velocity_factor') * v_m - v_m / 2)            # what the gas still has to deliver after the payload leaves
    f_exit = AREA * p_exit; tau = j_gas / f_exit
    while t < t_exit + 8 * tau:
        T.append(t); X.append(travel); Vv.append(v_m); Pp.append(p_exit * math.exp(-(t - t_exit) / tau)); F.append(f_exit * math.exp(-(t - t_exit) / tau)); t += dt
    return dict(t=np.array(T), x=np.array(X), v=np.array(Vv), p=np.array(Pp), f=np.array(F), dt=dt, t_exit=t_exit, v_muzzle=v_m, p_exit=p_exit, x_pk=x_pk, v_barrel_model=v_barrel, tau=tau, m_e=m_e)

# ----------------------------------------------------------------------------- mass properties from the model
def mass_properties():
    parts = {n: p for n, p in MODEL['parts'].items() if not n.startswith('shell_')}
    raw = sum(p['mass_g'] for p in parts.values()) * 1e-3; k = V('gun_mass') / raw
    m = np.array([p['mass_g'] * 1e-3 * k for p in parts.values()])
    z = np.array([sum(p['bbox_mm']['z']) / 2e3 for p in parts.values()]); y = np.array([sum(p['bbox_mm']['y']) / 2e3 for p in parts.values()])
    ext = np.array([((p['bbox_mm']['z'][1] - p['bbox_mm']['z'][0]) ** 2 + (p['bbox_mm']['y'][1] - p['bbox_mm']['y'][0]) ** 2) / 12e6 for p in parts.values()])
    zc, yc = float((m * z).sum() / m.sum()), float((m * y).sum() / m.sum())
    i_cg = float((m * ((z - zc) ** 2 + (y - yc) ** 2 + ext)).sum())
    return dict(model_volume_mass_kg=round(raw, 3), scale_to_published=round(k, 3), cg=[0.0, round(yc, 4), round(zc, 4)], inertia_pitch_cg=round(i_cg, 4),
                note='part masses are mesh volume x material density (model/inventory.json), scaled so the total is the published 7.25 lb; each part is a box of its bounding size at its bounding-box centre')

# ----------------------------------------------------------------------------- recoil into a shooter
def recoil(sh, stance, mp, n_shells=0, t_end=0.8, dt_out=1e-3):
    S = STANCES[stance]; m_g = V('gun_mass') + n_shells * V('shell_mass')
    sock = MODEL['sockets']; butt = sock['socket_shoulder']; grip = sock['socket_hand_right']
    piv = butt if S['arm'] is None else grip
    arm = -piv[1] * 1e-3                                           # bore axis above the reaction point
    d2 = (mp['cg'][1] - piv[1] * 1e-3) ** 2 + (mp['cg'][2] - piv[2] * 1e-3) ** 2
    i_p = mp['inertia_pitch_cg'] * m_g / V('gun_mass') + m_g * d2
    c_b = 2 * S['body_zeta'] * math.sqrt(S['body_k'] * (S['body_mass'] + m_g)); c_t = 2 * S['pitch_zeta'] * math.sqrt(S['pitch_k'] * i_p)
    dt = 2e-5; n = int(t_end / dt); zg = vg = zs = vs = th = om = 0.0; lock = V('lock_time')
    out = []; vmax = 0.0; step = int(round(dt_out / dt)); imp = 0.0
    for i in range(n + 1):
        t = i * dt; ts = t - lock; j = int(ts / sh['dt']) if ts >= 0 else -1
        f = float(sh['f'][j]) if 0 <= j < len(sh['f']) else 0.0
        if i % step == 0: out.append((zg * 1e3, math.degrees(th), k_force if i else 0.0))
        k_force = S['pad_k'] * (zg - zs) + S['pad_c'] * (vg - vs)
        ag = (f - k_force) / m_g; a_s = (k_force - S['body_k'] * zs - c_b * vs) / S['body_mass']; al = (f * arm - S['pitch_k'] * th - c_t * om) / i_p
        vg += ag * dt; zg += vg * dt; vs += a_s * dt; zs += vs * dt; om += al * dt; th += om * dt; vmax = max(vmax, vg); imp += f * dt
    o = np.array(out)
    return dict(z_mm=np.round(o[:, 0], 3).tolist(), pitch_up_deg=np.round(o[:, 1], 4).tolist(), shoulder_force_N=np.round(o[:, 2], 1).tolist(),
                peak_gun_speed=round(vmax, 3), impulse=round(imp, 4), pivot=[0.0, piv[1] * 1e-3, piv[2] * 1e-3], arm_m=round(arm, 4), inertia_about_pivot=round(i_p, 4), gun_mass=round(m_g, 3))

# ----------------------------------------------------------------------------- the pump stroke and its events
def cycle():
    S, lm = V('stroke'), V('lost_motion'); hull, shell = V('hull_fired_len'), V('shell_loaded_len')
    breech = MP['breech'] * 1e-3; lifter_head = -0.008 - shell                         # head of the shell lying on the elevator (model socket_lifter)
    ev_back = [
        ('unlock', lm, 'the bolt lock is down: the bolt starts to move', 'inferred'),
        ('hammer_cocked', lm + 0.030, 'the bolt slide has pushed the hammer back onto the sear', 'guess'),
        ('extracted', lm + hull, 'the fired hull\'s mouth is out of the chamber (hull length of bolt travel)', 'derived'),
        ('eject', lm + hull + 0.005, 'the hull meets the ejector and leaves through the port (manual p9)', 'inferred'),
        ('shell_released', S - 0.008, 'the cartridge stop lets the next shell onto the elevator (manual p10: "completely rearward")', 'manual'),
        ('rear_stop', S, 'the slide stops at the rear', 'traced'),
    ]
    pick = S - ((breech - lifter_head) - 0.0)                                           # slide travel at which the bolt face is at the shell head, less the lost motion
    ev_fwd = [
        ('lift_start', S, 'the elevator starts to rise as the slide starts forward', 'inferred'),
        ('lift_done', S - 0.030, 'the shell is in line with the chamber', 'guess'),
        ('feed', lm + (breech - lifter_head), 'the bolt face meets the shell head and pushes it forward', 'derived'),
        ('chambered', lm, 'the shell is home and the bolt stops', 'derived'),
        ('locked', 0.0, 'the bolt lock is up, the slide is forward, the action lock engages (manual p10: "fully forward")', 'manual'),
    ]
    te = V('stroke_exponent'); tb, td, tf = V('stroke_time_back'), V('stroke_dwell'), V('stroke_time_forward')
    def when(s, back): return tb * (s / S) ** (1 / te) if back else tb + td + tf * ((S - s) / S) ** (1 / te)
    def speed(s, back):
        T = tb if back else tf; u = (s / S) if back else ((S - s) / S); return te * S / T * max(u, 1e-9) ** (1 - 1 / te)
    events = [dict(name=n, direction='back', slide_mm=round(s * 1e3, 2), t=round(when(s, True), 4), slide_speed=round(speed(s, True), 3), what=w, basis=b) for n, s, w, b in ev_back]
    events += [dict(name=n, direction='forward', slide_mm=round(s * 1e3, 2), t=round(when(s, False), 4), slide_speed=round(speed(s, False), 3), what=w, basis=b) for n, s, w, b in ev_fwd]
    return dict(stroke_mm=S * 1e3, lost_motion_mm=lm * 1e3, bolt_travel_mm=(S - lm) * 1e3, events=events, duration=round(tb + td + tf, 4),
                profile=dict(back_s=tb, dwell_s=td, forward_s=tf, exponent=te, formula='back: s = S (t / Tb)^e. forward: s = S (1 - ((t - Tb - Td) / Tf)^e)'),
                kinematics=dict(bolt_lock_deg_unlocked=7.0, elevator_deg_raised=-MP['elevator_lift'], note='the same numbers as the model\'s pump clips (model/build.py)'))

# ----------------------------------------------------------------------------- the ejected hull
HULL = dict(mass=0.009, length=V('hull_fired_len'), radius=0.0102,
            side_factor=1.2, up_factor=0.35, back_factor=0.5, spin_factor=1.0, jitter=0.15, drag_k=0.012,
            surfaces=dict(concrete=dict(e=0.45, mu=0.5), dirt=dict(e=0.15, mu=0.8), grass=dict(e=0.1, mu=0.9), wood=dict(e=0.4, mu=0.45)),
            source='guess throughout (game tuning): the hull leaves sideways at about 1.2 x the slide speed, a little up and back, tumbling; restitution and friction by surface')

def rng(seed):                    # mulberry32, the same sequence as the JavaScript module
    s = seed & 0xFFFFFFFF
    def r():
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF; z = s
        z = ((z ^ (z >> 15)) * (z | 1)) & 0xFFFFFFFF
        z = (z ^ ((z + (((z ^ (z >> 7)) * (z | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return r

def eject_hull(r, slide_speed):
    j = lambda: 1 + HULL['jitter'] * (2 * r() - 1); p = MODEL['sockets']['socket_eject']
    return dict(pos=[p[0] * 1e-3, p[1] * 1e-3, p[2] * 1e-3], vel=[-HULL['side_factor'] * slide_speed * j(), HULL['up_factor'] * slide_speed * j(), -HULL['back_factor'] * slide_speed * j()],
                spin=HULL['spin_factor'] * slide_speed / (HULL['length'] / 2) * j(), resting=0)

def step_hull(c, dt, ground_y, surface, g=9.80665):
    """point-mass flight with a little drag; bounces on the plane y = ground_y; resting: 0 flying, 1 sliding, 2 at rest"""
    if c['resting'] == 2: return c
    s = HULL['surfaces'][surface]; v = c['vel']; sp = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    k = HULL['drag_k'] * sp
    v[0] -= k * v[0] * dt; v[1] -= (g + k * v[1]) * dt; v[2] -= k * v[2] * dt
    for i in range(3): c['pos'][i] += v[i] * dt
    floor = ground_y + HULL['radius']
    if c['pos'][1] <= floor:
        c['pos'][1] = floor
        if abs(v[1]) > 0.35:
            v[1] = -v[1] * s['e']; f = max(0.0, 1 - s['mu'] * 0.5); v[0] *= f; v[2] *= f; c['spin'] *= 0.5
        else:
            v[1] = 0.0; c['resting'] = 1; h = math.hypot(v[0], v[2]); dec = s['mu'] * g * dt
            if h <= dec: v[0] = v[2] = 0.0; c['resting'] = 2; c['spin'] = 0.0
            else: v[0] *= (h - dec) / h; v[2] *= (h - dec) / h
    return c

# ----------------------------------------------------------------------------- build
def main():
    mp = mass_properties(); cyc = cycle(); out = dict(
        units='SI: metres, seconds, kilograms, newtons, pascals unless a key says otherwise',
        frame='the model\'s: +Z towards the muzzle, +Y up, +X to the shooter\'s left; origin on the bore axis at the receiver front face',
        time_zero='the sear releasing the hammer (the trigger break); ignition follows after lock_time',
        params=PARAMS, loads=LOADS, manual=MANUAL, stances=STANCES, mass=mp, cycle=cyc, hull=HULL, shots={}, recoil=dict(dt=1e-3, loads={}), checks={})
    f = V('gas_velocity_factor'); chk = out['checks']
    for key, L in LOADS.items():
        sh = shot(L); m_e = sh['m_e']
        free_v = (m_e * sh['v_muzzle'] + L['charge'] * f * sh['v_muzzle']) / V('gun_mass'); free_e = 0.5 * V('gun_mass') * free_v ** 2
        dec = 4                                    # 20 microsecond samples
        out['shots'][key] = dict(dt=sh['dt'] * dec, t0=V('lock_time'), pressure_MPa=np.round(sh['p'][::dec] / 1e6, 3).tolist(), payload_travel_mm=np.round(sh['x'][::dec] * 1e3, 2).tolist(),
                                 payload_speed=np.round(sh['v'][::dec], 2).tolist(), gun_force_N=np.round(sh['f'][::dec], 1).tolist(),
                                 muzzle_velocity=round(sh['v_muzzle'], 2), barrel_time_ms=round(sh['t_exit'] * 1e3, 3), muzzle_pressure_MPa=round(sh['p_exit'] / 1e6, 3), peak_travel_mm=round(sh['x_pk'] * 1e3, 1),
                                 gas_tail_tau_ms=round(sh['tau'] * 1e3, 3), gas_energy_at_exit_J=round(sh['p_exit'] * AREA * (V('barrel_length') - V('payload_start') + V('chamber_len_equiv')) / (V('gamma') - 1), 1),
                                 free_recoil=dict(gun_speed=round(free_v, 3), energy_J=round(free_e, 2), energy_ftlb=round(free_e / 1.3558179, 2), momentum=round(free_v * V('gun_mass'), 3),
                                                  formula='SAAMI: gun mass x speed = ejecta mass x muzzle velocity + charge mass x 1.5 x muzzle velocity; gun unloaded, 7.25 lb'),
                                 barrel_20in_estimate=dict(muzzle_velocity=round(sh['v_barrel_model'], 1), ratio_to_published=round(sh['v_barrel_model'] / L['v_pub'], 3),
                                                           note='what this pressure curve gives in 20 in when fitted to the published speed in 30 in. A model estimate that depends on the guessed curve; not used for the tracks'))
        out['recoil']['loads'][key] = {st: recoil(sh, st, mp) for st in STANCES}
        imp = float(np.sum(sh['f']) * sh['dt']); want = m_e * sh['v_muzzle'] + L['charge'] * f * sh['v_muzzle']
        r = out['recoil']['loads'][key]
        chk[f'{key}_muzzle_velocity'] = dict(sim=round(sh['v_muzzle'], 2), published=round(L['v_pub'], 2), passed=abs(sh['v_muzzle'] - L['v_pub']) / L['v_pub'] < 0.005, note='a calibration: the pressure curve is scaled to deliver the published speed')
        chk[f'{key}_impulse'] = dict(force_integral=round(imp, 4), saami_momentum=round(want, 4), passed=abs(imp - want) / want < 0.01, note='the force on the gun integrates to the SAAMI recoil momentum')
        chk[f'{key}_peak_pressure'] = dict(peak_MPa=round(float(sh['p'].max()) / 1e6, 1), limit_MPa=79.3, passed=float(sh['p'].max()) < 79.3e6, note='below the 11,500 psi industry maximum average pressure (recalled figure)')
        for st in STANCES:
            chk[f'{key}_{st}_gun_speed'] = dict(peak=r[st]['peak_gun_speed'], free=round(free_v, 3), passed=0.75 * free_v < r[st]['peak_gun_speed'] <= free_v * 1.001, note='a held gun peaks a little under the free recoil speed')
            chk[f'{key}_{st}_settles'] = dict(z_mm_at_end=r[st]['z_mm'][-1], pitch_deg_at_end=r[st]['pitch_up_deg'][-1], passed=abs(r[st]['z_mm'][-1]) < 3.0 and abs(r[st]['pitch_up_deg'][-1]) < 0.3)
    ev = {e['name']: e for e in cyc['events']}
    chk['stroke_clears_hull'] = dict(bolt_travel_mm=cyc['bolt_travel_mm'], hull_2_75_mm=round(2.75 * IN * 1e3, 1), hull_3_mm=round(3 * IN * 1e3, 1), passed=cyc['bolt_travel_mm'] > 3 * IN * 1e3 + 5,
                                     note='the bolt travels further than a fired 3 in hull is long, as it must to eject one (manual p8: 3 in shells are allowed)')
    chk['event_order'] = dict(order=[e['name'] for e in cyc['events']], passed=all(a['t'] <= b['t'] for a, b in zip(cyc['events'], cyc['events'][1:])))
    tube_len = (MP['cap'][1] - MP['tube_z'][0]) * 1e-3 + 0.012; n_fit = int((tube_len - 0.045) // V('shell_loaded_len'))
    chk['tube_holds_published_capacity'] = dict(tube_inside_m=round(tube_len, 3), allowance_for_follower_and_spring_m=0.045, shells_that_fit=n_fit, published=V('tube_capacity'), passed=n_fit == V('tube_capacity'),
                                                note='modelled tube length (cartridge stop to the inside of the cap) less a guessed 45 mm for follower and compressed spring, over a 59 mm shell. An independent check of the photo ruler')
    r = rng(590); traj = []
    for i in range(4):
        sp = ev['eject']['slide_speed'] * (0.7 + 0.2 * i); c = eject_hull(r, sp); surf = ['concrete', 'dirt', 'grass', 'wood'][i]
        for _ in range(3 * 240):
            if c['resting'] == 2: break
            step_hull(c, 1 / 240, -1.2, surf)
        traj.append(dict(seed_index=i, slide_speed=round(sp, 4), surface=surf, ground_y=-1.2, rest=[round(x, 5) for x in c['pos']]))
    out['socket_eject'] = [x * 1e-3 for x in MODEL['sockets']['socket_eject']]; out['sockets'] = {k: [x * 1e-3 for x in v] for k, v in MODEL['sockets'].items()}
    out['hull']['step_dt'] = 1 / 240; out['hull']['seed'] = 590; out['hull']['trajectories'] = traj
    out['checks'] = chk
    json.dump(out, open(os.path.join(HERE, 'action.json'), 'w'), separators=(',', ':'))
    plots(out)
    for k, c in chk.items(): print('PASS' if c['passed'] else 'FAIL', k, {a: b for a, b in c.items() if a not in ('passed', 'note', 'order')})
    for k in LOADS: print(k, {a: b for a, b in out['shots'][k].items() if not isinstance(b, list)})
    print(mp)

def plots(out):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for k, s in out['shots'].items():
        t = np.arange(len(s['pressure_MPa'])) * s['dt'] * 1e3; ax[0].plot(t, s['pressure_MPa'], label=out['loads'][k]['name']); ax[1].plot(t, s['payload_speed']); ax[2].plot(t, np.array(s['gun_force_N']) / 1e3)
    ax[0].set(xlabel='ms after ignition', ylabel='MPa', title='Base pressure (fitted curve)'); ax[1].set(xlabel='ms after ignition', ylabel='m/s', title='Payload speed'); ax[2].set(xlabel='ms after ignition', ylabel='kN', title='Force on the gun'); ax[0].legend()
    fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', '01_shot.png'), dpi=90); plt.close(fig)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6)); t = np.arange(len(out['recoil']['loads']['slug']['shoulder']['z_mm']))
    for k, r in out['recoil']['loads'].items():
        for st, d in r.items():
            ax[0].plot(t, d['z_mm'], label=f'{k}, {st}'); ax[1].plot(t, d['pitch_up_deg']); ax[2].plot(t[:120], d['shoulder_force_N'][:120])
    ax[0].set(xlabel='ms after the trigger break', ylabel='mm', title='Gun moves back'); ax[1].set(xlabel='ms', ylabel='degrees', title='Muzzle rises'); ax[2].set(xlabel='ms', ylabel='N', title='Force into the shooter'); ax[0].legend()
    fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', '02_recoil.png'), dpi=90); plt.close(fig)
    c = out['cycle']; p = c['profile']; S = c['stroke_mm']; fig, ax = plt.subplots(figsize=(9, 3.6)); tt = np.linspace(0, c['duration'], 400)
    s = [S * (x / p['back_s']) ** p['exponent'] if x < p['back_s'] else (S if x < p['back_s'] + p['dwell_s'] else S * (1 - ((x - p['back_s'] - p['dwell_s']) / p['forward_s']) ** p['exponent'])) for x in tt]
    ax.plot(tt * 1e3, s, label='slide'); ax.plot(tt * 1e3, [max(0, x - c['lost_motion_mm']) for x in s], label='bolt')
    for e in c['events']: ax.axvline(e['t'] * 1e3, color='k', lw=0.4); ax.text(e['t'] * 1e3, S * (1.02 if e['direction'] == 'back' else -0.1), e['name'], rotation=60, fontsize=7)
    ax.set(xlabel='ms', ylabel='rearward travel (mm)', title='Pump stroke and its events', ylim=(-18, S * 1.35)); ax.legend(loc='center right'); fig.tight_layout(); fig.savefig(os.path.join(HERE, 'plots', '03_pump_cycle.png'), dpi=90); plt.close(fig)

if __name__ == '__main__':
    main()
