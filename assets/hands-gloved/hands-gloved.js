/* Gloved first-person hands for the HK416: skeleton, grips and clips. Evaluates hands-gloved.json. No dependencies.
 *
 *   <script src="hands-gloved.js"></script>             -> window.HandsGloved
 *   const HandsGloved = require('./hands-gloved.js')     (Node)
 *
 *   await HandsGloved.load('hands-gloved.json')          // or HandsGloved.use(parsedJson)
 *   const s = HandsGloved.sample('charge', t)            // t seconds from the start of the HAND clip
 *   // s.rifleClip, s.rifleTime (seconds into the rifle's clip, null before it starts), s.R and s.L:
 *   //   .hand, .forearm   [x, y, z, qx, qy, qz, qw]   metres + quaternion in the rifle frame
 *   //   .angles           { index_mcp_flex: degrees, ... }  (HandsGloved.angles lists the 23 names)
 *   //   .bones            { forearm: m, hand: m, index_meta: m, index_01: m, ... }  4x4 world matrices, row-major
 *   const g = HandsGloved.grip('support')                // a static grip: { side, hand, forearm, angles, bones }
 *   HandsGloved.checkLimits(s.R.angles)                  // [] or [{ joint, value, min, max }]
 *   HandsGloved.landmark(s.R, 'index_tip')               // [x, y, z] of a named point of the hand
 *
 * Frame: the rifle's (assets/hk416): metres, +X shooter's left, +Y up, +Z to the muzzle, origin on the bore axis at
 * the upper receiver's front face. Clips run at 24 frames per second, the rifle's rate. A hand clip may start
 * `pre_roll` frames before its rifle clip: start the rifle clip when s.rifleTime turns from null to 0.
 * Bones: Y along the bone toward the fingertip, Z out of the back of the hand. A matrix m maps bone coordinates to
 * the rifle frame: x' = m[0]*x + m[1]*y + m[2]*z + m[3], and so on (translation in m[3], m[7], m[11]).
 * The skeleton is stored for a LEFT hand; the right hand is its mirror image in x.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.HandsGloved = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var D = null, RAD = Math.PI / 180, B = null, IDX = null, LOCAL = null, AI = null;
  var FING = ['index', 'middle', 'ring', 'little'];

  function need() { if (!D) throw new Error('HandsGloved: call use(data) or load(url) first'); return D; }

  /* ---- 4x4 helpers, row-major arrays of 16 */
  function mul(a, b) {
    var o = new Array(16);
    for (var r = 0; r < 4; r++) for (var c = 0; c < 4; c++)
      o[r * 4 + c] = a[r * 4] * b[c] + a[r * 4 + 1] * b[4 + c] + a[r * 4 + 2] * b[8 + c] + a[r * 4 + 3] * b[12 + c];
    return o;
  }
  function invRigid(m) {
    var o = [m[0], m[4], m[8], 0, m[1], m[5], m[9], 0, m[2], m[6], m[10], 0, 0, 0, 0, 1];
    o[3] = -(o[0] * m[3] + o[1] * m[7] + o[2] * m[11]); o[7] = -(o[4] * m[3] + o[5] * m[7] + o[6] * m[11]); o[11] = -(o[8] * m[3] + o[9] * m[7] + o[10] * m[11]);
    return o;
  }
  function rotX(a) { var c = Math.cos(a), s = Math.sin(a); return [1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1]; }
  function rotY(a) { var c = Math.cos(a), s = Math.sin(a); return [c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0, 0, 0, 0, 1]; }
  function rotZ(a) { var c = Math.cos(a), s = Math.sin(a); return [c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; }
  function fromPQ(p) {
    var x = p[3], y = p[4], z = p[5], w = p[6];
    return [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), p[0],
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), p[1],
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), p[2], 0, 0, 0, 1];
  }
  /* mirror in x on both sides: M m M with M = diag(-1, 1, 1, 1); maps a left-hand matrix to the right hand and back */
  function mirror(m) { return [m[0], -m[1], -m[2], -m[3], -m[4], m[5], m[6], m[7], -m[8], m[9], m[10], m[11], 0, 0, 0, 1]; }

  function use(data) {
    D = data; B = data.skeleton.bones; IDX = {}; AI = {};
    B.forEach(function (b, i) { IDX[b.name] = i; b.m = [].concat.apply([], b.rest); });
    data.angles.forEach(function (a, i) { AI[a] = i; });
    LOCAL = B.map(function (b) { return b.parent ? mul(invRigid(B[IDX[b.parent]].m), b.m) : b.m.slice(); });
    return api;
  }
  function load(url) { return fetch(url).then(function (r) { return r.json(); }).then(use); }

  /* local rotation of every bone in its own rest frame, from the 23 joint angles (degrees); left-hand convention */
  function localRot(q) {
    var R = {}, d = need();
    FING.forEach(function (f) {
      R[f + '_01'] = mul(rotZ(-q[AI[f + '_mcp_abd']] * RAD), rotX(-q[AI[f + '_mcp_flex']] * RAD));
      R[f + '_02'] = rotX(-q[AI[f + '_pip_flex']] * RAD); R[f + '_03'] = rotX(-q[AI[f + '_dip_flex']] * RAD);
    });
    R.ring_meta = rotX(-q[AI.mc4_flex] * RAD); R.little_meta = rotX(-q[AI.mc5_flex] * RAD);
    R.thumb_01 = mul(mul(rotZ(q[AI.thumb_cmc_abd] * RAD), rotY(q[AI.thumb_cmc_rot] * RAD)), rotX(-q[AI.thumb_cmc_flex] * RAD));
    R.thumb_02 = rotX(-q[AI.thumb_mcp_flex] * RAD); R.thumb_03 = rotX(-q[AI.thumb_ip_flex] * RAD);
    return R;
  }
  /* forward kinematics. side 'L' or 'R'; hand and forearm are [x,y,z,qx,qy,qz,qw] in the rifle frame; q = 23 angles */
  function fk(side, hand, forearm, q) {
    need(); var H = fromPQ(hand), F = fromPQ(forearm), right = side === 'R';
    if (right) { H = mirror(H); F = mirror(F); }
    var R = localRot(q), W = new Array(B.length), out = {};
    B.forEach(function (b, i) {
      if (b.name === 'hand') W[i] = H;
      else if (b.name === 'forearm') W[i] = F;
      else { W[i] = mul(W[IDX[b.parent]], LOCAL[i]); if (R[b.name]) W[i] = mul(W[i], R[b.name]); }
    });
    B.forEach(function (b, i) { out[b.name] = right ? mirror(W[i]) : W[i]; });
    return out;
  }
  function named(q) { var o = {}; need().angles.forEach(function (a, i) { o[a] = q[i]; }); return o; }
  function build(side, hand, forearm, q) { return { side: side, hand: hand, forearm: forearm, angleList: q, angles: named(q), bones: fk(side, hand, forearm, q) }; }

  function lerpPQ(a, b, u) {
    var o = new Array(7), i, dot = a[3] * b[3] + a[4] * b[4] + a[5] * b[5] + a[6] * b[6], s = dot < 0 ? -1 : 1, n = 0;
    for (i = 0; i < 3; i++) o[i] = a[i] + (b[i] - a[i]) * u;
    for (i = 3; i < 7; i++) { o[i] = a[i] + (s * b[i] - a[i]) * u; n += o[i] * o[i]; }
    n = Math.sqrt(n); for (i = 3; i < 7; i++) o[i] /= n;
    return o;
  }
  function lerpA(a, b, u) { return a.map(function (v, i) { return v + (b[i] - v) * u; }); }

  /* a clip at time t (seconds from the start of the hand clip); clamps at both ends */
  function sample(name, t) {
    var c = need().clips[name]; if (!c) throw new Error('HandsGloved: no clip ' + name);
    var u = Math.max(0, Math.min((t || 0) * D.fps, c.frames - 1)), i = Math.floor(u), j = Math.min(i + 1, c.frames - 1), w = u - i, out = { clip: name, frame: u + 1 };
    ['R', 'L'].forEach(function (s) {
      var a = c[s][i], b = c[s][j];
      out[s] = build(s, lerpPQ(a.hand, b.hand, w), lerpPQ(a.forearm, b.forearm, w), lerpA(a.angles, b.angles, w));
    });
    out.rifleClip = c.rifle_clip; var rt = (u - c.pre_roll) / D.fps;
    out.rifleTime = c.rifle_clip ? (rt < 0 ? null : Math.min(rt, (c.rifle_frames - 1) / D.fps)) : null;
    out.rifleFrame = c.rifle_clip ? Math.max(1, Math.min(u - c.pre_roll + 1, c.rifle_frames)) : null;
    return out;
  }
  function grip(name) {
    var g = need().grips[name]; if (!g) throw new Error('HandsGloved: no grip ' + name);
    return build(g.side, g.hand, g.forearm, g.angles);
  }
  function duration(name) { var c = need().clips[name]; return (c.frames - 1) / D.fps; }

  /* joint limits: every one of the 23 angles against its range */
  function limitOf(a) { var L = need().limits_deg; return L[a] || L[a.slice(a.indexOf('_') + 1)]; }
  function checkLimits(angles) {
    var bad = []; need().angles.forEach(function (a) {
      var v = angles[a], L = limitOf(a);
      if (v < L.min - 1e-6 || v > L.max + 1e-6) bad.push({ joint: a, value: v, min: L.min, max: L.max });
    });
    return bad;
  }
  /* a named point of the hand (fingertips, pads, knuckles: HandsGloved.data.landmarks) in the rifle frame */
  function landmark(pose, name) {
    var lm = need().landmarks[name]; if (!lm) throw new Error('HandsGloved: no landmark ' + name);
    var p = lm.position, m = pose.bones[lm.bone], i = IDX[lm.bone];
    var x = p[0], y = p[1], z = p[2], r = invRigid(B[i].m);            // canonical rest position -> bone coordinates
    var bx = r[0] * x + r[1] * y + r[2] * z + r[3], by = r[4] * x + r[5] * y + r[6] * z + r[7], bz = r[8] * x + r[9] * y + r[10] * z + r[11];
    if (pose.side === 'R') {                                            // the right hand's bone frame is the mirrored one
      var W = mirror(m), wx = W[0] * bx + W[1] * by + W[2] * bz + W[3], wy = W[4] * bx + W[5] * by + W[6] * bz + W[7], wz = W[8] * bx + W[9] * by + W[10] * bz + W[11];
      return [-wx, wy, wz];
    }
    return [m[0] * bx + m[1] * by + m[2] * bz + m[3], m[4] * bx + m[5] * by + m[6] * bz + m[7], m[8] * bx + m[9] * by + m[10] * bz + m[11]];
  }
  /* the far end of a bone (its tip) in the rifle frame */
  function boneEnd(pose, name) { var m = pose.bones[name], L = B[IDX[name]].length; return [m[1] * L + m[3], m[5] * L + m[7], m[9] * L + m[11]]; }

  var api = {
    use: use, load: load, sample: sample, grip: grip, duration: duration, fk: fk, checkLimits: checkLimits, limitOf: limitOf, landmark: landmark, boneEnd: boneEnd,
    get data() { return D; },
    get fps() { return need().fps; },
    get angles() { return need().angles.slice(); },
    get clips() { return Object.keys(need().clips); },
    get grips() { return Object.keys(need().grips); },
    get bones() { return need().skeleton.bones.map(function (b) { return b.name; }); }
  };
  return api;
});
