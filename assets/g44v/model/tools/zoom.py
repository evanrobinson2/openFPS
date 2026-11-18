"""python3 tools/zoom.py <image> <x0> <y0> <x1> <y1> <scale> <out> [gamma] : crop with a labelled pixel grid, for reading coordinates off a reference."""
import sys, numpy as np
from PIL import Image, ImageDraw
src, x0, y0, x1, y1, s, out = sys.argv[1], *map(int, sys.argv[2:6]), float(sys.argv[6]), sys.argv[7]
g = float(sys.argv[8]) if len(sys.argv) > 8 else 0.5
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1))
a = np.asarray(im).astype(float) / 255; a = np.clip(a ** g * 1.15, 0, 1); im = Image.fromarray((a * 255).astype(np.uint8))
im = im.resize((int((x1 - x0) * s), int((y1 - y0) * s)), Image.LANCZOS); d = ImageDraw.Draw(im)
step = 10 if s >= 3 else 20 if s >= 1.5 else 50
for x in range((x0 // step + 1) * step, x1, step):
    big = x % (step * 5) == 0; d.line([((x - x0) * s, 0), ((x - x0) * s, im.height)], fill=(255, 0, 0) if big else (255, 150, 150), width=1)
    if big: d.text(((x - x0) * s + 2, 2), str(x), fill=(255, 0, 0))
for y in range((y0 // step + 1) * step, y1, step):
    big = y % (step * 5) == 0; d.line([(0, (y - y0) * s), (im.width, (y - y0) * s)], fill=(0, 160, 255) if big else (150, 210, 255), width=1)
    if big: d.text((2, (y - y0) * s + 2), str(y), fill=(0, 100, 255))
im.save(out)
