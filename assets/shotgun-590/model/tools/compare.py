"""python3 model/tools/compare.py   (after model/tools/render.py)

Matched comparison of the model's right-side render against the reference photo, in the photo's own pixel grid.
Writes model/compare.json (numbers) and renders/compare_right.jpg (photo, render, and the difference map).
The photo is public domain (notes/REFERENCES.md), so the comparison image may be committed."""
import json, os
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace_reference as T

photo = Image.open(T.SRC).convert('RGB'); a, pm = T.load(); F = T.frame(a, pm); K = F['mm_per_px']
ra = Image.open(os.path.join(HERE, 'build', 'r', 'match_right_alpha.png')).resize(photo.size, Image.LANCZOS)
mm = np.asarray(ra)[:, :, 3] > 127
rr = Image.open(os.path.join(HERE, 'build', 'r', 'match_right.png')).convert('RGB').resize(photo.size, Image.LANCZOS)

def iou(p, m): return float((p & m).sum() / max(1, (p | m).sum()))
REG = [('butt and pad', 20, 130), ('stock', 130, 300), ('wrist', 300, 365), ('receiver rear, trigger guard', 365, 470), ('receiver front, port', 470, 580),
       ('barrel root, action bars', 580, 683), ('forend', 683, 905), ('barrel, tube, lug band', 905, 1055), ('ring, cap, muzzle', 1055, 1125)]
regions = []
for name, x0, x1 in REG:
    p, m = pm[:, x0:x1], mm[:, x0:x1]
    regions.append(dict(region=name, photo_x=[x0, x1], iou=round(iou(p, m), 3), photo_px=int(p.sum()), model_px=int(m.sum()), only_photo_px=int((p & ~m).sum()), only_model_px=int((~p & m).sum())))
# outline: top and bottom edge of each column, where both exist
dt, db, cols = [], [], []
for x in range(pm.shape[1]):
    yp, ym = np.where(pm[:, x])[0], np.where(mm[:, x])[0]
    if len(yp) > 2 and len(ym) > 2: dt.append((ym.min() - yp.min()) * K); db.append((ym.max() - yp.max()) * K); cols.append(x)
dt, db = np.array(dt), np.array(db)
xs_p = np.where(pm.sum(0) > 2)[0]; xs_m = np.where(mm.sum(0) > 2)[0]
out = dict(method='silhouettes in the photo pixel grid; photo mask = luminance < 200, model mask = render alpha > 0.5; mm = px * %.4f' % K,
           iou=round(iou(pm, mm), 4), photo_px=int(pm.sum()), model_px=int(mm.sum()), only_photo_px=int((pm & ~mm).sum()), only_model_px=int((~pm & mm).sum()),
           length_mm=dict(photo=round((xs_p.max() - xs_p.min() + 1) * K, 1), model=round((xs_m.max() - xs_m.min() + 1) * K, 1)),
           top_edge_mm=dict(mean_abs=round(float(np.abs(dt).mean()), 2), p95_abs=round(float(np.percentile(np.abs(dt), 95)), 2), max_abs=round(float(np.abs(dt).max()), 2), worst_photo_x=int(cols[int(np.abs(dt).argmax())])),
           bottom_edge_mm=dict(mean_abs=round(float(np.abs(db).mean()), 2), p95_abs=round(float(np.percentile(np.abs(db), 95)), 2), max_abs=round(float(np.abs(db).max()), 2), worst_photo_x=int(cols[int(np.abs(db).argmax())])),
           regions=regions,
           not_measured='interior detail, materials, colour and lighting are compared by eye only (notes/COMPARE.md); nothing lateral can be compared: there is no top or front reference')
json.dump(out, open(os.path.join(HERE, 'compare.json'), 'w'), indent=1)
diff = np.full(pm.shape + (3,), 255, np.uint8); diff[pm & mm] = (150, 150, 150); diff[pm & ~mm] = (220, 40, 40); diff[~pm & mm] = (40, 90, 220)
W, H = photo.size; sheet = Image.new('RGB', (W, H * 3 + 54), 'white'); d = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(((photo, 'reference: Wikimedia Commons File:Mossberg 590.jpg (ATF, public domain)'), (rr, 'model: orthographic render in the same pixel grid'),
                               (Image.fromarray(diff), f'difference: grey both, red photo only, blue model only. IoU {out["iou"]:.3f}'))):
    sheet.paste(im, (0, i * (H + 18) + 18)); d.text((6, i * (H + 18) + 3), lab, fill=(0, 0, 0))
os.makedirs(os.path.join(HERE, '..', 'renders'), exist_ok=True)
sheet.save(os.path.join(HERE, '..', 'renders', 'compare_right.jpg'), quality=88)
print(json.dumps({k: out[k] for k in ('iou', 'length_mm', 'top_edge_mm', 'bottom_edge_mm')})); [print(r) for r in regions]

if '--zoom' in sys.argv:      # local inspection crops (not committed)
    for name, x0, x1 in (('rear', 20, 420), ('mid', 340, 720), ('front', 660, 1148)):
        tiles = [im.crop((x0, 20, x1, 150 if x0 > 300 else 240)).resize(((x1 - x0) * 2, (130 if x0 > 300 else 220) * 2), Image.LANCZOS) for im in (photo, rr, Image.fromarray(diff))]
        z = Image.new('RGB', (tiles[0].width, tiles[0].height * 3)); [z.paste(t, (0, i * t.height)) for i, t in enumerate(tiles)]
        z.save(os.path.join(HERE, 'build', 'r', f'zoom_{name}.png'))
