"""Silhouette check (brief: Checks > Silhouettes).  python3 tools/score.py [--round N --change "..."]
Projects the model orthographically onto each reference's pixel grid and computes intersection over union.
  right photo : fixed transform from the rail ruler (0.897 px/mm, L=0 at x=372, bore at y=69); no fitting.
  drawing     : its scale is not on the rail ruler (see NOTES.md), so scale and offset are fitted (similarity, no rotation).
Writes r/silhouette_*.png overlays (purple both, orange reference only, blue model only) and work/score.json."""
import numpy as np, json, os, sys, argparse
from PIL import Image, ImageDraw
from scipy import ndimage
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(HERE), 'refs-local')   # cited, not committed: notes/REFERENCES.md
PXMM, X0, Y0 = 0.897, 372.0, 69.0
SS = 4

def raster(tris2d, w, h):
    """tris2d: (n, 3, 2) pixel coords. Anti-aliased coverage in [0, 1] on a w x h grid."""
    im = Image.new('L', (w * SS, h * SS), 0); d = ImageDraw.Draw(im)
    for t in (tris2d * SS):
        d.polygon([tuple(p) for p in t], fill=255)
    return np.asarray(im.resize((w, h), Image.BOX)).astype(float) / 255

BASE = 3.0                                   # px per mm of the cached orthographic projection
_cache = {}
def base_mask(tris):
    """The model's orthographic side projection, rasterised once at BASE px/mm (anti-aliased)."""
    k = id(tris)
    if k not in _cache:
        L, Z = tris[..., 0], tris[..., 2]; l0, z1 = L.min() - 5, Z.max() + 5
        w = int((L.max() - l0 + 5) * BASE); h = int((z1 - Z.min() + 5) * BASE)
        im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
        for t in np.stack([(L - l0) * BASE, (z1 - Z) * BASE], -1):
            d.polygon([tuple(p) for p in t], fill=255)
        _cache[k] = (im, l0, z1)
    return _cache[k]

def model_mask(tris, w, h, s, tx, ty, mirror=False):
    """Resample the projection onto a reference grid: pixel x = tx +/- L*s, y = ty - Z*s (pixel-area average, then > 0.5)."""
    im, l0, z1 = base_mask(tris); q = SS
    sg = -1.0 if mirror else 1.0
    # output (super-sampled) pixel (X, Y) -> base pixel: L = sg*(X/q - tx)/s ; Z = (ty - Y/q)/s
    a = sg * BASE / (s * q); c = (-sg * tx / s - l0) * BASE; e = BASE / (s * q); f = (z1 - ty / s) * BASE
    big = im.transform((w * q, h * q), Image.AFFINE, (a, 0, c, 0, e, f), Image.BILINEAR)
    return np.asarray(big.resize((w, h), Image.BOX)).astype(float) / 255 > 0.5

def iou(a, b): return float((a & b).sum() / max(1, (a | b).sum()))

def photo_mask():
    g = np.asarray(Image.open(os.path.join(REF, 'profile-right-photo.png')).convert('RGB')).astype(float).mean(-1)
    return g < 215

def drawing_masks():
    g = np.asarray(Image.open(os.path.join(REF, 'profile-both-sides-drawing.jpg')).convert('L')).astype(int)
    m = g < 75; m[:, :30] = 0; m[:, 770:] = 0; m[:30] = 0; m[575:] = 0          # < 75 keeps the body (<= 61), drops the soft drop shadow (>= 86)
    top = m.copy(); top[295:] = 0; bot = m.copy(); bot[:295] = 0
    return dict(left=top, right=bot)

def fit(tris, target, mirror):
    """Best similarity transform (scale, tx, ty) of the model onto a target mask, by coarse-to-fine search."""
    ys, xs = np.where(target); h, w = target.shape
    L, Z = tris[..., 0], tris[..., 2]
    s = (xs.max() - xs.min()) / (L.max() - L.min())
    cx = (xs.max() + xs.min()) / 2; lc = (L.max() + L.min()) / 2
    tx = cx - (-lc if mirror else lc) * s; ty = ys.min() + Z.max() * s
    best = (iou(model_mask(tris, w, h, s, tx, ty, mirror), target), s, tx, ty)
    for ds, dt in ((0.03, 6), (0.012, 3), (0.005, 1.5), (0.002, 0.7), (0.001, 0.35)):
        improved = True
        while improved:
            improved = False
            for a, b, c in ((ds, 0, 0), (-ds, 0, 0), (0, dt, 0), (0, -dt, 0), (0, 0, dt), (0, 0, -dt)):
                _, s0, x0, y0 = best
                # scale about the model centre so scale and translation stay decoupled
                s1 = s0 * (1 + a); x1 = x0 + b + (-lc if mirror else lc) * (s0 - s1); y1 = y0 + c
                v = iou(model_mask(tris, w, h, s1, x1, y1, mirror), target)
                if v > best[0] + 1e-5: best = (v, s1, x1, y1); improved = True
    return best

def overlay(target, model, path, scale=2):
    o = np.full(target.shape + (3,), (245, 242, 235), np.uint8)
    o[target & ~model] = (230, 120, 60); o[model & ~target] = (40, 110, 200); o[target & model] = (150, 110, 170)
    Image.fromarray(o).resize((o.shape[1] * scale, o.shape[0] * scale), Image.NEAREST).save(path)

REGIONS = [(0, 45, 'buttpad / butt plate'), (45, 186, 'stock'), (186, 202, 'castle nut / end plate'), (202, 372, 'receiver'), (372, 578, 'handguard'), (578, 594, 'gas block / front sight'), (594, 740, 'barrel / flash hider')]
def mismatches(target, model, n=5):
    x = target ^ model; lab, k = ndimage.label(x, structure=np.ones((3, 3)))
    out = []
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i); cx = xs.mean(); cy = ys.mean()
        reg = next((nm for a, b, nm in REGIONS if a <= cx < b), '?')
        if 202 <= cx < 372:
            reg = 'rear sight' if cy < 40 else 'upper receiver' if cy < 81 else 'grip' if cx < 262 and cy > 112 else 'magazine' if cx > 300 and cy > 141 else 'lower receiver / trigger guard'
        share = float(target[ys, xs].mean())
        kind = 'reference only (model too small)' if share > 0.8 else 'model only (model too big)' if share < 0.2 else f'mixed ({share * 100:.0f} percent reference only)'
        out.append(dict(area_px=int(len(ys)), bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], region=reg, kind=kind))
    out.sort(key=lambda d: -d['area_px'])
    return out[:n], int(x.sum())

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--round', type=int); ap.add_argument('--change', default=''); x = ap.parse_args()
    tris = np.load(os.path.join(HERE, 'work', 'tris.npz'))['tris']
    os.makedirs(os.path.join(HERE, 'r'), exist_ok=True)
    res = {}
    pm = photo_mask(); h, w = pm.shape
    mm = model_mask(tris, w, h, PXMM, X0, Y0)
    top5, xor = mismatches(pm, mm)
    res['right_photo'] = dict(iou=round(iou(pm, mm), 4), reference_px=int(pm.sum()), model_px=int(mm.sum()), mismatch_px=xor, top5=top5)
    overlay(pm, mm, os.path.join(HERE, 'r', 'silhouette_right_photo.png'), 3)
    bf = fit(tris, pm, False); res['right_photo']['iou_if_fitted'] = round(bf[0], 4)
    for side, tm in drawing_masks().items():
        v, s, tx, ty = fit(tris, tm, side == 'left')
        mmd = model_mask(tris, tm.shape[1], tm.shape[0], s, tx, ty, side == 'left')
        res[f'drawing_{side}'] = dict(iou=round(v, 4), fitted_px_per_mm=round(s, 4), reference_px=int(tm.sum()), model_px=int(mmd.sum()))
        ys, xs = np.where(tm | mmd); c = (slice(max(0, ys.min() - 8), ys.max() + 8), slice(max(0, xs.min() - 8), xs.max() + 8))
        overlay(tm[c], mmd[c], os.path.join(HERE, 'r', f'silhouette_drawing_{side}.png'), 2)
    # how well do the references agree with each other?  photo silhouette fitted onto the drawing's right side
    ys, xs = np.where(pm); pts = np.stack([(xs - X0) / PXMM, np.zeros(len(xs)), (Y0 - ys) / PXMM], -1)
    quads = np.stack([pts, pts + [1 / PXMM, 0, 0], pts + [1 / PXMM, 0, -1 / PXMM]], 1); quads2 = np.stack([pts, pts + [0, 0, -1 / PXMM], pts + [1 / PXMM, 0, -1 / PXMM]], 1)
    ptris = np.concatenate([quads, quads2])
    for side, tm in drawing_masks().items():
        res[f'reference_ceiling_photo_vs_drawing_{side}'] = round(fit(ptris, tm, side == 'left')[0], 4)
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(HERE, 'work', 'score.json'), 'w'), indent=1)
    if x.round is not None:
        p = os.path.join(HERE, 'work', 'rounds.json'); rounds = json.load(open(p)) if os.path.exists(p) else []
        rounds = [r for r in rounds if r['round'] != x.round]
        rounds.append(dict(round=x.round, change=x.change, iou_right_photo=res['right_photo']['iou'], iou_drawing_right=res['drawing_right']['iou'],
                           iou_drawing_left=res['drawing_left']['iou'], top5_mismatch=[f"{t['region']}: {t['area_px']} px, {t['kind']}" for t in top5]))
        json.dump(sorted(rounds, key=lambda r: r['round']), open(p, 'w'), indent=1)
