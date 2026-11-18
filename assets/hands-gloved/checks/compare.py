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

# ------------------------------------------------------------------ R1: from behind and below the right side, firing grip
# CR-1: version 1 tried a perspective pose from six points and rejected it (10 px RMS).  Its points lie about 95 px to the
# left of the ones read here, as if read off a differently cut crop.  Version 2 reads the points off the present crop and fits a scaled
# orthographic camera (the hands are 2.7 m from a 70 mm lens: depth changes scale by under 2 %):
#   1. a 2-D affine map from the plane of the receiver's right side (model z, y) to the crop, least squares over the points below;
#   2. the picture direction of the third axis (x, across the rifle) from the condition that the camera is rigid
#      (rows of a rotation times one scale), its sign from the camera being behind and to the right.
rifle_pts = {  # name: (model point, mm, asset frame), (crop x, crop y)
    'magazine release button, centre': ((-16.1, -35.7, -84.0), (865, 213)), 'selector, right side, pivot': ((-14.8, -34.6, -147.2), (575, 163)),
    'magazine well, bottom rear corner': ((-15.5, -80.8, -89.2), (848, 498)), 'ejection port cover hinge, rear end': ((-18.6, -8.6, -89.5), (808, 18)),
    'ejection port cover hinge, front end': ((-18.6, -8.6, -17.5), (1160, 42))}
X = np.array([v[0] for v in rifle_pts.values()], float); U = np.array([v[1] for v in rifle_pts.values()], float)
Aff, *_ = np.linalg.lstsq(np.c_[X[:, 2], X[:, 1], np.ones(len(X))], U, rcond=None); a1 = Aff[:2, 0]; a2 = Aff[:2, 1]; t0 = Aff[2]     # u = a1 . (z, y) + t0u ; v = a2 . (z, y) + t0v
rms = float(np.sqrt((((np.c_[X[:, 2], X[:, 1], np.ones(len(X))] @ Aff) - U) ** 2).sum(1).mean()))
pp, qq, cc = a1 @ a1, a2 @ a2, a1 @ a2; s2 = ((pp + qq) + math.sqrt((pp - qq) ** 2 + 4 * cc * cc)) / 2; sc = math.sqrt(s2)
bx = np.array([math.sqrt(max(s2 - pp, 0.0)), 0.0]); bx[1] = -cc / bx[0] if bx[0] > 1e-9 else math.sqrt(max(s2 - qq, 0.0))
if bx[0] > 0: bx = -bx                                    # camera behind and to the right: +x (the rifle's left) moves left in the picture
xbar = float(X[:, 0].mean())                               # the fitted plane sits at the points' mean x
def proj1(p): p = np.asarray(p, float); return np.array([a1[0] * p[2] + a1[1] * p[1] + bx[0] * (p[0] - xbar) + t0[0], a2[0] * p[2] + a2[1] * p[1] + bx[1] * (p[0] - xbar) + t0[1]])
r1 = np.array([bx[0], a1[1], a1[0]]) / sc; r2 = -np.array([bx[1], a2[1], a2[0]]) / sc; r3 = np.cross(r1, r2)      # picture right, picture up, toward the camera (asset x, y, z)
photo = dict(index_mcp_dorsal=(765, 335), middle_mcp_dorsal=(843, 470), ring_mcp_dorsal=(852, 620), little_mcp_dorsal=(818, 790), hand_back=(520, 500))
L = landmarks('fire'); model = {n: tuple(proj1(L[n])) for n in photo}
W, Hh = 1600, 1169; ctr = np.linalg.lstsq(np.array([r1 * sc, -r2 * sc, r3]), np.array([W / 2 - (t0[0] - bx[0] * xbar), Hh / 2 - (t0[1] - bx[1] * xbar), 0.0]), rcond=None)[0]
cam = dict(eye=list(ctr + r3 * 900.0), target=list(ctr), up=list(r2), ortho_mm=W / sc)
rp = scene.render(scene.rifle_meshes() + hands('fire'), cam, os.path.join(REN, 'compare_R1_firing_grip.jpg'), size=(W, Hh), samples=32)
side_by_side('R1', rp, photo, model, os.path.join(OUT, 'R1_side_by_side.jpg'))
err = {n: round(float(np.hypot(model[n][0] - photo[n][0], model[n][1] - photo[n][1]) / sc), 1) for n in photo}
yaw_cam = math.degrees(math.atan2(-r3[2], -r3[0])); elev = math.degrees(math.asin(-r3[1]))
res['R1'] = dict(grip='fire', camera=dict(kind='scaled orthographic, fitted', px_per_mm=round(sc, 3), points=list(rifle_pts), reprojection_rms_px=round(rms, 1), reprojection_rms_mm=round(rms / sc, 1),
                                         behind_square_on_deg=round(yaw_cam, 1), below_deg=round(elev, 1), note='In-plane map from five points on the receiver\'s right side; the across-rifle direction follows from the camera being rigid. No point off that plane was available to test it.'),
                 landmarks_px={n: dict(photo=list(photo[n]), model=[round(float(v), 1) for v in model[n]], error_mm=err[n]) for n in photo},
                 mean_error_mm=round(float(np.mean(list(err.values()))), 1), max_error_mm=max(err.values()),
                 note='Photo points are the knuckles as they show on the outline of the back of the hand, good to about 20 px (4 mm); the model points are joint landmarks on the glove. The shooter in R1 is prone; the model stands. '
                      'The support hand in R1 holds the front of the magazine well (R1-S01); that hold is not one of this asset\'s grips and is not drawn.')
print('R1 fit rms px', round(rms, 1), 'px/mm', round(sc, 2), 'camera behind', round(yaw_cam, 1), 'below', round(elev, 1), res['R1']['landmarks_px'], res['R1']['mean_error_mm'])

# ------------------------------------------------------------------ R3: right side, prone, rifle wrapped in cloth
# The cloth hides the rifle except the magazine release, so there is no ruler and no camera fit.  What can be measured without
# one: directions in the picture, and distances in units of the hand's own gloved finger breadth.
W, Hh = 1600, 757
rp = scene.render(scene.rifle_meshes() + hands('fire_indexed', 'mag_grip'), dict(eye=[-640.0, 150.0, -160.0], target=[0.0, -75.0, -95.0], up=[0, 1, 0], fov_deg=27.0), os.path.join(REN, 'compare_R3_indexed_and_magazine_grip.jpg'), size=(W, Hh), samples=32)
side_by_side('R3', rp, {}, {}, os.path.join(OUT, 'R3_side_by_side.jpg'))
ph = dict(index_axis=((650, 215), (955, 245)), gaps_between_wrapped_fingers=[((665, 295), (800, 330)), ((680, 455), (790, 470)), ((650, 580), (800, 585))], index_tip=(960, 250), button=(938, 128), finger_pitch_px=145.0)
ang = lambda a, b: math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))                      # picture angle, + = rising toward the muzzle
p_index = ang(*ph['index_axis']); p_wrapped = float(np.mean([ang(*g_) for g_ in ph['gaps_between_wrapped_fingers']]))
p_tip = ((ph['index_tip'][0] - ph['button'][0]) / ph['finger_pitch_px'], -(ph['index_tip'][1] - ph['button'][1]) / ph['finger_pitch_px'])
L = landmarks('fire_indexed'); zy = lambda n: np.array([L[n][2], L[n][1]]); el = lambda a, b: math.degrees(math.atan2((zy(b) - zy(a))[1], (zy(b) - zy(a))[0]))
m_index = el('index_mcp_dorsal', 'index_tip'); m_wrapped = float(np.mean([el(f + '_mcp_dorsal', f + '_pip_dorsal') for f in ('middle', 'ring', 'little')]))
fb = float(np.mean([hl.breadth(f) + 2 * hl.P['glove'] for f in ('middle', 'ring', 'little')])); btn = np.array([-84.0, -35.7]); m_tip = tuple((zy('index_tip') - btn) / fb)
res['R3'] = dict(grips=['fire_indexed', 'mag_grip'], camera=dict(kind='set by eye: the rifle in R3 is wrapped in cloth and shows too few points to fit'), landmarks_px={},
                 measures=dict(index_finger_against_the_three_wrapped_fingers_deg=dict(photo=round(p_index - p_wrapped, 1), model=round(m_index - m_wrapped, 1), how='photo: index axis against the mean direction of the three gaps between the wrapped fingers; model: index knuckle-to-tip against the mean knuckle-to-middle-joint direction of the three fingers, seen square from the right'),
                               index_finger_against_the_bore_deg=dict(photo=None, model=round(m_index, 1), how='the photo has no bore line (rifle wrapped); in the picture the finger lies %.1f deg from the picture\'s horizontal' % p_index),
                               index_tip_from_magazine_release_in_finger_breadths=dict(photo=dict(ahead=round(p_tip[0], 2), above=round(p_tip[1], 2)), model=dict(ahead=round(float(m_tip[0]), 2), above=round(float(m_tip[1]), 2)),
                                                                                       how='tip of the index finger relative to the centre of the button, in units of one gloved finger breadth (photo: 145 px between the gaps; model: %.1f mm)' % fb)),
                 photo_readings_px=ph, note='Read by eye, about 15 px; angles good to about 5 deg. The glove in R3 is a thick cold-weather glove. The magazine grip is compared by grid region only (notes/NOTES.md).')
print('R3', res['R3']['measures'])
json.dump(dict(asset='hands-gloved', method='see the docstring of checks/compare.py', photo_point_accuracy='about +-15 px of the 1600 px crop, read by eye', references=res,
               verdict='Not a fidelity score. Structural, visual and owner-review results are reported separately in notes/NOTES.md.'), open(os.path.join(HERE, 'checks', 'comparison.json'), 'w'), indent=1)
