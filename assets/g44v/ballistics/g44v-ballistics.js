/* G44 V ballistics runtime (.22 LR, three CCI loads). Self-contained: no imports.
 *
 *   <script src="g44v-ballistics.js"></script>      -> window.G44VBallistics
 *   import './g44v-ballistics.js'                   -> globalThis.G44VBallistics
 *   const B = require('./g44v-ballistics.js')       -> node
 *
 *   B.poi('cci_standard_velocity', 25, 50)          -> { y, x, v, tof, energy, mach }  point of impact relative to the line of sight, 25 m zero, at 50 m
 *   const shot = B.fire({ origin: eye, dir: lineOfSight, up: [0,1,0], ammo: 'cci_mini_mag', zero: 25, rng: Math.random })
 *   shot.advance(dt, targets)  -> [] or [hit]       (call every frame)        shot.trace(targets, maxT) -> first hit or null
 *   targets: [{ name, point:[x,y,z], normal:[x,y,z], radius }]   a disc (or an unbounded plane without radius)
 *   B.configure({ gravity: [0,-9.80665,0], wind: [x,y,z], rho: 1.225, sound: 340.294 })
 *
 * World frame: metres, seconds, +Y up by default. Vectors are [x, y, z] arrays or {x, y, z} objects; results are arrays.
 * Point mass with the G1 drag function, RK4 at 1 ms: the same arithmetic as sim.py. The numbers in DATA are written by sim.py.
 * See README.md for sources and limits. Sport and range simulation only.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.G44VBallistics = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
'use strict';

/*DATA-BEGIN (written by sim.py; do not edit by hand)*/
const DATA = {"g1":[[0.0,0.2629],[0.05,0.2558],[0.1,0.2487],[0.15,0.2413],[0.2,0.2344],[0.25,0.2278],[0.3,0.2214],[0.35,0.2155],[0.4,0.2104],[0.45,0.2061],[0.5,0.2032],[0.55,0.202],[0.6,0.2034],[0.7,0.2165],[0.725,0.223],[0.75,0.2313],[0.775,0.2417],[0.8,0.2546],[0.825,0.2706],[0.85,0.2901],[0.875,0.3136],[0.9,0.3415],[0.925,0.3734],[0.95,0.4084],[0.975,0.4448],[1.0,0.4805],[1.025,0.5136],[1.05,0.5427],[1.075,0.5677],[1.1,0.5883],[1.125,0.6053],[1.15,0.6191],[1.2,0.6393],[1.25,0.6518],[1.3,0.6589],[1.35,0.6621],[1.4,0.6625],[1.45,0.6607],[1.5,0.6573],[1.55,0.6528],[1.6,0.6474],[1.65,0.6413],[1.7,0.6347],[1.75,0.628],[1.8,0.621],[1.85,0.6141],[1.9,0.6072],[1.95,0.6003],[2.0,0.5934]],"ammo":{"cci_standard_velocity":{"label":"CCI Standard Velocity 40 gr LRN (part 35)","bc":0.12,"mass":0.0025919563999999996,"diameter":0.00566,"mv":271.24,"sigma_moa":3.0},"cci_mini_mag":{"label":"CCI Mini-Mag 40 gr CPRN (part 30)","bc":0.13,"mass":0.0025919563999999996,"diameter":0.00566,"mv":299.64,"sigma_moa":3.5},"cci_quiet_22":{"label":"CCI Quiet-22 40 gr LRN (part 960)","bc":0.12,"mass":0.0025919563999999996,"diameter":0.00566,"mv":185.62,"sigma_moa":4.0}},"sight_height":0.0159,"muzzle_z":0.1743,"rho0":1.225,"sound0":340.294,"default_zero":25.0};
/*DATA-END*/

const G0 = 9.80665, BC_SI = 703.0696, MOA = Math.PI / 10800, H = 0.001;
const cfg = { gravity: [0, -G0, 0], wind: [0, 0, 0], rho: DATA.rho0, sound: DATA.sound0 };
function arr(v) { return Array.isArray(v) ? [v[0], v[1], v[2]] : [v.x, v.y, v.z]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function norm(a) { const l = Math.sqrt(dot(a, a)) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
function gauss(rng) { let u = 0; while (u < 1e-12) u = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng()); }
function configure(o) { for (const k of ['gravity', 'wind']) if (o[k]) cfg[k] = arr(o[k]); if (o.rho != null) cfg.rho = o.rho; if (o.sound != null) cfg.sound = o.sound; return api; }
function ammoOf(name) { const a = DATA.ammo[name || 'cci_standard_velocity']; if (!a) throw new Error('G44VBallistics: unknown ammo ' + name); return a; }

function cdG1(m) {
  const g = DATA.g1; if (m >= 2.0) return g[g.length - 1][1];
  let lo = 0, hi = g.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (g[mid][0] <= m) lo = mid; else hi = mid; }
  return g[lo][1] + (g[hi][1] - g[lo][1]) * (m - g[lo][0]) / (g[hi][0] - g[lo][0]);
}
function accel(vel, bc, wind, grav) {
  const rx = vel[0] - wind[0], ry = vel[1] - wind[1], rz = vel[2] - wind[2], s = Math.sqrt(rx * rx + ry * ry + rz * rz);
  const k = cfg.rho * s * cdG1(s / cfg.sound) * Math.PI / (8 * bc * BC_SI);
  return [-k * rx + grav[0], -k * ry + grav[1], -k * rz + grav[2]];
}
/* one RK4 step; returns [pos, vel] */
function step(pos, vel, bc, wind, grav, h) {
  const k1 = accel(vel, bc, wind, grav), v2 = [0, 0, 0], v3 = [0, 0, 0], v4 = [0, 0, 0], np = [0, 0, 0], nv = [0, 0, 0]; let i;
  for (i = 0; i < 3; i++) v2[i] = vel[i] + k1[i] * h / 2;
  const k2 = accel(v2, bc, wind, grav); for (i = 0; i < 3; i++) v3[i] = vel[i] + k2[i] * h / 2;
  const k3 = accel(v3, bc, wind, grav); for (i = 0; i < 3; i++) v4[i] = vel[i] + k3[i] * h;
  const k4 = accel(v4, bc, wind, grav);
  for (i = 0; i < 3; i++) { np[i] = pos[i] + h * (vel[i] + 2 * v2[i] + 2 * v3[i] + v4[i]) / 6; nv[i] = vel[i] + h * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6; }
  return [np, nv];
}
/* flat fire in the range frame (+Z downrange, +Y up, +X left): state at X metres. Mirrors sim.py fly(). */
function flat(mv, bc, elev, X, windX, y0) {
  let pos = [0, y0, 0], vel = [0, mv * Math.sin(elev), mv * Math.cos(elev)], t = 0; const wind = [windX || 0, 0, 0], grav = [0, -G0, 0];
  while (t < 30) {
    const s = step(pos, vel, bc, wind, grav, H), np = s[0], nv = s[1];
    if (np[2] >= X) {
      const f = (X - pos[2]) / (np[2] - pos[2]); let q = 0;
      for (let i = 0; i < 3; i++) { const c = vel[i] + (nv[i] - vel[i]) * f; q += c * c; }
      return { y: pos[1] + (np[1] - pos[1]) * f, x: pos[0] + (np[0] - pos[0]) * f, v: Math.sqrt(q), tof: t + H * f };
    }
    pos = np; vel = nv; t += H; if (vel[2] <= 1) break;
  }
  return null;
}
const zeroCache = {};
/* bore elevation above the line of sight (rad) for a zero at `zero` metres */
function zeroAngle(name, zero) {
  const a = ammoOf(name), z = zero == null ? DATA.default_zero : zero, key = (name || 'cci_standard_velocity') + '|' + z + '|' + cfg.rho + '|' + cfg.sound;
  if (zeroCache[key] != null) return zeroCache[key];
  let lo = -0.02, hi = 0.2;
  for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2, s = flat(a.mv, a.bc, mid, z, 0, -DATA.sight_height); if (s.y < 0) lo = mid; else hi = mid; }
  return (zeroCache[key] = (lo + hi) / 2);
}
/* point of impact relative to the line of sight at `distance` metres: y up, x left (crosswind opts.windX m/s toward +X) */
function poi(name, zero, distance, opts) {
  const a = ammoOf(name), s = flat(a.mv, a.bc, zeroAngle(name, zero), distance, opts && opts.windX, -DATA.sight_height);
  if (!s) return null; s.energy = 0.5 * a.mass * s.v * s.v; s.mach = s.v / cfg.sound; s.elevation = zeroAngle(name, zero); return s;
}
/* first intersection of the segment a -> b with the targets */
function firstHit(a, b, targets) {
  let best = null;
  for (const tg of targets || []) {
    const n = norm(arr(tg.normal)), p0 = arr(tg.point), da = dot([a[0] - p0[0], a[1] - p0[1], a[2] - p0[2]], n), db = dot([b[0] - p0[0], b[1] - p0[1], b[2] - p0[2]], n);
    if (da === db || da * db > 0) continue;
    const f = da / (da - db), q = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
    if (tg.radius != null) { const d = [q[0] - p0[0], q[1] - p0[1], q[2] - p0[2]]; if (dot(d, d) > tg.radius * tg.radius) continue; }
    if (!best || f < best.f) best = { f: f, point: q, target: tg, normal: n };
  }
  return best;
}
/* Fire one bullet. o.origin: the eye / rear sight on the line of sight; o.dir: the line of sight; o.up: world up of the pistol (default +Y).
 * The bullet starts at the muzzle (sight height below the line of sight) with the bore elevated for the zero, plus dispersion if o.rng is given. */
function fire(o) {
  const a = ammoOf(o.ammo), d = norm(arr(o.dir)), up0 = o.up ? arr(o.up) : [0, 1, 0], right = norm(cross(d, up0)), up = cross(right, d);
  const el = zeroAngle(o.ammo, o.zero) + (o.rng ? a.sigma_moa * MOA * gauss(o.rng) : 0), az = o.rng ? a.sigma_moa * MOA * gauss(o.rng) : 0;
  const org = arr(o.origin), mv = o.mv || a.mv;
  const dir = norm([d[0] + up[0] * Math.tan(el) + right[0] * Math.tan(az), d[1] + up[1] * Math.tan(el) + right[1] * Math.tan(az), d[2] + up[2] * Math.tan(el) + right[2] * Math.tan(az)]);
  const shot = {
    ammo: o.ammo || 'cci_standard_velocity', t: 0, done: false, mass: a.mass,
    pos: [org[0] - up[0] * DATA.sight_height, org[1] - up[1] * DATA.sight_height, org[2] - up[2] * DATA.sight_height],
    vel: [dir[0] * mv, dir[1] * mv, dir[2] * mv],
    speed() { return Math.sqrt(dot(this.vel, this.vel)); },
    /* advance by dt seconds; returns the hits in this interval (at most one: the bullet stops at the first target) */
    advance(dt, targets) {
      const hits = []; let left = dt;
      while (left > 1e-12 && !this.done) {
        const h = Math.min(H, left), s = step(this.pos, this.vel, a.bc, cfg.wind, cfg.gravity, h), hit = firstHit(this.pos, s[0], targets);
        if (hit) {
          const v = [this.vel[0] + (s[1][0] - this.vel[0]) * hit.f, this.vel[1] + (s[1][1] - this.vel[1]) * hit.f, this.vel[2] + (s[1][2] - this.vel[2]) * hit.f], sp = Math.sqrt(dot(v, v));
          this.t += h * hit.f; this.pos = hit.point; this.vel = v; this.done = true;
          hits.push({ target: hit.target, point: hit.point, t: this.t, speed: sp, energy: 0.5 * a.mass * sp * sp, momentum: a.mass * sp,
                      angleDeg: Math.asin(Math.min(1, Math.abs(dot(v, hit.normal)) / sp)) * 180 / Math.PI, mach: sp / cfg.sound });
        } else { this.pos = s[0]; this.vel = s[1]; this.t += h; }
        left -= h;
        if (this.t > 30) this.done = true;
      }
      return hits;
    },
    trace(targets, maxT) { const T = maxT || 10; while (!this.done && this.t < T) { const h = this.advance(0.01, targets); if (h.length) return h[0]; } return null; }
  };
  return shot;
}
const api = { configure, fire, poi, zeroAngle, flat, cdG1, firstHit, get DATA() { return DATA; }, get ammo() { return Object.keys(DATA.ammo); } };
return api;
});
