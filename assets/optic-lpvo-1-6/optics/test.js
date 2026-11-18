// node test.js : checks optic-lpvo.js against lpvo.json (written by sim.py) and the reticle against the rifle's
// ballistics runtime (assets/hk416/ballistics/hk416-ballistics.js). Writes parity.json.
const fs = require('fs'), path = require('path');
const L = require('./optic-lpvo.js'), J = require('./lpvo.json');
const B = require('../../hk416/ballistics/hk416-ballistics.js');
L.init(J);
let fail = 0; const out = {}; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m); } };

// 1. first-order optics, JS against Python
{
  const w = { cam: 0, eyeRelief: 0, exitPupil: 0, tan: 0, trans: 0, mask: 0 };
  for (const r of J.parity_samples.rows) {
    const M = r.magnification, c = L.cam(M), fo = L.firstOrder(M), f = L.field(M);
    w.cam = Math.max(w.cam, Math.abs(c[0] - r.cam[0]), Math.abs(c[1] - r.cam[1]));
    w.eyeRelief = Math.max(w.eyeRelief, Math.abs(fo.eyeRelief - r.eye_relief_mm));
    w.exitPupil = Math.max(w.exitPupil, Math.abs(fo.exitPupil - r.exit_pupil_mm));
    w.tan = Math.max(w.tan, Math.abs(f.tanReal - r.tan_half_real), Math.abs(f.tanApparent - r.tan_half_apparent));
    w.trans = Math.max(w.trans, Math.abs(L.transmission(M, f.tanReal * 0.9, 31) - r.transmission_at_0p9_field));
    for (const m of r.mask) w.mask = Math.max(w.mask, Math.abs(L.mask(m.ex, m.ey, m.dz, m.ax, m.ay, fo.exitPupil, m.eye_pupil_mm) - m.value));
  }
  for (const r of J.by_magnification) {
    const fo = L.firstOrder(r.magnification);
    w.eyeRelief = Math.max(w.eyeRelief, Math.abs(fo.eyeRelief - r.eye_relief_mm)); w.exitPupil = Math.max(w.exitPupil, Math.abs(fo.exitPupil - r.exit_pupil_mm));
    ok(fo.apertureStop === r.aperture_stop, 'stop at ' + r.magnification);
    ok(Math.abs(fo.angularMagnification) - r.magnification < 1e-9, 'magnification ' + r.magnification);
  }
  out.js_vs_python = { what: 'largest |JS - Python| over the parity samples and the per-magnification table', cam_mm: w.cam, eye_relief_mm: w.eyeRelief, exit_pupil_mm: w.exitPupil,
                       field_tangent: w.tan, vignetting_fraction: w.trans, eye_box_mask: w.mask };
  ok(w.cam < 1e-7 && w.eyeRelief < 1e-6 && w.exitPupil < 1e-7 && w.tan < 1e-9 && w.trans < 1e-9 && w.mask < 1e-7, 'JS vs Python ' + JSON.stringify(w));
  console.log('JS vs Python: cam', w.cam.toExponential(1), 'mm; eye relief', w.eyeRelief.toExponential(1), 'mm; exit pupil', w.exitPupil.toExponential(1), 'mm; vignetting', w.trans.toExponential(1), '; mask', w.mask.toExponential(1));
}

// 2. shade(): centred eye at the design point sees a full, evenly lit field; off the eye box it goes dark
{
  const st = L.state(6), c = L.shade(st, { x: 0, y: 0, z: 0 }, 0, 0), e = L.shade(st, { x: 0, y: 0, z: 0 }, st.tanApparent * 0.5, 0);
  ok(Math.abs(c.brightness - 1) < 1e-9 && e.brightness > 0.9, 'centred eye: ' + c.brightness + ' ' + e.brightness);
  ok(L.shade(st, { x: 4, y: 0, z: 0 }, 0, 0).brightness === 0, 'eye 4 mm off at 6x is dark');
  ok(!L.shade(st, { x: 0, y: 0, z: 0 }, st.tanApparent * 1.01, 0).inField, 'field stop');
  const far = L.shade(st, { x: 0, y: 0, z: 30 }, st.tanApparent * 0.9, 0).brightness; ok(far === 0, 'eye 30 mm too far back: edge lost, got ' + far);
  const s1 = L.state(1); ok(Math.abs(s1.eyeRelief - J.by_magnification[0].eye_relief_mm) < 1e-6 && s1.reticleScale === 6, 'state(1)');
  out.shade = { centre_6x: c.brightness, half_field_6x: e.brightness };
}

// 3. the reticle and the zero tables against the ballistics runtime
{
  L.mountTo(B);
  B.configure({ atmosphere: { tempC: 15, pressureHPa: 1013.25, humidity: 0 }, spinDrift: false });
  const rows = []; let worstHold = 0, worstZero = 0, worstTable = 0;
  for (const ammo of ['M855', 'Mk262']) {
    for (const zn of Object.keys(J.zero.ammo[ammo])) {
      const Z = J.zero.ammo[ammo][zn], za = B.zeroAngle(ammo, Z.zero_distance_m) * 1000;
      worstZero = Math.max(worstZero, Math.abs(za - Z.bore_angle_mrad));
      for (const h of Z.holds) worstTable = Math.max(worstTable, Math.abs(-B.poi(ammo, Z.zero_distance_m, h.distance_m) / h.distance_m * 1000 - h.hold_mrad));
    }
    for (const m of J.reticle.bdc_marks) {
      const rt = -B.poi(ammo, 200, m.distance_m) / m.distance_m * 1000, mark = ammo === 'M855' ? m.m855_hold_mrad : m.mk262_hold_mrad;
      rows.push({ ammo, distance_m: m.distance_m, reticle_mark_mrad: mark, ballistics_runtime_mrad: rt, difference_mrad: mark - rt, miss_mm: (mark - rt) * m.distance_m });
      worstHold = Math.max(worstHold, Math.abs(mark - rt));
    }
  }
  out.reticle_vs_ballistics_runtime = { what: 'BDC marks (bar = M855, leg tips = Mk 262, 200 m zero) against HK416Ballistics.poi() with the optic mounted (sightHeight ' +
    (J.zero.axis_over_bore_mm / 1000).toFixed(5) + ' m, eyeToMuzzle ' + J.zero.eye_to_muzzle_m.toFixed(4) + ' m)', rows, max_difference_mrad: worstHold };
  out.zero_tables_vs_ballistics_runtime = { what: 'every zero angle and every hold-table row, both loads and M856, against the runtime', max_zero_angle_difference_mrad: worstZero, max_hold_difference_mrad: worstTable };
  ok(worstHold < 0.02, 'reticle holds ' + worstHold); ok(worstZero < 0.005, 'zero angles ' + worstZero); ok(worstTable < 0.03, 'hold tables ' + worstTable);
  for (const r of rows) console.log(r.ammo.padEnd(6), r.distance_m, 'm: mark', r.reticle_mark_mrad.toFixed(3), 'runtime', r.ballistics_runtime_mrad.toFixed(3), 'mrad, difference', (r.miss_mm).toFixed(1), 'mm');
  console.log('zero angles within', worstZero.toExponential(1), 'mrad; hold tables within', worstTable.toExponential(1), 'mrad');
  // hold() interpolation
  ok(Math.abs(L.hold('M855', '200m', 300) - J.reticle.bdc_marks[0].m855_hold_mrad) < 1e-9, 'hold at a table row');
  const hi = L.hold('M855', '200m', 325), ref = -B.poi('M855', 200, 325) / 325 * 1000; ok(Math.abs(hi - ref) < 0.03, 'hold between rows ' + hi + ' vs ' + ref);
}

// 4. speed
{
  const st = L.state(3.3); const t0 = process.hrtime.bigint(); let s = 0; const N = 2e6;
  for (let i = 0; i < N; i++) s += L.shade(st, { x: 1, y: 0.5, z: 5 }, (i % 100) * 0.002 - 0.1, 0.05).brightness;
  out.speed = { shade_ns_per_pixel: Number(process.hrtime.bigint() - t0) / N };
  const t1 = process.hrtime.bigint(); for (let i = 0; i < 50; i++) L.state(1 + i * 0.0999); out.speed.state_ms = Number(process.hrtime.bigint() - t1) / 50 / 1e6;
  console.log('shade():', out.speed.shade_ns_per_pixel.toFixed(0), 'ns per pixel; state():', out.speed.state_ms.toFixed(2), 'ms');
}
out.failures = fail; out.passed = fail === 0;
fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify(out, (k, v) => (typeof v === 'number' ? +v.toPrecision(6) : v), 1) + '\n');
console.log(fail ? fail + ' FAILED' : 'all checks passed');
process.exit(fail ? 1 : 0);
