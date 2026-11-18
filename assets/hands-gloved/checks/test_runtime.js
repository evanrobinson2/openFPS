// node checks/test_runtime.js : checks hands-gloved.js against the Python recipe (run after clips/make.py and checks/limits.py)
const H = require('../hands-gloved.js'); const fs = require('fs'); const path = require('path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'hands-gloved.json'), 'utf8')); H.use(d);
const ref = JSON.parse(fs.readFileSync(path.join(__dirname, 'fk_reference.json'), 'utf8'));
let fail = 0; const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
// 1. forward kinematics parity: fingertips of both hands in every frame of every clip
let worst = 0, n = 0;
for (const clip of H.clips) for (let f = 0; f < d.clips[clip].frames; f++) {
  const s = H.sample(clip, f / H.fps);
  for (const side of ['R', 'L']) ref.tips.forEach((t, k) => { const p = H.landmark(s[side], t), r = ref.clips[clip][side][f][k]; worst = Math.max(worst, Math.hypot(p[0] - r[0], p[1] - r[1], p[2] - r[2])); n++; });
}
ok(worst < 5e-6, 'fingertip positions match the Python recipe in every frame: worst ' + (worst * 1e6).toFixed(2) + ' micrometres over ' + n + ' points');
// 2. joint limits in every frame, and between frames
let bad = 0, m = 0; for (const clip of H.clips) for (let t = 0; t <= H.duration(clip) + 1e-9; t += 1 / (H.fps * 4)) { const s = H.sample(clip, t); bad += H.checkLimits(s.R.angles).length + H.checkLimits(s.L.angles).length; m += 46; }
ok(bad === 0, 'all 23 joint angles of both hands inside their limits at 4 samples per frame: ' + m + ' values, ' + bad + ' outside');
// 3. grips load and bones are rigid (orthonormal)
let orth = 0; for (const g of H.grips) { const p = H.grip(g); for (const b of H.bones) { const x = p.bones[b]; orth = Math.max(orth, Math.abs(x[0] * x[1] + x[4] * x[5] + x[8] * x[9]), Math.abs(x[0] * x[0] + x[4] * x[4] + x[8] * x[8] - 1)); } }
ok(orth < 1e-5, H.grips.length + ' grips: bone matrices orthonormal to ' + orth.toExponential(1));
// 4. sync with the rifle clips
for (const clip of H.clips) { const c = d.clips[clip]; if (!c.rifle_clip) continue;
  const a = H.sample(clip, (c.pre_roll - 0.5) / H.fps), b = H.sample(clip, c.pre_roll / H.fps), e = H.sample(clip, H.duration(clip));
  ok((c.pre_roll === 0 || a.rifleTime === null) && b.rifleTime === 0 && Math.abs(e.rifleFrame - c.rifle_frames) < 1e-9, clip + ': rifle clip ' + c.rifle_clip + ' starts at hand frame ' + (c.pre_roll + 1) + ' and has ended by the last hand frame'); }
// 5. continuity: no hand jumps between frames (wrist speed under 3 m/s)
let vmax = 0, where = ''; for (const clip of H.clips) { const c = d.clips[clip]; for (const s of ['R', 'L']) for (let f = 1; f < c.frames; f++) { const p = c[s][f].hand, q = c[s][f - 1].hand, v = Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) * H.fps; if (v > vmax) { vmax = v; where = clip + ' ' + s + ' frame ' + (f + 1); } } }
ok(vmax < 3.0, 'fastest wrist ' + vmax.toFixed(2) + ' m/s (' + where + ')');
// 6. mag_out ends where mag_in starts
{ const a = d.clips.mag_out.L[d.clips.mag_out.frames - 1].hand, b = d.clips.mag_in.L[0].hand; const dd = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); ok(dd < 1e-4, 'mag_out ends where mag_in starts: ' + (dd * 1e3).toFixed(3) + ' mm apart'); }
console.log(fail ? fail + ' FAILED' : 'all passed'); process.exit(fail ? 1 : 0);
