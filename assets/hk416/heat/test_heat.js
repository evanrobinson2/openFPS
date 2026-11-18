// node test_heat.js : checks hk416-heat.js against the Python runs stored in heat.json (run after sim.py).
// Writes parity.json (the committed result of the JS-vs-Python parity test).
const H = require('./hk416-heat.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'heat.json'), 'utf8')); H.use(d);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const out = { note: 'hk416-heat.js against sim.py on the runtime grid: largest absolute difference over all samples', cases: {} };

// 1. parity: replay each reference case with the same grid, step and shot times, compare every probe and effect
for (const [name, ref] of Object.entries(d.runtime.reference)) {
  const t0 = Date.now();
  const run = H.simulate(ref.shot_times_s, ref.t_end, ref.sample_times_s, { ambientC: ref.ambient_C, wind: ref.wind_m_s, dt: ref.dt });
  const ms = Date.now() - t0;
  let worstT = 0, worstTk = '', worstRel = 0, worstRelK = '';
  const tempKey = k => !/^(q_line|cookoff_damage|mv_delta|poi_bow|barrel_max_z)/.test(k);
  for (const [k, arr] of Object.entries(ref.probes)) {
    for (let i = 0; i < arr.length; i++) {
      const a = run.rows[i][k], b = arr[i];
      if (tempKey(k)) { const e = Math.abs(a - b); if (e > worstT) { worstT = e; worstTk = k; } }
      else if (k !== 'barrel_max_z_mm') { const e = Math.abs(a - b) / Math.max(Math.abs(b), 1e-6); if (e > worstRel) { worstRel = e; worstRelK = k; } }
    }
  }
  let worstEff = 0, worstEffK = '';
  for (const [k, arr] of Object.entries(ref.effects)) {
    for (let i = 0; i < arr.length; i++) {
      let a = run.effects[i][k], b = arr[i];
      if (b === null) { if (isFinite(a)) { worstEff = 1; worstEffK = k + ' (finite vs inf)'; } continue; }
      const e = Math.abs(a - b) / Math.max(Math.abs(b), 1e-9); if (e > worstEff) { worstEff = e; worstEffK = k; }
    }
  }
  let worstF = 0; const p = run.gun.profile();
  for (let i = 0; i < p.outerC.length; i++) worstF = Math.max(worstF, Math.abs(p.outerC[i] - ref.final_outer_C[i]), Math.abs(p.boreC[i] - ref.final_bore_C[i]));
  for (let i = 0; i < p.handguardC.length; i++) worstF = Math.max(worstF, Math.abs(p.handguardC[i] - ref.final_handguard_C[i]));
  const en = run.gun.energy(), eRel = Math.max(Math.abs(en.depositedJ - ref.energy_J.deposited) / ref.energy_J.deposited, Math.abs(en.lostJ - ref.energy_J.lost) / ref.energy_J.lost);
  ok(run.rows.length === ref.sample_times_s.length, name + ': ' + run.rows.length + ' samples');
  ok(worstT < 1e-3, name + ': temperatures within ' + worstT.toExponential(2) + ' K of sim.py (worst: ' + worstTk + ')');
  ok(worstRel < 1e-5, name + ': other probes within ' + worstRel.toExponential(2) + ' relative (worst: ' + worstRelK + ')');
  ok(worstEff < 1e-5, name + ': effects within ' + worstEff.toExponential(2) + ' relative (worst: ' + worstEffK + ')');
  ok(worstF < 1e-3, name + ': final temperature fields within ' + worstF.toExponential(2) + ' K');
  ok(eRel < 1e-7, name + ': energy in and out within ' + eRel.toExponential(2) + ' relative');
  const peak = k => Math.max(...ref.probes[k]);
  out.cases[name] = { samples: run.rows.length, shots: ref.shot_times_s.length, sim_seconds: ref.t_end, wall_ms: ms, max_temperature_difference_K: worstT, worst_temperature_probe: worstTk,
    max_relative_difference_other_probes: worstRel, max_relative_difference_effects: worstEff, max_field_difference_K: worstF, energy_relative_difference: eRel,
    python_peaks_C: { chamber_wall: peak('chamber_wall'), barrel_max_outer: peak('barrel_max_outer'), handguard_hand: peak('handguard_hand') } };
}

// 2. energy conservation in the JS model itself
{
  const g = H.create(); for (let i = 0; i < 60; i++) { g.fire(); g.advance(0.5); } g.advance(120);
  const R = d.runtime, K0 = R.K0;
  // stored energy is not exposed; check instead that deposited > lost > 0 and temperatures are above ambient and finite
  const s = g.state(); const e = g.energy();
  ok(e.depositedJ > e.lostJ && e.lostJ > 0 && isFinite(s.barrelMaxC) && s.barrelMaxC > 25, 'live API: 60 rounds at 120 rpm then 2 min: barrel max ' + s.barrelMaxC.toFixed(1) + ' C, hand ' + s.handguardHandC.toFixed(1) + ' C, deposited ' + e.depositedJ.toFixed(0) + ' J, lost ' + e.lostJ.toFixed(0) + ' J');
  ok(Math.abs(g.outerAt(R.z_mm[5]) - g.profile().outerC[5]) < 1e-9, 'outerAt() agrees with profile() at a station');
  ok(s.comfort.level >= 0 && s.comfort.level <= 5 && typeof s.comfort.name === 'string' && s.mirage.strength >= 0 && s.mirage.strength <= 1, 'state(): comfort "' + s.comfort.name + '", mirage strength ' + s.mirage.strength.toFixed(3));
}
// 3. cool-down returns to ambient
{
  const g = H.create({ ambientC: 10 }); for (let i = 0; i < 30; i++) g.fire(); for (let i = 0; i < 6 * 3600 / 2; i++) g.advance(2);
  const s = g.state({ cookoffTime: false });
  ok(Math.abs(s.barrelMaxC - 10) < 0.5 && Math.abs(s.handguardMaxC - 10) < 0.5, 'after 6 h everything is back at ambient: barrel ' + s.barrelMaxC.toFixed(2) + ' C');
}
// 4. effect tables
ok(H.cookoffTime(150) === Infinity && H.cookoffTime(220) < 30 && H.cookoffTime(300) < H.cookoffTime(220), 'cook-off: none at 150 C, ' + H.cookoffTime(220).toFixed(1) + ' s at 220 C, ' + H.cookoffTime(300).toFixed(1) + ' s at 300 C');
for (const row of d.effects.cookoff.table) {
  const a = H.cookoffTime(row.chamber_C), b = row.time_to_cookoff_s;
  if (b === null ? isFinite(a) : Math.abs(a - b) > 0.06) { ok(false, 'cook-off table at ' + row.chamber_C + ' C: ' + a + ' vs ' + b); }
}
ok(H.comfort(40).level === 0 && H.comfort(50).level === 2 && H.comfort(80).level === 5, 'comfort levels at 40, 50, 80 C: ' + [40, 50, 80].map(t => H.comfort(t).name).join(', '));
ok(H.glow(300).cdM2 === 0 && H.glow(800).cdM2 > H.glow(600).cdM2, 'glow rises with temperature: ' + H.glow(600).cdM2.toPrecision(3) + ' cd/m2 at 600 C, ' + H.glow(800).cdM2.toPrecision(3) + ' at 800 C');
// 5. speed
{
  const g = H.create(); const t0 = process.hrtime.bigint(); const N = 20000; for (let i = 0; i < N; i++) g.step(d.runtime.dt);
  const us = Number(process.hrtime.bigint() - t0) / 1e3 / N; out.step_microseconds = +us.toFixed(2);
  ok(us < 200, 'one model step takes ' + us.toFixed(1) + ' us (the model steps ' + (1 / d.runtime.dt).toFixed(0) + ' times per simulated second)');
}
out.passed = fail === 0;
fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify(out, null, 1) + '\n');
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
