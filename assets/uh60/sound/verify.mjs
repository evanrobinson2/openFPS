// Sound check: render the synthesiser offline from fixed flight states and measure its spectrum.
// Expected physics: main-rotor blade passage 4 x 258 rpm = 17.2 Hz, tail rotor 4 x 1190 rpm = 79.3 Hz.
// Run: node sound/verify.mjs   (writes sound/sound.json)
import { coreFactory } from './uh60-sound.js';
import { writeFileSync } from 'node:fs';
const sr = 48000, N = sr * 6;
function render(set) {
  const c = coreFactory(sr); Object.assign(c.P, set); const L = new Float32Array(N), R = new Float32Array(N);
  for (let i = 0; i < N; i += 128) c.process(L.subarray(i, i + 128), R.subarray(i, i + 128));
  return L.subarray(sr);            // drop the first second (parameter smoothing)
}
const goertzel = (x, f) => { const w = 2 * Math.PI * f / sr, k = 2 * Math.cos(w); let a = 0, b = 0; for (let i = 0; i < x.length; i++) { const s = x[i] + k * a - b; b = a; a = s; } return Math.sqrt(a * a + b * b - k * a * b) / x.length * 2; };
const peak = (x, lo, hi, st) => { let bf = 0, bv = 0; for (let f = lo; f <= hi; f += st) { const v = goertzel(x, f); if (v > bv) { bv = v; bf = f; } } return [bf, bv]; };
const rms = (x) => Math.sqrt(x.reduce((s, v) => s + v * v, 0) / x.length);
const pk = (x) => x.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
const hover = { omega: 27.02, thrust: 16500, tipMach: 0.65, bvi: 0, tailThrust: 1100, ng1: 0.92, ng2: 0.92, pw1: 0.7, pw2: 0.7, torque: 0.7, ias: 0 };
const res = { pass: true, checks: [] };
const chk = (name, value, ok) => { res.checks.push({ name, value, ok }); res.pass &&= ok; console.log(ok ? 'ok  ' : 'FAIL', name, value); };
for (const cinematic of [1, 0]) {
  const tag = cinematic ? 'cinematic' : 'realistic';
  const out = render({ ...hover, cinematic, inside: 0, distance: 30 });
  const [f1] = peak(out, 12, 24, 0.05); chk(`${tag}: main blade-passage fundamental Hz (expect 17.2)`, +f1.toFixed(2), Math.abs(f1 - 17.2) < 0.15);
  const [f2] = peak(out, 70, 90, 0.05); chk(`${tag}: tail-rotor blade-passage Hz (expect 79.3; 5th main harmonic is 86.0)`, +f2.toFixed(2), Math.abs(f2 - 79.3) < 0.3 || Math.abs(f2 - 86.0) < 0.3);
  chk(`${tag}: peak below clipping`, +pk(out).toFixed(3), pk(out) <= 1.0);
  chk(`${tag}: audible level (rms)`, +rms(out).toFixed(3), rms(out) > 0.03);
  const slap = render({ ...hover, cinematic, inside: 0, bvi: 0.9, ias: 70 });
  const band = (x) => { const a1 = 1 - Math.exp(-2 * Math.PI * 1500 / sr), a2 = 1 - Math.exp(-2 * Math.PI * 300 / sr); let y1 = 0, y2 = 0, e = 0; for (let i = 0; i < x.length; i++) { y1 += a1 * (x[i] - y1); y2 += a2 * (y1 - y2); e += (y1 - y2) ** 2; } return Math.sqrt(e / x.length); };
  chk(`${tag}: slap raises the 300-1500 Hz band (ratio)`, +(band(slap) / band(out)).toFixed(2), band(slap) / band(out) > 1.3);
  const idle = render({ ...hover, cinematic, inside: 0, ng1: 0.65, ng2: 0.65 });
  const [w1] = peak(out, 5500, 5900, 1), [w2] = peak(idle, 3800, 4200, 1);
  chk(`${tag}: turbine whine follows Ng (Hz at 92 % / 65 %)`, [w1, w2], [1, 1.013].some(d => Math.abs(w1 - 6150 * 0.92 * d) < 12) && [1, 1.013].some(d => Math.abs(w2 - 6150 * 0.65 * d) < 12));
  const stopped = render({ ...hover, cinematic, omega: 0, ng1: 0, ng2: 0, pw1: 0, pw2: 0, torque: 0, thrust: 0, tailThrust: 0 });
  chk(`${tag}: silent when shut down (rms)`, +rms(stopped).toFixed(4), rms(stopped) < 0.003);
}
const cin = render({ ...hover, cinematic: 1, inside: 0 }), real = render({ ...hover, cinematic: 0, inside: 0 });
const lowShare = (x) => { let lo = 0; for (let f = 17.2; f < 120; f += 17.2) lo += goertzel(x, f) ** 2; return Math.sqrt(lo) / rms(x); };
chk('cinematic carries more low-frequency thump than realistic (ratio)', +(lowShare(cin) / lowShare(real)).toFixed(2), lowShare(cin) > lowShare(real));
writeFileSync(new URL('./sound.json', import.meta.url), JSON.stringify(res, null, 1));
process.exit(res.pass ? 0 : 1);
