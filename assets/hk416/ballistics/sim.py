#!/usr/bin/env python3
"""HK416 D14.5RS external and terminal ballistics (sport / range simulation).

One command reproduces everything:

    python3 sim.py            # writes ballistics.json, plots/*.png, and the DATA block of hk416-ballistics.js

Options: --mv-m855 850 (m/s), --mv-mk262, --mv-m856, --temp, --pressure, --humidity, --altitude,
         --action-json PATH --action-key dotted.key  (take the M855 muzzle velocity from the action model)

Frame used here: x downrange from the muzzle crown, y up, z to the shooter's right. SI units throughout.
Facts and inferences are labelled in PARAMS[...]["source"]; README.md has the full table.
"""
import argparse, json, math, os, re, sys
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
G0 = 9.80665
GR = 6.479891e-5          # kg per grain
IN = 0.0254
FPS = 0.3048
YD = 0.9144
MOA = math.radians(1 / 60)
BC_SI = 703.0696          # kg/m^2 per lb/in^2
OMEGA_E = 7.292115e-5     # rad/s

# ----------------------------------------------------------------------------- drag functions
# Standard G7 and G1 drag functions (Cd versus Mach), BRL tables as distributed with JBM and
# py-ballisticcalc (checked against py_ballisticcalc/drag_tables.py on 2026-11-17).
G7 = np.array([
 (0.00,.1198),(0.05,.1197),(0.10,.1196),(0.15,.1194),(0.20,.1193),(0.25,.1194),(0.30,.1194),(0.35,.1194),
 (0.40,.1193),(0.45,.1193),(0.50,.1194),(0.55,.1193),(0.60,.1194),(0.65,.1197),(0.70,.1202),(0.725,.1207),
 (0.75,.1215),(0.775,.1226),(0.80,.1242),(0.825,.1266),(0.85,.1306),(0.875,.1368),(0.90,.1464),(0.925,.1660),
 (0.95,.2054),(0.975,.2993),(1.0,.3803),(1.025,.4015),(1.05,.4043),(1.075,.4034),(1.10,.4014),(1.125,.3987),
 (1.15,.3955),(1.20,.3884),(1.25,.3810),(1.30,.3732),(1.35,.3657),(1.40,.3580),(1.50,.3440),(1.55,.3376),
 (1.60,.3315),(1.65,.3260),(1.70,.3209),(1.75,.3160),(1.80,.3117),(1.85,.3078),(1.90,.3042),(1.95,.3010),
 (2.00,.2980),(2.05,.2951),(2.10,.2922),(2.15,.2892),(2.20,.2864),(2.25,.2835),(2.30,.2807),(2.35,.2779),
 (2.40,.2752),(2.45,.2725),(2.50,.2697),(2.55,.2670),(2.60,.2643),(2.65,.2615),(2.70,.2588),(2.75,.2561),
 (2.80,.2533),(2.85,.2506),(2.90,.2479),(2.95,.2451),(3.00,.2424),(3.10,.2368),(3.20,.2313),(3.30,.2258),
 (3.40,.2205),(3.50,.2154),(3.60,.2106),(3.70,.2060),(3.80,.2017),(3.90,.1975),(4.00,.1935),(4.20,.1861),
 (4.40,.1793),(4.60,.1730),(4.80,.1672),(5.00,.1618)])
G1 = np.array([
 (0.00,.2629),(0.05,.2558),(0.10,.2487),(0.15,.2413),(0.20,.2344),(0.25,.2278),(0.30,.2214),(0.35,.2155),
 (0.40,.2104),(0.45,.2061),(0.50,.2032),(0.55,.2020),(0.60,.2034),(0.70,.2165),(0.725,.2230),(0.75,.2313),
 (0.775,.2417),(0.80,.2546),(0.825,.2706),(0.85,.2901),(0.875,.3136),(0.90,.3415),(0.925,.3734),(0.95,.4084),
 (0.975,.4448),(1.0,.4805),(1.025,.5136),(1.05,.5427),(1.075,.5677),(1.10,.5883),(1.125,.6053),(1.15,.6191),
 (1.20,.6393),(1.25,.6518),(1.30,.6589),(1.35,.6621),(1.40,.6625),(1.45,.6607),(1.50,.6573),(1.55,.6528),
 (1.60,.6474),(1.65,.6413),(1.70,.6347),(1.75,.6280),(1.80,.6210),(1.85,.6141),(1.90,.6072),(1.95,.6003),
 (2.00,.5934),(2.05,.5867),(2.10,.5804),(2.15,.5743),(2.20,.5685),(2.25,.5630),(2.30,.5577),(2.35,.5527),
 (2.40,.5481),(2.45,.5438),(2.50,.5397),(2.60,.5325),(2.70,.5264),(2.80,.5211),(2.90,.5168),(3.00,.5133),
 (3.10,.5105),(3.20,.5084),(3.30,.5067),(3.40,.5054),(3.50,.5040),(3.60,.5030),(3.70,.5022),(3.80,.5016),
 (3.90,.5010),(4.00,.5006),(4.20,.4998),(4.40,.4995),(4.60,.4992),(4.80,.4990),(5.00,.4988)])
TABLES = {"G7": G7, "G1": G1}

def cd(model, mach):
    t = TABLES[model]
    return np.interp(mach, t[:, 0], t[:, 1])

# ----------------------------------------------------------------------------- atmosphere
def atmosphere(temp_c=None, pressure_hpa=None, humidity=0.0, altitude_m=0.0):
    """Air density (kg/m^3) and speed of sound (m/s). Defaults are the ICAO standard atmosphere at the given
    altitude. pressure_hpa is the station (absolute) pressure; humidity is relative, 0..1."""
    if temp_c is None:
        temp_c = 15.0 - 0.0065 * altitude_m
    if pressure_hpa is None:
        pressure_hpa = 1013.25 * (1 - 2.25577e-5 * altitude_m) ** 5.25588
    T = temp_c + 273.15
    es = 6.1121 * math.exp((18.678 - temp_c / 234.5) * (temp_c / (257.14 + temp_c)))  # Buck 1981, hPa
    pv = humidity * es
    rho = ((pressure_hpa - pv) * 100) / (287.058 * T) + (pv * 100) / (461.495 * T)
    x = pv / pressure_hpa                              # mole fraction of water vapour
    molar = 0.0289647 * (1 - x) + 0.018015 * x
    gamma = (7 + x) / (5 + x)
    c = math.sqrt(gamma * 8.314462 * T / molar)
    return {"temp_c": temp_c, "pressure_hpa": pressure_hpa, "humidity": humidity, "altitude_m": altitude_m,
            "rho": rho, "c": c, "vapour_pressure_hpa": pv, "saturation_hpa": es}

# ----------------------------------------------------------------------------- parameters
RIFLE = {
    "name": "HK416 D14.5RS",
    "barrel_length_m": 0.3683,
    "twist_m": 7 * IN, "twist_in": 7.0, "twist_hand": "right",
    "sight_height_m": 0.0655,      # aperture centre and front post tip above the bore (hk416.glb)
    "sight_radius_m": 0.3640,      # rear aperture z=-127.4 mm to front post z=+236.6 mm (hk416.glb)
    "eye_to_muzzle_m": 0.6239,     # socket_ads_eye z=-260.6 mm to barrel crown z=+363.3 mm (hk416.glb)
    "eye_to_flash_hider_tip_m": 0.6586,
    "source": {
        "barrel_length_m": "fact: HK manual p.7 (14.5 in); model NOTES.md",
        "twist": "fact: HK manual p.7, 1 in 7 in right hand",
        "sight_height_m": "measured from hk416.glb: rear_sight_aperture centre and front_sight_post tip both y=65.5 mm, socket_ads_eye y=65.5 mm",
        "sight_radius_m": "measured from hk416.glb",
        "eye_to_muzzle_m": "measured from hk416.glb (barrel mesh ends z=363.3 mm; socket_muzzle at the flash hider tip z=398.0 mm)",
    },
}

AMMO = {
    "M855": {
        "label": "M855 ball, 62 gr, steel penetrator (SS109 type)",
        "mass_kg": 62 * GR, "mass_gr": 62, "diameter_m": 0.224 * IN, "length_m": 0.906 * IN,
        "bc_g7": 0.151, "bc_g1": 0.304,
        "mv": 850.0, "mv_sigma": 7.5,
        "group_es10_moa": 3.0,
        "core": "lead with a hardened steel penetrator of about 10 gr (0.65 g) in the nose",
        "sparks_on_steel": 0.8,
        "source": {
            "mass": "fact: M855 specification, 62 gr",
            "length_m": "recalled: 0.906 in, commonly published for the SS109/M855 bullet",
            "bc_g7": "recalled: 0.151, Bryan Litz / Applied Ballistics measured G7 (not re-verified today; consistent with G1 0.304 in the check below)",
            "bc_g1": "published: 0.304 (commonly listed military figure; 0.307 also quoted)",
            "mv": "fact: HK manual p.7, 2,790 ft/s (850 m/s) for the 14.5 in barrel (ammunition type not stated; taken as M855/SS109 class). Parameter; action/action.json should override it",
            "mv_sigma": "inferred: about 25 ft/s shot-to-shot standard deviation, typical of service ball",
            "group_es10_moa": "inferred: 10-shot extreme spread from a service carbine; range reports cluster around 2.5 to 4 MOA",
            "penetrator": "recalled, approximate",
            "sparks_on_steel": "inferred probability of a visible spark; steel-core ammunition is widely banned on steel ranges for sparks and plate damage",
        },
    },
    "Mk262": {
        "label": "Mk 262 Mod 1, 77 gr Sierra MatchKing OTM",
        "mass_kg": 77 * GR, "mass_gr": 77, "diameter_m": 0.224 * IN, "length_m": 0.994 * IN,
        "bc_g7": 0.190, "bc_g1": 0.372,
        "mv": 770.0, "mv_sigma": 4.5,
        "group_es10_moa": 1.5,
        "core": "lead, open-tip match jacket",
        "sparks_on_steel": 0.05,
        "source": {
            "mass": "fact: 77 gr Sierra MatchKing",
            "length_m": "recalled: 0.994 in (Sierra 77 gr MatchKing)",
            "bc_g7": "recalled: 0.190, Litz measured G7 for the 77 gr SMK (not re-verified today)",
            "bc_g1": "published: Sierra's 0.372 (above 2,500 ft/s)",
            "mv": "inferred: HK's 850 m/s scaled by the Mk 262 to M855 ratio seen in 14.5 in chronograph reports (about 2,620 against 2,900 ft/s)",
            "mv_sigma": "inferred: about 15 ft/s, match ammunition",
            "group_es10_moa": "inferred: 10-shot extreme spread from a chrome-lined 14.5 in service barrel; the ammunition alone shoots under 1 MOA from match barrels",
            "sparks_on_steel": "inferred: copper and lead on steel rarely spark",
        },
    },
    "M856": {
        "label": "M856 tracer, 63.7 gr",
        "mass_kg": 63.7 * GR, "mass_gr": 63.7, "diameter_m": 0.224 * IN, "length_m": 1.15 * IN,
        "bc_g7": 0.140, "bc_g1": 0.282,
        "mv": 810.0, "mv_sigma": 9.0,
        "group_es10_moa": 5.0,
        "core": "lead front core, tracer composition in the base",
        "sparks_on_steel": 1.0,
        "tracer": {
            "ignite_distance_m": 15.0, "full_bright_distance_m": 70.0, "burnout_distance_m": 800.0,
            "color_rgb": [1.0, 0.25, 0.08], "mass_loss_kg": 0.25e-3,
            "source": "recalled: specification asks for a visible trace from about 75 yd to at least 875 yd (800 m); red strontium-based composition. ignite_distance_m (dim trace start) and mass loss are inferred. Mass loss and base-burn drag change are not modelled",
        },
        "source": {
            "mass": "recalled: 63.7 gr",
            "length_m": "recalled: about 1.15 in",
            "bc_g7": "inferred: no trusted published figure; set a little below M855",
            "mv": "inferred: HK's 850 m/s scaled by the published 20 in velocities of M856 and M855 (about 2,870 against 3,020 ft/s)",
            "group_es10_moa": "inferred: tracers group worse than ball",
        },
    },
}

ZEROS = {
    "hk100yd": {"distance_m": 100 * YD, "label": "HK manual zero: 100 yd on the V notch (drum position 1)", "default": True},
    "hk200yd": {"distance_m": 200 * YD, "label": "HK drum diopter 2 (200 yd)"},
    "hk300yd": {"distance_m": 300 * YD, "label": "HK drum diopter 3 (300 yd)"},
    "hk400yd": {"distance_m": 400 * YD, "label": "HK drum diopter 4 (400 yd)"},
    "50_200":  {"distance_m": 50.0,  "label": "50 m near zero (the '50/200' zero)"},
    "25_300":  {"distance_m": 25.0,  "label": "25 m near zero (the '25/300' zero)"},
}
DEFAULT_ZERO = "hk100yd"

SHOOTER = {   # per-axis angular standard deviation of the aiming error, added in quadrature to the rifle's
    "bench":    {"sigma_moa": 0.0,  "source": "definition: rifle and ammunition only"},
    "aimed_supported": {"sigma_moa": 1.2, "source": "inferred upper bound from the US Army grouping standard (5 of 6 shots in a 4 cm circle at 25 m, about 5.5 MOA, prone supported) after removing the rifle's share"},
    "aimed":    {"sigma_moa": 4.0,  "source": "inferred: standing unsupported, iron sights, about three times the supported wobble"},
    "hip":      {"sigma_moa": 60.0, "source": "inferred: unsighted fire from the hip, 1 degree per axis. No published standard; tune for feel"},
}

TERMINAL = {
    "paper": {
        "hole_factor": 0.85, "grease_ring_factor": 1.0, "speed_loss_fraction": 0.0005,
        "source": "inferred: pointed bullets leave a hole smaller than calibre in target paper because the fibres close back (the reason scoring plugs exist); 0.85 is a typical ratio, not a measurement of this target stock",
    },
    "steel": {
        "density_kg_m3": 7850.0, "momentum_transfer": 1.0, "splash_half_angle_deg": 20.0,
        "fragment_speed_fraction": [0.35, 0.9], "fragment_count": 28, "fragment_size_m": [0.0002, 0.002],
        "fragment_drag_tau_s": 0.035, "ricochet_angle_deg": 12.0, "ricochet_width_deg": 3.0,
        "pit_threshold_mps": {"lead_core": 870.0, "steel_core": 640.0}, "pit_depth_per_mps_m": 4.0e-6,
        "real_world_min_distance_m": 91.0,
        "source": {
            "density": "fact: steel 7,850 kg/m^3",
            "momentum_transfer": "physics: the bullet shatters and its fragments leave along the plate face, so the plate takes the normal momentum once (coefficient about 1.0, within roughly 10 percent)",
            "splash_half_angle_deg": "published guidance from steel-target makers: splatter leaves within about 20 degrees of the plate face",
            "fragments": "inferred: speeds, count, sizes and the drag time constant are visual calibration",
            "ricochet": "inferred: below about 12 degrees from the plate face the bullet glances mostly intact",
            "pit_threshold_mps": "published guidance: makers rate AR500 for lead-core rifle impacts below about 2,850 ft/s (870 m/s) and forbid steel-core ammunition; the steel-core threshold and the depth slope are inferred",
            "real_world_min_distance_m": "published guidance: 100 yd minimum for rifle on steel. The game's 20 to 55 m plates are closer than any real range allows",
        },
    },
    "dirt": {
        "density_kg_m3": 1600.0, "strength_pa": 3.0e6, "drag_coefficient": 1.0, "tumble_area_factor": 2.5,
        "ricochet_angle_deg": 8.0, "ricochet_width_deg": 2.0, "ricochet_exit_ratio": 1.3,
        "ricochet_speed_loss_per_deg": 0.035, "ricochet_drag_scale": 3.0, "ricochet_scatter_deg": 3.0,
        "crater_k_m_per_j13": 0.0087, "plume_height_k_m_per_j13": 0.079, "plume_width_ratio": 0.5,
        "ejecta_speed_mps": [3.0, 9.0], "dust_linger_s": 1.6, "moisture": 0.1,
        "source": {
            "model": "Poncelet penetration: depth = m / (2 C rho A_eff) * ln(1 + C rho v^2 / R)",
            "density": "typical dry compacted soil or sand",
            "strength_pa, drag_coefficient, tumble_area_factor": "inferred; chosen so 5.56 mm ball stops in roughly 10 to 15 cm of packed sand, as commonly reported (one sandbag layer stops it)",
            "ricochet": "inferred from forensic literature ranges: critical angles for soil and sand are a few degrees up to about 10 to 15; exit angle steeper than entry; the bullet tumbles afterwards",
            "plume": "inferred visual calibration: a 1,500 J strike on dry dirt raises a puff roughly 0.9 m high and a 10 cm scar; scaled with energy^(1/3)",
        },
    },
    "berm": {"inherits": "dirt", "moisture": 0.25, "strength_pa": 2.0e6,
             "source": "inferred: looser, damper banked earth than the trodden ground"},
}

VISIBILITY = {
    "trace_min_range_m": 100.0, "trace_needs_magnification": 8.0,
    "vapour_humidity_threshold": 0.9, "vapour_max_opacity": 0.12, "vapour_life_s": 0.04,
    "glint_probability": 0.02,
    "source": "inferred from shooting practice: 'trace' is the refractive wake of the bullet, seen from behind through a spotting scope or magnified optic in good light, usually past 100 m. To the naked eye over iron sights a ball round is not visible. Condensation in the wake needs air close to saturation and is brief and faint. Values are visual calibration",
}

DEFAULT_ATMOS = dict(temp_c=15.0, pressure_hpa=1013.25, humidity=0.0, altitude_m=0.0)

# ----------------------------------------------------------------------------- trajectory
class Trajectory:
    def __init__(self, mass, bc, mv, elev, atmos, model="G7", wind=(0, 0, 0), coriolis=None, drag=True, t_max=4.0,
                 azimuth=0.0):
        self.mass, self.mv, self.atmos = mass, mv, atmos
        k = math.pi / 8 * atmos["rho"] / (bc * BC_SI) if drag else 0.0
        c = atmos["c"]; w = np.array(wind, float)
        om = np.zeros(3)
        if coriolis is not None:
            lat, az = math.radians(coriolis["latitude_deg"]), math.radians(coriolis["azimuth_deg"])
            om = OMEGA_E * np.array([math.cos(lat) * math.cos(az), math.sin(lat), -math.cos(lat) * math.sin(az)])
        def f(t, s):
            v = s[3:]; vr = v - w; sp = math.sqrt(vr @ vr)
            a = -k * cd(model, sp / c) * sp * vr
            a[1] -= G0
            a -= 2 * np.cross(om, v)
            return np.concatenate([v, a])
        s0 = [0, 0, 0, mv * math.cos(elev) * math.cos(azimuth), mv * math.sin(elev), mv * math.cos(elev) * math.sin(azimuth)]
        self.sol = solve_ivp(f, (0, t_max), s0, method="DOP853", dense_output=True, rtol=1e-10, atol=1e-10, max_step=0.004)
    def t_at_x(self, x):
        if x <= 0: return 0.0
        return brentq(lambda t: self.sol.sol(t)[0] - x, 0, self.sol.t[-1], xtol=1e-12)
    def at_x(self, x):
        t = self.t_at_x(x); s = self.sol.sol(t)
        v = float(np.linalg.norm(s[3:]))
        return {"t": t, "x": s[0], "y": s[1], "z": s[2], "v": v, "vx": s[3], "vy": s[4], "vz": s[5],
                "mach": v / self.atmos["c"], "energy": 0.5 * self.mass * v * v}

def traj(ammo, elev, atmos, mv=None, **kw):
    model = kw.pop("model", "G7")
    bc = kw.pop("bc", None) or (ammo["bc_g7"] if model == "G7" else ammo["bc_g1"])
    return Trajectory(ammo["mass_kg"], bc, mv or ammo["mv"], elev, atmos, model=model, **kw)

def zero_angle(ammo, dist_from_eye, atmos, mv=None, sight_h=None, e2m=None, **kw):
    """Bore elevation above the line of sight so the bullet crosses the sight line dist_from_eye metres from the eye."""
    h = RIFLE["sight_height_m"] if sight_h is None else sight_h
    x = dist_from_eye - (RIFLE["eye_to_muzzle_m"] if e2m is None else e2m)
    return brentq(lambda a: traj(ammo, a, atmos, mv, t_max=1.5, **kw).at_x(x)["y"] - h, 0.0, 0.03, xtol=1e-10)

def miller_sg(ammo, mv, atmos):
    d = ammo["diameter_m"] / IN; l = ammo["length_m"] / ammo["diameter_m"]; t = RIFLE["twist_in"] / d
    sg = 30 * ammo["mass_gr"] / (t * t * d ** 3 * l * (1 + l * l))
    sg *= (mv / FPS / 2800) ** (1 / 3)
    sg *= ((atmos["temp_c"] + 273.15) / 288.15) * (1013.25 / atmos["pressure_hpa"])
    return sg

def spin_drift(sg, tof):
    """Litz's empirical fit: drift (m, to the right for right-hand twist)."""
    return 1.25 * (sg + 1.2) * tof ** 1.83 * IN

# ----------------------------------------------------------------------------- terminal effects
def plate(radius, thickness=0.010, hinge_offset=None):
    m = TERMINAL["steel"]["density_kg_m3"] * math.pi * radius ** 2 * thickness
    s = radius if hinge_offset is None else hinge_offset          # hinge axis to plate centre
    I = 0.25 * m * radius ** 2 + m * s * s                        # disc about a horizontal axis in its plane
    return {"mass": m, "s": s, "I": I}

def plate_response(pl, p_normal, hit_height, lean_deg=2.0, damping=0.0):
    """Hinged plate resting lean_deg toward the shooter against a stop. Returns initial rate, whether it
    passes top dead centre, and the fall time to horizontal."""
    w0 = p_normal * hit_height / pl["I"]
    ke = 0.5 * pl["I"] * w0 * w0
    need = pl["mass"] * G0 * pl["s"] * (1 - math.cos(math.radians(lean_deg)))
    falls = ke > need
    out = {"omega0": w0, "plate_ke": ke, "energy_to_topple": need, "falls": bool(falls)}
    k = pl["mass"] * G0 * pl["s"] / pl["I"]
    th, w, t, dt = -math.radians(lean_deg), w0, 0.0, 2e-4
    while th < math.pi / 2 and t < 5:
        a = k * math.sin(th) - damping * w
        w += a * dt; th += w * dt; t += dt
        if th < -math.radians(lean_deg):       # back on the stop
            break
    out["fall_time"] = t if falls else None
    out["landing_rate"] = w if falls else None
    return out

def dirt_depth(ammo, v, kind="dirt"):
    d = dict(TERMINAL["dirt"]); d.update({k: v_ for k, v_ in TERMINAL[kind].items() if k not in ("inherits", "source")})
    A = math.pi * ammo["diameter_m"] ** 2 / 4 * d["tumble_area_factor"]
    C, rho, R = d["drag_coefficient"], d["density_kg_m3"], d["strength_pa"]
    return ammo["mass_kg"] / (2 * C * rho * A) * math.log(1 + C * rho * v * v / R)

def logistic(angle, centre, width):
    return 1 / (1 + math.exp((angle - centre) / width))

def sonic_crack(ammo, mach, miss, atmos):
    """Whitham N-wave at miss distance (m): peak overpressure (Pa) and duration (s)."""
    if mach <= 1: return None
    d, l, P0, c = ammo["diameter_m"], ammo["length_m"], atmos["pressure_hpa"] * 100, atmos["c"]
    b = mach * mach - 1
    dp = 0.53 * P0 * b ** 0.125 * d / (miss ** 0.75 * l ** 0.25)
    T = 1.82 * mach * miss ** 0.25 * d / (c * b ** 0.375 * l ** 0.25)
    return {"peak_pa": dp, "peak_db_spl": 20 * math.log10(dp / 20e-6), "duration_s": T,
            "cone_half_angle_deg": math.degrees(math.asin(1 / mach))}

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mv-m855", type=float); ap.add_argument("--mv-mk262", type=float); ap.add_argument("--mv-m856", type=float)
    ap.add_argument("--temp", type=float, default=DEFAULT_ATMOS["temp_c"]); ap.add_argument("--pressure", type=float, default=None)
    ap.add_argument("--humidity", type=float, default=0.0); ap.add_argument("--altitude", type=float, default=0.0)
    ap.add_argument("--action-json"); ap.add_argument("--action-key", default="muzzle_velocity_mps")
    ap.add_argument("--no-plots", action="store_true")
    a = ap.parse_args()
    mv_note = None
    if a.action_json and os.path.exists(a.action_json):
        v = json.load(open(a.action_json))
        for k in a.action_key.split("."): v = v[k]
        ratio = float(v) / AMMO["M855"]["mv"]
        for am in AMMO.values(): am["mv"] *= ratio          # keep the inferred ratios between loads
        mv_note = f"M855 muzzle velocity {float(v):.1f} m/s from {a.action_json}:{a.action_key}; other loads scaled by the same ratio"
    if a.mv_m855: AMMO["M855"]["mv"] = a.mv_m855
    if a.mv_mk262: AMMO["Mk262"]["mv"] = a.mv_mk262
    if a.mv_m856: AMMO["M856"]["mv"] = a.mv_m856
    atmos = atmosphere(a.temp, a.pressure, a.humidity, a.altitude)
    icao = atmosphere()

    out = {
        "meta": {
            "title": "HK416 D14.5RS external and terminal ballistics",
            "generator": "ballistics/sim.py", "credit": "carpetshark",
            "units": "SI: metres, seconds, kilograms, joules, newton-seconds, radians unless a key says otherwise (_deg, _moa, _mm, _hpa, _c)",
            "frame": "range tables: x downrange from the muzzle crown, y up, z to the shooter's right. Paths are relative to the line of sight (+ is high). poi_vs_poa distances are measured from socket_ads_eye",
            "muzzle_velocity_note": mv_note or "HK manual value for M855; see ammo.*.source.mv",
            "scope": "sport and range simulation: paper, steel plates, earth",
        },
        "atmosphere": atmos, "rifle": RIFLE, "zeros": ZEROS, "default_zero": DEFAULT_ZERO,
        "ammo": {}, "dispersion": {}, "terminal": {"params": TERMINAL}, "visibility": VISIBILITY, "validation": {},
    }

    ranges = sorted(set(list(range(0, 601, 25)) + [10, 15, 20, 35, 45, 55, 62]))
    game_d = [10, 15, 20, 25, 35, 45, 55, 62]
    wind10 = 10 * 0.44704
    h, e2m = RIFLE["sight_height_m"], RIFLE["eye_to_muzzle_m"]
    cache = {}
    for name, am in AMMO.items():
        sg = miller_sg(am, am["mv"], atmos)
        flat = traj(am, 0.0, atmos)
        windy = traj(am, 0.0, atmos, wind=(0, 0, wind10))
        cor = traj(am, 0.0, atmos, coriolis={"latitude_deg": 45, "azimuth_deg": 0})
        rows = []
        for r in ranges:
            s = flat.at_x(r); sw = windy.at_x(r); sc = cor.at_x(r)
            rows.append({"range_m": r, "velocity_mps": round(s["v"], 2), "mach": round(s["mach"], 4),
                         "energy_j": round(s["energy"], 1), "momentum_ns": round(am["mass_kg"] * s["v"], 4),
                         "tof_s": round(s["t"], 5), "drop_m": round(s["y"], 5),
                         "wind_drift_10mph_m": round(sw["z"], 5), "spin_drift_m": round(spin_drift(sg, s["t"]), 5),
                         "coriolis_right_m": round(sc["z"], 5), "coriolis_up_m": round(sc["y"] - s["y"], 5)})
        # supersonic limit
        t_sonic = brentq(lambda t: float(np.linalg.norm(flat.sol.sol(t)[3:])) / atmos["c"] - 1.0, 0.0, flat.sol.t[-1])
        x_sonic = float(flat.sol.sol(t_sonic)[0])
        zs = {}
        for zn, z in ZEROS.items():
            ang = zero_angle(am, z["distance_m"], atmos)
            tr = traj(am, ang, atmos, t_max=2.5); cache[(name, zn)] = tr
            path = [round(tr.at_x(r)["y"] - h, 5) for r in ranges]
            f = lambda x: tr.at_x(x)["y"] - h
            xs = np.linspace(1, 700, 1400); ys = np.array([f(x) for x in xs])
            cross = [brentq(f, xs[i], xs[i + 1]) + e2m for i in range(len(xs) - 1) if ys[i] * ys[i + 1] < 0]
            imax = int(np.argmax(ys))
            zs[zn] = {
                "label": z["label"], "zero_distance_from_eye_m": round(z["distance_m"], 3),
                "bore_angle_rad": ang, "bore_angle_moa": round(ang / MOA, 3), "bore_angle_mrad": round(ang * 1000, 4),
                "rear_sight_rise_mm": round(ang * RIFLE["sight_radius_m"] * 1000, 3),
                "crossings_from_eye_m": [round(c, 1) for c in cross],
                "max_ordinate_m": round(float(ys[imax]), 4), "max_ordinate_range_m": round(float(xs[imax]), 0),
                "path_m": path,
                "poi_vs_poa": [{"distance_from_eye_m": d, "poi_m": round(tr.at_x(d - e2m)["y"] - h, 5),
                                "poi_mm": round((tr.at_x(d - e2m)["y"] - h) * 1000, 1),
                                "velocity_mps": round(tr.at_x(d - e2m)["v"], 1), "energy_j": round(tr.at_x(d - e2m)["energy"], 0),
                                "tof_ms": round(tr.at_x(d - e2m)["t"] * 1000, 2)} for d in game_d],
            }
        am_out = {k: v for k, v in am.items()}
        am_out.update({"muzzle_energy_j": round(0.5 * am["mass_kg"] * am["mv"] ** 2, 1), "stability_sg": round(sg, 3),
                       "supersonic_to_m": round(x_sonic, 0) if x_sonic else None,
                       "range_m": ranges, "table": rows, "zeros": zs})
        out["ammo"][name] = am_out

    # ---- dispersion: convert a 10-shot extreme spread to a per-axis standard deviation by Monte Carlo
    rng = np.random.default_rng(416)
    pts = rng.standard_normal((40000, 10, 2))
    dd = np.linalg.norm(pts[:, :, None, :] - pts[:, None, :, :], axis=-1).reshape(40000, -1).max(1)
    es10 = float(dd.mean())
    pts5 = pts[:, :5]
    es5 = float(np.linalg.norm(pts5[:, :, None, :] - pts5[:, None, :, :], axis=-1).reshape(40000, -1).max(1).mean())
    out["dispersion"] = {
        "model": "circular bivariate normal in angle; rifle-plus-ammunition and shooter terms add in quadrature",
        "es10_over_sigma": round(es10, 3), "es5_over_sigma": round(es5, 3),
        "es_note": "mean extreme spread of an n-shot group divided by the per-axis sigma (Monte Carlo, 40,000 groups, seed 416)",
        "rifle_ammo": {n: {"group_es10_moa": am["group_es10_moa"], "sigma_moa": round(am["group_es10_moa"] / es10, 4),
                           "sigma_mrad": round(am["group_es10_moa"] / es10 * MOA * 1000, 4),
                           "mean_radius_moa": round(am["group_es10_moa"] / es10 * math.sqrt(math.pi / 2), 3),
                           "source": am["source"]["group_es10_moa"]} for n, am in AMMO.items()},
        "shooter": SHOOTER,
        "current_range_page": "uniform cone 0.0015 rad aimed (sigma about 1.5 MOA) and 0.025 rad at the hip (sigma about 0.41 degree)",
    }
    for n in AMMO: AMMO[n]["sigma_moa"] = out["dispersion"]["rifle_ammo"][n]["sigma_moa"]

    # ---- terminal tables
    term = out["terminal"]
    st = TERMINAL["steel"]
    plates = []
    for name in ("M855", "Mk262"):
        am = AMMO[name]; tr = cache[(name, DEFAULT_ZERO)]
        for r in (0.18, 0.20, 0.25, 0.30):
            pl = plate(r)
            for d in (20, 35, 55):
                s = tr.at_x(d - e2m); p = am["mass_kg"] * s["v"] * st["momentum_transfer"]
                pr = plate_response(pl, p, pl["s"], lean_deg=2.0)
                max_lean = math.degrees(math.acos(max(-1, 1 - pr["plate_ke"] / (pl["mass"] * G0 * pl["s"]))))
                tau = am["length_m"] / s["v"]
                plates.append({"ammo": name, "plate_radius_m": r, "plate_thickness_m": 0.010, "plate_mass_kg": round(pl["mass"], 2),
                               "inertia_about_hinge_kgm2": round(pl["I"], 4), "distance_from_eye_m": d,
                               "impact_speed_mps": round(s["v"], 1), "impact_energy_j": round(s["energy"], 0),
                               "momentum_ns": round(p, 3), "centre_hit_omega0_rad_s": round(pr["omega0"], 3),
                               "plate_ke_j": round(pr["plate_ke"], 3), "plate_ke_fraction": round(pr["plate_ke"] / s["energy"], 6),
                               "max_rest_lean_to_topple_deg": round(max_lean, 2), "falls_at_2deg_lean": pr["falls"],
                               "fall_time_s_at_2deg_lean": round(pr["fall_time"], 3) if pr["falls"] else None,
                               "landing_rate_rad_s": round(pr["landing_rate"], 2) if pr["falls"] else None,
                               "contact_time_s": round(tau, 8), "peak_force_n": round(math.pi * p / (2 * tau), 0)})
    term["steel_plate_table"] = plates
    term["steel_notes"] = {
        "hinge": "plate hinged along a horizontal axis at its bottom edge (hinge_offset = radius), resting lean_deg toward the shooter against a stop; I = m r^2 / 4 + m s^2",
        "force_pulse": "half-sine of duration contact_time_s = bullet length / impact speed, carrying momentum_ns; bandwidth about 1 / contact_time, well above the audible range",
        "energy_split": "the plate's swing takes under 0.1 percent of the bullet's energy; the rest goes to breaking and heating the bullet, the splash, and sound",
    }
    dirt = []
    for name in ("M855", "Mk262"):
        for v in (300, 500, 700, 800, 850):
            E = 0.5 * AMMO[name]["mass_kg"] * v * v
            dirt.append({"ammo": name, "speed_mps": v, "energy_j": round(E, 0),
                         "dirt_depth_m": round(dirt_depth(AMMO[name], v, "dirt"), 3), "berm_depth_m": round(dirt_depth(AMMO[name], v, "berm"), 3),
                         "crater_diameter_m": round(TERMINAL["dirt"]["crater_k_m_per_j13"] * E ** (1 / 3), 3),
                         "plume_height_dry_m": round(TERMINAL["dirt"]["plume_height_k_m_per_j13"] * E ** (1 / 3), 2)})
    term["dirt_table"] = dirt
    term["ricochet_probability"] = [{"angle_from_surface_deg": ang,
                                     "dirt": round(logistic(ang, TERMINAL["dirt"]["ricochet_angle_deg"], TERMINAL["dirt"]["ricochet_width_deg"]), 3),
                                     "steel": round(logistic(ang, st["ricochet_angle_deg"], st["ricochet_width_deg"]), 3)}
                                    for ang in (1, 2, 3, 5, 8, 10, 12, 15, 20, 30, 45, 90)]
    term["ground_strike_note"] = "from a 1.6 m eye height the flat ground is struck at atan(1.6 / distance): 4.6 degrees at 20 m, 1.8 degrees at 50 m. Low shots almost always skip off the dirt and carry on into the berm"
    term["paper"] = {n: {"hole_diameter_mm": round(am["diameter_m"] * TERMINAL["paper"]["hole_factor"] * 1000, 2),
                         "grease_ring_mm": round(am["diameter_m"] * 1000, 2),
                         "keyhole_length_mm_at_yaw_deg": {str(y): round((am["diameter_m"] * math.cos(math.radians(y)) + am["length_m"] * math.sin(math.radians(y))) * 1000, 2) for y in (0, 2, 5, 15, 90)}}
                     for n, am in AMMO.items()}
    m855 = AMMO["M855"]
    term["sonic_crack"] = {"model": "Whitham N-wave (peak = 0.53 P0 (M^2-1)^(1/8) d / (b^(3/4) l^(1/4)))",
                           "M855": [dict(miss_distance_m=b, mach=round(mach, 2), **{k: round(v, 6) for k, v in sonic_crack(m855, mach, b, atmos).items()})
                                    for mach in (2.45, 2.0) for b in (0.5, 1, 3, 10)]}

    # ---- validation
    val = out["validation"]
    # 1. vacuum: analytic parabola
    tv = Trajectory(0.004, 1, 850, 0.01, icao, drag=False, t_max=1.0); s = tv.at_x(500)
    t_an = 500 / (850 * math.cos(0.01)); y_an = 850 * math.sin(0.01) * t_an - 0.5 * G0 * t_an ** 2
    val["vacuum_parabola"] = {"y_error_m": abs(s["y"] - y_an), "t_error_s": abs(s["t"] - t_an)}
    # 2. constant-Cd drag in level flight without gravity has v(x) = v0 exp(-k Cd x): test on the flat part of G7 at low Mach
    k = math.pi / 8 * icao["rho"] / (0.151 * BC_SI)
    tc = Trajectory(0.004, 0.151, 100.0, 0.0, icao, t_max=0.5); s = tc.at_x(40)
    val["constant_cd_decay"] = {"vx_sim": s["vx"], "vx_analytic": 100 * math.exp(-k * 0.1194 * 40),
                                "note": "Mach 0.29 where G7 Cd is flat at 0.1194: vx = v0 exp(-k Cd x) to first order in the small fall angle"}
    # 3. Sierra Infinity table for M855 (forum transcription): 3,025 ft/s, G1 0.307, 2.25 in sight height, 300 yd zero, 100 F, sea level
    pub = {0: -2.25, 50: 1.34, 100: 3.85, 150: 5.15, 200: 5.07, 250: 3.43, 300: 0.0, 350: -5.47, 400: -13.3, 450: -23.8, 500: -37.5}
    def sierra(atm, model="G1", bc=0.307):
        fake = {"mass_kg": 62 * GR, "bc_g1": bc, "bc_g7": bc, "mv": 3025 * FPS}
        ang = brentq(lambda q: traj(fake, q, atm, model=model, bc=bc, t_max=1.2).at_x(300 * YD)["y"] - 2.25 * IN, 0, 0.02, xtol=1e-10)
        tr = traj(fake, ang, atm, model=model, bc=bc, t_max=1.5)
        return {yd: (tr.at_x(yd * YD)["y"] - 2.25 * IN) / IN if yd else -2.25 for yd in pub}
    hot = atmosphere(37.78, 1013.25, 0.0)
    hot_asm = atmosphere(37.78, 1000.0, 0.78)
    r1, r2, r3 = sierra(hot), sierra(hot_asm), sierra(hot, "G7", 0.151)
    val["sierra_infinity_m855"] = {
        "source": "Sierra Infinity output for M855 posted on forums.accuratereloading.com (thread 352101342): 3,025 ft/s (TM 43-0001-27), 300 yd zero, 100 F, sea level; BC 0.307 quoted in the thread. Forum transcription, not a primary source",
        "rows": [{"range_yd": yd, "published_in": pub[yd], "sim_g1_0.307_in": round(r1[yd], 2), "sim_g1_humid_in": round(r2[yd], 2),
                  "sim_g7_0.151_in": round(r3[yd], 2)} for yd in pub],
        "fit": "a one-parameter refit (G1 0.260 at 100 F, or 0.274 at 15 C) reproduces every posted row within 0.11 in (0.4 in at 15 C), so the posted run did not use 0.307; the integrator and geometry agree with Sierra's, the BC of that run is unknown",
        "sim_g1_0.260_in": {str(yd): round(v, 2) for yd, v in sierra(hot, "G1", 0.260).items()},
        "max_abs_error_in_g1_0.260": round(max(abs(v - pub[yd]) for yd, v in sierra(hot, "G1", 0.260).items()), 2),
        "max_abs_error_in_g1": round(max(abs(r1[yd] - pub[yd]) for yd in pub), 2),
        "max_abs_error_in_g1_humid": round(max(abs(r2[yd] - pub[yd]) for yd in pub), 2),
        "max_abs_error_in_g7": round(max(abs(r3[yd] - pub[yd]) for yd in pub), 2),
        "conditions": "sim_g1: 37.8 C, 1013.25 hPa, dry. sim_g1_humid: 37.8 C, 1000 hPa, 78 percent humidity (Army Standard Metro pressure and humidity). sim_g7: this model's M855 drag (G7 0.151) at the same velocity",
    }
    # 4. G1 0.304 against G7 0.151 for this rifle (two published descriptions of the same bullet)
    fa = traj(AMMO["M855"], 0, icao, mv=850); fb = traj(AMMO["M855"], 0, icao, mv=850, model="G1")
    val["g7_vs_g1_m855"] = [{"range_m": r, "v_g7": round(fa.at_x(r)["v"], 1), "v_g1": round(fb.at_x(r)["v"], 1),
                             "drop_g7_m": round(fa.at_x(r)["y"], 4), "drop_g1_m": round(fb.at_x(r)["y"], 4)} for r in (100, 200, 300, 400, 500, 600)]
    # 5. 20 in velocities quoted in a search summary as Aberdeen data (weak, second hand)
    fc = traj(AMMO["M855"], 0, icao, mv=3100 * FPS)
    val["aberdeen_20in_snippet"] = {
        "source": "search-result summary of a forum post citing Aberdeen data for M855 from a 20 in barrel: 2,751 / 2,420 / 2,115 ft/s at 100 / 200 / 300 m. Second hand; the muzzle velocity (assumed 3,100 ft/s) was not stated. Weak evidence",
        "rows": [{"range_m": r, "published_fps": p, "sim_fps": round(fc.at_x(r)["v"] / FPS, 0)} for r, p in ((100, 2751), (200, 2420), (300, 2115))]}
    # 6. HK drum: the 2, 3, 4 diopters against the V notch
    z = out["ammo"]["M855"]["zeros"]
    val["hk_drum_steps"] = {
        "note": "bore-angle steps this model needs between HK's drum positions, and what they mean at the rear sight (sight radius 364 mm). HK manual: a quarter turn of the drum is about 1.5 in at 100 yd (0.417 mrad)",
        "steps_mrad": {k: round((z[k]["bore_angle_rad"] - z["hk100yd"]["bore_angle_rad"]) * 1000, 3) for k in ("hk200yd", "hk300yd", "hk400yd")},
        "steps_mm_at_rear_sight": {k: round((z[k]["bore_angle_rad"] - z["hk100yd"]["bore_angle_rad"]) * RIFLE["sight_radius_m"] * 1000, 3) for k in ("hk200yd", "hk300yd", "hk400yd")},
        "quarter_turn_mm_at_rear_sight": round(1.5 * IN / (100 * YD) * RIFLE["sight_radius_m"] * 1000, 3)}
    # 7. HK effective range sanity
    val["hk_ranges"] = {"note": "HK manual: 500 m point, 600 m area effective range",
                        "M855_at_500m": out["ammo"]["M855"]["table"][ranges.index(500)], "M855_supersonic_to_m": out["ammo"]["M855"]["supersonic_to_m"]}

    json.dump(out, open(os.path.join(HERE, "ballistics.json"), "w"), indent=1)

    # ---- data block for the JS runtime (single source of truth)
    def ammo_js(n, am):
        d = {"label": am["label"], "massKg": round(am["mass_kg"], 8), "diameterM": round(am["diameter_m"], 6), "lengthM": round(am["length_m"], 6),
             "bcG7": am["bc_g7"], "mv": am["mv"], "mvSigma": am["mv_sigma"], "sigmaMoa": am["sigma_moa"],
             "sparks": am["sparks_on_steel"], "steelCore": n == "M855"}
        if "tracer" in am:
            t = am["tracer"]; d["tracer"] = {"igniteM": t["ignite_distance_m"], "fullM": t["full_bright_distance_m"], "burnoutM": t["burnout_distance_m"], "color": t["color_rgb"]}
        return d
    def surf(kind):
        d = dict(TERMINAL["dirt"]); d.update(TERMINAL[kind]) if kind != "dirt" else None
        return {"rho": d["density_kg_m3"], "R": d["strength_pa"], "C": d["drag_coefficient"], "areaK": d["tumble_area_factor"],
                "ricA": d["ricochet_angle_deg"], "ricW": d["ricochet_width_deg"], "exitRatio": d["ricochet_exit_ratio"],
                "lossPerDeg": d["ricochet_speed_loss_per_deg"], "dragScale": d["ricochet_drag_scale"], "scatterDeg": d["ricochet_scatter_deg"],
                "craterK": d["crater_k_m_per_j13"], "plumeK": d["plume_height_k_m_per_j13"], "plumeW": d["plume_width_ratio"],
                "ejecta": d["ejecta_speed_mps"], "linger": d["dust_linger_s"], "moisture": d["moisture"]}
    data = {
        "g7": [[float(m), float(c_)] for m, c_ in G7],
        "rifle": {"sightHeightM": RIFLE["sight_height_m"], "eyeToMuzzleM": RIFLE["eye_to_muzzle_m"], "sightRadiusM": RIFLE["sight_radius_m"], "twistIn": RIFLE["twist_in"]},
        "ammo": {n: ammo_js(n, am) for n, am in AMMO.items()},
        "zeros": {k: v["distance_m"] for k, v in ZEROS.items()}, "defaultZero": DEFAULT_ZERO,
        "shooter": {k: v["sigma_moa"] for k, v in SHOOTER.items()},
        "atmosphere": {"tempC": atmos["temp_c"], "pressureHPa": atmos["pressure_hpa"], "humidity": atmos["humidity"]},
        "paper": {"hole": TERMINAL["paper"]["hole_factor"], "loss": TERMINAL["paper"]["speed_loss_fraction"]},
        "steel": {"rho": st["density_kg_m3"], "transfer": st["momentum_transfer"], "splashDeg": st["splash_half_angle_deg"],
                  "fragSpeed": st["fragment_speed_fraction"], "fragCount": st["fragment_count"], "fragSize": st["fragment_size_m"],
                  "fragTau": st["fragment_drag_tau_s"], "ricA": st["ricochet_angle_deg"], "ricW": st["ricochet_width_deg"],
                  "pitLead": st["pit_threshold_mps"]["lead_core"], "pitSteel": st["pit_threshold_mps"]["steel_core"], "pitSlope": st["pit_depth_per_mps_m"]},
        "dirt": surf("dirt"), "berm": surf("berm"),
        "vis": {"traceMinM": VISIBILITY["trace_min_range_m"], "traceMag": VISIBILITY["trace_needs_magnification"], "vapRh": VISIBILITY["vapour_humidity_threshold"],
                "vapMax": VISIBILITY["vapour_max_opacity"], "vapLife": VISIBILITY["vapour_life_s"], "glint": VISIBILITY["glint_probability"]},
    }
    js_path = os.path.join(HERE, "hk416-ballistics.js")
    if os.path.exists(js_path):
        src = open(js_path).read()
        block = "/*DATA-BEGIN (written by sim.py; do not edit by hand)*/\nconst DATA = " + json.dumps(data, separators=(",", ":")) + ";\n/*DATA-END*/"
        new, n = re.subn(r"/\*DATA-BEGIN.*?/\*DATA-END\*/", lambda m: block, src, flags=re.S)
        if n != 1: sys.exit("hk416-ballistics.js: DATA markers not found")
        open(js_path, "w").write(new)

    if not a.no_plots:
        plots(out, cache, atmos)
    # ---- console summary
    print(f"atmosphere: rho {atmos['rho']:.4f} kg/m3, c {atmos['c']:.2f} m/s")
    for n, am in out["ammo"].items():
        print(f"\n{n}: mv {am['mv']:.0f} m/s, E0 {am['muzzle_energy_j']:.0f} J, Sg {am['stability_sg']}, supersonic to {am['supersonic_to_m']} m")
        print("  range   v     E     tof     drop    wind10  spin")
        for r in am["table"]:
            if r["range_m"] in (0, 25, 50, 100, 200, 300, 400, 500, 600):
                print(f"  {r['range_m']:4d} {r['velocity_mps']:6.1f} {r['energy_j']:6.0f} {r['tof_s']:7.4f} {r['drop_m']:8.4f} {r['wind_drift_10mph_m']:7.4f} {r['spin_drift_m']:6.4f}")
        for zn, z in am["zeros"].items():
            print(f"  zero {zn:8s} bore {z['bore_angle_mrad']:.3f} mrad, crossings {z['crossings_from_eye_m']}, POI mm at 10/15/25/35/45/55: "
                  + ", ".join(f"{p['poi_mm']:+.1f}" for p in z["poi_vs_poa"] if p["distance_from_eye_m"] in (10, 15, 25, 35, 45, 55)))
    print("\nvalidation:", json.dumps({k: v for k, v in val.items() if k not in ("hk_ranges",)}, indent=1)[:6000])

def plots(out, cache, atmos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    P = os.path.join(HERE, "plots"); os.makedirs(P, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    col = {"M855": "#2a6f97", "Mk262": "#c1440e", "M856": "#6a994e"}
    A = out["ammo"]
    # drag
    f, ax = plt.subplots(figsize=(6, 3.4)); m = np.linspace(0, 3.5, 500)
    ax.plot(m, cd("G7", m), label="G7", color="#2a6f97"); ax.plot(m, cd("G1", m), label="G1", color="#999")
    ax.set(xlabel="Mach", ylabel="Cd of the standard projectile", title="Standard drag functions"); ax.legend(); f.tight_layout(); f.savefig(P + "/drag_curves.png"); plt.close(f)
    # velocity and energy
    f, axs = plt.subplots(1, 3, figsize=(11, 3.4))
    for n, am in A.items():
        r = [x["range_m"] for x in am["table"]]
        axs[0].plot(r, [x["velocity_mps"] for x in am["table"]], color=col[n], label=n)
        axs[1].plot(r, [x["energy_j"] for x in am["table"]], color=col[n], label=n)
        axs[2].plot(r, [x["tof_s"] for x in am["table"]], color=col[n], label=n)
    axs[0].axhline(atmos["c"], color="k", lw=0.7, ls=":"); axs[0].text(5, atmos["c"] + 8, "speed of sound", fontsize=7)
    axs[0].set(xlabel="range from muzzle (m)", ylabel="velocity (m/s)"); axs[1].set(xlabel="range from muzzle (m)", ylabel="energy (J)")
    axs[2].set(xlabel="range from muzzle (m)", ylabel="time of flight (s)"); axs[0].legend(); f.suptitle("HK416 D14.5RS, 14.5 in barrel"); f.tight_layout(); f.savefig(P + "/velocity_energy_tof.png"); plt.close(f)
    # trajectories per zero
    f, axs = plt.subplots(1, 2, figsize=(11, 3.8)); zc = {"hk100yd": "#2a6f97", "50_200": "#c1440e", "25_300": "#6a994e", "hk300yd": "#8d6cab"}
    xs = np.linspace(0.0, 400, 300); xn = np.linspace(0.0, 70 - RIFLE["eye_to_muzzle_m"], 200)
    for zn, c in zc.items():
        tr = cache[("M855", zn)]
        axs[0].plot(xs + RIFLE["eye_to_muzzle_m"], [(tr.at_x(x)["y"] - RIFLE["sight_height_m"]) * 100 for x in xs], color=c, label=zn)
        axs[1].plot(xn + RIFLE["eye_to_muzzle_m"], [(tr.at_x(x)["y"] - RIFLE["sight_height_m"]) * 1000 for x in xn], color=c, label=zn)
    axs[0].axhline(0, color="k", lw=0.7); axs[0].set(ylim=(-60, 25), xlabel="distance from the eye (m)", ylabel="path above line of sight (cm)", title="M855 path by zero"); axs[0].legend()
    axs[1].axhline(0, color="k", lw=0.7)
    for d in (10, 15, 25, 35, 45, 55): axs[1].axvline(d, color="#bbb", lw=0.6, ls=":")
    axs[1].set(xlabel="distance from the eye (m)", ylabel="point of impact vs point of aim (mm)", title="Game distances: where the shot lands"); f.tight_layout(); f.savefig(P + "/trajectory_zero.png"); plt.close(f)
    # wind / spin / coriolis
    f, ax = plt.subplots(figsize=(6, 3.4)); t = A["M855"]["table"]; r = [x["range_m"] for x in t]
    ax.plot(r, [x["wind_drift_10mph_m"] * 100 for x in t], label="10 mph (4.5 m/s) crosswind", color="#2a6f97")
    ax.plot(r, [x["spin_drift_m"] * 100 for x in t], label="spin drift (Litz fit)", color="#c1440e")
    ax.plot(r, [x["coriolis_right_m"] * 100 for x in t], label="Coriolis, 45° N", color="#6a994e")
    ax.set(xlabel="range (m)", ylabel="sideways deflection (cm)", title="M855: what moves the bullet sideways", yscale="symlog"); ax.legend(); f.tight_layout(); f.savefig(P + "/wind_spin_coriolis.png"); plt.close(f)
    # dispersion at 25 m
    f, axs = plt.subplots(1, 3, figsize=(10, 3.5)); rng = np.random.default_rng(1)
    for ax, (st, ttl) in zip(axs, (("bench", "bench: rifle and M855 only"), ("aimed", "aimed, standing"), ("hip", "hip"))):
        s = math.hypot(AMMO["M855"]["sigma_moa"], SHOOTER[st]["sigma_moa"]) * MOA * 25
        p = rng.standard_normal((30, 2)) * s * 100
        for rr in (2.5, 5, 7.5, 10, 12.5): ax.add_patch(plt.Circle((0, 0), rr, fill=False, color="#bbb", lw=0.6))
        ax.scatter(p[:, 0], p[:, 1], s=8, color="#c1440e"); lim = max(14, 3.2 * s * 100); ax.set(xlim=(-lim, lim), ylim=(-lim, lim), aspect="equal", title=f"{ttl}\nsigma {s*1000:.0f} mm at 25 m", xlabel="cm"); ax.grid(False)
    f.tight_layout(); f.savefig(P + "/dispersion_25m.png"); plt.close(f)
    # plate response
    f, axs = plt.subplots(1, 2, figsize=(10, 3.5)); rr = np.linspace(0.15, 0.32, 40)
    for n in ("M855", "Mk262"):
        tr = cache[(n, DEFAULT_ZERO)]; p = AMMO[n]["mass_kg"] * tr.at_x(35)["v"]
        axs[0].plot(rr, [plate_response(plate(r), p, r)["omega0"] for r in rr], color=col[n], label=n + " centre hit at 35 m")
        axs[1].plot(rr, [math.degrees(math.acos(max(-1, 1 - plate_response(plate(r), p, r)["plate_ke"] / (plate(r)["mass"] * G0 * r)))) for r in rr], color=col[n], label=n)
    axs[0].set(xlabel="plate radius (m), 10 mm steel", ylabel="initial swing rate (rad/s)", title="Hinged plate: kick from one hit"); axs[0].legend()
    axs[1].set(xlabel="plate radius (m), 10 mm steel", ylabel="largest rest lean it still topples from (deg)", title="Will it fall?"); f.tight_layout(); f.savefig(P + "/steel_plate_response.png"); plt.close(f)
    # dirt + ricochet
    f, axs = plt.subplots(1, 2, figsize=(10, 3.5)); v = np.linspace(100, 900, 80)
    for n in ("M855", "Mk262"):
        axs[0].plot(v, [dirt_depth(AMMO[n], x) * 100 for x in v], color=col[n], label=n + ", ground")
        axs[0].plot(v, [dirt_depth(AMMO[n], x, "berm") * 100 for x in v], color=col[n], ls="--", label=n + ", berm")
    axs[0].set(xlabel="impact speed (m/s)", ylabel="penetration (cm)", title="Earth penetration (Poncelet, inferred constants)"); axs[0].legend()
    an = np.linspace(0, 40, 200)
    axs[1].plot(an, [logistic(x, TERMINAL["dirt"]["ricochet_angle_deg"], TERMINAL["dirt"]["ricochet_width_deg"]) for x in an], color="#8a6d3b", label="dirt")
    axs[1].plot(an, [logistic(x, TERMINAL["steel"]["ricochet_angle_deg"], TERMINAL["steel"]["ricochet_width_deg"]) for x in an], color="#555", label="steel plate")
    axs[1].set(xlabel="angle from the surface (deg)", ylabel="ricochet probability", title="Ricochet (inferred)"); axs[1].legend(); f.tight_layout(); f.savefig(P + "/dirt_ricochet.png"); plt.close(f)
    # validation
    vs = out["validation"]["sierra_infinity_m855"]["rows"]
    f, ax = plt.subplots(figsize=(6, 3.4)); yd = [x["range_yd"] for x in vs]
    ax.plot(yd, [x["published_in"] for x in vs], "ko", label="Sierra Infinity (as posted)")
    ax.plot(yd, [x["sim_g1_0.307_in"] for x in vs], color="#2a6f97", label="this sim, G1 0.307")
    ax.plot(yd, [x["sim_g7_0.151_in"] for x in vs], color="#c1440e", ls="--", label="this sim, G7 0.151")
    fit = out["validation"]["sierra_infinity_m855"]["sim_g1_0.260_in"]
    ax.plot(yd, [fit[str(y)] for y in yd], color="#6a994e", ls=":", label="this sim, G1 0.260 (refit)")
    ax.set(xlabel="range (yd)", ylabel="path (in)", title="Validation: M855, 3,025 ft/s, 300 yd zero, 100 °F"); ax.legend(); f.tight_layout(); f.savefig(P + "/validation_sierra.png"); plt.close(f)

if __name__ == "__main__":
    main()
