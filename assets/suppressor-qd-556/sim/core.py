"""Lumped gas dynamics of one shot through the suppressor (or out of the bare muzzle).

This file is the reference implementation of the model that ../sim/suppressor-qd-556.js ports line for line
(test.js checks the two against each other). Pure Python scalars, no numpy, fixed-step RK4, so the arithmetic
is the same in both languages.

Nodes: 0 = the bore (a stagnation reservoir in the state the HK416 interior ballistics leaves it at bullet exit),
1..N = the can's chambers, then the atmosphere. Each node carries propellant gas, air, the air's unburnt oxygen
and internal energy. Time zero is the bullet base leaving the barrel crown.

  * Interfaces: quasi-steady compressible orifice flow (choked or not, either direction). Interface 0 is the muzzle,
    interfaces 1..N the baffle apertures and the end cap. The bullet blocks each aperture while it is in it.
  * Carry-over: a share alpha_j of whatever arrives at aperture j from the aperture behind it goes straight on down
    the bore line without stagnating in chamber j (the kinetic-energy carry-over of labyrinth-seal theory).
  * Walls: convective heat loss with a Stanton-number law on the through-flow, plus a small still-gas term.
  * Oxygen: the air a cold can starts with burns the fuel-rich propellant gas once the mix is hot enough
    (the first-round pop).
  * Breech: an optional leak from the bore to the atmosphere through the opening chamber (gas to the face).
  * Sound source: a compact source at the exit. The exhaust's volume flow at ambient pressure, Q(t), radiates as a
    monopole and its thrust F(t) as an axial dipole:
        p(r, theta, t) = [rho0 dQ/dt + cos(theta) / c0 dF/dt] / (4 pi r)
    Both derivatives are taken through a first-order lag tau_ac (the aperture's acoustic transit time), which is what
    limits the rise of the uncorking pop.

Also here, and ported the same way: acoustics() (pulse parameters per listener), sound_overlay() (the patch for the
HK416 sound tables), flash_input(), shot_heat() and heat_string().
"""
import math

PATM = 101325.0
T_AMB = 293.15
RA, GA = 287.05, 1.40                   # air
CVA = RA / (GA - 1.0)
Y_O2 = 0.232                            # mass fraction of oxygen in air
RHO0 = PATM / (RA * T_AMB)              # ambient air density, 1.204 kg/m3
FOUR_PI = 4.0 * math.pi
C0 = 343.2                              # speed of sound, as assets/hk416/sound (20 C)
P_REF = 20e-6
SIGMA = 5.670374e-8


def psi(pr, g):
    """Orifice flow function: mdot = Cd A p_up psi / sqrt(R T_up). Linear near pr = 1 to keep the explicit solver calm."""
    pc = (2.0 / (g + 1.0)) ** (g / (g - 1.0))
    if pr <= pc: return math.sqrt(g) * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))
    if pr > 0.97:
        return math.sqrt(2.0 * g / (g - 1.0) * (0.97 ** (2.0 / g) - 0.97 ** ((g + 1.0) / g))) * (1.0 - pr) / 0.03
    return math.sqrt(2.0 * g / (g - 1.0) * (pr ** (2.0 / g) - pr ** ((g + 1.0) / g)))


def interp(ts, vs, t):
    """Piecewise-linear table, clamped at both ends."""
    n = len(ts)
    if n == 0: return 0.0
    if t <= ts[0]: return vs[0]
    if t >= ts[n - 1]: return vs[n - 1]
    lo = 0; hi = n - 1
    while hi - lo > 1:
        mid = (lo + hi) >> 1
        if ts[mid] <= t: lo = mid
        else: hi = mid
    return vs[lo] + (vs[hi] - vs[lo]) * (t - ts[lo]) / (ts[hi] - ts[lo])


def run_shot(cfg, opt):
    """cfg: the baked configuration (see sim.py build_config). opt: t_wall (K), o2 (0..1: share of the can's fill that
    is fresh air, the rest being spent propellant gas), breech (dict t, area or None), bare (True = no can),
    t_end, dt1, t1, dt2, rec_every1, rec_every2. Returns scalars and recorded series."""
    gas = cfg['gas']; RG = gas['R']; GG = gas['gamma']; ETA = gas['covolume']; CVG = RG / (GG - 1.0)
    bore = cfg['bore']; bul = cfg['bullet']; mod = cfg['model']
    bare = bool(opt.get('bare', False))
    N = 0 if bare else len(cfg['chambers']['volume_m3'])
    n = N + 1
    V = [bore['V']] + ([] if bare else list(cfg['chambers']['volume_m3']))
    AW = [0.0] + ([] if bare else list(cfg['chambers']['wall_area_m2']))
    AP = [bore['area']] + ([] if bare else list(cfg['chambers']['aperture_area_m2']))
    XA = [0.0] + ([] if bare else list(cfg['chambers']['aperture_from_crown_m']))
    WEB = [0.0] + ([] if bare else list(cfg['chambers']['web_t_m']))
    ALPHA = [0.0] + ([] if bare else list(cfg['chambers']['carry_over']))
    CD = [mod['cd_muzzle']] + [mod['cd_aperture']] * N
    t_wall = opt.get('t_wall', T_AMB); o2 = opt.get('o2', 1.0)
    br = opt.get('breech', None)
    ST = mod['stanton']; HFREE = mod['h_free']; AREF = mod['a_ref']; TIGN = mod['t_ign']; TAUC = mod['tau_burn']; QO2 = mod['q_o2']
    TAUAC = mod['tau_ac']; RAMP = bul['ramp_m']; VB = bul['v']; LB = bul['length']; ABUL = math.pi * bul['radius'] ** 2
    CDB = mod['cd_breech']

    # ---- state vector
    iMG = 0; iMA = n; iMO = 2 * n; iE = 3 * n; iQF = 4 * n; iFF = 4 * n + 1; iQW = 4 * n + 2
    iIMP = 5 * n + 2; iMOUT = iIMP + 1; iHOUT = iIMP + 2; iMBR = iIMP + 3; iO2B = iIMP + 4; iEK = iIMP + 5
    NY = iIMP + 6
    y = [0.0] * NY
    y[iMG] = bore['m']; y[iE] = bore['m'] * CVG * bore['T']
    for k in range(1, n):                                      # the can starts at 1 atm and wall temperature
        ma = o2 * PATM * V[k] / (RA * t_wall); mg = (1.0 - o2) * PATM * V[k] / (RG * t_wall)
        y[iMA + k] = ma; y[iMO + k] = Y_O2 * ma; y[iMG + k] = mg; y[iE + k] = (ma * CVA + mg * CVG) * t_wall

    aux = [0.0] * 12                                           # filled by rhs: exit and bore quantities at this instant
    stp = [0.0] * n; stT = [0.0] * n; stR = [0.0] * n; stcv = [0.0] * n; sth = [0.0] * n
    flow = [0.0] * n; gate = [0.0] * (n + 1); fin = [0.0] * (n + 1); fout = [0.0] * (n + 1)

    def rhs(t, y, d):
        for i in range(NY): d[i] = 0.0
        for k in range(n):
            mg = y[iMG + k]; ma = y[iMA + k]; m = mg + ma
            cv = (mg * CVG + ma * CVA) / m; R = (mg * RG + ma * RA) / m
            T = y[iE + k] / (m * cv); p = m * R * T / (V[k] - ETA * mg)
            stp[k] = p; stT[k] = T; stR[k] = R; stcv[k] = cv; sth[k] = cv * T + p * V[k] / m
        xb = VB * t
        # how far each aperture is open: 1 = clear, the annulus round the bullet while it is in it
        for j in range(1, n):
            xo = XA[j] + WEB[j]
            if xb + LB < XA[j]: a = 1.0; s_ = 0.0                      # bullet not there yet: open, but no stream ahead of the bullet
            elif xb < xo: a = 1.0 - ABUL / AP[j]; s_ = 0.0             # bullet in the aperture
            else:
                u = (xb - xo) / RAMP
                if u > 1.0: u = 1.0
                a = 1.0 - (1.0 - u) * ABUL / AP[j]; s_ = u
            flow[j] = a; gate[j] = ALPHA[j] * s_
        gate[n] = 0.0
        for k in range(n + 1): fin[k] = 0.0; fout[k] = 0.0
        q_exit = 0.0; m_exit = 0.0; h_exit = 0.0; thrust = 0.0; ek = 0.0
        for j in range(n):                                         # interface j joins node j and node j + 1 (or the atmosphere)
            pu = stp[j]
            if j + 1 < n: pd = stp[j + 1]
            else: pd = PATM
            A = CD[j] * AP[j] * (flow[j] if j > 0 else 1.0)
            if pu >= pd:
                g = 1.0 + stR[j] / stcv[j]
                f = A * pu * psi(pd / pu, g) / math.sqrt(stR[j] * stT[j])
                m = y[iMG + j] + y[iMA + j]
                yg = y[iMG + j] / m; ya = y[iMA + j] / m; yo = y[iMO + j] / m; h = sth[j]
                d[iMG + j] -= f * yg; d[iMA + j] -= f * ya; d[iMO + j] -= f * yo; d[iE + j] -= f * h; fout[j] += f
                # carry-over: of what leaves node j, share (1 - gate) stops in the next chamber, the rest goes on
                rem = f
                for k in range(j + 1, n):
                    part = rem * (1.0 - gate[k]); rem -= part; fin[k] += part
                    d[iMG + k] += part * yg; d[iMA + k] += part * ya; d[iMO + k] += part * yo; d[iE + k] += part * h
                if rem > 0.0:                                      # this much leaves the can
                    cp = stcv[j] + stR[j]; T0 = stT[j]; pr = PATM / pu
                    if pr > 1.0: pr = 1.0
                    Te = T0 * pr ** ((g - 1.0) / g)
                    ue = math.sqrt(2.0 * cp * (T0 - Te))
                    q_exit += rem * stR[j] * Te / PATM; m_exit += rem; h_exit += rem * h; ek += 0.5 * rem * ue * ue
                    pc = (2.0 / (g + 1.0)) ** (g / (g - 1.0))
                    if j == n - 1 and pr <= pc:                      # choked at the last orifice: momentum plus pressure thrust
                        thrust += rem * math.sqrt(g * stR[j] * T0 * 2.0 / (g + 1.0)) + (pu * pc - PATM) * A
                    else: thrust += rem * ue
            else:                                                  # reverse flow
                if j + 1 < n:
                    k = j + 1; g = 1.0 + stR[k] / stcv[k]
                    f = A * pd * psi(pu / pd, g) / math.sqrt(stR[k] * stT[k])
                    m = y[iMG + k] + y[iMA + k]
                    yg = y[iMG + k] / m; ya = y[iMA + k] / m; yo = y[iMO + k] / m; h = sth[k]
                    d[iMG + k] -= f * yg; d[iMA + k] -= f * ya; d[iMO + k] -= f * yo; d[iE + k] -= f * h; fout[k] += f
                else:                                              # air comes back in at the exit
                    f = A * pd * psi(pu / pd, GA) / math.sqrt(RA * T_AMB)
                    yg = 0.0; ya = 1.0; yo = Y_O2; h = (CVA + RA) * T_AMB
                    q_exit -= f * RA * T_AMB / PATM; m_exit -= f
                d[iMG + j] += f * yg; d[iMA + j] += f * ya; d[iMO + j] += f * yo; d[iE + j] += f * h; fin[j] += f
        # ---- breech leak (bore to atmosphere through the opening chamber)
        mbr = 0.0
        if br is not None:
            ab = interp(br['t'], br['area'], t)
            if ab > 0.0 and stp[0] > PATM:
                g = 1.0 + stR[0] / stcv[0]
                mbr = CDB * ab * stp[0] * psi(PATM / stp[0], g) / math.sqrt(stR[0] * stT[0])
                m = y[iMG] + y[iMA]
                d[iMG] -= mbr * y[iMG] / m; d[iMA] -= mbr * y[iMA] / m; d[iMO] -= mbr * y[iMO] / m; d[iE] -= mbr * sth[0]
        # ---- walls and oxygen
        burn = 0.0
        for k in range(1, n):
            G = (fin[k] if fin[k] > fout[k] else fout[k]) / AREF            # mass flux scale of the through-flow
            T = stT[k]
            q = (ST * (stcv[k] + stR[k]) * G + HFREE) * AW[k] * (T - t_wall)
            d[iQW + k - 1] = q; d[iE + k] -= q
            mo = y[iMO + k]
            if mo > 1e-12 and T > TIGN and y[iMG + k] > 2.0 * mo:
                r = mo / TAUC; d[iMO + k] -= r; d[iE + k] += r * QO2; burn += r
        d[iQF] = (q_exit - y[iQF]) / TAUAC; d[iFF] = (thrust - y[iFF]) / TAUAC
        d[iIMP] = thrust; d[iMOUT] = m_exit; d[iHOUT] = h_exit; d[iMBR] = mbr; d[iO2B] = burn; d[iEK] = ek
        aux[0] = q_exit; aux[1] = m_exit; aux[2] = thrust; aux[3] = h_exit; aux[4] = ek
        aux[5] = RHO0 * (q_exit - y[iQF]) / (TAUAC * FOUR_PI)       # monopole pressure at 1 m, Pa
        aux[6] = mbr; aux[7] = burn
        aux[8] = (thrust - y[iFF]) / (C0 * TAUAC * FOUR_PI)         # dipole pressure at 1 m on the axis ahead, Pa

    k1 = [0.0] * NY; k2 = [0.0] * NY; k3 = [0.0] * NY; k4 = [0.0] * NY; yt = [0.0] * NY
    COS = cfg['listen']['dip']; na = len(COS)                  # dipole weight per listener: dipole_share * cos(theta)
    rec = dict(t=[], p_bore=[], T_bore=[], p=[], T=[], q_exit=[], m_exit=[], thrust=[], mono=[], dip=[], qf=[], ff=[], m_breech=[], ek=[], h_exit=[])
    pkP = [0.0] * na; pkT = [0.0] * na; pkN = [0.0] * na
    pk_q = 0.0; pk_m = 0.0; pk_h = 0.0; pk_ek = 0.0; pk_th = 0.0; t_ek = 0.0
    pk_p = [0.0] * n; pk_T = [0.0] * n
    t = 0.0; step = 0
    phases = ((opt.get('t1', 4e-3), opt.get('dt1', 2e-7), opt.get('rec_every1', 5)),
              (opt.get('t_end', 40e-3), opt.get('dt2', 2e-6), opt.get('rec_every2', 25)))
    for (t_end, dt, every) in phases:
        nsteps = int(round((t_end - t) / dt))
        for _ in range(nsteps):
            rhs(t, y, k1)
            for a in range(na):
                v = aux[5] + COS[a] * aux[8]
                if v > pkP[a]: pkP[a] = v; pkT[a] = t
                if v < pkN[a]: pkN[a] = v
            if aux[0] > pk_q: pk_q = aux[0]
            if aux[1] > pk_m: pk_m = aux[1]
            if aux[3] > pk_h: pk_h = aux[3]
            if aux[4] > pk_ek: pk_ek = aux[4]; t_ek = t
            if aux[2] > pk_th: pk_th = aux[2]
            for k in range(n):
                if stp[k] > pk_p[k]: pk_p[k] = stp[k]
                if stT[k] > pk_T[k]: pk_T[k] = stT[k]
            if step % every == 0:
                rec['t'].append(t); rec['p_bore'].append(stp[0]); rec['T_bore'].append(stT[0])
                rec['p'].append(stp[1:]); rec['T'].append(stT[1:])
                rec['q_exit'].append(aux[0]); rec['m_exit'].append(aux[1]); rec['thrust'].append(aux[2]); rec['h_exit'].append(aux[3])
                rec['mono'].append(aux[5]); rec['dip'].append(aux[8]); rec['qf'].append(y[iQF]); rec['ff'].append(y[iFF])
                rec['m_breech'].append(aux[6]); rec['ek'].append(aux[4])
            for i in range(NY): yt[i] = y[i] + 0.5 * dt * k1[i]
            rhs(t + 0.5 * dt, yt, k2)
            for i in range(NY): yt[i] = y[i] + 0.5 * dt * k2[i]
            rhs(t + 0.5 * dt, yt, k3)
            for i in range(NY): yt[i] = y[i] + dt * k3[i]
            rhs(t + dt, yt, k4)
            for i in range(NY): y[i] = y[i] + dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])
            for k in range(n):
                if y[iMO + k] < 0.0: y[iMO + k] = 0.0
            step += 1; t = step_time(phases, step)
    rhs(t, y, k1)
    heat = [y[iQW + k] for k in range(N)]
    ht = 0.0
    for k in range(N): ht += heat[k]
    return dict(
        n_chambers=N, t_end=t, t_wall=t_wall, o2=o2,
        peak_p1m_Pa=pkP, t_peak_p1m=pkT, neg_p1m_Pa=pkN,
        peak_q_m3s=pk_q, peak_mdot_exit=pk_m, peak_hdot_exit=pk_h, peak_ekdot_exit=pk_ek, t_peak_ekdot=t_ek, peak_thrust_N=pk_th,
        peak_p_Pa=pk_p, peak_T_K=pk_T,
        impulse_Ns=y[iIMP], mass_out_kg=y[iMOUT], enthalpy_out_J=y[iHOUT], kinetic_out_J=y[iEK], mass_breech_kg=y[iMBR], o2_burnt_kg=y[iO2B],
        heat_wall_J=heat, heat_total_J=ht,
        end_p_Pa=list(stp), end_T_K=list(stT), end_gas_kg=[y[iMG + k] for k in range(n)], end_air_kg=[y[iMA + k] for k in range(n)],
        rec=rec)


def step_time(phases, step):
    """Time after `step` steps, computed from the phase table (no accumulated rounding)."""
    t0 = 0.0; s0 = 0
    for (t_end, dt, _e) in phases:
        ns = int(round((t_end - t0) / dt))
        if step <= s0 + ns: return t0 + (step - s0) * dt
        s0 += ns; t0 = t_end
    return t0


# ====================================================================== products (all ported to JS the same way)
def db(p):
    return 20.0 * math.log10((p if p > 1e-12 else 1e-12) / P_REF)


def acoustics(cfg, shot):
    """Pulse parameters at 1 m for each listener direction, from one shot's record.
    pop: the uncorking pulse (peak P, Friedlander time T so that the positive impulse matches).
    hump: the slower swell that follows while the can's exit flow is still rising.
    jet: peak kinetic power of the exhaust and the time its amplitude envelope takes to fall by e."""
    COS = cfg['listen']['dip']; tau = cfg['model']['tau_ac']; rec = shot['rec']; nt = len(rec['t'])
    out = []
    for a in range(len(COS)):
        c = COS[a]; P = shot['peak_p1m_Pa'][a]; tp = shot['t_peak_p1m'][a]
        t1 = tp + 3.0 * tau
        i_pop = (RHO0 * interp(rec['t'], rec['qf'], t1) + c * interp(rec['t'], rec['ff'], t1) / C0) / FOUR_PI
        t2 = tp + 5.0 * tau; ph = 0.0; th = t2; i_max = i_pop
        for i in range(nt):
            ti = rec['t'][i]
            imp = (RHO0 * rec['qf'][i] + c * rec['ff'][i] / C0) / FOUR_PI
            if imp > i_max: i_max = imp
            if ti > t2:
                v = rec['mono'][i] + c * rec['dip'][i]
                if v > ph: ph = v; th = ti
        T_pop = math.e * i_pop / P if P > 0.0 else 0.0
        if T_pop < 2e-5: T_pop = 2e-5
        T_hump = math.e * (i_max - i_pop) / ph if ph > 0.0 else 0.0
        if T_hump < 1e-4: T_hump = 1e-4
        if T_hump > 3e-3: T_hump = 3e-3
        out.append(dict(name=cfg['listen']['names'][a], cos=cfg['listen']['cos'][a], pop_P1m=P, pop_dB1m=db(P), pop_T=T_pop, t_pop=tp,
                        hump_P1m=ph, hump_T=T_hump, hump_dt=th - tp, impulse_pos_Pa_s=i_max))
    pk = shot['peak_ekdot_exit']; t_e = shot['t_peak_ekdot']; lim = pk / (math.e * math.e); tj = rec['t'][nt - 1]
    for i in range(nt):
        if rec['t'][i] > t_e and rec['ek'][i] < lim: tj = rec['t'][i]; break
    return dict(listeners=out, jet_power_W=pk, jet_tau_s=tj - t_e, t_uncork_s=out[0]['t_pop'])


def sound_overlay(cfg, params, ac, bare_jet, mech=None):
    """Patch a copy of the HK416 sound tables (assets/hk416/sound/params.json) for the suppressed rifle.
    ac: acoustics() of the shot state wanted; bare_jet: acoustics() of the bare muzzle (jet reference);
    mech: optional {event name: time ratio} and 'period_ratio' from the suppressed action.
    The supersonic crack (`nwave`) is not touched. Returns the patched tables (a deep copy)."""
    P = _copy(params)
    L = cfg['listen']; dz = cfg['exit_offset_m']
    k_rms = math.sqrt(ac['jet_power_W'] / bare_jet['jet_power_W']); k_tau = ac['jet_tau_s'] / bare_jet['jet_tau_s']
    for a in range(len(L['names'])):
        nm = L['names'][a]
        if nm not in P['persp']: continue
        pp = P['persp'][nm]; A = ac['listeners'][a]
        for key in ('free', 'field'):
            bl = pp['blast'][key]
            if len(bl) == 0: continue
            r0 = bl[0]['r']; r1 = r0 - dz * A['cos']; dt = (r1 - r0) / C0
            ratio = (A['pop_P1m'] / r1) / bl[0]['P']
            hratio = (A['hump_P1m'] / r1) / bl[0]['P']
            sec = []
            for e in bl:
                h = dict(e); h['P'] = e['P'] * hratio; h['T'] = A['hump_T']; h['t'] = e['t'] + dt + A['hump_dt']
                if 'r' in h: del h['r']
                sec.append(h)
                e['P'] = e['P'] * ratio; e['T'] = A['pop_T']; e['t'] = e['t'] + dt
                if 'bm' in e: e['bm'] = e['bm'] * ratio            # HK416 sound v2: the gas-volume body follows the pop
                if 'r' in e: e['r'] = e['r'] + (r1 - r0)
            pp['sec'][key] = sec                                   # the bare rifle's afterburn pulse is gone; the hump takes its slot
            for e in pp['jet'][key]:
                if 'g' in e: e['g'] = e['g'] * k_rms * (r0 / r1)       # HK416 sound v2: a gain on the shared jet envelope
                else: e['rms'] = e['rms'] * k_rms * (r0 / r1); e['tau'] = e['tau'] * k_tau
                e['t'] = e['t'] + dt
    if mech is not None:
        for ev in P['cycle']:
            if ev[0] in mech and ev[1] > 0.0: ev[1] = ev[1] * mech[ev[0]]
        if 'cycle' in P['mech_clips']:
            for ev in P['mech_clips']['cycle']:
                if ev[0] in mech and ev[1] > 0.0: ev[1] = ev[1] * mech[ev[0]]
        pr = mech.get('period_ratio', 1.0)
        P['cycle_s'] = P['cycle_s'] * pr
        for v in P['variants']:
            tt = P['variants'][v]['times']
            if v.startswith('auto'):
                for i in range(len(tt)): tt[i] = tt[i] * pr
    P['suppressor'] = dict(asset='suppressor-qd-556', exit_offset_m=dz)
    return P


def _copy(x):
    if isinstance(x, dict):
        o = {}
        for k in x: o[k] = _copy(x[k])
        return o
    if isinstance(x, list): return [_copy(v) for v in x]
    return x


def flash_input(cfg, shot, bare):
    """What a muzzle-flash model needs to know about the can (the interface for assets/hk416/flash/).
    Scales multiply the bare rifle's luminous output phase by phase."""
    mod = cfg['model']
    T0s = shot['peak_hdot_exit'] / shot['peak_mdot_exit'] / cfg['gas']['cp']       # stagnation temperature of the exhaust at peak flow
    T0b = bare['peak_hdot_exit'] / bare['peak_mdot_exit'] / cfg['gas']['cp']
    glow = (shot['peak_mdot_exit'] / bare['peak_mdot_exit']) * (T0s / T0b) ** 4      # optically thin emitter: amount times T^4
    cpa = CVA + RA; cpg = cfg['gas']['cp']; r = mod['flash_mix_ratio']
    Tmix_s = (cpg * T0s + r * cpa * T_AMB) / (cpg + r * cpa)
    Tmix_b = (cpg * T0b + r * cpa * T_AMB) / (cpg + r * cpa)
    ps = 1.0 / (1.0 + math.exp(-(Tmix_s - mod['flash_t_ign']) / mod['flash_t_width']))   # chance the exhaust-air mix lights
    pb = 1.0 / (1.0 + math.exp(-(Tmix_b - mod['flash_t_ign']) / mod['flash_t_width']))
    through = 1.0
    for al in cfg['chambers']['carry_over']: through = through * al
    return dict(exit_offset_m=cfg['exit_offset_m'], delay_s=cfg['t_uncork_cap_s'],
                exhaust_T0_K=T0s, bare_T0_K=T0b, exhaust_peak_kg_s=shot['peak_mdot_exit'], bare_peak_kg_s=bare['peak_mdot_exit'],
                scale=dict(precursor=0.0, primary=glow, intermediate=glow, slot_jet=0.0, sparks=through, secondary=ps / pb),
                secondary=dict(mix_T_K=Tmix_s, bare_mix_T_K=Tmix_b, ignition_T_K=mod['flash_t_ign'], chance=ps, bare_chance=pb),
                o2_burnt_in_can_kg=shot['o2_burnt_kg'], duration_scale=1.0)


def shot_heat(cfg, t_wall, o2):
    """Heat one shot leaves in the can (J) at wall temperature t_wall (K), with share o2 of the fill being fresh air."""
    H = cfg['heat']
    return interp(H['t_wall_K'], H['shot_J'], t_wall) + o2 * H['first_round_extra_J']


def cool(cfg, T, dt):
    """Can temperature after dt seconds of still-air cooling (free convection and radiation), explicit steps of at most 0.05 s."""
    H = cfg['heat']; n = int(math.ceil(dt / 0.05))
    if n < 1: n = 1
    h = dt / n
    for _ in range(n):
        q = H['h_conv'] * H['area_m2'] * (T - T_AMB) + H['emissivity'] * SIGMA * H['area_m2'] * (T ** 4 - T_AMB ** 4)
        T = T - h * q / H['C_J_per_K']
    return T


def heat_string(cfg, shot_times, T0=T_AMB, idle_before=1e9):
    """Bulk can temperature through a string of shots. Returns per shot: wall temperature before it, oxygen share of
    the fill, the heat it leaves, the temperature after it."""
    H = cfg['heat']; T = T0; out = []; last = None
    for ts in shot_times:
        gap = idle_before if last is None else ts - last
        if last is not None: T = cool(cfg, T, gap)
        o2 = 1.0 - math.exp(-gap / H['tau_o2_s'])
        q = shot_heat(cfg, T, o2)
        T1 = T + q / H['C_J_per_K']
        out.append(dict(t=ts, T_before_K=T, o2=o2, heat_J=q, T_after_K=T1))
        T = T1; last = ts
    return out
