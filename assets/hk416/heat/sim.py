#!/usr/bin/env python3
"""HK416 D14.5RS thermal simulation under fire.

Axisymmetric (r, z) explicit finite-volume model of the barrel on the lathe profile in
../model/build.py (read from that file at run time), with lumped gas block, piston,
flash-hider crown, barrel nut and upper receiver, and a 1D aluminium handguard.  The heat
each shot leaves in the bore is computed from the interior ballistics in ../action/action.json.

  python3 sim.py              # everything: validation, schedules, heat.json, plots, JS parameters
  python3 sim.py --validate   # only the validation cases (M4A1 geometry against published data)
  python3 sim.py --quick      # short cool-downs, for a fast check

Every number is explained in README.md.  Units are SI unless a name says otherwise
(z_mm, *_C).  Temperatures are kelvin inside the solver and deg C in the outputs.
Standard library + numpy; matplotlib only for the plots (plots.py).
"""
import argparse, json, math, os, re, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ACTION = json.load(open(os.path.join(HERE, '..', 'action', 'action.json')))
AP = {k: v['value'] for k, v in ACTION['params'].items()}

def build_params():
    """The shape numbers of ../model/build.py (its ruler and its P table), read from the source so this model follows the recipe."""
    src = open(os.path.join(HERE, '..', 'model', 'build.py')).read()
    m = re.search(r'^PX_PER_MM = .*?^P = dict\(.*?^\)\n', src, flags=re.S | re.M)
    ns = {}; exec(m.group(0), ns)
    B = dict(ns['P']); B['LX'] = ns['LX']; B['ZY'] = ns['ZY']
    return B
BP = build_params()
SIGMA = 5.670374e-8
G0 = 9.80665
K0 = 273.15

# =============================================================================== parameters
# Each entry: value, unit, source.  "inferred" = my estimate, with the reasoning in README.md.
PARAMS = dict(
    # ---- cartridge and energy (all from ../action/action.json, the interior ballistics of this asset)
    charge_mass_g=(AP['m_charge'] * 1e3, 'g', 'action.json m_charge: M855, 26.1 gr WC844 (US Army TM 43-0001-27)'),
    propellant_energy_J_per_g=(AP['force_const'] / (AP['gamma'] - 1) * 1e-3, 'J/g', 'action.json: F / (gamma - 1), the energy the gas can give up (force 1.0 MJ/kg, gamma 1.24)'),
    bullet_mass_g=(AP['m_bullet'] * 1e3, 'g', 'action.json m_bullet: M855, 62 gr'),
    muzzle_velocity_m_s=(AP['v_muzzle_target'], 'm/s', 'HK manual p. 7, 14.5 in barrel (action.json)'),
    bore_heat_scale=(1.0, '-', 'multiplier on the Dittus-Boelter bore heat-transfer coefficient. 1.0 = the correlation as published, NOT fitted; the fire-to-destruction counts check it'),
    f_chamber=(1.85, '-', 'CALIBRATED on the NSWC Crane M4A1 chamber temperatures (first firing sequence): heat per unit length into the chamber wall relative to the first bore station; see README'),
    g_chamber_case=(1.0, 'W/K', 'inferred: contact conductance between the chamber wall and the chambered round, 1000 W/m2/K over the 1100 mm2 case wall of action.json. The Crane data support it weakly: see validation.fit_scan'),
    c_case_J_K=(AP['m_case'] * 380.0, 'J/K', 'heat capacity of the brass case: action.json m_case 6.2 g x 380 J/kg/K (C26000 handbook)'),
    case_wall_m=(0.0006, 'm', 'inferred: mean 5.56 mm case wall over the body and shoulder (0.3 mm at the neck to about 1 mm near the head)'),
    chamber_h_ratio=(0.57, '-', 'inferred: gas-side heat-transfer coefficient inside the case relative to the first bore station (half the gas speed, to the power 0.8)'),
    k_brass=(120.0, 'W/m/K', 'cartridge brass C26000, handbook'),
    rhoc_brass=(8530.0 * 380.0, 'J/m3/K', 'cartridge brass C26000, handbook'),
    friction_to_bore=(0.5, '-', 'inferred: share of the bullet friction and engraving work (action.json p_friction, p_engrave) that stays in the bore; the rest leaves in the jacket'),
    q_port_J=(15.0, 'J/shot', 'inferred: extra bore heating around the gas port (Purdue thesis: port heating "should not be neglected")'),
    piston_share=(0.22, '-', 'inferred: share of the gas-cylinder wall heat taken by the piston and rod, the rest by the gas block'),
    q_gas_block_di_J=(10.0, 'J/shot', 'inferred, validation rifles only: a direct-impingement gas block keeps little heat (the gas goes down the tube)'),
    q_flash_hider_J=(20.0, 'J/shot', 'inferred: muzzle gas washing the birdcage; large uncertainty'),
    case_len_m=(AP['case_len'], 'm', '5.56x45 case length 44.70 mm (action.json)'),
    # ---- steel (barrel, nut, gas block, piston, flash hider)
    rho_steel=(7850.0, 'kg/m3', 'Cr-Mo-V barrel steel (4140/4150 class), handbook'),
    eps_steel=(0.85, '-', 'manganese-phosphated / black-oxide steel, handbook 0.8 to 0.9'),
    alpha_steel=(12.3e-6, '1/K', '4140 mean expansion 20 to 300 C, handbook'),
    # ---- aluminium (handguard 6061-T6, upper receiver 7075-T6)
    rho_al=(2700.0, 'kg/m3', '6061-T6 handbook (7075: 2810)'),
    k_al_hg=(167.0, 'W/m/K', '6061-T6 handbook'),
    k_al_upper=(130.0, 'W/m/K', '7075-T6 handbook'),
    eps_al=(0.85, '-', 'black hard-anodised aluminium, handbook 0.8 to 0.9'),
    # ---- handguard geometry (from ../model/build.py: 60 mm octagonal tube, 3.0 mm wall, 228.5 mm long)
    hg_area_m2=(650e-6, 'm2', 'metal cross-section: 0.20 m perimeter x 3 mm wall + four rails, less vents -> 0.40 kg (inferred from the build.py section)'),
    hg_perim_out_m=(0.26, 'm', 'convecting perimeter: 0.20 m envelope x 1.3 for rail lugs (inferred)'),
    hg_perim_rad_m=(0.20, 'm', 'radiating envelope perimeter (build.py)'),
    hg_r_inner_m=(0.0234, 'm', 'inner half-width 26.4 - 3.0 mm (build.py)'),
    hg_view_to_ambient=(0.05, '-', 'fraction of barrel radiation leaving through vents and the open front (vent area / wall area, build.py)'),
    hg_vent_fraction=(0.25, '-', 'inferred: share of the gap convection carried straight out of the vents and front'),
    hg_top_bottom_split=(0.20, '-', 'inferred: top of the handguard runs this fraction of its excess hotter than the mean, the bottom half that cooler'),
    # ---- contacts and lumps
    g_barrel_nut=(4.0, 'W/K', 'inferred: barrel flange clamped by the nut at 110 N m, 200 mm2 at 20 kW/m2/K'),
    g_nut_handguard=(3.0, 'W/K', 'inferred: sliding fit of the rail on the barrel nut, 2000 mm2 at 1.5 kW/m2/K'),
    g_nut_upper=(2.0, 'W/K', 'inferred: nut threads on the 7075 receiver ring'),
    g_barrel_upper=(1.2, 'W/K', 'inferred: barrel extension, slip fit in the receiver bore'),
    m_nut=(0.061, 'kg', 'build.py barrel_nut: 29 mm OD, 19.8 mm ID, 22 mm long'),
    g_upper_front_rear=(0.65, 'W/K', 'inferred: 450 mm2 of receiver wall over 90 mm'),
    g_handguard_upper=(1.0, 'W/K', 'inferred: handguard rear face against the receiver'),
    g_barrel_gas_block=(5.0, 'W/K', 'inferred: pinned gas block journal, 1050 mm2 at 5 kW/m2/K'),
    g_gas_block_piston=(0.4, 'W/K', 'inferred: piston with three rings in the cylinder cup'),
    g_barrel_fh=(0.37, 'W/K', 'steel 160 mm2 over 15 mm between the threads and the birdcage (build.py)'),
    m_gas_block=(0.100, 'kg', 'build.py gas block prism 72 g + front sight base 30 g (volume x 7850)'),
    m_piston=(0.075, 'kg', 'inferred: piston, rod and guide'),
    m_fh_front=(0.031, 'kg', 'build.py birdcage ahead of the muzzle, slots removed'),
    m_upper_front=(0.100, 'kg', 'inferred: front 50 mm of the upper receiver'),
    m_upper_rear=(0.300, 'kg', 'inferred: rest of the upper receiver'),
    a_gas_block=(0.0035, 'm2', 'build.py gas block outer area'),
    a_piston=(0.0065, 'm2', 'build.py gas_piston_tube: 9.8 mm x 210 mm'),
    a_fh_front=(0.0040, 'm2', 'build.py birdcage, inside + outside'),
    a_upper_front=(0.012, 'm2', 'inferred'),
    a_upper_rear=(0.035, 'm2', 'inferred'),
    # ---- environment defaults
    ambient_C=(25.0, 'C', 'default'),
    wind_m_s=(0.0, 'm/s', 'default: still air'),
    cyclic_rpm=(round(ACTION['auto']['rpm'], 1), 'rounds/min', 'action.json auto.rpm, the simulated cyclic rate (HK manual p. 7: 700 to 900)'),
)
def P(name): return PARAMS[name][0]


# =============================================================================== materials
def k_steel(T):
    return np.maximum(27.0, 42.7 - 0.0165 * (T - K0))

def c_steel_C(tc):
    """EN 1993-1-2 specific heat of carbon steel, tc in deg C (array)."""
    tc = np.asarray(tc, float)
    c = 425 + 0.773 * tc - 1.69e-3 * tc ** 2 + 2.22e-6 * tc ** 3
    c = np.where(tc >= 600, 666 + 13002 / np.maximum(738 - tc, 1e-9), c)
    c = np.where(tc >= 735, 545 + 17820 / np.maximum(tc - 731, 1e-9), c)
    c = np.where(tc >= 900, 650.0, c)
    return c

# enthalpy table for steel: h(T) from 0 K reference at -50 C, 0.5 K steps
_TT = np.arange(-50.0, 1600.01, 0.5) + K0
_CC = c_steel_C(_TT - K0)
_HH = np.concatenate([[0.0], np.cumsum(0.5 * (_CC[1:] + _CC[:-1]) * 0.5)])
def steel_T(h): return np.interp(h, _HH, _TT)
def steel_h(T): return np.interp(T, _TT, _HH)

def c_al(T): return 896.0 + 0.45 * (T - K0 - 25.0)

def air(Tf):
    """k [W/m/K], nu [m2/s], Pr for air at film temperature Tf [K]; power-law fits to tables (300 to 900 K, within 3 %)."""
    return 0.0263 * (Tf / 300.0) ** 0.82, 1.589e-5 * (Tf / 300.0) ** 1.7, 0.70

def h_cylinder(D, Ts, Ta, U=0.0):
    """Mean h [W/m2/K] on a horizontal cylinder: Churchill-Chu (free) and Churchill-Bernstein (cross-flow), blended as cubes."""
    Ts = np.asarray(Ts, float)
    Tf = 0.5 * (Ts + Ta); k, nu, Pr = air(Tf)
    dT = np.abs(Ts - Ta) + 1e-3
    Ra = G0 * dT / Tf * D ** 3 / (nu * nu / Pr)
    Nun = (0.60 + 0.387 * Ra ** (1 / 6) / (1 + (0.559 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2
    if U > 0:
        Re = U * D / nu
        Nuf = 0.3 + 0.62 * Re ** 0.5 * Pr ** (1 / 3) / (1 + (0.4 / Pr) ** (2 / 3)) ** 0.25 * (1 + (Re / 282000.0) ** (5 / 8)) ** 0.8
        Nu = (Nun ** 3 + Nuf ** 3) ** (1 / 3)
    else:
        Nu = Nun
    return Nu * k / D

def gap_conductance(ri, ro, Ti, To):
    """Raithby-Hollands effective conductance per unit length [W/m/K] of the air annulus between barrel and handguard."""
    Tf = 0.5 * (Ti + To); k, nu, Pr = air(Tf)
    L = ro - ri; dT = np.abs(Ti - To) + 1e-3
    RaL = G0 * dT / Tf * L ** 3 / (nu * nu / Pr)
    Rac = np.log(ro / ri) ** 4 / (L ** 3 * (ri ** -0.6 + ro ** -0.6) ** 5) * RaL
    keff = k * np.maximum(1.0, 0.386 * (Pr / (0.861 + Pr)) ** 0.25 * Rac ** 0.25)
    return 2 * math.pi * keff / np.log(ro / ri)


# =============================================================================== geometry
def make_grid(breaks, target_mm):
    """Station edges [mm]: every break is an edge (so no cell straddles a step in the profile), cells close to target_mm long."""
    e = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        n = max(1, int(round((b - a) / target_mm)))
        e += [a + (b - a) * (i + 1) / n for i in range(n)]
    return np.array(e)

def geometry_hk416(dz_mm=2.5, nr=4, variant='default'):
    """Barrel profile of ../model/build.py build_barrel(); z in mm from the upper receiver's front face (the asset frame's +Z).
    Everything a photo shows follows build.py.  The chamber end, hidden inside the receiver, nut and handguard, does not: build.py
    draws a 20 mm cylinder there (a shape nobody sees), which would leave 5.3 mm of steel around a 358 MPa chamber.  The default
    here is the AR-pattern chamber reinforce, 24.9 mm to z = 57 mm (INFERRED; the same as the M4A1 drawing values below).
    variant 'as_drawn' uses build.py's 20 mm; 'heavy' also thickens the barrel under the handguard to the M4A1 SOCOM's 20.4 mm."""
    B = BP; LX = B['LX']
    z0 = B['barrel_breech']; z1 = z0 + B['barrel_len']                 # -5.0, 363.3
    gb0, gb1 = B['gas_block']; n0, n1 = B['neck']; hg1 = B['hg_l1']     # 228.5, 246.4; 269.8, 294.3; 228.5
    sh = LX(685.0); washer = LX(688.0); fh0 = B['fh_l0']                # thread shoulder 348.9, jam ring to 352.3, flash hider from 355.1
    nut1 = 22.0                                                         # barrel_nut spans z = 0 to 22 in build_barrel()
    case_z = z0 + AP['case_len'] * 1e3
    rein_end = 61.0 if variant == 'as_drawn' else 57.0; rein_r = 10.0 if variant == 'as_drawn' else 12.45
    ze = make_grid([z0, 0.0, 11.0, nut1, z0 + 36.5, case_z, rein_end, gb0, gb1, n0, n1, sh, fh0, z1], dz_mm); zc = 0.5 * (ze[1:] + ze[:-1]); nz = len(zc)
    def r_out(z):
        if z < 11.0: return 12.7        # INFERRED: barrel extension, 25.4 mm (AR-pattern; build.py draws 11.0 mm here, hidden in the receiver)
        if z < rein_end: return rein_r  # chamber reinforce (see the docstring)
        if variant == 'heavy' and z < gb0: return 10.2
        if z < gb1: return B['barrel_hg_r']   # 9.3: under the handguard (seen through the vents) and the gas block journal
        if z < n0: return B['barrel_r']       # 8.9: photo, 17.8 mm
        if z < n1: return B['barrel_neck_r']  # 7.25: the necked section, photo
        if z < sh: return B['barrel_r']
        if z < fh0: return 9.6          # jam ring (9.7) + crush washer (9.4 to 8.5) over the 6.35 mm threads, fused
        return B['fh_r']                # 10.6: flash hider body over the threads (fused)
    def r_in(z):
        s = z - z0
        if s < 36.5: return 4.7         # chamber body (5.56x45 case 9.6 mm head to 9.0 mm shoulder, CIP)
        if s < AP['case_len'] * 1e3: return 3.2   # case neck
        return 2.82                     # groove radius 2.845, bore 2.78
    g = dict(name='HK416 D14.5RS', nz=nz, nr=nr, z_edges_mm=ze, z_mm=zc, breech_mm=z0, muzzle_mm=z1,
             r_out_mm=np.array([r_out(z) for z in zc]), r_in_mm=np.array([r_in(z) for z in zc]),
             nut=(zc < nut1), upper=(zc < 11.0), hg=(zc >= nut1) & (zc < gb0), gb=(zc >= gb0) & (zc < gb1),
             exposed=(zc >= gb1), hg_cells=(zc >= B['hg_l0']) & (zc < hg1), piston_span=(zc >= 18.0) & (zc < gb0),
             hand_z_mm=110.0, gas_piston=True, marks=dict(gas_block=[gb0, gb1], neck=[n0, n1], thread_shoulder=sh, flash_hider=[fh0, B['fh_l1']], handguard=[B['hg_l0'], hg1]))
    return g

def geometry_m4a1(heavy=False, dz_mm=5.0, nr=4):
    """Validation geometry: Colt M4A1 14.5 in barrel, government or SOCOM-heavy profile (approximate drawing values).
    z is measured from the bolt face here (breech 0).  Used only to test the solver against published M4A1 data."""
    ze = make_grid([0.0, 10.0, 16.0, 30.0, 36.5, 44.7, 62.0, 72.0, 188.0, 222.0, 262.0, 300.0, 352.0, 368.3], dz_mm); zc = 0.5 * (ze[1:] + ze[:-1]); nz = len(zc)
    mid = 10.2 if heavy else 8.13       # 0.80 in SOCOM / 0.640 in government under the handguards
    def r_out(z):
        if z < 16.0: return 12.7        # barrel extension
        if z < 62.0: return 12.45       # 0.98 in chamber reinforce
        if z < 72.0: return 12.45 + (mid - 12.45) * (z - 62.0) / 10.0
        if z < 188.0: return mid
        if z < 222.0: return 9.53       # 0.750 in front sight base journal
        if z < 262.0: return 9.4
        if z < 300.0: return 8.0        # M203 cut
        if z < 352.0: return 9.4
        return 10.9                     # A2 flash hider over the threads
    def r_in(z):
        if z < 36.5: return 4.7
        if z < 44.7: return 3.2
        return 2.82
    return dict(name='M4A1 ' + ('SOCOM' if heavy else 'government'), nz=nz, nr=nr, z_edges_mm=ze, z_mm=zc, breech_mm=0.0, muzzle_mm=368.3,
                r_out_mm=np.array([r_out(z) for z in zc]), r_in_mm=np.array([r_in(z) for z in zc]),
                nut=(zc >= 10.0) & (zc < 30.0), upper=(zc < 16.0), hg=(zc >= 30.0) & (zc < 188.0), gb=(zc >= 188.0) & (zc < 222.0),
                exposed=(zc >= 222.0), hg_cells=(zc >= 16.0) & (zc < 188.0), piston_span=(zc >= 30.0) & (zc < 188.0),
                hand_z_mm=110.0, gas_piston=False)


# =============================================================================== heat per shot, from ../action/action.json
PATM = 101325.0
TREF = 298.15          # bore temperature at which the reference heat per shot is quoted
_SH_CACHE = {}

def _gas_history():
    """Gas state in the bore for one shot, from the sampled interior ballistics of action.json (breech pressure, bullet travel and
    speed, mean gas temperature), continued past the end of its 4 ms record with the same isentropic choked blowdown action/sim.py uses.
    Returns arrays on a time grid from ignition: dt, T gas, density, bullet-base Lagrange coordinate, speed scale, in-bore flag."""
    b = ACTION['ballistics']; dt0 = b['dt']
    mb, mc, Ab, V0 = AP['m_bullet'], AP['m_charge'], AP['bore_area'], AP['chamber_vol']
    F, g, cov, rho_p = AP['force_const'], AP['gamma'], AP['covolume'], AP['rho_prop']
    R = F / AP['flame_temp']
    travel = AP['barrel_len'] - AP['bullet_base0']
    kb = 1 + mc / (3 * mb); kbr = (1 + mc / (2 * mb)) / kb           # Lagrange: breech pressure / mean pressure
    pbr = np.array(b['chamber_MPa']) * 1e6; x = np.array(b['bullet_mm']) * 1e-3; v = np.array(b['bullet_mps']); Tg = np.array(b['gas_temp_K'])
    t = np.arange(len(pbr)) * dt0
    t_exit = float(np.interp(travel - 1e-9, x, t))
    # fine grid while the bullet is in the bore and just after, coarser later
    tf = np.concatenate([np.arange(0.0, 1.5e-3, 2e-6), np.arange(1.5e-3, t[-1], 1e-5)])
    dtf = np.diff(np.concatenate([tf, [t[-1]]]))
    P = np.interp(tf, t, pbr); X = np.minimum(np.interp(tf, t, x), travel); V = np.interp(tf, t, v); T = np.interp(tf, t, Tg)
    inb = tf < t_exit
    Pm = np.where(inb, P / kbr, P)
    psi = np.clip(Pm * (V0 + Ab * X - mc / rho_p) / (mc * (R * T - Pm / rho_p + Pm * cov)), 1e-3, 1.0)
    Vres = V0 + Ab * travel
    m = np.where(inb, mc * psi, Pm * Vres / (R * T + Pm * cov))
    rho = m / np.where(inb, V0 + Ab * X - mc * (1 - psi) / rho_p, Vres)
    # continue the blowdown to 1.05 atm
    crit = (2 / (g + 1)) ** (g / (g - 1)); kflow = math.sqrt(g) * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1)))
    mm, TT, PP = float(m[-1]), float(T[-1]), float(Pm[-1]); et, eT, erho = [], [], []; tt = float(t[-1]); dte = 2e-5
    while PP > 1.05 * PATM and tt < 0.05:
        et.append(tt); eT.append(TT); erho.append(mm / Vres)
        pr = max(PATM / PP, crit)
        md = Ab * PP * math.sqrt(2 * g / ((g - 1) * R * TT) * (pr ** (2 / g) - pr ** ((g + 1) / g))) if pr > crit else Ab * PP * kflow / math.sqrt(R * TT)
        dm = min(md * dte, 0.5 * mm); TT *= (1 - dm / mm) ** (g - 1); mm -= dm; PP = mm * R * TT / (Vres - cov * mm); tt += dte
    n_e = len(et)
    tf = np.concatenate([tf, et]); dtf = np.concatenate([dtf, np.full(n_e, dte)]); T = np.concatenate([T, eT]); rho = np.concatenate([rho, erho])
    X = np.concatenate([X, np.full(n_e, travel)]); V = np.concatenate([V, np.zeros(n_e)]); inb = np.concatenate([inb, np.zeros(n_e, bool)])
    # speed scale: bullet speed in the bore; the sonic speed at the muzzle during blowdown
    astar = np.sqrt(g * R * 2 * T / (g + 1))
    U = np.where(inb, V, astar)
    return dict(t=tf, dt=dtf, T=T, rho=rho, x=X, U=U, inb=inb, t_exit=t_exit, R=R, g=g, travel=travel, l0=V0 / Ab, D=2 * math.sqrt(Ab / math.pi),
                t_end=float(tf[-1]), record_end=float(t[-1]))

def _wall_solve(G, s_st, T0, scale, brass_m=0.0, h_ratio=1.0, t_stop=None, k_brass=120.0, rhoc_brass=3.24e6):
    """Heat into the bore wall at stations s_st [m from the bolt face] over one shot, wall starting at T0 [K].
    Gas side: Dittus-Boelter, Nu = 0.023 Re^0.8 Pr^0.4, on the local gas speed of the Lagrange profile (linear from the breech to the
    bullet base in the equivalent-length coordinate action/sim.py uses for its port pressure), gas density uniform, viscosity by
    Sutherland's law for air, Prandtl number by Eucken's relation.  Wall side: 1D implicit conduction on a graded grid (2 um at the
    surface, 3.5 mm deep) with temperature-dependent steel properties.  With brass_m > 0 the first brass_m metres are cartridge brass
    (the case wall) and the function returns the heat that has reached the steel behind it by t_stop (extraction).
    Returns (J/m2 into the wall, peak flux W/m2, peak surface temperature K)."""
    g = G['g']; R = G['R']; cp = g * R / (g - 1); Pr = 4 * g / (9 * g - 5); D = G['D']; l0 = G['l0']; s0 = AP['bullet_base0']
    ns = len(s_st); nn = 40
    dx = 2e-6 * 1.15 ** np.arange(nn); xc = np.cumsum(dx) - 0.5 * dx
    isb = (xc < brass_m)[None, :]
    Tw = np.full((ns, nn), float(T0)); Q = np.zeros(ns); qmax = np.zeros(ns); Tsmax = np.full(ns, float(T0))
    for i in range(len(G['t'])):
        if t_stop is not None and G['t'][i] >= t_stop: break
        Tg = G['T'][i]; dt = G['dt'][i]
        mu = 1.458e-6 * Tg ** 1.5 / (Tg + 110.4); kg = mu * cp / Pr
        sL = l0 + s_st - s0                                    # Lagrange coordinate of the station
        sb = l0 + G['x'][i]
        u = np.where(sL <= sb, G['U'][i] * sL / sb, 0.0)       # nothing ahead of the bullet
        Re = G['rho'][i] * u * D / mu
        h = scale * h_ratio * 0.023 * Re ** 0.8 * Pr ** 0.4 * kg / D
        k = np.where(isb, k_brass, k_steel(Tw)); rc = np.where(isb, rhoc_brass, 7850.0 * c_steel_C(Tw - K0)) * dx[None, :]
        Gc = 1.0 / (0.5 * dx[None, :-1] / k[:, :-1] + 0.5 * dx[None, 1:] / k[:, 1:])
        Gs = 1.0 / (1.0 / np.maximum(h, 1e-9) + 0.5 * dx[0] / k[:, 0])
        bb = rc / dt; d = bb * Tw
        bb[:, 1:] += Gc; bb[:, :-1] += Gc; bb[:, 0] += Gs; d[:, 0] += Gs * Tg
        for j in range(1, nn):                                 # Thomas algorithm, all stations at once
            w = -Gc[:, j - 1] / bb[:, j - 1]; bb[:, j] += w * Gc[:, j - 1]; d[:, j] -= w * d[:, j - 1]
        Tn = np.empty_like(Tw); Tn[:, -1] = d[:, -1] / bb[:, -1]
        for j in range(nn - 2, -1, -1): Tn[:, j] = (d[:, j] + Gc[:, j] * Tn[:, j + 1]) / bb[:, j]
        q = Gs * (Tg - Tn[:, 0])
        Q += q * dt; qmax = np.maximum(qmax, q); Tsmax = np.maximum(Tsmax, Tn[:, 0] + q * 0.5 * dx[0] / k[:, 0])
        Tw = Tn
    if brass_m > 0:
        st = ~isb[0]
        Q = ((7850.0 * (steel_h(Tw[:, st]) - steel_h(T0))) * dx[None, st]).sum(axis=1)
    return Q, qmax, Tsmax

def shot_heat(scale=1.0):
    """Heat one shot leaves in the gun, by position, from the interior ballistics of ../action/action.json.  Cached per scale."""
    key = round(scale, 6)
    if key in _SH_CACHE: return _SH_CACHE[key]
    G = _gas_history(); D = G['D']; L = AP['barrel_len']; case = AP['case_len']
    s = np.linspace(case, L, 41)
    T0s = np.array([TREF, 600.0, 900.0]); QQ = []; extra = {}
    for T0 in T0s:
        Q, qm, Tsm = _wall_solve(G, s, T0, scale); QQ.append(Q * math.pi * D)
        if T0 == TREF: extra = dict(peak_flux_MW_m2=qm / 1e6, peak_surface_C=Tsm - K0)
    QQ = np.array(QQ)                                                   # J/m at three starting wall temperatures
    # straight line in the starting temperature: Q = Qref (Teff - T0) / (Teff - TREF)
    b_, a_ = np.polyfit(T0s, QQ, 1)                                     # per station
    Teff = -a_ / b_; Qref = a_ + b_ * TREF
    lin_err = float(np.max(np.abs((a_[None, :] + b_[None, :] * T0s[:, None]) / QQ - 1)))
    # in-bore share (to compare with action.json's loss_factor), cold wall
    Gin = dict(G); Qin, _, _ = _wall_solve(Gin, s, TREF, scale, t_stop=G['t_exit'])
    Qrec, _, _ = _wall_solve(Gin, s, TREF, scale, t_stop=G['record_end'])
    tz = lambda y: float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(s)))
    # friction and engraving work left in the bore
    fr = P('friction_to_bore') * AP['bore_area'] * (AP['p_friction'] + AP['p_engrave'] * np.exp(-(s - s[0]) / AP['engrave_len']))
    # chamber: heat through the case wall by the time the case is pulled
    ev = ACTION['events']['times']; t_ext = ev['extract'] - ev['ignition']
    Qc, _, _ = _wall_solve(G, s[:1], TREF, scale, brass_m=P('case_wall_m'), h_ratio=P('chamber_h_ratio'), t_stop=t_ext,
                           k_brass=P('k_brass'), rhoc_brass=P('rhoc_brass'))
    r_ch = 4.7e-3
    f_ch = float(Qc[0] * 2 * math.pi * r_ch / Qref[0])
    # gas cylinder: wall heat = (1 - cyl_heat_eff) x inflow enthalpy, with the orifice flow of action/sim.py
    cyc = ACTION['cycle']; bal = ACTION['ballistics']; g = G['g']; R = G['R']; cp = g * R / (g - 1)
    tb = np.arange(len(bal['port_MPa'])) * bal['dt']; tcy = np.arange(len(cyc['cylinder_MPa'])) * cyc['dt'] + cyc['t0'] - bal['t0']
    Ao = math.pi * (0.5 * AP['port_d']) ** 2 * AP['orifice_cd']; crit = (2 / (g + 1)) ** (g / (g - 1))
    kflow = math.sqrt(g) * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1)))
    Hin = 0.0; m_in = 0.0
    for i in range(len(tb)):
        Pp = bal['port_MPa'][i] * 1e6; Tp = bal['gas_temp_K'][i]; Pc = float(np.interp(tb[i], tcy, cyc['cylinder_MPa'])) * 1e6
        if Pp <= Pc or Pp < 2 * PATM: continue
        pr = Pc / Pp
        md = Ao * Pp * kflow / math.sqrt(R * Tp) if pr <= crit else Ao * Pp * math.sqrt(2 * g / ((g - 1) * R * Tp) * (pr ** (2 / g) - pr ** ((g + 1) / g)))
        Hin += cp * Tp * md * bal['dt']; m_in += md * bal['dt']
    q_cyl = (1 - AP['cyl_heat_eff']) * Hin
    work = 0.5 * AP['m_bullet'] * AP['v_muzzle_target'] ** 2 + 0.5 * (AP['m_charge'] / 3) * AP['v_muzzle_target'] ** 2 \
           + AP['bore_area'] * (AP['p_friction'] * G['travel'] + AP['p_engrave'] * AP['engrave_len'])
    out = dict(s=s, J_per_m_ref=Qref, Teff=Teff, friction_J_per_m=fr, f_chamber=f_ch, q_cylinder_J=q_cyl, cylinder_inflow_mg=m_in * 1e6,
               J_per_m_600K=QQ[1], J_per_m_900K=QQ[2], linear_fit_max_error=lin_err, t_exit_ms=G['t_exit'] * 1e3, blowdown_end_ms=G['t_end'] * 1e3,
               bore_total_J=dict(cold=tz(QQ[0]), at_600K=tz(QQ[1]), at_900K=tz(QQ[2]), in_bore_phase_cold=tz(Qin * math.pi * D),
                                 within_action_record_cold=tz(Qrec * math.pi * D), friction=tz(fr)),
               action_loss_factor_J=AP['loss_factor'] * work, **extra)
    _SH_CACHE[key] = out
    return out


# =============================================================================== solver
class Sim:
    def __init__(self, geo, ambient_C=None, wind=None, over=None):
        self.g = g = geo
        self.p = {k: v[0] for k, v in PARAMS.items() if isinstance(v, tuple)}
        if over: self.p.update(over)
        p = self.p
        self.Ta = (p['ambient_C'] if ambient_C is None else ambient_C) + K0
        self.U = p['wind_m_s'] if wind is None else wind
        nz, nr = g['nz'], g['nr']
        self.dz = dz = np.diff(g['z_edges_mm']) * 1e-3
        ri, ro = g['r_in_mm'] * 1e-3, g['r_out_mm'] * 1e-3
        re = ri[:, None] + (ro - ri)[:, None] * np.linspace(0, 1, nr + 1)[None, :]      # radial cell edges
        rc = 0.5 * (re[:, 1:] + re[:, :-1])
        self.A = math.pi * (re[:, 1:] ** 2 - re[:, :-1] ** 2)                           # annulus areas
        self.M = p['rho_steel'] * self.A * dz[:, None]                                   # cell masses
        self.Gr = 2 * math.pi * dz[:, None] / np.log(rc[:, 1:] / rc[:, :-1])            # radial conductance / k
        self.Ga = np.minimum(self.A[1:], self.A[:-1]) / (0.5 * (dz[1:] + dz[:-1]))[:, None]  # axial conductance / k
        self.ro = ro; self.As = 2 * math.pi * ro * dz                                    # outer surface per station
        self.H = np.full((nz, nr), float(steel_h(self.Ta)))
        self.T = np.full((nz, nr), self.Ta)
        # handguard cells sit on the barrel stations inside the rail
        self.hgi = np.where(g['hg_cells'])[0]; nh = len(self.hgi)
        self.Thg = np.full(nh, self.Ta)
        self.hg_dz = dz[self.hgi]
        self.hg_M = p['rho_al'] * p['hg_area_m2'] * self.hg_dz
        self.hg_Ga = p['k_al_hg'] * p['hg_area_m2'] / (0.5 * (self.hg_dz[1:] + self.hg_dz[:-1]))
        # map barrel station -> handguard cell (or -1)
        self.b2h = -np.ones(nz, int); self.b2h[self.hgi] = np.arange(nh)
        self.m_hg = g['hg'] & (self.b2h >= 0)                 # stations radiating to the handguard
        self.m_nut_hg = g['nut'] & (self.b2h >= 0)            # stations where the rail sits on the nut
        self.m_upper = g['upper']; self.m_gb = g['gb']; self.m_exp = g['exposed'] | (g['hg'] & (self.b2h < 0))
        def share(mask, G):
            a = np.where(mask, self.As, 0.0); return G * a / a.sum() if a.sum() > 0 else a
        self.G_bn = share(g['nut'], p['g_barrel_nut'])
        self.nh = self.b2h[self.m_nut_hg]                    # handguard cells sitting on the nut
        if len(self.nh) == 0: self.nh = np.array([0])
        self.G_up = share(self.m_upper, p['g_barrel_upper'])
        self.G_gb = share(self.m_gb, p['g_barrel_gas_block'])
        self.pist = np.where(g['piston_span'] & (self.b2h >= 0))[0]
        eb, eh = p['eps_steel'], p['eps_al']
        ratio = ro / p['hg_r_inner_m']
        self.eps_gap = 1.0 / (1.0 / eb + ratio * (1.0 / eh - 1.0))
        # lumps: gas block, piston, flash hider front, upper front, upper rear
        self.Tl = dict(gb=self.Ta, piston=self.Ta, fh=self.Ta, uf=self.Ta, ur=self.Ta, nut=self.Ta)
        # per-shot heat to the bore, J per station at a bore surface at TREF, and the temperature at which it would fall to zero
        SH = shot_heat(p['bore_heat_scale'])
        s = (g['z_mm'] - g['breech_mm']) * 1e-3
        bore = s >= p['case_len_m']
        fch = p['f_chamber']
        self.Eg = np.where(bore, np.interp(s, SH['s'], SH['J_per_m_ref']), fch * SH['J_per_m_ref'][0]) * dz
        self.Teff = np.where(bore, np.interp(s, SH['s'], SH['Teff']), SH['Teff'][0])
        port = np.zeros(nz); port[np.where(self.m_gb)[0]] = 1.0
        self.Efix = np.where(bore, np.interp(s, SH['s'], SH['friction_J_per_m']), 0.0) * dz + p['q_port_J'] * port / max(port.sum(), 1)
        self.Eshot = self.Eg + self.Efix                       # cold-bore value, for reporting
        # the chambered round: a brass lump on the chamber wall, thrown out (with its heat) at every shot and replaced by a cool one
        ch = (s < 0.0365); a_ch = np.where(ch, dz, 0.0)
        self.G_case = p['g_chamber_case'] * a_ch / a_ch.sum(); self.T_case = self.Ta; self.E_case_out = 0.0
        self.T_prop = self.Ta; self.D_co = 0.0; self.mv_delta = 0.0      # propellant of the chambered round, its cook-off integral, last shot's velocity gain
        self.free = g['z_mm'] >= 22.0                                   # barrel ahead of the nut: free to bend
        self.q_gb = SH['q_cylinder_J'] * (1 - p['piston_share']) if g['gas_piston'] else p['q_gas_block_di_J']
        self.q_piston = SH['q_cylinder_J'] * p['piston_share'] if g['gas_piston'] else 0.0
        se = (g['z_edges_mm'] - g['breech_mm'])                           # chamber probe: the wall around the case body, 15 to 40 mm from the bolt face
        self.w_ch = np.clip(np.minimum(se[1:], 40.0) - np.maximum(se[:-1], 15.0), 0.0, None) / np.diff(se)
        self.t = 0.0; self.shots = 0
        self.E_in = 0.0; self.E_out = 0.0
        self._coef_t = -1e9
        self.E0 = self.energy()
        # stability limit of the explicit scheme
        dr = (ro - ri) / nr
        amax = 42.7 / (p['rho_steel'] * 430.0)
        self.dt_max = 0.40 * float(np.min(dr) ** 2 / amax) / 1.0
        self.dt_max = min(self.dt_max, 0.2 * float(np.min(self.hg_dz)) ** 2 / (p['k_al_hg'] / (p['rho_al'] * 896)), 0.25 * float(np.min(dz)) ** 2 / amax)

    # ---------------------------------------------------------------- energy bookkeeping
    def energy(self):
        p = self.p
        Tl = self.Tl
        def e_st(m, T): return m * float(steel_h(T))
        def e_al(m, T): return m * (896.0 * (T - K0) + 0.225 * (T - K0 - 25.0) ** 2)
        return (float((self.M * self.H).sum()) + float(e_al(self.hg_M, self.Thg).sum()) + e_st(p['m_gas_block'], Tl['gb'])
                + e_st(p['m_piston'], Tl['piston']) + p['c_case_J_K'] * self.T_case + e_st(p['m_fh_front'], Tl['fh']) + e_st(p['m_nut'], Tl['nut']) + e_al(p['m_upper_front'], Tl['uf']) + e_al(p['m_upper_rear'], Tl['ur']))

    # ---------------------------------------------------------------- coefficients refreshed twice a second
    def _coefs(self):
        p = self.p; Ta = self.Ta; U = self.U
        Ts = self.T[:, -1]
        h = h_cylinder(2 * self.ro, Ts, Ta, U)
        self.hA_amb = np.where(self.m_exp, h * self.As, 0.0)
        Thg_b = np.where(self.b2h >= 0, self.Thg[np.clip(self.b2h, 0, None)], Ta)
        Gg = gap_conductance(self.ro, p['hg_r_inner_m'], Ts, Thg_b) * self.dz
        self.G_gap = np.where(self.m_hg, Gg, 0.0)
        self.h_hg = h_cylinder(0.060, self.Thg, Ta, U)
        Tl = self.Tl
        self.h_gb = float(h_cylinder(0.030, Tl['gb'], Ta, U)); self.h_fh = float(h_cylinder(0.0212, Tl['fh'], Ta, U))
        self.h_uf = float(h_cylinder(0.045, Tl['uf'], Ta, U)); self.h_ur = float(h_cylinder(0.045, Tl['ur'], Ta, U))

    def fire(self, n=1):
        """Deposit n shots' heat.  The gas-to-wall part falls linearly with the bore surface temperature (hot wall, less heat)."""
        p = self.p
        E = n * (self.Eg * np.clip((self.Teff - self.T[:, 0]) / (self.Teff - TREF), 0.0, None) + self.Efix)
        self.H[:, 0] += E / self.M[:, 0]
        self.T[:, 0] = steel_T(self.H[:, 0])
        Tl = self.Tl
        self.mv_delta = MV['m_s_per_K'] * (min(self.T_prop, MV['T_max_C'] + K0) - TREF)
        dE = p['c_case_J_K'] * (self.T_case - self.Ta); self.E_out += dE; self.E_case_out += dE    # fired case leaves, fresh round in
        self.T_case = self.Ta; self.T_prop = self.Ta; self.D_co = 0.0
        qg = self.q_gb; qp = self.q_piston
        Tl['gb'] = float(steel_T(steel_h(Tl['gb']) + n * qg / p['m_gas_block']))
        Tl['piston'] = float(steel_T(steel_h(Tl['piston']) + n * qp / p['m_piston']))
        Tl['fh'] = float(steel_T(steel_h(Tl['fh']) + n * p['q_flash_hider_J'] / p['m_fh_front']))
        self.E_in += float(E.sum()) + n * (qg + qp + p['q_flash_hider_J'])
        self.shots += n

    def step(self, dt):
        p = self.p; Ta = self.Ta; T = self.T; Tl = self.Tl
        if self.t - self._coef_t >= 0.5: self._coefs(); self._coef_t = self.t
        k = k_steel(T)
        dQ = np.zeros_like(T)
        qr = self.Gr * 0.5 * (k[:, 1:] + k[:, :-1]) * (T[:, 1:] - T[:, :-1])
        dQ[:, :-1] += qr; dQ[:, 1:] -= qr
        qa = self.Ga * 0.5 * (k[1:] + k[:-1]) * (T[1:] - T[:-1])
        dQ[:-1] += qa; dQ[1:] -= qa
        Ts = T[:, -1]; Ts4 = Ts ** 4; Ta4 = Ta ** 4
        Thg = self.Thg; hb = np.clip(self.b2h, 0, None)
        Thg_b = Thg[hb]
        es = p['eps_steel']; Fa = p['hg_view_to_ambient']; fv = p['hg_vent_fraction']
        # barrel surface -> ambient
        q_amb = self.hA_amb * (Ts - Ta) + np.where(self.m_exp, SIGMA * es * self.As * (Ts4 - Ta4), 0.0)
        q_amb = q_amb + np.where(self.m_hg, SIGMA * es * Fa * self.As * (Ts4 - Ta4) + fv * self.G_gap * (Ts - Ta), 0.0)
        # barrel surface -> handguard (radiation, gap convection, nut contact)
        q_hg = np.where(self.m_hg, SIGMA * self.eps_gap * (1 - Fa) * self.As * (Ts4 - Thg_b ** 4) + (1 - fv) * self.G_gap * (Ts - Thg_b), 0.0)
        q_bn = self.G_bn * (Ts - Tl['nut'])
        q_up = self.G_up * (Ts - Tl['uf'])
        q_gb = self.G_gb * (Ts - Tl['gb'])
        q_fh = p['g_barrel_fh'] * (T[-1, -1] - Tl['fh'])
        out = q_amb + q_hg + q_up + q_gb + q_bn
        out[-1] += q_fh
        dQ[:, -1] -= out
        q_case = self.G_case * (T[:, 0] - self.T_case)
        dQ[:, 0] -= q_case
        self.H += dQ * dt / self.M
        self.T = steel_T(self.H)
        # handguard
        dH = np.zeros_like(Thg)
        np.add.at(dH, hb[self.b2h >= 0], q_hg[self.b2h >= 0])
        qax = self.hg_Ga * (Thg[1:] - Thg[:-1]); dH[:-1] += qax; dH[1:] -= qax
        ea = p['eps_al']
        loss_hg = (self.h_hg * p['hg_perim_out_m'] * (Thg - Ta) + SIGMA * ea * p['hg_perim_rad_m'] * (Thg ** 4 - Ta4)) * self.hg_dz
        dH -= loss_hg
        # piston/rod -> handguard (radiation + still-air film), spread along its span
        ph = self.b2h[self.pist]
        Ap = p['a_piston'] / max(len(ph), 1)
        q_p = Ap * (SIGMA * 0.75 * (Tl['piston'] ** 4 - Thg[ph] ** 4) + 8.0 * (Tl['piston'] - Thg[ph])) if self.g['gas_piston'] else np.zeros(len(ph))
        np.add.at(dH, ph, q_p)
        q_hu = p['g_handguard_upper'] * (Thg[0] - Tl['uf']); dH[0] -= q_hu
        q_nh = p['g_nut_handguard'] / len(self.nh) * (Tl['nut'] - Thg[self.nh]); np.add.at(dH, self.nh, q_nh)
        q_nu = p['g_nut_upper'] * (Tl['nut'] - Tl['uf'])
        self.Thg = Thg + dH * dt / (self.hg_M * c_al(Thg))
        self.T_case += float(q_case.sum()) * dt / p['c_case_J_K']
        self.T_prop += (self.T_case - self.T_prop) * dt / COOKOFF['tau_prop_s']
        self.D_co += dt / cookoff_induction(self.T_case)
        # lumps
        def cool(Tx, A, h, eps): return A * (h * (Tx - Ta) + SIGMA * eps * (Tx ** 4 - Ta4))
        q_gp = p['g_gas_block_piston'] * (Tl['gb'] - Tl['piston']) if self.g['gas_piston'] else 0.0
        l_gb = cool(Tl['gb'], p['a_gas_block'], self.h_gb, es); l_fh = cool(Tl['fh'], p['a_fh_front'], self.h_fh, es)
        l_uf = cool(Tl['uf'], p['a_upper_front'], self.h_uf, ea); l_ur = cool(Tl['ur'], p['a_upper_rear'], self.h_ur, ea)
        q_ufr = p['g_upper_front_rear'] * (Tl['uf'] - Tl['ur'])
        Tl['gb'] = float(steel_T(steel_h(Tl['gb']) + (q_gb.sum() - q_gp - l_gb) * dt / p['m_gas_block']))
        Tl['piston'] = float(steel_T(steel_h(Tl['piston']) + (q_gp - q_p.sum()) * dt / p['m_piston']))
        Tl['fh'] = float(steel_T(steel_h(Tl['fh']) + (q_fh - l_fh) * dt / p['m_fh_front']))
        Tl['nut'] = float(steel_T(steel_h(Tl['nut']) + (q_bn.sum() - q_nh.sum() - q_nu) * dt / p['m_nut']))
        Tl['uf'] += (q_up.sum() + q_hu + q_nu - q_ufr - l_uf) * dt / (p['m_upper_front'] * float(c_al(Tl['uf'])))
        Tl['ur'] += (q_ufr - l_ur) * dt / (p['m_upper_rear'] * float(c_al(Tl['ur'])))
        self.E_out += (q_amb.sum() + loss_hg.sum() + l_gb + l_fh + l_uf + l_ur) * dt
        # line strengths of the two plumes the mirage model uses, W/m
        ex = self.g['exposed'] & (self.g['z_mm'] < 349.0)
        self.q_line_barrel = float((self.hA_amb * (Ts - Ta))[ex].sum() / self.dz[ex].sum())
        sp = p['hg_top_bottom_split']
        self.q_line_hg = float(((self.h_hg * p['hg_perim_out_m'] * 0.5 * (1 + sp) * (Thg - Ta)) * self.hg_dz).sum() / self.hg_dz.sum()
                               + (fv * self.G_gap * (Ts - Ta)).sum() / self.hg_dz.sum())
        self.t += dt

    # ---------------------------------------------------------------- probes
    def probes(self):
        g = self.g; z = g['z_mm']; s = z - g['breech_mm']; T = self.T - K0; Tl = self.Tl
        th = (s >= 45) & (s < 70); w = self.w_ch; wm = self.M * w[:, None]; wl = w * self.dz
        hgm = g['hg']; ex = g['exposed'] & (z < 349)
        ih = int(np.argmin(np.abs(z[self.hgi] - g['hand_z_mm'])))
        Thg = self.Thg - K0; excess = Thg - (self.Ta - K0); sp = self.p['hg_top_bottom_split']
        return dict(t=self.t, shots=self.shots,
                    chamber_wall=float((T * wm).sum() / wm.sum()), chamber_skin=float((T[:, 0] * wl).sum() / wl.sum()), chamber_outer=float((T[:, -1] * wl).sum() / wl.sum()),
                    throat_bore=float(T[th, 0].max()), throat_outer=float(T[th, -1].max()),
                    barrel_max_outer=float(T[:, -1].max()), barrel_max_z_mm=float(z[int(np.argmax(T[:, -1]))]),
                    bore_max=float(T[:, 0].max()),
                    under_handguard_outer=float(T[hgm, -1].mean()), exposed_outer=float(T[ex, -1].mean()),
                    neck_outer=float(T[(z >= 270) & (z < 294), -1].mean()) if g['gas_piston'] else float('nan'),
                    muzzle_outer=float(T[-1, -1]), barrel_mean=float((T * self.M).sum() / self.M.sum()),
                    gas_block=Tl['gb'] - K0, piston=Tl['piston'] - K0, flash_hider=Tl['fh'] - K0,
                    upper_front=Tl['uf'] - K0, upper_rear=Tl['ur'] - K0, barrel_nut=Tl['nut'] - K0,
                    handguard_hand=float(Thg[ih] - 0.5 * sp * excess[ih]), handguard_hand_mean=float(Thg[ih]),
                    handguard_max=float(Thg.max()), handguard_top_max=float((Thg + sp * excess).max()), handguard_mean=float(Thg.mean()),
                    round_case=self.T_case - K0, round_propellant=self.T_prop - K0, cookoff_damage=self.D_co, mv_delta_m_s=self.mv_delta,
                    mv_delta_next_m_s=MV['m_s_per_K'] * (min(self.T_prop, MV['T_max_C'] + K0) - TREF), poi_bow_moa=self.poi_bow_moa(),
                    q_line_barrel_W_m=getattr(self, 'q_line_barrel', 0.0), q_line_handguard_W_m=getattr(self, 'q_line_hg', 0.0))

    def poi_bow_moa(self):
        """Muzzle angle from thermal bow, MOA, negative = impact low (see POI)."""
        Tm = (self.T * self.M).sum(axis=1) / self.M.sum(axis=1) - self.Ta
        kappa = self.p['alpha_steel'] * POI['eta'] * Tm / (2 * self.ro)
        return -float((kappa * self.dz)[self.free].sum()) * 3437.75

    def fields(self):
        return dict(outer=np.round(self.T[:, -1] - K0, 1), bore=np.round(self.T[:, 0] - K0, 1), handguard=np.round(self.Thg - K0, 1))


def run(sim, shot_times, t_end, sample_times, dt=None, stop=None):
    """Advance to t_end, firing at shot_times.  Returns (probe rows, field snapshots)."""
    dt = dt or min(0.02, sim.dt_max)
    shot_times = np.asarray(shot_times, float); si = 0
    rows = []; snaps = []
    sample_times = list(sample_times); k = 0
    n = int(math.ceil(t_end / dt))
    for i in range(n + 1):
        t = i * dt
        while k < len(sample_times) and sample_times[k] <= t + 1e-9:
            rows.append(sim.probes()); f = sim.fields(); f['t'] = round(t, 3); snaps.append(f); k += 1
        m = 0
        while si < len(shot_times) and shot_times[si] < t + dt - 1e-12: si += 1; m += 1
        if m: sim.fire(m)
        sim.step(dt)
        if stop and stop(sim): rows.append(sim.probes()); break
    return rows, snaps


# =============================================================================== firing schedules
def sched_uniform(n, rpm, mag=None, reload_s=0.0, t0=0.0):
    ts = []; t = t0
    for i in range(n):
        ts.append(t); t += 60.0 / rpm
        if mag and (i + 1) % mag == 0: t += reload_s
    return np.array(ts)

def sched_bursts(n, burst, cyclic, pause_s, mag=30, reload_s=5.0):
    ts = []; t = 0.0; i = 0
    while i < n:
        for b in range(burst):
            if i >= n: break
            ts.append(t); t += 60.0 / cyclic; i += 1
            if i % mag == 0: t += reload_s; break
        else:
            t += pause_s
    return np.array(ts)

def schedules(cyc):
    return [
        dict(id='semi_45', title='Semi-automatic, 45 rounds/min (manual: maximum effective rate, semi), 300 rounds',
             shots=sched_uniform(300, 45.0)),
        dict(id='sustained_12', title='Sustained, 12 rounds/min for 30 min (360 rounds)', shots=sched_uniform(360, 12.0)),
        dict(id='sustained_15', title='Sustained, 15 rounds/min for 30 min (450 rounds)', shots=sched_uniform(450, 15.0)),
        dict(id='auto_bursts', title='Automatic, 5-round bursts at %d rounds/min cyclic, 3 s between bursts, 5 s reloads, 210 rounds' % cyc,
             shots=sched_bursts(210, 5, cyc, 3.0)),
        dict(id='auto_mag_dumps', title='Automatic, 30-round magazines emptied at %d rounds/min cyclic, 5 s reloads, 210 rounds' % cyc,
             shots=sched_uniform(210, cyc, mag=30, reload_s=5.0)),
        dict(id='manual_250_in_3min', title="HK manual's limit: 250 rounds in 3 minutes (83 rounds/min, evenly paced)",
             shots=sched_uniform(250, 250.0 / 3.0)),
        dict(id='auto_to_destruction', title='Beyond the manual: 30-round magazines at cyclic, 4 s reloads, 600 rounds (where glow starts)',
             shots=sched_uniform(600, cyc, mag=30, reload_s=4.0)),
    ]


# =============================================================================== validation
MARSH = dict(   # NSWC Crane, C. Marsh, "Small Arms Propellant Thermal Stability", NDIA Small Arms Symposium 2006, slide 6.
                # M4A1, MK 262, thermocouple outside the chamber at the shoulder; deg F at the end of each 30-round magazine and the
                # seconds taken to fire it.  Magazines 1 to 7, then the magazines were reloaded (the gun cooling meanwhile) and 8 to 14 fired.
                # None = the slide gives no duration; the mean of that weapon's other magazines is used.
    semi=dict(initial_F=77, temp_F=[165, 211, 244, 261, 290, 303, 317], dur_s=[52, 60, 60, None, 64, 60, 63],
              initial2_F=175, temp2_F=[216, 250, 278, 296, 308, 314, 320], dur2_s=[55, 55, 58, 57, 60, 59, 63]),
    double_tap=dict(initial_F=83, temp_F=[177, 240, 278, 304, 326, 354, 384], dur_s=[None, 49, 41, 55, 45, 47, 48],
                    initial2_F=167, temp2_F=[213, 235, 255, 277, 308, 343, 356], dur2_s=[None, 40, 40, 60, 50, 60, 48]),
)
def F2C(f): return (f - 32.0) / 1.8
def _durs(d):
    m = float(np.mean([x for x in d if x is not None])); return [m if x is None else float(x) for x in d]

def validate_marsh(over=None, heavy=True, gap_s=20.0, second=True):
    """Fire the Crane sequences through the M4A1 geometry; return model and measured end-of-magazine temperatures.
    gap_s is the magazine change, which the slides do not give (INFERRED: 20 s).  The second sequence starts when the
    model's thermocouple has cooled to the recorded second initial temperature."""
    out = {}
    for name, d in MARSH.items():
        sim = Sim(geometry_m4a1(heavy), ambient_C=F2C(d['initial_F']), over=over)
        z = sim.g['z_mm']
        dt = min(0.02, sim.dt_max)
        def tc(): return float(np.interp(36.5, z, sim.T[:, -1]) - K0)       # thermocouple outside the chamber at the shoulder
        def mags(durs):
            rows = []
            for k, dur in enumerate(durs):
                n = int(round(dur / dt)); shots = np.floor(np.arange(30) * dur / 30.0 / dt).astype(int); j = 0
                for i in range(n):
                    m = 0
                    while j < 30 and shots[j] <= i: j += 1; m += 1
                    if m: sim.fire(m)
                    sim.step(dt)
                rows.append(tc())
                if k < len(durs) - 1:
                    for i in range(int(round(gap_s / dt))): sim.step(dt)
            return rows
        r1 = mags(_durs(d['dur_s'])); meas1 = [F2C(f) for f in d['temp_F']]; T0 = F2C(d['initial_F'])
        out[name] = dict(model_C=[round(x, 1) for x in r1], measured_C=[round(x, 1) for x in meas1],
                         rise_ratio=[round((a - T0) / (b - T0), 3) for a, b in zip(r1, meas1)])
        if second:
            t_c = 0.0; T2 = F2C(d['initial2_F'])
            while tc() > T2 and t_c < 7200: sim.step(dt); t_c += dt
            r2 = mags(_durs(d['dur2_s'])); meas2 = [F2C(f) for f in d['temp2_F']]
            out[name].update(second_cool_down_s=round(t_c), second_initial_C=round(T2, 1), second_model_C=[round(x, 1) for x in r2], second_measured_C=[round(x, 1) for x in meas2])
    return out

def marsh_errors(over=None, key='model_C', mkey='measured_C'):
    e = []
    for heavy in (False, True):
        r = validate_marsh(over, heavy, second=(key != 'model_C'))
        for v in r.values(): e += [a - b for a, b in zip(v[key], v[mkey])]
    return float(np.sqrt(np.mean(np.square(e)))), float(np.mean(e))

def marsh_scan():
    """Error of the first-sequence fit at the values used and around them (the evidence for the two calibrated numbers)."""
    f0, g0 = P('f_chamber'), P('g_chamber_case'); rows = []
    for f, gc in ((f0, g0), (0.85 * f0, g0), (1.15 * f0, g0), (f0, 0.5 * g0), (f0, 2.0 * g0), (f0, 0.0), (1.15, 0.0)):
        e = marsh_errors(dict(f_chamber=f, g_chamber_case=gc))
        rows.append(dict(f_chamber=round(f, 3), g_chamber_case=round(gc, 3), rms_C=round(e[0], 1), bias_C=round(e[1], 1)))
    e = marsh_errors(dict(f_chamber=1.15, g_chamber_case=0.0), 'second_model_C', 'second_measured_C')
    rows[-1].update(note='the alternative without round cooling, f_chamber refitted', held_out_rms_C=round(e[0], 1), held_out_bias_C=round(e[1], 1))
    return rows

def validate_burst(heavy=False, mode='colt'):
    """Fire-to-destruction: M4A1 government barrel, 30-round magazines on automatic.
    'colt': 535 rounds in 111 s (Colt video, NYT 2010);  'windham': about 90 rounds/min mean (secondary account of ADA317929)."""
    sim = Sim(geometry_m4a1(heavy))
    cyc = 850.0                           # M4A1 cyclic rate, middle of the 700 to 950 rounds/min of its manual (INFERRED choice)
    if mode == 'colt': reload_s = (111.0 - 535 * 60 / cyc) / 17.0
    else: reload_s = 30 * 60 / 90.0 - 30 * 60 / cyc
    ts = sched_uniform(960, cyc, mag=30, reload_s=reload_s)
    marks = {}; trace = dict(rounds=[], barrel_max_outer_C=[], t_s=[])
    def stop(s):
        Tm = float(s.T[:, -1].max()) - K0
        if s.shots % 15 == 0 and (not trace['rounds'] or trace['rounds'][-1] != s.shots):
            trace['rounds'].append(s.shots); trace['barrel_max_outer_C'].append(round(Tm, 1)); trace['t_s'].append(round(s.t, 2))
        for name, thr in (('glow_dark_525C', 525.0), ('glow_day_700C', 700.0), ('weakened_737C', 737.0), ('rupture_817C', 817.0)):
            if name not in marks and Tm >= thr:
                marks[name] = dict(rounds=s.shots, t_s=round(s.t, 1), z_mm=float(s.g['z_mm'][int(np.argmax(s.T[:, -1]))]))
        return 'rupture_817C' in marks
    rows, _ = run(sim, ts, ts[-1] + 5, [], stop=stop)
    return dict(reload_s=round(reload_s, 2), marks=marks, trace=trace, final=rows[-1] if rows else None)

def rounds_to_cookoff_point(geo, rpm=90.0, thr_C=180.0):
    """Rounds of rapid continuous fire (rpm) until the chamber wall reaches thr_C (compare TM 9-1005-319-10: 140 / 150 / 180 rounds)."""
    sim = Sim(geo); ts = sched_uniform(500, rpm)
    res = {}
    def stop(s):
        if s.probes()['chamber_wall'] >= thr_C: res['rounds'] = s.shots; res['t_s'] = round(s.t, 1); return True
        return False
    run(sim, ts, ts[-1] + 60, [], stop=stop)
    return res


# =============================================================================== effects
def planck_luminance(T, eps=0.85):
    """Photopic luminance [cd/m2] and linear sRGB chromaticity of a grey body at T [K]."""
    lam = np.linspace(380e-9, 780e-9, 401)
    B = 2 * 6.62607e-34 * 2.99792e8 ** 2 / lam ** 5 / np.expm1(6.62607e-34 * 2.99792e8 / (lam * 1.380649e-23 * T))
    nm = lam * 1e9                                  # CIE 1931 analytic fits (Wyman, Sloan, Shirley 2013)
    def gs(x, mu, s1, s2): return np.exp(-0.5 * ((x - mu) / np.where(x < mu, s1, s2)) ** 2)
    xb = 1.056 * gs(nm, 599.8, 37.9, 31.0) + 0.362 * gs(nm, 442.0, 16.0, 26.7) - 0.065 * gs(nm, 501.1, 20.4, 26.2)
    yb = 0.821 * gs(nm, 568.8, 46.9, 40.5) + 0.286 * gs(nm, 530.9, 16.3, 31.1)
    zb = 1.217 * gs(nm, 437.0, 11.8, 36.0) + 0.681 * gs(nm, 459.0, 26.0, 13.8)
    tz = lambda y: float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(lam)))
    X, Y, Z = (tz(B * c) for c in (xb, yb, zb))
    L = 683.0 * eps * Y
    rgb = np.array([3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z, 0.0557 * X - 0.2040 * Y + 1.0570 * Z])
    rgb = np.clip(rgb, 0, None); rgb = rgb / rgb.max()
    return L, [round(float(c), 4) for c in rgb]
GLOW_T = list(range(400, 1151, 25))

def mirage(Q_line, Ta, U, y, L_path, dT_surface):
    """Plume above a horizontal line source of convective power Q_line [W/m] (Rouse, Yih & Humphreys 1952 line plume).
    Returns centre-line excess temperature at height y, refractive-index difference, 1/e half-width, rise speed,
    the height at which the excess falls to 3 K, and the apparent image jitter along a sight line of length L_path."""
    rho, cp = 101325.0 / (287.05 * Ta), 1006.0
    F = G0 * max(Q_line, 0.0) / (rho * cp * Ta)
    w = 1.8 * F ** (1 / 3)
    calm = 2.6 * F ** (2 / 3) * Ta / (G0 * y)
    if U > w and U > 0: calm = min(calm, F * Ta / (G0 * U * y))          # bent-over plume in a cross-wind
    dT = min(calm, 0.5 * max(dT_surface, 0.0))
    dn = 0.0796 * (1 / Ta - 1 / (Ta + dT))        # n - 1 = 7.86e-4 p[kPa] / T[K] (Edlen, visible light, 101.3 kPa)
    b = 0.156 * y
    h_calm = 2.6 * F ** (2 / 3) * Ta / (G0 * 3.0)
    h = min(h_calm, F * Ta / (G0 * U * 3.0)) if (U > w and U > 0) else h_calm
    on_axis = math.exp(-(U / (0.35 * w)) ** 2) if w > 0 else 0.0         # cross-wind carries the plume off the sight line
    jitter = 0.3 * dn * math.sqrt(2 * math.sqrt(math.pi) * L_path / b) * on_axis     # random-medium ray wander, rad rms
    steady = dn / y * L_path * on_axis
    return dict(dT=dT, dn=dn, half_width=b, rise_speed=w, height=h, jitter_moa=jitter * 3437.75, steady_moa=steady * 3437.75)

MIRAGE = dict(sight_y=BP['sight_line'] * 1e-3, hg_top_y=BP['rail_floor'] * 1e-3, barrel_r=BP['barrel_r'] * 1e-3,
              len_barrel=(BP['fh_l0'] - BP['gas_block'][1]) * 1e-3, len_hg=BP['hg_l1'] * 1e-3, ref_y=0.03)
def mirage_sight(Qb, Qh, dTb, dTh, Ta, U):
    """Both plumes as the shooter and a side camera see them.  The sight line (build.py sight_line, 65.5 mm above the bore) passes
    above the exposed barrel's top for len_barrel and above the handguard's top for len_hg.  'strength' (0..1) is the index
    difference 30 mm above the hotter source as a fraction of the ambient air's whole refractivity (n - 1), which is
    dT / (Ta + dT): 0 for no plume, 1 for infinitely hot air; 'height' is the taller plume."""
    M = MIRAGE
    a = mirage(Qb, Ta, U, M['sight_y'] - M['barrel_r'], M['len_barrel'], dTb); b = mirage(Qh, Ta, U, M['sight_y'] - M['hg_top_y'], M['len_hg'], dTh)
    ra = mirage(Qb, Ta, U, M['ref_y'], M['len_barrel'], dTb); rb = mirage(Qh, Ta, U, M['ref_y'], M['len_hg'], dTh)
    dn_ref = max(ra['dn'], rb['dn'])
    return dict(dn=dn_ref, dn_sight=max(a['dn'], b['dn']), height=max(a['height'], b['height']), jitter_moa=math.hypot(a['jitter_moa'], b['jitter_moa']),
                steady_moa=a['steady_moa'] + b['steady_moa'], rise_speed=max(a['rise_speed'], b['rise_speed']), strength=min(1.0, dn_ref / (0.0796 / Ta)),
                gradient=dn_ref / (0.156 * M['ref_y']))

# ---- cook-off.  The case of the chambered round follows the chamber wall (lump in Sim); the propellant against the case wall
# ignites after an induction time that falls steeply with temperature.  Two anchors (INFERRED readings of published statements):
#   170 C, 600 s : smokeless (nitrocellulose) propellant self-ignites at about 160 to 200 C on slow heating (handbook range)
#   220 C,  10 s : TM 9-1005-319-10: a round left in a barrel at the cook-off point may fire "in as little as 10 seconds"
# Check: NSWC Crane (Marsh 2006) soaked rounds in a 330 F (166 C) chamber for 60 s and fired them without a cook-off.
COOKOFF = dict(T1_C=170.0, t1_s=600.0, T2_C=220.0, t2_s=10.0, tau_prop_s=25.0, caution_C=170.0, danger_C=220.0)
COOKOFF['E_over_R_K'] = math.log(COOKOFF['t1_s'] / COOKOFF['t2_s']) / (1 / (COOKOFF['T1_C'] + K0) - 1 / (COOKOFF['T2_C'] + K0))
def cookoff_induction(T_K):
    """Induction time [s] of propellant held at T_K (Arrhenius through the two anchors)."""
    return COOKOFF['t1_s'] * math.exp(min(60.0, COOKOFF['E_over_R_K'] * (1 / max(T_K, 200.0) - 1 / (COOKOFF['T1_C'] + K0))))
def cookoff_time(T_chamber_C, T_round0_C=25.0, limit_s=1800.0):
    """Time for a fresh round, chambered at T_round0_C into a chamber held at T_chamber_C, to cook off; inf beyond limit_s."""
    tau = P('c_case_J_K') / max(P('g_chamber_case'), 1e-9)
    Tw = T_chamber_C + K0; T0 = T_round0_C + K0
    if cookoff_induction(Tw) > limit_s: return float('inf')
    D = 0.0; t = 0.0; dt = 0.25
    while t < limit_s:
        Tc = Tw - (Tw - T0) * math.exp(-(t + 0.5 * dt) / tau)
        D += dt / cookoff_induction(Tc); t += dt
        if D >= 1.0: return t
    return float('inf')

# ---- muzzle velocity of a round that has sat in a hot chamber.  INFERRED from Marsh 2006 slide 8: lot BLH03M032 averaged 65,172 psi
# after 15 s in a 200 F chamber and 85,662 psi after 60 s at 330 F (+31 %).  With velocity ~ pressure^0.4 (INFERRED exponent, between
# the 0.25 and 0.5 of closed-form interior ballistics) that is +11 % over a propellant temperature rise of about 110 K: 0.85 m/s per K.
MV = dict(m_s_per_K=0.85, p_ratio=85662.0 / 65172.0, exponent=0.4, T_max_C=166.0)   # T_max_C: the hottest soak in the source data; no gain is claimed beyond it
MV['derived_m_s_per_K'] = (MV['p_ratio'] ** MV['exponent'] - 1) * AP['v_muzzle_target'] / 110.0

COMFORT = [   # bare skin on bare metal
    dict(level=0, name='comfortable', below_C=43.0, note='below 43 C: ISO 13732-1 gives 43 C as the burn threshold for contact of 8 h and longer'),
    dict(level=1, name='warm', below_C=48.0, note='43 to 48 C: can be held; ISO 13732-1 burn threshold for 10 min contact with uncoated metal is 48 C'),
    dict(level=2, name='hot', below_C=51.0, note='48 to 51 C: ISO 13732-1 burn threshold for 1 min contact with uncoated metal is 51 C; MIL-STD-1472 limit for prolonged bare-hand contact with metal is 49 C'),
    dict(level=3, name='burn_within_a_minute', below_C=60.0, note='51 to 60 C: ISO 13732-1 10 s threshold is about 55 C; MIL-STD-1472 momentary-contact limit for metal is 60 C'),
    dict(level=4, name='burn_on_grip', below_C=70.0, note='60 to 70 C: burns within seconds; ISO 13732-1 burn threshold spread for 1 s contact with uncoated metal is 65 to 70 C'),
    dict(level=5, name='burn_on_touch', below_C=1e9, note='above 70 C: beyond the ISO 13732-1 1 s burn threshold for bare metal'),
]
SKIN = dict(T_C=33.0, b=1300.0, b_al=math.sqrt(167.0 * 2700.0 * 896.0),
            note='contact temperature of two half-spaces: (b_metal T_metal + b_skin T_skin) / (b_metal + b_skin), b = sqrt(k rho c); skin 33 C and b = 1300 W s^0.5/m2/K are INFERRED typical values')
def comfort_level(T_C):
    for c in COMFORT:
        if T_C < c['below_C']: return c['level']
def contact_temp(T_C): return (SKIN['b_al'] * T_C + SKIN['b'] * SKIN['T_C']) / (SKIN['b_al'] + SKIN['b'])

POI = dict(eta=0.010, note='INFERRED: top-to-bottom temperature difference across the barrel = eta x local excess temperature (the top of a hot '
           'horizontal cylinder sits in its own plume, and the gas block and piston are above the bore); curvature = alpha * eta * dT / D; '
           'muzzle angle = its integral over the free length ahead of the barrel nut; the muzzle points DOWN, so impact moves low')


# =============================================================================== schedules: run and summarise
def cooling_fit(t, y, Ta):
    """Time constants of a cool-down curve: time to fall to 1/e of the peak excess, and a late-time exponential fit."""
    t = np.asarray(t, float); y = np.asarray(y, float) - Ta
    i0 = int(np.argmax(y)); t = t[i0:] - t[i0]; y = y[i0:]
    if y[0] <= 1: return dict(peak_C=round(float(y[0] + Ta), 1), tau_1e_s=None, tau_late_s=None)
    e = y[0] / math.e
    tau1 = float(np.interp(e, y[::-1], t[::-1])) if y[-1] < e else None
    m = (y < 0.5 * y[0]) & (y > 0.05 * y[0]) & (y > 1.0)
    tau2 = float(-1.0 / np.polyfit(t[m], np.log(y[m]), 1)[0]) if m.sum() >= 4 else None
    return dict(peak_C=round(float(y[0] + Ta), 1), tau_1e_s=None if tau1 is None else round(tau1), tau_late_s=None if tau2 is None else round(tau2))

def time_below(t, y, thr):
    """First time after the peak at which y is below thr."""
    t = np.asarray(t); y = np.asarray(y); i0 = int(np.argmax(y))
    if y[i0] < thr: return 0.0
    idx = np.where(y[i0:] < thr)[0]
    return round(float(t[i0 + idx[0]]), 1) if len(idx) else None

def run_schedule(sc, cool_s, geo=None, n_fire=104, n_cool=64, dt=None, **kw):
    sim = Sim(geo if geo is not None else geometry_hk416(), **kw)
    shots = sc['shots']; t_fire = float(shots[-1]) + 0.2
    st = list(np.linspace(0, t_fire, n_fire)) + list(t_fire + np.geomspace(1.0, cool_s, n_cool))
    rows, snaps = run(sim, shots, t_fire + cool_s, st, dt=dt)
    return sim, rows, snaps, t_fire

def derive_effects(rows, Ta_C, U):
    """Per-sample effect values from the probe rows (the same formulas hk416-heat.js uses)."""
    Ta = Ta_C + K0; out = []
    for r in rows:
        m = mirage_sight(r['q_line_barrel_W_m'], r['q_line_handguard_W_m'], r['exposed_outer'] - Ta_C, r['handguard_top_max'] - Ta_C, Ta, U)
        Tmax = max(r['barrel_max_outer'], r['gas_block'], r['flash_hider'])
        out.append(dict(t=r['t'], mirage_dn=m['dn'], mirage_height_m=m['height'], mirage_jitter_moa=m['jitter_moa'], mirage_steady_moa=m['steady_moa'],
                        mirage_strength=m['strength'], mirage_rise_m_s=m['rise_speed'],
                        glow_cd_m2=float(np.interp(Tmax, GLOW_T, GLOW_L)) if Tmax >= GLOW_T[0] else 0.0,
                        comfort=comfort_level(r['handguard_hand']), contact_C=contact_temp(r['handguard_hand']),
                        cookoff_time_s=cookoff_time(r['chamber_wall'], Ta_C)))
    return out
GLOW_L = [planck_luminance(tc + K0)[0] for tc in GLOW_T]
GLOW_RGB = [planck_luminance(tc + K0)[1] for tc in GLOW_T]

EFFECT_KEYS = ('mirage_dn', 'mirage_height_m', 'mirage_jitter_moa', 'mirage_steady_moa', 'mirage_strength', 'glow_cd_m2', 'comfort', 'contact_C', 'cookoff_time_s')
def sig(x, n=4):
    if x is None or (isinstance(x, float) and (math.isinf(x) or math.isnan(x))): return None
    return float('%.*g' % (n, x))


# =============================================================================== runtime export (hk416-heat.js reads this block)
RT_GRID = dict(dz_mm=5.0, nr=3, dt=0.05)
def export_runtime():
    """Everything hk416-heat.js needs: the same model on a coarser grid (5 mm stations, 3 radial cells), as plain arrays."""
    geo = geometry_hk416(dz_mm=RT_GRID['dz_mm'], nr=RT_GRID['nr']); s = Sim(geo); p = s.p
    L = lambda a, n=12: [float('%.*g' % (n, float(x))) for x in np.asarray(a).ravel()]
    I = lambda a: [int(x) for x in np.asarray(a).ravel()]
    Bm = lambda a: [1 if x else 0 for x in np.asarray(a).ravel()]
    ex = geo['exposed'] & (geo['z_mm'] < 349.0)
    z = geo['z_mm']; sb = z - geo['breech_mm']
    R = dict(
        note='generated by sim.py; arrays are row-major [station][radial cell]; SI units, kelvin inside',
        nz=geo['nz'], nr=geo['nr'], dt=min(RT_GRID['dt'], s.dt_max), dt_max=s.dt_max, coef_refresh_s=0.5,
        z_mm=L(z, 6), dz=L(s.dz), r_out=L(s.ro), r_in=L(geo['r_in_mm'] * 1e-3),
        M=L(s.M), Gr=L(s.Gr), Ga=L(s.Ga), As=L(s.As),
        m_exp=Bm(s.m_exp), m_hg=Bm(s.m_hg), m_gb=Bm(s.m_gb), b2h=I(s.b2h), hgi=I(s.hgi), hg_dz=L(s.hg_dz), hg_M=L(s.hg_M), hg_Ga=L(s.hg_Ga),
        G_bn=L(s.G_bn), G_up=L(s.G_up), G_gb=L(s.G_gb), G_case=L(s.G_case), nh=I(s.nh), pist=I(s.b2h[s.pist]), eps_gap=L(s.eps_gap),
        Eg=L(s.Eg), Teff=L(s.Teff), Efix=L(s.Efix), q_gb=float(s.q_gb), q_piston=float(s.q_piston),
        w_chamber=L(s.w_ch), mask=dict(throat=Bm((sb >= 45) & (sb < 70)), hg=Bm(geo['hg']), ex=Bm(ex), neck=Bm((z >= 270) & (z < 294)), free=Bm(s.free)),
        i_hand=int(np.argmin(np.abs(z[s.hgi] - geo['hand_z_mm']))), hand_z_mm=geo['hand_z_mm'],
        p={k: v for k, v in p.items() if v is not None},
        steel=dict(T0_K=float(_TT[0]), dT=10.0, h=L(np.interp(np.arange(_TT[0], _TT[-1] + 0.01, 10.0), _TT, _HH), 9), k0=42.7, k1=-0.0165, kmin=27.0),
        al=dict(c0=896.0, c1=0.45), TREF=TREF, K0=K0, SIGMA=SIGMA, G0=G0,
        cookoff=COOKOFF, mv=MV, comfort_C=[c['below_C'] for c in COMFORT[:-1]], comfort_names=[c['name'] for c in COMFORT], skin=SKIN, poi=dict(eta=POI['eta']),
        glow=dict(T_C=GLOW_T, cd_m2=L(GLOW_L, 12), rgb=GLOW_RGB, dark_C=525.0), mirage=MIRAGE,
        marks_mm=geo['marks'], breech_mm=geo['breech_mm'], muzzle_mm=geo['muzzle_mm'],
    )
    return R

def reference_case(shots, t_end, n_samples, ambient_C, wind):
    """A run on the runtime grid with the runtime's time step: the Python side of the JS parity test."""
    geo = geometry_hk416(dz_mm=RT_GRID['dz_mm'], nr=RT_GRID['nr']); sim = Sim(geo, ambient_C=ambient_C, wind=wind)
    dt = min(RT_GRID['dt'], sim.dt_max)
    st = [round(float(x), 6) for x in np.linspace(0, t_end, n_samples)]
    rows, snaps = run(sim, shots, t_end, st, dt=dt)
    eff = derive_effects(rows, ambient_C, wind)
    keys = [k for k in rows[0] if k not in ('t', 'shots')]
    return dict(ambient_C=ambient_C, wind_m_s=wind, dt=dt, t_end=t_end, shot_times_s=[float(x) for x in shots], sample_times_s=st,
                probes={k: [float(r[k]) for r in rows] for k in keys}, shots=[int(r['shots']) for r in rows],
                effects={k: [None if (isinstance(e[k], float) and math.isinf(e[k])) else e[k] for e in eff] for k in EFFECT_KEYS},
                final_outer_C=[float(x) for x in sim.T[:, -1] - K0], final_bore_C=[float(x) for x in sim.T[:, 0] - K0], final_handguard_C=[float(x) for x in sim.Thg - K0],
                energy_J=dict(deposited=sim.E_in, lost=sim.E_out, stored=sim.energy() - sim.E0))


# =============================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--validate', action='store_true'); ap.add_argument('--quick', action='store_true')
    ap.add_argument('--no-plots', action='store_true')
    a = ap.parse_args()
    t00 = time.time()
    cyc = P('cyclic_rpm')
    out = dict(model='HK416 D14.5RS barrel and handguard heating', generated_by='heat/sim.py', credit='carpetshark',
               frame='z_mm is the asset frame: +Z towards the muzzle, 0 at the upper receiver front face (barrel breech at -5 mm)',
               units=dict(temperature='deg C', time='s', length='mm unless named _m'))
    out['parameters'] = {k: dict(value=v[0], unit=v[1], source=v[2]) for k, v in PARAMS.items()}
    out['parameters']['k_steel'] = dict(value='42.7 - 0.0165*T_C, floor 27', unit='W/m/K', source='linear fit to ASM handbook 4140 (42.7 at 100 C, 33 at 600 C)')
    out['parameters']['c_steel'] = dict(value='EN 1993-1-2 curve', unit='J/kg/K', source='Eurocode 3 part 1-2 specific heat of carbon steel, incl. the 735 C transformation peak; 440 at 20 C')
    out['parameters']['c_al'] = dict(value='896 + 0.45*(T_C - 25)', unit='J/kg/K', source='handbook 6061 (896 at 25 C, about 1020 at 300 C)')

    # ---------------- heat per shot from the interior ballistics
    SH = shot_heat(P('bore_heat_scale')); s0 = Sim(geometry_hk416())
    bt = SH['bore_total_J']
    out['shot_heat'] = dict(
        method='Dittus-Boelter Nu = 0.023 Re^0.8 Pr^0.4 on the gas state of ../action/action.json (pressure, gas temperature, bullet travel and speed, Lagrange velocity profile), '
               '1D conduction into the wall; blowdown continued to 1.05 atm',
        s_from_bolt_face_mm=[round(float(x) * 1e3, 1) for x in SH['s']],
        J_per_m_cold=[round(float(x), 1) for x in SH['J_per_m_ref']], J_per_m_at_600K=[round(float(x), 1) for x in SH['J_per_m_600K']],
        J_per_m_at_900K=[round(float(x), 1) for x in SH['J_per_m_900K']], T_eff_K=[round(float(x), 1) for x in SH['Teff']],
        friction_J_per_m=[round(float(x), 1) for x in SH['friction_J_per_m']],
        peak_flux_MW_m2=[round(float(x), 1) for x in SH['peak_flux_MW_m2']], peak_surface_C_cold=[round(float(x), 1) for x in SH['peak_surface_C']],
        linear_in_wall_temperature_max_error=round(SH['linear_fit_max_error'], 4),
        bore_J=dict(cold_bore=round(bt['cold'], 1), bore_at_600K=round(bt['at_600K'], 1), bore_at_900K=round(bt['at_900K'], 1),
                    while_bullet_in_bore=round(bt['in_bore_phase_cold'], 1), friction_and_engraving=round(bt['friction'], 1)),
        action_json_loss_factor_J=round(SH['action_loss_factor_J'], 1),
        action_json_loss_factor_note='action.json assumes heat loss while the bullet is in the bore = loss_factor x work on bullet and gas; compare bore_J.while_bullet_in_bore',
        chamber_J=round(float(s0.Eg[(s0.g['z_mm'] - s0.g['breech_mm']) * 1e-3 < P('case_len_m')].sum()), 1),
        chamber_through_case_estimate_f=round(SH['f_chamber'], 3),
        gas_cylinder_wall_J=round(SH['q_cylinder_J'], 1), gas_cylinder_inflow_mg=round(SH['cylinder_inflow_mg'], 1),
        gas_block_J=round(s0.q_gb, 1), piston_J=round(s0.q_piston, 1), port_J=P('q_port_J'), flash_hider_J=P('q_flash_hider_J'),
        t_exit_ms=round(SH['t_exit_ms'], 3), blowdown_end_ms=round(SH['blowdown_end_ms'], 2))
    tot = float(s0.Eshot.sum()) + s0.q_gb + s0.q_piston + P('q_flash_hider_J')
    out['shot_heat'].update(total_cold_gun_J=round(tot, 1), propellant_energy_J=round(P('charge_mass_g') * P('propellant_energy_J_per_g')),
                            bullet_kinetic_J=round(0.5 * P('bullet_mass_g') * 1e-3 * P('muzzle_velocity_m_s') ** 2),
                            fraction_of_propellant_energy=round(tot / (P('charge_mass_g') * P('propellant_energy_J_per_g')), 3))
    print('heat per shot, cold gun: bore %.0f J (%.0f J while the bullet is in the bore; action.json loss_factor implies %.0f J), chamber %.0f J, gas block %.0f J, piston %.0f J, total %.0f J = %.1f %% of the charge'
          % (bt['cold'], bt['in_bore_phase_cold'], SH['action_loss_factor_J'], out['shot_heat']['chamber_J'], s0.q_gb, s0.q_piston, tot, 100 * out['shot_heat']['fraction_of_propellant_energy']))

    # ---------------- validation
    print('validation: NSWC Crane M4A1 chamber temperatures (Marsh 2006)')
    val = dict()
    val['f_chamber_used'] = P('f_chamber'); val['g_chamber_case_used'] = P('g_chamber_case')
    val['fit_scan'] = marsh_scan()
    val['marsh_assumed_magazine_change_s'] = 20.0
    for r in val['fit_scan']: print('  f_chamber %.2f  g_chamber_case %.2f W/K : first-sequence rms %.1f C, bias %.1f C' % (r['f_chamber'], r['g_chamber_case'], r['rms_C'], r['bias_C']))
    e2 = marsh_errors(None, 'second_model_C', 'second_measured_C')
    val['marsh_first_sequence_error_C'] = dict(rms=val['fit_scan'][0]['rms_C'], bias=val['fit_scan'][0]['bias_C'], note='14 points x 2 barrel profiles; f_chamber was fitted to these')
    val['marsh_second_sequence_error_C'] = dict(rms=round(e2[0], 1), bias=round(e2[1], 1), note='magazines 8 to 14 after the reload pause, 14 points x 2 barrel profiles, NOT used in the fit')
    print('  second sequence (held out): rms %.1f C, bias %.1f C' % e2)
    for heavy in (False, True):
        r = validate_marsh(None, heavy); val['marsh_' + ('socom' if heavy else 'government')] = r
        for k, v in r.items(): print('  %-6s %-10s model %s | %s\n  %17s meas  %s | %s' % ('SOCOM' if heavy else 'gov', k, v['model_C'], v['second_model_C'], '', v['measured_C'], v['second_measured_C']))
    print('validation: fire to destruction (M4A1 barrels; nothing fitted)')
    r = validate_burst(False, 'colt'); val['destruction_colt'] = r; print('   government barrel', json.dumps(r['marks']))
    val['destruction_colt_socom'] = validate_burst(True, 'colt')
    print('   SOCOM barrel', json.dumps(val['destruction_colt_socom']['marks']), 'max at 911 rounds:', [b for a_, b in zip(val['destruction_colt_socom']['trace']['rounds'], val['destruction_colt_socom']['trace']['barrel_max_outer_C']) if a_ >= 900][:1])
    val['destruction_published'] = dict(
        colt_video='Colt test, M4 on automatic, magazines changed as fast as possible: barrel ruptured at 535 rounds after about two minutes (1 min 51 s in the earlier build\'s notes); heavy-barrel M4A1: 911 rounds, then the gas tube failed, barrel intact (New York Times At War blog, 12 Jan 2010, as summarised by AccurateShooter and others)',
        windham='J. Windham, Fire to Destruction Test of 5.56mm M4A1 Carbine and M16A2 Rifle Barrels, AMSTA-AR-ES-96-2, 1996 (DTIC ADA317929): M16A2 barrel ruptured at 491 rounds, M4A1 at 540 to 596 (figures from secondary accounts; the report itself could not be re-read for this build)',
        rupture_temperature='817 C (1090 K) is the simulated rupture temperature of a Purdue thesis (AAI30501545, 548 rounds, 0.092 m from the breech); 737 C is quoted from a 1996 Army message as weak enough to burst. Both are secondary; the model reports when its hottest outer station passes each')
    val['rounds_to_180C_chamber'] = dict(assumed_rate_rpm=90, m4_government=rounds_to_cookoff_point(geometry_m4a1(False)), m4a1_socom=rounds_to_cookoff_point(geometry_m4a1(True)),
                                         hk416=rounds_to_cookoff_point(geometry_hk416()),
                                         m4_government_at_45rpm=rounds_to_cookoff_point(geometry_m4a1(False), 45.0), hk416_at_45rpm=rounds_to_cookoff_point(geometry_hk416(), 45.0),
                                         published='TM 9-1005-319-10: 140 rounds fired rapidly and continuously bring an M16A2 barrel to the cook-off point (150 for the M4 and 180 for the M4A1 in later editions, from the earlier build\'s notes); the TM gives neither the rate nor the temperature, so 90 rounds/min and 180 C are INFERRED')
    print('   rounds to a 180 C chamber wall:', json.dumps({k: v for k, v in val['rounds_to_180C_chamber'].items() if k != 'published'}))
    out['validation'] = val
    if a.validate: return

    # ---------------- schedules
    geo = geometry_hk416(); Ta_C = P('ambient_C'); U = P('wind_m_s')
    out['geometry'] = dict(z_mm=[round(float(x), 2) for x in geo['z_mm']], r_out_mm=[float(x) for x in geo['r_out_mm']], r_in_mm=[float(x) for x in geo['r_in_mm']],
                           source='../model/build.py build_barrel() and P; barrel extension radius and bore radii as noted in sim.py',
                           breech_mm=geo['breech_mm'], muzzle_mm=geo['muzzle_mm'], marks_mm=geo['marks'],
                           handguard_z_mm=[round(float(x), 2) for x in geo['z_mm'][geo['hg_cells']]],
                           socket_hand_left_mm=dict(x=0.0, y=round(BP['rail_bot'], 1), z=110.0),
                           barrel_steel_mass_kg=round(float(s0.M.sum()), 3), handguard_mass_kg=round(float(s0.hg_M.sum()), 3),
                           shot_heat_J_per_station_cold=[round(float(x), 2) for x in s0.Eshot])
    out['schedules'] = {}
    cool_s = 600.0 if a.quick else 5400.0
    for sc in schedules(cyc):
        t0 = time.time()
        sim, rows, snaps, t_fire = run_schedule(sc, cool_s)
        eff = derive_effects(rows, Ta_C, U)
        tt = [r['t'] for r in rows]
        keys = [k for k in rows[0] if k not in ('t', 'shots')]
        nopeak = ('barrel_max_z_mm', 'q_line_barrel_W_m', 'q_line_handguard_W_m', 'cookoff_damage', 'poi_bow_moa', 'mv_delta_m_s', 'mv_delta_next_m_s')
        peak = {k: round(max(r[k] for r in rows), 1) for k in keys if k not in nopeak}
        peak['mirage_strength'] = round(max(e['mirage_strength'] for e in eff), 3); peak['mirage_height_m'] = round(max(e['mirage_height_m'] for e in eff), 2)
        peak['mirage_jitter_moa'] = round(max(e['mirage_jitter_moa'] for e in eff), 2)
        peak['poi_bow_moa'] = round(min(r['poi_bow_moa'] for r in rows), 2)
        peak['mv_delta_m_s'] = round(max(r['mv_delta_m_s'] for r in rows), 2)
        peak['handguard_contact_C'] = round(max(e['contact_C'] for e in eff), 1)
        i_end = int(np.searchsorted(tt, t_fire)) - 1
        cool = {}
        for k in ('chamber_wall', 'barrel_max_outer', 'under_handguard_outer', 'gas_block', 'exposed_outer', 'flash_hider', 'handguard_hand', 'barrel_mean'):
            c = cooling_fit(tt, [r[k] for r in rows], Ta_C)
            c['t_peak_s'] = round(tt[int(np.argmax([r[k] for r in rows]))], 1)
            cool[k] = c
        hh = [r['handguard_hand'] for r in rows]; cw = [r['chamber_wall'] for r in rows]; bm = [r['barrel_max_outer'] for r in rows]
        thr = dict(chamber_below_170C_s=time_below(tt, cw, COOKOFF['caution_C']),
                   handguard_hand_below_60C_s=time_below(tt, hh, 60.0), handguard_hand_below_51C_s=time_below(tt, hh, 51.0),
                   handguard_hand_below_48C_s=time_below(tt, hh, 48.0), handguard_hand_below_43C_s=time_below(tt, hh, 43.0),
                   barrel_below_60C_s=time_below(tt, bm, 60.0), barrel_below_150C_s=time_below(tt, bm, 150.0))
        def first_above(key, v):
            for r in rows:
                if r[key] >= v: return dict(t_s=round(r['t'], 1), rounds=int(np.searchsorted(sc['shots'], r['t'], side='right')))
            return None
        onset = dict(handguard_hand_43C=first_above('handguard_hand', 43.0), handguard_hand_48C=first_above('handguard_hand', 48.0),
                     handguard_hand_51C=first_above('handguard_hand', 51.0), handguard_hand_60C=first_above('handguard_hand', 60.0),
                     handguard_hand_70C=first_above('handguard_hand', 70.0),
                     chamber_170C_cookoff_caution=first_above('chamber_wall', COOKOFF['caution_C']), chamber_220C_cookoff_danger=first_above('chamber_wall', COOKOFF['danger_C']),
                     glow_dark_525C=first_above('barrel_max_outer', 525.0), barrel_737C=first_above('barrel_max_outer', 737.0))
        ser = dict(t=[round(x, 2) for x in tt], shots=[int(r['shots']) for r in rows])
        for k in keys:
            if k == 'barrel_max_z_mm': continue
            ser[k] = [sig(r[k], 4) if k in ('cookoff_damage', 'poi_bow_moa', 'mv_delta_m_s', 'mv_delta_next_m_s') else round(r[k], 1) for r in rows]
        for k in EFFECT_KEYS: ser[k] = [e[k] if k == 'comfort' else sig(e[k], 4) for e in eff]
        out['schedules'][sc['id']] = dict(
            title=sc['title'], rounds=len(sc['shots']), fire_duration_s=round(t_fire, 1), cool_down_s=cool_s,
            mean_rate_rpm=round(len(sc['shots']) / max(t_fire, 1e-9) * 60, 1),
            peak=peak, at_cease_fire={k: round(rows[i_end][k], 2) for k in keys if not k.startswith('q_line')},
            onset=onset, cooling=cool, time_from_start_until=thr,
            energy_J=dict(deposited=round(sim.E_in), lost_to_air_and_cases=round(sim.E_out), carried_out_by_cases=round(sim.E_case_out), stored=round(sim.energy() - sim.E0),
                          balance_error=round(sim.E_in - sim.E_out - (sim.energy() - sim.E0), 2)),
            series=ser,
            fields=dict(t=[s_['t'] for s_ in snaps][::8], z_mm='geometry.z_mm', handguard_z_mm='geometry.handguard_z_mm',
                        outer_C=[[float(x) for x in s_['outer']] for s_ in snaps][::8], bore_C=[[float(x) for x in s_['bore']] for s_ in snaps][::8],
                        handguard_C=[[float(x) for x in s_['handguard']] for s_ in snaps][::8]),
            shot_times_s=[round(float(x), 3) for x in sc['shots']])
        print('%-20s %4d rds %6.0f s | chamber %4.0f  throat bore %4.0f  barrel max %4.0f  gas block %4.0f  FH %4.0f  hand %4.0f C  bow %5.2f MOA  dv %4.1f m/s | energy err %.2f J | %.0f s cpu'
              % (sc['id'], len(sc['shots']), t_fire, peak['chamber_wall'], peak['throat_bore'], peak['barrel_max_outer'], peak['gas_block'], peak['flash_hider'], peak['handguard_hand'],
                 peak['poi_bow_moa'], peak['mv_delta_m_s'], out['schedules'][sc['id']]['energy_J']['balance_error'], time.time() - t0))

    # ---------------- effect tables
    eff = dict()
    eff['glow'] = dict(note='grey body, emissivity 0.85; luminance from Planck x CIE 1931 y-bar (Wyman et al. 2013 fits); sRGB chromaticity normalised to max 1',
                       table=[dict(T_C=tc, luminance_cd_m2=float('%.3g' % GLOW_L[i]), rgb=GLOW_RGB[i]) for i, tc in enumerate(GLOW_T)],
                       dark_adapted_threshold_C=525, threshold_note='Draper point, 525 C (798 K): the classical limit of visible incandescence in darkness')
    eff['mirage'] = dict(
        note='two line plumes: above the exposed barrel and above the handguard top; values on the sight line %.1f mm above the bore' % (MIRAGE['sight_y'] * 1e3),
        constants=MIRAGE,
        formula=dict(F='g Q / (rho cp Ta)', dT='min(2.6 F^(2/3) Ta / (g y), 0.5 dT_surface); cross-wind U > w: min(.., F Ta / (g U y))', w='1.8 F^(1/3)',
                     dn='0.0796 (1/Ta - 1/(Ta + dT))', half_width='0.156 y', height='y where dT = 3 K',
                     jitter_rad='0.3 dn sqrt(2 sqrt(pi) L / b) exp(-(U / 0.35 w)^2)', steady_rad='dn L / y exp(-(U / 0.35 w)^2)',
                     strength='dn at 30 mm above the hotter source / (0.0796 / Ta) = dT / (Ta + dT)'),
        table=[])
    for src, D in (('exposed_barrel', 2 * MIRAGE['barrel_r']), ('handguard', 0.060)):
        for U_ in (0.0, 1.0, 3.0):
            for tc in (40, 60, 80, 100, 150, 200, 300, 400, 500, 600, 700):
                if src == 'handguard' and tc > 200: continue
                h = float(h_cylinder(D, tc + K0, Ta_C + K0, U_))
                Q = h * (math.pi * D if src == 'exposed_barrel' else P('hg_perim_out_m') * 0.5) * (tc - Ta_C)
                y = MIRAGE['sight_y'] - (MIRAGE['barrel_r'] if src == 'exposed_barrel' else MIRAGE['hg_top_y'])
                m = mirage(Q, Ta_C + K0, U_, y, MIRAGE['len_barrel'] if src == 'exposed_barrel' else MIRAGE['len_hg'], tc - Ta_C)
                eff['mirage']['table'].append(dict(source=src, wind_m_s=U_, surface_C=tc, h_W_m2K=round(h, 1), Q_W_per_m=round(Q, 1), dT_K=round(m['dT'], 2),
                                                   dn=float('%.3g' % m['dn']), plume_height_m=round(m['height'], 3),
                                                   rise_speed_m_s=round(m['rise_speed'], 3), jitter_moa=round(m['jitter_moa'], 3), steady_moa=round(m['steady_moa'], 3)))
    eff['comfort'] = dict(position='socket_hand_left: z = 110 mm, bottom rail', levels=COMFORT, skin=SKIN,
                          sources='ISO 13732-1:2006, burn thresholds for bare skin on uncoated metal: 1 s 65 to 70 C, 10 s about 55 C, 1 min 51 C, 10 min 48 C, 8 h 43 C; MIL-STD-1472 (metal: momentary contact 60 C, prolonged 49 C)',
                          note='thresholds are for bare skin on bare metal (hard anodising is too thin to help); gloves or polymer rail covers raise them by tens of kelvin')
    eff['cookoff'] = dict(model='the brass case of the chambered round follows the chamber wall through g_chamber_case (time constant c_case/g = %.1f s); the propellant on the case wall fires when the integral of dt / induction(T_case) reaches 1' % (P('c_case_J_K') / P('g_chamber_case')),
                          induction='t1 exp(E/R (1/T - 1/T1))', constants=COOKOFF, inferred=True,
                          anchors=['170 C, 600 s: smokeless (nitrocellulose) propellant self-ignites at about 160 to 200 C on slow heating (handbook range; INFERRED choice of point)',
                                   '220 C, 10 s: TM 9-1005-319-10 warns that a round left in a barrel at the cook-off point may fire in as little as 10 seconds (INFERRED temperature)'],
                          checks=['NSWC Crane (Marsh 2006, slide 8): rounds soaked in a 330 F (166 C) chamber for 15, 30 and 60 s were then fired for pressure; none is reported to have cooked off. Model: %.0f s at 166 C' % cookoff_time(166.0),
                                  'Marsh 2006, slide 2: M16-family chambers reach 400 F (204 C) in extreme use. Model at 204 C: %.0f s' % cookoff_time(204.0)],
                          table=[dict(chamber_C=tc, time_to_cookoff_s=(None if math.isinf(cookoff_time(tc)) else round(cookoff_time(tc), 1))) for tc in (160, 170, 180, 190, 200, 210, 220, 240, 260, 300, 350, 400)])
    eff['poi_shift'] = dict(
        bow=dict(method=POI['note'], eta=POI['eta'], alpha_steel=P('alpha_steel'), inferred=True, sign='negative = impact low',
                 source='mechanism: thermal bow of a beam with a linear temperature difference across it (Timoshenko, thermal stresses in beams; curvature = alpha dT / depth); the 1 % asymmetry is a guess, not a measurement'),
        velocity=dict(method='the propellant of the chambered round follows the case with a %.0f s lag (INFERRED: conduction into a 9 mm bed of grains); muzzle velocity rises %.2f m/s per K of propellant temperature above 25 C, up to %.0f C' % (COOKOFF['tau_prop_s'], MV['m_s_per_K'], MV['T_max_C']),
                      constants=MV, source='Marsh 2006 slide 8 pressures (65,172 psi after 15 s at 200 F; 85,662 psi after 60 s at 330 F, lot BLH03M032) with v ~ p^0.4 (INFERRED exponent)',
                      use='pass 850 + mv_delta to HK416Ballistics.fire({muzzleVelocity}) to get the change of drop at any range'),
        mirage=dict(method='the optical shift of the target image through the plume is series mirage_steady_moa; it moves the picture, not the bullet'))
    out['effects'] = eff

    # ---------------- sensitivity on the manual's schedule
    sens = {}
    sc = [s_ for s_ in schedules(cyc) if s_['id'] == 'manual_250_in_3min'][0]
    gkeys = [k for k in PARAMS if k.startswith('g_') and k != 'g_chamber_case']
    for name, kw in (('still_25C', {}), ('wind_3_m_s', dict(wind=3.0)), ('wind_8_m_s', dict(wind=8.0)), ('ambient_45C', dict(ambient_C=45.0)), ('ambient_minus20C', dict(ambient_C=-20.0)),
                     ('bore_heat_minus_20pct', dict(over=dict(bore_heat_scale=0.8))), ('bore_heat_plus_20pct', dict(over=dict(bore_heat_scale=1.2))),
                     ('chamber_as_drawn_in_build_py', dict(geo=geometry_hk416(variant='as_drawn'))), ('heavy_barrel_under_handguard', dict(geo=geometry_hk416(variant='heavy'))), ('no_vent_loss', dict(over=dict(hg_vent_fraction=0.0))),
                     ('no_round_cooling', dict(over=dict(g_chamber_case=0.0))),
                     ('contacts_x0.5', dict(over={k: 0.5 * P(k) for k in gkeys})), ('contacts_x2', dict(over={k: 2.0 * P(k) for k in gkeys}))):
        sim, rows, _, t_fire = run_schedule(sc, 900.0 if not a.quick else 300.0, n_fire=60, n_cool=40, **kw)
        tt = [r['t'] for r in rows]
        sens[name] = dict(peak_chamber_wall_C=round(max(r['chamber_wall'] for r in rows), 1), peak_barrel_outer_C=round(max(r['barrel_max_outer'] for r in rows), 1),
                          peak_handguard_hand_C=round(max(r['handguard_hand'] for r in rows), 1),
                          barrel_max_at_15min_C=round(float(np.interp(900.0, tt, [r['barrel_max_outer'] for r in rows])), 1) if tt[-1] >= 900 else None)
        sens[name]['barrel_steel_mass_kg'] = round(float(sim.M.sum()), 3)
    out['sensitivity_manual_250_in_3min'] = sens
    print('sensitivity:', json.dumps(sens))

    # ---------------- runtime block and parity references
    R = export_runtime()
    refs = dict(
        manual_250_in_3min=reference_case(sched_uniform(250, 250.0 / 3.0), 600.0, 61, 25.0, 0.0),
        auto_mag_dumps_hot_windy=reference_case(sched_uniform(120, cyc, mag=30, reload_s=5.0), 240.0, 49, 40.0, 3.0))
    R['reference'] = refs
    # how far the runtime grid is from the full grid, on the manual's schedule
    full = out['schedules']['manual_250_in_3min']['series']; rr = refs['manual_250_in_3min']
    acc = {}
    for k in ('chamber_wall', 'throat_bore', 'barrel_max_outer', 'under_handguard_outer', 'exposed_outer', 'gas_block', 'handguard_hand', 'barrel_mean'):
        yf = np.interp(rr['sample_times_s'], full['t'], full[k]); d = np.array(rr['probes'][k]) - yf
        acc[k] = dict(max_abs_C=round(float(np.max(np.abs(d))), 1), peak_full_C=round(float(yf.max()), 1), peak_runtime_C=round(float(max(rr['probes'][k])), 1))
    R['accuracy_vs_full_grid'] = dict(case='manual_250_in_3min, 0 to 600 s', note='runtime grid %d x %d at dt %.3g s against the full grid %d x 4' % (R['nz'], R['nr'], R['dt'], len(geo['z_mm'])), probes=acc)
    print('runtime grid vs full grid:', json.dumps(acc))
    out['runtime'] = R
    out = _clean(out)
    with open(os.path.join(HERE, 'heat.json'), 'w') as f:
        json.dump(out, f, separators=(',', ':'), allow_nan=False)
    print('heat.json %.2f MB' % (os.path.getsize(os.path.join(HERE, 'heat.json')) / 1e6))
    if not a.no_plots:
        import plots as PL
        PL.make_all(out, HERE, SH)
    print('done in %.0f s' % (time.time() - t00))

def _clean(o):
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, np.ndarray): return _clean(o.tolist())
    if isinstance(o, (float, np.floating)): return None if (math.isnan(o) or math.isinf(o)) else float(o)
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o


if __name__ == '__main__':
    main()
