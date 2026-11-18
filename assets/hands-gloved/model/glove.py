"""Glove grammar: which material each face of each shell carries, and the raised parts sewn onto the shells.
Derived from reference R1 (notes/DECOMPOSITION.md, notes/STUDIES.md): knit back, synthetic-leather palm, dark fingertip
caps, ribbed flex panels over the knuckles, a terry wipe panel on the back of the thumb, a dark cuff with a plain strap."""
import math
import numpy as np
from handlib import BI, ORDER, P, seg, FING

MATERIALS = ['glove_back_knit', 'glove_palm_synthetic_leather', 'glove_fingertip', 'glove_flex_rib', 'glove_terry', 'glove_cuff', 'sleeve_fabric', 'glove_seam', 'glove_tab']
MI = {n: i for i, n in enumerate(MATERIALS)}
RIB_PITCH = 3.2           # mm, ribs of a flex panel (R1: 5 ribs over the index knuckle, about 16 mm)

def face_materials(sh):
    """Material index per triangle of a shell (rest pose)."""
    F = sh['F']; rg = sh['ring'][F].min(1); s = sh['s'][F].mean(1); s[:len(s) // 2 * 2] = np.repeat((s[0:len(s) // 2 * 2:2] + s[1:len(s) // 2 * 2:2]) / 2, 2); a = sh['ang'][F]; dors = np.sin(a).mean(1); dors[:len(dors) // 2 * 2] = np.repeat((dors[0:len(dors) // 2 * 2:2] + dors[1:len(dors) // 2 * 2:2]) / 2, 2); k = sh['kind']; m = np.zeros(len(F), np.int32)
    if k in ('finger', 'thumb'):
        j0, j1, j2 = sh['joints']; L = sh['L']; B = sh['B']
        m[:] = np.where(dors > -0.25, MI['glove_back_knit'], MI['glove_palm_synthetic_leather'])
        side = np.abs(dors) < 0.22; m[side & (s > j1 * 0.2)] = MI['glove_seam']                       # fourchette seam along each side
        for jc, half in ((j1, 8.0), (j2, 5.5)) if k == 'finger' else ((j2, 6.5),):                    # flex panels over PIP and DIP
            band = (np.abs(s - jc) < half) & (dors > 0.35); rib = rg % 2 == 0
            m[band & rib] = MI['glove_flex_rib']; m[band & ~rib] = MI['glove_seam']
        if k == 'thumb': m[(dors > 0.3) & (s > 10) & (s < j2 - 8)] = MI['glove_terry']
        m[s > L - 1.15 * 2 * B * (0.55 if k == 'finger' else 0.6)] = MI['glove_fingertip']
    elif k == 'palm':
        V = sh['V'][F].mean(1); V[:len(V) // 2 * 2] = np.repeat((V[0:len(V) // 2 * 2:2] + V[1:len(V) // 2 * 2:2]) / 2, 2, axis=0)                                           # dorsal by vertex z against the mid-plane
        m[:] = np.where(V[:, 2] > -3.0, MI['glove_back_knit'], MI['glove_palm_synthetic_leather'])
        u = s                                    # (CR-2: the ribbed panel over the knuckles is now four raised pads, detail_parts)
        m[(np.abs(V[:, 2] + 3.0) < 1.6) & (u > 0.1)] = MI['glove_seam']
    elif k == 'web':
        m[:] = MI['glove_palm_synthetic_leather']; m[dors > 0.25] = MI['glove_seam']      # CR-2: R1-F07, the dark binding along the edge between thumb and index
    elif k == 'cuff': m[:] = MI['glove_cuff']
    else: m[:] = MI['sleeve_fabric']
    return m

def _box(c, ax, ay, az, hx, hy, hz, bev=0.8):
    """A slab with its top edges pulled in by bev (a simple chamfer): 8 corners, 12 outward triangles."""
    pts = np.array([c + sx * (hx - (bev if sz > 0 else 0)) * ax + sy * (hy - (bev if sz > 0 else 0)) * ay + sz * hz * az for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)])
    F = np.array([(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)], np.int32)
    if np.dot(np.cross(ax, ay), az) < 0: F = F[:, ::-1].copy()
    return pts, F

def detail_parts(hand):
    """Raised parts, each rigid to one bone: name -> dict(V, F, bone, mat).  Canonical left hand, rest pose, mm."""
    g = P['glove']; wh = P['wrist_half']; X, Y, Z = np.eye(3); out = {}
    # closure strap across the back of the wrist with a plain pull tab (R1: C3-D4).  No lettering: placeholder panel.
    V, F = _box(np.array([-4.0, -9.0, wh[1] + 2.4 + 1.0]), X, Y, Z, 19.0, 8.0, 1.3); out['cuff_strap'] = dict(V=V, F=F, bone='hand', mat='glove_tab')
    V, F = _box(np.array([-24.5, -9.0, wh[1] + 2.4 + 0.2]), unit((1, 0, 0.45)), Y, unit((-0.45, 0, 1)), 5.0, 6.0, 1.0); out['cuff_pull_tab'] = dict(V=V, F=F, bone='hand', mat='glove_tab')
    V, F = _box(np.array([-4.0, -9.0, wh[1] + 2.4 + 2.4]), X, Y, Z, 11.0, 5.0, 0.35, bev=0.3); out['cuff_placeholder_panel'] = dict(V=V, F=F, bone='hand', mat='glove_flex_rib')
    # palm reinforcement patch (heel of the hand) and a knuckle bar: low raised slabs
    V, F = _box(np.array([-22.0, 24.0, -P['thick_palmar'] - g - 3.2]), X, Y, Z, 15.0, 14.0, 1.0); out['palm_heel_patch'] = dict(V=V, F=F, bone='hand', mat='glove_palm_synthetic_leather')
    out['palm_heel_patch']['pad_shift'] = hand.pad_fields(np.array([[-22.0, 24.0, -P['thick_palmar'] - g - 3.2]]), 'palm')[:, 0, :]      # CR-2: the patch rides the hypothenar pad under it
    # CR-2: a ribbed pad over each big knuckle (R1-F05 shows it on the index knuckle; carried to the other three by inference),
    # four ridges across the finger, each rigid to its own metacarpal just behind the joint so the joint itself stays free
    for f in FING:
        m = hand.J[f + '_01'][1]; o, Xf, Yf, Zf = m[:3, 3], m[:3, 0], m[:3, 1], m[:3, 2]; top = 11.5 + P['knuckle']['mcp'] + g
        for i in range(4):
            c = o - Yf * (3.0 + i * RIB_PITCH) + Zf * (top - 0.55 * i - 0.2)
            V, F = _box(c, Xf, Yf, Zf, 7.6 - 0.3 * i, 1.05, 0.75, bev=0.45); out['knuckle_rib_%s_%d' % (f, i + 1)] = dict(V=V, F=F, bone=f + '_meta', mat='glove_flex_rib')
    return out
def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
