"""python3 model/tools/trace_reference.py  ->  model/reference_trace.json

Measures the primary profile reference (refs-local/commons-atf-mossberg-590.jpg, public domain, see
notes/REFERENCES.md) and writes numbers only. Method:
  1. Silhouette mask: luminance < 200 on the white background.
  2. Tilt: least-squares line through the barrel's top edge over its untapered front part, photo x = 820..1050
     (the rear 230 px of the barrel taper up to the chamber, so they are not used).
  3. Bore axis: midway between the barrel's top and bottom edges where both are visible (x = 990..1050).
  4. Ruler: the silhouette's extent along the bore (butt to muzzle) is the published overall length, 41 in
     (1041.4 mm). The photo cannot also satisfy the published 20 in barrel: see notes/NOTES.md, "The ruler", for
     the other rulers this photo allows, what each implies, and why this one was chosen.
  5. Every silhouette column is rotated into the gun frame (Z along the bore, + muzzle, Z = 0 at the receiver
     front face; Y up, 0 on the bore) and written as runs of covered Y, every 2 mm of Z.
"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, '..', 'refs-local', 'commons-atf-mossberg-590.jpg')
X_MUZZLE, X_BREECH, X_RECV_FRONT = 1117.0, 555.0, 577.0
OAL_MM = 41 * 25.4

def load():
    a = np.asarray(Image.open(SRC).convert('L')).astype(float)
    return a, a < 200

def frame(a, mask):
    xs = np.arange(820, 1050, 5); top = [np.where(mask[:, x])[0].min() for x in xs]
    slope, icpt = np.polyfit(xs, top, 1); th = float(np.arctan(slope))
    cs = []
    for x in range(990, 1050, 4):
        c = np.where(mask[:, x])[0]; brk = np.where(np.diff(c) > 1)[0]
        cs.append((x, (c[0] + c[brk[0]]) / 2.0))           # first run = the barrel
    cs = np.array(cs); y_axis_at = lambda x: float(np.mean(cs[:, 1] - slope * cs[:, 0]) + slope * x)
    F = dict(theta=th, slope=float(slope), y_axis0=y_axis_at(0.0), mm_per_px=1.0)
    ys, xs2 = np.where(mask); u, _ = to_gun(F, xs2.astype(float), ys.astype(float))
    cnt, edges = np.histogram(u, bins=np.arange(np.floor(u.min()), np.ceil(u.max()) + 2))
    good = np.where(cnt >= 3)[0]; ext_px = float(edges[good[-1] + 1] - edges[good[0]])
    F['mm_per_px'] = OAL_MM / ext_px; F['extent_px'] = ext_px
    return F

def to_gun(F, x, y):
    """photo pixel -> (Z mm, Y mm)"""
    c, s = np.cos(F['theta']), np.sin(F['theta'])
    x0, y0 = X_RECV_FRONT, F['y_axis0'] + F['slope'] * X_RECV_FRONT
    dx, dy = x - x0, y - y0
    return (dx * c + dy * s) * F['mm_per_px'], -(-dx * s + dy * c) * F['mm_per_px']

def to_px(F, z, yy):
    c, s = np.cos(F['theta']), np.sin(F['theta'])
    x0, y0 = X_RECV_FRONT, F['y_axis0'] + F['slope'] * X_RECV_FRONT
    u, v = z / F['mm_per_px'], -yy / F['mm_per_px']
    return x0 + u * c - v * s, y0 + u * s + v * c

def gun_mask(F, mask, z0=-560.0, z1=540.0, y0=-200.0, y1=40.0, step=0.5):
    """the silhouette resampled on a gun-frame grid (rows: Y from y1 down to y0; cols: Z)"""
    zs = np.arange(z0, z1, step); ys = np.arange(y1, y0, -step)
    Z, Y = np.meshgrid(zs, ys); px, py = to_px(F, Z, Y)
    xi = np.clip(np.rint(px).astype(int), 0, mask.shape[1] - 1); yi = np.clip(np.rint(py).astype(int), 0, mask.shape[0] - 1)
    ok = (px >= 0) & (px <= mask.shape[1] - 1) & (py >= 0) & (py <= mask.shape[0] - 1)
    return zs, ys, mask[yi, xi] & ok

def runs_of(col, ys):
    idx = np.where(col)[0]
    if not len(idx): return []
    out = []; s = p = idx[0]
    for i in idx[1:]:
        if i != p + 1: out.append((s, p)); s = i
        p = i
    out.append((s, p))
    return [[round(float(ys[a]), 1), round(float(ys[b]), 1)] for a, b in out if b - a >= 2]

if __name__ == '__main__':
    a, mask = load(); F = frame(a, mask)
    zs, ys, gm = gun_mask(F, mask)
    cols = {}
    for i in range(0, len(zs), 4):                       # every 2 mm
        r = runs_of(gm[:, i], ys)
        if r: cols[f'{zs[i]:.0f}'] = r
    out = dict(source='refs-local/commons-atf-mossberg-590.jpg (Wikimedia Commons File:Mossberg 590.jpg, public domain, ATF)',
               method=__doc__.split('Method:')[1].strip(), frame=F,
               anchors_px=dict(muzzle_x=X_MUZZLE, breech_x=X_BREECH, receiver_front_x=X_RECV_FRONT),
               extent_mm=dict(z_min=float(min(map(float, cols))), z_max=float(max(map(float, cols)))),
               runs_mm=cols)
    json.dump(out, open(os.path.join(HERE, 'reference_trace.json'), 'w'), separators=(',', ':'))
    print(json.dumps(F), out['extent_mm'])
    if '--lm' in sys.argv:
        for ln in open(sys.argv[sys.argv.index('--lm') + 1]):
            if ln.strip():
                n, x, y = ln.split(); z, yy = to_gun(F, float(x), float(y)); print(f'{n:28s} px({x},{y}) -> Z {z:8.1f}  Y {yy:7.1f}')
    if '--print' in sys.argv:
        for k in list(cols)[::4]: print(k, cols[k])
