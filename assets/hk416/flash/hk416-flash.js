/* HK416 D14.5RS muzzle flash and smoke. Evaluates flash.json (built by sim.py). No dependencies, no three.js.
 *
 *   <script src="hk416-flash.js"></script>              -> window.HK416Flash
 *   const HK416Flash = require('./hk416-flash.js')      (Node)
 *   import './hk416-flash.js'                           -> globalThis.HK416Flash
 *
 *   await HK416Flash.load('flash.json')                 // or HK416Flash.use(parsedJson)
 *   const s  = HK416Flash.sample(t, { secondary })      // the flash at one instant (slow motion)
 *   const f  = HK416Flash.frame(t0, t1, { secondary })  // what one game frame collects (use this at 60 fps)
 *   const L  = HK416Flash.light(t0, t1, { secondary })  // just the light source: { intensity cd, rgb, colorK, position }
 *   const p  = HK416Flash.smoke(t, [wx, wy, wz])        // smoke puffs
 *   const on = HK416Flash.rollSecondary()               // does this shot get a secondary flash (a fireball)?
 *
 * Time t is SECONDS SINCE THE CHARGE IGNITED. action/ places ignition HK416Flash.ignitionAfterSear (8.51 ms) after
 * the sear releases the hammer, so with HK416Action's clock use  t = tAction - HK416Flash.ignitionAfterSear.
 * Nothing shows before the bullet leaves the crown at t = HK416Flash.bulletExit (0.976 ms).
 *
 * Frame: the gun frame of hk416.glb (metres, +Z muzzle, +Y up, +X shooter's left, origin on the bore axis at the
 * upper receiver's front face). Pass { frame: 'muzzle' } for positions relative to socket_muzzle instead.
 * Photometric units: intensity in candela (seen side-on), luminance in cd/m2, rgb is linear sRGB with luminance 1.
 *
 * A card is an additive quad:  emitted colour = rgb * luminance * texture value  (textures from HK416Flash.textures()).
 *   kind 'plume'  quad from `position` along `axis` for `length`, `width` across (texture u along the axis, bright face
 *                 at u = 0). billboard 'axis': turn it about its axis to face the camera.
 *   kind 'slot'   quad lying on the hider, centred at `position`, long side along `axis`, facing `normal` (one-sided).
 *   kind 'disc'   quad centred at `position` facing `normal`, `width` across (the open mouth, seen from the front).
 *   kind 'blob'   camera-facing quad centred at `position`, `width` across and `length` along `axis` (secondary flash).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.HK416Flash = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const lerp = (a, b, f) => a + (b - a) * f;
  function sampler(ts) {
    return (t) => {
      if (t <= ts[0]) return [0, 0];
      const n = ts.length - 1;
      if (t >= ts[n]) return [n - 1, 1];
      let i = 0; while (ts[i + 1] < t) i++;
      return [i, (t - ts[i]) / (ts[i + 1] - ts[i])];
    };
  }
  const pick = (arr, [i, f]) => lerp(arr[i], arr[i + 1], f);
  const pick3 = (arr, [i, f]) => [0, 1, 2].map((k) => lerp(arr[i][k], arr[i + 1][k], f));
  function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  // texture shapes (also used to turn intensity into luminance)
  const PLUME = (u, v) => Math.exp(-3 * u) * Math.exp(-0.5 * (v / (0.29 * (1 - 0.55 * u))) ** 2);   // v in units of `width`, card spans -1..1
  const BLOB = (u, v) => Math.exp(-4.5 * (u * u + v * v));                                           // u, v in -1..1
  const SLOT = (u) => 0.15 + 0.85 * u ** 1.2;                                                        // u = 0 rear end of the slot, 1 front
  function mean2(fn, u0, u1, v0, v1, n = 48) {
    let s = 0; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) s += fn(u0 + (u1 - u0) * (i + 0.5) / n, v0 + (v1 - v0) * (j + 0.5) / n);
    return s / (n * n);
  }
  const MEAN = { plume: mean2(PLUME, 0, 1, -1, 1), blob: mean2(BLOB, -1, 1, -1, 1), slot: mean2((u) => SLOT(u), 0, 1, 0, 1) };

  function create(data, opts = {}) {
    const ph = data.phases, tOf = sampler(ph.t_ms), tSec = sampler(ph.secondary.t_ms);
    const hider = data.hider, sm = data.smoke;
    const rand = mulberry32(opts.seed == null ? 416 : opts.seed);
    const slotLen = hider.slot_z_m[1] - hider.slot_z_m[0], slotW = hider.slot_width_m;

    function at(tMs, o = {}) {
      const cards = [];
      const add = (c, K) => { if (K != null && c.T_K == null) c.T_K = K; cards.push(c); };
      if (tMs >= 0 && tMs <= ph.t_ms[ph.t_ms.length - 1]) {
        const s = tOf(tMs);
        // primary: lit slots and the open mouth
        const p = ph.primary, Lp = pick(p.luminance, s), rgbP = pick3(p.rgb, s), Kp = pick(p.T_K, s);
        if (Lp > 0) {
          for (const sl of hider.slots) {
            const n = [sl.origin_m[0] / hider.outer_radius_m, sl.origin_m[1] / hider.outer_radius_m, 0];
            add({ id: 'slot_glow_' + sl.angle_from_up_deg, kind: 'slot', texture: 'slot', billboard: 'fixed', position: sl.origin_m, axis: [0, 0, 1], normal: n,
              length: slotLen, width: slotW, rgb: rgbP, luminance: Lp * 0.45 / MEAN.slot, intensity: Lp * 0.45 * slotLen * slotW * 0.5 }, Kp);
          }
          const r = hider.chamber_radius_m;
          cards.push({ id: 'mouth_glow', kind: 'disc', texture: 'blob', billboard: 'fixed', position: [0, 0, 0], axis: [0, 1, 0], normal: [0, 0, 1], length: 2 * r, width: 2 * r,
            rgb: rgbP, luminance: Lp, intensity: pick(p.intensity_from_front_cd, s), frontOnly: true });
        }
        // intermediate: glow behind the Mach disc of the mouth jet
        const m = ph.intermediate, Im = pick(m.intensity_cd, s);
        if (Im > 0) {
          const len = pick(m.length_mm, s) / 1e3, w = pick(m.width_mm, s) / 1e3;
          add({ id: 'muzzle_glow', kind: 'plume', texture: 'plume', billboard: 'axis', position: [0, 0, pick(m.start_z_mm, s) / 1e3], axis: [0, 0, 1], length: len, width: 2 * w,
            rgb: pick3(m.rgb, s), luminance: Im / (len * 2 * w * MEAN.plume), intensity: Im }, pick(m.T_K, s));
        }
        // slot jets
        const j = ph.slot_jet, Ij = pick(j.intensity_cd, s);
        if (Ij > 0) {
          const len = pick(j.length_mm, s) / 1e3, w = pick(j.width_mm, s) / 1e3, d = pick(j.dist_mm, s) / 1e3, rgbJ = pick3(j.rgb, s), Kj = pick(j.T_K, s);
          for (const sl of hider.slots) {
            add({ id: 'slot_jet_' + sl.angle_from_up_deg, kind: 'plume', texture: 'plume', billboard: 'axis', position: sl.origin_m.map((v, k) => v + sl.jet_dir[k] * d), axis: sl.jet_dir,
              length: len, width: 2 * w, rgb: rgbJ, luminance: Ij / (len * 2 * w * MEAN.plume), intensity: Ij }, Kj);
          }
        }
      }
      // secondary flash: only when the caller says this shot has one (see rollSecondary)
      const sec = ph.secondary;
      if (o.secondary && tMs > sec.t_ms[0] && tMs < sec.t_ms[sec.t_ms.length - 1]) {
        // o.secondary: true = the partial fireball usual through the hider; a number in (0, 1] = that share of the full one
        const k = typeof o.secondary === 'number' ? Math.min(1, Math.max(0, o.secondary)) : sec.hider_scale, q = Math.sqrt(k);
        const s = tSec(tMs), Is = pick(sec.intensity_cd_full, s) * k;
        if (Is > 0) {
          const len = pick(sec.length_mm_full, s) / 1e3 * q, dia = pick(sec.diameter_mm_full, s) / 1e3 * q;
          add({ id: 'secondary', kind: 'blob', texture: 'blob', billboard: 'camera', position: [0, 0, 0.02 + (pick(sec.centre_z_mm_full, s) / 1e3 - 0.02) * q], axis: [0, 0, 1], length: len, width: dia,
            rgb: sec.rgb, luminance: Is / (len * dia * MEAN.blob), intensity: Is, T_K: sec.T_K });
        }
      }
      // the light: the side-on total from the table (the cards above are its parts), plus the secondary flash if any
      let light = { intensity: 0, colorK: 1500, rgb: [1, 0.3, 0], position: [0, 0, 0.1] };
      const lt = data.light;
      if (tMs >= 0 && tMs <= lt.t_ms[lt.t_ms.length - 1]) { const s = tOf(tMs); light = { intensity: pick(lt.intensity_cd, s), colorK: pick(lt.colorK, s), rgb: pick3(lt.rgb, s), position: [0, 0, pick(lt.position_z_m, s)] }; }
      const sc = cards.find((c) => c.id === 'secondary');
      if (sc) { const a = light.intensity, b = sc.intensity, n = a + b; light = { intensity: n, colorK: (a * light.colorK + b * sec.T_K) / n, rgb: light.rgb.map((v, k) => (a * v + b * sc.rgb[k]) / n), position: [0, 0, (a * light.position[2] + b * sc.position[2]) / n] }; }
      return { tMs, cards, light };
    }

    // Time-average of at() over [t0, t1] ms: each card keeps its id; luminance and intensity are means over the interval,
    // geometry is intensity-weighted. This is what a camera frame (or the eye, for flashes under about 50 ms) collects.
    function frame(t0, t1, o = {}) {
      const span = t1 - t0, acc = new Map();
      let L = { I: 0, K: 0, rgb: [0, 0, 0], z: 0 };
      const end = Math.max(ph.t_ms[ph.t_ms.length - 1], o.secondary ? ph.secondary.t_ms[ph.secondary.t_ms.length - 1] : 0);
      let t = Math.max(t0, 0);
      const stop = Math.min(t1, end);
      while (t < stop) {
        const h = Math.min(t < 1.5 ? 0.02 : 0.25, stop - t), f = at(t + h / 2, o), w = h / span;
        for (const c of f.cards) {
          let a = acc.get(c.id);
          if (!a) { a = { ...c, position: [0, 0, 0], rgb: [0, 0, 0], length: 0, width: 0, luminance: 0, intensity: 0, _w: 0 }; acc.set(c.id, a); }
          const wi = c.intensity * w;
          a.intensity += wi; a.luminance += c.luminance * w; a._w += wi; a.length += c.length * wi; a.width += c.width * wi;
          for (let k = 0; k < 3; k++) { a.position[k] += c.position[k] * wi; a.rgb[k] += c.rgb[k] * wi; }
        }
        L.I += f.light.intensity * w; L.K += f.light.colorK * f.light.intensity * w; L.z += f.light.position[2] * f.light.intensity * w;
        for (let k = 0; k < 3; k++) L.rgb[k] += f.light.rgb[k] * f.light.intensity * w;
        t += h;
      }
      const cards = [];
      for (const a of acc.values()) {
        if (a._w <= 0) continue;
        a.length /= a._w; a.width /= a._w; a.position = a.position.map((v) => v / a._w); a.rgb = a.rgb.map((v) => v / a._w);
        // keep luminance consistent with the averaged size
        const area = a.kind === 'slot' ? a.length * a.width * 0.5 / 0.45 * MEAN.slot : a.length * a.width * (MEAN[a.texture] || 1);
        if (a.kind !== 'disc') a.luminance = a.intensity / area;
        delete a._w; cards.push(a);
      }
      const light = L.I > 0 ? { intensity: L.I, colorK: L.K / L.I, rgb: L.rgb.map((v) => v / L.I), position: [0, 0, L.z / L.I] } : { intensity: 0, colorK: 1500, rgb: [1, 0.3, 0], position: [0, 0, 0.1] };
      if (!o.secondary && L.I > 0) {           // exact luminous energy from the cumulative table
        const cum = (t) => (t <= 0 ? 0 : pick(data.light.cumulative_cd_s, tOf(t)));
        light.intensity = (cum(t1) - cum(t0)) / (span / 1e3);
      }
      return { t0, t1, cards, light };
    }

    // Does this shot have a secondary flash? Physical default: data.phases.secondary.probability.
    function rollSecondary(probability = ph.secondary.probability, rng = rand) { return rng() < probability; }

    // ---- smoke: the same entraining-puff sums as physics.puff_track
    function track(s, t, wind) {
      const a = sm.entrain_alpha, ka = sm.ambient_spread_m_s, rho = sm.rho_air;
      let pos = s.pos.slice(), R = s.r0, M = s.gas_mass + rho * 4 / 3 * Math.PI * R ** 3;
      let mom = s.dir.map((d) => d * s.impulse);
      const lift = 9.81 * s.heat / (1005.0 * sm.T_air_K);
      const tgt = t - s.t0;
      if (tgt <= 0) return null;
      let tt = 0, dt = 2e-6;
      while (tt < tgt) {
        const h = Math.min(dt, tgt - tt), u = mom.map((m) => m / M);
        const urel = Math.hypot(u[0] - wind[0], u[1] - wind[1], u[2] - wind[2]);
        const dM = rho * 4 * Math.PI * R * R * (a * urel + ka) * h;
        mom = [mom[0] + wind[0] * dM, mom[1] + wind[1] * dM + lift * h, mom[2] + wind[2] * dM];
        M += dM; pos = [pos[0] + u[0] * h, pos[1] + u[1] * h, pos[2] + u[2] * h];
        R = Math.cbrt(3 * (M - s.gas_mass) / (4 * Math.PI * rho));
        tt += h; dt = Math.min(dt * 1.05, 5e-3);
      }
      return { pos, R };
    }
    // -> [{ source, position, radius, tau, opacity, rgb }]: tau is the optical depth through the centre;
    // across the puff it falls as exp(-b^2 / (2 (radius/2)^2)). opacity = 1 - exp(-tau).
    function smoke(tSec, wind = [0, 0, 0], o = {}) {
      const out = [], k = sm.mass_extinction_m2_per_kg * (o.density == null ? 1 : o.density), w = sm.wake;
      for (const s of sm.sources) {
        const tr = track(s, tSec, wind);
        if (!tr) continue;
        const parts = [[1, w.head_share], ...w.fractions.map((f) => [f, w.share_each])];
        for (const [f, share] of parts) {
          const r = tr.R * (w.radius_floor + (1 - w.radius_floor) * f);
          const tau = k * s.smoke_mass * share / (2 * Math.PI * (r / 2) ** 2);
          out.push({ source: s.name, position: s.pos.map((p, i) => p + (tr.pos[i] - p) * f), radius: r, tau, opacity: 1 - Math.exp(-tau), rgb: sm.rgb, albedo: sm.albedo });
        }
      }
      return out;
    }

    // Residual sparks for one shot (inferred, see flash.json phases.sparks): straight streaks with drag-free flight.
    function sparks(seed = 1) {
      const r = mulberry32(seed), sp = ph.sparks, out = [];
      let n = 0; for (let L = Math.exp(-sp.mean_count), p = r(); p > L; p *= r()) n++;
      for (let i = 0; i < n; i++) {
        const th = Math.acos(1 - r() * (1 - Math.cos(sp.cone_half_angle_deg * Math.PI / 180))), az = r() * 2 * Math.PI;
        out.push({ dir: [Math.sin(th) * Math.cos(az), Math.sin(th) * Math.sin(az), Math.cos(th)], speed: lerp(sp.speed_m_s[0], sp.speed_m_s[1], r()),
          lifeMs: lerp(sp.life_ms[0], sp.life_ms[1], r()), intensity: lerp(sp.intensity_cd[0], sp.intensity_cd[1], r()), T_K: sp.T_K });
      }
      return out;
    }

    // ---- textures as plain RGBA arrays (white, value in alpha and in rgb): wrap in a DataTexture or putImageData
    function textures(size = 128) {
      const make = (w, h, fn) => { const d = new Uint8ClampedArray(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const v = Math.round(255 * Math.min(1, Math.max(0, fn((x + 0.5) / w, (y + 0.5) / h)))); d.set([v, v, v, v], (y * w + x) * 4); } return { width: w, height: h, data: d }; };
      const r = mulberry32(7), g = 9, grid = Array.from({ length: g * g }, () => r());
      const noise = (u, v) => { const x = u * (g - 1), y = v * (g - 1), i = Math.min(g - 2, x | 0), j = Math.min(g - 2, y | 0), fx = x - i, fy = y - j; const q = (a, b) => grid[b * g + a]; return lerp(lerp(q(i, j), q(i + 1, j), fx), lerp(q(i, j + 1), q(i + 1, j + 1), fx), fy); };
      return {
        plume: make(size, size, (u, v) => PLUME(u, v * 2 - 1)),                   // u (x) along the axis from the bright face, v (y) across
        blob: make(size, size, (u, v) => BLOB(u * 2 - 1, v * 2 - 1)),
        slot: make(size, Math.max(4, size >> 3), (u) => SLOT(u)),                   // u (x) from the rear of the slot to the front
        smoke: make(size, size, (u, v) => Math.exp(-((u * 2 - 1) ** 2 + (v * 2 - 1) ** 2) / (2 * 0.5 ** 2)) * (0.55 + 0.9 * noise(u, v)) / 1.45),   // quad spans 2 radii each way
        mean: { ...MEAN },
      };
    }

    return { data, at, frame, rollSecondary, smoke, sparks, textures, durationMs: ph.t_ms[ph.t_ms.length - 1], secondaryDurationMs: ph.secondary.t_ms[ph.secondary.t_ms.length - 1] };
  }

  // ------------------------------------------------------------------ the module (same shape as HK416Action)
  let M = null, D = null;
  const api = { ignitionAfterSear: 0, bulletExit: 0, socketMuzzle: [0, 0, 0] };
  function need() { if (!M) throw new Error('HK416Flash: call use(data) or load(url) first'); return M; }
  function use(data, opts) {
    D = data; M = create(data, opts || {});
    api.ignitionAfterSear = data.timing.ignition_after_sear_s; api.bulletExit = data.timing.bullet_exit_after_ignition_s;
    api.socketMuzzle = data.meta.socket_muzzle_gun_frame.slice(); api.data = data;
    api.duration = api.bulletExit + M.durationMs / 1e3; api.secondaryDuration = api.bulletExit + M.secondaryDurationMs / 1e3;
    api.secondaryProbability = data.phases.secondary.probability;
    return api;
  }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(function (d) { return use(d); });
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }
  const ms = (t) => (t - api.bulletExit) * 1e3;                       // seconds since ignition -> ms since bullet exit
  function place(o, r) {                                              // muzzle frame -> gun frame unless asked otherwise
    if (o && o.frame === 'muzzle') return r;
    const z = api.socketMuzzle[2], mv = (p) => [p[0], p[1], p[2] + z];
    if (r.cards) for (const c of r.cards) c.position = mv(c.position);
    if (r.light) r.light.position = mv(r.light.position);
    return r;
  }
  /* The flash at time t (s since ignition). opts.secondary: false (default) | true | 0..1 share of the full fireball. */
  function sample(t, opts) { need(); const r = M.at(ms(t), opts || {}); r.t = t; r.tau = t - api.bulletExit; return place(opts, r); }
  /* Time-average over [t0, t1] (s since ignition): what a camera frame, or the eye, collects. */
  function frame(t0, t1, opts) { need(); const r = M.frame(ms(t0), ms(t1), opts || {}); r.t0 = t0; r.t1 = t1; return place(opts, r); }
  /* Only the light source. light(t) is instantaneous; light(t0, t1) is the mean over a frame (same luminous energy). */
  function light(t0, t1, opts) {
    if (typeof t1 !== 'number') return sample(t0, t1).light;
    return frame(t0, t1, opts).light;
  }
  /* Smoke puffs at time t (s since ignition), wind in m/s in the gun frame. -> [{ source, position, radius, tau, opacity, rgb, albedo }] */
  function smoke(t, wind, opts) {
    need(); const p = M.smoke(t - api.bulletExit, wind || [0, 0, 0], opts || {});
    if (!(opts && opts.frame === 'muzzle')) for (const q of p) q.position = [q.position[0], q.position[1], q.position[2] + api.socketMuzzle[2]];
    return p;
  }
  Object.assign(api, { use, load, sample, frame, light, smoke,
    rollSecondary: function (p, rng) { return need().rollSecondary(p, rng); },
    sparks: function (seed) { return need().sparks(seed); },
    textures: function (size) { return need().textures(size); } });
  return api;
});
