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
  function play(ac, name, opts) {
    var o = opts || {}, src = ac.createBufferSource(), g = ac.createGain();
    src.buffer = buffer(ac, name, o); g.gain.value = o.gain != null ? o.gain : 1; src.connect(g); g.connect(o.destination || ac.destination); src.start(o.when || 0);
    return src;
  }
  var api = { use: use, load: load, names: function () { return Object.keys(need().sounds); }, info: info, render: render, renderSound: renderSound, buffer: buffer, play: play, fullScalePa: 0,
              get data() { return D; } };
  return api;
});
