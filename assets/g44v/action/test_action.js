// node test_action.js : checks g44v-action.js against action.json (run after sim.py). Writes parity.json.
const A = require('./g44v-action.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'action.json'), 'utf8')); A.use(d);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const m = d.mechanics, sv = d.loads.cci_standard_velocity, e = sv.events;
let s = A.sample(0); ok(s.slideMm === 0 && Math.abs(s.strikerMm - m.striker_break_mm) < 1e-9 && s.recoil.pos[2] === 0, 'rest at t = 0, firing pin at the break position');
s = A.sample(e.striker_hits + 1e-5); ok(s.strikerMm < 0.05, 'firing pin forward at the lock time: ' + s.strikerMm.toFixed(3) + ' mm');
s = A.sample(e.max_travel); ok(Math.abs(s.slideMm - m.full_travel_mm) < 0.5, 'full travel ' + s.slideMm.toFixed(2) + ' mm');
s = A.sample(e.in_battery + 0.02); ok(Math.abs(s.slideMm) < 1e-6 && Math.abs(s.strikerMm - m.striker_break_mm) < 1e-6, 'back in battery, firing pin held at the break position (trigger still back)');
s = A.sample(0.1, { lastRound: true }); ok(s.slideHeldOpen && s.slideMm === m.lock_open_mm, 'last round locks the slide open at ' + s.slideMm + ' mm');
s = A.sample(0.1, { ammo: 'cci_quiet_22', lastRound: true }); ok(!s.slideHeldOpen, 'CCI Quiet-22 does not lock the slide open (' + d.loads.cci_quiet_22.max_travel_mm + ' mm of travel)');
let pk = 0; for (let t = 0; t < 0.004; t += 2e-6) pk = Math.max(pk, A.sample(t, { ammo: 'cci_mini_mag' }).chamberPressureMPa);
ok(Math.abs(pk - d.loads.cci_mini_mag.pistol.p_max_MPa) < 2 && pk <= d.params.p_map.value / 1e6 * 1.01, 'Mini-Mag peak pressure ' + pk.toFixed(1) + ' MPa, at or under the SAAMI limit');
// parity with sim.py's own sample()
let worst = 0;
for (const q of d.parity.samples) {
  const r = A.sample(q.t, { ammo: q.ammo, stance: q.stance, lastRound: q.lastRound });
  worst = Math.max(worst, Math.abs(r.slideMm - q.slideMm), Math.abs(r.slideVel - q.slideVel), Math.abs(r.recoil.pos[2] * 1e3 - q.z), Math.abs(r.recoil.pitchDeg - q.pitch), r.slideHeldOpen === q.held ? 0 : 1);
}
ok(worst < 1e-9, d.parity.samples.length + ' random samples match sim.py: worst difference ' + worst.toExponential(2));
// burst by superposition: two shots 0.25 s apart equal the sum of two single responses
const r2 = A.recoil(0.3, [0, 0.25], 'two_hand'), ra = A.recoil(0.3, [0], 'two_hand'), rb = A.recoil(0.05, [0], 'two_hand');
ok(Math.abs(r2.pos[2] - ra.pos[2] - rb.pos[2]) < 1e-12, 'recoil of two shots is the sum of the single-shot responses');
// brass: reproduce the seeded trajectories of sim.py
let wb = 0;
for (const tr of d.brass.trajectories) {
  const r = A.rng(tr.seed), c = A.ejectCase(r);
  for (let i = 0; i < 240 * 4 && c.resting !== 2; i++) A.stepCase(c, d.brass.scatter.step_dt, { groundY: tr.ground_y });
  wb = Math.max(wb, Math.hypot(c.pos[0] - tr.rest[0], c.pos[1] - tr.rest[1], c.pos[2] - tr.rest[2]));
}
ok(wb < 1e-4, 'seeded brass rest positions match sim.py within ' + (wb * 1e3).toFixed(4) + ' mm');
const c0 = A.ejectCase(A.rng(7)); ok(c0.vel[0] < 0 && c0.vel[1] > 0, 'case leaves to the right (-X) and upward: v = ' + c0.vel.map(v => v.toFixed(2)));
fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify({ note: 'node test_action.js: g44v-action.js against sim.py', samples: d.parity.samples.length, worst_sample_difference: worst, worst_brass_rest_m: wb, failed: fail }, null, 1));
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
