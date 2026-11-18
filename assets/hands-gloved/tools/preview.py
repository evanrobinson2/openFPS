"""Scratch previews of solved grips (local only): python3 tools/preview.py name [name...]"""
import os, sys, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'tools'))
import scene
g = dict(np.load(os.path.join(scene.BUILD, 'grips_raw.npz'), allow_pickle=True)['g'].item())
VIEWS = dict(right=dict(eye=[-700, -40, -60], target=[0, -40, -60], ortho_mm=520), left=dict(eye=[700, -40, -60], target=[0, -40, -60], ortho_mm=520),
             rear=dict(eye=[-260, 40, -520], target=[0, -70, -150], fov_deg=30), fp=dict(eye=[0, 65.5, -260.6], target=[0, 20, 300], fov_deg=75),
             below=dict(eye=[0, -600, 0], target=[0, 0, 0.1], up=[0, 0, 1], ortho_mm=560), frontleft=dict(eye=[330, 120, 420], target=[0, -30, 60], fov_deg=32))
names = [a for a in sys.argv[1:] if a in g]; views = [a for a in sys.argv[1:] if a in VIEWS] or ['right', 'left', 'rear']
ms = scene.rifle_meshes()
for n in names: ms += scene.hand_meshes(g[n]['side'], g[n]['q'], g[n]['H'], g[n]['F'], prefix=n)
for v in views:
    out = os.path.join(scene.BUILD, 'r', 'pv_' + '_'.join(names) + '_' + v + '.jpg'); scene.render(ms, VIEWS[v], out, size=(1200, 800), samples=12); print(out)
