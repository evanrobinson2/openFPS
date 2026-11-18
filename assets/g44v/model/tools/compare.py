"""python3 tools/compare.py : the matched visual comparison (after `blender -b work/g44v.blend --python tools/render.py -- match_left`).
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
json.dump(res, open(os.path.join(HERE, 'compare.json'), 'w'), indent=1)
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
