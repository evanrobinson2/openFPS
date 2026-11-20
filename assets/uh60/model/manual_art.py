"""The instrument panel and lower console faces, taken from the manual's own drawings.

TM 1-1520-237-10 figure 2-9 (Instrument Panel, sheets 1 and 2, UH) is one large-scale front view of the whole panel
split over two pages; figure 2-8 (Lower Console, sheet 1, UH) is a plan of the console top. Both are vector art in the
PDF. This module joins the two panel sheets (registered on the central display unit's lettering, which appears on
both), cuts the result into the individual instruments by flood-filling the blank panel between them, and writes:

  panel_art.png / console_art.png   the drawings as white-on-black faces (what the crew see: black dials, white marks)
  manual_art.json                   every instrument's outline (panel inches), every knob circle the drawings show

Nothing here is drawn by hand: instrument positions, shapes, dial markings, legends and knob positions are the
manual's. Scale: the panel drawing is fitted to the 67 in panel width; the console drawing to the 5.75 in standard
control-head width its three columns are drawn with. Heights of plates and knobs above the panel are not in these
front views and are small nominal values [INF].
Needs PyMuPDF and OpenCV, and the manual at refs-local/tm10.pdf (not in git; see notes/SOURCES.md).
"""
import json, os
import numpy as np

ZOOM = 6.0                                   # render scale, px per PDF point
PANEL_W = 67.0                               # in, across the panel face [fitted]
P_CLIP = (60, 55, 990, 300)                  # panel area in sheet-1 page points
P_SEAM, P_SHIFT = 521.0, (437.7, -27.6)      # sheet 2 = sheet 1 - shift (from the 'OFF' / 'DIGITS' lettering on both)
P_POLY = [(100, 230), (170, 120), (2790, 95), (5380, 120), (5470, 230), (5470, 1180), (5400, 1265), (4150, 1265), (3700, 1400),
          (1900, 1400), (1250, 1265), (170, 1265), (100, 1180)]            # panel face outline traced on the joined drawing, px
P_CALLOUTS = [[(0, 1300), (100, 1300), (100, 1430), (0, 1430)], [(40, 1320), (75, 1320), (170, 1050), (140, 1030)],
              [(3760, 0), (4300, 0), (4300, 30), (3830, 250), (3790, 225)], [(4060, 1385), (4200, 1385), (4200, 1470), (4060, 1470)],
              [(4100, 1390), (4140, 1390), (4300, 1085), (4268, 1070)]]    # the figure's own callout arrows, erased
P_FRAMES = [(130, 880, 445, 1210), (4270, 922, 4587, 1247)]                # MODE SEL frames the callout arrows crossed: redrawn
# knobs on the panel: approximate centres (px) snapped to the circle the drawing shows there
P_KNOBS = [(576, 721), (930, 721), (576, 1161), (930, 1161), (1100, 515), (1327, 515), (1636, 976), (2570, 576), (2667, 597), (2836, 591),
           (3115, 782), (3515, 697), (3636, 682), (3433, 879), (3661, 1052), (2564, 1085),
           (4706, 721), (5061, 721), (4706, 1161), (5061, 1161), (5233, 515), (5464, 515), (3961, 976)]
C_CLIP = (180, 80, 470, 690)                 # console figure, page points
C_TOP = (28, 30, 1626, 3337)                 # the console (sloped top, then the aft section) in the rendered clip, px
C_INSET = (1170, 2550)                       # a separate inset view overlaps the aft right corner from here: blanked
C_ARROW = (1078, 338, 1598, 374)             # callout arrow C across the top section: erased, crossing lines healed
C_HEAD_W = 5.75                              # in, standard control head width
C_COL_PX = 85.0 * ZOOM                       # one column of the drawing, px


def _render(doc, page, rect):
    import fitz
    pm = doc[page - 1].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=fitz.Rect(*rect), colorspace=fitz.csGRAY)
    return np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width).copy()


def _circles(img, rmin, rmax):
    import cv2
    c = cv2.HoughCircles(cv2.GaussianBlur(img, (5, 5), 1.2), cv2.HOUGH_GRADIENT_ALT, dp=1.5, minDist=rmin * 1.2, param1=200, param2=0.82,
                         minRadius=rmin, maxRadius=rmax)
    return [] if c is None else [tuple(float(v) for v in k) for k in c[0]]


def _silhouette(img, box, clamps, k=4.8):
    """Filled outline of one drawn object. box and clamps are in 90 dpi page pixels; clamps = rows (y0, y1) keep x0..x1."""
    import cv2
    x0, y0, x1, y1 = box
    c = img[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)]
    free = cv2.bitwise_not(cv2.dilate((c < 150).astype(np.uint8) * 255, np.ones((5, 5), np.uint8))); h, w = free.shape
    ff = free.copy(); mask = np.zeros((h + 2, w + 2), np.uint8)
    for sd in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if ff[sd[1], sd[0]] == 255: cv2.floodFill(ff, mask, sd, 128)
    shape = cv2.morphologyEx((ff != 128).astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((23, 23), np.uint8))   # drops leader lines and lettering
    for (ya, yb, xa, xb) in clamps:
        r0, r1 = int((ya - y0) * k), int((yb - y0) * k); shape[r0:r1, :max(0, int((xa - x0) * k))] = 0; shape[r0:r1, int((xb - x0) * k):] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(shape)
    return (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)


def _extents(shape, rows=44):
    """Per height (bottom to top, 0..1): (lo, hi) of the shape, in units of its own height, measured from the base centre."""
    ys = np.where(shape.any(1))[0]; top, bot = ys.min(), ys.max(); H = bot - top
    base = np.where(shape[bot - 3])[0]; c0 = (base.min() + base.max()) / 2; out = []
    for t in np.linspace(0.0, 1.0, rows):
        r = shape[int(round(bot - t * H * 0.995))]; xs = np.where(r)[0]
        out.append((float((xs.min() - c0) / H), float((xs.max() - c0) / H)) if len(xs) else out[-1])
    return out


def _face(img, plate_mask=None):
    """White-on-black: lines light, plates black, bare panel dark grey."""
    ink = ((255 - img).astype(np.float32) / 255.0) ** 1.5      # thin the drawn line a little: it is heavier than engraved lettering
    base = np.full(img.shape, 9.0 if plate_mask is None else 17.0, np.float32)   # control heads black; bare panel dark grey
    if plate_mask is not None: base[plate_mask > 0] = 6.0
    out = base * (1 - ink) + 178.0 * ink
    return np.clip(out, 0, 255).astype(np.uint8)


def build(out_dir, pdf, log=print):
    """Returns the parsed manual_art.json (building it and the images if they are missing or stale)."""
    os.makedirs(out_dir, exist_ok=True)
    pj = os.path.join(out_dir, 'manual_art.json'); pp = os.path.join(out_dir, 'panel_art.png'); pc = os.path.join(out_dir, 'console_art.png')
    if all(os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(__file__) for p in (pj, pp, pc)):
        return json.load(open(pj))
    import fitz, cv2
    doc = fitz.open(pdf)
    # ---------------- panel: join the sheets
    X0, Y0, X1, Y1 = P_CLIP; dx, dy = P_SHIFT
    a = _render(doc, 61, (X0, Y0, P_SEAM, Y1)); b = _render(doc, 62, (P_SEAM - dx, Y0 - dy, X1 - dx, Y1 - dy))
    h = min(a.shape[0], b.shape[0]); img = np.hstack([a[:h], b[:h]]); H, W = img.shape
    for pts in P_CALLOUTS: cv2.fillPoly(img, [np.array(pts, np.int32)], 255)
    for (x0, y0, x1, y1) in P_FRAMES: cv2.rectangle(img, (x0, y0), (x1, y1), 30, 3)
    poly = np.array(P_POLY, np.int32)
    P = np.zeros((H, W), np.uint8); cv2.fillPoly(P, [poly], 255)
    lines = (img < 150).astype(np.uint8) * 255
    free = cv2.bitwise_and(cv2.bitwise_not(cv2.dilate(lines, np.ones((3, 3), np.uint8))), P)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
    bg = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255       # the blank panel between instruments
    bg = cv2.morphologyEx(bg, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    plates = cv2.morphologyEx(cv2.bitwise_and(cv2.bitwise_not(bg), P), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(plates, connectivity=8)
    ppi = (poly[:, 0].max() - poly[:, 0].min()) / PANEL_W; px0 = poly[:, 0].min(); pz0 = poly[:, 1].max()
    to_in = lambda p: (round(PANEL_W / 2 - (p[0] - px0) / ppi, 3), round((pz0 - p[1]) / ppi, 3))     # px -> panel (BL, up), inches
    plist = []; pmask = np.zeros((H, W), np.uint8)
    for i in range(1, n2):
        x, y, w, hh, area = st2[i]
        if area < 3000 or y < 150: continue                              # specks; glare shield brackets along the top edge
        m = (lab2 == i).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea); c = cv2.approxPolyDP(c, 2.5, True)[:, 0, :]
        if len(c) < 3: continue
        plist.append([to_in(p) for p in c]); pmask[lab2 == i] = 255
    circ = _circles(img, 14, 48); knobs = []
    for (kx, ky) in P_KNOBS:
        best = min(circ, key=lambda c: (c[0] - kx) ** 2 + (c[1] - ky) ** 2) if circ else None
        if best and (best[0] - kx) ** 2 + (best[1] - ky) ** 2 < 45 ** 2:
            y, z = to_in(best[:2]); knobs.append((y, z, round(best[2] / ppi, 3)))
    face = _face(img, pmask); face[P == 0] = 17
    x_lo, x_hi = int(px0), int(poly[:, 0].max()); y_lo, y_hi = int(poly[:, 1].min()), int(pz0)
    cv2.imwrite(pp, face[y_lo:y_hi, x_lo:x_hi])
    panel = dict(ppi=float(ppi), w=PANEL_W, h=float((y_hi - y_lo) / ppi), outline=[to_in(p) for p in poly], plates=plist, knobs=knobs)
    # ---------------- console top
    c = _render(doc, 56, C_CLIP); cx0, cy0, cx1, cy1 = C_TOP; top = c[cy0:cy1, cx0:cx1].copy()
    top[C_INSET[1] - cy0:, C_INSET[0] - cx0:] = 255
    ax0, ay0, ax1, ay1 = C_ARROW; keep = (top[ay0 - 6, ax0:ax1] < 150) & (top[ay1 + 6, ax0:ax1] < 150)
    top[ay0:ay1, ax0:ax1] = np.where(keep[None, :], 30, 255)
    cppi = C_COL_PX / C_HEAD_W; cw = (cx1 - cx0) / cppi; cl = (cy1 - cy0) / cppi
    ck = [(round(y / cppi, 3), round(cw / 2 - x / cppi, 3), round(r / cppi, 3)) for x, y, r in _circles(top, 9, 60)]   # (along aft, BL, r)
    cv2.imwrite(pc, _face(top))
    # ---------------- cyclic stick grip: side and front views of figure 2-14 sheet 2
    g = _render(doc, 88, (0, 0, doc[87].rect.width, doc[87].rect.height))
    side = _silhouette(g, (150, 340, 400, 725), [(640, 725, 256, 360), (340, 640, 150, 385)])
    front = _silhouette(g, (500, 340, 720, 725), [(340, 470, 520, 720), (470, 610, 548, 720), (630, 725, 500, 652)])
    art = dict(panel=panel, console=dict(ppi=float(cppi), w=float(cw), l=float(cl), knobs=ck), cyclic=dict(side=_extents(side), front=_extents(front)))
    json.dump(art, open(pj, 'w'))
    log(f'manual art: panel {x_hi - x_lo}x{y_hi - y_lo} px, {len(plist)} instruments, {len(knobs)} knobs; console {cw:.1f} x {cl:.1f} in, {len(ck)} circles')
    return art


def material(ctx, name, path, scale=1.0):
    """Unlit-looking face: the drawing as colour and, dimmed, as its own panel lighting."""
    import bpy
    img = bpy.data.images.load(path)
    if scale != 1.0: img.scale(max(8, int(img.size[0] * scale)), max(8, int(img.size[1] * scale)))
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 0.32; b.inputs['Roughness'].default_value = 0.92
    b.inputs['Specular IOR Level'].default_value = 0.12
    ctx.mats[name] = m


def set_uv(o, fn):
    """fn(aircraft (n, 4) homogeneous inches) -> (n, 2) uv."""
    from lib import IN
    import recipe as RC
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    nv = len(me.vertices); co = np.zeros(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    a = np.stack([co[:, 1] / IN + RC.STA_MAST, co[:, 0] / IN, co[:, 2] / IN + RC.WL_GROUND, np.ones(nv)], 1)
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    me.uv_layers[0].data.foreach_set('uv', fn(a)[lv].ravel())
