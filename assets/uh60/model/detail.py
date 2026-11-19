"""Interior maps painted by code: the instrument faces, and small tiling surfaces (seat fabric, webbing, quilted
soundproofing, non-skid floor). Nothing here comes from a photograph or a downloaded texture.

Instrument atlas (2048 x 2048, 30 px per inch), three flat regions:
    panel     the main instrument panel face, in panel-local inches (BL across, up the face)
    console   top of the lower console (radio control heads)
    overhead  the upper console (switch rows, circuit breakers)
The instrument set and its arrangement follow TM 1-1520-237-10 figure 2-9 (UH-60A): airspeed, vertical situation
indicator, barometric altimeter, radar altimeter, horizontal situation indicator, vertical speed, clock, standby
attitude for each pilot; the central display unit's vertical-scale engine and fuel instruments; the pilot display
units (rotor / torque); the caution-advisory panel. Dial ranges printed on the faces are the manual's (airspeed to
250 kt, rotor and torque in percent); individual tick spacing and the radio control heads' legends are inferred.
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import recipe as RC
import skin

PPI = 30.0
AW = 2048
PANEL = dict(x0=4, y0=4, w=68.0, h=27.0, ymin=-34.0, zmin=-10.0)          # px origin, size in inches
CONSOLE = dict(x0=4, y0=840, w=17.2, h=24.0)
OVER = dict(x0=600, y0=840, w=18.0, h=25.0, sta0=221.5)
WHITE = (226, 226, 214, 255); GREEN = (70, 200, 90, 255); AMBER = (232, 160, 40, 255); RED = (220, 50, 40, 255)
CYAN = (90, 170, 210, 255)


def F(size, bold=True):
    return skin._font(skin.FONT if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', max(5, int(size)))


def dial(d, cx, cy, r, lo, hi, major, minor, a0=-225.0, a1=45.0, label='', value=None, fmt=lambda v: str(int(v)), arcs=(), num_r=0.66, fs=0.2):
    """Round dial: ticks from lo to hi swept clockwise from a0 to a1 degrees (0 = east, screen angles)."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(6, 6, 7, 255))
    ang = lambda v: math.radians(a0 + (a1 - a0) * (v - lo) / (hi - lo))
    for (v0, v1, col) in arcs:
        d.arc([cx - r * 0.95, cy - r * 0.95, cx + r * 0.95, cy + r * 0.95], math.degrees(ang(v0)), math.degrees(ang(v1)), fill=col, width=max(2, int(r * 0.07)))
    v = lo
    while v <= hi + 1e-6:
        a = ang(v); is_major = abs((v - lo) / major - round((v - lo) / major)) < 1e-6
        r0 = r * (0.78 if is_major else 0.86)
        d.line([cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r * 0.93 * math.cos(a), cy + r * 0.93 * math.sin(a)], fill=WHITE, width=2 if is_major else 1)
        if is_major:
            d.text((cx + r * num_r * math.cos(a), cy + r * num_r * math.sin(a)), fmt(v), font=F(r * fs), fill=WHITE, anchor='mm')
        v += minor
    if label:
        d.text((cx, cy + r * 0.34), label, font=F(r * 0.15), fill=WHITE, anchor='mm')
    if value is not None:
        a = ang(value)
        d.line([cx - r * 0.15 * math.cos(a), cy - r * 0.15 * math.sin(a), cx + r * 0.74 * math.cos(a), cy + r * 0.74 * math.sin(a)], fill=WHITE, width=max(2, int(r * 0.07)))
        d.ellipse([cx - r * 0.09, cy - r * 0.09, cx + r * 0.09, cy + r * 0.09], fill=(40, 40, 42, 255))


def attitude(im, cx, cy, r, pitch=2.0, roll=-3.0):
    """Vertical situation indicator: sky / ground sphere with a pitch ladder, bank scale, fixed aircraft symbol."""
    s = int(r * 2); t = Image.new('RGBA', (s * 2, s * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(t); c = s
    k = r / 28.0                                                    # pixels per degree of pitch
    d.rectangle([0, 0, s * 2, c + pitch * k], fill=(52, 96, 150, 255)); d.rectangle([0, c + pitch * k, s * 2, s * 2], fill=(84, 60, 38, 255))
    d.line([0, c + pitch * k, s * 2, c + pitch * k], fill=WHITE, width=2)
    for p in range(-30, 31, 5):
        if p == 0: continue
        w = r * (0.34 if p % 10 == 0 else 0.17); y = c + (pitch - p) * k
        d.line([c - w, y, c + w, y], fill=WHITE, width=1)
        if p % 10 == 0: d.text((c + w + r * 0.12, y), str(abs(p)), font=F(r * 0.14), fill=WHITE, anchor='mm')
    t = t.rotate(roll, resample=Image.BICUBIC)
    mask = Image.new('L', t.size, 0); ImageDraw.Draw(mask).ellipse([c - r * 0.8, c - r * 0.8, c + r * 0.8, c + r * 0.8], fill=255)
    d0 = ImageDraw.Draw(im); d0.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(6, 6, 7, 255))
    im.paste(t, (int(cx - c), int(cy - c)), mask)
    for a in (-60, -30, -20, -10, 0, 10, 20, 30, 60):
        q = math.radians(a - 90); r0 = r * (0.8 if a % 30 else 0.78)
        d0.line([cx + r0 * math.cos(q), cy + r0 * math.sin(q), cx + r * 0.93 * math.cos(q), cy + r * 0.93 * math.sin(q)], fill=WHITE, width=2)
    d0.line([cx - r * 0.5, cy, cx - r * 0.16, cy], fill=AMBER, width=3); d0.line([cx + r * 0.16, cy, cx + r * 0.5, cy], fill=AMBER, width=3)
    d0.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=AMBER)
    d0.rectangle([cx - r * 0.3, cy + r * 0.84, cx + r * 0.3, cy + r * 0.95], fill=(12, 12, 12, 255)); d0.ellipse([cx - 4, cy + r * 0.85, cx + 4, cy + r * 0.94], fill=WHITE)


def hsi(d, cx, cy, r, hdg=318.0):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(6, 6, 7, 255))
    for a in range(0, 360, 5):
        q = math.radians(a - hdg - 90); r0 = r * (0.74 if a % 30 == 0 else 0.80 if a % 10 == 0 else 0.84)
        d.line([cx + r0 * math.cos(q), cy + r0 * math.sin(q), cx + r * 0.9 * math.cos(q), cy + r * 0.9 * math.sin(q)], fill=WHITE, width=1)
        if a % 30 == 0:
            s = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}.get(a, str(a // 10))
            d.text((cx + r * 0.62 * math.cos(q), cy + r * 0.62 * math.sin(q)), s, font=F(r * 0.17), fill=WHITE, anchor='mm')
    d.polygon([(cx, cy - r * 0.98), (cx - r * 0.06, cy - r * 0.86), (cx + r * 0.06, cy - r * 0.86)], fill=WHITE)
    q = math.radians(25 - 90)                                       # course pointer with deviation bar
    for sgn, col in ((1, AMBER), (-1, AMBER)):
        d.line([cx + sgn * r * 0.3 * math.cos(q), cy + sgn * r * 0.3 * math.sin(q), cx + sgn * r * 0.55 * math.cos(q), cy + sgn * r * 0.55 * math.sin(q)], fill=col, width=3)
    d.line([cx - r * 0.26 * math.cos(q) + 5, cy - r * 0.26 * math.sin(q), cx + r * 0.26 * math.cos(q) + 5, cy + r * 0.26 * math.sin(q)], fill=AMBER, width=3)
    d.line([cx - r * 0.2, cy, cx + r * 0.2, cy], fill=WHITE, width=2); d.line([cx, cy - r * 0.16, cx, cy + r * 0.22], fill=WHITE, width=2)


def strip(d, x, y0, y1, w, frac, bands, label, rng=None):
    """Vertical-scale instrument: a column of lit segments up to `frac`, coloured by band, with its legend."""
    d.rectangle([x - w / 2 - 3, y0 - 3, x + w / 2 + 3, y1 + 3], fill=(4, 4, 5, 255))
    n = int((y1 - y0) / 4)
    for i in range(n):
        f = i / (n - 1); yy = y1 - (y1 - y0) * f
        col = next((c for (a, b, c) in bands if a <= f <= b), GREEN)
        lit = f <= frac
        d.rectangle([x - w / 2, yy - 1, x + w / 2, yy + 1], fill=col if lit else tuple(int(v * 0.16) for v in col[:3]) + (255,))
    for f in (0, 0.25, 0.5, 0.75, 1.0):
        yy = y1 - (y1 - y0) * f; d.line([x + w / 2 + 1, yy, x + w / 2 + 4, yy], fill=WHITE, width=1)
    d.text((x, y1 + 12), label, font=F(8.5), fill=WHITE, anchor='mm')


def panel_px(y, z):
    """Panel-local inches (y = BL, +left; z up the face) -> atlas pixel, as the crew see it (their left = +BL)."""
    return PANEL['x0'] + (PANEL['ymin'] + PANEL['w'] - y) * PPI, PANEL['y0'] + (PANEL['zmin'] + PANEL['h'] - z) * PPI


def build_instruments(out_dir, log=print):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'instruments.png')
    if os.path.exists(path) and os.path.getmtime(path) > os.path.getmtime(__file__):
        return path
    im = Image.new('RGBA', (AW, AW), (5, 5, 6, 255)); d = ImageDraw.Draw(im)
    for sg in (1, -1):
        cy = sg * 21.0
        for (dy, z, r), kind in zip(RC.FLIGHT_GAUGES, ('ias', 'vsi', 'alt', 'ralt', 'hsi', 'vs', 'clock', 'stby')):
            x, y = panel_px(cy + dy, z); R = (r - 0.22) * PPI
            if kind == 'ias':
                dial(d, x, y, R, 0, 250, 50, 10, a0=-250, a1=70, label='KNOTS', value=0, arcs=((193, 250, RED),))
            elif kind == 'vsi': attitude(im, x, y, R); d = ImageDraw.Draw(im)
            elif kind == 'alt':
                dial(d, x, y, R, 0, 10, 1, 0.2, a0=-90, a1=270, label='ALT', value=3.4, fmt=lambda v: str(int(v) % 10))
                d.rectangle([x + R * 0.2, y - R * 0.12, x + R * 0.7, y + R * 0.12], fill=(14, 14, 14, 255)); d.text((x + R * 0.45, y), '29.92', font=F(R * 0.14), fill=WHITE, anchor='mm')
            elif kind == 'ralt':
                dial(d, x, y, R, 0, 15, 5, 1, a0=-250, a1=40, label='FEET x100', value=0, fmt=lambda v: str(int(v)))
            elif kind == 'hsi': hsi(d, x, y, R)
            elif kind == 'vs':
                dial(d, x, y, R, -4, 4, 1, 0.5, a0=-345, a1=-15, label='VERT SPEED', value=0, fmt=lambda v: str(abs(int(v))), num_r=0.6)
            elif kind == 'clock':
                dial(d, x, y, R, 0, 12, 1, 0.2, a0=-90, a1=270, value=10.15, fmt=lambda v: '' if v == 0 else str(int(v)), fs=0.26)
            else: attitude(im, x, y, R, 0.0, 0.0); d = ImageDraw.Draw(im)
        for dy, name in ((-7.5, 'CIS MODE SEL'), (-4.5, 'VSI/HSI MODE')):
            x, y = panel_px(cy + dy * sg, 1.3)
            for i, t in enumerate(('HDG', 'NAV', 'ALT', 'DPLR', 'VOR', 'ILS')):
                bx = x - 28 + (i % 3) * 28; by = y - 11 + (i // 3) * 22
                d.rectangle([bx - 11, by - 8, bx + 11, by + 8], fill=(22, 22, 24, 255), outline=(60, 60, 60, 255)); d.text((bx, by), t, font=F(7.5), fill=GREEN if i in (0, 4) else (90, 90, 80, 255), anchor='mm')
    # caution / advisory panel
    x0, y0 = panel_px(6.75, 14.7); x1, y1 = panel_px(-6.75, 10.5)
    legends = ('#1 FUEL LOW', '#1 GEN', '#2 GEN', '#2 FUEL LOW', '#1 FUEL PRESS', '#1 GEN BRG', '#2 GEN BRG', '#2 FUEL PRESS', '#1 ENGINE OIL PRESS', '#1 CONV', '#2 CONV', '#2 ENGINE OIL PRESS',
               '#1 ENGINE OIL TEMP', 'AC ESS BUS OFF', 'DC ESS BUS OFF', '#2 ENGINE OIL TEMP', 'CHIP #1 ENGINE', 'BATT LOW CHARGE', 'BATTERY FAULT', 'CHIP #2 ENGINE',
               '#1 FUEL FLTR BYPASS', 'GUST LOCK', 'PITCH BIAS FAIL', '#2 FUEL FLTR BYPASS', '#1 ENGINE STARTER', '#1 OIL FLTR BYPASS', '#2 OIL FLTR BYPASS', '#2 ENGINE STARTER',
               '#1 PRI SERVO PRESS', '#1 HYD PUMP', '#2 HYD PUMP', '#2 PRI SERVO PRESS', 'TAIL ROTOR QUADRANT', 'IRCM INOP', 'AUX FUEL', '#1 TAIL RTR SERVO',
               'MAIN XMSN OIL TEMP', 'INT XMSN OIL TEMP', 'TAIL XMSN OIL TEMP', 'APU OIL TEMP HI', 'BOOST SERVO OFF', 'STABILATOR', 'SAS OFF', 'TRIM FAIL',
               'LFT PITOT HEAT', 'FLT PATH STAB', 'IFF', 'RT PITOT HEAT', 'CHIP INPUT MDL-LH', 'CHIP INT XMSN', 'CHIP TAIL XMSN', 'CHIP INPUT MDL-RH')
    cols, rows = 4, 13; cw = (x1 - x0) / cols; ch = (y1 - y0) / rows
    lit = {'#1 GEN': AMBER, '#2 GEN': AMBER, '#1 HYD PUMP': AMBER, '#2 HYD PUMP': AMBER, 'SAS OFF': AMBER, 'GUST LOCK': AMBER, 'BATT LOW CHARGE': AMBER}
    for i, t in enumerate(legends):
        bx = x0 + (i % cols) * cw; by = y0 + (i // cols) * ch
        on = lit.get(t)
        d.rectangle([bx + 1, by + 1, bx + cw - 1, by + ch - 1], fill=(70, 46, 10, 255) if on else (14, 13, 11, 255), outline=(40, 40, 40, 255))
        d.text((bx + cw / 2, by + ch / 2), t, font=F(5.6, False), fill=on or (70, 60, 40, 255), anchor='mm')
    # central display unit: vertical-scale engine and fuel instruments (figure 2-9)
    names = ('FUEL\n1', 'FUEL\n2', 'XMSN\nTEMP', 'XMSN\nPRESS', 'OIL T\n1', 'OIL T\n2', 'OIL P\n1', 'OIL P\n2', 'TGT\n1', 'TGT\n2', 'Ng\n1', 'Ng\n2', 'AMPS')
    fracs = (0.62, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    bands = ((0, 0.12, AMBER), (0.12, 0.78, GREEN), (0.78, 0.9, AMBER), (0.9, 1.0, RED))
    for i in range(13):
        x, yt = panel_px(6.0 - i * 1.0, 9.1); _, yb = panel_px(0, 3.4)
        strip(d, x, yt, yb, 9, fracs[i], bands, names[i].split('\n')[0])
        d.text((x, yb + 22), names[i].split('\n')[1] if '\n' in names[i] else '', font=F(8), fill=WHITE, anchor='mm')
    for dyc in (-11.2, 11.2):                                      # pilot display units: % RPM R, 1, 2 and % TRQ 1, 2
        for j, (nm, bd) in enumerate((('R', ((0, 0.86, AMBER), (0.86, 0.93, GREEN), (0.93, 1, RED))), ('1', bands), ('2', bands), ('T1', bands), ('T2', bands))):
            x, yt = panel_px(dyc + 1.0 - j * 0.5, 11.4); _, yb = panel_px(0, 6.9)
            strip(d, x, yt, yb, 6, 0.0, bd, nm)
        x, y = panel_px(dyc, 11.75); d.text((x, y), '% RPM      % TRQ', font=F(7.5), fill=WHITE, anchor='mm')
    for dyc, t, col in ((-11.2, 'MASTER CAUTION', AMBER), (11.2, 'MASTER CAUTION', AMBER)):
        x, y = panel_px(dyc, 14.4); d.text((x, y), t, font=F(8), fill=(60, 40, 10, 255), anchor='mm')
    # ---- lower console: radio control heads
    cx0, cy0 = CONSOLE['x0'], CONSOLE['y0']
    heads = ('VHF-FM  30.00', 'UHF-AM  243.000', 'VOR/ILS  108.10', 'IFF  1200', 'ADF  0190', 'DOPPLER / GPS', 'KY-58', 'STAB / AFCS')
    heights = (2.6, 2.2, 3.4, 2.2, 2.6, 3.0, 2.2, 2.6); xin = 0.6
    for hgt, name in zip(heights, heads * 2):
        for yc in (-4.1, 4.1):
            px0 = cx0 + (8.6 - yc - 2.9) * PPI; py0 = cy0 + xin * PPI
            d.rectangle([px0, py0 + 3, px0 + 5.75 * PPI, py0 + (hgt - 0.25) * PPI], fill=(20, 21, 22, 255), outline=(70, 70, 70, 255))
            # display window sits at yc + 1.2 (interior.py), legend along the top edge
            wx = cx0 + (8.6 - (yc + 1.2)) * PPI; wy = py0 + hgt * PPI / 2
            d.rectangle([wx - 34, wy - min(13, hgt * 5), wx + 34, wy + min(13, hgt * 5)], fill=(8, 10, 8, 255), outline=(90, 90, 90, 255))
            d.text((wx, wy), name.split('  ')[-1], font=F(13), fill=(240, 120, 30, 255), anchor='mm')
            d.text((px0 + 5, py0 + 6), name.split('  ')[0], font=F(7), fill=WHITE, anchor='la')
        xin += hgt
    # ---- overhead console: switch rows with their legends
    ox0, oy0 = OVER['x0'], OVER['y0']
    d.rectangle([ox0, oy0, ox0 + OVER['w'] * PPI, oy0 + OVER['h'] * PPI], fill=(18, 19, 20, 255))
    rowsn = (('BATT', 'GEN 1', 'GEN 2', 'APU GEN', 'EXT PWR'), ('FUEL BOOST 1', 'FUEL BOOST 2', 'PRIME', 'XFEED', 'APU'), ('PITOT HT', 'WSHLD', 'ENG ANTI-ICE 1', 'ENG ANTI-ICE 2', 'DE-ICE'),
             ('POS LTS', 'ANTI COLL', 'FORM LTS', 'CARGO HOOK', 'WIPER'), ('INSTR LTS', 'CONSOLE LTS', 'DOME', 'HTR', 'VENT'), ('STAB AUTO', 'SAS 1', 'SAS 2', 'TRIM', 'FPS'))
    for i, sx in enumerate(np.linspace(226.0, 243.0, 6)):
        for jc, yc in enumerate((-4.4, 4.4)):
            for k in range(5):
                bl = yc - 2.8 + k * 1.4
                x = ox0 + (9.0 - bl) * PPI; y = oy0 + (sx - OVER['sta0']) * PPI
                d.text((x, y - 24), rowsn[(i + jc) % 6][k], font=F(5.6, False), fill=WHITE, anchor='mm')
                d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(120, 120, 120, 255), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.4))
    im.convert('RGB').save(path)
    log('instrument atlas', round(os.path.getsize(path) / 1e6, 2), 'MB')
    return path


# ------------------------------------------------------------------ tiling surfaces
def _tile_noise(n, cell, seed):
    rng = np.random.default_rng(seed); g = rng.random((n // cell, n // cell)).astype(np.float32)
    g = np.pad(g, 2, mode='wrap')
    a = np.asarray(Image.fromarray(g).resize(((n // cell + 4) * cell, (n // cell + 4) * cell), Image.BICUBIC))
    return a[2 * cell:2 * cell + n, 2 * cell:2 * cell + n]


def _normal(h, k):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -gx * k, gy * k, np.ones_like(h); ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5


def build_tiles(out_dir, log=print):
    """name -> (colour path, normal path, tile size in inches)."""
    os.makedirs(out_dir, exist_ok=True); n = 512; out = {}
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    specs = {}
    # plain-weave nylon duck: 64 threads across a 4 in tile
    wv = np.sin(xx * 2 * np.pi * 64 / n) * np.where(np.sin(yy * 2 * np.pi * 32 / n) > 0, 1, -1) * 0.5 + np.sin(yy * 2 * np.pi * 64 / n) * 0.5
    specs['fabric_seat'] = (wv * 0.5 + 0.25 * (_tile_noise(n, 64, 1) - 0.5), (0.230, 0.250, 0.190), 0.10, 2.2, 4.0)
    # webbing: herringbone ribs, 2 in tile
    rib = np.sin((xx + np.abs(((yy * 8 / n) % 2) - 1) * 24) * 2 * np.pi * 40 / n)
    specs['fabric_belt'] = (rib * 0.6, (0.300, 0.300, 0.270), 0.09, 2.4, 2.0)
    # quilted soundproofing blanket: 4 in diamonds, stitched, puffed between the stitches (8 in tile)
    u = (xx + yy) / n * 2; v = (xx - yy) / n * 2
    du = np.abs((u % 1) - 0.5); dv = np.abs((v % 1) - 0.5)
    puff = np.sqrt(np.clip(du * dv * 4, 0, 1)); stitch = np.minimum(du, dv) < 0.012
    dash = (np.sin((xx + yy) * 2 * np.pi * 24 / n) > -0.2) | (np.sin((xx - yy) * 2 * np.pi * 24 / n) > -0.2)
    hq = puff * 1.0 - 0.25 * (stitch & dash) + 0.05 * np.sin(xx * 2 * np.pi * 128 / n) * np.sin(yy * 2 * np.pi * 128 / n)
    specs['quilt'] = (hq * 3.0 + 0.3 * (_tile_noise(n, 32, 2) - 0.5), (0.250, 0.265, 0.220), 0.07, 3.0, 8.0)
    # non-skid floor coating: sharp grit in paint, scuffed (12 in tile)
    grit = (np.random.default_rng(3).random((n, n)).astype(np.float32) > 0.86).astype(np.float32)
    grit = skin.blur(np.pad(grit, 4, mode='wrap'), 0.8)[4:-4, 4:-4]
    specs['floor'] = (grit * 1.6 + 0.4 * (_tile_noise(n, 64, 4) - 0.5), (0.090, 0.095, 0.090), 0.22, 2.6, 12.0)
    for name, (h, base, cvar, k, tile) in specs.items():
        c = np.array(base, np.float32)[None, None, :] * (1 + cvar * (h - h.mean()) / (h.std() + 1e-6) * 0.5)[..., None]
        c *= (0.9 + 0.2 * _tile_noise(n, 128, sum(map(ord, name)) % 97))[..., None]
        pc = os.path.join(out_dir, f'{name}_color.jpg'); pn = os.path.join(out_dir, f'{name}_normal.png')
        Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(pc, quality=92)
        Image.fromarray((_normal(h, k) * 255).astype(np.uint8)).save(pn)
        out[name] = (pc, pn, tile)
    return out


# ------------------------------------------------------------------ Blender side
def materials(ctx, out_dir, log=print):
    """Replace the plain interior materials with textured ones of the same name; record which ones want box UVs."""
    import bpy
    tiles = build_tiles(out_dir, log); ctx.box_uv = {}

    def tex(nt, path, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path); t.image.colorspace_settings.name = cs; return t
    for name, (pc, pn, tile) in tiles.items():
        m = ctx.mats[name]; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
        nt.links.new(tex(nt, pc, 'sRGB').outputs['Color'], b.inputs['Base Color'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex(nt, pn, 'Non-Color').outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
        ctx.box_uv[name] = tile
    m = ctx.mats['instrument']; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    t = tex(nt, build_instruments(out_dir, log), 'sRGB')
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    em = 'Emission Color' if 'Emission Color' in b.inputs else 'Emission'
    nt.links.new(t.outputs['Color'], b.inputs[em]); b.inputs['Emission Strength'].default_value = 0.55
    b.inputs['Roughness'].default_value = 0.25


def box_uv(o, tile_in):
    """Tile a small surface by projecting each face along its dominant axis; one tile every `tile_in` inches."""
    from lib import IN
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    nv = len(me.vertices); co = np.zeros(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3) / (tile_in * IN)
    npoly = len(me.polygons); nrm = np.zeros(npoly * 3); me.polygons.foreach_get('normal', nrm); nrm = np.abs(nrm.reshape(-1, 3))
    lt = np.zeros(npoly, np.int32); me.polygons.foreach_get('loop_total', lt)
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    ax = np.argmax(nrm, 1)[np.repeat(np.arange(npoly), lt)]; p = co[lv]
    u = np.where(ax == 0, p[:, 1], p[:, 0]); v = np.where(ax == 2, p[:, 1], p[:, 2])
    me.uv_layers[0].data.foreach_set('uv', np.stack([u, v], 1).ravel())


def instrument_uv(o, Mp, Mc):
    """UVs for the instrument faces: each face goes to the atlas region of the surface it lies on."""
    from lib import IN
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    nv = len(me.vertices); co = np.zeros(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    a = np.stack([co[:, 1] / IN + RC.STA_MAST, co[:, 0] / IN, co[:, 2] / IN + RC.WL_GROUND, np.ones(nv)], 1)
    pl = a @ np.linalg.inv(Mp).T; cl = a @ np.linalg.inv(Mc).T
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    on_panel = np.abs(pl[:, 0]) < 1.2; over = a[:, 2] > 258.0
    x = np.where(on_panel, PANEL['x0'] + (PANEL['ymin'] + PANEL['w'] - pl[:, 1]) * PPI,
                 np.where(over, OVER['x0'] + (9.0 - a[:, 1]) * PPI, CONSOLE['x0'] + (8.6 - cl[:, 1]) * PPI))
    y = np.where(on_panel, PANEL['y0'] + (PANEL['zmin'] + PANEL['h'] - pl[:, 2]) * PPI,
                 np.where(over, OVER['y0'] + (a[:, 0] - OVER['sta0']) * PPI, CONSOLE['y0'] + cl[:, 0] * PPI))
    me.uv_layers[0].data.foreach_set('uv', np.stack([x / AW, 1 - y / AW], 1)[lv].ravel())
