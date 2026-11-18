/* Generic QD 5.56 mm suppressor on the HK416 D14.5RS: runtime module. No dependencies, no three.js.
 *
 *   <script src="suppressor-qd-556.js"></script>             -> window.SuppressorQD556
 *   const SuppressorQD556 = require('./suppressor-qd-556.js')   (Node)
 *
 *   await SuppressorQD556.load('suppressor.json')            // or SuppressorQD556.use(parsedJson)
 *
 * Baked results (states 'first_round', 'subsequent', 'hot'):
 *   SuppressorQD556.levels(state)              peak levels, bare and suppressed, at the HK416 listeners
 *   SuppressorQD556.soundParams(hkParams, state)   a patched copy of assets/hk416/sound/params.json; pass it to
 *                                              HK416Sound.build(ctx, { params }) and use the sound module as usual
 *   SuppressorQD556.actionData(hkAction)       a copy of assets/hk416/action/action.json with the cycle, events, rate
 *                                              and recoil of the suppressed rifle; pass it to HK416Action.use()
 *   SuppressorQD556.flashInput(state)          per-phase scales, source offset and delay for a muzzle-flash model
 *   SuppressorQD556.heatString(shotTimes, T0)  bulk can temperature through a string of shots
 *   SuppressorQD556.sockets, .mass, .exitOffset
 *
 * Live simulation (the same model as sim/core.py; test.js checks the two against each other):
 *   const shot = SuppressorQD556.runShot({ t_wall: 450, o2: 0.2 })    // about 50 ms of CPU
 *   const ac   = SuppressorQD556.acoustics(shot)                      // pulse parameters per listener
 *   SuppressorQD556.soundParams(hkParams, ac)                          // the patch for that exact state
 *   SuppressorQD556.flashInput(shot)
 *
 * Time zero of a shot here is the bullet base leaving the barrel crown: data.hk416.exit_after_sear_s (9.49 ms)
 * after the trigger break on the HK416Action clock. Frame: metres, +Z down-range, +Y up, +X to the shooter's left,
 * origin at socket_mount (= the rifle's socket_muzzle). SI units throughout.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.SuppressorQD556 = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null;
  var PATM = 101325.0, T_AMB = 293.15, RA = 287.05, GA = 1.40, CVA = RA / (GA - 1.0), Y_O2 = 0.232;
  var RHO0 = PATM / (RA * T_AMB), FOUR_PI = 4.0 * Math.PI, C0 = 343.2, P_REF = 20e-6, SIGMA = 5.670374e-8;

  function need() { if (!D) throw new Error('SuppressorQD556: call use(data) or load(url) first'); return D; }
  function use(data) { D = data; return api; }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }

  /* Orifice flow function: mdot = Cd A p_up psi / sqrt(R T_up). Linear near pr = 1. */
  function psi(pr, g) {
    var pc = Math.pow(2.0 / (g + 1.0), g / (g - 1.0));
    if (pr <= pc) return Math.sqrt(g) * Math.pow(2.0 / (g + 1.0), (g + 1.0) / (2.0 * (g - 1.0)));
    if (pr > 0.97) return Math.sqrt(2.0 * g / (g - 1.0) * (Math.pow(0.97, 2.0 / g) - Math.pow(0.97, (g + 1.0) / g))) * (1.0 - pr) / 0.03;
    return Math.sqrt(2.0 * g / (g - 1.0) * (Math.pow(pr, 2.0 / g) - Math.pow(pr, (g + 1.0) / g)));
  }

  /* Piecewise-linear table, clamped at both ends. */
  function interp(ts, vs, t) {
    var n = ts.length;
    if (n === 0) return 0.0;
    if (t <= ts[0]) return vs[0];
    if (t >= ts[n - 1]) return vs[n - 1];
    var lo = 0, hi = n - 1, mid;
    while (hi - lo > 1) { mid = (lo + hi) >> 1; if (ts[mid] <= t) lo = mid; else hi = mid; }
    return vs[lo] + (vs[hi] - vs[lo]) * (t - ts[lo]) / (ts[hi] - ts[lo]);
  }

  function stepTime(phases, step) {
    var t0 = 0.0, s0 = 0, i, ns;
    for (i = 0; i < phases.length; i++) {
      ns = Math.round((phases[i][0] - t0) / phases[i][1]);
      if (step <= s0 + ns) return t0 + (step - s0) * phases[i][1];
      s0 += ns; t0 = phases[i][0];
    }
    return t0;
  }
  function opt(o, k, d) { return o[k] !== undefined && o[k] !== null ? o[k] : d; }

  /* One shot. o: { t_wall (K), o2 (0..1), bare (bool), breech ('suppressed' | 'bare' | {t, area} | null),
   * t_end, t1, dt1, dt2, rec_every1, rec_every2 }. Port of core.run_shot. */
  function runShot(o) {
    o = o || {};
    var cfg = need().config, gas = cfg.gas, RG = gas.R, GG = gas.gamma, ETA = gas.covolume, CVG = RG / (GG - 1.0);
    var bore = cfg.bore, bul = cfg.bullet, mod = cfg.model, ch = cfg.chambers;
    var bare = !!o.bare, N = bare ? 0 : ch.volume_m3.length, n = N + 1, k, i, j, a;
    var V = [bore.V], AW = [0.0], AP = [bore.area], XA = [0.0], WEB = [0.0], ALPHA = [0.0], CD = [mod.cd_muzzle];
    for (k = 0; k < N; k++) { V.push(ch.volume_m3[k]); AW.push(ch.wall_area_m2[k]); AP.push(ch.aperture_area_m2[k]); XA.push(ch.aperture_from_crown_m[k]); WEB.push(ch.web_t_m[k]); ALPHA.push(ch.carry_over[k]); CD.push(mod.cd_aperture); }
    var t_wall = opt(o, 't_wall', T_AMB), o2 = opt(o, 'o2', 1.0);
    var br = o.breech === undefined ? (cfg.breech ? cfg.breech[bare ? 'bare' : 'suppressed'] : null) : (typeof o.breech === 'string' ? cfg.breech[o.breech] : o.breech);
    var ST = mod.stanton, HFREE = mod.h_free, AREF = mod.a_ref, TIGN = mod.t_ign, TAUC = mod.tau_burn, QO2 = mod.q_o2;
    var TAUAC = mod.tau_ac, RAMP = bul.ramp_m, VB = bul.v, LB = bul.length, ABUL = Math.PI * bul.radius * bul.radius, CDB = mod.cd_breech;

    var iMG = 0, iMA = n, iMO = 2 * n, iE = 3 * n, iQF = 4 * n, iFF = 4 * n + 1, iQW = 4 * n + 2;
    var iIMP = 5 * n + 2, iMOUT = iIMP + 1, iHOUT = iIMP + 2, iMBR = iIMP + 3, iO2B = iIMP + 4, iEK = iIMP + 5, NY = iIMP + 6;
    var y = new Float64Array(NY);
    y[iMG] = bore.m; y[iE] = bore.m * CVG * bore.T;
    for (k = 1; k < n; k++) {
      var ma0 = o2 * PATM * V[k] / (RA * t_wall), mg0 = (1.0 - o2) * PATM * V[k] / (RG * t_wall);
      y[iMA + k] = ma0; y[iMO + k] = Y_O2 * ma0; y[iMG + k] = mg0; y[iE + k] = (ma0 * CVA + mg0 * CVG) * t_wall;
    }
    var aux = new Float64Array(12), stp = new Float64Array(n), stT = new Float64Array(n), stR = new Float64Array(n), stcv = new Float64Array(n), sth = new Float64Array(n);
    var flow = new Float64Array(n), gate = new Float64Array(n + 1), fin = new Float64Array(n + 1), fout = new Float64Array(n + 1);

    function rhs(t, y, d) {
      var i, k, j, mg, ma, m, cv, R, T, p, xb, xo, a, s_, u, pu, pd, A, g, f, yg, ya, yo, h, rem, part, cp, T0, pr, Te, ue, pc, mbr, ab, burn, G, q, mo, r;
      for (i = 0; i < NY; i++) d[i] = 0.0;
      for (k = 0; k < n; k++) {
        mg = y[iMG + k]; ma = y[iMA + k]; m = mg + ma;
        cv = (mg * CVG + ma * CVA) / m; R = (mg * RG + ma * RA) / m;
        T = y[iE + k] / (m * cv); p = m * R * T / (V[k] - ETA * mg);
        stp[k] = p; stT[k] = T; stR[k] = R; stcv[k] = cv; sth[k] = cv * T + p * V[k] / m;
      }
      xb = VB * t;
      for (j = 1; j < n; j++) {
        xo = XA[j] + WEB[j];
        if (xb + LB < XA[j]) { a = 1.0; s_ = 0.0; }
        else if (xb < xo) { a = 1.0 - ABUL / AP[j]; s_ = 0.0; }
        else { u = (xb - xo) / RAMP; if (u > 1.0) u = 1.0; a = 1.0 - (1.0 - u) * ABUL / AP[j]; s_ = u; }
        flow[j] = a; gate[j] = ALPHA[j] * s_;
      }
      gate[n] = 0.0;
      for (k = 0; k < n + 1; k++) { fin[k] = 0.0; fout[k] = 0.0; }
      var q_exit = 0.0, m_exit = 0.0, h_exit = 0.0, thrust = 0.0, ek = 0.0;
      for (j = 0; j < n; j++) {
        pu = stp[j];
        if (j + 1 < n) pd = stp[j + 1]; else pd = PATM;
        A = CD[j] * AP[j] * (j > 0 ? flow[j] : 1.0);
        if (pu >= pd) {
          g = 1.0 + stR[j] / stcv[j];
          f = A * pu * psi(pd / pu, g) / Math.sqrt(stR[j] * stT[j]);
          m = y[iMG + j] + y[iMA + j];
          yg = y[iMG + j] / m; ya = y[iMA + j] / m; yo = y[iMO + j] / m; h = sth[j];
          d[iMG + j] -= f * yg; d[iMA + j] -= f * ya; d[iMO + j] -= f * yo; d[iE + j] -= f * h; fout[j] += f;
          rem = f;
          for (k = j + 1; k < n; k++) {
            part = rem * (1.0 - gate[k]); rem -= part; fin[k] += part;
            d[iMG + k] += part * yg; d[iMA + k] += part * ya; d[iMO + k] += part * yo; d[iE + k] += part * h;
          }
          if (rem > 0.0) {
            cp = stcv[j] + stR[j]; T0 = stT[j]; pr = PATM / pu;
            if (pr > 1.0) pr = 1.0;
            Te = T0 * Math.pow(pr, (g - 1.0) / g);
            ue = Math.sqrt(2.0 * cp * (T0 - Te));
            q_exit += rem * stR[j] * Te / PATM; m_exit += rem; h_exit += rem * h; ek += 0.5 * rem * ue * ue;
            pc = Math.pow(2.0 / (g + 1.0), g / (g - 1.0));
            if (j === n - 1 && pr <= pc) thrust += rem * Math.sqrt(g * stR[j] * T0 * 2.0 / (g + 1.0)) + (pu * pc - PATM) * A;
            else thrust += rem * ue;
          }
        } else {
          if (j + 1 < n) {
            k = j + 1; g = 1.0 + stR[k] / stcv[k];
            f = A * pd * psi(pu / pd, g) / Math.sqrt(stR[k] * stT[k]);
            m = y[iMG + k] + y[iMA + k];
            yg = y[iMG + k] / m; ya = y[iMA + k] / m; yo = y[iMO + k] / m; h = sth[k];
            d[iMG + k] -= f * yg; d[iMA + k] -= f * ya; d[iMO + k] -= f * yo; d[iE + k] -= f * h; fout[k] += f;
          } else {
            f = A * pd * psi(pu / pd, GA) / Math.sqrt(RA * T_AMB);
            yg = 0.0; ya = 1.0; yo = Y_O2; h = (CVA + RA) * T_AMB;
            q_exit -= f * RA * T_AMB / PATM; m_exit -= f;
          }
          d[iMG + j] += f * yg; d[iMA + j] += f * ya; d[iMO + j] += f * yo; d[iE + j] += f * h; fin[j] += f;
        }
      }
      mbr = 0.0;
      if (br) {
        ab = interp(br.t, br.area, t);
        if (ab > 0.0 && stp[0] > PATM) {
          g = 1.0 + stR[0] / stcv[0];
          mbr = CDB * ab * stp[0] * psi(PATM / stp[0], g) / Math.sqrt(stR[0] * stT[0]);
          m = y[iMG] + y[iMA];
          d[iMG] -= mbr * y[iMG] / m; d[iMA] -= mbr * y[iMA] / m; d[iMO] -= mbr * y[iMO] / m; d[iE] -= mbr * sth[0];
        }
      }
      burn = 0.0;
      for (k = 1; k < n; k++) {
        G = (fin[k] > fout[k] ? fin[k] : fout[k]) / AREF;
        T = stT[k];
        q = (ST * (stcv[k] + stR[k]) * G + HFREE) * AW[k] * (T - t_wall);
        d[iQW + k - 1] = q; d[iE + k] -= q;
        mo = y[iMO + k];
        if (mo > 1e-12 && T > TIGN && y[iMG + k] > 2.0 * mo) { r = mo / TAUC; d[iMO + k] -= r; d[iE + k] += r * QO2; burn += r; }
      }
      d[iQF] = (q_exit - y[iQF]) / TAUAC; d[iFF] = (thrust - y[iFF]) / TAUAC;
      d[iIMP] = thrust; d[iMOUT] = m_exit; d[iHOUT] = h_exit; d[iMBR] = mbr; d[iO2B] = burn; d[iEK] = ek;
      aux[0] = q_exit; aux[1] = m_exit; aux[2] = thrust; aux[3] = h_exit; aux[4] = ek;
      aux[5] = RHO0 * (q_exit - y[iQF]) / (TAUAC * FOUR_PI);
      aux[6] = mbr; aux[7] = burn;
      aux[8] = (thrust - y[iFF]) / (C0 * TAUAC * FOUR_PI);
    }

    var k1 = new Float64Array(NY), k2 = new Float64Array(NY), k3 = new Float64Array(NY), k4 = new Float64Array(NY), yt = new Float64Array(NY);
    var COS = cfg.listen.dip, na = COS.length;
    var rec = { t: [], p_bore: [], T_bore: [], p: [], T: [], q_exit: [], m_exit: [], thrust: [], mono: [], dip: [], qf: [], ff: [], m_breech: [], ek: [], h_exit: [] };
    var pkP = new Array(na).fill(0.0), pkT = new Array(na).fill(0.0), pkN = new Array(na).fill(0.0);
    var pk_q = 0.0, pk_m = 0.0, pk_h = 0.0, pk_ek = 0.0, pk_th = 0.0, t_ek = 0.0, pk_p = new Array(n).fill(0.0), pk_T = new Array(n).fill(0.0);
    var t = 0.0, step = 0, v, ph, nsteps, s, dt, every, t_end;
    var phases = [[opt(o, 't1', 4e-3), opt(o, 'dt1', 2e-7), opt(o, 'rec_every1', 5)], [opt(o, 't_end', 40e-3), opt(o, 'dt2', 2e-6), opt(o, 'rec_every2', 25)]];
    for (ph = 0; ph < 2; ph++) {
      t_end = phases[ph][0]; dt = phases[ph][1]; every = phases[ph][2];
      nsteps = Math.round((t_end - t) / dt);
      for (s = 0; s < nsteps; s++) {
        rhs(t, y, k1);
        for (a = 0; a < na; a++) {
          v = aux[5] + COS[a] * aux[8];
          if (v > pkP[a]) { pkP[a] = v; pkT[a] = t; }
          if (v < pkN[a]) pkN[a] = v;
        }
        if (aux[0] > pk_q) pk_q = aux[0];
        if (aux[1] > pk_m) pk_m = aux[1];
        if (aux[3] > pk_h) pk_h = aux[3];
        if (aux[4] > pk_ek) { pk_ek = aux[4]; t_ek = t; }
        if (aux[2] > pk_th) pk_th = aux[2];
        for (k = 0; k < n; k++) { if (stp[k] > pk_p[k]) pk_p[k] = stp[k]; if (stT[k] > pk_T[k]) pk_T[k] = stT[k]; }
        if (step % every === 0) {
          rec.t.push(t); rec.p_bore.push(stp[0]); rec.T_bore.push(stT[0]);
          rec.p.push(Array.from(stp.subarray(1))); rec.T.push(Array.from(stT.subarray(1)));
          rec.q_exit.push(aux[0]); rec.m_exit.push(aux[1]); rec.thrust.push(aux[2]); rec.h_exit.push(aux[3]);
          rec.mono.push(aux[5]); rec.dip.push(aux[8]); rec.qf.push(y[iQF]); rec.ff.push(y[iFF]);
          rec.m_breech.push(aux[6]); rec.ek.push(aux[4]);
        }
        for (i = 0; i < NY; i++) yt[i] = y[i] + 0.5 * dt * k1[i];
        rhs(t + 0.5 * dt, yt, k2);
        for (i = 0; i < NY; i++) yt[i] = y[i] + 0.5 * dt * k2[i];
        rhs(t + 0.5 * dt, yt, k3);
        for (i = 0; i < NY; i++) yt[i] = y[i] + dt * k3[i];
        rhs(t + dt, yt, k4);
        for (i = 0; i < NY; i++) y[i] = y[i] + dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]);
        for (k = 0; k < n; k++) if (y[iMO + k] < 0.0) y[iMO + k] = 0.0;
        step += 1; t = stepTime(phases, step);
      }
    }
    rhs(t, y, k1);
    var heat = [], ht = 0.0, eg = [], ea = [];
    for (k = 0; k < N; k++) heat.push(y[iQW + k]);
    for (k = 0; k < N; k++) ht += heat[k];
    for (k = 0; k < n; k++) { eg.push(y[iMG + k]); ea.push(y[iMA + k]); }
    return {
      n_chambers: N, t_end: t, t_wall: t_wall, o2: o2,
      peak_p1m_Pa: pkP, t_peak_p1m: pkT, neg_p1m_Pa: pkN,
      peak_q_m3s: pk_q, peak_mdot_exit: pk_m, peak_hdot_exit: pk_h, peak_ekdot_exit: pk_ek, t_peak_ekdot: t_ek, peak_thrust_N: pk_th,
      peak_p_Pa: pk_p, peak_T_K: pk_T,
      impulse_Ns: y[iIMP], mass_out_kg: y[iMOUT], enthalpy_out_J: y[iHOUT], kinetic_out_J: y[iEK], mass_breech_kg: y[iMBR], o2_burnt_kg: y[iO2B],
      heat_wall_J: heat, heat_total_J: ht,
      end_p_Pa: Array.from(stp), end_T_K: Array.from(stT), end_gas_kg: eg, end_air_kg: ea,
      rec: rec
    };
  }

  function db(p) { return 20.0 * Math.log10((p > 1e-12 ? p : 1e-12) / P_REF); }

  /* Pulse parameters at 1 m for each listener direction. Port of core.acoustics. */
  function acoustics(shot) {
    var cfg = need().config, COS = cfg.listen.dip, tau = cfg.model.tau_ac, rec = shot.rec, nt = rec.t.length, out = [], a, i;
    for (a = 0; a < COS.length; a++) {
      var c = COS[a], P = shot.peak_p1m_Pa[a], tp = shot.t_peak_p1m[a], t1 = tp + 3.0 * tau;
      var i_pop = (RHO0 * interp(rec.t, rec.qf, t1) + c * interp(rec.t, rec.ff, t1) / C0) / FOUR_PI;
      var t2 = tp + 5.0 * tau, ph = 0.0, th = t2, i_max = i_pop, ti, imp, v;
      for (i = 0; i < nt; i++) {
        ti = rec.t[i];
        imp = (RHO0 * rec.qf[i] + c * rec.ff[i] / C0) / FOUR_PI;
        if (imp > i_max) i_max = imp;
        if (ti > t2) { v = rec.mono[i] + c * rec.dip[i]; if (v > ph) { ph = v; th = ti; } }
      }
      var T_pop = P > 0.0 ? Math.E * i_pop / P : 0.0;
      if (T_pop < 2e-5) T_pop = 2e-5;
      var T_hump = ph > 0.0 ? Math.E * (i_max - i_pop) / ph : 0.0;
      if (T_hump < 1e-4) T_hump = 1e-4;
      if (T_hump > 3e-3) T_hump = 3e-3;
      out.push({ name: cfg.listen.names[a], cos: cfg.listen.cos[a], pop_P1m: P, pop_dB1m: db(P), pop_T: T_pop, t_pop: tp, hump_P1m: ph, hump_T: T_hump, hump_dt: th - tp, impulse_pos_Pa_s: i_max });
    }
    var pk = shot.peak_ekdot_exit, t_e = shot.t_peak_ekdot, lim = pk / (Math.E * Math.E), tj = rec.t[nt - 1];
    for (i = 0; i < nt; i++) if (rec.t[i] > t_e && rec.ek[i] < lim) { tj = rec.t[i]; break; }
    return { listeners: out, jet_power_W: pk, jet_tau_s: tj - t_e, t_uncork_s: out[0].t_pop };
  }

  function copy(x) {
    if (Array.isArray(x)) return x.map(copy);
    if (x && typeof x === 'object') { var o = {}; for (var k in x) o[k] = copy(x[k]); return o; }
    return x;
  }

  /* Port of core.sound_overlay. ac: acoustics() result; bareJet: { jet_power_W, jet_tau_s }; mech: time ratios. */
  function soundOverlay(params, ac, bareJet, mech) {
    var cfg = need().config, P = copy(params), L = cfg.listen, dz = cfg.exit_offset_m, a, i;
    var k_rms = Math.sqrt(ac.jet_power_W / bareJet.jet_power_W), k_tau = ac.jet_tau_s / bareJet.jet_tau_s;
    for (a = 0; a < L.names.length; a++) {
      var nm = L.names[a];
      if (!(nm in P.persp)) continue;
      var pp = P.persp[nm], A = ac.listeners[a], keys = ['free', 'field'];
      for (var q = 0; q < 2; q++) {
        var key = keys[q], bl = pp.blast[key];
        if (bl.length === 0) continue;
        var r0 = bl[0].r, r1 = r0 - dz * A.cos, dt = (r1 - r0) / C0;
        var ratio = (A.pop_P1m / r1) / bl[0].P, hratio = (A.hump_P1m / r1) / bl[0].P, sec = [];
        for (i = 0; i < bl.length; i++) {
          var e = bl[i], h = Object.assign({}, e);
          h.P = e.P * hratio; h.T = A.hump_T; h.t = e.t + dt + A.hump_dt;
          if ('r' in h) delete h.r;
          sec.push(h);
          e.P = e.P * ratio; e.T = A.pop_T; e.t = e.t + dt;
          if ('bm' in e) e.bm = e.bm * ratio;                 // HK416 sound v2: the gas-volume body of the blast follows the pop (the swell is the 'sec' entry)
          if ('r' in e) e.r = e.r + (r1 - r0);
        }
        pp.sec[key] = sec;
        var jl = pp.jet[key];
        for (i = 0; i < jl.length; i++) {
          if ('g' in jl[i]) jl[i].g = jl[i].g * k_rms * (r0 / r1);   // HK416 sound v2: a gain on the shared jet envelope (its length is not changed)
          else { jl[i].rms = jl[i].rms * k_rms * (r0 / r1); jl[i].tau = jl[i].tau * k_tau; }
          jl[i].t = jl[i].t + dt;
        }
      }
    }
    if (mech) {
      for (i = 0; i < P.cycle.length; i++) if (P.cycle[i][0] in mech && P.cycle[i][1] > 0.0) P.cycle[i][1] = P.cycle[i][1] * mech[P.cycle[i][0]];
      if ('cycle' in P.mech_clips) { var mc = P.mech_clips.cycle; for (i = 0; i < mc.length; i++) if (mc[i][0] in mech && mc[i][1] > 0.0) mc[i][1] = mc[i][1] * mech[mc[i][0]]; }
      var pr = 'period_ratio' in mech ? mech.period_ratio : 1.0;
      P.cycle_s = P.cycle_s * pr;
      for (var v in P.variants) if (v.indexOf('auto') === 0) { var tt = P.variants[v].times; for (i = 0; i < tt.length; i++) tt[i] = tt[i] * pr; }
    }
    P.suppressor = { asset: 'suppressor-qd-556', exit_offset_m: dz };
    return P;
  }

  /* The patched HK416 sound tables. state: 'first_round' | 'subsequent' | 'hot', or an acoustics() result of a live shot. */
  function soundParams(hkParams, state, o) {
    var d = need(), ac = typeof state === 'object' && state ? state : d.sound[state || 'subsequent'];
    if (!ac) throw new Error('SuppressorQD556: unknown state ' + state);
    return soundOverlay(hkParams, ac, d.config.bare_ref, o && o.mech === false ? null : d.config.mech);
  }

  /* Port of core.flash_input. With a state name, the baked result. */
  function flashInput(shot, bare) {
    var d = need(), cfg = d.config, mod = cfg.model;
    if (shot === undefined || typeof shot === 'string') return d.flash[shot || 'subsequent'];
    bare = bare || cfg.bare_ref;
    var T0s = shot.peak_hdot_exit / shot.peak_mdot_exit / cfg.gas.cp, T0b = bare.peak_hdot_exit / bare.peak_mdot_exit / cfg.gas.cp;
    var glow = (shot.peak_mdot_exit / bare.peak_mdot_exit) * Math.pow(T0s / T0b, 4);
    var cpa = CVA + RA, cpg = cfg.gas.cp, r = mod.flash_mix_ratio;
    var Tmix_s = (cpg * T0s + r * cpa * T_AMB) / (cpg + r * cpa), Tmix_b = (cpg * T0b + r * cpa * T_AMB) / (cpg + r * cpa);
    var ps = 1.0 / (1.0 + Math.exp(-(Tmix_s - mod.flash_t_ign) / mod.flash_t_width)), pb = 1.0 / (1.0 + Math.exp(-(Tmix_b - mod.flash_t_ign) / mod.flash_t_width));
    var through = 1.0, co = cfg.chambers.carry_over;
    for (var i = 0; i < co.length; i++) through = through * co[i];
    return { exit_offset_m: cfg.exit_offset_m, delay_s: cfg.t_uncork_cap_s, exhaust_T0_K: T0s, bare_T0_K: T0b, exhaust_peak_kg_s: shot.peak_mdot_exit, bare_peak_kg_s: bare.peak_mdot_exit,
      scale: { precursor: 0.0, primary: glow, intermediate: glow, slot_jet: 0.0, sparks: through, secondary: ps / pb },
      secondary: { mix_T_K: Tmix_s, bare_mix_T_K: Tmix_b, ignition_T_K: mod.flash_t_ign, chance: ps, bare_chance: pb },
      o2_burnt_in_can_kg: shot.o2_burnt_kg, duration_scale: 1.0 };
  }

  /* Heat one shot leaves in the can (J) at wall temperature t_wall (K), with share o2 of the fill being fresh air. */
  function shotHeat(t_wall, o2) { var H = need().config.heat; return interp(H.t_wall_K, H.shot_J, t_wall) + o2 * H.first_round_extra_J; }

  /* Can temperature after dt seconds of still-air cooling. */
  function cool(T, dt) {
    var H = need().config.heat, n = Math.ceil(dt / 0.05), h, i, q;
    if (n < 1) n = 1;
    h = dt / n;
    for (i = 0; i < n; i++) {
      q = H.h_conv * H.area_m2 * (T - T_AMB) + H.emissivity * SIGMA * H.area_m2 * (Math.pow(T, 4) - Math.pow(T_AMB, 4));
      T = T - h * q / H.C_J_per_K;
    }
    return T;
  }

  /* Bulk can temperature through a string of shots (times in seconds, ascending). idleBefore: seconds the can stood
   * open to the air before the first shot (default: long enough to be full of air). */
  function heatString(shotTimes, T0, idleBefore) {
    var H = need().config.heat, T = T0 === undefined ? T_AMB : T0, out = [], last = null, i, gap, o2, q, T1;
    if (idleBefore === undefined) idleBefore = 1e9;
    for (i = 0; i < shotTimes.length; i++) {
      gap = last === null ? idleBefore : shotTimes[i] - last;
      if (last !== null) T = cool(T, gap);
      o2 = 1.0 - Math.exp(-gap / H.tau_o2_s);
      q = shotHeat(T, o2); T1 = T + q / H.C_J_per_K;
      out.push({ t: shotTimes[i], T_before_K: T, o2: o2, heat_J: q, T_after_K: T1 });
      T = T1; last = shotTimes[i];
    }
    return out;
  }

  /* A copy of the HK416 action.json with the blocks that change when the can is fitted. Pass it to HK416Action.use(). */
  function actionData(hkAction) {
    var ov = need().action.overlay, o = Object.assign({}, hkAction);
    o.cycle = ov.cycle; o.ballistics = ov.ballistics; o.events = ov.events;
    o.auto = Object.assign({}, hkAction.auto, ov.auto);
    o.recoil = Object.assign({}, hkAction.recoil, { semi: ov.recoil.semi, auto: ov.recoil.auto });
    o.mechanics = Object.assign({}, hkAction.mechanics, ov.mechanics);
    o.brass = Object.assign({}, hkAction.brass, { release_time_s: ov.brass.release_time_s, nominal: Object.assign({}, hkAction.brass.nominal, ov.brass.nominal) });
    o.suppressor = { asset: 'suppressor-qd-556' };
    return o;
  }

  function levels(state) { return need().sound[state || 'subsequent'].levels; }
  function state(name) { return need().states[name || 'subsequent']; }

  var api = {
    load: load, use: use, runShot: runShot, acoustics: acoustics, soundOverlay: soundOverlay, soundParams: soundParams, flashInput: flashInput,
    shotHeat: shotHeat, cool: cool, heatString: heatString, actionData: actionData, levels: levels, state: state, db: db, interp: interp,
    get data() { return D; },
    get mass() { return need().config.mass_kg; },
    get exitOffset() { return need().config.exit_offset_m; },
    get exitAfterSear() { return need().hk416.exit_after_sear_s; },
    get sockets() { var z = need().config.exit_offset_m; return { socket_mount: [0, 0, 0], socket_exit: [0, 0, z] }; },
    states: ['first_round', 'subsequent', 'hot']
  };
  return api;
});
