# Grenades: throw, bounce, roll, fuse and cook-off

A grenade in flight is a point mass with quadratic air drag and a contact radius. It bounces on the ground and on
walls, rolls to rest, and carries a fuse timer. Credit: carpetshark. Simulation by Claude.

| File | What it is |
|---|---|
| `sim.py` | The reference simulation. Calibrates release speeds, samples fuses, runs reference throws, writes `throw.json`. |
| `throw.json` | Constants, ground table, per-variant body and calibration, reference runs, Python checks. |
| `grenades-throw.js` | Browser and node runtime (`window.GrenadeThrow`). The same integrator as `sim.py`. |
| `test.js`, `check.json` | The runtime against `throw.json` and the published figures; results committed. |

Rebuild from `assets/grenades/`: `python3 throw/sim.py`, then `node throw/test.js`. Needs Python 3 and node only.

## Model

- **Drag.** a = g - k |v| v, k = rho Cd A / 2m. Mass is the published weight. A sphere uses Cd 0.47 on its frontal
  area; a can or the flash body tumbles, so it uses Cd 0.80 on its mean projected area, surface / 4 (Cauchy).
  Cd values are textbook estimates (Hoerner). RK4 at 1/240 s.
- **Release.** The manual publishes an average throwing distance, not a release speed. The release is taken as 40 deg
  above the horizon from 1.8 m (estimate), and the speed is solved so the first landing on level ground is the
  published distance. `power` scales that speed.
- **Bounce.** At a contact the normal speed is reversed and scaled by the ground's restitution e; the tangential
  speed loses mu (1 + e) |v_n| (sliding friction, no spin). A rebound slower than 0.35 m/s becomes a roll.
- **Roll.** Constant deceleration mu_r g, times 3 for a can (it tumbles) and 4 for the flash (its hexagon ends).
- **Fuse.** The delay is sampled inside the published window (triangular, a game choice of shape). Smoke burn time is
  sampled inside its window; the coloured can's has the published 60 s mean.
- **Cook-off** is a game mechanic: the delay starts when the lever is released, so releasing it in the hand and
  waiting shortens what is left after the throw; waiting too long functions it in the hand.
- **Impact** (game-only): no delay. After 0.35 s in flight it functions on the first contact faster than 2 m/s,
  or after 6 s. All three numbers are game tuning.

| Ground (estimates) | e | mu | mu_r |
|---|---|---|---|
| concrete | 0.50 | 0.45 | 0.05 |
| steel plate | 0.55 | 0.35 | 0.04 |
| wood floor | 0.45 | 0.40 | 0.06 |
| packed dirt | 0.30 | 0.55 | 0.12 |
| grass | 0.20 | 0.60 | 0.25 |
| sand | 0.05 | 0.70 | 0.60 |
| mud | 0.02 | 0.80 | 0.90 |

## Results

| Variant | Weight (published) | Release speed | First landing | Published | Flight | Rest on dirt / concrete |
|---|---|---|---|---|---|---|
| frag | 14 oz | 18.70 m/s | 35.00 m | 35 m | 2.56 s | 38.2 / 40.6 m |
| impact (game-only) | 14 oz | 18.70 m/s | 35.00 m | 35 m (game) | 2.56 s | functions on landing |
| flash | 13.3 oz | 19.51 m/s | 35.00 m | none; 35 m inferred | 2.61 s | 37.2 / 39.3 m |
| smoke (coloured) | 19 oz | 20.24 m/s | 35.00 m | 35 m | 2.65 s | 36.6 / 38.3 m |
| smoke-white | 24 oz | 17.98 m/s | 30.00 m | 30 m | 2.42 s | 31.8 / 33.6 m |

## Checks (`check.json`: 18 Python and 39 JS checks, all passed)

- First landing equals the published distance for every variant. This is a calibration, so it shows the solver and
  the JS port are right, not that the drag model is.
- **Independent check:** the coloured can (19 oz, 35 m) and the white can (24 oz, 30 m) are separate published rows.
  Throwing the white can with the release energy calibrated on the coloured one (110 J) lands it at 30.09 m against
  the published 30 m.
- 20,000 sampled delays per variant sit inside the published windows; 20,000 burn times inside theirs, with a mean
  of 60.0 s for the coloured can (published average 60).
- JS against Python: every 0.1 s sample of each reference flight within 1e-5 m, rest points within 1e-6 m on three
  grounds, and the same random stream.
- Handling: thrown at once, cooked 2 s, cooked too long (in the hand), pin not pulled (nothing happens); impact on
  landing, and impact bouncing off a wall inside its arming time.

## Runtime

```js
await GrenadeThrow.load('assets/grenades/throw/throw.json');
const g = new GrenadeThrow.Grenade('frag', { seed: 1, surface: 'concrete', walls: [{ point: [8, 0, 0], normal: [-1, 0, 0], surface: 'concrete' }] });
g.pullPin();                                   // then optionally g.releaseLever() and wait: cooking
g.throwFrom(handPos, GrenadeThrow.releaseVelocity('frag', aimDir, power));
for (const e of g.update(dt)) { /* e.type: 'bounce' | 'rest' | 'function' (kind 'detonate' | 'ignite', inHand) | 'burnout' */ }
g.pos; g.remaining();                          // position now, seconds of delay left
```

`GrenadeThrow.Flight` is the bare projectile (`step()`, `run()`), `sampleDelay` and `sampleBurn` the fuse samplers.
Variants: `frag`, `impact`, `flash`, `smoke-red|yellow|green|violet`, `smoke-white`.

## Limits

No spin, no rolling on slopes, the ground is the plane y = 0 and walls are planes. Ground numbers and Cd are
estimates. The release angle and height are assumed, so the release speeds are "the speed that gives the published
distance at 40 deg", not measured throws. The lighter grenades come out with less release energy (69 to 72 J) than
the cans (110 J): a light object is limited by arm speed, which this model does not represent.
