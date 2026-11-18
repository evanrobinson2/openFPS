// node test.js : checks optic-red-dot.js against reddot.json (written by sim.py) and the zero tables against the
// rifle's ballistics runtime (assets/hk416/ballistics/hk416-ballistics.js). Writes parity.json.
const fs = require('fs'), path = require('path');
const R = require('./optic-red-dot.js'), J = require('./reddot.json');
const B = require('../../hk416/ballistics/hk416-ballistics.js');
R.init(J);
let fail = 0; const out = {}; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m); } };
const MOA = R.MOA;

// 1. the exact ray trace in JS against the Python ray trace, and the polynomial against both
{
  let wBeam = 0, wErr = 0, wPoly = 0;
  for (const s of J.parity_samples.rows) {
    const b = R.beam(s.eye_right_mm, s.eye_up_mm, { exact: true }), p = R.beam(s.eye_right_mm, s.eye_up_mm);
    wBeam = Math.max(wBeam, Math.abs(b[0] - s.beam_shooter[0]), Math.abs(b[1] - s.beam_shooter[1]));
    wPoly = Math.max(wPoly, Math.abs(p[0] - s.beam_shooter[0]), Math.abs(p[1] - s.beam_shooter[1]));
    for (const D of Object.keys(s.errors)) {
      const e = R.parallax(s.eye_right_mm, s.eye_up_mm, +D, { exact: true }), q = R.parallax(s.eye_right_mm, s.eye_up_mm, +D);
      wErr = Math.max(wErr, Math.abs(e.right - s.errors[D][0]), Math.abs(e.up - s.errors[D][1]));
      wPoly = Math.max(wPoly, Math.abs(q.right - s.errors[D][0]), Math.abs(q.up - s.errors[D][1]));
    }
  }
  out.js_vs_python = { what: 'largest |JS - Python| over 10 eye positions and 5 distances, in rad', exact_trace_beam_direction: wBeam, exact_trace_parallax_error: wErr,
                       polynomial_vs_python_trace: wPoly, polynomial_vs_python_trace_moa: wPoly / MOA };
  ok(wBeam < 5e-9 && wErr < 5e-9, 'exact trace: ' + wBeam + ' ' + wErr); ok(wPoly / MOA < 0.05, 'polynomial: ' + wPoly / MOA + ' MOA');
  console.log('JS exact trace vs Python: beam', wBeam.toExponential(1), 'rad, parallax', wErr.toExponential(1), 'rad; polynomial within', (wPoly / MOA).toFixed(4), 'MOA');
}

// 2. parallax behaviour: zero on the axis, and the thin-lens relation near it
{
  const c = R.parallax(0, 0, 50); ok(c.moa < 1e-9, 'centred eye has no parallax');
  const d0 = J.optics.parallax.parallax_free_distance_m;
  const e = R.parallax(1, 0, 25, { exact: true }), l = J.frames.lens_from_shooter;
  // 1 mm to the right is (l[0][0], l[1][0]) in the lens frame
  const thin = [l[0][0] * 1e-3 * (1 / 25 - 1 / d0.sagittal), l[1][0] * 1e-3 * (1 / 25 - 1 / d0.tangential)], s = J.frames.shooter_from_lens;
  const tr = s[0][0] * thin[0] + s[0][1] * thin[1], tu = s[1][0] * thin[0] + s[1][1] * thin[1];
  ok(Math.hypot(e.right - tr, e.up - tu) < 5e-6, 'thin-lens relation at 1 mm: ' + [e.right, e.up, tr, tu]);
  out.parallax_examples_moa = {};
  for (const D of [10, 25, 50, 100, 300]) out.parallax_examples_moa[D + ' m'] = { eye_3mm_right: R.parallax(3, 0, D).moa, eye_6mm_right: R.parallax(6, 0, D).moa, eye_6mm_up: R.parallax(0, 6, D).moa, eye_10mm_up: R.parallax(0, 10, D).moa };
}

// 3. brightness
{
  for (const row of J.brightness.versus_ambient) {
    const rec = R.recommend(row.scene_luminance_cd_m2), d = R.dot(rec, row.scene_luminance_cd_m2);
    ok(rec === row.recommended_position, 'recommended position for ' + row.ambient + ': ' + rec + ' vs ' + row.recommended_position);
    ok(Math.abs(d.contrast / row.contrast_at_recommended - 1) < 1e-6, 'contrast for ' + row.ambient);
    ok(Math.abs(R.eyePupil(row.scene_luminance_cd_m2) - row.eye_pupil_mm) < 1e-6, 'eye pupil for ' + row.ambient);
  }
  ok(R.dot(0, 100).look === 'off' && R.dot(11, 0.01).look === 'blooming' && R.dot(4, 20000).look === 'invisible', 'looks');
  out.brightness = { top_setting_on_sunlit_paper: R.dot(11, 20000), lowest_day_setting_indoors: R.dot(4, 60) };
}

// 4. sight picture
{
  const c = R.sightPicture({ x: 0, y: 0, z: 0 }); ok(c.visible && Math.abs(c.dot.x) < 1e-12 && Math.abs(c.front.x) < 1e-12, 'centred');
  ok(R.sightPicture({ x: 10, y: 0, z: 0 }).visible && !R.sightPicture({ x: 13, y: 0, z: 0 }).visible, 'the dot leaves the window between 10 and 13 mm of eye offset');
  const t = R.sightPicture({ x: 0, y: 0, z: 0 }, { clicksUp: 10 }); ok(Math.abs(t.dot.y - 10 * 0.5 * MOA) < 1e-9, 'ten clicks up');
  out.sight_picture = { front_window_half_angle_deg: Math.atan(c.front.r) * 180 / Math.PI, rear_window_half_angle_deg: Math.atan(c.rear.r) * 180 / Math.PI };
}

// 5. the zero tables against the ballistics runtime
{
  R.mountTo(B);
  B.configure({ atmosphere: { tempC: 15, pressureHPa: 1013.25, humidity: 0 }, spinDrift: false });
  let wZero = 0, wHold = 0, wPoi = 0;
  for (const ammo of Object.keys(J.zero.ammo)) for (const zn of Object.keys(J.zero.ammo[ammo])) {
    const Z = J.zero.ammo[ammo][zn];
    wZero = Math.max(wZero, Math.abs(B.zeroAngle(ammo, Z.zero_distance_m) * 1000 - Z.bore_angle_mrad));
    for (const h of Z.holds) { const p = B.poi(ammo, Z.zero_distance_m, h.distance_m); wHold = Math.max(wHold, Math.abs(-p / h.distance_m * 1000 - h.hold_mrad)); wPoi = Math.max(wPoi, Math.abs(p * 1000 - h.poi_mm)); }
  }
  out.zero_tables_vs_ballistics_runtime = { what: 'every zero angle and hold-table row (3 loads, 4 zeros, 19 distances) against HK416Ballistics with the optic mounted (sightHeight ' +
    (J.zero.axis_over_bore_mm / 1000).toFixed(5) + ' m, eyeToMuzzle ' + J.zero.eye_to_muzzle_m.toFixed(4) + ' m)', max_zero_angle_difference_mrad: wZero, max_hold_difference_mrad: wHold, max_poi_difference_mm: wPoi };
  ok(wZero < 0.005 && wHold < 0.03 && wPoi < 1.0, 'zero tables: ' + [wZero, wHold, wPoi]);
  console.log('zero tables vs ballistics runtime: zero angle', wZero.toExponential(1), 'mrad, hold', wHold.toExponential(1), 'mrad, POI', wPoi.toFixed(2), 'mm');
  const hi = R.hold('M855', '50m', 325), ref = -B.poi('M855', 50, 325) / 325 * 1000; ok(Math.abs(hi - ref) < 0.03, 'hold between rows ' + hi + ' vs ' + ref);
}

// 6. speed
{
  const t0 = process.hrtime.bigint(); let s = 0; const N = 1e6;
  for (let i = 0; i < N; i++) s += R.parallax((i % 20) - 10, 3, 25).right;
  const t1 = process.hrtime.bigint(); for (let i = 0; i < 2000; i++) s += R.parallax((i % 20) - 10, 3, 25, { exact: true }).right;
  out.speed = { polynomial_ns: Number(t1 - t0) / N, exact_trace_us: Number(process.hrtime.bigint() - t1) / 2000 / 1000 };
  console.log('parallax(): polynomial', out.speed.polynomial_ns.toFixed(0), 'ns; exact trace', out.speed.exact_trace_us.toFixed(0), 'us');
}
out.failures = fail; out.passed = fail === 0;
fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify(out, (k, v) => (typeof v === 'number' ? +v.toPrecision(6) : v), 1) + '\n');
console.log(fail ? fail + ' FAILED' : 'all checks passed');
process.exit(fail ? 1 : 0);
