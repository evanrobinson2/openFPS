// node test.js : checks g44v-ballistics.js against ballistics.json (run after sim.py). Writes parity.json.
const B = require('./g44v-ballistics.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'ballistics.json'), 'utf8'));
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
let worst = 0;
for (const c of d.parity.cases) {
  const s = B.poi(c.ammo, c.zero, c.distance, { windX: c.wind_x });
  worst = Math.max(worst, Math.abs(s.y - c.y), Math.abs(s.x - c.x), Math.abs(s.v - c.v), Math.abs(s.tof - c.tof), Math.abs(s.elevation - c.elevation));
}
ok(worst < 1e-9, d.parity.cases.length + ' poi() cases match sim.py: worst difference ' + worst.toExponential(2));
for (const k of B.ammo) {
  const z = B.poi(k, 25, 25); ok(Math.abs(z.y) < 1e-6, k + ': on the line of sight at the 25 m zero (' + (z.y * 1e3).toExponential(1) + ' mm)');
  const t = d.ammo[k].table_zero_25m[10], s = B.poi(k, 25, 50); ok(Math.abs(s.y * 1e3 - t.path_mm) < 0.01 && Math.abs(s.v - t.v_mps) < 0.01, k + ': 50 m row of the table: path ' + (s.y * 1e3).toFixed(1) + ' mm, ' + s.v.toFixed(1) + ' m/s');
}
// a fired bullet in the world frame lands where poi() says: eye at 1.5 m, looking along +Z, disc target at 50 m
const tg = [{ name: 'paper', point: [0, 1.5, 50], normal: [0, 0, -1], radius: 1 }];
const shot = B.fire({ origin: [0, 1.5, 0], dir: [0, 0, 1], ammo: 'cci_mini_mag', zero: 25 }), hit = shot.trace(tg), ref = B.poi('cci_mini_mag', 25, 50);
ok(hit && Math.abs(hit.point[1] - 1.5 - ref.y) < 2e-4 && Math.abs(hit.speed - ref.v) < 0.05, 'fire() + trace() agree with poi(): ' + ((hit.point[1] - 1.5) * 1e3).toFixed(1) + ' mm against ' + (ref.y * 1e3).toFixed(1) + ' mm');
ok(!d.ammo.cci_mini_mag.supersonic_at_muzzle && hit.mach < 1, 'Mini-Mag is subsonic from the 102 mm barrel (Mach ' + (d.ammo.cci_mini_mag.mv / 340.294).toFixed(2) + ')');
// dispersion: seeded, with the stated sigma
let s = 12345; const rng = () => { s = (s + 0x6D2B79F5) >>> 0; let z = s; z = Math.imul(z ^ (z >>> 15), z | 1) >>> 0; z = (z ^ (z + (Math.imul(z ^ (z >>> 7), z | 61) >>> 0))) >>> 0; return ((z ^ (z >>> 14)) >>> 0) / 4294967296; };
let sx = 0, sy = 0, n = 400; const far = [{ name: 'p', point: [0, 1.5, 25], normal: [0, 0, -1] }];
for (let i = 0; i < n; i++) { const h = B.fire({ origin: [0, 1.5, 0], dir: [0, 0, 1], ammo: 'cci_standard_velocity', zero: 25, rng }).trace(far); sx += h.point[0] ** 2; sy += (h.point[1] - 1.5) ** 2; }
const sig = Math.sqrt((sx + sy) / (2 * n)) / 25 / (Math.PI / 10800);
ok(Math.abs(sig - d.ammo.cci_standard_velocity.sigma_moa) < 0.3, 'dispersion of 400 seeded shots: ' + sig.toFixed(2) + ' MOA per axis (stated ' + d.ammo.cci_standard_velocity.sigma_moa + ')');
fs.writeFileSync(path.join(__dirname, 'parity.json'), JSON.stringify({ note: 'node test.js: g44v-ballistics.js against sim.py', cases: d.parity.cases.length, worst_difference: worst, failed: fail }, null, 1));
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
