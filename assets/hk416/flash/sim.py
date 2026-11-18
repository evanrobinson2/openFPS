#!/usr/bin/env python3
"""HK416 D14.5RS muzzle flash and smoke simulation.

    python3 sim.py            # writes flash.json, plots/*.png and renders/*.png (about a minute)
    node test_flash.js        # JS-vs-Python parity, writes parity.json
    python3 sim.py --no-render

Needs numpy, scipy, matplotlib and Pillow, and ../action/ (action.json and sim.py: the interior ballistics). See README.md for the physics, the sources and the limits.
"""
import json, math, sys, os
import numpy as np
import physics as ph
from physics import P

HERE = os.path.dirname(os.path.abspath(__file__))
T_MS_BASE = [0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8]
T_SEC_MS = [0, 0.6, 0.7, 0.8, 0.9, 1, 1.15, 1.3, 1.45] + [round(1.6 + 0.25 * i, 2) for i in range(18)] + [round(6.1 + 0.5 * i, 1) for i in range(14)] + [13.6, 14.6, 15.6, 17, 18.5, 20]
T_SMOKE = [0.002, 0.005, 0.01, 0.02, 0.035, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6]
FINE = np.concatenate([np.linspace(0, 3e-3, 12001), np.linspace(3e-3, 0.12, 2400)[1:]])
T_MS = list(T_MS_BASE)

def r(x, n=4):
    """Round to n significant figures for the JSON."""
    if isinstance(x, (list, tuple, np.ndarray)): return [r(v, n) for v in x]
    x = float(x)
    return 0.0 if x == 0 or not math.isfinite(x) else float(f'{x:.{n}g}')

def total_I(shot, t, cal):
    f = ph.phases(shot, t, cal)
    return f['primary']['I'] + f['intermediate']['I'] + (f['slot_jet']['I'] * shot.n_slots if shot.n_slots else 0)

def build():
    # ---------------- the drive: action/'s interior ballistics (nothing about the charge or the bore is set here)
    ib = ph.drive()
    ib16 = ph.drive(16 * 0.0254)
    manual_v = {10: 774, 14.5: 850, 16.5: 880, 20: 915}
    vcheck = [dict(barrel_in=L, model_m_s=r(ph.drive(L * 0.0254)['v']), manual_m_s=v) for L, v in manual_v.items()]
    A = ph.ACTION; ab = A['ballistics']; ie = int(round(ib['t_exit'] / ab['dt'])) + 1      # first action.json sample after exit
    drive_check = dict(
        note='the bore state used here against the numbers printed in action/action.json (same model, re-run through action/sim.py ib_solve with the stored calibration)',
        muzzle_velocity_m_s=[r(ib['v'], 6), r(A['validation']['muzzle_velocity']['sim'], 6)],
        peak_chamber_pressure_MPa=[r(ib['p_max'] / 1e6, 6), r(A['validation']['chamber_pressure']['sim'], 6)],
        barrel_time_ms=[r(ib['t_exit'] * 1e3, 6), r(A['validation']['barrel_time']['sim'], 6)],
        reservoir_pressure_MPa_at_sample=[r(float(np.interp(ie * ab['dt'] - ib['t_exit'], ib['blow']['t'], ib['blow']['p0'])) / 1e6, 5), ab['chamber_MPa'][ie]],
        reservoir_temperature_K_at_sample=[r(float(np.interp(ie * ab['dt'] - ib['t_exit'], ib['blow']['t'], ib['blow']['T0'])), 5), ab['gas_temp_K'][ie]],
        order='[this simulation, action.json]')
    shot = ph.Shot(ib, hider=True)
    bare = ph.Shot(ib, hider=False)
    ref_a2 = ph.Shot(ib16, hider=True, slots=5)        # the TTAG test: 16 in barrel, A2 birdcage (5 slots)
    ref_bare = ph.Shot(ib16, hider=False)

    # ---------------- photometric calibration against the TTAG light-meter readings (16 in barrel)
    I_ref = np.array([total_I(ref_a2, t, 1.0) for t in FINE])
    raw = ph.meter_reading(FINE, I_ref, P('anchor_dist'), P('anchor_tau'))
    cal = P('anchor_lux_a2') / raw
    I_bare_thermal = np.array([total_I(ref_bare, t, cal) for t in FINE])
    unit = ph.meter_reading(FINE, ph.secondary_pulse(FINE, 1.0), P('anchor_dist'), P('anchor_tau'))
    base = ph.meter_reading(FINE, I_bare_thermal, P('anchor_dist'), P('anchor_tau'))
    I_sec_pk = (P('anchor_lux_bare') - base) / unit

    # ---------------- secondary-flash ignition: two constants fitted to two observations (16 in barrel)
    # bare muzzle lights essentially every shot (P = 0.95); the A2 did not in 3 of 3 shots (P = 0.1, inferred)
    from scipy.optimize import brentq
    from scipy.special import erfinv
    sig = P('T_ignite_sigma')
    T_ign = ph.mix_temperature(ref_bare, ph.R_FLAMMABLE) - math.sqrt(2) * sig * erfinv(2 * 0.95 - 1)
    T_need = T_ign + math.sqrt(2) * sig * erfinv(2 * 0.10 - 1)
    r_h = brentq(lambda q: ph.mix_temperature(ref_a2, q) - T_need, 0.5, 5)
    ign = {k: ph.ignition(s, T_ign, r_h) for k, s in (('hk416_14p5_hider', shot), ('hk416_14p5_bare', bare),
                                                       ('ref_16_a2', ref_a2), ('ref_16_bare', ref_bare))}
    ib10 = ph.drive(10 * 0.0254)
    ign['hk416_10_hider'] = ph.ignition(ph.Shot(ib10, hider=True), T_ign, r_h)

    # ---------------- time series (the table is refined around the short peak of the intermediate flash)
    global T_MS
    pk = shot.t_xmax * 1e3
    T_MS = sorted(set(round(v, 4) for v in list(T_MS_BASE) + list(np.arange(max(pk - 0.08, 0.005), pk + 0.2, 0.005))))
    ts = np.array(T_MS) * 1e-3
    fr = [ph.phases(shot, t, cal) for t in ts]
    def series(key, name): return [f[key][name] for f in fr]
    def rgbs(key, sec=False): return [r(ph.rgb_of(ph.spectrum(f[key]['T'], f[key]['eps'], sec)), 3) if f[key]['L'] > 1e-9 else [1, 0.2, 0] for f in fr]
    I_tot = np.array([total_I(shot, t, cal) for t in ts])
    I_fine = np.array([total_I(shot, t, cal) for t in FINE])
    cum = np.interp(ts, FINE, np.concatenate([[0], np.cumsum(0.5 * (I_fine[1:] + I_fine[:-1]) * np.diff(FINE))]))
    # colour of the light: luminance-weighted temperature and rgb
    def light_rgb(i):
        f = fr[i]; w = [f['primary']['I'], f['intermediate']['I'] + f['slot_jet']['I'] * shot.n_slots]
        if sum(w) <= 0: return [1, 0.2, 0], f['primary']['T']
        c = (w[0] * ph.rgb_of(ph.spectrum(f['primary']['T'], f['primary']['eps'])) +
             w[1] * ph.rgb_of(ph.spectrum(f['intermediate']['T'], f['intermediate']['eps']))) / sum(w)
        return r(c, 3), (w[0] * f['primary']['T'] + w[1] * f['intermediate']['T']) / sum(w)
    lrgb = [light_rgb(i) for i in range(len(ts))]
    xcen = [(f['intermediate']['I'] * (f['intermediate']['x_disk'] + 0.35 * f['intermediate']['length'])) /
            max(f['primary']['I'] + f['intermediate']['I'], 1e-30) for f in fr]

    tsec = np.array(T_SEC_MS) * 1e-3
    sec_scale = P('sec_hider_scale')
    I_sec = ph.secondary_pulse(tsec, I_sec_pk)
    tt = np.maximum(tsec - P('sec_delay'), 0)
    grow = 1 - np.exp(-tt / 1.2e-3)
    sec_len, sec_dia = 0.20 + 0.95 * grow, 0.18 + 0.93 * grow        # envelope (about 7 sigma); the part above a quarter of the peak is half of it
    sec_spec = ph.spectrum(P('T_secondary'), 0.05, True)
    sec_fine = ph.secondary_pulse(FINE, I_sec_pk)

    # ---------------- smoke
    src, impulse, heat = ph.smoke_sources(shot)
    tracks = []
    for s in src:
        p, R, tau = ph.puff_track(s, T_SMOKE)
        tracks.append(dict(name=s['name'], pos_m=[r(q, 4) for q in p], radius_m=r(R, 4), tau_centre_whole=r(tau, 3)))

    z0, z1 = P('fh_slot_z'); lean = math.radians(P('slot_lean_deg'))
    slots = []
    for k in range(shot.n_slots):
        th = math.radians(30 + 60 * k)
        slots.append(dict(angle_from_up_deg=30 + 60 * k,
                          origin_m=r([math.sin(th) * P('fh_r'), math.cos(th) * P('fh_r'), (z0 + z1) / 2]),
                          jet_dir=r([math.sin(th) * math.sin(lean), math.cos(th) * math.sin(lean), math.cos(lean)])))
    sp = {k: ph.spectrum(v['T'], v['eps']) for k, v in ph.phases(shot, 2e-4, cal).items()}
    f02 = ph.phases(shot, 2e-4, cal)

    E_frame = float(cum[-1])
    # ---------------- numbers for the JS-vs-Python parity test (computed here from the physics, not from the tables)
    te = ib['t_exit']; cumf = np.concatenate([[0], np.cumsum(0.5 * (I_fine[1:] + I_fine[:-1]) * np.diff(FINE))])
    def mean_I(a, b): return float(np.interp(b - te, FINE, cumf, left=0) - np.interp(a - te, FINE, cumf, left=0)) / (b - a)
    wins = [(0.0, 1 / 60), (0.0, 1 / 240), (te + 1e-4, te + 4e-4), (te + shot.t_xmax - 2e-5, te + shot.t_xmax + 6e-5), (1 / 240, 2 / 240)]
    t_off = [shot.t_xmax + d for d in (-3.3e-5, -1.2e-5, 0.7e-5, 2.3e-5, 5.1e-5, 1.13e-4, 3.7e-4, 9.1e-4)]
    wind = (-2.0, 0.0, 0.5)
    parity = dict(
        note='computed by sim.py straight from physics.py; test_flash.js asks hk416-flash.js for the same things. Times are seconds since ignition; positions in the muzzle frame.',
        frame_mean_intensity=[dict(t0=a, t1=b, cd=mean_I(a, b)) for a, b in wins],
        light_instant=[dict(t=te + t, cd=total_I(shot, t, cal)) for t in t_off],
        secondary_instant=[dict(t=te + t, share=k, cd=float(ph.secondary_pulse(t, I_sec_pk)) * k) for t, k in ((1.1e-3, 0.3), (2.4e-3, 0.3), (2.4e-3, 1.0), (7e-3, 1.0))],
        smoke=dict(t=te + 1.0, wind=list(wind), puffs=[dict(name=s_['name'], pos_m=[float(v) for v in ph.puff_track(s_, [1.0], wind)[0][0]], radius_m=float(ph.puff_track(s_, [1.0], wind)[1][0])) for s_ in ph.smoke_sources(shot)[0]]))
    out = dict(
        meta=dict(
            title='HK416 D14.5RS muzzle flash and smoke simulation',
            credit='carpetshark', generator='assets/hk416/flash/sim.py', schema=2,
            frame='tables are in the muzzle frame: origin at socket_muzzle (hider face, on the bore axis), axes parallel to the gun frame (+Z down-range, +Y up, +X to the shooter\'s left; the rifle\'s right side is -X); metres. socket_muzzle_gun_frame gives its place in the gun frame.', socket_muzzle_gun_frame=A['meta']['nodes']['present']['socket_muzzle'],
            units='SI. t_ms in milliseconds after the bullet base leaves the barrel crown (see timing), t_s in seconds; lengths in mm where the key says _mm, else m; intensity_cd = luminous intensity seen side-on; luminance in cd/m2; rgb = linear sRGB with luminance 1',
            config='D14.5RS, 14.5 in barrel, M855 (as action/), the modelled 6-slot birdcage flash hider'),
        parameters={k: dict(value=(list(v[0]) if isinstance(v[0], tuple) else v[0]), unit=v[1], source=v[2], note=v[3]) for k, v in ph.PARAMS.items()},
        timing=dict(
            ignition_after_sear_s=P('ignition_after_sear'), bullet_exit_after_ignition_s=r(ib['t_exit'], 6),
            bullet_exit_after_sear_s=r(P('ignition_after_sear') + ib['t_exit'], 6),
            note='from action/: the charge ignites 8.51 ms after the sear releases the hammer and the bullet base leaves the crown 0.976 ms after that. Every t_ms table in this file counts from bullet exit; HK416Flash takes time from ignition and adds the offset. The 41 microseconds the bullet base then spends inside the hider cage are not resolved.'),
        drive=dict(
            source='../action/action.json and ../action/sim.py (ib_solve): Resal energy balance, Nobel-Abel gas, Lagrange gradient; after exit the bore empties as an isentropic reservoir through a sonic muzzle',
            bullet_exit=dict(t_from_ignition_ms=r(ib['t_exit'] * 1e3), velocity_m_s=r(ib['v']), base_pressure_MPa=r(ib['p_base'] / 1e6),
                             reservoir_pressure_MPa=r(ib['p_mean'] / 1e6), reservoir_temperature_K=r(ib['T']), gas_mass_kg=P('charge_mass'),
                             burnt_fraction=r(ib['z']), gamma=P('gamma'), gas_constant_J_kgK=r(ib['Rg']), molar_mass_g_mol=r(8314 / ib['Rg']),
                             note='action/ empties the bore as a reservoir holding the whole charge as gas at the mean pressure; its temperature there (1797 K) is what this simulation takes as the stagnation temperature of the muzzle flow. Just before exit action/ prints 1956 K for the burnt fraction alone (92.6 %); the step is its own change of book-keeping, kept as it is.'),
            check_against_action_json=drive_check,
            velocity_check=dict(rows=vcheck, note='the same model at the manual\'s other barrel lengths (HK manual p. 7). It shows how far the 16 in reference run behind the photo and light-meter comparisons can be trusted.'),
            gas_composition_mole_fraction=dict(CO=0.42, H2=0.11, H2O=0.21, CO2=0.13, N2=0.12, other=0.01,
                source='inferred: typical frozen muzzle composition of a double-base ball powder (fuel-rich: CO + H2 over half). Used only for the wording of the secondary flash and the water-vapour figure.')),
        blowdown=dict(
            model='action/sim.py: isentropic emptying of the bore reservoir through a sonic muzzle. p0 and T0 are the reservoir state; mass flow is the choked-nozzle flow of that state; thrust is action\'s bore force after exit (scaled there to the SAAMI gas momentum)',
            p00_MPa=r(shot.p00 / 1e6), T00_K=r(shot.T0), exit_mach=r(shot.Me), gas_impulse_N_s=r(impulse),
            gas_mass_out_kg=r(float(np.trapezoid(shot.bd['mdot'], shot.bd['t']))),
            t_ms=T_MS, p0_MPa=r(shot.p0(ts) / 1e6), T0_K=r(shot.T0t(ts)), mass_flow_kg_s=r(shot.mdot(ts)), thrust_N=r(shot.thrust(ts)),
            half_pressure_ms=r(float(shot.bd['t'][np.argmax(shot.bd['p0'] < 0.5 * shot.p00)]) * 1e3),
            unchoke_ms=r(float(shot.bd['t'][np.argmax(shot.bd['p0'] < P_ATM_CRIT(shot))]) * 1e3)),
        hider=dict(length_m=P('fh_len'), outer_radius_m=P('fh_r'), chamber_radius_m=P('fh_chamber_r'), crown_behind_face_m=P('fh_crown_back'),
                   slot_z_m=list(P('fh_slot_z')), slot_width_m=P('fh_slot_w'), slots=slots, mouth_mach=r(shot.Mm),
                   axial_momentum_share=r(shot.f_ax), mass_share_per_slot=r(shot.f_slot),
                   mouth_static_pressure_MPa_t0=r(float(shot.p_mouth(0)) / 1e6)),
        jet=dict(
            t_ms=T_MS,
            mach_disk_x_mm=r(shot.x_disk(ts) * 1e3), mach_disk_d_mm=r(P('disk_d_over_x') * shot.x_disk(ts) * 1e3),
            mach_disk_steady_mm=r(shot.x_full(ts) * math.sqrt(shot.f_ax) * 1e3), bullet_base_x_mm=r(shot.ve * ts * 1e3),
            gas_front_x_mm=r(shot.x_front(ts) * 1e3), blast_radius_mm=r(shot.blast_radius(ts) * 1e3),
            slot_disk_dist_mm=r(shot.x_disk(ts, shot.f_slot) * 1e3),
            bare_muzzle_mach_disk_x_mm=r(bare.x_disk(ts) * 1e3),
            note='x measured from the hider face along the bore; slot_disk_dist along each slot jet from its slot. Cell pattern: one barrel shock and Mach disc per jet; behind the disc the gas is subsonic at about the reservoir temperature; weaker cells further out are not resolved.'),
        phases=dict(
            t_ms=T_MS,
            precursor=dict(note='air and blow-by pushed out ahead of the bullet (about -0.3 to 0 ms). Weak red glow; not simulated, no light assigned.'),
            primary=dict(what='gas stagnating in the front of the cage, seen through the slots and the mouth',
                         intensity_cd=r(series('primary', 'I')), intensity_from_front_cd=r(series('primary', 'I_front')),
                         luminance=r(series('primary', 'L')), T_K=r(series('primary', 'T')), emissivity=r(series('primary', 'eps'), 3), rgb=rgbs('primary')),
            intermediate=dict(what='muzzle glow: gas re-heated behind the Mach disc of the mouth jet, with some air burning in (intermediate flash)',
                              intensity_cd=r(series('intermediate', 'I')), luminance=r(series('intermediate', 'L')), T_K=r(series('intermediate', 'T')),
                              emissivity=r(series('intermediate', 'eps'), 3), rgb=rgbs('intermediate'),
                              start_z_mm=r(np.array(series('intermediate', 'x_disk')) * 1e3), width_mm=r(np.array(series('intermediate', 'width')) * 1e3),
                              length_mm=r(np.array(series('intermediate', 'length')) * 1e3),
                              shape='sharp bright face at start_z (the Mach disc), tapering down-range over length; width is the disc diameter'),
            slot_jet=dict(what='the same glow behind the small Mach disc of each of the six slot jets (per slot)',
                          intensity_cd=r(series('slot_jet', 'I')), luminance=r(series('slot_jet', 'L')), T_K=r(series('slot_jet', 'T')),
                          rgb=rgbs('slot_jet'), dist_mm=r(np.array(series('slot_jet', 'x_disk')) * 1e3),
                          width_mm=r(np.array(series('slot_jet', 'width')) * 1e3), length_mm=r(np.array(series('slot_jet', 'length')) * 1e3)),
            secondary=dict(what='re-ignition of the fuel-rich gas in air: a fireball. Suppressed on most shots by the hider.',
                           probability=r(ign['hk416_14p5_hider']['probability'], 2),
                           probability_bare_muzzle=r(ign['hk416_14p5_bare']['probability'], 2),
                           ignition={k: {a: r(b) for a, b in v.items()} for k, v in ign.items()},
                           t_ms=T_SEC_MS, intensity_cd_full=r(I_sec), hider_scale=sec_scale,
                           intensity_cd=r(I_sec * sec_scale), T_K=P('T_secondary'), rgb=r(ph.rgb_of(sec_spec), 3),
                           centre_z_mm=r((0.02 + 0.25 * sec_len * math.sqrt(sec_scale)) * 1e3), centre_z_mm_full=r((0.02 + 0.25 * sec_len) * 1e3), length_mm=r(sec_len * 1e3 * math.sqrt(sec_scale)),
                           diameter_mm=r(sec_dia * 1e3 * math.sqrt(sec_scale)), length_mm_full=r(sec_len * 1e3), diameter_mm_full=r(sec_dia * 1e3),
                           integral_cd_s=r(float(np.trapezoid(sec_fine, FINE)) * sec_scale),
                           note='intensity_cd_full is the full fireball, its peak set by the TTAG bare-muzzle reading of 10,760 lx; through the hider a secondary flash is usually partial (hider_scale, inferred). Final sizes are fitted to the two service photos in REFERENCES.md (full: 103rd Rescue Squadron M4; partial: Marine M4A1 at dusk); the growth law is inferred. length and diameter are the envelope of the fireball; the part brighter than a quarter of the peak is about half as big.'),
            sparks=dict(what='residual sparks: burning grains and hot metal thrown down-range', mean_count=2, speed_m_s=[40, 250],
                        cone_half_angle_deg=25, life_ms=[15, 80], T_K=[1800, 1200], intensity_cd=[0.01, 0.05],
                        source='inferred from streaks in the cited dusk and night-vision photos; not simulated'),
            relative_strength=dict(
                primary_cd_ms=r(np.trapezoid([total_part(shot, t, cal, 'primary') for t in FINE], FINE) * 1e3),
                intermediate_cd_ms=r(np.trapezoid([total_part(shot, t, cal, 'intermediate') for t in FINE], FINE) * 1e3),
                slot_jets_all_cd_ms=r(np.trapezoid([total_part(shot, t, cal, 'slot_jet') for t in FINE], FINE) * 1e3),
                secondary_if_it_lights_cd_ms=r(float(np.trapezoid(sec_fine, FINE)) * sec_scale * 1e3),
                secondary_bare_muzzle_cd_ms=r(float(np.trapezoid(sec_fine, FINE)) * 1e3))),
        spectra=dict(wavelength_nm=ph.LAM.tolist(), unit='W m-2 sr-1 nm-1 at t = 0.2 ms (secondary: at its own temperature, emissivity 0.05)',
                     primary=r(sp['primary'], 3), intermediate=r(sp['intermediate'], 3), secondary=r(sec_spec, 3),
                     features={k: dict(centre_nm=v[0], sigma_nm=v[1], strength=v[2]) for k, v in ph.LINES.items()},
                     note='grey particulate continuum at the phase temperature; Na and K resonance lines and CaOH/CuOH bands fill toward the blackbody ceiling. Feature strengths are inferred; the species are published. The K doublet at 766/770 nm carries much of the near-infrared signature (bright in night vision) but little visible light.'),
        light=dict(
            what='point light for the game: luminous intensity (cd) and colour of the whole flash without a secondary flash',
            t_ms=T_MS, intensity_cd=r(I_tot), cumulative_cd_s=r(cum, 5), colorK=r([c[1] for c in lrgb]), rgb=[c[0] for c in lrgb],
            position_z_m=r(xcen), peak_cd=r(I_fine.max()), peak_t_ms=r(FINE[I_fine.argmax()] * 1e3), integral_cd_s=r(E_frame, 5),
            fwhm_ms=r(float(np.ptp(FINE[I_fine > I_fine.max() / 2])) * 1e3),
            frame60=dict(intensity_cd=r(E_frame * 60), note='the whole flash spread over one 1/60 s frame (same luminous energy)'),
            secondary=dict(t_ms=T_SEC_MS, intensity_cd=r(I_sec * sec_scale), colorK=P('T_secondary'), rgb=r(ph.rgb_of(sec_spec), 3),
                           position_z_m=r(0.02 + 0.25 * sec_len * math.sqrt(sec_scale)), integral_cd_s=r(float(np.trapezoid(sec_fine, FINE)) * sec_scale, 5))),
        smoke=dict(
            what='particulate and condensate plume as entraining puffs. Positions in the muzzle frame.',
            particulate_mass_kg=r(P('charge_mass') * P('smoke_mass_frac')), mass_extinction_m2_per_kg=P('smoke_kext'), albedo=P('smoke_albedo'),
            rgb=[0.80, 0.82, 0.86], entrain_alpha=P('entrain_alpha'), ambient_spread_m_s=P('ambient_spread'), rho_air=ph.RHO_AIR, T_air_K=ph.T_ATM,
            gas_thermal_energy_J=r(heat), water_vapour_kg=r(P('charge_mass') * 0.16),
            condensate_note='about 0.27 g of water vapour leaves with the gas; it condenses to a white mist only in cold or humid air (not simulated; raise opacity up to 3x for a cold-weather look, inferred)',
            sources=src,
            opacity_rule='optical depth through a puff at impact parameter b: tau = tau_centre * exp(-b^2 / (2 (R/2)^2)), tau_centre = kext * smoke_mass * share / (2 pi (R/2)^2); opacity = 1 - exp(-tau)',
            wake=dict(ph.WAKE, note='each source is drawn as a head puff (head_share of its smoke, at the track position) plus stem puffs at these fractions of the way from the source to the head, radius = R (floor + (1 - floor) f). Inferred closure.'),
            t_s=T_SMOKE, tracks_no_wind=tracks,
            wind_note='wind enters through entrainment: the air a puff swallows carries the wind momentum. HK416Flash.smoke(t, wind) and physics.puff_track(src, t, wind) run the same sums.'),
        parity=parity,
        reference_check=dict(
            photometric_calibration=dict(
                factor=r(cal), raw_model_lux=r(raw), anchor_lux=P('anchor_lux_a2'),
                note='all thermal intensities are multiplied by this factor so the 16 in / A2 run reproduces the TTAG reading of 0.23 lx above ambient at 0.61 m on a 10 ms peak-hold meter'),
            secondary_peak_cd_bare=r(I_sec_pk),
            ref_16in_a2=dict(mach_disk_max_mm=r(float(np.max(ref_a2.x_disk(FINE))) * 1e3), slot_disk_max_mm=r(float(np.max(ref_a2.x_disk(FINE, ref_a2.f_slot))) * 1e3),
                             axial_share=r(ref_a2.f_ax), T00_K=r(ref_a2.T0), p_exit_MPa=r(ib16['p_base'] / 1e6)),
            hk416=dict(mach_disk_max_mm=r(float(np.max(shot.x_disk(FINE))) * 1e3), mach_disk_max_t_ms=r(FINE[np.argmax(shot.x_disk(FINE))] * 1e3),
                       slot_disk_max_mm=r(float(np.max(shot.x_disk(FINE, shot.f_slot))) * 1e3))),
    )
    # ---------------- checks against published measurements (written to checks.json)
    g = P('gamma'); Db = bare.Dm
    f_pk = ph.phases(shot, shot.t_xmax, cal)
    lit = dict(
        note='model against published rifle measurements. The published rifle is a 7.62 mm (M14 class), not this one, so agreement to about 10 % is the most these can show.',
        temperatures_K=[
            dict(what='primary flash, next to the muzzle', model_bare_muzzle_exit=r(bare.T0 * 2 / (g + 1)), model_in_the_hider_cage=r(shot.T0), published=1645,
                 source='Klingenberg & Mach 1976 (emission-absorption, 7.62 mm rifle)', status='prediction: the temperature is action/\'s reservoir temperature at exit, nothing fitted here'),
            dict(what='intermediate flash, behind the Mach disc', model_at_onset=r(float(shot.T0t(shot.t_xmax))), model_peak=r(f_pk['intermediate']['T']), published='1600 rising to 1940',
                 source='Klingenberg & Mach 1976 (Na and K line reversal, 100 to 300 mm from the muzzle)', status='onset is a prediction; the 300 K rise is taken from this same paper, so the peak is not independent'),
            dict(what='secondary flash', model=P('T_secondary'), published='about 2500', source='Klingenberg & Mach 1976', status='input, not a check'),
            dict(what='gas in the intermediate flash region late in the event', model_reservoir_at_0p70_ms=r(float(shot.T0t(0.70e-3))), model_reservoir_at_1p53_ms=r(float(shot.T0t(1.53e-3))),
                 published='1468 K at 0.70 ms falling to about 500 K at 1.53 ms', source='CARS temperature measurements in the muzzle flash region of a 7.62 mm rifle (DTIC ADA190786)',
                 status='mismatch late: the model keeps the shocked gas at the reservoir temperature and has no mixing with cold air, so it stays far too hot after about 1 ms (it has stopped glowing by then: glow_floor). The time origin of the published figures was not confirmed.')],
        mach_disc=dict(
            bare_muzzle_steady_mm_lewis_carlson=r(float(bare.x_full(0)) * 1e3), bare_muzzle_steady_calibres=r(float(bare.x_full(0)) / Db),
            bare_muzzle_steady_mm_ashkenas_sherman=r(0.67 * Db * math.sqrt(bare.p00 / ph.P_ATM) * 1e3),
            note='two published correlations for the Mach disc of a steady under-expanded jet, fed with action/\'s exit pressure: x/D = 0.69 M sqrt(gamma p_e/p_inf) (Lewis & Carlson 1964) and x/D = 0.67 sqrt(p_0/p_inf) (Ashkenas & Sherman 1966). They differ by %.0f %%, which is the uncertainty of the jet model before any hider. The muzzle jet never reaches the steady value: the pressure has fallen by the time the disc is established.' % (100 * (0.67 * math.sqrt(bare.p00 / ph.P_ATM) / (float(bare.x_full(0)) / Db) - 1)),
            hk416_with_hider_max_mm=r(shot.x_max * 1e3), hk416_with_hider_max_t_ms=r(shot.t_xmax * 1e3), hk416_bare_max_mm=r(bare.x_max * 1e3),
            ref_16in_5slot_max_mm=r(ref_a2.x_max * 1e3), photo_ttag_a2_upstream_face_mm='123 +- 12', photo_status='fitted (slot_cd), not a prediction'),
        light_meter=dict(
            a2_birdcage_lux=[r(P('anchor_lux_a2') + 0.25), 0.48], bare_muzzle_lux=[r(P('anchor_lux_bare')), 10760], order='[model, TTAG]',
            uncalibrated_model_over_measured=r(1 / cal), status='calibration, not a check: one factor (%.3g) on all thermal light makes the 16 in / 5-slot run read 0.48 lx; the secondary peak is set by the bare-muzzle reading. Before calibration the thermal model is %.0f times too bright.' % (cal, 1 / cal)))
    checks = dict(generator='assets/hk416/flash/sim.py', drive_against_action_json=drive_check, velocity_against_manual=vcheck, literature=lit,
                  see_also=['compare/measurements.json (photos)', 'parity.json (JS against Python)'])
    with open(os.path.join(HERE, 'checks.json'), 'w') as f_:
        json.dump(checks, f_, indent=1); f_.write('\n')
    ctx = dict(shot=shot, bare=bare, ref_a2=ref_a2, ref_bare=ref_bare, cal=cal, I_sec_pk=I_sec_pk, src=src, out=out)
    return out, ctx

def P_ATM_CRIT(shot): return ph.P_ATM * ((shot.g + 1) / 2) ** (shot.g / (shot.g - 1))
def total_part(shot, t, cal, key):
    f = ph.phases(shot, t, cal)
    return f[key]['I'] * (shot.n_slots if key == 'slot_jet' else 1)

if __name__ == '__main__':
    out, ctx = build()
    with open(os.path.join(HERE, 'flash.json'), 'w') as f:
        json.dump(out, f, indent=1)
    e = out['drive']['bullet_exit']; rc = out['reference_check']
    print('exit: %.0f m/s, reservoir %.1f MPa, %.0f K; half pressure at %.2f ms, unchoked at %.2f ms' % (
        e['velocity_m_s'], e['reservoir_pressure_MPa'], e['reservoir_temperature_K'], out['blowdown']['half_pressure_ms'], out['blowdown']['unchoke_ms']))
    print('drive check', out['drive']['check_against_action_json'])
    print('velocity check', out['drive']['velocity_check']['rows'])
    print('photometric cal x%.3g; secondary peak (bare) %.0f cd' % (rc['photometric_calibration']['factor'], rc['secondary_peak_cd_bare']))
    print('light: peak %.3g cd at %.2f ms, FWHM %.2f ms, integral %.3g cd s, frame60 %.3g cd' % (
        out['light']['peak_cd'], out['light']['peak_t_ms'], out['light']['fwhm_ms'], out['light']['integral_cd_s'], out['light']['frame60']['intensity_cd']))
    print('mach disc max: hk416 %s, 16in A2 ref %s' % (rc['hk416'], rc['ref_16in_a2']))
    print('secondary P:', {k: round(v['probability'], 3) for k, v in out['phases']['secondary']['ignition'].items()})
    print('strength', out['phases']['relative_strength'])
    if '--no-render' not in sys.argv:
        import render, plots
        plots.make(out, ctx, os.path.join(HERE, 'plots'))
        render.all(ctx, os.path.join(HERE, 'renders'))
