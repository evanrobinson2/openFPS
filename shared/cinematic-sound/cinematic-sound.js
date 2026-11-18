/* openFPS cinematic gun sound: one designed synthesis shared by every gun. Credit: carpetshark.
 *
 * This is DESIGNED sound, not physics. The owner's decision (2026-11-17): a real shot at the shooter's ear is a
 * 0.2 ms shock that no loudspeaker can reproduce, so the default sound of a gun is a game-style shot built from
 * layers, and the physical simulation stays available as mode 'realistic'. Nothing here is a recording, a sample
 * or an analysis of one: every layer is arithmetic on seeded noise and sines, sized by numbers that come out of
 * each gun's own simulation (muzzle energy, gas energy and mass, bore, barrel length, cyclic period, action
 * events, and the physical blast waveform itself). Every constant below is a design choice and is labelled so.
 *
 *   <script src="shared/cinematic-sound/cinematic-sound.js"></script>   -> globalThis.OpenFPSCinematicSound
 *   import '../../../shared/cinematic-sound/cinematic-sound.js'          (ES module: same global)
 *
 * Pure functions (run in Node too):  design(sim)  synthShot(d, o)  mixBurst(...)  synthMech(d, o)  tailIR(env, d, o)
 *                                    metrics(x, fs)  spectralPeaks(x, fs, o)
 * Web Audio:                         makeGun(ctx, adapter, opts) -> the per-gun object every asset returns
 * See README.md next to this file for the design, the API and the acceptance numbers.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.OpenFPSCinematicSound = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var C0 = 343.2, TWO_PI = 2 * Math.PI;
  var db2a = function (d) { return Math.pow(10, d / 20); }, clamp = function (x, a, b) { return Math.max(a, Math.min(b, x)); };

  // ------------------------------------------------------------------ seeded noise (mulberry32 on an FNV-1a hash)
  function Rng(name) { var h = 0x811c9dc5; for (var i = 0; i < name.length; i++) { h ^= name.charCodeAt(i) & 255; h = Math.imul(h, 0x01000193) >>> 0; } this.a = h >>> 0; }
  Rng.prototype.next = function () { this.a = (this.a + 0x6d2b79f5) >>> 0; var t = this.a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  Rng.prototype.gauss = function () { var a = this.next(), b = this.next(); return Math.sqrt(-2 * Math.log(a + 1e-12)) * Math.cos(TWO_PI * b); };
  function noise(n, seed) { var r = new Rng(seed), o = new Float64Array(n); for (var i = 0; i < n; i++) o[i] = r.gauss(); return o; }

  // ------------------------------------------------------------------ filters (RBJ biquads and one-poles), in place
  function biquad(x, type, f, fs, q, gainDb) {
    var w = TWO_PI * clamp(f, 5, fs * 0.45) / fs, cs = Math.cos(w), sn = Math.sin(w), al = sn / (2 * (q || 0.7071)), b0, b1, b2, a0, a1, a2;
    if (type === 'lp') { b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0; a0 = 1 + al; a1 = -2 * cs; a2 = 1 - al; }
    else if (type === 'hp') { b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0; a0 = 1 + al; a1 = -2 * cs; a2 = 1 - al; }
    else { var A = Math.pow(10, gainDb / 40), sq = 2 * Math.sqrt(A) * al, s = type === 'ls' ? 1 : -1;   // 'ls' low shelf, 'hs' high shelf
      b0 = A * ((A + 1) - s * (A - 1) * cs + sq); b1 = s * 2 * A * ((A - 1) - s * (A + 1) * cs); b2 = A * ((A + 1) - s * (A - 1) * cs - sq);
      a0 = (A + 1) + s * (A - 1) * cs + sq; a1 = -s * 2 * ((A - 1) + s * (A + 1) * cs); a2 = (A + 1) + s * (A - 1) * cs - sq; }
    b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
    var x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    for (var i = 0; i < x.length; i++) { var v = x[i], y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = v; y2 = y1; y1 = y; x[i] = y; }
    return x;
  }
  function lp1(x, f, fs) { var a = 1 - Math.exp(-TWO_PI * clamp(f, 1, fs * 0.49) / fs), z = 0; for (var i = 0; i < x.length; i++) { z += a * (x[i] - z); x[i] = z; } return x; }
  function hp1(x, f, fs) { var a = 1 - Math.exp(-TWO_PI * clamp(f, 1, fs * 0.49) / fs), z = 0; for (var i = 0; i < x.length; i++) { z += a * (x[i] - z); x[i] -= z; } return x; }
  function peakOf(x) { var p = 0; for (var i = 0; i < x.length; i++) { var v = Math.abs(x[i]); if (v > p) p = v; } return p; }
  function rmsNorm(x) { var s = 0; for (var i = 0; i < x.length; i++) s += x[i] * x[i]; var k = 1 / Math.sqrt(s / x.length + 1e-30); for (i = 0; i < x.length; i++) x[i] *= k; return x; }
  function addInto(out, x, n0, g) { var a = Math.max(0, -n0), b = Math.min(x.length, out.length - n0); for (var i = a; i < b; i++) out[n0 + i] += g * x[i]; }

  // ------------------------------------------------------------------ the design: simulation values -> layer parameters
  /* sim: { muzzle_energy_J, gas_energy_J, gas_mass_g, bore_mm, barrel_mm, muzzle_velocity, cyclic_period_s (null = manual action),
   *        bullet_diam_mm, bullet_len_mm, supersonic_to_m (0 = subsonic) }
   * Every formula is a DESIGN mapping (label: design). The inputs are simulation values; the outputs are not physical claims. */
  function design(sim) {
    var E = sim.muzzle_energy_J + sim.gas_energy_J;
    var e = clamp(Math.log(E / 300) / Math.log(10000 / 300), 0, 1);                       // design: 300 J (a .22 pistol) = 0, 10 kJ = 1
    var b = clamp(Math.log(sim.bore_mm / 5.6) / Math.log(18.5 / 5.6), 0, 1);               // design: 5.6 mm bore = 0, 12 gauge = 1
    var size = 0.65 * e + 0.35 * b;                                                        // design: energy counts about twice as much as bore
    var gm = Math.sqrt(clamp(sim.gas_mass_g / 1.7, 0.01, 2));                              // design: gas mass relative to a 5.56 charge
    var Lr = sim.barrel_mm / 368, per = sim.cyclic_period_s;
    var d = {
      sim: sim, size: size, energy_term: e, bore_term: b,
      // 1. crack: the physical blast waveform plus a broadband gas-noise burst
      g_crack: 1.0,
      f_crack: 5200 - 2200 * size,                 // Hz, centre of the gas-noise burst: smaller guns are brighter
      tau_crack: 0.0025 + 0.007 * gm,              // s: more gas hisses longer
      g_cracknoise: 0.42 + 0.1 * size,
      // 2. body: a broadband burst (no resonances), its band set by barrel length and bore
      f_body: 300 * Math.pow(Lr, -0.5) * Math.pow(sim.bore_mm / 5.56, -0.3),              // Hz: longer, wider barrels speak lower
      tau_body: 0.018 + 0.032 * size,              // s: the punch
      tau_roar: Math.min(0.04 + 0.11 * size, per ? 0.6 * per : 1),   // s: the slower broadband blast under it; a self-loader's is over before its next round
      g_body: 0.6 + 0.3 * size, g_roar: 0.2 + 0.3 * size,
      // 3. sub thump: a sine whose pitch keeps falling, with second and third harmonics and soft saturation
      f_sub_end: 105 * Math.pow(2, -1.25 * size),  // Hz reached after one decay time
      sub_ratio: 3.2,                              // start pitch / f_sub_end
      tau_sub: Math.min(0.038 + 0.105 * size, per ? 0.5 * per : 1),   // s; held under half the cyclic period so that automatic fire stays a row of thumps
      g_sub: 0.42 + 0.38 * size, sub_h2: 0.7, sub_h3: 0.45, sub_drive: 1.6,
      // 4. mechanical layer inside the shot (self-loading guns): level relative to the crack peak
      g_mech: sim.cyclic_period_s ? db2a(-15) : 0, // design: about 25 dB above its physical place; 0 for a manual action (the pump is its own sound)
      // 5. tail
      tail_rt_scale: 0.75 + 0.55 * size,           // a bigger gun stays above the noise floor longer
      tail_lp: 5500 - 2500 * size,                 // Hz
      tail_db: -20 + 7 * size,                     // tail gain relative to the dry shot, outdoors; indoors +3 dB
      // 6. bus
      trim_db: -2.5 * (1 - size),                    // output trim after the bus: every gun drives the bus equally hard, then keeps its place in the size order
      // autofire
      steal_s: per ? clamp(0.25 * per, 0.008, 0.03) : 0.03,       // fade of the previous shot's voice when the next one starts
      steal_floor: 0.08,                                           // the previous voice is held at this gain (its bolt noise stays audible)
      duck_floor: 0.1, duck_tau: per ? clamp(3.5 * per, 0.1, 0.4) : 0.25,   // tail return dips at each shot and recovers
      pump_delay_s: 0.45,                          // manual action: when fire({ pump: true }) starts the rack after the shot
      // bullet
      mach: sim.muzzle_velocity / C0, supersonic_to_m: sim.supersonic_to_m || 0,
    };
    return d;
  }

  // Whitham's N-wave duration for a bullet (diameter dm, length l) at miss distance x; used only to size the crack layer
  function nwaveT(M, dm, l, x) { return 1.82 * M * Math.pow(x, 0.25) / (C0 * Math.pow(M * M - 1, 0.375)) * dm / Math.pow(l, 0.25); }

  /* One dry cinematic shot (layers 1 to 4, no tail, no bus).
   * o: { fs, crack: Float64Array physical blast (any units), nPeak: index of its peak (found if absent), mech: Float64Array|null physical
   *      action noise on the same time base, seed, distance (m, 0 = shooter), bearing ('front'|'side'), suppress_db (physical reduction
   *      of the muzzle blast, 0 = none), refCrackPeak (peak of the bare blast, so a suppressed waveform keeps its own shape but not its level) }
   * Returns { x, nPeak, len, blast_delay_s }. Amplitudes are relative to a crack peak of 1; the caller sets the final scale. */
  function synthShot(d, o) {
    var fs = o.fs, sim = d.sim, seed = (o.seed || 0) + '', dist = o.distance || 0, R = o.suppress_db || 0, crack = o.crack;
    var nPk = o.nPeak; if (nPk == null) { nPk = 0; var pk0 = 0; for (var i = 0; i < crack.length; i++) if (Math.abs(crack[i]) > pk0) { pk0 = Math.abs(crack[i]); nPk = i; } }
    var supersonic = d.mach > 1.03, front = dist > 0 && (o.bearing || 'front') === 'front' && supersonic && dist <= d.supersonic_to_m;
    // the bullet's shock reaches a listener near the line of fire before the muzzle blast does
    var dt = front ? dist * (1 / C0 - 1 / sim.muzzle_velocity) : 0, nb = Math.round(dt * fs);            // design: muzzle velocity held over the range
    var tailLen = Math.max(7 * d.tau_sub, 0.5), mechEnd = 0;
    if (o.mech && d.g_mech > 0) for (i = o.mech.length - 1; i > 0; i--) if (Math.abs(o.mech[i]) > 1e-9) { mechEnd = i; break; }
    var N = Math.max(nPk + nb + Math.round(tailLen * fs), mechEnd + Math.round(0.05 * fs)), out = new Float64Array(N), n0 = nPk + nb, M = N - n0, t;
    // distance (design): with each doubling of (1 + d / 4 m) the crack loses 1.8 dB and the body 0.8 dB against the thump, and the air takes the top
    var dbl = Math.log2(1 + dist / 4), gC = db2a(-1.8 * dbl), gB = db2a(-0.8 * dbl), gS = 1, fAir = 20000 / (1 + dist / 12);   // balance only: the level itself falls after the bus (chain: distance_db_per_doubling)
    // suppressor (design): each layer loses a share of the physical reduction R
    var sC = db2a(-0.55 * R), sN = db2a(-0.5 * R), sB = db2a(-0.4 * R), sS = db2a(-0.45 * R);
    // ---- 1. crack: the physical blast, peak 1 (or its own share of the bare peak when suppressed)
    var cpk = o.refCrackPeak || peakOf(crack), cw = Math.min(crack.length, nPk + Math.round(0.03 * fs)), c = new Float64Array(cw), nf = Math.round(0.005 * fs);
    for (i = 0; i < cw; i++) c[i] = crack[i] / cpk * (i > cw - nf ? (cw - i) / nf : 1);
    if (R > 0) { var k = peakOf(c); if (k > 0) for (i = 0; i < cw; i++) c[i] *= sC / k; }   // the suppressed pop keeps its shape; its level is the design share
    if (dist > 0) { lp1(c, fAir, fs); lp1(c, fAir, fs); }
    addInto(out, c, nb, d.g_crack * gC);
    var cn = noise(M, 'cn' + seed); biquad(cn, 'hp', d.f_crack * (R > 0 ? 0.3 : 0.45), fs, 0.6); biquad(cn, 'lp', d.f_crack * (R > 0 ? 1.2 : 2.2), fs, 0.6); rmsNorm(cn);
    var tc = d.tau_crack * (R > 0 ? 1.8 : 1);
    for (i = 0; i < M; i++) { t = i / fs; cn[i] *= (1 - Math.exp(-t / 0.0003)) * Math.exp(-t / tc); }
    if (dist > 0) lp1(cn, fAir, fs);
    addInto(out, cn, n0, d.g_cracknoise * gC * sN);
    // ---- 2. body: broadband noise between about f_body / 3 and f_body * 4, gentle 6 dB/octave skirts, two decay rates. No resonant filter.
    var fb = d.f_body * (R > 0 ? 0.8 : 1), bd = noise(M, 'bd' + seed), ro = noise(M, 'ro' + seed);
    lp1(bd, fb * 4, fs); hp1(bd, fb / 3, fs); rmsNorm(bd); lp1(ro, fb * 6, fs); lp1(ro, fb * 6, fs); hp1(ro, fb / 3, fs); rmsNorm(ro);
    for (i = 0; i < M; i++) { t = i / fs; var at = 1 - Math.exp(-t / 0.0008); bd[i] = at * (d.g_body * Math.exp(-t / d.tau_body) * bd[i] + d.g_roar * Math.exp(-t / d.tau_roar) * ro[i]); }
    if (dist > 0) lp1(bd, fAir * 2, fs);
    addInto(out, bd, n0, 0.9 * gB * sB);
    // ---- 3. sub thump: f(t) = f_start / (1 + t / tp) never settles on a tone; harmonics 2 and 3; tanh saturation
    var ts = d.tau_sub * (R > 0 ? 0.7 : 1), f0 = d.f_sub_end * d.sub_ratio * (R > 0 ? 0.85 : 1) * (1 + 0.02 * (new Rng('sp' + seed).next() - 0.5)), tp = ts / (d.sub_ratio - 1), sub = new Float64Array(M), th = Math.tanh(d.sub_drive);
    for (i = 0; i < M; i++) {
      t = i / fs; var ph = TWO_PI * f0 * tp * Math.log(1 + t / tp), en = (1 - Math.exp(-t / 0.0015)) * Math.exp(-t / ts);
      sub[i] = en * Math.tanh(d.sub_drive * (Math.sin(ph) + d.sub_h2 * Math.pow(en, 0.3) * Math.sin(2 * ph) + d.sub_h3 * en * Math.sin(3 * ph)) / (1 + d.sub_h2 + d.sub_h3) * 1.6) / th;
    }
    addInto(out, sub, n0, d.g_sub * gS * sS);
    // ---- the bullet's own shock (supersonic rounds only). A suppressor does not change it.
    if (supersonic) {
      if (front) {      // direct: an N-wave and a short whip of noise, then the blast arrives dt later
        var T = nwaveT(d.mach, sim.bullet_diam_mm / 1000, sim.bullet_len_mm / 1000, 3), nn = Math.max(4, Math.round(T * fs)), nw = new Float64Array(nn + 2);   // design: 3 m miss distance
        for (i = 0; i <= nn; i++) nw[i + 1] = 1 - 2 * i / nn;
        var wh = noise(Math.round(0.06 * fs), 'wh' + seed); biquad(wh, 'hp', 1800, fs, 0.6); rmsNorm(wh); for (i = 0; i < wh.length; i++) wh[i] *= Math.exp(-(i / fs) / 0.006);
        lp1(nw, fAir * 2, fs); lp1(wh, fAir * 2, fs);
        addInto(out, nw, nPk, 0.8); addInto(out, wh, nPk, 0.3);                                                // design: level set by the miss distance, not by the range to the gun
      } else if (dist === 0) {   // at the gun: the shock comes back off the ground downrange as a hiss
        var hs = noise(Math.round(0.4 * fs), 'bh' + seed); biquad(hs, 'hp', 2500, fs, 0.6); lp1(hs, 9000, fs); rmsNorm(hs);
        for (i = 0; i < hs.length; i++) { t = i / fs; hs[i] *= (1 - Math.exp(-t / 0.012)) * Math.exp(-t / 0.07); }
        addInto(out, hs, n0 + Math.round(0.02 * fs), db2a(-22));                                               // design
      }
    }
    // ---- 4. the action, on the simulation's own clock, brought forward
    if (o.mech && d.g_mech > 0) { var mp = o.mechPeak || peakOf(o.mech); if (mp > 0) addInto(out, o.mech, nb, d.g_mech / mp * (dist > 0 ? gC : 1)); }
    return { x: out, nPeak: n0, len: N, blast_delay_s: dt, bullet_crack: front };
  }

  /* Several shots in one buffer with the same voice stealing fire() does live: when shot k starts, what is still
   * sounding of shot k-1 fades to steal_floor over steal_s. mk(k) -> { x, nPeak } for shot k; times in seconds. */
  function mixBurst(d, fs, times, mk) {
    var shots = times.map(function (_, k) { return mk(k); }), N = 0;
    times.forEach(function (t, k) { N = Math.max(N, Math.round(t * fs) + shots[k].x.length); });
    var out = new Float64Array(N), ns = Math.round(d.steal_s * fs);
    times.forEach(function (t, k) {
      var x = shots[k].x, n0 = Math.round(t * fs), cut = k + 1 < times.length ? Math.round((times[k + 1] - t) * fs) + shots[k + 1].nPeak - Math.round(0.002 * fs) : Infinity;
      for (var i = 0; i < x.length; i++) { var g = i < cut ? 1 : i < cut + ns ? 1 - (1 - d.steal_floor) * (i - cut) / ns : d.steal_floor * Math.exp(-(i - cut - ns) / (0.05 * fs)); out[n0 + i] += g * x[i]; }
    });
    return { x: out, nPeak: shots[0].nPeak, times: times };
  }

  /* A cinematic mechanical clip: the physical clip (modes and friction from the simulation) plus designed weight on each action event.
   * o: { fs, phys: Float64Array, events: [{ t, w (0..1 relative momentum or level), ms (contact time, ms) }], slides: [{ t0, t1, w }], seed } */
  function synthMech(d, o) {
    var fs = o.fs, n = o.phys.length + Math.round(0.08 * fs), out = new Float64Array(n), pk = peakOf(o.phys) || 1, i, t;
    addInto(out, o.phys, 0, 0.6 / pk);                                                     // design: the physical clip at 60 % of the mix
    (o.events || []).forEach(function (ev, j) {
      var w = clamp(ev.w, 0.05, 1), n0 = Math.round(ev.t * fs), m = Math.round(0.12 * fs);
      var cl = noise(m, 'cl' + o.seed + j); hp1(cl, 900, fs); lp1(cl, clamp(400 / (ev.ms || 0.2), 2500, 9000), fs); rmsNorm(cl);       // the clack: brighter for a shorter contact
      var tcl = 0.002 + 0.006 * w; for (i = 0; i < m; i++) { t = i / fs; cl[i] *= Math.exp(-t / tcl); }
      addInto(out, cl, n0, 0.22 + 0.45 * w);
      if (w > 0.3) {                                                                       // the weight of a heavy part stopping: low broadband thud and a short falling thump
        var tk = noise(m, 'tk' + o.seed + j); lp1(tk, 700, fs); lp1(tk, 700, fs); hp1(tk, 140, fs); rmsNorm(tk);
        var tt = 0.006 + 0.016 * w, f0 = 260, tp = 0.02;
        for (i = 0; i < m; i++) { t = i / fs; tk[i] = (1 - Math.exp(-t / 0.0006)) * (0.45 * w * Math.exp(-t / tt) * tk[i] + 0.22 * w * Math.exp(-t / 0.018) * Math.sin(TWO_PI * f0 * tp * Math.log(1 + t / tp))); }
        addInto(out, tk, n0, 1);
      }
    });
    (o.slides || []).forEach(function (s, j) {                                            // parts sliding: a broadband 'shhk' under a sine-squared envelope
      var m = Math.max(8, Math.round((s.t1 - s.t0) * fs)), sl = noise(m, 'sl' + o.seed + j); hp1(sl, 2000, fs); lp1(sl, 8000, fs); rmsNorm(sl);
      for (i = 0; i < m; i++) { var u = i / m; sl[i] *= Math.pow(Math.sin(Math.PI * Math.pow(u, 1.4)), 2); }
      addInto(out, sl, Math.round(s.t0 * fs), 0.12 * (s.w || 1));
    });
    var p = peakOf(out) || 1, k = db2a(-7) / p; for (i = 0; i < n; i++) out[i] *= k;      // design: mechanical clips peak at -7 dBFS before the bus
    return out;
  }

  /* The designed tail as a stereo impulse response. env: { kind: 'outdoor' | 'indoor', rt60 (s, from the gun's own surroundings),
   * slaps: [{ t (s), db (re direct, from the simulation) }] }. o: { fs, seed }. Returns [L, R] with summed energy 1 per channel. */
  function tailIR(env, d, o) {
    var fs = o.fs, indoor = env.kind === 'indoor', seed = 'ir' + (o.seed || 0) + env.kind;
    var rt = indoor ? clamp(env.rt60 * d.tail_rt_scale, 0.4, 3.5) : clamp(Math.max(env.rt60, 1.3) * d.tail_rt_scale, 0.9, 3.2);   // design: outdoors the tail is at least 1.3 s times the size scale
    var slaps = (env.slaps || []).slice(0, 4), last = 0; slaps.forEach(function (s) { last = Math.max(last, s.t); });
    var N = Math.round(Math.min(4.5, Math.max(rt * 1.25, last + 0.5)) * fs), ch = [];
    for (var c = 0; c < 2; c++) {
      var h = new Float64Array(N), lo = noise(N, seed + 'lo' + c), hi = noise(N, seed + 'hi' + c), i, t, n0 = Math.round((indoor ? 0.004 : 0.012) * fs);
      lp1(lo, 700, fs); rmsNorm(lo); hp1(hi, 700, fs); lp1(hi, d.tail_lp, fs); rmsNorm(hi);
      var aLo = 6.908 / rt, aHi = 6.908 / (rt * (indoor ? 0.6 : 0.5)), gd = indoor ? 1 : 0.55, rise = indoor ? 0.012 : 0.04;      // design: highs decay about twice as fast
      for (i = n0; i < N; i++) { t = (i - n0) / fs; h[i] = gd * (1 - Math.exp(-t / rise)) * (Math.exp(-aLo * t) * lo[i] + 0.8 * Math.exp(-aHi * t) * hi[i]); }
      var r = new Rng(seed + 'early');
      if (indoor) {                    // a dense room: many early returns in the first 80 ms, each a 3 ms smear so that none rings
        for (var j = 0; j < 14; j++) { var te = 0.005 + 0.075 * Math.pow(r.next(), 1.3) * clamp(env.rt60, 0.5, 1.5), ge = (0.9 - 0.6 * te / 0.12) * (r.next() < 0.5 ? -1 : 1) * (0.85 + 0.3 * (c ? r.next() : 1 - r.next())); smear(h, te, 0.003, ge * 1.6, seed + 'e' + j + c, fs, d.tail_lp * 1.5); }
      } else {                         // outdoors: near ground scatter, then the slapback returns the surroundings give
        smear(h, 0.007, 0.02, 0.9, seed + 'g' + c, fs, d.tail_lp);
        slaps.forEach(function (s, j) { var g = db2a(clamp(0.5 * s.db - 3, -16, -5)) * 6; smear(h, s.t, 0.03 + 0.04 * s.t, g, seed + 's' + j + c, fs, d.tail_lp / (1 + s.t)); });   // design: echoes brought forward, darker with distance
      }
      var e = 0; for (i = 0; i < N; i++) e += h[i] * h[i]; var k = 1 / Math.sqrt(e); for (i = 0; i < N; i++) h[i] *= k;
      var nfade = Math.round(0.05 * fs); for (i = 0; i < nfade; i++) h[N - 1 - i] *= i / nfade;
      ch.push(h);
    }
    return { channels: ch, rt60: rt, length_s: N / fs };
  }
  function smear(h, t0, dur, g, seed, fs, lp) {   // a burst of noise in place of a single tap: an echo with no comb filter
    var m = Math.max(16, Math.round(dur * 5 * fs)), x = noise(m, seed), i; lp1(x, lp, fs); rmsNorm(x);
    for (i = 0; i < m; i++) { var t = i / fs; x[i] *= (1 - Math.exp(-t / (dur * 0.15))) * Math.exp(-t / dur); }
    addInto(h, x, Math.round(t0 * fs), g);
  }

  // ------------------------------------------------------------------ measurement (shared by the acceptance page and the Node checks)
  function fftMag2(x, n0, n1, NF) {   // power spectrum of x[n0..n1) with a Hann window, zero padded to NF
    var re = new Float64Array(NF), im = new Float64Array(NF), L = n1 - n0, i, j;
    for (i = 0; i < L; i++) re[i] = x[n0 + i] * (0.5 - 0.5 * Math.cos(TWO_PI * i / (L - 1)));
    for (i = 1, j = 0; i < NF; i++) { var bit = NF >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { var tr = re[i]; re[i] = re[j]; re[j] = tr; } }
    for (var len = 2; len <= NF; len <<= 1) { var ang = -TWO_PI / len, wr = Math.cos(ang), wi = Math.sin(ang), half = len >> 1;
      for (i = 0; i < NF; i += len) { var cr = 1, ci = 0; for (var k = 0; k < half; k++) { var a = i + k, b = a + half, xr = re[b] * cr - im[b] * ci, xi = re[b] * ci + im[b] * cr; re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi; var tt = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = tt; } } }
    var p = new Float64Array(NF / 2); for (i = 0; i < NF / 2; i++) p[i] = re[i] * re[i] + im[i] * im[i]; return p;
  }
  /* The acceptance numbers. Onset = the first sample at 10 % of the peak. Short-term level = 10 ms RMS, 1 ms hop. */
  function metrics(x, fs) {
    var pk = peakOf(x), on = 0, i; for (i = 0; i < x.length; i++) if (Math.abs(x[i]) >= 0.1 * pk) { on = i; break; }
    var cum = new Float64Array(x.length + 1); for (i = 0; i < x.length; i++) cum[i + 1] = cum[i] + x[i] * x[i];
    var E = function (a, b) { a = Math.min(x.length, on + Math.round(a * fs)); b = Math.min(x.length, on + Math.round(b * fs)); return cum[b] - cum[a]; }, tot = cum[x.length] - cum[on];
    var w = Math.round(0.01 * fs), hop = Math.round(0.001 * fs), lv = [], mx = 0, im = 0;
    for (i = 0; i + w <= x.length; i += hop) { var v = (cum[i + w] - cum[i]) / w; lv.push(v); if (v > mx) { mx = v; im = lv.length - 1; } }
    var t20 = null, t40 = 0; for (i = im; i < lv.length; i++) { if (t20 === null && lv[i] < mx * 0.01) t20 = (i - im) / 1000; if (lv[i] >= mx * 1e-4) t40 = (i - im) / 1000; }
    var NF = 1; while (NF < x.length) NF *= 2; var re = fftMag2(x, 0, x.length, NF), band = function (a, b) { var s = 0; for (var k = Math.ceil(a * NF / fs); k <= Math.floor(b * NF / fs); k++) s += re[k]; return s; }, all = band(10, fs / 2 - 1);
    var r300 = Math.sqrt(E(0, 0.3) / Math.round(0.3 * fs)), clip = 0, run = 0; for (i = 0; i < x.length; i++) { if (Math.abs(x[i]) >= 0.999) { run++; if (run > clip) clip = run; } else run = 0; }
    var dB = function (v) { return Math.round(100 * 10 * Math.log10(v + 1e-30)) / 100; }, pc = function (v) { return Math.round(1000 * v / tot) / 10; };
    // loudness figure: energy of the loudest 400 ms after a simple ear weighting (high-pass 60 Hz, +4 dB shelf above 1.5 kHz, as in K-weighting)
    var y = Float64Array.from(x); biquad(y, 'hp', 60, fs, 0.5); biquad(y, 'hs', 1500, fs, 0.7071, 4); var c2 = 0, best = 0, W = Math.round(0.4 * fs), acc = new Float64Array(y.length + 1);
    for (i = 0; i < y.length; i++) acc[i + 1] = acc[i] + y[i] * y[i]; for (i = 0; i + W <= y.length; i += hop) best = Math.max(best, acc[i + W] - acc[i]); if (y.length < W) best = acc[y.length]; c2 = best / W;
    return { peak_dbfs: dB(pk * pk), clipped_run: clip, share_0_2ms: pc(E(0, 0.002)), share_2_10ms: pc(E(0.002, 0.01)), share_10_50ms: pc(E(0.01, 0.05)), share_50_300ms: pc(E(0.05, 0.3)), share_after_300ms: pc(tot - E(0, 0.3)),
      crest_db: Math.round(100 * 20 * Math.log10(pk / r300)) / 100, t_minus20_ms: t20 === null ? null : Math.round(t20 * 1000), tail_minus40_ms: Math.round(t40 * 1000),
      band_40_120_db: dB(band(40, 120) / all), band_120_300_db: dB(band(120, 300) / all), band_300_2k_db: dB(band(300, 2000) / all), band_2k_up_db: dB(band(2000, fs / 2 - 1) / all), centroid_hz: Math.round(centroid(re, NF, fs)), loudness_db: dB(c2) };
  }
  function centroid(p, NF, fs) { var a = 0, b = 0; for (var k = 1; k < p.length; k++) { a += k * p[k]; b += p[k]; } return a / b * fs / NF; }
  /* Narrow peaks: power in 1/12-octave bands (never fewer than 4 FFT bins) against the same spectrum smoothed over 1/3 octave, 150 Hz to 2 kHz.
   * xs: one signal or several (their power spectra are averaged, so that the chance fine structure of one noise burst does not count
   * as a resonance and a peak that is there every time does). Returns the largest excess and where; ring() gives how long that band lasts. */
  function spectralPeaks(xs, fs, o) {
    if (!Array.isArray(xs)) xs = [xs]; o = o || {};
    var t0 = o.t0 || 0, t1 = o.t1, NF = 1, P = null, n0, n1;
    xs.forEach(function (x) { n0 = Math.round(t0 * fs); n1 = Math.min(x.length, t1 ? Math.round(t1 * fs) : x.length); while (NF < 2 * (n1 - n0)) NF *= 2; });
    xs.forEach(function (x) { n0 = Math.round(t0 * fs); n1 = Math.min(x.length, t1 ? Math.round(t1 * fs) : x.length); var p = fftMag2(x, n0, n1, NF); if (!P) P = p; else for (var i = 0; i < p.length; i++) P[i] += p[i]; });
    var df = fs / NF, res = fs / (n1 - n0) * 2, worst = { excess_db: -99, hz: 0 }, bp = function (fa, fb) { var s = 0, c = 0; for (var k = Math.max(1, Math.round(fa / df)); k <= Math.round(fb / df); k++) { s += P[k]; c++; } return s / Math.max(1, c); };
    for (var f = (o.f0 || 150); f <= (o.f1 || 2000); f *= Math.pow(2, 1 / 24)) {
      var bw = Math.max(f * (Math.pow(2, 1 / 24) - Math.pow(2, -1 / 24)), 4 * res), nar = bp(f - bw / 2, f + bw / 2), wide = bp(f * Math.pow(2, -1 / 6) - bw / 2, f * Math.pow(2, 1 / 6) + bw / 2), ex = 10 * Math.log10(nar / wide);
      if (ex > worst.excess_db) worst = { excess_db: Math.round(ex * 100) / 100, hz: Math.round(f), band_hz: Math.round(bw) };
    }
    return worst;
  }
  /* Time for a band to fall 20 dB from its maximum (5 ms RMS), for the band at hz and its neighbours a third of an octave either side. */
  function ring(x, fs, hz) {
    var one = function (f) { var y = Float64Array.from(x); biquad(y, 'hp', f / 1.06, fs, 2); biquad(y, 'lp', f * 1.06, fs, 2); var w = Math.round(0.005 * fs), mx = 0, im = 0, lv = [], s = 0, i;
      for (i = 0; i < y.length; i++) { s += y[i] * y[i]; if (i >= w) s -= y[i - w] * y[i - w]; if (i % 48 === 0) { lv.push(s); if (s > mx) { mx = s; im = lv.length - 1; } } }
      for (i = im; i < lv.length; i++) if (lv[i] < mx * 0.01) return Math.round((i - im) * 48 / fs * 1000); return Math.round((lv.length - im) * 48 / fs * 1000); };
    return { band_ms: one(hz), below_ms: one(hz / 1.26), above_ms: one(hz * 1.26) };
  }

  // ------------------------------------------------------------------ Web Audio: the per-gun object and its chain
  var then2 = function (v, f) { return v && typeof v.then === 'function' ? v.then(f) : f(v); };
  var BUS = {                 // design: one bus for every gun
    drive_db: 3,              // into the saturator
    sat_knee: 0.9,            // y = knee * tanh(x / knee): soft saturation, 4x oversampled
    comp: { threshold: -14, knee: 8, ratio: 3, attack: 0.008, release: 0.2 },    // lets the first 8 ms through: the punch
    makeup_db: 0,
    limit: { threshold: -5, knee: 3, ratio: 20, attack: 0.001, release: 0.08 },
    post_db: 5,             // into the ceiling
    ceiling: 0.84,            // final soft ceiling, y = c * tanh(x / c): the output cannot pass c (-1.5 dBFS) before the resampler's overshoot
    hpd_makeup_db: 3,         // earmuffs sit after the bus (at the ear); an adapter with a deeper filter sets its own make-up (hpdMakeupDb)
    tail_send_hp: 80, tail_send_lp: 6000,
    mech_tail_send_db: -12,   // mechanical sounds are close: they excite the surroundings 12 dB less than a shot does
    distance_db_per_doubling: 3.2,   // output level against log2(1 + d / 4 m): 10 m -5.8 dB, 50 m -12 dB, 100 m -15 dB
    suppress_post_share: 0.15,       // of the suppressor's physical reduction, taken after the bus (the rest is in the layers)
  };
  function shaper(ctx, c) { var n = 8193, cv = new Float32Array(n); for (var i = 0; i < n; i++) { var x = (2 * i / (n - 1) - 1) * 4; cv[i] = c * Math.tanh(x / c); } var ws = ctx.createWaveShaper(); ws.curve = cv; ws.oversample = '4x'; var pre = ctx.createGain(); pre.gain.value = 0.25; pre.connect(ws); return { input: pre, output: ws }; }   // the curve spans +-4 so that nothing hits its ends
  function comp(ctx, p) { var c = ctx.createDynamicsCompressor(); c.threshold.value = p.threshold; c.knee.value = p.knee; c.ratio.value = p.ratio; c.attack.value = p.attack; c.release.value = p.release; return c; }
  function defaultHpd(ctx) { var lo = ctx.createBiquadFilter(), hi = ctx.createBiquadFilter(); lo.type = 'lowshelf'; lo.frequency.value = 250; lo.gain.value = -15; hi.type = 'highshelf'; hi.frequency.value = 1000; hi.gain.value = -18; lo.connect(hi); return { input: lo, output: hi }; }   // about 15 dB at 125 Hz, 33 dB above 1 kHz

  /* adapter (one per gun; see each asset's sound module):
   *   id, fs, defaultKey, defaultOverlay, sim(key) -> sim values, times(key) -> { base, times } for multi-shot keys,
   *   physical(key, sup) -> { blast, mech, nPeak } Float64Arrays of one shot (may be a Promise), suppression(sup) -> dB (may be a Promise),
   *   mechClip(name, sup) -> { phys, events, slides }, env(overlay) -> { kind, rt60, slaps } or null for dry,
   *   realShot(key, o), realMech(name, o) -> AudioBuffer, realChain(o, ctx) -> { input, output } (may be a Promise), hpd(ctx) -> { input, output } or null */
  function makeGun(ctx, A, opts) {
    opts = opts || {};
    var G = { mode: opts.mode === 'realistic' ? 'realistic' : 'cinematic', adapter: A, BUS: BUS }, cache = new Map(), meta = new WeakMap(), designs = {};
    var memo = function (k, f) { if (!cache.has(k)) cache.set(k, f()); return cache.get(k); };
    G.design = function (key) { key = key || A.defaultKey; var b = A.times(key).base; return designs[b] || (designs[b] = design(A.sim(b))); };
    G.setMode = function (m) { G.mode = m === 'realistic' ? 'realistic' : 'cinematic'; return G; };
    G.info = function (buf) { return meta.get(buf); };
    function toBuffer(x, k, info) { var b = ctx.createBuffer(1, x.length, A.fs), ch = b.getChannelData(0); for (var i = 0; i < x.length; i++) ch[i] = x[i] * k; meta.set(b, info); return b; }
    var supId = new WeakMap(), supN = 0, sid = function (s) { if (!s) return ''; if (!supId.has(s)) supId.set(s, ++supN); return 's' + supId.get(s); };
    // the scale of every cinematic shot of a load: the bare shot at the gun, seed 0, peaks at -1 dBFS
    function refScale(base) { return memo('ref/' + base, function () { return then2(A.physical(base, null), function (ph) { var d = G.design(base), s = synthShot(d, { fs: A.fs, crack: ph.blast, nPeak: ph.nPeak, mech: ph.mech, seed: 0 }); return { k: db2a(-1) / peakOf(s.x), crackPeak: peakOf(ph.blast), mechPeak: ph.mech ? peakOf(ph.mech) : 0, nPeak: s.nPeak }; }); }); }
    /* The cinematic dry shot. o: { distance, bearing, perspective, suppressor, seed }. Sync unless the adapter is async (a suppressor being built). */
    G.cineShot = function (key, o) {
      key = key || A.defaultKey; o = o || {};
      var dist = o.distance || 0, bearing = o.bearing || 'front', sup = o.suppressor || A.builtSuppressed || null;
      if (o.perspective && A.perspective) { var pv = A.perspective(o.perspective); if (pv) { dist = pv.distance; bearing = pv.bearing; } }
      var tm = A.times(key), d = G.design(key), ck = 'cine/' + key + '/' + dist + '/' + bearing + '/' + sid(sup) + '/' + (o.seed || 0);
      return memo(ck, function () {
        return then2(refScale(tm.base), function (ref) { return then2(A.physical(tm.base, sup), function (ph) { return then2(sup ? A.suppression(sup) : 0, function (R) {
          var one = function (k) { var j = new Rng('shot' + k + '/' + (o.seed || 0)), g = db2a(1.2 * (j.next() - 0.5)), s = synthShot(d, { fs: A.fs, crack: ph.blast, nPeak: ref.nPeak, mech: ph.mech, mechPeak: ref.mechPeak, refCrackPeak: ref.crackPeak, seed: (o.seed || 0) * 1000 + k, distance: dist, bearing: bearing, suppress_db: R }); if (k) for (var i = 0; i < s.x.length; i++) s.x[i] *= g; return s; };   // design: +-0.6 dB from shot to shot
          var s = tm.times.length > 1 ? mixBurst(d, A.fs, tm.times, one) : one(0);
          return toBuffer(s.x, ref.k, { mode: 'cinematic', key: key, times: tm.times, distance_m: dist, bearing: bearing, suppress_db: R, onset_s: s.nPeak / A.fs, blast_delay_s: s.blast_delay_s || 0, arrival_s: dist / C0, size: d.size });
        }); }); });
      });
    };
    G.cineMech = function (name, o) { o = o || {}; var sup = o.suppressor || A.builtSuppressed || null; return memo('cmech/' + name + '/' + sid(sup), function () { return then2(A.mechClip(name, sup), function (m) { return toBuffer(synthMech(G.design(), { fs: A.fs, phys: m.phys, events: m.events, slides: m.slides, seed: name }), 1, { mode: 'cinematic', clip: name }); }); }); };
    G.shot = function (key, o) { o = o || {}; return (o.mode || G.mode) === 'realistic' ? A.realShot(key || A.defaultKey, o) : G.cineShot(key, o); };
    G.mech = function (name, o) { o = o || {}; return (o.mode || G.mode) === 'realistic' ? A.realMech(name, o) : G.cineMech(name, o); };
    G.tail = function (overlay, o) { o = o || {}; var env = A.env(overlay); if (!env) return null; var d = G.design(o.key); return memo('tail/' + overlay + '/' + d.size + '/' + (o.seed || 0), function () { var ir = tailIR(env, d, { fs: A.fs, seed: o.seed || 0 }), b = ctx.createBuffer(2, ir.channels[0].length, A.fs); b.getChannelData(0).set(ir.channels[0]); b.getChannelData(1).set(ir.channels[1]); meta.set(b, { env: env, rt60: ir.rt60 }); return b; }); };

    /* chain(o, ctx2): input -> [tail convolver] -> [earmuffs] -> bus -> output, or the gun's own realistic chain.
     * o: { mode, overlay (undefined = the gun's default, null or 'dry' = none), hpd, distance, bearing, perspective, suppressor, key, seed, ear, peakDb }
     * Returns the chain (HK416: a Promise of it, as before). Always usable as: const c = await S.chain(o). */
    G.chain = function (o, actx) {
      var cx = actx || ctx, input = cx.createGain(), output = cx.createGain(), mechIn = cx.createGain(), inner = [], voices = [], duck = null, sendG = null;
      var c = { input: input, output: output, opts: {}, ctx: cx };
      c.set = function (n) {
        Object.assign(c.opts, n || {}); var q = c.opts, mode = q.mode || G.mode; c.mode = mode;
        var teardown = function () { input.disconnect(); mechIn.disconnect(); inner.forEach(function (x) { try { x.disconnect(); } catch (e) { /* already free */ } }); inner = []; duck = null; sendG = null; };
        if (mode === 'realistic') {
          var ro = { perspective: q.perspective || 'shooter', hpd: !!q.hpd, ear: q.ear !== false }; if ('overlay' in q) ro.overlay = q.overlay; if (q.peakDb != null) ro.peakDb = q.peakDb;
          return then2(A.realChain(ro, cx, q), function (rc) { teardown(); input.connect(rc.input); mechIn.connect(rc.input); rc.output.connect(output); inner = [rc.output]; return c; });
        }
        var key = q.key || A.defaultKey, d = G.design(key), ov = 'overlay' in q && q.overlay !== undefined ? q.overlay : A.defaultOverlay, dist = q.distance || 0, sup = q.suppressor || A.builtSuppressed || null;
        if (q.perspective && A.perspective) { var pv = A.perspective(q.perspective); if (pv) dist = pv.distance; }
        return then2(sup ? A.suppression(sup) : 0, function (R) {
          teardown();
          var sum = cx.createGain(), dry = cx.createGain(); input.connect(dry); dry.connect(sum); mechIn.connect(sum); inner.push(dry, sum);
          var tb = ov && ov !== 'dry' ? G.tail(ov, { key: key, seed: q.seed }) : null, dbl = Math.log2(1 + dist / 4);
          if (tb) {
            var hp = cx.createBiquadFilter(), lp = cx.createBiquadFilter(), cv = cx.createConvolver(), tg = cx.createGain(), ms = cx.createGain(); sendG = cx.createGain(); duck = cx.createGain();
            hp.type = 'highpass'; hp.frequency.value = BUS.tail_send_hp; hp.Q.value = 0.5; lp.type = 'lowpass'; lp.Q.value = 0.5;
            lp.frequency.value = BUS.tail_send_lp * (R > 0 ? 0.6 : 1) / (1 + dist / 60);                                           // design: a suppressed or distant shot leaves a darker tail
            cv.normalize = false; cv.buffer = tb; ms.gain.value = db2a(BUS.mech_tail_send_db);
            var env = A.env(ov);
            tg.gain.value = db2a(d.tail_db + (env.kind === 'indoor' ? 3 : 0) - 0.5 * R + 1.2 * dbl);                               // design: against the dry shot the tail gains 1.2 dB per doubling of distance and loses half the suppressor's reduction
            input.connect(sendG); mechIn.connect(ms); ms.connect(hp); sendG.connect(hp); hp.connect(lp); lp.connect(cv); cv.connect(duck); duck.connect(tg); tg.connect(sum); inner.push(sendG, ms, hp, lp, cv, duck, tg);
          }
          var drive = cx.createGain(); drive.gain.value = db2a(BUS.drive_db); var sat = shaper(cx, BUS.sat_knee), c1 = comp(cx, BUS.comp), mu = cx.createGain(), c2 = comp(cx, BUS.limit), po = cx.createGain(), ceil = shaper(cx, BUS.ceiling), post = cx.createGain();
          mu.gain.value = db2a(BUS.makeup_db); po.gain.value = db2a(BUS.post_db);
          post.gain.value = db2a(d.trim_db - BUS.distance_db_per_doubling * dbl - BUS.suppress_post_share * R);
          sum.connect(drive); drive.connect(sat.input); sat.output.connect(c1); c1.connect(mu); mu.connect(c2); c2.connect(po); po.connect(ceil.input); ceil.output.connect(post);
          inner.push(drive, sat.input, sat.output, c1, mu, c2, po, ceil.input, ceil.output, post);
          if (q.hpd) { var h = (A.hpd && A.hpd(cx)) || defaultHpd(cx), mk = cx.createGain(); mk.gain.value = db2a(A.hpdMakeupDb != null && A.hpd ? A.hpdMakeupDb : BUS.hpd_makeup_db); post.connect(h.input); h.output.connect(mk); mk.connect(output); inner.push(h.input, h.output, mk); }
          else post.connect(output);
          return c;
        });
      };
      function start(buf, when, gain, dest) { var src = cx.createBufferSource(), g = cx.createGain(); src.buffer = buf; g.gain.value = gain == null ? 1 : gain; src.connect(g); g.connect(dest || input); src.start(when); return { source: src, gain: g, when: when, buffer: buf }; }
      /* One shot through the chain, with voice stealing and tail ducking. f: { key, when, seed, gain, pump }. Returns { source, gain, when } (a Promise of it if the gun is async). */
      c.fire = function (f) {
        f = f || {}; var q = c.opts, key = f.key || q.key || A.defaultKey, when = f.when == null ? cx.currentTime : f.when, mode = c.mode;
        var so = { distance: q.distance, bearing: q.bearing, perspective: q.perspective, suppressor: q.suppressor, seed: f.seed == null ? (c.nfired = (c.nfired || 0) + 1) % 8 : f.seed, mode: mode, ground: q.ground };
        var buf = mode === 'realistic' ? A.realShot(key, Object.assign({}, q, so)) : G.cineShot(key, so);
        return then2(buf, function (b) {
          var d = G.design(key), inf = meta.get(b) || {}, on = inf.onset_s || 0, v = start(b, when, f.gain);
          if (mode !== 'realistic') {
            voices = voices.filter(function (p) { return p.when + p.buffer.duration > when; });
            voices.forEach(function (p) { var t = when + on - 0.002; p.gain.gain.setValueAtTime(p.gain.gain.value, t); p.gain.gain.linearRampToValueAtTime(d.steal_floor * (p.level || 1), t + d.steal_s); p.gain.gain.setTargetAtTime(0, t + d.steal_s, 0.05); });   // voice stealing
            if (duck && voices.length) { duck.gain.setTargetAtTime(d.duck_floor, when + on - 0.004, 0.003); duck.gain.setTargetAtTime(1, when + on + 0.03, d.duck_tau); }                                                                                    // the tail gives way to the new shot
            v.level = f.gain == null ? 1 : f.gain; voices.push(v);
            if (f.pump && A.pumpClip) c.mech(A.pumpClip, { when: when + on + (typeof f.pump === 'number' ? f.pump : d.pump_delay_s) });
          }
          return v;
        });
      };
      /* Autofire: shots at the gun's cyclic period (or f.period). f: { shots, period, when, key }. */
      c.auto = function (f) { f = f || {}; var per = f.period || A.sim(A.times(f.key || c.opts.key || A.defaultKey).base).cyclic_period_s || 0.5, t0 = f.when == null ? cx.currentTime + 0.01 : f.when, out = []; for (var k = 0; k < (f.shots || 3); k++) out.push(c.fire({ key: f.key, when: t0 + k * per, seed: k % 8 })); return out; };
      /* A mechanical sound through the chain. f: { when, gain }. */
      c.mech = function (name, f) { f = f || {}; var mode = c.mode, when = f.when == null ? cx.currentTime : f.when; return then2(mode === 'realistic' ? A.realMech(name, c.opts) : G.cineMech(name, c.opts), function (b) { return start(b, when, f.gain, mechIn); }); };
      c.mechInput = mechIn;
      return c.set(o || {});
    };
    return G;
  }

  return { design: design, synthShot: synthShot, mixBurst: mixBurst, synthMech: synthMech, tailIR: tailIR, metrics: metrics, spectralPeaks: spectralPeaks, ring: ring, makeGun: makeGun, BUS: BUS, Rng: Rng, biquad: biquad, version: 1 };
});
