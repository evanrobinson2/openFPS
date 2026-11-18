// node effects/test.js : the runtime against effects.json (Python) and the published radii. Writes effects/check.json.
const fs = require('fs'), path = require('path');
const GE = require('./grenades-effects.js'); const E = GE.use(JSON.parse(fs.readFileSync(path.join(__dirname, 'effects.json'))));
const checks = []; const add = (check, value, passed) => { checks.push({ check, value, passed }); console.log(passed ? 'ok  ' : 'FAIL', check, '->', JSON.stringify(value)); };
let w = 0; for (const [r, d] of E.reference.frag) w = Math.max(w, Math.abs(GE.fragDamage(r).damage - d));
add('frag: JS damage vs Python at 11 distances (limit 1e-9)', w, w < 1e-9);
add('frag: lethal to 5 m, casualty to 15 m (published radii)', [GE.fragDamage(5).lethal, GE.fragDamage(5.01).lethal, GE.fragDamage(15).casualty, GE.fragDamage(15.01).casualty],
    GE.fragDamage(5).lethal && !GE.fragDamage(5.01).lethal && GE.fragDamage(15).casualty && !GE.fragDamage(15.01).casualty);
add('frag: cover blocks it, prone halves it outside the killing radius', [GE.fragDamage(8, { cover: true }).damage, GE.fragDamage(8, { prone: true }).damage / GE.fragDamage(8).damage], GE.fragDamage(8, { cover: true }).damage === 0 && Math.abs(GE.fragDamage(8, { prone: true }).damage / GE.fragDamage(8).damage - 0.5) < 1e-12);
w = 0; for (const s of E.reference.flash) { const f = GE.flashEffect(s.r, { viewDeg: s.view_deg, ambient: s.ambient, occluded: s.occluded, protectionDb: s.protection_db }); for (const k of ['lux', 'blind', 'whiteout_s', 'afterimage_s', 'spl_db', 'deafen', 'deaf_s']) w = Math.max(w, Math.abs(f[k] - s[k]) / Math.max(1, Math.abs(s[k]))); }
add(`flash: JS vs Python over ${E.reference.flash.length} cases (relative limit 1e-12)`, w, w < 1e-12);
const f9 = GE.flashAt([0, 1.6, 0], [1, 0, 0], [9, 1.6, 0], { ambient: 'indoor' }), fb = GE.flashAt([0, 1.6, 0], [-1, 0, 0], [9, 1.6, 0], { ambient: 'indoor' });
add('flash: facing it at the published 9 m is full blind and full deafen; back turned keeps the deafen and loses most of the blind', [f9.blind, f9.deafen, fb.blind, fb.deafen], f9.blind === 1 && Math.abs(f9.deafen - 1) < 1e-12 && fb.blind < 0.5 && Math.abs(fb.deafen - 1) < 1e-12);
add('flash: bang level at 5 ft', GE.spl(1.524), GE.spl(1.524) >= 170 && GE.spl(1.524) <= 180);
for (const key of ['smoke', 'smoke-white']) {
  const ref = E.reference[key], pl = new GE.SmokePlume(key === 'smoke' ? 'smoke-violet' : key, { burn: ref.burn, wind: ref.wind }); let worst = 0, i = 0, steps = 0;
  while (i < ref.samples.length) { pl.step(ref.dt); steps++; const s = ref.samples[i]; if (Math.abs(pl.t - s.t) < 1e-6) { worst = Math.max(worst, Math.abs(pl.opticalDepth([10, 2.5, -30], [10, 2.5, 30]) - s.across_10m), Math.abs(pl.transmission([-5, 1.6, 0], [40, 1.6, 0]) - s.along), Math.abs(pl.transmission([-5, 1.6, 15], [40, 1.6, 15]) - s.clear)); i++; } if (steps > 1e5) break; }
  add(`${key}: JS plume vs Python at ${ref.samples.length} times (limit 1e-9)`, worst, worst < 1e-9 && i === ref.samples.length);
}
{ const pl = new GE.SmokePlume('smoke-red', { burn: 60, wind: [2, 0, 0] }); while (pl.t < 30) pl.step(0.25);
  add('smoke: a sight line through the plume is blocked, one 15 m to the side is clear', [pl.transmission([-5, 1.6, 0], [40, 1.6, 0]), pl.transmission([-5, 1.6, 15], [40, 1.6, 15])], pl.transmission([-5, 1.6, 0], [40, 1.6, 0]) < 0.02 && pl.transmission([-5, 1.6, 15], [40, 1.6, 15]) > 0.98);
  add('smoke: colour of the red variant', pl.colour, pl.colour[0] > 0.6 && pl.colour[1] < 0.2); }
const passed = checks.every((c) => c.passed);
fs.writeFileSync(path.join(__dirname, 'check.json'), JSON.stringify({ _doc: 'Written by node effects/test.js', python_checks: E.checks, js_checks: checks, all_passed: passed && E.all_passed }, null, 1));
console.log(passed ? 'ALL PASSED' : 'FAILED'); process.exit(passed ? 0 : 1);
