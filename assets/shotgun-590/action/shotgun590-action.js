/* Shotgun 590 action: the pump mechanism as a state machine, its poses for the model, recoil playback and the
 * ejected hull. Evaluates action.json (built by sim.py). No dependencies.
 *
 *   <script src="shotgun590-action.js"></script>             -> window.Shotgun590Action
 *   const A = require('./shotgun590-action.js')               (Node)
 *
 *   await A.load('action.json')                // or A.use(parsedJson)
 *   const gun = A.create()                     // empty, action closed, safety on, hammer cocked
 *   gun.setSlide(1); gun.loadThroughPort('buck00'); gun.setSlide(0)    // manual p8: first shell through the port
 *   gun.insertShell('buck00')                  // manual p9: the rest into the magazine, action closed
 *   gun.setSafety(false); const ev = gun.pullTrigger()                 // -> [{ type: 'fire', load: 'buck00' }]
 *   gun.releaseTrigger(); gun.setSlide(1); gun.setSlide(0)             // pump: eject, feed, chamber, lock
 *   A.pose(gun.slide)                          // { slideZ, boltZ, boltLock, elevator } for the model's nodes
 *   A.recoil(t, 'buck00', 'shoulder')          // gun pose offset t seconds after the trigger break
 *
 * Every method that changes the gun returns the list of events it caused, in order; README.md lists them.
 * Frame: metres, +Z muzzle, +Y up, +X shooter's left (the model's frame).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.Shotgun590Action = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, RAD = Math.PI / 180;
  function need() { if (!D) throw new Error('Shotgun590Action: call use(data) or load(url) first'); return D; }
  function use(data) { D = data; return api; }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }
  function lerp(arr, dt, t) {
    var u = t / dt, n = arr.length;
    if (!(u > 0)) return arr[0];
    if (u >= n - 1) return arr[n - 1];
    var i = Math.floor(u), f = u - i;
    return arr[i] + (arr[i + 1] - arr[i]) * f;
  }
  function ev(name) { var e = need().cycle.events; for (var i = 0; i < e.length; i++) if (e[i].name === name) return e[i]; throw new Error('no event ' + name); }

  /* ------------------------------------------------------------------ the mechanism
   * slide: 0 = fully forward (in battery), 1 = fully rearward. A shell is { load, fired }.
   * tube[0] is the shell nearest the receiver: the last one pushed in and the next one out. */
  function create(opts) {
    var d = need(), o = opts || {}, S = d.cycle.stroke_mm;
    var X = { unlock: ev('unlock').slide_mm / S, cock: ev('hammer_cocked').slide_mm / S, eject: ev('eject').slide_mm / S, release: ev('shell_released').slide_mm / S,
              lift: ev('lift_done').slide_mm / S, feed: ev('feed').slide_mm / S, chamber: ev('chambered').slide_mm / S };
    var g = {
      slide: 0, safety: true, hammerCocked: true, actionLocked: true, triggerHeld: false, leverHeld: false,
      chamber: null, lifter: null, tube: [], capacity: o.capacity != null ? o.capacity : d.params.tube_capacity.value, lifterUp: false, shotsFired: 0,

      /* manual p5: rearward is ON (SAFE), forward is OFF (FIRE) */
      setSafety: function (on) { if (g.safety === !!on) return []; g.safety = !!on; return [{ type: 'safety', on: g.safety }]; },
      /* manual p6: holding the action lock lever lets the closed action be opened without pulling the trigger */
      holdActionLock: function (down) { g.leverHeld = !!down; return [{ type: 'action_lock_lever', down: g.leverHeld }]; },
      canOpen: function () { return g.slide > 0 || !g.actionLocked || g.leverHeld; },

      /* manual p9 and p20. The trigger must be let go and pulled again for each shot, and the hammer cannot fall
       * unless the action is fully closed: both are inferences (the manual describes neither case). */
      pullTrigger: function () {
        if (g.triggerHeld) return [];
        g.triggerHeld = true;
        if (g.safety) return [{ type: 'blocked', why: 'safety' }];
        if (g.slide > 0) return [{ type: 'blocked', why: 'action_open' }];
        if (!g.hammerCocked) return [{ type: 'blocked', why: 'hammer_down' }];
        g.hammerCocked = false; g.actionLocked = false;
        if (g.chamber && !g.chamber.fired) { g.chamber.fired = true; g.shotsFired++; return [{ type: 'hammer_fall' }, { type: 'fire', load: g.chamber.load }]; }
        return [{ type: 'hammer_fall' }, { type: 'click', why: g.chamber ? 'fired_hull_in_chamber' : 'empty_chamber' }];
      },
      releaseTrigger: function () { g.triggerHeld = false; return []; },

      /* Move the slide to x (0..1). The motion runs through every threshold between here and there, in order. */
      setSlide: function (x) {
        x = Math.min(1, Math.max(0, x)); var out = [], from = g.slide;
        if (x === from) return out;
        if (from === 0 && x > 0 && !g.canOpen()) return [{ type: 'blocked', why: 'action_locked' }];
        function crossed(th) { return x > from ? (from < th && x >= th) : (from > th && x <= th); }
        if (x > from) {                                  // rearward
          if (crossed(X.unlock)) out.push({ type: 'unlock' });
          if (crossed(X.cock) && !g.hammerCocked) { g.hammerCocked = true; out.push({ type: 'hammer_cocked' }); }
          if (crossed(X.eject)) {
            g.lifterUp = false;
            if (g.chamber) { out.push({ type: 'eject', shell: g.chamber, fired: g.chamber.fired }); g.chamber = null; }
          }
          if (crossed(X.release) && !g.lifter && g.tube.length) { g.lifter = g.tube.shift(); out.push({ type: 'shell_released', shell: g.lifter }); }
          if (x === 1) out.push({ type: 'rear_stop' });
        } else {                                         // forward
          if (crossed(X.lift) && g.lifter) { g.lifterUp = true; out.push({ type: 'lift' }); }
          if (crossed(X.feed) && g.lifter && g.lifterUp) out.push({ type: 'feed' });
          if (crossed(X.chamber)) {
            if (g.lifter && g.lifterUp && !g.chamber) { g.chamber = g.lifter; g.lifter = null; out.push({ type: 'chambered', shell: g.chamber }); }
            g.lifterUp = false;
          }
          if (x === 0) { g.actionLocked = g.hammerCocked; out.push({ type: 'locked', actionLocked: g.actionLocked }); }
        }
        g.slide = x; return out;
      },
      /* a full pump: back and forward. Returns the events of both strokes. */
      pump: function () { var a = g.setSlide(1); if (a.length && a[0].type === 'blocked') return a; return a.concat(g.setSlide(0)); },

      /* manual p9: load the magazine with the action closed */
      insertShell: function (loadKey) {
        if (g.slide !== 0) return [{ type: 'refused', why: 'close_the_action_first' }];
        if (g.tube.length >= g.capacity) return [{ type: 'refused', why: 'magazine_full' }];
        g.tube.unshift({ load: loadKey || 'buck00', fired: false }); return [{ type: 'shell_inserted', inTube: g.tube.length }];
      },
      /* manual p8: with the action open, the first shell goes through the ejection port onto the elevator */
      loadThroughPort: function (loadKey) {
        if (g.slide !== 1) return [{ type: 'refused', why: 'open_the_action_first' }];
        if (g.lifter || g.chamber) return [{ type: 'refused', why: 'elevator_occupied' }];
        g.lifter = { load: loadKey || 'buck00', fired: false }; return [{ type: 'shell_on_elevator' }];
      },
      /* manual p10: with the action closed, pressing the cartridge stop lets one shell out of the magazine */
      releaseFromMagazine: function () {
        if (g.slide !== 0) return [{ type: 'refused', why: 'close_the_action_first' }];
        if (!g.tube.length) return [{ type: 'refused', why: 'magazine_empty' }];
        return [{ type: 'shell_removed', shell: g.tube.shift(), inTube: g.tube.length }];
      },
      /* manual p10: with the action open, a shell lying on the elevator drops out when the port faces down */
      tipOutElevatorShell: function () {
        if (g.slide !== 1 || !g.lifter) return [{ type: 'refused', why: 'nothing_on_the_elevator' }];
        var s = g.lifter; g.lifter = null; return [{ type: 'shell_removed', shell: s, inTube: g.tube.length }];
      },
      rounds: function () { return g.tube.length + (g.lifter ? 1 : 0) + (g.chamber && !g.chamber.fired ? 1 : 0); }
    };
    return g;
  }

  /* ------------------------------------------------------------------ poses for the model's nodes
   * x = slide position 0..1; forward = true on the forward stroke (the elevator is up while a shell is fed).
   * slideZ and boltZ are offsets in metres along Z (<= 0) for slide_assembly + bolt_slide_group, and bolt_group;
   * boltLock and elevator are rotations in radians about the model's X axis for bolt_lock and elevator_group. */
  function pose(x, forward, feeding) {
    var c = need().cycle, S = c.stroke_mm, s = Math.min(1, Math.max(0, x)) * S, lm = c.lost_motion_mm;
    var lock = Math.min(1, s / lm) * c.kinematics.bolt_lock_deg_unlocked, el = 0;
    if (forward && feeding !== false) {
      var l0 = S, l1 = ev('lift_done').slide_mm, down = ev('chambered').slide_mm;
      el = s >= l1 ? (l0 - s) / (l0 - l1) : (s > down ? 1 : s / down);
      el *= c.kinematics.elevator_deg_raised;
    }
    return { slideZ: -s * 1e-3, boltZ: -Math.max(0, s - lm) * 1e-3, boltLock: lock * RAD, elevator: el * RAD, slideMm: s, boltMm: Math.max(0, s - lm) };
  }

  /* Slide position (0..1) and speed (m/s) at time t of a hand-driven stroke. opts.scale stretches the timing
   * (2 = half speed). Returns { x, speed, forward, done }. */
  function stroke(t, opts) {
    var p = need().cycle.profile, k = (opts && opts.scale) || 1, tb = p.back_s * k, td = p.dwell_s * k, tf = p.forward_s * k, e = p.exponent, S = need().cycle.stroke_mm * 1e-3;
    if (t <= 0) return { x: 0, speed: 0, forward: false, done: false };
    if (t < tb) return { x: Math.pow(t / tb, e), speed: e * S / tb * Math.pow(t / tb, e - 1), forward: false, done: false };
    if (t < tb + td) return { x: 1, speed: 0, forward: false, done: false };
    if (t < tb + td + tf) { var u = Math.max(0, (t - tb - td) / tf); return { x: 1 - Math.pow(u, e), speed: e * S / tf * Math.pow(u, e - 1), forward: true, done: false }; }
    return { x: 0, speed: 0, forward: true, done: true };
  }
  function strokeDuration(opts) { var p = need().cycle.profile; return (p.back_s + p.dwell_s + p.forward_s) * ((opts && opts.scale) || 1); }

  /* ------------------------------------------------------------------ the shot and the recoil
   * t is seconds since the trigger break. stance: 'shoulder' (default) | 'hip'.
   * Apply with a +Y-up scene graph: rotate the gun about `pivot` by rotation.x = -pitch, then translate by pos. */
  function recoil(t, loadKey, stance) {
    var d = need(), st = stance === 'hip' ? 'hip' : 'shoulder', r = d.recoil.loads[loadKey || 'buck00'][st], dt = d.recoil.dt;
    if (t < 0 || t > (r.z_mm.length - 1) * dt) return { pos: [0, 0, 0], pitch: 0, pitchDeg: 0, shoulderForce: 0, pivot: r.pivot.slice() };
    var p = lerp(r.pitch_up_deg, dt, t);
    return { pos: [0, 0, -lerp(r.z_mm, dt, t) * 1e-3], pitch: p * RAD, pitchDeg: p, shoulderForce: lerp(r.shoulder_force_N, dt, t), pivot: r.pivot.slice() };
  }
  /* Inside the barrel at t seconds after the trigger break: { pressureMPa, payloadTravel (m), payloadSpeed, gunForce (N), inBarrel } */
  function shot(t, loadKey) {
    var s = need().shots[loadKey || 'buck00'], tt = t - s.t0;
    if (tt < 0 || tt > (s.pressure_MPa.length - 1) * s.dt) return { pressureMPa: 0, payloadTravel: 0, payloadSpeed: tt < 0 ? 0 : s.muzzle_velocity, gunForce: 0, inBarrel: false };
    return { pressureMPa: lerp(s.pressure_MPa, s.dt, tt), payloadTravel: lerp(s.payload_travel_mm, s.dt, tt) * 1e-3, payloadSpeed: lerp(s.payload_speed, s.dt, tt), gunForce: lerp(s.gun_force_N, s.dt, tt), inBarrel: tt * 1e3 < s.barrel_time_ms };
  }

  /* ------------------------------------------------------------------ the ejected hull (same arithmetic as sim.py)
   * rng: a function returning [0, 1), e.g. rng(seed). slideSpeed in m/s at the moment of ejection. */
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
  function ejectHull(r, slideSpeed, port) {
    var h = need().hull, j = function () { return 1 + h.jitter * (2 * r() - 1); }, p = port || need().socket_eject, v = slideSpeed;
    return { pos: p.slice(), vel: [-h.side_factor * v * j(), h.up_factor * v * j(), -h.back_factor * v * j()], spin: h.spin_factor * v / (h.length / 2) * j(), resting: 0 };
  }
  /* env: { groundY, surface: 'concrete' | 'dirt' | 'grass' | 'wood' }. resting: 0 flying, 1 sliding, 2 at rest. */
  function stepHull(c, dt, env) {
    if (c.resting === 2) return c;
    var h = need().hull, s = h.surfaces[env.surface || 'concrete'], v = c.vel, g = 9.80665, sp = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]), k = h.drag_k * sp;
    v[0] -= k * v[0] * dt; v[1] -= (g + k * v[1]) * dt; v[2] -= k * v[2] * dt;
    for (var i = 0; i < 3; i++) c.pos[i] += v[i] * dt;
    var floor = env.groundY + h.radius;
    if (c.pos[1] <= floor) {
      c.pos[1] = floor;
      if (Math.abs(v[1]) > 0.35) { v[1] = -v[1] * s.e; var f = Math.max(0, 1 - s.mu * 0.5); v[0] *= f; v[2] *= f; c.spin *= 0.5; }
      else {
        v[1] = 0; c.resting = 1; var hh = Math.hypot(v[0], v[2]), dec = s.mu * g * dt;
        if (hh <= dec) { v[0] = v[2] = 0; c.resting = 2; c.spin = 0; } else { v[0] *= (hh - dec) / hh; v[2] *= (hh - dec) / hh; }
      }
    }
    return c;
  }

  var api = { use: use, load: load, create: create, pose: pose, stroke: stroke, strokeDuration: strokeDuration, recoil: recoil, shot: shot, rng: rng, ejectHull: ejectHull, stepHull: stepHull,
              events: function () { return need().cycle.events.slice(); }, get data() { return D; } };
  return api;
});
