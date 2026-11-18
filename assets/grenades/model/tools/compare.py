"""python3 tools/compare.py
Matched comparison of the renders in model/r/match_*.png against the reference figure crops in refs-local/.

Writes
  work/compare.json                     numbers only (committed): silhouette overlap and edge offsets per view
  ../renders/match_<view>.jpg           the matched render with the reference silhouette's outline traced over it (committed;
                                        the outline is a measurement of the figure, the figure's pixels are not included)
  ../refs-local/compare/<view>.jpg      figure | render | overlay, side by side (local only: it contains the figure)

The silhouette of a figure is everything that is not background connected to the picture's border, with the
background found by a brightness threshold (views.json "thr"). Cast shadows and the picture's frame leak into it;
the per-view notes in notes/COMPARISON.md say where. The render's silhouette is its alpha channel.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(HERE, '..', 'refs-local'); OUT = os.path.join(HERE, '..', 'renders'); LOCAL = os.path.join(REFS, 'compare')
os.makedirs(OUT, exist_ok=True); os.makedirs(LOCAL, exist_ok=True)
VIEWS = json.load(open(os.path.join(HERE, 'tools', 'views.json')))

def ref_mask(g, thr, bg, close_v=0):
    back = (g > thr) if bg == 'light' else (g < thr)
    if close_v: back = ~ndi.binary_closing(~back, structure=np.ones((close_v, 1), bool))      # bridge a light paint band on a dark can
    lab, n = ndi.label(back)
    border = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1]); border.discard(0)
    m = ~np.isin(lab, list(border))
    m = ndi.binary_opening(m, iterations=2)
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1)); m = lab == (1 + int(np.argmax(sizes)))
    return m

def outline(m): return m & ~ndi.binary_erosion(m, iterations=1)

def bbox(m):
    ys, xs = np.where(m); return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

res = {}
for name, v in VIEWS.items():
    if name.startswith('_'): continue
    rp = os.path.join(HERE, 'r', f'match_{name}.png')
    if not os.path.exists(rp): continue
    x0, y0, x1, y1 = v['crop']
    ref = Image.open(os.path.join(REFS, v['ref'])).convert('L').crop((x0, y0, x1, y1))
    W, H = ref.size
    rnd = Image.open(rp).convert('RGBA').resize((W, H), Image.LANCZOS)
    a = np.asarray(rnd)[..., 3] > 127
    g = np.asarray(ref).astype(float)
    m = ref_mask(g, v['thr'], v['bg'], v.get('close_v', 0))
    inter = (a & m).sum(); union = (a | m).sum()
    bb_r, bb_m = bbox(m), bbox(a); k = 1.0 / v['px_per_mm']
    rows = {}
    for frac in (0.15, 0.3, 0.5, 0.7, 0.85):      # body width at five heights of the reference silhouette
        y = int(bb_r[1] + frac * (bb_r[3] - bb_r[1]))
        xr = np.where(m[y])[0]; xm = np.where(a[y])[0]
        if len(xr) and len(xm): rows[str(frac)] = dict(ref_mm=round((xr.max() - xr.min()) * k, 1), model_mm=round((xm.max() - xm.min()) * k, 1))
    res[name] = dict(stem=v['stem'], iou=round(float(inter / union), 3), ref_only_px=int((m & ~a).sum()), model_only_px=int((a & ~m).sum()),
                     ref_bbox_px=bb_r, model_bbox_px=bb_m,
                     edge_offset_mm=dict(left=round((bb_m[0] - bb_r[0]) * k, 1), top=round((bb_m[1] - bb_r[1]) * k, 1), right=round((bb_m[2] - bb_r[2]) * k, 1), bottom=round((bb_m[3] - bb_r[3]) * k, 1)),
                     width_at_height=rows, mm_per_px=round(k, 4), camera=dict(az=v['az'], el=v['el'], roll=v['roll'], dist_mm=v['dist_mm']))
    bgc = (236, 236, 236) if v['bg'] == 'light' else (28, 28, 28)
    comp = Image.new('RGBA', (W, H), bgc + (255,)); comp.alpha_composite(rnd); comp = comp.convert('RGB')
    ov = comp.copy(); px = ov.load(); o = outline(m)
    for yy, xx in zip(*np.where(ndi.binary_dilation(o, iterations=1))): px[int(xx), int(yy)] = (255, 40, 40)
    ov.save(os.path.join(OUT, f'match_{name}.jpg'), quality=82)
    grey = comp.convert('L').convert('RGB')
    side = Image.new('RGB', (W * 3 + 20, H), (255, 255, 255)); side.paste(ref.convert('RGB'), (0, 0)); side.paste(grey, (W + 10, 0)); side.paste(ov, (2 * W + 20, 0))
    side.save(os.path.join(LOCAL, f'{name}.jpg'), quality=88)
    print(name, 'IoU', res[name]['iou'], 'edges mm', res[name]['edge_offset_mm'])
json.dump(res, open(os.path.join(HERE, 'work', 'compare.json'), 'w'), indent=1)
