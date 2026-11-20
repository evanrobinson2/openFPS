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

def _scratches(n, seed, count, len_mm, tile_mm, width_px=1.2):
    """Periodic field (0..1) of thin random scratches and their burnished halo, drawn with wrap-around."""
    r = _rng(seed)
    acc = np.zeros((n, n))
    halo = np.zeros((n, n))
    px = n / tile_mm
    for _ in range(count):
        L = r.uniform(*len_mm) * px
        x0, y0 = r.uniform(0, n, 2)
        ang = r.uniform(0, np.pi)
        bend = r.uniform(-0.25, 0.25)
        steps = max(4, int(L * 1.5))
        t = np.linspace(0, 1, steps)
        a = ang + bend * (t - 0.5)
        xs = (x0 + np.cumsum(np.cos(a)) * L / steps) % n
        ys = (y0 + np.cumsum(np.sin(a)) * L / steps) % n
        depth = np.sin(np.pi * t) ** 0.5 * r.uniform(0.4, 1.0)
        xi, yi = xs.astype(int), ys.astype(int)
        np.maximum.at(acc, (yi, xi), depth)
        np.maximum.at(halo, (yi, xi), depth)
    # widen: scratch core ~width_px, halo a few px
    k = np.fft.fftfreq(n)
    kx, ky = np.meshgrid(k, k)
    def blur(a, s):
        return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (kx ** 2 + ky ** 2))))
    core = np.clip(blur(acc, width_px * 0.5) * width_px * 2.2, 0, 1)
    halo = np.clip(blur(halo, width_px * 3.0) * width_px * 9.0, 0, 1)
    return core, halo


def paint(n=1024, seed=1):
    """Textured ballistic-shell coating, worn: sand-grit stipple, orange peel, scuffs, scratches and dust.
    Tile is 120 mm (0.12 mm a texel at 1024)."""
    sc = n / 1024
    peel = band_noise(n, 25, 60, seed)                                  # 2-5 mm orange peel
    grain = band_noise(n, 140, 330, seed + 1)                           # 0.35-0.85 mm sand grit in the coat
    grit = np.clip((grain - 0.5) * 3.2 + 0.5, 0, 1) ** 1.6              # sharpened: discrete bumps, not fuzz
    fine = band_noise(n, 330, n // 2, seed + 4) if n >= 512 else np.zeros((n, n))
    # scuffs: patches where the grit tops are rubbed flat and slightly polished (handling, rifle slings, kit)
    scuff = np.clip((band_noise(n, 3, 9, seed + 5) - 0.6) * 4.0, 0, 1) * np.clip((band_noise(n, 10, 30, seed + 6) - 0.35) * 2.5, 0, 1)
    core, halo = _scratches(n, seed + 7, int(30), (4, 30), 120.0, width_px=max(1.0, 1.4 * sc))
    hair, _ = _scratches(n, seed + 8, int(90), (2, 9), 120.0, width_px=max(0.8, 0.9 * sc))
    dust = np.clip((band_noise(n, 4, 14, seed + 3) - 0.45) * 2.0, 0, 1)
    h = 0.30 * peel + 0.55 * grit * (1 - 0.55 * scuff) + 0.08 * fine - 0.35 * core - 0.12 * hair
    rough = 0.86 - 0.10 * grit * scuff - 0.22 * scuff * 0.6 - 0.10 * core + 0.06 * dust + 0.05 * (fine - 0.5)
    tint = (0.95 + 0.06 * (band_noise(n, 2, 7, seed + 2) - 0.5)       # uneven coat
            - 0.07 * (1 - grit) * 0.5                                    # dirt held between the grit
            + 0.10 * grit * scuff                                        # rubbed tops lighter
            + 0.14 * core + 0.05 * hair + 0.01 * halo                    # scratches through to the lighter coat
            + 0.06 * dust)                                               # dried dust
    return {'height': h, 'normal': normal_from_height(h, 5.0 * sc + 1.0), 'rough': np.clip(rough, 0.45, 0.97), 'tint': tint}


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
    """Moulded glass-filled polymer (rails, shroud body, buckles, ear cups): a matte mould texture (spark-eroded
    stipple) with handling wear; tile is 30 mm."""
    st = band_noise(n, 60, 160, seed)                                    # 0.2-0.5 mm mould stipple
    st = np.clip((st - 0.5) * 2.6 + 0.5, 0, 1)
    sw = band_noise(n, 12, 30, seed + 1)                                 # 1-2.5 mm sink and flow marks
    rub = np.clip((band_noise(n, 2, 6, seed + 2) - 0.55) * 3.0, 0, 1)    # worn shiny where handled
    core, _ = _scratches(n, seed + 3, 22, (2, 10), 30.0, width_px=1.0)
    h = 0.75 * st * (1 - 0.5 * rub) + 0.25 * sw - 0.25 * core
    rough = 0.78 - 0.12 * rub - 0.08 * st * rub + 0.06 * (st - 0.5) - 0.1 * core
    return {'normal': normal_from_height(h, 3.2), 'rough': np.clip(rough, 0.4, 0.95),
            'tint': 0.94 + 0.05 * st + 0.02 * rub + 0.12 * core}


def cast_metal(n=512, seed=61):
    """Hard-anodised aluminium (shroud, front plate): bead-blast; tile is 30 mm."""
    g = band_noise(n, 150, n // 2, seed)
    return {'normal': normal_from_height(g, 0.8), 'rough': 0.42 + 0.16 * g, 'tint': 0.96 + 0.04 * g}


def leatherette(n=512, seed=71):
    """Protein-leather ear seals: pebbled grain plus soft creases where the seal folds; tile is 30 mm."""
    cells = band_noise(n, 40, 90, seed)
    peb = (1 - np.abs(cells - 0.5) * 2) ** 3
    crease = band_noise(n, 4, 12, seed + 1, aniso=(1.0, 0.25))
    crease = np.exp(-((crease - 0.5) / 0.035) ** 2)                      # thin creases along the seal
    h = 0.75 * peb - 0.45 * crease + 0.1 * band_noise(n, 8, 20, seed + 2)
    rough = 0.5 + 0.22 * peb + 0.12 * crease
    return {'normal': normal_from_height(h, 3.0), 'rough': np.clip(rough, 0.3, 0.9), 'tint': 0.88 + 0.1 * peb - 0.08 * crease}


def grille(n=256, seed=95):
    """Perforated speaker / ambient-microphone grille: a hex hole pattern; tile is 6 mm."""
    y, x = np.mgrid[0:n, 0:n] / n
    k = 6
    a = np.cos(2 * np.pi * k * x) + np.cos(2 * np.pi * k * (x / 2 + y)) + np.cos(2 * np.pi * k * (x / 2 - y))
    holes = np.clip((a - 1.2) * 1.2, 0, 1)
    h = 1 - holes
    return {'normal': normal_from_height(h, 4.0), 'rough': 0.6 + 0.3 * holes, 'tint': 1.0 - 0.9 * holes}


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
    'polymer': polymer, 'metal': cast_metal, 'leatherette': leatherette, 'foam_ball': foam_ball, 'grille': grille,
}
