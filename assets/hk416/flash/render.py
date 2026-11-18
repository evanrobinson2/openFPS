"""Reference renders of the simulation (numpy splatting; no game code).

Emitters are sampled as 3-D points with a luminous-intensity weight, projected, binned into luminance
(cd/m2, or cd s/m2 for time-integrated pictures), blurred slightly and tone-mapped. Each picture states its exposure.
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import ConvexHull
import physics as ph
from physics import P

EYE = np.array([0.0, 0.0655, -0.659])        # socket_ads_eye in the muzzle frame (from hk416.glb)

def slot_angles(shot):
    return [0, 60, 120, 240, 300] if shot.n_slots == 5 else [30 + 60 * k for k in range(shot.n_slots)]

# ---------------------------------------------------------------- emitters -> samples
def _cone(rng, n, start, axis, width, length, taper=0.55, k=3.0):
    """Points in a tapering plume: bright face at start, exponential fall along the axis."""
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    s = -np.log(1 - rng.random(n) * (1 - math.exp(-k))) / k
    rad = 0.29 * width * (1 - taper * s) * np.sqrt(-2 * np.log(1 - rng.random(n)))    # soft edge; projected FWHM = 0.68 width
    phi = rng.random(n) * 2 * math.pi
    a = np.cross(axis, [0, 1, 0] if abs(axis[1]) < 0.9 else [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(axis, a)
    return (np.asarray(start)[None] + axis[None] * (s * length)[:, None] +
            a[None] * (rad * np.cos(phi))[:, None] + b[None] * (rad * np.sin(phi))[:, None])

def samples(shot, t, cal, rng, n=40000, secondary=None):
    """Returns pos (N,3), weight cd (N), rgb (N,3), normal (N,3; zero = volumetric), kind (N)."""
    f = ph.phases(shot, t, cal)
    pos, w, rgb, nrm, kind = [], [], [], [], []
    def push(p, wt, c, nn=None, kd=0):
        pos.append(p); w.append(np.full(len(p), wt / len(p))); rgb.append(np.tile(c, (len(p), 1)))
        nrm.append(np.zeros((len(p), 3)) if nn is None else np.tile(nn, (len(p), 1))); kind.append(np.full(len(p), kd))
    pr = f['primary']
    if pr['L'] > 0:
        c = ph.rgb_of(ph.spectrum(pr['T'], pr['eps']))
        if shot.hider:
            z0, z1 = P('fh_slot_z'); sw = P('fh_slot_w'); m = max(n // 40, 200)
            for a in slot_angles(shot):
                th = math.radians(a); nn = np.array([math.sin(th), math.cos(th), 0.0]); tg = np.array([math.cos(th), -math.sin(th), 0.0])
                u = rng.random(m); z = z0 + (z1 - z0) * u ** 0.45               # brighter toward the front of the slot
                p = nn[None] * P('fh_r') + tg[None] * ((rng.random(m) - 0.5) * sw)[:, None] + np.array([0, 0, 1.0])[None] * z[:, None]
                push(p, pr['L'] * pr['slot_area'] * 0.45, c, nn, 1)             # Lambert surface patch
            rr = P('fh_chamber_r') * np.sqrt(rng.random(m)); ph_ = rng.random(m) * 2 * math.pi
            push(np.stack([rr * np.cos(ph_), rr * np.sin(ph_), np.zeros(m)], 1), pr['I_front'], c, np.array([0, 0, 1.0]), 1)
        else:
            push(_cone(rng, n // 10, (0, 0, 0), (0, 0, 1), shot.Dm * 1.2, 2 * shot.Dm, taper=-0.8), pr['I'], c)
    it = f['intermediate']
    if it['I'] > 0:
        c = ph.rgb_of(ph.spectrum(it['T'], it['eps']))
        push(_cone(rng, n // 2, (0, 0, it['x_disk']), (0, 0, 1), it['width'], it['length']), it['I'], c)
    if shot.n_slots and f['slot_jet']['I'] > 0:
        sj = f['slot_jet']; c = ph.rgb_of(ph.spectrum(sj['T'], sj['eps']))
        lean = math.radians(P('slot_lean_deg')); zc = sum(P('fh_slot_z')) / 2
        for a in slot_angles(shot):
            th = math.radians(a); rad = np.array([math.sin(th), math.cos(th), 0.0])
            d = rad * math.sin(lean) + np.array([0, 0, math.cos(lean)])
            o = rad * P('fh_r') + np.array([0, 0, zc]) + d * sj['x_disk']
            push(_cone(rng, n // 16, o, d, sj['width'], sj['length']), sj['I'], c)
    if secondary:
        tt = max(t - P('sec_delay'), 0.0)
        I = float(ph.secondary_pulse(t, secondary['peak'])) * secondary.get('scale', 1.0)
        if I > 0:
            sc = math.sqrt(secondary.get('scale', 1.0)); g = 1 - math.exp(-tt / 1.2e-3)
            L, D = (0.20 + 0.95 * g) * sc, (0.18 + 0.93 * g) * sc
            lr = np.random.default_rng(secondary.get('seed', 7))
            cen = lr.normal(0, 1, (14, 3)) * np.array([D / 10, D / 10, L / 8]) + np.array([0, 0, 0.02 + 0.25 * L])
            idx = rng.integers(0, len(cen), n)
            p = cen[idx] + rng.normal(0, 1, (n, 3)) * np.array([D / 12, D / 12, L / 14])
            hot = np.exp(-np.sum(((p - np.array([0, 0, 0.02 + 0.25 * L])) / np.array([D / 6, D / 6, L / 6])) ** 2, 1))
            c_hot = ph.rgb_of(ph.spectrum(P('T_secondary'), 0.05, True)); c_cool = ph.rgb_of(ph.spectrum(1700.0, 0.2))
            pos.append(p); w.append(np.full(n, I / n)); rgb.append(c_cool[None] + (c_hot - c_cool)[None] * hot[:, None])
            nrm.append(np.zeros((n, 3))); kind.append(np.full(n, 2))
    if not pos:
        return np.zeros((0, 3)), np.zeros(0), np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0)
    return np.concatenate(pos), np.concatenate(w), np.concatenate(rgb), np.concatenate(nrm), np.concatenate(kind)

# ---------------------------------------------------------------- views
class View:
    def __init__(self, kind, extent, ppm, elev_deg=0.0):
        self.kind, self.ext, self.ppm, self.e = kind, extent, ppm, math.radians(elev_deg)
        self.W = int(round((extent[1] - extent[0]) * ppm)); self.H = int(round((extent[3] - extent[2]) * ppm))
    def project(self, p):
        """-> u, v (m in the picture plane), unit view direction per point, area scale."""
        p = np.atleast_2d(p)
        if self.kind == 'side':                       # from the rifle's right; picture right = down-range
            e = self.e
            d = np.tile([math.cos(e), -math.sin(e), 0.0], (len(p), 1))
            return p[:, 2], p[:, 0] * math.sin(e) + p[:, 1] * math.cos(e), d, np.ones(len(p))
        if self.kind == 'rear':                       # straight down the bore from behind, orthographic
            return -p[:, 0], p[:, 1], np.tile([0, 0, 1.0], (len(p), 1)), np.ones(len(p))
        if self.kind == 'top':                        # from above; picture right = down-range, picture up = rifle's left (+X)
            return p[:, 2], p[:, 0], np.tile([0, -1.0, 0], (len(p), 1)), np.ones(len(p))
        q = p - EYE[None]; D = -EYE[2]                # 'ads': perspective from socket_ads_eye, scaled to the muzzle plane
        return -q[:, 0] / q[:, 2] * D, q[:, 1] / q[:, 2] * D, q / np.linalg.norm(q, axis=1)[:, None], (D / q[:, 2]) ** 2
    def pix(self, u, v):
        return (u - self.ext[0]) * self.ppm, (self.ext[3] - v) * self.ppm

def gun_parts():
    """Crude occluders in the muzzle frame (m), from the model's dimensions: hider, barrel, handguard, receiver, front sight."""
    def cyl(r, z0, z1, n=28):
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        return np.concatenate([np.stack([r * np.cos(a), r * np.sin(a), np.full(n, z)], 1) for z in (z0, z1)])
    def box(x, y0, y1, z0, z1):
        return np.array([[sx * x, y, z] for sx in (-1, 1) for y in (y0, y1) for z in (z0, z1)])
    return [('hider', cyl(P('fh_r'), -P('fh_len'), 0)), ('barrel', cyl(0.0089, -0.101, -P('fh_len'))),
            ('handguard', box(0.028, -0.028, 0.0368, -0.326, -0.101)), ('receiver', box(0.020, -0.060, 0.0368, -0.640, -0.326)),
            ('sight_base', box(0.006, 0.0368, 0.050, -0.118, -0.104)), ('sight_post', box(0.0012, 0.050, 0.0655, -0.112, -0.108))]

def gun_mask(view):
    im = Image.new('L', (view.W, view.H), 0); d = ImageDraw.Draw(im)
    for name, pts in gun_parts():
        if view.kind in ('side', 'top') and name not in ('hider', 'barrel'): continue
        u, v, _, _ = view.project(pts); x, y = view.pix(u, v); q = np.stack([x, y], 1)
        try: hull = q[ConvexHull(q).vertices]
        except Exception: continue
        d.polygon([tuple(a) for a in hull], fill=255)
    return np.asarray(im) > 0

def splat(view, pos, w, rgb, nrm, kind, mask=None):
    """Accumulate samples into an (H,W,3) image of luminance * rgb (cd/m2 if w is in cd)."""
    img = np.zeros((view.H, view.W, 3))
    if len(pos) == 0: return img
    u, v, d, sc = view.project(pos)
    lam = np.where(np.any(nrm != 0, 1), np.clip(-np.sum(nrm * d, 1), 0, None), 1.0)
    x, y = view.pix(u, v); xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    ok = (xi >= 0) & (xi < view.W) & (yi >= 0) & (yi < view.H) & (lam > 0)
    if mask is not None and view.kind in ('rear', 'ads'):
        ok &= ~(mask[np.clip(yi, 0, view.H - 1), np.clip(xi, 0, view.W - 1)])
    ww = (w * lam * sc * view.ppm ** 2)[ok]
    for c in range(3):
        np.add.at(img[..., c], (yi[ok], xi[ok]), ww * rgb[ok, c])
    return img

def integrate(view, shot, cal, t0, t1, rng, steps=400, n=10000, secondary=None, mask=None):
    """Time-integrated picture over [t0, t1] (cd s / m2)."""
    img = np.zeros((view.H, view.W, 3))
    # denser sampling where the flash is bright (first 1.5 ms)
    edges = np.unique(np.concatenate([np.linspace(t0, min(t1, 1.5e-3), steps + 1), np.linspace(min(t1, 1.5e-3), t1, steps // 8 + 1)]))
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a: continue
        s = samples(shot, 0.5 * (a + b), cal, rng, n, secondary)
        img += splat(view, *s, mask=mask) * (b - a)
    return img

def tonemap(img, white, blur=1.2, glare=0.0):
    x = gaussian_filter(img, (blur, blur, 0))
    if glare: x = x + glare * gaussian_filter(img, (12, 12, 0))
    x = 1 - np.exp(-x / white)
    return (255 * np.clip(x, 0, 1) ** (1 / 2.2)).astype(np.uint8)

def auto_white(img):
    lum = gaussian_filter(img @ np.array([0.2126, 0.7152, 0.0722]), 1.2)
    nz = lum[lum > 0]
    return float(np.percentile(nz, 99.5)) * 0.5 if len(nz) else 1.0

def finish(view, rgb8, label, draw_gun=True, mask=None, bg=(6, 6, 8), scale_bar=0.05):
    a = rgb8.astype(int)
    base = np.zeros_like(a) + np.array(bg)[None, None]
    if mask is not None:
        base[mask] = (26, 26, 28)
    im = Image.fromarray(np.clip(base + a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    d.text((8, 6), label, fill=(210, 210, 210))
    if scale_bar:
        L = scale_bar * view.ppm; d.line([(view.W - 12 - L, view.H - 12), (view.W - 12, view.H - 12)], fill=(200, 200, 200), width=2)
        d.text((view.W - 12 - L, view.H - 28), f'{scale_bar * 1000:.0f} mm', fill=(200, 200, 200))
    return im

def sheet(images, cols, pad=4, bg=(0, 0, 0)):
    w, h = images[0].size; rows = (len(images) + cols - 1) // cols
    s = Image.new('RGB', (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad), bg)
    for i, im in enumerate(images):
        s.paste(im, (pad + (i % cols) * (w + pad), pad + (i // cols) * (h + pad)))
    return s

SIDE = lambda: View('side', (-0.07, 0.33, -0.10, 0.10), 3000)
REAR = lambda: View('rear', (-0.11, 0.11, -0.11, 0.11), 3000)
ADS = lambda: View('ads', (-0.13, 0.13, -0.17, 0.05), 2600)
TIMES_MS = [0.05, 0.15, 0.23, 0.3, 0.5, 1]

# ---------------------------------------------------------------- smoke
def _noise(shape, rng, octaves=4):
    out = np.zeros(shape)
    for o in range(octaves):
        s = 2 ** (o + 2)
        g = rng.random((s + 1, s + 1))
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize(shape[::-1], Image.BICUBIC)) / 255 / 2 ** o
    return out / out.max()

def smoke_panel(src, t, wind, view, rng_seed=3, label=''):
    H, W = view.H, view.W
    yy, xx = np.mgrid[0:H, 0:W]
    tau = np.zeros((H, W))
    for i, s in enumerate(src):
        nz = _noise((H, W), np.random.default_rng(rng_seed + i))
        for p, R, t0 in ph.puff_set(s, t, wind):
            u, v, _, _ = view.project(p); x, y = view.pix(u, v)
            sig = max(R / 2 * view.ppm, 0.6)
            g = np.exp(-((xx - x[0]) ** 2 + (yy - y[0]) ** 2) / (2 * sig * sig))
            tau += t0 * g * (0.55 + 0.9 * nz)
    T = np.exp(-tau)
    sky = np.linspace(0.62, 0.78, H)[:, None, None] * np.array([0.86, 0.93, 1.0])[None, None]
    sky = np.broadcast_to(sky, (H, W, 3)).copy()
    if view.kind == 'side':
        gy = int(view.pix(np.array([0.0]), np.array([-1.4]))[1][0])
        if gy < H: sky[gy:] = np.array([0.36, 0.38, 0.30])
    col = sky * T[..., None] + np.array([0.80, 0.82, 0.86])[None, None] * (1 - T[..., None])
    im = Image.fromarray((255 * np.clip(col, 0, 1) ** (1 / 2.2)).astype(np.uint8)); d = ImageDraw.Draw(im)
    # the rifle as a bar from the stock to the muzzle
    (x0, x1), (y0, y1) = view.pix(np.array([-0.80, 0.0]), np.array([0.0, 0.0]))
    d.line([(x0, y0), (x1, y1)], fill=(20, 20, 20), width=max(2, int(0.04 * view.ppm)))
    d.text((6, 4), label, fill=(15, 15, 15))
    L = 0.5 * view.ppm; d.line([(W - 10 - L, H - 10), (W - 10, H - 10)], fill=(15, 15, 15), width=2); d.text((W - 10 - L, H - 24), '0.5 m', fill=(15, 15, 15))
    return im, float(tau.max())

# ---------------------------------------------------------------- everything
def all(ctx, outdir):
    os.makedirs(outdir, exist_ok=True)
    shot, cal = ctx['shot'], ctx['cal']
    rng = np.random.default_rng(416)
    log = {}
    for name, mk in (('side', SIDE), ('rear', REAR), ('ads', ADS)):
        view = mk(); mask = gun_mask(view)
        raws = [splat(view, *samples(shot, t * 1e-3, cal, rng, 160000), mask=mask) for t in TIMES_MS]
        fixed = auto_white(raws[2])
        row_fixed, row_auto = [], []
        for t, raw in zip(TIMES_MS, raws):
            lum = gaussian_filter(raw @ np.array([0.2126, 0.7152, 0.0722]), 1.2); pk = float(lum.max())
            aw = auto_white(raw) if pk > 0 else 1.0
            a = finish(view, tonemap(raw, aw), f't = {t} ms   {name}   auto exposure: white = {aw:.3g} cd/m2   peak {pk:.3g} cd/m2', mask=mask)
            b = finish(view, tonemap(raw, fixed), f't = {t} ms   {name}   fixed exposure: white = {fixed:.3g} cd/m2', mask=mask)
            a.save(os.path.join(outdir, f'{name}_{str(t).replace(".", "p")}ms.png'))
            row_fixed.append(b); row_auto.append(a); log[f'{name}_{t}ms_peak_cd_m2'] = pk
        sheet(row_fixed + row_auto, len(TIMES_MS)).save(os.path.join(outdir, f'sheet_{name}.png'))
        # the whole flash, time-integrated: what a 1/60 s game frame or a long camera exposure collects
        integ = integrate(view, shot, cal, 0, 4e-3, rng, mask=mask)
        aw = auto_white(integ)
        finish(view, tonemap(integ, aw, glare=0.15), f'whole flash, time-integrated   {name}   white = {aw:.3g} cd s/m2 (= {aw * 60:.3g} cd/m2 held for 1/60 s)', mask=mask
               ).save(os.path.join(outdir, f'{name}_integrated.png'))
        log[f'{name}_integrated_white_cd_s_m2'] = aw
        # a shot whose secondary flash lights (partial, through the hider)
        sec = dict(peak=ctx['I_sec_pk'], scale=P('sec_hider_scale'))
        vw = View(view.kind, tuple(3 * np.array(view.ext)) if name != 'ads' else (-0.39, 0.39, -0.45, 0.21), view.ppm / 3)
        m2 = gun_mask(vw)
        raw = splat(vw, *samples(shot, 2.1e-3, cal, rng, 200000, sec), mask=m2)
        aw = auto_white(raw)
        finish(vw, tonemap(raw, aw, blur=2.0, glare=0.25), f'a shot whose secondary flash lights (partial, through the hider), t = 2.1 ms   {name}   white = {aw:.3g} cd/m2', mask=m2, scale_bar=0.2
               ).save(os.path.join(outdir, f'{name}_secondary_2p1ms.png'))
    # smoke time-lapses
    src = ctx['src']
    tl = [0.005, 0.02, 0.05, 0.15, 0.4, 1.0, 2.0, 4.0]
    vs = View('side', (-0.9, 3.6, -1.5, 1.2), 150)
    panels = [smoke_panel(src, t, (0, 0, 0), vs, label=f'side, no wind, t = {t} s') for t in tl]
    sheet([p[0] for p in panels], 4).save(os.path.join(outdir, 'smoke_timelapse_side_nowind.png'))
    log['smoke_tau_max_side'] = [round(p[1], 3) for p in panels]
    vt = View('top', (-0.9, 3.6, -2.0, 0.7), 150)
    panels = [smoke_panel(src, t, (-2.0, 0, 0), vt, label=f'top, 2 m/s cross-wind toward the rifle\'s right, t = {t} s') for t in tl]
    sheet([p[0] for p in panels], 4).save(os.path.join(outdir, 'smoke_timelapse_top_crosswind.png'))
    # close-up of the first 50 ms, side
    vc = View('side', (-0.6, 1.5, -0.6, 0.6), 320)
    panels = [smoke_panel(src, t, (0, 0, 0), vc, label=f'side close-up, t = {t * 1e3:.0f} ms') for t in (0.002, 0.005, 0.015, 0.05)]
    sheet([p[0] for p in panels], 4).save(os.path.join(outdir, 'smoke_first_50ms_side.png'))
    import json
    with open(os.path.join(outdir, 'render_log.json'), 'w') as f: json.dump(log, f, indent=1)
    print('renders ->', outdir)
