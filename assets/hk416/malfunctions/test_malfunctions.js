// node test_malfunctions.js : checks hk416-malfunctions.js against sim.py (parity.json, validation.json) and against the sourced figures.
// Run after sim.py. Takes about 20 seconds (it fires about 22 million simulated rounds).
const fs = require('fs'), path = require('path');
const M = require('./hk416-malfunctions.js');
const J = (f) => JSON.parse(fs.readFileSync(path.join(__dirname, f), 'utf8'));
const D = J('malfunctions.json'), R = J('procedures.json'), PAR = J('parity.json'), V = J('validation.json');
M.use(D, R);
const C = M.core;
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const close = (a, b, rel) => Math.abs(a - b) <= rel * Math.max(Math.abs(a), Math.abs(b), 1e-300);

// 1. margins and analytic probabilities, state by state
{
  let worst = 0, n = 0;
  for (const v of PAR.probabilities) {
    const st = C.newState(v.cfg); Object.assign(st, v.state); st.mag.rounds = v.magRounds;
    const m = C.margins(st), p = C.probabilities(st);
    for (const k of Object.keys(v.margins)) {
      if (typeof v.margins[k] === 'number') { n++; worst = Math.max(worst, Math.abs(m[k] - v.margins[k]) / Math.max(Math.abs(v.margins[k]), 1e-300)); }
      else if (m[k] !== v.margins[k]) worst = 1;
    }
    for (const k of Object.keys(v.p)) { n++; worst = Math.max(worst, Math.abs((p[k] || 0) - v.p[k]) / Math.max(Math.abs(v.p[k]), 1e-300)); }
    if (Object.keys(p).length !== Object.keys(v.p).length) worst = 1;
  }
  ok(worst < 1e-9, `margins and per-round probabilities match sim.py: ${n} numbers in ${PAR.probabilities.length} states, largest relative difference ${worst.toExponential(1)}`);
}

// 2. seeded sequences of shots and clearances, step by step
{
  let steps = 0, bad = 0, first = '';
  for (const s of PAR.sequences) {
    const rnd = M.rng(s.seed); let st = C.newState(s.cfg);
    for (let i = 0; i < s.steps; i++) {
      const want = s.log[i]; let got;
      if (st.status !== 'ok') st = C.newState(s.cfg);
      if (!C.ready(st)) { const cl = C.clear(st, rnd); got = ['clear', cl.procedures, cl.seconds, cl.end, cl.klass]; }
      else { const r = C.fire(st, rnd); C.advance(st, 1.0); got = ['fire', r.outcome, r.variant || '', r.travelMm || 0, r.delayS || 0, st.chamber, st.feedway, st.bolt, st.mag.rounds]; }
      steps++;
      const same = got.length === want.length && got.every((g, j) => typeof g === 'number' ? Math.abs(g - want[j]) < 2e-3 * Math.max(1, Math.abs(g)) && (j !== 4 || close(g, want[j], 1e-6) || Math.abs(g - want[j]) < 1e-9)
        : JSON.stringify(g) === JSON.stringify(want[j]));
      if (!same) { bad++; if (!first) first = `seed ${s.seed} step ${i}: ${JSON.stringify(got)} vs ${JSON.stringify(want)}`; }
    }
  }
  ok(bad === 0, `seeded sequences match sim.py: ${steps} steps over ${PAR.sequences.length} seeds` + (bad ? `, ${bad} differ, first ${first}` : ''));
}

// 3. whole protocol runs, stoppage by stoppage
{
  let bad = 0, tot = 0;
  for (const p of PAR.protocols) {
    const r = M.runProtocol(p.seed, p.rounds, p.cfg), w = p.result; tot += r.stoppages;
    const same = r.rounds === w.rounds && r.stoppages === w.stoppages && r.replaced === w.replaced && r.lostRounds === w.lostRounds &&
      JSON.stringify(r.at) === JSON.stringify(w.at) && JSON.stringify(Object.entries(r.counts).sort()) === JSON.stringify(Object.entries(w.counts).sort()) &&
      [1, 2, 3].every((k) => r.klass[k] === w.klass[k]);
    if (!same) bad++;
  }
  ok(bad === 0, `protocol runs match sim.py: ${PAR.protocols.length} runs, ${tot} stoppages at the same rounds with the same types and classes`);
}

// 4. the long runs: the same seeds give the same totals as Python, and the rates sit on the sourced figures
function longRun(L) {
  const cats = {}; let stoppages = 0, rounds = 0; const klass = { 1: 0, 2: 0, 3: 0 };
  for (let i = 0; i < L.rifles; i++) {
    const r = M.runProtocol(L.first_seed + i, L.rounds, L.cfg); stoppages += r.stoppages; rounds += r.rounds;
    for (const k of Object.keys(r.counts)) { const c = M.edtCategory(k); cats[c] = (cats[c] || 0) + r.counts[k]; }
    for (const k of [1, 2, 3]) klass[k] += r.klass[k];
  }
  return { cats, stoppages, rounds, klass };
}
{
  const t0 = Date.now(), L = PAR.long_runs.dust, a = longRun(L), reps = L.rifles / 10, pub = D.calibration.dust_test.hk416, tg = D.calibration.targets;
  ok(a.stoppages === L.sum_stoppages && Object.keys(L.cats).every((k) => a.cats[k] === L.cats[k]), `dust test long run equals sim.py exactly: ${a.stoppages} stoppages in ${a.rounds} rounds (${reps} repeats of 10 rifles x 6,000)`);
  const rows = ['FFD', 'FTC', 'FFR', 'FXT', 'FEJ', 'FBR'].map((c) => {
    const sim = (a.cats[c] || 0) / reps, row = V.dust_test.rows.find((r) => r.category === c);
    return { c, sim, target: tg[c], lo: row.poisson95_of_published[0], hi: row.poisson95_of_published[1] };
  });
  ok(rows.every((r) => r.sim >= r.lo && r.sim <= r.hi), 'dust test rates against the 2007 briefing (per 60,000 rounds, simulated vs published): ' + rows.map((r) => `${r.c} ${r.sim.toFixed(1)} vs ${r.target}`).join(', '));
  const tot = a.stoppages / reps;
  ok(Math.abs(tot - 217) < 0.06 * 217, `dust test total ${tot.toFixed(1)} per 60,000 rounds against 217 published (219 class 1 and 2, less 2 "other"): MRBS ${(60000 / tot).toFixed(0)} vs ${(60000 / 219).toFixed(0)}`);
  const Lc = PAR.long_runs.clean, b = longRun(Lc), mrbs = b.rounds / b.stoppages;
  ok(b.stoppages === Lc.sum_stoppages, `clean long run equals sim.py exactly: ${b.stoppages} stoppages in ${b.rounds} rounds`);
  ok(mrbs > 4000 && mrbs < 6000, `clean rifle ${mrbs.toFixed(0)} rounds between stoppages against the assumed 5,000 (Army laboratory figure for new M4s)`);
  console.log(`     (${((a.rounds + b.rounds) / 1e6).toFixed(1)} million simulated rounds in ${((Date.now() - t0) / 1000).toFixed(1)} s)`);
}

// 4b. a larger run of this module alone, on seeds sim.py never used: 150 dust tests (9 million rounds) and 6 million clean rounds
{
  const t0 = Date.now(), reps = 150, a = longRun({ first_seed: 700000, rifles: reps * 10, rounds: 6000, cfg: { dust: 1 } }), tg = D.calibration.targets;
  const rows = ['FFD', 'FTC', 'FFR', 'FXT', 'FEJ', 'FBR'].map((c) => ({ c, sim: (a.cats[c] || 0) / reps, target: tg[c], se: Math.sqrt(Math.max(1, a.cats[c] || 0)) / reps }));
  ok(rows.every((r) => Math.abs(r.sim - r.target) < 0.08 * r.target + 4 * r.se), 'dust test, 150 repeats, mean per 60,000 rounds (simulated +/- standard error vs target): ' +
    rows.map((r) => `${r.c} ${r.sim.toFixed(2)} +/- ${r.se.toFixed(2)} vs ${r.target}`).join(', '));
  const k = a.klass, tot = a.stoppages / reps;
  console.log(`     total ${tot.toFixed(1)} per 60,000 (MRBS ${(60000 / tot).toFixed(0)}; published 219, MRBS 274). Classes by clearing time, a prediction: class 1 ${(k[1] / reps).toFixed(1)}, class 2 ${(k[2] / reps).toFixed(1)}, class 3 ${(k[3] / reps).toFixed(1)} (published: 219 class 1 and 2, 14 class 3 of unstated kind; parts breakage is not modelled)`);
  const b = longRun({ first_seed: 800000, rifles: 1000, rounds: 6000, cfg: {} }), mrbs = b.rounds / b.stoppages;
  ok(Math.abs(mrbs - 5000) < 0.08 * 5000, `clean rifle, 6 million rounds: ${b.stoppages} stoppages, ${mrbs.toFixed(0)} rounds between stoppages (target 5,000; standard error ${(mrbs / Math.sqrt(b.stoppages)).toFixed(0)})`);
  const al = longRun({ first_seed: 900000, rifles: 400, rounds: 6000, cfg: { dust: 1, magType: 'gi_aluminium' } }), extra = (al.cats.FFD || 0) / 40 - rows[0].sim;
  ok(extra > 148 * 0.9 && extra < 239 * 1.1, `aluminium magazines in the dust test add ${extra.toFixed(0)} feed stoppages per 60,000 rounds (the M4's magazine stoppages: 148 and 239)`);
  console.log(`     (${((a.rounds + b.rounds + al.rounds) / 1e6).toFixed(1)} million simulated rounds in ${((Date.now() - t0) / 1000).toFixed(1)} s)`);
}

// 5. sim.py's own checks all passed, and this is not a --quick build
ok(V.failed === 0 && !V.meta.quick, `validation.json: ${V.passed} checks passed, ${V.failed} failed` + (V.meta.quick ? ' (QUICK build: rerun sim.py without --quick)' : ''));

// 6. reproducibility and the gun object
{
  const run = (seed) => { const g = M.create({ seed, dust: 1, ammo: 'degraded' }); const out = []; for (let i = 0; i < 300; i++) { const r = g.fire(); out.push(r.outcome); if (g.state.status !== 'ok') g.reset({ seed: seed + 1000 + i, dust: 1, ammo: 'degraded' }); else if (!g.ready) g.clear(); } return out.join(','); };
  ok(run(5) === run(5) && run(5) !== run(6), 'the same seed gives the same 300-shot history; another seed gives another');
}

// 7. every forced stoppage shows a pose and is cleared by the procedure its picture calls for
{
  const kinds = ['failure_to_fire:dud', 'hangfire', 'failure_to_feed:nose_jam', 'failure_to_feed:bolt_over_empty_chamber', 'failure_to_feed:failure_to_chamber', 'stovepipe:stovepipe',
    'stovepipe:case_in_receiver', 'stovepipe:rechambered_case', 'double_feed:stuck_case_plus_round', 'double_feed:two_live', 'failure_to_extract:claw_slip', 'failure_to_extract:torn_rim',
    'bolt_override', 'squib', 'failure_to_lock_back'];
  let bad = [], seen = new Set();
  for (const k of kinds) for (let seed = 1; seed <= 20; seed++) {
    const g = M.create({ seed, mode: 'range' });
    if (k.startsWith('failure_to_extract') || k === 'failure_to_lock_back') g.state.mag.rounds = 0;
    const r = g.fire({ force: k }); const base = k.split(':')[0], want = k.split(':')[1];
    if (r.outcome !== base || (want && r.variant !== want)) { bad.push(k + ' gave ' + r.outcome + ':' + r.variant); break; }
    seen.add(r.outcome);
    const p = g.pose(); if (!(p.carrierMm >= 0 && p.carrierMm <= 95.01)) bad.push(k + ' pose');
    if (k === 'stovepipe:stovepipe' && !(p.carrierMm === 27.5 && p.props.length === 1 && g.stopTime() > D.action.t_max_travel_s && g.stopTime() < D.action.t_in_battery_s)) bad.push(k + ' stop');
    const cl = g.clear(); if (!(cl.end === 'ready' || (k === 'squib' && cl.end === 'needs_inspection'))) bad.push(k + ' ended ' + cl.end);
  }
  ok(bad.length === 0 && ['failure_to_fire', 'hangfire', 'failure_to_feed', 'stovepipe', 'double_feed', 'failure_to_extract', 'bolt_override', 'squib'].every((k) => seen.has(k)),
    `the eight stoppages of the brief (${kinds.length} variants x 20 seeds) can each be produced, posed and cleared` + (bad.length ? ': ' + bad.slice(0, 3).join('; ') : ''));
  // the safety lessons the state machine carries
  let g = M.create({ seed: 3 }); g.fire({ force: 'squib' }); g.act('tap'); g.act('rack'); const r2 = g.fire();
  ok(r2.outcome === 'fired_into_obstruction' && g.state.status === 'out_of_service', 'tap, rack and fire after a squib is reported as a round fired into a blocked bore, and the rifle is out of service');
  g = M.create({ seed: 3 }); g.fire({ force: 'double_feed:stuck_case_plus_round' }); const a = g.act('rack');
  ok(a.events.includes('rounds_pinned_magazine_must_come_out') && !g.ready, 'racking a double feed with the magazine in clears nothing');
  g = M.create({ seed: 3 }); g.fire({ force: 'failure_to_fire' }); const s = g.act('safe');
  ok(!s.ok && g.state.selector === 'fire', 'the selector will not go to safe with the hammer down (manual p. 3)');
}

// 8. the carrier curve this module carries is the action simulation's
{
  const A = J('../action/action.json'), c = A.cycle; let worst = 0;
  const r = { travelMm: D.action.x_full_mm };
  for (let i = 0; i < c.carrier_mm.length; i++) worst = Math.max(worst, Math.abs(C.carrierAt(r, i * c.dt, 0) - c.carrier_mm[i]));
  ok(worst < 0.6, `carrierAt() follows action.json's carrier curve within ${worst.toFixed(2)} mm over the whole cycle`);
  ok(D.action.x_full_mm === A.mechanics.full_stroke_mm && D.action.x_hold_mm === A.mechanics.hold_open_mm && D.action.x_eject_mm === A.mechanics.eject_carrier_mm && D.action.x_pick_mm === A.mechanics.feed_pick_carrier_mm &&
    Math.abs(D.params.hammer_energy.value - A.validation.hammer_energy.sim) < 1e-4, 'stroke, hold-open, eject and pick-up positions and the hammer energy are those of action.json (rerun sim.py if the action changes)');
}

// 9. motions resolve against the model's node names
{
  const mo = M.motion('rack_full', { x0: 27.5, x1: 0 }), s0 = M.sampleMotion(mo, 0), s1 = M.sampleMotion(mo, 8 / 24);
  ok(s0['bolt_carrier.loc.L'] === -27.5 && s1['bolt_carrier.loc.L'] === -95 && s1['charging_handle.loc.L'] === -95, 'rack_full starts from the stoppage position and draws the carrier to 95 mm');
}
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
