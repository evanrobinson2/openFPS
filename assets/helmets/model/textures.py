"""Procedural, tileable surface textures for the helmet kit (numpy only, no image sources).

Every map is periodic (built in the frequency domain or from integer-period functions), so it tiles without seams.
Each function returns float arrays in 0..1; `save_png` writes 8-bit PNGs. Normal maps are OpenGL convention (+Y up),
which is what glTF expects.
"""
import math

import numpy as np
from PIL import Image


def _rng(seed):
    return np.random.default_rng(seed)


def band_noise(n, lo, hi, seed, aniso=(1.0, 1.0)):
    """Periodic noise with energy between spatial frequencies lo..hi (cycles per tile)."""
    r = _rng(seed)
    f = np.fft.fftfreq(n) * n
    fx, fy = np.meshgrid(f * aniso[0], f * aniso[1])
    rad = np.sqrt(fx ** 2 + fy ** 2)
    amp = np.where((rad >= lo) & (rad <= hi), 1.0, 0.0) / np.maximum(rad, 1.0)
    ph = r.standard_normal((n, n)) + 1j * r.standard_normal((n, n))
    out = np.real(np.fft.ifft2(ph * amp))
    out -= out.min()
    return out / max(out.max(), 1e-9)


def normal_from_height(h, strength):
    """Height (0..1, periodic) to a tangent-space normal map."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx ** 2 + dy ** 2 + nz ** 2)
    n = np.stack([-dx / l, dy / l, nz / l], -1)
    return n * 0.5 + 0.5


def save_png(path, a):
    a = np.clip(a, 0, 1)
    if a.ndim == 2:
        img = Image.fromarray((a * 255 + 0.5).astype(np.uint8), 'L')
    else:
        img = Image.fromarray((a * 255 + 0.5).astype(np.uint8), 'RGB')
    img.save(path, optimize=True)


def srgb(hexstr):
    h = hexstr.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


# --- the maps -------------------------------------------------------------------------------------------------

def paint(n=1024, seed=1):
    """Textured ballistic-shell paint: orange peel plus fine grit; tile is 120 mm."""
    peel = band_noise(n, 60, 120, seed)
    grit = band_noise(n, 220, n // 2, seed + 1)
    h = 0.25 * peel + 0.75 * grit
    rough = 0.84 + 0.1 * (band_noise(n, 2, 8, seed + 2) - 0.5) + 0.1 * (grit - 0.5)
    tint = 0.97 + 0.03 * band_noise(n, 3, 12, seed + 3) - 0.04 * grit   # (dust and wear, multiplied in)
    return {'height': h, 'normal': normal_from_height(h, 0.9), 'rough': rough, 'tint': tint}


def loop_fabric(n=512, seed=11):
    """Hook-and-loop 'loop' pile: dense random fibres; tile is 40 mm."""
    fib = band_noise(n, 60, n // 2, seed, aniso=(1.0, 0.55))
    clump = band_noise(n, 12, 30, seed + 1)
    h = 0.7 * fib + 0.3 * clump
    tint = 0.86 + 0.14 * h
    return {'normal': normal_from_height(h, 7.0), 'rough': 0.95 + 0.05 * h, 'tint': 0.78 + 0.22 * h}


def webbing(n=512, seed=21, picks=64):
    """2/2 twill nylon webbing; tile is 25.4 mm (one strap width), `picks` yarns per tile each way."""
    y, x = np.mgrid[0:n, 0:n] / n
    u, v = x * picks, y * picks
    warp_up = ((np.floor(u) + np.floor(v)) % 4) < 2                  # twill float pattern
    fu, fv = u % 1, v % 1
    warp = np.sin(np.pi * fu) ** 0.6                               # yarn rounding across its width
    weft = np.sin(np.pi * fv) ** 0.6
    h = np.where(warp_up, 0.55 + 0.45 * warp * (0.75 + 0.25 * np.cos(2 * np.pi * fv)),
                 0.55 + 0.45 * weft * (0.75 + 0.25 * np.cos(2 * np.pi * fu)))
    h = 0.85 * h + 0.15 * band_noise(n, 100, n // 2, seed)
    return {'normal': normal_from_height(h, 3.0), 'rough': 0.78 + 0.12 * h, 'tint': 0.9 + 0.1 * h}


def braid(n=512, seed=31, strands=16):
    """Braided elastic shock cord sleeve; tile is 12 mm along the cord."""
    y, x = np.mgrid[0:n, 0:n] / n
    a = np.sin(2 * np.pi * (x * strands / 2 + y * strands))
    b = np.sin(2 * np.pi * (x * strands / 2 - y * strands))
    h = np.maximum(a, b) * 0.5 + 0.5
    h = 0.9 * h + 0.1 * band_noise(n, 90, n // 2, seed)
    return {'normal': normal_from_height(h, 3.5), 'rough': 0.7 + 0.2 * h, 'tint': 0.85 + 0.15 * h}


def foam_fabric(n=512, seed=41):
    """Pad cover: wicking knit over foam; tile is 30 mm."""
    y, x = np.mgrid[0:n, 0:n] / n
    knit = (np.sin(2 * np.pi * x * 48) * np.sin(2 * np.pi * y * 96)) * 0.5 + 0.5
    h = 0.6 * knit + 0.4 * band_noise(n, 40, n // 2, seed)
    return {'normal': normal_from_height(h, 1.6), 'rough': 0.9 + 0.05 * h, 'tint': 0.88 + 0.12 * h}


def polymer(n=512, seed=51):
    """Moulded glass-filled polymer (rails, shroud body, buckles, ear cups): fine stipple; tile is 30 mm."""
    st = band_noise(n, 70, 200, seed)
    h = st
    return {'normal': normal_from_height(h, 1.2), 'rough': 0.55 + 0.2 * st, 'tint': 0.95 + 0.05 * st}


def cast_metal(n=512, seed=61):
    """Hard-anodised aluminium (shroud, front plate): bead-blast; tile is 30 mm."""
    g = band_noise(n, 150, n // 2, seed)
    return {'normal': normal_from_height(g, 0.8), 'rough': 0.42 + 0.16 * g, 'tint': 0.96 + 0.04 * g}


def leatherette(n=512, seed=71):
    """Protein-leather ear seals: pebbled grain; tile is 30 mm."""
    cells = band_noise(n, 40, 90, seed)
    h = 1 - np.abs(cells - 0.5) * 2
    h = h ** 3
    return {'normal': normal_from_height(h, 2.0), 'rough': 0.45 + 0.25 * h, 'tint': 0.9 + 0.1 * h}


def digital_camo(n=1024, seed=81, colours=('#8b9474', '#5f6a47', '#463b2c', '#232220'), px=8):
    """An original four-colour digital (pixel) woodland pattern; tile is 300 mm, pixel `px` texels (about 1.8 mm).

    Layered thresholds of periodic noise at two scales, quantised to a square pixel grid, the way digital patterns
    are built. The colours are a generic Eastern-European field palette (light grey-green, olive, brown, black).
    """
    px = max(2, px * n // 1024)                      # (same pixel size in millimetres at any texture size)
    m = n // px
    lay = []
    for i, (lo, hi) in enumerate(((5, 12), (7, 17), (10, 24))):
        f = band_noise(m, lo, hi, seed + i) * 0.7 + band_noise(m, 24, 48, seed + 10 + i) * 0.3
        lay.append(f)
    idx = np.zeros((m, m), int)
    idx[lay[0] > 0.52] = 1
    idx[lay[1] > 0.6] = 2
    idx[(lay[2] > 0.66) & (idx != 0)] = 3
    pal = np.array([srgb(c) for c in colours])
    col = pal[idx]
    col = np.kron(col, np.ones((px, px, 1)))
    weave = foam_fabric(n, seed + 99)
    fade = 0.93 + 0.07 * band_noise(n, 2, 6, seed + 50)[..., None]
    return {'color': col * fade, 'normal': webbing(n, seed + 5, picks=200)['normal'],
            'rough': 0.86 + 0.08 * band_noise(n, 100, n // 2, seed + 7)}


def foam_ball(n=256, seed=91):
    """Open-cell foam windscreen."""
    c = band_noise(n, 30, 120, seed)
    h = (c > 0.5).astype(float) * 0.6 + c * 0.4
    return {'normal': normal_from_height(h, 3.0), 'rough': 0.95 + 0 * h, 'tint': 0.8 + 0.2 * h}


MAPS = {
    'paint': paint, 'loop': loop_fabric, 'webbing': webbing, 'braid': braid, 'foam_fabric': foam_fabric,
    'polymer': polymer, 'metal': cast_metal, 'leatherette': leatherette, 'foam_ball': foam_ball,
}
