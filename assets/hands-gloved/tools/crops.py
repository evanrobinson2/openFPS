"""Cut the decomposition crops from the local reference photos (refs-local/, never committed) and draw the grid on them.
    python3 tools/crops.py
Regions are in the pixel frame of each photo scaled to 1920 px wide, as listed in notes/DECOMPOSITION.md."""
import os
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); REFS = os.path.join(HERE, 'refs-local')
CROPS = dict(R1=('R1_firing_hand_rear_right.jpg', (780, 660, 1300, 1040)), R2=('R2_support_hand_right_profile.jpg', (880, 440, 1480, 760)),
             R3=('R3_right_side_prone.jpg', (760, 700, 1520, 1060)))
def crop(key, grid=8, outw=1600):
    src, box = CROPS[key]; im = Image.open(os.path.join(REFS, src)); s = im.width / 1920.0
    c = im.crop(tuple(int(v * s) for v in box)); c = c.resize((outw, int(c.height * outw / c.width)), Image.LANCZOS)
    os.makedirs(os.path.join(REFS, 'crops'), exist_ok=True); c.save(os.path.join(REFS, 'crops', key + '_hands.jpg'), quality=92)
    g = c.copy(); d = ImageDraw.Draw(g); rows = max(2, round(grid * g.height / g.width))
    for i in range(1, grid): x = i * g.width // grid; d.line([(x, 0), (x, g.height)], fill=(255, 255, 0)); d.text((x + 3, 3), chr(65 + i), fill=(255, 255, 0))
    for j in range(1, rows): y = j * g.height // rows; d.line([(0, y), (g.width, y)], fill=(255, 255, 0)); d.text((3, y + 3), str(j + 1), fill=(255, 255, 0))
    g.save(os.path.join(REFS, 'crops', key + '_hands_grid.jpg'), quality=90); return c
if __name__ == '__main__':
    for k in CROPS: print(k, crop(k).size)
