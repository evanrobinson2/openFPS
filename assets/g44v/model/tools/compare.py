"""python3 tools/compare.py : the matched visual comparison (after `blender -b ../../../build/g44v/g44v.blend --python tools/render.py -- match_left`).
The render uses the reference's camera: orthographic, 5.785 px/mm, the same 1654 x 1042 frame as the maker's dimension image.
Reference silhouette: work/ref_mask_side.png (tools/trace_ref.py, from the local copy of the image; see notes/REFERENCES.md).
Writes compare.json (numbers, committed), ../renders/compare_outline.png (the model render with the traced outlines drawn over it; no
reference pixels) and work/compare_overlay.png (render over the photo; local only)."""
import numpy as np, json, os, cv2
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = json.load(open(os.path.join(HERE, 'outlines.json'))); K = OUT['ruler']['px_per_mm']
rgba = np.asarray(Image.open(os.path.join(HERE, 'work/match_left.png')).convert('RGBA'))
model = rgba[..., 3] > 127
ref = np.asarray(Image.open(os.path.join(HERE, 'work/ref_mask_side.png'))) > 0
ref = cv2.morphologyEx(ref.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0     # close the dimension-line nicks
H, W = ref.shape; model = model[:H, :W]
model = cv2.morphologyEx(model.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0   # close the 0.4 mm running gap between slide and frame
# the trigger guard opening is open in both; fill nothing else
inter = (model & ref).sum(); union = (model | ref).sum()
res = dict(view='left side, orthographic, the reference camera', px_per_mm=K, iou=round(float(inter / union), 4),
           model_area_mm2=round(float(model.sum() / K ** 2), 1), reference_area_mm2=round(float(ref.sum() / K ** 2), 1),
           model_only_mm2=round(float((model & ~ref).sum() / K ** 2), 1), reference_only_mm2=round(float((ref & ~model).sum() / K ** 2), 1))
# outline distance, both ways
def edge(m): return m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
em, er = edge(model), edge(ref)
dm = cv2.distanceTransform((~em).astype(np.uint8), cv2.DIST_L2, 5); dr = cv2.distanceTransform((~er).astype(np.uint8), cv2.DIST_L2, 5)
d1 = dr[em] / K; d2 = dm[er] / K
res['outline_distance_mm'] = dict(model_to_reference=dict(mean=round(float(d1.mean()), 2), p95=round(float(np.percentile(d1, 95)), 2), max=round(float(d1.max()), 2)),
                                  reference_to_model=dict(mean=round(float(d2.mean()), 2), p95=round(float(np.percentile(d2, 95)), 2), max=round(float(d2.max()), 2)))
# grid regions: 6 x 4 cells over the reference's bounding box
ys, xs = np.where(ref); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
grid = []
for j in range(4):
    row = []
    for i in range(6):
        a, b = x0 + (x1 - x0) * i // 6, x0 + (x1 - x0) * (i + 1) // 6; c, d = y0 + (y1 - y0) * j // 4, y0 + (y1 - y0) * (j + 1) // 4
        m, r = model[c:d, a:b], ref[c:d, a:b]; u = (m | r).sum()
        row.append(None if u < 200 else round(float((m & r).sum() / u), 3))
    grid.append(row)
res['grid_iou_rows_top_to_bottom_cols_muzzle_to_rear'] = grid
# landmarks: feature positions read off the reference (px) against the model's (px in the matched render)
inv = json.load(open(os.path.join(HERE, 'inventory.json'))); parts = {q['name']: q for q in inv['parts']}
XR, YB = OUT['ruler']['x_slide_rear'], OUT['ruler']['y_bore']
def px(l, z): return [round(XR - l * K, 1), round(YB - z * K, 1)]
def cen(n): b = parts[n]['bbox_mm']; return px((b['L'][0] + b['L'][1]) / 2, (b['Z'][0] + b['Z'][1]) / 2)
def bb(n): b = parts[n]['bbox_mm']; return px(b['L'][1], b['Z'][1]) + px(b['L'][0], b['Z'][0])
LAND = [('trigger pin centre', cen('p28_trigger_pin'), [682, 350]), ('trigger housing pin centre', cen('p29_trigger_housing_pin'), [1047, 440]),
        ('front sight box', bb('p16a_front_sight'), [189, 148, 230, 170]), ('rear sight box', bb('p15_rear_sight'), [1067, 143, 1142, 170]),
        ('slide box', bb('p01_slide_guide_rail_l')[:1] + [round(YB - 11.75 * K, 1)] + [round(XR, 1), round(YB + 9.2 * K, 1)], [222, 170, 1157, 291]),
        ('floor plate box', bb('p35_magazine_floor_plate'), [905, 822, 1162, 875]),
        ('muzzle', px(parts['p02_barrel']['bbox_mm']['L'][1], 0), [150, 236])]
res['landmarks_px'] = [dict(name=n, model=m, reference=r, max_abs_diff_px=round(float(max(abs(a - b) for a, b in zip(m, r))), 1),
                            max_abs_diff_mm=round(float(max(abs(a - b) for a, b in zip(m, r)) / K), 2)) for n, m, r in LAND]
# ---- close-up matched regions and interior detail (v2).  Edges: Canny on a 1.5 px Gaussian blur of the luminance, inside the silhouette only.
# Both images are contrast-equalised (CLAHE) first.
# coverage = share of the reference's interior edge pixels that have a model edge within 0.6 mm; precision = the reverse.
def edges(gray, mask):
    g = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray); g = cv2.GaussianBlur(g, (0, 0), 1.5); e = cv2.Canny(g, 30, 70) > 0      # CLAHE first: the comparison should not depend on exposure
    return e & (cv2.erode(mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
def detail(ref_gray, ref_mask, mod_gray, mod_mask, box, k):
    x0, y0, x1, y1 = box; er = edges(ref_gray, ref_mask)[y0:y1, x0:x1]; em_ = edges(mod_gray, mod_mask)[y0:y1, x0:x1]; tol = 0.6 * k
    dm_ = cv2.distanceTransform((~em_).astype(np.uint8), cv2.DIST_L2, 5); dr_ = cv2.distanceTransform((~er).astype(np.uint8), cv2.DIST_L2, 5)
    m, r = mod_mask[y0:y1, x0:x1], ref_mask[y0:y1, x0:x1]
    return dict(box_px=list(box), iou=round(float((m & r).sum() / max((m | r).sum(), 1)), 4), reference_edge_px=int(er.sum()), model_edge_px=int(em_.sum()),
                edge_coverage=round(float((dm_[er] <= tol).mean()) if er.any() else 0.0, 3), edge_precision=round(float((dr_[em_] <= tol).mean()) if em_.any() else 0.0, 3))
def gray_of(path):
    a = np.asarray(Image.open(path).convert('RGBA')).astype(float); al = a[..., 3:4] / 255
    return ((a[..., :3] * al + 128 * (1 - al)).mean(-1)).astype(np.uint8), a[..., 3] > 127
ph = os.path.join(HERE, '..', 'refs-local', 'glock-web', '18162-Glock-44-V.jpg')
REG = dict(slide=(140, 130, 1170, 300), grip=(840, 430, 1240, 890), controls=(560, 280, 900, 530))
if os.path.exists(ph):
    rg = np.asarray(Image.open(ph).convert('L'))[:H, :W]; res['closeups'] = {}
    for tag, f in (('v2', 'work/match_left.png'), ('v1', 'work/match_left_v1.png')):
        if not os.path.exists(os.path.join(HERE, f)): continue
        mg, mm_ = gray_of(os.path.join(HERE, f)); mg, mm_ = mg[:H, :W], mm_[:H, :W]
        res['closeups'][tag] = {n: detail(rg, ref, mg, mm_, b, K) for n, b in REG.items()}
        for n, b in REG.items():
            if tag == 'v2':
                x0, y0, x1, y1 = b; pair = np.concatenate([np.stack([rg[y0:y1, x0:x1]] * 3, -1), np.stack([mg[y0:y1, x0:x1]] * 3, -1)], 0)
                Image.fromarray(pair.astype(np.uint8)).save(os.path.join(HERE, 'work', 'closeup_%s.png' % n))      # reference over model: local only
    res['closeups']['note'] = 'regions of the dimension image, same camera. iou: silhouette; edge_coverage: share of the photograph\'s interior edges matched by a model edge within 0.6 mm; edge_precision: the reverse. Photographic grain and lighting put edges in the reference that no model has, so coverage well below 1 is expected; the before/after change is what the number is for.'
# ---- the slide from above against manual p. 23 picture 27 (v2)
tr_ = os.path.join(HERE, '..', 'refs-local', 'img', 'p23_4.png'); res['slide_top_view'] = {}
for tag, tp in (('v2', os.path.join(HERE, 'work', 'match_top.png')), ('v1', os.path.join(HERE, 'work', 'match_top_v1.png'))):
  if os.path.exists(tp) and os.path.exists(tr_):
      KT = 3.494; rgt = np.asarray(Image.open(tr_).convert('L')); rmask = cv2.morphologyEx((rgt > 6).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)); ff = rmask.copy(); cv2.floodFill(ff, None, (0, 0), 2); rmask = (ff != 2)      # the dark slide on a black ground: close, then fill
      mg, mm_ = gray_of(tp); hh, ww = min(rgt.shape[0], mg.shape[0]), min(rgt.shape[1], mg.shape[1]); rgt, rmask, mg, mm_ = rgt[:hh, :ww], rmask[:hh, :ww], mg[:hh, :ww], mm_[:hh, :ww]
      d = detail(rgt, rmask, mg, mm_, (0, 0, ww, hh), KT); em2, er2 = edge(mm_), edge(rmask)
      dd = cv2.distanceTransform((~em2).astype(np.uint8), cv2.DIST_L2, 5)[er2] / KT
      d.update(px_per_mm=KT, reference='manual p. 23 picture 27 (slide from above)', outline_reference_to_model_mm=dict(mean=round(float(dd.mean()), 2), p95=round(float(np.percentile(dd, 95)), 2)))
      res['slide_top_view'][tag] = d
      Image.fromarray(np.concatenate([np.stack([rgt] * 3, -1), np.stack([mg] * 3, -1)], 0).astype(np.uint8)).save(os.path.join(HERE, 'work', 'closeup_top_%s.png' % tag))
json.dump(res, open(os.path.join(HERE, 'compare.json'), 'w'), indent=1)
print('closeups', json.dumps(res.get('closeups', {}).get('v1')), '\n      v2', json.dumps(res.get('closeups', {}).get('v2')), '\n top', json.dumps(res.get('slide_top_view')))
print('IoU', res['iou'], '| outline mm', res['outline_distance_mm']); print('grid', grid)
for q in res['landmarks_px']: print(' ', q['name'], q['model'], q['reference'], q['max_abs_diff_mm'], 'mm')
# figure without reference pixels: the render with the traced outlines over it
im = Image.fromarray(rgba).convert('RGBA'); bg = Image.new('RGBA', im.size, (235, 235, 235, 255)); bg.alpha_composite(im); d = ImageDraw.Draw(bg)
for k, col in (('outer_smooth', (230, 60, 0)), ('guard_hole', (230, 60, 0)), ('slide', (0, 110, 230)), ('trigger', (0, 150, 60)), ('floor_plate', (150, 0, 180))):
    pts = [tuple(q) for q in OUT['px'][k]]; d.line(pts + pts[:1], fill=col + (255,), width=2)
bg.convert('RGB').crop((100, 100, 1280, 920)).save(os.path.join(HERE, '..', 'renders', 'compare_outline.png'), optimize=True)
# local overlay on the photo
ph = os.path.join(HERE, '..', 'refs-local', 'glock-web', '18162-Glock-44-V.jpg')
if os.path.exists(ph):
    p = np.asarray(Image.open(ph).convert('RGB')).astype(float)[:H, :W]; o = p.copy()
    o[model & ~ref] = o[model & ~ref] * 0.4 + np.array([255, 0, 0]) * 0.6; o[ref & ~model] = o[ref & ~model] * 0.4 + np.array([0, 0, 255]) * 0.6
    side = np.concatenate([p, o, np.asarray(bg.convert('RGB')).astype(float)[:H, :W]], 0)
    Image.fromarray(side.astype(np.uint8)).save(os.path.join(HERE, 'work', 'compare_overlay.png'))
