// node throw/test.js : the runtime against throw.json (Python) and the published figures. Writes throw/check.json.
const fs = require('fs'), path = require('path');
const GT = require('./grenades-throw.js'); const T = GT.use(JSON.parse(fs.readFileSync(path.join(__dirname, 'throw.json'))));
const checks = []; const add = (check, value, passed) => { checks.push({ check, value, passed }); console.log(passed ? 'ok  ' : 'FAIL', check, '->', JSON.stringify(value)); };
for (const [key, e] of Object.entries(T.variants)) {
  const variant = key === 'smoke' ? 'smoke-green' : key;
  // 1. published average throwing distance, first landing
  const f = GT.referenceThrow(variant, 'packed_dirt'); let first = null; while (!first) { const ev = f.step(); if (ev.length) first = ev[0]; }
  add(`${key}: JS first landing vs the ${e.throw_inferred ? 'inferred' : key === 'impact' ? 'game-only' : 'published'} ${e.published_throw_m} m (limit 0.05 m)`, +first.pos[0].toFixed(4), Math.abs(first.pos[0] - e.published_throw_m) < 0.05);
  // 2. parity with the Python reference run: every 0.1 s sample and the rest point
  const g = GT.referenceThrow(variant, 'packed_dirt'), ref = e.reference.packed_dirt; let n = 0, worst = 0, i = 0;
  while (g.mode !== 'rest' && g.t < 30) { if (n % 24 === 0 && i < ref.samples.length) { const s = ref.samples[i++]; worst = Math.max(worst, Math.hypot(g.p[0] - s[1], g.p[1] - s[2], g.p[2] - s[3])); } n++; g.step(); }
  add(`${key}: JS path vs Python reference, worst difference over ${i} samples (limit 1e-5 m)`, worst, worst < 1e-5);
  add(`${key}: JS rest point vs Python on packed dirt (limit 1e-6 m)`, +g.p[0].toFixed(4), Math.abs(g.p[0] - ref.rest.pos[0]) < 1e-6 && g.bounces === ref.bounces);
  for (const s of ['concrete', 'grass']) { const h = GT.referenceThrow(variant, s); h.run(); add(`${key}: rest point on ${s} vs Python`, +h.p[0].toFixed(3), Math.abs(h.p[0] - e.reference[s].rest.pos[0]) < 1e-6); }
  // 3. fuse samples
  if (e.delay_window_s) { const r = GT.mulberry32(1234); let lo = 1e9, hi = -1e9, first8 = []; for (let k = 0; k < 20000; k++) { const d = GT.sampleDelay(variant, r); lo = Math.min(lo, d); hi = Math.max(hi, d); if (k < 8) first8.push(d); }
    add(`${key}: 20000 JS delays inside ${JSON.stringify(e.delay_window_s)} s and equal to Python's stream`, [lo, hi], lo >= e.delay_window_s[0] && hi <= e.delay_window_s[1] && first8.every((d, k) => Math.abs(d - e.delay_stats.first8[k]) < 1e-12)); }
  if (e.burn_window_s) { const r = GT.mulberry32(4321); let lo = 1e9, hi = -1e9, sum = 0; for (let k = 0; k < 20000; k++) { const d = GT.sampleBurn(variant, r); lo = Math.min(lo, d); hi = Math.max(hi, d); sum += d; }
    add(`${key}: 20000 JS burn times inside ${JSON.stringify(e.burn_window_s)} s, mean ${e.burn_mean_s || 'not published'}`, [lo, hi, sum / 20000], lo >= e.burn_window_s[0] && hi <= e.burn_window_s[1] && (!e.burn_mean_s || Math.abs(sum / 20000 - e.burn_mean_s) < 0.5)); }
}
// 4. the handling sequence and cook-off
const a = 40 * Math.PI / 180, dir = [Math.cos(a), Math.sin(a), 0];
{ const g = new GT.Grenade('frag', { seed: 7 }); g.pullPin().throwFrom([0, 1.8, 0], GT.releaseVelocity('frag', dir)); let ev = []; while (g.state !== 'done' && g.t < 20) ev = ev.concat(g.update(1 / 60));
  const fn = ev.find((e) => e.type === 'function'); add('frag thrown at once: functions after its sampled delay, in the published 4 to 5.5 s window', +fn.t.toFixed(3), fn.t >= 4 && fn.t <= 5.5 + 1 / 240 && Math.abs(fn.t - g.delay) < 2 / 240 && !fn.inHand); }
{ const g = new GT.Grenade('frag', { seed: 7 }); g.pullPin().releaseLever(); g.update(2.0); g.throwFrom([0, 1.8, 0], GT.releaseVelocity('frag', dir)); let ev = []; while (g.state !== 'done' && g.t < 20) ev = ev.concat(g.update(1 / 60));
  const fn = ev.find((e) => e.type === 'function'); add('frag cooked for 2 s: functions the same delay after the lever, so 2 s sooner after the throw', +(fn.t - 2).toFixed(3), Math.abs(fn.t - g.delay) < 2 / 240 && fn.pos[1] > 0.5); }
{ const g = new GT.Grenade('frag', { seed: 7 }); g.pullPin().releaseLever(); const ev = g.update(8); const fn = ev.find((e) => e.type === 'function'); add('frag cooked too long: functions in the hand', fn && fn.inHand, !!fn && fn.inHand); }
{ const g = new GT.Grenade('frag', { seed: 7 }); g.throwFrom([0, 1.8, 0], GT.releaseVelocity('frag', dir)); const ev = g.update(10); add('pin not pulled: nothing functions', ev.length, ev.every((e) => e.type !== 'function')); }
{ const g = new GT.Grenade('impact', { seed: 3 }); g.pullPin().throwFrom([0, 1.8, 0], GT.releaseVelocity('impact', dir)); let ev = []; while (g.state !== 'done' && g.t < 20) ev = ev.concat(g.update(1 / 60));
  const fn = ev.find((e) => e.type === 'function'), b = ev.find((e) => e.type === 'bounce'); add('impact (game-only): functions on its first contact, at the landing point', [fn.cause, +fn.pos[0].toFixed(2)], fn.cause === 'contact' && Math.abs(fn.pos[0] - 35) < 0.1 && b.t === fn.t); }
{ const g = new GT.Grenade('impact', { seed: 3, walls: [{ point: [1.5, 0, 0], normal: [-1, 0, 0], surface: 'concrete' }] }); g.pullPin().throwFrom([0, 1.8, 0], GT.releaseVelocity('impact', dir)); let ev = []; while (g.state !== 'done' && g.t < 20) ev = ev.concat(g.update(1 / 60));
  const fn = ev.find((e) => e.type === 'function'), nb = ev.filter((e) => e.type === 'bounce' && e.t < fn.t).length; add('impact (game-only): a wall 1.5 m away is hit before the 0.35 s arming time, so it bounces off and functions on a later contact', [nb, fn.cause], nb >= 1 && fn.cause === 'contact'); }
{ const g = new GT.Grenade('smoke-red', { seed: 5 }); g.pullPin().throwFrom([0, 1.8, 0], GT.releaseVelocity('smoke-red', dir)); let ev = []; while (g.state !== 'done' && g.t < 200) ev = ev.concat(g.update(1 / 30));
  const ig = ev.find((e) => e.type === 'function'), bo = ev.find((e) => e.type === 'burnout'); add('smoke: ignites in 0.7 to 2.0 s, burns 50 to 90 s', [+ig.t.toFixed(2), +(bo.t - ig.t).toFixed(1)], ig.kind === 'ignite' && ig.t >= 0.7 && ig.t <= 2.01 && bo.t - ig.t >= 50 && bo.t - ig.t <= 90.01); }
// 5. energy never grows through a bounce
{ const f = GT.referenceThrow('frag', 'concrete'); let ok = true, prev = Infinity; for (const e of f.run()) if (e.type === 'bounce') { ok = ok && e.speed <= prev + 1e-9; prev = e.speed; } add('frag on concrete: impact speed falls at every bounce', f.bounces, ok && f.bounces >= 3); }
const passed = checks.every((c) => c.passed);
fs.writeFileSync(path.join(__dirname, 'check.json'), JSON.stringify({ _doc: 'Written by node throw/test.js', python_checks: T.checks, js_checks: checks, all_passed: passed && T.all_passed }, null, 1));
console.log(passed ? 'ALL PASSED' : 'FAILED'); process.exit(passed ? 0 : 1);
