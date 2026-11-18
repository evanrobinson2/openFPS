/* openFPS grenades: synthesised sound. ES module for the browser; also loads under node for the parity check.
     import GrenadeSound from './grenades-sound.js';
     const S = await GrenadeSound.build(audioContext);        // fetches params.json next to this module
     S.play('detonation_flash', { distance: 12 });            // or S.buffer(name), S.bounce(variant, surface, speed)
   Every sound is rendered from a recipe in params.json (written by sound/sim.py): Friedlander pulses, decaying
   modes and filtered noise. No recordings. Pressures are pascals at the recipe's reference distance. */
const P0 = 20e-6;
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function biquad(x, kind, fc, q, sr) {
  const w = 2 * Math.PI * fc / sr, cs = Math.cos(w), al = Math.sin(w) / (2 * q);
  let b0, b1, b2; if (kind === 'lp') { b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0; } else { b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0; }
  const a0 = 1 + al; let a1 = -2 * cs, a2 = 1 - al; b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
  const y = new Float64Array(x.length); let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) { const xi = x[i], yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = xi; y2 = y1; y1 = yi; y[i] = yi; }
  return y;
}
function envAt(env, t) {
  if (env.type === 'exp') return t < env.a ? t / env.a : Math.exp(-(t - env.a) / env.tau);
  const p = env.points; if (t <= p[0][0]) return p[0][1];
  for (let i = 1; i < p.length; i++) if (t <= p[i][0]) return p[i - 1][1] + (p[i][1] - p[i - 1][1]) * (t - p[i - 1][0]) / (p[i][0] - p[i - 1][0]);
  return p[p.length - 1][1];
}
/* Recipe -> Float64Array of pascals at the reference distance. The same arithmetic as sound/sim.py render(). */
function render(rec, sr) {
  const n = Math.round(rec.dur * sr), out = new Float64Array(n);
  for (const c of rec.components) {
    const i0 = Math.round(c.t0 * sr);
    if (c.type === 'pulse') {
      for (let i = i0; i < n; i++) { const tau = (i - i0) / sr; if (tau > 12 * c.T) break; out[i] += c.peak * (1 - tau / c.T) * Math.exp(-tau / c.T); }
    } else if (c.type === 'modes') {
      for (const [f, td, amp, ph] of c.modes) { const m = Math.min(n, i0 + Math.trunc(8 * td * sr) + 1); for (let i = i0; i < m; i++) { const tau = (i - i0) / sr; out[i] += amp * Math.exp(-tau / td) * Math.sin(2 * Math.PI * f * tau + ph); } }
    } else if (c.type === 'noise') {
      const m = Math.min(n - i0, Math.round(c.dur * sr)), rnd = mulberry32(c.seed); let x = new Float64Array(m);
      for (let i = 0; i < m; i++) x[i] = rnd() * 2 - 1;
      if (c.hp) x = biquad(x, 'hp', c.hp[0], c.hp[1], sr);
      if (c.lp) x = biquad(x, 'lp', c.lp[0], c.lp[1], sr);
      for (let i = 0; i < m; i++) out[i0 + i] += c.amp * x[i] * envAt(c.env, i / sr);
    }
  }
  return out;
}
const pa = (db) => P0 * Math.pow(10, db / 20), dB = (p) => 20 * Math.log10(Math.max(p, 1e-12) / P0);
function contactTime(P, body, surface, v) { const b = P.body[body], g = P.ground[surface]; return 2.87 * Math.pow(b.mass * b.mass / (b.radius * g.Estar * g.Estar * Math.max(v, 0.05)), 0.2); }
/* Bounce of a body on a surface at a normal speed (m/s), as throw events give it. Hertz contact sets the pitch and loudness. */
function bounceRecipe(P, body, surface, v) {
  const b = P.body[body], g = P.ground[surface], tc = contactTime(P, body, surface, v), tref = contactTime(P, 'frag', P.bounce.ref_surface, P.bounce.ref_speed);
  const amp = pa(P.bounce.ref_db_at_1m) * (b.mass * v / tc) / (P.body.frag.mass * P.bounce.ref_speed / tref);
  const fc = Math.min(1 / (2 * tc), 12000), hard = Math.min(1, fc / 1500);
  const comps = [{ type: 'modes', t0: 0.002, modes: [[fc, 1.5 * tc, amp / 0.733, 0]].concat(b.modes.map(([f, td, a]) => [f, td, amp * a * hard, 0])) }];
  if (g.scatter > 0) comps.push({ type: 'noise', t0: 0.002, dur: 0.12, seed: 7 + Math.trunc(v * 10), amp: amp * 0.6 * g.scatter, hp: [600, 0.7], lp: [5000, 0.7], env: { type: 'exp', a: 0.004, tau: 0.03 } });
  return { dur: 0.25, ref_distance_m: 1, components: comps, contact_time_ms: tc * 1e3 };
}
const bodyKey = (variant) => (variant.startsWith('smoke-') && variant !== 'smoke-white') ? 'smoke' : variant;
const leverKey = (variant) => variant === 'frag' || variant === 'impact' ? 'frag' : variant === 'flash' ? 'flash' : 'smoke';

class GrenadeSound {
  constructor(ac, params) { this.ac = ac; this.params = params; this.sr = params.sample_rate; this._cache = new Map(); }
  static async build(ac, url) { const u = url || new URL('./params.json', import.meta.url); return new GrenadeSound(ac, await (await fetch(u)).json()); }
  names() { return Object.keys(this.params.recipes); }
  /* { samples (pascals at ref), peakPa, peakDb, ref } for a named recipe, or for any recipe object. */
  pressure(nameOrRecipe) {
    const rec = typeof nameOrRecipe === 'string' ? this.params.recipes[nameOrRecipe] : nameOrRecipe, samples = render(rec, this.sr); let pk = 0;
    for (let i = 0; i < samples.length; i++) pk = Math.max(pk, Math.abs(samples[i]));
    return { samples, peakPa: pk, peakDb: dB(pk), ref: rec.ref_distance_m, loop: !!rec.loop };
  }
  /* AudioBuffer normalised to full scale, with the true level kept in buffer.info. */
  buffer(nameOrRecipe) {
    const key = typeof nameOrRecipe === 'string' ? nameOrRecipe : null; if (key && this._cache.has(key)) return this._cache.get(key);
    const p = this.pressure(nameOrRecipe), buf = this.ac.createBuffer(1, p.samples.length, this.sr), d = buf.getChannelData(0), k = p.peakPa > 0 ? 0.98 / p.peakPa : 0;
    for (let i = 0; i < d.length; i++) d[i] = p.samples[i] * k;
    buf.info = { peakDb: p.peakDb, ref: p.ref, loop: p.loop }; if (key) this._cache.set(key, buf); return buf;
  }
  bounce(variant, surface, normalSpeed) { return this.buffer(bounceRecipe(this.params, bodyKey(variant), surface, normalSpeed)); }
  leverRelease(variant) { return this.buffer('lever_release_' + leverKey(variant)); }
  leverLand(variant) { return this.buffer('lever_land_' + leverKey(variant)); }
  /* Level at the listener and the playback gain the mapping gives it (params.playback: game tuning, not physics). */
  levelAt(buf, distance) { return buf.info.peakDb - 20 * Math.log10(Math.max(distance, 0.05) / buf.info.ref); }
  gainFor(db) { const pb = this.params.playback; return Math.max(pb.floor, Math.min(1, Math.pow(10, (db - pb.full_scale_db) / (20 * pb.compression)))); }
  /* Play a buffer (or a recipe name) heard from `distance` metres: delay r / c, level by distance, low-pass for the air. */
  play(what, opts = {}) {
    const buf = typeof what === 'string' ? this.buffer(what) : what, r = opts.distance === undefined ? buf.info.ref : opts.distance, pb = this.params.playback, ac = this.ac;
    const src = ac.createBufferSource(); src.buffer = buf; src.loop = !!opts.loop;
    const lp = ac.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = pb.air_lp.fc0 / (1 + r / pb.air_lp.r_half);
    const g = ac.createGain(); g.gain.value = this.gainFor(this.levelAt(buf, r) - (opts.protectionDb || 0)) * (opts.gain === undefined ? 1 : opts.gain);
    src.connect(lp); lp.connect(g); g.connect(opts.destination || ac.destination);
    src.start((opts.when === undefined ? ac.currentTime : opts.when) + r / pb.speed_of_sound);
    return { source: src, gain: g, filter: lp };
  }
}
GrenadeSound.render = render; GrenadeSound.bounceRecipe = bounceRecipe; GrenadeSound.contactTime = contactTime; GrenadeSound.mulberry32 = mulberry32;
export default GrenadeSound;
export { render, bounceRecipe, contactTime };
