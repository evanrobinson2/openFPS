"""python3 tools/sheets.py : contact sheets of the presentation renders in model/r/ -> ../renders/lineup_<view>.jpg"""
import os
from PIL import Image
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = ['frag', 'impact', 'flash', 'smoke-red', 'smoke-yellow', 'smoke-green', 'smoke-violet', 'smoke-white']
for view in ('front', 'lever', 'back', 'three_quarter', 'top'):
    ims = []
    for v in V:
        im = Image.open(os.path.join(HERE, 'r', f'grenade_{v}_{view}.png')).convert('RGBA'); bg = Image.new('RGBA', im.size, (232, 232, 232, 255)); bg.alpha_composite(im)
        ims.append(bg.convert('RGB').resize((320, 400), Image.LANCZOS))
    s = Image.new('RGB', (320 * len(ims), 400)); [s.paste(im, (320 * i, 0)) for i, im in enumerate(ims)]
    s.save(os.path.join(HERE, '..', 'renders', f'lineup_{view}.jpg'), quality=80)
