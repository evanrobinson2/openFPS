/* optic-lpvo.js : runtime for the generic 1-6x24 second-focal-plane LPVO. Credit: carpetshark.
 *
 * Self-contained (no three.js). Browser: window.OpticLPVO, then `await OpticLPVO.load('.../lpvo.json')`.
 * Node: const L = require('./optic-lpvo.js'); L.init(require('./lpvo.json')).
 *
 * It carries the same first-order optics as sim.py (cam solver, paraxial trace, pupils, eye box mask), so any
 * magnification between 1x and 6x is computed, not interpolated; `node test.js` checks the two against each other.
 *
 * Conventions. Eye offsets and field directions are as the shooter sees them: x right, y up. Lengths in the optics
 * are millimetres; field directions are tangents of the angle from the optical axis. Sockets are in the asset frame
 * (metres, +Z muzzle, +Y up, +X shooter's left; origin socket_mount = the rifle's socket_optic).
 */
(function (root) {
'use strict';
const MOA = Math.PI / 180 / 60;
let D = null, G = null;       // lpvo.json, and the design numbers pulled out of it

function init(data) {
  D = data;
  const d = data.design, s = d.stops_radius_mm;
  G = { FO: d.objective_f_mm, FE: d.eyepiece_f_mm, F1: d.erector_f_mm[0], F2: d.erector_f_mm[1], LE: d.first_to_second_image_plane_mm,
        FFL: d.field_lens_f_mm, FSL: d.reticle_plane_field_lens_f_mm, R_OBJ: s.objective, R_FFP: s.first_image_plane, R_E1: s.erector, R_E2: s.erector,
        R_FS: s.second_plane_field_stop, R_OC: s.ocular, EP_MAX: d.exit_pupil_ceiling_mm, TAN_A: Math.tan(d.apparent_half_field_rad) };
  G.table = data.by_magnification.map((r) => ({ lm: Math.log(r.magnification), a: r.erector_cam_mm.group_1_from_first_image_plane, b: r.erector_cam_mm.group_2_from_first_image_plane }));
  G.Mmin = data.body.mag_min; G.Mmax = data.body.mag_max;
  camCache.clear();
  return api;
}
async function load(url) { const r = await fetch(url || 'lpvo.json'); if (!r.ok) throw new Error('lpvo.json: ' + r.status); return init(await r.json()); }
function need() { if (!D) throw new Error('OpticLPVO: call init(data) or load(url) first'); }

// ---------------------------------------------------------------- cams
function gOf(a, M) {            // imaging condition of the erector pair, and the second group's place (see sim.py Lpvo._g)
  const m = M * G.FE / G.FO, s1 = a * G.F1 / (a - G.F1), m1 = -s1 / a, I = a + s1, m2 = -m / m1;
  return [-G.F2 * (1 - m2) * (1 - m2) / m2 - (G.LE - I), I + G.F2 * (1 - 1 / m2)];
}
const camCache = new Map();
/** Erector group positions [a, b] (mm behind the first image plane) for magnification M. */
function cam(M) {
  need();
  M = Math.min(G.Mmax, Math.max(G.Mmin, M));
  const key = Math.round(M * 1e6);
  if (camCache.has(key)) return camCache.get(key);
  // guess from the table (linear in log M), then every root of g on a scan, bisected; keep the one nearest the guess
  const lm = Math.log(M), T = G.table; let i = 0; while (i < T.length - 2 && T[i + 1].lm < lm) i++;
  const f = (lm - T[i].lm) / (T[i + 1].lm - T[i].lm), ga = T[i].a + f * (T[i + 1].a - T[i].a), gb = T[i].b + f * (T[i + 1].b - T[i].b);
  const n = 6000, a0 = 2.0, a1 = G.LE - 6; let best = null, bd = Infinity, pa = a0, pg = gOf(a0, M)[0];
  for (let k = 1; k < n; k++) {
    const a = a0 + (a1 - a0) * k / (n - 1), g = gOf(a, M)[0];
    if (pg * g < 0 && Math.abs(pg) < 1e4 && Math.abs(g) < 1e4) {
      let lo = pa, hi = a, glo = pg;
      for (let it = 0; it < 60; it++) { const mid = 0.5 * (lo + hi), gm = gOf(mid, M)[0]; if ((gm < 0) === (glo < 0)) { lo = mid; glo = gm; } else hi = mid; }
      const aa = 0.5 * (lo + hi), bb = gOf(aa, M)[1];
      if (aa > 3 && aa < bb - 2 && bb < G.LE - 3) { const dd = Math.abs(aa - ga) + Math.abs(bb - gb); if (dd < bd) { bd = dd; best = [aa, bb]; } }
    }
    pa = a; pg = g;
  }
  if (!best) throw new Error('no cam solution at ' + M + 'x');
  camCache.set(key, best);
  return best;
}

// ---------------------------------------------------------------- first order
function layout(M) {
  const c = cam(M), zf = G.FO;
  return [[0, G.FO, G.R_OBJ, 0], [zf, G.FFL, G.R_FFP, 0], [zf + c[0], G.F1, G.R_E1, 0], [zf + c[1], G.F2, G.R_E2, 0], [zf + G.LE, G.FSL, G.R_FS, 1], [zf + G.LE + G.FE, G.FE, G.R_OC, 0]];
}
function trace(els, y, u, hs) {
  for (let i = 0; i < els.length; i++) {
    if (hs) hs[i] = y;
    u -= y / els[i][1];
    if (i + 1 < els.length) y += u * (els[i + 1][0] - els[i][0]);
  }
  return [y, u];
}
/** Pupils, stop and eye relief at magnification M. */
function firstOrder(M) {
  need();
  M = Math.min(G.Mmax, Math.max(G.Mmin, M));
  const els = layout(M), hs = [];
  trace(els, 1, 0, hs);
  const c = trace(els, 0, 0.01);
  let lim = Infinity;
  for (let i = 0; i < els.length; i++) if (!els[i][3] && Math.abs(hs[i]) > 1e-6) lim = Math.min(lim, els[i][2] / Math.abs(hs[i]));
  const hIn = Math.min(lim, G.EP_MAX * M / 2);
  return { magnification: M, angularMagnification: c[1] / 0.01, eyeRelief: -c[0] / c[1], entrancePupil: 2 * hIn, exitPupil: 2 * hIn / M,
           apertureStop: Math.abs(hIn - G.R_OBJ) < 1e-6 ? 'objective' : (hIn < lim ? 'erector-cell stop' : 'erector lens'), els };
}
/** Field of view at M: tangents of the real and apparent half fields. */
function field(M) {
  need();
  M = Math.min(G.Mmax, Math.max(G.Mmin, M));
  let ta = G.TAN_A, tr = ta / M;
  if (G.FO * tr > G.R_FFP) { tr = G.R_FFP / G.FO; ta = tr * M; }
  return { tanReal: tr, tanApparent: ta, realFovDeg: 2 * Math.atan(tr) * 180 / Math.PI, apparentFovDeg: 2 * Math.atan(ta) * 180 / Math.PI,
           fovMAt100m: 200 * tr, reticleScale: G.Mmax / M };
}
/** Fraction of the on-axis beam that passes every aperture at field tangent tanTh (vignetting), by pupil sampling. */
function transmission(M, tanTh, n) {
  n = n || 31;
  const fo = firstOrder(M), els = fo.els, h = fo.entrancePupil / 2, hx = [], hy = [];
  let ok0 = 0, ok = 0;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const x = h * (2 * i / (n - 1) - 1), y = h * (2 * j / (n - 1) - 1);
    if (x * x + y * y > h * h) continue;
    ok0++; trace(els, x, 0, hx); trace(els, y, tanTh, hy);
    let pass = 1;
    for (let k = 0; k < els.length; k++) if (hx[k] * hx[k] + hy[k] * hy[k] > els[k][2] * els[k][2] * 1.0001) { pass = 0; break; }
    ok += pass;
  }
  return ok / Math.max(ok0, 1);
}

// ---------------------------------------------------------------- the eye
/** Eye pupil diameter (mm) for a scene luminance in cd/m2 (Stanley and Davies 1995). */
function eyePupil(L) { const f = Math.pow(L * 2827 / 846, 0.41); return 7.75 - 5.75 * f / (f + 2); }
function discOverlap(r1, r2, d) {
  d = Math.abs(d);
  if (d >= r1 + r2) return 0;
  if (d <= Math.abs(r1 - r2)) return Math.PI * Math.min(r1, r2) * Math.min(r1, r2);
  const a = r1 * r1 * Math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1)), b = r2 * r2 * Math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2));
  return a + b - 0.5 * Math.sqrt(Math.max(0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)));
}
/** Scope-shadow mask 0..1. ex, ey: eye offset from the axis (mm, right/up). dz: eye behind (+) the exit pupil plane (mm).
 *  ax, ay: apparent field direction (tangents, right/up). */
function mask(ex, ey, dz, ax, ay, exitPupil, eyePupilMm) {
  const rp = exitPupil / 2, re = eyePupilMm / 2, m = Math.min(rp, re);
  return discOverlap(rp, re, Math.hypot(ex + dz * ax, ey + dz * ay)) / (Math.PI * m * m);
}

// ---------------------------------------------------------------- one object per frame for a renderer
/**
 * state(M, {eyePupilMm | luminance}) -> everything the shader needs at this magnification:
 *   { magnification, tanReal, tanApparent, realFovDeg, apparentFovDeg, exitPupil, eyeRelief, eyePupil, imageBrightness,
 *     reticleScale, k1, vignette:[7 values over field fraction 0, .25, .5, .7, .85, .95, 1], transmission:[r,g,b], powerRingDeg }
 */
const FR = [0, 0.25, 0.5, 0.7, 0.85, 0.95, 1];
function state(M, o) {
  need(); o = o || {};
  M = Math.min(G.Mmax, Math.max(G.Mmin, M));
  const fo = firstOrder(M), f = field(M), pe = o.eyePupilMm || (o.luminance != null ? eyePupil(o.luminance) : 3.0);
  const lm = Math.log(M) / Math.log(G.Mmax), di = D.distortion;
  return { magnification: M, tanReal: f.tanReal, tanApparent: f.tanApparent, realFovDeg: f.realFovDeg, apparentFovDeg: f.apparentFovDeg,
           exitPupil: fo.exitPupil, entrancePupil: fo.entrancePupil, eyeRelief: fo.eyeRelief, apertureStop: fo.apertureStop, eyePupil: pe,
           imageBrightness: Math.min(1, (fo.exitPupil / pe) * (fo.exitPupil / pe)), reticleScale: f.reticleScale,
           k1: di.k1_at_1x + (di.k1_at_6x - di.k1_at_1x) * lm, vignette: FR.map((x) => transmission(M, f.tanReal * x, o.vignetteSamples || 21)),
           transmission: D.transmission.linear_srgb, powerRingDeg: D.body.throw_deg * lm,
           designEyeRelief: D.eye_relief_summary.at_6x_mm };
}
function vignetteAt(st, r) {
  let i = 0; while (i < FR.length - 2 && FR[i + 1] < r) i++;
  const f = Math.min(1, Math.max(0, (r - FR[i]) / (FR[i + 1] - FR[i])));
  return st.vignette[i] + f * (st.vignette[i + 1] - st.vignette[i]);
}
/**
 * shade(state, eye, ax, ay) -> { inField, r, u, v, brightness }
 *   eye     {x, y, z}: the eye relative to socket_eye in mm: x right, y up, z back (away from the scope).
 *           socket_eye is the 6x exit pupil; at other powers the exit pupil is elsewhere (eyeRelief changes), which is
 *           accounted for here.
 *   ax, ay  apparent direction of the pixel from the eye: tangents of the angle from the optical axis (right, up)
 *   r       field radius, 0 centre .. 1 field stop.   u, v: where to sample the scope pass (0..1, v up), distortion applied
 *   brightness  field stop * vignetting * cos^4 * image brightness * eye box mask (multiply the scope pass by it)
 */
function shade(st, eye, ax, ay) {
  const t = Math.hypot(ax, ay), r = t / st.tanApparent;
  if (r >= 1) return { inField: false, r, u: 0.5, v: 0.5, brightness: 0 };
  const rs = r / (1 + st.k1 * r * r), k = t > 1e-12 ? rs / t : 0;
  const dz = (eye.z || 0) + st.designEyeRelief - st.eyeRelief;
  const edge = Math.min(1, (1 - r) / 0.015), c2 = 1 / (1 + t * t);
  const b = edge * vignetteAt(st, r) * c2 * c2 * st.imageBrightness * mask(eye.x || 0, eye.y || 0, dz, ax, ay, st.exitPupil, st.eyePupil);
  return { inField: true, r, u: 0.5 + 0.5 * ax * k, v: 0.5 + 0.5 * ay * k, brightness: b };
}
/** Object-space error (rad) between reticle and target for an eye offset e (mm) at distance Dm, fixed parallax setting. */
function parallax(M, eMm, Dm) { need(); return M * eMm / 1000 * (1 / Dm - 1 / D.parallax.setting_m); }

// ---------------------------------------------------------------- reticle, zero, turrets
/** The reticle at magnification M: primitives in mrad at 6x, `scale` (multiply by it for object-space mrad at M),
 *  and `apparentScale` (multiply by it for mrad as the eye sees them: constant, because it is a second-plane reticle). */
function reticle(M) { need(); const R = D.reticle; return { name: R.name, primitives: R.primitives, marks: R.bdc_marks, scale: G.Mmax / (M || G.Mmax), apparentScale: G.Mmax, fieldRadiusMradAt6x: R.field_radius_mrad_at_6x }; }
/** Draw the reticle on a 2D canvas. cx, cy: the optical axis in pixels; pxPerApparentMrad: pixels per mrad as the eye sees it;
 *  opts {illumination: 0..1, etched: css colour}. The reticle is drawn at its fixed apparent size (6 x its 6x subtension). */
function drawReticle(ctx, cx, cy, pxPerApparentMrad, opts) {
  need(); opts = opts || {};
  const S = pxPerApparentMrad * G.Mmax, X = (x) => cx + x * S, Y = (y) => cy - y * S, ill = opts.illumination == null ? 1 : opts.illumination;
  ctx.save(); ctx.lineCap = 'butt'; ctx.lineJoin = 'round';
  for (const p of D.reticle.primitives) {
    const lit = p.layer === 'illuminated' && ill > 0;
    const col = lit ? 'rgba(255,40,16,' + Math.min(1, 0.35 + 0.65 * ill) + ')' : (opts.etched || '#060606');
    ctx.strokeStyle = col; ctx.fillStyle = col;
    if (lit) { ctx.shadowColor = 'rgba(255,40,16,' + ill + ')'; ctx.shadowBlur = 6 * ill * Math.max(1, p.d * S / 4); } else ctx.shadowBlur = 0;
    if (p.type === 'line') { ctx.lineWidth = Math.max(0.6, p.width * S); ctx.beginPath(); ctx.moveTo(X(p.p0[0]), Y(p.p0[1])); ctx.lineTo(X(p.p1[0]), Y(p.p1[1])); ctx.stroke(); }
    else if (p.type === 'dot') { ctx.beginPath(); ctx.arc(X(p.c[0]), Y(p.c[1]), Math.max(0.6, p.d / 2 * S), 0, 2 * Math.PI); ctx.fill(); }
    else if (p.type === 'arc') { ctx.lineWidth = Math.max(0.6, p.width * S); ctx.beginPath(); ctx.arc(X(p.c[0]), Y(p.c[1]), p.r * S, -p.a1 * Math.PI / 180, -p.a0 * Math.PI / 180); ctx.stroke(); }
    else if (p.type === 'polyline') { ctx.lineWidth = Math.max(0.6, p.width * S); ctx.beginPath(); p.pts.forEach((q, i) => (i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1])))); ctx.stroke(); }
  }
  ctx.restore();
}
/** Zero table: zero('M855', '200m') -> {bore_angle_mrad, clicks_up_from_centre, holds:[...], ...}. */
function zero(ammo, name) { need(); const a = D.zero.ammo[ammo || 'M855']; if (!a) throw new Error('unknown ammo ' + ammo); const z = a[name || D.zero.default]; if (!z) throw new Error('unknown zero ' + name); return z; }
/** Hold (mrad, + = aim higher) at a distance from the eye, cubic through the table rows. */
function hold(ammo, name, distance) {
  const h = zero(ammo, name).holds; let i = 0; while (i < h.length - 2 && h[i + 1].distance_m < distance) i++;
  const q = [Math.max(0, i - 1), i, i + 1, Math.min(h.length - 1, i + 2)].map((k) => h[k]);
  let s = 0;                                   // Lagrange through up to four neighbours, on the drop (poi), which is smooth
  const uniq = q.filter((p, k) => q.indexOf(p) === k);
  for (const p of uniq) { let w = 1; for (const o of uniq) if (o !== p) w *= (distance - o.distance_m) / (p.distance_m - o.distance_m); s += w * p.poi_mm; }
  return -s / distance;
}
/** Point the rifle's ballistics runtime (HK416Ballistics) at this optic: line of sight height and eye position. Returns it. */
function mountTo(B) { need(); return B.configure({ sightHeight: D.zero.axis_over_bore_mm / 1000, eyeToMuzzle: D.zero.eye_to_muzzle_m }); }
/** Line-of-sight shift for a turret setting: clicks up and right from the zero. Returns mrad {up, right}; the POI moves the same way. */
function turret(clicksUp, clicksRight) { need(); const c = D.body.click_mrad; return { up: (clicksUp || 0) * c, right: (clicksRight || 0) * c }; }
function powerRingDeg(M) { need(); return D.body.throw_deg * Math.log(M) / Math.log(G.Mmax); }
function magnificationAtRing(deg) { need(); return Math.exp(deg / D.body.throw_deg * Math.log(G.Mmax)); }
/** Illuminated dot: luminance (cd/m2) at a knob position 0..10, and its Weber contrast against a scene luminance. */
function illumination(position, sceneLuminance) {
  need(); const L = D.illumination.dot_luminance_cd_m2[Math.max(0, Math.min(10, position | 0))];
  return { luminance: L, contrast: sceneLuminance ? L / (D.transmission.luminous * sceneLuminance) : Infinity };
}

const api = { init, load, cam, firstOrder, field, transmission, eyePupil, discOverlap, mask, state, shade, vignetteAt, parallax, reticle, drawReticle, zero, hold, mountTo, turret,
              powerRingDeg, magnificationAtRing, illumination, MOA, get data() { return D; }, get sockets() { return D && D.sockets; } };
if (typeof module === 'object' && module.exports) module.exports = api; else root.OpticLPVO = api;
})(typeof window !== 'undefined' ? window : globalThis);
