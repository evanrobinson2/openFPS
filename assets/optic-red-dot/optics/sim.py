#!/usr/bin/env python3
"""Generic 2 MOA tube red-dot sight: optical simulation.

    python3 sim.py        writes reddot.json, checks.json, reticle/dot_2moa.svg, plots/*.png   (about 10 s)

What is simulated (physics and first-order optical design, no engine code):
  * the collimator: an exact 3D ray trace of an off-axis Mangin (cemented doublet) reflex collimator whose radii,
    tilt and emitter focus are solved here; the parallax map (dot shift with eye offset and target distance), the
    parallax-free distance per axis, the dot's size and blur
  * the window: tint of the band-reflecting coating, computed from its spectrum
  * brightness: dot luminance per switch position against scene luminance (Weber contrast, eye pupil)
  * mounting and zero on the HK416 (assets/hk416): height over bore, click and hold tables from its ballistics tables
  * a rendering model: what a real-time renderer needs to draw the sight picture
Units: millimetres and radians inside the optics; SI in the tables unless a key says otherwise.
Frame of the asset: the HK416's (metres, +Z muzzle, +Y up, +X shooter's left), origin at socket_mount, which sits on
the rifle's socket_optic. Credit: carpetshark.
"""
import json, math, os, sys
import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
MOA = math.radians(1 / 60.0)
MRAD = 1e-3
BALLISTICS = os.path.join(HERE, '..', '..', 'hk416', 'ballistics', 'ballistics.json')

# ============================================================================ the rifle it mounts on (read by build.py too)
# Measured from a local build of assets/hk416/model/build.py (2026-11-17), model mm: L along the bore (+ muzzle,
# 0 at the upper receiver's front face), Z up from the bore axis.
RIFLE = dict(
    rail_top_mm=36.79,              # socket_optic height above the bore = top of the rail lugs
    socket_optic_l_mm=-60.0,        # socket_optic along the bore
    rail_pitch_mm=10.0, rail_lug_mm=4.77, upper_lug0_l_mm=-111.48, n_upper_lugs=10, rail_half_width_mm=10.5,
    iron_sight_line_mm=65.5,        # rear aperture and front post tip
    ads_eye_l_mm=-260.6,            # socket_ads_eye (the head position for the irons)
    crown_l_mm=363.3,               # barrel crown: eye_to_muzzle 0.6239 m in ballistics.json minus the eye's 260.6 mm
    folded_rear_sight_top_mm=52.7,  # rear sight folded: highest point above the bore; it spans L -151.6 .. -99.2
    raised_rear_sight_top_mm=69.8,
)
REDDOT = dict(
    name='generic 2 MOA tube red-dot sight',
    axis_over_rail_mm=39.0,         # optical axis above the rail top. Recalled: the AR-height spacer class of 30 mm tube red dots (39 mm)
    tube_centre_l_mm=-45.0,         # rifle L of the housing's mid-length (15 mm ahead of socket_optic): my placement
    length_mm=130.0,                # generic. Class: Aimpoint CompM4 user manual, section 1.1: 135 x 51 x 57 mm, 370 g with mount
    ring_od_mm=30.0, hood_od_mm=38.0, bore_id_mm=27.0,
    window_clear_mm=24.0,           # clear aperture of the objective (window) doublet: inferred for a 30 mm tube class sight
    rear_clear_mm=24.0,
    lens_inset_mm=24.0,             # window vertex behind the front of the hood: inferred (sun shade depth)
    rear_inset_mm=8.0,              # rear flat window behind... ahead of the rear face of the housing
    led_distance_mm=88.0, led_offset_mm=13.5, led_clock_deg=135.0,   # emitter at 4:30 as the shooter sees it (lower right), at the tube wall
    click_moa=0.5,                  # class: 1/2 MOA clicks (the CompM4 manual gives 16 mm at 100 m = 0.55 MOA)
    dot_moa=2.0,                    # the brief
    travel_moa=120.0,               # class: the CompM4 manual gives +/- 2 m at 100 m (+/- 69 MOA)
    mass_kg=0.34,                   # inferred: class figure (370 g with mount for the CompM4)
)
REDDOT['axis_over_bore_mm'] = RIFLE['rail_top_mm'] + REDDOT['axis_over_rail_mm']
REDDOT['eye_l_mm'] = RIFLE['ads_eye_l_mm']       # design eye point: the same head position along the rifle as the irons
# ============================================================================ small helpers
def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rnd(x, n=4):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, n) for v in x]
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (float, np.floating)):
        return float('%.*g' % (n, float(x)))        # n significant digits
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


# ============================================================================ 1. RED DOT: Mangin reflex collimator
class Sphere:
    def __init__(self, vertex, axis_back, radius):
        """Spherical surface through `vertex`, centre of curvature at vertex + axis_back * radius (radius may be
        negative or huge: the intersection is written in the curvature so that a flat surface is exact)."""
        self.v = np.asarray(vertex, float)
        self.a = np.asarray(axis_back, float)
        self.k = 1.0 / radius

    def hit(self, p, d):
        """Nearest intersection to the vertex of the ray p + t d, and the unit normal there.
        Points q on the sphere satisfy k |q - v|^2 - 2 a.(q - v) = 0."""
        w = p - self.v
        B = self.k * np.dot(w, d) - np.dot(self.a, d)
        C = self.k * np.dot(w, w) - 2 * np.dot(self.a, w)
        disc = B * B - self.k * C
        if disc < 0:
            return None, None
        sq = math.copysign(math.sqrt(disc), -np.dot(self.a, d))     # this sign picks the root on the vertex cap
        den = B + sq
        t = -C / den if abs(den) > 1e-9 else (-B + sq) / self.k
        q = p + d * t
        return q, self.k * (q - self.v) - self.a


def newton2(f, guess, h=1e-7, tol=1e-15, it=40):
    """Two-dimensional Newton iteration with a central-difference Jacobian (the JS runtime uses the same)."""
    x = np.array(guess, float)
    for _ in range(it):
        f0 = f(x)
        J = np.empty((2, 2))
        for k in range(2):
            dx = np.zeros(2); dx[k] = h
            J[:, k] = (f(x + dx) - f(x - dx)) / (2 * h)
        step = np.linalg.solve(J, f0)
        x = x - step
        if abs(step[0]) + abs(step[1]) < tol:
            break
    return x


def refract(d, n, n1, n2):
    if np.dot(d, n) > 0:
        n = -n
    eta = n1 / n2
    c = -np.dot(d, n)
    k = 1 - eta * eta * (1 - c * c)
    if k < 0:
        return None
    return unit(eta * d + (eta * c - math.sqrt(k)) * n)


def reflect(d, n):
    return unit(d - 2 * np.dot(d, n) * n)


N_GLASS = 1.5168   # N-BK7 class crown at 650 nm is 1.5145; one index for both halves of the cemented doublet


class RedDotOptics:
    """Doublet window: S1 (eye side), S2 (cemented, dichroic: reflects the LED band), S3 (target side).
    All three are concave toward the eye. The element is tilted toward the LED by `tilt`.
    Frame: +z toward the target, the LED sits at -y (the 'tangential' axis), x is sagittal. Window vertex at the origin."""

    def __init__(self, R1, R2, tilt, led_dz=0.0, led_dy=0.0, t1=2.5, t2=2.5, n=N_GLASS, P=REDDOT):
        self.R1, self.R2, self.tilt, self.t1, self.t2, self.n = R1, R2, tilt, t1, t2, n
        ab = np.array([0.0, -math.sin(tilt), -math.cos(tilt)])   # element axis, pointing back toward the eye
        self.ab = ab
        v1 = np.zeros(3)
        self.s1 = Sphere(v1, ab, R1)
        self.s2 = Sphere(v1 - ab * t1, ab, R2)
        # S3 makes the see-through path afocal (thick meniscus, zero power): solve phi = 0 for R3
        t = t1 + t2
        self.R3 = R1 + (n - 1) * t / n
        self.s3 = Sphere(v1 - ab * t, ab, self.R3)
        self.led = np.array([0.0, -P['led_offset_mm'] + led_dy, -P['led_distance_mm'] + led_dz])

    # reverse traces from the eye -------------------------------------------------
    def dot_landing(self, E, v):
        """Ray leaves the eye at E along v, refracts at S1, reflects at S2, refracts out of S1, lands on the LED plane."""
        q, n = self.s1.hit(E, v)
        d = refract(v, n, 1.0, self.n)
        q, n = self.s2.hit(q, d)
        d = reflect(d, n)
        q, n = self.s1.hit(q, d)
        d = refract(d, n, self.n, 1.0)
        if d is None or abs(d[2]) < 1e-9:
            return np.array([1e3, 1e3])
        s = (self.led[2] - q[2]) / d[2]
        return (q + d * s)[:2]

    def target_landing(self, E, v, dist):
        q, n = self.s1.hit(E, v)
        d = refract(v, n, 1.0, self.n)
        q, n = self.s3.hit(q, d)
        d = refract(d, n, self.n, 1.0)
        s = (dist - q[2]) / d[2]
        return (q + d * s)[:2]

    @staticmethod
    def _dir(a):
        return np.array([a[0], a[1], math.sqrt(max(1e-12, 1 - a[0] ** 2 - a[1] ** 2))])

    def dot_dir(self, E, led_xy=None, guess=(0.0, 0.0)):
        """Direction (unit vector, from the eye) in which the eye at E sees the LED point."""
        tgt = self.led[:2] if led_xy is None else np.asarray(led_xy)
        sol = newton2(lambda a: self.dot_landing(E, self._dir(a)) - tgt, guess)
        return self._dir(sol)

    def target_dir(self, E, T, guess=(0.0, 0.0)):
        sol = newton2(lambda a: (self.target_landing(E, self._dir(a), T[2]) - T[:2]) / T[2], guess)
        return self._dir(sol)

    def parallax(self, E, dist_mm, E0, u0=None):
        """Angular error (x, y in rad) between the dot and the target point that the centred eye's dot covers."""
        if u0 is None:
            u0 = self.dot_dir(E0)
        T = np.append(self.target_landing(E0, u0, dist_mm), dist_mm)     # the point the centred eye's dot covers, seen through the window
        ud = self.dot_dir(E, guess=u0[:2])
        ut = self.target_dir(E, T, guess=u0[:2])
        return (ud - ut)[:2]


def window_l_mm(P=REDDOT):
    """Rifle L of the window (doublet) vertex."""
    return P['tube_centre_l_mm'] + P['length_mm'] / 2 - P['lens_inset_mm']


def eye_grid(radius, n):
    pts = []
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x, y = radius * i / n, radius * j / n
            if x * x + y * y <= radius * radius * 1.0001:
                pts.append((x, y))
    return pts


R1_MIN_MM = 150.0     # design constraint: a flatter window keeps the see-through magnification within about 1 percent of 1x


def design_reddot(disc_mm=7.0, dz_max=4.0):
    """Solve the collimator. Free: the curvature of the eye-side surface, the curvature of the dichroic surface and the
    emitter's focus position. The tilt is not free: it is solved so the centred eye sees the dot exactly on the
    mechanical axis. Merit: mean square parallax error over a 14 mm eye disc (the central zone the eye uses) for a
    target at 50 m. The emitter may move 4 mm either way from its nominal seat; the housing length allows no more."""
    from scipy.optimize import brentq
    P = REDDOT
    ez = -(window_l_mm() - P['eye_l_mm'])   # eye z in the lens frame (the eye is behind the window)
    D0 = 50_000.0
    grid = eye_grid(disc_mm, 2)
    E0 = np.array([0, 0, ez])

    def build(x):
        c1, c2, dz = x[0] / 100, x[1] / 100, x[2]
        mk = lambda tilt: RedDotOptics(1.0 / c1 if abs(c1) > 1e-9 else 1e9, 1.0 / c2, tilt, led_dz=dz)
        tilt = brentq(lambda t: mk(t).dot_dir(E0)[1], 0.02, 0.14, xtol=1e-13)
        return mk(tilt)

    def merit(x):
        c1, c2, dz = x[0] / 100, x[1] / 100, x[2]
        if not (abs(c1) < 1 / R1_MIN_MM and 1 / 600 < c2 < 1 / 90 and abs(dz) < dz_max):
            return 1e3
        try:
            o = build(x)
            u0 = o.dot_dir(E0)
            err = [np.hypot(*o.parallax(np.array([x_, y_, ez]), D0, E0, u0)) for x_, y_ in grid]
            return 1e6 * float(np.mean(np.square(err)))
        except Exception:
            return 1e3
    best = None
    for c1 in (-1 / 150, 0.0, 1 / 150):
        for c2 in (1 / 160, 1 / 220):
            x0 = np.array([c1 * 100, c2 * 100, 0.0])
            simplex = np.vstack([x0] + [x0 + d for d in np.diag([0.3, 0.1, 1.0])])
            r = minimize(merit, x0, method='Nelder-Mead', options=dict(xatol=1e-7, fatol=1e-10, maxiter=1500, initial_simplex=simplex))
            if best is None or r.fun < best.fun:
                best = r
    return build(best.x), ez, best.fun


def reddot_results():
    P = REDDOT
    o, ez, merit = design_reddot()
    E0 = np.array([0, 0, ez])
    u0 = o.dot_dir(E0)
    # plate scale: how far the dot moves when the emitter moves 0.1 mm (gives the effective focal length)
    du = o.dot_dir(E0, led_xy=o.led[:2] + np.array([0.0, 0.1]), guess=u0[:2]) - u0
    efl = 0.1 / np.hypot(du[0], du[1])
    emitter_um = P['dot_moa'] * MOA * efl * 1000
    # collimation: direction slope with eye offset -> the dot's virtual image distance
    offs = np.linspace(-11, 11, 23)
    a_t = np.array([o.dot_dir(np.array([0, y, ez]), guess=u0[:2])[:2] - u0[:2] for y in offs])   # tangential scan
    a_s = np.array([o.dot_dir(np.array([x, 0, ez]), guess=u0[:2])[:2] - u0[:2] for x in offs])   # sagittal scan
    # polynomial model of the beam direction a(ex, ey) in rad (ex sagittal, ey tangential, mm), order 5
    pts = eye_grid(11.5, 7)
    A, bx, by = [], [], []
    terms = [(i, j) for i in range(6) for j in range(6) if 1 <= i + j <= 5]
    for x, y in pts:
        d = o.dot_dir(np.array([x, y, ez]), guess=u0[:2])[:2] - u0[:2]
        A.append([x ** i * y ** j for i, j in terms]); bx.append(d[0]); by.append(d[1])
    cx = np.linalg.lstsq(np.array(A), np.array(bx), rcond=None)[0]
    cy = np.linalg.lstsq(np.array(A), np.array(by), rcond=None)[0]
    with np.errstate(all='ignore'):
        fit_resid = float(np.max(np.abs(np.array(A) @ cx - bx)) + np.max(np.abs(np.array(A) @ cy - by)))
    # see-through path: residual power and magnification of the afocal doublet (target direction slope with eye offset)
    Tfar = np.array([0.0, 0.0, 1e9])
    t_far = np.array([o.target_dir(np.array([0, y, ez]), Tfar, guess=u0[:2])[:2] - o.target_dir(E0, Tfar, guess=u0[:2])[:2] for y in (-10, 10)])
    window_power_dpt = float((t_far[1][1] - t_far[0][1]) / 20.0 * 1000)   # 1/m
    los_dev = o.target_dir(E0, Tfar, guess=u0[:2])[:2]
    th = 5e-3
    see_mag = float((o.target_dir(E0, np.array([0.0, th * 1e9, 1e9]), guess=u0[:2])[1] - o.target_dir(E0, np.array([0.0, -th * 1e9, 1e9]), guess=u0[:2])[1]) / (2 * th))
    # how the target's direction changes with eye offset through the window: -k e / D (k = 1 for a perfect 1x window)
    T25 = np.append(o.target_landing(E0, u0, 25000.0), 25000.0)
    k_see = [float(-(o.target_dir(np.array([1.0 * (ax == 0), 1.0 * (ax == 1), ez]), T25, guess=u0[:2])[ax]
                     - o.target_dir(np.array([-1.0 * (ax == 0), -1.0 * (ax == 1), ez]), T25, guess=u0[:2])[ax]) / 2.0 * (25000.0 - ez)) for ax in (0, 1)]      # where a far point straight ahead appears through the tilted window
    # parallax table: error for eye offsets in 8 directions at several distances
    dists = [10, 15, 25, 35, 45, 50, 55, 75, 100, 200, 300, 600]
    table = []
    for D in dists:
        row = {'distance_m': D}
        for e in (3, 6, 9, 11):
            errs = []
            for k in range(8):
                ang = k * math.pi / 4
                E = np.array([e * math.cos(ang), e * math.sin(ang), ez])
                errs.append(o.parallax(E, D * 1000.0, E0, u0))
            errs = np.array(errs)
            mag = np.hypot(errs[:, 0], errs[:, 1])
            row[f'eye_{e}mm'] = {'max_moa': float(mag.max() / MOA), 'mean_moa': float(mag.mean() / MOA),
                                 'max_mm_on_target': float(mag.max() * D * 1000)}
        # edge-to-edge sweep (the 2017 independent test's measure): eye from -11 to +11 mm, both axes
        sw = []
        for ax in (0, 1):
            a = np.zeros(3); a[ax] = 11.0; a[2] = ez
            b = a.copy(); b[ax] = -11.0
            sw.append(np.hypot(*(o.parallax(a, D * 1000.0, E0, u0) - o.parallax(b, D * 1000.0, E0, u0))) / MOA)
        row['edge_to_edge_sweep_moa'] = {'sagittal': float(sw[0]), 'tangential': float(sw[1])}
        table.append(row)
    # parallax-free distance per axis from the linear term of the fit: a = -e / D0  ->  D0 = -1 / slope
    kx = cx[terms.index((1, 0))]; ky = cy[terms.index((0, 1))]
    d0x = -1.0 / kx / 1000.0 if abs(kx) > 1e-12 else float('inf')
    d0y = -1.0 / ky / 1000.0 if abs(ky) > 1e-12 else float('inf')
    # blur of the dot seen through a 3 mm eye pupil (the pupil samples a patch of the aberrated beam)
    blur = {}
    for name, (x, y) in {'centre': (0, 0), 'edge_tangential_9mm': (0, 9), 'edge_sagittal_9mm': (9, 0)}.items():
        dirs = np.array([o.dot_dir(np.array([x + 1.5 * math.cos(t), y + 1.5 * math.sin(t), ez]), guess=u0[:2])[:2] for t in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
        blur[name] = float(2 * np.max(np.hypot(*(dirs - dirs.mean(axis=0)).T)) / MOA)
    return dict(
        design=dict(
            type='off-axis Mangin doublet collimator: LED at the tube wall, dichroic on the cemented surface',
            R1_eye_side_mm=o.R1, R2_dichroic_mm=o.R2, R3_target_side_mm=o.R3, centre_thickness_mm=o.t1 + o.t2,
            tilt_deg=math.degrees(o.tilt), glass_index=o.n,
            led_position_mm={'behind_window_vertex': float(-o.led[2]), 'off_axis': float(-o.led[1]), 'clock_as_shooter_sees_deg': P['led_clock_deg']},
            effective_focal_length_mm=float(efl), emitter_diameter_um=float(emitter_um),
            eye_plane_behind_window_mm=-ez, optimiser_merit=float(merit),
            window_see_through_power_dioptre=window_power_dpt, window_see_through_magnification=see_mag,
            window_line_of_sight_deviation_urad=float(np.hypot(*los_dev) * 1e6),
            window_deviation_note='the tilted meniscus window bends the line of sight by this constant angle (a weak wedge); zeroing absorbs it, and the parallax figures are measured from the point the centred eye\'s dot covers through the window',
            note='R1, R2 and the emitter focus position are solved here by minimising the parallax error over a 14 mm eye disc at 50 m; the tilt puts the centred eye\'s dot on the mechanical axis; R3 makes the window afocal.'),
        dot=dict(size_moa=P['dot_moa'], size_mrad=P['dot_moa'] * MOA * 1000, blur_added_moa_3mm_pupil=blur,
                 covers_mm_at={str(d): P['dot_moa'] * MOA * d * 1000 for d in (10, 25, 50, 100, 200, 300)}),
        parallax=dict(
            definition='angle between the dot and the target point the centred eye aimed at, as the eye moves off the optical axis; '
                       'POI moves opposite: poi_shift = -error * distance',
            frame='lens frame: ex = sagittal, ey = tangential (+ey is away from the LED). See frames.lens_from_shooter for the shooter\'s right/up',
            parallax_free_distance_m={'sagittal': d0x, 'tangential': d0y},
            beam_direction_poly=dict(
                doc='a_x, a_y (rad) = sum c[i][j] * ex^i * ey^j, eye offsets in mm; error(e, D) = a(e) + k * e / (D * 1000 + eye_plane_behind_window_mm) per axis, D = target distance from the front window (m), k = see_through_factor (1 for a perfect 1x window)',
                see_through_factor=k_see,
                terms=terms, cx=[float(v) for v in cx], cy=[float(v) for v in cy], max_fit_residual_rad=fit_resid),
            scan_mm=[float(v) for v in offs],
            beam_direction_tangential_scan_moa=[float(v) for v in a_t[:, 1] / MOA],
            beam_direction_sagittal_scan_moa=[float(v) for v in a_s[:, 0] / MOA],
            table=table,
            sweep_note='edge_to_edge_sweep_moa: the eye goes from -11 to +11 mm across the window; the figure is how far the dot moves on the target'),
    ), o, ez


# ---------------------------------------------------------------------------- spectral tint
def _g(l, mu, s1, s2):
    s = np.where(l < mu, s1, s2)
    return np.exp(-0.5 * ((l - mu) / s) ** 2)


def cmf(l):   # Wyman, Sloan, Shirley (2013) analytic fit of the CIE 1931 colour matching functions
    x = 1.056 * _g(l, 599.8, 37.9, 31.0) + 0.362 * _g(l, 442.0, 16.0, 26.7) - 0.065 * _g(l, 501.1, 20.4, 26.2)
    y = 0.821 * _g(l, 568.8, 46.9, 40.5) + 0.286 * _g(l, 530.9, 16.3, 31.1)
    z = 1.217 * _g(l, 437.0, 11.8, 36.0) + 0.681 * _g(l, 459.0, 26.0, 13.8)
    return np.array([x, y, z])


XYZ2RGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])


def planck(l_nm, T=6504.0):
    l = l_nm * 1e-9
    return 1.0 / (l ** 5 * (np.exp(1.4388e-2 / (l * T)) - 1))


def spectrum_rgb(weight):
    l = np.arange(380.0, 781.0, 1.0)
    ill = planck(l)
    base = XYZ2RGB @ (cmf(l) * ill).sum(axis=1)
    filt = XYZ2RGB @ (cmf(l) * ill * weight(l)).sum(axis=1)
    lum = float((cmf(l)[1] * ill * weight(l)).sum() / (cmf(l)[1] * ill).sum())
    return [float(v) for v in filt / base], lum


def reddot_window():
    led_nm, led_fwhm = 650.0, 20.0
    notch_peak, notch_sigma = 0.80, 15.0          # dichroic reflectance at the LED line (inferred, typical band-reflector)
    ar = 0.005                                    # residual reflectance of each of the three AR-coated air surfaces
    refl = lambda l: notch_peak * np.exp(-0.5 * ((l - led_nm) / notch_sigma) ** 2)
    trans = lambda l: (1 - refl(l)) * (1 - ar) ** 3
    t_rgb, t_lum = spectrum_rgb(trans)
    r_rgb, r_lum = spectrum_rgb(lambda l: refl(l) + ar)
    return dict(
        led_peak_nm=led_nm, led_fwhm_nm=led_fwhm, dichroic_peak_reflectance=notch_peak, dichroic_sigma_nm=notch_sigma,
        transmission_linear_srgb=t_rgb, luminous_transmission=t_lum,
        front_reflection_linear_srgb=r_rgb, front_luminous_reflectance=r_lum,
        look='seen through: a faint cyan-blue cast (red is taken out of the scene); seen from the front: a deep red mirror-like flash',
        rear_window='plain AR-coated flat, 0.5 percent per surface, neutral',
        eye_side_ghost='the eye-side surface of the doublet reflects about 0.5 percent of what is behind the shooter (bright sky behind gives a faint veil)',
        source='inferred: reflectance and bandwidth typical of a single-line band reflector; the tint is computed from that spectrum '
               'with the Wyman 2013 fit of the CIE 1931 observer under a 6504 K source')


def pupil_mm(L):
    """Stanley and Davies (1995) pupil diameter for a 60 degree adapting field of luminance L (cd/m^2)."""
    f = (L * 2827.0 / 846.0) ** 0.41
    return 7.75 - 5.75 * f / (f + 2.0)


AMBIENT = [   # scene luminance the dot is seen against (cd/m^2); typical photometric handbook values
    ('starlight', 0.001), ('full_moon', 0.03), ('deep_twilight', 1.0), ('indoor_range', 60.0), ('heavy_overcast', 700.0),
    ('overcast_day', 2500.0), ('sunlit_grass', 5000.0), ('sunlit_paper_target', 20000.0), ('sunlit_snow_or_sand', 32000.0)]


def reddot_brightness(win):
    # 12-position switch: OFF, 3 night-vision, 8 daylight. Dot luminance as the eye sees it (after the dichroic).
    nv = [0.003, 0.03, 0.3]
    day = [2.0e5 / (3.0 ** (8 - k)) for k in range(1, 9)]
    settings = [{'position': 0, 'label': 'OFF', 'dot_luminance_cd_m2': 0.0}]
    for i, L in enumerate(nv):
        settings.append({'position': i + 1, 'label': f'NV{i + 1}', 'dot_luminance_cd_m2': L})
    for i, L in enumerate(day):
        settings.append({'position': i + 4, 'label': f'{i + 1}', 'dot_luminance_cd_m2': L})
    tau = win['luminous_transmission']
    rows = []
    for name, Lb in AMBIENT:
        seen = tau * Lb
        # crisp dot: Weber contrast 8 to 60. Below about 3 it washes out, above about 300 it blooms.
        pick = next((s for s in settings[4:] if s['dot_luminance_cd_m2'] / seen >= 8.0), settings[-1])
        if seen < 0.2:
            pick = next((s for s in settings[1:] if s['dot_luminance_cd_m2'] / max(seen, 1e-4) >= 8.0), settings[4])
        rows.append({'ambient': name, 'scene_luminance_cd_m2': Lb, 'seen_through_window_cd_m2': seen, 'eye_pupil_mm': pupil_mm(Lb),
                     'recommended_position': pick['position'], 'contrast_at_recommended': pick['dot_luminance_cd_m2'] / seen,
                     'contrast_at_max': settings[-1]['dot_luminance_cd_m2'] / seen})
    return dict(
        settings=settings,
        contrast='Weber contrast C = dot_luminance / (window_transmission * scene_luminance)',
        appearance=dict(washed_out_below=3.0, crisp_range=[8.0, 60.0], bloom_above=300.0,
                        bloom_model='apparent diameter = dot * sqrt(1 + (C / 300)); add a halo of radius 6 * dot at 0.02 * C / 300 of the core (clamped to 1), plus two faint starburst spikes for C > 1000',
                        astigmatism_note='a real eye with astigmatism smears the dot into a comma; not modelled, expose as an option'),
        versus_ambient=rows,
        source='inferred: step ratio 3 per daylight position and a 2e5 cd/m^2 top setting chosen so the top position keeps contrast above 6 on sunlit snow; '
               'manufacturers publish the number of settings, not luminances')



# ============================================================================ 3. mounting and zero on the HK416
class Drop:
    """Flat-fire table from assets/hk416/ballistics/ballistics.json (distances from the muzzle crown)."""
    def __init__(self, table):
        from scipy.interpolate import CubicSpline
        x = np.array([r['range_m'] for r in table], float)
        self.fy = CubicSpline(x, [r['drop_m'] for r in table]); self.fw = CubicSpline(x, [r['wind_drift_10mph_m'] for r in table])
        self.ft = CubicSpline(x, [r['tof_s'] for r in table]); self.fv = CubicSpline(x, [r['velocity_mps'] for r in table])


HOLD_DISTANCES = (10, 15, 20, 25, 35, 45, 55, 75, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600)


def zero_tables(bal, h, e2m, click, click_name, zeros):
    """h: optical axis over the bore (m). e2m: eye to muzzle crown (m). Distances are from the eye, as in ballistics.json.
    The bore is tilted up by the bore angle about the muzzle; path(D) = drop(x) + angle * x - h with x = D - e2m."""
    out = dict(axis_over_bore_mm=h * 1000, eye_to_muzzle_m=e2m, click=click_name, click_rad=click,
               click_moves_poi_mm_at={str(d): click * d * 1000 for d in (10, 25, 50, 100, 200)},
               convention='Distances are from the eye. bore_angle is the bore above the line of sight for an exact zero (POI = POA at the zero distance). '
                          'clicks_up_from_centre is that angle in whole clicks from optical centre (line of sight parallel to the bore); the hold tables use the exact angle. '
                          'poi_mm: + is high. hold: aim this much higher (+) to hit.',
               ammo={})
    for an, a in bal['ammo'].items():
        d = Drop(a['table'])
        zs = {}
        for zn, zd in zeros:
            x = zd - e2m
            th = (h - float(d.fy(x))) / x
            path = lambda D: float(d.fy(D - e2m) + th * (D - e2m) - h)
            dd = np.arange(1.0, 600.5, 0.5)
            pp = np.array([path(D) for D in dd])
            cross = [float(dd[i] - pp[i] * 0.5 / (pp[i + 1] - pp[i])) for i in range(len(dd) - 1) if pp[i] * pp[i + 1] < 0 or pp[i] == 0]
            imax = int(np.argmax(pp))
            n = round(th / click)
            rows = []
            for D in HOLD_DISTANCES:
                p = path(D); x = D - e2m; wind = float(d.fw(x))
                rows.append(dict(distance_m=D, poi_mm=p * 1000, hold_mrad=-p / D * 1000, hold_moa=-p / D / MOA, hold_clicks_up=round(-p / D / click),
                                 wind_10mph_mm=wind * 1000, wind_10mph_mrad=wind / D * 1000, tof_ms=float(d.ft(x)) * 1000, velocity_mps=float(d.fv(x))))
            inside = [D for D, p in zip(dd, pp) if abs(p) <= 0.05]
            zs[zn] = dict(zero_distance_m=zd, bore_angle_mrad=th * 1000, bore_angle_moa=th / MOA, clicks_up_from_centre=n,
                          rounding_moves_poi_mm_at_zero=(n * click - th) * x * 1000,
                          crossings_from_eye_m=cross, max_ordinate_mm=float(pp[imax] * 1000), max_ordinate_at_m=float(dd[imax]),
                          within_50mm_from_to_m=[inside[0], inside[-1]] if inside else None, holds=rows)
        out['ammo'][an] = zs
    return out


# ============================================================================ 4. the dot as a reticle
def reddot_reticle():
    r = REDDOT['dot_moa'] * MOA * 1000 / 2
    return dict(name='2 MOA dot', units='mrad', primitives=[dict(type='dot', c=[0, 0], d=2 * r, layer='illuminated')],
                profile='radial: uniform luminance to r = %.3f mrad, then a Gaussian skirt of sigma 0.06 mrad (about the eye\'s point spread at a 3 mm pupil: inferred)' % r,
                skirt_sigma_mrad=0.06)


def write_dot_svg(ret, path, extent=3.0):
    S = 1000.0 / (2 * extent); r = ret['primitives'][0]['d'] / 2 * S
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">\n'
                          '<title>2 MOA dot (generic; carpetshark). The drawing is %g mrad wide.</title>\n'
                          '<rect width="1000" height="1000" fill="#cfd6cf"/>\n<circle cx="500" cy="500" r="%.2f" fill="#ff2a12"/>\n</svg>\n' % (2 * extent, r))


# ============================================================================ 5. rendering model
def rendering_model(win):
    return dict(
        frame='Asset frame (metres, +Z muzzle, +Y up, +X shooter\'s left), origin socket_mount. The optical axis is the line through socket_eye and socket_objective.',
        render_target=False,
        steps=['1. Draw the world as usual. The housing, mount and caps are ordinary opaque geometry.',
               '2. On pixels of the front window seen through the rear window (materials lens_front and lens_rear): multiply the scene by window.transmission_linear_srgb.',
               '3. Dot direction: d = optical axis + zero offset + a(eye offset), with a from optics.parallax.beam_direction_poly rotated by frames.lens_from_shooter '
               '(OpticRedDot.dotDirection does this). The dot is at infinity: draw a disc of angular diameter dot.size_mrad around d. It has a fixed angular size and '
               'does not scale with how big the window is on screen.',
               '4. The dot exists only on window pixels: when the line from the eye along d misses the front or rear clear aperture the dot is gone. That is the whole "eye box" of a red dot.',
               '5. Dot radiance = led colour * brightness.settings[position].dot_luminance_cd_m2 / exposure. Bloom and wash-out follow brightness.appearance from the Weber contrast.',
               '6. Optional: 0.5 percent environment reflection on the front surface tinted window.front_reflection_linear_srgb, a 0.5 percent ghost of the scene behind the shooter, '
               'and a dark ring in the outer 6 percent of the window radius (the tube wall seen through the edge of the doublet).'],
        parameters=dict(dot_moa=REDDOT['dot_moa'], led_colour_linear_srgb=[1.0, 0.045, 0.012], window_clear_mm=REDDOT['window_clear_mm'], rear_clear_mm=REDDOT['rear_clear_mm'],
                        tint=win['transmission_linear_srgb'], magnification=1.0, distortion_k1=0.0),
        parallax_shortcut='error (rad) = e * (1/D - 1/D0) per lens axis, e = eye offset (m), D0 = optics.parallax.parallax_free_distance_m. The polynomial adds the aberration terms, '
                          'which dominate beyond about 6 mm of eye offset.',
        source='led colour: inferred, a 650 nm LED in linear sRGB primaries (out of gamut, clipped)')


# ============================================================================ 6. checks
def mangin_paraxial_efl(o):
    """First-order focal length of the folded collimator by ray-transfer matrices, independent of the ray trace:
    refraction at S1 (air to glass), t1 of glass, reflection at S2 inside the glass, t1 back, refraction out of S1."""
    n = o.n
    P1 = -(n - 1) / o.R1               # S1: centre of curvature on the eye side when R1 > 0: diverging going in
    P2 = 2 * n / o.R2                  # concave mirror in glass
    R = lambda P: np.array([[1, 0], [-P, 1]]); T = lambda d: np.array([[1, d], [0, 1]])
    M = R(P1) @ T(o.t1 / n) @ R(P2) @ T(o.t1 / n) @ R(P1)
    return float(-1.0 / M[1, 0])


def run_checks(rd, o, ez, bright, win):
    E0 = np.array([0, 0, ez]); u0 = o.dot_dir(E0)
    efl_trace = rd['design']['effective_focal_length_mm']; efl_par = mangin_paraxial_efl(o)
    d0 = rd['parallax']['parallax_free_distance_m']
    # thin-lens parallax relation against the ray trace, 1 mm of eye offset
    rows = []; worst = 0.0
    for D in (10, 25, 50, 100, 300):
        ex = o.parallax(np.array([1.0, 0, ez]), D * 1000.0, E0, u0)[0]; ey = o.parallax(np.array([0, 1.0, ez]), D * 1000.0, E0, u0)[1]
        px = 1e-3 * (1 / D - 1 / d0['sagittal']); py = 1e-3 * (1 / D - 1 / d0['tangential'])
        # the tangential axis has a quadratic (coma) term; remove it with the opposite offset
        ey2 = -o.parallax(np.array([0, -1.0, ez]), D * 1000.0, E0, u0)[1]
        rows.append(dict(distance_m=D, trace_sagittal_urad=ex * 1e6, thin_lens_sagittal_urad=px * 1e6, trace_tangential_urad=(ey + ey2) / 2 * 1e6, thin_lens_tangential_urad=py * 1e6))
        worst = max(worst, abs(ex - px), abs((ey + ey2) / 2 - py))
    # dot size: trace the two edges of the emitter
    r_em = rd['design']['emitter_diameter_um'] / 2000.0
    a = o.dot_dir(E0, led_xy=o.led[:2] + np.array([0.0, r_em]), guess=u0[:2]); b = o.dot_dir(E0, led_xy=o.led[:2] - np.array([0.0, r_em]), guess=u0[:2])
    dot_traced = float(np.linalg.norm(a - b) / MOA)
    # does the dot direction depend on how far back the eye is? (it should not: the beam is collimated)
    zdep = max(float(np.linalg.norm(o.dot_dir(np.array([x, y, ez + dz]), guess=u0[:2]) - o.dot_dir(np.array([x, y, ez]), guess=u0[:2])))
               for x, y in ((0, 0), (6, 0), (0, 6), (0, -6)) for dz in (-100.0, 100.0))
    # published edge-to-edge parallax figures
    tab = {r['distance_m']: r for r in rd['parallax']['table']}
    yd = [22.86, 45.72, 91.44]
    sw = []
    for D in yd:
        for ax in (0, 1):
            p = np.zeros(3); p[ax] = 11.0; p[2] = ez; q = p.copy(); q[ax] = -11.0
            sw.append(float(np.hypot(*(o.parallax(p, D * 1000.0, E0, u0) - o.parallax(q, D * 1000.0, E0, u0))) / MOA))
    top = bright['settings'][-1]['dot_luminance_cd_m2']
    L55k = 55000.0 * 0.9 / math.pi
    ck = dict(
        mangin_first_order=dict(
            what='Effective focal length of the collimator: ray-transfer matrices (thick Mangin mirror, first order) against the plate scale of the exact ray trace',
            paraxial_efl_mm=efl_par, ray_trace_efl_mm=efl_trace, difference_percent=100 * (efl_trace / efl_par - 1),
            note='The difference is the off-axis geometry: the emitter sits %.1f degrees off the tube axis and the plate scale is measured in its plane; 1/cos^2 of that angle is the size of the effect.' % math.degrees(math.atan2(REDDOT['led_offset_mm'], -o.led[2])),
            passed=abs(efl_trace / efl_par - 1) < 0.02),
        thin_lens_parallax=dict(
            what='Parallax error for 1 mm of eye offset: exact ray trace against the thin-lens relation e * (1/D - 1/D0)',
            rows=rows, max_difference_urad=worst * 1e6, passed=worst < 5e-6),
        dot_size=dict(what='Angle between the traced images of the two edges of the emitter', emitter_diameter_um=rd['design']['emitter_diameter_um'],
                      traced_moa=dot_traced, wanted_moa=REDDOT['dot_moa'], passed=abs(dot_traced - REDDOT['dot_moa']) < 0.01),
        collimation_along_the_axis=dict(what='Largest change in the dot direction when the eye moves 100 mm nearer or farther (centre and 6 mm off axis)',
                                        max_change_urad=zdep * 1e6, max_change_moa=zdep / MOA, passed=zdep / MOA < 0.05),
        window_see_through=dict(what='Residual power of the doublet for the scene (it should be a zero-power window)',
                                power_dioptre=rd['design']['window_see_through_power_dioptre'], passed=abs(rd['design']['window_see_through_power_dioptre']) < 0.01),
        polynomial_fit=dict(what='Order-5 polynomial of the beam direction against the ray trace over an 11.5 mm eye disc',
                            max_residual_urad=rd['parallax']['beam_direction_poly']['max_fit_residual_rad'] * 1e6,
                            passed=rd['parallax']['beam_direction_poly']['max_fit_residual_rad'] / MOA < 0.05),
        published_parallax=dict(
            what='Dot movement on the target as the eye sweeps edge to edge across the window, mean over 25, 50 and 100 yd and both axes',
            model_mean_moa=float(np.mean(sw)), model_by_distance_and_axis_moa=dict(distances_m=yd, sagittal=sw[0::2], tangential=sw[1::2]),
            published=dict(source='Green Eye Tactical, "Comparative Study of Red Dot Sight Parallax" (2017), as transcribed in a post on the accuratereloading.com optics forum '
                                  '(thread 7031016252), read 2026-11-17. Average deviation over all distances and testers.',
                           aimpoint_micro_t2_moa=4.5, aimpoint_comp_m2_moa=6.29, aimpoint_micro_t1_moa=9.68),
            verdict='The model sits below the published averages for three tube and micro sights. That study had human testers moving their heads, so its figures include '
                    'more than the optics; this is a plausibility check, not a calibration.',
            passed=0.5 < float(np.mean(sw)) < 9.68),
        published_brightness=dict(
            what='Top daylight setting against the brightest background the class is specified for',
            published='Aimpoint CompM4 product sheet: dot visible against a background luminance of 0.1 to 55,000 lx (seen in a search summary on 2026-11-17, not in the document itself)',
            background_luminance_cd_m2=L55k, background_note='55,000 lx on a 90 percent diffuse white surface: L = E * 0.9 / pi',
            top_setting_cd_m2=top, weber_contrast=top / (win['luminous_transmission'] * L55k), passed=top / (win['luminous_transmission'] * L55k) >= 3.0),
        click=dict(what='Click value against the class figure',
                   model_mm_at_100m=REDDOT['click_moa'] * MOA * 1e5, published_mm_at_100m=16.0, published_source='Aimpoint CompM4 user manual, section 1.1 Specification',
                   emitter_shift_per_click_um=REDDOT['click_moa'] * MOA * efl_trace * 1000,
                   emitter_travel_for_full_range_mm=REDDOT['travel_moa'] * MOA * efl_trace,
                   passed=abs(REDDOT['click_moa'] * MOA * 1e5 - 16.0) < 2.0),
    )
    ck['all_passed'] = all(v['passed'] for v in ck.values())
    return ck


def plots(rd, bright, o, ez):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pd = os.path.join(HERE, 'plots'); os.makedirs(pd, exist_ok=True)
    E0 = np.array([0, 0, ez]); u0 = o.dot_dir(E0)
    es = np.linspace(-11, 11, 23)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for D in (10, 25, 50, 100, 300):
        axs[0].plot(es, [o.parallax(np.array([e, 0, ez]), D * 1000.0, E0, u0)[0] / MOA for e in es], label=f'{D} m')
        axs[1].plot(es, [o.parallax(np.array([0, e, ez]), D * 1000.0, E0, u0)[1] / MOA for e in es], label=f'{D} m')
    axs[0].set_title('Sagittal (across the emitter plane)'); axs[1].set_title('Tangential (toward and away from the emitter)')
    for a in axs: a.set_xlabel('eye offset from the optical axis (mm)'); a.grid(alpha=0.3); a.axhline(0, color='k', lw=0.5)
    axs[0].set_ylabel('dot minus target direction (MOA)'); axs[1].legend(title='target at')
    fig.suptitle('Red dot parallax: exact ray trace of the Mangin collimator (simulation only)'); fig.tight_layout(); fig.savefig(os.path.join(pd, 'parallax.png'), dpi=110); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    Ls = np.logspace(-3, 4.6, 100)
    for s in bright['settings'][1:]:
        ax.loglog(Ls, s['dot_luminance_cd_m2'] / (0.954 * Ls), label=s['label'], color='C3' if s['label'].startswith('NV') else 'C0', alpha=0.4 + 0.05 * s['position'])
    ax.axhspan(8, 60, color='g', alpha=0.12); ax.axhline(3, color='k', ls=':'); ax.axhline(300, color='k', ls=':')
    ax.set_ylim(0.1, 1e5); ax.set_xlabel('scene luminance behind the dot (cd/m2)'); ax.set_ylabel('Weber contrast of the dot')
    ax.set_title('Dot contrast per switch position (green: crisp; dotted: wash-out and bloom)'); ax.grid(alpha=0.3, which='both')
    fig.tight_layout(); fig.savefig(os.path.join(pd, 'brightness.png'), dpi=110); plt.close(fig)


# ============================================================================ main
if __name__ == '__main__':
    print('designing the collimator...', flush=True)
    rd, o, ez = reddot_results()
    win = reddot_window()
    bright = reddot_brightness(win)
    bal = json.load(open(BALLISTICS))
    h = REDDOT['axis_over_bore_mm'] / 1000.0
    e2m = (RIFLE['crown_l_mm'] - REDDOT['eye_l_mm']) / 1000.0
    zero = zero_tables(bal, h, e2m, REDDOT['click_moa'] * MOA, '0.5 MOA', (('50m', 50.0), ('100m', 100.0), ('200m', 200.0), ('25m', 25.0)))
    zero['default'] = '50m'
    dot = reddot_reticle()
    write_dot_svg(dot, os.path.join(HERE, 'reticle', 'dot_2moa.svg'))
    # frames and sockets
    phi = math.radians(REDDOT['led_clock_deg']); c, s = math.cos(phi), math.sin(phi)
    lens_from_shooter = [[-c, s], [-s, -c]]            # [ex, ey] = M @ [right, up]
    so, rt, H = RIFLE['socket_optic_l_mm'], RIFLE['rail_top_mm'], REDDOT['axis_over_rail_mm']
    P3 = lambda L, right=0.0, up=0.0: [0.0 - right / 1000, (H + up) / 1000, (L - so) / 1000]
    wl = window_l_mm(); led_right, led_up = -o.led[1] * s, -o.led[1] * c
    front_l = REDDOT['tube_centre_l_mm'] + REDDOT['length_mm'] / 2; rear_l = front_l - REDDOT['length_mm']
    sockets = dict(socket_mount=[0, 0, 0], socket_eye=P3(REDDOT['eye_l_mm']), socket_objective=P3(wl), socket_rear_window=P3(rear_l + REDDOT['rear_inset_mm']),
                   socket_emitter=P3(wl + o.led[2], led_right, led_up))
    # parity samples for the JS runtime: exact trace values
    E0 = np.array([0, 0, ez]); u0 = o.dot_dir(E0)
    Ms = np.array(lens_from_shooter)
    samples = []
    for (r_, u_) in ((0, 0), (3, 0), (0, 3), (-6, 2), (5, -5), (0, 9), (9, 0), (-7, -7), (0, -11), (11, 0)):
        ex, ey = Ms @ np.array([r_, u_], float)
        E = np.array([ex, ey, ez])
        a = o.dot_dir(E, guess=u0[:2])[:2] - u0[:2]
        row = dict(eye_right_mm=r_, eye_up_mm=u_, beam_lens=[float(a[0]), float(a[1])], beam_shooter=[float(v) for v in Ms.T @ a], errors={})
        for D in (10, 25, 50, 100, 300):
            e = o.parallax(E, D * 1000.0, E0, u0)
            row['errors'][str(D)] = [float(v) for v in Ms.T @ e]
        samples.append(row)
    checks = run_checks(rd, o, ez, bright, win)
    doc = dict(
        meta=dict(title='Generic 2 MOA tube red-dot sight: optical system, zero tables and rendering model', generator='assets/optic-red-dot/optics/sim.py', credit='carpetshark',
                  units='millimetres, degrees, MOA or mrad as each key says; SI in the zero tables; sockets in metres',
                  ballistics_source='assets/hk416/ballistics/ballistics.json (' + bal['meta'].get('generator', 'sim.py') + ')',
                  class_references='External figures of the class come from the Aimpoint CompM4 user manual, section 1.1 (135 x 51 x 57 mm, 370 g, 2 MOA, 16 positions, unlimited eye relief, '
                                   '1 click = 16 mm at 100 m, +/- 2 m at 100 m). This is a generic sight: no maker\'s name, logo or trade dress; the optical prescription is solved here.'),
        rifle=RIFLE, body=REDDOT,
        frames=dict(asset='metres, +Z muzzle, +Y up, +X shooter\'s left; origin socket_mount = the rifle\'s socket_optic (rail top, on the centreline)',
                    shooter='eye offsets and angles as the shooter sees them: right and up; right = -X of the asset frame',
                    lens='the collimator\'s frame: ex sagittal, ey tangential (+ey points away from the emitter)',
                    lens_from_shooter=lens_from_shooter, shooter_from_lens=[[-c, -s], [s, -c]],
                    centred_eye_beam_lens=[float(u0[0]), float(u0[1])],
                    centred_eye_beam_note='direction of the dot for the centred eye relative to the mechanical axis (rad, lens frame); zeroing absorbs it, and every other angle here is relative to it'),
        sockets=sockets,
        optics=rd, window=win, brightness=bright,
        turrets=dict(click='0.5 MOA', click_mrad=0.5 * MOA * 1000, mm_at_100m=0.5 * MOA * 1e5, travel_moa=REDDOT['travel_moa'],
                     elevation='top, coin-slot adjuster under a screw cap; clip elevation_adjust', windage='right side, the same; clip windage_adjust',
                     mechanism='the adjusters move the emitter: %.1f um per click' % (0.5 * MOA * rd['design']['effective_focal_length_mm'] * 1000)),
        eye_relief='unlimited (a collimated dot). The design eye point %.0f mm behind the rear window only fixes the head position.' % (rear_l + REDDOT['rear_inset_mm'] - REDDOT['eye_l_mm']),
        reticle=dot, zero=zero, rendering=rendering_model(win), parity_samples=dict(doc='exact ray-trace values for optic-red-dot.js to reproduce: beam direction a (rad) and parallax error (rad, shooter right/up) per distance (m)', rows=samples),
        lens_trace=dict(doc='the numbers the runtime needs for its own exact trace (lens frame, mm; window vertex at the origin, +z toward the target)',
                        R1=o.R1, R2=o.R2, R3=o.R3, t1=o.t1, t2=o.t2, n=o.n, tilt_rad=o.tilt, led=[float(v) for v in o.led], eye_z=ez),
    )
    json.dump(rnd(doc, 12), open(os.path.join(HERE, 'reddot.json'), 'w'), indent=1)
    json.dump(rnd(checks, 8), open(os.path.join(HERE, 'checks.json'), 'w'), indent=1)
    plots(rd, bright, o, ez)
    print('design', rnd(rd['design'], 3))
    print('parallax-free distance m', rnd(rd['parallax']['parallax_free_distance_m'], 1))
    for r in rd['parallax']['table']:
        print('  %4d m  3mm %.2f  6mm %.2f  9mm %.2f  11mm %.2f MOA max | sweep %s' % (r['distance_m'], r['eye_3mm']['max_moa'], r['eye_6mm']['max_moa'], r['eye_9mm']['max_moa'], r['eye_11mm']['max_moa'], rnd(r['edge_to_edge_sweep_moa'], 2)))
    for zn, z in zero['ammo']['M855'].items():
        print(zn, 'bore %.3f mrad' % z['bore_angle_mrad'], 'clicks', z['clicks_up_from_centre'], 'cross', rnd(z['crossings_from_eye_m'], 1), 'max ord %.0f mm @%.0f' % (z['max_ordinate_mm'], z['max_ordinate_at_m']))
    for k, v in checks.items():
        if isinstance(v, dict): print('CHECK', k, 'PASS' if v['passed'] else 'FAIL', {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items() if isinstance(b, (int, float)) and a != 'passed'})
    print('all passed:', checks['all_passed'])
