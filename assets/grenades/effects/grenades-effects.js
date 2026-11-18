/* openFPS grenades: game-level effects. Frag damage falloff, flash blind and deafen, smoke plume and obscuration.
   Browser: <script src="grenades-effects.js"></script> -> window.GrenadeEffects.   Node: require('./grenades-effects.js').
   Parameters come from effects.json (written by effects/sim.py). Metres, seconds, +Y up. */
(function (root, factory) { if (typeof module === 'object' && module.exports) module.exports = factory(); else root.GrenadeEffects = factory(); })(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  let E = null;
  async function load(url) { E = await (await fetch(url)).json(); return E; }
  function use(json) { E = json; return E; }
  function erf(x) {                       // Abramowitz and Stegun 7.1.26 is too coarse for the parity check; use the series / continued fraction
    const ax = Math.abs(x); let r;
    if (ax < 2.5) { let sum = ax, term = ax; for (let n = 1; n < 60; n++) { term *= -ax * ax / n; sum += term / (2 * n + 1); } r = 2 / Math.sqrt(Math.PI) * sum; }
    else { let f = 0; for (let n = 60; n >= 1; n--) f = n / 2 / (ax + f); r = 1 - Math.exp(-ax * ax) / Math.sqrt(Math.PI) / (ax + f); }
    return x < 0 ? -r : r;
  }

  /* Damage from a frag (or impact) grenade at distance r. opts: { prone, cover }. Returns { damage, lethal, casualty }. */
  function fragDamage(r, opts = {}) {
    const P = E.frag, rk = P.killing_radius_m, rc = P.casualty_radius_m, rz = P.zero_radius_m; let d;
    if (r <= rk) d = P.lethal_damage * Math.pow(P.centre_damage / P.lethal_damage, (rk - r) / rk);
    else if (r <= rc) d = P.lethal_damage * Math.pow(P.casualty_damage / P.lethal_damage, (r - rk) / (rc - rk));
    else if (r < rz) d = P.casualty_damage * (rz - r) / (rz - rc);
    else d = 0;
    if (opts.cover) d *= P.cover_factor;
    if (opts.prone && r > rk) d *= P.prone_factor;
    return { damage: d, lethal: d >= P.lethal_damage, casualty: d >= P.casualty_damage };
  }

  function spl(r, db0) { const P = E.flash; return (db0 === undefined || db0 === null ? P.bang_db_default : db0) - 20 * Math.log10(Math.max(r, 0.05) / P.ref_distance_m); }
  function illuminance(r) { return E.flash.candela / Math.pow(Math.max(r, 0.05), 2); }
  function viewFactor(deg) {
    const P = E.flash, a = P.view_full_deg, b = P.view_edge_deg;
    if (deg <= a) return 1; if (deg >= b) return P.view_behind;
    return P.view_behind + (1 - P.view_behind) * (0.5 + 0.5 * Math.cos(Math.PI * (deg - a) / (b - a)));
  }
  /* Flash and bang at distance r. opts: { viewDeg (angle between the view axis and the flash), ambient:'night'|'indoor'|'day',
     occluded, protectionDb, db0 }. Returns { lux, blind 0..1, whiteout_s, afterimage_s, spl_db, deafen 0..1, deaf_s }. */
  function flashEffect(r, opts = {}) {
    const P = E.flash, e0 = P.ambient_lux[opts.ambient || 'indoor'], e9 = illuminance(P.effect_radius_m);
    const e = illuminance(r) * viewFactor(opts.viewDeg || 0) * (opts.occluded ? P.occluded_flash : 1);
    const sb = e > e0 ? Math.min(1, Math.max(0, Math.log10(e / e0) / Math.log10(e9 / e0))) : 0;
    const L = spl(r, opts.db0) - (opts.protectionDb || 0) - (opts.occluded ? P.wall_db : 0), L9 = spl(P.effect_radius_m, opts.db0);
    const sd = Math.min(1, Math.max(0, (L - P.hearing_threshold_db) / (L9 - P.hearing_threshold_db)));
    return { lux: e, blind: sb, whiteout_s: sb > 0 ? P.whiteout_s[0] + P.whiteout_s[1] * sb : 0, afterimage_s: sb > 0 ? P.afterimage_s[0] + P.afterimage_s[1] * sb : 0,
             spl_db: L, deafen: sd, deaf_s: sd > 0 ? P.deaf_s[0] + P.deaf_s[1] * sd : 0 };
  }
  /* The same, from positions: eye position, unit view direction, flash position. */
  function flashAt(eye, viewDir, flashPos, opts = {}) {
    const d = [flashPos[0] - eye[0], flashPos[1] - eye[1], flashPos[2] - eye[2]], r = Math.hypot(d[0], d[1], d[2]) || 1e-6;
    const c = (d[0] * viewDir[0] + d[1] * viewDir[1] + d[2] * viewDir[2]) / r / (Math.hypot(viewDir[0], viewDir[1], viewDir[2]) || 1);
    return flashEffect(r, Object.assign({}, opts, { viewDeg: Math.acos(Math.max(-1, Math.min(1, c))) * 180 / Math.PI }));
  }

  function emission(t, burn) {
    const P = E.smoke; if (t < 0 || t > burn) return 0;
    const plateau = 1 / (burn - 0.5 * P.ramp_up_s - 0.5 * P.ramp_down_s);
    if (t < P.ramp_up_s) return plateau * t / P.ramp_up_s;
    if (t > burn - P.ramp_down_s) return plateau * (burn - t) / P.ramp_down_s;
    return plateau;
  }
  function emitted(t0, t1, burn, n = 20) { const h = (t1 - t0) / n; let s = 0; for (let i = 0; i < n; i++) s += (emission(t0 + i * h, burn) + emission(t0 + (i + 1) * h, burn)) / 2 * h; return s; }

  /* A smoke plume. variant: 'smoke-red' ... 'smoke-white'. opts: { burn (s, e.g. from GrenadeThrow.sampleBurn), origin, wind:[x,y,z] m/s }. setOrigin(pos) follows a grenade still in flight.
     step(dt) emits and moves puffs; opticalDepth(a, b) and transmission(a, b) give the obscuration along a sight line;
     puffs[] carries { pos, sigma, m } for drawing (opacity of a puff seen through its centre = 1 - exp(-m / (2 pi sigma^2))). */
  class SmokePlume {
    constructor(variant, opts = {}) {
      const key = variant === 'smoke-white' ? 'smoke-white' : 'smoke', P = E.smoke;
      this.colour = (E.colours[key][variant.split('-')[1]] || Object.values(E.colours[key])[0]).slice();
      this.Y = P.yield_m2[key]; this.burn = opts.burn; this.o = (opts.origin || [0, 0.06, 0]).slice(); this.wind = (opts.wind || [2, 0, 0]).slice();
      this.t = 0; this.next = 0; this.puffs = []; this.K = P.diffusivity[0] + P.diffusivity[1] * Math.hypot(this.wind[0], this.wind[1], this.wind[2]);
    }
    setOrigin(p) { this.o = [p[0], p[1], p[2]]; }                // call while the grenade is still moving: new puffs start where it is
    rate() { return emission(this.t, this.burn); }               // fraction of the output per second, for the hiss and the particle rate
    step(dt) {
      const P = E.smoke, t1 = this.t + dt;
      while (this.next < t1 && this.next < this.burn) {
        const a = this.next, b = Math.min(this.next + P.puff_interval_s, this.burn);
        this.puffs.push({ born: (a + b) / 2, m0: this.Y * emitted(a, b, this.burn), o: this.o.slice() }); this.next += P.puff_interval_s;
      }
      this.t = t1;
      for (const p of this.puffs) {
        const age = Math.max(0, this.t - p.born), rise = P.rise_mps * P.rise_tau_s * (1 - Math.exp(-age / P.rise_tau_s));
        p.pos = [p.o[0] + this.wind[0] * age, p.o[1] + this.wind[1] * age + rise, p.o[2] + this.wind[2] * age];
        p.sigma = Math.sqrt(P.sigma0_m * P.sigma0_m + 2 * this.K * age); p.m = p.m0 * Math.exp(-age / P.lifetime_s);
      }
      if (this.t > this.burn + 6 * P.lifetime_s) this.puffs.length = 0;
    }
    opticalDepth(a, b) {
      const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], L = Math.hypot(d[0], d[1], d[2]), u = [d[0] / L, d[1] / L, d[2] / L]; let tau = 0;
      for (const p of this.puffs) {
        if (!p.pos) continue;
        const w = [p.pos[0] - a[0], p.pos[1] - a[1], p.pos[2] - a[2]], s = w[0] * u[0] + w[1] * u[1] + w[2] * u[2], d2 = Math.max(0, w[0] * w[0] + w[1] * w[1] + w[2] * w[2] - s * s), sg = p.sigma;
        tau += p.m / (2 * Math.PI * sg * sg) * Math.exp(-d2 / (2 * sg * sg)) * 0.5 * (erf((L - s) / (sg * Math.SQRT2)) + erf(s / (sg * Math.SQRT2)));
      }
      return tau;
    }
    transmission(a, b) { return Math.exp(-this.opticalDepth(a, b)); }
  }
  return { load, use, fragDamage, flashEffect, flashAt, spl, illuminance, viewFactor, emission, SmokePlume, erf, get params() { return E; } };
});
