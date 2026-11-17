// node test.js : checks hk416-ballistics.js against ballistics.json (written by sim.py) and times it.
const B = require('./hk416-ballistics.js');
const J = require('./ballistics.json');
let fail = 0;
const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m); } };
const E2M = J.rifle.eye_to_muzzle_m, HS = J.rifle.sight_height_m;
B.configure({ atmosphere: { tempC: J.atmosphere.temp_c, pressureHPa: J.atmosphere.pressure_hpa, humidity: J.atmosphere.humidity } });

// 1. range tables: flat fire from the muzzle, no dispersion
let worst = { v: 0, y: 0, t: 0, w: 0 };
for (const name of Object.keys(J.ammo)) {
  const A = J.ammo[name];
  const s = B.fire({ origin: [0, 0, 0], dir: [0, 0, -1], originIs: 'muzzle', ammo: name, stance: 'none', spinDrift: false, maxTime: 2 });
  const w = B.fire({ origin: [0, 0, 0], dir: [0, 0, -1], originIs: 'muzzle', ammo: name, stance: 'none', spinDrift: false, maxTime: 2, wind: [4.4704, 0, 0] });
  for (const row of A.table) {
    if (!row.range_m) continue;
    const a = s.at(row.tof_s), b = w.at(row.tof_s);
    worst.v = Math.max(worst.v, Math.abs(a.speed - row.velocity_mps));
    worst.y = Math.max(worst.y, Math.abs(a.pos[1] - row.drop_m));
    worst.t = Math.max(worst.t, Math.abs(-a.pos[2] - row.range_m));
    if (row.range_m <= 500) worst.w = Math.max(worst.w, Math.abs(b.pos[0] - row.wind_drift_10mph_m));
  }
  // 2. zero angles and point of impact
  for (const zn of Object.keys(A.zeros)) {
    const Z = A.zeros[zn];
    ok(Math.abs(B.zeroAngle(name, zn) - Z.bore_angle_rad) < 2e-6, `zero ${name} ${zn}: ${B.zeroAngle(name, zn)} vs ${Z.bore_angle_rad}`);
    for (const p of Z.poi_vs_poa) ok(Math.abs(B.poi(name, zn, p.distance_from_eye_m) - p.poi_m) < 2e-4, `poi ${name} ${zn} ${p.distance_from_eye_m}`);
  }
}
console.log('max |JS - Python| over all range tables: speed', worst.v.toFixed(3), 'm/s; drop', (worst.y * 1000).toFixed(2), 'mm; range', (worst.t * 1000).toFixed(1), 'mm; wind drift', (worst.w * 1000).toFixed(2), 'mm');
ok(worst.v < 0.1 && worst.y < 0.002 && worst.t < 0.05 && worst.w < 0.003, 'range tables');

// 3. an aimed shot through the sights lands where the table says, in a rotated frame
{
  const eye = [3, 1.6, 5], dir = [0.6, 0, -0.8];
  const T = { type: 'disc', center: [eye[0] + dir[0] * 25, 1.6, eye[2] + dir[2] * 25], normal: [-0.6, 0, 0.8], radius: 0.3, passThrough: true, id: 'paper25' };
  const berm = { type: 'box', min: [-100, -2, -70], max: [100, 6, -62] }, ground = { type: 'plane', point: [0, 0, 0], normal: [0, 1, 0] };
  const s = B.fire({ origin: eye, dir, stance: 'none', spinDrift: false });
  const hits = s.trace([T, berm, ground]);
  const want = J.ammo.M855.zeros.hk100yd.poi_vs_poa.find((p) => p.distance_from_eye_m === 25);
  ok(hits.length === 2 && hits[0].target === T && hits[1].target === berm, 'paper then berm: ' + hits.map((h) => h.target && (h.target.id || h.target.type)));
  ok(Math.abs(hits[0].offset.y - want.poi_m) < 3e-4 && Math.abs(hits[0].offset.x) < 1e-4, `25 m POI ${hits[0].offset.y} vs ${want.poi_m}`);
  ok(Math.abs(hits[0].speed - want.velocity_mps) < 0.2 && Math.abs(hits[0].t * 1000 - want.tof_ms) < 0.05, '25 m speed and time');
  ok(Math.abs(hits[0].angle - 90) < 0.5, 'square hit');
  console.log('25 m paper: offset', (hits[0].offset.y * 1000).toFixed(1), 'mm (table', want.poi_mm + '), then berm at', hits[1].range.toFixed(1), 'm after', (hits[1].t * 1000).toFixed(1), 'ms');
  // stepping frame by frame gives the same answer as trace
  const s2 = B.fire({ origin: eye, dir, stance: 'none', spinDrift: false }); let all = [];
  for (let i = 0; i < 60 && !s2.done; i++) all = all.concat(s2.advance(1 / 60, [T, berm, ground]));
  ok(all.length === 2 && Math.abs(all[0].t - hits[0].t) < 1e-6 && Math.abs(all[1].t - hits[1].t) < 1e-6, 'advance == trace');
  // raycast callback
  const s3 = B.fire({ origin: eye, dir, stance: 'none', spinDrift: false });
  const viaCb = s3.trace(null, (o, d, max) => { const h = B.intersect(o, [o[0] + d[0] * max, o[1] + d[1] * max, o[2] + d[2] * max], [berm, ground]); return h ? { distance: h.f * max, normal: h.normal, object: h.target } : null; });
  ok(viaCb.length === 1 && viaCb[0].object === berm && Math.abs(viaCb[0].t - hits[1].t) < 1e-6, 'raycast callback');
}

// 4. dispersion statistics
{
  let seed = 12345; const rng = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const N = 4000, T = [{ type: 'plane', point: [0, 0, -100 - E2M], normal: [0, 0, 1] }]; let sx = 0, sy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < N; i++) { const h = B.fire({ origin: [0, 0, 0], dir: [0, 0, -1], stance: 'bench', rng }).trace(T)[0]; sx += h.point[0]; sy += h.point[1]; sxx += h.point[0] ** 2; syy += h.point[1] ** 2; }
  const sd = Math.sqrt(((sxx - sx * sx / N) + (syy - sy * sy / N)) / (2 * N)) / 100 / (Math.PI / 10800);
  console.log('bench M855 at 100 m: per-axis sigma', sd.toFixed(3), 'MOA (data', J.dispersion.rifle_ammo.M855.sigma_moa + ')');
  ok(Math.abs(sd / J.dispersion.rifle_ammo.M855.sigma_moa - 1) < 0.06, 'dispersion sigma');
}

// 5. terminal effects against the Python tables
{
  const rng = () => 0.999;
  for (const r of J.terminal.steel_plate_table) {
    const im = B.impact({ surface: 'steel', ammo: r.ammo, speed: r.impact_speed_mps, angle: 90, plate: { radius: r.plate_radius_m, thickness: r.plate_thickness_m, leanDeg: 2 }, hitOffsetY: 0, rng });
    ok(Math.abs(im.plate.omega0 - r.centre_hit_omega0_rad_s) < 0.003 && im.plate.falls === r.falls_at_2deg_lean, `plate ${r.ammo} r${r.plate_radius_m} d${r.distance_from_eye_m}: ${im.plate.omega0} vs ${r.centre_hit_omega0_rad_s}`);
    if (r.falls_at_2deg_lean) {
      const st = B.plateKick({ radius: r.plate_radius_m, leanDeg: 2 }, im.plateImpulse, 0); let t = 0;
      while (!st.down && !st.atRest && t < 5) { B.plateStep(st, 1 / 60); t += 1 / 60; }
      ok(st.down && Math.abs(t - r.fall_time_s_at_2deg_lean) < 0.03, `plate fall time ${t} vs ${r.fall_time_s_at_2deg_lean}`);
    }
  }
  for (const r of J.terminal.dirt_table) {
    const im = B.impact({ surface: 'dirt', ammo: r.ammo, speed: r.speed_mps, angle: 60, rng });
    ok(Math.abs(im.penetration - r.dirt_depth_m) < 6e-4, `dirt ${r.ammo} ${r.speed_mps}: ${im.penetration} vs ${r.dirt_depth_m}`);
  }
  const g = B.impact({ surface: 'dirt', speed: 800, angle: 3, dir: [0, -0.0523, -0.9986], normal: [0, 1, 0], rng: () => 0.3 });
  ok(g.ricochet && g.exit.dir[1] > 0 && g.exit.dir[2] < 0, 'low ground strike skips on');
  const sh = B.ricochet({ point: [0, 0, -30], normal: [0, 1, 0], ammo: 'M855' }, g);
  ok(sh && sh.at(0.05).pos[2] < -50, 'ricochet continues downrange');
  const p = B.impact({ surface: 'paper', speed: 800, angle: 90 });
  ok(Math.abs(p.hole.diameter * 1000 - J.terminal.paper.M855.hole_diameter_mm) < 0.01, 'paper hole');
  const st = B.impact({ surface: 'steel', speed: 820, angle: 90, dir: [0, 0, -1], normal: [0, 0, 1], rng: Math.random });
  const fr = st.fragments(200); let maxEl = 0;
  for (const f of fr) maxEl = Math.max(maxEl, Math.asin(f.vel[2] / Math.hypot(...f.vel)) * 180 / Math.PI);
  ok(maxEl <= 20.01 && maxEl > 10, 'splash stays within 20 deg of the plate face: ' + maxEl);
  console.log('steel, M855 at 820 m/s square: impulse', st.plateImpulse.toFixed(2), 'N s, contact', (st.contactTime * 1e6).toFixed(1), 'us, peak force', (st.peakForce / 1000).toFixed(0), 'kN');
  const c = B.sonicCrack({ mach: 2.45, missDistance: 1 }), cj = J.terminal.sonic_crack.M855.find((x) => x.mach === 2.45 && x.miss_distance_m === 1);
  ok(Math.abs(c.peakPa - cj.peak_pa) < 1 && Math.abs(c.duration - cj.duration_s) < 1e-6, 'sonic crack');
  ok(B.visibility({ ammo: 'M855' }).nakedEye === false && B.visibility({ ammo: 'M856' }).nakedEye === true, 'visibility');
  const tr = B.fire({ origin: [0, 0, 0], dir: [0, 0, -1], ammo: 'M856', stance: 'none' });
  ok(!tr.at(0.01).tracer.lit && tr.at(0.03).tracer.lit && tr.at(0.2).tracer.brightness === 1, 'tracer lights up downrange');
}

// 6. speed: one second of automatic fire (850 rpm) stepped at 60 fps against 16 targets
{
  const targets = []; for (let i = 0; i < 14; i++) targets.push({ type: 'disc', center: [i - 7, 1.2, -20 - i * 2.5], normal: [0, 0, 1], radius: 0.2 });
  targets.push({ type: 'box', min: [-30, -2, -68], max: [30, 6, -62] }, { type: 'plane', point: [0, 0, 0], normal: [0, 1, 0] });
  const t0 = process.hrtime.bigint(); let frames = 0, shots = [], fired = 0, hits = 0, acc = 0, worstFrame = 0;
  for (let rep = 0; rep < 20; rep++) for (let f = 0; f < 60; f++) {
    const f0 = process.hrtime.bigint();
    acc += 850 / 60 / 60; while (acc >= 1) { acc--; fired++; shots.push(B.fire({ origin: [0, 1.6, 0], dir: [Math.random() * 0.2 - 0.1, Math.random() * 0.04 - 0.03, -1], stance: 'aimed' })); }
    for (const s of shots) hits += s.advance(1 / 60, targets).length;
    shots = shots.filter((s) => !s.done); frames++;
    worstFrame = Math.max(worstFrame, Number(process.hrtime.bigint() - f0) / 1e6);
  }
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  console.log(`speed: ${fired} shots over ${frames} frames: ${(ms / frames).toFixed(4)} ms per frame on average, worst frame ${worstFrame.toFixed(3)} ms, ${(ms / fired * 1000).toFixed(1)} us per shot in total (${hits} hits)`);
  ok(ms / frames < 1, 'fast enough');
}
console.log(fail ? `${fail} FAILED` : 'all checks passed');
process.exit(fail ? 1 : 0);
