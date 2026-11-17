// node test_action.js : checks hk416-action.js against action.json (run after sim.py)
const A = require('./hk416-action.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'action.json'), 'utf8')); A.use(d);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const e = d.events.times;
let s = A.sample(0); ok(s.carrierZ === 0 && s.hammerDeg === 0 && s.recoil.pos[2] === 0, 'rest at t = 0');
s = A.sample(e.hammer_strike); ok(Math.abs(s.hammerDeg - d.params.hammer_fall.value) < 1.0, 'hammer at the firing pin at hammer_strike: ' + s.hammerDeg.toFixed(2) + ' deg');
s = A.sample(e.indent_done || e.ignition); ok(s.firingPinMm > d.params.fp_float.value * 1e3, 'firing pin past primer contact at ignition: ' + s.firingPinMm.toFixed(3) + ' mm');
s = A.sample(e.peak_pressure); ok(Math.abs(s.chamberPressureMPa - 358.5) < 3, 'peak chamber pressure ' + s.chamberPressureMPa.toFixed(1) + ' MPa');
s = A.sample(e.unlock + 2.5e-4); ok(s.boltDeg > 22.0, 'bolt unlocked after unlock: ' + s.boltDeg.toFixed(2));
s = A.sample(e.max_travel); ok(Math.abs(s.carrierMm - d.mechanics.full_stroke_mm) < 0.5, 'full stroke ' + s.carrierMm.toFixed(2) + ' mm');
s = A.sample(e.in_battery + 0.02); ok(Math.abs(s.carrierMm) < 0.05 && s.boltDeg === 0 && Math.abs(s.hammerDeg) < 0.05, 'back in battery, hammer on the sear');
s = A.sample(0.2, { lastRound: true }); ok(s.boltHeldOpen && s.carrierMm === d.mechanics.hold_open_mm, 'last round holds the bolt open at ' + s.carrierMm + ' mm');
// auto: carrier continuity across the period, burst by superposition against the coupled 10-round run
let worst = 0; for (let k = 1; k < 5; k++) { const a = A.sample(k * A.period - 1e-6, { mode: 'auto' }), b = A.sample(k * A.period + 1e-6, { mode: 'auto' }); worst = Math.max(worst, Math.abs(a.carrierMm - b.carrierMm)); }
ok(worst < 2.0, 'auto carrier jump at the period boundary ' + worst.toFixed(2) + ' mm');
for (const st of ['ads', 'hip']) {
  const ref = d.recoil.auto[st]; let ez = 0, ep = 0, pz = 0, pp = 0;
  for (let i = 0; i < ref.z_mm.length; i++) { const r = A.recoil(i * d.recoil.dt, ref.shot_times, st); ez = Math.max(ez, Math.abs(r.pos[2] * 1e3 - ref.z_mm[i])); ep = Math.max(ep, Math.abs(r.pitchDeg - ref.pitch_up_deg[i])); pz = Math.max(pz, Math.abs(ref.z_mm[i])); pp = Math.max(pp, Math.abs(ref.pitch_up_deg[i])); }
  ok(ez < 0.1 * pz && ep < 0.1 * pp, st + ' burst by superposition: z error ' + ez.toFixed(2) + ' of ' + pz.toFixed(1) + ' mm, pitch error ' + ep.toFixed(3) + ' of ' + pp.toFixed(2) + ' deg');
}
// brass: reproduce the seeded trajectories of sim.py
let wb = 0;
for (const tr of d.brass.trajectories) {
  const r = A.rng(tr.seed), c = A.ejectCase(r); const env = { groundY: tr.ground_y, surface: tr.surface, rng: r };
  for (let i = 0; i < 3 * 240 + 1 && c.resting !== 2; i++) A.stepCase(c, d.brass.step_dt, env);
  wb = Math.max(wb, Math.hypot(c.pos[0] - tr.rest[0], c.pos[1] - tr.rest[1], c.pos[2] - tr.rest[2]));
}
ok(wb < 0.005, 'seeded brass rest positions match sim.py within ' + (wb * 1e3).toFixed(3) + ' mm');
const c0 = A.ejectCase(A.rng(7)); ok(c0.vel[0] < 0 && c0.angVel[1] < 0, 'case leaves to the right (-X), spinning mouth-outwards: v = ' + c0.vel.map(v => v.toFixed(2)));
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
