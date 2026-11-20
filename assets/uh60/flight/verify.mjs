// Flight-model check against TM 1-1520-237-10 worked examples. Run: node flight/verify.mjs  (writes flight/flight.json)
import { UH60Flight } from './uh60-flight.js';
import { writeFileSync } from 'node:fs';
const KT = 1.68781, D = 180 / Math.PI;
function steady(w, alt, oat, kt, hgt) {     // hold height and speed for 50 s, read torque
  const f = new UH60Flight({ params: { weight: w, shpEngine: 2500 }, dT: oat });   // engines un-limited so the rotor sets torque
  f.groundAlt = alt; f.pos = [0, 0, -hgt]; f.vel = [kt * KT, 0, 0];
  const c = { collective: 0.6, lon: 0, lat: 0, pedal: 0, fps: true }; let iz = 0, li = 0;
  for (let t = 0; t < 50; t += 1 / 60) {
    const o = f.out, z = hgt + f.pos[2]; iz += z * 0.01 / 60;
    c.collective = Math.min(1, Math.max(0, 0.6 + iz + 0.02 * z - 0.0004 * o.vs));
    const se = kt - o.u; li += se * 0.004 / 60; c.lon = Math.max(-1, Math.min(1, 0.02 * se + li)); f.step(1 / 60, c);
  }
  return f.out;
}
const cases = [
  ['hover OGE, 19,500 lb, 2000 ft PA, 30 C', 19500, 2000, 18.96, 0, 3000, 94, 4],
  ['hover 10-ft wheel height, same day', 19500, 2000, 18.96, 0, 15.36, 80, 7],
  ['cruise 135 KTAS, 17,000 lb, 6000 ft, 30 C', 17000, 6000, 26.9, 135, 3000, 62, 4],
  ['cruise 82 KTAS (max endurance), same', 17000, 6000, 26.9, 82, 3000, 41, 4],
];
const res = { source: 'TM 1-1520-237-10 chapter 7 worked examples (UH-60A, T700-GE-700)', torque: [], pass: true };
for (const [name, w, alt, oat, kt, hgt, tm, tol] of cases) {
  const o = steady(w, alt, oat, kt, hgt), trq = +o.torquePct[0].toFixed(1), ok = Math.abs(trq - tm) <= tol;
  res.torque.push({ name, manual_pct: tm, model_pct: trq, tolerance: tol, pitch_deg: +(o.pitch * D).toFixed(1), roll_deg: +(o.roll * D).toFixed(1), ok });
  res.pass &&= ok; console.log(ok ? 'ok  ' : 'FAIL', name, 'manual', tm, 'model', trq);
}
{ // takeoff: raise collective, expect lift-off with heading held and rotor speed governed
  const f = new UH60Flight({}), c = { collective: 0, lon: 0, lat: 0, pedal: 0, fps: true };
  for (let t = 0; t < 25; t += 1 / 60) { c.collective = Math.min(0.62, t * 0.08); f.step(1 / 60, c); }
  const o = f.out, ok = o.agl > 5 && Math.abs(o.rotorPct - 100) < 3 && Math.abs(Math.sin(o.heading)) < 0.1 && !o.crashed;
  res.takeoff = { agl_ft: +o.agl.toFixed(1), rotor_pct: +o.rotorPct.toFixed(1), heading_deg: +(o.heading * D).toFixed(1), torque_pct: +o.torquePct[0].toFixed(0), ok };
  res.pass &&= ok; console.log(ok ? 'ok  ' : 'FAIL', 'takeoff', JSON.stringify(res.takeoff));
}
{ // both engines cut at 80 kt: rotor keeps turning (95-110 %), descent 1,700-2,800 ft/min (TM autorotation chart region)
  const f = new UH60Flight({}); f.pos = [0, 0, -6000]; f.vel = [80 * KT, 0, 0];
  const c = { collective: 0.5, lon: 0.05, lat: 0, pedal: 0, fps: true }; let li = 0;
  for (let t = 0; t < 45; t += 1 / 60) {
    if (t > 5) { f.eng.forEach(e => e.on = false); c.collective = 0; }
    const se = 80 - f.out.ias; li += se * 0.004 / 60; c.lon = Math.max(-1, Math.min(1, 0.02 * se + li)); f.step(1 / 60, c);
  }
  const o = f.out, ok = o.rotorPct > 95 && o.rotorPct < 110 && -o.vs > 1700 && -o.vs < 2800;
  res.autorotation = { ias_kt: +o.ias.toFixed(0), descent_fpm: +(-o.vs).toFixed(0), rotor_pct: +o.rotorPct.toFixed(1), ok };
  res.pass &&= ok; console.log(ok ? 'ok  ' : 'FAIL', 'autorotation', JSON.stringify(res.autorotation));
}
writeFileSync(new URL('./flight.json', import.meta.url), JSON.stringify(res, null, 1));
process.exit(res.pass ? 0 : 1);
