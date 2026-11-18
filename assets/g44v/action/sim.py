#!/usr/bin/env python3
"""G44 V action and recoil simulation: one shot of a .22 LR straight-blowback pistol, from the trigger break to the slide
back in battery, for three named factory loads.   python3 sim.py   -> action.json, plots/

Lumped-parameter physics (ordinary differential equations, no fluid or finite-element model).  Every number is in PARAMS
with its source and status: 'published' (named source), 'measured' (from the model recipe / a photo), 'inferred' (reason
given), 'calibrated' (fitted to a published figure, which is named).  Frame of the output: that of the model export
(metres, +Z muzzle, +Y up, +X shooter's left).  Time zero is the trigger bar releasing the firing pin.
"""
import json, math, os, sys
import numpy as np
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
INV = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
CHK = json.load(open(os.path.join(HERE, '..', 'model', 'checks.json')))
GR, FPS, PSI, IN = 64.79891e-6, 0.3048, 6894.757, 0.0254
mp = lambda k: INV['params'][k]['value']
kin = INV['kinematics']

def P(value, unit, status, source): return dict(value=value, unit=unit, status=status, source=source)
PARAMS = dict(
    # ---- cartridge and bore
    m_bullet=P(40 * GR, 'kg', 'published', 'CCI: 40 grain bullet (all three loads)'),
    bore_area=P(math.pi / 4 * (5.6e-3) ** 2 * 0.985, 'm2', 'published', '.22 LR groove diameter 5.6 mm, less 1.5 % for the lands (SAAMI Z299.1 rimfire, nominal)'),
    case_area=P(math.pi / 4 * (5.72e-3) ** 2, 'm2', 'published', '.22 LR case body diameter 0.225 in (SAAMI Z299.1)'),
    case_len=P(15.6e-3, 'm', 'published', '.22 LR case length 0.613 in (SAAMI Z299.1)'),
    m_case=P(0.60e-3, 'kg', 'inferred', 'empty .22 LR brass case, about 9 grains'),
    m_cartridge=P(3.33e-3, 'kg', 'published', 'maker\'s weights: loaded magazine - empty magazine = 50 g for 15 rounds'),
    chamber_vol=P(0.17e-6, 'm3', 'inferred', '.22 LR case capacity about 0.23 cm3 gross less the seated bullet heel'),
    bullet_travel_test=P(24 * IN - 15.6e-3, 'm', 'published', 'CCI velocities are test-barrel figures; 24 in rimfire test barrel (SAAMI Z299.1), less the case length'),
    bullet_travel=P(mp('barrel_len') * 1e-3 - 15.6e-3, 'm', 'published', 'maker\'s barrel length 102 mm less the case length'),
    p_map=P(24000 * PSI, 'Pa', 'published', 'SAAMI maximum average pressure for .22 Long Rifle: 24,000 psi (Z299.1)'),
    # ---- propellant gas (generic fast double-base flake powder; none of these is published for the loads)
    force_const=P(1.00e6, 'J/kg', 'inferred', 'typical fast pistol powder impetus'),
    gamma=P(1.24, '-', 'inferred', 'typical propellant gas'), covolume=P(1.0e-3, 'm3/kg', 'inferred', 'typical'), rho_prop=P(1600.0, 'kg/m3', 'inferred', 'typical'),
    burn_exp=P(0.9, '-', 'inferred', 'pressure exponent of the burn law'), form_theta=P(0.5, '-', 'inferred', 'degressive flake'),
    p_ign=P(3.0e6, 'Pa', 'inferred', 'pressure left by the priming compound'), p_start=P(8.0e6, 'Pa', 'inferred', 'crimp and engraving of the heeled bullet'),
    p_fric=P(2.0e6, 'Pa', 'inferred', 'bore friction as an equivalent pressure (about 50 N); a lubricated lead bullet'), phi=P(1.05, '-', 'inferred', 'bullet fictitious mass factor'),
    ign_delay=P(0.15e-3, 's', 'inferred', 'rim crush to charge alight'),
    # ---- firing train (Safe Action striker)
    m_striker=P(5.5e-3, 'kg', 'measured', 'model volume of the firing pin and spring cups x steel density (inventory.json)'),
    striker_precock=P(mp('striker_precock') * 1e-3, 'm', 'inferred', 'model: firing pin held part-cocked with the trigger forward'),
    striker_break=P(kin['striker_break_mm'] * 1e-3, 'm', 'inferred', 'model kinematics: part-cock plus the trigger bar travel to the break'),
    striker_F_fired=P(8.0, 'N', 'inferred', 'firing pin spring force with the pin forward'), striker_F_cocked=P(16.0, 'N', 'inferred', 'firing pin spring force at the break; gives 0.10 J. It must stay below the recoil spring load in battery or the slide could not close'),
    rim_crush=P(0.5e-3, 'm', 'inferred', 'depth of the rim indent at ignition'),
    trigger_pull=P(26.0, 'N', 'published', 'maker\'s specification table: trigger pull 26 N'),
    # ---- slide and springs
    m_slide=P(CHK['mass']['normalised_g']['slide'] * 1e-3, 'kg', 'inferred', 'model volumes x nominal densities, scaled so slide + barrel + frame = the published 358 g (model/checks.json). The split is not published'),
    m_pistol=P(0.358, 'kg', 'published', 'maker\'s specification table: weight without magazine'), m_magazine=P(0.057, 'kg', 'published', 'maker\'s table: with empty magazine 415 g'),
    travel=P(mp('full_travel') * 1e-3, 'm', 'inferred', 'model: lock-open travel 42 mm measured from a photo (manual p. 21) + 3 mm'),
    lock_open=P(mp('lock_open_travel') * 1e-3, 'm', 'measured', 'slide position locked open, manual p. 21 picture 18'),
    spring_F0=P(24.0, 'N', 'inferred', 'recoil spring load in battery. Not published'), spring_F1=P(65.0, 'N', 'inferred', 'recoil spring load at full travel (about 14.6 lbf). Not published; chosen with m_slide so that standard-velocity ammunition cycles and CCI Quiet-22 does not, as the makers say'),
    obturation=P(0.90, '-', 'inferred', 'share of the gas force on the case head that reaches the slide; the rest is case friction on the chamber wall'),
    slide_friction=P(2.0, 'N', 'inferred', 'rail drag'), strip_force=P(4.0, 'N', 'inferred', 'drag of stripping a round from the feed lips'),
    u_eject=P((mp('breech_face') - 58.0) * 1e-3, 'm', 'measured', 'model: ejector tip 15 mm behind the breech face'),
    u_feed=P(31.0e-3, 'm', 'inferred', 'model: breech face passes the rim of the top round'), u_chamber=P(8.0e-3, 'm', 'inferred', 'round leaves the lips'),
    e_rear=P(0.30, '-', 'inferred', 'restitution, slide on the polymer frame'), e_front=P(0.15, '-', 'inferred', 'restitution, breech on the barrel'),
    # ---- shooter
    m_hand=P(1.20, 'kg', 'inferred', 'effective mass of hands and forearms moving with the pistol'),
    bore_height=P(0.075, 'm', 'inferred', 'bore axis above the wrist pivot (socket_hand_right is 52 mm below the bore, the wrist lower still)'),
    # ---- brass
    eject_speed_ratio=P(0.5, '-', 'inferred', 'case speed over slide speed at the ejector'), eject_azimuth_deg=P(100.0, 'deg', 'inferred', 'from +Z toward -X (to the right, slightly rearward)'),
    eject_elevation_deg=P(30.0, 'deg', 'inferred', 'above horizontal'), eject_spin=P(300.0, 'rad/s', 'inferred', 'tumbling about the vertical axis'),
)
STANCES = dict(two_hand=dict(f_hz=7.0, zeta=0.7, fp_hz=5.0, zeta_p=0.7, I=0.030, m_scale=1.0, note='both hands, arms extended; all four numbers inferred, not measured'),
               one_hand=dict(f_hz=5.0, zeta=0.55, fp_hz=3.5, zeta_p=0.55, I=0.020, m_scale=0.6, note='firing hand only; inferred'))
LOADS = dict(   # name: published box figures (CCI, cci-ammunition.com product pages, retrieved 2026-11-17) + two guessed inputs (charge, peak pressure)
    cci_standard_velocity=dict(label='CCI Standard Velocity 40 gr LRN (part 35)', mv_test=1070 * FPS, charge=0.085e-3, p_max=140e6, maker_note=None),
    cci_mini_mag=dict(label='CCI Mini-Mag 40 gr CPRN (part 30)', mv_test=1235 * FPS, charge=0.110e-3, p_max=24000 * PSI, maker_note=None),
    cci_quiet_22=dict(label='CCI Quiet-22 40 gr LRN (part 960)', mv_test=710 * FPS, charge=0.045e-3, p_max=60e6,
                      maker_note='CCI: may be used in semi-automatic firearms, however manual cycling of the action may be required'),
)
LOAD_GUESS = 'charge mass and peak pressure are guesses (not published); the burn coefficient and loss factor are calibrated so the 24 in test barrel gives the published velocity at that peak pressure'
v = lambda k: PARAMS[k]['value']

# ------------------------------------------------------------------ internal ballistics
def interior(load, travel, beta, loss, dt=2e-7, post=6e-3):
    """returns dict of arrays (uniform dt) from ignition: p_breech, x, v until exit, then blow-down of the bore."""
    mb, A, V0, f, g, eta, rho = v('m_bullet'), v('bore_area'), v('chamber_vol'), v('force_const'), v('gamma'), v('covolume'), v('rho_prop')
    mc = load['charge']; phi = v('phi'); al, th = v('burn_exp'), v('form_theta')
    meff = phi * mb + mc / 3
    def pres(z, x, vel):
        Vf = V0 + A * x - mc * (1 - z) / rho - eta * mc * z
        return max((f * mc * z - (g - 1) * (1 + loss) * 0.5 * meff * vel * vel) / Vf, 0.0)
    z = v('p_ign') * (V0 - mc / rho) / (f * mc); x = 0.0; vel = 0.0; t = 0.0; moving = False
    T, PB, X, VV = [], [], [], []
    kb = 1 + mc / (6 * phi * mb)          # breech over mean pressure (Lagrange)
    kbase = 1 - mc / (3 * phi * mb)
    def deriv(z, x, vel, mov):
        p_ = pres(z, x, vel)
        dz = beta * (p_ / 1e6) ** al * max(1 - z, 0.0) ** th if z < 1 else 0.0
        a = A * (p_ * kbase - v('p_fric')) / (phi * mb) if mov else 0.0
        return dz, vel, a
    while x < travel and t < 20e-3:
        p_ = pres(z, x, vel)
        if not moving and p_ > v('p_start'): moving = True
        T.append(t); PB.append(p_ * kb); X.append(x); VV.append(vel)
        k1 = deriv(z, x, vel, moving); k2 = deriv(z + k1[0] * dt / 2, x + k1[1] * dt / 2, vel + k1[2] * dt / 2, moving)
        k3 = deriv(z + k2[0] * dt / 2, x + k2[1] * dt / 2, vel + k2[2] * dt / 2, moving); k4 = deriv(z + k3[0] * dt, x + k3[1] * dt, vel + k3[2] * dt, moving)
        z = min(z + dt * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6, 1.0); x += dt * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        vel = max(vel + dt * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]) / 6, 0.0); t += dt
        if moving and vel <= 0 and t > 1e-3: break          # stuck bullet
    n_exit = len(T); pe = pres(z, x, vel); Ve = V0 + A * x - eta * mc
    out = dict(t_exit=t, v_exit=vel, p_max=max(PB), z_exit=z, p_exit=pe)
    # blow-down: isentropic emptying of the bore through a sonic muzzle
    RT = pe * Ve / mc; m = mc; cf = math.sqrt(g) * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1)))
    tp = 0.0
    while tp < post:
        r = m / mc; p_ = pe * r ** g; RTt = RT * r ** (g - 1)
        T.append(t + tp); PB.append(p_); X.append(x); VV.append(vel)
        m -= A * p_ / math.sqrt(RTt) * cf * dt * 5; tp += dt * 5
        if p_ < 1e5: break
    # resample to uniform 2e-6
    tt = np.array(T); du = 2e-6; tu = np.arange(0, tt[-1], du)
    out.update(dt=du, p_breech=np.interp(tu, tt, PB), x=np.interp(tu, tt, X), vel=np.interp(tu, tt, VV), n_exit=int(t / du))
    out['gas_momentum'] = float(np.trapezoid(np.interp(tu, tt, PB)[int(t / du):], dx=du) * A)      # after the bullet has left
    return out

def calibrate(load):
    """burn coefficient and loss factor so the test barrel gives the published velocity at the stated peak pressure"""
    Lt = v('bullet_travel_test')
    def beta_for(loss):
        return brentq(lambda b: interior(load, 0.03, b, loss, dt=1e-6, post=0)['p_max'] - load['p_max'], 5, 4000, xtol=0.05)
    def err(loss):
        return interior(load, Lt, beta_for(loss), loss, dt=1e-6, post=0)['v_exit'] - load['mv_test']
    lo, hi = 0.0, 12.0
    if err(lo) < 0: raise SystemExit('calibration: the guessed charge cannot reach the published velocity: ' + load['label'])
    loss = brentq(err, lo, hi, xtol=1e-3); return beta_for(loss), loss, True

# ------------------------------------------------------------------ firing train
def firing_train():
    m, xb, F0, F1 = v('m_striker'), v('striker_break'), v('striker_F_fired'), v('striker_F_cocked')
    k = (F1 - F0) / xb; dt = 1e-5; x = xb; vel = 0.0; t = 0.0; T, Xs = [0.0], [xb]
    while x > 0:
        a = -(F0 + k * x) / m; vel += a * dt; x += vel * dt; t += dt; T.append(t); Xs.append(max(x, 0.0))
    E = 0.5 * m * vel * vel; t_hit = t
    t_ign = t_hit + v('ign_delay')
    return dict(dt=dt, striker_mm=[round(q * 1e3, 4) for q in Xs], lock_time=t_hit, t_ignition=t_ign, impact_speed=abs(vel), energy=E, k=k)

# ------------------------------------------------------------------ slide, gun body and shooter
def cycle(load, ib, ft, stance='two_hand', trigger_held=True, dt=1e-5, t_end=0.25):
    ms, U = v('m_slide'), v('travel'); F0, F1 = v('spring_F0'), v('spring_F1'); ks = (F1 - F0) / U
    mg = v('m_pistol') + v('m_magazine') + v('m_cartridge') * 7 - ms + v('m_hand') * STANCES[stance]['m_scale']      # gun body with a half-full magazine, plus the hands
    st = STANCES[stance]; kg = (2 * math.pi * st['f_hz']) ** 2 * (mg + ms); cg = 2 * st['zeta'] * math.sqrt(kg * (mg + ms))
    I = st['I']; kp = (2 * math.pi * st['fp_hz']) ** 2 * I; cp = 2 * st['zeta_p'] * math.sqrt(kp * I); h = v('bore_height')
    t0 = ft['t_ignition']; A_c, ob = v('case_area'), v('obturation'); fr = v('slide_friction')
    catch = v('striker_break') if trigger_held else v('striker_precock'); kS = ft['k']
    n = int(t_end / dt) + 1; out = {k_: np.zeros(n) for k_ in ('u', 'ud', 'g', 'gd', 'pitch', 'body_force', 'striker')}
    u = ud = g = gd = th = thd = 0.0; phase = 'closed'; ev = {}; fed = False; outcome = 'cycled'; umax = 0.0; ejected = False; resting = False
    pb, dtb = ib['p_breech'], ib['dt']; t_exit = t0 + ib['t_exit']
    for i in range(n):
        t = i * dt
        # gas force on the case head
        tb = t - t0; p = float(np.interp(tb, np.arange(len(pb)) * dtb, pb)) if 0 <= tb < (len(pb) - 1) * dtb else 0.0
        Fg = p * A_c
        seated = resting or (phase == 'closed' and Fg * ob <= F0)      # slide held on the barrel by the spring: no net force between them
        Fs = 0.0 if seated else (F0 + ks * u)
        Fsl = Fg * ob - Fs                                   # on the slide, + rearward
        Fbody = Fs + Fg * (1 - ob) * 0.0                     # on the gun body, + rearward: the recoil spring pushes on the barrel lug
        if t0 <= t < t_exit: Fbody -= v('p_fric') * v('bore_area')      # bullet friction drags the barrel forward; case friction (1 - ob) is internal to barrel + case until the case leaves
        if abs(ud) > 1e-6: Fsl -= fr * math.copysign(1, ud); Fbody += fr * math.copysign(1, ud)
        strik = 0.0
        if phase == 'forward':
            if not fed and u <= v('u_feed'):                 # pick up the next round (inelastic), then drag it off the lips
                ud *= ms / (ms + v('m_cartridge')); fed = True; ev['feed_pick_up'] = t
            if fed and u > v('u_chamber'): Fsl += v('strip_force'); Fbody -= v('strip_force')
            if u < catch and not resting:                    # the trigger bar holds the firing pin: the slide compresses the firing pin spring as it closes
                xs = catch - u; Fst = v('striker_F_fired') + kS * xs; Fsl += Fst; Fbody -= Fst
                ev.setdefault('firing_pin_caught', t)
        if phase == 'forward' and u < catch: strik = catch - max(u, 0.0)
        if resting: Fsl = 0.0; ud = 0.0; u = 0.0
        # integrate (semi-implicit Euler; the stiff part is the pressure, which is an input)
        ua = Fsl / ms - 0.0; ga = (Fbody - kg * g - cg * gd) / mg
        # u is relative travel: slide absolute acceleration minus body acceleration
        if seated: ud = 0.0; u = 0.0
        else: ud += (ua - ga) * dt; u += ud * dt
        gd += ga * dt; g += gd * dt
        tha = (Fbody * h - kp * th - cp * thd) / I; thd += tha * dt; th += thd * dt
        if phase == 'closed' and u > 1e-5: phase = 'back'; ev['slide_moves'] = t
        if u < 0 and phase in ('closed',): u = 0.0; ud = max(ud, 0.0)
        if phase == 'back':
            if not ejected and u >= v('u_eject'): ejected = True; ev['eject'] = t; ev['eject_slide_speed'] = ud
            if u >= U:                                       # frame stop
                mu = ms * mg / (ms + mg); J = (1 + v('e_rear')) * mu * ud; ev['rear_stop'] = t; ev['rear_stop_speed'] = ud
                ud -= J / ms + J / mg; gd += J / mg; thd += J * h / I; u = U; phase = 'forward'; ev['max_travel'] = t; umax = U
            elif ud <= 0: phase = 'forward'; ev['max_travel'] = t; umax = u
        elif phase == 'forward' and u <= 0 and not resting:
            mu = ms * mg / (ms + mg); J = (1 + v('e_front')) * mu * (-ud); ev.setdefault('in_battery', t); ev['closing_speed'] = -ud
            gd -= J / mg; thd -= J * h / I; u = 0.0; ud = 0.0; resting = True
        umax = max(umax, u)
        for k_, val in (('u', u), ('ud', ud), ('g', g), ('gd', gd), ('pitch', th), ('body_force', Fbody), ('striker', strik)): out[k_][i] = val
    if umax < v('u_eject'): outcome = 'short stroke: the case is not ejected'
    elif umax < v('u_feed') + 2e-3: outcome = 'short stroke: ejects but does not pick up the next round'
    elif umax < v('lock_open'): outcome = 'cycles, but will not lock open on the last round'
    out.update(dt=dt, events=ev, outcome=outcome, max_travel=umax, mg=mg, ms=ms, ks=ks)
    return out

# ------------------------------------------------------------------ brass
def mulberry32(seed):
    s = seed & 0xFFFFFFFF
    def r():
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF; z = s
        z = ((z ^ (z >> 15)) * (z | 1)) & 0xFFFFFFFF
        z = (z ^ (z + (((z ^ (z >> 7)) * (z | 61)) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return r
def gauss(r): return math.sqrt(-2 * math.log(max(r(), 1e-12))) * math.cos(2 * math.pi * r())
BRASS = dict(speed_sigma=0.15, azimuth_sigma_deg=10.0, elevation_sigma_deg=8.0, spin_sigma=0.3, restitution=0.35, friction=0.5, drag_k=0.012, gravity=9.80665, step_dt=1 / 240)
def eject_case(nom, r):
    sp = nom['speed'] * max(0.3, 1 + BRASS['speed_sigma'] * gauss(r)); az = math.radians(nom['azimuth_deg'] + BRASS['azimuth_sigma_deg'] * gauss(r))
    el = math.radians(nom['elevation_deg'] + BRASS['elevation_sigma_deg'] * gauss(r)); w = nom['spin'] * max(0.2, 1 + BRASS['spin_sigma'] * gauss(r))
    vel = [-sp * math.cos(el) * math.sin(az), sp * math.sin(el), sp * math.cos(el) * math.cos(az) + nom['carry_z']]
    return dict(pos=list(nom['pos']), vel=vel, angVel=[0.0, -w, 0.0], resting=0, bounces=0)
def step_case(c, dt, ground_y):
    if c['resting'] == 2: return c
    g = BRASS['gravity']; k = BRASS['drag_k']; sp = math.sqrt(sum(q * q for q in c['vel']))
    for i in range(3): c['vel'][i] -= k * sp * c['vel'][i] * dt
    c['vel'][1] -= g * dt
    for i in range(3): c['pos'][i] += c['vel'][i] * dt
    if c['pos'][1] <= ground_y and c['vel'][1] < 0:
        c['pos'][1] = ground_y; c['vel'][1] = -c['vel'][1] * BRASS['restitution']; f = 1 - BRASS['friction']
        c['vel'][0] *= f; c['vel'][2] *= f; c['angVel'][1] *= 0.5; c['bounces'] += 1
        if abs(c['vel'][1]) < 0.25: c['vel'] = [0.0, 0.0, 0.0]; c['angVel'] = [0.0, 0.0, 0.0]; c['resting'] = 2
    return c

# ------------------------------------------------------------------ run
def sample_py(D, t, ammo, stance, last_round=False):
    """the reference implementation of the runtime's sample(): linear interpolation of the tracks (mirrored in g44v-action.js)"""
    L = D['loads'][ammo]; c = L['cycle']
    def lerp(a, dt, tt):
        u = tt / dt; n = len(a)
        if not u > 0: return a[0]
        if u >= n - 1: return a[n - 1]
        i = int(math.floor(u)); return a[i] + (a[i + 1] - a[i]) * (u - i)
    mm = lerp(c['slide_mm'], c['dt'], t); vel = lerp(c['slide_mps'], c['dt'], t)
    held = False
    if last_round and t > L['events']['max_travel'] and mm <= D['mechanics']['lock_open_mm'] and L['max_travel_mm'] >= D['mechanics']['lock_open_mm']:
        mm = D['mechanics']['lock_open_mm']; vel = 0.0; held = True
    r = L['recoil'][stance]
    return dict(slideMm=mm, slideVel=vel, held=held, z=lerp(r['z_mm'], c['dt'], t), pitch=lerp(r['pitch_up_deg'], c['dt'], t))

DEC = 10      # tracks are written every 0.1 ms
def main():
    r5 = lambda a, n=5: [round(float(q), n) for q in a]
    ft = firing_train()
    D = dict(meta=dict(title='G44 V action and recoil', credit='carpetshark', generator='sim.py', model='model/build.py (inventory.json)',
                       frame='metres, +Z muzzle, +Y up, +X shooter\'s left; origin on the bore axis at the slide\'s rear face',
                       time_zero='the trigger bar releases the firing pin', units='SI unless the key says otherwise (mm, deg, MPa)',
                       nodes=dict(slide='p01_slide (translate -Z by slide_mm)', firing_pin='p04_firing_pin (translate +Z by striker_fwd_mm relative to the rest pose)',
                                  recoil_spring='p03_recoil_spring (scale Z by 1 - slide_mm / 68.3)', slide_stop='p27_slide_stop_lever (rotate +%.1f deg about X when held open)' % mp('stop_lift_deg'))),
             params=PARAMS, stances=STANCES, loads={}, load_note=LOAD_GUESS)
    D['firing'] = dict(dt=ft['dt'], striker_mm=ft['striker_mm'], lock_time_s=round(ft['lock_time'], 6), ignition_s=round(ft['t_ignition'], 6), impact_speed_mps=round(ft['impact_speed'], 3),
                       energy_J=round(ft['energy'], 4), note='striker_mm: rearward position of the firing pin from its fired position; it is released at the break and flies forward')
    D['mechanics'] = dict(full_travel_mm=mp('full_travel'), lock_open_mm=mp('lock_open_travel'), eject_mm=v('u_eject') * 1e3, feed_mm=v('u_feed') * 1e3,
                          striker_precock_mm=mp('striker_precock'), striker_break_mm=kin['striker_break_mm'], trigger_break_deg=mp('trigger_break_deg'), bar_travel_mm=kin['bar_travel_break_mm'],
                          recoil_spring_free_mm=68.3, notes='travel numbers come from model/inventory.json so the clips and this simulation agree')
    D['trigger'] = dict(pull_N=v('trigger_pull'), curve_deg_N=[[0, 0], [0.5, 6.0], [mp('trigger_takeup_deg'), 11.0], [mp('trigger_takeup_deg') + 0.2, 22.0], [mp('trigger_break_deg'), 26.0]],
                        note='force at the trigger against rotation; only the 26 N break is published, the take-up shape is inferred')
    val = {}; cyc = {}
    for name, load in LOADS.items():
        beta, loss, ok = calibrate(load)
        test = interior(load, v('bullet_travel_test'), beta, loss, dt=1e-6, post=0)
        ib = interior(load, v('bullet_travel'), beta, loss)
        mom_b = v('m_bullet') * ib['v_exit']; imp = float(np.trapezoid(ib['p_breech'], dx=ib['dt']) * v('case_area'))
        L = dict(label=load['label'], published=dict(muzzle_velocity_test_barrel_mps=round(load['mv_test'], 2), source='cci-ammunition.com product page, retrieved 2026-11-17', maker_note=load['maker_note']),
                 guessed=dict(charge_kg=load['charge'], p_max_Pa=load['p_max']), calibrated=dict(burn_coeff=round(beta, 3), loss_factor=round(loss, 4), converged=ok),
                 test_barrel=dict(v_mps=round(test['v_exit'], 2), p_max_MPa=round(test['p_max'] / 1e6, 1), muzzle_pressure_MPa=round(test['p_exit'] / 1e6, 3)),
                 pistol=dict(muzzle_velocity_mps=round(ib['v_exit'], 2), muzzle_velocity_fps=round(ib['v_exit'] / FPS, 1), p_max_MPa=round(ib['p_max'] / 1e6, 1), barrel_time_ms=round(ib['t_exit'] * 1e3, 4),
                             muzzle_pressure_MPa=round(ib['p_exit'] / 1e6, 2), burnt_at_exit=round(ib['z_exit'], 3), muzzle_energy_J=round(0.5 * v('m_bullet') * ib['v_exit'] ** 2, 1),
                             bullet_momentum_Ns=round(mom_b, 4), breech_impulse_Ns=round(imp, 4)))
        L['ballistics'] = dict(dt=ib['dt'], t0=round(ft['t_ignition'], 6), chamber_MPa=r5(ib['p_breech'][::5] / 1e6, 3), bullet_mm=r5(ib['x'][::5] * 1e3, 3), bullet_mps=r5(ib['vel'][::5], 2))
        L['ballistics']['dt'] = ib['dt'] * 5
        L['recoil'] = {}
        for stn in STANCES:
            cy = cycle(load, ib, ft, stn)
            if stn == 'two_hand':
                cyc[name] = (ib, cy); e = cy['events']
                L['outcome'] = cy['outcome']; L['max_travel_mm'] = round(cy['max_travel'] * 1e3, 2)
                L['events'] = {k: round(float(val_), 6) for k, val_ in e.items()}
                L['events'].update(striker_hits=round(ft['lock_time'], 6), ignition=round(ft['t_ignition'], 6), bullet_exit=round(ft['t_ignition'] + ib['t_exit'], 6))
                L['cycle'] = dict(dt=cy['dt'] * DEC, slide_mm=r5(cy['u'][::DEC] * 1e3, 4), slide_mps=r5(cy['ud'][::DEC], 4), striker_recock_mm=r5(cy['striker'][::DEC] * 1e3, 3))
                L['slide_peak_speed_mps'] = round(float(cy['ud'].max()), 3); L['slide_peak_energy_J'] = round(0.5 * cy['ms'] * float(cy['ud'].max()) ** 2, 3)
                L['cycle_time_ms'] = round(e.get('in_battery', float('nan')) * 1e3, 2)
            L['recoil'][stn] = dict(z_mm=r5(-cy['g'][::DEC] * 1e3, 4), pitch_up_deg=r5(np.degrees(cy['pitch'])[::DEC], 4), body_force_N=r5(cy['body_force'][::DEC], 2),
                                    peak_z_mm=round(float(cy['g'].max() * 1e3), 3), peak_pitch_deg=round(float(np.degrees(cy['pitch']).max()), 3))
        D['loads'][name] = L
        val[name] = dict(test_barrel_velocity=dict(model_mps=round(test['v_exit'], 2), published_mps=round(load['mv_test'], 2), note='calibration target'),
                         peak_pressure=dict(model_MPa=round(ib['p_max'] / 1e6, 1), saami_map_MPa=round(v('p_map') / 1e6, 1), within_map=bool(ib['p_max'] <= v('p_map') * 1.001)),
                         momentum=dict(bullet_Ns=round(mom_b, 4), breech_impulse_Ns=round(imp, 4), gas_share=round(imp / mom_b - 1, 3),
                                       note='breech impulse = bullet momentum + bore friction impulse + gas momentum; a conservation check on the integration'),
                         slide=dict(peak_speed_mps=L['slide_peak_speed_mps'], max_travel_mm=L['max_travel_mm'], outcome=L['outcome']))
    full = mp('full_travel')
    val['function_against_makers_statements'] = dict(
        cci_standard_velocity=dict(statement='manual p. 12: designed to work with quality SAAMI / CIP .22 l.r. ammunition', expected='full stroke', model=D['loads']['cci_standard_velocity']['outcome'],
                                   agrees=bool(D['loads']['cci_standard_velocity']['max_travel_mm'] >= full)),
        cci_mini_mag=dict(statement='as above', expected='full stroke', model=D['loads']['cci_mini_mag']['outcome'], agrees=bool(D['loads']['cci_mini_mag']['max_travel_mm'] >= full)),
        cci_quiet_22=dict(statement='manual p. 12: some .22 l.r. loads may not produce sufficient energy to fully cycle the slide; CCI: manual cycling of the action may be required',
                          expected='less than the full stroke', model=D['loads']['cci_quiet_22']['outcome'] + ' (%.1f of %.0f mm)' % (D['loads']['cci_quiet_22']['max_travel_mm'], full),
                          agrees=bool(D['loads']['cci_quiet_22']['max_travel_mm'] < full)),
        note='a qualitative check: the recoil spring loads and the slide mass are not published and were chosen inside the window where these statements hold (see sensitivity)')
    # sensitivity of the cycle to the two unpublished numbers that matter most
    sens = []
    for prm, fac in (('m_slide', 0.7), ('m_slide', 1.3), ('spring_F1', 0.7), ('spring_F1', 1.3), ('obturation', 0.9)):
        old = PARAMS[prm]['value']; PARAMS[prm]['value'] = old * fac; row = dict(param=prm, factor=fac)
        for name in LOADS: cy = cycle(LOADS[name], cyc[name][0], ft); row[name] = dict(max_travel_mm=round(cy['max_travel'] * 1e3, 1), peak_speed_mps=round(float(cy['ud'].max()), 2), outcome=cy['outcome'])
        PARAMS[prm]['value'] = old; sens.append(row)
    D['sensitivity'] = sens; D['validation'] = val
    # brass
    ref = D['loads']['cci_standard_velocity']; es = ref['events'].get('eject_slide_speed', 0.0)
    sock = {s['name']: s['pos_m_export'] for s in INV['sockets']}
    nom = dict(pos=sock['socket_eject'], speed=round(v('eject_speed_ratio') * es, 4), azimuth_deg=v('eject_azimuth_deg'), elevation_deg=v('eject_elevation_deg'), spin=v('eject_spin'), carry_z=round(-es * 0.3, 4))
    traj = []
    for seed in range(1, 9):
        r = mulberry32(seed); c = eject_case(nom, r); gy = -1.4
        for _ in range(240 * 4):
            step_case(c, BRASS['step_dt'], gy)
            if c['resting'] == 2: break
        traj.append(dict(seed=seed, ground_y=gy, rest=[round(q, 5) for q in c['pos']], bounces=c['bounces']))
    D['brass'] = dict(note='nominal ejection for the reference load, in the gun frame; scatter is Gaussian; speeds per load scale with events.eject_slide_speed',
                      release_time_s=ref['events'].get('eject'), case=dict(mass_kg=v('m_case'), length_m=v('case_len'), diameter_m=5.72e-3), nominal=nom, scatter=BRASS, trajectories=traj,
                      per_load_speed={k: round(v('eject_speed_ratio') * D['loads'][k]['events'].get('eject_slide_speed', 0.0), 4) for k in LOADS})
    # parity samples for the JS runtime
    rr = mulberry32(2026); par = []
    for _ in range(60):
        ammo = list(LOADS)[int(rr() * 3)]; stn = list(STANCES)[int(rr() * 2)]; t = rr() * 0.24; lr = rr() > 0.5
        s = sample_py(D, t, ammo, stn, lr); par.append(dict(t=t, ammo=ammo, stance=stn, lastRound=lr, slideMm=s['slideMm'], slideVel=s['slideVel'], held=s['held'], z=s['z'], pitch=s['pitch']))
    D['parity'] = dict(note='sample() evaluated by sim.py at random times; test_action.js must reproduce these with g44v-action.js', samples=par)
    json.dump(D, open(os.path.join(HERE, 'action.json'), 'w'), separators=(',', ':'))
    print('firing train: lock time %.2f ms, %.3f J, %.2f m/s' % (ft['lock_time'] * 1e3, ft['energy'], ft['impact_speed']))
    for name, L in D['loads'].items():
        print('%-22s test %.0f m/s (pub %.0f) | pistol %.1f m/s = %.0f fps, pmax %.0f MPa, exit %.2f ms | slide %.2f m/s, travel %.1f mm, %s, cycle %.1f ms | recoil z %.2f mm pitch %.2f deg' % (
            name, L['test_barrel']['v_mps'], L['published']['muzzle_velocity_test_barrel_mps'], L['pistol']['muzzle_velocity_mps'], L['pistol']['muzzle_velocity_fps'], L['pistol']['p_max_MPa'],
            L['pistol']['barrel_time_ms'], L['slide_peak_speed_mps'], L['max_travel_mm'], L['outcome'], L['cycle_time_ms'], L['recoil']['two_hand']['peak_z_mm'], L['recoil']['two_hand']['peak_pitch_deg']))
    for s in sens: print('  sens', s['param'], s['factor'], {k: (s[k]['max_travel_mm'], s[k]['outcome'][:12]) for k in LOADS})
    print('function check:', {k: q['agrees'] for k, q in val['function_against_makers_statements'].items() if k != 'note'})
    if '--noplots' not in sys.argv:
        import plots; plots.make(D, HERE)

if __name__ == '__main__':
    main()
