/* HK416 D14.5RS barrel and handguard heating. Runs the thermal model of sim.py in the browser, on the
 * coarser grid stored in heat.json (block "runtime": 5 mm stations along the barrel, 3 radial cells). No dependencies.
 *
 *   <script src="hk416-heat.js"></script>             -> window.HK416Heat
 *   const HK416Heat = require('./hk416-heat.js')       (Node)
 *
 *   await HK416Heat.load('heat.json')         // or HK416Heat.use(parsedJson)
 *   const gun = HK416Heat.create({ ambientC: 25, wind: 0 })
 *   gun.fire()                                // once per shot, when it is fired
 *   gun.advance(dt)                           // every frame, seconds
 *   const s = gun.state()
 *   // s.chamberC, s.boreMaxC, s.barrelMaxC, s.gasBlockC, s.handguardHandC ...   temperatures, deg C
 *   // s.mirage  = { strength 0..1, dn, heightM, riseMps, jitterMoa, steadyMoa }
 *   // s.comfort = { level 0..5, name, surfaceC, contactC }
 *   // s.cookoff = { chamberC, caseC, propellantC, damage 0..1, timeS, risk 'none'|'caution'|'danger' }
 *   // s.poi     = { bowMoa (negative = low), mvDelta (m/s, for the next shot) }
 *   // s.glow    = { cdM2, rgb }
 *   const p = gun.profile()                   // { zMm[], outerC[], boreC[], handguardZMm[], handguardC[] }
 *
 * Frame: zMm is the asset's +Z (towards the muzzle), 0 at the upper receiver's front face.
 * Temperatures are deg C at the API and kelvin inside. Every formula here mirrors sim.py line for line;
 * test_heat.js checks the two against each other.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.HK416Heat = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, R = null, K0 = 273.15, SIGMA = 5.670374e-8, G0 = 9.80665, TREF = 298.15;

  function need() { if (!R) throw new Error('HK416Heat: call use(data) or load(url) first'); return R; }

  /* ---------------- steel: EN 1993-1-2 specific heat, enthalpy table on 0.5 K steps (as sim.py) */
  var TT = null, HH = null, NT = 3301;
  function cSteel(tc) {
    if (tc >= 900) return 650.0;
    if (tc >= 735) return 545 + 17820 / Math.max(tc - 731, 1e-9);
    if (tc >= 600) return 666 + 13002 / Math.max(738 - tc, 1e-9);
    return 425 + 0.773 * tc - 1.69e-3 * tc * tc + 2.22e-6 * tc * tc * tc;
  }
  function buildSteel() {
    TT = new Float64Array(NT); HH = new Float64Array(NT);
    var cPrev = 0;
    for (var i = 0; i < NT; i++) {
      var tc = -50.0 + 0.5 * i; TT[i] = tc + K0;
      var c = cSteel(tc);
      if (i > 0) HH[i] = HH[i - 1] + 0.5 * (c + cPrev) * 0.5;
      cPrev = c;
    }
  }
  function steelH(T) {
    var u = (T - TT[0]) / 0.5;
    if (!(u > 0)) return HH[0];
    if (u >= NT - 1) return HH[NT - 1];
    var i = Math.floor(u), f = u - i;
    return HH[i] + (HH[i + 1] - HH[i]) * f;
  }
  function steelT(h) {
    if (!(h > HH[0])) return TT[0];
    if (h >= HH[NT - 1]) return TT[NT - 1];
    var lo = 0, hi = NT - 1;
    while (hi - lo > 1) { var m = (lo + hi) >> 1; if (HH[m] <= h) lo = m; else hi = m; }
    return TT[lo] + (TT[hi] - TT[lo]) * (h - HH[lo]) / (HH[hi] - HH[lo]);
  }
  function kSteel(T) { return Math.max(27.0, 42.7 - 0.0165 * (T - K0)); }
  function cAl(T) { return 896.0 + 0.45 * (T - K0 - 25.0); }

  /* ---------------- air and convection */
  function hCylinder(Dm, Ts, Ta, U) {            // Churchill-Chu (free) and Churchill-Bernstein (cross-flow), blended as cubes
    var Tf = 0.5 * (Ts + Ta), k = 0.0263 * Math.pow(Tf / 300.0, 0.82), nu = 1.589e-5 * Math.pow(Tf / 300.0, 1.7), Pr = 0.70;
    var dT = Math.abs(Ts - Ta) + 1e-3;
    var Ra = G0 * dT / Tf * Dm * Dm * Dm / (nu * nu / Pr);
    var a = 0.60 + 0.387 * Math.pow(Ra, 1 / 6) / Math.pow(1 + Math.pow(0.559 / Pr, 9 / 16), 8 / 27);
    var Nu = a * a;
    if (U > 0) {
      var Re = U * Dm / nu;
      var Nuf = 0.3 + 0.62 * Math.pow(Re, 0.5) * Math.pow(Pr, 1 / 3) / Math.pow(1 + Math.pow(0.4 / Pr, 2 / 3), 0.25) * Math.pow(1 + Math.pow(Re / 282000.0, 5 / 8), 0.8);
      Nu = Math.pow(Nu * Nu * Nu + Nuf * Nuf * Nuf, 1 / 3);
    }
    return Nu * k / Dm;
  }
  function gapConductance(ri, ro, Ti, To) {      // Raithby-Hollands, W/m/K per unit length of annulus
    var Tf = 0.5 * (Ti + To), k = 0.0263 * Math.pow(Tf / 300.0, 0.82), nu = 1.589e-5 * Math.pow(Tf / 300.0, 1.7), Pr = 0.70;
    var L = ro - ri, dT = Math.abs(Ti - To) + 1e-3;
    var RaL = G0 * dT / Tf * L * L * L / (nu * nu / Pr);
    var Rac = Math.pow(Math.log(ro / ri), 4) / (L * L * L * Math.pow(Math.pow(ri, -0.6) + Math.pow(ro, -0.6), 5)) * RaL;
    var keff = k * Math.max(1.0, 0.386 * Math.pow(Pr / (0.861 + Pr), 0.25) * Math.pow(Rac, 0.25));
    return 2 * Math.PI * keff / Math.log(ro / ri);
  }

  /* ---------------- effects (same formulas as sim.py) */
  function miragePlume(Q, Ta, U, y, Lp, dTs) {
    var rho = 101325.0 / (287.05 * Ta), cp = 1006.0;
    var F = G0 * Math.max(Q, 0.0) / (rho * cp * Ta);
    var w = 1.8 * Math.cbrt(F);
    var F23 = Math.pow(F, 2 / 3);
    var calm = 2.6 * F23 * Ta / (G0 * y);
    if (U > w && U > 0) calm = Math.min(calm, F * Ta / (G0 * U * y));
    var dT = Math.min(calm, 0.5 * Math.max(dTs, 0.0));
    var dn = 0.0796 * (1 / Ta - 1 / (Ta + dT));
    var b = 0.156 * y;
    var hCalm = 2.6 * F23 * Ta / (G0 * 3.0);
    var h = (U > w && U > 0) ? Math.min(hCalm, F * Ta / (G0 * U * 3.0)) : hCalm;
    var onAxis = w > 0 ? Math.exp(-Math.pow(U / (0.35 * w), 2)) : 0.0;
    var jitter = 0.3 * dn * Math.sqrt(2 * Math.sqrt(Math.PI) * Lp / b) * onAxis;
    var steady = dn / y * Lp * onAxis;
    return { dT: dT, dn: dn, halfWidth: b, rise: w, height: h, jitterMoa: jitter * 3437.75, steadyMoa: steady * 3437.75 };
  }
  function mirageSight(Qb, Qh, dTb, dTh, Ta, U) {
    var M = R.mirage;
    var a = miragePlume(Qb, Ta, U, M.sight_y - M.barrel_r, M.len_barrel, dTb), b = miragePlume(Qh, Ta, U, M.sight_y - M.hg_top_y, M.len_hg, dTh);
    var ra = miragePlume(Qb, Ta, U, M.ref_y, M.len_barrel, dTb), rb = miragePlume(Qh, Ta, U, M.ref_y, M.len_hg, dTh);
    var dnRef = Math.max(ra.dn, rb.dn);
    return { dn: dnRef, dnSight: Math.max(a.dn, b.dn), heightM: Math.max(a.height, b.height), jitterMoa: Math.hypot(a.jitterMoa, b.jitterMoa),
             steadyMoa: a.steadyMoa + b.steadyMoa, riseMps: Math.max(a.rise, b.rise), strength: Math.min(1.0, dnRef / (0.0796 / Ta)),
             gradient: dnRef / (0.156 * M.ref_y) };
  }
  function cookoffInduction(TK) {
    var c = R.cookoff;
    return c.t1_s * Math.exp(Math.min(60.0, c.E_over_R_K * (1 / Math.max(TK, 200.0) - 1 / (c.T1_C + K0))));
  }
  /* time for a fresh round at roundC, chambered into a chamber held at chamberC, to cook off; Infinity beyond limit */
  function cookoffTime(chamberC, roundC, limit) {
    if (roundC == null) roundC = 25.0;
    if (limit == null) limit = 1800.0;
    var tau = R.p.c_case_J_K / Math.max(R.p.g_chamber_case, 1e-9), Tw = chamberC + K0, T0 = roundC + K0;
    if (cookoffInduction(Tw) > limit) return Infinity;
    var Dm = 0.0, t = 0.0, dt = 0.25;
    while (t < limit) {
      var Tc = Tw - (Tw - T0) * Math.exp(-(t + 0.5 * dt) / tau);
      Dm += dt / cookoffInduction(Tc); t += dt;
      if (Dm >= 1.0) return t;
    }
    return Infinity;
  }
  function comfortLevel(TC) {
    var c = R.comfort_C;
    for (var i = 0; i < c.length; i++) if (TC < c[i]) return i;
    return c.length;
  }
  function contactTemp(TC) { var s = R.skin; return (s.b_al * TC + s.b * s.T_C) / (s.b_al + s.b); }
  function interpTable(x, xs, ys) {
    var n = xs.length;
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    var i = 0; while (xs[i + 1] < x) i++;
    return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i]);
  }
  function glow(TC) {
    var g = R.glow;
    if (TC < g.T_C[0]) return { cdM2: 0.0, rgb: [1, 0, 0] };
    var n = g.T_C.length, i = 0; while (i < n - 2 && g.T_C[i + 1] < TC) i++;
    var f = Math.min(1, (TC - g.T_C[i]) / (g.T_C[i + 1] - g.T_C[i])), a = g.rgb[i], b = g.rgb[i + 1];
    return { cdM2: interpTable(TC, g.T_C, g.cd_m2), rgb: [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f] };
  }

  /* ---------------- the model */
  function Gun(opts) {
    need(); opts = opts || {};
    var p = R.p, nz = R.nz, nr = R.nr, nh = R.hgi.length, i;
    this.Ta = (opts.ambientC != null ? opts.ambientC : p.ambient_C) + K0;
    this.U = opts.wind != null ? opts.wind : p.wind_m_s;
    this.T = new Float64Array(nz * nr).fill(this.Ta);
    this.H = new Float64Array(nz * nr).fill(steelH(this.Ta));
    this.Thg = new Float64Array(nh).fill(this.Ta);
    this.Tl = { gb: this.Ta, piston: this.Ta, fh: this.Ta, uf: this.Ta, ur: this.Ta, nut: this.Ta };
    this.Tcase = this.Ta; this.Tprop = this.Ta; this.Dco = 0.0; this.mvDelta = 0.0;
    this.t = 0.0; this.shots = 0; this.Ein = 0.0; this.Eout = 0.0; this.coefT = -1e9; this.acc = 0.0;
    this.qLineBarrel = 0.0; this.qLineHg = 0.0;
    this.hAamb = new Float64Array(nz); this.Ggap = new Float64Array(nz); this.hHg = new Float64Array(nh);
    this.hGb = 0; this.hFh = 0; this.hUf = 0; this.hUr = 0;
    this._k = new Float64Array(nz * nr); this._dQ = new Float64Array(nz * nr); this._dH = new Float64Array(nh);
    this._qhg = new Float64Array(nz);
    var dzEx = 0, dzHg = 0;
    for (i = 0; i < nz; i++) if (R.mask.ex[i]) dzEx += R.dz[i];
    for (i = 0; i < nh; i++) dzHg += R.hg_dz[i];
    this.dzEx = dzEx; this.dzHg = dzHg;
  }
  Gun.prototype.setEnvironment = function (o) {
    if (o.ambientC != null) this.Ta = o.ambientC + K0;
    if (o.wind != null) this.U = o.wind;
    this.coefT = -1e9;
  };
  Gun.prototype._coefs = function () {
    var p = R.p, nz = R.nz, nr = R.nr, nh = R.hgi.length, Ta = this.Ta, U = this.U, i;
    for (i = 0; i < nz; i++) {
      var Ts = this.T[i * nr + nr - 1];
      this.hAamb[i] = R.m_exp[i] ? hCylinder(2 * R.r_out[i], Ts, Ta, U) * R.As[i] : 0.0;
      if (R.m_hg[i]) {
        var Thb = this.Thg[Math.max(R.b2h[i], 0)];
        this.Ggap[i] = gapConductance(R.r_out[i], p.hg_r_inner_m, Ts, Thb) * R.dz[i];
      } else this.Ggap[i] = 0.0;
    }
    for (i = 0; i < nh; i++) this.hHg[i] = hCylinder(0.060, this.Thg[i], Ta, U);
    this.hGb = hCylinder(0.030, this.Tl.gb, Ta, U); this.hFh = hCylinder(0.0212, this.Tl.fh, Ta, U);
    this.hUf = hCylinder(0.045, this.Tl.uf, Ta, U); this.hUr = hCylinder(0.045, this.Tl.ur, Ta, U);
  };
  /* one shot's heat (n shots if they fall in one step) */
  Gun.prototype.fire = function (n) {
    if (n == null) n = 1;
    var p = R.p, nz = R.nz, nr = R.nr, Tl = this.Tl, sum = 0.0;
    for (var i = 0; i < nz; i++) {
      var f = (R.Teff[i] - this.T[i * nr]) / (R.Teff[i] - TREF); if (f < 0) f = 0;
      var E = n * (R.Eg[i] * f + R.Efix[i]);
      this.H[i * nr] += E / R.M[i * nr]; this.T[i * nr] = steelT(this.H[i * nr]); sum += E;
    }
    this.mvDelta = R.mv.m_s_per_K * (Math.min(this.Tprop, R.mv.T_max_C + K0) - TREF);
    this.Eout += p.c_case_J_K * (this.Tcase - this.Ta);          // the fired case leaves with its heat; a fresh round is chambered
    this.Tcase = this.Ta; this.Tprop = this.Ta; this.Dco = 0.0;
    Tl.gb = steelT(steelH(Tl.gb) + n * R.q_gb / p.m_gas_block);
    Tl.piston = steelT(steelH(Tl.piston) + n * R.q_piston / p.m_piston);
    Tl.fh = steelT(steelH(Tl.fh) + n * p.q_flash_hider_J / p.m_fh_front);
    this.Ein += sum + n * (R.q_gb + R.q_piston + p.q_flash_hider_J);
    this.shots += n;
    return this;
  };
  Gun.prototype.step = function (dt) {
    var p = R.p, nz = R.nz, nr = R.nr, nh = R.hgi.length, Ta = this.Ta, T = this.T, H = this.H, Tl = this.Tl, Thg = this.Thg;
    var i, j, c;
    if (this.t - this.coefT >= R.coef_refresh_s) { this._coefs(); this.coefT = this.t; }
    var k = this._k, dQ = this._dQ, dH = this._dH, qhg = this._qhg;
    for (c = 0; c < nz * nr; c++) { k[c] = kSteel(T[c]); dQ[c] = 0.0; }
    for (i = 0; i < nz; i++) for (j = 0; j < nr - 1; j++) {
      c = i * nr + j;
      var qr = R.Gr[i * (nr - 1) + j] * 0.5 * (k[c + 1] + k[c]) * (T[c + 1] - T[c]);
      dQ[c] += qr; dQ[c + 1] -= qr;
    }
    for (i = 0; i < nz - 1; i++) for (j = 0; j < nr; j++) {
      c = i * nr + j;
      var qa = R.Ga[c] * 0.5 * (k[c + nr] + k[c]) * (T[c + nr] - T[c]);
      dQ[c] += qa; dQ[c + nr] -= qa;
    }
    var Ta4 = Ta * Ta * Ta * Ta, es = p.eps_steel, ea = p.eps_al, Fa = p.hg_view_to_ambient, fv = p.hg_vent_fraction, sp = p.hg_top_bottom_split;
    var sAmb = 0, sBn = 0, sUp = 0, sGb = 0, sCase = 0, qlB = 0, qlG = 0;
    var qFh = p.g_barrel_fh * (T[nz * nr - 1] - Tl.fh);
    for (i = 0; i < nz; i++) {
      c = i * nr + nr - 1;
      var Ts = T[c], Ts4 = Ts * Ts * Ts * Ts, Thb = Thg[Math.max(R.b2h[i], 0)];
      var qAmb = this.hAamb[i] * (Ts - Ta) + (R.m_exp[i] ? SIGMA * es * R.As[i] * (Ts4 - Ta4) : 0.0);
      var qH = 0.0;
      if (R.m_hg[i]) {
        qAmb += SIGMA * es * Fa * R.As[i] * (Ts4 - Ta4) + fv * this.Ggap[i] * (Ts - Ta);
        qH = SIGMA * R.eps_gap[i] * (1 - Fa) * R.As[i] * (Ts4 - Thb * Thb * Thb * Thb) + (1 - fv) * this.Ggap[i] * (Ts - Thb);
        qlG += fv * this.Ggap[i] * (Ts - Ta);
      }
      qhg[i] = qH;
      var qBn = R.G_bn[i] * (Ts - Tl.nut), qUp = R.G_up[i] * (Ts - Tl.uf), qGb = R.G_gb[i] * (Ts - Tl.gb);
      var out = qAmb + qH + qUp + qGb + qBn;
      if (i === nz - 1) out += qFh;
      dQ[c] -= out;
      var qCase = R.G_case[i] * (T[i * nr] - this.Tcase);
      dQ[i * nr] -= qCase;
      sAmb += qAmb; sBn += qBn; sUp += qUp; sGb += qGb; sCase += qCase;
      if (R.mask.ex[i]) qlB += this.hAamb[i] * (Ts - Ta);
    }
    /* handguard */
    for (j = 0; j < nh; j++) dH[j] = 0.0;
    for (i = 0; i < nz; i++) if (R.b2h[i] >= 0) dH[R.b2h[i]] += qhg[i];
    for (j = 0; j < nh - 1; j++) { var qax = R.hg_Ga[j] * (Thg[j + 1] - Thg[j]); dH[j] += qax; dH[j + 1] -= qax; }
    var sLoss = 0, qlH = 0;
    for (j = 0; j < nh; j++) {
      var Th = Thg[j];
      var loss = (this.hHg[j] * p.hg_perim_out_m * (Th - Ta) + SIGMA * ea * p.hg_perim_rad_m * (Th * Th * Th * Th - Ta4)) * R.hg_dz[j];
      dH[j] -= loss; sLoss += loss;
      qlH += this.hHg[j] * p.hg_perim_out_m * 0.5 * (1 + sp) * (Th - Ta) * R.hg_dz[j];
    }
    var np_ = R.pist.length, Ap = p.a_piston / Math.max(np_, 1), Tp = Tl.piston, Tp4 = Tp * Tp * Tp * Tp, sP = 0;
    for (j = 0; j < np_; j++) {
      var ph = R.pist[j], Tx = Thg[ph];
      var qp = Ap * (SIGMA * 0.75 * (Tp4 - Tx * Tx * Tx * Tx) + 8.0 * (Tp - Tx));
      dH[ph] += qp; sP += qp;
    }
    var qHu = p.g_handguard_upper * (Thg[0] - Tl.uf); dH[0] -= qHu;
    var nn = R.nh.length, sNh = 0;
    for (j = 0; j < nn; j++) { var qnh = p.g_nut_handguard / nn * (Tl.nut - Thg[R.nh[j]]); dH[R.nh[j]] += qnh; sNh += qnh; }
    var qNu = p.g_nut_upper * (Tl.nut - Tl.uf);
    /* advance the barrel, then the handguard */
    for (c = 0; c < nz * nr; c++) { H[c] += dQ[c] * dt / R.M[c]; T[c] = steelT(H[c]); }
    for (j = 0; j < nh; j++) Thg[j] = Thg[j] + dH[j] * dt / (R.hg_M[j] * cAl(Thg[j]));
    /* the chambered round */
    this.Tcase += sCase * dt / p.c_case_J_K;
    this.Tprop += (this.Tcase - this.Tprop) * dt / R.cookoff.tau_prop_s;
    this.Dco += dt / cookoffInduction(this.Tcase);
    /* lumps */
    function cool(Tx_, A, h, eps) { return A * (h * (Tx_ - Ta) + SIGMA * eps * (Tx_ * Tx_ * Tx_ * Tx_ - Ta4)); }
    var qGp = p.g_gas_block_piston * (Tl.gb - Tl.piston);
    var lGb = cool(Tl.gb, p.a_gas_block, this.hGb, es), lFh = cool(Tl.fh, p.a_fh_front, this.hFh, es);
    var lUf = cool(Tl.uf, p.a_upper_front, this.hUf, ea), lUr = cool(Tl.ur, p.a_upper_rear, this.hUr, ea);
    var qUfr = p.g_upper_front_rear * (Tl.uf - Tl.ur);
    Tl.gb = steelT(steelH(Tl.gb) + (sGb - qGp - lGb) * dt / p.m_gas_block);
    Tl.piston = steelT(steelH(Tl.piston) + (qGp - sP) * dt / p.m_piston);
    Tl.fh = steelT(steelH(Tl.fh) + (qFh - lFh) * dt / p.m_fh_front);
    Tl.nut = steelT(steelH(Tl.nut) + (sBn - sNh - qNu) * dt / p.m_nut);
    var uf = Tl.uf, ur = Tl.ur;
    Tl.uf = uf + (sUp + qHu + qNu - qUfr - lUf) * dt / (p.m_upper_front * cAl(uf));
    Tl.ur = ur + (qUfr - lUr) * dt / (p.m_upper_rear * cAl(ur));
    this.Eout += (sAmb + sLoss + lGb + lFh + lUf + lUr) * dt;
    this.qLineBarrel = qlB / this.dzEx;
    this.qLineHg = qlH / this.dzHg + qlG / this.dzHg;
    this.t += dt;
  };
  /* advance by a frame time; the model steps at its own fixed step */
  Gun.prototype.advance = function (dt) {
    this.acc += dt; var h = R.dt, n = 0;
    while (this.acc >= h && n < 400) { this.step(h); this.acc -= h; n++; }
    if (n === 400) this.acc = 0;
    return this;
  };
  /* the probe set of sim.py (same names, deg C) */
  Gun.prototype.probes = function () {
    var p = R.p, nz = R.nz, nr = R.nr, nh = R.hgi.length, T = this.T, Tl = this.Tl, m = R.mask, i, j, c;
    var chM = 0, chTM = 0, chS = 0, chO = 0, chN = 0, thB = -1e9, thO = -1e9, mxO = -1e9, mxZ = 0, mxB = -1e9;
    var hgS = 0, hgN = 0, exS = 0, exN = 0, nkS = 0, nkN = 0, totM = 0, totTM = 0, bow = 0;
    for (i = 0; i < nz; i++) {
      var Ti = T[i * nr] - K0, To = T[i * nr + nr - 1] - K0, sM = 0, sTM = 0;
      for (j = 0; j < nr; j++) { c = i * nr + j; sM += R.M[c]; sTM += T[c] * R.M[c]; }
      totM += sM; totTM += (sTM - K0 * sM);
      var wc = R.w_chamber[i];
      if (wc > 0) { chM += wc * sM; chTM += wc * (sTM - K0 * sM); chS += wc * R.dz[i] * Ti; chO += wc * R.dz[i] * To; chN += wc * R.dz[i]; }
      if (m.throat[i]) { if (Ti > thB) thB = Ti; if (To > thO) thO = To; }
      if (To > mxO) { mxO = To; mxZ = R.z_mm[i]; }
      if (Ti > mxB) mxB = Ti;
      if (m.hg[i]) { hgS += To; hgN++; }
      if (m.ex[i]) { exS += To; exN++; }
      if (m.neck[i]) { nkS += To; nkN++; }
      if (m.free[i]) bow += p.alpha_steel * R.poi.eta * (sTM / sM - this.Ta) / (2 * R.r_out[i]) * R.dz[i];
    }
    var TaC = this.Ta - K0, sp = p.hg_top_bottom_split, ih = R.i_hand, hMax = -1e9, hTop = -1e9, hSum = 0;
    for (j = 0; j < nh; j++) {
      var Th = this.Thg[j] - K0, ex = Th - TaC;
      if (Th > hMax) hMax = Th;
      if (Th + sp * ex > hTop) hTop = Th + sp * ex;
      hSum += Th;
    }
    var Thand = this.Thg[ih] - K0;
    return {
      t: this.t, shots: this.shots,
      chamber_wall: chTM / chM, chamber_skin: chS / chN, chamber_outer: chO / chN,
      throat_bore: thB, throat_outer: thO, barrel_max_outer: mxO, barrel_max_z_mm: mxZ, bore_max: mxB,
      under_handguard_outer: hgS / hgN, exposed_outer: exS / exN, neck_outer: nkS / nkN,
      muzzle_outer: T[nz * nr - 1] - K0, barrel_mean: totTM / totM,
      gas_block: Tl.gb - K0, piston: Tl.piston - K0, flash_hider: Tl.fh - K0, upper_front: Tl.uf - K0, upper_rear: Tl.ur - K0, barrel_nut: Tl.nut - K0,
      handguard_hand: Thand - 0.5 * sp * (Thand - TaC), handguard_hand_mean: Thand, handguard_max: hMax, handguard_top_max: hTop, handguard_mean: hSum / nh,
      round_case: this.Tcase - K0, round_propellant: this.Tprop - K0, cookoff_damage: this.Dco, mv_delta_m_s: this.mvDelta,
      mv_delta_next_m_s: R.mv.m_s_per_K * (Math.min(this.Tprop, R.mv.T_max_C + K0) - TREF), poi_bow_moa: -bow * 3437.75,
      q_line_barrel_W_m: this.qLineBarrel, q_line_handguard_W_m: this.qLineHg
    };
  };
  /* the effect set of sim.py's derive_effects, from a probe row */
  Gun.prototype.effects = function (r) {
    r = r || this.probes();
    var TaC = this.Ta - K0;
    var mi = mirageSight(r.q_line_barrel_W_m, r.q_line_handguard_W_m, r.exposed_outer - TaC, r.handguard_top_max - TaC, this.Ta, this.U);
    var Tmax = Math.max(r.barrel_max_outer, r.gas_block, r.flash_hider);
    return { mirage_dn: mi.dn, mirage_height_m: mi.heightM, mirage_jitter_moa: mi.jitterMoa, mirage_steady_moa: mi.steadyMoa, mirage_strength: mi.strength,
             mirage_rise_m_s: mi.riseMps, glow_cd_m2: Tmax >= R.glow.T_C[0] ? interpTable(Tmax, R.glow.T_C, R.glow.cd_m2) : 0.0,
             comfort: comfortLevel(r.handguard_hand), contact_C: contactTemp(r.handguard_hand), cookoff_time_s: cookoffTime(r.chamber_wall, TaC) };
  };
  /* everything a game needs, in one object. cookoff.timeS is costly (a short integration): pass {cookoffTime:false} to skip it */
  Gun.prototype.state = function (o) {
    var r = this.probes(), TaC = this.Ta - K0, c = R.cookoff;
    var mi = mirageSight(r.q_line_barrel_W_m, r.q_line_handguard_W_m, r.exposed_outer - TaC, r.handguard_top_max - TaC, this.Ta, this.U);
    var lvl = comfortLevel(r.handguard_hand), Tmax = Math.max(r.barrel_max_outer, r.gas_block, r.flash_hider);
    var risk = (r.chamber_wall >= c.danger_C || r.cookoff_damage >= 0.5) ? 'danger' : (r.chamber_wall >= c.caution_C ? 'caution' : 'none');
    return {
      t: r.t, shots: r.shots, ambientC: TaC,
      chamberC: r.chamber_wall, chamberBoreC: r.chamber_skin, throatBoreC: r.throat_bore, boreMaxC: r.bore_max,
      barrelMaxC: r.barrel_max_outer, barrelMaxZMm: r.barrel_max_z_mm, underHandguardC: r.under_handguard_outer, exposedBarrelC: r.exposed_outer,
      muzzleC: r.muzzle_outer, barrelMeanC: r.barrel_mean, gasBlockC: r.gas_block, pistonC: r.piston, flashHiderC: r.flash_hider,
      upperFrontC: r.upper_front, upperRearC: r.upper_rear, handguardHandC: r.handguard_hand, handguardMaxC: r.handguard_max, handguardTopMaxC: r.handguard_top_max,
      mirage: mi,
      comfort: { level: lvl, name: R.comfort_names[lvl], surfaceC: r.handguard_hand, contactC: contactTemp(r.handguard_hand) },
      cookoff: { chamberC: r.chamber_wall, caseC: r.round_case, propellantC: r.round_propellant, damage: Math.min(1, r.cookoff_damage),
                 cookedOff: r.cookoff_damage >= 1, timeS: (o && o.cookoffTime === false) ? null : cookoffTime(r.chamber_wall, TaC), risk: risk },
      poi: { bowMoa: r.poi_bow_moa, mvDelta: r.mv_delta_next_m_s, mvDeltaLastShot: r.mv_delta_m_s, mirageShiftMoa: mi.steadyMoa },
      glow: glow(Tmax),
      probes: r
    };
  };
  Gun.prototype.profile = function () {
    var nz = R.nz, nr = R.nr, o = [], b = [], h = [], hz = [], i;
    for (i = 0; i < nz; i++) { o.push(this.T[i * nr + nr - 1] - K0); b.push(this.T[i * nr] - K0); }
    for (i = 0; i < R.hgi.length; i++) { h.push(this.Thg[i] - K0); hz.push(R.z_mm[R.hgi[i]]); }
    return { zMm: R.z_mm.slice(), outerC: o, boreC: b, handguardZMm: hz, handguardC: h };
  };
  /* outer barrel temperature at a position along the bore (asset +Z, mm), linear between stations */
  Gun.prototype.outerAt = function (zMm) {
    var nz = R.nz, nr = R.nr, z = R.z_mm;
    if (zMm <= z[0]) return this.T[nr - 1] - K0;
    if (zMm >= z[nz - 1]) return this.T[nz * nr - 1] - K0;
    var i = 0; while (z[i + 1] < zMm) i++;
    var a = this.T[i * nr + nr - 1], b = this.T[(i + 1) * nr + nr - 1];
    return a + (b - a) * (zMm - z[i]) / (z[i + 1] - z[i]) - K0;
  };
  Gun.prototype.energy = function () { return { depositedJ: this.Ein, lostJ: this.Eout }; };

  /* Offline run with the stepping of sim.py's run(): fire the shots whose time falls in a step, then step.
   * Returns { rows: [probe rows], effects: [effect rows], gun }. Used by the parity test; handy for planning too. */
  function simulate(shotTimes, tEnd, sampleTimes, opts) {
    var gun = new Gun(opts), dt = (opts && opts.dt) || R.dt, n = Math.ceil(tEnd / dt), si = 0, k = 0, rows = [], eff = [];
    for (var i = 0; i <= n; i++) {
      var t = i * dt;
      while (k < sampleTimes.length && sampleTimes[k] <= t + 1e-9) { var r = gun.probes(); rows.push(r); eff.push(gun.effects(r)); k++; }
      var m = 0;
      while (si < shotTimes.length && shotTimes[si] < t + dt - 1e-12) { si++; m++; }
      if (m) gun.fire(m);
      gun.step(dt);
    }
    return { rows: rows, effects: eff, gun: gun };
  }
  /* shot times of n rounds at rpm, with an optional pause after every magazine */
  function shotTimes(n, rpm, mag, reloadS) {
    var ts = [], t = 0;
    for (var i = 0; i < n; i++) { ts.push(t); t += 60.0 / rpm; if (mag && (i + 1) % mag === 0) t += (reloadS || 0); }
    return ts;
  }

  function use(data) {
    D = data; R = data.runtime;
    K0 = R.K0; SIGMA = R.SIGMA; G0 = R.G0; TREF = R.TREF;
    buildSteel();
    return api;
  }
  function load(url) {
    if (typeof fetch === 'function' && !(typeof process !== 'undefined' && process.versions && process.versions.node && !/^https?:/.test(url))) {
      return fetch(url).then(function (r) { return r.json(); }).then(use);
    }
    return Promise.resolve(use(JSON.parse(require('fs').readFileSync(url, 'utf8'))));
  }

  var api = {
    use: use, load: load,
    create: function (opts) { return new Gun(opts); },
    simulate: simulate, shotTimes: shotTimes,
    cookoffTime: function (chamberC, roundC, limit) { need(); return cookoffTime(chamberC, roundC, limit); },
    comfort: function (surfaceC) { need(); var l = comfortLevel(surfaceC); return { level: l, name: R.comfort_names[l], contactC: contactTemp(surfaceC) }; },
    glow: function (TC) { need(); return glow(TC); },
    /* precomputed full-grid runs from heat.json: ids() and schedule(id) -> { title, rounds, series, fields, peak, onset, ... } */
    scheduleIds: function () { need(); return Object.keys(D.schedules); },
    schedule: function (id) { need(); return D.schedules[id]; },
    get data() { return D; },
    get runtime() { return R; },
    get manualLimit() { return { rounds: 250, seconds: 180, source: 'HK maintenance manual p. 4' }; }
  };
  return api;
});
