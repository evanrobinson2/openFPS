"""The locally built HK416 as a signed distance field for the grip solver (numpy / scipy).

Per part: surface samples (0.5 mm) with outward normals; the part's signed distance at a grid node is the distance to
its nearest sample, signed by that sample's normal.  The rifle is the union (minimum) over parts, stored on a 1 mm grid
per moving part and read with trilinear interpolation.  It is approximate; the committed interpenetration check
(checks/penetration.py) measures against the exact triangles instead.  Asset frame, mm."""
import os, json, time, numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates, distance_transform_edt, label
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BUILD = os.path.join(HERE, 'refs-local', 'build')
REGION = np.array([[-95.0, -235.0, -275.0], [95.0, 85.0, 255.0]]); CAP = 10.0; H = 1.0
class Rifle:
    def __init__(self):
        self.z = np.load(os.path.join(BUILD, 'rifle.npz')); self.meta = json.load(open(os.path.join(BUILD, 'rifle.json')))
        self.movers = self.meta['movers']; self.sockets = {k: np.array(v) for k, v in self.meta['sockets'].items()}
        cache = os.path.join(BUILD, 'rifle_sdf.npz')
        if not os.path.exists(cache): self._build(cache)
        self._u = {}; c = np.load(cache); self.grid = {k[2:]: c[k].astype(np.float32) for k in c.files if k.startswith('g_')}; self.org = {k[2:]: c[k] for k in c.files if k.startswith('o_')}
    def _samples(self, n, rng, spacing=0.5):
        V = self.z['V_' + n].astype(float); T = self.z['T_' + n]; a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        nn = np.cross(b - a, c - a); area = np.linalg.norm(nn, axis=1) / 2; ok = area > 1e-9
        if np.einsum('ij,ij->i', a, np.cross(b, c)).sum() < 0: nn = -nn
        cnt = np.maximum(1, np.ceil(area / spacing ** 2)).astype(int) * ok; idx = np.repeat(np.arange(len(T)), cnt)
        r1 = np.sqrt(rng.random(len(idx))); r2 = rng.random(len(idx))
        pts = a[idx] * (1 - r1)[:, None] + b[idx] * (r1 * (1 - r2))[:, None] + c[idx] * (r1 * r2)[:, None]
        nr = nn[idx] / np.linalg.norm(nn[idx], axis=1)[:, None]; return pts, nr
    def _build(self, cache):
        rng = np.random.default_rng(416); t0 = time.time(); out = {}
        groups = {}
        for n, p in self.meta['parts'].items(): groups.setdefault(p['mover'] or 'static', []).append(n)
        for g, names in groups.items():
            lo = np.min([self.meta['parts'][n]['lo'] for n in names], 0) - 45.0; hi = np.max([self.meta['parts'][n]['hi'] for n in names], 0) + 45.0
            if g == 'static': lo, hi = REGION
            else: lo = np.maximum(lo, REGION[0] - 250); hi = np.minimum(hi, REGION[1] + 250)
            lo = np.floor(lo); shape = np.ceil((hi - lo) / H).astype(int) + 1; G = np.full(shape, CAP, np.float32)
            for n in names:
                p = self.meta['parts'][n]; a = np.maximum(np.floor((np.array(p['lo']) - CAP - lo) / H).astype(int), 0); b = np.minimum(np.ceil((np.array(p['hi']) + CAP - lo) / H).astype(int) + 1, shape)
                if np.any(b <= a): continue
                pts, nr = self._samples(n, rng); tree = cKDTree(pts)
                ii = np.stack(np.meshgrid(*[np.arange(a[k], b[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3); q = lo + ii * H
                d, i = tree.query(q, distance_upper_bound=CAP, workers=-1); ok = np.isfinite(d)
                sd = d[ok] * np.sign(np.einsum('ij,ij->i', q[ok] - pts[i[ok]], nr[i[ok]]) + 1e-9)
                sub = G[a[0]:b[0], a[1]:b[1], a[2]:b[2]].reshape(-1); sub2 = sub.copy(); sub2[ok] = np.minimum(sub[ok], sd); G[a[0]:b[0], a[1]:b[1], a[2]:b[2]] = sub2.reshape(b - a)
            unk = G >= CAP - 1e-3; lab, _ = label(unk); edge = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(), lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
            outside = unk & np.isin(lab, edge[edge > 0]); deep = unk & ~outside                 # far cells not connected to the border are inside
            far = distance_transform_edt(G > 1.0) * H + 1.0; G = np.where(outside, np.maximum(far, CAP), G)
            G = np.where(deep, -np.maximum(distance_transform_edt(deep) * H + CAP - 1.0, CAP), G).astype(np.float32)
            out['g_' + g] = G; out['o_' + g] = lo; print('sdf', g, shape, round(time.time() - t0, 1), 's', flush=True)
        np.savez_compressed(cache, **out)
    def motion(self, clip, frame):
        """mover -> 4x4 at an integer or fractional frame (1-based) of a rifle clip (the clip holds its last frame after it ends)."""
        D = self.z['clip_' + clip]; f = min(max(frame, 1.0), float(len(D))) - 1; i = int(np.floor(f)); j = min(i + 1, len(D) - 1); t = f - i
        return {m: D[i, k] * (1 - t) + D[j, k] * t for k, m in enumerate(self.movers) if m in self.meta['clips'][clip]['movers']}
    def _union(self, moving):
        """Static grid merged with every mover that is at rest (not in `moving`), cached per set of moving parts."""
        key = tuple(sorted(moving))
        if key not in self._u:
            G = self.grid['static'].copy(); lo = self.org['static']
            for name, g in self.grid.items():
                if name == 'static' or name in key: continue
                a = np.maximum(np.round(self.org[name] - lo).astype(int), 0); b = np.minimum(a + np.array(g.shape) - np.maximum(np.round(lo - self.org[name]).astype(int), 0), G.shape)
                o = np.maximum(np.round(lo - self.org[name]).astype(int), 0)
                if np.any(b <= a): continue
                sub = g[o[0]:o[0] + b[0] - a[0], o[1]:o[1] + b[1] - a[1], o[2]:o[2] + b[2] - a[2]]
                G[a[0]:b[0], a[1]:b[1], a[2]:b[2]] = np.minimum(G[a[0]:b[0], a[1]:b[1], a[2]:b[2]], sub)      # grids share the 1 mm lattice (origins are whole mm)
            self._u[key] = G
        return self._u[key]
    def sdf(self, Q, motion=None, mirror=False, skip=(), only=None):
        """Signed distance (mm, + outside) of points Q.  motion: mover -> 4x4 (from .motion()); skip: movers left out;
        mirror: Q is in the x-mirrored world (a right hand solved as a left)."""
        Q = np.asarray(Q, float)
        if mirror: Q = Q * [-1, 1, 1]
        moving = set(motion or ()) | set(skip); G = self._union(moving)
        c = (Q - self.org['static']) / H; best = map_coordinates(G, c.T, order=1, mode='nearest')
        hi = np.array(G.shape) - 1; best = best + np.linalg.norm(c - np.clip(c, 0, hi), axis=1) * H
        for name, M in (motion or {}).items():
            if name in skip: continue
            Mi = np.linalg.inv(M); q = Q @ Mi[:3, :3].T + Mi[:3, 3]; g = self.grid[name]
            c = (q - self.org[name]) / H; d = map_coordinates(g, c.T, order=1, mode='nearest')
            hi = np.array(g.shape) - 1; best = np.minimum(best, d + np.linalg.norm(c - np.clip(c, 0, hi), axis=1) * H)
        return best
if __name__ == '__main__':
    r = Rifle(); s = r.sockets
    print(r.sdf(np.array([s['socket_hand_right'], s['socket_hand_right'] + [14.2, 0, 0], s['socket_hand_right'] + [30, 0, 0], s['socket_hand_left'], s['socket_hand_left'] - [0, 5, 0], [0, 0, 100.0]])))
    t = time.time(); Q = np.random.default_rng(0).uniform(-60, 60, (4000, 3)); [r.sdf(Q) for _ in range(20)]; print('ms per 4000-pt query', (time.time() - t) * 50)
