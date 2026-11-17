/* HK416 D14.5RS ballistics runtime. Self-contained: no three.js, no imports.
 *
 *   <script src="hk416-ballistics.js"></script>      -> window.HK416Ballistics
 *   import './hk416-ballistics.js'                   -> globalThis.HK416Ballistics
 *   const B = require('./hk416-ballistics.js')       -> node
 *
 * World frame: metres, seconds, +Y up by default (gravity along -Y; change with configure({gravity})).
 * Vectors may be [x, y, z] arrays or {x, y, z} objects (THREE.Vector3 works); results are plain arrays.
 * Angles handed to impact() are measured from the surface: 90 is a square hit, 0 is grazing.
 *
 * The numbers in DATA are written by sim.py from the same parameters as ballistics.json. See README.md
 * for the physics, sources and limits. Sport and range simulation only: paper, steel, earth.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.HK416Ballistics = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
'use strict';

/*DATA-BEGIN (written by sim.py; do not edit by hand)*/
const DATA = {"g7":[[0.0,0.1198],[0.05,0.1197],[0.1,0.1196],[0.15,0.1194],[0.2,0.1193],[0.25,0.1194],[0.3,0.1194],[0.35,0.1194],[0.4,0.1193],[0.45,0.1193],[0.5,0.1194],[0.55,0.1193],[0.6,0.1194],[0.65,0.1197],[0.7,0.1202],[0.725,0.1207],[0.75,0.1215],[0.775,0.1226],[0.8,0.1242],[0.825,0.1266],[0.85,0.1306],[0.875,0.1368],[0.9,0.1464],[0.925,0.166],[0.95,0.2054],[0.975,0.2993],[1.0,0.3803],[1.025,0.4015],[1.05,0.4043],[1.075,0.4034],[1.1,0.4014],[1.125,0.3987],[1.15,0.3955],[1.2,0.3884],[1.25,0.381],[1.3,0.3732],[1.35,0.3657],[1.4,0.358],[1.5,0.344],[1.55,0.3376],[1.6,0.3315],[1.65,0.326],[1.7,0.3209],[1.75,0.316],[1.8,0.3117],[1.85,0.3078],[1.9,0.3042],[1.95,0.301],[2.0,0.298],[2.05,0.2951],[2.1,0.2922],[2.15,0.2892],[2.2,0.2864],[2.25,0.2835],[2.3,0.2807],[2.35,0.2779],[2.4,0.2752],[2.45,0.2725],[2.5,0.2697],[2.55,0.267],[2.6,0.2643],[2.65,0.2615],[2.7,0.2588],[2.75,0.2561],[2.8,0.2533],[2.85,0.2506],[2.9,0.2479],[2.95,0.2451],[3.0,0.2424],[3.1,0.2368],[3.2,0.2313],[3.3,0.2258],[3.4,0.2205],[3.5,0.2154],[3.6,0.2106],[3.7,0.206],[3.8,0.2017],[3.9,0.1975],[4.0,0.1935],[4.2,0.1861],[4.4,0.1793],[4.6,0.173],[4.8,0.1672],[5.0,0.1618]],"rifle":{"sightHeightM":0.0655,"eyeToMuzzleM":0.6239,"sightRadiusM":0.364,"twistIn":7.0},"ammo":{"M855":{"label":"M855 ball, 62 gr, steel penetrator (SS109 type)","massKg":0.00401753,"diameterM":0.00569,"lengthM":0.023012,"bcG7":0.151,"mv":850.0,"mvSigma":7.5,"sigmaMoa":0.786,"sparks":0.8,"steelCore":true},"Mk262":{"label":"Mk 262 Mod 1, 77 gr Sierra MatchKing OTM","massKg":0.00498952,"diameterM":0.00569,"lengthM":0.025248,"bcG7":0.19,"mv":770.0,"mvSigma":4.5,"sigmaMoa":0.393,"sparks":0.05,"steelCore":false},"M856":{"label":"M856 tracer, 63.7 gr","massKg":0.00412769,"diameterM":0.00569,"lengthM":0.02921,"bcG7":0.14,"mv":810.0,"mvSigma":9.0,"sigmaMoa":1.3101,"sparks":1.0,"steelCore":false,"tracer":{"igniteM":15.0,"fullM":70.0,"burnoutM":800.0,"color":[1.0,0.25,0.08]}}},"zeros":{"hk100yd":91.44,"hk200yd":182.88,"hk300yd":274.32,"hk400yd":365.76,"50_200":50.0,"25_300":25.0},"defaultZero":"hk100yd","shooter":{"bench":0.0,"aimed_supported":1.2,"aimed":4.0,"hip":60.0},"atmosphere":{"tempC":15.0,"pressureHPa":1013.25,"humidity":0.0},"paper":{"hole":0.85,"loss":0.0005},"steel":{"rho":7850.0,"transfer":1.0,"splashDeg":20.0,"fragSpeed":[0.35,0.9],"fragCount":28,"fragSize":[0.0002,0.002],"fragTau":0.035,"ricA":12.0,"ricW":3.0,"pitLead":870.0,"pitSteel":640.0,"pitSlope":4e-06},"dirt":{"rho":1600.0,"R":3000000.0,"C":1.0,"areaK":2.5,"ricA":8.0,"ricW":2.0,"exitRatio":1.3,"lossPerDeg":0.035,"dragScale":3.0,"scatterDeg":3.0,"craterK":0.0087,"plumeK":0.079,"plumeW":0.5,"ejecta":[3.0,9.0],"linger":1.6,"moisture":0.1},"berm":{"rho":1600.0,"R":2000000.0,"C":1.0,"areaK":2.5,"ricA":8.0,"ricW":2.0,"exitRatio":1.3,"lossPerDeg":0.035,"dragScale":3.0,"scatterDeg":3.0,"craterK":0.0087,"plumeK":0.079,"plumeW":0.5,"ejecta":[3.0,9.0],"linger":1.6,"moisture":0.25},"vis":{"traceMinM":100.0,"traceMag":8.0,"vapRh":0.9,"vapMax":0.12,"vapLife":0.04,"glint":0.02}};
/*DATA-END*/

const G0 = 9.80665, MOA = Math.PI / 10800, BC_SI = 703.0696, IN = 0.0254;
const H = 0.001;                 // integrator step, s (RK4)
const EMPTY = Object.freeze([]);

// ---------------------------------------------------------------- small vector helpers
function arr(v) { return Array.isArray(v) ? [v[0], v[1], v[2]] : [v.x, v.y, v.z]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function len(a) { return Math.sqrt(dot(a, a)); }
function norm(a) { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
function add(a, b, s) { return [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s]; }
function gauss(rng) { let u = 0; while (u < 1e-12) u = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng()); }
function perp(n) { const a = Math.abs(n[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]; return norm(cross(a, n)); }

// ---------------------------------------------------------------- drag table (G7), uniform in Mach
const DM = 0.005, NM = 1001, CD = new Float64Array(NM + 1);
(function () {
  const k = DATA.g7; let j = 0;
  for (let i = 0; i <= NM; i++) {
    const m = Math.min(i * DM, 5);
    while (j < k.length - 2 && k[j + 1][0] < m) j++;
    const f = (m - k[j][0]) / (k[j + 1][0] - k[j][0]);
    CD[i] = k[j][1] + (k[j + 1][1] - k[j][1]) * Math.min(1, Math.max(0, f));
  }
})();
function cdG7(mach) { if (mach >= 5) return CD[NM - 1]; const x = mach / DM, i = x | 0; return CD[i] + (CD[i + 1] - CD[i]) * (x - i); }

// ---------------------------------------------------------------- atmosphere and configuration
function atmosphere(o) {
  o = o || {};
  const alt = o.altitudeM || 0;
  const tC = o.tempC != null ? o.tempC : 15 - 0.0065 * alt;
  const p = o.pressureHPa != null ? o.pressureHPa : 1013.25 * Math.pow(1 - 2.25577e-5 * alt, 5.25588);
  const rh = o.humidity || 0, T = tC + 273.15;
  const es = 6.1121 * Math.exp((18.678 - tC / 234.5) * (tC / (257.14 + tC)));
  const pv = rh * es, x = pv / p;
  const rho = (p - pv) * 100 / (287.058 * T) + pv * 100 / (461.495 * T);
  const c = Math.sqrt((7 + x) / (5 + x) * 8.314462 * T / (0.0289647 * (1 - x) + 0.018015 * x));
  return { tempC: tC, pressureHPa: p, humidity: rh, altitudeM: alt, rho, c };
}

const cfg = {
  env: atmosphere(DATA.atmosphere),
  gravity: [0, -G0, 0],
  mv: {},                                   // per-ammo muzzle velocity overrides, m/s
  sightHeight: DATA.rifle.sightHeightM,
  eyeToMuzzle: DATA.rifle.eyeToMuzzleM,
  spinDrift: true,
  maxTime: 3.0,
};
let zeroCache = {};

/** configure({atmosphere:{tempC,pressureHPa,humidity,altitudeM}, muzzleVelocity:{M855:850}|number, gravity, sightHeight, eyeToMuzzle, spinDrift, maxTime}) */
function configure(o) {
  o = o || {};
  if (o.atmosphere) cfg.env = atmosphere(o.atmosphere);
  if (o.muzzleVelocity != null) {
    if (typeof o.muzzleVelocity === 'number') {      // M855 value from the action model: scale the other loads with it
      const r = o.muzzleVelocity / DATA.ammo.M855.mv;
      for (const k in DATA.ammo) cfg.mv[k] = DATA.ammo[k].mv * r;
    } else Object.assign(cfg.mv, o.muzzleVelocity);
  }
  if (o.gravity) cfg.gravity = arr(o.gravity);
  for (const k of ['sightHeight', 'eyeToMuzzle', 'spinDrift', 'maxTime']) if (o[k] != null) cfg[k] = o[k];
  zeroCache = {};
  return api;
}
function ammoOf(name) { const a = DATA.ammo[name || 'M855']; if (!a) throw new Error('unknown ammo ' + name); return a; }
function mvOf(name) { return cfg.mv[name] != null ? cfg.mv[name] : DATA.ammo[name].mv; }
function millerSg(a, mv) {
  const d = a.diameterM / IN, l = a.lengthM / a.diameterM, t = DATA.rifle.twistIn / d;
  return 30 * (a.massKg / 6.479891e-5) / (t * t * d * d * d * l * (1 + l * l)) * Math.cbrt(mv / 0.3048 / 2800)
    * ((cfg.env.tempC + 273.15) / 288.15) * (1013.25 / cfg.env.pressureHPa);
}

// ---------------------------------------------------------------- the shot
class Shot {
  /** Use HK416Ballistics.fire(); the constructor takes the muzzle state directly. */
  constructor(p, v, ammoName, o) {
    o = o || {};
    const a = ammoOf(ammoName);
    this.ammo = ammoName; this.mass = a.massKg; this._a = a;
    this.origin = [p[0], p[1], p[2]]; this.muzzleVelocity = len(v);
    this.k = Math.PI / 8 * cfg.env.rho / (a.bcG7 * BC_SI) * (o.dragScale || 1);
    this.c = cfg.env.c;
    const w = o.wind ? arr(o.wind) : [0, 0, 0];
    this.wx = w[0]; this.wy = w[1]; this.wz = w[2];
    this.gx = cfg.gravity[0]; this.gy = cfg.gravity[1]; this.gz = cfg.gravity[2];
    this.maxTime = o.maxTime || cfg.maxTime;
    // spin drift (Litz fit), applied as a sideways offset that grows as t^1.83
    this.sd = 0; this.sr = [0, 0, 0];
    if ((o.spinDrift != null ? o.spinDrift : cfg.spinDrift) && !o.dragScale) {
      const up = norm([-this.gx, -this.gy, -this.gz]);
      this.sr = norm(cross(norm(v), up));
      this.sd = 1.25 * (millerSg(a, this.muzzleVelocity) + 1.2) * IN;
    }
    this.s = [p[0], p[1], p[2], v[0], v[1], v[2]];   // integrator state (without spin drift)
    this.buf = new Float64Array(6 * 128); this.n = 0;
    this._store();
    this.t = 0; this.done = false; this.chord = 0.01;
    this._skip = null;
  }
  _store() {
    if ((this.n + 1) * 6 > this.buf.length) { const b = new Float64Array(this.buf.length * 2); b.set(this.buf); this.buf = b; }
    const s = this.s, b = this.buf, i = this.n * 6, t = this.n * H;
    const d = this.sd ? this.sd * Math.pow(t, 1.83) : 0, dv = this.sd && t > 0 ? 1.83 * d / t : 0, r = this.sr;
    b[i] = s[0] + r[0] * d; b[i + 1] = s[1] + r[1] * d; b[i + 2] = s[2] + r[2] * d;
    b[i + 3] = s[3] + r[0] * dv; b[i + 4] = s[4] + r[1] * dv; b[i + 5] = s[5] + r[2] * dv;
    this.n++;
  }
  _rk4() {
    const s = this.s, k = this.k, c = this.c, wx = this.wx, wy = this.wy, wz = this.wz, gx = this.gx, gy = this.gy, gz = this.gz;
    let vx = s[3], vy = s[4], vz = s[5], rx, ry, rz, sp, q;
    rx = vx - wx; ry = vy - wy; rz = vz - wz; sp = Math.sqrt(rx * rx + ry * ry + rz * rz); q = -k * cdG7(sp / c) * sp;
    const a1x = q * rx + gx, a1y = q * ry + gy, a1z = q * rz + gz;
    const v2x = vx + a1x * H / 2, v2y = vy + a1y * H / 2, v2z = vz + a1z * H / 2;
    rx = v2x - wx; ry = v2y - wy; rz = v2z - wz; sp = Math.sqrt(rx * rx + ry * ry + rz * rz); q = -k * cdG7(sp / c) * sp;
    const a2x = q * rx + gx, a2y = q * ry + gy, a2z = q * rz + gz;
    const v3x = vx + a2x * H / 2, v3y = vy + a2y * H / 2, v3z = vz + a2z * H / 2;
    rx = v3x - wx; ry = v3y - wy; rz = v3z - wz; sp = Math.sqrt(rx * rx + ry * ry + rz * rz); q = -k * cdG7(sp / c) * sp;
    const a3x = q * rx + gx, a3y = q * ry + gy, a3z = q * rz + gz;
    const v4x = vx + a3x * H, v4y = vy + a3y * H, v4z = vz + a3z * H;
    rx = v4x - wx; ry = v4y - wy; rz = v4z - wz; sp = Math.sqrt(rx * rx + ry * ry + rz * rz); q = -k * cdG7(sp / c) * sp;
    const a4x = q * rx + gx, a4y = q * ry + gy, a4z = q * rz + gz;
    s[0] += H / 6 * (vx + 2 * v2x + 2 * v3x + v4x); s[1] += H / 6 * (vy + 2 * v2y + 2 * v3y + v4y); s[2] += H / 6 * (vz + 2 * v2z + 2 * v3z + v4z);
    s[3] += H / 6 * (a1x + 2 * a2x + 2 * a3x + a4x); s[4] += H / 6 * (a1y + 2 * a2y + 2 * a3y + a4y); s[5] += H / 6 * (a1z + 2 * a2z + 2 * a3z + a4z);
    this._store();
  }
  /** Position (out[0..2]) and velocity (out[3..5]) at time t, into a 6-array. */
  state(t, out) {
    if (t < 0) t = 0;
    const x = t / H; let i = Math.floor(x);
    while (this.n < i + 2) this._rk4();
    const f = x - i, b = this.buf, j = i * 6, f2 = f * f, f3 = f2 * f;
    const h00 = 2 * f3 - 3 * f2 + 1, h10 = (f3 - 2 * f2 + f) * H, h01 = 3 * f2 - 2 * f3, h11 = (f3 - f2) * H;
    out = out || new Array(6);
    for (let a = 0; a < 3; a++) {
      out[a] = h00 * b[j + a] + h10 * b[j + 3 + a] + h01 * b[j + 6 + a] + h11 * b[j + 9 + a];
      out[a + 3] = b[j + 3 + a] + (b[j + 9 + a] - b[j + 3 + a]) * f;
    }
    return out;
  }
  /** {t, pos, vel, speed, mach, energy, momentum, tracer} at time t (seconds after the shot). */
  at(t) {
    const s = this.state(t), sp = Math.sqrt(s[3] * s[3] + s[4] * s[4] + s[5] * s[5]);
    return { t, pos: [s[0], s[1], s[2]], vel: [s[3], s[4], s[5]], speed: sp, mach: sp / this.c,
      energy: 0.5 * this.mass * sp * sp, momentum: this.mass * sp, tracer: this.tracer(t, s) };
  }
  /** Tracer state at time t: null for ball; {lit, brightness 0..1, color} for M856. */
  tracer(t, s) {
    const tr = this._a.tracer; if (!tr) return null;
    s = s || this.state(t);
    const d = Math.hypot(s[0] - this.origin[0], s[1] - this.origin[1], s[2] - this.origin[2]);
    let b = 0;
    if (d >= tr.igniteM && d <= tr.burnoutM) b = d >= tr.fullM ? 1 : 0.15 + 0.85 * (d - tr.igniteM) / (tr.fullM - tr.igniteM);
    return { lit: b > 0, brightness: b, color: tr.color };
  }
  /**
   * Advance the shot by dt seconds and report what it hit on the way.
   *   targets: array of shapes (see intersect) and/or
   *   raycast(origin, dir, maxDist) -> null | {distance, normal?, object?, passThrough?}   (e.g. a THREE.Raycaster wrapper)
   * Returns an array of hits in time order (usually empty). A target with passThrough:true (paper) is reported once
   * and the bullet carries on; anything else stops the shot (shot.done = true).
   */
  advance(dt, targets, raycast) {
    if (this.done) return EMPTY;
    let hits = null;
    const tEnd = Math.min(this.t + dt, this.maxTime), A = SA, B = SB;
    while (this.t < tEnd) {
      const t0 = this.t, t1 = Math.min(t0 + this.chord, tEnd);
      this.state(t0, A); this.state(t1, B);
      let fMin = 0;
      for (;;) {
        const h = firstHit(A, B, targets, this._skip, raycast, fMin);
        if (!h) break;
        const hit = this._hit(h, t0 + (t1 - t0) * h.f);
        (hits || (hits = [])).push(hit);
        if (h.passThrough) { if (h.target) (this._skip || (this._skip = new Set())).add(h.target); fMin = h.f + 1e-6; continue; }
        this.done = true; this.t = hit.t; return hits;
      }
      this.t = t1;
    }
    if (this.t >= this.maxTime) this.done = true;
    return hits || EMPTY;
  }
  /** Resolve the whole flight now. Returns the hits in time order (empty if nothing within maxTime / maxRange). */
  trace(targets, raycast, o) {
    o = o || {};
    const tMax = Math.min(o.maxTime || this.maxTime, this.maxTime), maxR = o.maxRange || Infinity;
    let all = null;
    while (!this.done && this.t < tMax) {
      const h = this.advance(Math.min(0.05, tMax - this.t), targets, raycast);
      if (h.length) all = all ? all.concat(h) : h.slice();
      if (maxR < Infinity) { this.state(this.t, SA); if (Math.hypot(SA[0] - this.origin[0], SA[1] - this.origin[1], SA[2] - this.origin[2]) > maxR) break; }
    }
    return all || EMPTY;
  }
  _hit(h, t) {
    let s = this.state(t);
    for (let i = 0; i < 2; i++) {            // the chord is straight but the speed along it is not: settle t on the hit point
      t += ((h.point[0] - s[0]) * s[3] + (h.point[1] - s[1]) * s[4] + (h.point[2] - s[2]) * s[5]) / (s[3] * s[3] + s[4] * s[4] + s[5] * s[5]);
      s = this.state(t);
    }
    const v = [s[3], s[4], s[5]], sp = len(v), d = [v[0] / sp, v[1] / sp, v[2] / sp];
    let n = h.normal ? h.normal : [-d[0], -d[1], -d[2]];
    if (dot(n, d) > 0) n = [-n[0], -n[1], -n[2]];
    const hit = { t, point: h.point, normal: n, dir: d, vel: v, speed: sp, mach: sp / this.c, energy: 0.5 * this.mass * sp * sp,
      momentum: this.mass * sp, angle: Math.asin(Math.min(1, -dot(n, d))) * 180 / Math.PI,
      range: Math.hypot(h.point[0] - this.origin[0], h.point[1] - this.origin[1], h.point[2] - this.origin[2]),
      ammo: this.ammo, target: h.target || null, index: h.index != null ? h.index : -1, object: h.object || null, passThrough: !!h.passThrough };
    if (h.target && (h.target.type === 'disc' || h.target.type === 'rect')) {      // offset in the target's own plane
      const c = arr(h.target.center), tn = norm(arr(h.target.normal));
      let up = h.target.up ? arr(h.target.up) : [0, 1, 0]; up = norm(add(up, tn, -dot(up, tn)));
      const rt = cross(up, tn), r = [h.point[0] - c[0], h.point[1] - c[1], h.point[2] - c[2]];
      hit.offset = { x: dot(r, rt), y: dot(r, up), r: len(r) };
    }
    return hit;
  }
}
const SA = new Array(6), SB = new Array(6);

// ---------------------------------------------------------------- intersection
/**
 * Earliest hit of the segment a->b against a list of shapes:
 *   {type:'disc',   center, normal, radius}
 *   {type:'rect',   center, normal, u (unit vector in the plane), halfU, halfV}
 *   {type:'plane',  point, normal}                (infinite: the ground)
 *   {type:'sphere', center, radius}
 *   {type:'box',    min, max}                     (axis-aligned: the berm)
 * Any shape may carry passThrough:true, an id, and anything else the game wants back in hit.target.
 * Returns null or {f (0..1 along the segment), point, normal, target, index}.
 */
function intersect(a, b, targets, skip) { return firstHit(arr(a), arr(b), targets, skip || null, null, 0); }

function firstHit(a, b, targets, skip, raycast, fMin) {
  const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
  let best = null, bf = 1 + 1e-12;
  if (targets) for (let i = 0; i < targets.length; i++) {
    const T = targets[i]; if (skip && skip.has(T)) continue;
    let f = -1, n = null;
    switch (T.type) {
      case 'disc': case 'rect': case 'plane': {
        const N = T.normal, nx = N.x !== undefined ? N.x : N[0], ny = N.y !== undefined ? N.y : N[1], nz = N.z !== undefined ? N.z : N[2];
        const C = T.type === 'plane' ? T.point : T.center, cx = C.x !== undefined ? C.x : C[0], cy = C.y !== undefined ? C.y : C[1], cz = C.z !== undefined ? C.z : C[2];
        const den = nx * dx + ny * dy + nz * dz; if (den > -1e-12 && den < 1e-12) break;
        const g = (nx * (cx - a[0]) + ny * (cy - a[1]) + nz * (cz - a[2])) / den;
        if (g < fMin || g >= bf) break;
        const px = a[0] + dx * g - cx, py = a[1] + dy * g - cy, pz = a[2] + dz * g - cz;
        if (T.type === 'disc') { if (px * px + py * py + pz * pz > T.radius * T.radius) break; }
        else if (T.type === 'rect') {
          const u = arr(T.u), w = cross([nx, ny, nz], u);
          if (Math.abs(px * u[0] + py * u[1] + pz * u[2]) > T.halfU || Math.abs(px * w[0] + py * w[1] + pz * w[2]) > T.halfV) break;
        }
        f = g; n = [nx, ny, nz]; break;
      }
      case 'sphere': {
        const C = arr(T.center), ox = a[0] - C[0], oy = a[1] - C[1], oz = a[2] - C[2];
        const A2 = dx * dx + dy * dy + dz * dz, Bq = ox * dx + oy * dy + oz * dz, Cq = ox * ox + oy * oy + oz * oz - T.radius * T.radius;
        const disc = Bq * Bq - A2 * Cq; if (disc < 0) break;
        const g = (-Bq - Math.sqrt(disc)) / A2; if (g < fMin || g >= bf) break;
        f = g; n = norm([ox + dx * g, oy + dy * g, oz + dz * g]); break;
      }
      case 'box': {
        const mn = arr(T.min), mx = arr(T.max), d = [dx, dy, dz]; let t0 = 0, t1 = 1, ax = -1, sg = 0, ok = true;
        for (let k = 0; k < 3 && ok; k++) {
          if (Math.abs(d[k]) < 1e-12) { if (a[k] < mn[k] || a[k] > mx[k]) ok = false; continue; }
          let e0 = (mn[k] - a[k]) / d[k], e1 = (mx[k] - a[k]) / d[k], s = -1; if (e0 > e1) { const q = e0; e0 = e1; e1 = q; s = 1; }
          if (e0 > t0) { t0 = e0; ax = k; sg = s; } if (e1 < t1) t1 = e1; if (t0 > t1) ok = false;
        }
        if (!ok || ax < 0 || t0 < fMin || t0 >= bf) break;
        f = t0; n = [0, 0, 0]; n[ax] = sg; break;
      }
    }
    if (f >= 0) { bf = f; best = { f, normal: n, target: T, index: i, passThrough: !!T.passThrough }; }
  }
  if (raycast) {
    const L = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (L > 0) {
      const s0 = fMin * L, r = raycast([a[0] + dx * fMin, a[1] + dy * fMin, a[2] + dz * fMin], [dx / L, dy / L, dz / L], L * Math.min(bf, 1) - s0);
      if (r && r.distance != null) {
        const f = (s0 + r.distance) / L;
        if (f < bf) best = { f, normal: r.normal ? norm(arr(r.normal)) : null, target: null, index: -1, object: r.object !== undefined ? r.object : r, passThrough: !!r.passThrough };
      }
    }
  }
  if (best) best.point = [a[0] + dx * best.f, a[1] + dy * best.f, a[2] + dz * best.f];
  return best;
}

// ---------------------------------------------------------------- zero
function flatY(ammoName, mv, elev, X) {            // height of the bullet X metres downrange of the muzzle, flat fire
  const sh = new Shot([0, 0, 0], [mv * Math.cos(elev), mv * Math.sin(elev), 0], ammoName, { spinDrift: false, maxTime: 5 });
  sh.gx = 0; sh.gy = -G0; sh.gz = 0;
  let i = 0;
  for (;;) { if (sh.n < i + 2) sh._rk4(); if (sh.buf[(i + 1) * 6] >= X || i > 5000) break; i++; }
  const x0 = sh.buf[i * 6], x1 = sh.buf[(i + 1) * 6], f = (X - x0) / (x1 - x0);
  return sh.state((i + f) * H)[1];
}
/** Bore elevation (rad) above the line of sight for a zero: a name from HK416Ballistics.zeros or a distance from the eye in metres. */
function zeroAngle(ammoName, zero, mv) {
  ammoName = ammoName || 'M855'; zero = zero == null ? DATA.defaultZero : zero;
  const D = typeof zero === 'number' ? zero : DATA.zeros[zero]; if (D == null) throw new Error('unknown zero ' + zero);
  mv = mv || mvOf(ammoName);
  const key = ammoName + '|' + D + '|' + mv;
  if (zeroCache[key] != null) return zeroCache[key];
  const X = D - cfg.eyeToMuzzle, h = cfg.sightHeight;
  let e = (h + 0.5 * G0 * (X / mv) * (X / mv)) / X;
  for (let i = 0; i < 6; i++) e -= (flatY(ammoName, mv, e, X) - h) / X;
  return (zeroCache[key] = e);
}
/** Point of impact relative to the point of aim (m, + is high) at a distance from the eye, for a level shot. */
function poi(ammoName, zero, distance) {
  ammoName = ammoName || 'M855';
  return flatY(ammoName, mvOf(ammoName), zeroAngle(ammoName, zero), distance - cfg.eyeToMuzzle) - cfg.sightHeight;
}

// ---------------------------------------------------------------- fire
/**
 * fire({origin, dir, up, ammo, zero, wind, rng, stance, originIs, muzzleVelocity, spreadMoa, dragScale, maxTime}) -> Shot
 *   origin, dir  eye position and line of sight (originIs:'eye', default: the ADS camera), or the muzzle position
 *                and bore direction (originIs:'muzzle': hip fire from socket_muzzle; no sight geometry is applied)
 *   up           world-ish up of the rifle (default: against gravity); only used to place the bore under the sights
 *   ammo         'M855' (default) | 'Mk262' | 'M856'
 *   zero         'hk100yd' (default) | 'hk200yd' | 'hk300yd' | 'hk400yd' | '50_200' | '25_300' | metres from the eye
 *   wind         air velocity vector, m/s, world frame
 *   stance       'bench' | 'aimed_supported' | 'aimed' (default) | 'hip' | 'none' (no dispersion at all)
 *   spreadMoa    extra per-axis sigma added in quadrature (e.g. recoil bloom during a burst)
 *   rng          function returning [0,1) (default Math.random)
 */
function fire(o) {
  const name = o.ammo || 'M855', a = ammoOf(name), rng = o.rng || Math.random;
  let d = norm(arr(o.dir)), p = arr(o.origin);
  let up = o.up ? arr(o.up) : [-cfg.gravity[0], -cfg.gravity[1], -cfg.gravity[2]];
  up = add(up, d, -dot(up, d)); up = len(up) < 1e-9 ? perp(d) : norm(up);
  const right = cross(d, up);
  const stance = o.stance || 'aimed';
  let mv = o.muzzleVelocity || mvOf(name), el = 0, az = 0;
  if (o.originIs !== 'muzzle') {
    p = add(add(p, d, cfg.eyeToMuzzle), up, -cfg.sightHeight);
    el = zeroAngle(name, o.zero, mvOf(name));
  }
  if (stance !== 'none') {
    const ss = DATA.shooter[stance]; if (ss == null) throw new Error('unknown stance ' + stance);
    const sig = Math.sqrt(a.sigmaMoa * a.sigmaMoa + ss * ss + (o.spreadMoa || 0) * (o.spreadMoa || 0)) * MOA;
    el += gauss(rng) * sig; az += gauss(rng) * sig;
    if (!o.muzzleVelocity) mv += gauss(rng) * a.mvSigma;
  }
  const b = norm([d[0] + up[0] * el + right[0] * az, d[1] + up[1] * el + right[1] * az, d[2] + up[2] * el + right[2] * az]);
  const shot = new Shot(p, [b[0] * mv, b[1] * mv, b[2] * mv], name, o);
  shot.bore = b; shot.zero = o.zero == null ? DATA.defaultZero : o.zero; shot.stance = stance;
  return shot;
}

// ---------------------------------------------------------------- terminal effects
function logistic(x, c, w) { return 1 / (1 + Math.exp((x - c) / w)); }
function reflectOut(dir, n, outDeg, scatterDeg, rng) {       // direction leaving the surface at outDeg above it
  let t = add(dir, n, -dot(dir, n)); t = len(t) < 1e-9 ? perp(n) : norm(t);
  const s = cross(n, t), o = outDeg * Math.PI / 180, y = gauss(rng) * scatterDeg * Math.PI / 180;
  return norm([t[0] * Math.cos(o) * Math.cos(y) + s[0] * Math.cos(o) * Math.sin(y) + n[0] * Math.sin(o),
    t[1] * Math.cos(o) * Math.cos(y) + s[1] * Math.cos(o) * Math.sin(y) + n[1] * Math.sin(o),
    t[2] * Math.cos(o) * Math.cos(y) + s[2] * Math.cos(o) * Math.sin(y) + n[2] * Math.sin(o)]);
}
/** Inertia and mass of a round steel plate hinged on a horizontal axis hingeOffset below its centre (default: its bottom edge). */
function plateProps(pl) {
  const r = pl.radius, th = pl.thickness != null ? pl.thickness : 0.010;
  const mass = pl.mass != null ? pl.mass : DATA.steel.rho * Math.PI * r * r * th;
  const s = pl.hingeOffset != null ? pl.hingeOffset : r;
  return { mass, s, inertia: 0.25 * mass * r * r + mass * s * s, k: mass * G0 * s };
}
/** Start a plate swinging. Returns the state for plateStep. theta is from vertical, + is falling away from the shooter. */
function plateKick(pl, momentumNormal, hitOffsetY, state) {
  const P = plateProps(pl), lean = (pl.leanDeg != null ? pl.leanDeg : 2) * Math.PI / 180;
  const st = state || { theta: -lean, omega: 0, down: false };
  st.omega += momentumNormal * Math.max(0, P.s + (hitOffsetY || 0)) / P.inertia;
  st.lean = lean; st.k = P.k / P.inertia; st.damping = pl.damping || 0; st.atRest = false;
  return st;
}
/** Integrate a kicked plate. Sets state.down when it lies flat (theta = 90 deg) and state.atRest when it has settled back on its stop. */
function plateStep(st, dt) {
  if (st.down || st.atRest) return st;
  let n = Math.max(1, Math.ceil(dt / 0.002)); const h = dt / n;
  while (n--) {
    st.omega += (st.k * Math.sin(st.theta) - st.damping * st.omega) * h; st.theta += st.omega * h;
    if (st.theta >= Math.PI / 2) { st.theta = Math.PI / 2; st.landingRate = st.omega; st.omega = 0; st.down = true; break; }
    if (st.theta <= -st.lean) { st.theta = -st.lean; st.omega = Math.abs(st.omega) > 0.3 ? -0.3 * st.omega : 0; if (!st.omega) { st.atRest = true; break; } }
  }
  return st;
}

/**
 * impact({surface, energy | speed, angle, ammo, dir, normal, rng, plate, hitOffsetY, yawDeg, moisture}) -> effects
 * or impact({hit, surface, plate}) with a hit from Shot.advance / trace.
 *   surface  'paper' | 'steel' | 'dirt' | 'berm'
 *   angle    degrees from the surface (90 = square). dir and normal (unit vectors) are needed only for outgoing directions
 *   plate    steel only: {radius, thickness (0.010), hingeOffset (radius), leanDeg (2), mass}
 */
function impact(o) {
  const h = o.hit || {}, name = o.ammo || h.ammo || 'M855', a = ammoOf(name), rng = o.rng || Math.random;
  const speed = o.speed != null ? o.speed : h.speed != null ? h.speed : Math.sqrt(2 * (o.energy != null ? o.energy : 0) / a.massKg);
  const energy = 0.5 * a.massKg * speed * speed, mom = a.massKg * speed;
  const angle = Math.max(0, Math.min(90, o.angle != null ? o.angle : h.angle != null ? h.angle : 90)), sinA = Math.sin(angle * Math.PI / 180);
  const dir = o.dir ? norm(arr(o.dir)) : h.dir || null, n = o.normal ? norm(arr(o.normal)) : h.normal || null;
  const surface = o.surface, out = { surface, ammo: name, speed, energy, momentum: mom, angle };
  if (surface === 'paper') {
    const dh = a.diameterM * DATA.paper.hole, yaw = (o.yawDeg || 0) * Math.PI / 180;
    out.hole = { diameter: dh, greaseRing: a.diameterM, length: Math.max(dh, (dh * Math.cos(yaw) + a.lengthM * Math.sin(yaw))) / Math.max(sinA, 0.05), keyhole: (o.yawDeg || 0) > 15 };
    out.passThrough = true; out.exitSpeed = speed * (1 - DATA.paper.loss / Math.max(sinA, 0.05));
    return out;
  }
  if (surface === 'steel') {
    const S = DATA.steel, pRic = logistic(angle, S.ricA, S.ricW), ric = rng() < pRic;
    const pn = mom * sinA * S.transfer, tau = a.lengthM / Math.max(speed * sinA, 1);
    out.plateImpulse = pn;                                   // N s, along -normal (into the plate)
    out.contactTime = tau; out.peakForce = Math.PI * pn / (2 * tau);     // half-sine force pulse for the sound model
    out.ricochetProbability = pRic; out.ricochet = ric;
    const vn = speed * sinA, thr = a.steelCore ? S.pitSteel : S.pitLead;
    out.pitDepth = Math.max(0, vn - thr) * S.pitSlope; out.perforates = false;
    out.spark = rng() < a.sparks * Math.min(1, vn / 400);
    if (o.plate) {
      const P = plateProps(o.plate), hh = Math.max(0, P.s + (o.hitOffsetY != null ? o.hitOffsetY : h.offset ? h.offset.y : 0));
      const w0 = pn * hh / P.inertia, ke = 0.5 * P.inertia * w0 * w0, lean = (o.plate.leanDeg != null ? o.plate.leanDeg : 2) * Math.PI / 180;
      out.plate = { mass: P.mass, inertia: P.inertia, hitHeight: hh, omega0: w0, kineticEnergy: ke, energyToTopple: P.k * (1 - Math.cos(lean)),
        falls: ke > P.k * (1 - Math.cos(lean)), centreSpeed: w0 * P.s };
    }
    if (ric) {
      const keep = Math.max(0.3, 1 - 0.03 * angle);
      out.exit = { speed: speed * keep, angle, dragScale: 3, dir: dir && n ? reflectOut(dir, n, angle, 3, rng) : null };
    } else {
      // splash: the bullet breaks up and leaves along the plate face
      out.splash = { halfAngleDeg: S.splashDeg, count: S.fragCount, speedMin: S.fragSpeed[0] * speed, speedMax: S.fragSpeed[1] * speed,
        sizeMin: S.fragSize[0], sizeMax: S.fragSize[1], dragTau: S.fragTau, bias: dir && n ? add(dir, n, -dot(dir, n)) : [0, 0, 0],
        massKg: a.massKg, hot: !!a.tracer };
      out.fragments = function (count) { return splash(out.splash, n, count, rng); };
    }
    return out;
  }
  if (surface === 'dirt' || surface === 'berm') {
    const S = DATA[surface], moist = o.moisture != null ? o.moisture : S.moisture;
    const pRic = logistic(angle, S.ricA, S.ricW), ric = rng() < pRic;
    const A = Math.PI * a.diameterM * a.diameterM / 4 * S.areaK;
    const depth = a.massKg / (2 * S.C * S.rho * A) * Math.log(1 + S.C * S.rho * speed * speed / S.R);
    const keep = ric ? Math.max(0.3, 1 - S.lossPerDeg * angle) : 0, eDep = energy * (1 - keep * keep), e13 = Math.cbrt(eDep), dry = 1 - 0.7 * moist;
    out.ricochetProbability = pRic; out.ricochet = ric;
    out.penetration = ric ? 0 : depth;                         // m along the bullet's path
    out.energyDeposited = eDep;
    out.crater = { diameter: S.craterK * e13, length: S.craterK * e13 / Math.max(sinA, 0.15) };
    let axis = n;
    if (dir && n) { const r = add(dir, n, -2 * dot(dir, n)); axis = norm([n[0] * 0.7 + r[0] * 0.3, n[1] * 0.7 + r[1] * 0.3, n[2] * 0.7 + r[2] * 0.3]); }
    out.dust = { height: S.plumeK * e13 * dry, width: S.plumeK * e13 * dry * S.plumeW, speedMin: S.ejecta[0], speedMax: S.ejecta[1] * Math.cbrt(eDep / 1500),
      linger: S.linger * dry, axis, clods: moist > 0.2, impulse: mom * (1 - keep) };
    if (ric) {
      const outA = Math.min(60, angle * S.exitRatio);
      out.exit = { speed: speed * keep, angle: outA, dragScale: S.dragScale, dir: dir && n ? reflectOut(dir, n, outA, S.scatterDeg, rng) : null };
    }
    return out;
  }
  throw new Error('unknown surface ' + surface);
}
/** Fragment velocities for a steel splash: [{vel:[x,y,z], size}], count items, leaving within halfAngle of the plate face. */
function splash(sp, n, count, rng) {
  rng = rng || Math.random; n = n || [0, 0, 1];
  const t = perp(n), s = cross(n, t), list = [], bl = len(sp.bias), bn = bl > 1e-9 ? [sp.bias[0] / bl, sp.bias[1] / bl, sp.bias[2] / bl] : null;
  for (let i = 0; i < (count || sp.count); i++) {
    const az = rng() * 2 * Math.PI, el = rng() * sp.halfAngleDeg * Math.PI / 180, v = sp.speedMin + (sp.speedMax - sp.speedMin) * rng() * rng();
    let d = [(t[0] * Math.cos(az) + s[0] * Math.sin(az)) * Math.cos(el) + n[0] * Math.sin(el),
      (t[1] * Math.cos(az) + s[1] * Math.sin(az)) * Math.cos(el) + n[1] * Math.sin(el),
      (t[2] * Math.cos(az) + s[2] * Math.sin(az)) * Math.cos(el) + n[2] * Math.sin(el)];
    if (bn) d = norm(add(d, bn, 1.5 * bl));                       // oblique hits throw the splash forward
    list.push({ vel: [d[0] * v, d[1] * v, d[2] * v], size: sp.sizeMin + (sp.sizeMax - sp.sizeMin) * rng() * rng() });
  }
  return list;
}
/** Continue a ricochet as a new, tumbling shot. Needs a hit and an impact() result that has exit.dir. */
function ricochet(hit, result, o) {
  if (!result || !result.exit || !result.exit.dir) return null;
  const e = result.exit, p = add(hit.point, hit.normal, 0.002);
  return new Shot(p, [e.dir[0] * e.speed, e.dir[1] * e.speed, e.dir[2] * e.speed], hit.ammo, Object.assign({ dragScale: e.dragScale, spinDrift: false }, o || {}));
}

// ---------------------------------------------------------------- what the shooter could see or hear
/** Whether a trace or wake could be seen from behind the rifle. Ball ammunition is not a tracer. */
function visibility(o) {
  o = o || {};
  const V = DATA.vis, a = ammoOf(o.ammo || 'M855'), rh = o.humidity != null ? o.humidity : cfg.env.humidity, mag = o.magnification || 1, light = o.light != null ? o.light : 1;
  const vap = rh >= V.vapRh ? V.vapMax * (rh - V.vapRh) / (1 - V.vapRh) * light : 0;
  return {
    tracer: !!a.tracer,
    trace: { visible: mag >= V.traceMag && light > 0.5, minRange: V.traceMinM, opacity: mag >= V.traceMag ? 0.08 * light : 0 },
    vapour: { visible: vap > 0.01, opacity: vap, life: V.vapLife },
    glintProbability: V.glint * light,
    nakedEye: !!a.tracer || vap > 0.01,
  };
}
/** Whitham N-wave of the passing bullet at missDistance (m): the supersonic crack. Null when subsonic. */
function sonicCrack(o) {
  const a = ammoOf(o.ammo || 'M855'), M = o.mach != null ? o.mach : o.speed / cfg.env.c; if (!(M > 1)) return null;
  const b = M * M - 1, x = Math.max(o.missDistance || 1, 0.05), P0 = cfg.env.pressureHPa * 100;
  const peak = 0.53 * P0 * Math.pow(b, 0.125) * a.diameterM / (Math.pow(x, 0.75) * Math.pow(a.lengthM, 0.25));
  return { peakPa: peak, peakDb: 20 * Math.log10(peak / 20e-6), duration: 1.82 * M * Math.pow(x, 0.25) * a.diameterM / (cfg.env.c * Math.pow(b, 0.375) * Math.pow(a.lengthM, 0.25)),
    coneHalfAngleDeg: Math.asin(1 / M) * 180 / Math.PI };
}

const api = {
  version: '1.0.0', DATA, configure, atmosphere, fire, Shot, intersect, impact, splash, ricochet,
  plateProps, plateKick, plateStep, zeroAngle, poi, visibility, sonicCrack, cdG7,
  get environment() { return cfg.env; },
  get zeros() { return Object.keys(DATA.zeros); },
  get ammo() { return Object.keys(DATA.ammo); },
  muzzleVelocity: mvOf,
};
return api;
});
