#!/usr/bin/env python3
"""HK416 D14.5RS: malfunction simulation, tied to the operating cycle in ../action/action.json.

    python3 sim.py            # rebuilds malfunctions.json, procedures.json, validation.json, parity.json and plots/ (about 3.5 minutes)
    python3 sim.py --quick    # shorter Monte Carlo runs (for development; do not commit its output)
    python3 sim.py --no-plots

Each shot is a short chain of physical margins taken from the action simulation (hammer energy against the primer,
carrier energy against travel, the ejection and feed timing windows, extraction drag against the rim), each with
logistic shot-to-shot scatter. Dust, fouling, heat, cold, ammunition, magazine and wear move the margins. Two
points are calibrated: an assumed clean baseline and the HK416's published counts in the Army's 2007 dust test.
The rifle is then a state machine that the clearing procedures act on.

hk416-malfunctions.js is the same model in JavaScript; parity.json and validation.json are what test_malfunctions.js
checks it against. Every number is in PARAMS with its source. Credit: carpetshark."""
import json, math, os, sys

import content as C

HERE = os.path.dirname(os.path.abspath(__file__))
ACTION = os.path.join(HERE, '..', 'action', 'action.json')
QUICK = '--quick' in sys.argv

# ================================================================== parameters
# name: [value, unit, source, note]. source: manual | published | action | inferred | guess | calibrated
PARAMS = {
    # ---- dust, fouling, heat
    'dust_residual': [0.30, '-', 'guess', 'share of the dust load still in the rifle straight after a wipe and lubrication'],
    'lube_interval': [600, 'rounds', 'published', 'dust test: wipe and lubricate every 600 rounds (edt3)'],
    'clean_interval': [1200, 'rounds', 'published', 'dust test: full clean every 1,200 rounds (edt3)'],
    'heat_per_shot': [2.0, 'K', 'inferred', 'mean barrel temperature rise per shot: about 1.1 kJ of the 6.5 kJ charge into 1.1 kg of steel'],
    'heat_tau': [600.0, 's', 'guess', 'barrel cooling time constant in still air'],
    'heat_ref': [432.0, 'K', 'manual', 'rise after 250 rounds in 180 s with the two values above: the manual\'s cooling limit (p. 4) is heat index 1'],
    'cold_ref': [-54.0, 'C', 'published', '-65 F, the cold extreme of MIL-C-63989C 3.10: cold index 1'],
    'hot_ref': [52.0, 'C', 'published', '+125 F, the hot extreme of MIL-C-63989C 3.10: hot index 1'],
    # ---- firing
    'hammer_energy': [None, 'J', 'action', 'hammer energy at the firing pin (action validation.hammer_energy)'],
    'primer_allfire': [0.334, 'J', 'guess', 'No. 41 primer all-fire: 3.94 oz ball from 12 in (commonly quoted, unconfirmed)'],
    'indent_nominal': [None, 'mm', 'action', 'primer indent of a normal strike (action validation.primer_indent)'],
    'primer_f0': [None, 'N', 'action', 'primer cup yield force'],
    'primer_k': [None, 'N/m', 'action', 'primer cup hardening slope'],
    'fp_protrusion_go': [0.90, 'mm', 'manual', 'firing pin protrusion GO (pp. 17, 21)'],
    'fp_protrusion_nogo': [1.10, 'mm', 'manual', 'firing pin protrusion NO-GO (pp. 17, 21)'],
    'clean_scale': [None, '-', 'calibrated', 'common factor on the seven clean targets (p_*_clean) so that the clean rifle run through the test protocol gives about 5,000 rounds between stoppages'],
    'p_light_clean': [1.0e-5, '/round', 'inferred', 'light strikes in a clean rifle with M855: target for k_fire'],
    'k_fire': [None, '-', 'calibrated', 'steepness of the light-strike curve p = 1 / (1 + ratio^k), ratio = delivered energy / all-fire energy'],
    'eta_dust': [None, '-', 'calibrated', 'share of hammer energy lost at full dust load; solved for the dust test failure-to-fire count'],
    'eta_cold': [0.10, '-', 'guess', 'share of hammer energy lost to congealed lubricant at cold index 1'],
    'eta_foul': [0.01, '-', 'guess', 'share lost per unit of carbon fouling (small: no gas enters the receiver, manual p. 6)'],
    # ---- carrier energy (short stroke)
    'energy_scatter': [0.30, 'J', 'inferred', 'logistic scale of shot-to-shot carrier energy (sd 0.54 J, 6 percent of 9.06 J), from the port pressure scatter MIL-C-63989C 3.8 allows'],
    'drag_dust': [None, 'N', 'calibrated', 'extra carrier friction at full dust load; solved for the dust test failure-to-lock-back count'],
    'drag_foul': [1.0, 'N', 'guess', 'extra carrier friction per unit of carbon fouling'],
    'drag_dry': [4.0, 'N', 'guess', 'extra carrier friction when run dry (the action simulation\'s lubricated rail friction is 5 N)'],
    'drag_cold': [6.0, 'N', 'guess', 'extra carrier friction at cold index 1'],
    'drive_cold': [0.10, '-', 'inferred', 'carrier drive energy lost at cold index 1; the specification lets port pressure fall 2,000 psi (about 14 percent) at -65 F'],
    'drive_hot': [0.04, '-', 'inferred', 'carrier drive energy gained at hot index 1'],
    'drive_rings': [0.25, '-', 'guess', 'carrier drive energy lost with worn piston rings (manual p. 27: not enough gas)'],
    'p_catch': [2.0e-4, '/last round', 'guess', 'bolt catch or follower fails to hold the bolt although the carrier passed it'],
    # ---- extraction
    'rim_strength': [1700.0, 'N', 'inferred', 'force that shears the rim: 250 MPa brass in shear over 6 mm of claw by 1.14 mm of rim'],
    'p_fxt_clean': [4.0e-6, '/round', 'inferred', 'failures to extract in a clean rifle with M855: target for k_extract'],
    'k_extract': [None, '-', 'calibrated', 'steepness of the extraction curve p = 1 / (1 + ratio^k), ratio = extractor capacity / case drag'],
    'stick_dust': [None, '-', 'calibrated', 'rise in case drag at full dust load; solved for the dust test failure-to-extract count'],
    'stick_foul': [0.05, '-', 'guess', 'rise in case drag per unit of carbon fouling'],
    'stick_heat': [0.15, '-', 'guess', 'rise in case drag at heat index 1'],
    'extractor_go': [1.28, 'mm', 'manual', 'extractor claw GO gauge (pp. 17, 23)'],
    'extractor_nogo': [1.59, 'mm', 'manual', 'extractor claw NO-GO gauge (pp. 17, 24)'],
    'p_torn': [0.2, '-', 'guess', 'share of failures to extract that tear the rim when the claw is in gauge'],
    # ---- ejection
    'eject_clear_mm': [12.0, 'mm', 'guess', 'sideways travel that takes the case out of the bolt\'s path'],
    'p_fej_clean': [5.0e-5, '/round', 'inferred', 'failures to eject in a clean rifle: target for k_eject'],
    'k_eject': [None, '-', 'calibrated', 'steepness of the ejection curve p = 1 / (1 + ratio^k), ratio = time window / time the case needs'],
    'slow_dust': [None, '-', 'calibrated', 'share of ejection speed lost at full dust load; solved for the dust test failure-to-eject count'],
    'slow_foul': [0.03, '-', 'guess', 'share of ejection speed lost per unit of carbon fouling'],
    'slow_ejector': [0.5, '-', 'guess', 'share of ejection speed lost with a weak ejector spring'],
    'slow_extractor': [0.3, '-', 'guess', 'share of ejection speed lost with a weak extractor spring (the case pivots on the claw)'],
    'p_stove': [0.7, '-', 'guess', 'share of failures to eject that leave the case standing in the port; the rest lie loose in the receiver'],
    # ---- feeding
    'rise_mm': [6.0, 'mm', 'guess', 'how far the magazine must lift the stack to present the next round'],
    'follower_mass': [0.015, 'kg', 'guess', 'follower plus a third of the magazine spring'],
    'mag_spring_f0': [15.0, 'N', 'guess', 'magazine spring force on the last round'],
    'mag_spring_per_round': [1.1, 'N', 'guess', 'added spring force per round in the magazine (48 N full)'],
    'p_override_clean': [1.2e-5, '/round', 'inferred', 'bolt over-rides in a clean rifle, mean over a 30-round magazine: target for k_feed_time'],
    'k_feed_time': [None, '-', 'calibrated', 'steepness of the over-ride curve p = 1 / (1 + ratio^k), ratio = time the bolt is behind the magazine / time the stack needs to rise'],
    'p_nose_clean': [8.5e-5, '/round', 'inferred', 'feed ramp jams in a clean rifle with an HK steel magazine'],
    'p_two_clean': [4.0e-6, '/round', 'inferred', 'two-round feeds in a clean rifle with an HK steel magazine'],
    'feed_dust': [None, '-', 'calibrated', 'exponent of the feed-jam rise with dust, p ~ exp(b c); solved for the dust test failure-to-feed count (150 with the magazine stoppages)'],
    'lip_nose': [30.0, '-', 'guess', 'feed ramp jam multiplier at feed-lip damage 1'],
    'lip_two': [200.0, '-', 'guess', 'two-round feed multiplier at feed-lip damage 1'],
    # ---- chambering
    'chamber_work': [0.75, 'J', 'inferred', 'work to strip, seat and lock a round: the action simulation\'s 15 N feed drag over 30 mm, plus the extractor snapping over the rim and the bolt turning'],
    'p_ftc_clean': [6.0e-6, '/round', 'inferred', 'failures to chamber in a clean rifle: target for k_chamber'],
    'k_chamber': [None, '-', 'calibrated', 'steepness of the chambering curve p = 1 / (1 + ratio^k), ratio = carrier energy on closing / work needed'],
    'chamber_dust': [None, '-', 'calibrated', 'rise in chambering work at full dust load; solved for the dust test failure-to-chamber count'],
    'chamber_foul': [0.10, '-', 'guess', 'rise in chambering work per unit of carbon fouling'],
    'buffer_weak': [0.30, '-', 'guess', 'share of closing energy lost with a weak buffer spring (manual p. 26, step 3)'],
    # ---- hangfire, squib
    'hang_median': [0.08, 's', 'guess', 'median hangfire delay (lognormal)'],
    'hang_sigma': [1.2, '-', 'guess', 'log standard deviation of the hangfire delay: 95 percent under 0.58 s'],
    'hang_perceptible': [0.25, 's', 'guess', 'delay above which the shooter notices a click before the shot'],
    'squib_min_mm': [20.0, 'mm', 'guess', 'least bullet travel of a squib'],
    'squib_max_mm': [200.0, 'mm', 'inferred', 'most bullet travel of a squib: short of the gas port, 208 mm of travel in the action simulation, or the action would have cycled'],
    # ---- clearing actions
    'rack_extracts': [0.5, '-', 'guess', 'chance one rack pulls out a case the claw slipped off'],
    'rack_clears_port': [0.9, '-', 'guess', 'chance one rack, port down, drops a trapped case'],
    'rack_clears_nose': [0.85, '-', 'guess', 'chance one rack clears a round from the feed ramp with the magazine in'],
    'strike_frees': [0.7, '-', 'guess', 'chance striking the charging handle forward frees an over-ridden round, magazine out'],
    'strike_frees_mag_in': [0.2, '-', 'guess', 'the same with the magazine still in'],
    'hold_strike_frees': [0.95, '-', 'guess', 'chance the second method (bolt held back) frees it'],
    'assist_seats': [0.6, '-', 'guess', 'chance a tap on the forward assist closes a bolt that stopped short'],
}

AMMO = {
    'm855': dict(name='M855 ball, in specification', drive=1.00, p_dud=2.0e-5, p_hang=2.0e-6, p_squib=5.0e-7, primer=1.00, stick=1.0, feed=1.0, source='guess',
                 note='rates are guesses, checked only to pass MIL-C-63989C lot acceptance comfortably; drive 1 is the action simulation'),
    'commercial_223': dict(name='Commercial .223 ball', drive=0.92, p_dud=3.0e-5, p_hang=3.0e-6, p_squib=1.0e-6, primer=0.90, stick=1.0, feed=1.0, source='guess',
                           note='lower port pressure, softer primers'),
    'steel_case': dict(name='Steel-cased import', drive=0.90, p_dud=1.0e-4, p_hang=1.0e-5, p_squib=2.0e-6, primer=1.10, stick=1.2, feed=1.2, source='guess',
                       note='harder primers, cases that seal and release less well'),
    'degraded': dict(name='Old, damp or reloaded (the manual forbids reloads, p. 26)', drive=0.85, p_dud=5.0e-3, p_hang=1.0e-3, p_squib=3.0e-4, primer=1.0, stick=1.05, feed=1.5, source='guess',
                     note='for showing misfires, hangfires and squibs at a rate a player will meet'),
}
MAGS = {
    'hk_steel': dict(name='HK steel 30-round (manual pp. 5, 6)', capacity=30, nose=1.0, two=1.0, friction=6.0, feed_dust_extra=0.0, source='manual / calibrated',
                     note='the reference magazine; assumed to be what the dust test used'),
    'gi_aluminium': dict(name='US issue aluminium 30-round', capacity=30, nose=1.5, two=1.5, friction=12.0, feed_dust_extra=None, source='published / calibrated',
                         note='clean factors are guesses (the manual says reliability is improved with the steel magazine); the dust exponent is solved for the M4\'s magazine stoppages'),
}

# Calibration targets
EDT = dict(rifles=10, rounds=6000, cycle=120,
           hk416=dict(FFD=141, FTC=7, FFR=5, FXT=3, FEJ=49, BLR=0, FBR=3, OTH=2, magazine=9, class12=219, class3=14),
           m4_magazine=dict(summer=148, fall=239))
TARGET = dict(FFD=150.0, FTC=7.0, FFR=5.0, FXT=3.0, FEJ=49.0, FBR=3.0, aluminium_extra_feed=193.5)
CLEAN_TARGET_MRBS = 5000.0

P = {}
TAB = {}


def load_action():
    a = json.load(open(ACTION))
    ap = {k: v['value'] for k, v in a['params'].items()}
    c = a['cycle']; dt = c['dt']; x = c['carrier_mm']; v = c['carrier_mps']
    m = ap['m_carrier'] + ap['m_bolt'] + ap['m_buffer'] + ap['m_spring_eff']
    imax = max(range(len(x)), key=lambda i: x[i])
    ipk = max(range(imax), key=lambda i: v[i])

    def t_at(xx, lo, hi, rising):
        for i in range(lo, hi):
            a0, a1 = x[i], x[i + 1]
            if (rising and a0 <= xx <= a1 and a1 > a0) or ((not rising) and a0 >= xx >= a1 and a0 > a1):
                return (i + (xx - a0) / (a1 - a0)) * dt
        return None

    def ke_at(xx):
        for i in range(ipk, imax):
            if x[i] <= xx <= x[i + 1] and x[i + 1] > x[i]:
                f = (xx - x[i]) / (x[i + 1] - x[i]); vv = v[i] + (v[i + 1] - v[i]) * f
                return 0.5 * m * vv * vv
        return 0.0
    mech = a['mechanics']; xs = list(range(0, 95))
    x_peak = x[ipk]
    tab = dict(
        source='../action/action.json (cycle.carrier_mm, cycle.carrier_mps, mechanics, events, validation)',
        moving_mass_kg=round(m, 4), x_peak_mm=round(x_peak, 3), ke_peak_J=round(0.5 * m * v[ipk] ** 2, 4),
        x_full_mm=mech['full_stroke_mm'], x_unlock_mm=round(mech['unlock_carrier_mm'], 3), x_cock_mm=round(ap['cock_x'] * 1e3, 3),
        x_eject_mm=mech['eject_carrier_mm'], x_pick_mm=mech['feed_pick_carrier_mm'], x_hold_mm=mech['hold_open_mm'],
        x_mm=xs, ke_out_J=[round(ke_at(xx) if xx >= x_peak else 0.5 * m * v[ipk] ** 2, 4) for xx in xs],
        t_out_s=[round(t_at(xx, 0, imax, True) or 0.0, 6) for xx in xs],
        t_back_s=[round(t_at(xx, imax, len(x) - 1, False) or (len(x) - 1) * dt, 6) for xx in xs],
        t_max_travel_s=a['events']['times']['max_travel'], t_in_battery_s=a['events']['times']['in_battery'], t_ignition_s=a['events']['times']['ignition'],
        t_primer_s=a['events']['times']['primer_contact'], period_s=a['auto']['period_s'])
    t_out = lambda xx: t_at(xx, 0, imax, True)
    t_back = lambda xx: t_at(xx, imax, len(x) - 1, False)
    for nm in ('eject', 'pick', 'hold'): tab['ke_%s_J' % nm] = round(ke_at(tab['x_%s_mm' % nm]), 4)
    tab['eject_window_s'] = round(t_back(tab['x_eject_mm']) - t_out(tab['x_eject_mm']), 6)
    tab['feed_dwell_s'] = round(t_back(tab['x_pick_mm']) - t_out(tab['x_pick_mm']), 6)
    tab['ke_close_J'] = round(0.5 * m * v[[i for i in range(imax, len(x)) if x[i] <= tab['x_unlock_mm']][0]] ** 2, 4)
    tab['eject_speed_mps'] = abs(a['brass']['nominal']['before_deflector_vel'][0])
    tab['unlock_pressure_MPa'] = round(a['validation']['chamber_pressure_at_unlock']['at_unlock_complete'], 4)
    tab['case_drag_N'] = round(ap['case_mu'] * a['validation']['chamber_pressure_at_unlock']['at_unlock_complete'] * 1e6 * ap['case_wall_area'], 2)
    tab['round_mass_kg'] = ap['m_round']
    tab['action_time_s'] = round(a['events']['times']['bullet_passes_port'] - a['events']['times']['primer_fire'], 6)
    PARAMS['hammer_energy'][0] = round(a['validation']['hammer_energy']['sim'], 4)
    PARAMS['indent_nominal'][0] = round(a['validation']['primer_indent']['sim'], 4)
    PARAMS['primer_f0'][0] = ap['primer_f0']; PARAMS['primer_k'][0] = ap['primer_k']
    return tab


def setp():
    P.clear(); P.update({k: v[0] for k, v in PARAMS.items()})


# ================================================================== the model (mirrored line for line in hk416-malfunctions.js)
def mulberry32(seed):
    s = [seed & 0xFFFFFFFF]

    def rnd():
        s[0] = (s[0] + 0x6D2B79F5) & 0xFFFFFFFF
        z = s[0]
        z = ((z ^ (z >> 15)) * (z | 1)) & 0xFFFFFFFF
        z ^= (z + (((z ^ (z >> 7)) * (z | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rnd


def clamp(v, lo, hi): return lo if v < lo else (hi if v > hi else v)
def odds(ratio, k): return 1.0 / (1.0 + math.pow(ratio, k)) if ratio > 0 else 1.0


DEFAULT_CFG = dict(ammo='m855', dust=0.0, dry=False, ambientC=20.0, firingPinProtrusionMm=1.0, extractorGapMm=1.45, extractorSpringWeak=0.0, ejectorWeak=0.0,
                   bufferSpringWeak=0.0, pistonRingsWorn=0.0, magType='hk_steel', magSpringWear=0.0, magLipDamage=0.0, magRounds=30, magSeated=True, mode='military')


def new_state(cfg):
    c = dict(DEFAULT_CFG); c.update(cfg or {})
    return dict(cfg=c, clock=0.0, shots=0, nLube=0, nClean=0, heatK=0.0, chamber='live', feedway='clear', bolt='closed', carrierMm=0.0, hammer='cocked', bore='clear',
                selector='fire', status='ok', mag=dict(present=True, seated=bool(c['magSeated']), rounds=c['magRounds'] - 1, type=c['magType']), pending=None, last=None, lostRounds=0)


def clone(st):
    c = dict(st); c['mag'] = dict(st['mag']); return c


def conditions(st):
    """Dimensionless condition indices from the rifle state."""
    cfg = st['cfg']
    c = cfg['dust'] * (P['dust_residual'] + (1.0 - P['dust_residual']) * min(1.0, st['nLube'] / P['lube_interval']))
    f = min(2.0, st['nClean'] / P['clean_interval'])
    cold = clamp((20.0 - cfg['ambientC']) / (20.0 - P['cold_ref']), 0.0, 1.0)
    hot = clamp((cfg['ambientC'] - 20.0) / (P['hot_ref'] - 20.0), 0.0, 1.0)
    heat = clamp(st['heatK'] / P['heat_ref'], 0.0, 2.0)
    return dict(c=c, f=f, cold=cold, hot=hot, heat=heat, dry=1.0 if cfg['dry'] else 0.0)


def indent_energy(d_mm):
    d = d_mm * 1e-3
    return P['primer_f0'] * d + 0.5 * P['primer_k'] * d * d


def margins(st):
    """Every physical margin for the next shot, from the state. No randomness."""
    cfg = st['cfg']; q = conditions(st); am = AMMO[cfg['ammo']]; mg = MAGS[st['mag']['type']]
    # firing: delivered hammer energy against the primer's all-fire energy
    e = P['hammer_energy'] * max(0.05, 1.0 - P['eta_dust'] * q['c'] - P['eta_cold'] * q['cold'] - P['eta_foul'] * q['f'])
    prot = cfg['firingPinProtrusionMm']
    if prot < P['indent_nominal']: e *= indent_energy(max(prot, 0.0)) / indent_energy(P['indent_nominal'])
    r_fire = e / (P['primer_allfire'] * am['primer'])
    # carrier energy: shift of the action simulation's kinetic energy curve, and extra friction
    drive = am['drive'] * (1.0 - P['drive_cold'] * q['cold'] + P['drive_hot'] * q['hot']) * (1.0 - P['drive_rings'] * cfg['pistonRingsWorn'])
    shift = TAB['ke_peak_J'] * (drive - 1.0)
    drag = P['drag_dust'] * q['c'] + P['drag_foul'] * q['f'] + P['drag_dry'] * q['dry'] + P['drag_cold'] * q['cold']
    # extraction: rim and claw capacity against case drag
    gap = cfg['extractorGapMm']
    if gap > P['extractor_nogo']: claw = max(0.3, 1.0 - 0.7 * (gap - P['extractor_nogo']) / 0.41)
    elif gap < P['extractor_go']: claw = 0.3
    else: claw = 1.0
    claw *= 1.0 - 0.5 * cfg['extractorSpringWeak']
    dragc = TAB['case_drag_N'] * am['stick'] * (1.0 + P['stick_dust'] * q['c'] + P['stick_foul'] * q['f'] + P['stick_heat'] * q['heat'])
    r_ext = P['rim_strength'] * claw / dragc
    # ejection: speed factor of the case
    vfac = max(0.05, 1.0 - P['slow_dust'] * q['c'] - P['slow_foul'] * q['f']) * (1.0 - P['slow_ejector'] * cfg['ejectorWeak']) * (1.0 - P['slow_extractor'] * cfg['extractorSpringWeak'])
    t_clear = P['eject_clear_mm'] * 1e-3 / (TAB['eject_speed_mps'] * vfac)
    # feeding
    n = st['mag']['rounds']
    spring = (P['mag_spring_f0'] + P['mag_spring_per_round'] * n) * (1.0 - 0.5 * cfg['magSpringWear']) - mg['friction'] * q['c']
    t_rise = math.sqrt(2.0 * P['rise_mm'] * 1e-3 * (n * TAB['round_mass_kg'] + P['follower_mass']) / max(1.0, spring))
    growth = math.exp((P['feed_dust'] + mg['feed_dust_extra']) * q['c'])
    p_nose = min(0.5, P['clean_scale'] * P['p_nose_clean'] * mg['nose'] * am['feed'] * growth * (1.0 + P['lip_nose'] * cfg['magLipDamage']))
    p_two = min(0.3, P['clean_scale'] * P['p_two_clean'] * mg['two'] * growth * (1.0 + P['lip_two'] * cfg['magLipDamage']))
    # chambering
    work = P['chamber_work'] * (1.0 + P['chamber_dust'] * q['c'] + P['chamber_foul'] * q['f'])
    close = TAB['ke_close_J'] * (1.0 - P['buffer_weak'] * cfg['bufferSpringWeak'])
    return dict(q=q, r_fire=r_fire, p_dud=am['p_dud'], p_hang=am['p_hang'], p_squib=am['p_squib'], shift=shift, drag=drag, r_ext=r_ext, claw=claw, t_clear=t_clear,
                t_rise=t_rise, p_nose=p_nose, p_two=p_two, work=work, close=close, n=n, feeds=bool(st['mag']['present'] and n > 0), seated=bool(st['mag']['seated']),
                mag_in=bool(st['mag']['present']))


def travel(M, e):
    """Carrier travel (mm) for an energy deviation e (J): where the shifted, dragged kinetic energy curve reaches zero."""
    xs = TAB['x_mm']; ke = TAB['ke_out_J']; xp = TAB['x_peak_mm']; n = len(xs)
    k_last = ke[n - 1] + M['shift'] + e - M['drag'] * (xs[n - 1] - xp) * 1e-3
    if k_last > 0: return TAB['x_full_mm']
    prev_x = xp; prev_k = TAB['ke_peak_J'] + M['shift'] + e
    if prev_k <= 0: return xp
    for i in range(n):
        if xs[i] <= xp: continue
        k = ke[i] + M['shift'] + e - M['drag'] * (xs[i] - xp) * 1e-3
        if k <= 0: return prev_x + (xs[i] - prev_x) * prev_k / (prev_k - k)
        prev_x = xs[i]; prev_k = k
    return TAB['x_full_mm']


def cycle_probs(M, xm):
    """Ordered, mutually exclusive outcome probabilities of the cycle after a fired shot, given carrier travel xm."""
    full = TAB['x_full_mm']; out = []; alive = 1.0
    p = odds(M['r_ext'], P['k_extract'])
    fed_behind = M['feeds'] and M['seated'] and xm >= TAB['x_pick_mm']
    out.append(('double_feed' if fed_behind else 'failure_to_extract', 'stuck', alive * p)); alive *= 1.0 - p
    if xm < TAB['x_eject_mm']:
        out.append(('stovepipe', 'rechambered_case', alive)); return out
    w = TAB['eject_window_s'] * math.sqrt(max(0.0, (xm - TAB['x_eject_mm']) / (full - TAB['x_eject_mm'])))
    p = odds(w / M['t_clear'], P['k_eject'])
    out.append(('stovepipe', 'eject', alive * p)); alive *= 1.0 - p
    if M['mag_in'] and M['n'] > 0:
        if xm < TAB['x_pick_mm'] or not M['seated']:
            out.append(('failure_to_feed', 'bolt_over_empty_chamber', alive)); return out
        dwell = TAB['feed_dwell_s'] * math.sqrt(max(0.0, (xm - TAB['x_pick_mm']) / (full - TAB['x_pick_mm'])))
        p = odds(dwell / M['t_rise'], P['k_feed_time'])
        out.append(('bolt_override', 'override', alive * p)); alive *= 1.0 - p
        out.append(('failure_to_feed', 'nose_jam', alive * M['p_nose'])); alive *= 1.0 - M['p_nose']
        out.append(('double_feed', 'two_live', alive * M['p_two'])); alive *= 1.0 - M['p_two']
        p = odds(M['close'] * min(1.0, xm / full) / M['work'], P['k_chamber'])
        out.append(('failure_to_feed', 'failure_to_chamber', alive * p)); alive *= 1.0 - p
    elif M['mag_in']:
        p = 1.0 if xm < TAB['x_hold_mm'] else P['p_catch']
        out.append(('failure_to_lock_back', 'closed_on_empty', alive * p)); alive *= 1.0 - p
    out.append(('fired', '', alive))
    return out


def fire_probs(M):
    pl = odds(M['r_fire'], P['k_fire'])
    return [('squib', M['p_squib']), ('hangfire', M['p_hang']), ('dud', M['p_dud']), ('light_strike', (1.0 - M['p_squib'] - M['p_hang'] - M['p_dud']) * pl)]


def probabilities(st, grid=64):
    """Analytic per-round probability of each first outcome for the next shot from this state (integrates the energy scatter)."""
    M = margins(st); out = {}
    add = lambda k, p: out.__setitem__(k, out.get(k, 0.0) + p)
    pf = 0.0
    for k, p in fire_probs(M):
        pf += p
        if k in ('dud', 'light_strike'): add('failure_to_fire:' + k, p)
        elif k == 'squib': add('squib:lodged', p)
    ph = M['p_hang']; fired = 1.0 - pf + ph            # a hangfire still cycles
    add('hangfire:delayed', ph)
    # the energy scatter: full stroke above u_full; below it, integrate band by band between the travel thresholds
    xs = TAB['x_mm']; s = P['energy_scatter']; xp = TAB['x_peak_mm']
    ucut = [0.0]
    for x, ke in ((TAB['x_eject_mm'], TAB['ke_eject_J']), (TAB['x_pick_mm'], TAB['ke_pick_J']), (TAB['x_hold_mm'], TAB['ke_hold_J']), (xs[-1], TAB['ke_out_J'][-1])):
        ucut.append(1.0 / (1.0 + math.exp((ke + M['shift'] - M['drag'] * (x - xp) * 1e-3) / s)))
    u_full = ucut[4]
    acc = {}
    for kk, vv, p in cycle_probs(M, TAB['x_full_mm']):
        key = kk + (':' + vv if vv else ''); acc[key] = acc.get(key, 0.0) + p * (1.0 - u_full)
    g = max(2, grid // 4)
    for b in range(4):
        lo, hi = ucut[b], ucut[b + 1]
        if hi - lo < 1e-18: continue
        for i in range(g):
            u = lo + (hi - lo) * (i + 0.5) / g; e = s * math.log(u / (1.0 - u))
            for kk, vv, p in cycle_probs(M, travel(M, e)):
                key = kk + (':' + vv if vv else ''); acc[key] = acc.get(key, 0.0) + p * (hi - lo) / g
    for key, p in acc.items():
        if key == 'fired': continue
        if key == 'double_feed:stuck': key = 'double_feed:stuck_case_plus_round'
        elif key == 'failure_to_extract:stuck': key = 'failure_to_extract:any'
        elif key == 'stovepipe:eject': key = 'stovepipe:caught'
        add(key, fired * p)
    out['fired'] = fired * acc.get('fired', 0.0)
    return out


# ---------------------------------------------------------------- the rifle as a state machine
STOP = dict(nose_jam=(45.5, 22.5), stovepipe=(27.5, 22.5), case_loose=(45.5, 22.5), round_behind_case=(68.0, 22.5), two_rounds=(50.0, 22.5), round_over_bolt=(50.0, 22.5))
OOB = (6.0, 9.0)
PORT = dict(nose_jam='round_nose_up', stovepipe='case_in_port', case_loose='case_loose_in_port', round_behind_case='brass_and_round', two_rounds='two_rounds',
            round_over_bolt='round_above_bolt')


def ready(st):
    return st['status'] == 'ok' and st['chamber'] == 'live' and st['bolt'] == 'closed' and st['feedway'] == 'clear' and st['bore'] == 'clear' and st['hammer'] == 'cocked' \
        and st['selector'] == 'fire' and st['pending'] is None


def observe(st):
    """What the shooter can see and feel, without opening anything."""
    if st['feedway'] != 'clear' and st['bolt'] != 'held_open': port = PORT[st['feedway']]
    elif st['bolt'] == 'held_open': port = 'bolt_held_open'
    elif st['bolt'] == 'out_of_battery': port = 'out_of_battery'
    else: port = 'closed'
    last = st['last'] or {}
    return dict(port=port, mag='in' if st['mag']['present'] else 'out', handle='bound' if st['feedway'] == 'round_over_bolt' else 'free',
                report=last.get('report', 'none'), trigger=last.get('trigger', 'none'), selector=st['selector'], ready=ready(st))


def diagnose(st, attempts=0):
    """The procedure a shooter should start from what is visible. attempts = immediate actions already tried on this stoppage."""
    o = observe(st)
    for rule in C.DIAGNOSIS:
        if all(o.get(k) == v for k, v in rule['see'].items()):
            pr = rule['procedure']
            if pr == 'immediate_action':
                if attempts >= 2: return 'remedial_clear'
                if st['cfg']['mode'] == 'range' and attempts == 0 and o['trigger'] == 'click': return 'misfire_range'
            return pr
    return 'remedial_clear'


def _heat(st, dt):
    if dt > 0: st['heatK'] *= math.exp(-dt / P['heat_tau'])


def advance(st, dt):
    """Let time pass; a pending hangfire fires if its time comes with the bolt still locked."""
    ev = []
    pd = st['pending']
    if pd is not None and st['clock'] + dt >= pd['at']:
        _heat(st, pd['at'] - st['clock']); dt -= pd['at'] - st['clock']; st['clock'] = pd['at']; st['pending'] = None
        r = _cycle(st, pd['M'], pd['ue'], pd['uc'], pd['ud'])
        r['delayS'] = pd['delay']; ev.append(r)
    _heat(st, dt); st['clock'] += dt
    return ev


def _stop(st, feedway):
    st['feedway'] = feedway; st['bolt'] = 'blocked'; st['carrierMm'] = STOP[feedway][0]


def _cycle(st, M, ue, uc, ud):
    """The shot has fired: run the operating cycle and leave the rifle in the state it ends in."""
    s = P['energy_scatter']; e = s * math.log(ue / (1.0 - ue)) if 0.0 < ue < 1.0 else 0.0
    xm = travel(M, e)
    st['shots'] += 1; st['nLube'] += 1; st['nClean'] += 1; st['heatK'] += P['heat_per_shot']
    st['hammer'] = 'cocked' if xm >= TAB['x_cock_mm'] else 'down'
    acc = 0.0; kind = 'fired'; var = ''; base = 0.0; pk = 0.0
    for kk, vv, p in cycle_probs(M, xm):
        if uc < acc + p: kind, var, base, pk = kk, vv, acc, p; break
        acc += p
    frac = (uc - base) / pk if pk > 0 else 0.0     # where in this outcome's slice the draw fell: reused to pick the variant
    mag = st['mag']; res = dict(outcome=kind, variant=var, travelMm=round(xm, 3), report='bang', trigger='bang', shortStroke=xm < TAB['x_full_mm'])
    if kind == 'fired':
        if M['mag_in'] and M['n'] > 0: mag['rounds'] -= 1; st['chamber'] = 'live'; st['bolt'] = 'closed'; st['carrierMm'] = 0.0
        elif M['mag_in']: st['chamber'] = 'empty'; st['bolt'] = 'held_open'; st['carrierMm'] = TAB['x_hold_mm']
        else: st['chamber'] = 'empty'; st['bolt'] = 'closed'; st['carrierMm'] = 0.0
    elif var == 'stuck':
        torn = frac < P['p_torn'] * min(1.0, M['claw'])
        st['chamber'] = 'stuck_torn' if torn else 'stuck'
        if kind == 'double_feed':
            res['variant'] = 'stuck_case_plus_round'; mag['rounds'] -= 1; _stop(st, 'round_behind_case')
        else:
            res['variant'] = 'torn_rim' if torn else 'claw_slip'
            if M['mag_in'] and M['n'] == 0 and xm >= TAB['x_hold_mm']: st['bolt'] = 'held_open'; st['carrierMm'] = TAB['x_hold_mm']
            else: st['bolt'] = 'closed'; st['carrierMm'] = 0.0
        res['rim'] = 'torn' if torn else 'intact'
    elif kind == 'stovepipe':
        if var == 'rechambered_case': st['chamber'] = 'fired'; st['bolt'] = 'closed'; st['carrierMm'] = 0.0
        else:
            st['chamber'] = 'empty'
            if frac < P['p_stove']: res['variant'] = 'stovepipe'; _stop(st, 'stovepipe')
            else: res['variant'] = 'case_in_receiver'; _stop(st, 'case_loose')
    elif kind == 'failure_to_feed':
        if var == 'bolt_over_empty_chamber': st['chamber'] = 'empty'; st['bolt'] = 'closed'; st['carrierMm'] = 0.0
        elif var == 'nose_jam': st['chamber'] = 'empty'; _stop(st, 'nose_jam')
        else: mag['rounds'] -= 1; st['chamber'] = 'live'; st['bolt'] = 'out_of_battery'; st['carrierMm'] = OOB[0]
    elif kind == 'bolt_override':
        st['chamber'] = 'empty'; mag['rounds'] -= 1; _stop(st, 'round_over_bolt')
    elif kind == 'double_feed':
        st['chamber'] = 'empty'; mag['rounds'] -= min(2, mag['rounds']); _stop(st, 'two_rounds')
    elif kind == 'failure_to_lock_back':
        st['chamber'] = 'empty'; st['bolt'] = 'closed'; st['carrierMm'] = 0.0
    res['stoppage'] = kind != 'fired'
    st['last'] = dict(report='bang', trigger='bang')
    return res


def fire(st, rng, force=None):
    """One press of the trigger. Returns what happened; the state is left as the shooter finds it."""
    if st['status'] != 'ok': return dict(outcome='out_of_service', stoppage=False, fired=False)
    if st['selector'] == 'safe': return dict(outcome='on_safe', stoppage=False, fired=False)
    if st['pending'] is not None: return dict(outcome='hangfire_pending', stoppage=False, fired=False)
    if st['bolt'] != 'closed' or st['hammer'] != 'cocked':
        st['last'] = dict(report='none', trigger='dead')
        return dict(outcome='dead_trigger', stoppage=True, fired=False, report='none', trigger='dead')
    if st['chamber'] != 'live':
        st['hammer'] = 'down'; st['last'] = dict(report='none', trigger='click')
        return dict(outcome='click', variant=st['chamber'], stoppage=True, fired=False, report='none', trigger='click')
    if st['bore'] != 'clear':
        st['status'] = 'out_of_service'; st['last'] = dict(report='bang', trigger='bang')
        return dict(outcome='fired_into_obstruction', stoppage=True, fired=True, report='bang',
                    note='a round was fired behind a lodged bullet: the barrel is treated as destroyed and the rifle is out of service')
    M = margins(st)
    uf, ue, uc, ud, ux = rng(), rng(), rng(), rng(), rng()
    kind = None
    if force:
        fk, _, fv = force.partition(':')
        return _forced(st, M, fk, fv, ue, ud, ux)
    acc = 0.0
    for k, p in fire_probs(M):
        if uf < acc + p: kind = k; break
        acc += p
    if kind == 'squib': return _squib(st, ud)
    if kind in ('dud', 'light_strike'):
        st['hammer'] = 'down'; st['chamber'] = 'dud'; st['last'] = dict(report='none', trigger='click')
        return dict(outcome='failure_to_fire', variant=kind, stoppage=True, fired=False, report='none', trigger='click')
    if kind == 'hangfire': return _hang(st, M, ue, uc, ud, ux)
    r = _cycle(st, M, ue, uc, ud); r['fired'] = True
    return r


def _squib(st, ud):
    st['hammer'] = 'down'; st['chamber'] = 'fired'; st['bore'] = 'obstructed'; st['shots'] += 1; st['nLube'] += 1; st['nClean'] += 1
    st['last'] = dict(report='pop', trigger='pop')
    return dict(outcome='squib', variant='lodged', stoppage=True, fired=False, report='pop', trigger='pop',
                lodgedMm=round(P['squib_min_mm'] + (P['squib_max_mm'] - P['squib_min_mm']) * ud, 1))


def _hang(st, M, ue, uc, ud, ux, z=None):
    if z is None: z = math.sqrt(-2.0 * math.log(max(ud, 1e-12))) * math.cos(2.0 * math.pi * ux)
    delay = P['hang_median'] * math.exp(P['hang_sigma'] * z)
    st['hammer'] = 'down'; st['last'] = dict(report='none', trigger='click')
    st['pending'] = dict(at=st['clock'] + delay, delay=delay, M=M, ue=ue, uc=uc, ud=ud)
    res = dict(outcome='hangfire', variant='delayed', stoppage=True, fired=False, delayS=delay, perceptible=delay >= P['hang_perceptible'], report='none', trigger='click')
    if delay < P['hang_perceptible']:          # too short to notice or act on: the shot simply goes
        ev = advance(st, delay); res['then'] = ev[0]; res['fired'] = True
        res['stoppage'] = ev[0]['stoppage']
    return res


def _forced(st, M, kind, var, ue, ud, ux):
    """Demonstration only: make the next shot produce a chosen stoppage. Uses the same state changes as the real path."""
    if kind == 'squib': return _squib(st, ud)
    if kind == 'failure_to_fire':
        st['hammer'] = 'down'; st['chamber'] = 'dud'; st['last'] = dict(report='none', trigger='click')
        return dict(outcome=kind, variant=var or 'dud', stoppage=True, fired=False, report='none', trigger='click', forced=True)
    if kind == 'hangfire':
        r = _hang(st, M, ue, 0.999999, ud, ux, 1.0 + 1.5 * ud); r['forced'] = True; return r   # 0.27 to 1.6 s: long enough to notice
    full = TAB['x_full_mm']; xm = full
    if (kind, var) in (('stovepipe', 'rechambered_case'),): xm = TAB['x_eject_mm'] - 5.0
    if (kind, var) == ('failure_to_feed', 'bolt_over_empty_chamber'): xm = TAB['x_pick_mm'] - 3.0
    if kind == 'failure_to_lock_back': xm = TAB['x_hold_mm'] - 2.0
    want = dict(failure_to_extract=('failure_to_extract', 'stuck'), double_feed=('double_feed', 'stuck' if var != 'two_live' else 'two_live'), stovepipe=('stovepipe', 'eject'),
                bolt_override=('bolt_override', 'override'), failure_to_feed=('failure_to_feed', var or 'nose_jam'), failure_to_lock_back=('failure_to_lock_back', 'closed_on_empty'))[kind]
    if (kind, var) == ('stovepipe', 'rechambered_case'): want = ('stovepipe', 'rechambered_case')
    if kind == 'failure_to_extract': M = dict(M); M['feeds'] = False
    acc = 0.0; uc = None
    for kk, vv, p in cycle_probs(M, xm):
        if (kk, vv) == want:
            fr = 0.5
            if var == 'torn_rim': fr = 0.0
            elif var in ('claw_slip', 'stuck_case_plus_round'): fr = 0.99
            elif var == 'stovepipe' or (kind == 'stovepipe' and not var): fr = 0.0
            elif var == 'case_in_receiver': fr = 0.99
            uc = acc + p * fr; break
        acc += p
    if uc is None: return dict(outcome='not_possible_now', stoppage=False, fired=False, note='this stoppage cannot arise from the present state (for example no round left to feed)')
    # give the forced energy: choose ue so that travel() returns xm
    if xm < full:
        lo, hi = -40.0, 0.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if travel(M, mid) < xm: lo = mid
            else: hi = mid
        ue2 = 1.0 / (1.0 + math.exp(-lo / P['energy_scatter']))
    else: ue2 = 0.5 if travel(M, 0.0) >= full else 0.999999
    r = _cycle(st, M, ue2, uc, ud); r['fired'] = True; r['forced'] = True
    return r


def _by_hand(st, u1, u2, ev):
    """Carrier drawn fully to the rear by hand: what comes out."""
    mag = st['mag']; fw = st['feedway']
    if fw in ('stovepipe', 'case_loose'):
        if u1 < P['rack_clears_port']: st['feedway'] = 'clear'; ev.append('case_out')
        else: ev.append('case_still_trapped')
    elif fw == 'nose_jam':
        if (not mag['present']) or u1 < P['rack_clears_nose']:
            st['feedway'] = 'clear'; ev.append('round_out'); st['lostRounds'] += 1
            if mag['present']: mag['rounds'] = max(0, mag['rounds'] - 1)
        else: ev.append('round_still_jammed')
    elif fw in ('round_behind_case', 'two_rounds'):
        if mag['present']: ev.append('rounds_pinned_magazine_must_come_out')
        else: st['feedway'] = 'clear'; ev.append('rounds_out'); st['lostRounds'] += 2 if fw == 'two_rounds' else 1
    if st['feedway'] == 'clear':
        ch = st['chamber']
        if ch == 'live': st['chamber'] = 'empty'; ev.append('live_round_ejected'); st['lostRounds'] += 1
        elif ch == 'dud': st['chamber'] = 'empty'; ev.append('dud_ejected')
        elif ch == 'fired': st['chamber'] = 'empty'; ev.append('case_ejected')
        elif ch == 'stuck':
            if u2 < P['rack_extracts']: st['chamber'] = 'empty'; ev.append('stuck_case_extracted')
            else: ev.append('case_still_in_chamber')
        elif ch == 'stuck_torn': ev.append('case_still_in_chamber')
    st['hammer'] = 'cocked'


def _close(st, ev):
    """The bolt goes forward under the buffer spring."""
    mag = st['mag']
    if st['feedway'] != 'clear':
        st['bolt'] = 'blocked'; st['carrierMm'] = STOP[st['feedway']][0]; ev.append('bolt_stopped'); return
    feeds = mag['present'] and mag['seated'] and mag['rounds'] > 0
    if st['chamber'] in ('stuck', 'stuck_torn'):
        if feeds: mag['rounds'] -= 1; _stop(st, 'round_behind_case'); ev.append('round_driven_into_stuck_case')
        elif mag['present'] and mag['rounds'] == 0: st['bolt'] = 'held_open'; st['carrierMm'] = TAB['x_hold_mm']; ev.append('bolt_locked_open')
        else: st['bolt'] = 'closed'; st['carrierMm'] = 0.0; ev.append('bolt_closed_on_case')
    elif st['chamber'] == 'empty':
        if feeds: mag['rounds'] -= 1; st['chamber'] = 'live'; st['bolt'] = 'closed'; st['carrierMm'] = 0.0; ev.append('round_chambered')
        elif mag['present'] and mag['seated'] and mag['rounds'] == 0: st['bolt'] = 'held_open'; st['carrierMm'] = TAB['x_hold_mm']; ev.append('bolt_locked_open')
        else: st['bolt'] = 'closed'; st['carrierMm'] = 0.0; ev.append('bolt_closed_on_empty_chamber')
    else: st['bolt'] = 'closed'; st['carrierMm'] = 0.0; ev.append('bolt_closed')


def act(st, name, rng, args=None):
    """One clearing action. Always draws two random numbers. Returns {ok, events, seconds}."""
    args = args or {}; A = C.ACTIONS[name]; ev = []; ok = True
    u1, u2 = rng(), rng()
    secs = float(args.get('seconds', A['time_s']))
    if st['status'] == 'out_of_service': return dict(action=name, ok=False, events=['out_of_service'], seconds=0.0)
    pd = st['pending']
    if pd is not None and name in ('rack', 'lock_back') and st['clock'] < pd['at']:
        st['status'] = 'out_of_service'; st['pending'] = None
        return dict(action=name, ok=False, events=['hangfire_fired_with_the_action_open'], seconds=0.0,
                    note='the round fired while the bolt was being opened: the reason for waiting on a misfire. The simulation stops here')
    for r in advance(st, secs): ev.append('hangfire_fired' + ('' if not r['stoppage'] else ':' + r['outcome']))
    mag = st['mag']
    if name == 'tap':
        if mag['present']: mag['seated'] = True
        else: ok = False
    elif name == 'rack':
        if st['feedway'] == 'round_over_bolt': ok = False; ev.append('charging_handle_bound')
        else: _by_hand(st, u1, u2, ev); _close(st, ev)
    elif name == 'lock_back':
        if st['feedway'] == 'round_over_bolt': ok = False; ev.append('charging_handle_bound')
        else: _by_hand(st, u1, u2, ev); st['bolt'] = 'held_open'; st['carrierMm'] = TAB['x_hold_mm']
    elif name == 'release_bolt':
        if st['bolt'] != 'held_open': ok = False
        else: _close(st, ev)
    elif name == 'strip_mag':
        if mag['present']: mag['present'] = False; mag['seated'] = False
        else: ok = False
    elif name == 'insert_mag':
        t = args.get('type', st['cfg']['magType'])
        st['mag'] = dict(present=True, seated=True, rounds=int(args.get('rounds', MAGS[t]['capacity'])), type=t)
    elif name == 'sweep_case':
        if st['feedway'] in ('stovepipe', 'case_loose'): st['feedway'] = 'clear'; ev.append('case_out'); _close(st, ev)
        else: ok = False
    elif name in ('handle_strike', 'hold_bolt_strike'):
        if st['feedway'] != 'round_over_bolt': ok = False
        else:
            p = P['hold_strike_frees'] if name == 'hold_bolt_strike' else (P['strike_frees_mag_in'] if mag['present'] else P['strike_frees'])
            if u1 < p: st['feedway'] = 'clear'; st['lostRounds'] += 1; ev.append('round_freed'); st['hammer'] = 'cocked'; _close(st, ev)
            else: ok = False; ev.append('round_still_wedged')
    elif name == 'forward_assist':
        if st['bolt'] != 'out_of_battery': ok = False
        elif u1 < P['assist_seats']: st['bolt'] = 'closed'; st['carrierMm'] = 0.0; ev.append('bolt_closed')
        else: ok = False; ev.append('bolt_did_not_close')
    elif name == 'safe':
        if st['hammer'] == 'cocked': st['selector'] = 'safe'
        else: ok = False; ev.append('selector_will_not_turn_hammer_not_cocked')
    elif name == 'selector_fire': st['selector'] = 'fire'
    elif name == 'inspect_chamber':
        if st['bolt'] != 'held_open': ok = False
        else: ev.append('chamber:' + st['chamber']); ev.append('feedway:' + st['feedway'])
    elif name == 'check_bore':
        if st['bolt'] != 'held_open' or st['chamber'] != 'empty': ok = False
        else: ev.append('bore:' + st['bore'])
    elif name == 'rod':
        if st['bolt'] != 'held_open' or mag['present']: ok = False
        else:
            if st['chamber'] in ('stuck', 'stuck_torn'): st['chamber'] = 'empty'; ev.append('case_pushed_out')
            if st['bore'] == 'obstructed': st['bore'] = 'clear'; st['status'] = 'needs_inspection'; ev.append('bullet_driven_out_barrel_needs_inspection')
    elif name in ('wait', 'reassess'): pass
    return dict(action=name, ok=ok, events=ev, seconds=secs)


def _cond(st, name):
    if name == 'mag_in': return st['mag']['present']
    if name == 'handle_bound': return st['feedway'] == 'round_over_bolt'
    if name == 'bolt_open': return st['bolt'] == 'held_open'
    if name == 'bolt_closed': return st['bolt'] != 'held_open'
    return True


def run_procedure(st, pid, rng):
    """Run one procedure's steps. Returns {procedure, steps, seconds, end, next}."""
    pr = C.PROCEDURES[pid]; log = []; secs = 0.0; nxt = None
    for s in pr['steps']:
        if 'if' in s and not _cond(st, s['if']): continue
        r = act(st, s['action'], rng, s.get('args')); log.append(r); secs += r['seconds']
        if st['status'] == 'out_of_service': break
        if 'branch' in s and (st['chamber'] != 'empty' or st['feedway'] != 'clear'): nxt = s['branch']['chamber_not_clear']; break
    if st['status'] != 'ok': end = st['status']
    elif pr['end'] == 'made_safe': end = 'made_safe'
    elif ready(st): end = 'ready'
    else: end = 'not_cleared'
    return dict(procedure=pid, steps=log, seconds=secs, end=end, next=nxt)


def clear(st, rng, max_procedures=8):
    """Diagnose and clear until the rifle is ready, made safe, or out of the shooter's hands. Returns {procedures, seconds, end, klass}."""
    done = []; secs = 0.0; ia = 0; nxt = None; end = 'ready' if ready(st) else 'not_cleared'
    while not ready(st) and len(done) < max_procedures:
        pid = nxt or diagnose(st, ia)
        if pid in ('immediate_action', 'misfire_range'): ia += 1
        r = run_procedure(st, pid, rng); done.append(pid); secs += r['seconds']; end = r['end']; nxt = r['next']
        if end in ('made_safe', 'out_of_service', 'needs_inspection'): break
        if end == 'not_cleared' and nxt is None and pid not in ('immediate_action', 'misfire_range', 'reload'): nxt = C.PROCEDURES[pid]['fallback']
    armourer = end != 'ready' or 'stuck_case_rod' in done
    return dict(procedures=done, seconds=secs, end=end, klass=3 if armourer else (1 if secs <= 10.0 else 2))


def maintain(st, what):
    if what in ('wipe_lube', 'clean'): st['nLube'] = 0
    if what == 'clean': st['nClean'] = 0


def run_protocol(seed, rounds, cfg, shot_dt=2.0, cycle=120, cycle_rest=600.0, lube=600, clean=1200):
    """Fire `rounds` rounds from one rifle, clearing every stoppage as a shooter would, maintaining it on the dust test's schedule.
    Returns counts by type and variant, by stoppage class, and the round numbers of the stoppages."""
    rng = mulberry32(seed); st = new_state(cfg)
    cnt = {}; klass = {1: 0, 2: 0, 3: 0}; at = []; events = 0; replaced = 0; guard = 0
    while st['shots'] < rounds and guard < rounds * 4:
        guard += 1
        if not ready(st):
            cl = clear(st, rng)
            if cl['end'] != 'ready':
                keep = (st['shots'], st['nLube'], st['nClean'], st['heatK'], st['clock']); st = new_state(cfg)
                st['shots'], st['nLube'], st['nClean'], st['heatK'], st['clock'] = keep; replaced += 1
            continue
        n0 = st['shots']
        r = fire(st, rng)
        advance(st, shot_dt)
        if r.get('stoppage') or not ready(st):
            key = r['outcome'] + (':' + r['variant'] if r.get('variant') else '')
            if r['outcome'] == 'hangfire' and r.get('then') is not None:
                t = r['then']; key = t['outcome'] + (':' + t['variant'] if t.get('variant') else '') if t['stoppage'] else None
            last_empty = (not r.get('stoppage')) and st['bolt'] == 'held_open' and st['chamber'] == 'empty'
            cl = clear(st, rng)
            if key is not None and not last_empty:
                cnt[key] = cnt.get(key, 0) + 1; klass[cl['klass']] += 1; at.append(st['shots']); events += 1
            if cl['end'] != 'ready':
                keep = (st['shots'], st['nLube'], st['nClean'], st['heatK'], st['clock']); st = new_state(cfg)
                st['shots'], st['nLube'], st['nClean'], st['heatK'], st['clock'] = keep; replaced += 1
        if st['shots'] != n0:
            if st['shots'] % clean == 0: maintain(st, 'clean')
            elif st['shots'] % lube == 0: maintain(st, 'wipe_lube')
            if st['shots'] % cycle == 0: advance(st, cycle_rest)
    return dict(seed=seed, rounds=st['shots'], stoppages=events, counts=cnt, klass=klass, at=at, replaced=replaced, lostRounds=st['lostRounds'])


def edt_category(key):
    k, _, v = key.partition(':')
    if k == 'failure_to_feed': return 'FTC' if v == 'failure_to_chamber' else 'FFD'
    if k == 'bolt_override': return 'FFD'
    if k == 'double_feed': return 'FFD' if v == 'two_live' else 'FXT'
    if k in ('failure_to_fire', 'hangfire', 'squib', 'click'): return 'FFR'
    if k == 'failure_to_extract': return 'FXT'
    if k == 'stovepipe': return 'FEJ'
    if k == 'failure_to_lock_back': return 'FBR'
    return 'OTH'


# ================================================================== calibration
def protocol_heat(shot_dt=2.0, cycle=120, rest=600.0):
    """Barrel temperature rise at each shot of a firing cycle, once the schedule has settled."""
    h = 0.0; out = [0.0] * cycle
    for _ in range(6):
        for i in range(cycle):
            out[i] = h; h += P['heat_per_shot']; h *= math.exp(-shot_dt / P['heat_tau'])
        h *= math.exp(-rest / P['heat_tau'])
    return out


def expected_protocol(cfg, rounds=6000, lube=600, clean=1200, block=20, cycle=120, grid=16):
    """Expected stoppages by dust-test category for one rifle over the protocol, from the analytic per-round probabilities.
    Ignores the knock-on effects of a stoppage."""
    out = {}; cap = MAGS[cfg.get('magType', 'hk_steel')]['capacity']; heat = protocol_heat(cycle=cycle)
    for b in range(0, clean, block):
        st = new_state(cfg); st['nLube'] = (b + block // 2) % lube; st['nClean'] = b + block // 2; st['heatK'] = heat[(b + block // 2) % cycle]
        for n in range(cap):
            st['mag']['rounds'] = n
            pr = probabilities(st, grid=grid)
            for k, p in pr.items():
                if k == 'fired': continue
                cat = edt_category(k); out[cat] = out.get(cat, 0.0) + p * block / cap * (rounds / clean)
                out[k] = out.get(k, 0.0) + p * block / cap * (rounds / clean)
    return out


def bisect(f, lo, hi, n=50):
    flo = f(lo)
    assert (f(hi) > 0) != (flo > 0), 'calibration target not bracketed'

    for _ in range(n):
        mid = 0.5 * (lo + hi); fm = f(mid)
        if (fm > 0) == (flo > 0): lo, flo = mid, fm
        else: hi = mid
    return 0.5 * (lo + hi)


def calibrate():
    for k in ('eta_dust', 'drag_dust', 'stick_dust', 'slow_dust', 'feed_dust', 'chamber_dust'): PARAMS[k][0] = 0.0
    MAGS['gi_aluminium']['feed_dust_extra'] = 0.0
    for k in ('k_fire', 'k_extract', 'k_eject', 'k_feed_time', 'k_chamber'): PARAMS[k][0] = 1.0
    PARAMS['clean_scale'][0] = 1.0
    setp()
    kset = lambda name, ratio, p: PARAMS[name].__setitem__(0, math.log(1.0 / p - 1.0) / math.log(ratio))

    def clean(scale):
        """Set the steepness of each margin curve so a clean, cool, freshly lubricated rifle has scale x its target probability."""
        st = new_state({}); M = margins(st)
        kset('k_fire', M['r_fire'], scale * P['p_light_clean'])
        kset('k_extract', M['r_ext'], scale * P['p_fxt_clean'])
        kset('k_eject', TAB['eject_window_s'] / M['t_clear'], scale * P['p_fej_clean'])
        kset('k_chamber', M['close'] / M['work'], scale * P['p_ftc_clean'])
        PARAMS['clean_scale'][0] = scale; setp()

        def mean_override(k):
            P['k_feed_time'] = k; tot = 0.0
            for n in range(1, 30):
                st['mag']['rounds'] = n; tot += odds(TAB['feed_dwell_s'] / margins(st)['t_rise'], k)
            return tot / 30.0 - scale * P['p_override_clean']
        PARAMS['k_feed_time'][0] = bisect(mean_override, 1.0, 60.0); setp()
    scale = 1.0
    for _ in range(5):          # the protocol (fouling between cleanings, a warm barrel) adds to the fresh-rifle rates: scale them so the protocol gives the target
        clean(scale)
        e = expected_protocol({}, block=60); tot = sum(v for k, v in e.items() if k.isupper())
        scale *= (6000.0 / CLEAN_TARGET_MRBS) / tot
    clean(scale)
    dust = dict(dust=1.0); n = EDT['rifles']

    def solve(name, cat, target, lo, hi, cfg=dust):
        def f(v):
            P[name] = v
            return n * expected_protocol(cfg).get(cat, 0.0) - target
        PARAMS[name][0] = bisect(f, lo, hi, 20); setp()
    solve('drag_dust', 'FBR', TARGET['FBR'], 0.0, 60.0)
    solve('eta_dust', 'FFR', TARGET['FFR'], 0.0, 0.5)
    solve('stick_dust', 'FXT', TARGET['FXT'], 0.0, 5.0)
    solve('slow_dust', 'FEJ', TARGET['FEJ'], 0.0, 0.9)
    solve('chamber_dust', 'FTC', TARGET['FTC'], 0.0, 5.0)
    solve('feed_dust', 'FFD', TARGET['FFD'], 0.0, 12.0)
    steel = n * expected_protocol(dust)['FFD']

    def f_al(v):
        MAGS['gi_aluminium']['feed_dust_extra'] = v
        return n * expected_protocol(dict(dust=1.0, magType='gi_aluminium'))['FFD'] - steel - TARGET['aluminium_extra_feed']
    MAGS['gi_aluminium']['feed_dust_extra'] = bisect(f_al, 0.0, 6.0, 20)
    for k in ('clean_scale', 'k_fire', 'k_extract', 'k_eject', 'k_feed_time', 'k_chamber', 'eta_dust', 'drag_dust', 'stick_dust', 'slow_dust', 'feed_dust', 'chamber_dust'):
        PARAMS[k][0] = float('%.6g' % PARAMS[k][0])
    MAGS['gi_aluminium']['feed_dust_extra'] = float('%.6g' % MAGS['gi_aluminium']['feed_dust_extra'])
    setp()


# ================================================================== checks
def poisson_interval(k):
    """Central 95 percent interval for a Poisson mean given one count k (Garwood, via the Wilson-Hilferty approximation)."""
    lo = 0.0 if k == 0 else k * (1 - 1 / (9.0 * k) - 1.96 / (3 * math.sqrt(k))) ** 3
    hi = (k + 1) * (1 - 1 / (9.0 * (k + 1)) + 1.96 / (3 * math.sqrt(k + 1))) ** 3
    return [round(lo, 2), round(hi, 2)]


def binom_accept(p, n, c):
    """P(at most c defects in n) for defect probability p."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(c + 1))


def sum_runs(runs):
    tot = dict(rounds=0, stoppages=0, counts={}, klass={1: 0, 2: 0, 3: 0}, cats={}, replaced=0)
    for r in runs:
        tot['rounds'] += r['rounds']; tot['stoppages'] += r['stoppages']; tot['replaced'] += r['replaced']
        for k, v in r['counts'].items():
            tot['counts'][k] = tot['counts'].get(k, 0) + v; c = edt_category(k); tot['cats'][c] = tot['cats'].get(c, 0) + v
        for k in (1, 2, 3): tot['klass'][k] += r['klass'][k]
    return tot


def build():
    global TAB
    TAB = load_action(); setp(); calibrate()
    reps = 5 if QUICK else 40
    clean_rifles = 40 if QUICK else 300
    checks = []

    def check(name, ok, detail):
        checks.append(dict(check=name, **{'pass': bool(ok)}, detail=detail)); print(('ok   ' if ok else 'FAIL ') + name + ': ' + detail)

    # ---- 1. the dust test, run in full: `reps` repeats of 10 rifles x 6,000 rounds
    dust = dict(dust=1.0)
    exp = expected_protocol(dust)
    runs = [run_protocol(1000 + i, EDT['rounds'], dust) for i in range(reps * EDT['rifles'])]
    tot = sum_runs(runs)
    src = EDT['hk416']; rows = []; worst = 0.0
    for cat in ('FFD', 'FTC', 'FFR', 'FXT', 'FEJ', 'FBR'):
        sim = tot['cats'].get(cat, 0) / reps; target = TARGET[cat]; se = math.sqrt(max(sim, 0.5) / reps)
        z = (sim - target) / se; worst = max(worst, abs(z)); lo, hi = poisson_interval(int(target))
        rows.append(dict(category=cat, published=src[cat] + (src['magazine'] if cat == 'FFD' else 0), sim_mean_per_60000=round(sim, 2), analytic_per_60000=round(EDT['rifles'] * exp.get(cat, 0.0), 2),
                         mc_standard_error=round(se, 2), z=round(z, 2), poisson95_of_published=[lo, hi], inside=bool(lo <= sim <= hi)))
    sim_total = tot['stoppages'] / reps
    check('dust test, counts by type', all(r['inside'] for r in rows) and worst < 4.0,
          '; '.join('%s %.1f vs %d' % (r['category'], r['sim_mean_per_60000'], r['published']) for r in rows) + ' per 60,000 rounds (%d repeats; calibration targets)' % reps)
    check('dust test, total class 1 and 2', abs(sim_total - 217.0) < 0.06 * 217, 'simulated %.1f per 60,000 rounds, published 219 less 2 "other" = 217; MRBS %.0f against 274' % (sim_total, 60000 / sim_total))
    k3 = tot['klass'][3] / reps; k2 = tot['klass'][2] / reps; k1 = tot['klass'][1] / reps
    # rise between wipes: the briefing's slide 9 says cleaning seemed to help
    early = sum(1 for r in runs for a in r['at'] if (a - 1) % 600 < 300); late = sum(1 for r in runs for a in r['at'] if (a - 1) % 600 >= 300)
    check('dust test, stoppages rise between wipes', late > 1.5 * early, 'second half of each 600-round interval has %.2f times the stoppages of the first (the briefing says only that cleaning appeared to help; it gives no number)' % (late / max(1, early)))
    edt_out = dict(protocol='10 rifles x 6,000 rounds, dust 1, HK steel magazines, M855, one shot per 2 s in 120-round cycles with a 10 minute pause, wipe and lubricate every 600, clean every 1,200',
                   repeats=reps, seeds='1000 .. %d' % (1000 + reps * EDT['rifles'] - 1), rows=rows, total_sim=round(sim_total, 2), total_published_class12=src['class12'],
                   by_variant={k: round(v / reps, 3) for k, v in sorted(tot['counts'].items())},
                   classes=dict(sim=dict(class1=round(k1, 2), class2=round(k2, 2), class3=round(k3, 2)), published=dict(class12=src['class12'], class3=src['class3']),
                                note='prediction, not calibrated. Simulated class 3 is only cases that need a rod and squibs; the briefing does not break its 14 down, and parts breakage is not modelled'),
                   rise_between_wipes=round(late / max(1, early), 3),
                   first_seed_counts=runs[0]['counts'], first_seed_stoppages=runs[0]['stoppages'], sum_stoppages=tot['stoppages'])

    # ---- 2. aluminium magazines in the same test
    al = dict(dust=1.0, magType='gi_aluminium'); nal = max(2, reps // 4)
    runs_al = [run_protocol(5000 + i, EDT['rounds'], al) for i in range(nal * EDT['rifles'])]
    tal = sum_runs(runs_al); extra = tal['cats'].get('FFD', 0) / nal - tot['cats'].get('FFD', 0) / reps
    check('dust test, aluminium magazines', 148 * 0.8 <= extra <= 239 * 1.2, 'extra feed stoppages %.0f per 60,000 rounds; the M4\'s magazine stoppages were 148 and 239 (calibrated to the midpoint 193.5)' % extra)
    al_out = dict(repeats=nal, seeds='5000 .. %d' % (5000 + nal * EDT['rifles'] - 1), feed_sim=round(tal['cats'].get('FFD', 0) / nal, 2), extra_feed_vs_steel=round(extra, 2), published_m4_magazine=EDT['m4_magazine'],
                  sum_stoppages=tal['stoppages'])

    # ---- 3. clean rifle
    runs_c = [run_protocol(20000 + i, EDT['rounds'], {}) for i in range(clean_rifles)]
    tc = sum_runs(runs_c); mrbs = tc['rounds'] / max(1, tc['stoppages']); expc = expected_protocol({})
    an = sum(v for k, v in expc.items() if k in ('FFD', 'FTC', 'FFR', 'FXT', 'FEJ', 'FBR'))
    check('clean rifle, mean rounds between stoppages', 4000 <= mrbs <= 6000, 'simulated %.0f over %d rounds (analytic %.0f); assumed target about 5,000 (Army laboratory figure for new M4s; no HK416 figure exists)' % (mrbs, tc['rounds'], 6000 / an))
    clean_out = dict(protocol='as the dust test with dust 0', rifles=clean_rifles, seeds='20000 .. %d' % (20000 + clean_rifles - 1), rounds=tc['rounds'], stoppages=tc['stoppages'], mrbs_sim=round(mrbs, 1),
                     mrbs_analytic=round(6000 / an, 1), target_mrbs=CLEAN_TARGET_MRBS, by_category={k: v for k, v in sorted(tc['cats'].items())},
                     by_variant={k: v for k, v in sorted(tc['counts'].items())}, classes={str(k): v for k, v in tc['klass'].items()},
                     context=dict(m4_requirement_1990=600, m4a1_m855a1_2013=1691, individual_carbine_requirement=3592, army_lab_2006_m4_m16=5000, usmc_2002_m4='186 failures in 69,000 rounds'))

    # ---- 4. ammunition against the M855 lot acceptance plan (MIL-C-63989C Table IV, 800 rounds per weapon type)
    a = AMMO['m855']; st = new_state({}); M = margins(st)
    p_mis = a['p_dud'] + odds(M['r_fire'], P['k_fire']); pr = probabilities(st)
    p_fxt = sum(v for k, v in pr.items() if k.startswith('failure_to_extract') or k == 'double_feed:stuck_case_plus_round')
    acc = dict(misfire=binom_accept(p_mis, 800, 1), bullet_in_bore=binom_accept(a['p_squib'], 800, 0), failure_to_extract=binom_accept(p_fxt, 800, 0))
    check('M855 rates against lot acceptance', min(acc.values()) > 0.95, 'chance a lot at the simulated rates passes the first sample: misfire %.4f (accept 1 in 800), bullet in bore %.4f (accept 0), failure to extract %.4f (accept 0)' % (acc['misfire'], acc['bullet_in_bore'], acc['failure_to_extract']))
    check('action time against the M855 specification', TAB['action_time_s'] < 0.003, 'primer to gas port %.2f ms in the action simulation; the specification allows 3 ms at mean plus five standard deviations' % (TAB['action_time_s'] * 1e3))
    spec_out = dict(per_round=dict(misfire=p_mis, bullet_in_bore=a['p_squib'], failure_to_extract=p_fxt), p_accept_first_sample=acc, action_time_ms=TAB['action_time_s'] * 1e3, action_time_limit_ms=3.0)

    # ---- 5. every stoppage is cleared by the state machine; clearing times by type
    forced = ['failure_to_fire:dud', 'failure_to_fire:light_strike', 'hangfire', 'failure_to_feed:nose_jam', 'failure_to_feed:bolt_over_empty_chamber', 'failure_to_feed:failure_to_chamber',
              'stovepipe:stovepipe', 'stovepipe:case_in_receiver', 'stovepipe:rechambered_case', 'double_feed:stuck_case_plus_round', 'double_feed:two_live',
              'failure_to_extract:claw_slip', 'failure_to_extract:torn_rim', 'bolt_override', 'squib', 'failure_to_lock_back']
    clr = {}; allok = True; ntr = 100 if QUICK else 400
    for mode in ('military', 'range'):
        for fk in forced:
            ends = {}; secs = []; procs = {}
            for i in range(ntr):
                rng = mulberry32(900000 + i); st = new_state(dict(mode=mode))
                if fk == 'failure_to_lock_back': st['mag']['rounds'] = 0
                if fk == 'failure_to_extract:claw_slip' or fk == 'failure_to_extract:torn_rim': st['mag']['rounds'] = 0
                r = fire(st, rng, force=fk); advance(st, 0.3)
                cl = clear(st, rng); ends[cl['end']] = ends.get(cl['end'], 0) + 1; secs.append(cl['seconds'])
                procs[cl['procedures'][0] if cl['procedures'] else '-'] = procs.get(cl['procedures'][0] if cl['procedures'] else '-', 0) + 1
            secs.sort(); bad = sum(v for k, v in ends.items() if k not in ('ready', 'made_safe', 'needs_inspection', 'out_of_service'))
            want_end = 'needs_inspection' if fk == 'squib' else 'ready'
            okk = bad == 0 and (fk == 'hangfire' or ends.get(want_end, 0) == ntr)
            allok = allok and okk
            clr[mode + ' / ' + fk] = dict(ends=ends, median_s=round(secs[len(secs) // 2], 2), p90_s=round(secs[int(len(secs) * 0.9)], 2), first_procedure=procs, ok=okk)
    hm = clr['military / hangfire']['ends']; hr = clr['range / hangfire']['ends']
    check('every stoppage is cleared', allok, '%d forced stoppages x %d trials x 2 modes end ready (squib: made safe, awaiting inspection)' % (len(forced), ntr))
    check('the wait covers a hangfire', hr.get('out_of_service', 0) == 0 and hm.get('out_of_service', 0) > 0,
          'forced perceptible hangfires: range mode (30 s wait) %d of %d opened early; military immediate action %d of %d opened the action before the round fired' % (hr.get('out_of_service', 0), ntr, hm.get('out_of_service', 0), ntr))

    # ---- 6. Monte Carlo against the analytic probabilities (one state, many shots)
    cfgm = dict(dust=0.6, ammo='degraded', magType='gi_aluminium'); n_mc = 150000 if QUICK else 1000000
    st0 = new_state(cfgm); st0['nLube'] = 300; st0['nClean'] = 300; st0['mag']['rounds'] = 20
    pr = probabilities(st0, grid=800); rng = mulberry32(77); got = {}
    for i in range(n_mc):
        st = clone(st0)
        r = fire(st, rng); key = r['outcome']
        if key == 'hangfire': key = (r.get('then') or advance(st, 100.0)[0])['outcome']      # a hangfire still cycles: count what the cycle did
        got[key] = got.get(key, 0) + 1
    grp = {}
    for k, v in pr.items(): grp[k.split(':')[0]] = grp.get(k.split(':')[0], 0.0) + v
    # short hangfires resolve at once and may then stop: fold them the way the analytic table does
    zmax = 0.0; mc_rows = []
    for k in sorted(grp):
        if k in ('hangfire',): continue
        e = grp[k] * n_mc; g = got.get(k, 0)
        if e > 20:
            z = (g - e) / math.sqrt(e); zmax = max(zmax, abs(z)); mc_rows.append(dict(outcome=k, expected=round(e, 1), got=g, z=round(z, 2)))
    check('Monte Carlo against the analytic probabilities', zmax < 4.5, 'largest deviation %.2f standard errors over %d outcomes in %d shots (dust 0.6, degraded ammunition, aluminium magazine)' % (zmax, len(mc_rows), n_mc))

    # ---- 7. reproducibility
    a1 = run_protocol(4242, 3000, dict(dust=1.0)); a2 = run_protocol(4242, 3000, dict(dust=1.0)); a3 = run_protocol(4243, 3000, dict(dust=1.0))
    check('seeded runs reproduce', a1 == a2 and a1['at'] != a3['at'], 'same seed gives the same %d stoppages at the same rounds; another seed differs' % a1['stoppages'])

    # ---- 8. node and clip names against the model inventory
    inv = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json'))); names = {x.get('part_name') for x in inv}
    clips = set(json.load(open(os.path.join(HERE, '..', 'model', 'work', 'stats_lod0.json')))['clips'])
    used = set(); usedc = set()
    for m in C.MALFUNCTIONS.values():
        used.update(m['shows']['nodes']); usedc.update(m['shows']['clips'])
    for mo in C.MOTIONS.values():
        used.update(t['node'] for t in mo['tracks'])
    for ac in C.ACTIONS.values(): usedc.update(ac['anim'])
    missing = sorted(n for n in used if n not in names and n not in C.PROPS); missc = sorted(c for c in usedc if c not in clips and c not in C.MOTIONS)
    check('node and clip names exist', not missing and not missc and set(C.EXISTING_CLIPS) <= clips,
          '%d model nodes and %d existing clips referenced are in model/inventory.json and stats_lod0.json; %d new motions; props: %s' % (len(used - set(C.PROPS)), len(usedc & clips), len(C.MOTIONS), ', '.join(C.PROPS)))

    # ---- conditions table (analytic), for the README and the page
    def rate(cfg, **stv):
        st = new_state(cfg); st.update({k: v for k, v in stv.items() if k != 'magRoundsNow'})
        tot = {}
        for n in range(30):
            st['mag']['rounds'] = n
            for k, v in probabilities(st, grid=64).items():
                if k != 'fired': tot[k.split(':')[0]] = tot.get(k.split(':')[0], 0.0) + v / 30.0
        tot['any'] = sum(tot.values()); return tot
    cond_rows = []
    for label, cfg, stv in [
            ('clean, lubricated, M855, HK steel magazine, 20 C', {}, {}),
            ('600 rounds since lubrication, 1,200 since cleaning', {}, dict(nLube=600, nClean=1200)),
            ('run dry', dict(dry=True), {}),
            ('dust 0.25, just wiped', dict(dust=0.25), {}),
            ('dust 0.5, 300 rounds since the wipe', dict(dust=0.5), dict(nLube=300, nClean=300)),
            ('dust 1 (Aberdeen), just wiped', dict(dust=1.0), {}),
            ('dust 1 (Aberdeen), 600 rounds since the wipe', dict(dust=1.0), dict(nLube=600, nClean=600)),
            ('dust 1, aluminium magazine, 600 since the wipe', dict(dust=1.0, magType='gi_aluminium'), dict(nLube=600, nClean=600)),
            ('-54 C', dict(ambientC=-54.0), {}),
            ('+52 C', dict(ambientC=52.0), {}),
            ('barrel at the manual\'s heat limit (250 rounds in 3 minutes)', {}, dict(heatK=432.0)),
            ('commercial .223', dict(ammo='commercial_223'), {}),
            ('steel-cased import', dict(ammo='steel_case'), {}),
            ('old, damp or reloaded ammunition', dict(ammo='degraded'), {}),
            ('aluminium magazine, clean', dict(magType='gi_aluminium'), {}),
            ('magazine spring worn (1.0)', dict(magSpringWear=1.0), {}),
            ('feed lips damaged (0.5)', dict(magLipDamage=0.5), {}),
            ('extractor claw gap 1.80 mm (NO-GO is 1.59)', dict(extractorGapMm=1.80), {}),
            ('weak ejector spring (1.0)', dict(ejectorWeak=1.0), {}),
            ('piston rings worn (1.0)', dict(pistonRingsWorn=1.0), {}),
            ('piston rings worn, commercial .223, -20 C', dict(pistonRingsWorn=1.0, ammo='commercial_223', ambientC=-20.0), {}),
            ('weak buffer spring (1.0)', dict(bufferSpringWeak=1.0), {}),
            ('firing pin protrusion 0.45 mm (GO is 0.90)', dict(firingPinProtrusionMm=0.45), {})]:
        r = rate(cfg, **stv)
        cond_rows.append(dict(condition=label, cfg=cfg, state=stv, per_round={k: float('%.4g' % v) for k, v in sorted(r.items())}, mrbs=round(1.0 / r['any'], 1)))

    # ---- parity vectors for test_malfunctions.js
    par = dict(note='written by sim.py; test_malfunctions.js replays these in hk416-malfunctions.js', probabilities=[], sequences=[], protocols=[])
    for cfg, stv, n in [({}, {}, 29), (dict(dust=1.0), dict(nLube=450, nClean=1050), 12), (dict(dust=0.4, ammo='steel_case', magType='gi_aluminium', ambientC=-30.0), dict(nLube=100, nClean=700, heatK=200.0), 0),
                        (dict(ammo='degraded', pistonRingsWorn=1.0, extractorGapMm=1.75, ejectorWeak=0.5, bufferSpringWeak=0.6, magSpringWear=0.8, magLipDamage=0.3, dry=True, firingPinProtrusionMm=0.5), {}, 25),
                        (dict(ambientC=50.0, ammo='commercial_223', dust=0.7), dict(nLube=599, nClean=1199, heatK=500.0), 5)]:
        st = new_state(cfg); st.update(stv); st['mag']['rounds'] = n
        par['probabilities'].append(dict(cfg=cfg, state=stv, magRounds=n, margins={k: v for k, v in margins(st).items() if k != 'q'}, p=probabilities(st)))
    for seed, cfg in [(1, dict(dust=1.0, ammo='degraded', magType='gi_aluminium', magLipDamage=0.2)), (2, dict(dust=0.8, ammo='steel_case', extractorGapMm=1.9, mode='range')),
                      (3, dict(ammo='degraded', pistonRingsWorn=1.0, ambientC=-40.0, mode='range')), (4, dict(dust=1.0, magSpringWear=1.0, ejectorWeak=1.0, bufferSpringWeak=1.0))]:
        rng = mulberry32(seed); st = new_state(cfg); log = []
        for i in range(400):
            if st['status'] != 'ok': st = new_state(cfg)
            if not ready(st):
                cl = clear(st, rng); log.append(['clear', cl['procedures'], round(cl['seconds'], 6), cl['end'], cl['klass']]); continue
            r = fire(st, rng); advance(st, 1.0)
            log.append(['fire', r['outcome'], r.get('variant', ''), r.get('travelMm', 0), round(r.get('delayS', 0.0), 9), st['chamber'], st['feedway'], st['bolt'], st['mag']['rounds']])
        par['sequences'].append(dict(seed=seed, cfg=cfg, steps=400, log=log))
    for seed, cfg, rounds in [(1000, dict(dust=1.0), 6000), (5000, dict(dust=1.0, magType='gi_aluminium'), 6000), (20000, {}, 6000), (31, dict(dust=0.5, ammo='degraded', mode='range'), 3000)]:
        r = run_protocol(seed, rounds, cfg); par['protocols'].append(dict(seed=seed, cfg=cfg, rounds=rounds, result=r))
    par['long_runs'] = dict(dust=dict(first_seed=1000, rifles=reps * EDT['rifles'], rounds=EDT['rounds'], cfg=dust, sum_stoppages=tot['stoppages'], cats=tot['cats']),
                            clean=dict(first_seed=20000, rifles=clean_rifles, rounds=EDT['rounds'], cfg={}, sum_stoppages=tc['stoppages'], cats=tc['cats']))

    # ---- write
    def pj(v):
        return v if not isinstance(v, float) else float('%.6g' % v)
    data = dict(
        meta=dict(title='HK416 D14.5RS malfunction simulation', credit='carpetshark', generator='assets/hk416/malfunctions/sim.py',
                  model='physical margins from the action simulation with logistic scatter, calibrated at a clean baseline and the 2007 dust test; see README.md',
                  frame='metres, +Z muzzle, +Y up, +X shooter\'s left, origin on the bore axis at the upper receiver front face (as hk416.glb)',
                  time_zero='sear release (trigger break), as in action.json', units='seconds, mm, J, N as each key says; probabilities are per round'),
        sources=C.SOURCES, edt_categories=C.EDT_MAP, inferences=C.INFERENCES, limits=C.LIMITS,
        params={k: dict(value=pj(v[0]), unit=v[1], source=v[2], note=v[3]) for k, v in PARAMS.items()},
        ammo=AMMO, magazines=MAGS, defaults=DEFAULT_CFG, action=TAB,
        stops=dict(positions={k: dict(carrier_mm=v[0], bolt_deg=v[1]) for k, v in STOP.items()}, out_of_battery=dict(carrier_mm=OOB[0], bolt_deg=OOB[1]), port=PORT),
        calibration=dict(dust_test=EDT, targets=TARGET, clean_target_mrbs=CLEAN_TARGET_MRBS,
                         clean_targets={k: PARAMS[k][0] for k in ('p_light_clean', 'p_fxt_clean', 'p_fej_clean', 'p_override_clean', 'p_nose_clean', 'p_two_clean', 'p_ftc_clean')},
                         solved={k: PARAMS[k][0] for k, v in PARAMS.items() if v[2] == 'calibrated'}, aluminium_feed_dust_extra=MAGS['gi_aluminium']['feed_dust_extra']),
        malfunctions=C.MALFUNCTIONS, conditions_table=cond_rows)
    proc = dict(meta=dict(title='HK416 clearing procedures: actions, clips and state machines', credit='carpetshark', generator='assets/hk416/malfunctions/sim.py',
                          clip_format='as model/build.py key(): 24 fps; loc in mm from rest (L + muzzle, S + shooter\'s left, Z up), rot in degrees about the Blender axis through the part pivot',
                          note='existing_clips are in the model; motions are new keyframe data for the model recipe to bake; props are not in the model'),
                rifle_state=dict(chamber=['live', 'empty', 'dud', 'fired', 'stuck', 'stuck_torn'], feedway=['clear'] + list(STOP), bolt=['closed', 'out_of_battery', 'blocked', 'held_open'],
                                 hammer=['cocked', 'down'], bore=['clear', 'obstructed'], selector=['fire', 'safe'], status=['ok', 'needs_inspection', 'out_of_service'],
                                 ready='status ok, chamber live, bolt closed, feedway clear, bore clear, hammer cocked, selector fire, no hangfire pending'),
                actions=C.ACTIONS, existing_clips=C.EXISTING_CLIPS, motions=C.MOTIONS, props=C.PROPS, procedures=C.PROCEDURES, diagnosis=C.DIAGNOSIS,
                transitions=transitions(), clearing=clr)
    valid = dict(meta=dict(title='HK416 malfunction simulation: check results', generator='assets/hk416/malfunctions/sim.py', quick=QUICK), checks=checks,
                 dust_test=edt_out, aluminium=al_out, clean=clean_out, m855_lot_acceptance=spec_out, monte_carlo_vs_analytic=dict(shots=n_mc, cfg=cfgm, rows=mc_rows, max_z=round(zmax, 2)),
                 passed=sum(1 for c in checks if c['pass']), failed=sum(1 for c in checks if not c['pass']))
    for name, obj in (('malfunctions.json', data), ('procedures.json', proc), ('validation.json', valid), ('parity.json', par)):
        with open(os.path.join(HERE, name), 'w') as fh:
            json.dump(obj, fh, indent=1 if name != 'parity.json' else None, separators=None if name != 'parity.json' else (',', ':'))
            fh.write('\n')
    if '--no-plots' not in sys.argv:
        import plots
        plots.make(dict(TAB=TAB, P=P, rows=rows, runs=runs[:EDT['rifles']], reps=reps, cond=cond_rows, margins=margins, travel=travel, new_state=new_state, probabilities=probabilities,
                        clean=clean_out, edt=edt_out), os.path.join(HERE, 'plots'))
    print('%d checks passed, %d failed' % (valid['passed'], valid['failed']))
    return valid['failed']


def transitions():
    """The state machine as a table: for each stoppage as the shooter finds it, what each relevant action does (most likely result)."""
    rows = []
    cases = [('failure_to_fire', dict(chamber='dud', hammer='down')), ('squib', dict(chamber='fired', hammer='down', bore='obstructed')),
             ('failure_to_feed:nose_jam', dict(chamber='empty', feedway='nose_jam', bolt='blocked')), ('failure_to_feed:bolt_over_empty_chamber', dict(chamber='empty')),
             ('failure_to_feed:failure_to_chamber', dict(bolt='out_of_battery')), ('stovepipe:stovepipe', dict(chamber='empty', feedway='stovepipe', bolt='blocked')),
             ('stovepipe:rechambered_case', dict(chamber='fired')), ('double_feed:stuck_case_plus_round', dict(chamber='stuck', feedway='round_behind_case', bolt='blocked')),
             ('double_feed:two_live', dict(chamber='empty', feedway='two_rounds', bolt='blocked')), ('failure_to_extract (magazine empty)', dict(chamber='stuck', bolt='held_open')),
             ('bolt_override', dict(chamber='empty', feedway='round_over_bolt', bolt='blocked')), ('failure_to_lock_back', dict(chamber='empty'))]
    lucky = lambda: 0.0
    for label, over in cases:
        st = new_state({}); st.update(over); st['mag']['rounds'] = 0 if ('empty)' in label or 'lock_back' in label) else 20
        if st['feedway'] != 'clear': st['carrierMm'] = STOP[st['feedway']][0]
        st['last'] = dict(report='pop' if 'squib' in label else 'none', trigger='click')
        o = observe(st); row = dict(stoppage=label, state={k: st[k] for k in ('chamber', 'feedway', 'bolt', 'hammer', 'bore')}, shooter_sees=o['port'], procedure=diagnose(st), actions={})
        for a in ('tap', 'rack', 'lock_back', 'strip_mag', 'sweep_case', 'handle_strike', 'forward_assist', 'safe'):
            s2 = json.loads(json.dumps(st)); r = act(s2, a, lucky)
            if r['ok'] or r['events']:
                row['actions'][a] = dict(ok=r['ok'], events=r['events'], to={k: s2[k] for k in ('chamber', 'feedway', 'bolt', 'hammer')}, ready=ready(s2))
        rows.append(row)
    return rows


if __name__ == '__main__':
    sys.exit(1 if build() else 0)
