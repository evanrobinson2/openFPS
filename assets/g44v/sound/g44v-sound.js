// G44 V simulated sound, version 2: browser synthesis from params.json (written by sim.py).
// A port of "stage B" of sound/sim.py: the same tables, the same named random streams, the same arithmetic. Nothing here is a recording.
//
//   import G44VSound from './sound/g44v-sound.js';
//   const S = await G44VSound.build(audioContext);                 // loads params.json next to this file
//   S.shot('cci_standard_velocity')                                -> AudioBuffer: free field, shooter's ear, peak at -1 dBFS
//   S.shot('cci_mini_mag', { perspective: 'bystander', ground: true })   // ground: reflection and diffuse scatter of open ground
//   S.mech('slide_rack' | 'slide_release' | 'slide_lock_open' | 'trigger' | 'dry_fire' | 'magazine_out' | 'magazine_in' | 'case_ground')
//   S.ir('indoor_range' | 'outdoor_berm')                          -> AudioBuffer impulse response (direct path = first sample)
//   S.chain({ overlay: 'indoor_range', hpd: false, ear: true })    -> { input, output, set(opts) }   (overlay null = no room)
//   S.info(buffer)                                                 -> { peak_pa, peak_db_spl, pa_per_fullscale }: the true simulated level
//   S.loads, S.perspectives, S.clips, S.overlays, S.params;  S.raw.dry / mech / ir -> Float64Array in pascals (IR: units), for tests
//
// Playback is normalised: 157 dB at the ear cannot be reproduced, so every buffer is scaled to -1 dBFS and S.info() carries the true level.
// chain()'s 'ear' is the playback mapping (not physics). In life the ground echo is 138 dB and the action 122 dB: loud sounds. Played 70 dB or more
// below the real level they fall under the room's noise and only the blast is left, as a click. 'ear' therefore (1) lifts the bass by the difference
// between the equal-loudness contours at the real and the played level (low shelf, +10 dB below 150 Hz) and (2) compresses the level with
// y = asinh(k x) / asinh(k), k = params.ear_map_k: about 2:1 over the top 30 dB, a fixed lift below. sim.py ear_map() is the same mapping.
// 'hpd' is a two-shelf approximation of an earmuff (about 24 dB NRR, the minimum the manual asks for, p. 13).

import '../../../shared/cinematic-sound/cinematic-sound.js';   // -> globalThis.OpenFPSCinematicSound (the shared cinematic synthesis)

const P_REF = 20e-6, CS = globalThis.OpenFPSCinematicSound;
// Simulation values the cinematic design reads that are not in params.json. Copied from action/action.json (pistol muzzle energy and velocity,
// the guessed charge mass); shared/cinematic-sound/check.mjs fails if they drift. Bore 5.6 mm and barrel 102 mm: the maker's table
// (notes/MANUAL_NOTES.md). cyclic_period_s: the simulation's trigger reset time, the fastest a second shot can follow.
const CINE_SIM = {
  common: { bore_mm: 5.6, barrel_mm: 102, bullet_diam_mm: 5.7, bullet_len_mm: 11.6, cyclic_period_s: 0.13 },
  cci_standard_velocity: { muzzle_energy_J: 95.3, muzzle_velocity: 271.24, gas_mass_g: 0.085 },
  cci_mini_mag: { muzzle_energy_J: 116.4, muzzle_velocity: 299.64, gas_mass_g: 0.11 },
  cci_quiet_22: { muzzle_energy_J: 44.7, muzzle_velocity: 185.62, gas_mass_g: 0.045 },
};
const fnv1a = (s) => { let h = 0x811c9dc5; for (const c of new TextEncoder().encode(s)) { h ^= c; h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; };
class Rng { // mulberry32; identical to sim.py
  constructor(name) { this.a = fnv1a(name); }
  next() { this.a = (this.a + 0x6d2b79f5) >>> 0; let t = this.a; t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0; t = (t ^ (t + (Math.imul(t ^ (t >>> 7), t | 61) >>> 0))) >>> 0; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  gauss() { const a = this.next(), b = this.next(); return Math.sqrt(-2 * Math.log(a + 1e-12)) * Math.cos(2 * Math.PI * b); }
}
function makeCore(P) {
  const fs = P.fs;
  function addImpact(buf, ev, t0, seed) {
    const te = t0 + ev.t, nz = ev.noise; let tmax = nz.tau; for (const m of ev.modes) tmax = Math.max(tmax, m.tau); tmax *= 7;
    const n0 = Math.max(0, Math.floor(te * fs)), n1 = Math.min(buf.length, n0 + Math.floor(tmax * fs) + 2), rng = new Rng(seed); let z = 0;
    for (let n = n0; n < n1; n++) {
      const t = n / fs - te; if (t < 0) continue;
      let x = 0; for (const m of ev.modes) x += m.a * Math.exp(-t / m.tau) * Math.sin(2 * Math.PI * m.f * t);
      z += nz.lp * (rng.gauss() - z); buf[n] += x + nz.a * Math.exp(-t / nz.tau) * z;
    }
  }
  function addFriction(buf, fr, t0, seed) {
    const rng = new Rng(seed), n0 = Math.floor((t0 + fr.t) * fs), N = fr.env.length; let z = 0, y = 0;
    for (let i = 0; i < (N - 1) * fr.step; i++) {
      const k = Math.floor(i / fr.step), u = (i - k * fr.step) / fr.step, e = fr.env[k] + (fr.env[k + 1] - fr.env[k]) * u, g = rng.gauss();
      z += fr.lp * (g - z); y += fr.hp * (z - y);
      if (n0 + i >= 0 && n0 + i < buf.length) buf[n0 + i] += e * (z - y) * 2.0;
    }
  }
  function sourceBlast(L, n) { const buf = new Float64Array(n), tb = L.blast; for (let i = 0; i < tb.length; i++) if (L.n_blast + i >= 0 && L.n_blast + i < n) buf[L.n_blast + i] += tb[i]; return buf; }
  function sourceMech(events, friction, n, t0, seed) {
    const buf = new Float64Array(n); events.forEach((ev, j) => addImpact(buf, ev, t0, `${seed}|${j}`));
    if (friction) addFriction(buf, friction, t0, seed + '|friction'); return buf;
  }
  // out += src convolved with kernel k, shifted by nd samples, times g (only where src is not zero)
  function addConv(out, src, k, nd, g) {
    const N = out.length, K = k.length;
    for (let i = 0; i < src.length; i++) { const s = src[i]; if (s === 0) continue; const b = nd + i, j0 = Math.max(0, -b), j1 = Math.min(K, N - b); for (let j = j0; j < j1; j++) out[b + j] += g * s * k[j]; }
  }
  function scatterKernel(sc, seed) {
    const rng = new Rng(seed), k = new Float64Array(sc.amp.length * sc.bin); let z = 0;
    for (let i = 0; i < k.length; i++) { const g = rng.gauss(); z += 0.2 * (g - z); k[i] = sc.amp[Math.floor(i / sc.bin)] * (g - z) * 1.118; }
    return k;
  }
  function parts(L, ps, field, seed) {
    const n = Math.floor(P.dur_shot * fs), out = new Float64Array(n), sb = sourceBlast(L, n), sm = sourceMech(L.mech || [], L.friction, n, 0, 'mech|' + seed);
    addConv(out, sb, ps.blast.direct.fir, ps.blast.direct.n, ps.blast.direct.gain); addConv(out, sm, ps.mech.direct.fir, ps.mech.direct.n, ps.mech.direct.gain);
    if (field) {
      addConv(out, sb, ps.blast.ground.fir, ps.blast.ground.n, ps.blast.ground.gain); addConv(out, sm, ps.mech.ground.fir, ps.mech.ground.n, ps.mech.ground.gain);
      if (ps.scatter) addConv(out, sb, scatterKernel(ps.scatter, 'scatter|' + seed), ps.scatter.n0, 1);
    }
    return out;
  }
  const dry = (load, persp = 'shooter', field = false) => parts(P.loads[load], P.perspectives[persp], field, load);
  function mech(clip, persp = 'shooter') {
    const C = P.clips[clip], n = Math.floor(P.dur_clip * fs), out = new Float64Array(n), pth = P.perspectives[persp].mech.direct;
    addConv(out, sourceMech(C.events, C.friction, n, 0.002, 'clip|' + clip), pth.fir, pth.n, pth.gain); return out;
  }
  function ir(overlay) {
    const O = P.overlays[overlay], tl = O.tail, n = Math.floor((tl.t0 + tl.rt60 * 1.1) * fs) + 1, h = new Float64Array(n); h[0] = 1;
    if (O.ground) { const g = O.ground; g.fir.forEach((v, i) => { if (g.n + i > 0 && g.n + i < n) h[g.n + i] += g.gain * v; }); }
    if (O.scatter) {
      const sc = P.perspectives.shooter.scatter, k = scatterKernel(sc, 'scatter|ir'), gd = P.perspectives.shooter.blast.direct, n0 = sc.n0 - gd.n - P.fir_centre;
      for (let i = 0; i < k.length; i++) if (n0 + i > 0 && n0 + i < n) h[n0 + i] += k[i] / gd.gain;
    }
    for (const tp of O.taps) { const k = Math.floor(tp.delay * fs + 0.5); if (k > 0 && k < n) h[k] += tp.gain; }
    const rng = new Rng('ir|' + overlay), k0 = Math.floor(tl.t0 * fs); let z = 0;
    for (let k = k0; k < n; k++) { const t = (k - k0) / fs; z += tl.lp * (rng.gauss() - z); h[k] += tl.level * z * Math.exp(-6.907755 * t / tl.rt60); }
    return h;
  }
  // one shot's blast and its action noise apart (free field), for the cinematic layers; dry() is unchanged
  function dryParts(load, persp = 'shooter') {
    const L = P.loads[load], ps = P.perspectives[persp], n = Math.floor(P.dur_shot * fs), blast = new Float64Array(n), m = new Float64Array(n);
    addConv(blast, sourceBlast(L, n), ps.blast.direct.fir, ps.blast.direct.n, ps.blast.direct.gain); addConv(m, sourceMech(L.mech || [], L.friction, n, 0, 'mech|' + load), ps.mech.direct.fir, ps.mech.direct.n, ps.mech.direct.gain);
    return { blast, mech: m };
  }
  return { dry, mech, ir, dryParts };
}
async function build(ctx, opts = {}) {
  const url = opts.params || new URL('params.json', import.meta.url), P = opts.data || await (await fetch(url)).json(), core = makeCore(P), levels = new WeakMap();
  function toBuffer(x, normalise) {
    let pk = 0; for (let i = 0; i < x.length; i++) pk = Math.max(pk, Math.abs(x[i]));
    const g = normalise ? Math.pow(10, -1 / 20) / (pk || 1) : 1, b = ctx.createBuffer(1, x.length, P.fs), d = b.getChannelData(0);
    for (let i = 0; i < x.length; i++) d[i] = x[i] * g;
    levels.set(b, { peak_pa: pk, peak_db_spl: 20 * Math.log10(pk / P_REF), pa_per_fullscale: 1 / g }); return b;
  }
  const K = P.ear_map_k || 30, curve = new Float32Array(16385);       // input -1..1 is half scale: curve(u) = asinh(2 K u) / asinh(K)
  for (let i = 0; i < curve.length; i++) curve[i] = Math.asinh(2 * K * (i / 8192 - 1)) / Math.asinh(K);
  let G = null;
  const S = {
    params: P, loads: Object.keys(P.loads), perspectives: Object.keys(P.perspectives), clips: Object.keys(P.clips), overlays: Object.keys(P.overlays), raw: core,
    realShot: (load = 'cci_standard_velocity', o = {}) => toBuffer(core.dry(load, o.perspective || 'shooter', !!o.ground), true),
    realMech: (clip, o = {}) => toBuffer(core.mech(clip, o.perspective || 'shooter'), true),
    ir: (overlay) => toBuffer(core.ir(overlay), false),
    info: (b) => levels.get(b) || (G && G.info(b)),
    realChain(o = {}, actx = ctx) {
      const ctx = actx, input = ctx.createGain(), conv = ctx.createConvolver(), dryG = ctx.createGain(), lo = ctx.createBiquadFilter(), hi = ctx.createBiquadFilter(), output = ctx.createGain();
      const loud = ctx.createBiquadFilter(), pre = ctx.createGain(), shaper = ctx.createWaveShaper(), post = ctx.createGain();
      conv.normalize = false; lo.type = 'lowshelf'; lo.frequency.value = 250; hi.type = 'highshelf'; hi.frequency.value = 1000;
      loud.type = 'lowshelf'; loud.frequency.value = 150; loud.gain.value = 10; pre.gain.value = 0.5; shaper.curve = curve; shaper.oversample = 'none'; post.gain.value = 0.85;
      const mix = ctx.createGain(); input.connect(dryG); dryG.connect(mix); input.connect(conv); conv.connect(mix); mix.connect(lo); lo.connect(hi);
      loud.connect(pre); pre.connect(shaper); shaper.connect(post); post.connect(output);
      const api = { input, output, set(q) {
        const ov = q.overlay && q.overlay !== 'dry' ? q.overlay : null;
        if (ov) { conv.buffer = S.ir(ov); dryG.gain.value = 0; } else { conv.buffer = null; dryG.gain.value = 1; }
        lo.gain.value = q.hpd ? -15 : 0; hi.gain.value = q.hpd ? -18 : 0;          // about 15 dB at 125 Hz and 33 dB above 1 kHz
        hi.disconnect(); if (q.ear !== false) hi.connect(loud); else hi.connect(output);
        return api;
      } };
      return api.set(o);
    }
  };
  // ---- cinematic mode (the default since 2026-11-17): shared/cinematic-sound/cinematic-sound.js sized by this pistol's simulation.
  // S.realShot / S.realMech / S.realChain above are the physical simulation, unchanged; S.shot / S.mech / S.chain follow S.mode.
  const physCache = {}, KIND = { outdoor_berm: 'outdoor', indoor_range: 'indoor' };                                   // design label: which kind of tail each simulated place gets
  const adapter = {
    id: 'g44v', fs: P.fs, defaultKey: 'cci_standard_velocity', defaultOverlay: 'outdoor_berm', builtSuppressed: null,
    sim: (k) => ({ ...CINE_SIM.common, ...CINE_SIM[k], gas_energy_J: P.loads[k].gas_energy_J, supersonic_to_m: 0 }),
    times: (k) => ({ base: k, times: [0] }),
    perspective: (p) => { const pp = P.perspectives[p]; return !pp ? null : p === 'shooter' ? { distance: 0, bearing: 'front' } : { distance: Math.round(pp.r), bearing: pp.theta_deg < 60 ? 'front' : 'side' }; },
    physical: (k) => physCache[k] || (physCache[k] = core.dryParts(k)),
    suppression: () => 0,
    mechClip: (name) => { const C = P.clips[name], mx = Math.max(...C.events.map((e) => e.noise.a)), fr = C.friction; return { phys: core.mech(name), events: C.events.map((e) => ({ t: 0.002 + e.t, w: e.noise.a / mx, ms: 0.15 })), slides: fr ? [{ t0: 0.002 + fr.t, t1: 0.002 + fr.t + (fr.env.length - 1) * fr.step / P.fs, w: 1 }] : [] }; },
    env: (ov) => { const O = ov && P.overlays[ov]; if (!O || !KIND[ov]) return null; const far = O.taps.filter((t) => t.delay > 0.05).sort((a, b) => b.gain - a.gain)[0]; return { kind: KIND[ov], rt60: O.tail.rt60, slaps: KIND[ov] === 'outdoor' && far ? [{ t: far.delay, db: 20 * Math.log10(far.gain) }] : [] }; },
    realShot: (k, o = {}) => S.realShot(k, o), realMech: (c, o = {}) => S.realMech(c, o),
    realChain: (ro, cx) => S.realChain(ro, cx),
    hpd: null,
  };
  G = CS.makeGun(ctx, adapter, { mode: opts.mode });
  Object.defineProperty(S, 'mode', { get: () => G.mode, set: (m) => { G.setMode(m); }, enumerable: true });
  S.setMode = (m) => { G.setMode(m); return S; }; S.design = G.design; S.cinematic = G; S.defaultOverlay = adapter.defaultOverlay;
  S.shot = (load = 'cci_standard_velocity', o = {}) => (o.mode || G.mode) === 'realistic' ? S.realShot(load, o) : G.shot(load, o);
  S.mech = (clip, o = {}) => (o.mode || G.mode) === 'realistic' ? S.realMech(clip, o) : G.mech(clip, o);
  S.chain = (o = {}, actx = ctx) => G.chain(o, actx);
  return S;
}
const G44VSound = { build, makeCore, CINE_SIM };
export default G44VSound;
export { G44VSound, build, makeCore };
