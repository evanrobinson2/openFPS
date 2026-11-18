/* Shotgun 590 synthesised sound, version 2. Renders params.json (built by sim.py) into audio; no recordings, no dependencies.
 *
 *   <script src="shotgun590-sound.js"></script>              -> window.Shotgun590Sound
 *   const S = require('./shotgun590-sound.js')                (Node: render() only)
 *
 *   await S.load('params.json')                // or S.use(parsedJson)
 *   S.names()                                  // ['shot_buck00_shooter', 'shot_buck00_shooter_covered', 'shot_buck00_shooter_free', 'pump', ...]
 *   const pa = S.render('pump')                // Float64Array of pascals at the listener, 48 kHz
 *   const buf = S.buffer(audioCtx, 'pump')     // AudioBuffer scaled by S.scale (full scale = S.fullScalePa pascals)
 *   S.play(audioCtx, 'shot_buck00_shooter', { destination: node, when: audioCtx.currentTime, gain: 1 })
 *
 * Shots come in four surroundings: 'shot_<load>_<listener>' is the default, a plywood-lined training room;
 * '..._covered' is a covered firing point on an outdoor range (roof, back wall, concrete pad, backstop);
 * '..._field' is open grass (ground reflection only); '..._free' is the dry shot with no reflection at all, for a
 * game that adds its own room.
 *
 * Levels: every buffer shares one scale, so a rack is as much quieter than a shot as the simulation says
 * (about 53 dB). Pass { normalize: true } to buffer() or play() to get each sound at full scale and mix by ear;
 * S.info(name).peak_db gives the simulated peak level in dB re 20 uPa either way.
 * Time zero of a shot or dry_fire is the trigger break; of the others, the start of the motion.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.Shotgun590Sound = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, cache = {};
  function need() { if (!D) throw new Error('Shotgun590Sound: call use(data) or load(url) first'); return D; }
  function use(data) { D = data; cache = {}; api.fullScalePa = 0; for (var k in D.sounds) api.fullScalePa = Math.max(api.fullScalePa, D.sounds[k].peak_pa); api.fullScalePa *= 1.05; return api; }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }
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
  /* The component list of one sound -> pascals. Same arithmetic as render() in sim.py.
   * filters: the table of short filters in params.json (the ground's reflection), needed by components that name one. */
  function renderSound(snd, fs, filters) {
    var n = Math.round(snd.duration * fs), y = new Float64Array(n), i, j, t, c, i0, end, u, len;
    for (var k = 0; k < snd.components.length; k++) {
      c = snd.components[k]; i0 = Math.max(0, Math.ceil(c.t0 * fs));
      if (i0 >= n) continue;
      if (c.kind === 'friedlander') {
        len = Math.floor(c.tpos * fs * 8) + 1;
        if (c.fir) {                                         // a blast wave through a filter: the wave, convolved, then added
          var F = (filters || (D && D.filters) || {})[c.fir]; if (!F) throw new Error('Shotgun590Sound: no filter ' + c.fir);
          var w = new Float64Array(len), h = F.taps, m = h.length;
          for (i = 0; i < len; i++) { u = ((i0 + i) / fs - c.t0) / c.tpos; w[i] = c.amp * (1 - u) * Math.exp(-u); }
          for (i = 0; i < len + m - 1; i++) {
            var o = i0 - F.lag + i; if (o < 0 || o >= n) continue;
            var acc = 0, j0 = Math.max(0, i - m + 1), j1 = Math.min(len - 1, i);
            for (j = j0; j <= j1; j++) acc += w[j] * h[i - j];
            y[o] += acc;
          }
        } else {
          end = Math.min(n, i0 + len);
          for (i = i0; i < end; i++) { u = (i / fs - c.t0) / c.tpos; y[i] += c.amp * (1 - u) * Math.exp(-u); }
        }
      } else if (c.kind === 'jet') {                           // gas emptying from the bore: filtered noise under the blow-down envelope
        var rj = rng(c.seed), wj = 2 * Math.PI * c.fc / fs, alj = Math.sin(wj) / (2 * c.q), aj = 1 + alj;
        var bj0 = alj / aj, bj2 = -alj / aj, aj1 = -2 * Math.cos(wj) / aj, aj2 = (1 - alj) / aj, p1 = 0, p2 = 0, q1 = 0, q2 = 0;
        end = Math.min(n, i0 + Math.floor(c.dur * fs) + 1);
        for (i = i0; i < end; i++) {
          t = i / fs - c.t0; var xj = 2 * rj() - 1, vj = bj0 * xj + bj2 * p2 - aj1 * q1 - aj2 * q2; p2 = p1; p1 = xj; q2 = q1; q1 = vj;
          y[i] += c.amp * 3.0 * (t < c.attack ? t / c.attack : 1) * Math.pow(1 + t / c.theta, -c.n) * vj;
        }
      } else if (c.kind === 'mode') {
        var w = 2 * Math.PI * c.f; end = Math.min(n, i0 + Math.floor(c.decay * fs * 9) + 1);
        for (i = i0; i < end; i++) { t = i / fs - c.t0; y[i] += c.amp * Math.exp(-t / c.decay) * Math.sin(w * t + c.phase); }
      } else {
        var r = rng(c.seed), w0 = 2 * Math.PI * c.fc / fs, al = Math.sin(w0) / (2 * c.q), a0 = 1 + al;
        var b0 = al / a0, b2 = -al / a0, a1 = -2 * Math.cos(w0) / a0, a2 = (1 - al) / a0, x1 = 0, x2 = 0, y1 = 0, y2 = 0;
        end = Math.min(n, i0 + Math.floor((c.attack + c.hold + c.decay * 9) * fs) + 1);
        for (i = i0; i < end; i++) {
          t = i / fs - c.t0; var x = 2 * r() - 1, v = b0 * x + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = v;
          var env = c.attack > 0 ? (t < c.attack ? t / c.attack : 1) : 1;
          if (t > c.attack + c.hold) env = Math.exp(-(t - c.attack - c.hold) / c.decay);
          y[i] += c.amp * 3.0 * env * v;
        }
      }
    }
    return y;
  }
  function info(name) { var s = need().sounds[name]; if (!s) throw new Error('Shotgun590Sound: no sound ' + name); return s; }
  function render(name) { if (!cache[name]) cache[name] = renderSound(info(name), need().fs, need().filters); return cache[name]; }
  function buffer(ac, name, opts) {
    var y = render(name), fs = need().fs, buf = ac.createBuffer(1, y.length, fs), ch = buf.getChannelData(0);
    var k = (opts && opts.normalize) ? 0.95 / info(name).peak_pa : 1 / api.fullScalePa;
    for (var i = 0; i < y.length; i++) ch[i] = y[i] * k;
    return buf;
  }
  function playRealistic(ac, name, opts) {
    var o = opts || {}, src = ac.createBufferSource(), g = ac.createGain();
    src.buffer = buffer(ac, name, o); g.gain.value = o.gain != null ? o.gain : 1; src.connect(g); g.connect(o.destination || ac.destination); src.start(o.when || 0);
    return src;
  }

  /* ---- cinematic mode (the default since 2026-11-17): the designed sound of shared/cinematic-sound/cinematic-sound.js, sized by this gun's simulation.
   * The realistic sounds above are unchanged and are what mode 'realistic' plays. */
  var SELF_URL = (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) || null;
  var CS_URL = SELF_URL ? new URL('../../../shared/cinematic-sound/cinematic-sound.js', SELF_URL).href : null, csWait = null;
  function cinematicLib() {            // the shared module: already loaded, or required (Node), or fetched once by a script tag
    var g = typeof globalThis !== 'undefined' ? globalThis : this;
    if (g.OpenFPSCinematicSound) return g.OpenFPSCinematicSound;
    if (typeof module === 'object' && module.exports && typeof require === 'function') return require('../../../shared/cinematic-sound/cinematic-sound.js');
    return null;
  }
  function cinematicReady() {
    if (cinematicLib()) return Promise.resolve(cinematicLib());
    if (!csWait) csWait = new Promise(function (res, rej) { if (!CS_URL) return rej(new Error('Shotgun590Sound: load shared/cinematic-sound/cinematic-sound.js first')); var el = document.createElement('script'); el.src = CS_URL; el.onload = function () { res(cinematicLib()); }; el.onerror = function () { rej(new Error('Shotgun590Sound: could not load ' + CS_URL)); }; document.head.appendChild(el); });
    return csWait;
  }
  if (CS_URL) cinematicReady().catch(function () {});
  /* Simulation values the design reads. Copied from action/action.json and ballistics/ballistics.json (the sound module does not load them);
   * shared/cinematic-sound/check.mjs fails if they drift. supersonic_to_m: where the ballistics table falls below 343.2 m/s.
   * bullet_len_mm: a pellet's diameter; for the slug 25 mm is a guess (the maker does not publish it). */
  var CINE_SIM = {
    buck00: { muzzle_energy_J: 2568.7, muzzle_velocity: 403.86, bore_mm: 18.5, barrel_mm: 508, bullet_diam_mm: 8.382, bullet_len_mm: 8.382, supersonic_to_m: 18.6 },
    slug: { muzzle_energy_J: 3417.4, muzzle_velocity: 490.73, bore_mm: 18.5, barrel_mm: 508, bullet_diam_mm: 18.5, bullet_len_mm: 25, supersonic_to_m: 94.1 }
  };
  var OVERLAYS = { range: 'outdoor', covered: 'outdoor', field: 'outdoor', room: 'indoor' };          // design label: which kind of tail each of the simulation's surroundings gets
  function soundName(load, listener, env) { return 'shot_' + load + '_' + (listener || 'shooter') + (env && env !== 'range' ? '_' + env : ''); }
  function parseName(name) {
    var m = /^shot_(buck00|slug)_(shooter|bystander)(?:_(room|covered|field|free))?$/.exec(name);
    if (m) return { key: m[1], overlay: m[3] === 'free' ? null : (m[3] || 'range'), distance: m[2] === 'bystander' ? 5 : 0, bearing: 'side' };
    m = /^shot_(buck00|slug)_range_(side|front)_(\d+)m$/.exec(name);
    if (m) return { key: m[1], overlay: 'range', distance: +m[3], bearing: m[2] };
    return null;
  }
  function adapter(ac) {
    var d = need(), fs = d.fs, pumpMax = 0.6349 * 1.114;
    return {
      id: 'shotgun-590', fs: fs, defaultKey: 'buck00', defaultOverlay: 'range', pumpClip: 'pump', builtSuppressed: null,
      sim: function (key) { var s = d.shot_source[key], c = CINE_SIM[key]; return { muzzle_energy_J: c.muzzle_energy_J, gas_energy_J: s.gas_energy_J, gas_mass_g: s.charge_kg * 1000, bore_mm: c.bore_mm, barrel_mm: c.barrel_mm, muzzle_velocity: c.muzzle_velocity, cyclic_period_s: null, bullet_diam_mm: c.bullet_diam_mm, bullet_len_mm: c.bullet_len_mm, supersonic_to_m: c.supersonic_to_m }; },
      times: function (key) { return { base: key, times: [0] }; },
      perspective: function (p) { return p === 'bystander' ? { distance: 5, bearing: 'side' } : p === 'shooter' ? { distance: 0, bearing: 'front' } : null; },
      /* the physical blast alone: the blast wave and the gas jet of the free-field shot. The receiver, barrel and stock modes of the
       * simulated shot are left out on purpose: in the cinematic shot they read as a struck box. They stay in the pump and in 'realistic'. */
      physical: function (key) { var s = info(soundName(key, 'shooter', 'free')), comps = s.components.filter(function (c) { return c.kind === 'friedlander' || c.kind === 'jet'; }); return { blast: renderSound({ duration: s.duration, components: comps }, fs, d.filters), mech: null }; },
      suppression: function () { return 0; },
      mechClip: function (name) {
        var s = info(name), ev = (s.events || []).map(function (e) { return { t: e.t, w: e.mass_kg * e.speed / pumpMax, ms: e.contact_ms, name: e.event }; }), slides = [], at = function (n) { for (var i = 0; i < ev.length; i++) if (ev[i].name === n) return ev[i].t; return null; };
        var rs = at('rear_stop'), lk = at('locked'), un = at('unlock');
        if (rs !== null) slides.push({ t0: Math.max(0, (un === null ? rs - 0.11 : un) - 0.03), t1: rs, w: 1 });                 // the forend coming back
        if (lk !== null) slides.push({ t0: rs !== null ? rs + 0.02 : Math.max(0, lk - 0.16), t1: lk, w: 1 });                      // and going forward (0.02 s dwell: action.json stroke_dwell)
        return { phys: render(name), events: ev, slides: slides };
      },
      env: function (ov) {
        if (!ov || ov === 'dry' || ov === 'free' || !OVERLAYS[ov]) return null;
        var su = info(soundName('buck00', 'shooter', ov)).surroundings || {}, slaps = [];
        if (su.berm_arrives_ms) slaps.push({ t: su.berm_arrives_ms / 1000, db: su.berm_energy_db_re_direct });
        if (su.trees_first_ms) slaps.push({ t: su.trees_first_ms / 1000, db: su.trees_energy_db_re_direct });
        var rt = su.t60_s ? (su.t60_s[0] + su.t60_s[1] + su.t60_s[2]) / 3 : su.scattered_decay_ms ? 6.908 * su.scattered_decay_ms / 1000 : 0;
        return { kind: OVERLAYS[ov], rt60: rt, slaps: slaps };
      },
      realShot: function (key, o) { o = o || {}; var p = parseName(key); if (p) return buffer(ac, key, { normalize: true }); var ov = 'overlay' in o && o.overlay !== undefined ? o.overlay : 'range'; return buffer(ac, soundName(key, o.perspective === 'bystander' ? 'bystander' : 'shooter', ov === null || ov === 'dry' ? 'free' : ov), { normalize: true }); },
      realMech: function (name) { return buffer(ac, name, { normalize: true }); },
      realChain: function (o, cx) { var a = cx.createGain(), b = cx.createGain(); if (o.hpd) { var lo = cx.createBiquadFilter(), hi = cx.createBiquadFilter(); lo.type = 'lowshelf'; lo.frequency.value = 250; lo.gain.value = -15; hi.type = 'highshelf'; hi.frequency.value = 1000; hi.gain.value = -18; a.connect(lo); lo.connect(hi); hi.connect(b); b.gain.value = 4; } else a.connect(b); return { input: a, output: b }; },
      hpd: null
    };
  }
  /* The same object every openFPS gun returns: S.build(ctx, { mode: 'cinematic' | 'realistic', params: url or parsed json }) -> Promise of
   * { mode, setMode(m), shot(load, o), mech(clip, o), chain(o), info(buffer), design(load), loads, overlays, clips, defaultOverlay }.
   * See README.md ("Cinematic mode") for chain.fire(), chain.mech(), chain.set(). */
  function build(ac, opts) {
    opts = opts || {};
    var p = opts.params ? (typeof opts.params === 'string' ? load(opts.params) : Promise.resolve(use(opts.params))) : D ? Promise.resolve(api) : load(SELF_URL ? new URL('params.json', SELF_URL).href : 'params.json');
    return Promise.all([p, cinematicReady()]).then(function (r) { return gunFor(ac, opts.mode); });
  }
  var guns = typeof WeakMap === 'function' ? new WeakMap() : null;
  function gunFor(ac, mode) {
    var CS = cinematicLib(), A = adapter(ac), G = CS.makeGun(ac, A, { mode: mode });
    G.loads = Object.keys(need().shot_source); G.overlays = Object.keys(OVERLAYS); G.clips = ['pump', 'pump_back', 'pump_forward', 'dry_fire', 'shell_insert', 'safety', 'action_release']; G.defaultOverlay = 'range'; G.params = need(); G.raw = api;
    return G;
  }
  /* play(): cinematic by default. Shot names are mapped onto the cinematic shot (load, surroundings, listener distance); the other names are
   * the cinematic mechanical clips. { mode: 'realistic' } plays the simulated sound exactly as before. */
  function play(ac, name, opts) {
    var o = opts || {}, CS = cinematicLib();
    if (o.mode === 'realistic' || !CS || !guns) return playRealistic(ac, name, o);
    var st = guns.get(ac); if (!st) { st = { gun: gunFor(ac), chains: new Map() }; guns.set(ac, st); }
    var dest = o.destination || ac.destination, ch = null; st.chains.forEach(function (c, d2) { if (d2 === dest) ch = c; });
    if (!ch) { ch = st.gun.chain({ overlay: 'range' }); ch.output.connect(dest); st.chains.set(dest, ch); }
    var p = parseName(name), when = o.when || ac.currentTime;
    if (!p) return ch.mech(name, { when: when, gain: o.gain }).source;
    if (ch.opts.overlay !== p.overlay || (ch.opts.distance || 0) !== p.distance || ch.opts.bearing !== p.bearing || !!ch.opts.hpd !== !!o.hpd) ch.set({ overlay: p.overlay, distance: p.distance, bearing: p.bearing, hpd: !!o.hpd });
    return ch.fire({ key: p.key, when: when, gain: o.gain, pump: o.pump }).source;
  }
  var api = { use: use, load: load, names: function () { return Object.keys(need().sounds); }, info: info, render: render, renderSound: renderSound, buffer: buffer, play: play, playRealistic: playRealistic, build: build, cinematicReady: cinematicReady, CINE_SIM: CINE_SIM, fullScalePa: 0,
              get data() { return D; } };
  return api;
});
