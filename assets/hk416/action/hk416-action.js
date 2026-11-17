/* HK416 D14.5RS action playback. Evaluates action.json (built by sim.py). No dependencies.
 *
 *   <script src="hk416-action.js"></script>            -> window.HK416Action
 *   const HK416Action = require('./hk416-action.js')    (Node)
 *   import './hk416-action.js'                          -> globalThis.HK416Action
 *
 *   await HK416Action.load('action.json')    // or HK416Action.use(parsedJson)
 *   const s = HK416Action.sample(t, { stance: 'ads', mode: 'semi' })
 *   // s.carrierZ (m, <= 0, add to bolt_carrier.position.z)   s.boltRot (rad)   s.hammer (rad)   s.firingPin (m)
 *   // s.recoil = { pos:[x,y,z] m, pitch rad (muzzle up), yaw rad (muzzle right), pivot:[x,y,z] }
 *
 * Time t is seconds since the sear released the hammer (the trigger break) for the first shot.
 * Frame: metres, +Z muzzle, +Y up, +X shooter's left (the frame of hk416.glb).
 * To apply the recoil pose with a +Y-up, right-handed scene graph: rotate the gun about `pivot` by
 * rotation.x = -pitch and rotation.y = -yaw, then translate by pos.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.HK416Action = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, RAD = Math.PI / 180;

  function need() { if (!D) throw new Error('HK416Action: call use(data) or load(url) first'); return D; }

  /* linear interpolation in a uniformly sampled track; clamps at both ends */
  function lerp(arr, dt, t) {
    var u = t / dt, n = arr.length;
    if (!(u > 0)) return arr[0];
    if (u >= n - 1) return arr[n - 1];
    var i = Math.floor(u), f = u - i;
    return arr[i] + (arr[i + 1] - arr[i]) * f;
  }
  /* as lerp, but zero outside the track (for impulse responses) */
  function lerp0(arr, dt, t) {
    if (t < 0 || t > (arr.length - 1) * dt) return 0;
    return lerp(arr, dt, t);
  }

  function use(data) { D = data; return api; }

  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }

  /* sear-release times of a burst of n shots at the simulated cyclic rate */
  function autoShotTimes(n) {
    var p = need().auto.period_s, out = [];
    for (var i = 0; i < n; i++) out.push(i * p);
    return out;
  }

  /* Gun pose offset at time t for shots whose sear released at shotTimes (seconds, ascending).
   * The shooter model is linear, so the burst is the sum of single-shot responses. */
  function recoil(t, shotTimes, stance) {
    var d = need(), st = stance === 'hip' ? 'hip' : 'ads', r = d.recoil.semi[st], dt = d.recoil.dt;
    var z = 0, p = 0, y = 0, f = 0;
    for (var i = 0; i < shotTimes.length; i++) {
      var tt = t - shotTimes[i];
      if (tt < 0) break;
      z += lerp0(r.z_mm, dt, tt); p += lerp0(r.pitch_up_deg, dt, tt); y += lerp0(r.yaw_right_deg, dt, tt); f += lerp0(r.support_force_N, dt, tt);
    }
    return { pos: [0, 0, z * 1e-3], pitch: p * RAD, yaw: y * RAD, pitchDeg: p, yawDeg: y, supportForce: f, pivot: d.recoil.stances[st].pivot.slice() };
  }

  /* The precomputed 10-round burst from the coupled simulation (for comparison with recoil()). */
  function recoilBurst10(t, stance) {
    var d = need(), st = stance === 'hip' ? 'hip' : 'ads', r = d.recoil.auto[st], dt = d.recoil.dt;
    var p = lerp(r.pitch_up_deg, dt, t), y = lerp(r.yaw_right_deg, dt, t);
    return { pos: [0, 0, lerp(r.z_mm, dt, t) * 1e-3], pitch: p * RAD, yaw: y * RAD, pitchDeg: p, yawDeg: y, supportForce: lerp(r.support_force_N, dt, t),
             pivot: d.recoil.stances[st].pivot.slice(), shotTimes: r.shot_times.slice() };
  }

  /* State of the mechanism and the gun pose at time t.
   * opts.stance: 'ads' (default) | 'hip'
   * opts.mode:   'semi' (default, one shot at t = 0) | 'auto'
   * opts.shots:  auto only, rounds in the burst (default: fire for as long as t runs)
   * opts.shotTimes: explicit sear-release times (overrides mode/shots), e.g. the game's own semi-auto shot log
   * opts.lastRound: true -> the carrier is held on the bolt catch after the final shot (empty magazine) */
  function sample(t, opts) {
    var d = need(), o = opts || {}, c = d.cycle, per = d.auto.period_s, times, i;
    if (o.shotTimes) times = o.shotTimes;
    else if (o.mode === 'auto') {
      var n = o.shots != null ? o.shots : Math.max(1, Math.floor(t / per) + 1);
      times = autoShotTimes(n);
    } else times = [0];
    i = 0;
    while (i + 1 < times.length && t >= times[i + 1]) i++;
    var tt = t - times[i], last = i === times.length - 1;
    var mm = lerp(c.carrier_mm, c.dt, tt), vel = lerp(c.carrier_mps, c.dt, tt), bolt = lerp(c.bolt_deg, c.dt, tt);
    var ham, pin, f = d.firing;
    if (tt >= 0 && tt <= (f.hammer_deg.length - 1) * f.dt) { ham = lerp(f.hammer_deg, f.dt, tt); pin = lerp(f.firing_pin_mm, f.dt, tt); }
    else { ham = lerp(c.hammer_deg, c.dt, tt); pin = lerp(c.firing_pin_mm, c.dt, tt); }
    if (tt < 0) { mm = 0; vel = 0; bolt = 0; ham = 0; pin = 0; }
    var held = false;
    if (o.lastRound && last && tt > d.events.times.max_travel && mm <= d.mechanics.hold_open_mm) {
      mm = d.mechanics.hold_open_mm; vel = 0; bolt = d.params.bolt_angle.value; held = true;
      ham = lerp(c.hammer_deg, c.dt, d.events.times.max_travel);
    }
    var b = d.ballistics, tb = tt - b.t0, pr = (tb >= 0 && tb <= (b.chamber_MPa.length - 1) * b.dt) ? lerp(b.chamber_MPa, b.dt, tb) : 0;
    return {
      shotIndex: i, shotTime: tt,
      carrierZ: -mm * 1e-3, carrierMm: mm, carrierVel: vel,
      boltRot: bolt * RAD, boltDeg: bolt,
      hammer: ham * RAD, hammerDeg: ham,
      firingPin: pin * 1e-3, firingPinMm: pin,
      chamberPressureMPa: pr,
      receiverForce: (tt >= 0) ? lerp0(c.receiver_force_N, c.dt, tt) : 0,
      boltHeldOpen: held,
      recoil: recoil(t, times, o.stance)
    };
  }

  /* Events of the shot in order: [{name, t}] seconds after that shot's sear release. */
  function events() {
    var e = need().events;
    return e.order.map(function (k) { return { name: k, t: e.times[k] }; });
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
  function gauss(r) { return Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r()); }

  /* Initial state of an ejected case in the gun frame, relative to the gun (add the gun's own velocity, and
   * rotate by the gun's world orientation). Spawn it brass.release_time_s after the shot's sear release.
   * r: function returning uniform [0,1), e.g. HK416Action.rng(seed) or Math.random. */
  function ejectCase(r) {
    var b = need().brass, n = b.nominal, sc = b.scatter; r = r || Math.random;
    var v = n.vel, sp = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]), az = Math.atan2(v[2], -v[0]), el = Math.asin(v[1] / sp);
    sp *= Math.max(0.3, 1 + sc.speed_sigma * gauss(r));
    az += sc.azimuth_sigma_deg * RAD * gauss(r);
    el += sc.elevation_sigma_deg * RAD * gauss(r);
    var w = n.angVel[1] * Math.max(0.2, 1 + sc.spin_sigma * gauss(r));
    var tx = sc.spin_tilt_sigma_deg * RAD * gauss(r), tz = sc.spin_tilt_sigma_deg * RAD * gauss(r);
    var py = n.pos[1] + sc.pos_sigma * gauss(r), pz = n.pos[2] + sc.pos_sigma * gauss(r);
    return {
      pos: [n.pos[0], py, pz],
      vel: [-sp * Math.cos(el) * Math.cos(az), sp * Math.sin(el), sp * Math.cos(el) * Math.sin(az)],
      angVel: [w * Math.sin(tx), w * Math.cos(tx) * Math.cos(tz), w * Math.sin(tz)],
      resting: 0, bounces: 0, mass: b.case.mass_kg, length: b.case.length_m, radius: b.case.radius_m
    };
  }

  /* Advance a case by dt (s) in a +Y-up frame: gravity, drag, a randomised cylinder bounce, then a slide to rest.
   * env: { groundY, surface: 'concrete' | 'dirt' | {restitution, friction, spin_keep, roll}, rng }
   * state.resting: 0 flying, 1 sliding on the ground, 2 at rest. Use dt = brass.step_dt (1/240 s) to match sim.py. */
  function stepCase(s, dt, env) {
    if (s.resting === 2) return s;
    var b = need().brass, surf = typeof env.surface === 'object' ? env.surface : b.surfaces[env.surface || 'concrete'];
    var r = env.rng || Math.random, p = s.pos, v = s.vel, w = s.angVel, g = b.gravity, rad = b.case.radius_m, k, sp, i;
    if (s.resting === 1) {
      sp = Math.hypot(v[0], v[2]); var dec = surf.roll * g * dt;
      if (sp <= dec) { v[0] = v[2] = 0; w[0] = w[1] = w[2] = 0; s.resting = 2; }
      else { k = (sp - dec) / sp; v[0] *= k; v[2] *= k; p[0] += v[0] * dt; p[2] += v[2] * dt; for (i = 0; i < 3; i++) w[i] *= k; }
      return s;
    }
    sp = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    var kd = 0.5 * b.air_density * b.case.cd_area_m2 * sp / b.case.mass_kg;
    v[0] -= kd * v[0] * dt; v[1] -= (g + kd * v[1]) * dt; v[2] -= kd * v[2] * dt;
    for (i = 0; i < 3; i++) p[i] += v[i] * dt;
    if (p[1] - rad < env.groundY && v[1] < 0) {
      p[1] = env.groundY + rad;
      var u1 = r(), u2 = r(), u3 = r();
      var e = surf.restitution * (0.55 + 0.45 * u1), vin = -v[1], vn = vin * e;
      var st = Math.hypot(v[0], v[2]), loss = surf.friction * (1 + e) * vin;
      k = st > 1e-9 ? Math.max(0, st - loss) / st : 0;
      var wm = Math.sqrt(w[0] * w[0] + w[1] * w[1] + w[2] * w[2]);
      var kick = 0.25 * wm * b.case.length_m * 0.5 * (2 * u2 - 1) * surf.spin_keep, ang = 2 * Math.PI * u3;
      v[0] = v[0] * k + kick * Math.cos(ang); v[2] = v[2] * k + kick * Math.sin(ang);
      for (i = 0; i < 3; i++) w[i] *= surf.spin_keep;
      if (vn < 0.25) { v[1] = 0; s.resting = 1; } else v[1] = vn;
      s.bounces = (s.bounces || 0) + 1;
      s.justBounced = vin;            /* impact speed, m/s: use it to scale the brass tinkle; clear it after reading */
    }
    return s;
  }

  var api = {
    use: use, load: load, sample: sample, recoil: recoil, recoilBurst10: recoilBurst10, autoShotTimes: autoShotTimes,
    events: events, ejectCase: ejectCase, stepCase: stepCase, rng: rng,
    get data() { return D; },
    get period() { return need().auto.period_s; },
    get rpm() { return need().auto.rpm; }
  };
  return api;
});
