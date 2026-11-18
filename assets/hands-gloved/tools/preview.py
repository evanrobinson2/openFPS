"""Scratch previews of solved grips (local only): python3 tools/preview.py name [name...] [view...] [--sheet]
--sheet renders four close views of the first grip's hand into one picture (refs-local/build/r/sheet_<name>.jpg)."""
import os, sys, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'tools'))
import scene
g = dict(np.load(os.path.join(scene.BUILD, 'grips_raw.npz'), allow_pickle=True)['g'].item())
VIEWS = dict(right=dict(eye=[-700, -40, -60], target=[0, -40, -60], ortho_mm=520), left=dict(eye=[700, -40, -60], target=[0, -40, -60], ortho_mm=520),
             rear=dict(eye=[-260, 40, -520], target=[0, -70, -150], fov_deg=30), fp=dict(eye=[0, 65.5, -260.6], target=[0, 20, 300], fov_deg=75),
             below=dict(eye=[0, -600, 0], target=[0, 0, 0.1], up=[0, 0, 1], ortho_mm=560), frontleft=dict(eye=[330, 120, 420], target=[0, -30, 60], fov_deg=32), topleft=dict(eye=[330, 330, -330], target=[0, 0, -130], fov_deg=30), rearleft=dict(eye=[280, 60, -560], target=[10, -30, -120], fov_deg=30))
def close(c, w=300.0):
    c = np.array(c, float)
    return [('right', dict(eye=list(c + [-600, 0, 0]), target=list(c), ortho_mm=w)), ('left', dict(eye=list(c + [600, 0, 0]), target=list(c), ortho_mm=w)),
            ('rear', dict(eye=list(c + [0, 0, -600]), target=list(c), ortho_mm=w)), ('below', dict(eye=list(c + [0, -600, 0]), target=list(c), up=[0, 0, 1], ortho_mm=w))]
if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if a in g]; views = [a for a in sys.argv[1:] if a in VIEWS] or ['right', 'left', 'rear']
    ms = scene.rifle_meshes()
    for n in names: ms += scene.hand_meshes(g[n]['side'], g[n]['q'], g[n]['H'], g[n]['F'], prefix=n)
    if '--sheet' in sys.argv:
        from PIL import Image
        c = g[names[0]]['H'][:3, 3] * ([-1, 1, 1] if g[names[0]]['side'] == 'R' else [1, 1, 1]) + [0, 20, 50]; sh = Image.new('RGB', (2000, 400), 'white')
        for i, (v, cam) in enumerate(close(c)):
            out = os.path.join(scene.BUILD, 'r', 'tmp_%s.jpg' % v); scene.render(ms, cam, out, size=(500, 400), samples=8); sh.paste(Image.open(out), (i * 500, 0)); os.remove(out)
        out = os.path.join(scene.BUILD, 'r', 'sheet_' + names[0] + '.jpg'); sh.save(out, quality=85); print(out); sys.exit()
    for v in views:
        out = os.path.join(scene.BUILD, 'r', 'pv_' + '_'.join(names) + '_' + v + '.jpg'); scene.render(ms, VIEWS[v], out, size=(1200, 800), samples=12); print(out)
