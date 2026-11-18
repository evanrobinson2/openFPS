/* Shotgun 590 exterior ballistics: a 1 oz rifled slug and nine-pellet 00 buckshot. No dependencies.
 *
 *   <script src="shotgun590-ballistics.js"></script>            -> window.Shotgun590Ballistics
 *   const B = require('./shotgun590-ballistics.js')              (Node)
 *
 *   await B.load('ballistics.json')          // or B.use(parsedJson)
 *   const shot = B.fire({ origin: [0, 1.5, 0], dir: [0, 0, 1], load: 'buck00', rng: B.rng(7) })
 *   shot.advance(dt)                          // steps every projectile; shot.projectiles[i] = { pos, vel, mass, t, alive }
 *   const hits = shot.trace([{ point: [0, 0, 20], normal: [0, 0, -1] }])   // where each projectile crosses a plane
 *   B.table('slug', [25, 50, 100])            // velocity, energy, time of flight, drop from the bore line
 *
 * Frame: metres and seconds, +Y up, the asset's frame when dir = [0, 0, 1] (+Z muzzle, +X shooter's left).
 * Numbers and sources are in ballistics.json (built by sim.py); README.md gives the checks and the limits.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.Shotgun590Ballistics = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, BC_SI = 0.45359237 / (0.0254 * 0.0254);
  function need() { if (!D) throw new Error('Shotgun590Ballistics: call use(data) or load(url) first'); return D; }
  function use(data) { D = data; return api; }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }
  /* Seedable generator (mulberry32) returning floats in [0, 1). Same sequence as sim.py. */
  function rng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var z = s;
      z = Math.imul(z ^ (z >>> 15), z | 1) >>> 0;
      z = (z ^ (z + (Math.imul(z ^ (z >>> 7), z | 61) >>> 0))) >>> 0;
      return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gauss2(r) {
    var u = Math.max(r(), 1e-12), v = r(), m = Math.sqrt(-2 * Math.log(u));
    return [m * Math.cos(2 * Math.PI * v), m * Math.sin(2 * Math.PI * v)];
  }
  function interp(tab, x) {
    if (x <= tab[0][0]) return tab[0][1];
    for (var i = 1; i < tab.length; i++) if (x <= tab[i][0]) { var a = tab[i - 1], b = tab[i]; return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]); }
    return tab[tab.length - 1][1];
  }
  function cd(model, mach) { var t = need().drag_tables; return interp(model === 'G1' ? t.G1 : t.sphere, mach); }
  function kDrag(L) {
    if (L.drag === 'G1') return Math.PI / (8 * L.bc_lb_in2 * BC_SI);
    var d = L.pellet_diameter_m; return (Math.PI * d * d / 4) / (2 * L.mass_kg);
  }
  function norm(v) { var n = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / n, v[1] / n, v[2] / n]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }

  /* acceleration of a projectile: drag against the air (wind in m/s, world frame) and gravity */
  function accel(k, model, vel, env) {
    var w = env.wind, rx = vel[0] - w[0], ry = vel[1] - w[1], rz = vel[2] - w[2], sp = Math.hypot(rx, ry, rz);
    var f = -k * env.rho * cd(model, sp / env.c) * sp;
    return [f * rx, f * ry - env.g, f * rz];
  }
  /* one classical Runge-Kutta step */
  function step(p, dt, env) {
    var k = p.k, m = p.drag, x = p.pos, v = p.vel;
    var a1 = accel(k, m, v, env);
    var v2 = [v[0] + 0.5 * dt * a1[0], v[1] + 0.5 * dt * a1[1], v[2] + 0.5 * dt * a1[2]], a2 = accel(k, m, v2, env);
    var v3 = [v[0] + 0.5 * dt * a2[0], v[1] + 0.5 * dt * a2[1], v[2] + 0.5 * dt * a2[2]], a3 = accel(k, m, v3, env);
    var v4 = [v[0] + dt * a3[0], v[1] + dt * a3[1], v[2] + dt * a3[2]], a4 = accel(k, m, v4, env);
    for (var i = 0; i < 3; i++) {
      x[i] += dt / 6 * (v[i] + 2 * v2[i] + 2 * v3[i] + v4[i]);
      v[i] += dt / 6 * (a1[i] + 2 * a2[i] + 2 * a3[i] + a4[i]);
    }
    p.t += dt;
  }
  function environment(o) {
    var d = need(), e = (o && o.env) || {};
    return { rho: e.rho != null ? e.rho : d.atmosphere.rho, c: e.c != null ? e.c : d.atmosphere.c, g: e.g != null ? e.g : d.gravity, wind: (o && o.wind) || [0, 0, 0] };
  }

  /* Fire one shell. opts: origin [x,y,z] (the muzzle), dir [x,y,z] (the bore), load 'buck00' | 'slug',
   * rng (a function returning [0,1); needed for the pellet scatter, default rng(1)), wind [x,y,z] m/s,
   * muzzleVelocity (override, m/s), spreadScale (multiplies the pattern's sigma; 1 = cylinder bore rule),
   * scatter (explicit [[ax, ay], ...] radians per pellet, overrides the generator). */
  function fire(opts) {
    var d = need(), o = opts || {}, L = d.loads[o.load || 'buck00'];
    if (!L) throw new Error('Shotgun590Ballistics: unknown load ' + o.load);
    var env = environment(o), dir = norm(o.dir || [0, 0, 1]), r = o.rng || rng(1), v0 = o.muzzleVelocity || L.muzzle_velocity;
    var up = Math.abs(dir[1]) > 0.99 ? [1, 0, 0] : [0, 1, 0], right = norm(cross(up, dir)), upv = cross(dir, right);
    var sigma = L.kind === 'shot' ? d.pattern.sigma_rad * (o.spreadScale != null ? o.spreadScale : 1) : 0, ps = [], k = kDrag(L);
    for (var i = 0; i < L.count; i++) {
      var g = o.scatter ? o.scatter[i] : (sigma ? gauss2(r).map(function (x) { return x * sigma; }) : [0, 0]);
      var dv = norm([dir[0] + right[0] * g[0] + upv[0] * g[1], dir[1] + right[1] * g[0] + upv[1] * g[1], dir[2] + right[2] * g[0] + upv[2] * g[1]]);
      ps.push({ pos: (o.origin || [0, 0, 0]).slice(), vel: [dv[0] * v0, dv[1] * v0, dv[2] * v0], mass: L.mass_kg, k: k, drag: L.drag, t: 0, alive: true, scatter: g });
    }
    var shot = {
      load: o.load || 'buck00', projectiles: ps, env: env,
      /* advance every live projectile by dt seconds (sub-stepped at 0.5 ms) */
      advance: function (dt) {
        var n = Math.max(1, Math.ceil(dt / 5e-4)), h = dt / n;
        for (var j = 0; j < ps.length; j++) if (ps[j].alive) for (var s = 0; s < n; s++) step(ps[j], h, env);
        return shot;
      },
      /* Where each projectile first crosses each plane {point, normal}; flies copies, so the shot itself is unchanged.
       * Returns [{ projectile, plane, pos, vel, speed, energy, t }] (energy in joules). maxTime defaults to 2 s. */
      trace: function (planes, maxTime) {
        var hits = [], h = 5e-4, T = maxTime || 2;
        for (var j = 0; j < ps.length; j++) {
          var p = { pos: ps[j].pos.slice(), vel: ps[j].vel.slice(), k: ps[j].k, drag: ps[j].drag, t: ps[j].t }, done = planes.map(function () { return false; }), left = planes.length;
          var side = planes.map(function (pl) { return (p.pos[0] - pl.point[0]) * pl.normal[0] + (p.pos[1] - pl.point[1]) * pl.normal[1] + (p.pos[2] - pl.point[2]) * pl.normal[2]; });
          while (left && p.t < T) {
            var prev = p.pos.slice(), pv = p.vel.slice(), pt = p.t; step(p, h, env);
            for (var q = 0; q < planes.length; q++) {
              if (done[q]) continue;
              var pl = planes[q], s1 = (p.pos[0] - pl.point[0]) * pl.normal[0] + (p.pos[1] - pl.point[1]) * pl.normal[1] + (p.pos[2] - pl.point[2]) * pl.normal[2];
              if ((side[q] > 0) !== (s1 > 0) || s1 === 0) {
                var u = side[q] / (side[q] - s1), pos = [0, 1, 2].map(function (i) { return prev[i] + (p.pos[i] - prev[i]) * u; }), vel = [0, 1, 2].map(function (i) { return pv[i] + (p.vel[i] - pv[i]) * u; });
                var sp = Math.hypot(vel[0], vel[1], vel[2]);
                hits.push({ projectile: j, plane: q, pos: pos, vel: vel, speed: sp, energy: 0.5 * ps[j].mass * sp * sp, t: pt + h * u }); done[q] = true; left--;
              }
              side[q] = s1;
            }
          }
        }
        return hits;
      }
    };
    return shot;
  }

  /* Downrange table along a level bore: [{ range, v, energy (one projectile, J), tof, drop }] for ranges in metres. */
  function table(loadKey, ranges) {
    var out = [], sh = fire({ load: loadKey, scatter: need().loads[loadKey].count > 1 ? need().loads[loadKey].count && Array.apply(null, Array(need().loads[loadKey].count)).map(function () { return [0, 0]; }) : null });
    var hits = sh.trace(ranges.map(function (r) { return { point: [0, 0, r], normal: [0, 0, -1] }; }), 3);
    for (var i = 0; i < hits.length; i++) if (hits[i].projectile === 0) out[hits[i].plane] = { range: ranges[hits[i].plane], v: hits[i].speed, energy: hits[i].energy, tof: hits[i].t, drop: -hits[i].pos[1] };
    return out;
  }

  /* Pellet holes on an upright plane at `range` metres, aimed along +Z from the origin: [[x, y], ...] in metres
   * (y includes the drop). opts as for fire(). */
  function pattern(loadKey, range, opts) {
    var o = Object.assign({}, opts || {}, { load: loadKey });
    return fire(o).trace([{ point: [0, 0, range], normal: [0, 0, -1] }]).map(function (h) { return [h.pos[0], h.pos[1]]; });
  }
  function extremeSpread(pts) {
    var m = 0; for (var i = 0; i < pts.length; i++) for (var j = i + 1; j < pts.length; j++) m = Math.max(m, Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])); return m;
  }
  /* Bore direction for a line of sight `los` (unit vector) with the named sight ('bead_flat' or 'bore'): the bore is
   * pitched up from the line of sight by the sight geometry. Returns { dir, muzzleBelowSight } (metres). */
  function aim(los, sight) {
    var d = need(), l = norm(los);
    if (sight === 'bore') return { dir: l, muzzleBelowSight: 0 };
    var a = d.sight_bead_flat.bore_above_sight_line_rad, up = Math.abs(l[1]) > 0.99 ? [1, 0, 0] : [0, 1, 0], right = norm(cross(up, l)), upv = cross(l, right);
    return { dir: norm([l[0] + upv[0] * Math.tan(a), l[1] + upv[1] * Math.tan(a), l[2] + upv[2] * Math.tan(a)]), muzzleBelowSight: d.sight_bead_flat.sight_line_height_at_muzzle_m };
  }

  var api = { use: use, load: load, rng: rng, gauss2: gauss2, fire: fire, table: table, pattern: pattern, extremeSpread: extremeSpread, aim: aim, cd: cd,
              get data() { return D; }, get loads() { return need().loads; } };
  return api;
});
