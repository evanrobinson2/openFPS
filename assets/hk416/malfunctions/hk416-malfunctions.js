/* HK416 D14.5RS malfunctions: stoppages, what the shooter sees, and the clearing procedures. No dependencies.
 * The same model as sim.py, function for function; malfunctions.json and procedures.json are its tables.
 *
 *   <script src="hk416-malfunctions.js"></script>            -> window.HK416Malfunctions
 *   const M = require('./hk416-malfunctions.js')              (Node)
 *
 *   await M.load('malfunctions.json', 'procedures.json')      // or M.use(malfunctionsJson, proceduresJson)
 *   const gun = M.create({ seed: 7, dust: 0.5, ammo: 'm855', magType: 'hk_steel', mode: 'range' })
 *   const r = gun.fire()            // { outcome, variant, stoppage, report, trigger, travelMm, ... }
 *   if (!gun.ready) {
 *     const what = gun.observe()    // what can be seen: { port, mag, handle, report, trigger }
 *     const pid  = gun.diagnose()   // the procedure for that picture, e.g. 'immediate_action'
 *     gun.act('tap'); gun.act('rack'); gun.act('reassess')      // or gun.step() one step at a time, gun.runProcedure(pid), or gun.clear()
 *   }
 *   const pose = gun.pose()         // { carrierMm, carrierZ, boltDeg, props: [{ prop, pos, axis }], ... } for the model
 *
 * Every run is reproducible: the generator is mulberry32 seeded by opts.seed (the same one as hk416-action.js).
 * Frame: metres, +Z muzzle, +Y up, +X shooter's left. Times are seconds; t = 0 of a shot is the trigger break.
 * This is education about stoppages and how to make a rifle safe. See README.md for sources and limits.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.HK416Malfunctions = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, R = null, P = null, TAB = null, AMMO = null, MAGS = null, STOP = null, OOB = null, PORT = null;

  function need() { if (!D) throw new Error('HK416Malfunctions: call use(malfunctions, procedures) or load(urls) first'); return D; }

  function use(data, procedures) {
    D = data; R = procedures || R; P = {}; var k;
    for (k in data.params) P[k] = data.params[k].value;
    TAB = data.action; AMMO = data.ammo; MAGS = data.magazines; PORT = data.stops.port;
    STOP = {}; for (k in data.stops.positions) STOP[k] = [data.stops.positions[k].carrier_mm, data.stops.positions[k].bolt_deg];
    OOB = [data.stops.out_of_battery.carrier_mm, data.stops.out_of_battery.bolt_deg];
    return api;
  }

  function readJson(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); });
    }
    return Promise.resolve(JSON.parse(require('fs').readFileSync(url, 'utf8')));
  }
  function load(malfunctionsUrl, proceduresUrl) {
    return Promise.all([readJson(malfunctionsUrl), readJson(proceduresUrl)]).then(function (a) { return use(a[0], a[1]); });
  }

  /* Seedable generator (mulberry32) returning floats in [0, 1). Same sequence as sim.py and hk416-action.js. */
  function rng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var z = s;
      z = Math.imul(z ^ (z >>> 15), z | 1) >>> 0;
      z = (z ^ (z + (Math.imul(z ^ (z >>> 7), z | 61) >>> 0))) >>> 0;
      return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
    };
  }

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function odds(ratio, k) { return ratio > 0 ? 1.0 / (1.0 + Math.pow(ratio, k)) : 1.0; }

  function newState(cfg) {
    var c = {}, k; need();
    for (k in D.defaults) c[k] = D.defaults[k];
    for (k in (cfg || {})) if (k !== 'seed') c[k] = cfg[k];
    return { cfg: c, clock: 0.0, shots: 0, nLube: 0, nClean: 0, heatK: 0.0, chamber: 'live', feedway: 'clear', bolt: 'closed', carrierMm: 0.0, hammer: 'cocked', bore: 'clear',
             selector: 'fire', status: 'ok', mag: { present: true, seated: !!c.magSeated, rounds: c.magRounds - 1, type: c.magType }, pending: null, last: null, lostRounds: 0 };
  }

  /* Dimensionless condition indices from the rifle state. */
  function conditions(st) {
    var cfg = st.cfg;
    var c = cfg.dust * (P.dust_residual + (1.0 - P.dust_residual) * Math.min(1.0, st.nLube / P.lube_interval));
    var f = Math.min(2.0, st.nClean / P.clean_interval);
    var cold = clamp((20.0 - cfg.ambientC) / (20.0 - P.cold_ref), 0.0, 1.0);
    var hot = clamp((cfg.ambientC - 20.0) / (P.hot_ref - 20.0), 0.0, 1.0);
    var heat = clamp(st.heatK / P.heat_ref, 0.0, 2.0);
    return { c: c, f: f, cold: cold, hot: hot, heat: heat, dry: cfg.dry ? 1.0 : 0.0 };
  }

  function indentEnergy(dMm) { var d = dMm * 1e-3; return P.primer_f0 * d + 0.5 * P.primer_k * d * d; }

  /* Every physical margin for the next shot, from the state. No randomness. */
  function margins(st) {
    var cfg = st.cfg, q = conditions(st), am = AMMO[cfg.ammo], mg = MAGS[st.mag.type];
    var e = P.hammer_energy * Math.max(0.05, 1.0 - P.eta_dust * q.c - P.eta_cold * q.cold - P.eta_foul * q.f);
    var prot = cfg.firingPinProtrusionMm;
    if (prot < P.indent_nominal) e *= indentEnergy(Math.max(prot, 0.0)) / indentEnergy(P.indent_nominal);
    var rFire = e / (P.primer_allfire * am.primer);
    var drive = am.drive * (1.0 - P.drive_cold * q.cold + P.drive_hot * q.hot) * (1.0 - P.drive_rings * cfg.pistonRingsWorn);
    var shift = TAB.ke_peak_J * (drive - 1.0);
    var drag = P.drag_dust * q.c + P.drag_foul * q.f + P.drag_dry * q.dry + P.drag_cold * q.cold;
    var gap = cfg.extractorGapMm, claw;
    if (gap > P.extractor_nogo) claw = Math.max(0.3, 1.0 - 0.7 * (gap - P.extractor_nogo) / 0.41);
    else if (gap < P.extractor_go) claw = 0.3;
    else claw = 1.0;
    claw *= 1.0 - 0.5 * cfg.extractorSpringWeak;
    var dragc = TAB.case_drag_N * am.stick * (1.0 + P.stick_dust * q.c + P.stick_foul * q.f + P.stick_heat * q.heat);
    var rExt = P.rim_strength * claw / dragc;
    var vfac = Math.max(0.05, 1.0 - P.slow_dust * q.c - P.slow_foul * q.f) * (1.0 - P.slow_ejector * cfg.ejectorWeak) * (1.0 - P.slow_extractor * cfg.extractorSpringWeak);
    var tClear = P.eject_clear_mm * 1e-3 / (TAB.eject_speed_mps * vfac);
    var n = st.mag.rounds;
    var spring = (P.mag_spring_f0 + P.mag_spring_per_round * n) * (1.0 - 0.5 * cfg.magSpringWear) - mg.friction * q.c;
    var tRise = Math.sqrt(2.0 * P.rise_mm * 1e-3 * (n * TAB.round_mass_kg + P.follower_mass) / Math.max(1.0, spring));
    var growth = Math.exp((P.feed_dust + mg.feed_dust_extra) * q.c);
    var pNose = Math.min(0.5, P.clean_scale * P.p_nose_clean * mg.nose * am.feed * growth * (1.0 + P.lip_nose * cfg.magLipDamage));
    var pTwo = Math.min(0.3, P.clean_scale * P.p_two_clean * mg.two * growth * (1.0 + P.lip_two * cfg.magLipDamage));
    var work = P.chamber_work * (1.0 + P.chamber_dust * q.c + P.chamber_foul * q.f);
    var close = TAB.ke_close_J * (1.0 - P.buffer_weak * cfg.bufferSpringWeak);
    return { q: q, r_fire: rFire, p_dud: am.p_dud, p_hang: am.p_hang, p_squib: am.p_squib, shift: shift, drag: drag, r_ext: rExt, claw: claw, t_clear: tClear,
             t_rise: tRise, p_nose: pNose, p_two: pTwo, work: work, close: close, n: n, feeds: !!(st.mag.present && n > 0), seated: !!st.mag.seated, mag_in: !!st.mag.present };
  }

  /* Carrier travel (mm) for an energy deviation e (J): where the shifted, dragged kinetic energy curve reaches zero. */
  function travel(M, e) {
    var xs = TAB.x_mm, ke = TAB.ke_out_J, xp = TAB.x_peak_mm, n = xs.length, i, k;
    var kLast = ke[n - 1] + M.shift + e - M.drag * (xs[n - 1] - xp) * 1e-3;
    if (kLast > 0) return TAB.x_full_mm;
    var prevX = xp, prevK = TAB.ke_peak_J + M.shift + e;
    if (prevK <= 0) return xp;
    for (i = 0; i < n; i++) {
      if (xs[i] <= xp) continue;
      k = ke[i] + M.shift + e - M.drag * (xs[i] - xp) * 1e-3;
      if (k <= 0) return prevX + (xs[i] - prevX) * prevK / (prevK - k);
      prevX = xs[i]; prevK = k;
    }
    return TAB.x_full_mm;
  }

  /* Ordered, mutually exclusive outcome probabilities of the cycle after a fired shot, given carrier travel xm: [[kind, variant, p], ...] */
  function cycleProbs(M, xm) {
    var full = TAB.x_full_mm, out = [], alive = 1.0, p, w, dwell;
    p = odds(M.r_ext, P.k_extract);
    var fedBehind = M.feeds && M.seated && xm >= TAB.x_pick_mm;
    out.push([fedBehind ? 'double_feed' : 'failure_to_extract', 'stuck', alive * p]); alive *= 1.0 - p;
    if (xm < TAB.x_eject_mm) { out.push(['stovepipe', 'rechambered_case', alive]); return out; }
    w = TAB.eject_window_s * Math.sqrt(Math.max(0.0, (xm - TAB.x_eject_mm) / (full - TAB.x_eject_mm)));
    p = odds(w / M.t_clear, P.k_eject);
    out.push(['stovepipe', 'eject', alive * p]); alive *= 1.0 - p;
    if (M.mag_in && M.n > 0) {
      if (xm < TAB.x_pick_mm || !M.seated) { out.push(['failure_to_feed', 'bolt_over_empty_chamber', alive]); return out; }
      dwell = TAB.feed_dwell_s * Math.sqrt(Math.max(0.0, (xm - TAB.x_pick_mm) / (full - TAB.x_pick_mm)));
      p = odds(dwell / M.t_rise, P.k_feed_time);
      out.push(['bolt_override', 'override', alive * p]); alive *= 1.0 - p;
      out.push(['failure_to_feed', 'nose_jam', alive * M.p_nose]); alive *= 1.0 - M.p_nose;
      out.push(['double_feed', 'two_live', alive * M.p_two]); alive *= 1.0 - M.p_two;
      p = odds(M.close * Math.min(1.0, xm / full) / M.work, P.k_chamber);
      out.push(['failure_to_feed', 'failure_to_chamber', alive * p]); alive *= 1.0 - p;
    } else if (M.mag_in) {
      p = xm < TAB.x_hold_mm ? 1.0 : P.p_catch;
      out.push(['failure_to_lock_back', 'closed_on_empty', alive * p]); alive *= 1.0 - p;
    }
    out.push(['fired', '', alive]);
    return out;
  }

  function fireProbs(M) {
    var pl = odds(M.r_fire, P.k_fire);
    return [['squib', M.p_squib], ['hangfire', M.p_hang], ['dud', M.p_dud], ['light_strike', (1.0 - M.p_squib - M.p_hang - M.p_dud) * pl]];
  }

  /* Analytic per-round probability of each first outcome for the next shot from this state (integrates the energy scatter). */
  function probabilities(st, grid) {
    grid = grid || 64;
    var M = margins(st), out = {}, pf = 0.0, i, b, fp = fireProbs(M), k, p, key;
    function add(kk, pp) { out[kk] = (out[kk] || 0.0) + pp; }
    for (i = 0; i < fp.length; i++) {
      k = fp[i][0]; p = fp[i][1]; pf += p;
      if (k === 'dud' || k === 'light_strike') add('failure_to_fire:' + k, p);
      else if (k === 'squib') add('squib:lodged', p);
    }
    var ph = M.p_hang, fired = 1.0 - pf + ph;
    add('hangfire:delayed', ph);
    var xs = TAB.x_mm, s = P.energy_scatter, xp = TAB.x_peak_mm;
    var cuts = [[TAB.x_eject_mm, TAB.ke_eject_J], [TAB.x_pick_mm, TAB.ke_pick_J], [TAB.x_hold_mm, TAB.ke_hold_J], [xs[xs.length - 1], TAB.ke_out_J[TAB.ke_out_J.length - 1]]];
    var ucut = [0.0];
    for (i = 0; i < 4; i++) ucut.push(1.0 / (1.0 + Math.exp((cuts[i][1] + M.shift - M.drag * (cuts[i][0] - xp) * 1e-3) / s)));
    var uFull = ucut[4], acc = {}, cp, j;
    cp = cycleProbs(M, TAB.x_full_mm);
    for (j = 0; j < cp.length; j++) { key = cp[j][0] + (cp[j][1] ? ':' + cp[j][1] : ''); acc[key] = (acc[key] || 0.0) + cp[j][2] * (1.0 - uFull); }
    var g = Math.max(2, Math.floor(grid / 4)), lo, hi, u, e;
    for (b = 0; b < 4; b++) {
      lo = ucut[b]; hi = ucut[b + 1];
      if (hi - lo < 1e-18) continue;
      for (i = 0; i < g; i++) {
        u = lo + (hi - lo) * (i + 0.5) / g; e = s * Math.log(u / (1.0 - u));
        cp = cycleProbs(M, travel(M, e));
        for (j = 0; j < cp.length; j++) { key = cp[j][0] + (cp[j][1] ? ':' + cp[j][1] : ''); acc[key] = (acc[key] || 0.0) + cp[j][2] * (hi - lo) / g; }
      }
    }
    for (key in acc) {
      if (key === 'fired') continue;
      p = acc[key];
      if (key === 'double_feed:stuck') key = 'double_feed:stuck_case_plus_round';
      else if (key === 'failure_to_extract:stuck') key = 'failure_to_extract:any';
      else if (key === 'stovepipe:eject') key = 'stovepipe:caught';
      add(key, fired * p);
    }
    out.fired = fired * (acc.fired || 0.0);
    return out;
  }

  /* ---------------------------------------------------------------- the rifle as a state machine */
  function ready(st) {
    return st.status === 'ok' && st.chamber === 'live' && st.bolt === 'closed' && st.feedway === 'clear' && st.bore === 'clear' && st.hammer === 'cocked' &&
      st.selector === 'fire' && st.pending === null;
  }

  /* What the shooter can see and feel, without opening anything. */
  function observe(st) {
    var port;
    if (st.feedway !== 'clear' && st.bolt !== 'held_open') port = PORT[st.feedway];
    else if (st.bolt === 'held_open') port = 'bolt_held_open';
    else if (st.bolt === 'out_of_battery') port = 'out_of_battery';
    else port = 'closed';
    var last = st.last || {};
    return { port: port, mag: st.mag.present ? 'in' : 'out', handle: st.feedway === 'round_over_bolt' ? 'bound' : 'free',
             report: last.report || 'none', trigger: last.trigger || 'none', selector: st.selector, ready: ready(st) };
  }

  /* The procedure a shooter should start from what is visible. attempts = immediate actions already tried on this stoppage. */
  function diagnose(st, attempts) {
    var o = observe(st), rules = R.diagnosis, i, k, ok, pr;
    attempts = attempts || 0;
    for (i = 0; i < rules.length; i++) {
      ok = true;
      for (k in rules[i].see) if (o[k] !== rules[i].see[k]) { ok = false; break; }
      if (ok) {
        pr = rules[i].procedure;
        if (pr === 'immediate_action') {
          if (attempts >= 2) return 'remedial_clear';
          if (st.cfg.mode === 'range' && attempts === 0 && o.trigger === 'click') return 'misfire_range';
        }
        return pr;
      }
    }
    return 'remedial_clear';
  }

  function heat(st, dt) { if (dt > 0) st.heatK *= Math.exp(-dt / P.heat_tau); }

  /* Let time pass; a pending hangfire fires if its time comes with the bolt still locked. Returns the cycle results of any such shot. */
  function advance(st, dt) {
    var ev = [], pd = st.pending, r;
    if (pd !== null && st.clock + dt >= pd.at) {
      heat(st, pd.at - st.clock); dt -= pd.at - st.clock; st.clock = pd.at; st.pending = null;
      r = cycle(st, pd.M, pd.ue, pd.uc, pd.ud);
      r.delayS = pd.delay; ev.push(r);
    }
    heat(st, dt); st.clock += dt;
    return ev;
  }

  function stop(st, feedway) { st.feedway = feedway; st.bolt = 'blocked'; st.carrierMm = STOP[feedway][0]; }

  /* The shot has fired: run the operating cycle and leave the rifle in the state it ends in. */
  function cycle(st, M, ue, uc, ud) {
    var s = P.energy_scatter, e = (ue > 0.0 && ue < 1.0) ? s * Math.log(ue / (1.0 - ue)) : 0.0;
    var xm = travel(M, e), i;
    st.shots += 1; st.nLube += 1; st.nClean += 1; st.heatK += P.heat_per_shot;
    st.hammer = xm >= TAB.x_cock_mm ? 'cocked' : 'down';
    var acc = 0.0, kind = 'fired', vr = '', base = 0.0, pk = 0.0, cp = cycleProbs(M, xm);
    for (i = 0; i < cp.length; i++) {
      if (uc < acc + cp[i][2]) { kind = cp[i][0]; vr = cp[i][1]; base = acc; pk = cp[i][2]; break; }
      acc += cp[i][2];
    }
    var frac = pk > 0 ? (uc - base) / pk : 0.0;
    var mag = st.mag, res = { outcome: kind, variant: vr, travelMm: Math.round(xm * 1000) / 1000, report: 'bang', trigger: 'bang', shortStroke: xm < TAB.x_full_mm };
    if (kind === 'fired') {
      if (M.mag_in && M.n > 0) { mag.rounds -= 1; st.chamber = 'live'; st.bolt = 'closed'; st.carrierMm = 0.0; }
      else if (M.mag_in) { st.chamber = 'empty'; st.bolt = 'held_open'; st.carrierMm = TAB.x_hold_mm; }
      else { st.chamber = 'empty'; st.bolt = 'closed'; st.carrierMm = 0.0; }
    } else if (vr === 'stuck') {
      var torn = frac < P.p_torn * Math.min(1.0, M.claw);
      st.chamber = torn ? 'stuck_torn' : 'stuck';
      if (kind === 'double_feed') { res.variant = 'stuck_case_plus_round'; mag.rounds -= 1; stop(st, 'round_behind_case'); }
      else {
        res.variant = torn ? 'torn_rim' : 'claw_slip';
        if (M.mag_in && M.n === 0 && xm >= TAB.x_hold_mm) { st.bolt = 'held_open'; st.carrierMm = TAB.x_hold_mm; }
        else { st.bolt = 'closed'; st.carrierMm = 0.0; }
      }
      res.rim = torn ? 'torn' : 'intact';
    } else if (kind === 'stovepipe') {
      if (vr === 'rechambered_case') { st.chamber = 'fired'; st.bolt = 'closed'; st.carrierMm = 0.0; }
      else {
        st.chamber = 'empty';
        if (frac < P.p_stove) { res.variant = 'stovepipe'; stop(st, 'stovepipe'); }
        else { res.variant = 'case_in_receiver'; stop(st, 'case_loose'); }
      }
    } else if (kind === 'failure_to_feed') {
      if (vr === 'bolt_over_empty_chamber') { st.chamber = 'empty'; st.bolt = 'closed'; st.carrierMm = 0.0; }
      else if (vr === 'nose_jam') { st.chamber = 'empty'; stop(st, 'nose_jam'); }
      else { mag.rounds -= 1; st.chamber = 'live'; st.bolt = 'out_of_battery'; st.carrierMm = OOB[0]; }
    } else if (kind === 'bolt_override') {
      st.chamber = 'empty'; mag.rounds -= 1; stop(st, 'round_over_bolt');
    } else if (kind === 'double_feed') {
      st.chamber = 'empty'; mag.rounds -= Math.min(2, mag.rounds); stop(st, 'two_rounds');
    } else if (kind === 'failure_to_lock_back') {
      st.chamber = 'empty'; st.bolt = 'closed'; st.carrierMm = 0.0;
    }
    res.stoppage = kind !== 'fired';
    st.last = { report: 'bang', trigger: 'bang' };
    return res;
  }

  /* One press of the trigger. Returns what happened; the state is left as the shooter finds it. */
  function fire(st, rnd, force) {
    if (st.status !== 'ok') return { outcome: 'out_of_service', stoppage: false, fired: false };
    if (st.selector === 'safe') return { outcome: 'on_safe', stoppage: false, fired: false };
    if (st.pending !== null) return { outcome: 'hangfire_pending', stoppage: false, fired: false };
    if (st.bolt !== 'closed' || st.hammer !== 'cocked') {
      st.last = { report: 'none', trigger: 'dead' };
      return { outcome: 'dead_trigger', stoppage: true, fired: false, report: 'none', trigger: 'dead' };
    }
    if (st.chamber !== 'live') {
      st.hammer = 'down'; st.last = { report: 'none', trigger: 'click' };
      return { outcome: 'click', variant: st.chamber, stoppage: true, fired: false, report: 'none', trigger: 'click' };
    }
    if (st.bore !== 'clear') {
      st.status = 'out_of_service'; st.last = { report: 'bang', trigger: 'bang' };
      return { outcome: 'fired_into_obstruction', stoppage: true, fired: true, report: 'bang',
               note: 'a round was fired behind a lodged bullet: the barrel is treated as destroyed and the rifle is out of service' };
    }
    var M = margins(st);
    var uf = rnd(), ue = rnd(), uc = rnd(), ud = rnd(), ux = rnd();
    if (force) { var cut = force.indexOf(':'); return forced(st, M, cut < 0 ? force : force.slice(0, cut), cut < 0 ? '' : force.slice(cut + 1), ue, ud, ux); }
    var kind = null, acc = 0.0, fp = fireProbs(M), i;
    for (i = 0; i < fp.length; i++) { if (uf < acc + fp[i][1]) { kind = fp[i][0]; break; } acc += fp[i][1]; }
    if (kind === 'squib') return squib(st, ud);
    if (kind === 'dud' || kind === 'light_strike') {
      st.hammer = 'down'; st.chamber = 'dud'; st.last = { report: 'none', trigger: 'click' };
      return { outcome: 'failure_to_fire', variant: kind, stoppage: true, fired: false, report: 'none', trigger: 'click' };
    }
    if (kind === 'hangfire') return hang(st, M, ue, uc, ud, ux, null);
    var r = cycle(st, M, ue, uc, ud); r.fired = true;
    return r;
  }

  function squib(st, ud) {
    st.hammer = 'down'; st.chamber = 'fired'; st.bore = 'obstructed'; st.shots += 1; st.nLube += 1; st.nClean += 1;
    st.last = { report: 'pop', trigger: 'pop' };
    return { outcome: 'squib', variant: 'lodged', stoppage: true, fired: false, report: 'pop', trigger: 'pop',
             lodgedMm: Math.round((P.squib_min_mm + (P.squib_max_mm - P.squib_min_mm) * ud) * 10) / 10 };
  }

  function hang(st, M, ue, uc, ud, ux, z) {
    if (z === null) z = Math.sqrt(-2.0 * Math.log(Math.max(ud, 1e-12))) * Math.cos(2.0 * Math.PI * ux);
    var delay = P.hang_median * Math.exp(P.hang_sigma * z);
    st.hammer = 'down'; st.last = { report: 'none', trigger: 'click' };
    st.pending = { at: st.clock + delay, delay: delay, M: M, ue: ue, uc: uc, ud: ud };
    var res = { outcome: 'hangfire', variant: 'delayed', stoppage: true, fired: false, delayS: delay, perceptible: delay >= P.hang_perceptible, report: 'none', trigger: 'click' };
    if (delay < P.hang_perceptible) {          /* too short to notice or act on: the shot simply goes */
      var ev = advance(st, delay); res.then = ev[0]; res.fired = true; res.stoppage = ev[0].stoppage;
    }
    return res;
  }

  /* Demonstration only: make the next shot produce a chosen stoppage. Uses the same state changes as the real path. */
  function forced(st, M, kind, vr, ue, ud, ux) {
    var r;
    if (kind === 'squib') return squib(st, ud);
    if (kind === 'failure_to_fire') {
      st.hammer = 'down'; st.chamber = 'dud'; st.last = { report: 'none', trigger: 'click' };
      return { outcome: kind, variant: vr || 'dud', stoppage: true, fired: false, report: 'none', trigger: 'click', forced: true };
    }
    if (kind === 'hangfire') { r = hang(st, M, ue, 0.999999, ud, ux, 1.0 + 1.5 * ud); r.forced = true; return r; }
    var full = TAB.x_full_mm, xm = full, want;
    if (kind === 'stovepipe' && vr === 'rechambered_case') xm = TAB.x_eject_mm - 5.0;
    if (kind === 'failure_to_feed' && vr === 'bolt_over_empty_chamber') xm = TAB.x_pick_mm - 3.0;
    if (kind === 'failure_to_lock_back') xm = TAB.x_hold_mm - 2.0;
    want = { failure_to_extract: ['failure_to_extract', 'stuck'], double_feed: ['double_feed', vr !== 'two_live' ? 'stuck' : 'two_live'], stovepipe: ['stovepipe', 'eject'],
             bolt_override: ['bolt_override', 'override'], failure_to_feed: ['failure_to_feed', vr || 'nose_jam'], failure_to_lock_back: ['failure_to_lock_back', 'closed_on_empty'] }[kind];
    if (!want) return { outcome: 'not_possible_now', stoppage: false, fired: false, note: 'unknown stoppage ' + kind };
    if (kind === 'stovepipe' && vr === 'rechambered_case') want = ['stovepipe', 'rechambered_case'];
    if (kind === 'failure_to_extract') { var M2 = {}, k; for (k in M) M2[k] = M[k]; M2.feeds = false; M = M2; }
    var acc = 0.0, uc = null, cp = cycleProbs(M, xm), i, fr;
    for (i = 0; i < cp.length; i++) {
      if (cp[i][0] === want[0] && cp[i][1] === want[1]) {
        fr = 0.5;
        if (vr === 'torn_rim') fr = 0.0;
        else if (vr === 'claw_slip' || vr === 'stuck_case_plus_round') fr = 0.99;
        else if (vr === 'stovepipe' || (kind === 'stovepipe' && !vr)) fr = 0.0;
        else if (vr === 'case_in_receiver') fr = 0.99;
        uc = acc + cp[i][2] * fr; break;
      }
      acc += cp[i][2];
    }
    if (uc === null) return { outcome: 'not_possible_now', stoppage: false, fired: false, note: 'this stoppage cannot arise from the present state (for example no round left to feed)' };
    var ue2;
    if (xm < full) {
      var lo = -40.0, hi = 0.0, mid;
      for (i = 0; i < 60; i++) { mid = 0.5 * (lo + hi); if (travel(M, mid) < xm) lo = mid; else hi = mid; }
      ue2 = 1.0 / (1.0 + Math.exp(-lo / P.energy_scatter));
    } else ue2 = travel(M, 0.0) >= full ? 0.5 : 0.999999;
    r = cycle(st, M, ue2, uc, ud); r.fired = true; r.forced = true;
    return r;
  }

  /* Carrier drawn fully to the rear by hand: what comes out. */
  function byHand(st, u1, u2, ev) {
    var mag = st.mag, fw = st.feedway;
    if (fw === 'stovepipe' || fw === 'case_loose') {
      if (u1 < P.rack_clears_port) { st.feedway = 'clear'; ev.push('case_out'); } else ev.push('case_still_trapped');
    } else if (fw === 'nose_jam') {
      if (!mag.present || u1 < P.rack_clears_nose) {
        st.feedway = 'clear'; ev.push('round_out'); st.lostRounds += 1;
        if (mag.present) mag.rounds = Math.max(0, mag.rounds - 1);
      } else ev.push('round_still_jammed');
    } else if (fw === 'round_behind_case' || fw === 'two_rounds') {
      if (mag.present) ev.push('rounds_pinned_magazine_must_come_out');
      else { st.feedway = 'clear'; ev.push('rounds_out'); st.lostRounds += fw === 'two_rounds' ? 2 : 1; }
    }
    if (st.feedway === 'clear') {
      var ch = st.chamber;
      if (ch === 'live') { st.chamber = 'empty'; ev.push('live_round_ejected'); st.lostRounds += 1; }
      else if (ch === 'dud') { st.chamber = 'empty'; ev.push('dud_ejected'); }
      else if (ch === 'fired') { st.chamber = 'empty'; ev.push('case_ejected'); }
      else if (ch === 'stuck') {
        if (u2 < P.rack_extracts) { st.chamber = 'empty'; ev.push('stuck_case_extracted'); } else ev.push('case_still_in_chamber');
      } else if (ch === 'stuck_torn') ev.push('case_still_in_chamber');
    }
    st.hammer = 'cocked';
  }

  /* The bolt goes forward under the buffer spring. */
  function close(st, ev) {
    var mag = st.mag;
    if (st.feedway !== 'clear') { st.bolt = 'blocked'; st.carrierMm = STOP[st.feedway][0]; ev.push('bolt_stopped'); return; }
    var feeds = mag.present && mag.seated && mag.rounds > 0;
    if (st.chamber === 'stuck' || st.chamber === 'stuck_torn') {
      if (feeds) { mag.rounds -= 1; stop(st, 'round_behind_case'); ev.push('round_driven_into_stuck_case'); }
      else if (mag.present && mag.rounds === 0) { st.bolt = 'held_open'; st.carrierMm = TAB.x_hold_mm; ev.push('bolt_locked_open'); }
      else { st.bolt = 'closed'; st.carrierMm = 0.0; ev.push('bolt_closed_on_case'); }
    } else if (st.chamber === 'empty') {
      if (feeds) { mag.rounds -= 1; st.chamber = 'live'; st.bolt = 'closed'; st.carrierMm = 0.0; ev.push('round_chambered'); }
      else if (mag.present && mag.seated && mag.rounds === 0) { st.bolt = 'held_open'; st.carrierMm = TAB.x_hold_mm; ev.push('bolt_locked_open'); }
      else { st.bolt = 'closed'; st.carrierMm = 0.0; ev.push('bolt_closed_on_empty_chamber'); }
    } else { st.bolt = 'closed'; st.carrierMm = 0.0; ev.push('bolt_closed'); }
  }

  /* One clearing action. Always draws two random numbers. Returns { action, ok, events, seconds }. */
  function act(st, name, rnd, args) {
    args = args || {};
    var A = R.actions[name], ev = [], ok = true, i;
    if (!A) throw new Error('HK416Malfunctions: unknown action ' + name);
    var u1 = rnd(), u2 = rnd();
    var secs = args.seconds !== undefined ? +args.seconds : A.time_s;
    if (st.status === 'out_of_service') return { action: name, ok: false, events: ['out_of_service'], seconds: 0.0 };
    var pd = st.pending;
    if (pd !== null && (name === 'rack' || name === 'lock_back') && st.clock < pd.at) {
      st.status = 'out_of_service'; st.pending = null;
      return { action: name, ok: false, events: ['hangfire_fired_with_the_action_open'], seconds: 0.0,
               note: 'the round fired while the bolt was being opened: the reason for waiting on a misfire. The simulation stops here' };
    }
    var fired = advance(st, secs);
    for (i = 0; i < fired.length; i++) ev.push('hangfire_fired' + (fired[i].stoppage ? ':' + fired[i].outcome : ''));
    var mag = st.mag, p, t;
    if (name === 'tap') { if (mag.present) mag.seated = true; else ok = false; }
    else if (name === 'rack') {
      if (st.feedway === 'round_over_bolt') { ok = false; ev.push('charging_handle_bound'); }
      else { byHand(st, u1, u2, ev); close(st, ev); }
    } else if (name === 'lock_back') {
      if (st.feedway === 'round_over_bolt') { ok = false; ev.push('charging_handle_bound'); }
      else { byHand(st, u1, u2, ev); st.bolt = 'held_open'; st.carrierMm = TAB.x_hold_mm; }
    } else if (name === 'release_bolt') {
      if (st.bolt !== 'held_open') ok = false; else close(st, ev);
    } else if (name === 'strip_mag') {
      if (mag.present) { mag.present = false; mag.seated = false; } else ok = false;
    } else if (name === 'insert_mag') {
      t = args.type !== undefined ? args.type : st.cfg.magType;
      st.mag = { present: true, seated: true, rounds: args.rounds !== undefined ? Math.floor(args.rounds) : MAGS[t].capacity, type: t };
    } else if (name === 'sweep_case') {
      if (st.feedway === 'stovepipe' || st.feedway === 'case_loose') { st.feedway = 'clear'; ev.push('case_out'); close(st, ev); } else ok = false;
    } else if (name === 'handle_strike' || name === 'hold_bolt_strike') {
      if (st.feedway !== 'round_over_bolt') ok = false;
      else {
        p = name === 'hold_bolt_strike' ? P.hold_strike_frees : (mag.present ? P.strike_frees_mag_in : P.strike_frees);
        if (u1 < p) { st.feedway = 'clear'; st.lostRounds += 1; ev.push('round_freed'); st.hammer = 'cocked'; close(st, ev); }
        else { ok = false; ev.push('round_still_wedged'); }
      }
    } else if (name === 'forward_assist') {
      if (st.bolt !== 'out_of_battery') ok = false;
      else if (u1 < P.assist_seats) { st.bolt = 'closed'; st.carrierMm = 0.0; ev.push('bolt_closed'); }
      else { ok = false; ev.push('bolt_did_not_close'); }
    } else if (name === 'safe') {
      if (st.hammer === 'cocked') st.selector = 'safe'; else { ok = false; ev.push('selector_will_not_turn_hammer_not_cocked'); }
    } else if (name === 'selector_fire') st.selector = 'fire';
    else if (name === 'inspect_chamber') {
      if (st.bolt !== 'held_open') ok = false; else { ev.push('chamber:' + st.chamber); ev.push('feedway:' + st.feedway); }
    } else if (name === 'check_bore') {
      if (st.bolt !== 'held_open' || st.chamber !== 'empty') ok = false; else ev.push('bore:' + st.bore);
    } else if (name === 'rod') {
      if (st.bolt !== 'held_open' || mag.present) ok = false;
      else {
        if (st.chamber === 'stuck' || st.chamber === 'stuck_torn') { st.chamber = 'empty'; ev.push('case_pushed_out'); }
        if (st.bore === 'obstructed') { st.bore = 'clear'; st.status = 'needs_inspection'; ev.push('bullet_driven_out_barrel_needs_inspection'); }
      }
    }
    return { action: name, ok: ok, events: ev, seconds: secs };
  }

  function cond(st, name) {
    if (name === 'mag_in') return st.mag.present;
    if (name === 'handle_bound') return st.feedway === 'round_over_bolt';
    if (name === 'bolt_open') return st.bolt === 'held_open';
    if (name === 'bolt_closed') return st.bolt !== 'held_open';
    return true;
  }

  /* Run one procedure's steps. Returns { procedure, steps, seconds, end, next }. */
  function runProcedure(st, pid, rnd) {
    var pr = R.procedures[pid], log = [], secs = 0.0, nxt = null, i, s, r, end;
    if (!pr) throw new Error('HK416Malfunctions: unknown procedure ' + pid);
    for (i = 0; i < pr.steps.length; i++) {
      s = pr.steps[i];
      if (s['if'] !== undefined && !cond(st, s['if'])) continue;
      r = act(st, s.action, rnd, s.args); log.push(r); secs += r.seconds;
      if (st.status === 'out_of_service') break;
      if (s.branch !== undefined && (st.chamber !== 'empty' || st.feedway !== 'clear')) { nxt = s.branch.chamber_not_clear; break; }
    }
    if (st.status !== 'ok') end = st.status;
    else if (pr.end === 'made_safe') end = 'made_safe';
    else if (ready(st)) end = 'ready';
    else end = 'not_cleared';
    return { procedure: pid, steps: log, seconds: secs, end: end, next: nxt };
  }

  /* Diagnose and clear until the rifle is ready, made safe, or out of the shooter's hands. klass: 1 cleared within 10 s, 2 longer, 3 armourer. */
  function clear(st, rnd, maxProcedures) {
    maxProcedures = maxProcedures || 8;
    var done = [], secs = 0.0, ia = 0, nxt = null, end = ready(st) ? 'ready' : 'not_cleared', pid, r;
    while (!ready(st) && done.length < maxProcedures) {
      pid = nxt || diagnose(st, ia);
      if (pid === 'immediate_action' || pid === 'misfire_range') ia += 1;
      r = runProcedure(st, pid, rnd); done.push(pid); secs += r.seconds; end = r.end; nxt = r.next;
      if (end === 'made_safe' || end === 'out_of_service' || end === 'needs_inspection') break;
      if (end === 'not_cleared' && nxt === null && pid !== 'immediate_action' && pid !== 'misfire_range' && pid !== 'reload') nxt = R.procedures[pid].fallback;
    }
    var armourer = end !== 'ready' || done.indexOf('stuck_case_rod') >= 0;
    return { procedures: done, seconds: secs, end: end, klass: armourer ? 3 : (secs <= 10.0 ? 1 : 2) };
  }

  function maintain(st, what) {
    if (what === 'wipe_lube' || what === 'clean') st.nLube = 0;
    if (what === 'clean') st.nClean = 0;
  }

  function carry(st, cfg) {
    var n = newState(cfg);
    n.shots = st.shots; n.nLube = st.nLube; n.nClean = st.nClean; n.heatK = st.heatK; n.clock = st.clock;
    return n;
  }

  /* Fire `rounds` rounds from one rifle, clearing every stoppage as a shooter would, maintained on the dust test's schedule.
   * opts: { shotDt: 2, cycle: 120, cycleRest: 600, lube: 600, clean: 1200 }. Returns counts by type, by class, and where they fell. */
  function runProtocol(seed, rounds, cfg, opts) {
    opts = opts || {};
    var shotDt = opts.shotDt !== undefined ? opts.shotDt : 2.0, cyc = opts.cycle || 120, rest = opts.cycleRest !== undefined ? opts.cycleRest : 600.0;
    var lube = opts.lube || 600, cleanN = opts.clean || 1200;
    var rnd = rng(seed), st = newState(cfg), cnt = {}, klass = { 1: 0, 2: 0, 3: 0 }, at = [], events = 0, replaced = 0, guard = 0, cl, r, n0, key, t, lastEmpty;
    while (st.shots < rounds && guard < rounds * 4) {
      guard += 1;
      if (!ready(st)) {
        cl = clear(st, rnd);
        if (cl.end !== 'ready') { st = carry(st, cfg); replaced += 1; }
        continue;
      }
      n0 = st.shots;
      r = fire(st, rnd);
      advance(st, shotDt);
      if (r.stoppage || !ready(st)) {
        key = r.outcome + (r.variant ? ':' + r.variant : '');
        if (r.outcome === 'hangfire' && r.then !== undefined) { t = r.then; key = t.stoppage ? t.outcome + (t.variant ? ':' + t.variant : '') : null; }
        lastEmpty = !r.stoppage && st.bolt === 'held_open' && st.chamber === 'empty';
        cl = clear(st, rnd);
        if (key !== null && !lastEmpty) { cnt[key] = (cnt[key] || 0) + 1; klass[cl.klass] += 1; at.push(st.shots); events += 1; }
        if (cl.end !== 'ready') { st = carry(st, cfg); replaced += 1; }
      }
      if (st.shots !== n0) {
        if (st.shots % cleanN === 0) maintain(st, 'clean');
        else if (st.shots % lube === 0) maintain(st, 'wipe_lube');
        if (st.shots % cyc === 0) advance(st, rest);
      }
    }
    return { seed: seed, rounds: st.shots, stoppages: events, counts: cnt, klass: klass, at: at, replaced: replaced, lostRounds: st.lostRounds };
  }

  /* The 2007 dust test briefing's category for an outcome key such as 'failure_to_feed:nose_jam'. */
  function edtCategory(key) {
    var cut = key.indexOf(':'), k = cut < 0 ? key : key.slice(0, cut), v = cut < 0 ? '' : key.slice(cut + 1);
    if (k === 'failure_to_feed') return v === 'failure_to_chamber' ? 'FTC' : 'FFD';
    if (k === 'bolt_override') return 'FFD';
    if (k === 'double_feed') return v === 'two_live' ? 'FFD' : 'FXT';
    if (k === 'failure_to_fire' || k === 'hangfire' || k === 'squib' || k === 'click') return 'FFR';
    if (k === 'failure_to_extract') return 'FXT';
    if (k === 'stovepipe') return 'FEJ';
    if (k === 'failure_to_lock_back') return 'FBR';
    return 'OTH';
  }

  /* ---------------------------------------------------------------- showing it on the model */
  function lerpTab(xs, ys, x) {
    var n = xs.length, i;
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    i = Math.floor(x - xs[0]); if (i > n - 2) i = n - 2;
    return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i]);
  }

  /* How the rifle looks now. Props are in the gun frame: pos is the base of the case or round, axis points to its mouth or nose. */
  function pose(st, lastResult) {
    var x = st.carrierMm, bolt = 0.0, props = [], k = null, vr = null, i, m, pr;
    if (st.bolt === 'blocked') bolt = STOP[st.feedway][1];
    else if (st.bolt === 'held_open') bolt = 22.5;
    else if (st.bolt === 'out_of_battery') bolt = OOB[1];
    if (st.feedway === 'nose_jam') { k = 'failure_to_feed'; vr = 'nose_jam'; }
    else if (st.feedway === 'stovepipe') { k = 'stovepipe'; vr = 'stovepipe'; }
    else if (st.feedway === 'case_loose') { k = 'stovepipe'; vr = 'case_in_receiver'; }
    else if (st.feedway === 'round_behind_case') { k = 'double_feed'; vr = 'stuck_case_plus_round'; }
    else if (st.feedway === 'two_rounds') { k = 'double_feed'; vr = 'two_live'; }
    else if (st.feedway === 'round_over_bolt') { k = 'bolt_override'; vr = null; }
    if (k) {
      m = D.malfunctions[k].shows.props;
      for (i = 0; i < m.length; i++) if (!m[i].variant || m[i].variant === vr) props.push({ prop: m[i].prop, pos: m[i].pos.slice(), axis: m[i].axis.slice(), note: m[i].note });
    } else if (st.chamber === 'stuck' || st.chamber === 'stuck_torn' || st.chamber === 'fired') {
      pr = D.malfunctions.failure_to_extract.shows.props[0]; props.push({ prop: pr.prop, pos: pr.pos.slice(), axis: pr.axis.slice(), note: pr.note });
    }
    if (st.bore === 'obstructed') {
      pr = D.malfunctions.squib.shows.props[0];
      props.push({ prop: pr.prop, pos: [pr.pos[0], pr.pos[1], pr.pos[2] + ((lastResult && lastResult.lodgedMm) || 100) * 1e-3], axis: pr.axis.slice(), note: pr.note });
    }
    return { carrierMm: x, carrierZ: -x * 1e-3, boltDeg: bolt, boltRot: bolt * Math.PI / 180, dustCoverOpen: st.shots > 0 || x > 0, magazineIn: st.mag.present,
             boltCatchUp: st.bolt === 'held_open', selector: st.selector, props: props, port: observe(st).port };
  }

  /* Carrier travel (mm) at time t (s after the trigger break) for a shot whose result is r, ending at the stop the state shows.
   * Full-stroke shots follow the action simulation's curve exactly (the table in malfunctions.json); a short stroke is that curve scaled. */
  function carrierAt(r, t, stopMm) {
    var xs = TAB.x_mm, full = TAB.x_full_mm, xm = (r && r.travelMm) || 0, sc, x, i, lo, hi, mid;
    if (!r || !r.travelMm) return 0.0;
    sc = xm / full; stopMm = stopMm || 0.0;
    if (t <= TAB.t_out_s[0]) return 0.0;
    if (t <= TAB.t_max_travel_s) {
      lo = 0; hi = xs.length - 1;
      if (t >= TAB.t_out_s[hi]) x = xs[hi] + (full - xs[hi]) * (t - TAB.t_out_s[hi]) / Math.max(1e-9, TAB.t_max_travel_s - TAB.t_out_s[hi]);
      else { while (hi - lo > 1) { mid = (lo + hi) >> 1; if (TAB.t_out_s[mid] <= t) lo = mid; else hi = mid; }
             x = xs[lo] + (t - TAB.t_out_s[lo]) / Math.max(1e-9, TAB.t_out_s[hi] - TAB.t_out_s[lo]); }
      return x * sc;
    }
    lo = 0; hi = xs.length - 1;
    if (t <= TAB.t_back_s[hi]) x = full - (full - xs[hi]) * (t - TAB.t_max_travel_s) / Math.max(1e-9, TAB.t_back_s[hi] - TAB.t_max_travel_s);
    else if (t >= TAB.t_back_s[0]) x = 0.0;
    else { while (hi - lo > 1) { mid = (lo + hi) >> 1; if (TAB.t_back_s[mid] >= t) lo = mid; else hi = mid; }
           x = xs[lo] + (TAB.t_back_s[lo] - t) / Math.max(1e-9, TAB.t_back_s[lo] - TAB.t_back_s[hi]); }
    x *= sc;
    return x < stopMm ? stopMm : x;
  }

  /* Seconds after the trigger break at which the carrier reaches its stop (for cutting the cycle sound), or null if it closed. */
  function stopTime(r, stopMm) {
    if (!r || !r.travelMm || !stopMm) return null;
    var sc = r.travelMm / TAB.x_full_mm;
    if (stopMm >= r.travelMm) return TAB.t_max_travel_s;
    return lerpTab(TAB.x_mm, TAB.t_back_s, stopMm / sc);
  }

  /* A clearing motion with its symbols resolved: ctx { x0, x1, z0, depth } in mm. Returns { fps, tracks: [{ node, chan, keys: [[frame, value]] }] }. */
  function motion(name, ctx) {
    var m = R.motions[name], out = [], i, j, tr, keys, v;
    if (!m) return null; ctx = ctx || {};
    for (i = 0; i < m.tracks.length; i++) {
      tr = m.tracks[i]; keys = [];
      for (j = 0; j < tr.keys.length; j++) {
        v = tr.keys[j][1];
        if (typeof v === 'string') { var neg = v.charAt(0) === '-', nm = neg ? v.slice(1) : v; v = (ctx[nm] || 0) * (neg ? -1 : 1); }
        keys.push([tr.keys[j][0], v]);
      }
      out.push({ node: tr.node, chan: tr.chan.slice(), keys: keys });
    }
    return { fps: m.fps, note: m.note, tracks: out };
  }

  /* Value of each track of a resolved motion at time t (s): { 'node.loc.L': mm, 'node.rot.Y': deg, ... } (linear between keys). */
  function sampleMotion(mo, t) {
    var f = 1 + t * mo.fps, out = {}, i, k, a, b, v;
    for (i = 0; i < mo.tracks.length; i++) {
      k = mo.tracks[i].keys; v = k[k.length - 1][1];
      if (f <= k[0][0]) v = k[0][1];
      else for (a = 0; a < k.length - 1; a++) { b = a + 1; if (f <= k[b][0]) { v = k[a][1] + (k[b][1] - k[a][1]) * (f - k[a][0]) / (k[b][0] - k[a][0]); break; } }
      out[mo.tracks[i].node + '.' + mo.tracks[i].chan.join('.')] = v;
    }
    return out;
  }

  /* ---------------------------------------------------------------- the object most pages use */
  function create(opts) {
    opts = opts || {}; need();
    var st = newState(opts), rnd = rng(opts.seed !== undefined ? opts.seed : 1), lastResult = null, attempts = 0, plan = null;
    var gun = {
      get state() { return st; },
      get ready() { return ready(st); },
      get last() { return lastResult; },
      /* one trigger press; opts.force = 'stovepipe', 'double_feed:two_live', ... makes that stoppage happen (for demonstrations) */
      fire: function (o) { lastResult = fire(st, rnd, o && o.force); attempts = 0; plan = null; return lastResult; },
      /* one step of the procedure the present picture calls for: { procedure, name, step, label, expect, result, ready } or null when ready */
      step: function () {
        if (ready(st) || st.status === 'out_of_service') { plan = null; return null; }
        if (!plan) {
          var pid = st.status === 'needs_inspection' ? null : diagnose(st, attempts);
          if (pid === null) return null;
          if (pid === 'immediate_action' || pid === 'misfire_range') attempts += 1;
          plan = { pid: pid, i: 0 };
        }
        var pr = R.procedures[plan.pid], s = null, r = null, info;
        while (plan.i < pr.steps.length) {
          s = pr.steps[plan.i++];
          if (s['if'] !== undefined && !cond(st, s['if'])) { s = null; continue; }
          r = act(st, s.action, rnd, s.args); break;
        }
        info = { procedure: plan.pid, name: pr.name, step: s ? s.action : null, label: s ? R.actions[s.action].label : null, expect: s ? s.expect : null, result: r, ready: ready(st) };
        if (s && s.branch !== undefined && (st.chamber !== 'empty' || st.feedway !== 'clear')) plan = { pid: s.branch.chamber_not_clear, i: 0 };
        else if (plan.i >= pr.steps.length) {
          var fb = (!ready(st) && st.status === 'ok' && plan.pid !== 'immediate_action' && plan.pid !== 'misfire_range' && plan.pid !== 'reload') ? pr.fallback : null;
          plan = fb ? { pid: fb, i: 0 } : null;
        }
        if (st.status !== 'ok') plan = null;
        return info;
      },
      /* let dt seconds pass (cooling; a pending hangfire may fire: its cycle results are returned) */
      advance: function (dt) { var ev = advance(st, dt); if (ev.length) lastResult = ev[ev.length - 1]; return ev; },
      act: function (name, args) { return act(st, name, rnd, args); },
      observe: function () { return observe(st); },
      diagnose: function () { return diagnose(st, attempts); },
      runProcedure: function (pid) { pid = pid || diagnose(st, attempts); if (pid === 'immediate_action' || pid === 'misfire_range') attempts += 1; return runProcedure(st, pid, rnd); },
      clear: function () { return clear(st, rnd); },
      maintain: function (what) { maintain(st, what); return gun; },
      set: function (cfg) { for (var k in cfg) st.cfg[k] = cfg[k]; return gun; },
      probabilities: function () { return probabilities(st); },
      margins: function () { return margins(st); },
      pose: function () { return pose(st, lastResult); },
      carrierAt: function (t) { return carrierAt(lastResult && (lastResult.then || lastResult), t, st.bolt === 'closed' ? 0 : st.carrierMm); },
      stopTime: function () { return stopTime(lastResult && (lastResult.then || lastResult), st.bolt === 'closed' ? 0 : st.carrierMm); },
      describe: function () { var k = lastResult && lastResult.outcome; return (k && D.malfunctions[k]) || null; },
      reset: function (o) { o = o || opts; st = newState(o); rnd = rng(o.seed !== undefined ? o.seed : 1); lastResult = null; attempts = 0; plan = null; return gun; }
    };
    return gun;
  }

  var api = {
    use: use, load: load, create: create, rng: rng, runProtocol: runProtocol, edtCategory: edtCategory, motion: motion, sampleMotion: sampleMotion,
    /* the functional core, for tests and for callers that keep their own state object */
    core: { newState: newState, conditions: conditions, margins: margins, travel: travel, cycleProbs: cycleProbs, fireProbs: fireProbs, probabilities: probabilities, ready: ready,
            observe: observe, diagnose: diagnose, advance: advance, fire: fire, act: act, runProcedure: runProcedure, clear: clear, maintain: maintain, pose: pose,
            carrierAt: carrierAt, stopTime: stopTime },
    get data() { return D; },
    get procedures() { return R; },
    get malfunctions() { return need().malfunctions; },
    get actions() { return R.actions; }
  };
  return api;
});
