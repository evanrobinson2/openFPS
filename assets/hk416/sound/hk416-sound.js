// HK416 D14.5RS simulated sound: browser synthesis from params.json (written by sim.py).
// This is a port of "stage B" of sound/sim.py: the same tables, the same deterministic random
// streams, the same arithmetic. Nothing here is a recording.
//
//   import HK416Sound from './sound/hk416-sound.js';
//   const S = await HK416Sound.build(audioContext);            // loads params.json next to this file
//   S.shot('single')                       -> AudioBuffer, free field, shooter's ear, peak at -1 dBFS
//   S.shot('auto1s', { perspective: 'bystander', ground: true })
//   S.mech('cycle' | 'case_drop' | 'trigger' | 'trigger_reset' | 'charge' | 'bolt_lock_back' | 'bolt_release')
//   S.steel(0.22, { dist: 35, seed: 3 })   -> AudioBuffer of the plate ring heard at dist metres
//   await S.ir('range_berm')               -> AudioBuffer impulse response (direct path = 1.0 at sample 0)
//   S.hpd()                                -> AudioBuffer earmuff FIR (apply after the room)
//   S.chain({ overlay: 'range_berm', hpd: false, ear: true }) -> Promise<{ input, output, set(opts) }>
//       (overlay: null or 'dry' = no room; second argument: an OfflineAudioContext to render into)
//   S.info(buffer)                         -> { peak_pa, peak_db_spl, pa_per_fullscale } true simulated level
//   S.overlays, S.variants, S.perspectives, S.mechClips, S.steelKeys, S.params
//   S.raw.dry / mech / steel / ir          -> Float64Array in pascals (or IR units), for tests
//
// Playback is normalised: real levels (157 dB at the ear) cannot be reproduced, so every buffer is
// scaled to -1 dBFS and S.info() carries the true level. The 'ear' stage of chain() is a compressor:
// a playback mapping so tails 40-60 dB under the shot stay audible. It is not part of the physics.

const P_REF = 20e-6;
const fnv1a = (s) => { let h = 0x811c9dc5; for (const c of new TextEncoder().encode(s)) { h ^= c; h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; };
class Rng { // mulberry32, counter based; identical to sim.py
  constructor(name) { this.a = fnv1a(name); }
  next() { this.a = (this.a + 0x6d2b79f5) >>> 0; let t = this.a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  u(n) { const o = new Float64Array(n); for (let i = 0; i < n; i++) o[i] = this.next(); return o; }
  g(n) { const o = new Float64Array(n); for (let i = 0; i < n; i++) { const a = this.next(), b = this.next(); o[i] = Math.sqrt(-2 * Math.log(a + 1e-12)) * Math.cos(2 * Math.PI * b); } return o; }
}
const rnd = (x) => Math.floor(x + 0.5);
const unb64 = (s) => { const b = typeof atob === 'function' ? Uint8Array.from(atob(s), (c) => c.charCodeAt(0)) : new Uint8Array(Buffer.from(s, 'base64')); return Float64Array.from(new Float32Array(b.buffer, b.byteOffset, b.length >> 2)); };
const convolve = (x, h) => { const y = new Float64Array(x.length + h.length - 1); for (let i = 0; i < x.length; i++) { const v = x[i]; if (v !== 0) for (let j = 0; j < h.length; j++) y[i + j] += v * h[j]; } return y; };
function fft(re, im, inverse) { // in-place radix-2
  const n = re.length; for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; } }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (inverse ? 2 : -2) * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang), half = len >> 1;
    for (let i = 0; i < n; i += len) { let cr = 1, ci = 0; for (let k = 0; k < half; k++) { const a = i + k, b = a + half, xr = re[b] * cr - im[b] * ci, xi = re[b] * ci + im[b] * cr; re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi; const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t; } }
  }
  if (inverse) for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
}

function makeCore(P) {
  const FS = P.fs, OS = P.os, FSO = FS * OS, dec = unb64(P.dec), firs = P.firs.map(unb64), LAT = P.fir_lat, C = P.c, MU = P.mu;
  const dirfac = (c, mu = MU) => (mu * c + Math.sqrt(1 - mu * mu * (1 - c * c))) / Math.sqrt(1 - mu * mu);
  function addAt(out, y, n0, gain, fir) {
    if (fir !== undefined && fir !== null && fir >= 0) { y = convolve(y, firs[fir]); n0 -= LAT; }
    const a = Math.max(0, -n0), b = Math.min(y.length, out.length - n0); for (let i = a; i < b; i++) out[n0 + i] += gain * y[i];
  }
  function decimatePlace(out, x, tArr, gain, fir) {
    const shift = rnd(tArr * FSO), o = ((shift % OS) + OS) % OS, base = Math.floor(shift / OS), L = o + 64 + x.length + 68, n = Math.ceil((L + 126 - 63) / OS), y = new Float64Array(n);
    for (let k = 0; k < n; k++) { const c = 63 + OS * k; let s = 0; const j0 = Math.max(0, c - (o + 64 + x.length - 1)), j1 = Math.min(126, c - (o + 64)); for (let j = j0; j <= j1; j++) s += dec[j] * x[c - j - o - 64]; y[k] = s; }
    addAt(out, y, base - 16, gain, fir);
  }
  function friedlander(Pk, T, rise) { const n = Math.floor((rise + 10 * T) * FSO) + 2, o = new Float64Array(n); for (let i = 0; i < n; i++) { const t = i / FSO - rise; o[i] = t < 0 ? Pk * (1 + t / rise) : Pk * (1 - t / T) * Math.exp(-t / T); } return o; }
  function nwave(dp, T, rise) { const n = Math.floor((T + 2 * rise) * FSO) + 3, o = new Float64Array(n); for (let i = 0; i < n; i++) { const t = i / FSO; o[i] = t < rise ? dp * t / rise : t < rise + T ? dp * (1 - 2 * (t - rise) / T) : t < T + 2 * rise ? -dp * (1 - (t - rise - T) / rise) : 0; } return o; }
  function mechSig(ev, seed) {
    let tmax = 0; for (const m of ev.modes) tmax = Math.max(tmax, m[1]);
    const n = Math.floor(FS * (Math.min(0.45, 1.2 * tmax) + 0.005)), s = new Float64Array(n);
    for (const [f, T60, a] of ev.modes) for (let i = 0; i < n; i++) { const t = i / FS; s[i] += a * Math.exp(-6.9078 * t / T60) * Math.sin(2 * Math.PI * f * t); }
    const [amp, tau] = ev.click;
    if (amp > 0) { const m = Math.min(n, Math.floor(8 * tau * FS) + 1), g = new Rng(seed).g(m); for (let i = 0; i < m; i++) s[i] += amp * g[i] * Math.exp(-(i / FS) / tau); }
    let pk = 0; for (let i = 0; i < n; i++) pk = Math.max(pk, Math.abs(s[i])); const k = P_REF * Math.pow(10, ev.p1m / 20) / pk; for (let i = 0; i < n; i++) s[i] *= k; return s;
  }
  function jetSig(rms, tau, seed) { const n = Math.floor(8 * tau * FS), x = new Rng(seed).g(n), a = 1 / (1 + 2 * Math.PI * 800 / FS), y = new Float64Array(n); let px = 0, py = 0; for (let i = 0; i < n; i++) { py = a * x[i] - a * px + a * py; px = x[i]; const t = i / FS; y[i] = rms * py * (1 - Math.exp(-t / 1e-4)) * Math.exp(-t / tau); } return y; }
  function addEvents(out, pp, events, ts, field, seed, jt = 1, ja = null) {
    events.forEach(([name, te, pos], i) => {
      const sig = mechSig(P.mech[name], seed + '/' + name), k = ja ? Math.pow(10, ja[i] / 20) : 1; if (k !== 1) for (let q = 0; q < sig.length; q++) sig[q] *= k;
      for (const path of pp.src[pos][field ? 'field' : 'free']) addAt(out, sig, rnd((ts + te * jt + path.t + pp.t0) * FS), path.g, path.fir);
    });
  }
  function dry(persp = 'shooter', variant = 'single', field = false, parts = ['blast', 'nwave', 'mech']) {
    const pp = P.persp[persp], v = P.variants[variant], key = field ? 'field' : 'free', out = new Float64Array(Math.floor(v.len * FS)), t0 = pp.t0, rise = P.rise;
    v.times.forEach((ts, k) => {
      const j = new Rng('shot' + k).g(16), jP = Math.pow(10, P.shot_sd_db * j[0] / 20), jt = 1 + 0.015 * j[1];
      if (parts.includes('blast')) {
        for (const e of pp.blast[key]) decimatePlace(out, friedlander(e.P * jP, e.T, rise), ts + e.t + t0, 1, e.fir);
        for (const e of pp.sec[key]) decimatePlace(out, friedlander(e.P * jP, e.T, rise), ts + e.t + t0, 1, e.fir);
        pp.jet[key].forEach((e, i) => addAt(out, jetSig(e.rms * jP, e.tau, 'jet' + k + '/' + i), rnd((ts + e.t + t0) * FS), 1, e.fir));
      }
      if (parts.includes('nwave')) for (const e of pp.nwave[key]) decimatePlace(out, nwave(e.dp, e.T, rise), ts + e.t + t0, 1, e.fir);
      if (parts.includes('mech')) { const ev = P.cycle.slice(); if (v.reset !== null) ev.push(['reset', v.reset, 'recv']); addEvents(out, pp, ev, ts, field, 'shot' + k, jt, ev.map((_, i) => 1.5 * j[2 + i])); }
    });
    return out;
  }
  function mech(clip, persp = 'shooter', field = false) {
    const pp = P.persp[persp], ev = P.mech_clips[clip]; let tmax = -1e9, tmin = 0; for (const e of ev) { tmax = Math.max(tmax, e[1]); tmin = Math.min(tmin, e[1]); }
    const out = new Float64Array(Math.floor((tmax + 0.5) * FS)); addEvents(out, pp, ev, 0.0 - pp.t0 + 0.005 - tmin, field, 'clip/' + clip); return out;
  }
  function steel(key, dist = null, seed = 0) {
    const st = P.steel[key], d = dist === null ? st.dist : dist, n = Math.floor(1.6 * FS), s = new Float64Array(n), rg = new Rng('steelhit/' + key + '/' + seed), w = rg.u(st.modes.length);
    st.modes.forEach(([f, T60, p1, al], q) => { const a = (0.6 + 0.8 * w[q]) * p1 * Math.pow(10, -al * d / 20); const nn = Math.min(n, Math.ceil(T60 * 2.5 * FS)); for (let i = 0; i < nn; i++) { const t = i / FS; s[i] += a * Math.exp(-6.9078 * t / T60) * Math.sin(2 * Math.PI * f * t); } });
    const m = Math.floor(8 * st.splash.tau * FS), g = rg.g(m); for (let i = 0; i < m; i++) s[i] += st.splash.p1m * g[i] * Math.exp(-(i / FS) / st.splash.tau);
    for (let i = 0; i < n; i++) s[i] /= d; return s;
  }
  // ---- impulse responses
  const mk9 = (N) => Array.from({ length: 9 }, () => new Float64Array(N));
  function elShoebox(el, rc, taps, burst) {
    const L = el.L, rmax = C * el.tmax + rc.rd, s = el.scat, air = P.air_band, gd = rc.Dd / rc.rd, N = taps[0].length, per = [];
    for (let a = 0; a < 3; a++) {
      const mm = el.mmax ? el.mmax[a] : Math.ceil(rmax / (2 * L[a])) + 1, d = [], fl = [], cnt = [], gain = [];
      const b0 = el.alpha[2 * a].map((x) => Math.sqrt(1 - x)), b1 = el.alpha[2 * a + 1].map((x) => Math.sqrt(1 - x));
      for (let m = -mm; m <= mm; m++) for (let p = 0; p < 2; p++) { const c0 = Math.abs(m - p), c1 = Math.abs(m); d.push(rc.lis[a] - ((1 - 2 * p) * rc.src[a] + 2 * m * L[a])); fl.push(1 - 2 * p); cnt.push(c0 + c1); gain.push(b0.map((v, b) => Math.pow(v, c0) * Math.pow(b1[b], c1))); }
      per.push({ d, fl, cnt, gain });
    }
    const [X, Y, Z] = per, ax = rc.axis;
    for (let i = 0; i < X.d.length; i++) for (let j = 0; j < Y.d.length; j++) {
      const dxy = X.d[i] * X.d[i] + Y.d[j] * Y.d[j]; if (dxy >= rmax * rmax) continue;
      for (let k = 0; k < Z.d.length; k++) {
        const r = Math.sqrt(dxy + Z.d[k] * Z.d[k]), order = X.cnt[i] + Y.cnt[j] + Z.cnt[k]; if (!(r < rmax) || order === 0) continue;
        const idx = Math.floor((r - rc.rd) / C * FS + 0.5); if (idx < 0 || idx >= N) continue;
        const cos = (X.d[i] * X.fl[i] * ax[0] + Y.d[j] * Y.fl[j] * ax[1] + Z.d[k] * Z.fl[k] * ax[2]) / Math.max(r, 1e-9), g0 = dirfac(cos) / Math.max(r, 1e-9) / gd, sp = Math.pow(1 - s, order / 2), df = 1 - Math.pow(1 - s, order);
        for (let b = 0; b < 9; b++) { const gb = g0 * X.gain[i][b] * Y.gain[j][b] * Z.gain[k][b] * Math.pow(10, -air[b] * r / 20); if (gb === 0) continue; taps[b][idx] += gb * sp; if (el.bursts) burst[b][idx] += gb * gb * df; }
      }
    }
  }
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], norm = (a) => Math.sqrt(dot(a, a));
  function elPatches(el, rc, taps) {
    const rg = new Rng(el.seed), { o, eu, ev, nu, nv } = el, N = taps[0].length; let nrm = [eu[1] * ev[2] - eu[2] * ev[1], eu[2] * ev[0] - eu[0] * ev[2], eu[0] * ev[1] - eu[1] * ev[0]]; const nl = norm(nrm), dA = nl / (nu * nv); nrm = nrm.map((v) => v / nl);
    for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) {
      const u0 = rg.next(), u1 = rg.next(), u2 = rg.next(), a = (i + u0) / nu, b = (j + u1) / nv, p = [o[0] + a * eu[0] + b * ev[0], o[1] + a * eu[1] + b * ev[1], o[2] + a * eu[2] + b * ev[2]], sign = u2 < 0.5 ? -1 : 1;
      const d1 = sub(p, rc.src), r1 = norm(d1), d2 = sub(rc.lis, p), r2 = norm(d2), ci = Math.abs(dot(d1, nrm)) / r1, cs = Math.abs(dot(d2, nrm)) / r2;
      const g = dirfac(dot(d1, rc.axis) / r1) / r1 * Math.sqrt(ci * cs * dA / Math.PI) / r2 / (rc.Dd / rc.rd) * sign, idx = Math.floor((r1 + r2 - rc.rd) / C * FS + 0.5); if (idx < 0 || idx >= N) continue;
      for (let q = 0; q < 9; q++) taps[q][idx] += g * Math.sqrt(1 - el.alpha[q]) * Math.pow(10, -P.air_band[q] * (r1 + r2) / 20);
    }
  }
  function elTrees(el, rc, taps) {
    const rg = new Rng(el.seed), n = Math.floor(el.density * (el.x1 - el.x0) * (el.z1 - el.z0)), N = taps[0].length;
    for (let t = 0; t < n; t++) {
      const u0 = rg.next(), u1 = rg.next(), u2 = rg.next(), x = el.x0 + u0 * (el.x1 - el.x0), z = el.z0 + u1 * (el.z1 - el.z0), sign = u2 < 0.5 ? -1 : 1, p = [x, 1.6, z];
      const d1 = sub(p, rc.src), r1 = norm(d1), d2 = sub(rc.lis, p), r2 = norm(d2), dz = Math.max(0, z - el.z0);
      const inside = dz * (r1 / Math.max(1e-6, Math.abs(d1[2]))) + (rc.lis[2] < el.z0 ? dz * (r2 / Math.max(1e-6, Math.abs(d2[2]))) : Math.min(r2, 60));
      const g = dirfac(dot(d1, rc.axis) / r1) / r1 / r2 / (rc.Dd / rc.rd) * sign, idx = Math.floor((r1 + r2 - rc.rd) / C * FS + 0.5); if (idx < 0 || idx >= N) continue;
      for (let b = 0; b < 9; b++) { const ka = 2 * Math.PI * P.bands[b] / C * el.radius, sig = 2 * el.radius * el.heff * Math.min(1, ka * ka); taps[b][idx] += g * Math.sqrt(sig / (4 * Math.PI)) * Math.pow(10, -(P.air_band[b] * (r1 + r2) + el.foliage[b] * inside) / 20); }
    }
  }
  function bandWeights(NF) { const W = mk9(NF); for (let k = 0; k < NF; k++) { const f = Math.min(k, NF - k) * FS / NF, u = Math.log2(Math.max(f, 1e-3) / 63); for (let b = 0; b < 9; b++) { const x = Math.max(-1, Math.min(1, u - b)); let w = Math.cos(Math.PI / 2 * x) ** 2; if (b === 0 && u < 0) w = 1; if (b === 8 && u > 8) w = 1; W[b][k] = w; } } return W; }
  function ir(overlay, persp = 'shooter') {
    const rc = P.overlays[overlay].persp[persp], N = Math.floor(rc.len * FS), NF = 1 << Math.ceil(Math.log2(N + 4096)), taps = mk9(N); let burst = null, vr = null; const firEls = [];
    for (let b = 0; b < 9; b++) taps[b][0] += 1;
    for (const el of rc.elements) {
      if (el.type === 'shoebox') {
        if (el.bursts) burst = mk9(N); elShoebox(el, rc, taps, burst);
        if (el.bursts) { vr = vr || mk9(N); const a = Math.exp(-1 / (el.bursts * FS)); for (let b = 0; b < 9; b++) { let y = 0; for (let i = 0; i < N; i++) { y = (1 - a) * burst[b][i] + a * y; vr[b][i] += y; } } }
      } else if (el.type === 'stat') {
        vr = vr || mk9(N); for (let i = 0; i < N; i++) { const t = i / FS, te = t + el.te0, w = t >= el.tmix ? 1 : 1 - Math.pow(1 - el.scat, el.nrate * te); if (w === 0) continue; for (let b = 0; b < 9; b++) vr[b][i] += el.var0 * Math.exp(-13.8155 * te / el.T60[b]) * w; }
      } else if (el.type === 'taps') { for (const [delay, g] of el.taps) { const i = rnd(delay * FS); for (let b = 0; b < 9; b++) taps[b][i] += g[b]; } }
      else if (el.type === 'fir') firEls.push(el);
      else if (el.type === 'patches') elPatches(el, rc, taps);
      else if (el.type === 'trees') elTrees(el, rc, taps);
    }
    const W = bandWeights(NF), Hr = new Float64Array(NF), Hi = new Float64Array(NF), re = new Float64Array(NF), im = new Float64Array(NF);
    for (let b = 0; b < 9; b++) { re.fill(0); im.fill(0); re.set(taps[b]); fft(re, im, false); const w = W[b]; for (let k = 0; k < NF; k++) { Hr[k] += re[k] * w[k]; Hi[k] += im[k] * w[k]; } }
    fft(Hr, Hi, true); const h = Hr.slice(0, N);
    if (vr) {
      const wr = new Float64Array(NF), wi = new Float64Array(NF); wr.set(new Rng(rc.seed + '/' + overlay + '/' + persp).g(NF)); fft(wr, wi, false);
      for (let b = 0; b < 9; b++) { const w = W[b], v = vr[b]; for (let k = 0; k < NF; k++) { re[k] = wr[k] * w[k]; im[k] = wi[k] * w[k]; } fft(re, im, true); for (let i = 0; i < N; i++) h[i] += re[i] * Math.sqrt(v[i]); }
    }
    for (const el of firEls) addAt(h, unb64(el.fir), rnd(el.delay * FS) - LAT, el.gain);
    const nf = Math.floor(0.02 * FS); for (let i = 0; i < nf; i++) h[N - nf + i] *= 0.5 + 0.5 * Math.cos(Math.PI * i / nf);
    return h;
  }
  return { dry, mech, steel, ir, hpd: () => unb64(P.hpd.fir), FS };
}

async function build(ctx, opts = {}) {
  const P = opts.params || await (await fetch(opts.paramsUrl || new URL('params.json', import.meta.url))).json();
  const core = makeCore(P), cache = new Map(), meta = new WeakMap(), norm = Math.pow(10, -1 / 20);
  const memo = (k, fn) => { if (!cache.has(k)) cache.set(k, fn()); return cache.get(k); };
  function toBuffer(x, normalise) {
    let pk = 0; for (let i = 0; i < x.length; i++) pk = Math.max(pk, Math.abs(x[i])); const k = normalise ? norm / pk : 1;
    const buf = ctx.createBuffer(1, x.length, core.FS), ch = buf.getChannelData(0); for (let i = 0; i < x.length; i++) ch[i] = x[i] * k;
    meta.set(buf, normalise ? { peak_pa: pk, peak_db_spl: 20 * Math.log10(pk / P_REF), pa_per_fullscale: 1 / k } : { units: 'impulse response, direct path = 1' }); return buf;
  }
  const steelKey = (r) => Object.keys(P.steel).reduce((a, b) => Math.abs(P.steel[a].radius - r) <= Math.abs(P.steel[b].radius - r) ? a : b);
  const S = {
    params: P, raw: core, overlays: Object.fromEntries(Object.entries(P.overlays).map(([k, v]) => [k, { title: v.title, perspectives: Object.keys(v.persp) }])),
    variants: Object.keys(P.variants), perspectives: ['shooter', 'bystander', 'downrange'], mechClips: Object.keys(P.mech_clips), steelKeys: Object.keys(P.steel),
    info: (buf) => meta.get(buf),
    shot: (variant = 'single', { perspective = 'shooter', ground = false } = {}) => memo(`shot/${variant}/${perspective}/${ground}`, () => toBuffer(core.dry(perspective, variant, ground), true)),
    mech: (clip = 'cycle', { perspective = 'shooter' } = {}) => memo(`mech/${clip}/${perspective}`, () => toBuffer(core.mech(clip, perspective), true)),
    steel: (radius = 0.2, { dist = null, seed = 0 } = {}) => { const k = steelKey(radius); return memo(`steel/${k}/${dist}/${seed}`, () => toBuffer(core.steel(k, dist, seed), true)); },
    // the IR is built on first use (0.1 to 2 s of CPU depending on its length), then cached
    ir: (overlay, perspective = 'shooter') => memo(`ir/${overlay}/${perspective}`, () => new Promise((res) => setTimeout(() => res(toBuffer(core.ir(overlay, perspective), false)), 0))),
    hpd: () => memo('hpd', () => toBuffer(core.hpd(), false)),
    // input -> [room convolver] -> [earmuff FIR] -> [ear compressor] -> output. Connect output yourself.
    async chain(o = {}, actx = ctx) { // actx: pass an OfflineAudioContext to render the chain
      const ctx = actx, input = ctx.createGain(), output = ctx.createGain(); let nodes = [];
      const c = { input, output, opts: {}, async set(n) {
        Object.assign(c.opts, n); const { overlay = null, perspective = 'shooter', hpd = false, ear = true } = c.opts; const next = [];
        if (overlay && overlay !== 'dry') { const cv = ctx.createConvolver(); cv.normalize = false; cv.buffer = await S.ir(overlay, perspective); next.push(cv); }
        if (hpd) { const cv = ctx.createConvolver(); cv.normalize = false; cv.buffer = S.hpd(); const g = ctx.createGain(); g.gain.value = 4; next.push(cv, g); } // +12 dB make-up so the muffled shot is still audible
        if (ear) { const k = ctx.createDynamicsCompressor(); k.threshold.value = -42; k.knee.value = 8; k.ratio.value = 14; k.attack.value = 0.001; k.release.value = 0.22; const g = ctx.createGain(); g.gain.value = 0.9; next.push(k, g); }
        input.disconnect(); nodes.forEach((x) => x.disconnect()); nodes = next; let prev = input; for (const x of nodes) { prev.connect(x); prev = x; } prev.connect(output); return c;
      } };
      return c.set(o);
    },
  };
  return S;
}

const HK416Sound = { build, makeCore, Rng, fft };
export default HK416Sound;
export { HK416Sound, build, makeCore };
