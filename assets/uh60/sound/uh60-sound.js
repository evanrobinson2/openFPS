// UH-60 sound, synthesised from the flight state. Nothing is sampled, filtered or learned from a recording.
// Sources, each driven by uh60-flight.js telemetry:
//   main rotor   blade-passage pulses at 4 x rotor speed (17.2 Hz at 100 percent): a loading pulse that scales with
//                thrust, a thickness pulse that sharpens with advancing-tip Mach number, blade-vortex-interaction
//                slap spikes driven by the model's BVI index, and broadband vortex noise swished at blade passage
//   tail rotor   4 blades at 4.61 x rotor speed (79.3 Hz), buzzier, scales with tail thrust, beats with the main rotor
//   engines      two T700 gas generators: whine tones that follow Ng (slightly detuned, so they beat), combustion
//                roar that follows power, exhaust hiss
//   transmission gear-mesh tones locked to rotor speed, louder with torque, with shaft-order sidebands
//   wind         airframe noise that rises with airspeed
// Two renderings of the same simulation, like the guns: 'cinematic' (default: heavier thump, more slap, saturation)
// and 'realistic' (physical balance: more broadband and whine, less bass). Listener: cockpit, cabin or outside.
// coreFactory() is self-contained so it can run in an AudioWorklet and in node (verify.mjs).

export function coreFactory(sampleRate) {
  const TAU = 2 * Math.PI, sr = sampleRate;
  const P = {           // target parameters, set from telemetry
    omega: 0, thrust: 0, tipMach: 0.65, bvi: 0, tailThrust: 0, ng1: 0, ng2: 0, pw1: 0, pw2: 0, torque: 0, ias: 0,
    cinematic: 1, inside: 1, cabin: 0, distance: 30, front: 0.5, master: 0.8, doorsOpen: 0,
  };
  const C = { ...P };   // smoothed values
  let phM = 0, phT = 0, phE = [0, 0, 0, 0], phG = [0, 0, 0], seed = 22222, slapAmp = [1, 1, 1, 1], lastBlade = -1;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2147483648 - 1; };
  const lp = (c) => { let y = 0; const f = { set(hz) { f.a = 1 - Math.exp(-TAU * hz / sr); }, run(x) { y += f.a * (x - y); return y; }, a: 0.1 }; f.set(c); return f; };
  const bp = (hz, q) => {
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0, b0, a1, a2;
    const f = { set(h, qq) { const w = TAU * Math.min(h, sr * 0.45) / sr, al = Math.sin(w) / (2 * qq), a0 = 1 + al; b0 = al / a0; a1 = -2 * Math.cos(w) / a0; a2 = (1 - al) / a0; },
      run(x) { const y = b0 * x - b0 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; } };
    f.set(hz, q); return f;
  };
  const vortex = bp(900, 0.7), vortex2 = bp(2400, 0.9), roar = [bp(260, 0.6), bp(310, 0.6)], hiss = bp(5200, 0.5), windL = lp(300), windR = lp(300),
    wallL = lp(700), wallR = lp(700), dist = lp(8000), sub = lp(60), tailBody = bp(420, 0.8);
  const gauss = (x, w) => Math.exp(-(x * x) / (w * w));
  const wrap = (x) => x - TAU * Math.round(x / TAU);

  function process(L, R) {
    const n = L.length, k = 1 - Math.exp(-n / (0.06 * sr));
    for (const key in P) C[key] += (P[key] - C[key]) * k;
    const nr = C.omega / 27.0, live = Math.min(1, nr * nr);
    const cin = C.cinematic, ins = C.inside;
    const thr = Math.min(1.6, Math.abs(C.thrust) / 16260), mach = C.tipMach;
    // level of each source (linear), before the listener path
    const aLoad = (0.30 + 0.55 * thr) * live * (0.75 + 0.6 * cin);
    const aThick = Math.pow(Math.max(mach, 0.3) / 0.75, 5) * 0.22 * live * (1 - 0.6 * ins);
    const aSlap = C.bvi * live * (0.85 + 0.45 * cin) * (1 - 0.35 * ins);
    const aVort = 0.085 * live * Math.sqrt(0.3 + thr) * (1.3 - 0.5 * cin);
    const aTail = (0.06 + 0.16 * Math.min(1.5, Math.abs(C.tailThrust) / 1100)) * live * (1 - 0.72 * ins) * (1.15 - 0.3 * cin);
    const ng = [C.ng1, C.ng2], pw = [C.pw1, C.pw2];
    const aWhine = [0, 1].map(i => Math.pow(Math.max(0, ng[i] - 0.15) / 0.85, 2.2) * 0.05 * (1 - 0.55 * ins) * (1.25 - 0.45 * cin));
    const aRoar = [0, 1].map(i => (0.02 + 0.10 * Math.sqrt(Math.max(0, pw[i]))) * Math.min(1, ng[i] * 2) * (1 - 0.5 * ins));
    const aGear = (0.012 + 0.03 * Math.min(1.3, C.torque)) * live * (0.25 + 0.75 * ins) * (1.2 - 0.4 * cin);
    const aWind = Math.pow(Math.min(1.4, C.ias / 150), 2.4) * 0.22 * (0.45 + 0.55 * ins + 0.5 * C.doorsOpen);
    const wT = 0.42 - 0.26 * Math.min(1, Math.max(0, (mach - 0.6) / 0.3));      // thickness pulse width (rad of blade passage)
    windL.set(180 + 5 * C.ias); windR.set(200 + 5 * C.ias);
    const dAtt = ins ? 1 : Math.min(1, 28 / Math.max(C.distance, 8));
    dist.set(ins > 0.5 ? 9000 : Math.max(900, 14000 / (1 + C.distance / 120)));
    wallL.set(520 + 900 * C.doorsOpen); wallR.set(560 + 900 * C.doorsOpen);
    const dM = C.omega / sr, dT = C.omega * (1190 / 258) / sr;
    for (let i = 0; i < n; i++) {
      phM += dM; if (phM > TAU) phM -= TAU;
      phT += dT; if (phT > TAU) phT -= TAU;
      const th = (phM * 4) % TAU, blade = Math.floor(phM * 4 / TAU) % 4;
      if (blade !== lastBlade) { lastBlade = blade; slapAmp[blade] = 0.75 + 0.5 * Math.abs(rnd()); }
      const x = wrap(th - Math.PI);
      // loading: a broad, asymmetric pressure swing each blade passage, plus its 'whop' second lobe
      let s = aLoad * (-x * gauss(x, 0.95) * 1.55 + 0.35 * gauss(x - 0.9, 0.6));
      s += -aThick * gauss(x, wT) * (1 - 2 * (x * x) / (wT * wT)) * 0.9;
      // slap: two sharp bipolar spikes from vortex crossings on the advancing side
      if (aSlap > 1e-4) {
        const a = slapAmp[blade] * aSlap;
        s += a * (-(x + 0.55) / 0.075 * gauss(x + 0.55, 0.075) * 1.9 + (x + 0.22) / 0.06 * gauss(x + 0.22, 0.06) * 1.2);
      }
      const nz = rnd();
      const sw = 0.55 + 0.45 * Math.cos(th - 0.6);
      const vn = (vortex.run(nz) + 0.5 * vortex2.run(nz)) * aVort * sw;
      // tail rotor: narrow pulses, four per turn, amplitude wobbling with main-rotor wake passage
      const xt = wrap((phT * 4) % TAU - Math.PI);
      let t = aTail * (-xt * gauss(xt, 0.55) * 2.2 + 0.5 * gauss(xt, 0.2)) * (0.8 + 0.2 * Math.cos(th));
      t += tailBody.run(t) * 0.6;
      // engines
      let e = 0;
      for (let j = 0; j < 2; j++) {
        const f1 = 6150 * ng[j] * (j ? 1.013 : 1), f2 = 2870 * ng[j] * (j ? 0.991 : 1);
        phE[j * 2] += TAU * f1 / sr; if (phE[j * 2] > TAU) phE[j * 2] -= TAU;
        phE[j * 2 + 1] += TAU * f2 / sr; if (phE[j * 2 + 1] > TAU) phE[j * 2 + 1] -= TAU;
        e += aWhine[j] * (Math.sin(phE[j * 2]) + 0.55 * Math.sin(phE[j * 2 + 1]));
        e += roar[j].run(rnd()) * aRoar[j] * 2.2;
      }
      e += hiss.run(nz) * 0.03 * (ng[0] + ng[1]) * (1 - 0.6 * ins);
      // transmission: planetary and bevel meshes with shaft-order sidebands
      const fG = [981 * nr, 1634 * nr, 2055 * nr];
      let g = 0;
      for (let j = 0; j < 3; j++) { phG[j] += TAU * fG[j] / sr; if (phG[j] > TAU) phG[j] -= TAU; g += Math.sin(phG[j] + 0.6 * Math.sin(phM * (j + 1))) * (j === 0 ? 1 : 0.55); }
      g *= aGear * (0.8 + 0.2 * Math.cos(phM));
      const wn = rnd(), wl = windL.run(wn) * aWind * 3.0, wr = windR.run(rnd()) * aWind * 3.0;
      // listener path
      let rotor = s + vn, mono;
      if (ins > 0.5) {
        const lowL = wallL.run(rotor + t + e), lowR = wallR.run(rotor + t + e);
        mono = g + 0.25 * (rotor + e);
        const subv = sub.run(s) * (0.3 + 0.7 * cin);
        L[i] = lowL * 1.6 + mono + subv + wl; R[i] = lowR * 1.6 + mono + subv + wr;
      } else {
        mono = dist.run(rotor + t + e + g * 0.4) * dAtt;
        const subv = sub.run(s) * (0.2 + 0.8 * cin) * dAtt;
        const pan = 0.5 + 0.35 * (C.front - 0.5);
        L[i] = (mono + subv) * (1.1 - pan * 0.4) + wl * 0.4; R[i] = (mono + subv) * (0.7 + pan * 0.4) + wr * 0.4;
      }
      const drive = C.master * (0.5 + 0.2 * cin);
      L[i] = Math.tanh(L[i] * drive) * 0.95; R[i] = Math.tanh(R[i] * drive) * 0.95;
    }
  }
  return { P, process };
}

const MODES = { cinematic: 1, realistic: 0 };

export class UH60Sound {
  constructor() { this.mode = 'cinematic'; this.listener = { view: 'cockpit', distance: 30, front: 0.5, doorsOpen: 0 }; this.node = null; this.ctx = null; this.master = 0.8; }
  async start(ctx) {
    this.ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    const src = `const coreFactory = ${coreFactory.toString()};
      registerProcessor('uh60-sound', class extends AudioWorkletProcessor {
        constructor() { super(); this.core = coreFactory(sampleRate); this.port.onmessage = (e) => Object.assign(this.core.P, e.data); }
        process(inputs, outputs) { const o = outputs[0]; this.core.process(o[0], o[1] || o[0]); return true; }
      });`;
    const url = URL.createObjectURL(new Blob([src], { type: 'application/javascript' }));
    await this.ctx.audioWorklet.addModule(url);
    this.node = new AudioWorkletNode(this.ctx, 'uh60-sound', { numberOfOutputs: 1, outputChannelCount: [2] });
    this.node.connect(this.ctx.destination);
    if (this.ctx.state === 'suspended') await this.ctx.resume();
    return this;
  }
  setMode(m) { if (m in MODES) this.mode = m; }
  setListener(l) { Object.assign(this.listener, l); }
  setVolume(v) { this.master = v; }
  // o = UH60Flight.out
  update(o) {
    if (!this.node) return;
    const l = this.listener, eng = (i) => Math.max(0, (o.torquePct[i] || 0) / 100);
    this.node.port.postMessage({
      omega: o.omega, thrust: o.thrust, tipMach: o.tipMach || 0.65, bvi: o.bvi, tailThrust: o.tailThrust, ias: o.ias,
      ng1: o.ngPct[0] / 100, ng2: o.ngPct[1] / 100, pw1: eng(0), pw2: eng(1), torque: (eng(0) + eng(1)) / 2,
      cinematic: MODES[this.mode], inside: l.view === 'outside' ? 0 : 1, cabin: l.view === 'cabin' ? 1 : 0,
      distance: l.distance, front: l.front, doorsOpen: l.doorsOpen || 0, master: this.master,
    });
  }
  stop() { if (this.node) { this.node.disconnect(); this.node = null; } }
}
