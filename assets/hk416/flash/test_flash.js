// node test_flash.js : checks hk416-flash.js against numbers sim.py computed straight from the physics (flash.json "parity")
const fs = require('fs'), path = require('path');
const F = require('./hk416-flash.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'flash.json'), 'utf8'));
const action = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'action', 'action.json'), 'utf8'));
F.use(data);
const out = { test: 'hk416-flash.js against physics.py (via flash.json parity) and action.json', checks: [] };
let bad = 0;
function check(what, got, want, tol, abs) {
  const err = Math.abs(got - want), lim = tol * Math.abs(want) + (abs || 0), ok = err <= lim;
  out.checks.push({ what, js: got, python: want, rel_error: want ? err / Math.abs(want) : err, tolerance: tol, pass: ok });
  if (!ok) { bad++; console.log('MISMATCH', what, got, want); }
}
const P = data.parity, peak = data.light.peak_cd;
// 1. the clock: ignition and bullet exit are action/'s
check('ignition after sear (s)', F.ignitionAfterSear, action.events.times.ignition, 1e-12);
check('bullet exit after sear (s)', F.ignitionAfterSear + F.bulletExit, action.events.times.bullet_exit, 2e-3);
// 2. nothing before the bullet leaves
check('light before exit (cd)', F.sample(F.bulletExit - 1e-5).light.intensity, 0, 0, 1e-12);
// 3. the luminous energy a frame collects
for (const w of P.frame_mean_intensity) check(`frame mean intensity ${(w.t0 * 1e3).toFixed(3)}..${(w.t1 * 1e3).toFixed(3)} ms (cd)`, F.frame(w.t0, w.t1).light.intensity, w.cd, 0.02, 1e-9);
// 4. the instantaneous light between table points (tolerance: 3 % of the value plus 1 % of the peak, the table's interpolation error)
for (const q of P.light_instant) check(`light at ${(q.t * 1e3).toFixed(4)} ms (cd)`, F.sample(q.t).light.intensity, q.cd, 0.03, 0.01 * peak);
// 5. the secondary flash pulse
for (const q of P.secondary_instant) {
  const c = F.sample(q.t, { secondary: q.share }).cards.find((x) => x.id === 'secondary');
  check(`secondary at ${(q.t * 1e3).toFixed(2)} ms, share ${q.share} (cd)`, c ? c.intensity : 0, q.cd, 0.03);
}
// 6. smoke: the same entraining-puff sums as physics.puff_track, with wind
const puffs = F.smoke(P.smoke.t, P.smoke.wind, { frame: 'muzzle' });
for (const p of P.smoke.puffs) {
  const q = puffs.find((x) => x.source === p.name);      // the head puff of each source comes first
  check('smoke radius ' + p.name + ' (m)', q.radius, p.radius_m, 1e-7);
  for (let k = 0; k < 3; k++) check('smoke ' + 'xyz'[k] + ' ' + p.name + ' (m)', q.position[k], p.pos_m[k], 1e-7, 1e-9);
}
// 7. the frame: gun-frame positions are the muzzle-frame ones moved to socket_muzzle
{ const a = F.sample(F.bulletExit + 2.3e-4), b = F.sample(F.bulletExit + 2.3e-4, { frame: 'muzzle' });
  check('gun frame offset (m)', a.light.position[2] - b.light.position[2], action.meta.nodes.present.socket_muzzle[2], 1e-12); }
// 8. the cards of the side-on view add up to the light
{ const a = F.sample(F.bulletExit + data.light.peak_t_ms / 1e3); const sum = a.cards.filter((c) => c.kind === 'plume').reduce((s, c) => s + c.intensity, 0);
  check('plume cards against the light at the peak (cd)', sum, a.light.intensity, 0.05); }
out.passed = out.checks.filter((c) => c.pass).length; out.failed = bad;
out.worst_rel_error = Math.max(...out.checks.filter((c) => Math.abs(c.python) > 1e-3 * peak || !/cd/.test(c.what)).map((c) => c.rel_error));   // light values under 0.1 % of the peak are judged by the absolute tolerance only
fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify(out, null, 1) + '\n');
const f = F.frame(0, 1 / 60);
console.log('frame60:', f.cards.length, 'cards, light', f.light.intensity.toPrecision(3), 'cd,', Math.round(f.light.colorK), 'K');
console.log(`${out.passed} passed, ${bad} failed; worst relative error ${out.worst_rel_error.toExponential(2)}`);
console.log(bad ? 'FAILED' : 'OK');
process.exit(bad ? 1 : 0);
