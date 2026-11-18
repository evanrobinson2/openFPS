// node action/test_action.js : checks shotgun590-action.js against action.json and the manual's procedures (run after sim.py)
const A = require('./shotgun590-action.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, 'action.json'), 'utf8')); A.use(d);
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
const types = (e) => e.map((x) => x.type).join(',');

// ---- the manual's function test, p20, on an empty gun
{ const g = A.create();
  g.holdActionLock(true); let moved = true; for (let i = 0; i < 3; i++) { const e = g.pump(); moved = moved && types(e).includes('rear_stop') && types(e).endsWith('locked'); } g.holdActionLock(false);
  ok(moved, 'p20: with the action lock lever held, the action opens and closes freely');
  g.setSafety(true); let e = g.pullTrigger(); ok(e[0].type === 'blocked' && e[0].why === 'safety' && g.hammerCocked, 'p20: safety ON, trigger pulled: the hammer does not fall');
  g.releaseTrigger(); e = g.setSafety(false); ok(g.hammerCocked && types(e) === 'safety', 'p20: trigger released, safety moved OFF: the hammer does not fall');
  e = g.pullTrigger(); ok(types(e) === 'hammer_fall,click' && !g.hammerCocked, 'p20: safety OFF, trigger pulled: the hammer falls');
  g.releaseTrigger(); e = g.setSlide(1); g.setSafety(true); ok(types(e).includes('hammer_cocked') && g.slide === 1 && g.safety, 'p20: the action opens after the hammer has fallen; safety back ON'); }

// ---- action lock, p6 and p9
{ const g = A.create(); let e = g.setSlide(1); ok(e[0].type === 'blocked' && e[0].why === 'action_locked' && g.slide === 0, 'p6: a cocked, closed action stays locked without the lever');
  g.holdActionLock(true); e = g.setSlide(1); ok(g.slide === 1, 'p6: with the lever depressed it opens'); }

// ---- loading to full capacity, p8 and p9, then firing it empty
{ const g = A.create(); g.holdActionLock(true); g.setSlide(1); g.holdActionLock(false);
  let e = g.loadThroughPort('slug'); ok(types(e) === 'shell_on_elevator', 'p8: first shell through the ejection port onto the elevator');
  e = g.setSlide(0); ok(types(e) === 'lift,feed,chambered,locked' && g.chamber.load === 'slug', 'p8: closing the action chambers it: ' + types(e));
  let n = 0; while (g.insertShell('buck00')[0].type === 'shell_inserted') n++;
  ok(n === 8 && g.rounds() === 9, `p9 and the maker's capacity: ${n} shells in the magazine, ${g.rounds()} in all`);
  ok(g.insertShell('buck00')[0].why === 'magazine_full', 'the ninth shell is refused');
  g.setSafety(false); const fired = [];
  for (let i = 0; i < 10; i++) { const f = g.pullTrigger(); g.releaseTrigger(); const last = f[f.length - 1]; fired.push(last.type === 'fire' ? last.load : last.type); g.pump(); }
  ok(fired.join(' ') === 'slug buck00 buck00 buck00 buck00 buck00 buck00 buck00 buck00 click', 'nine shots, then a click: ' + fired.join(' '));
  ok(g.rounds() === 0 && g.chamber === null, 'the gun is empty afterwards'); }

// ---- one pump after a shot: the events in the manual's order (p9, p10)
{ const g = A.create(); g.holdActionLock(true); g.setSlide(1); g.loadThroughPort('buck00'); g.setSlide(0); g.holdActionLock(false); g.insertShell('buck00'); g.setSafety(false);
  g.pullTrigger(); g.releaseTrigger(); const back = g.setSlide(1), fwd = g.setSlide(0);
  ok(types(back) === 'unlock,hammer_cocked,eject,shell_released,rear_stop' && back[2].fired === true, 'rearward: ' + types(back));
  ok(types(fwd) === 'lift,feed,chambered,locked' && fwd[3].actionLocked, 'forward: ' + types(fwd));
  // the trigger held through the pump does not fire on closing (an inference, see README); it must be let go and pulled again
  g.insertShell('buck00'); g.pullTrigger(); const held = g.pump(); const again = g.pullTrigger(); g.releaseTrigger(); const next = g.pullTrigger();
  ok(!types(held).includes('fire') && again.length === 0 && types(next) === 'hammer_fall,fire', 'trigger held through the pump: no shot on closing; release and pull fires');
  const h = A.create(); h.holdActionLock(true); h.insertShell('buck00'); h.setSlide(0.8); const e = h.setSlide(0); ok(h.chamber === null && h.tube.length === 1, 'a short stroke (80 %) does not release a shell: ' + types(e)); }

// ---- unloading, p10
{ const g = A.create(); g.holdActionLock(true); g.setSlide(1); g.loadThroughPort('buck00'); g.setSlide(0); g.insertShell('buck00'); g.insertShell('buck00');
  let e = g.setSlide(0.5); e = e.concat(g.setSlide(1)); ok(types(e).includes('eject') && e.find((x) => x.type === 'eject').fired === false, 'p10: opening with the lever ejects the unfired shell');
  ok(g.lifter !== null, 'p10: fully rearward releases the next shell onto the elevator'); g.tipOutElevatorShell(); g.setSlide(0);
  e = g.releaseFromMagazine(); ok(e[0].type === 'shell_removed' && g.rounds() === 0, 'p10: the cartridge stop releases the last shell; the gun is empty'); }

// ---- playback against action.json
const S = d.cycle.stroke_mm, lm = d.cycle.lost_motion_mm;
let p = A.pose(1); ok(Math.abs(p.slideZ + S * 1e-3) < 1e-9 && Math.abs(p.boltZ + (S - lm) * 1e-3) < 1e-9, `full stroke: slide ${(-p.slideZ * 1e3).toFixed(1)} mm, bolt ${(-p.boltZ * 1e3).toFixed(1)} mm`);
p = A.pose(lm / S / 2); ok(p.boltZ === 0 && p.boltLock > 0, 'lost motion: the bolt lock drops before the bolt moves');
p = A.pose(0.5, true); ok(Math.abs(p.elevator / Math.PI * 180 - d.cycle.kinematics.elevator_deg_raised) < 1e-9, 'elevator fully raised mid-way through the forward stroke');
{ let worst = 0; for (const e of d.cycle.events) { const s = A.stroke(e.t + (e.direction === 'back' ? 0 : 0)); worst = Math.max(worst, Math.abs(s.x * S - e.slide_mm)); } ok(worst < 0.15, `stroke(t) passes every event at its slide position (worst ${worst.toFixed(3)} mm)`); }
for (const k of ['buck00', 'slug']) {
  const s = d.shots[k], fr = s.free_recoil; let pk = 0, tpk = 0;
  for (let t = 0; t < 0.02; t += 1e-5) { const q = A.shot(t, k); if (q.pressureMPa > pk) { pk = q.pressureMPa; tpk = t; } }
  ok(pk < 79.3 && tpk > s.t0, `${k}: peak ${pk.toFixed(1)} MPa at ${(tpk * 1e3).toFixed(2)} ms after the trigger break`);
  let zmax = 0, pmax = 0; for (let t = 0; t < 0.8; t += 1e-3) { const r = A.recoil(t, k, 'shoulder'); zmax = Math.max(zmax, -r.pos[2]); pmax = Math.max(pmax, r.pitchDeg); }
  ok(zmax > 0.01 && zmax < 0.12 && pmax > 0.5 && pmax < 12 && A.recoil(0.79, k).pitchDeg < 0.3, `${k}: recoil ${(zmax * 1e3).toFixed(0)} mm back, ${pmax.toFixed(1)} deg up, settled by 0.8 s; free recoil ${fr.energy_J} J`);
}
// ---- hulls: reproduce the seeded trajectories of sim.py
{ const r = A.rng(d.hull.seed); let w = 0;
  for (const tr of d.hull.trajectories) { const c = A.ejectHull(r, tr.slide_speed); for (let i = 0; i < 3 * 240 && c.resting !== 2; i++) A.stepHull(c, d.hull.step_dt, { groundY: tr.ground_y, surface: tr.surface }); w = Math.max(w, Math.hypot(c.pos[0] - tr.rest[0], c.pos[1] - tr.rest[1], c.pos[2] - tr.rest[2])); }
  ok(w < 1e-4, `seeded hull rest positions match sim.py within ${(w * 1e3).toFixed(3)} mm`);
  const c = A.ejectHull(A.rng(3), 1.0); ok(c.vel[0] < 0 && c.vel[1] > 0, 'the hull leaves to the right (-X) and upward'); }
console.log(fail ? fail + ' FAILED' : 'all checks passed'); process.exit(fail ? 1 : 0);
