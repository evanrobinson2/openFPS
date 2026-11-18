// G44 V simulated sound: browser synthesis from params.json (written by sim.py).
// A port of "stage B" of sound/sim.py: the same tables, the same named random streams, the same arithmetic. Nothing here is a recording.
//
//   import G44VSound from './sound/g44v-sound.js';
//   const S = await G44VSound.build(audioContext);                 // loads params.json next to this file
//   S.shot('cci_standard_velocity')                                -> AudioBuffer: free field, shooter's ear, peak at -1 dBFS
//   S.shot('cci_mini_mag', { perspective: 'bystander', ground: true })
//   S.mech('slide_rack' | 'slide_release' | 'slide_lock_open' | 'trigger' | 'dry_fire' | 'magazine_out' | 'magazine_in' | 'case_ground')
//   S.ir('indoor_range' | 'outdoor_berm')                          -> AudioBuffer impulse response (direct path = first sample)
//   S.chain({ overlay: 'indoor_range', hpd: false, ear: true })    -> { input, output, set(opts) }   (overlay null = no room)
//   S.info(buffer)                                                 -> { peak_pa, peak_db_spl, pa_per_fullscale }: the true simulated level
//   S.loads, S.perspectives, S.clips, S.overlays, S.params;  S.raw.dry / mech / ir -> Float64Array in pascals (IR: units), for tests
//
// Playback is normalised: 150 dB at the ear cannot be reproduced, so every buffer is scaled to -1 dBFS and S.info() carries the true level.
// chain()'s 'hpd' is a two-shelf approximation of an earmuff (about 24 dB NRR, the minimum the manual asks for, p. 13) and 'ear' is a compressor
// so the tails stay audible; both are playback mappings, not part of the physics.

const P_REF = 20e-6;
const fnv1a = (s) => { let h = 0x811c9dc5; for (const c of new TextEncoder().encode(s)) { h ^= c; h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; };
class Rng { // mulberry32; identical to sim.py
  constructor(name) { this.a = fnv1a(name); }
  next() { this.a = (this.a + 0x6d2b79f5) >>> 0; let t = this.a; t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0; t = (t ^ (t + (Math.imul(t ^ (t >>> 7), t | 61) >>> 0))) >>> 0; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  gauss() { const a = this.next(), b = this.next(); return Math.sqrt(-2 * Math.log(a + 1e-12)) * Math.cos(2 * Math.PI * b); }
}
function makeCore(P) {
  const fs = P.fs;
  function addBlast(buf, pk, T, t0, lp) {
    const b = P.friedlander_b, rise = P.rise, n0 = Math.max(0, Math.floor(t0 * fs)), n1 = Math.min(buf.length, Math.ceil((t0 + rise + 8 * T) * fs) + 1); let y = 0;
    for (let n = n0; n < n1; n++) {
      const t = n / fs - t0; let x = 0;
      if (t >= 0) { if (t < rise) x = pk * t / rise; else { const u = (t - rise) / T; x = pk * (1 - u) * Math.exp(-b * u); } }
      y += lp * (x - y); buf[n] += y;
    }
  }
  function addImpact(buf, ev, t0, gain, lp, seed) {
    let tmax = 0; for (const m of ev.modes) tmax = Math.max(tmax, m.tau); tmax *= 7;
    const n0 = Math.max(0, Math.floor((t0 + ev.t) * fs)), n1 = Math.min(buf.length, n0 + Math.floor(tmax * fs) + 2), rng = new Rng(seed), nz = ev.noise; let y = 0, z = 0;
    for (let n = n0; n < n1; n++) {
      const t = n / fs - (t0 + ev.t); let x = 0;
      if (t >= 0) {
        for (const m of ev.modes) x += m.a * Math.exp(-t / m.tau) * Math.sin(2 * Math.PI * m.f * t);
        z += nz.lp * (rng.gauss() - z); x += nz.a * Math.exp(-t / nz.tau) * z;
      }
      y += lp * (x * gain - y); buf[n] += y;
    }
  }
  function dry(load, persp = 'shooter', field = false) {
    const L = P.loads[load], ps = P.perspectives[persp], buf = new Float64Array(Math.floor(P.dur_shot * fs)), paths = field ? [ps.direct, ps.ground] : [ps.direct];
    paths.forEach((pth, i) => {
      addBlast(buf, L.peak_pa_1m_90 * pth.gain, L.t_pos, L.t_blast + pth.delay, pth.lp);
      L.mech.forEach((ev, j) => addImpact(buf, ev, pth.delay, pth.mech_gain, pth.lp, `mech|${load}|${j}|${i}`));
    });
    return buf;
  }
  function mech(clip, persp = 'shooter') {
    const pth = P.perspectives[persp].direct, buf = new Float64Array(Math.floor(P.dur_clip * fs));
    P.clips[clip].forEach((ev, j) => addImpact(buf, ev, 0.002, pth.mech_gain, pth.lp, `clip|${clip}|${j}`));
    return buf;
  }
  function ir(overlay) {
    const O = P.overlays[overlay], tl = O.tail, n = Math.floor((tl.t0 + tl.rt60 * 1.1) * fs) + 1, h = new Float64Array(n); h[0] = 1;
    for (const tp of O.taps) { const k = Math.floor(tp.delay * fs + 0.5); if (k > 0 && k < n) h[k] += tp.gain; }
    const rng = new Rng('ir|' + overlay), k0 = Math.floor(tl.t0 * fs); let z = 0;
    for (let k = k0; k < n; k++) { const t = (k - k0) / fs; z += tl.lp * (rng.gauss() - z); h[k] += tl.level * z * Math.exp(-6.907755 * t / tl.rt60); }
    return h;
  }
  return { dry, mech, ir };
}
async function build(ctx, opts = {}) {
  const url = opts.params || new URL('params.json', import.meta.url), P = opts.data || await (await fetch(url)).json(), core = makeCore(P), levels = new WeakMap();
  function toBuffer(x, normalise) {
    let pk = 0; for (let i = 0; i < x.length; i++) pk = Math.max(pk, Math.abs(x[i]));
    const g = normalise ? Math.pow(10, -1 / 20) / (pk || 1) : 1, b = ctx.createBuffer(1, x.length, P.fs), d = b.getChannelData(0);
    for (let i = 0; i < x.length; i++) d[i] = x[i] * g;
    levels.set(b, { peak_pa: pk, peak_db_spl: 20 * Math.log10(pk / P_REF), pa_per_fullscale: 1 / g }); return b;
  }
  const S = {
    params: P, loads: Object.keys(P.loads), perspectives: Object.keys(P.perspectives), clips: Object.keys(P.clips), overlays: Object.keys(P.overlays), raw: core,
    shot: (load = 'cci_standard_velocity', o = {}) => toBuffer(core.dry(load, o.perspective || 'shooter', !!o.ground), true),
    mech: (clip, o = {}) => toBuffer(core.mech(clip, o.perspective || 'shooter'), true),
    ir: (overlay) => toBuffer(core.ir(overlay), false),
    info: (b) => levels.get(b),
    chain(o = {}) {
      const input = ctx.createGain(), conv = ctx.createConvolver(), dryG = ctx.createGain(), lo = ctx.createBiquadFilter(), hi = ctx.createBiquadFilter(), comp = ctx.createDynamicsCompressor(), output = ctx.createGain();
      conv.normalize = false; lo.type = 'lowshelf'; lo.frequency.value = 250; hi.type = 'highshelf'; hi.frequency.value = 1000;
      comp.threshold.value = -30; comp.ratio.value = 6; comp.attack.value = 0.001; comp.release.value = 0.15;
      const mix = ctx.createGain(); input.connect(dryG); dryG.connect(mix); input.connect(conv); conv.connect(mix); mix.connect(lo); lo.connect(hi);
      const api = { input, output, set(q) {
        const ov = q.overlay && q.overlay !== 'dry' ? q.overlay : null;
        if (ov) { conv.buffer = S.ir(ov); dryG.gain.value = 0; } else { conv.buffer = null; dryG.gain.value = 1; }
        lo.gain.value = q.hpd ? -15 : 0; hi.gain.value = q.hpd ? -18 : 0;          // about 15 dB at 125 Hz and 33 dB above 1 kHz
        hi.disconnect(); comp.disconnect(); if (q.ear !== false) { hi.connect(comp); comp.connect(output); } else hi.connect(output);
        return api;
      } };
      return api.set(o);
    }
  };
  return S;
}
const G44VSound = { build, makeCore };
export default G44VSound;
export { G44VSound, build, makeCore };
