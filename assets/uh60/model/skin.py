"""Exterior skin maps, painted by code from the recipe: no photograph, scan or downloaded texture is used.

One 4096 x 4096 atlas holds four orthographic projections of the airframe in aircraft coordinates:
    left side (STA x WL), right side (STA x WL), top (STA x BL), bottom (STA x BL)
so every mark below is placed in station / water line / butt line inches, the same frame as the manual's diagram.

What is drawn, and where it comes from:
  frame seams at the stations lettered on figure 6-1 (162, 204, 247, 270, 315.5, 343, 370.5, 398, 443.5, 485, 644.6) [F6-1]
  intermediate frames, stringer lines, access panels, cowl splits, fastener pitch                               [INF]
  rivet rows on every seam, screw rings on removable panels, doublers round the door and window cut-outs        [INF]
  markings: UNITED STATES ARMY on the tailcone, serial on the pylon (fictional number), NO STEP, rescue arrows,
            tail rotor warning arrow, fuel and grounding stencils (wording per the type's usual markings)       [PUB]/[INF]
  weathering: sun fade, grime that gathers in seams and runs down from them (each run has its own length and
              weight, nothing repeats), exhaust soot aft of the ejectors, boot wear on the walkways, paint
              chipped to bare metal at door edges, steps and latches                                            [INF]
Outputs (work/tex/, git-ignored): skin_color.jpg, skin_normal.png, skin_orm.png (occlusion, roughness, metallic).
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import recipe as RC

W = 4096
STA0, STA1 = 160.0, 776.0
WLA, WLB = 188.0, 372.0
BLH = 88.0
H_SIDE, H_TOP = 1104, 944
KX = W / (STA1 - STA0)
KZ = H_SIDE / (WLB - WLA)
KB = H_TOP / (2 * BLH)
ROW = {'L': 0, 'R': H_SIDE, 'T': 2 * H_SIDE, 'B': 2 * H_SIDE + H_TOP}
FRAMES_TM = [204.0, 247.0, 270.0, 315.5, 343.0, 370.5, 398.0, 443.5, 485.0, 644.6]           # [F6-1]
FRAMES_INF = [176.0, 188.0, 225.0, 292.0, 420.0, 464.0, 505.0, 525.0, 545.0, 565.0, 585.0, 605.0, 625.0]   # [INF]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_C = '/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf'


def _font(path, size):
    for p in (path, FONT, '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def px(region, sta, v):
    """Atlas pixel of a point: v is WL for the side regions and BL (+left) for top / bottom."""
    x = (sta - STA0) * KX
    if region in 'LR':
        return x, ROW[region] + (WLB - v) * KZ
    return x, ROW[region] + (BLH - v) * KB if region == 'T' else ROW[region] + (BLH + v) * KB


def uv(region, sta, v):
    x, y = px(region, sta, v)
    return x / W, 1.0 - y / W


def noise(shape, cell, seed, octaves=4):
    """Fractal value noise 0..1 (bicubic-upsampled random grids)."""
    rng = np.random.default_rng(seed); out = np.zeros(shape, np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        c = max(2, int(cell / 2 ** o))
        g = rng.random((shape[0] // c + 3, shape[1] // c + 3)).astype(np.float32)
        im = Image.fromarray(g).resize(((shape[1] // c + 3) * c, (shape[0] // c + 3) * c), Image.BICUBIC)
        out += amp * np.asarray(im)[c:c + shape[0], c:c + shape[1]]; tot += amp; amp *= 0.5
    return np.clip(out / tot, 0, 1)


def blur(a, r):
    """Gaussian blur of a float image (sigma r pixels); wide blurs run at reduced size."""
    a = np.asarray(a, np.float32)
    if r > 3.0:
        f = int(r / 1.5); h, w = a.shape
        sm = np.asarray(Image.fromarray(a).resize((max(2, w // f), max(2, h // f)), Image.BOX))
        return np.asarray(Image.fromarray(blur(sm, r / f)).resize((w, h), Image.BICUBIC))
    k = int(math.ceil(r * 3)); x = np.arange(-k, k + 1); g = np.exp(-x * x / (2 * r * r)); g /= g.sum()
    for ax in (0, 1):
        p = np.pad(a, [(k, k) if i == ax else (0, 0) for i in (0, 1)], mode='edge'); out = np.zeros_like(a)
        for i, wgt in enumerate(g):
            out += wgt * (p[i:i + a.shape[0], :] if ax == 0 else p[:, i:i + a.shape[1]])
        a = out
    return a


class Painter:
    def __init__(self):
        self.groove = Image.new('L', (W, W), 0); self.dg = ImageDraw.Draw(self.groove)      # panel gaps
        self.rivet = Image.new('L', (W, W), 0); self.dr = ImageDraw.Draw(self.rivet)        # flush rivet dimples
        self.screw = Image.new('L', (W, W), 0); self.ds = ImageDraw.Draw(self.screw)        # raised screw heads
        self.plate = Image.new('L', (W, W), 0); self.dp = ImageDraw.Draw(self.plate)        # doublers (raised)
        self.ink = Image.new('RGBA', (W, W), (0, 0, 0, 0)); self.di = ImageDraw.Draw(self.ink)   # markings
        self.dark = Image.new('L', (W, W), 0); self.dd = ImageDraw.Draw(self.dark)          # non-skid, soot seeds
        self.chip = Image.new('L', (W, W), 0); self.dc = ImageDraw.Draw(self.chip)          # where paint wears through
        self.drip = Image.new('L', (W, W), 0); self.dq = ImageDraw.Draw(self.drip)          # where runs start
        self.rng = np.random.default_rng(60)
        self.rivets = []; self.screws = []          # (region, sta, v): hardware.py stands real heads on these at LOD0

    # ---- primitives, all in aircraft inches
    def seam(self, region, pts, rivets=True, pitch=1.25, off=0.7, width=2, drip=True):
        p = [px(region, s, v) for s, v in pts]
        self.dg.line(p, fill=255, width=width)
        if drip and region in 'LR':
            self.dq.line(p, fill=90, width=1)
        if rivets:
            for a, b in zip(pts[:-1], pts[1:]):
                a = np.array(a, float); b = np.array(b, float); L = np.linalg.norm(b - a)
                if L < 1e-6: continue
                t = (b - a) / L; n = np.array((-t[1], t[0]))
                for sgn in (1, -1):
                    for d in np.arange(pitch * 0.5, L, pitch):
                        q = a + t * d + n * off * sgn
                        x, y = px(region, q[0], q[1]); self.dr.ellipse([x - 1.3, y - 1.3, x + 1.3, y + 1.3], fill=255)
                        self.rivets.append((region, q[0], q[1]))

    def panel(self, region, s0, v0, s1, v1, r=1.5, screws=True, pitch=2.2, chip=0.5):
        """Removable access panel: gap all round, screw ring just inside, a little chipping at the edge."""
        x0, y0 = px(region, s0, v0); x1, y1 = px(region, s1, v1)
        box = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]; rr = r * KX
        self.dg.rounded_rectangle(box, rr, outline=255, width=2)
        if region in 'LR': self.dq.line([(box[0] + rr, box[3]), (box[2] - rr, box[3])], fill=140, width=1)
        if chip: self.dc.rounded_rectangle(box, rr, outline=int(255 * chip), width=3)
        if screws:
            ins = 0.75
            for (a, b) in (((s0 + ins, v0 + ins), (s1 - ins, v0 + ins)), ((s1 - ins, v0 + ins), (s1 - ins, v1 - ins)),
                           ((s1 - ins, v1 - ins), (s0 + ins, v1 - ins)), ((s0 + ins, v1 - ins), (s0 + ins, v0 + ins))):
                a = np.array(a); b = np.array(b); L = np.linalg.norm(b - a); n = max(2, int(round(L / pitch)))
                for i in range(n):
                    q = a + (b - a) * (i + 0.5) / n; x, y = px(region, q[0], q[1])
                    self.ds.ellipse([x - 1.8, y - 1.8, x + 1.8, y + 1.8], fill=255)
                    self.screws.append((region, q[0], q[1]))

    def doubler(self, region, poly, grow=2.2):
        from shapely.geometry import Polygon
        ring = Polygon(poly).buffer(grow, quad_segs=5)
        pts = [px(region, s, v) for s, v in ring.exterior.coords]
        self.dp.polygon(pts, fill=255)
        inner = np.array(Polygon(poly).buffer(grow - 0.7, quad_segs=5).exterior.coords)
        self.seam(region, [tuple(q) for q in inner], pitch=1.1, off=0.0, width=0, drip=False)
        self.dc.line(pts, fill=60, width=2)

    def text(self, region, sta, v, s, h, col=(8, 8, 8, 235), font=FONT_C, anchor='mm', angle=0.0):
        f = _font(font, max(6, int(h * KZ * 1.38)))
        tmp = Image.new('RGBA', (int(f.getlength(s)) + 8, int(h * KZ * 2.2) + 8), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((tmp.width // 2, tmp.height // 2), s, font=f, fill=col, anchor='mm')
        if region == 'R': tmp = tmp.transpose(Image.FLIP_LEFT_RIGHT)
        if region == 'B': tmp = tmp.transpose(Image.FLIP_TOP_BOTTOM)
        if angle: tmp = tmp.rotate(angle if region != 'R' else -angle, expand=True, resample=Image.BICUBIC)
        x, y = px(region, sta, v)
        self.ink.alpha_composite(tmp, (int(x - tmp.width / 2), int(y - tmp.height / 2)))

    def arrow(self, region, s0, v, s1, h, col):
        """Solid arrow from s0 to s1 (head at s1), height h."""
        d = 1 if s1 > s0 else -1; hd = h * 1.1
        pts = [(s0, v - h * 0.28), (s1 - d * hd, v - h * 0.28), (s1 - d * hd, v - h * 0.5), (s1, v), (s1 - d * hd, v + h * 0.5),
               (s1 - d * hd, v + h * 0.28), (s0, v + h * 0.28)]
        self.di.polygon([px(region, a, b) for a, b in pts], fill=col)


def body_lines(s):
    zb, zt, hw = (float(x) for x in RC.body_params(min(max(s, 162.5), 644.9))[:3])
    return zb, zt, hw


def paint():
    P = Painter()
    frames = sorted(FRAMES_TM + FRAMES_INF)
    for reg in 'LR':
        # ---- frames and stringers of the body (nose to fold hinge)
        for s in frames:
            zb, zt, _ = body_lines(s)
            P.seam(reg, [(s, zb - 1), (s, zt + 1)], pitch=1.25, off=0.75)
        for t in (0.13, 0.36, 0.62, 0.86):
            pts = []
            for s in np.arange(166.0, 645.0, 6.0):
                zb, zt, _ = body_lines(s); pts.append((s, zb + (zt - zb) * t))
            P.seam(reg, pts, pitch=1.5, off=0.0, width=1 if t in (0.36, 0.62) else 2)
        # ---- nose avionics bay door (hinged at the top), battery / external power, landing light bay
        P.panel(reg, 168.0, 209.5, 201.5, 236.0, r=3.0, pitch=2.6)
        P.panel(reg, 178.0, 203.8, 190.0, 208.0, r=1.0)
        # ---- kick-in steps and hand holds up the side to the engine deck [F2-1 shows the step pattern]
        for (s, wl) in ((252.0, 211.0), (254.0, 228.0), (256.0, 248.0), (404.0, 214.0), (404.0, 232.0), (404.0, 250.0)):
            x0, y0 = px(reg, s - 3.2, wl + 2.0); x1, y1 = px(reg, s + 3.2, wl - 2.0)
            P.dp.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], 5, fill=255)
            P.dd.rounded_rectangle([x0, y0, x1, y1], 6, fill=235)
            P.dc.rounded_rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], 5, outline=230, width=4)
            P.dq.line([(x0, y1 + 3), (x1, y1 + 3)], fill=255, width=2)
        # ---- cut-out doublers
        for spec in (RC.GUNNER_WIN, RC.CHIN_WIN):
            P.doubler(reg, spec['poly'])
        P.doubler(reg, RC.CABIN_DOOR['poly'], 2.6); P.doubler(reg, RC.COCKPIT_DOOR['poly'], 2.0)
        # ---- fuel: gravity filler and closed-circuit port (left side on the aircraft), cabin-side access panels
        if reg == 'L':
            for s, wl, r in ((424.0, 246.0, 2.6), (432.0, 238.0, 1.8)):
                x, y = px(reg, s, wl); P.dg.ellipse([x - r * KX, y - r * KZ, x + r * KX, y + r * KZ], outline=255, width=2)
                P.di.ellipse([x - (r + 1.4) * KX, y - (r + 1.4) * KZ, x + (r + 1.4) * KX, y + (r + 1.4) * KZ], outline=(150, 28, 20, 210), width=2)
                P.dq.ellipse([x - 4, y, x + 4, y + 8], fill=255)
            P.text(reg, 424.0, 251.5, 'JP-4  JP-5  JP-8', 0.9); P.text(reg, 424.0, 240.6, 'GRAVITY FILL 181 GAL', 0.75)
        P.panel(reg, 408.0, 208.0, 438.0, 226.0, r=2.0, pitch=2.4)       # fuel cell / aft avionics access
        P.panel(reg, 450.0, 214.0, 478.0, 236.0, r=2.0, pitch=2.4)
        P.panel(reg, 500.0, 222.0, 520.0, 236.0, r=1.5)
        P.panel(reg, 600.0, 232.0, 622.0, 243.0, r=1.5)                  # tail landing gear / IGB access
        # ---- engine cowls: split lines, latches (drawn as short screws rows), nacelle door outline
        P.panel(reg, 352.0, 268.5, 412.0, 290.5, r=4.0, pitch=3.5, chip=0.8)
        P.seam(reg, [(382.0, 268.5), (382.0, 290.5)], pitch=1.6)
        P.panel(reg, 416.0, 268.0, 441.0, 289.0, r=3.0, pitch=3.0)
        for s in (360.0, 374.0, 390.0, 404.0):                            # cowl latches along the lower edge
            x, y = px(reg, s, 268.5); P.dp.rectangle([x - 6, y - 7, x + 6, y + 3], fill=255); P.dc.rectangle([x - 7, y - 8, x + 7, y + 4], outline=255, width=2)
            P.dq.line([(x - 5, y + 4), (x + 5, y + 4)], fill=255, width=2)
        # ---- transmission / APU / oil cooler deck above the cabin: service panels
        P.panel(reg, 300.0, 271.0, 334.0, 286.0, r=2.5, pitch=2.6)
        P.panel(reg, 446.0, 262.0, 486.0, 276.0, r=2.5, pitch=2.6)
        # ---- tail rotor drive shaft cover segments
        for s in np.arange(500.0, 646.0, 29.0):
            P.seam(reg, [(s, 244.0), (s, 262.0)], pitch=1.4, drip=False)
        # ---- tail pylon: leading edge strip, ribs square to the spar, gearbox fairing joint
        pyl = np.array(RC.PYLON)
        zs = np.linspace(pyl[0, 0] + 2, pyl[-1, 0] - 2, 9)
        for z in zs:
            le = float(np.interp(z, pyl[:, 0], pyl[:, 1])); te = float(np.interp(z, pyl[:, 0], pyl[:, 2]))
            P.seam(reg, [(le + 1.5, z), (te - 1.0, z)], pitch=1.4, off=0.0, width=1)
        for f in (0.12, 0.42, 0.72):
            pts = [(float(np.interp(z, pyl[:, 0], pyl[:, 1])) * (1 - f) + float(np.interp(z, pyl[:, 0], pyl[:, 2])) * f, z) for z in np.linspace(pyl[0, 0], pyl[-1, 0], 24)]
            P.seam(reg, pts, pitch=1.3, off=0.55, width=2 if f < 0.2 else 1)
        P.panel(reg, 664.0, 262.0, 684.0, 284.0, r=2.0)                   # pylon drive shaft access
        # ---- markings
        P.text(reg, 556.0, 229.0, 'UNITED STATES ARMY', 6.2, font=FONT)
        zm = float(pyl[len(pyl) // 2, 0]); sm = 0.5 * float(np.interp(zm, pyl[:, 0], pyl[:, 1]) + np.interp(zm, pyl[:, 0], pyl[:, 2]))
        P.text(reg, sm + 2.0, zm + 6.0, '0-26467', 4.4, font=FONT)
        P.text(reg, 690.0, 258.0, 'DANGER', 2.2, col=(170, 30, 22, 235)); P.arrow(reg, 682.0, 254.0, 700.0, 3.0, (170, 30, 22, 235))
        P.text(reg, 690.0, 250.0, 'TAIL ROTOR', 1.6, col=(170, 30, 22, 235))
        # rescue arrow by the cabin door, yellow on the dark paint, and the cockpit door release
        P.arrow(reg, 262.0, 216.5, 300.5, 2.6, (196, 150, 20, 235)); P.text(reg, 276.0, 220.2, 'RESCUE', 1.5, col=(196, 150, 20, 235))
        P.text(reg, 276.0, 212.8, 'SLIDE DOOR AFT', 0.9, col=(196, 150, 20, 235))
        P.text(reg, 212.0, 211.0, 'EMERGENCY RELEASE  PULL', 0.8, col=(196, 150, 20, 235))
        P.text(reg, 254.0, 216.5, 'STEP', 0.9); P.text(reg, 404.0, 219.5, 'STEP', 0.9)
        P.text(reg, 465.0, 239.0, 'ELECTRICAL GROUND HERE', 0.8); P.text(reg, 610.0, 246.0, 'HOIST', 0.9)
        P.text(reg, 184.0, 211.0, 'EXTERNAL POWER 28 VDC / 115 VAC', 0.7)
        P.text(reg, 196.0, 240.0, 'AVIONICS', 0.8)
    # ---- top
    for s in frames:
        _, _, hw = body_lines(s)
        P.seam('T', [(s, -hw), (s, hw)], pitch=1.25, off=0.75)
    for b in (0.0,):
        P.seam('T', [(166.0, b), (300.0, b)], pitch=1.5, off=0.6)
    for sg in (1, -1):
        P.seam('T', [(228.0, sg * 24.0), (336.0, sg * 24.0)], pitch=1.5, off=0.0, width=1)
        # walkway non-skid either side of the roof, to the engine work platforms
        x0, y0 = px('T', 252.0, sg * 38.0); x1, y1 = px('T', 334.0, sg * 13.0)
        P.dd.rounded_rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 8, fill=150)
        P.text('T', 292.0, sg * 42.0, 'NO STEP', 1.3)
        # nacelle top cowl seams and deck panels
        P.panel('T', 352.0, sg * 24.0, 412.0, sg * 46.0, r=3.0, pitch=3.5)
        P.panel('T', 300.0, sg * 3.0, 334.0, sg * 19.0, r=2.0, pitch=2.6)
        P.panel('T', 446.0, sg * 2.0, 486.0, sg * 15.0, r=2.0, pitch=2.6)
        # stabilator: spars and ribs, NO STEP
        stab = np.array(RC.STAB)
        for b in np.arange(8.0, 84.0, 9.5):
            le = float(np.interp(b, stab[:, 0], stab[:, 1])); te = float(np.interp(b, stab[:, 0], stab[:, 2]))
            for reg in 'TB': P.seam(reg, [(le + 1.0, sg * b), (te - 0.8, sg * b)], pitch=1.3, off=0.0, width=1)
        for f in (0.1, 0.36, 0.7):
            pts = [(float(np.interp(b, stab[:, 0], stab[:, 1])) * (1 - f) + float(np.interp(b, stab[:, 0], stab[:, 2])) * f, sg * b) for b in np.linspace(1.0, 84.0, 12)]
            for reg in 'TB': P.seam(reg, pts, pitch=1.3, off=0.5, width=2 if f < 0.2 else 1)
        P.text('T', 716.0, sg * 46.0, 'NO STEP', 2.0)
    for s in np.arange(500.0, 646.0, 29.0):
        P.seam('T', [(s, -8.0), (s, 8.0)], pitch=1.4)
    P.seam('T', [(445.0, 0.0), (645.0, 0.0)], pitch=1.5, off=0.6, rivets=False)
    # ---- bottom
    for s in frames:
        _, _, hw = body_lines(s)
        P.seam('B', [(s, -hw), (s, hw)], pitch=1.25, off=0.75)
    for b in (-22.0, 0.0, 22.0):
        P.seam('B', [(190.0, b), (440.0, b)], pitch=1.5, off=0.6, width=2 if b == 0 else 1)
    P.panel('B', 330.0, -9.0, 356.0, 9.0, r=3.0, pitch=2.4)             # cargo hook well
    P.panel('B', 410.0, -14.0, 440.0, 14.0, r=2.0, pitch=2.4)           # fuel cell access
    P.panel('B', 196.0, -10.0, 222.0, 10.0, r=2.0, pitch=2.4)           # nose / searchlight access
    for s in (232.0, 262.0, 300.0, 380.0, 460.0, 540.0):                # drains
        x, y = px('B', s, 0.0); P.dd.ellipse([x - 4, y - 4, x + 4, y + 4], fill=255); P.dc.ellipse([x - 6, y - 6, x + 6, y + 6], outline=200, width=2)
    return P


def compose(P, out_dir, size=W, log=print):
    os.makedirs(out_dir, exist_ok=True)
    A = lambda im: np.asarray(im, np.float32) / 255.0
    groove = blur(A(P.groove), 0.7); rivet = blur(A(P.rivet), 0.6); screw = blur(A(P.screw), 0.8); plate = blur(A(P.plate), 1.2)
    dark = blur(A(P.dark), 1.0); ink = np.asarray(P.ink, np.float32) / 255.0
    rng = np.random.default_rng(61)
    n_big = noise((W, W), 420, 1, 4); n_mid = noise((W, W), 96, 2, 4); n_fine = noise((W, W), 14, 3, 3); n_px = rng.random((W, W)).astype(np.float32)
    # ---- runs: grime that starts at seams, panel bottoms and fasteners and trails down the sides
    seeds = A(P.drip) * (n_fine > 0.52) * (rng.random((W, W)) > 0.72) * (0.35 + 0.65 * n_mid)
    seeds += blur(screw, 0.5) * (rng.random((W, W)) > 0.9) * 0.5
    run = np.zeros((W, W), np.float32)
    decay = (0.955 + 0.04 * noise((1, W), 9, 7, 2)[0] * rng.random(W)).astype(np.float32)        # every column its own length
    for reg in 'LR':
        r0 = ROW[reg]; acc = np.zeros(W, np.float32)
        for r in range(r0, r0 + H_SIDE):
            acc = np.maximum(seeds[r], acc * decay); run[r] = acc
    run = blur(run, 0.9) * (0.45 + 0.55 * n_mid)
    # ---- soot aft of each exhaust ejector (side: STA 440+, WL ~ 277; top: BL +-36), carried aft and a little up
    soot = np.zeros((W, W), np.float32)
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    for reg in 'LR':
        x0, y0 = px(reg, 446.0, 277.5); dx = (xx - x0) / KX; dy = (y0 - yy) / KZ
        m = (dx > -4) * np.exp(-np.maximum(dx, 0) / 62.0) * np.exp(-((dy - 0.05 * np.maximum(dx, 0)) / (7.0 + 0.11 * np.maximum(dx, 0))) ** 2) * np.clip((dx + 4) / 10, 0, 1)
        m[:ROW[reg]] = 0; m[ROW[reg] + H_SIDE:] = 0; soot += m
    for sg in (1, -1):
        x0, y0 = px('T', 446.0, sg * 37.0); dx = (xx - x0) / KX; dy = (yy - y0) / KB
        m = (dx > -4) * np.exp(-np.maximum(dx, 0) / 62.0) * np.exp(-(dy / (8.0 + 0.10 * np.maximum(dx, 0))) ** 2) * np.clip((dx + 4) / 10, 0, 1)
        m[:ROW['T']] = 0; m[ROW['T'] + H_TOP:] = 0; soot += m
    soot = np.clip(soot * (0.55 + 0.6 * n_mid), 0, 1)
    del xx, yy
    # ---- belly dust and wheel spray on the bottom and the low sides
    dust = np.zeros((W, W), np.float32)
    dust[ROW['B']:ROW['B'] + H_TOP] = 0.55
    for reg in 'LR':
        wl = WLB - (np.arange(H_SIDE) / KZ); dust[ROW[reg]:ROW[reg] + H_SIDE] = np.clip((214.0 - wl) / 16.0, 0, 1)[:, None] * 0.6
    dust *= (0.4 + 0.9 * n_mid) * (0.6 + 0.6 * n_big)
    # ---- chips: bare metal where the masks say hands, boots and latches work, broken up by fine noise
    chipm = blur(A(P.chip), 1.4)
    chips = ((chipm * (0.45 + 0.9 * n_fine) * (0.4 + n_px)) > 0.74).astype(np.float32)
    chips = np.maximum(chips, ((n_fine * n_mid * (0.6 + 0.8 * n_px)) > 0.74).astype(np.float32) * 0.0)
    chips = blur(chips, 0.45)
    # ---- colour
    base = np.array((0.150, 0.165, 0.120), np.float32)                      # same paint as materials.LIB['paint_od']
    fade = (0.82 + 0.36 * n_big)[..., None] * (0.92 + 0.16 * n_mid)[..., None]
    col = base[None, None, :] * fade
    col = col * (1 + 0.10 * (n_big - 0.5))[..., None] + np.array((0.012, 0.006, -0.004), np.float32) * (n_big - 0.5)[..., None]
    grime = np.clip(blur(groove, 2.6) * 1.6 + blur(rivet, 1.8) * 0.5, 0, 1) * (0.5 + 0.8 * n_mid)
    col *= (1 - 0.42 * grime)[..., None]
    col *= (1 - 0.62 * np.clip(run * 1.7, 0, 1))[..., None]
    col *= (1 - 0.55 * dark)[..., None]
    col = col * (1 - 0.86 * soot)[..., None] + np.array((0.012, 0.011, 0.010), np.float32) * (0.86 * soot)[..., None]
    dcol = np.array((0.33, 0.29, 0.22), np.float32)
    col = col * (1 - 0.34 * dust)[..., None] + dcol * (0.34 * dust)[..., None]
    a = ink[..., 3:4] * (0.72 + 0.28 * n_fine)[..., None] * (1 - 0.6 * soot)[..., None]
    col = col * (1 - a) + ink[..., :3] * a
    col *= (1 - 0.55 * np.clip(groove * 1.2, 0, 1))[..., None]
    col *= (1 - 0.25 * rivet)[..., None]
    bare = np.array((0.52, 0.53, 0.54), np.float32)
    col = col * (1 - chips)[..., None] + bare * chips[..., None]
    col = np.clip(col, 0, 1)
    # ---- height -> normal
    h = (-1.0 * groove - 0.35 * rivet + 0.55 * screw + 0.5 * plate + 0.10 * chips * -1
         + 0.9 * (blur(n_mid, 6) - 0.5) * 0.0 + 0.05 * (n_fine - 0.5) + 0.03 * (n_px - 0.5))
    # oil-canning: the thin skin dishes a little between frames and stringers
    can = blur(1 - np.clip(blur(groove, 9.0) * 6.0, 0, 1), 5.0) * (0.6 + 0.8 * n_big)
    h = h + 1.0 * can
    gx = np.zeros_like(h); gy = np.zeros_like(h)
    gx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5; gy[1:-1, :] = (h[2:, :] - h[:-2, :]) * 0.5
    k = 1.6
    nx = -gx * k; ny = gy * k; nz = np.ones_like(h)             # image rows run down, V runs up
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
    # ---- occlusion, roughness, metallic
    ao = np.clip(1 - 0.5 * blur(groove, 1.6) - 0.25 * rivet, 0, 1)
    rough = 0.80 + 0.10 * (n_mid - 0.5) - 0.16 * np.clip(blur(chipm, 6) * (n_mid), 0, 1) + 0.14 * soot + 0.12 * dust + 0.12 * dark
    rough = rough * (1 - chips) + 0.42 * chips
    orm = np.stack([ao, np.clip(rough, 0.05, 1), chips], -1)

    def save(a, name, **kw):
        im = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
        if size != W: im = im.resize((size, size), Image.LANCZOS)
        p = os.path.join(out_dir, name); im.save(p, **kw); return p
    srgb = col                                              # colours above are picked in sRGB, like materials.LIB
    paths = dict(color=save(srgb, 'skin_color.jpg', quality=92), normal=save(nrm, 'skin_normal.png'), orm=save(orm, 'skin_orm.png'))
    log('skin maps', size, {k: round(os.path.getsize(v) / 1e6, 2) for k, v in paths.items()})
    return paths


def build_maps(out_dir, size=W, log=print):
    """Paint the maps, or reuse the ones already in out_dir if this file has not changed since."""
    names = dict(color='skin_color.jpg', normal='skin_normal.png', orm='skin_orm.png')
    paths = {k: os.path.join(out_dir, v) for k, v in names.items()}
    if all(os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(__file__) for p in paths.values()) \
            and Image.open(paths['color']).size[0] == size:
        return paths
    return compose(paint(), out_dir, size, log)


# ------------------------------------------------------------------ Blender side
def material(ctx, paths, name='skin_od'):
    import bpy
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF')

    def tex(path, colorspace):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path); t.image.colorspace_settings.name = colorspace
        return t
    c = tex(paths['color'], 'sRGB'); nt.links.new(c.outputs['Color'], b.inputs['Base Color'])
    o = tex(paths['orm'], 'Non-Color'); sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(o.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness']); nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    n = tex(paths['normal'], 'Non-Color'); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.0
    nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    m.use_backface_culling = True
    ctx.mats[name] = m
    return m


def unwrap(o, inner_mat=None):
    """Give a painted exterior object its atlas UVs from where each face sits on the aircraft. Faces of a solidified
    shell that look inward get `inner_mat` (slot 1) instead."""
    import bpy
    from lib import IN
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    nv = len(me.vertices); co = np.zeros(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]
    sta = co[:, 1] / IN + RC.STA_MAST; bl = co[:, 0] / IN; wl = co[:, 2] / IN + RC.WL_GROUND
    npoly = len(me.polygons); nrm = np.zeros(npoly * 3); me.polygons.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3) @ mw[:3, :3].T
    cen = np.zeros(npoly * 3); me.polygons.foreach_get('center', cen); cen = cen.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    ls = np.zeros(npoly, np.int32); lt = np.zeros(npoly, np.int32); me.polygons.foreach_get('loop_start', ls); me.polygons.foreach_get('loop_total', lt)
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    lp = np.repeat(np.arange(npoly), lt)                      # polygon of each loop (loops are stored polygon by polygon)
    nbl = nrm[:, 0]; nwl = nrm[:, 2]
    side = np.abs(nbl) >= np.abs(nwl)
    reg = np.where(side, np.where(nbl >= 0, 0, 1), np.where(nwl >= 0, 2, 3))[lp]
    s = sta[lv]; b = bl[lv]; w = wl[lv]
    x = (s - STA0) * KX
    y = np.select([reg == 0, reg == 1, reg == 2, reg == 3],
                  [ROW['L'] + (WLB - w) * KZ, ROW['R'] + (WLB - w) * KZ, ROW['T'] + (BLH - b) * KB, ROW['B'] + (BLH + b) * KB])
    uvs = np.stack([x / W, 1 - y / W], 1)
    me.uv_layers[0].data.foreach_set('uv', uvs.ravel())
    if inner_mat is not None:
        csta = cen[:, 1] / IN + RC.STA_MAST; cbl = cen[:, 0] / IN; cwl = cen[:, 2] / IN + RC.WL_GROUND
        zc = np.array([0.5 * sum(body_lines(float(q))[:2]) for q in csta])
        inward = (nbl * cbl + nwl * (cwl - zc)) < -0.02 * np.hypot(cbl, cwl - zc)
        me.materials.append(inner_mat)
        me.polygons.foreach_set('material_index', inward.astype(np.int32))
    me.update()
