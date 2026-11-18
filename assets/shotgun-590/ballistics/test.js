// node ballistics/test.js : checks shotgun590-ballistics.js against ballistics.json (run after sim.py)
const B = require('./shotgun590-ballistics.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'ballistics.json'), 'utf8')); B.use(d);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const IN = 0.0254, YD = 0.9144, FT = 0.3048;
// 1. the module's tables against sim.py's
for (const key of ['slug', 'buck00']) {
  const ref = d.tables[key].filter((r) => r.range_m > 0), t = B.table(key, ref.map((r) => r.range_m)); let ev = 0, ed = 0;
  ref.forEach((r, i) => { ev = Math.max(ev, Math.abs(t[i].v - r.v) / r.v); ed = Math.max(ed, Math.abs(t[i].drop - r.drop_m)); });
  ok(ev < 1e-3 && ed < 1e-3, `${key}: table matches sim.py (velocity ${(ev * 100).toFixed(4)} %, drop ${(ed * 1e3).toFixed(3)} mm)`);
}
// 2. the slug against the maker's published velocities (level bore, so velocity only)
{ const rows = d.checks.slug_vs_federal_table.rows.filter((r) => r.range_yd > 0), t = B.table('slug', rows.map((r) => r.range_yd * YD)); let e = 0;
  rows.forEach((r, i) => { e = Math.max(e, Math.abs(t[i].v / FT - r.v_fps_pub) / r.v_fps_pub); });
  ok(e < 0.02, `slug within ${(e * 100).toFixed(2)} % of the published velocities at 25 to 125 yd`); }
// 3. seeded scatter matches sim.py
{ const r = B.rng(d.reference_scatter_rad.seed); let e = 0;
  for (const shot of d.reference_scatter_rad.shots) { const s = B.fire({ load: 'buck00', rng: r }); s.projectiles.forEach((p, i) => { e = Math.max(e, Math.abs(p.scatter[0] - shot[i][0]), Math.abs(p.scatter[1] - shot[i][1])); }); }
  ok(e < 1e-8, `seeded pellet scatter matches sim.py (max difference ${e.toExponential(1)} rad)`); }
// 4. mean extreme spread follows the 1 in per yd rule
{ const r = B.rng(99); let s = 0; const n = 600;
  for (let i = 0; i < n; i++) s += B.extremeSpread(B.pattern('buck00', 15 * YD, { rng: r }));
  const mean = s / n / IN; ok(Math.abs(mean - 15) < 0.75, `mean extreme spread at 15 yd over ${n} shots: ${mean.toFixed(2)} in (rule: 15)`); }
// 5. nine pellets, each 3.50 g at the published speed; momentum of the load
{ const s = B.fire({ load: 'buck00' }); const v = Math.hypot(...s.projectiles[0].vel);
  ok(s.projectiles.length === 9 && Math.abs(s.projectiles[0].mass - 0.0035) < 5e-5 && Math.abs(v - 1325 * FT) < 1e-6, `nine pellets of ${(s.projectiles[0].mass * 1e3).toFixed(2)} g at ${v.toFixed(1)} m/s`); }
// 6. advance() and trace() agree
{ const a = B.fire({ load: 'slug' }), hit = a.trace([{ point: [0, 0, 50], normal: [0, 0, -1] }])[0]; const b = B.fire({ load: 'slug' }); b.advance(hit.t);
  ok(Math.abs(b.projectiles[0].pos[2] - 50) < 0.02, `advance(${hit.t.toFixed(4)} s) reaches the 50 m plane: z = ${b.projectiles[0].pos[2].toFixed(3)} m`); }
// 7. crosswind pushes the slug downwind; bead sight tilts the bore up
{ const h = B.fire({ load: 'slug', wind: [4.4704, 0, 0] }).trace([{ point: [0, 0, 100 * YD], normal: [0, 0, -1] }])[0];
  ok(Math.abs(h.pos[0] / IN - 6.6) < 1.0, `10 mph crosswind drift at 100 yd: ${(h.pos[0] / IN).toFixed(2)} in (published 6.6)`);
  const a = B.aim([0, 0, 1], 'bead_flat'); ok(a.dir[1] > 0 && Math.abs(Math.atan2(a.dir[1], a.dir[2]) - d.sight_bead_flat.bore_above_sight_line_rad) < 1e-9, `bead sight: bore ${(Math.atan2(a.dir[1], a.dir[2]) * 1e3).toFixed(2)} mrad above the line of sight`); }
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
