/* optic-red-dot.js : runtime for the generic 2 MOA tube red-dot sight. Credit: carpetshark.
 *
 * Self-contained (no three.js). Browser: window.OpticRedDot, then `await OpticRedDot.load('.../reddot.json')`.
 * Node: const R = require('./optic-red-dot.js'); R.init(require('./reddot.json')).
 *
 * It carries the same exact ray trace of the collimator as sim.py (pass {exact: true}) and the order-5 polynomial
 * fitted to it (the default, for per-frame use); `node test.js` checks both against the Python.
 *
 * Conventions. Eye offsets and angles are as the shooter sees them: right and up. Eye offsets in millimetres from
 * the optical axis, angles in radians. Sockets are in the asset frame (metres, +Z muzzle, +Y up, +X shooter's left;
 * origin socket_mount = the rifle's socket_optic).
 */
(function (root) {
'use strict';
const MOA = Math.PI / 180 / 60;
let D = null, T = null, P = null;     // reddot.json, the lens trace set-up, the polynomial

// ---------------------------------------------------------------- vectors and surfaces (the same maths as sim.py)
const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a) => { const l = Math.sqrt(dot3(a, a)); return [a[0] / l, a[1] / l, a[2] / l]; };
function sphere(v, a, R) { return { v, a, k: 1 / R }; }
function hit(s, p, d) {           // nearest intersection to the vertex, and the unit normal: k |q - v|^2 - 2 a.(q - v) = 0
  const w = [p[0] - s.v[0], p[1] - s.v[1], p[2] - s.v[2]];
  const ad = dot3(s.a, d), B = s.k * dot3(w, d) - ad, C = s.k * dot3(w, w) - 2 * dot3(s.a, w), disc = B * B - s.k * C;
  if (disc < 0) return null;
  const sq = (ad > 0 ? -1 : 1) * Math.sqrt(disc), den = B + sq, t = Math.abs(den) > 1e-9 ? -C / den : (-B + sq) / s.k;
  const q = [p[0] + d[0] * t, p[1] + d[1] * t, p[2] + d[2] * t];
  return { q, n: [s.k * (q[0] - s.v[0]) - s.a[0], s.k * (q[1] - s.v[1]) - s.a[1], s.k * (q[2] - s.v[2]) - s.a[2]] };
}
function refract(d, n, n1, n2) {
  if (dot3(d, n) > 0) n = [-n[0], -n[1], -n[2]];
  const eta = n1 / n2, c = -dot3(d, n), k = 1 - eta * eta * (1 - c * c);
  if (k < 0) return null;
  const f = eta * c - Math.sqrt(k);
  return unit([eta * d[0] + f * n[0], eta * d[1] + f * n[1], eta * d[2] + f * n[2]]);
}
function reflect(d, n) { const f = 2 * dot3(d, n); return unit([d[0] - f * n[0], d[1] - f * n[1], d[2] - f * n[2]]); }
const dirOf = (a) => [a[0], a[1], Math.sqrt(Math.max(1e-12, 1 - a[0] * a[0] - a[1] * a[1]))];
function dotLanding(E, v) {       // from the eye, into the doublet, off the dichroic, back out, onto the emitter's plane
  let h = hit(T.s1, E, v); let d = refract(v, h.n, 1, T.n);
  h = hit(T.s2, h.q, d); d = reflect(d, h.n);
  h = hit(T.s1, h.q, d); d = refract(d, h.n, T.n, 1);
  const s = (T.led[2] - h.q[2]) / d[2];
  return [h.q[0] + d[0] * s, h.q[1] + d[1] * s];
}
function targetLanding(E, v, dist) {
  let h = hit(T.s1, E, v); let d = refract(v, h.n, 1, T.n);
  h = hit(T.s3, h.q, d); d = refract(d, h.n, T.n, 1);
  const s = (dist - h.q[2]) / d[2];
  return [h.q[0] + d[0] * s, h.q[1] + d[1] * s];
}
function newton2(f, guess) {      // 2D Newton with a central-difference Jacobian, as in sim.py
  let x = [guess[0], guess[1]]; const h = 1e-7;
  for (let it = 0; it < 40; it++) {
    const f0 = f(x), fa = f([x[0] + h, x[1]]), fb = f([x[0] - h, x[1]]), fc = f([x[0], x[1] + h]), fd = f([x[0], x[1] - h]);
    const j00 = (fa[0] - fb[0]) / (2 * h), j10 = (fa[1] - fb[1]) / (2 * h), j01 = (fc[0] - fd[0]) / (2 * h), j11 = (fc[1] - fd[1]) / (2 * h), det = j00 * j11 - j01 * j10;
    const s0 = (f0[0] * j11 - f0[1] * j01) / det, s1 = (f0[1] * j00 - f0[0] * j10) / det;
    x = [x[0] - s0, x[1] - s1];
    if (Math.abs(s0) + Math.abs(s1) < 1e-15) break;
  }
  return x;
}
function dotDirLens(E, guess) { return dirOf(newton2((a) => { const p = dotLanding(E, dirOf(a)); return [p[0] - T.led[0], p[1] - T.led[1]]; }, guess || [0, 0])); }
function targetDirLens(E, Tp, guess) { return dirOf(newton2((a) => { const p = targetLanding(E, dirOf(a), Tp[2]); return [(p[0] - Tp[0]) / Tp[2], (p[1] - Tp[1]) / Tp[2]]; }, guess || [0, 0])); }

// ---------------------------------------------------------------- set-up
function init(data) {
  D = data;
  const t = data.lens_trace, ab = [0, -Math.sin(t.tilt_rad), -Math.cos(t.tilt_rad)], th = t.t1 + t.t2;
  T = { n: t.n, led: t.led, ez: t.eye_z,
        s1: sphere([0, 0, 0], ab, t.R1), s2: sphere([-ab[0] * t.t1, -ab[1] * t.t1, -ab[2] * t.t1], ab, t.R2), s3: sphere([-ab[0] * th, -ab[1] * th, -ab[2] * th], ab, t.R3) };
  T.E0 = [0, 0, T.ez]; T.u0 = dotDirLens(T.E0);
  const p = data.optics.parallax.beam_direction_poly;
  P = { terms: p.terms, cx: p.cx, cy: p.cy, k: p.see_through_factor, d0: data.optics.parallax.parallax_free_distance_m };
  const F = data.frames; T.LS = F.lens_from_shooter; T.SL = F.shooter_from_lens;
  const b = data.body;
  G.frontDist = (b.tube_centre_l_mm + b.length_mm / 2 - b.lens_inset_mm) - b.eye_l_mm;
  G.rearDist = (b.tube_centre_l_mm - b.length_mm / 2 + b.rear_inset_mm) - b.eye_l_mm;
  G.frontR = b.window_clear_mm / 2; G.rearR = b.rear_clear_mm / 2;
  return api;
}
const G = {};
async function load(url) { const r = await fetch(url || 'reddot.json'); if (!r.ok) throw new Error('reddot.json: ' + r.status); return init(await r.json()); }
function need() { if (!D) throw new Error('OpticRedDot: call init(data) or load(url) first'); }
const toLens = (r, u) => [T.LS[0][0] * r + T.LS[0][1] * u, T.LS[1][0] * r + T.LS[1][1] * u];
const toShooter = (x, y) => [T.SL[0][0] * x + T.SL[0][1] * y, T.SL[1][0] * x + T.SL[1][1] * y];

// ---------------------------------------------------------------- the dot's direction and parallax
function polyLens(ex, ey) {
  let ax = 0, ay = 0;
  for (let k = 0; k < P.terms.length; k++) { const m = Math.pow(ex, P.terms[k][0]) * Math.pow(ey, P.terms[k][1]); ax += P.cx[k] * m; ay += P.cy[k] * m; }
  return [ax, ay];
}
/**
 * beam(eyeRight, eyeUp, {exact}) -> [right, up] in rad: where the dot is, relative to where the centred eye sees it.
 * The dot is at infinity, so this is a direction; it is zero on the axis and grows with eye offset (aberration and defocus
 * of the collimator). Default: the polynomial (valid to 11.5 mm of eye offset). exact: the ray trace.
 */
function beam(eyeRight, eyeUp, o) {
  need();
  const e = toLens(eyeRight, eyeUp);
  if (o && o.exact) { const u = dotDirLens([e[0], e[1], T.ez + ((o && o.eyeBackMm) || 0)], [T.u0[0], T.u0[1]]); return toShooter(u[0] - T.u0[0], u[1] - T.u0[1]); }
  const a = polyLens(e[0], e[1]);
  return toShooter(a[0], a[1]);
}
/**
 * parallax(eyeRight, eyeUp, distanceM, {exact}) -> { right, up, moa, poiShiftMm: [right, up] }   (distance from the front window)
 * The angle between the dot and the target point that the centred eye's dot covers, seen from the offset eye.
 * A shot fired with the dot held on the target lands poiShiftMm away from it (opposite to the error).
 */
function parallax(eyeRight, eyeUp, distanceM, o) {
  need();
  let er, eu;
  if (o && o.exact) {
    const e = toLens(eyeRight, eyeUp), E = [e[0], e[1], T.ez], dist = distanceM * 1000, u0 = T.u0;
    const tl = targetLanding(T.E0, u0, dist), Tp = [tl[0], tl[1], dist];      // the point the centred eye's dot covers, seen through the window
    const ud = dotDirLens(E, [u0[0], u0[1]]), ut = targetDirLens(E, Tp, [u0[0], u0[1]]);
    [er, eu] = toShooter(ud[0] - ut[0], ud[1] - ut[1]);
  } else {
    const e = toLens(eyeRight, eyeUp), al = polyLens(e[0], e[1]);          // error = a(e) + k e / D per lens axis
    const De = distanceM * 1000 - T.ez;                                     // target distance from the eye plane, mm
    [er, eu] = toShooter(al[0] + P.k[0] * e[0] / De, al[1] + P.k[1] * e[1] / De);
  }
  return { right: er, up: eu, moa: Math.hypot(er, eu) / MOA, poiShiftMm: [-er * distanceM * 1000, -eu * distanceM * 1000] };
}

// ---------------------------------------------------------------- brightness
/** Eye pupil diameter (mm) for a scene luminance in cd/m2 (Stanley and Davies 1995). */
function eyePupil(L) { const f = Math.pow(L * 2827 / 846, 0.41); return 7.75 - 5.75 * f / (f + 2); }
/**
 * dot(position, sceneLuminance) -> how the dot looks at a switch position (0 = off .. 11) against a scene luminance (cd/m2)
 *   { luminance, contrast, look: 'off'|'invisible'|'washed_out'|'crisp'|'bright'|'blooming', apparentMoa, halo: 0..1, starburst }
 */
function dot(position, sceneLuminance) {
  need();
  const S = D.brightness.settings, s = S[Math.max(0, Math.min(S.length - 1, position | 0))], A = D.brightness.appearance;
  const seen = D.window.luminous_transmission * Math.max(sceneLuminance, 1e-4), C = s.dot_luminance_cd_m2 / seen;
  const look = s.dot_luminance_cd_m2 === 0 ? 'off' : C < 0.5 ? 'invisible' : C < A.washed_out_below ? 'washed_out' : C <= A.crisp_range[1] ? 'crisp' : C <= A.bloom_above ? 'bright' : 'blooming';
  return { label: s.label, luminance: s.dot_luminance_cd_m2, contrast: C, look, apparentMoa: D.body.dot_moa * Math.sqrt(1 + C / A.bloom_above),
           halo: Math.min(1, 0.02 * C / A.bloom_above), starburst: C > 1000 };
}
/** The lowest switch position that gives a crisp dot (Weber contrast >= 8) against a scene luminance. */
function recommend(sceneLuminance) {
  need();
  const S = D.brightness.settings, seen = D.window.luminous_transmission * Math.max(sceneLuminance, 1e-4), first = seen < 0.2 ? 1 : 4;
  for (let i = first; i < S.length; i++) if (S[i].dot_luminance_cd_m2 / seen >= 8) return i;
  return seen < 0.2 ? 4 : S.length - 1;
}

// ---------------------------------------------------------------- what the eye sees
/**
 * sightPicture(eye, {clicksUp, clicksRight}) -> the geometry a renderer needs, all as tangents (right, up) from the
 * optical axis as seen from the eye:
 *   front, rear   {x, y, r}: the two clear apertures (front window and rear window) as circles
 *   dot           {x, y, r}: the dot's direction and its angular radius (1 MOA); it does not move with the housing
 *   visible       false when the line from the eye to the dot misses either aperture
 * eye: {x, y, z} in mm relative to socket_eye: x right, y up, z back.
 */
function sightPicture(eye, o) {
  need(); o = o || {};
  const x = eye.x || 0, y = eye.y || 0, z = eye.z || 0, Lf = G.frontDist + z, Lr = G.rearDist + z;
  const b = beam(x, y), c = D.turrets.click_mrad / 1000;
  const d = { x: b[0] + (o.clicksRight || 0) * c, y: b[1] + (o.clicksUp || 0) * c, r: D.body.dot_moa * MOA / 2 };
  const front = { x: -x / Lf, y: -y / Lf, r: G.frontR / Lf }, rear = { x: -x / Lr, y: -y / Lr, r: G.rearR / Lr };
  const visible = Math.hypot(d.x - front.x, d.y - front.y) < front.r && Math.hypot(d.x - rear.x, d.y - rear.y) < rear.r;
  return { front, rear, dot: d, visible, tint: D.window.transmission_linear_srgb };
}

// ---------------------------------------------------------------- zero and turrets
function zero(ammo, name) { need(); const a = D.zero.ammo[ammo || 'M855']; if (!a) throw new Error('unknown ammo ' + ammo); const z = a[name || D.zero.default]; if (!z) throw new Error('unknown zero ' + name); return z; }
/** Hold (mrad, + = aim higher) at a distance from the eye, cubic through the table rows. */
function hold(ammo, name, distance) {
  const h = zero(ammo, name).holds; let i = 0; while (i < h.length - 2 && h[i + 1].distance_m < distance) i++;
  const q = [Math.max(0, i - 1), i, i + 1, Math.min(h.length - 1, i + 2)].map((k) => h[k]), uniq = q.filter((p, k) => q.indexOf(p) === k);
  let s = 0;
  for (const p of uniq) { let w = 1; for (const r of uniq) if (r !== p) w *= (distance - r.distance_m) / (p.distance_m - r.distance_m); s += w * p.poi_mm; }
  return -s / distance;
}
/** Point the rifle's ballistics runtime (HK416Ballistics) at this optic: line of sight height and eye position. Returns it. */
function mountTo(B) { need(); return B.configure({ sightHeight: D.zero.axis_over_bore_mm / 1000, eyeToMuzzle: D.zero.eye_to_muzzle_m }); }
/** Dot shift for an adjuster setting: clicks up and right. Returns mrad {up, right}; the POI moves the same way. */
function turret(clicksUp, clicksRight) { need(); const c = D.turrets.click_mrad; return { up: (clicksUp || 0) * c, right: (clicksRight || 0) * c }; }

const api = { init, load, beam, parallax, eyePupil, dot, recommend, sightPicture, zero, hold, mountTo, turret, MOA,
              get data() { return D; }, get sockets() { return D && D.sockets; } };
if (typeof module === 'object' && module.exports) module.exports = api; else root.OpticRedDot = api;
})(typeof window !== 'undefined' ? window : globalThis);
