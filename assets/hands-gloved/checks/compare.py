"""Matched visual comparison of the solved grips with the reference photographs.  Writes checks/comparison.json and
renders/compare_*.jpg (simulation-generated pictures only).  The side-by-side pictures with the photographs go to
refs-local/build/compare/ and stay local.

    python3 checks/compare.py        # needs refs-local/ (the photographs), the local rifle build and Blender

For each reference: (1) fit the photograph's camera from points of the rifle that the model also has, (2) render the
rifle and the hands from that camera with the photograph's framing, (3) project the model's hand landmarks into the
picture and compare them with the same landmarks read off the photograph.

The photograph coordinates below were read by eye from gridded crops (tools/crops.py); they are good to about
+-15 px of the 1600 px crops (about +-3 mm at the rifle).  They are the only numbers here that come from the
photographs, and they are positions of things, not image content."""
import os, sys, json, math
import numpy as np, cv2
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ('model', 'grips', 'tools'): sys.path.insert(0, os.path.join(HERE, d))
import handlib as hl, scene, crops
Image.MAX_IMAGE_PIXELS = None
G = dict(np.load(os.path.join(scene.BUILD, 'grips_raw.npz'), allow_pickle=True)['g'].item()); h = scene.hand()
OUT = os.path.join(scene.BUILD, 'compare'); os.makedirs(OUT, exist_ok=True); REN = os.path.join(HERE, 'renders'); os.makedirs(REN, exist_ok=True)
def landmarks(name):
    g = G[name]; L = h.pose_landmarks(h.skin_mats(h.fk(g['q'], g['H'], g['F']))); s = np.array([-1, 1, 1]) if g['side'] == 'R' else np.ones(3)
    return {k: v * s for k, v in L.items()}
def hands(*names): return [m for n in names for m in scene.hand_meshes(G[n]['side'], G[n]['q'], G[n]['H'], G[n]['F'], prefix=n)]
def side_by_side(key, render_path, pts_photo, pts_model, out):
    a = crops.crop(key).convert('RGB'); b = Image.open(render_path).convert('RGB').resize(a.size); sh = Image.new('RGB', (a.width * 2 + 12, a.height), 'white')
    for im, pts, x0 in ((a, pts_photo, 0), (b, pts_model, a.width + 12)):
        d = ImageDraw.Draw(im)
        for k, (x, y) in pts.items(): d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 255, 0), width=2); d.text((x + 9, y - 6), k, fill=(255, 255, 0))
        if im is b:
            for k, (x, y) in pts_photo.items(): d.line([x - 8, y, x + 8, y], fill=(255, 60, 60), width=2); d.line([x, y - 8, x, y + 8], fill=(255, 60, 60), width=2)
        sh.paste(im, (x0, 0))
    sh.save(out, quality=90)
res = {}

# ------------------------------------------------------------------ R2: right profile, support grip (orthographic fit)
# rifle: top of the handguard at crop y 235, bottom at 497 (68.0 mm apart in the model); rear of the handguard at x 924
k = (497.0 - 235.0) / 68.0; x0, y0 = 924.0, 235.0 + 36.79 * k; W, Hh = 1600, 853
photo = dict(little_tip=(1140, 250), ring_tip=(1205, 200), middle_tip=(1305, 215), index_tip=(1425, 322), thumb_tip=(1300, 120))
L = landmarks('support'); model = {n: (x0 + k * L[n][2], y0 - k * L[n][1]) for n in photo}
cam = dict(eye=[-900.0, (y0 - Hh / 2) / k, (W / 2 - x0) / k], target=[0.0, (y0 - Hh / 2) / k, (W / 2 - x0) / k], up=[0, 1, 0], ortho_mm=W / k)
rp = scene.render(scene.rifle_meshes() + hands('support', 'fire_indexed'), cam, os.path.join(REN, 'compare_R2_support_grip.jpg'), size=(W, Hh), samples=32)
side_by_side('R2', rp, photo, model, os.path.join(OUT, 'R2_side_by_side.jpg'))
err = {n: round(float(np.hypot(model[n][0] - photo[n][0], model[n][1] - photo[n][1]) / k), 1) for n in photo}
res['R2'] = dict(grip='support', camera=dict(kind='orthographic, from the right', px_per_mm=round(k, 3), fitted_from='handguard height 68.0 mm and the rear end of the handguard'),
                 landmarks_px={n: dict(photo=list(photo[n]), model=[round(float(v), 1) for v in model[n]], error_mm=err[n]) for n in photo},
                 mean_error_mm=round(float(np.mean(list(err.values()))), 1), max_error_mm=max(err.values()),
                 hand_centre_along_bore_mm=dict(photo=round(float(np.mean([(photo[n][0] - x0) / k for n in ('little_tip', 'ring_tip', 'middle_tip', 'index_tip')])), 1), model=round(float(np.mean([L[n][2] for n in ('little_tip', 'ring_tip', 'middle_tip', 'index_tip')])), 1)),
                 note='The glove in R2 is a thick cold-weather glove (24.7 mm per finger against the model\'s 23.3 mm); its thumb tip stands about 10 mm higher over the rail than a thin glove would.')
print('R2', res['R2']['landmarks_px'], res['R2']['mean_error_mm'])

# ------------------------------------------------------------------ R1: from behind the right shoulder, firing grip (perspective fit)
s1 = 1289.0 / 1600.0; o1 = np.array([1934.0, 1636.0])                       # crop pixel -> photo pixel
rifle_pts = {  # name: (model point, mm, asset frame), (crop x, crop y)
    'selector axis, right': ((-14.8, -34.6, -147.2), (478, 165)), 'takedown pin, right': ((-14.2, -21.2, -166.1), (355, 95)),
    'magazine release button': ((-16.1, -35.7, -84.0), (770, 215)), 'magazine well, bottom rear corner': ((-15.5, -80.8, -89.2), (765, 505)),
    'ejection port cover hinge, rear end': ((-18.6, -8.6, -89.5), (700, 25)), 'ejection port cover hinge, front end': ((-18.6, -8.6, -17.5), (1050, 45))}
obj = np.array([v[0] for v in rifle_pts.values()], np.float64); img = np.array([np.array(v[1]) * s1 + o1 for v in rifle_pts.values()], np.float64)
im_w, im_h = 4761, 3174; best = None
# the lens: 70 mm on a 36 mm sensor 5184 px wide (the photo's EXIF; the published file is that frame cropped to 4761 px)
for f_mm in (70.0,):
    f = f_mm / 36.0 * 5184.0; K = np.array([[f, 0, im_w / 2], [0, f, im_h / 2], [0, 0, 1.0]])
    ok, rv, tv = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
    pr, _ = cv2.projectPoints(obj, rv, tv, K, None); e = float(np.sqrt(((pr.reshape(-1, 2) - img) ** 2).sum(1).mean())); best = (e, f_mm, f, rv, tv, K)
e, f_mm, f, rv, tv, K = best; Rm, _ = cv2.Rodrigues(rv); eye = (-Rm.T @ tv).ravel()
def proj1(p): pr, _ = cv2.projectPoints(np.array([p], np.float64), rv, tv, K, None); return (pr.reshape(2) - o1) / s1
photo = dict(index_mcp_dorsal=(690, 330), wrist_dorsal=(430, 585), hand_back=(450, 480), ring_mcp_dorsal=(752, 600), little_mcp_dorsal=(735, 790))
L = landmarks('fire'); model = {n: tuple(proj1(L[n])) for n in photo}
W, Hh = 1600, 1169; dist = float(np.linalg.norm(eye - np.array([-15.0, -60.0, -150.0])))
# The fit is not trusted: six nearly coplanar points read by eye, 10 px RMS, and the fitted camera puts the model's rifle at
# a visibly different size and side from the photograph.  So no landmark errors are claimed for R1; the picture is rendered
# from a camera set by eye (behind and below the right side) and compared by grid region in notes/NOTES.md.
rp = scene.render(scene.rifle_meshes() + hands('fire'), dict(eye=[-560.0, -230.0, -470.0], target=[-5.0, -85.0, -120.0], up=[0, 1, 0], fov_deg=21.0), os.path.join(REN, 'compare_R1_firing_grip.jpg'), size=(W, Hh), samples=32)
side_by_side('R1', rp, {}, {}, os.path.join(OUT, 'R1_side_by_side.jpg'))
res['R1'] = dict(grip='fire', camera=dict(kind='set by eye', rejected_fit=dict(kind='perspective pose from six points of the rifle, focal length 70 mm from EXIF', points=list(rifle_pts), reprojection_rms_px_of_photo=round(e, 1),
                                         eye_mm=[round(float(x), 0) for x in eye], why_rejected='points nearly coplanar and read by eye; the fitted view shows the rifle at the wrong size and from the wrong side')),
                 landmarks_px={}, note='No numbers are claimed for R1. The support hand in R1 holds the front of the magazine well (R1-S01); that hold is not one of this asset\'s grips and is not drawn. The shooter in R1 is prone; the model\'s forearm is solved for standing.')
print('R1 fit rejected, rms', round(e, 1))

# ------------------------------------------------------------------ R3: right side, prone, rifle wrapped (no rifle points to fit: camera set by eye)
W, Hh = 1600, 757
rp = scene.render(scene.rifle_meshes() + hands('fire_indexed', 'mag_grip'), dict(eye=[-640.0, 150.0, -160.0], target=[0.0, -75.0, -95.0], up=[0, 1, 0], fov_deg=27.0), os.path.join(REN, 'compare_R3_indexed_and_magazine_grip.jpg'), size=(W, Hh), samples=32)
side_by_side('R3', rp, {}, {}, os.path.join(OUT, 'R3_side_by_side.jpg'))
res['R3'] = dict(grips=['fire_indexed', 'mag_grip'], camera=dict(kind='set by eye: the rifle in R3 is wrapped in cloth and shows too few points to fit'), landmarks_px={},
                 note='Compared by grid region only (notes/NOTES.md). No numbers are claimed for R3.')
json.dump(dict(asset='hands-gloved', method='see the docstring of checks/compare.py', photo_point_accuracy='about +-15 px of the 1600 px crop, read by eye', references=res,
               verdict='Not a fidelity score. Structural, visual and owner-review results are reported separately in notes/NOTES.md.'), open(os.path.join(HERE, 'checks', 'comparison.json'), 'w'), indent=1)
