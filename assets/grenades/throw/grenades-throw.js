/* openFPS grenades: throw, bounce, roll, fuse timing, cook-off and the game-only impact variant.
   Browser: <script src="grenades-throw.js"></script> -> window.GrenadeThrow.   Node: require('./grenades-throw.js').
   Frame: metres, seconds, +Y up; the ground is y = 0. Tables come from throw.json (written by throw/sim.py). */
(function (root, factory) { if (typeof module === 'object' && module.exports) module.exports = factory(); else root.GrenadeThrow = factory(); })(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  let T = null;                                   // throw.json
  const tableKey = (variant) => (variant.startsWith('smoke-') && variant !== 'smoke-white') ? 'smoke' : variant;   // smoke-red, ... share the coloured can's row

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  async function load(url) { T = await (await fetch(url)).json(); return T; }
  function use(json) { T = json; return T; }

  function acc(v, k, g) { const s = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); return [-k * s * v[0], -g - k * s * v[1], -k * s * v[2]]; }
  function rk4(p, v, k, g, dt) {
    const a1 = acc(v, k, g), v2 = [0, 1, 2].map((i) => v[i] + a1[i] * dt / 2);
    const a2 = acc(v2, k, g), v3 = [0, 1, 2].map((i) => v[i] + a2[i] * dt / 2);
    const a3 = acc(v3, k, g), v4 = [0, 1, 2].map((i) => v[i] + a3[i] * dt);
    const a4 = acc(v4, k, g);
    return [[0, 1, 2].map((i) => p[i] + dt * (v[i] + 2 * v2[i] + 2 * v3[i] + v4[i]) / 6), [0, 1, 2].map((i) => v[i] + dt * (a1[i] + 2 * a2[i] + 2 * a3[i] + a4[i]) / 6)];
  }

  /* A body in flight. opts: { pos:[x,y,z], vel:[x,y,z], surface:'packed_dirt', walls:[{ point, normal, surface }] }.
     step() advances one fixed step (constants.dt) and returns the events of that step:
     { type:'bounce', t, pos, speed, normalSpeed, surface } or { type:'rest', t, pos }. */
  class Flight {
    constructor(variant, opts) {
      this.variant = variant; this.body = T.variants[tableKey(variant)].body; this.p = opts.pos.slice(); this.v = opts.vel.slice();
      this.surface = opts.surface || 'packed_dirt'; this.walls = opts.walls || []; this.t = 0; this.mode = 'air'; this.apex = this.p[1]; this.bounces = 0;
    }
    step() {
      const C = T.constants, b = this.body, sf = T.surfaces[this.surface], rc = b.radius_m, dt = C.dt, ev = [];
      if (this.mode === 'rest') return ev;
      if (this.mode === 'air') {
        const [p1, v1] = rk4(this.p, this.v, b.k, C.g, dt), s0 = this.p[1] - rc, s1 = p1[1] - rc;
        if (s1 < 0 && s0 >= 0) {
          const f = s0 / (s0 - s1);
          this.p = [0, 1, 2].map((i) => this.p[i] + (p1[i] - this.p[i]) * f); this.v = [0, 1, 2].map((i) => this.v[i] + (v1[i] - this.v[i]) * f); this.t += f * dt;
          const vn = this.v[1], vtl = Math.hypot(this.v[0], this.v[2]), jn = -(1 + sf.e) * vn;
          ev.push({ type: 'bounce', t: this.t, pos: this.p.slice(), speed: Math.sqrt(vn * vn + vtl * vtl), normalSpeed: -vn, surface: this.surface });
          const keep = vtl > 1e-9 ? Math.max(0, 1 - sf.mu * jn / vtl) : 0, up = -sf.e * vn;
          this.v = [this.v[0] * keep, up, this.v[2] * keep]; this.p[1] = rc; this.bounces++;
          if (up < C.rest_speed) { this.mode = 'roll'; this.v[1] = 0; }
        } else {
          let hit = null;
          for (const w of this.walls) {                         // vertical or sloped planes: bounce only, no rolling on them
            const n = w.normal, d0 = (this.p[0] - w.point[0]) * n[0] + (this.p[1] - w.point[1]) * n[1] + (this.p[2] - w.point[2]) * n[2] - rc;
            const d1 = (p1[0] - w.point[0]) * n[0] + (p1[1] - w.point[1]) * n[1] + (p1[2] - w.point[2]) * n[2] - rc;
            if (d1 < 0 && d0 >= 0 && (!hit || d0 / (d0 - d1) < hit.f)) hit = { f: d0 / (d0 - d1), w };
          }
          if (hit) {
            const f = hit.f, n = hit.w.normal, ws = T.surfaces[hit.w.surface || 'concrete'];
            this.p = [0, 1, 2].map((i) => this.p[i] + (p1[i] - this.p[i]) * f); const v = [0, 1, 2].map((i) => this.v[i] + (v1[i] - this.v[i]) * f); this.t += f * dt;
            const vn = v[0] * n[0] + v[1] * n[1] + v[2] * n[2], vt = [0, 1, 2].map((i) => v[i] - vn * n[i]), vtl = Math.hypot(vt[0], vt[1], vt[2]), jn = -(1 + ws.e) * vn;
            ev.push({ type: 'bounce', t: this.t, pos: this.p.slice(), speed: Math.hypot(v[0], v[1], v[2]), normalSpeed: -vn, surface: hit.w.surface || 'concrete' });
            const keep = vtl > 1e-9 ? Math.max(0, 1 - ws.mu * jn / vtl) : 0;
            this.v = [0, 1, 2].map((i) => vt[i] * keep - ws.e * vn * n[i]); this.bounces++;
          } else { this.p = p1; this.v = v1; this.t += dt; if (this.p[1] > this.apex) this.apex = this.p[1]; }
        }
      } else {
        const s = Math.hypot(this.v[0], this.v[2]), a = sf.mu_r * b.roll_factor * C.g, s1 = Math.max(0, s - a * dt);
        if (s > 1e-12) { const d = (s + s1) / 2 * dt; this.p = [this.p[0] + this.v[0] / s * d, this.p[1], this.p[2] + this.v[2] / s * d]; this.v = [this.v[0] / s * s1, 0, this.v[2] / s * s1]; }
        this.t += dt;
        if (s1 <= 0) { this.mode = 'rest'; ev.push({ type: 'rest', t: this.t, pos: this.p.slice() }); }
      }
      return ev;
    }
    run(tMax = 30) { const all = []; while (this.t < tMax && this.mode !== 'rest') for (const e of this.step()) all.push(e); return all; }
  }

  /* Release velocity for a throw. power 1 = the release speed that reproduces the published average distance. */
  function releaseVelocity(variant, dir, power = 1) {
    const s = T.variants[tableKey(variant)].release_speed_mps * power, n = Math.hypot(dir[0], dir[1], dir[2]) || 1;
    return [dir[0] / n * s, dir[1] / n * s, dir[2] / n * s];
  }
  function referenceThrow(variant, surface) {
    const a = T.constants.throw.angle_deg * Math.PI / 180;
    return new Flight(variant, { pos: [0, T.constants.throw.height_m, 0], vel: releaseVelocity(variant, [Math.cos(a), Math.sin(a), 0]), surface });
  }
  function sampleDelay(variant, rnd) { const w = T.variants[tableKey(variant)].delay_window_s; return w ? w[0] + (w[1] - w[0]) * (rnd() + rnd()) / 2 : null; }
  function sampleBurn(variant, rnd) {
    const e = T.variants[tableKey(variant)], w = e.burn_window_s; if (!w) return null;
    if (e.burn_mean_s) return w[0] + (w[1] - w[0]) * Math.pow(rnd(), (w[1] - w[0]) / (e.burn_mean_s - w[0]) - 1);
    return w[0] + (w[1] - w[0]) * (rnd() + rnd()) / 2;
  }

  /* The handling sequence a player performs, as a game state machine:
       pullPin() -> releaseLever() (the delay starts; holding on after this is "cooking") -> throwFrom(pos, vel) -> update(dt)
     update returns events: bounce, rest, 'function' (detonation, or ignition for smoke) with { inHand }, and 'burnout' for smoke.
     The impact variant has no delay: after game.arm_time_s in flight it functions on its first contact faster than
     game.min_contact_speed_mps, or at game.self_timeout_s. All three are game tuning. */
  class Grenade {
    constructor(variant, opts = {}) {
      this.variant = variant; this.key = tableKey(variant); this.entry = T.variants[this.key]; this.rnd = mulberry32(opts.seed === undefined ? 1 : opts.seed);
      this.state = 'safe'; this.t = 0; this.tLever = null; this.tThrow = null; this.flight = null; this.pos = opts.pos ? opts.pos.slice() : [0, 0, 0];
      this.delay = this.entry.delay_window_s ? sampleDelay(variant, this.rnd) : null; this.burn = sampleBurn(variant, this.rnd); this.tFunction = null;
      this.surface = opts.surface || 'packed_dirt'; this.walls = opts.walls || [];
    }
    pullPin() { if (this.state === 'safe') this.state = 'pin_pulled'; return this; }
    releaseLever() { if (this.state === 'pin_pulled' || this.state === 'flying_held') { this.tLever = this.t; this.state = this.flight ? 'flying' : 'cooking'; } return this; }
    throwFrom(pos, vel) {
      if (this.state === 'safe') return this;                                   // a safe grenade can be thrown; nothing will happen
      this.flight = new Flight(this.variant, { pos, vel, surface: this.surface, walls: this.walls }); this.tThrow = this.t;
      if (this.tLever === null) this.tLever = this.t;                           // the lever leaves as the hand opens
      this.state = 'flying'; return this;
    }
    remaining() { return this.delay === null || this.tLever === null ? null : Math.max(0, this.tLever + this.delay - this.t); }
    update(dt) {
      const out = []; if (this.state === 'done' || this.state === 'safe') return out;
      const tEnd = this.t + dt, C = T.constants;
      while (this.t < tEnd - 1e-12) {
        let fev = [];
        if (this.flight) { fev = this.flight.step(); this.pos = this.flight.p.slice(); }
        this.t += C.dt;
        for (const e of fev) {
          e.t = this.t; out.push(e);
          if (this.entry.game && this.tFunction === null && e.type === 'bounce' && this.t - this.tThrow >= this.entry.game.arm_time_s && e.normalSpeed >= this.entry.game.min_contact_speed_mps) this._function(out, 'contact');
        }
        if (this.tFunction === null && this.tLever !== null) {
          if (this.delay !== null && this.t - this.tLever >= this.delay) this._function(out, 'delay');
          else if (this.entry.game && this.tThrow !== null && this.t - this.tThrow >= this.entry.game.self_timeout_s) this._function(out, 'timeout');
        }
        if (this.tFunction !== null && this.burn !== null && this.state === 'burning' && this.t - this.tFunction >= this.burn) { this.state = 'done'; out.push({ type: 'burnout', t: this.t, pos: this.pos.slice() }); }
        if (this.state === 'done') break;
      }
      return out;
    }
    _function(out, cause) {
      this.tFunction = this.t; const smoke = this.entry.burn_window_s !== undefined;
      out.push({ type: 'function', kind: smoke ? 'ignite' : 'detonate', cause, t: this.t, pos: this.pos.slice(), inHand: !this.flight, burn: this.burn });
      this.state = smoke ? 'burning' : 'done';
    }
  }
  return { load, use, mulberry32, Flight, Grenade, releaseVelocity, referenceThrow, sampleDelay, sampleBurn, tableKey, get tables() { return T; } };
});
