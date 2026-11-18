"""python3 tools/trace_ref.py : measure the official GLOCK dimension image (refs-local/glock-web/18162-Glock-44-V.jpg,
https://eu-images.contentstack.com/v3/assets/bltf7171cc1cfc1a31f/blt9be7c190c34896ff/69036c17b4940ce99e7ceadd/18162-Glock-44-V.jpg).
Writes work/ref_mask_side.png (silhouette of the left-side view), work/ref_mask_rear.png and prints the dimension-line pixel positions."""
import numpy as np, os, json
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
im = np.asarray(Image.open(os.path.join(HERE, 'refs-local/glock-web/18162-Glock-44-V.jpg')).convert('RGB')).astype(int)
R, G, B = im[..., 0], im[..., 1], im[..., 2]
orange = (R > 170) & (R - B > 70) & (G > 70) & (G < 200)
orange_d = ndimage.binary_dilation(orange, iterations=2)
dark = (im.mean(-1) < 150) & ~orange_d
def clean(m):
    m = ndimage.binary_closing(m, iterations=4)          # bridge the dimension lines that cross the body
    lab, n = ndimage.label(m); sizes = ndimage.sum(m, lab, range(1, n + 1)); return lab == (1 + int(np.argmax(sizes)))
side = dark.copy(); side[:, 1300:] = 0; side = clean(side)
rear = dark.copy(); rear[:, :1300] = 0; rear = clean(rear)
side = ndimage.binary_fill_holes(side) & ~(ndimage.binary_fill_holes(side) & ~side & ~ndimage.binary_dilation(orange, iterations=4) & (im.mean(-1) > 200))
Image.fromarray((side * 255).astype(np.uint8)).save(os.path.join(HERE, 'work/ref_mask_side.png'))
Image.fromarray((rear * 255).astype(np.uint8)).save(os.path.join(HERE, 'work/ref_mask_rear.png'))
for nm, m in (('side', side), ('rear', rear)):
    ys, xs = np.where(m); print(nm, 'bbox x', xs.min(), xs.max(), 'y', ys.min(), ys.max(), 'area', m.sum())
# orange dimension lines: long vertical / horizontal runs
cols = orange.sum(0); rows = orange.sum(1)
print('vertical orange lines at x:', [int(x) for x in np.where(cols > 60)[0]])
print('horizontal orange lines at y:', [int(y) for y in np.where(rows > 60)[0]])
for y in np.where(rows > 60)[0]:
    xs = np.where(orange[y])[0]; print('  y', y, 'x', xs.min(), xs.max())
for x in np.where(cols > 60)[0]:
    ys = np.where(orange[:, x])[0]; print('  x', x, 'y', ys.min(), ys.max())
