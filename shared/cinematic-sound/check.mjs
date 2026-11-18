// Node checks for the cinematic sound (no Web Audio here; the bus is measured in the browser by measure.html).
//   node shared/cinematic-sound/check.mjs        -> writes compare/check.json, exits 1 on any failure
// 1. The simulation values each sound module copies from action/ and ballistics/ (CINE_SIM) still equal their sources.
// 2. The dry cinematic shot of every gun is finite, deterministic, and not a click before the bus; the size order holds.
// 3. Realistic raw synthesis is bit-identical to the merged commit (aa037ac) when its modules are unpacked in audio/_base/.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url'; import { createRequire } from 'node:module';
const HERE = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.resolve(HERE, '../..'), A = (p) => path.join(ROOT, 'assets', p), J = (p) => JSON.parse(fs.readFileSync(A(p), 'utf8')), require = createRequire(import.meta.url);
const CS = require('./cinematic-sound.js'), out = { checks: [], guns: {} }; let fails = 0;
const ok = (c, msg) => { out.checks.push({ ok: !!c, check: msg }); if (!c) fails++; console.log((c ? 'ok   ' : 'FAIL ') + msg); }, near = (a, b, tol) => Math.abs(a - b) <= tol * Math.max(1, Math.abs(b));
const fake = { createBuffer: (c, n, fs) => { const d = Array.from({ length: c }, () => new Float32Array(n)); return { getChannelData: (i) => d[i], length: n, duration: n / fs }; } };
const C0 = 343.2, subsonicAt = (rows, v) => { for (let i = 1; i < rows.length; i++) if (v(rows[i]) < C0) { const a = rows[i - 1], b = rows[i]; return a.range_m + (v(a) - C0) / (v(a) - v(b)) * (b.range_m - a.range_m); } return null; };

// ---- 1. copied simulation values
const HK = (await import(pathToFileURL(A('hk416/sound/hk416-sound.js')))).default, G44 = (await import(pathToFileURL(A('g44v/sound/g44v-sound.js')))).default, SG = require(A('shotgun-590/sound/shotgun590-sound.js'));
{ const act = J('hk416/action/action.json'), bal = J('hk416/ballistics/ballistics.json'), c = HK.CINE_SIM, m = act.params.m_bullet.value, t = bal.ammo.M855.table;
  ok(near(c.muzzle_energy_J, t[0].energy_j, 1e-3) && near(0.5 * m * t[0].velocity_mps ** 2, c.muzzle_energy_J, 2e-3), `hk416 muzzle energy ${c.muzzle_energy_J} J = ballistics table ${t[0].energy_j} J = m v^2 / 2`);
  ok(near(c.muzzle_velocity, t[0].velocity_mps, 1e-4) && near(c.barrel_mm, act.params.barrel_len.value * 1000, 1e-4), `hk416 muzzle velocity ${c.muzzle_velocity} m/s and barrel ${c.barrel_mm} mm = action.json and ballistics.json`);
  ok(subsonicAt(t, (r) => r.velocity_mps) === null && t[t.length - 1].range_m >= c.supersonic_to_m, `hk416 M855 still supersonic at ${t[t.length - 1].range_m} m (supersonic_to_m ${c.supersonic_to_m})`);
  const P = J('hk416/sound/params.json'), core = HK.makeCore(P), x = core.dry('shooter', 'single', false, ['blast']); let pk = 0; for (const v of x) pk = Math.max(pk, Math.abs(v));
  ok(near(20 * Math.log10(pk / 20e-6), c.bare_peak_db_ear, 2e-4), `hk416 bare peak at the ear ${(20 * Math.log10(pk / 20e-6)).toFixed(2)} dB (CINE_SIM ${c.bare_peak_db_ear})`); }
{ const act = J('g44v/action/action.json'), c = G44.CINE_SIM; for (const k of Object.keys(act.loads)) { const L = act.loads[k];
    ok(near(c[k].muzzle_energy_J, L.pistol.muzzle_energy_J, 1e-3) && near(c[k].muzzle_velocity, L.pistol.muzzle_velocity_mps, 1e-4) && near(c[k].gas_mass_g, L.guessed.charge_kg * 1000, 1e-6), `g44v ${k}: ${c[k].muzzle_energy_J} J, ${c[k].muzzle_velocity} m/s, ${c[k].gas_mass_g} g charge = action.json`);
    ok(L.pistol.muzzle_velocity_mps < C0, `g44v ${k} is subsonic from the pistol (no bullet crack)`); } }
{ const act = J('shotgun-590/action/action.json'), bal = J('shotgun-590/ballistics/ballistics.json'), c = SG.CINE_SIM; for (const k of ['buck00', 'slug']) {
    ok(near(c[k].muzzle_energy_J, bal.muzzle[k].energy_j, 1e-4) && near(c[k].muzzle_velocity, bal.muzzle[k].v, 1e-4) && near(c[k].bore_mm, act.params.bore_d.value * 1000, 1e-6) && near(c[k].barrel_mm, act.params.barrel_length.value * 1000, 1e-6), `shotgun-590 ${k}: ${c[k].muzzle_energy_J} J, ${c[k].muzzle_velocity} m/s, bore and barrel = action.json and ballistics.json`);
    const s = subsonicAt(bal.tables[k], (r) => r.v); ok(s !== null && Math.abs(s - c[k].supersonic_to_m) < 0.2, `shotgun-590 ${k} goes subsonic at ${s && s.toFixed(1)} m (supersonic_to_m ${c[k].supersonic_to_m})`); } }

// ---- 2. the dry cinematic shot of every gun
SG.use(J('shotgun-590/sound/params.json'));
const guns = { 'shotgun-590': [await SG.build(fake, { params: SG.data }), 'buck00', 'pump'], hk416: [await HK.build(fake, { params: J('hk416/sound/params.json') }), 'single', 'charge'], g44v: [await G44.build(fake, { data: J('g44v/sound/params.json') }), 'cci_standard_velocity', 'slide_rack'] };
for (const [id, [S, key, clip]] of Object.entries(guns)) {
  ok(S.mode === 'cinematic', `${id}: the default mode is cinematic`);
  const b = await S.shot(key), x = Float64Array.from(b.getChannelData(0)), m = CS.metrics(x, 48000), d = S.design(key), b2 = await S.shot(key, { seed: 0 }), r = await S.shot(key, { mode: 'realistic' });
  let fin = true; for (const v of x) if (!Number.isFinite(v)) fin = false; let same = b === b2;
  ok(fin && same, `${id}: dry cinematic shot is finite and cached (${x.length} samples)`);
  ok(m.share_0_2ms < 10 && m.peak_dbfs <= -0.99, `${id}: dry shot before the bus: ${m.share_0_2ms} % of the energy in the first 2 ms, peak ${m.peak_dbfs} dBFS`);
  const mb = await S.mech(clip); ok(mb.length > 1000, `${id}: cinematic mechanical clip '${clip}' (${mb.length} samples)`);
  ok(r !== b && r.length > 0, `${id}: mode 'realistic' returns the physical shot`);
  out.guns[id] = { design: Object.fromEntries(Object.entries(d).filter(([, v]) => typeof v === 'number').map(([k, v]) => [k, +v.toPrecision(4)])), sim: d.sim, dry_shot_before_bus: m };
}
const sz = (id) => out.guns[id].design.size, fe = (id) => out.guns[id].design.f_sub_end;
ok(sz('g44v') < sz('hk416') && sz('hk416') < sz('shotgun-590'), `size order: g44v ${sz('g44v')} < hk416 ${sz('hk416')} < shotgun-590 ${sz('shotgun-590')}`);
ok(fe('g44v') > fe('hk416') && fe('hk416') > fe('shotgun-590'), `thump pitch after one decay time: g44v ${fe('g44v')} Hz > hk416 ${fe('hk416')} Hz > shotgun-590 ${fe('shotgun-590')} Hz`);

// ---- 3. realistic raw synthesis against the merged commit
const BASE = path.join(HERE, 'audio', '_base', 'assets');
if (fs.existsSync(BASE)) {
  const same = (a, b) => { if (a.length !== b.length) return false; for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false; return true; };
  const oh = (await import(pathToFileURL(path.join(BASE, 'hk416/sound/hk416-sound.js')))).default, P = J('hk416/sound/params.json'), a = oh.makeCore(P), b = HK.makeCore(P); let n = 0, good = true;
  for (const p of ['shooter', 'bystander', 'downrange', 'front50']) for (const v of ['single', 'auto1s']) for (const f of [false, true]) { n++; good = good && same(a.dry(p, v, f), b.dry(p, v, f)); }
  for (const c of Object.keys(P.mech_clips)) { n++; good = good && same(a.mech(c), b.mech(c)); } for (const o of ['range_berm', 'hallway', 'indoor_range']) { n++; good = good && same(a.ir(o), b.ir(o)); } n++; good = good && same(a.hpd(), b.hpd());
  ok(good, `hk416 realistic: ${n} raw outputs (shots, mechanical clips, impulse responses, earmuff filter) bit-identical to aa037ac`);
  const og = (await import(pathToFileURL(path.join(BASE, 'g44v/sound/g44v-sound.js')))).default, Pg = J('g44v/sound/params.json'), ag = og.makeCore(Pg), bg = G44.makeCore(Pg); n = 0; good = true;
  for (const l of Object.keys(Pg.loads)) for (const p of Object.keys(Pg.perspectives)) for (const f of [false, true]) { n++; good = good && same(ag.dry(l, p, f), bg.dry(l, p, f)); }
  for (const c of Object.keys(Pg.clips)) { n++; good = good && same(ag.mech(c), bg.mech(c)); } for (const o of Object.keys(Pg.overlays)) { n++; good = good && same(ag.ir(o), bg.ir(o)); }
  ok(good, `g44v realistic: ${n} raw outputs bit-identical to aa037ac`);
  const os = require(path.join(BASE, 'shotgun-590/sound/shotgun590-sound.js')); os.use(J('shotgun-590/sound/params.json')); SG.use(J('shotgun-590/sound/params.json')); n = 0; good = true;   // require() gives the old module its own state
  for (const nm of os.names()) { n++; good = good && same(os.render(nm), SG.render(nm)); }
  ok(good && os !== SG, `shotgun-590 realistic: ${n} rendered sounds bit-identical to aa037ac`);
  for (const f of ['hk416/sound/params.json', 'g44v/sound/params.json', 'shotgun-590/sound/params.json']) ok(fs.readFileSync(A(f)).equals(fs.readFileSync(path.join(BASE, f))), `${f} is byte-identical to aa037ac`);
} else console.log('skip  realistic identity: unpack the merged commit first (README.md, "Realistic is unchanged")');
out.failed = fails; fs.mkdirSync(path.join(HERE, 'compare'), { recursive: true }); fs.writeFileSync(path.join(HERE, 'compare', 'check.json'), JSON.stringify(out, null, 1));
console.log(fails ? fails + ' FAILED' : 'all ok'); process.exit(fails ? 1 : 0);
