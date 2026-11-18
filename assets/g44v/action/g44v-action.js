/* G44 V action playback. Evaluates action.json (built by sim.py). No dependencies.
 *
 *   <script src="g44v-action.js"></script>             -> window.G44VAction
 *   const G44VAction = require('./g44v-action.js')      (Node)
 *   import './g44v-action.js'                           -> globalThis.G44VAction
 *
 *   await G44VAction.load('action.json')    // or G44VAction.use(parsedJson)
 *   const s = G44VAction.sample(t, { ammo: 'cci_standard_velocity', stance: 'two_hand', lastRound: false })
 *   // s.slideZ (m, <= 0: add to p01_slide.position.z)   s.springScale (scale of p03_recoil_spring along the bore)
 *   // s.firingPinZ (m, add to p04_firing_pin.position.z; rest pose = part-cocked)   s.chamberPressureMPa
 *   // s.slideHeldOpen, s.slideStopRot (rad about X for p27_slide_stop_lever)
 *   // s.recoil = { pos:[x,y,z] m, pitch rad (muzzle up), yaw rad, pivot:[x,y,z] }
 *
 * Time t is seconds since the trigger bar released the firing pin (the trigger break) of the first shot.
 * Frame: metres, +Z muzzle, +Y up, +X shooter's left (the frame of the model export).
 * To apply the recoil pose in a +Y-up, right-handed scene graph: rotate the pistol about `pivot` by rotation.x = -pitch, then translate by pos.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.G44VAction = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, RAD = Math.PI / 180;
  function need() { if (!D) throw new Error('G44VAction: call use(data) or load(url) first'); return D; }
  /* linear interpolation in a uniformly sampled track; clamps at both ends (same arithmetic as sim.py sample_py) */
  function lerp(arr, dt, t) {
    var u = t / dt, n = arr.length;
    if (!(u > 0)) return arr[0];
    if (u >= n - 1) return arr[n - 1];
    var i = Math.floor(u); return arr[i] + (arr[i + 1] - arr[i]) * (u - i);
  }
  function lerp0(arr, dt, t) { return (t < 0 || t > (arr.length - 1) * dt) ? 0 : lerp(arr, dt, t); }
  function use(data) { D = data; return api; }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url)))
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }
  function loadOf(name) { var L = need().loads[name || 'cci_standard_velocity']; if (!L) throw new Error('G44VAction: unknown ammo ' + name); return L; }
  function ammo() { return Object.keys(need().loads); }

  /* Pistol pose offset at time t for shots whose trigger broke at shotTimes (ascending). The shooter model is linear, so shots add. */
  function recoil(t, shotTimes, stance, name) {
    var d = need(), L = loadOf(name), st = d.stances[stance] ? stance : 'two_hand', r = L.recoil[st], dt = L.cycle.dt, z = 0, p = 0;
    for (var i = 0; i < shotTimes.length; i++) { var tt = t - shotTimes[i]; if (tt < 0) break; z += lerp0(r.z_mm, dt, tt); p += lerp0(r.pitch_up_deg, dt, tt); }
    var sock = d.brass.nominal.pos;   // unused; the pivot is the wrist under the grip
    return { pos: [0, 0, z * 1e-3], pitch: p * RAD, yaw: 0, pitchDeg: p, pivot: [0, -d.params.bore_height.value, 0.02] };
  }

  /* State of the mechanism and the pistol pose at time t.
   * opts.ammo: a key of ammo() (default 'cci_standard_velocity')   opts.stance: 'two_hand' (default) | 'one_hand'
   * opts.shotTimes: trigger-break times of the shots so far (default [0])   opts.lastRound: the magazine is empty after the last shot */
  function sample(t, opts) {
    var d = need(), o = opts || {}, L = loadOf(o.ammo), c = L.cycle, times = o.shotTimes || [0], i = 0;
    while (i + 1 < times.length && t >= times[i + 1]) i++;
    var tt = t - times[i], last = i === times.length - 1, m = d.mechanics;
    var mm = lerp(c.slide_mm, c.dt, tt), vel = lerp(c.slide_mps, c.dt, tt), held = false;
    if (o.lastRound && last && tt > L.events.max_travel && mm <= m.lock_open_mm && L.max_travel_mm >= m.lock_open_mm) { mm = m.lock_open_mm; vel = 0; held = true; }
    if (tt < 0) { mm = 0; vel = 0; }
    /* firing pin: forward of the rest (part-cocked) pose. Falls from the break position, is carried by the slide, and is caught again as the slide closes */
    var f = d.firing, pc = m.striker_precock_mm, brk = m.striker_break_mm, sm;
    if (tt < 0) sm = pc;
    else if (tt <= (f.striker_mm.length - 1) * f.dt) sm = lerp(f.striker_mm, f.dt, tt);
    else sm = held ? 0 : lerp(c.striker_recock_mm, c.dt, tt);
    var b = L.ballistics, tb = tt - b.t0, pr = (tb >= 0 && tb <= (b.chamber_MPa.length - 1) * b.dt) ? lerp(b.chamber_MPa, b.dt, tb) : 0;
    return {
      shotIndex: i, shotTime: tt, ammo: o.ammo || 'cci_standard_velocity',
      slideMm: mm, slideZ: -mm * 1e-3, slideVel: vel, springScale: 1 - mm / m.recoil_spring_free_mm,
      strikerMm: sm, firingPinZ: (pc - sm) * 1e-3,
      chamberPressureMPa: pr, slideHeldOpen: held, slideStopRot: held ? 3.7 * RAD : 0,
      outcome: L.outcome,
      recoil: recoil(t, times, o.stance, o.ammo)
    };
  }
  /* Events of one shot in order: [{name, t}] seconds after that shot's trigger break. */
  function events(name) {
    var e = loadOf(name).events, out = [];
    for (var k in e) if (k.indexOf('speed') < 0) out.push({ name: k, t: e[k] });
    return out.sort(function (a, b) { return a.t - b.t; });
  }
  /* Seedable generator (mulberry32) returning floats in [0, 1). Same sequence as sim.py. */
  function rng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0; var z = s;
      z = Math.imul(z ^ (z >>> 15), z | 1) >>> 0;
      z = (z ^ (z + (Math.imul(z ^ (z >>> 7), z | 61) >>> 0))) >>> 0;
      return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gauss(r) { return Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r()); }
  /* Initial state of an ejected case in the gun frame, relative to the pistol. Spawn it at events(ammo) 'eject'.
   * r: function returning uniform [0,1), e.g. G44VAction.rng(seed) or Math.random.  name: ammo key (scales the speed). */
  function ejectCase(r, name) {
    var b = need().brass, n = b.nominal, sc = b.scatter; r = r || Math.random;
    var k = name ? b.per_load_speed[name] / n.speed : 1;
    var sp = n.speed * k * Math.max(0.3, 1 + sc.speed_sigma * gauss(r)), az = (n.azimuth_deg + sc.azimuth_sigma_deg * gauss(r)) * RAD;
    var el = (n.elevation_deg + sc.elevation_sigma_deg * gauss(r)) * RAD, w = n.spin * Math.max(0.2, 1 + sc.spin_sigma * gauss(r));
    return { pos: n.pos.slice(), vel: [-sp * Math.cos(el) * Math.sin(az), sp * Math.sin(el), sp * Math.cos(el) * Math.cos(az) + n.carry_z * k], angVel: [0, -w, 0], resting: 0, bounces: 0 };
  }
  /* Advance a case by dt (use brass.scatter.step_dt for parity with sim.py). env.groundY: height of the ground in the same frame. */
  function stepCase(c, dt, env) {
    if (c.resting === 2) return c;
    var sc = need().brass.scatter, sp = Math.sqrt(c.vel[0] * c.vel[0] + c.vel[1] * c.vel[1] + c.vel[2] * c.vel[2]), i;
    for (i = 0; i < 3; i++) c.vel[i] -= sc.drag_k * sp * c.vel[i] * dt;
    c.vel[1] -= sc.gravity * dt;
    for (i = 0; i < 3; i++) c.pos[i] += c.vel[i] * dt;
    if (c.pos[1] <= env.groundY && c.vel[1] < 0) {
      c.pos[1] = env.groundY; c.vel[1] = -c.vel[1] * sc.restitution; var f = 1 - sc.friction;
      c.vel[0] *= f; c.vel[2] *= f; c.angVel[1] *= 0.5; c.bounces++;
      if (Math.abs(c.vel[1]) < 0.25) { c.vel = [0, 0, 0]; c.angVel = [0, 0, 0]; c.resting = 2; }
    }
    return c;
  }
  var api = { use: use, load: load, sample: sample, recoil: recoil, events: events, ammo: ammo, rng: rng, ejectCase: ejectCase, stepCase: stepCase,
              get data() { return D; } };
  return api;
});
