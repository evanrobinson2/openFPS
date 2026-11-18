"""A frame strip of one hand clip: python3 tools/strip.py clip view[,view] out.jpg [frame frame ...] [--cols=N] [--size=WxH]

Renders the named frames (1-based, default: every frame) of a clip from refs-local/build/frames.npz (written by
clips/make.py) with the rifle's moving parts where the rifle clip has them, and pastes them into one picture, one row
per view, each tile labelled with its frame number and the rifle's frame.  Views: left, right, rear, top, sel_left
(close on the selector lever from the left), sel_rear (close, from behind and left), charge_left, charge_top."""
import os, sys, json, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'tools'))
import scene
VIEWS = dict(left=dict(eye=[700, -40, -60], target=[0, -40, -60], ortho_mm=520), right=dict(eye=[-700, -40, -60], target=[0, -40, -60], ortho_mm=520),
             rear=dict(eye=[0, -40, -800], target=[0, -40, -60], ortho_mm=420), top=dict(eye=[0, 700, -60], target=[0, 0, -60], up=[0, 0, 1], ortho_mm=520),
             sel_left=dict(eye=[600, -60, -175], target=[0, -60, -175], ortho_mm=190), sel_rear=dict(eye=[330, 40, -560], target=[5, -62, -175], fov_deg=17),
             sel_right=dict(eye=[-600, -75, -165], target=[0, -75, -165], ortho_mm=230), sel_below=dict(eye=[0, -600, -175], target=[0, 0, -175], up=[0, 0, 1], ortho_mm=230),
             charge_left=dict(eye=[700, -30, -90], target=[0, -30, -90], ortho_mm=420), charge_top=dict(eye=[60, 700, -90], target=[60, 0, -90], up=[0, 0, 1], ortho_mm=420),
             charge_rear=dict(eye=[420, 260, -620], target=[40, -20, -130], fov_deg=30))
if __name__ == '__main__':
    from PIL import Image, ImageDraw
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; clip, views, out = args[0], args[1].split(','), args[2]
    cols = int(next((a[7:] for a in sys.argv if a.startswith('--cols=')), 0)); W, H = [int(v) for v in next((a[7:] for a in sys.argv if a.startswith('--size=')), '420x420').split('x')]
    z = np.load(os.path.join(scene.BUILD, 'frames.npz'), allow_pickle=True); E = z['E'].item()[clip]; meta = json.loads(str(z['meta']))[clip]
    frames = [int(a) for a in args[3:]] or list(range(1, len(E) + 1)); cols = cols or len(frames); rows = -(-len(frames) // cols)
    sheet = Image.new('RGB', (cols * W, rows * len(views) * H), 'white'); tmp = os.path.join(scene.BUILD, 'strip_tmp_%d.jpg' % os.getpid())
    for i, f in enumerate(frames):
        fr = E[f - 1]; ms = scene.rifle_meshes(meta['rifle'], int(fr['rifle_frame'])) if meta['rifle'] else scene.rifle_meshes()
        for s in 'RL':
            M = scene.hl.mirror_mats if s == 'R' else (lambda m: m); ms += scene.hand_meshes(s, fr[s]['q'], M(fr[s]['H']), M(fr[s]['F']))
        for k, v in enumerate(views):
            scene.render(ms, VIEWS[v], tmp, size=(W, H), samples=10); im = Image.open(tmp).convert('RGB'); d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 150, 16], fill=(255, 255, 255)); d.text((4, 2), 'frame %d  rifle %s' % (f, fr['rifle_frame'] if meta['rifle'] else '-'), fill=(0, 0, 0))
            sheet.paste(im, ((i % cols) * W, ((i // cols) * len(views) + k) * H))
    os.remove(tmp); sheet.save(out, quality=88); print(out)
