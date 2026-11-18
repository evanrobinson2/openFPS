#!/usr/bin/env python3
"""Matched comparison of the simulation with the reference photos.

    python3 compare/make_compare.py ../refs-local/flash ../refs-local/flash/compare_out

The photos are not committed (see ../REFERENCES.md for the sources and the file names expected here).
Writes side-by-side sheets to the output dir, and compare/measurements.json plus the model-only
matched renders (compare/model_*.png) into the repo.
"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import physics as ph, render as rd, sim
from physics import P

def measure_glow(rgb, face_x, axis_y, ppm_mm, bg):
    """Same measurements on photo and model: positions in mm from the hider face."""
    R = rgb[..., 0].astype(float) - bg
    x0 = int(face_x + 60 * ppm_mm)
    prof = R[int(axis_y - 8 * ppm_mm):int(axis_y + 8 * ppm_mm), :].mean(0)
    pk = prof[x0:].max(); xs = np.arange(len(prof))
    above = np.where((prof >= 0.5 * pk) & (xs >= x0))[0]
    sub = np.clip(R[:, x0:] - 0.1 * pk, 0, None); yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
    cx = (xx * sub).sum() / sub.sum() + x0
    col = R[:, int(cx) - 5:int(cx) + 5].mean(1); ya = np.where(col >= 0.5 * col.max())[0]
    out = dict(upstream_half_max_mm=(above[0] - face_x) / ppm_mm, downstream_half_max_mm=(above[-1] - face_x) / ppm_mm,
               centroid_mm=(cx - face_x) / ppm_mm, height_fwhm_mm=(ya[-1] - ya[0]) / ppm_mm)
    # dark gap: mean signal 40 to 90 mm ahead of the face against the peak
    blob = R[int(axis_y - 50 * ppm_mm):int(axis_y - 25 * ppm_mm), int(face_x + 15 * ppm_mm):int(face_x + 45 * ppm_mm)]
    out['slot_blob_over_peak_gamma'] = float(gaussian_filter(blob, 3).max() / R[:, x0:].max())
    out['gap_over_peak'] = float(prof[int(face_x + 40 * ppm_mm):int(face_x + 90 * ppm_mm)].mean() / pk)
    return {k: round(float(v), 2) for k, v in out.items()}

def gr_ratio(rgb, x, y, bg, h=6):
    p = rgb[y - h:y + h, x - h:x + h].reshape(-1, 3).astype(float).mean(0)
    lin = (np.clip(p, 1, 255) / 255) ** 2.2 - (np.array(bg) / 255) ** 2.2
    return round(float(lin[1] / max(lin[0], 1e-6)), 3)

def main(refdir, outdir):
    os.makedirs(outdir, exist_ok=True)
    out, ctx = sim.build()
    cal = ctx['cal']; rng = np.random.default_rng(16)
    res = {}
    # ---- 1. TTAG A2 photo: 16 in barrel, A2 birdcage, three shots in one 3.2 s exposure, camera to the right and raised
    ppm_mm, face_x, axis_y = 3.55, 463, 575                       # measured on the photo: hider 78 px across = 22 mm
    view = rd.View('side', (-face_x / ppm_mm / 1e3, (1500 - face_x) / ppm_mm / 1e3, -(1000 - axis_y) / ppm_mm / 1e3, axis_y / ppm_mm / 1e3), ppm_mm * 1e3, elev_deg=25)
    integ = 3 * rd.integrate(view, ctx['ref_a2'], cal, 0, 4e-3, rng, steps=500, n=30000)
    lum = gaussian_filter(integ @ np.array([0.2126, 0.7152, 0.0722]), 2)
    white = float(lum.max()) / 3                                   # the photo's glow is clipped; clip the model alike
    mask = rd.gun_mask(view)
    m8 = rd.tonemap(integ, white, blur=2.5, glare=0.1).astype(int) + np.array([44, 29, 9])[None, None]
    m8[mask] = (18, 12, 6)
    # draw the lit slots again over the gun silhouette
    lit = rd.tonemap(integ, white, blur=2.5, glare=0.1); sel = mask & (lit.sum(2) > 40); m8[sel] = lit[sel]
    model = Image.fromarray(np.clip(m8, 0, 255).astype(np.uint8))
    model.save(os.path.join(HERE, 'model_ttag_a2_matched.png'))
    res['model_16in_a2_3shots'] = measure_glow(np.asarray(model), face_x, axis_y, ppm_mm, 44)
    hz = lambda m: (int(face_x + (m['upstream_half_max_mm'] - 8) * ppm_mm), axis_y - 30)
    res['model_16in_a2_3shots']['haze_G_over_R_linear'] = gr_ratio(np.asarray(model), *hz(res['model_16in_a2_3shots']), (44, 29, 9))
    p = os.path.join(refdir, 'ttag_a2.jpg')
    if os.path.exists(p):
        photo = Image.open(p).convert('RGB'); a = np.asarray(photo)
        res['photo_ttag_a2'] = measure_glow(a, face_x, axis_y, ppm_mm, 44)
        res['photo_ttag_a2']['haze_G_over_R_linear'] = gr_ratio(a, *hz(res['photo_ttag_a2']), (44, 29, 9))
        s = Image.new('RGB', (3000, 1040), (0, 0, 0)); s.paste(photo, (0, 40)); s.paste(model, (1500, 40))
        d = ImageDraw.Draw(s); d.text((10, 12), 'REFERENCE: thetruthaboutguns.com AR-15 flash hider shootout, A2 birdcage, 16 in, 3 shots / 3.2 s', fill=(255, 255, 255))
        d.text((1510, 12), 'MODEL: 16 in barrel, 5-slot cage, 3 shots integrated, same scale (3.55 px/mm) and framing, camera raised 25 deg', fill=(255, 255, 255))
        for x in range(0, 260, 20):
            for off in (0, 1500):
                X = off + face_x + x * ppm_mm; d.line([(X, 990), (X, 1000 if x % 100 else 975)], fill=(0, 255, 0)); 
                if x % 100 == 0: d.text((X + 2, 962), f'{x} mm', fill=(0, 255, 0))
        s.save(os.path.join(outdir, 'compare_ttag_a2.png'))
    # ---- 2. a full secondary flash against the 103rd RQS M4 photo (about 1.98 mm/px, from the carbine's length)
    vb = rd.View('side', (-0.25, 0.75, -0.35, 0.35), 505.0)
    sec = dict(peak=ctx['I_sec_pk'], scale=1.0)
    ig = rd.integrate(vb, ctx['ref_bare'], cal, 0, 15e-3, rng, steps=120, n=20000, secondary=sec)
    ig = ig[:, ::-1]                                               # the photo's muzzle points left
    lum = gaussian_filter(ig @ np.array([0.2126, 0.7152, 0.0722]), 2)
    mb = Image.fromarray(rd.tonemap(ig, float(lum.max()) / 25, blur=2.0, glare=0.3))      # the photo's core is clipped white; clip the model alike
    mb.save(os.path.join(HERE, 'model_secondary_full_matched.png'))
    ys, xs = np.where(lum > 0.25 * lum.max())
    res['model_secondary_full'] = dict(length_mm=round(float(np.ptp(xs)) / 0.505, 0), height_mm=round(float(np.ptp(ys)) / 0.505, 0))
    res['photo_103rqs_m4'] = dict(length_mm=round(220 * 1.98), height_mm=round(200 * 1.98), note='clipped core plus orange rim, measured by eye on the 1280 px image; scale from the carbine length, +-15 %')
    p = os.path.join(refdir, 'wm_1.jpg')
    if os.path.exists(p):
        photo = Image.open(p).convert('RGB').crop((0, 250, 505, 604))
        s = Image.new('RGB', (1010 + 12, 354 + 40), (0, 0, 0)); s.paste(photo, (4, 36)); s.paste(mb.resize((505, 354)), (513, 36))
        d = ImageDraw.Draw(s); d.text((6, 10), 'REFERENCE: 103rd Rescue Squadron M4, DVIDS / Commons (public domain)', fill=(255, 255, 255))
        d.text((515, 10), 'MODEL: full secondary flash, 15 ms integrated, 1.98 mm/px', fill=(255, 255, 255))
        s.save(os.path.join(outdir, 'compare_secondary.png'))
    # ---- 3. a partial secondary flash through the hider against the Marine M4A1 dusk photo (about 1.5 mm/px)
    vh = rd.View('side', (-0.30, 0.45, -0.25, 0.25), 667.0)
    sec = dict(peak=ctx['I_sec_pk'], scale=P('sec_hider_scale'))
    ig = rd.integrate(vh, ctx['shot'], cal, 0, 15e-3, rng, steps=120, n=20000, secondary=sec)
    lum = gaussian_filter(ig @ np.array([0.2126, 0.7152, 0.0722]), 2)
    mh = Image.fromarray(rd.tonemap(ig, float(lum.max()) / 6, blur=2.0, glare=0.3))
    mh.save(os.path.join(HERE, 'model_secondary_hider_matched.png'))
    ys, xs = np.where(lum > 0.25 * lum.max())
    res['model_secondary_through_hider'] = dict(length_mm=round(float(np.ptp(xs)) / 0.667, 0), height_mm=round(float(np.ptp(ys)) / 0.667, 0))
    res['photo_marine_m4a1_dusk'] = dict(length_mm=300, height_mm=240, core_ahead_of_muzzle_mm=160, note='orange halo measured by eye; scale from the carbine length, +-20 %; includes lens glare')
    p = os.path.join(refdir, 'wm_2.jpg')
    if os.path.exists(p):
        photo = Image.open(p).convert('RGB').crop((693, 76, 693 + 500, 76 + 333))
        s = Image.new('RGB', (1000 + 12, 333 + 40), (0, 0, 0)); s.paste(photo, (4, 36)); s.paste(mh, (508, 36))
        d = ImageDraw.Draw(s); d.text((6, 10), 'REFERENCE: US Marine M4A1, night drill 2020, DVIDS / Commons (public domain)', fill=(255, 255, 255))
        d.text((510, 10), 'MODEL: partial secondary flash through the hider, 1.5 mm/px', fill=(255, 255, 255))
        s.save(os.path.join(outdir, 'compare_secondary_hider.png'))
    json.dump(res, open(os.path.join(HERE, 'measurements.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
