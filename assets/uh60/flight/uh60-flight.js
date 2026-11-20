// UH-60A flight dynamics for the browser: rigid body + main rotor (blade-element thrust, momentum inflow with ground
// effect and the vortex-ring branch, first-order tip-path-plane tilt), tail rotor, stabilator, fin, fuselage drag,
// two governed T700 engines with a rotor-speed degree of freedom (so autorotation is real), wheels and a SAS / FPS.
// No dependencies. Internal units are the sources' own: feet, slugs, pounds, seconds, radians. Body axes x forward,
// y right, z down; world axes north, east, down. toThree() converts to metres in the model's export frame.
// Every constant carries its source in README.md (TM = TM 1-1520-237-10, PUB = published figure, INF = inferred).

const D2R = Math.PI / 180, KT = 1.68781, HP = 550, G = 32.174;

export const P = {
  // --- mass [TM 5.14 limits; PUB mission weight and inertias]
  weight: 16260, weightMax: 22000, weightEmptyOperating: 11780,
  Ixx: 4659, Iyy: 38512, Izz: 36796, Ixz: 1882,
  staCG: 346.5, wlCG: 248.0,                       // INF within the manual's CG envelope (fig 6-13)
  // --- main rotor [TM fig 2-2, 6-1; PUB]
  R: 26.833, chord: 1.73, nb: 4, omega100: 27.0,   // 53 ft 8 in; 258 rpm at 100 percent
  a: 5.73, twist: -16.0 * D2R,                     // lift slope; equivalent linear twist (PUB -18 deg nominal, tuned to TM hover torque)
  lock: 8.19, hingeOffset: 1.25, bladeMass: 7.95,  // PUB
  staHub: 341.2, wlHub: 315.0, shaftTilt: 3.0 * D2R,
  cd0: 0.0085, cd2: 0.50, kInd: 1.13,              // profile drag polar and induced power factor, fitted to the TM points (README)
  collMin: 13.1 * D2R, collMax: 25.9 * D2R,        // root collective: PUB upper limit; the lower one set so full-down autorotation holds about 108 percent rotor speed
  cycLon: 14.0 * D2R, cycLat: 8.0 * D2R,           // PUB approximate swashplate authority
  Irotor: 7060,                                    // slug ft2, blades + hub + drive train referred to the rotor (PUB blades, INF rest)
  // --- tail rotor [TM fig 2-2, 6-1; PUB]
  Rt: 5.5, chordT: 0.81, nbT: 4, gearT: 1190 / 258, staT: 732.0, wlT: 324.7, cant: 20.0 * D2R,
  twistT: -18.0 * D2R, pitchT0: 15.5 * D2R, pitchTRange: 15.0 * D2R, blockage: 0.88,
  // --- surfaces [PUB areas; positions TM fig 6-1]
  stabArea: 45.0, staStab: 712.0, wlStab: 240.5, stabSlope: 3.6,
  finArea: 32.3, staFin: 705.0, wlFin: 285.0, finSlope: 2.6, finCamber: 3.0 * D2R,
  fx: 45.0, fy: 150.0, fz: 135.0, download: 0.03,   // equivalent flat-plate areas ft2 (fx fitted to the TM cruise torque)
  // --- engines: 2 x T700-GE-700 [PUB 1,560 shp intermediate; TM 100 percent torque = transmission rating]
  shpEngine: 1560, shpTorque100: 1413, accessoryShp: 60, transLoss: 0.03,
  // --- landing gear [TM fig 2-2]
  staMain: 296.6, blMain: 53.3 / 12, staTail: 644.6, wlGround: 183.7,
};

export function atmosphere(hFt, dT = 0) {           // ISA with a temperature offset; returns slug/ft3 and speed of sound
  const T = 288.15 - 0.0019812 * hFt + dT, delta = Math.pow(1 - 6.8756e-6 * hFt, 5.2559);
  return { rho: 0.0023769 * delta * 288.15 / T, a: 49.02 * Math.sqrt(T * 1.8), T };
}

// Momentum-theory induced velocity, all in units of the hover value vh. vx in-plane, vz climb (+ up through the disc from above).
export function inducedRatio(vx, vz) {
  if ((2 * vz + 3) * (2 * vz + 3) + vx * vx < 1) return vz * (0.373 * vz * vz + 0.598 * vx * vx - 1.991);   // Johnson, vortex ring / turbulent wake
  let v = 1;
  for (let i = 0; i < 12; i++) {
    const s = vx * vx + (vz + v) * (vz + v), f = v - 1 / Math.sqrt(s), df = 1 + (vz + v) / Math.pow(s, 1.5);
    v -= f / df; if (v < 1e-3) v = 1e-3;
  }
  return v;
}
// Hayden's flight-test fit: induced power in ground effect / out of ground effect, z = rotor height above ground
export const groundEffect = (zOverR) => Math.min(1, 1 / (0.9926 + 0.03794 * 4 / (zOverR * zOverR)));

const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
const lerp = (a, b, t) => a + (b - a) * t;
function interp(x, xs, ys) { if (x <= xs[0]) return ys[0]; for (let i = 1; i < xs.length; i++) if (x <= xs[i]) return lerp(ys[i - 1], ys[i], (x - xs[i - 1]) / (xs[i] - xs[i - 1])); return ys[ys.length - 1]; }

export class UH60Flight {
  constructor(o = {}) {
    this.p = { ...P, ...(o.params || {}) };
    this.dT = o.dT || 0; this.groundAlt = o.groundAlt || 0; this.groundHeight = o.groundHeight || null;   // optional terrain fn (north, east) -> ft above datum
    this.reset(o);
  }
  reset(o = {}) {
    const p = this.p;
    this.hcg = (p.wlCG - p.wlGround) / 12;                                    // cg height with the wheels on the ground
    this.pos = [0, 0, -(this.hcg - 0.12)]; this.vel = [0, 0, 0];               // NED, ft
    this.q = [1, 0, 0, 0]; if (o.heading) this.q = [Math.cos(o.heading / 2), 0, 0, Math.sin(o.heading / 2)];
    this.w = [0, 0, 0];                                                        // p q r
    const run = o.running !== false;
    this.omega = run ? p.omega100 : 0; this.vi = 0; this.viT = 0; this.a1 = 0; this.b1 = 0; this.psi = 0; this.psiT = 0;
    this.eng = [0, 1].map(() => ({ on: run, ng: run ? 0.72 : 0, power: 0, tgt: run ? 500 : 15 }));
    this.govI = 0; this.thetaRef = 0; this.phiRef = 0; this.psiRef = o.heading || 0; this.time = 0;
    this.ctl = { collective: 0, lat: 0, lon: 0, pedal: 0 };
    this.fps = true; this.out = {}; this.wheelLoad = [0, 0, 0]; this.crashed = false; this.thI = this.phI = this.pedI = 0;
    this._telemetry(atmosphere(0, this.dT), 0, 0, 0, 0, 0, 0, 0);
  }
  // ---- small maths
  dcm() { const [a, b, c, d] = this.q; return [[a * a + b * b - c * c - d * d, 2 * (b * c - a * d), 2 * (b * d + a * c)], [2 * (b * c + a * d), a * a - b * b + c * c - d * d, 2 * (c * d - a * b)], [2 * (b * d - a * c), 2 * (c * d + a * b), a * a - b * b - c * c + d * d]]; }   // body -> world
  euler() { const m = this.dcm(); return { phi: Math.atan2(m[2][1], m[2][2]), theta: -Math.asin(clamp(m[2][0], -1, 1)), psi: Math.atan2(m[1][0], m[0][0]) }; }
  agl() { const g = this.groundHeight ? this.groundHeight(this.pos[0], this.pos[1]) : 0; return -this.pos[2] - g; }

  step(dt, c) {
    const n = Math.max(1, Math.ceil(dt / (1 / 240))), h = dt / n;
    for (let i = 0; i < n; i++) this._sub(h, c);
    return this.out;
  }

  _sub(h, c) {
    const p = this.p, m = p.weight / G, Rm = this.dcm();
    const e = this.euler(), alt = -this.pos[2] + this.groundAlt, atm = atmosphere(alt, this.dT), rho = atm.rho;
    // body velocities
    const vw = this.vel, vb = [0, 1, 2].map(i => Rm[0][i] * vw[0] + Rm[1][i] * vw[1] + Rm[2][i] * vw[2]);
    const [u, v, w] = vb, [pp, qq, rr] = this.w, V = Math.hypot(u, v, w); this._u = u / KT;
    // ---- SAS / FPS: the pilot's stick plus rate damping, and attitude hold when FPS is on
    const ias = V * Math.sqrt(rho / 0.0023769) / KT, onGround = this.wheelLoad[0] + this.wheelLoad[1] + this.wheelLoad[2] > 0.5 * p.weight;
    let lon = c.lon || 0, lat = c.lat || 0, ped = c.pedal || 0; const coll = clamp(c.collective || 0, 0, 1);
    this.fps = c.fps !== false;
    if (!onGround && this.omega > 0.8 * p.omega100) {
      if (this.fps) {
        let thCmd = -lon * 22 * D2R, phCmd = lat * 38 * D2R;
        if (c.assist !== false && ias < 40) {            // hover assist (a game aid, not an aircraft system): kill drift when the stick is centred
          const fade = 1 - ias / 40;
          if (Math.abs(c.lon || 0) < 0.05) thCmd += clamp(0.012 * u, -0.2, 0.2) * fade;
          if (Math.abs(c.lat || 0) < 0.05) phCmd += clamp(-0.012 * v, -0.2, 0.2) * fade;
        }
        this.thI = clamp((this.thI || 0) + (thCmd - e.theta) * h * 2.0, -0.5, 0.5); this.phI = clamp((this.phI || 0) + (phCmd - e.phi) * h * 1.5, -0.4, 0.4);
        lon = clamp(-(5.0 * (thCmd - e.theta) + this.thI - 1.7 * qq), -1, 1);
        lat = clamp(3.6 * (phCmd - e.phi) + this.phI - 0.8 * pp, -1, 1);
        const turn = ias > 45 ? (G * Math.tan(e.phi) / Math.max(V, 60)) : 0;      // coordinated turn above 45 kt
        let rCmd = ped * 0.9 + turn;
        if (Math.abs(c.pedal || 0) < 0.03 && ias < 45) { let d = this.psiRef - e.psi; d = Math.atan2(Math.sin(d), Math.cos(d)); rCmd = clamp(1.5 * d, -0.6, 0.6); }
        else this.psiRef = e.psi;
        this.pedI = clamp((this.pedI || 0) + (rCmd - rr) * h * 1.5, -0.8, 0.8);
        ped = clamp(2.2 * (rCmd - rr) + this.pedI + (ias > 45 ? 0.012 * v : 0), -1, 1);
      } else { lon += 0.55 * qq; lat -= 0.3 * pp; ped -= 0.9 * rr; this.psiRef = e.psi; }
    } else { this.psiRef = e.psi; this.thI = this.phI = this.pedI = 0;
    }
    this.ctl = { collective: coll, lat: clamp(lat, -1, 1), lon: clamp(lon, -1, 1), pedal: clamp(ped, -1, 1) };
    const th0 = lerp(p.collMin, p.collMax, coll), B1 = this.ctl.lon * p.cycLon, A1 = this.ctl.lat * p.cycLat;
    // ---- main rotor, in shaft axes (shaft tilted forward)
    const xh = (p.staCG - p.staHub) / 12, zh = -(p.wlHub - p.wlCG) / 12, cs = Math.cos(p.shaftTilt), ss = Math.sin(p.shaftTilt);
    const uh = u + qq * zh, vh_ = v - pp * zh + rr * xh, wh = w - qq * xh;
    const us = uh * cs + wh * ss, wsft = -uh * ss + wh * cs, vs = vh_;         // shaft axes: x fwd, z down the shaft
    const Om = Math.max(this.omega, 0.5), VT = Om * p.R, A = Math.PI * p.R * p.R, sigma = p.nb * p.chord / (Math.PI * p.R);
    const mu = Math.hypot(us, vs) / VT, chi = Math.atan2(vs, us), Vc = -wsft - this.a1 * us + this.b1 * vs;   // flow through the tip-path plane
    const zRotor = Math.max(this.agl() + (p.wlHub - p.wlCG) / 12, 2), kG0 = groundEffect(zRotor / p.R);
    const kG = 1 - (1 - kG0) * Math.exp(-Math.pow(Math.hypot(u, v) / (35 * KT), 2));
    const lam = (this.vi * kG + Vc) / VT;
    let CT = 0.5 * p.a * sigma * (th0 * (1 / 3 + mu * mu / 2) + p.twist / 4 * (1 + mu * mu) - lam / 2);
    const CTmax = 0.17 * sigma; CT = clamp(CT, -0.3 * CTmax, CTmax);            // blade stall limit (CT/sigma ~ 0.17)
    const Tm = CT * rho * A * VT * VT;
    const vhov = Math.sqrt(Math.abs(Tm) / (2 * rho * A)) + 1e-6;
    const viTarget = Math.sign(Tm) * vhov * inducedRatio(mu * VT / vhov, Vc / vhov * Math.sign(Tm || 1));
    this.vi += (viTarget - this.vi) * Math.min(1, h / 0.12);
    const ctS = Math.abs(CT) / sigma, Mat = (VT + Math.max(us, 0)) / atm.a;
    const cd = p.cd0 + p.cd2 * Math.pow(Math.max(0, ctS - 0.04), 2) + 0.9 * Math.pow(Math.max(0, Mat - 0.87), 2);
    const P0 = rho * A * VT * VT * VT * sigma * cd / 8 * (1 + 4.6 * mu * mu);
    const Pmain = Tm * (p.kInd * this.vi * kG + Vc) + P0, Qmain = Pmain / Om;
    // tip-path-plane tilt (first order, time constant 16 / (lock * omega)), flap-back in wind axes turned into shaft axes
    const a0 = p.lock / 8 * (th0 * (1 + mu * mu) + 0.8 * p.twist - 4 / 3 * lam);
    const fb = mu * (8 / 3 * th0 + 2 * p.twist - 2 * lam) / (1 - mu * mu / 2), lb = 4 / 3 * mu * a0 / (1 + mu * mu / 2);
    const k16 = 16 / (p.lock * Om);
    const a1T = fb * Math.cos(chi) - lb * Math.sin(chi) * 0 - B1 - k16 * qq + pp / Om;
    const b1T = fb * Math.sin(chi) * -1 + lb * Math.cos(chi) * 0.5 + A1 - k16 * pp - qq / Om;
    const kf = Math.min(1, h / k16); this.a1 += (clamp(a1T, -0.2, 0.2) - this.a1) * kf; this.b1 += (clamp(b1T, -0.2, 0.2) - this.b1) * kf;
    const Hf = 0;   // the rotor in-plane drag is already in the (1 + 4.6 mu^2) profile power term
    const Xs = -Tm * Math.sin(this.a1) - Hf * Math.cos(chi), Ys = Tm * Math.sin(this.b1) - Hf * Math.sin(chi), Zs = -Tm * Math.cos(this.a1) * Math.cos(this.b1);
    const Xr = Xs * cs - Zs * ss, Zr = Xs * ss + Zs * cs, Yr = Ys;
    const Kh = p.nb / 2 * p.hingeOffset * (p.bladeMass * (p.R - p.hingeOffset) / 2) * Om * Om;
    let F = [Xr, Yr, Zr], M = [Kh * this.b1 + (-zh) * -Yr * -1, Kh * this.a1, 0];
    M[0] = Kh * this.b1 - zh * Yr;                       // L = y Fz - z Fy  (y = 0)
    M[1] = Kh * this.a1 + zh * Xr - xh * Zr;             // M = z Fx - x Fz
    M[2] = xh * Yr + Qmain;                              // N = x Fy ; torque reaction turns the nose right
    // ---- tail rotor (thrust to the right, canted so part of it lifts)
    const xt = -(p.staT - p.staCG) / 12, zt = -(p.wlT - p.wlCG) / 12, Omt = Om * p.gearT, VTt = Omt * p.Rt, At = Math.PI * p.Rt * p.Rt, sigT = p.nbT * p.chordT / (Math.PI * p.Rt);
    const thT = p.pitchT0 - this.ctl.pedal * p.pitchTRange;
    const vnT = (v + rr * xt - pp * zt) * Math.cos(p.cant) - (w - qq * xt) * Math.sin(p.cant);      // air speed along the thrust axis (+ = rotor moving the way it pushes)
    const muT = Math.hypot(u, w) / VTt, lamT = (this.viT + vnT) / VTt;
    const CTt = clamp(0.5 * p.a * sigT * (thT * (1 / 3 + muT * muT / 2) + p.twistT / 4 - lamT / 2), -0.02, 0.03);
    const Tt = CTt * rho * At * VTt * VTt * p.blockage;
    const vht = Math.sqrt(Math.abs(Tt) / (2 * rho * At)) + 1e-6;
    this.viT += (Math.sign(Tt) * vht * inducedRatio(muT * VTt / vht, vnT / vht * Math.sign(Tt || 1)) - this.viT) * Math.min(1, h / 0.05);
    const Ptail = Math.abs(Tt) * 1.2 * Math.abs(this.viT) + rho * At * VTt * VTt * VTt * sigT * 0.0105 / 8 * (1 + 4.6 * muT * muT);
    const Yt = Tt * Math.cos(p.cant), Zt = -Tt * Math.sin(p.cant);
    F[1] += Yt; F[2] += Zt; M[0] += -zt * Yt; M[1] += -xt * Zt; M[2] += xt * Yt;
    // ---- fuselage, stabilator, fin
    const qd = 0.5 * rho * V;
    const dl = p.download * Tm * Math.exp(-Math.pow(V / (60 * KT), 2));
    F[0] += -qd * p.fx * u; F[1] += -qd * p.fy * v; F[2] += -qd * p.fz * w + dl;
    const xs = -(p.staStab - p.staCG) / 12, iS = interp(ias, [0, 30, 60, 100, 150, 200], [39, 39, 20, 5, 0, -2]) * D2R;   // PUB stabilator programming, approximate
    const wS = w - qq * xs - 0.6 * this.vi * Math.exp(-Math.pow(V / (80 * KT), 2)) - 0.4 * this.vi, uS = Math.max(Math.abs(u), 1);
    const aS = clamp(Math.atan2(wS, uS) + iS, -0.42, 0.42) , VS2 = u * u + wS * wS;
    const Zstab = -0.5 * rho * VS2 * p.stabArea * p.stabSlope * (Math.abs(aS) < 0.2 ? aS : Math.sign(aS) * 0.2);
    F[2] += Zstab; M[1] += -xs * Zstab;
    const xf = -(p.staFin - p.staCG) / 12, zf = -(p.wlFin - p.wlCG) / 12, vF = v + rr * xf - pp * zf - 0.5 * this.viT;
    const bF = clamp(Math.atan2(vF, uS) - p.finCamber, -0.35, 0.35), Yfin = -0.5 * rho * (u * u + vF * vF) * p.finArea * p.finSlope * bF;
    F[1] += Yfin; M[2] += xf * Yfin; M[0] += -zf * Yfin;
    M[1] += -0.5 * rho * V * 900 * qq; M[0] += -0.5 * rho * V * 300 * pp; M[2] += -0.5 * rho * V * 700 * rr;          // INF fuselage rate damping
    // ---- engines, governor, rotor speed
    const lapse = Math.pow(rho / 0.0023769, 0.72), Pavail = p.shpEngine * HP * Math.min(1.0, lapse);   // INF lapse, set so the TM's 94 percent hover example is available
    const Pacc = p.accessoryShp * HP * (Om / p.omega100), Pload = (Pmain + Ptail) / (1 - p.transLoss) + Pacc;
    const nOn = this.eng.filter(e => e.on).length;
    const err = p.omega100 - this.omega;
    this.govI = clamp(this.govI + err * h * 2.2e5, -4e5, 1.6e6);
    const antic = (lerp(0.42, 1.25, coll) * 1400 * HP) * 0;
    let demand = nOn ? clamp(Pload + 9e5 * err + this.govI + antic, 0, nOn * Pavail) : 0;
    demand = Math.min(demand, 2828 * HP * 1.2);
    // run-up: below flight rotor speed the engines are held to about 30 percent torque, as when the power control levers are advanced on the ground (INF rate)
    const nrNow = this.omega / p.omega100; if (nrNow < 0.97) demand = Math.min(demand, lerp(0.30, 1.2, clamp((nrNow - 0.90) / 0.07, 0, 1)) * 2 * p.shpTorque100 * HP * Math.max(nrNow, 0.08));
    let Peng = 0;
    for (const en of this.eng) {
      const tgt = en.on ? demand / nOn : 0;
      en.power += (tgt - en.power) * Math.min(1, h / (en.on ? 0.45 : 0.25));
      const ngT = en.on ? 0.66 + 0.36 * Math.sqrt(clamp(en.power / Pavail, 0, 1.1)) : 0;
      en.ng += (ngT - en.ng) * Math.min(1, h / (en.on ? 0.9 : 6.0));
      en.tgt += ((en.on ? 430 + 420 * clamp(en.power / Pavail, 0, 1.1) : 20) - en.tgt) * Math.min(1, h / 2.5);
      Peng += en.power;
    }
    this.omega = Math.max(0, this.omega + (Peng - Pload) / (p.Irotor * Math.max(this.omega, 3)) * h);
    this.psi = (this.psi + this.omega * h) % (2 * Math.PI); this.psiT = (this.psiT + this.omega * p.gearT * h) % (2 * Math.PI);
    // ---- gravity and wheels (three spring-damper points with friction)
    const Fw = [0, 0, 0].map((_, i) => Rm[i][0] * F[0] + Rm[i][1] * F[1] + Rm[i][2] * F[2]);
    Fw[2] += p.weight;
    const hg = (p.wlCG - p.wlGround) / 12, pts = [[(p.staCG - p.staMain) / 12, p.blMain, hg], [(p.staCG - p.staMain) / 12, -p.blMain, hg], [(p.staCG - p.staTail) / 12, 0, hg]];
    pts.push([8.5, 0, hg - 1.4], [-12.0, 0, hg - 1.6], [0, 3.6, hg - 1.5], [0, -3.6, hg - 1.5]);   // belly, for arrivals the wheels cannot take
    const Mw = [0, 0, 0]; const share = [0.44, 0.44, 0.12, 1.5, 1.5, 1.5, 1.5]; let deepest = 0;
    pts.forEach((r, i) => {
      const rw = [0, 1, 2].map(k => Rm[k][0] * r[0] + Rm[k][1] * r[1] + Rm[k][2] * r[2]);
      const gz = this.groundHeight ? -this.groundHeight(this.pos[0] + rw[0], this.pos[1] + rw[1]) : 0;
      const pen = this.pos[2] + rw[2] - gz; if (i < 3) this.wheelLoad[i] = 0; deepest = Math.max(deepest, pen - (i < 3 ? 1.2 : 0.3));
      if (pen > 0) {
        const wxr = [this.w[1] * r[2] - this.w[2] * r[1], this.w[2] * r[0] - this.w[0] * r[2], this.w[0] * r[1] - this.w[1] * r[0]];
        const vp = [0, 1, 2].map(k => vw[k] + Rm[k][0] * wxr[0] + Rm[k][1] * wxr[1] + Rm[k][2] * wxr[2]);
        const kS = share[i] * p.weight / 0.12, cS = 2 * 0.7 * Math.sqrt(kS * share[i] * m);
        const N = Math.max(0, kS * pen + cS * vp[2]); if (i < 3) this.wheelLoad[i] = N;
        if (i >= 3 || vp[2] > 14) this.crashed = this.crashed || vp[2] > 8;
        const sl = Math.hypot(vp[0], vp[1]), fr = Math.min(0.75 * N, (share[i] * m) * sl / h * 0.5);
        const f = [sl > 1e-4 ? -fr * vp[0] / sl : 0, sl > 1e-4 ? -fr * vp[1] / sl : 0, -N];
        Fw[0] += f[0]; Fw[1] += f[1]; Fw[2] += f[2];
        const tw = [rw[1] * f[2] - rw[2] * f[1], rw[2] * f[0] - rw[0] * f[2], rw[0] * f[1] - rw[1] * f[0]];
        for (let k = 0; k < 3; k++) Mw[k] += tw[k];
      }
    });
    for (let k = 0; k < 3; k++) M[k] += Rm[0][k] * Mw[0] + Rm[1][k] * Mw[1] + Rm[2][k] * Mw[2];
    if (deepest > 0) { this.pos[2] -= deepest; if (this.vel[2] > 0) this.vel[2] = 0; }
    // ---- integrate
    for (let k = 0; k < 3; k++) { this.vel[k] += Fw[k] / m * h; this.pos[k] += this.vel[k] * h; }
    const { Ixx, Iyy, Izz, Ixz } = p, [L, Mm, N] = M;
    const det = Ixx * Izz - Ixz * Ixz;
    const Lr = L - (Izz - Iyy) * qq * rr + Ixz * pp * qq, Nr = N - (Iyy - Ixx) * pp * qq - Ixz * qq * rr;
    const pd = (Izz * Lr + Ixz * Nr) / det, rd = (Ixz * Lr + Ixx * Nr) / det, qdot = (Mm - (Ixx - Izz) * pp * rr - Ixz * (pp * pp - rr * rr)) / Iyy;
    this.w[0] += pd * h; this.w[1] += qdot * h; this.w[2] += rd * h;
    const [a, b, cq, d] = this.q, [wx, wy, wz] = this.w;
    this.q = [a + 0.5 * h * (-b * wx - cq * wy - d * wz), b + 0.5 * h * (a * wx + cq * wz - d * wy), cq + 0.5 * h * (a * wy - b * wz + d * wx), d + 0.5 * h * (a * wz + b * wy - cq * wx)];
    const qn = Math.hypot(...this.q); this.q = this.q.map(x => x / qn);
    this.time += h;
    this._telemetry(atm, V, ias, Tm, Pmain, Ptail, mu, Mat, CT, sigma, Vc, e, Tt);
  }

  _telemetry(atm, V, ias, Tm, Pmain, Ptail, mu, Mat, CT = 0, sigma = 0.082, Vc = 0, e = null, Tt = 0) {
    const p = this.p; e = e || this.euler();
    const nr = this.omega / p.omega100, gamma = Math.atan2(-this.vel[2], Math.hypot(this.vel[0], this.vel[1]) + 1e-3);
    // blade-vortex interaction (slap) index: strongest in a shallow powered descent at 50 to 100 kt, and when the disc is loaded up
    const descent = Math.exp(-Math.pow((gamma / D2R + 6) / 4.5, 2)), speed = Math.exp(-Math.pow((ias - 75) / 38, 2));
    const nz = Tm / p.weight;
    const bvi = clamp(descent * speed * 1.1 + Math.max(0, nz - 1.15) * 1.6 * Math.min(1, ias / 50), 0, 1) * Math.min(1, nr * nr);
    this.out = {
      time: this.time, ias, u: this._u || 0, tas: V / KT, groundspeed: Math.hypot(this.vel[0], this.vel[1]) / KT, vs: -this.vel[2] * 60, agl: this.agl() - this.hcg, alt: -this.pos[2],
      pitch: e.theta, roll: e.phi, heading: (e.psi + 2 * Math.PI) % (2 * Math.PI),
      rotorPct: nr * 100, torquePct: this.eng.map(en => en.power / HP / Math.max(nr, 0.3) / p.shpTorque100 * 100),
      ngPct: this.eng.map(en => en.ng * 100), tgt: this.eng.map(en => en.tgt), shp: this.eng.reduce((s, en) => s + en.power, 0) / HP,
      thrust: Tm, loadFactor: nz, mu, tipMach: Mat, ctSigma: Math.abs(CT) / sigma, vi: this.vi, inflowClimb: Vc, coning: 0,
      a1: this.a1, b1: this.b1, bvi, tailThrust: Tt, mainPower: Pmain / HP, tailPower: Ptail / HP,
      psi: this.psi, psiTail: this.psiT, omega: this.omega, omegaTail: this.omega * p.gearT,
      onGround: this.wheelLoad[0] + this.wheelLoad[1] + this.wheelLoad[2] > 50, wheelLoad: this.wheelLoad.slice(), controls: this.ctl,
      crashed: this.crashed,
      stabilator: interp(ias, [0, 30, 60, 100, 150, 200], [39, 39, 20, 5, 0, -2]),
    };
  }

  // Position (metres) and orientation (3x3, columns = the model's +X left, +Y up, +Z forward) in the three.js world:
  // X = west... the export frame of the model: +X left of north-facing aircraft, +Y up, +Z north.
  toThree() {
    const F = 0.3048, m = this.dcm(), c = (k) => [-m[1][k], -m[2][k], m[0][k]];   // world NED -> (X = -east, Y = up, Z = north)
    const bx = c(0), by = c(1), bz = c(2);
    const X = by.map(v => -v), Y = bz.map(v => -v), Z = bx;
    // the model's origin is on the ground under the mast, not at the cg: offset by the cg position in the model frame
    const cg = [0, (this.p.wlCG - this.p.wlGround) * 0.0254, -(this.p.staCG - this.p.staHub) * 0.0254];
    const pc = [-this.pos[1] * F, -this.pos[2] * F, this.pos[0] * F];
    const o = [0, 1, 2].map(i => pc[i] - (X[i] * cg[0] + Y[i] * cg[1] + Z[i] * cg[2]));
    return { position: o, basis: [X, Y, Z] };
  }
}

// Trim helper used by the checks: steady level flight (or hover) at a true airspeed, returns torque percent per engine.
export function trim(opts) {
  const { weight = 16260, alt = 0, dT = 0, ktas = 0, wheelHeight = null, climbFpm = 0, enginesOn = true, seconds = 60 } = opts;
  const f = new UH60Flight({ params: { weight }, dT });
  const hgt = wheelHeight != null ? wheelHeight + f.hcg : 3000;
  f.groundAlt = alt; f.pos = [0, 0, -hgt]; f.vel = [ktas * KT, 0, -climbFpm / 60];
  if (!enginesOn) f.eng.forEach(e => { e.on = false; });
  let coll = 0.45, iz = 0, lonI = 0; const c = { collective: coll, lon: 0, lat: 0, pedal: 0, fps: true };
  let acc = { trq: 0, n: 0, vs: 0, nr: 0, pitch: 0, coll: 0, shp: 0 };
  const dt = 1 / 60;
  for (let t = 0; t < seconds; t += dt) {
    const o = f.out;
    if (enginesOn) {                                   // hold the flight path with collective, speed with pitch
      const zErr = (hgt + climbFpm / 60 * t) + f.pos[2];       // + = too low
      iz = clamp(iz + zErr * dt * 0.01, -0.5, 0.5);
      c.collective = clamp(0.45 + iz + 0.02 * zErr + 0.0004 * (climbFpm - o.vs), 0, 1);
    } else { c.collective = clamp(opts.collective ?? 0.0, 0, 1); }
    const spErr = ktas - o.u; lonI = clamp(lonI + spErr * dt * 0.004, -0.6, 0.6);
    c.lon = clamp(0.02 * spErr + lonI + (opts.lonBias || 0), -1, 1);
    f.step(dt, c);
    if (t > seconds - 10) { acc.trq += (o.torquePct[0] + o.torquePct[1]) / 2; acc.vs += o.vs; acc.nr += o.rotorPct; acc.pitch += o.pitch; acc.coll += c.collective; acc.shp += o.shp; acc.n++; }
  }
  const k = 1 / acc.n;
  return { torquePct: acc.trq * k, vs: acc.vs * k, rotorPct: acc.nr * k, pitchDeg: acc.pitch * k / D2R, collective: acc.coll * k, shp: acc.shp * k, tas: f.out.tas, ias: f.out.ias };
}
