#!/usr/bin/env python3
"""Generic 1-6x24 low-power variable optic (second focal plane): optical simulation.

    python3 sim.py        writes lpvo.json, checks.json, reticle/*.svg, plots/*.png   (about 1 minute)

What is simulated (first-order optical design and geometry of pupils, no engine code):
  * a thin-lens zoom: objective, field lens, two erector groups on cams, reticle-plane field lens, eyepiece, fitted
    to the published external figures of 1-6x24 scopes; cams solved for any magnification
  * per magnification: aperture stop, entrance and exit pupil, eye relief, real and apparent field, vignetting
  * the eye box: how far the eye can move sideways and along the axis, and the scope shadow it sees when it does
  * mounting and zero on the HK416 (assets/hk416): click and hold tables from its ballistics tables
  * an original BDC reticle whose marks are computed from those tables for M855 and Mk 262
  * a rendering model for a picture-in-picture scope
Units: millimetres and radians inside the optics; SI in the tables unless a key says otherwise.
Frame of the asset: the HK416's (metres, +Z muzzle, +Y up, +X shooter's left), origin at socket_mount, which sits on
the rifle's socket_optic. Credit: carpetshark.
"""
import json, math, os, sys
import numpy as np

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
LPVO = dict(
    name='generic 1-6x24 second-focal-plane LPVO',
    axis_over_rail_mm=43.18,        # a 1.70 in mount, one of the common heights (1.5, 1.7, 1.93 in). Chosen: the lowest of them that clears the folded rear sight
    ocular_rear_l_mm=-170.0,        # rifle L of the rear face of the eyepiece: my placement, it puts the eye where the irons put it
    length_mm=257.0,                # class: Vortex Razor HD Gen II-E 1-6x24, 10.1 in
    tube_mm=30.0,                   # class: 30 mm main tube (the same scope, the Trijicon VCOG is a one-piece body, the SIG Tango6T 30 mm)
    objective_clear_mm=24.0,        # the brief (1-6x24)
    ocular_clear_mm=42.0, ocular_od_mm=46.0,          # inferred: typical for the class
    ocular_lens_inset_mm=3.0, objective_lens_inset_mm=10.0,   # inferred
    click_mrad=0.1,                 # class: 0.1 mrad or 1/2 MOA clicks (the Razor is offered in both)
    travel_mrad=40.0,               # class: the Razor lists 150 MOA (43.6 mrad) of total travel
    clicks_per_rev=100,             # inferred
    parallax_m=100.0,               # class: fixed parallax at 100 yd (Razor); 100 m here
    mag_min=1.0, mag_max=6.0, throw_deg=180.0,        # inferred: half a turn of the power ring from 1x to 6x
    mass_kg=0.61,                   # class: 21.5 oz (609 g) for the Razor, without the mount
    mount_mass_kg=0.20,             # inferred: a one-piece cantilever mount
)
LPVO['axis_over_bore_mm'] = RIFLE['rail_top_mm'] + LPVO['axis_over_rail_mm']
PUBLISHED = dict(
    doc='Published external figures of three 1-6x24 scopes, read on 2026-11-17. ft at 100 yd for the field of view.',
    vortex_razor_hd_gen2e=dict(focal_plane='second', fov_ft_100yd=[115.2, 20.5], eye_relief_in=[4.0, 4.0], length_in=10.1, weight_oz=21.5, tube_mm=30, click='1/2 MOA', travel_moa=150, parallax='100 yd',
                               source='retailer technical specification page (scottcountry.co.uk, "Vortex Razor HD Gen II-E 1-6x24 Riflescope - Technical Specification")'),
    trijicon_vcog=dict(focal_plane='first', fov_ft_100yd=[95.0, 15.9], eye_relief_in=[4.0, 4.0], exit_pupil_mm=[10.4, 3.8],
                       source='Trijicon VCOG spec sheet and product catalogue as summarised by a web search: field 95 to 15.9 ft, eye relief 4 in constant, exit pupil 0.41 to 0.15 in'),
    sig_tango6t=dict(focal_plane='first', fov_ft_100yd=[105.8, 17.7], eye_relief_in=[3.9, 4.1], exit_pupil_mm=[11.4, 4.0],
                     source='SIG product page and a review (thefirearmblog.com, 2021) as summarised by a web search: field 105.8 to 17.7 ft, eye relief 3.9 to 4.1 in, exit pupil 11.4 to 4 mm'),
)


# ============================================================================ small helpers
def rnd(x, n=4):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, n) for v in x]
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (float, np.floating)):
        return round(float(x), n)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def pupil_mm(L):
    """Stanley and Davies (1995) pupil diameter for a 60 degree adapting field of luminance L (cd/m^2)."""
    f = (L * 2827.0 / 846.0) ** 0.41
    return 7.75 - 5.75 * f / (f + 2.0)


# ============================================================================ 1. the zoom: paraxial design
MAGS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]


class Lpvo:
    """Thin-lens model. z along the scope from the objective (z = 0) to the eye. All apertures are radii in mm.
    The focal lengths come from a Nelder-Mead search (in the old build's tools, not kept) that minimised the spread of
    the eye relief over 1-6x with the first image fitting inside the 30 mm tube. They are a design of mine fitted to
    the class, not a measurement of any scope."""
    FO, FE = 62.6, 42.5          # objective and eyepiece focal lengths
    F1, F2 = 23.2, 23.1          # the two moving erector groups
    LE = 76.4                    # first image plane to second image plane
    FFL = 31.0                   # field lens at the first image plane
    FSL = -78.5                  # field lens at the second image plane (the reticle cell's collector)
    R_OBJ = 12.0                 # 24 mm objective
    R_FFP = 12.0                 # first-image-plane stop: it trims the 1x field to the published 115 ft at 100 yd
    R_E1 = R_E2 = 8.0            # erector lens clear radii
    R_OC = 21.0                  # 42 mm ocular clear aperture
    EP_MAX = 10.4                # exit pupil ceiling, set by a stop in the erector cell conjugate to the objective. Published: 10.4 mm (VCOG) and 11.4 mm (Tango6T) at 1x
    AFOV_HALF = math.radians(11.58)   # apparent half field: 20.5 ft at 100 yd at 6x (published for the Razor)

    def __init__(self):
        self.R_FS = self.FE * math.tan(self.AFOV_HALF)
        self.cams = {}

    # ---- cams ----------------------------------------------------------------------------------------------
    def _g(self, a, M):
        """Imaging condition of the erector for its first group a mm behind the first image plane: zero when the pair
        images the first plane onto the second at lateral magnification -M FE / FO. Also returns the second group's place."""
        m = M * self.FE / self.FO
        f1, f2, L = self.F1, self.F2, self.LE
        with np.errstate(all='ignore'):
            s1 = a * f1 / (a - f1); m1 = -s1 / a; I = a + s1; m2 = (-m) / m1
            return -f2 * (1 - m2) ** 2 / m2 - (L - I), I + f2 * (1 - 1 / m2)

    def cam_roots(self, M, n=6000):
        a = np.linspace(2.0, self.LE - 6, n)
        g, b = self._g(a, M)
        out = []
        for i in np.where((g[:-1] * g[1:] < 0) & (np.abs(g[:-1]) < 1e4) & (np.abs(g[1:]) < 1e4))[0]:
            lo, hi = a[i], a[i + 1]
            glo = self._g(lo, M)[0]
            for _ in range(60):                       # bisection to machine precision
                mid = 0.5 * (lo + hi); gm = self._g(mid, M)[0]
                if (gm < 0) == (glo < 0): lo, glo = mid, gm
                else: hi = mid
            aa = 0.5 * (lo + hi); bb = float(self._g(aa, M)[1])
            if 3 < aa < bb - 2 and bb < self.LE - 3:
                out.append((float(aa), bb))
        return out

    def solve_all(self, mags):
        prev = None
        for M in sorted(mags, reverse=True):
            roots = self.cam_roots(M)
            if not roots:
                raise SystemExit(f'no cam solution at {M}x')
            c = min(roots, key=lambda c: (abs(c[0] - prev[0]) + abs(c[1] - prev[1])) if prev else -c[1])
            self.cams[M] = c; prev = c

    def cam(self, M):
        """Cam positions for any magnification: the root nearest the interpolated table (what the runtime does)."""
        if M in self.cams:
            return self.cams[M]
        ms = sorted(self.cams)
        ga = np.interp(math.log(M), [math.log(m) for m in ms], [self.cams[m][0] for m in ms])
        gb = np.interp(math.log(M), [math.log(m) for m in ms], [self.cams[m][1] for m in ms])
        return min(self.cam_roots(M), key=lambda c: abs(c[0] - ga) + abs(c[1] - gb))

    # ---- first order ---------------------------------------------------------------------------------------
    def layout(self, M):
        a, b = self.cam(M)
        zf = self.FO
        return [('objective', 0.0, self.FO, self.R_OBJ), ('field_lens', zf, self.FFL, self.R_FFP),
                ('erector_1', zf + a, self.F1, self.R_E1), ('erector_2', zf + b, self.F2, self.R_E2),
                ('field_stop', zf + self.LE, self.FSL, self.R_FS), ('ocular', zf + self.LE + self.FE, self.FE, self.R_OC)]

    def trace(self, M, y, u, els=None):
        """Paraxial trace of a ray arriving at the objective at height y with slope u. Returns the heights at each element and the exit ray."""
        els = els or self.layout(M)
        hs = []
        for i, (name, z, f, r) in enumerate(els):
            hs.append((name, y, r))
            if f:
                u -= y / f
            if i + 1 < len(els):
                y += u * (els[i + 1][1] - z)
        return hs, y, u

    def first_order(self, M):
        els = self.layout(M)
        hs, y, u = self.trace(M, 1.0, 0.0, els)
        _, yc, uc = self.trace(M, 0.0, 0.01, els)     # chief ray through the objective centre
        ang_mag = uc / 0.01
        er = -yc / uc                                 # where it crosses the axis behind the ocular: the exit pupil
        lens_limit = min(r / abs(h) for name, h, r in hs if name != 'field_stop' and abs(h) > 1e-6)
        h_in = min(lens_limit, self.EP_MAX * M / 2)
        stop = 'objective' if abs(h_in - self.R_OBJ) < 1e-6 else ('erector-cell stop' if h_in < lens_limit else 'erector lens')
        return dict(M=M, angular_magnification=ang_mag, afocal_residual=u, entrance_pupil_mm=2 * h_in, exit_pupil_mm=2 * h_in / M, aperture_stop=stop, eye_relief_mm=er,
                    marginal_heights={name: abs(h) * h_in for name, h, r in hs})

    def field(self, M):
        """Tangent of the real half field and of the apparent half field. The second-plane stop sets it, unless the
        first-plane stop is tighter (it is at 1x: the low-power tunnel)."""
        tan_a = math.tan(self.AFOV_HALF); tan_real = tan_a / M
        if self.FO * tan_real > self.R_FFP:
            tan_real = self.R_FFP / self.FO; tan_a = tan_real * M
        return tan_real, tan_a

    def transmission(self, M, tan_th, n=41):
        """Fraction of the on-axis beam that survives every aperture for a field angle (vignetting), by pupil sampling."""
        els = self.layout(M)
        h = self.first_order(M)['entrance_pupil_mm'] / 2
        ok0 = ok = 0
        for i in range(n):
            for j in range(n):
                x, y = h * (2 * i / (n - 1) - 1), h * (2 * j / (n - 1) - 1)
                if x * x + y * y > h * h:
                    continue
                ok0 += 1
                hx, _, _ = self.trace(M, x, 0.0, els)
                hy, _, _ = self.trace(M, y, tan_th, els)
                ok += all(a * a + b * b <= r * r * 1.0001 for (nm, a, r), (_, b, _) in zip(hx, hy))
        return ok / max(ok0, 1)

    def system_matrix(self, M):
        """Ray-transfer matrix from just before the objective to just after the ocular (a second code path for the checks)."""
        els = self.layout(M)
        S = np.eye(2)
        for i, (name, z, f, r) in enumerate(els):
            if f:
                S = np.array([[1, 0], [-1.0 / f, 1]]) @ S
            if i + 1 < len(els):
                S = np.array([[1, els[i + 1][1] - z], [0, 1]]) @ S
        return S


def design_lpvo():
    s = Lpvo()
    s.solve_all(MAGS)
    return s


# ============================================================================ 2. the eye box
def disc_overlap(r1, r2, d):
    """Area of intersection of two discs."""
    d = abs(d)
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    b = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    c = 0.5 * math.sqrt(max(0.0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)))
    return a + b - c


def eyebox_mask(ex, ey, dz, ax, ay, exit_pupil_mm, eye_pupil_mm):
    """Scope-shadow mask (0..1, 1 = as bright as the centred eye sees it).
    ex, ey: eye offset from the optical axis (mm, + right/up). dz: eye behind (+) or ahead (-) of the exit pupil plane (mm).
    ax, ay: apparent field direction as tangents (+ right/up).
    Every image point leaves the eyepiece as a parallel bundle that fills the exit pupil disc and travels along its
    apparent direction: light seen to the right travels leftward on its way to the eye. dz behind the exit pupil that
    bundle is the exit pupil disc shifted by -dz * a; the eye collects the part that falls in its own pupil."""
    rp, re = exit_pupil_mm / 2, eye_pupil_mm / 2
    sep = math.hypot(ex + dz * ax, ey + dz * ay)
    return disc_overlap(rp, re, sep) / (math.pi * min(rp, re) ** 2)


def lpvo_results(s):
    P = LPVO
    per_mag = []
    for M in MAGS:
        fo = s.first_order(M)
        tan_real, tan_a = s.field(M)
        fr = [0.0, 0.25, 0.5, 0.7, 0.85, 0.95, 1.0]
        vig = [s.transmission(M, tan_real * f, n=31) for f in fr]
        ep = fo['exit_pupil_mm']
        row = dict(
            magnification=M,
            erector_cam_mm={'group_1_from_first_image_plane': float(s.cams[M][0]), 'group_2_from_first_image_plane': float(s.cams[M][1])},
            power_ring_deg=float(P['throw_deg'] * math.log(M) / math.log(P['mag_max'])),
            aperture_stop=fo['aperture_stop'], entrance_pupil_mm=fo['entrance_pupil_mm'], exit_pupil_mm=ep,
            eye_relief_mm=fo['eye_relief_mm'],
            real_fov_deg=2 * math.degrees(math.atan(tan_real)), apparent_fov_deg=2 * math.degrees(math.atan(tan_a)),
            tan_half_real=tan_real, tan_half_apparent=tan_a, field_limited_by='first-plane stop' if s.FO * math.tan(s.AFOV_HALF) / M > s.R_FFP else 'second-plane field stop',
            fov_m_at_100m=2 * 100 * tan_real, fov_ft_at_100yd=2 * 300 * tan_real,
            vignetting={'field_fraction': fr, 'relative_illumination': vig},
            reticle_scale=P['mag_max'] / M,     # SFP: the reticle subtends this many times its 6x value
            twilight_factor=math.sqrt(M * 24.0),
        )
        for pe in (3.0, 6.0):
            lat_full = abs(ep - pe) / 2
            lat_half = next(x for x in np.arange(0, 30, 0.01) if eyebox_mask(x, 0, 0, 0, 0, ep, pe) <= 0.5)
            lat_gone = (ep + pe) / 2
            ax_half = next((z for z in np.arange(0, 120, 0.1) if eyebox_mask(0, 0, z, tan_a, 0, ep, pe) <= 0.5), 120.0)
            ax_gone = (ep + pe) / 2 / tan_a
            row[f'eyebox_eye_pupil_{pe:g}mm'] = dict(
                lateral_no_dimming_mm=lat_full, lateral_half_brightness_mm=float(lat_half), lateral_blackout_mm=lat_gone,
                axial_edge_half_brightness_mm=float(ax_half), axial_edge_lost_mm=ax_gone,
                image_brightness_vs_naked_eye=min(1.0, (ep / pe) ** 2))
        per_mag.append(row)
    par = []
    for M in (1.0, 3.0, 6.0):
        ep = next(r for r in per_mag if r['magnification'] == M)['exit_pupil_mm']
        for D in (10, 25, 55, 100, 200, 300, 600):
            e = ep / 2          # the eye pupil centred on the exit pupil's edge: the largest offset that still shows half an image
            ang = M * e / 1000.0 * (1.0 / D - 1.0 / P['parallax_m'])
            par.append(dict(magnification=M, distance_m=D, eye_offset_mm=e, error_mrad=ang * 1000, error_moa=ang / MOA, error_mm_on_target=abs(ang) * D * 1000))
    er = [r['eye_relief_mm'] for r in per_mag]
    return dict(
        focal_plane='second',
        focal_plane_reason='Second focal plane. The reticle stays the same bold size at every power, so at 1x (where a carbine spends most of its time) the centre dot and ring are '
                           'as quick as a red dot; a first-plane reticle fine enough to hold with at 6x shrinks to a speck at 1x. The cost: the BDC marks are true only at 6x. '
                           'At another power every subtension is 6 / M times larger in object space (reticle_scale).',
        design=dict(
            type='thin-lens (first-order) zoom: objective, field lens, two-group erector on cams, reticle-plane field lens, eyepiece',
            objective_f_mm=s.FO, eyepiece_f_mm=s.FE, erector_f_mm=[s.F1, s.F2], field_lens_f_mm=s.FFL, reticle_plane_field_lens_f_mm=s.FSL, exit_pupil_ceiling_mm=s.EP_MAX,
            first_to_second_image_plane_mm=s.LE, optical_length_mm=s.FO + s.LE + s.FE, apparent_half_field_rad=s.AFOV_HALF,
            stops_radius_mm=dict(objective=s.R_OBJ, first_image_plane=s.R_FFP, erector=s.R_E1, second_plane_field_stop=s.R_FS, ocular=s.R_OC),
            stop_model='From 6x down to %.2fx the objective rim is the aperture stop (exit pupil = 24 / M). Below that a stop in the erector cell, conjugate to the objective, holds the exit pupil at the ceiling.' % (2 * s.R_OBJ / s.EP_MAX),
            note='A first-order design fitted to the published external figures of 1-6x24 scopes. It is not a lens prescription: aberrations come from the stated models, not from this layout. '
                 'Its principal planes span %.1f mm; the body is %.0f mm long, because real groups are thick.' % (s.FO + s.LE + s.FE, P['length_mm'])),
        eye_relief_summary=dict(min_mm=min(er), max_mm=max(er), at_1x_mm=er[0], at_6x_mm=er[-1]),
        by_magnification=per_mag,
        eyebox_function=dict(
            doc='mask(ex, ey, dz, ax, ay) = overlap_area(disc(exit_pupil / 2), disc(eye_pupil / 2), separation) / (pi * min(r)^2), '
                'separation = hypot(ex + dz * ax, ey + dz * ay). ex, ey = eye offset from the axis (mm, right and up); dz = eye distance behind the exit pupil plane (mm, negative = too close); '
                'ax, ay = tangent of the apparent field angle of the pixel (right and up). Multiply by the vignetting profile and by image_brightness.',
            eye_pupil_mm_from_luminance='d = 7.75 - 5.75 * f / (f + 2), f = (L * 2827 / 846)^0.41 (Stanley and Davies 1995, 60 degree field)',
            behaviour='dz = 0: the whole picture dims evenly and then blacks out as the eye moves sideways. dz != 0: a crescent shadow enters from one side as the eye moves sideways and, '
                      'with the eye centred, the field tunnels to tan(a) < (exit_pupil + eye_pupil) / (2 |dz|). Too far back, the shadow enters from the side the eye moved toward; too close, from the opposite side.'),
        parallax=dict(setting_m=P['parallax_m'],
                      formula='error (rad, object space) = M * e * (1/D - 1/parallax_distance); e = eye offset in the exit pupil (m). The reticle appears to move over the target by this much.',
                      worst_case=par),
        distortion=dict(model='r_d = r * (1 + k1 * r^2), r = field radius normalised to the field stop (r = 1 at the edge); positive = pincushion',
                        k1_at_1x=0.010, k1_at_6x=0.030, interpolation='linear in log(M)', true_magnification_at_1x=1.0,
                        source='inferred: typical edge distortion of 1-6x scopes (about 1 percent at 1x, 2 to 4 percent at 6x); a thin-lens model cannot predict it'),
        transmission=dict(luminous=0.90, linear_srgb=[0.905, 0.915, 0.880],
                          source='inferred: about 90 percent for a fully multi-coated 1-6x; a slight warm cast is typical'),
        illumination=dict(
            what='centre dot only (an LED lights the etched dot), red 650 nm', settings=11, daylight_bright=True,
            dot_luminance_cd_m2=[0.0] + [float(6.0e4 / 2.6 ** (10 - k)) for k in range(1, 11)],
            off_appearance='the dot is etched, so it is black when the illumination is off',
            source='inferred: a "daylight bright" centre needs roughly 5e4 cd/m^2 to hold a Weber contrast of 3 on a sunlit paper target (20,000 cd/m^2)'),
    )


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


# ============================================================================ 4. the reticle (an original design)
STROKE_DIGITS = {   # 3 x 5 grid stroke digits, polylines in units (x 0..2, y 0..4, y down)
    '3': [[(0, 0), (2, 0), (2, 4), (0, 4)], [(0.6, 2), (2, 2)]],
    '4': [[(0, 0), (0, 2), (2, 2)], [(2, 0), (2, 4)]],
    '5': [[(2, 0), (0, 0), (0, 2), (2, 2), (2, 4), (0, 4)]],
    '6': [[(2, 0), (0, 0), (0, 4), (2, 4), (2, 2), (0, 2)]],
}
BDC_ZERO = '200m'
BDC_DISTANCES = (300, 400, 500, 600)


def bdc_reticle(zero, bal, e2m, h, wind_mps=5.0):
    """Reticle 'staple BDC': primitives in mrad at 6x (x right, y up; drops are negative y).
    Each range mark is a staple: the cross-bar is the M855 hold, the tips of the two short legs hanging from its ends
    are the Mk 262 hold. Both loads zeroed at 200 m on the centre dot."""
    hm = {r['distance_m']: r for r in zero['ammo']['M855'][BDC_ZERO]['holds']}
    hk = {r['distance_m']: r for r in zero['ammo']['Mk262'][BDC_ZERO]['holds']}
    prim = []
    RING = 2.6
    line = lambda x0, y0, x1, y1, w, tag='etched': prim.append(dict(type='line', p0=[x0, y0], p1=[x1, y1], width=w, layer=tag))
    prim.append(dict(type='dot', c=[0, 0], d=0.30, layer='illuminated'))
    for k in range(4):      # broken ring: four arcs, gaps at 12, 3, 6 and 9 o'clock
        prim.append(dict(type='arc', c=[0, 0], r=RING, a0=18 + 90 * k, a1=72 + 90 * k, width=0.14, layer='etched'))
    marks = []
    for D in BDC_DISTANCES:
        y = -hm[D]['hold_mrad']; yk = -hk[D]['hold_mrad']
        half = 0.5 * 0.45 / D * 1000          # the bar is as wide as a 45 cm (shoulder-width) target at that distance
        line(-half, y, half, y, 0.07)
        for sgn in (-1, 1):                   # the legs: from the bar down to the Mk 262 hold
            line(sgn * half, y + 0.035, sgn * half, yk, 0.05)
        wind = hm[D]['wind_10mph_mrad'] * wind_mps / 4.4704
        for sgn in (-1, 1):
            prim.append(dict(type='dot', c=[sgn * wind, y], d=0.14, layer='etched'))
        s = 0.16; ox, oy = wind + 0.45, y + 2 * s        # stroke digit to the right of the wind dot
        for pl in STROKE_DIGITS[str(D // 100)]:
            prim.append(dict(type='polyline', pts=[[ox + px * s, oy - py * s] for px, py in pl], width=0.05, layer='etched'))
        marks.append(dict(distance_m=D, m855_hold_mrad=-y, mk262_hold_mrad=-yk, leg_length_mrad=y - yk, bar_half_width_mrad=half, bar_spans_m=0.45,
                          wind_dot_mrad=wind, wind_mps=wind_mps, wind_note='M855, full-value wind'))
    y_last = min(-hk[BDC_DISTANCES[-1]]['hold_mrad'], -hm[BDC_DISTANCES[-1]]['hold_mrad'])
    line(0, -RING - 0.25, 0, -hm[BDC_DISTANCES[-1]]['hold_mrad'], 0.045)      # thin stem from under the ring to the last bar
    for sgn in (-1, 1):      # side bars: thin inner section with mrad ticks, heavy outer posts to the field edge
        line(sgn * 3.2, 0, sgn * 9.0, 0, 0.07)
        for t in (4, 5, 6, 7, 8):
            ln = 0.35 if t != 5 else 0.6
            line(sgn * t, -ln, sgn * t, ln, 0.05)
        line(sgn * 9.0, 0, sgn * 40.0, 0, 0.6)
    line(0, y_last - 1.2, 0, -40.0, 0.6)       # heavy bottom post
    # second focal plane: what each mark means at lower powers (M855)
    d = Drop(bal['ammo']['M855']['table']); th = zero['ammo']['M855'][BDC_ZERO]['bore_angle_mrad'] / 1000
    hold = lambda D: -(float(d.fy(D - e2m)) + th * (D - e2m) - h) / D * 1000
    from scipy.optimize import brentq
    other = []
    for M in (3.0, 4.0, 5.0, 6.0):
        row = dict(magnification=M, marks=[])
        for mk in marks:
            want = mk['m855_hold_mrad'] * 6.0 / M
            row['marks'].append(dict(mark=mk['distance_m'], subtends_mrad=want, true_distance_m=float(brentq(lambda D: hold(D) - want, 200.0, 650.0)) if hold(650.0) > want else None))
        other.append(row)
    return dict(
        name='staple BDC', design='original (carpetshark): not a copy of any maker\'s reticle. The staple-shaped range marks carry two loads at once.',
        focal_plane='second', true_at_magnification=6.0, units='mrad at 6x; at magnification M every subtension is 6 / M times larger in object space',
        zero='200 m on the centre dot, for either load (re-zero when the load changes: the two differ by %.2f mrad of bore angle)' % (
            zero['ammo']['Mk262'][BDC_ZERO]['bore_angle_mrad'] - zero['ammo']['M855'][BDC_ZERO]['bore_angle_mrad']),
        how_to_read='Centre dot: 200 m. Each staple below it is 300, 400, 500, 600 m (numbered). Hold the cross-bar on the target for M855, the tips of the legs for Mk 262. '
                    'The bar is as wide as a 45 cm target at its distance, so it also ranges. The two small dots beside each bar are the hold for a 5 m/s full-value wind (M855).',
        centre_dot_mrad=0.30, ring_radius_mrad=RING,
        ring_use='at 1x the ring is %.1f mrad in radius: it frames a 45 cm wide target at %.0f m and makes a fast close-range aiming circle' % (RING * 6, 0.225 / (RING * 6e-3)),
        bdc_marks=marks, marks_at_other_powers=other, primitives=prim, field_radius_mrad_at_6x=None)


def reticle_svg(ret, extent, path, bg=None):
    """extent: half-width of the drawing in mrad."""
    S = 1000.0 / (2 * extent)
    X = lambda x: 500 + x * S
    Y = lambda y: 500 - y * S
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">',
           f'<title>{ret["name"]} (original design, carpetshark). The drawing is {2 * extent:g} mrad wide at 6x.</title>']
    if bg:
        out.append(f'<rect width="1000" height="1000" fill="{bg}"/>')
    col = {'etched': '#0a0a0a', 'illuminated': '#ff2a12'}
    for p in ret['primitives']:
        c = col[p['layer']]
        if p['type'] == 'line':
            out.append(f'<line x1="{X(p["p0"][0]):.2f}" y1="{Y(p["p0"][1]):.2f}" x2="{X(p["p1"][0]):.2f}" y2="{Y(p["p1"][1]):.2f}" stroke="{c}" stroke-width="{p["width"] * S:.2f}"/>')
        elif p['type'] == 'dot':
            out.append(f'<circle cx="{X(p["c"][0]):.2f}" cy="{Y(p["c"][1]):.2f}" r="{p["d"] / 2 * S:.2f}" fill="{c}"/>')
        elif p['type'] == 'arc':
            a0, a1 = math.radians(p['a0']), math.radians(p['a1'])
            x0, y0 = X(p['c'][0] + p['r'] * math.cos(a0)), Y(p['c'][1] + p['r'] * math.sin(a0))
            x1, y1 = X(p['c'][0] + p['r'] * math.cos(a1)), Y(p['c'][1] + p['r'] * math.sin(a1))
            out.append(f'<path d="M {x0:.2f} {y0:.2f} A {p["r"] * S:.2f} {p["r"] * S:.2f} 0 0 0 {x1:.2f} {y1:.2f}" fill="none" stroke="{c}" stroke-width="{p["width"] * S:.2f}"/>')
        elif p['type'] == 'polyline':
            pts = ' '.join(f'{X(x):.2f},{Y(y):.2f}' for x, y in p['pts'])
            out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="{p["width"] * S:.2f}" stroke-linejoin="round" stroke-linecap="round"/>')
    out.append('</svg>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write('\n'.join(out) + '\n')


# ============================================================================ 5. rendering model (picture in picture)
def rendering_model(lv):
    return dict(
        frame='Asset frame (metres, +Z muzzle, +Y up, +X shooter\'s left), origin socket_mount. The optical axis runs from socket_eye through socket_ocular_lens to socket_objective.',
        render_target=True,
        passes=['1. World pass: the normal scene camera at the shooter\'s eye.',
                '2. Scope pass into a square render target: a camera at socket_objective looking along the optical axis, full field = real_fov_deg(M). '
                'Bias the scene level of detail as for a camera M times closer.',
                '3. Composite on the ocular lens of the optic mesh (material lens_ocular) with the shader below. The body is ordinary opaque geometry, '
                'so the housing occludes the lens for free; that is what makes the picture move correctly with the eye.'],
        render_target_px='512 at 1x to 1024 at 6x is enough for a 1080p frame',
        shader=['a = field direction of the pixel as seen from the eye: tangents (right, up) of the angle between the view ray and the optical axis. The image is at infinity, '
                'so it is fixed in angle while the housing slides over it; do not use the pixel\'s UV on the lens.',
                'r = |a| / tan_half_apparent(M). If r > 1: black (field stop), with a 1.5 percent soft edge.',
                'Distortion: r_src = r / (1 + k1 * r^2); uv = 0.5 + 0.5 * r_src * a / |a| (flip nothing: the erector makes the picture upright).',
                'colour = render_target(uv) * transmission * vignette(r, M) * image_brightness(M, eye pupil).',
                'Reticle: draw it in the same angle space, r scaled by reticle_scale(M) (second focal plane: constant on screen while the scene grows behind it). '
                'The etched layer multiplies toward black; the illuminated dot adds. Shift the reticle by M * parallax(e, D) if depth is available.',
                'Eye box: colour *= mask(ex, ey, dz, a) from eyebox_function with exit_pupil(M) and the eye pupil for the scene luminance; dz = (eye distance behind the ocular lens) - eye_relief(M). This is the scope shadow.',
                'Inside the lens but outside the image circle: black tube wall. Optional edge colour fringe: sample R and B at r * (1 -/+ 0.002 * r^2).'],
        parameters=dict(by_magnification='by_magnification[*]: tan_half_real, tan_half_apparent, exit_pupil_mm, eye_relief_mm, vignetting',
                        vignette='interpolate vignetting.relative_illumination over field_fraction, then multiply by cos^4 of the apparent angle',
                        both_eyes_open='at 1x the true magnification is 1.00, so the picture lines up with the world pass around the housing'),
        runtime='OpticLPVO.state(M) and OpticLPVO.shade(state, eye, a) implement exactly these formulas; the sample page uses them per pixel.')


# ============================================================================ 6. checks
def run_checks(s, lv, zero, bdc):
    rows = []; worst_c = worst_m = worst_er = 0.0
    for M in MAGS + [1.1, 2.2, 3.3, 4.7, 5.9]:
        S = s.system_matrix(M); fo = s.first_order(M)
        mag = abs(S[1, 1]); er = -S[0, 1] / S[1, 1]
        # the Lagrange invariant: (ray height * field angle) is the same at the entrance and exit pupils
        hs, y_out, u_out = s.trace(M, 1.0, 0.0)
        rows.append(dict(magnification=M, matrix_C=float(S[1, 0]), matrix_magnification=float(mag), matrix_eye_relief_mm=float(er), trace_eye_relief_mm=fo['eye_relief_mm'],
                         beam_compression=float(1.0 / abs(y_out))))
        worst_c = max(worst_c, abs(S[1, 0])); worst_m = max(worst_m, abs(mag - M) / M, abs(1.0 / abs(y_out) - M) / M); worst_er = max(worst_er, abs(er - fo['eye_relief_mm']))
    by = {r['magnification']: r for r in lv['by_magnification']}
    ft = lambda M: by[M]['fov_ft_at_100yd']
    pub = PUBLISHED
    ep6 = by[6.0]['exit_pupil_mm']; ep1 = by[1.0]['exit_pupil_mm']
    er_in = [lv['eye_relief_summary']['min_mm'] / 25.4, lv['eye_relief_summary']['max_mm'] / 25.4]
    # eye box: the disc-overlap formula against brute-force sampling of rays through the two pupils
    rng = np.random.default_rng(7); worst_mc = 0.0; mc = []
    for (ex, dz, ax, ep, pe) in ((1.0, 0.0, 0.0, 4.0, 3.0), (2.5, 0.0, 0.0, 4.0, 3.0), (0.0, 15.0, 0.2, 4.0, 3.0), (3.0, -10.0, 0.15, 10.4, 6.0), (4.0, 20.0, 0.1, 6.0, 3.0)):
        n = 400000
        # points uniformly over the eye pupil; light seen at +ax travels toward -x, so dz earlier (at the exit pupil plane) it was at x + dz * ax
        rr = (pe / 2) * np.sqrt(rng.random(n)); tt = 2 * math.pi * rng.random(n)
        px = ex + rr * np.cos(tt) + dz * ax; py = rr * np.sin(tt)
        frac = float(np.mean(px * px + py * py <= (ep / 2) ** 2)) * (pe / 2) ** 2 / min(pe / 2, ep / 2) ** 2
        f = eyebox_mask(ex, 0, dz, ax, 0, ep, pe)
        mc.append(dict(eye_offset_mm=ex, dz_mm=dz, tan_field=ax, exit_pupil_mm=ep, eye_pupil_mm=pe, formula=f, sampled=frac)); worst_mc = max(worst_mc, abs(f - frac))
    ck = dict(
        afocal_and_magnification=dict(
            what='Ray-transfer matrix of the whole scope at 18 magnifications (a second code path): it must be afocal (C = 0), magnify by M, compress the beam by M (Lagrange invariant), '
                 'and put the exit pupil where the chief-ray trace does',
            max_abs_C_per_mm=worst_c, max_magnification_error=worst_m, max_eye_relief_difference_mm=worst_er, rows=rows,
            passed=worst_c < 1e-9 and worst_m < 1e-9 and worst_er < 1e-6),
        exit_pupil=dict(
            what='Exit pupil = objective / magnification while the objective is the stop (thin-lens relation), against published exit pupils',
            model_6x_mm=ep6, relation_24_over_6_mm=24.0 / 6.0, published_6x_mm=[pub['trijicon_vcog']['exit_pupil_mm'][1], pub['sig_tango6t']['exit_pupil_mm'][1]],
            model_1x_mm=ep1, published_1x_mm=[pub['trijicon_vcog']['exit_pupil_mm'][0], pub['sig_tango6t']['exit_pupil_mm'][0]],
            note='At 1x no real scope shows a 24 mm exit pupil: an internal stop takes over. The model\'s ceiling is set to the lower published figure.',
            passed=abs(ep6 - 4.0) < 1e-6 and 3.8 <= ep6 <= 4.0 and 10.4 <= ep1 <= 11.4),
        field_of_view=dict(
            what='Field of view at 1x and 6x against three published scopes (ft at 100 yd)',
            model=[ft(1.0), ft(6.0)], published={k: pub[k]['fov_ft_100yd'] for k in ('vortex_razor_hd_gen2e', 'trijicon_vcog', 'sig_tango6t')},
            ratio_model=ft(1.0) / ft(6.0), ratio_published={k: pub[k]['fov_ft_100yd'][0] / pub[k]['fov_ft_100yd'][1] for k in ('vortex_razor_hd_gen2e', 'trijicon_vcog', 'sig_tango6t')},
            note='The model is fitted to the Razor\'s two figures, so agreement with it is by construction. The check is the ratio: a pure zoom gives 6.00 (VCOG 5.97, Tango6T 5.98); '
                 'the Razor\'s 5.62 means a second stop limits its 1x field, which is what the model\'s first-plane stop does.',
            apparent_field_deg=by[6.0]['apparent_fov_deg'],
            passed=abs(ft(1.0) - 115.2) < 0.5 and abs(ft(6.0) - 20.5) < 0.1 and 15.9 <= ft(6.0) <= 20.5 and 95.0 <= ft(1.0) <= 115.3),
        eye_relief=dict(
            what='Eye relief over the zoom range against published figures',
            model_mm=[lv['eye_relief_summary']['min_mm'], lv['eye_relief_summary']['max_mm']], model_in=er_in, model_at_1x_and_6x_mm=[lv['eye_relief_summary']['at_1x_mm'], lv['eye_relief_summary']['at_6x_mm']],
            published_in=dict(vortex_razor_hd_gen2e=4.0, trijicon_vcog='4.0 constant', sig_tango6t=[3.9, 4.1]),
            note='At 1x and from 2.5x to 6x the model is within 0.1 in of 4.0 in. Between 1.25x and 2x it dips to 3.6 in, more than the 0.2 in the published scopes move: a limit of a two-group thin-lens erector.',
            passed=abs(lv['eye_relief_summary']['at_6x_mm'] / 25.4 - 4.0) < 0.1 and abs(lv['eye_relief_summary']['at_1x_mm'] / 25.4 - 4.0) < 0.1 and er_in[0] > 3.5),
        eye_box=dict(what='Scope-shadow mask: the disc-overlap formula against brute-force sampling of 400,000 rays through the eye pupil and the exit pupil',
                     rows=mc, max_difference=worst_mc, passed=worst_mc < 0.005),
        reticle=dict(what='The reticle\'s marks are the zero table\'s holds (same numbers); the independent check against the ballistics runtime is in parity.json (node test.js)',
                     marks=[dict(distance_m=m['distance_m'], m855_mrad=m['m855_hold_mrad'], mk262_mrad=m['mk262_hold_mrad']) for m in bdc['bdc_marks']],
                     passed=all(m['leg_length_mrad'] > 0 for m in bdc['bdc_marks'])),
    )
    ck['all_passed'] = all(v['passed'] for v in ck.values())
    return ck


def plots(s, lv, bdc, zero):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Arc
    pd = os.path.join(HERE, 'plots'); os.makedirs(pd, exist_ok=True)
    Ms = np.exp(np.linspace(0, math.log(6), 61))
    fo = [s.first_order(M) for M in Ms]
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
    axs[0].plot(Ms, [f['eye_relief_mm'] for f in fo]); axs[0].axhline(101.6, color='k', ls=':', label='4.0 in (published)'); axs[0].set_ylabel('eye relief (mm)'); axs[0].set_ylim(80, 110); axs[0].legend()
    axs[1].plot(Ms, [f['exit_pupil_mm'] for f in fo]); axs[1].plot(Ms, 24 / Ms, 'k:', label='24 / M'); axs[1].set_ylabel('exit pupil (mm)'); axs[1].set_ylim(0, 14); axs[1].legend()
    axs[2].plot(Ms, [2 * 300 * s.field(M)[0] for M in Ms]); axs[2].plot([1, 6], [115.2, 20.5], 'ko', label='Razor Gen II-E'); axs[2].plot([1, 6], [95, 15.9], 'k^', label='VCOG'); axs[2].plot([1, 6], [105.8, 17.7], 'ks', label='Tango6T')
    axs[2].set_ylabel('field of view (ft at 100 yd)'); axs[2].set_yscale('log'); axs[2].legend()
    for a in axs: a.set_xlabel('magnification'); a.grid(alpha=0.3)
    fig.suptitle('1-6x24 thin-lens zoom (simulation; markers are published figures)'); fig.tight_layout(); fig.savefig(os.path.join(pd, 'first_order.png'), dpi=110); plt.close(fig)
    # eye box maps
    fig, axs = plt.subplots(2, 3, figsize=(11, 7))
    for j, M in enumerate((1.0, 3.0, 6.0)):
        r = next(r for r in lv['by_magnification'] if r['magnification'] == M); ep = r['exit_pupil_mm']; ta = r['tan_half_apparent']
        xs = np.linspace(-10, 10, 81); zs = np.linspace(-40, 40, 81)
        img = np.array([[min(eyebox_mask(x, 0, z, sx * ta, 0, ep, 3.0) for sx in (-1, 0, 1)) for x in xs] for z in zs])
        axs[0, j].imshow(img, extent=[-10, 10, -40, 40], origin='lower', aspect='auto', cmap='gray', vmin=0, vmax=1)
        axs[0, j].set_title(f'{M:g}x: exit pupil {ep:.1f} mm'); axs[0, j].set_xlabel('eye offset sideways (mm)'); axs[0, j].set_ylabel('eye behind the exit pupil (mm)')
        n = 121; g = np.linspace(-1.15, 1.15, n)
        pic = np.array([[(eyebox_mask(2.0, 0.0, 15.0, gx * ta, gy * ta, ep, 3.0) if gx * gx + gy * gy <= 1 else 0.0) for gx in g] for gy in g])
        axs[1, j].imshow(pic, extent=[-1.15, 1.15, -1.15, 1.15], origin='lower', cmap='gray', vmin=0, vmax=1)
        axs[1, j].set_title('picture: eye 2 mm right, 15 mm too far back'); axs[1, j].set_xticks([]); axs[1, j].set_yticks([])
    fig.suptitle('Eye box (top: darkest of field centre and edges, 3 mm eye pupil) and scope shadow (bottom)'); fig.tight_layout(); fig.savefig(os.path.join(pd, 'eyebox.png'), dpi=100); plt.close(fig)
    # reticle preview
    fig, ax = plt.subplots(figsize=(6, 6)); ax.set_facecolor('#cfd6cf'); ext = 8.0
    k = 6 * 72 * 0.775 / (2 * ext)       # points per mrad
    for p in bdc['primitives']:
        c = '#0a0a0a' if p['layer'] == 'etched' else '#e0200a'
        if p['type'] == 'line': ax.plot([p['p0'][0], p['p1'][0]], [p['p0'][1], p['p1'][1]], color=c, lw=p['width'] * k, solid_capstyle='butt')
        elif p['type'] == 'dot': ax.add_patch(Circle(p['c'], p['d'] / 2, color=c))
        elif p['type'] == 'arc': ax.add_patch(Arc(p['c'], 2 * p['r'], 2 * p['r'], theta1=p['a0'], theta2=p['a1'], color=c, lw=p['width'] * k))
        elif p['type'] == 'polyline': ax.plot([q[0] for q in p['pts']], [q[1] for q in p['pts']], color=c, lw=p['width'] * k)
    ax.set_xlim(-ext, ext); ax.set_ylim(-ext - 2, ext - 2); ax.set_aspect('equal'); ax.set_xlabel('mrad at 6x'); ax.set_title('Staple BDC reticle: bar = M855, leg tips = Mk 262')
    fig.tight_layout(); fig.savefig(os.path.join(pd, 'reticle.png'), dpi=110); plt.close(fig)
    # holds
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for an, c in (('M855', 'C0'), ('Mk262', 'C1')):
        hz = zero['ammo'][an][BDC_ZERO]['holds']
        ax.plot([r['distance_m'] for r in hz if r['distance_m'] >= 100], [r['hold_mrad'] for r in hz if r['distance_m'] >= 100], color=c, label=f'{an}, 200 m zero')
    ax.plot([m['distance_m'] for m in bdc['bdc_marks']], [m['m855_hold_mrad'] for m in bdc['bdc_marks']], 'C0s', label='bars'); ax.plot([m['distance_m'] for m in bdc['bdc_marks']], [m['mk262_hold_mrad'] for m in bdc['bdc_marks']], 'C1v', label='leg tips')
    ax.set_xlabel('distance from the eye (m)'); ax.set_ylabel('hold (mrad)'); ax.grid(alpha=0.3); ax.legend(); ax.set_title('Holds from the HK416 ballistics tables and the reticle marks')
    fig.tight_layout(); fig.savefig(os.path.join(pd, 'holds.png'), dpi=110); plt.close(fig)


# ============================================================================ main
if __name__ == '__main__':
    print('solving the zoom...', flush=True)
    s = design_lpvo()
    lv = lpvo_results(s)
    er6 = lv['eye_relief_summary']['at_6x_mm']
    lens_l = LPVO['ocular_rear_l_mm'] + LPVO['ocular_lens_inset_mm']
    LPVO['eye_l_mm'] = lens_l - er6          # design eye point: at the 6x exit pupil (the tightest eye box)
    bal = json.load(open(BALLISTICS))
    h = LPVO['axis_over_bore_mm'] / 1000.0
    e2m = (RIFLE['crown_l_mm'] - LPVO['eye_l_mm']) / 1000.0
    zero = zero_tables(bal, h, e2m, LPVO['click_mrad'] * MRAD, '0.1 mrad', (('200m', 200.0), ('100m', 100.0), ('50m', 50.0), ('25m', 25.0)))
    zero['default'] = BDC_ZERO
    bdc = bdc_reticle(zero, bal, e2m, h)
    bdc['field_radius_mrad_at_6x'] = next(r for r in lv['by_magnification'] if r['magnification'] == 6.0)['tan_half_real'] * 1000
    reticle_svg(bdc, 36.0, os.path.join(HERE, 'reticle', 'staple_bdc_full.svg'))
    reticle_svg(bdc, 8.0, os.path.join(HERE, 'reticle', 'staple_bdc_centre.svg'), bg='#cfd6cf')
    so, rt, H = RIFLE['socket_optic_l_mm'], RIFLE['rail_top_mm'], LPVO['axis_over_rail_mm']
    P3 = lambda L: [0, H / 1000, (L - so) / 1000]
    front_l = LPVO['ocular_rear_l_mm'] + LPVO['length_mm']
    sockets = dict(socket_mount=[0, 0, 0], socket_eye=P3(LPVO['eye_l_mm']), socket_ocular_lens=P3(lens_l), socket_objective=P3(front_l - LPVO['objective_lens_inset_mm']))
    checks = run_checks(s, lv, zero, bdc)
    samples = []
    for M in (1.0, 1.1, 2.2, 3.0, 4.7, 6.0):
        fo = s.first_order(M); c = s.cam(M); tr, ta = s.field(M)
        samples.append(dict(magnification=M, cam=[c[0], c[1]], eye_relief_mm=fo['eye_relief_mm'], exit_pupil_mm=fo['exit_pupil_mm'], tan_half_real=tr, tan_half_apparent=ta,
                            transmission_at_0p9_field=s.transmission(M, tr * 0.9, n=31),
                            mask=[dict(ex=ex, ey=ey, dz=dz, ax=ax * ta, ay=ay * ta, eye_pupil_mm=pe, value=eyebox_mask(ex, ey, dz, ax * ta, ay * ta, fo['exit_pupil_mm'], pe))
                                  for (ex, ey, dz, ax, ay, pe) in ((0, 0, 0, 0, 0, 3.0), (1.5, 0.5, 0, 0.3, 0.2, 3.0), (2.0, -1.0, 12.0, 0.8, -0.3, 3.0), (0, 0, -25.0, 0.9, 0.0, 6.0), (3.0, 2.0, 30.0, -0.5, 0.5, 6.0))]))
    doc = dict(
        meta=dict(title='Generic 1-6x24 second-focal-plane LPVO: optical system, eye box, reticle, zero tables and rendering model', generator='assets/optic-lpvo-1-6/optics/sim.py', credit='carpetshark',
                  units='millimetres, degrees, MOA or mrad as each key says; SI in the zero tables; sockets in metres',
                  ballistics_source='assets/hk416/ballistics/ballistics.json (' + bal['meta'].get('generator', 'sim.py') + ')',
                  class_references='External figures of the class are in `published`. This is a generic scope: no maker\'s name, logo or trade dress; the optical design and the reticle are original.'),
        rifle=RIFLE, body=LPVO, published=PUBLISHED,
        frames=dict(asset='metres, +Z muzzle, +Y up, +X shooter\'s left; origin socket_mount = the rifle\'s socket_optic (rail top, on the centreline)',
                    shooter='eye offsets and field angles as the shooter sees them: right and up; right = -X of the asset frame'),
        sockets=sockets, **lv,
        turrets=dict(click='0.1 mrad', mm_at_100m=10.0, clicks_per_revolution=LPVO['clicks_per_rev'], travel_mrad=LPVO['travel_mrad'],
                     elevation='top, capped, low profile; clips elevation_turn and elevation_cap_off', windage='right side, capped; clips windage_turn and windage_cap_off',
                     illumination='left side knob, 11 positions; clip illumination', power_ring='half a turn from 1x to 6x with a throw lever; clip magnification (its angle is by_magnification[*].power_ring_deg)'),
        design_eye_point='socket_eye is at the 6x exit pupil (the tightest eye box); the eye relief at other powers is listed per magnification',
        reticle=bdc, zero=zero, rendering=rendering_model(lv),
        parity_samples=dict(doc='values for optic-lpvo.js to reproduce with its own cam solver, paraxial trace and mask', rows=samples),
    )
    json.dump(rnd(doc, 9), open(os.path.join(HERE, 'lpvo.json'), 'w'), indent=1)
    json.dump(rnd(checks, 9), open(os.path.join(HERE, 'checks.json'), 'w'), indent=1)
    plots(s, lv, bdc, zero)
    for r in lv['by_magnification']:
        print('  %.2fx stop %-17s EP %.2f ER %.1f FOV %.2f deg (%.1f ft/100yd) AFOV %.1f vig %s  box3 lat %.1f ax %.1f' % (
            r['magnification'], r['aperture_stop'], r['exit_pupil_mm'], r['eye_relief_mm'], r['real_fov_deg'], r['fov_ft_at_100yd'], r['apparent_fov_deg'], rnd(r['vignetting']['relative_illumination'], 2),
            r['eyebox_eye_pupil_3mm']['lateral_half_brightness_mm'], r['eyebox_eye_pupil_3mm']['axial_edge_half_brightness_mm']))
    for an in ('M855', 'Mk262'):
        for zn, z in zero['ammo'][an].items():
            print(an, zn, 'bore %.3f mrad' % z['bore_angle_mrad'], 'clicks', z['clicks_up_from_centre'], 'cross', rnd(z['crossings_from_eye_m'], 1), 'max ord %.0f mm @%.0f' % (z['max_ordinate_mm'], z['max_ordinate_at_m']))
    print('BDC', rnd(bdc['bdc_marks'], 3)); print('other powers', rnd(bdc['marks_at_other_powers'], 1))
    print('eye L', LPVO['eye_l_mm'], 'sockets', rnd(sockets, 4))
    for k, v in checks.items():
        if isinstance(v, dict): print('CHECK', k, 'PASS' if v['passed'] else 'FAIL', {a: (float('%.3g' % b) if isinstance(b, float) else b) for a, b in v.items() if isinstance(b, (int, float)) and not isinstance(b, bool)})
    print('all passed:', checks['all_passed'])
