// node test.js : checks suppressor-qd-556.js against sim/core.py (through suppressor.json) and against the HK416 modules.
// Run after sim.py. Writes parity.json.
const fs = require('fs'), path = require('path');
const S = require('./suppressor-qd-556.js');
const HK = path.join(__dirname, '..', '..', 'hk416');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'suppressor.json'), 'utf8')); S.use(d);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };

// deep numeric comparison: the largest relative difference, and where
function cmp(a, b, where, st) {
  if (typeof a === 'number' && typeof b === 'number') {
    const e = Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b), 1e-300); st.n++;
    if (Math.abs(a - b) > 1e-300 && e > st.max) { st.max = e; st.at = where; }
  } else if (Array.isArray(a) || ArrayBuffer.isView(a)) {
    if (a.length !== b.length) { st.shape.push(where); return; }
    for (let i = 0; i < a.length; i++) cmp(a[i], b[i], where + '[' + i + ']', st);
  } else if (a && typeof a === 'object') {
    for (const k of Object.keys(a)) { if (!(k in b)) { st.shape.push(where + '.' + k); continue; } cmp(a[k], b[k], where + '.' + k, st); }
  } else if (a !== b) st.shape.push(where + ' (' + a + ' vs ' + b + ')');
  return st;
}
const fresh = () => ({ max: 0, at: '', n: 0, shape: [] });
const TOL = 1e-9, report = { tolerance: TOL, cases: {} };

(async () => {
  // ---- 1. the gas model, three states
  const shots = {};
  for (const nm of ['bare', 'first_round', 'subsequent']) {
    const ref = d.parity[nm], t0 = Date.now();
    const s = S.runShot(Object.assign({}, ref.opt, { breech: ref.breech })); const ms = Date.now() - t0; shots[nm] = s;
    const out = Object.assign({}, s); delete out.rec;
    out.rec_samples = {}; for (const k of Object.keys(ref.out.rec_samples)) out.rec_samples[k] = s.rec[k].filter((_, i) => i % 400 === 0);
    const st = cmp(ref.out, out, nm, fresh()); const sa = cmp(ref.acoustics, S.acoustics(s), nm + '.acoustics', fresh());
    report.cases['run_shot_' + nm] = { numbers: st.n, max_rel_diff: st.max, at: st.at, js_ms: ms };
    report.cases['acoustics_' + nm] = { numbers: sa.n, max_rel_diff: sa.max, at: sa.at };
    ok(st.shape.length === 0 && st.max < TOL, `run_shot ${nm}: ${st.n} numbers, largest relative difference ${st.max.toExponential(2)} (${st.at || 'none'}), ${ms} ms in JS`);
    ok(sa.shape.length === 0 && sa.max < TOL, `acoustics ${nm}: ${sa.n} numbers, largest relative difference ${sa.max.toExponential(2)}`);
    if (st.shape.length) console.log('   shape:', st.shape.slice(0, 5));
  }
  // ---- 2. the sound patch, flash input, heat string
  const hkp = JSON.parse(fs.readFileSync(path.join(HK, 'sound', 'params.json'), 'utf8'));
  const pat = S.soundOverlay(hkp, S.acoustics(shots.subsequent), S.acoustics(shots.bare), d.config.mech);
  const got = { persp: {}, cycle: pat.cycle, cycle_s: pat.cycle_s, auto1s: pat.variants.auto1s.times };
  for (const nm of ['shooter', 'bystander', 'downrange']) got.persp[nm] = { blast: pat.persp[nm].blast, sec: pat.persp[nm].sec, jet: pat.persp[nm].jet };
  const ref = Object.assign({}, d.parity.sound_overlay); delete ref.note;
  let st = cmp(ref, got, 'sound_overlay', fresh()); report.cases.sound_overlay = { numbers: st.n, max_rel_diff: st.max, at: st.at };
  ok(st.shape.length === 0 && st.max < TOL, `sound overlay: ${st.n} numbers, largest relative difference ${st.max.toExponential(2)}`);
  st = cmp(d.parity.flash, S.flashInput(shots.subsequent, shots.bare), 'flash', fresh()); report.cases.flash_input = { numbers: st.n, max_rel_diff: st.max, at: st.at };
  ok(st.shape.length === 0 && st.max < TOL, `flash input: ${st.n} numbers, largest relative difference ${st.max.toExponential(2)}`);
  st = cmp(d.parity.heat_string.out, S.heatString(d.parity.heat_string.times), 'heat', fresh()); report.cases.heat_string = { numbers: st.n, max_rel_diff: st.max, at: st.at };
  ok(st.shape.length === 0 && st.max < TOL, `heat string: ${st.n} numbers, largest relative difference ${st.max.toExponential(2)}`);

  // ---- 3. the patched tables through the HK416 sound module
  const { makeCore } = await import(path.join(HK, 'sound', 'hk416-sound.js'));
  const bare = makeCore(hkp), peak = (x) => { let p = 0; for (let i = 0; i < x.length; i++) p = Math.max(p, Math.abs(x[i])); return p; };
  report.hk416_sound = {};
  for (const state of S.states) {
    const sup = makeCore(S.soundParams(hkp, state)), lv = S.levels(state), row = {};
    for (const persp of ['shooter', 'bystander', 'downrange']) {
      const pb = S.db(peak(bare.dry(persp, 'single', false, ['blast']))), ps = S.db(peak(sup.dry(persp, 'single', false, ['blast'])));
      row[persp] = { bare_dB: +pb.toFixed(2), suppressed_dB: +ps.toFixed(2), reduction_dB: +(pb - ps).toFixed(2), table_reduction_dB: lv[persp].reduction_dB };
    }
    report.hk416_sound[state] = row;
    ok(Math.abs(row.shooter.reduction_dB - lv.shooter.reduction_dB) < 3.0, `${state}: synthesised muzzle blast at the shooter's ear ${row.shooter.bare_dB} -> ${row.shooter.suppressed_dB} dB (48 kHz band-limited; table says -${lv.shooter.reduction_dB} dB)`);
  }
  const nb = bare.dry('downrange', 'single', false, ['nwave']), ns = makeCore(S.soundParams(hkp, 'subsequent')).dry('downrange', 'single', false, ['nwave']);
  let same = nb.length === ns.length; for (let i = 0; same && i < nb.length; i++) same = nb[i] === ns[i];
  report.crack = { identical_samples: same, peak_dB: +S.db(peak(nb)).toFixed(2) };
  ok(same, `supersonic crack down-range is sample-for-sample identical with and without the can (${report.crack.peak_dB} dB)`);
  const full = makeCore(S.soundParams(hkp, 'subsequent')).dry('downrange', 'single', false);
  report.downrange_total_peak_dB = { bare: +S.db(peak(bare.dry('downrange', 'single', false))).toFixed(2), suppressed: +S.db(peak(full)).toFixed(2) };
  ok(Math.abs(report.downrange_total_peak_dB.suppressed - report.crack.peak_dB) < 1.0, `down-range, the suppressed shot's peak is the crack: ${report.downrange_total_peak_dB.suppressed} dB (bare ${report.downrange_total_peak_dB.bare} dB)`);

  // ---- 4. the action overlay through the HK416 action module
  const A = require(path.join(HK, 'action', 'hk416-action.js')), base = JSON.parse(fs.readFileSync(path.join(HK, 'action', 'action.json'), 'utf8'));
  A.use(base); const rb = { period: base.auto.period_s, vmax: Math.max(...base.cycle.carrier_mps) };
  const merged = S.actionData(base); A.use(merged);
  const e = merged.events.times; let s = A.sample(e.max_travel);
  ok(Math.abs(s.carrierMm - merged.mechanics.full_stroke_mm) < 0.5, 'HK416Action plays the suppressed cycle: full stroke ' + s.carrierMm.toFixed(2) + ' mm');
  s = A.sample(e.in_battery + 0.02); ok(Math.abs(s.carrierMm) < 0.05 && s.boltDeg === 0, 'back in battery');
  const rs = { period: merged.auto.period_s, vmax: Math.max(...merged.cycle.carrier_mps) };
  report.action = { bare_rpm: +(60 / rb.period).toFixed(1), suppressed_rpm: +(60 / rs.period).toFixed(1), bare_peak_carrier_mps: rb.vmax, suppressed_peak_carrier_mps: rs.vmax };
  ok(rs.period < rb.period, `cyclic rate ${report.action.bare_rpm} -> ${report.action.suppressed_rpm} rpm with the can`);
  const pr = A.recoil(0.05, [0], 'ads'); ok(isFinite(pr.pos[2]) && pr.pos[2] < 0, 'recoil pose from the overlay: ' + (pr.pos[2] * 1e3).toFixed(2) + ' mm at 50 ms');
  ok(base.cycle !== merged.cycle && JSON.parse(fs.readFileSync(path.join(HK, 'action', 'action.json'), 'utf8')).auto.period_s === base.auto.period_s, 'the base action data is not modified');

  // ---- 5. baked tables and simple properties
  const h = S.heatString(Array.from({ length: 30 }, (_, i) => i * 1.0));
  ok(h[0].o2 > 0.99 && h[1].o2 < 0.06 && h[29].T_after_K > h[0].T_after_K, `30 rounds at 1 per second: ${(h[29].T_after_K - 273.15).toFixed(0)} C, first-round air share ${h[0].o2.toFixed(2)} then ${h[1].o2.toFixed(3)}`);
  ok(S.shotHeat(900, 0) < S.shotHeat(300, 0), 'a hot can takes less heat per shot');
  const f = S.flashInput('subsequent'); ok(f.scale.primary < 0.2 && f.scale.slot_jet === 0 && f.scale.secondary < 0.5, `flash scales: glow ${f.scale.primary.toFixed(3)}, secondary ${f.scale.secondary.toFixed(3)}`);
  ok(Math.abs(S.exitOffset - 0.122) < 1e-9 && S.mass > 0.4 && S.mass < 0.65, `exit ${S.exitOffset} m ahead of socket_muzzle, mass ${S.mass} kg`);

  report.passed = fail === 0; report.node = process.version;
  fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify(report, null, 1));
  console.log(fail ? fail + ' FAILED' : 'all passed'); process.exit(fail ? 1 : 0);
})();
