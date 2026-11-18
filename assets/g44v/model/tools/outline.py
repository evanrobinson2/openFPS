"""python3 tools/outline.py : source-indexed outlines traced from the official dimension image's left-side view.
Reads work/ref_mask_side.png (from tools/trace_ref.py). Writes outlines.json: polygons in model mm (L along the bore from
the slide's rear face, + toward the muzzle; Z up from the bore axis) plus the same polygons in photo pixels, and
work/outlines_check.png to look at.  The ruler: see RULER below and NOTES.md."""
import numpy as np, cv2, json, os
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULER = dict(px_per_mm=5.785, x_slide_rear=1157.5, y_bore=238.0,
             why='overall length 185 mm = 1069 px (5.778), slide length 174 mm = 1008 px (5.793): mean 5.785 px/mm; '
                 'bore axis at 57 % of the slide height below the slide top (muzzle seen in the 3D-viewer still)')
K, XR, YB = RULER['px_per_mm'], RULER['x_slide_rear'], RULER['y_bore']
m = np.asarray(Image.open(os.path.join(HERE, 'work/ref_mask_side.png'))) > 0
H, W = m.shape; yy, xx = np.mgrid[0:H, 0:W]
filled = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
def biggest(mask, eps=0.6):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea); c = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(float)
    return c
# the trigger-guard opening: the white region enclosed by the silhouette (largest hole), convex hull bridges the trigger
holes = (~m) & (cv2.floodFill(m.astype(np.uint8).copy(), None, (0, 0), 2)[1] != 2)
hole = holes & (xx > 480) & (xx < 800) & (yy > 360) & (yy < 560)      # the trigger splits the opening in two: take both halves
hy, hx = np.where(hole); hull = cv2.convexHull(np.stack([hx, hy], -1).astype(np.float32))[:, 0, :]
hull = cv2.approxPolyDP(hull, 0.4, True)[:, 0, :]
hullmask = np.zeros((H, W), np.uint8); cv2.fillPoly(hullmask, [hull.astype(np.int32)], 1); hullmask = hullmask > 0
solid = m | holes                                              # silhouette with every hole filled
Y_SLIDE_TOP, Y_PART, X_FRAME_FRONT = 170, 291, 168             # slide top (sights above), slide/frame parting line, frame's front face
plate_line = lambda x: 848 - (x - 945) * (26.0 / 195.0)        # the gap between the grip's bottom and the magazine floor plate
below_plate = (yy > plate_line(xx)) & (yy > 800) & (xx > 880)
P = {}
P['outer'] = biggest(solid)
P['slide'] = biggest(solid & (yy >= Y_SLIDE_TOP) & (yy < Y_PART))
P['front_sight'] = biggest(solid & (yy < Y_SLIDE_TOP - 2) & (xx < 400))
P['rear_sight'] = biggest(solid & (yy < Y_SLIDE_TOP - 2) & (xx > 900))
EL = lambda n: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (n, n))
fr = (solid & (yy >= Y_PART) & (xx >= X_FRAME_FRONT) & ~below_plate).astype(np.uint8)
fr = cv2.copyMakeBorder(fr, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=0)
fr = cv2.morphologyEx(cv2.morphologyEx(fr, cv2.MORPH_CLOSE, EL(11)), cv2.MORPH_OPEN, EL(9))[20:-20, 20:-20]   # close the dimension-line nicks, then drop the grip-texture pimples
P['frame'] = biggest(fr > 0, 0.5)
gr = cv2.morphologyEx(cv2.morphologyEx(solid.astype(np.uint8), cv2.MORPH_CLOSE, EL(11)), cv2.MORPH_OPEN, EL(9)) > 0
P['outer_smooth'] = biggest(gr, 0.5)
P['floor_plate'] = biggest(solid & below_plate)
P['guard_hole'] = hull
P['trigger'] = biggest(m & (cv2.erode(hullmask.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0), 0.5)
# ---- smooth versions for the organic polymer parts (Gaussian along the contour, 2.5 px = 0.43 mm)
from scipy.ndimage import gaussian_filter1d
def smooth_mask(mask, sigma=2.5, eps=0.35):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
    c = np.stack([gaussian_filter1d(c[:, 0], sigma, mode='wrap'), gaussian_filter1d(c[:, 1], sigma, mode='wrap')], -1)
    return cv2.approxPolyDP(c.astype(np.float32), eps, True)[:, 0, :].astype(float)
def poly_mask(c):
    mm = np.zeros((H, W), np.uint8); cv2.fillPoly(mm, [np.round(c).astype(np.int32)], 1); return mm > 0
frm = poly_mask(P['frame'])
P['frame'] = smooth_mask(frm)
P['floor_plate'] = smooth_mask(poly_mask(P['floor_plate']), 2.0)
P['trigger'] = smooth_mask(poly_mask(P['trigger']), 1.5, 0.3)
# ---- beavertail backstraps 17c (M, +2 mm) and 17d (L, +4 mm): the rear strap grown outward, plus the beavertail
# (manual p. 38: the straps add 2 / 4 mm; p. 9 shows the strap's shape.  The band and the beavertail are constructed, not traced.)
rear = np.array([np.where(r)[0].max() if r.any() else -1 for r in frm])            # rear-most frame pixel per row
for nm, t in (('backstrap_m', 2.0), ('backstrap_l', 4.0)):
    grown = cv2.dilate(frm.astype(np.uint8), EL(int(2 * t * K) | 1)) > 0
    band = np.zeros((H, W), bool)
    for y in range(int(YB + 13.0 * K), int(YB + 98.0 * K)):
        if rear[y] > 0: band[y, int(rear[y] - 5.0 * K):int(rear[y] + t * K + 3)] = True
    bt = np.zeros((H, W), np.uint8)                                                 # the beavertail over the tang
    pts = [(2.0, -9.6), (-6.0, -9.7), (-11.0 - t, -10.4), (-11.5 - t, -12.6), (-7.0 - t, -17.5), (-2.0, -21.0), (3.0, -16.0)]
    cv2.fillPoly(bt, [np.array([[XR - l * K, YB - z * K] for l, z in pts]).astype(np.int32)], 1)
    bs = ((grown & band) | (bt > 0)).astype(np.uint8)
    bs = cv2.morphologyEx(bs, cv2.MORPH_CLOSE, EL(9))
    P[nm] = smooth_mask(bs > 0, 3.0)
out = dict(source='https://eu-images.contentstack.com/v3/assets/bltf7171cc1cfc1a31f/blt9be7c190c34896ff/69036c17b4940ce99e7ceadd/18162-Glock-44-V.jpg',
           view='left side, muzzle to the left', ruler=RULER, px={}, mm={})
for k, c in P.items():
    out['px'][k] = [[round(float(x), 1), round(float(y), 1)] for x, y in c]
    out['mm'][k] = [[round(float(XR - x) / K, 3), round(float(YB - y) / K, 3)] for x, y in c]
    L = [p[0] for p in out['mm'][k]]; Z = [p[1] for p in out['mm'][k]]
    print(f'{k:12s} {len(c):4d} pts  L {min(L):7.2f} .. {max(L):7.2f}   Z {min(Z):7.2f} .. {max(Z):7.2f}')
json.dump(out, open(os.path.join(HERE, 'outlines.json'), 'w'), indent=0)
im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
for k, col in (('slide', (60, 60, 200)), ('frame', (60, 150, 60)), ('floor_plate', (200, 120, 0)), ('front_sight', (200, 0, 0)), ('rear_sight', (200, 0, 0)), ('guard_hole', (255, 255, 255)), ('trigger', (150, 0, 150)), ('backstrap_l', (120, 120, 120)), ('backstrap_m', (170, 170, 170))):
    d.polygon([tuple(p) for p in out['px'][k]], fill=col if 'backstrap' not in k else None, outline=(0, 0, 0))
im.crop((130, 120, 1240, 900)).save(os.path.join(HERE, 'work/outlines_check.png'))
