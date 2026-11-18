"""Orthographic sheet: lays the orthographic renders out on one drawing and dimensions them from spec.py.
    python3 tools/sheet.py --in work/r_blockout --out ../renders/sheet_blockout.jpg --title "..." """
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path[:0] = [HERE, os.path.join(HERE, 'tools')]
from PIL import Image, ImageDraw, ImageFont
import spec, shots as SH
argv = sys.argv[1:]
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
IN = os.path.join(HERE, arg('--in', 'work/r_blockout')); OUT = os.path.join(HERE, arg('--out', '../renders/sheet.jpg'))
TITLE = arg('--title', 'F-27 WAYFARER  ·  general arrangement'); STAGE = arg('--stage', 'BLOCKOUT')
FD = '/usr/share/fonts/opentype/inter/'
def font(sz, w='Regular'):
    try: return ImageFont.truetype(FD + f'Inter-{w}.otf', sz)
    except Exception: return ImageFont.load_default()
INK = (28, 32, 38); DIM = (176, 40, 30); SOFT = (95, 102, 112); PAPER = (236, 237, 239)
S = spec.ST
Wc, Hc = 3900, 4400
sheet = Image.new('RGB', (Wc, Hc), PAPER); D = ImageDraw.Draw(sheet)

def place(name, x, y, w, caption):
    im = Image.open(os.path.join(IN, name + '.jpg')); h = int(w * im.height / im.width)
    im = im.resize((w, h), Image.LANCZOS); sheet.paste(im, (x, y))
    D.rectangle((x, y, x + w, y + h), outline=(150, 154, 160), width=2)
    D.text((x + 14, y + 10), caption, font=font(30, 'SemiBold'), fill=INK)
    sh = SH.ORTHO[name]
    def P(p):
        px, py = SH.project(sh, p, w); return (x + px, y + py)
    return P, (x, y, w, h)

def label(P, p, text, dx=0, dy=0, anchor='mm', sz=24, col=INK, leader=None):
    x, y = P(p); f = font(sz, 'Medium')
    if leader:
        lx, ly = P(leader); D.line((lx, ly, x + dx, y + dy), fill=col, width=2); D.ellipse((lx - 4, ly - 4, lx + 4, ly + 4), fill=col)
    bb = D.textbbox((x + dx, y + dy), text, font=f, anchor=anchor)
    D.rectangle((bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4), fill=(248, 248, 249))
    D.text((x + dx, y + dy), text, font=f, fill=col, anchor=anchor)

def dim(P, a, b, text, off=(0, 0), sz=24):
    (x0, y0), (x1, y1) = P(a), P(b); x0 += off[0]; x1 += off[0]; y0 += off[1]; y1 += off[1]
    D.line((x0, y0, x1, y1), fill=DIM, width=3)
    horiz = abs(x1 - x0) > abs(y1 - y0)
    for (x, y) in ((x0, y0), (x1, y1)):
        if horiz: D.line((x, y - 14, x, y + 14), fill=DIM, width=3)
        else: D.line((x - 14, y, x + 14, y), fill=DIM, width=3)
    f = font(sz, 'SemiBold'); mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    bb = D.textbbox((mx, my), text, font=f, anchor='mm')
    D.rectangle((bb[0] - 8, bb[1] - 4, bb[2] + 8, bb[3] + 4), fill=PAPER); D.text((mx, my), text, font=f, fill=DIM, anchor='mm')

def station_ticks(P, z, every=5):
    for s in range(0, 31, every):
        x, y = P((s, 0, z)); D.line((x, y, x, y + 16), fill=SOFT, width=2); D.text((x, y + 20), f'{s}', font=font(20), fill=SOFT, anchor='ma')

# ---------------------------------------------------------------- title
D.text((60, 40), TITLE, font=font(64, 'Bold'), fill=INK)
D.text((60, 122), f'1.25 x F-27 spec  ·  {spec.L:.0f} x {spec.W:.0f} x {spec.H:.2f} m  ·  stage: {STAGE}  ·  figures are 1.80 m  ·  station numbers are metres aft of the nose', font=font(30), fill=SOFT)
M = 60; WW = Wc - 2 * M; hw = WW // 3
y = 190
# ---------------------------------------------------------------- port side
P, (x0, y0, w, h) = place('port_side', M, y, WW, 'PORT SIDE, gear and lift down')
dim(P, (0, 0, 3.75), (30, 0, 3.75), 'overall length 30.00 m')
dim(P, (31.0, 0, -3.375 + 0.0), (31.0, 0, 3.375), '6.75', sz=22)
dim(P, (-0.9, 0, spec.Z_GROUND), (-0.9, 0, -3.0), '1.70')
station_ticks(P, spec.Z_GROUND - 0.25)
label(P, (2.6, 0, 1.2), 'canopy slit', dy=-150, leader=(2.6, 0, 1.25))
label(P, (0.4, 0, -2.5), 'chin cannon', dy=110, dx=40, leader=(0.4, 0, -2.6))
label(P, (6.0, 0, -3.9), 'fwd gear x2', dx=-150, dy=40, leader=(6.0, 0, -3.9))
label(P, (21.0, 0, -3.9), 'aft gear x2', dx=150, dy=40, leader=(21.0, 0, -3.9))
label(P, (11.4, 0, -4.4), 'lift chassis (lowered)', dy=70, leader=(11.4, 0, -4.4))
label(P, (26.0, 0, -0.45), 'main pod', sz=24); label(P, (26.5, 0, 1.75), 'upper pod', sz=24)
y += h + 40
# ---------------------------------------------------------------- centreline section
P, (x0, y0, w, h) = place('section_cl', M, y, WW, 'SECTION ON THE CENTRELINE, looking to starboard')
zc = spec.Z_MAIN + 1.75; zl = spec.Z_LOWER + 1.55
for (s, z, t) in ((3.7, zc + 0.75, 'COCKPIT'), (7.2, zc, 'VESTIBULE\ncrew hatch, ladder'), (11.0, zc + 0.45, 'CREW DECK'), (17.5, zc, 'MISSION BAY'), (22.9, zc + 0.45, 'ENGINEERING'),
                  (7.4, zl - 0.9, 'AVIONICS AISLE'), (11.4, zl + 0.25, 'HOLD + LIFT'), (17.4, zl, 'LANDER BAY\n(internal landing array)'), (22.3, zl - 0.2, 'REACTOR')):
    label(P, (s, 0, z), t, sz=24)
dim(P, (13.3, 0, spec.Z_MAIN), (13.3, 0, spec.Z_MAIN + spec.HEAD_MAIN), '2.30')
dim(P, (14.0, 0, spec.Z_LOWER), (14.0, 0, spec.Z_LOWER + spec.HEAD_LOWER), '2.20')
dim(P, (9.6, 0, -4.25), (13.2, 0, -4.25), '3.60', off=(0, 95))
dim(P, (14.2, 0, -3.3), (20.6, 0, -3.3), 'bay doors 6.40')
dim(P, (9.0, 0, spec.Z_GROUND + spec.LIFT['chassis_depth']), (9.0, 0, spec.Z_LOWER), 'travel 1.70')
for st in ('cockpit_aft', 'vestibule_aft', 'hold_aft', 'eng_fwd', 'eng_aft'):
    xx, yy = P((S[st], 0, 3.3)); D.text((xx, yy), f'{S[st]:.1f}', font=font(20), fill=SOFT, anchor='mb')
station_ticks(P, spec.Z_GROUND - 0.25)
y += h + 40
# ---------------------------------------------------------------- plans
for k, (nm, cap) in enumerate((('top', 'TOP'), ('plan_main', 'MAIN DECK PLAN (cut 1.8 m above the deck)'), ('plan_lower', 'LOWER DECK PLAN (cut 1.8 m above the deck)'))):
    P, (x0, y0, w, h) = place(nm, M + k * (hw + 0) + (0 if k == 0 else 0), y, hw - 20, cap)
    if nm == 'top':
        dim(P, (29.0, -4.5, 0), (29.0, 4.5, 0), '9.00', sz=20); dim(P, (12.0, -3.0, 0), (12.0, 3.0, 0), '6.00', sz=20)
    if nm == 'plan_main':
        for (s, t) in ((3.6, 'cockpit'), (7.2, 'vest.'), (11.0, 'crew deck'), (17.5, 'mission bay'), (22.9, 'eng.')):
            label(P, (s, -1.6, 0), t, sz=19)
        label(P, (7.4, 1.4, 0), 'ladder', sz=17)
    if nm == 'plan_lower':
        for (s, t) in ((7.2, 'aisle'), (11.4, 'lift'), (17.4, 'lander'), (22.0, 'reactor')):
            label(P, (s, 0, 0), t, sz=19)
        label(P, (7.6, 1.8, 0), 'gear well', sz=16); label(P, (19.4, 1.8, 0), 'gear well', sz=16)
y += h + 40
# ---------------------------------------------------------------- ends and cross sections
qw = WW // 4
for k, (nm, cap) in enumerate((('front', 'FRONT'), ('rear', 'REAR'), ('section_lift', 'SECTION AT 11.4 (lift), looking forward'), ('section_bay', 'SECTION AT 17.4 (lander bay), looking forward'))):
    P, (x0, y0, w, h) = place(nm, M + k * qw, y, qw - 20, cap)
    if nm == 'front':
        dim(P, (0, 3.0, -3.55), (0, -3.0, -3.55), 'hull 6.00', sz=20); dim(P, (0, 1.8, spec.Z_GROUND + 0.5), (0, -1.8, spec.Z_GROUND + 0.5), 'track 3.60', sz=20)
    if nm == 'rear':
        dim(P, (30, -4.5, 3.6), (30, 4.5, 3.6), 'over pods 9.00', sz=20)
    if nm == 'section_lift':
        dim(P, (11.4, -1.3, -3.9), (11.4, 1.3, -3.9), '2.60', sz=20, off=(0, 0))
        label(P, (11.4, 1.75, spec.Z_MAIN + 1.9), 'main deck', sz=18); label(P, (11.4, 1.3, spec.Z_LOWER + 1.9), 'hold', sz=18)
    if nm == 'section_bay':
        dim(P, (17.4, -1.2, spec.Z_LOWER - 0.45), (17.4, 1.2, spec.Z_LOWER - 0.45), 'lander 2.40', sz=20)
        label(P, (17.4, 0, spec.Z_MAIN + 1.9), 'mission bay', sz=18)
yq = y + h + 36
notes = [
    'Modules (built and exported separately): fuselage · cockpit · engines · landing gear · lift chassis · lander bay · gadgets.',
    'Read from the concept image: rounded barrel hull, wraparound canopy slit under an armoured brow, recessed red waist channel, row of equipment bays under it, chin cannon,',
    'ventral gun pod, side engine pods with octagonal intake faces and ribbed barrels, armoured cowl over the upper pods, exposed machinery along the keel.',
    'Not in the image, designed here: everything inside, the four-leg landing gear, the lift chassis that lowers from the hold, and the lander bay with its belly doors.',
]
for k, t in enumerate(notes):
    D.text((M, yq + k * 38), t, font=font(26), fill=INK if k == 0 else SOFT)
sheet = sheet.crop((0, 0, Wc, min(Hc, yq + len(notes) * 38 + 40)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
sheet.save(OUT, quality=88); print('SHEET', OUT, sheet.size)
