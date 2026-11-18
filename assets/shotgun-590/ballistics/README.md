# Shotgun 590: exterior ballistics

Flight of a 1 oz rifled slug and of nine-pellet 00 buckshot from the muzzle: drag, gravity, wind, and the pattern.
Credit: carpetshark.

```
python3 ballistics/sim.py      # writes ballistics.json and plots/
node ballistics/test.js        # checks shotgun590-ballistics.js against ballistics.json and the published table
```

| File | What it is |
|---|---|
| `sim.py` | the simulation; loads, sights and the pattern rule each carry their source |
| `ballistics.json` | loads, drag tables, downrange tables, sight geometry, pattern calibration, checks, seeded reference scatter |
| `shotgun590-ballistics.js` | the runtime: `fire()`, `table()`, `pattern()`, `aim()`, `extremeSpread()`, `rng()` |
| `test.js` | 9 Node checks |
| `plots/` | slug against the published table; velocity and energy of both loads; sample patterns |

## Loads

| | Slug | 00 buck |
|---|---|---|
| Published by | Federal Premium, Power-Shok F127 RS | Federal Premium, Power-Shok F127 00 |
| Projectiles | one, 438 gr (28.4 g) | nine lead balls, .33 in, 3.50 g each (derived from the published density, 11.35 g/cc) |
| Muzzle velocity | 1610 ft/s (490.7 m/s) | 1325 ft/s (403.9 m/s) |
| Drag | G1, ballistic coefficient .110 (published) | a sphere's drag against Mach number (approximate, recalled from the sphere-drag literature, about 10 % of doubt) |
| Muzzle energy | 3417 J | 2569 J for the nine |

Published shotshell speeds are test-barrel figures. They are used unchanged; `action/README.md` gives an estimate
of what a 20 in barrel loses (about 6 %), which is not applied.

## Method

Each projectile is a point mass: `dv/dt = -k rho Cd(M) |v - wind| (v - wind) + g`, with `k = pi / (8 BC)` for the slug
(BC in kg/m2) and `k = A / (2 m)` for a pellet. Fourth-order Runge-Kutta, 0.25 ms steps in `sim.py`, 0.5 ms in the
module. ICAO standard air at sea level unless `env` says otherwise. No spin, no Coriolis, no terminal effects.

**Pattern.** Each pellet leaves with an independent angular error, normal on each axis with standard deviation
7.50 mrad. That number is fitted so the mean extreme spread of nine pellets is 1 in per yard, the published rule of
thumb for a cylinder bore (R. Mann, Shooting Illustrated, 2012). `spreadScale` multiplies it: the same article
reports loads patterning at half the rule.

**Sights.** `aim(lineOfSight, 'bead_flat')` returns the bore direction for a shooter who sees the bead resting on the
receiver's flat top. From the model's traced geometry the bore then points 14.9 mrad above the line of sight, so shots
land high: 0.21 m at 15 m and 0.41 m at 30 m for the slug. This is an inference from a bead that is 2 px tall in the
photo (about 1.5 mrad of doubt), not a published figure; `aim(los, 'bore')` aims along the bore.

## Results (level bore)

| Range | 10 m | 25 m | 50 m | 100 m |
|---|---|---|---|---|
| Slug: speed, energy, drop | 471 m/s, 3147 J, 2 mm | 443 m/s, 2782 J, 14 mm | 400 m/s, 2275 J, 59 mm | 337 m/s, 1607 J, 271 mm |
| Pellet: speed, energy each, drop | 369 m/s, 238 J, 3 mm | 326 m/s, 186 J, 22 mm | 275 m/s, 133 J, 102 mm | 209 m/s, 77 J, 531 mm |

## Checks

| Check | Result |
|---|---|
| **Slug against Federal's published table** (100 yd zero, sights 0.5 in above the bore, 10 mph crosswind; 25 to 125 yd) | velocity within 0.55 %, path within 0.04 in, wind drift within 0.25 in. **Pass.** |
| Pattern against the 1 in per yard rule at 7, 15, 25 and 40 yd | means 7.05, 15.06, 25.02 and 40.25 in. This is the fit showing itself, not an independent test. One shot in ten is tighter than 11.5 in or wider than 19 in at 15 yd. |
| Pellets on an 18 x 30 in plate (our choice of plate) | 9.0 of 9 at 10 yd, 8.1 at 20 yd, 6.2 at 30 yd, 4.5 at 40 yd; all nine on in 40 % of shots at 20 yd. The article says at least one pellet will likely miss a man-size target beyond 20 yd and half are hard to keep on beyond 30: the same picture, a little kinder at 30 yd. |
| `test.js` | 9 of 9: tables against `sim.py` (0.002 %), the slug against the published speeds, seeded scatter against `sim.py`, the spread rule over 600 shots (15.02 in at 15 yd), pellet count and mass, `advance()` against `trace()`, wind drift 6.8 in against the published 6.6 in at 100 yd, the bead's bore angle |

## Runtime

```js
const B = Shotgun590Ballistics; await B.load('assets/shotgun-590/ballistics/ballistics.json');
const a = B.aim(lineOfSight, 'bead_flat');                       // or 'bore'
const shot = B.fire({ origin: muzzle, dir: a.dir, load: 'buck00', rng: B.rng(seed), wind: [2, 0, 0] });
shot.advance(dt);                                                // per frame: shot.projectiles[i].pos / .vel / .alive
const hits = shot.trace([{ point: [0, 0, 20], normal: [0, 0, -1] }]);   // or all crossings at once: pos, vel, speed, energy, t
```

Set `projectile.alive = false` when your own collision code stops one. `fire()` takes `muzzleVelocity`,
`spreadScale`, `scatter` (explicit angles) and `env: { rho, c, g }`.

## Limits

- No published downrange or pattern data exists for this buckshot load; only its muzzle figures are checked. The
  sphere drag curve is approximate and a real pellet, flattened by firing, slows faster.
- The pattern is a single normal scatter: no fliers, no shot string, no wad, no choke other than through `spreadScale`.
- No penetration, ricochet or wounding model. Energy at impact is what the module reports.
- Flight uses the published test-barrel speeds, not a 20 in figure.
