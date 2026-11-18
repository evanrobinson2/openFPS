"""Gloved hand: the numbers, the skeleton, the glove surface and the skinning (numpy only, no bpy).

Canonical frame = a LEFT hand, flat, palm down: X radial (thumb side), Y distal, Z dorsal, origin at the wrist joint
centre (head of the capitate), millimetres.  The right hand is the mirror image (x -> -x).

Every number is tagged with its source key (SRC).  notes/NOTES.md lists the inferences and what was not re-read.
"""
import math
import numpy as np

# ------------------------------------------------------------------ sources
SRC = {
    'A': 'ANSUR II male working database (Gordon et al. 2014, NATICK/TR-15/007), n = 4,082; mean and percentiles '
         'recomputed on 2026-11-17 from the public CSV (ANSUR_II_MALE_Public.csv, Penn State OpenLab mirror)',
    'B': 'Buryanov & Kotiuk 2010, Int. J. Morphol. 28(3):755-758, Table I (X-ray, 66 adults, both sexes); values '
         'carried over from the paused build, table not re-read this session (the publisher blocked the request)',
    'H': 'Hsiao, Whitestone, Kau & Hildreth 2015, Human Factors 57(8):1359-1377, firefighter hand anthropometry, men; '
         'values carried over from the paused build, table not re-read this session',
    'BA': 'Bain, Polites, Higgs, Heptinstall & McGrath 2015, J Hand Surg Eur 40(4):406-411: functional range 19-71 / '
          '23-87 / 10-64 deg at MCP / PIP / DIP, being 48 / 59 / 60 % of the active range (abstract, read this session); '
          'the active-range end points -19..90, -7..101, -6..84 are recalled and agree with those percentages',
    'HU': 'Hume, Gellman, McKellop & Brumfield 1990, J Hand Surg Am 15(2):240-243 (citation and functional averages '
          'confirmed this session; thumb MP 0..56 and IP -5..73 active range recalled, not re-read)',
    'CO': 'Cooney, Lucca, Chao & Linscheid 1981, J Bone Joint Surg Am 63(9):1371-1381, trapeziometacarpal joint: '
          'flexion-extension 53, abduction-adduction 42, axial rotation 17 deg total (citation confirmed; values recalled)',
    'AA': 'American Academy of Orthopaedic Surgeons 1965, Joint Motion: Method of Measuring and Recording (wrist 80 '
          'flexion / 70 extension / 20 radial / 30 ulnar, forearm 80 / 80, elbow 0..150; recalled, not re-read)',
    'K': 'Kapandji, The Physiology of the Joints vol. 1: finger MCP abduction-adduction 20-30 deg each way (recalled)',
    'RG': 'Rijpkema & Girard 1991, Computer Graphics 25(4):339-348: DIP flexion is about 2/3 of PIP flexion (recalled)',
    'I': 'inference (no measurement found); see notes/NOTES.md',
}

# ------------------------------------------------------------------ measured dimensions (mm)
ANSUR = dict(  # name: (mean, sd, p5, p50, p95)
    hand_length=(193.3, 9.9, 177, 193, 210), hand_breadth=(88.3, 4.4, 81, 88, 96),
    hand_circumference=(212.3, 10.2, 195, 212, 230), palm_length=(116.5, 6.2, 107, 116, 127),
    wrist_circumference=(175.9, 9.0, 162, 176, 191), radiale_stylion=(267.9, 15.4, 244, 267, 295),
    acromion_radiale=(335.2, 17.5, 307, 335, 365), forearm_circ_flexed=(310.1, 22.0, 275, 310, 348),
    biacromial=(415.7, 19.2, 384, 415, 447))
BURY = dict(  # soft tissue at the tip, distal, middle, proximal phalanx, metacarpal (B)
    thumb=(5.67, 21.67, None, 31.57, 46.22), index=(3.84, 15.82, 22.38, 39.78, 68.12),
    middle=(3.95, 17.40, 26.33, 44.63, 64.60), ring=(3.95, 17.30, 25.65, 41.37, 58.00),
    little=(3.73, 15.96, 18.11, 32.74, 53.69))
HSIAO_BREADTH = dict(thumb=23.6, index=22.1, middle=22.0, ring=21.3, little=19.3)   # at the PIP joint (thumb: IP) (H)
HSIAO_LENGTH = dict(thumb=69.9, index=75.2, middle=83.3, ring=79.1, little=64.3)    # crease to tip (H); check only
FING = ('index', 'middle', 'ring', 'little')

# the size of this hand: the ANSUR II male mean (the 50th percentile is within 0.3 mm of it for every dimension used)
SIZE = dict(percentile=50, length=1.0, breadth=1.0)
def set_size(percentile):
    """Scale lengths by the ANSUR II hand-length percentile and breadths by the hand-breadth percentile (5, 50 or 95)."""
    i = {5: 2, 50: None, 95: 4}[percentile]
    SIZE.update(percentile=percentile, length=1.0 if i is None else ANSUR['hand_length'][i] / ANSUR['hand_length'][0],
                breadth=1.0 if i is None else ANSUR['hand_breadth'][i] / ANSUR['hand_breadth'][0])

P = dict(
    bury_scale=1.04,                   # I: the mixed-sex X-ray sample scaled so the middle ray plus a 30 mm carpus gives the ANSUR II male hand length
    stylion_y=-8.0,                    # I: stylion lies 8 mm proximal of the wrist joint centre
    glove=1.2,                         # I: glove shell over the skin (knit back / 0.8 mm synthetic leather palm + lining)
    glove_tip=1.5,                     # I: extra length at the fingertips (seam allowance)
    mcp_x=dict(index=21.0, middle=0.0, ring=-20.0, little=-39.0),      # I: MCP centres across the 88.3 mm breadth (A)
    mcp_dy=dict(index=-2.3, middle=0.0, ring=-6.8, little=-15.8),      # I: metacarpal-head arc relative to MCP III
    mcp_z=dict(index=-1.0, middle=0.0, ring=-1.5, little=-4.0),        # I: transverse metacarpal arch
    rest_abd=dict(index=6.0, middle=0.0, ring=-5.0, little=-11.0),     # I: rest spread (deg, + = radial), the neutral of MCP abduction
    depth_pip=0.90, depth_dip=0.80, dip_breadth=0.87,                  # I: depth / breadth ratios (order of Garrett 1971, not re-read)
    dorsal_share=0.42,                 # I: share of a finger's depth that lies dorsal of the bone axis
    thumb_cmc=(24.0, 18.0, -12.0),     # I: trapeziometacarpal joint centre (the trapezium sits about 20 mm distal and 25 mm radial of the wrist centre)
    thumb_dir=(0.60, 0.72, -0.35),     # I: rest direction of the thumb metacarpal (relaxed, mid-range)
    thumb_dorsal=(0.80, -0.25, 0.55),  # I: rest direction of the thumbnail normal
    thick_dorsal=12.0, thick_palmar=17.5,   # I: at the metacarpal heads (29.5 mm thick), set so the circumference matches A
    wrist_half=(30.8, 21.4),           # I: wrist half-breadth and half-depth, set so the circumference matches A
    palm_expo=3.8,                     # I: superellipse exponent of the palm's section at the knuckles (2 = ellipse), set so the circumference matches A
    web_offset=19.2,                   # I: the finger web / proximal digital crease lies this far distal of the MCP joint centre
    cuff_len=42.0, sleeve_len=210.0,   # I: glove cuff past the wrist; forearm sleeve shown
)

def seg(f):
    """Bone lengths (mm): metacarpal, proximal, middle, distal, soft tip."""
    t, d, m, p, mc = BURY[f]; s = P['bury_scale'] * SIZE['length']
    return dict(mc=mc * s, pp=p * s, mp=(m * s if m else 0.0), dp=d * s, tip=t * s)
def breadth(f): return HSIAO_BREADTH[f] * SIZE['breadth']
def mcp3_y(): return ANSUR['hand_length'][0] * SIZE['length'] + P['stylion_y'] - sum(seg('middle')[k] for k in ('pp', 'mp', 'dp', 'tip'))
def finger_len(f):
    s = seg(f); return s['pp'] + s['mp'] + s['dp'] + s['tip'] + P['glove_tip']

# ------------------------------------------------------------------ joint limits, degrees (flexion +, extension -)
LIMITS = dict(   # joint: (min, max, source key, note)
    mcp_flex=(-19, 90, 'BA', 'active range'), pip_flex=(-7, 101, 'BA', 'active range'), dip_flex=(-6, 84, 'BA', 'active range'),
    mcp_abd=(-20, 20, 'K', 'about the rest spread; the lower figure of 20-30'),
    thumb_cmc_flex=(-26.5, 26.5, 'CO', 'half of 53 each way from the relaxed mid-range rest (I)'),
    thumb_cmc_abd=(-21, 21, 'CO', 'half of 42 each way from the relaxed mid-range rest (I)'),
    thumb_cmc_rot=(-8.5, 8.5, 'CO', 'half of 17 each way'),
    thumb_mcp_flex=(0, 56, 'HU', 'active range'), thumb_ip_flex=(-5, 73, 'HU', 'active range'),
    mc4_flex=(0, 10, 'I', 'ring carpometacarpal, about 10 deg'), mc5_flex=(0, 20, 'I', 'little carpometacarpal, about 20 deg'),
    wrist_flex=(-70, 80, 'AA', 'extension 70, flexion 80'), wrist_dev=(-30, 20, 'AA', 'ulnar 30 (-), radial 20 (+)'),
    pronation=(-80, 80, 'AA', 'supination 80 (-), pronation 80 (+) from the thumb-up neutral'),
    elbow_flex=(0, 150, 'AA', 'extension 0, flexion 150'))
ANGLES = [f + '_' + k for f in FING for k in ('mcp_flex', 'mcp_abd', 'pip_flex', 'dip_flex')] + \
         ['thumb_cmc_flex', 'thumb_cmc_abd', 'thumb_cmc_rot', 'thumb_mcp_flex', 'thumb_ip_flex', 'mc4_flex', 'mc5_flex']
def limit_of(name):
    k = name if name in LIMITS else name.split('_', 1)[1]
    return LIMITS[k][0], LIMITS[k][1]
LO = np.array([limit_of(a)[0] for a in ANGLES], float); HI = np.array([limit_of(a)[1] for a in ANGLES], float)

# ------------------------------------------------------------------ small maths
def rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)
def ry(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)
def rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)
def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def M4(R=None, t=None):
    m = np.eye(4)
    if R is not None: m[:3, :3] = R
    if t is not None: m[:3, 3] = t
    return m
def frame(origin, y, z):
    """4x4 with Y along y, Z as close to z as possible, X = Y x Z (right-handed)."""
    y = unit(y); z = unit(np.asarray(z, float) - np.dot(z, y) * y); x = np.cross(y, z)
    m = np.eye(4); m[:3, 0] = x; m[:3, 1] = y; m[:3, 2] = z; m[:3, 3] = origin; return m
def rotvec(v):
    v = np.asarray(v, float); a = np.linalg.norm(v)
    if a < 1e-12: return np.eye(3)
    x, y, z = v / a; c, s = math.cos(a), math.sin(a); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s], [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])
def to_rotvec(R):
    a = math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2)))
    if a < 1e-9: return np.zeros(3)
    if abs(a - math.pi) < 1e-6:
        w, V = np.linalg.eigh((R + R.T) / 2); return V[:, np.argmax(w)] * a
    return np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * math.sin(a)) * a
def smooth(t): t = np.clip(t, 0.0, 1.0); return t * t * (3 - 2 * t)
D2R = math.pi / 180
MIRROR = np.diag([-1.0, 1.0, 1.0, 1.0])

# ------------------------------------------------------------------ skeleton (canonical left hand)
ORDER = ['forearm', 'hand'] + [f + s for f in FING for s in ('_meta', '_01', '_02', '_03')] + ['thumb_01', 'thumb_02', 'thumb_03']
BI = {n: i for i, n in enumerate(ORDER)}
def canonical_joints():
    """name -> (parent, 4x4 rest frame in the canonical frame, length mm).  Frames: Y distal along the bone, Z dorsal, X = Y x Z."""
    J = {}; up = np.array([0, 0, 1.0]); L = ANSUR['radiale_stylion'][0]; m3 = mcp3_y()
    J['forearm'] = (None, frame((0, -L, 0), (0, 1, 0), up), L)
    J['hand'] = ('forearm', frame((0, 0, 0), (0, 1, 0), up), m3)
    for f in FING:
        s = seg(f); m = np.array([P['mcp_x'][f] * SIZE['breadth'], m3 + P['mcp_dy'][f] * SIZE['length'], P['mcp_z'][f]])
        a = P['rest_abd'][f] * D2R; d = np.array([math.sin(a), math.cos(a), 0.0])
        base = np.array([m[0] * 0.55, m[1] - s['mc'], m[2] - 2.0])                    # I: metacarpal bases converge on the carpus
        if f == 'middle': base = np.array([0.0, m[1] - s['mc'], 0.0])
        J[f + '_meta'] = ('hand', frame(base, m - base, up), np.linalg.norm(m - base))
        J[f + '_01'] = (f + '_meta', frame(m, d, up), s['pp'])
        J[f + '_02'] = (f + '_01', frame(m + d * s['pp'], d, up), s['mp'])
        J[f + '_03'] = (f + '_02', frame(m + d * (s['pp'] + s['mp']), d, up), s['dp'] + s['tip'] + P['glove_tip'])
    s = seg('thumb'); c = np.array(P['thumb_cmc']); d = unit(P['thumb_dir']); z = np.array(P['thumb_dorsal'])
    J['thumb_01'] = ('hand', frame(c, d, z), s['mc'])
    J['thumb_02'] = ('thumb_01', frame(c + d * s['mc'], d, z), s['pp'])
    J['thumb_03'] = ('thumb_02', frame(c + d * (s['mc'] + s['pp']), d, z), s['dp'] + s['tip'] + P['glove_tip'])
    return J

def local_rotations(q):
    """q: dict angle name -> degrees.  3x3 local rotation of each bone in its own rest frame (canonical left hand)."""
    R = {}
    for f in FING:
        R[f + '_01'] = rz(-q[f + '_mcp_abd'] * D2R) @ rx(-q[f + '_mcp_flex'] * D2R)      # abduction in the palm plane, then flexion
        R[f + '_02'] = rx(-q[f + '_pip_flex'] * D2R); R[f + '_03'] = rx(-q[f + '_dip_flex'] * D2R)
    R['ring_meta'] = rx(-q['mc4_flex'] * D2R); R['little_meta'] = rx(-q['mc5_flex'] * D2R)
    R['thumb_01'] = rz(q['thumb_cmc_abd'] * D2R) @ ry(q['thumb_cmc_rot'] * D2R) @ rx(-q['thumb_cmc_flex'] * D2R)
    R['thumb_02'] = rx(-q['thumb_mcp_flex'] * D2R); R['thumb_03'] = rx(-q['thumb_ip_flex'] * D2R)
    return R
def qdict(vec): return dict(zip(ANGLES, np.asarray(vec, float)))
def qvec(q): return np.array([q[a] for a in ANGLES], float)

# ------------------------------------------------------------------ the glove surface: closed shells swept along the bones
NSEG = 20
def _tube(path, X, Z, hb, dz, dp, expo=2.0, cap0=True, cap1=True):
    """Closed tube: rings of NSEG vertices at path[i] with half-breadth hb along X, half-depth dz dorsal (+Z) and dp palmar."""
    n = len(path); th = np.arange(NSEG) * 2 * math.pi / NSEG; c, s = np.cos(th), np.sin(th)
    e = 2.0 / expo; cc = np.sign(c) * np.abs(c) ** e; ss = np.sign(s) * np.abs(s) ** e
    V = []
    for i in range(n):
        dep = np.where(ss >= 0, dz[i], dp[i])
        V.append(path[i][None] + hb[i] * cc[:, None] * X[i][None] + (dep * ss)[:, None] * Z[i][None])
    V = np.concatenate(V); F = []
    for i in range(n - 1):
        for j in range(NSEG):
            a, b = i * NSEG + j, i * NSEG + (j + 1) % NSEG; F += [(a, b, b + NSEG), (a, b + NSEG, a + NSEG)]
    ring = np.repeat(np.arange(n), NSEG); ang = np.tile(th, n)
    if cap0:
        V = np.vstack([V, path[0]]); k = len(V) - 1; F += [(k, (j + 1) % NSEG, j) for j in range(NSEG)]; ring = np.r_[ring, 0]; ang = np.r_[ang, 0]
    if cap1:
        V = np.vstack([V, path[-1]]); k = len(V) - 1; o = (n - 1) * NSEG; F += [(k, o + j, o + (j + 1) % NSEG) for j in range(NSEG)]; ring = np.r_[ring, n - 1]; ang = np.r_[ang, 0]
    return V, np.array(F, np.int32), ring, ang

def _stations(knots, step=2.2):
    """knots: [(s, hb, dz, dp)] -> dense stations by piecewise-cubic (smoothstep) interpolation."""
    out = []
    for (s0, *a), (s1, *b) in zip(knots, knots[1:]):
        n = max(1, int(round((s1 - s0) / step)))
        for k in range(n):
            t = k / n; u = t * t * (3 - 2 * t); out.append([s0 + (s1 - s0) * t] + [a[i] + (b[i] - a[i]) * u for i in range(3)])
    out.append(list(knots[-1])); return np.array(out)
def _round_tip(st, L, r):
    """Append a quarter-ellipse closing to the end of stations st, ending at s = L with a tip radius r along the axis."""
    last = st[-1]; out = [st]
    for ph in np.linspace(0, math.pi / 2, 7)[1:-1]:
        out.append(np.array([[L - r + r * math.sin(ph), last[1] * math.cos(ph), last[2] * math.cos(ph), last[3] * math.cos(ph)]]))
    out.append(np.array([[L - 0.25, last[1] * 0.12, last[2] * 0.12, last[3] * 0.12]]))
    return np.vstack(out)
def _blend(s, joints, half):
    """Weights along a chain: joints = [s_j], bones = len(joints) + 1; smoothstep over +-half[j] about each joint."""
    # make a partition of unity: bone k carries prod(t_j, j<k) * (1 - t_k)
    T = [smooth((s - (sj - half[j])) / (2 * half[j])) for j, sj in enumerate(joints)]
    w = np.zeros((len(s), len(joints) + 1)); acc = np.ones(len(s))
    for k in range(len(joints) + 1):
        w[:, k] = acc * ((1 - T[k]) if k < len(joints) else 1.0)
        if k < len(joints): acc = acc * T[k]
    return w

class Hand:
    """The rest-pose glove (canonical left hand): shells, skin weights, landmarks.  All mm."""
    def __init__(self):
        self.J = canonical_joints(); J = self.J; g = P['glove']; self.shells = {}; self.landmarks = {}
        self.rest = np.array([J[n][1] for n in ORDER]); self.rest_inv = np.linalg.inv(self.rest)
        self.parent = [BI[J[n][0]] if J[n][0] else -1 for n in ORDER]
        self.local = np.array([np.eye(4) if p < 0 else self.rest_inv[p] @ self.rest[i] for i, p in enumerate(self.parent)])
        ds = P['dorsal_share']
        def lm(name, bone, p): self.landmarks[name] = (bone, np.asarray(p, float))
        # ---- fingers
        for f in FING:
            s = seg(f); B = breadth(f) / 2 + g; L = finger_len(f) + g
            m = J[f + '_01'][1]; o, X, Y, Z = m[:3, 3], m[:3, 0], m[:3, 1], m[:3, 2]
            D_p, D_d, D_t = 2 * B * P['depth_pip'], 2 * B * P['dip_breadth'] * P['depth_dip'], 2 * B * 0.66
            s1, s2 = s['pp'], s['pp'] + s['mp']
            kn = [(-13.0, B * 0.70, 8.0, 9.0), (-6.0, B * 1.00, 10.5, 12.5), (0.0, B * 1.03, 11.5, 13.0),
                  (s1 * 0.5, B * 0.95, D_p * 1.02 * ds, D_p * 1.06 * (1 - ds)), (s1, B, D_p * ds * 1.05, D_p * (1 - ds) * 0.97),
                  ((s1 + s2) / 2, B * 0.92, D_p * 0.93 * ds, D_p * 0.97 * (1 - ds)), (s2, B * P['dip_breadth'], D_d * ds * 1.05, D_d * (1 - ds)),
                  (L - 0.50 * 2 * B, B * 0.84, D_t * 0.40, D_t * 0.60)]
            st = _round_tip(_stations(kn), L, 0.50 * 2 * B * 0.9)
            path = o[None] + st[:, :1] * Y[None]
            V, F, ring, ang = _tube(path, np.tile(X, (len(st), 1)), np.tile(Z, (len(st), 1)), st[:, 1], st[:, 2], st[:, 3], expo=2.3)
            sv = st[ring, 0]; hw = [0.50 * 2 * B, 0.52 * D_p, 0.52 * D_d]
            wl = _blend(sv, [0.0, s1, s2], hw); W = np.zeros((len(V), len(ORDER)))
            base = f + '_meta' if f in ('ring', 'little') else 'hand'
            for k, bn in enumerate([base, f + '_01', f + '_02', f + '_03']): W[:, BI[bn]] += wl[:, k]
            self.shells['finger_' + f] = dict(V=V, F=F, W=W, s=sv, ang=ang, ring=ring, kind='finger', L=L, joints=(0.0, s1, s2), B=B)
            # landmarks (rigid to one bone)
            lm(f + '_tip', f + '_03', o + Y * L)
            lm(f + '_pad', f + '_03', o + Y * (L - 0.50 * 2 * B) - Z * D_t * 0.60)
            lm(f + '_pad_mid', f + '_02', o + Y * (s1 + s2) / 2 - Z * D_p * 0.97 * (1 - ds))
            lm(f + '_pad_prox', f + '_01', o + Y * s1 * 0.5 - Z * D_p * 1.06 * (1 - ds))
            lm(f + '_mcp_palmar', base, o - Z * 13.0 - Y * 4.0)
            lm(f + '_mcp_dorsal', base, o + Z * 11.5)
            lm(f + '_pip_dorsal', f + '_01', o + Y * s1 + Z * D_p * ds * 1.05)
            lm(f + '_dip_dorsal', f + '_02', o + Y * s2 + Z * D_d * ds * 1.05)
            lm(f + '_side_radial', f + '_02', o + Y * (s1 + s2) / 2 + X * B * 0.92)
        # ---- thumb (the metacarpal carries the thenar eminence)
        s = seg('thumb'); B = breadth('thumb') / 2 + g; m = J['thumb_01'][1]; o, X, Y, Z = m[:3, 3], m[:3, 0], m[:3, 1], m[:3, 2]
        s1, s2 = s['mc'], s['mc'] + s['pp']; L = s2 + s['dp'] + s['tip'] + P['glove_tip'] + g
        kn = [(-9.0, 9.0, 8.0, 9.0), (0.0, 13.5, 11.0, 13.5), (s1 * 0.45, 14.5, 11.5, 17.0), (s1 * 0.8, 13.2, 11.0, 14.0), (s1, B * 1.03, 10.2, 11.2),
              ((s1 + s2) / 2, B * 0.94, 9.2, 10.4), (s2, B, 9.2, 10.2), (L - 0.52 * 2 * B, B * 0.92, 7.4, 9.6)]
        st = _round_tip(_stations(kn), L, 0.52 * 2 * B * 0.9); path = o[None] + st[:, :1] * Y[None]
        V, F, ring, ang = _tube(path, np.tile(X, (len(st), 1)), np.tile(Z, (len(st), 1)), st[:, 1], st[:, 2], st[:, 3], expo=2.2)
        sv = st[ring, 0]; wl = _blend(sv, [6.0, s1, s2], [11.0, 9.5, 9.0]); W = np.zeros((len(V), len(ORDER)))
        for k, bn in enumerate(['hand', 'thumb_01', 'thumb_02', 'thumb_03']): W[:, BI[bn]] += wl[:, k]
        self.shells['thumb'] = dict(V=V, F=F, W=W, s=sv, ang=ang, ring=ring, kind='thumb', L=L, joints=(0.0, s1, s2), B=B)
        lm('thumb_tip', 'thumb_03', o + Y * L); lm('thumb_pad', 'thumb_03', o + Y * (L - 0.52 * 2 * B) - Z * 9.6)
        lm('thumb_pad_prox', 'thumb_02', o + Y * (s1 + s2) / 2 - Z * 10.4); lm('thenar', 'thumb_01', o + Y * s1 * 0.45 - Z * 17.0)
        lm('thumb_mcp_dorsal', 'thumb_01', o + Y * s1 + Z * 10.2); lm('thumb_ip_dorsal', 'thumb_02', o + Y * s2 + Z * 9.2)
        lm('thumb_side_ulnar', 'thumb_02', o + Y * (s1 + s2) / 2 - X * B * 0.94)
        # ---- palm: lofted from the wrist to the oblique line of the metacarpal heads
        m3 = mcp3_y(); wh = P['wrist_half']; hbm = ANSUR['hand_breadth'][0] * SIZE['breadth'] / 2 + g
        xs = np.array([P['mcp_x'][f] * SIZE['breadth'] for f in FING[::-1]]); dys = np.array([P['mcp_dy'][f] * SIZE['length'] for f in FING[::-1]])
        us = np.r_[np.linspace(0, 0.93, 26), 0.955, 0.975, 0.99, 1.0]; th = np.arange(2 * NSEG) * math.pi / NSEG
        V = []; uu = []
        for u in us:
            hw = wh[0] + g + (hbm - wh[0] - g) * smooth(u / 0.72); cx = -1.0 + (-9.0 + 1.0) * smooth(u / 0.8)
            zt = wh[1] + g + (P['thick_dorsal'] + g - wh[1] - g) * smooth(u / 0.75); zp = wh[1] + g + (P['thick_palmar'] + g - wh[1] - g) * smooth(u / 0.85)
            k = 1.0 if u < 0.93 else math.sqrt(max(0.0, 1 - ((u - 0.93) / 0.075) ** 2)) * 0.92 + 0.08
            c, sn = np.cos(th), np.sin(th); e = 2.0 / (2.6 + (P['palm_expo'] - 2.6) * smooth(u / 0.6)); cc = np.sign(c) * np.abs(c) ** e; ss = np.sign(sn) * np.abs(sn) ** e
            x = cx + hw * cc * (0.985 + 0.015 * k); z = np.where(ss >= 0, zt, zp) * ss * k
            hyp = np.exp(-((x + 30) / 14.0) ** 2) * np.exp(-((u - 0.30) / 0.30) ** 2) * 4.5      # hypothenar eminence (I)
            z = np.where(ss < 0, z - hyp * k, z) - 0.0022 * (x + 9.0) ** 2 * u                  # transverse arch (I)
            y = -7.0 + u * (m3 + 5.0 + np.interp(x, xs, dys) + 7.0)
            V.append(np.c_[x, y, z]); uu.append(np.full(len(th), u))
        n = len(us); R = 2 * NSEG; V = np.concatenate(V); uu = np.concatenate(uu); F = []
        for i in range(n - 1):
            for j in range(R):
                a, b = i * R + j, i * R + (j + 1) % R; F += [(a, b, b + R), (a, b + R, a + R)]
        V = np.vstack([V, V[:R].mean(0), V[-R:].mean(0)]); uu = np.r_[uu, 0, 1]
        F += [(len(V) - 2, (j + 1) % R, j) for j in range(R)]; o2 = (n - 1) * R; F += [(len(V) - 1, o2 + j, o2 + (j + 1) % R) for j in range(R)]
        W = np.zeros((len(V), len(ORDER))); tr = smooth((-10.0 - V[:, 0]) / 12.0) * smooth(uu / 0.6); tl = smooth((-29.0 - V[:, 0]) / 10.0) * smooth(uu / 0.6)
        W[:, BI['little_meta']] = tl; W[:, BI['ring_meta']] = tr - tl * tr; W[:, BI['hand']] = 1 - W.sum(1)
        self.shells['palm'] = dict(V=V, F=np.array(F, np.int32), W=W, s=uu, ang=np.zeros(len(V)), ring=np.r_[np.repeat(np.arange(n), R), 0, n - 1], kind='palm')
        lm('palm_centre', 'hand', (-6.0, m3 * 0.55, -P['thick_palmar'] - g + 1.0)); lm('hypothenar', 'hand', (-32.0, m3 * 0.30, -P['thick_palmar'] - g - 4.0))
        lm('palm_heel', 'hand', (-6.0, 8.0, -wh[1] - g)); lm('palm_distal', 'hand', (-8.0, m3 * 0.86, -P['thick_palmar'] - g))
        lm('hand_back', 'hand', (-6.0, m3 * 0.5, 15.0)); lm('wrist_dorsal', 'hand', (0, 0, wh[1] + g)); lm('wrist_palmar', 'hand', (0, 0, -wh[1] - g))
        lm('wrist_radial', 'hand', (wh[0] + g, 0, 0)); lm('wrist_ulnar', 'hand', (-wh[0] - g, 0, 0)); lm('wrist', 'hand', (0, 0, 0))
        # ---- web between the thumb and the index metacarpal
        mt = J['thumb_01'][1]; a = mt[:3, 3] + mt[:3, 1] * seg('thumb')['mc'] * 0.80 - mt[:3, 0] * 4.0
        mi = J['index_meta'][1]; b = mi[:3, 3] + mi[:3, 1] * J['index_meta'][2] * 0.78 + np.array([8.0, 0, -5.0])
        t = np.linspace(0, 1, 9); path = a[None] * (1 - t[:, None]) + b[None] * t[:, None] + np.array([0.35, 0.55, 0.0])[None] * (np.sin(t * math.pi) * 6.0)[:, None]
        along = unit(b - a); wide = unit(mt[:3, 1] + mi[:3, 1]); wide = unit(wide - np.dot(wide, along) * along); thin = np.cross(along, wide)
        hb = 15.0 - 3.0 * np.sin(t * math.pi); hd = 6.0 + g + 0 * t
        V, F, ring, ang = _tube(path, np.tile(wide, (9, 1)), np.tile(thin, (9, 1)), hb, hd, hd, expo=2.0)
        W = np.zeros((len(V), len(ORDER))); tt = smooth(t[ring]); W[:, BI['thumb_01']] = 1 - tt; W[:, BI['hand']] = tt
        self.shells['web'] = dict(V=V, F=F, W=W, s=t[ring], ang=ang, ring=ring, kind='web')
        lm('web', 'hand', path[5] + wide * 13.0)
        # ---- cuff (glove) and sleeve (forearm); the forearm follows the hand in pronation, the wrist bends over y -26..+6
        for name, y0, y1, grow in (('cuff', 5.0, -P['cuff_len'], 2.6), ('sleeve', -P['cuff_len'] + 14.0, -P['sleeve_len'], 5.0)):
            ys = np.linspace(y0, y1, max(6, int(abs(y1 - y0) / 4.0))); fr = np.clip(-ys / 200.0, 0, 1)
            hb = wh[0] + grow + 15.0 * fr ** 0.8; hd = wh[1] + grow + 20.0 * fr ** 0.8
            path = np.c_[-1.0 + 0 * ys, ys, 0 * ys]
            V, F, ring, ang = _tube(path, np.tile([1.0, 0, 0], (len(ys), 1)), np.tile([0, 0, 1.0], (len(ys), 1)), hb, hd, hd, expo=2.3)
            W = np.zeros((len(V), len(ORDER))); tt = smooth((V[:, 1] + 26.0) / 32.0); W[:, BI['hand']] = tt; W[:, BI['forearm']] = 1 - tt
            self.shells[name] = dict(V=V, F=F, W=W, s=V[:, 1].copy(), ang=ang, ring=ring, kind=name)
        for sh in self.shells.values():              # outward-facing triangles (positive signed volume)
            a, b, c = (sh['V'][sh['F'][:, k]] for k in range(3))
            if np.einsum('ij,ij->i', a, np.cross(b, c)).sum() < 0: sh['F'] = sh['F'][:, ::-1].copy()
        self.names = list(self.shells)
        self.lm_names = list(self.landmarks); self.lm_bone = np.array([BI[self.landmarks[n][0]] for n in self.lm_names])
        self.lm_pos = np.array([self.landmarks[n][1] for n in self.lm_names])

    # -------------------------------------------------------------- kinematics
    def fk(self, q, H, F=None):
        """World 4x4 of every bone.  q: angle vector (deg, order ANGLES), H: hand world matrix, F: forearm world matrix
        (default: rigidly behind the hand, i.e. a neutral wrist)."""
        R = local_rotations(qdict(q)); Wd = np.zeros((len(ORDER), 4, 4)); Wd[BI['hand']] = H
        Wd[BI['forearm']] = F if F is not None else H @ self.rest[BI['forearm']]
        for i, n in enumerate(ORDER):
            if i < 2: continue
            Wd[i] = Wd[self.parent[i]] @ self.local[i] @ M4(R.get(n))
        return Wd
    def skin_mats(self, Wd): return Wd @ self.rest_inv
    def pose_shell(self, name, S):
        sh = self.shells[name]; Vh = np.c_[sh['V'], np.ones(len(sh['V']))]
        out = np.einsum('vb,bij,vj->vi', sh['W'], S[:, :3, :], Vh); return out
    def pose_points(self, P_, bones, S):
        return np.einsum('nij,nj->ni', S[bones][:, :3, :3], P_) + S[bones][:, :3, 3]
    def pose_landmarks(self, S): return dict(zip(self.lm_names, self.pose_points(self.lm_pos, self.lm_bone, S)))

def mirror_mats(Wd):
    """Bone or skin matrices of the left hand -> the right hand (x -> -x on both sides keeps them proper rotations)."""
    return MIRROR @ Wd @ MIRROR

# ------------------------------------------------------------------ arm: elbow from a two-bone solve, wrist angles from a swing / twist split
def arm_ik(shoulder, wrist, l1, l2, pole):
    d = wrist - shoulder; D = np.linalg.norm(d); Dc = min(D, (l1 + l2) * 0.999); u = d / D
    a = (l1 * l1 - l2 * l2 + Dc * Dc) / (2 * Dc); h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = pole - np.dot(pole, u) * u; p = p / np.linalg.norm(p)
    return shoulder + u * a + p * h, D > (l1 + l2)
def forearm_and_wrist(H, shoulder, pole):
    """Canonical-left-hand world (mirror the world for a right hand).  Returns the forearm world matrix (it carries all
    of the twist about its own axis, as pronation) and wrist_flex, wrist_dev, pronation, elbow_flex in degrees."""
    l1, l2 = ANSUR['acromion_radiale'][0], ANSUR['radiale_stylion'][0]
    w = H[:3, 3]; e, over = arm_ik(np.asarray(shoulder, float), w, l1, l2, np.asarray(pole, float))
    y = unit(w - e)
    # swing that takes the forearm axis to the hand's Y; the forearm frame is the hand frame with that swing removed
    hy = H[:3, 1]; ax = np.cross(y, hy); sn = np.linalg.norm(ax); cs = float(np.dot(y, hy))
    swing = rotvec(ax / sn * math.atan2(sn, cs)) if sn > 1e-9 else np.eye(3)
    Rf = swing.T @ H[:3, :3]                         # same twist as the hand, axis along the forearm
    F = M4(Rf, e)
    Rw = Rf.T @ H[:3, :3]                            # wrist rotation in the forearm frame: pure swing
    v = Rw[:, 1]                                     # hand Y in forearm axes: (x radial, y distal, z dorsal)
    flex = math.degrees(math.atan2(-v[2], v[1])); dev = math.degrees(math.asin(max(-1, min(1, v[0]))))
    # pronation: the forearm's radial axis against the elbow hinge.  Neutral (thumb up) = radial axis in the arm plane, on the flexor side
    ua = unit(e - np.asarray(shoulder, float)); hinge = unit(np.cross(ua, y)) if np.linalg.norm(np.cross(ua, y)) > 1e-6 else np.array([1.0, 0, 0])
    inplane = np.cross(hinge, y)                     # in the arm plane, perpendicular to the forearm
    if np.dot(inplane, -ua) < 0: inplane = -inplane  # toward the upper arm = the flexor side
    xr = Rf[:, 0]; pron = math.degrees(math.atan2(np.dot(np.cross(inplane, xr), y), np.dot(inplane, xr)))
    elbow = 180.0 - math.degrees(math.acos(max(-1, min(1, float(np.dot(-ua, y))))))
    return F, dict(wrist_flex=flex, wrist_dev=dev, pronation=pron, elbow_flex=elbow, reach_over=bool(over))

if __name__ == '__main__':
    h = Hand()
    print('MCP3_Y', round(mcp3_y(), 2), 'carpus', round(mcp3_y() - seg('middle')['mc'] - P['stylion_y'], 2))
    for n, s in h.shells.items(): print(n, len(s['V']), 'verts', len(s['F']), 'tris', 'weights ok' if np.allclose(s['W'].sum(1), 1) else 'WEIGHTS BAD')
