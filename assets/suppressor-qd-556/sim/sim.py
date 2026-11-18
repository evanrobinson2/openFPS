#!/usr/bin/env python3
"""Generic QD 5.56 mm suppressor on the HK416 D14.5RS: gas dynamics, sound, back-pressure, heat and flash inputs.

    python3 sim.py            # rebuilds suppressor.json, checks.json and plots/ (about 4 minutes)
    python3 sim.py --no-plots

The physics is in core.py (the reference the JS module is checked against). This script
  1. takes the bore state at bullet exit from the HK416 interior ballistics (assets/hk416/action/sim.py),
  2. builds the configuration from the geometry recipe (../model/geom.py),
  3. calibrates the one calibrated parameter (clip_factor) to the published peak reduction at 1 m,
  4. runs the shot states, couples the residual bore pressure into the HK416 action model, and
  5. writes the tables the runtime uses, the checks against published figures, and the plots.

Every parameter carries its source in PARAMS: 'hk416' (taken from the HK416 asset), 'geometry' (from geom.py),
'published' (named), 'inferred' (an engineering estimate, not measured) or 'calibrated' (solved so that a published
figure is reproduced; not a prediction).
"""
import copy, importlib.util, json, math, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.dirname(HERE)
HK = os.path.join(os.path.dirname(ASSET), 'hk416')
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ASSET, 'model'))
import core, geom

PARAMS = {
    # key: (value, unit, source, note)
    'bullet_len': (23.0e-3, 'm', 'published', 'M855 length (as assets/hk416/sound)'),
    'bullet_r': (2.85e-3, 'm', 'published', 'M855 diameter 5.70 mm'),
    'bullet_ramp': (6.0e-3, 'm', 'inferred', 'bullet-base travel over which an aperture goes from annulus to fully open: aperture radius plus the 2.5 mm boat tail'),
    'cd_muzzle': (1.0, '-', 'hk416', 'the HK416 action empties the bore through a sonic muzzle with no contraction; kept so the bare case reproduces it'),
    'cd_aperture': (0.8, '-', 'inferred', 'discharge coefficient of a sharp-edged aperture (0.8 to 0.85 choked); the HK416 action uses 0.8 for its orifices'),
    'cd_breech': (0.8, '-', 'inferred', 'discharge coefficient of the leak round the withdrawing case'),
    'stanton': (0.006, '-', 'inferred', 'Stanton number of the wall heat transfer; turbulent duct flow gives 0.003 to 0.005, impinging jets more'),
    'h_free': (30.0, 'W/m2/K', 'inferred', 'heat transfer of the gas left stirring in the can once the through-flow stops'),
    't_ign': (850.0, 'K', 'inferred', 'temperature above which the air in the can burns the fuel-rich propellant gas (H2/CO-air autoignition is about 850 to 900 K)'),
    'tau_burn': (1.0e-4, 's', 'inferred', 'time constant of that burn once alight'),
    'q_o2': (13.1e6, 'J/kg O2', 'published', 'heat released per kg of oxygen consumed (Thornton\'s rule; Huggett 1980, Fire and Materials 4)'),
    'tau_ac': (2 * geom.RB * 1e-3 / core.C0, 's', 'inferred', 'acoustic transit time across the exit aperture (7.2 mm / 343 m/s): the shortest rise the exit can radiate as a compact source'),
    'carry_gamma_phi': (1.99, 'rad', 'inferred', 'limiting plume angle of the muzzle source flow for gamma 1.24, extrapolated from Ashkenas and Sherman (1966): 1.365, 1.662, 1.888 rad for gamma 1.67, 1.40, 1.29'),
    'clip_factor': (None, '-', 'calibrated', 'share of the in-line kinetic-energy carry-over that survives the clips and the under-expansion of the jets; solved for the published peak reduction at 1 m'),
    'target_reduction_db': (22.5, 'dB', 'published', 'midpoint of the 20 to 25 dB peak reduction at 1 m left of the muzzle for AR-15 rifles with 14 suppressors (Lobarinas et al. 2016, as summarised in the NIOSH review)'),
    'target_ear_reduction_db': (20.5, 'dB', 'published', 'midpoint of the 17 to 24 dB peak reduction at the shooter\'s ear (Murphy et al. 2018, Int. J. Audiology 57 S1, abstract)'),
    'dipole_share': (None, '-', 'calibrated', 'share of the compact thrust dipole that radiates (the starting jet is not compact, so less than 1); solved for the published peak reduction at the shooter\'s ear'),
    'bare_side_db': (164.0, 'dB', 'hk416', 'bare rifle at 1 m, 90 degrees: assets/hk416/sound (M4, M855, 14.5 in; Dater, "Firearm Sound Briefing")'),
    'mu_bare': (0.78, '-', 'hk416', 'directivity parameter of the bare muzzle blast in assets/hk416/sound (Fansler and Schmidt)'),
    'theta_shooter_deg': (174.8, 'deg', 'hk416', 'shooter\'s ear from the bore line, assets/hk416/sound'),
    'theta_bystander_deg': (97.5, 'deg', 'hk416', 'bystander 5 m to the right, assets/hk416/sound'),
    'theta_downrange_deg': (2.3, 'deg', 'hk416', 'listener 50 m down-range, 2 m off the line, assets/hk416/sound'),
    'warm_wall': (320.0, 'K', 'inferred', 'wall temperature of the reference "subsequent shot" state (a few rounds in)'),
    'hot_wall': (600.0, 'K', 'inferred', 'wall temperature of the "hot can" state (about 60 rounds in)'),
    'h_conv': (12.0, 'W/m2/K', 'inferred', 'free convection from a 38 mm horizontal cylinder in still air (Churchill-Chu order of magnitude)'),
    'emissivity': (0.85, '-', 'inferred', 'matte black high-temperature finish'),
    'tau_o2': (20.0, 's', 'inferred', 'time for fresh air to refill a can left open to the air: a guess, design dependent'),
    'case_taper': (0.0081, '-', 'published', 'half-angle taper of the 5.56x45 case body (9.58 mm at the head to 8.99 mm at the shoulder over 36.5 mm)'),
    'case_d': (9.3e-3, 'm', 'published', 'mean case body diameter'),
    'neck_leak': (1.0e-6, 'm2', 'inferred', 'leak round the case neck as soon as the case starts back: 6.43 mm neck, 0.05 mm fired clearance'),
    'port_d_thrust': (None, 'm', 'calibrated', 'HK416 gas port diameter re-solved with the residual-thrust term on, for the same bare cyclic rate as the shipped action (so the bare rifle does not change)'),
    'residual_thrust': (1.0, '-', 'inferred', 'share of residual bore pressure times case-head area that pushes the bolt once the lugs are clear'),
    'case_seal_len': (6.0e-3, 'm', 'inferred', 'case travel over which the neck still seals the chamber (5.1 mm neck plus the shoulder)'),
    'flash_mix_ratio': (1.2, 'kg air/kg gas', 'inferred', 'air needed to burn the fuel-rich exhaust, about stoichiometric for 50 to 60 % CO + H2 by volume'),
    'flash_t_ign': (1100.0, 'K', 'inferred', 'ignition temperature of the exhaust-air mixture (order given by Klingenberg and Heimerl 1992; recalled, not re-read)'),
    'flash_t_width': (60.0, 'K', 'inferred', 'width of the ignition band'),
}
P = {k: v[0] for k, v in PARAMS.items()}


def setp(k, v): P[k] = v; PARAMS[k] = (v,) + PARAMS[k][1:]


def load_hk():
    spec = importlib.util.spec_from_file_location('hk416_action_sim', os.path.join(HK, 'action', 'sim.py'))
    hk = importlib.util.module_from_spec(spec); spec.loader.exec_module(hk)
    aj = json.load(open(os.path.join(HK, 'action', 'action.json')))
    for k, v in aj['params'].items():
        if k in hk.P: hk.setp(k, v['value'])
    tab, info = hk.ib_solve(hk.P['burn_coeff'], hk.P['form_theta'])
    FT = hk.firing_train()
    return hk, aj, (tab, info), FT


def source_fraction(theta_a, phi):
    """Share of a highly under-expanded jet's mass flux inside a cone of half-angle theta_a (Ashkenas-Sherman source flow)."""
    f = lambda th: math.cos(math.pi * th / (2 * phi)) ** 2 * math.sin(th)
    def integ(a, b, n=4000):
        h = (b - a) / n; return sum(f(a + (i + 0.5) * h) for i in range(n)) * h
    return integ(0, theta_a) / integ(0, min(phi, math.pi / 2))


def vermes(run, web, c):
    """Kinetic-energy carry-over of a straight-through labyrinth (Vermes 1961): alpha = 8.52 / ((s - t)/c + 7.23)."""
    return 8.52 / ((run - web) / c + 7.23)


def build_config(hk, info, clip_factor, dipole_share=0.0):
    hp = hk.P; ch = geom.chambers(); rb = geom.RB * 1e-3; inv = geom.inventory()
    Vres = hp['chamber_vol'] + hp['bore_area'] * info['travel']; m = hp['m_charge']; R = info['R']
    Tg = info['p_exit_mean'] * (Vres - hp['covolume'] * m) / (m * R)
    al_raw = [source_fraction(math.atan(rb / ch['aperture_from_crown_m'][0]), P['carry_gamma_phi'])]
    for j in range(1, len(ch['volume_m3'])): al_raw.append(vermes(ch['jet_run_m'][j], ch['web_t_m'][j - 1], rb))
    al = [al_raw[0]] + [clip_factor * a for a in al_raw[1:]]
    th = [90.0, P['theta_shooter_deg'], P['theta_bystander_deg'], P['theta_downrange_deg'], 180.0]
    area_ext = math.pi * geom.G['tube_od'] * 1e-3 * geom.L * 1e-3 + 2 * math.pi * (geom.R_OUT * 1e-3) ** 2
    cfg = dict(
        gas=dict(R=R, gamma=hp['gamma'], covolume=hp['covolume'], cp=R * hp['gamma'] / (hp['gamma'] - 1)),
        bore=dict(V=Vres, m=m, T=Tg, area=hp['bore_area'], p_exit=info['p_exit_mean']),
        bullet=dict(v=info['v_exit'], length=P['bullet_len'], radius=P['bullet_r'], ramp_m=P['bullet_ramp']),
        chambers=dict(names=ch['names'], volume_m3=ch['volume_m3'], wall_area_m2=ch['wall_area_m2'], aperture_area_m2=ch['aperture_area_m2'],
                      aperture_from_crown_m=ch['aperture_from_crown_m'], web_t_m=ch['web_t_m'], carry_over=al, carry_over_unclipped=al_raw),
        model=dict(cd_muzzle=P['cd_muzzle'], cd_aperture=P['cd_aperture'], cd_breech=P['cd_breech'], stanton=P['stanton'], h_free=P['h_free'],
                   a_ref=math.sqrt(math.pi * rb * rb * math.pi * (geom.R_SK * 1e-3) ** 2), t_ign=P['t_ign'], tau_burn=P['tau_burn'], q_o2=P['q_o2'],
                   tau_ac=P['tau_ac'], flash_mix_ratio=P['flash_mix_ratio'], flash_t_ign=P['flash_t_ign'], flash_t_width=P['flash_t_width']),
        listen=dict(names=['side', 'shooter', 'bystander', 'downrange', 'behind'], theta_deg=th, cos=[math.cos(math.radians(a)) if a != 90.0 else 0.0 for a in th],
                    dip=[dipole_share * math.cos(math.radians(a)) if a != 90.0 else 0.0 for a in th]),
        exit_offset_m=(geom.L - geom.S_MOUNT) * 1e-3,
        t_uncork_cap_s=(ch['aperture_from_crown_m'][-1] + ch['web_t_m'][-1]) / info['v_exit'],
        heat=dict(C_J_per_K=inv['heat_capacity_J_per_K'], area_m2=area_ext, h_conv=P['h_conv'], emissivity=P['emissivity'], tau_o2_s=P['tau_o2'],
                  t_wall_K=[], shot_J=[], first_round_extra_J=0.0),
        mass_kg=inv['mass_kg'])
    return cfg


def calibrate(hk, info):
    target = P['bare_side_db'] - P['target_reduction_db']
    def f(k):
        cfg = build_config(hk, info, k)
        s = core.run_shot(cfg, dict(o2=0.0, t_wall=P['warm_wall'], t1=1.5e-3, t_end=1.5e-3))
        return core.db(s['peak_p1m_Pa'][0]) - target
    lo, hi = 0.3, 1.0; flo, fhi = f(lo), f(hi)
    print('  clip_factor %.2f -> %+.1f dB, %.2f -> %+.1f dB re target' % (lo, flo, hi, fhi))
    if flo * fhi > 0: raise RuntimeError('target reduction not bracketed')
    for _ in range(14):
        mid = 0.5 * (lo + hi); fm = f(mid)
        if fm * flo <= 0: hi = mid
        else: lo = mid; flo = fm
    return 0.5 * (lo + hi), dict(uncalibrated_reduction_db=P['target_reduction_db'] - fhi)


def calibrate_dipole(hk, info, kf, hkp):
    """Share of the thrust dipole for which the peak at the shooter's ear is the published reduction below the bare rifle."""
    cfg = build_config(hk, info, kf, 0.0)
    s = core.run_shot(cfg, dict(o2=0.0, t_wall=P['warm_wall'], t1=1.5e-3, t_end=1.5e-3, rec_every1=1))
    b = hkp['persp']['shooter']['blast']['free'][0]; c = cfg['listen']['cos'][1]
    r1 = b['r'] - cfg['exit_offset_m'] * c
    want = core.P_REF * 10 ** ((core.db(b['P']) - P['target_ear_reduction_db']) / 20) * r1          # peak at 1 m toward the ear
    mono = np.array(s['rec']['mono']); dip = np.array(s['rec']['dip'])
    f = lambda k: float(np.max(mono + k * c * dip)) - want
    lo, hi = 0.0, 1.0
    if f(lo) * f(hi) > 0: raise RuntimeError('ear target not bracketed: %.1f, %.1f Pa re %.1f' % (f(lo) + want, f(hi) + want, want))
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if f(mid) * f(lo) <= 0: hi = mid
        else: lo = mid
    return 0.5 * (lo + hi), dict(omnidirectional_reduction_db=core.db(b['P']) - core.db((f(0.0) + want) / r1), full_dipole_reduction_db=core.db(b['P']) - core.db(max(f(1.0) + want, 1e-9) / r1))


def calibrate_port(hk, IBb, FT, ov, rpm_target):
    from scipy.optimize import brentq
    d0 = hk.P['port_d']
    f = lambda d: hk.cyclic_rate(IBb, FT, 'ads', over=dict(ov, port_d=d))[0] - rpm_target
    return float(brentq(f, 0.85 * d0, 1.02 * d0, xtol=2e-7))


def make_tab(hk, tab, info, rec, t_len=40e-3):
    """HK416 interior-ballistics tables (1 us grid, t = 0 at ignition) with the blowdown replaced by a core.py run."""
    ie = int(round(info['t_exit'] * 1e6)); n = int(round(t_len * 1e6)); tt = np.arange(n) * 1e-6
    p = np.interp(tt, rec['t'], rec['p_bore']); T = np.interp(tt, rec['t'], rec['T_bore']); thr = np.interp(tt, rec['t'], rec['thrust'])
    ratio = float(tab['pport'][ie - 1] / tab['pm'][ie - 1])
    out = {}
    out['t'] = np.concatenate([tab['t'][:ie], info['t_exit'] + tt])
    out['pm'] = np.concatenate([tab['pm'][:ie], p]); out['pbr'] = np.concatenate([tab['pbr'][:ie], p])
    out['pport'] = np.concatenate([tab['pport'][:ie], np.maximum(core.PATM, p * ratio)])
    out['tg'] = np.concatenate([tab['tg'][:ie], T])
    out['fg'] = np.concatenate([tab['fg'][:ie], thr * hk.P['blowdown_scale'] * (1 - hk.P['brake_beta'])])
    out['x'] = np.concatenate([tab['x'][:ie], info['travel'] + info['v_exit'] * tt]); out['v'] = np.concatenate([tab['v'][:ie], np.full(n, info['v_exit'])])
    inf = dict(info); inf['impulse_total'] = float(np.sum(out['fg']) * 1e-6); inf['impulse_gas'] = inf['impulse_total'] - inf['impulse_bullet']
    return out, inf


def breech_schedule(hk, r, info):
    """Leak area from the bore past the withdrawing case, against time since the bullet left (from one action run)."""
    hp = hk.P; x_u = hp['cam_dwell'] + hp['cam_len']
    tg = r['t'] - r['ign'][0] - info['t_exit']; x = r['x']
    ts = np.arange(0.0, 40.0e-3 + 1e-9, 1.0e-4); xs = np.interp(ts, tg, x)
    i_max = int(np.argmax(xs)); area = []
    for i, xv in enumerate(xs):
        xc = xv - x_u
        if i > i_max: a = hp['bore_area']                                    # the case has gone; the chamber stands open
        elif xc <= 0: a = 0.0
        elif xc >= hp['case_len']: a = hp['bore_area']
        else: a = min(hp['bore_area'], P['neck_leak'] + math.pi * P['case_d'] * P['case_taper'] * xc)
        area.append(a)
    i0 = max(0, next((i for i, a in enumerate(area) if a > 0), 0) - 1)
    return dict(t=[round(float(t), 7) for t in ts[i0:]], area=[float(a) for a in area[i0:]])


def action_case(hk, IB, FT, over, label):
    r = hk.run(IB, FT, 'ads', 1, 0.2, over=over)
    rpm, r3 = hk.cyclic_rate(IB, FT, 'ads', over=over)
    ev = dict(r['events'][0]); tab, info = IB; ign = r['ign'][0]
    j_un = int((ev['unlock_start'] - ign) * 1e6); j_ex = int((ev['unlock'] - ign) * 1e6)
    M = r['M_all'] - hk.STANCES['ads']['m_arm']
    d = dict(label=label, peak_carrier_mps=float(r['v_peak'][0]), carrier_at_eject_mps=float(r['v_eject'][0]), max_travel_mm=float(r['x_max'][0] * 1e3),
             cyclic_rpm=float(rpm), period_s=float(60.0 / rpm) if rpm > 0 else None,
             bore_MPa_at_unlock_start=float(tab['pbr'][j_un] / 1e6), bore_MPa_at_unlock=float(tab['pbr'][j_ex] / 1e6),
             recoil_impulse_Ns=float(info['impulse_total']), gun_mass_kg=float(M), free_recoil_mps=float(info['impulse_total'] / M),
             free_recoil_J=float(0.5 * info['impulse_total'] ** 2 / M), events={k: round(float(v), 6) for k, v in sorted(ev.items(), key=lambda kv: kv[1])})
    print('    %-34s carrier %.2f m/s peak, %.2f at eject, %.0f rpm, bore %.1f / %.1f MPa at unlock, recoil %.2f N s' %
          (label, d['peak_carrier_mps'], d['carrier_at_eject_mps'], d['cyclic_rpm'], d['bore_MPa_at_unlock_start'], d['bore_MPa_at_unlock'], d['recoil_impulse_Ns']))
    return d, r


def action_overlay(hk, aj, IB, FT, over):
    """The blocks of action.json that change with the can, in the same format, for HK416Action.use()."""
    rl = hk.rl; resample = hk.resample; tab, info = IB
    runs = {}
    for st in ('ads', 'hip'):
        runs['semi_' + st] = hk.run(IB, FT, st, 1, 1.2, over=over)
        runs['auto_' + st] = hk.run(IB, FT, st, 10, 2.0, over=over)
    semi = runs['semi_ads']; evs = dict(semi['events'][0]); fev = FT[2]
    d = np.diff(runs['auto_ads']['rel']); per = float(d[1:].mean())
    t_cyc = math.ceil((evs['in_battery'] + 0.01) / 0.005) * 0.005; DT = aj['cycle']['dt']
    cyc = dict(dt=DT, t0=0.0, note=aj['cycle']['note'] + ' With the suppressor fitted.',
               carrier_mm=rl(np.clip(resample(semi['t'], semi['x'] * 1e3, DT, t_cyc), 0, None), 3), carrier_mps=rl(resample(semi['t'], semi['v'], DT, t_cyc), 3),
               bolt_deg=rl(resample(semi['t'], semi['bolt'], DT, t_cyc), 2), hammer_deg=rl(resample(semi['t'], semi['hammer'], DT, t_cyc), 2),
               firing_pin_mm=rl(resample(semi['t'], semi['pin'] * 1e3, DT, t_cyc), 3),
               cylinder_MPa=rl(resample(semi['t'], semi['pc'] / 1e6, DT, t_cyc), 3),
               receiver_force_N=rl(resample(semi['t'], semi['frecv'], DT, t_cyc, mean=True), 1))
    nb = 1200; kb_ = np.arange(nb) * 10
    ball = dict(dt=1e-5, t0=round(fev['ignition'], 6), note=aj['ballistics']['note'] + '; with the suppressor the bore empties into the can',
                chamber_MPa=rl(tab['pbr'][kb_] / 1e6, 2), port_MPa=rl(tab['pport'][kb_] / 1e6, 2),
                bullet_mm=rl(np.minimum(tab['x'][kb_], info['travel']) * 1e3, 2), bullet_mps=rl(tab['v'][kb_], 1),
                bore_force_N=rl(tab['fg'][kb_], 0), gas_temp_K=rl(tab['tg'][kb_], 0))
    RD = aj['recoil']['dt']
    def pose(r, t_end):
        return dict(z_mm=rl(resample(r['t'], r['zg'] * 1e3, RD, t_end), 2), pitch_up_deg=rl(resample(r['t'], np.degrees(r['pitch']), RD, t_end), 3),
                    yaw_right_deg=rl(resample(r['t'], np.degrees(r['yaw']), RD, t_end), 3),
                    support_force_N=rl(resample(r['t'], r['fsh'], RD, t_end, mean=True), 0), shot_times=rl(r['rel'], 5))
    order = sorted(evs.items(), key=lambda kv: kv[1])
    nom = hk.eject_nominal(semi['v_eject'][0]); vn = np.round(nom['vel'], 3); sp = float(np.linalg.norm(vn))
    return dict(
        note='Blocks of assets/hk416/action/action.json recomputed with the suppressor fitted (same format and units). Merge over the base file and pass to HK416Action.use().',
        cycle=cyc, ballistics=ball,
        events=dict(note=aj['events']['note'] + ', suppressor fitted', times={k: round(v, 6) for k, v in order}, order=[k for k, _ in order]),
        auto=dict(note=aj['auto']['note'], period_s=round(per, 5), rpm=round(60 / per, 1)),
        recoil=dict(semi={st: pose(runs['semi_' + st], 1.2) for st in ('ads', 'hip')}, auto={st: pose(runs['auto_' + st], 2.0) for st in ('ads', 'hip')}),
        mechanics=dict(full_stroke_mm=round(semi['x_max'][0] * 1e3, 2)),
        brass=dict(release_time_s=round(evs['eject'] + 0.004, 5),
                   nominal=dict(vel=rl(vn, 3), angVel=[0.0, round(nom['spin_y'], 1), 0.0], speed=round(sp, 3), carrier_speed_at_eject=round(semi['v_eject'][0], 3))),
    ), runs


def thin(rec, keys, stride_fast=20, t_fast=4e-3, stride_slow=4):
    """Downsample a record for the JSON: 20 us steps to 4 ms, 0.2 ms after."""
    idx = [i for i, t in enumerate(rec['t']) if t < t_fast][::stride_fast] + [i for i, t in enumerate(rec['t']) if t >= t_fast][::stride_slow]
    out = {'t': [round(rec['t'][i], 7) for i in idx]}
    for k in keys: out[k] = [float('%.5g' % rec[k][i]) for i in idx]
    return out


def summary(cfg, s):
    return dict(peak_p_MPa=[round(p / 1e6, 3) for p in s['peak_p_Pa']], peak_T_K=[round(T, 0) for T in s['peak_T_K']],
                peak_exit_kg_s=round(s['peak_mdot_exit'], 4), peak_exit_MW=round(s['peak_hdot_exit'] / 1e6, 4), impulse_Ns_raw=round(s['impulse_Ns'], 4),
                heat_J=round(s['heat_total_J'], 1), heat_by_chamber_J=[round(q, 1) for q in s['heat_wall_J']], o2_burnt_mg=round(s['o2_burnt_kg'] * 1e6, 2),
                mass_out_g=round(s['mass_out_kg'] * 1e3, 4), mass_breech_mg=round(s['mass_breech_kg'] * 1e6, 3))


def residual_heat(cfg, s, t_wall):
    """Heat the gas still in the can gives up as it cools to the wall after the run ends, J."""
    g = cfg['gas']; cvg = g['R'] / (g['gamma'] - 1); q = 0.0
    for k in range(1, len(s['end_T_K'])): q += (s['end_gas_kg'][k] * cvg + s['end_air_kg'][k] * core.CVA) * (s['end_T_K'][k] - t_wall)
    return q


def main():
    t0 = time.time(); plots = '--no-plots' not in sys.argv
    print('loading the HK416 interior ballistics ...')
    hk, aj, IB, FT = load_hk(); tab, info = IB; hp = hk.P
    rpm_ship, _ = hk.cyclic_rate(IB, FT, 'ads')
    print('  exit %.1f MPa mean, %.0f m/s; shipped action reproduces %.1f rpm (action.json: %.1f)' % (info['p_exit_mean'] / 1e6, info['v_exit'], rpm_ship, aj['auto']['rpm']))
    print('calibrating clip_factor for a %.1f dB peak reduction at 1 m ...' % P['target_reduction_db'])
    kf, cal = calibrate(hk, info); setp('clip_factor', kf)
    hkp = json.load(open(os.path.join(HK, 'sound', 'params.json')))
    ds, cald = calibrate_dipole(hk, info, kf, hkp); setp('dipole_share', ds)
    cfg = build_config(hk, info, kf, ds)
    print('  clip_factor %.4f; carry-over %s' % (kf, ' '.join('%.3f' % a for a in cfg['chambers']['carry_over'])))
    print('  dipole_share %.4f (ear reduction %.1f dB with none, %.1f dB with all of it)' % (ds, cald['omnidirectional_reduction_db'], cald['full_dipole_reduction_db']))

    # ---- pass 1: no breech leak, to get the carrier motion
    print('pass 1 (no breech leak) ...')
    bare0 = core.run_shot(cfg, dict(bare=True, t_end=20e-3))
    sub0 = core.run_shot(cfg, dict(o2=0.0, t_wall=P['warm_wall']))
    IBb0 = make_tab(hk, tab, info, bare0['rec'], 20e-3); IBs0 = make_tab(hk, tab, info, sub0['rec'])
    ov_b = dict(residual_thrust=P['residual_thrust'], case_seal_len=P['case_seal_len'])
    ov_b['port_d'] = calibrate_port(hk, IBb0, FT, ov_b, rpm_ship)
    ov_s = dict(ov_b, m_gun=hp['m_gun'] + cfg['mass_kg'])
    _, rb0 = action_case(hk, IBb0, FT, ov_b, 'pass 1 bare'); _, rs0 = action_case(hk, IBs0, FT, ov_s, 'pass 1 suppressed')
    br_b = breech_schedule(hk, rb0, info); br_s = breech_schedule(hk, rs0, info)
    cfg['breech'] = dict(bare=br_b, suppressed=br_s,
                         note='leak area (m2) from the bore past the withdrawing case against time since the bullet left the crown, from the HK416 action run with and without the can')

    # ---- pass 2: the shot states
    print('pass 2: shot states ...')
    bare = core.run_shot(cfg, dict(bare=True, t_end=20e-3, breech=br_b))
    sub = core.run_shot(cfg, dict(o2=0.0, t_wall=P['warm_wall'], breech=br_s))
    first = core.run_shot(cfg, dict(o2=1.0, t_wall=core.T_AMB, breech=br_s))
    hot = core.run_shot(cfg, dict(o2=0.0, t_wall=P['hot_wall'], breech=br_s))
    tw = [core.T_AMB, 450.0, 650.0, 900.0]; hs = []
    for T in tw:
        s = core.run_shot(cfg, dict(o2=0.0, t_wall=T, breech=br_s, rec_every1=50, rec_every2=250))
        hs.append(s['heat_total_J'] + residual_heat(cfg, s, T)); print('    wall %.0f K: %.0f J' % (T, hs[-1]))
    q_first = first['heat_total_J'] + residual_heat(cfg, first, core.T_AMB)
    cfg['heat']['t_wall_K'] = tw; cfg['heat']['shot_J'] = [round(q, 2) for q in hs]; cfg['heat']['first_round_extra_J'] = round(q_first - hs[0], 2)
    ac = {k: core.acoustics(cfg, s) for k, s in (('bare', bare), ('first_round', first), ('subsequent', sub), ('hot', hot))}
    cfg['bare_ref'] = dict(jet_power_W=ac['bare']['jet_power_W'], jet_tau_s=ac['bare']['jet_tau_s'], peak_mdot_exit=bare['peak_mdot_exit'], peak_hdot_exit=bare['peak_hdot_exit'])

    # ---- the action with the can
    print('HK416 action with the residual bore pressure ...')
    IBb = make_tab(hk, tab, info, bare['rec'], 20e-3); IBs = make_tab(hk, tab, info, sub['rec']); IBf = make_tab(hk, tab, info, first['rec']); IBh = make_tab(hk, tab, info, hot['rec'])
    ov_b['port_d'] = calibrate_port(hk, IBb, FT, ov_b, rpm_ship); ov_s['port_d'] = ov_b['port_d']; setp('port_d_thrust', ov_b['port_d'])
    print('  gas port re-solved with the residual-thrust term: %.3f mm (shipped %.3f mm)' % (ov_b['port_d'] * 1e3, hp['port_d'] * 1e3))
    A = {}
    A['shipped'], _ = action_case(hk, IB, FT, None, 'bare, action as shipped')
    A['bare_core'], _ = action_case(hk, IBb, FT, None, 'bare, blowdown from core.py')
    A['bare_thrust'], r_b = action_case(hk, IBb, FT, ov_b, 'bare + residual thrust')
    A['supp_gas_only'], _ = action_case(hk, IBs, FT, dict(m_gun=ov_s['m_gun']), 'suppressed, no residual thrust, shipped port')
    A['suppressed'], r_s = action_case(hk, IBs, FT, ov_s, 'suppressed + residual thrust')
    A['suppressed_first'], _ = action_case(hk, IBf, FT, ov_s, 'suppressed, first round')
    A['suppressed_hot'], _ = action_case(hk, IBh, FT, ov_s, 'suppressed, hot can')
    overlay, oruns = action_overlay(hk, aj, IBs, FT, ov_s)
    eb = A['bare_thrust']['events']; es = A['suppressed']['events']
    rel = lambda e, k: e[k] - e['bullet_exit']
    mech = dict(deflector=rel(es, 'eject') / rel(eb, 'eject'), buffer=rel(es, 'buffer_impact') / rel(eb, 'buffer_impact'), spring=rel(es, 'buffer_impact') / rel(eb, 'buffer_impact'),
                feed=rel(es, 'feed') / rel(eb, 'feed'), battery=rel(es, 'in_battery') / rel(eb, 'in_battery'),
                period_ratio=A['suppressed']['period_s'] / A['bare_thrust']['period_s'])
    cfg['mech'] = {k: round(v, 5) for k, v in mech.items()}

    # ---- sound: the patch for the HK416 tables
    snd = {}
    for st in ('first_round', 'subsequent', 'hot'):
        patched = core.sound_overlay(cfg, hkp, ac[st], ac['bare'], cfg['mech'])
        per = {}
        for nm in ('shooter', 'bystander', 'downrange'):
            b = hkp['persp'][nm]['blast']['free'][0]; p = patched['persp'][nm]['blast']['free'][0]
            nw = hkp['persp'][nm]['nwave']['free']
            per[nm] = dict(bare_dB=round(core.db(b['P']), 2), suppressed_dB=round(core.db(p['P']), 2), reduction_dB=round(core.db(b['P']) - core.db(p['P']), 2),
                           crack_dB=round(core.db(nw[0]['dp']), 2) if nw else None, crack_unchanged=patched['persp'][nm]['nwave'] == hkp['persp'][nm]['nwave'])
        A1 = ac[st]['listeners']
        per['side_1m'] = dict(bare_dB=P['bare_side_db'], suppressed_dB=round(A1[0]['pop_dB1m'], 2), reduction_dB=round(P['bare_side_db'] - A1[0]['pop_dB1m'], 2))
        mu = P['mu_bare']; bare_behind = P['bare_side_db'] + 20 * math.log10((1 - mu) / math.sqrt(1 - mu * mu))
        per['behind_1m'] = dict(bare_dB=round(bare_behind, 2), suppressed_dB=round(A1[4]['pop_dB1m'], 2), reduction_dB=round(bare_behind - A1[4]['pop_dB1m'], 2),
                                note='bare level from the HK416 directivity law at 180 degrees, both at 1 m from their own source')
        snd[st] = dict(levels=per, listeners=[{k: (round(v, 7) if isinstance(v, float) else v) for k, v in l.items()} for l in ac[st]['listeners']],
                       jet_power_W=round(ac[st]['jet_power_W'], 1), jet_tau_s=round(ac[st]['jet_tau_s'], 6),
                       jet_rms_ratio=round(math.sqrt(ac[st]['jet_power_W'] / ac['bare']['jet_power_W']), 5), jet_tau_ratio=round(ac[st]['jet_tau_s'] / ac['bare']['jet_tau_s'], 4))
    fl = {st: core.flash_input(cfg, s, bare) for st, s in (('first_round', first), ('subsequent', sub), ('hot', hot))}

    # ---- heat strings
    C = cfg['heat']['C_J_per_K']
    strings = {}
    for nm, times in (('semi_30_in_30s', [i * 1.0 for i in range(30)]), ('auto_30', [i * A['suppressed']['period_s'] for i in range(30)]),
                      ('rapid_70_in_35s', [i * 0.5 for i in range(70)]), ('rapid_100_in_50s', [i * 0.5 for i in range(100)]), ('sustained_210_in_10min', [i * (600.0 / 210) for i in range(210)])):
        hsr = core.heat_string(cfg, times)
        strings[nm] = dict(shots=len(times), duration_s=round(times[-1], 2), T_end_K=round(hsr[-1]['T_after_K'], 1), rise_K=round(hsr[-1]['T_after_K'] - core.T_AMB, 1),
                           rise_F=round((hsr[-1]['T_after_K'] - core.T_AMB) * 1.8, 0), first_shot_rise_K=round(hsr[0]['heat_J'] / C, 2), last_shot_rise_K=round(hsr[-1]['heat_J'] / C, 2))

    # ---- closure checks
    g = cfg['gas']; cvg = g['R'] / (g['gamma'] - 1)
    E0 = cfg['bore']['m'] * cvg * cfg['bore']['T']
    e_end = bare['end_gas_kg'][0] * cvg * bare['end_T_K'][0]
    mass_err = abs(cfg['bore']['m'] - bare['mass_out_kg'] - bare['mass_breech_kg'] - bare['end_gas_kg'][0]) / cfg['bore']['m']
    m_can0 = sum(core.PATM * v / (g['R'] * P['warm_wall']) for v in cfg['chambers']['volume_m3'])
    mass_err_s = abs(cfg['bore']['m'] + m_can0 - sub['mass_out_kg'] - sub['mass_breech_kg'] - sum(sub['end_gas_kg']) - sum(sub['end_air_kg'])) / cfg['bore']['m']
    ie = int(round(info['t_exit'] * 1e6))
    eq = [dict(t_ms=tt * 1e3, action_MPa=round(float(tab['pbr'][ie + int(tt * 1e6)] / 1e6), 3), core_MPa=round(core.interp(bare0['rec']['t'], bare0['rec']['p_bore'], tt) / 1e6, 3)) for tt in (0.0, 0.5e-3, 1e-3, 2e-3, 4e-3)]
    raw_blow = info['impulse_raw'] - (hp['m_bullet'] + hp['m_charge'] / 2) * info['v_exit']
    hdot_ratio = bare['peak_hdot_exit'] / sub['peak_hdot_exit']

    S = snd['subsequent']['levels']; F = snd['first_round']['levels']; H = snd['hot']['levels']
    pct = lambda a, b: round(100.0 * (a / b - 1.0), 1)
    checks = dict(
        note='sim = this simulation; published = the named source. status says whether the figure was calibrated to, predicted, or only bounded.',
        sound_peak_reduction_1m_side=dict(sim_dB=S['side_1m']['reduction_dB'], suppressed_dB=S['side_1m']['suppressed_dB'], published='20 to 25 dB',
            source='Lobarinas, Scott, Spankovich and Le Prell (2016), Int. J. Audiology 55 (S1): nine AR-15 rifles, 14 suppressors, 1 m left of the muzzle per MIL-STD-1474D; range as summarised in Murphy et al., "Developing a method to assess noise reduction of firearm suppressors for small-caliber weapons" (NIOSH/CDC stacks 221679)',
            status='calibration target (clip_factor solved for the 22.5 dB midpoint); with clip_factor = 1 the model gives %.1f dB' % cal['uncalibrated_reduction_db']),
        sound_peak_reduction_shooter_ear=dict(sim_dB=S['shooter']['reduction_dB'], bare_dB=S['shooter']['bare_dB'], suppressed_dB=S['shooter']['suppressed_dB'], published='17 to 24 dB',
            source='Murphy, Flamme, Campbell, Zechmann, Tasko, Lankford, Meinke, Finan and Stewart (2018), Int. J. Audiology 57 (S1): peak reduction at the shooter\'s ear, several firearms (abstract)',
            status='calibration target (dipole_share solved for the 20.5 dB midpoint); an omnidirectional source gives %.1f dB, the full compact dipole %.1f dB' % (cald['omnidirectional_reduction_db'], cald['full_dipole_reduction_db'])),
        sound_peak_reduction_behind=dict(sim_dB=S['behind_1m']['reduction_dB'], published='20 to 28 dB',
            source='Murphy et al. (2018): instructor position about 1 m behind the shooter (abstract)', status='prediction once the two sound parameters are set; the bare reference here is the HK416 directivity law extrapolated to 180 degrees'),
        suppressed_level_at_ear=dict(sim_dB=S['shooter']['suppressed_dB'], published='most suppressed AR-15 conditions 140 to 150 dB at the ear; above 140 dB at the right ear',
            source='Lobarinas et al. (2016), abstract and the Student Academy of Audiology summary', status='follows from the ear calibration; the model has no ejection-port or gas-vent source, which is what the paper blames for the right ear, so it sits below the measured band'),
        supersonic_crack=dict(sim='N-wave entries untouched: %.1f dB at the down-range listener, bare and suppressed' % F['downrange']['crack_dB'], unchanged=bool(S['downrange']['crack_unchanged'] and F['downrange']['crack_unchanged']),
            muzzle_blast_downrange_dB=dict(bare=S['downrange']['bare_dB'], suppressed=S['downrange']['suppressed_dB']),
            published='a suppressor does not affect the ballistic shock of a supersonic bullet', source='physics (Whitham 1952 N-wave depends on the bullet alone); assets/hk416/sound section 2', status='by construction'),
        first_round_pop=dict(sim_dB_side=round(F['side_1m']['suppressed_dB'] - S['side_1m']['suppressed_dB'], 2), sim_dB_ear=round(F['shooter']['suppressed_dB'] - S['shooter']['suppressed_dB'], 2),
            sim_dB_swell_after_the_pop=round(core.db(snd['first_round']['listeners'][0]['hump_P1m']) - core.db(snd['subsequent']['listeners'][0]['hump_P1m']), 2),
            sim_dB_positive_impulse=round(core.db(snd['first_round']['listeners'][0]['impulse_pos_Pa_s']) - core.db(snd['subsequent']['listeners'][0]['impulse_pos_Pa_s']), 2),
            o2_burnt_mg=round(first['o2_burnt_kg'] * 1e6, 1), o2_available_mg=round(sum(core.Y_O2 * core.PATM * v / (core.RA * core.T_AMB) for v in cfg['chambers']['volume_m3']) * 1e6, 1),
            published='no controlled 5.56 figure found; trade sources give 5 to 10 dB in general and "little difference" on short 5.56 rifles',
            source='The Truth About Guns, "The science of silence" (general estimate); RECOIL, best 5.56 suppressors (5.56 remark). Neither is a measurement report',
            status='prediction, unverified'),
        heat_per_shot=dict(sim_K_cold=round(q_first / C, 2), sim_K_warm=round(hs[0] / C, 2), sim_J_cold=round(q_first, 0), published='7 to 10 F (3.9 to 5.6 K) per round, rule of thumb; 100 rounds raise the core about 750 F (4.2 K per round)',
            source='retailer rule of thumb (Silencer Central and others, no method given); Small Arms Defense Journal (100-round burst figure, as found by search; article not read in full)',
            status='prediction with an inferred Stanton number (not fitted)'),
        heat_strings=strings,
        heat_100_rounds=dict(sim_rise_F=strings['rapid_100_in_50s']['rise_F'], published='about 750 F above ambient', source='Small Arms Defense Journal, as above', status='prediction'),
        back_pressure=dict(
            bore_MPa_at_unlock=dict(bare=A['bare_thrust']['bore_MPa_at_unlock'], suppressed=A['suppressed']['bore_MPa_at_unlock']),
            peak_carrier_change_pct=pct(A['suppressed']['peak_carrier_mps'], A['bare_thrust']['peak_carrier_mps']),
            carrier_at_eject_change_pct=pct(A['suppressed']['carrier_at_eject_mps'], A['bare_thrust']['carrier_at_eject_mps']),
            cyclic_rate_change_pct=pct(A['suppressed']['cyclic_rpm'], A['bare_thrust']['cyclic_rpm']),
            cyclic_rpm=dict(shipped=A['shipped']['cyclic_rpm'], bare_with_thrust=A['bare_thrust']['cyclic_rpm'], suppressed=A['suppressed']['cyclic_rpm'], suppressed_without_residual_thrust=A['supp_gas_only']['cyclic_rpm']),
            gas_to_face_mg=dict(bare=round(bare['mass_breech_kg'] * 1e6, 2), suppressed=round(sub['mass_breech_kg'] * 1e6, 2), ratio=round(sub['mass_breech_kg'] / max(bare['mass_breech_kg'], 1e-12), 1)),
            published='M4A1 (direct impingement) with a suppressor: about 25 % more bolt carrier speed; patents cite 20 to 30 % more rate of fire. No HK416 figure found; the manual gives 700 to 900 rpm for the bare rifle',
            source='NDIA 2016 Armament Systems Forum briefing 18366 (Davis), slide figure; US patents 10151544 and 11578931 (inventors\' statements)',
            status='prediction. The HK416 short-stroke piston vents after 3 mm, so the gas system itself adds little; residual bore pressure first grips the case harder (slower without the thrust term), then pushes on the case head'),
        recoil=dict(impulse_Ns=dict(bare=A['shipped']['recoil_impulse_Ns'], suppressed=A['suppressed']['recoil_impulse_Ns']), impulse_change_pct=pct(A['suppressed']['recoil_impulse_Ns'], A['shipped']['recoil_impulse_Ns']),
            free_recoil_mps=dict(bare=A['shipped']['free_recoil_mps'], suppressed=A['suppressed']['free_recoil_mps']), status='prediction; the same blowdown scale as the HK416 action is applied to the exit thrust'),
        blast_scaling_cross_check=dict(peak_enthalpy_flux_MW=dict(bare=round(bare['peak_hdot_exit'] / 1e6, 3), suppressed=round(sub['peak_hdot_exit'] / 1e6, 4)),
            reduction_if_blast_like_dB=round(11.0 * math.log10(hdot_ratio), 1),
            note='Fansler and Schmidt scale peak overpressure with (energy efflux rate)^0.55. Applied to the can it gives the reduction the exit flow would have if it started as abruptly as a bare muzzle: a lower bound on the reduction.',
            source='Fansler and Schmidt (1983), BRL-TR-2504 (exponent recalled, not re-read)', status='bound'),
        bare_equivalence=dict(bore_pressure=eq, blowdown_impulse_raw_Ns=dict(action=round(raw_blow, 4), core=round(bare0['impulse_Ns'], 4)),
            cyclic_rpm=dict(action_json=aj['auto']['rpm'], action_rerun=round(rpm_ship, 1), with_core_blowdown=round(A['bare_core']['cyclic_rpm'], 1)), status='consistency check of core.py against assets/hk416/action'),
        conservation=dict(mass_error_bare=float('%.3g' % mass_err), mass_error_suppressed=float('%.3g' % mass_err_s),
            energy_bare_J=dict(initial=round(E0, 1), enthalpy_out=round(bare['enthalpy_out_J'], 1), left_in_bore=round(e_end, 1), unaccounted=round(E0 - bare['enthalpy_out_J'] - e_end, 1),
                note='the unaccounted part is the enthalpy of the %.1f mg breech leak, which is not tallied' % (bare['mass_breech_kg'] * 1e6)), status='numerical check'),
        geometry=dict(mass_g=round(cfg['mass_kg'] * 1e3, 0), mass_oz=round(cfg['mass_kg'] / 0.0283495, 1), length_mm=geom.L, diameter_mm=geom.G['tube_od'], gas_volume_cm3=round(sum(cfg['chambers']['volume_m3']) * 1e6, 1),
            published='fielded 5.56 QD cans: about 6 to 7 in long, 1.5 in diameter, 14 to 22 oz', source='makers\' published specifications in general (class figures, recalled; no single product)', status='inside the class by design'),
    )

    data = dict(
        meta=dict(title='Generic QD 5.56 mm suppressor on the HK416 D14.5RS: gas dynamics, sound, back-pressure, heat, flash', credit='carpetshark',
                  generator='assets/suppressor-qd-556/sim/sim.py', model='lumped-parameter; see README.md for the physics, sources and limits',
                  frame='metres, +Z down-range, +Y up, +X to the shooter\'s left; origin at socket_mount = the HK416 socket_muzzle',
                  time_zero='the bullet base leaving the barrel crown (HK416 events.bullet_exit); add hk416.exit_after_sear_s for the HK416Action clock',
                  units='SI unless a key says otherwise'),
        hk416=dict(exit_after_ignition_s=round(info['t_exit'], 6), exit_after_sear_s=round(FT[2]['ignition'] + info['t_exit'], 6), socket_muzzle_gun_frame=aj['meta']['nodes']['present']['socket_muzzle'],
                   exit_pressure_MPa=round(info['p_exit_mean'] / 1e6, 2), bore_T_K=round(cfg['bore']['T'], 1), muzzle_velocity=round(info['v_exit'], 2)),
        params={k: dict(value=v[0], unit=v[1], source=v[2], note=v[3]) for k, v in PARAMS.items()},
        config=cfg,
        model=dict(note='from model/geom.py: what a page needs to draw the section and play the QD clips. Polygons are (s, r) in mm, s = z*1000 + s_mount.',
                   s_mount=geom.S_MOUNT, length_mm=geom.L, r_out=geom.R_OUT, bore_r=geom.RB,
                   parts={nm: dict(material=p['mat'], group=p['group'], role=p['role'], poly=[[round(a, 3), round(b, 3)] for a, b in p['poly']]) for nm, p in geom.parts().items()},
                   jaw={k: v for k, v in geom.jaw().items() if k in ('s0', 's1', 'r_in', 'r_out', 'arc_deg', 'role')}, jaw_travel=geom.G['jaw_travel'], collar_turn_deg=geom.G['collar_turn_deg'],
                   rifle=dict(hider=[[round(a, 3), round(b, 3)] for a, b in geom.hider_poly()], crown_s=geom.S_CROWN, hider_rear_s=geom.S_HIDER0, jam_ring_r=geom.G['jam_ring_r']),
                   baffle_apex_s=[geom.baffle_apex(i) for i in range(geom.G['n_baffles'])], sockets=geom.sockets(), clips=geom.clips(), fit_checks_mm=geom.fit_checks()),
        states=dict(note='first_round: cold can full of air. subsequent: a few rounds in, can full of spent gas, 320 K wall (the reference state). hot: 600 K wall.',
                    bare=summary(cfg, bare), first_round=summary(cfg, first), subsequent=summary(cfg, sub), hot=summary(cfg, hot)),
        sound=dict(note='Peak levels of the muzzle (exit) source. pop = the uncorking pulse, hump = the swell after it, both at 1 m; levels at the HK416 listeners use its path lengths. The N-wave of the bullet is not changed.', **snd),
        flash=dict(note='Interface for assets/hk416/flash (not on this branch when this was built): multiply each phase of the bare flash by scale[phase], move the source to socket_exit, delay it by delay_s.', **fl),
        heat=dict(note='Bulk can temperature. shot heat by wall temperature is in config.heat; strings below are still-air cooling.', strings=strings,
                  share_by_chamber=[round(q / sub['heat_total_J'], 4) for q in sub['heat_wall_J']]),
        action=dict(note='HK416 action (assets/hk416/action/sim.py run) driven by the bore pressure, gas temperature and exit thrust of core.py. overlay holds the blocks of action.json for the suppressed rifle.',
                    cases=A, input=dict(note='blowdown tables against time since the bullet left the crown: what replaces the tail of the HK416 interior-ballistics tables (pbr, tg, fg) when the can is fitted',
                                        over=dict(m_gun_add_kg=cfg['mass_kg'], residual_thrust=P['residual_thrust'], case_seal_len=P['case_seal_len'], port_d=ov_b['port_d']),
                                        bare=thin(bare['rec'], ('p_bore', 'T_bore', 'thrust')), suppressed=thin(sub['rec'], ('p_bore', 'T_bore', 'thrust'))),
                    overlay=overlay),
        series=dict(note='the reference shot (subsequent) and the first round, for plots: chamber pressures (Pa), exit flow, sound pressure at 1 m (mono = all directions, dip = times cos(theta))',
                    subsequent=dict(thin(sub['rec'], ('p_bore', 'q_exit', 'm_exit', 'mono', 'dip')), p=[[float('%.5g' % v) for v in sub['rec']['p'][i]] for i in
                                    ([i for i, t in enumerate(sub['rec']['t']) if t < 4e-3][::20] + [i for i, t in enumerate(sub['rec']['t']) if t >= 4e-3][::4])]),
                    first_round=thin(first['rec'], ('p_bore', 'q_exit', 'm_exit', 'mono', 'dip')),
                    bare=thin(bare['rec'], ('p_bore', 'q_exit', 'm_exit'))),
    )
    # ---- parity references for test.js: full-precision outputs of short runs
    par = {}
    for nm, opt in (('bare', dict(bare=True, t_end=8e-3, breech=br_b)), ('first_round', dict(o2=1.0, t_wall=core.T_AMB, t_end=12e-3, breech=br_s)),
                    ('subsequent', dict(o2=0.0, t_wall=P['warm_wall'], t_end=12e-3, breech=br_s))):
        s = core.run_shot(cfg, opt); a = core.acoustics(cfg, s)
        o = {k: v for k, v in s.items() if k != 'rec'}
        o['rec_samples'] = {k: [s['rec'][k][i] for i in range(0, len(s['rec']['t']), 400)] for k in ('t', 'p_bore', 'q_exit', 'mono', 'dip', 'qf', 'ff')}
        par[nm] = dict(opt={k: v for k, v in opt.items() if k != 'breech'}, breech='bare' if nm == 'bare' else 'suppressed', out=o, acoustics=a)
    pat = core.sound_overlay(cfg, hkp, par['subsequent']['acoustics'], par['bare']['acoustics'], cfg['mech'])
    par['sound_overlay'] = dict(note='from the 12 ms parity runs', persp={nm: {k: pat['persp'][nm][k] for k in ('blast', 'sec', 'jet')} for nm in ('shooter', 'bystander', 'downrange')},
                                cycle=pat['cycle'], cycle_s=pat['cycle_s'], auto1s=pat['variants']['auto1s']['times'])
    par['flash'] = core.flash_input(cfg, core.run_shot(cfg, par['subsequent']['opt'] | dict(breech=br_s)), core.run_shot(cfg, par['bare']['opt'] | dict(breech=br_b)))
    times = [0.0, 0.5, 1.0, 1.08, 1.16, 30.0, 30.5]
    par['heat_string'] = dict(times=times, out=core.heat_string(cfg, times))
    data['parity'] = par

    with open(os.path.join(HERE, 'suppressor.json'), 'w') as fh: json.dump(data, fh, separators=(',', ':'))
    with open(os.path.join(HERE, 'checks.json'), 'w') as fh: json.dump(checks, fh, indent=1)
    print('wrote suppressor.json (%.0f kB) and checks.json in %.0f s' % (os.path.getsize(os.path.join(HERE, 'suppressor.json')) / 1e3, time.time() - t0))
    print(json.dumps({k: v for k, v in checks.items() if k not in ('bare_equivalence',)}, indent=1)[:6000])
    if plots:
        import plots as _pl
        _pl.make(data, checks, dict(bare=bare, sub=sub, first=first, hot=hot), dict(bare=r_b, supp=r_s), os.path.join(HERE, 'plots'))
    return data


if __name__ == '__main__':
    main()
