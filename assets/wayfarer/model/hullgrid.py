"""The hull as a grid, plus the helpers every module uses to cut openings in it and to make parts that follow
its curve (doors, glazing, coamings, frames). Starboard half is stored; side = -1 mirrors to port."""
import math
import numpy as np
import spec
from kit import MB, vnorm, vsub, vadd, vmul, vcross

class Hull:
    def __init__(self, nr=spec.NR):
        self.st, self.P, self.N, self.rows = spec.hull_grid(nr)
        self.ni, self.nr = len(self.st), nr
        self.sarr = np.asarray(self.st)
        # tag per cell and side: 0 plate, 1 opening (cut right through), 2 waist channel, 3 bay
        self.tag = {+1: np.zeros((self.ni - 1, nr), dtype=np.int8), -1: np.zeros((self.ni - 1, nr), dtype=np.int8)}
        self.s_split, self.j_split = set(), set()
        self.openings = {}

    # ---- index helpers
    def si(self, s):
        return int(np.argmin(np.abs(self.sarr - s)))

    def row_z(self, i, z):
        return int(np.argmin(np.abs(self.P[i, :, 2] - z)))

    def row_y_belly(self, i, y):
        jm = int(np.argmax(self.P[i, :, 1]))
        return jm + int(np.argmin(np.abs(self.P[i, jm:, 1] - y)))

    def pt(self, i, j, off=0.0, side=1):
        p = self.P[i, j] + off * self.N[i, j]
        return (p[0], side * p[1], p[2])

    def nrm(self, i, j, side=1):
        n = self.N[i, j]
        return (n[0], side * n[1], n[2])

    def open(self, name, i0, i1, j0, j1, side, tag=1):
        """Mark cells [i0, i1) x [j0, j1) on a side (or 0 = both) and remember the rectangle."""
        for sd in ((1, -1) if side == 0 else (side,)):
            self.tag[sd][i0:i1, j0:j1] = tag
        self.s_split.update((i0, i1)); self.j_split.update((j0, j1))
        self.openings[name] = (i0, i1, j0, j1, side)
        return (i0, i1, j0, j1, side)

    # ---- geometry that follows the hull
    def nodes(self, i0, i1, j0, j1, off, side=1, margin=0.0):
        """Node positions of the patch at an offset, edges pulled in by margin (metres, in the surface)."""
        P = self.P[i0:i1 + 1, j0:j1 + 1] + off * self.N[i0:i1 + 1, j0:j1 + 1]
        P = P.copy()
        if margin:
            base = self.P
            def unit(v):
                l = np.linalg.norm(v, axis=-1, keepdims=True); return v / np.maximum(l, 1e-9)
            ds0 = unit(base[i0 + 1, j0:j1 + 1] - base[i0, j0:j1 + 1]); ds1 = unit(base[i1 - 1, j0:j1 + 1] - base[i1, j0:j1 + 1])
            du0 = unit(base[i0:i1 + 1, j0 + 1] - base[i0:i1 + 1, j0]); du1 = unit(base[i0:i1 + 1, j1 - 1] - base[i0:i1 + 1, j1])
            P[0] += margin * ds0; P[-1] += margin * ds1
            P[:, 0] += margin * du0; P[:, -1] += margin * du1
        if side < 0:
            P[:, :, 1] *= -1
        return P

    def sheet(self, mb, G, m, flip=False, min_area=1e-6):
        """Add a grid of points as quads. Winding gives outward normals on the starboard side when flip is False."""
        ni, nj, _ = G.shape
        idx = [[mb.v(G[a, b]) for b in range(nj)] for a in range(ni)]
        for a in range(ni - 1):
            for b in range(nj - 1):
                p0, p1, p2, p3 = G[a, b], G[a + 1, b], G[a + 1, b + 1], G[a, b + 1]
                if np.linalg.norm(np.cross(p2 - p0, p3 - p1)) < min_area:
                    continue
                q = (idx[a][b], idx[a + 1][b], idx[a + 1][b + 1], idx[a][b + 1])
                mb.f(q[::-1] if flip else q, m)
        return idx

    def skirt(self, mb, A, B, m, flip=False):
        """Walls joining the edges of two same-sized node grids A (outer) and B (inner)."""
        ni, nj, _ = A.shape
        loop = [(a, 0) for a in range(ni)] + [(ni - 1, b) for b in range(1, nj)] + [(a, nj - 1) for a in range(ni - 2, -1, -1)] + [(0, b) for b in range(nj - 2, 0, -1)]
        ia = [mb.v(A[a, b]) for a, b in loop]; ib = [mb.v(B[a, b]) for a, b in loop]
        n = len(loop)
        for k in range(n):
            k2 = (k + 1) % n
            if np.linalg.norm(A[loop[k]] - A[loop[k2]]) < 1e-5:
                continue
            q = (ia[k], ib[k], ib[k2], ia[k2])
            mb.f(q[::-1] if flip else q, m)

    def slab(self, mb, i0, i1, j0, j1, side, o_out, o_in, m_out, m_in=None, m_edge=None, margin=0.0):
        """A closed plate following the hull between two offsets: armour plates, doors, glazing."""
        A = self.nodes(i0, i1, j0, j1, o_out, side, margin); B = self.nodes(i0, i1, j0, j1, o_in, side, margin)
        fl = side < 0
        self.sheet(mb, A, m_out, flip=fl)
        self.sheet(mb, B, m_in or m_out, flip=not fl)
        self.skirt(mb, A, B, m_edge or m_out, flip=fl)
        return A, B

    def rect(self, name):
        return self.openings[name]

    def rect_centre(self, i0, i1, j0, j1, side, off=0.0):
        G = self.nodes(i0, i1, j0, j1, off, side)
        return tuple(G.reshape(-1, 3).mean(axis=0))

    def rib_s(self, mb, i, j0, j1, side, o_out, o_in, half_w, m):
        """A bar following the section at station i from row j0 to j1 (a frame, a window pillar): four faces + ends."""
        def ring(off, ds):
            return [np.array(self.pt(i, j, off, side)) + np.array((ds, 0.0, 0.0)) for j in range(j0, j1 + 1)]
        a0, a1, b0, b1 = ring(o_out, -half_w), ring(o_out, half_w), ring(o_in, -half_w), ring(o_in, half_w)
        fl = side < 0
        for (p, q) in ((a1, a0), (a0, b0), (b0, b1), (b1, a1)):
            ip = [mb.v(x) for x in p]; iq = [mb.v(x) for x in q]
            for k in range(len(p) - 1):
                if np.linalg.norm(p[k] - p[k + 1]) < 1e-5: continue
                quad = (ip[k], iq[k], iq[k + 1], ip[k + 1])
                mb.f(quad[::-1] if fl else quad, m)
        for k in (0, len(a0) - 1):
            q = mb.vs([a0[k], a1[k], b1[k], b0[k]])
            mb.f(q if ((k == 0) != fl) else q[::-1], m)

    def rib_j(self, mb, j, i0, i1, side, o_out, o_in, half_w, m):
        """A bar following row j from station i0 to i1 (a longeron, a sill or brow rail)."""
        def rail(off, k):
            out = []
            for i in range(i0, i1 + 1):
                t = self.P[i, min(j + 1, self.nr)] - self.P[i, max(j - 1, 0)]
                l = np.linalg.norm(t); t = t / l if l > 1e-6 else np.array((0.0, 1.0, 0.0))
                p = self.P[i, j] + off * self.N[i, j] + k * half_w * t
                out.append(np.array((p[0], side * p[1], p[2])))
            return out
        a0, a1, b0, b1 = rail(o_out, -1), rail(o_out, 1), rail(o_in, -1), rail(o_in, 1)
        fl = side < 0
        for (p, q) in ((a0, a1), (b0, a0), (b1, b0), (a1, b1)):
            ip = [mb.v(x) for x in p]; iq = [mb.v(x) for x in q]
            for k in range(len(p) - 1):
                quad = (ip[k], iq[k], iq[k + 1], ip[k + 1])
                mb.f(quad[::-1] if fl else quad, m)
        for k in (0, len(a0) - 1):
            q = mb.vs([a0[k], a1[k], b1[k], b0[k]])
            mb.f(q[::-1] if ((k == 0) != fl) else q, m)
