# HK416 D14.5RS ballistics: external and terminal

A physical simulation of the bullets fired from the HK416 model in this folder, as data plus a small runtime module. Sport and range terms only: paper, steel plates, earth. Credit: carpetshark.

| File | What it is |
|---|---|
| `sim.py` | The simulation. `python3 sim.py` rewrites everything below (Python 3 with numpy, scipy, matplotlib; about a minute). |
| `ballistics.json` | Range tables per ammunition and zero, dispersion, terminal-effect tables, validation results. SI units; keys carry `_mm`, `_deg`, `_moa` where they differ. |
| `hk416-ballistics.js` | Self-contained runtime (no three.js). Its `DATA` block is written by `sim.py`, so the two never disagree. |
| `test.js` | `node test.js` checks the runtime against `ballistics.json` and times it. |
| `plots/` | Eight figures. |

Muzzle velocity is a parameter. When the action model lands: `python3 sim.py --action-json ../action/action.json --action-key <dotted.key>` (or `--mv-m855 <m/s>`), and at runtime `HK416Ballistics.configure({muzzleVelocity: <M855 m/s>})`. The other loads scale by the same ratio.

## Headline result for the game

With HK's own zero (100 yd on the V notch) a shot aimed through the sights lands **low** at every game distance, because the bore sits 65.5 mm under the sights and the paths only meet at 91 m.

Point of impact relative to point of aim, M855, default zero `hk100yd`, distance measured from `socket_ads_eye`:

| Distance | 10 m | 15 m | 20 m | 25 m | 35 m | 45 m | 55 m | 62 m (berm) |
|---|---|---|---|---|---|---|---|---|
| Impact (mm) | -53 | -47 | -41 | -36 | -26 | -18 | -11 | -7 |
| Speed (m/s) | 840 | 835 | 830 | 825 | 815 | 805 | 794 | 787 |
| Energy (J) | 1418 | 1401 | 1384 | 1367 | 1333 | 1300 | 1268 | 1246 |
| Flight time (ms) | 11 | 17 | 23 | 29 | 41 | 54 | 66 | 75 |

Other zeros, M855, same distances 10 / 15 / 25 / 35 / 45 / 55 m (mm):

| Zero | Bore angle | 10 | 15 | 25 | 35 | 45 | 55 | Crosses the sight line at |
|---|---|---|---|---|---|---|---|---|
| `hk100yd` (default, HK manual) | 1.387 mrad (4.77 MOA) | -53 | -47 | -36 | -26 | -18 | -11 | 91 m (touches; peak 0 mm) |
| `50_200` | 1.676 mrad | -50 | -43 | -29 | -16 | -5 | +5 | 50 m and 164 m |
| `25_300` | 2.856 mrad | -39 | -26 | 0 | +24 | +47 | +69 | 25 m and 297 m |
| `hk200yd` (diopter 2) | 1.809 mrad | -49 | -41 | -26 | -12 | +1 | +12 | 44 m and 183 m |
| `hk300yd` (diopter 3) | 2.617 mrad | -42 | -29 | -6 | +16 | +37 | +56 | 28 m and 274 m |
| `hk400yd` (diopter 4) | 3.667 mrad | -32 | -14 | +20 | +52 | +83 | +113 | 19 m and 366 m |

Two things the tables say that are worth knowing:

- With HK's 850 m/s, the "50/200" zero actually comes back down through the sight line at 164 m, not 200 m, and "25/300" at 297 m. Those names come from faster 20 in and 16 in barrels.
- Mk 262 with the same zero lands within 3 mm of M855 at these distances (-52, -45, -33, -23, -15, -8 mm).

On a 10-ring of a few centimetres, 53 mm low at 10 m is the difference between a bullseye and a seven. A real shooter holds a little high up close.

## Physics

**Drag.** Point-mass trajectory. Drag deceleration `a = (pi/8) rho v^2 Cd_G7(Mach) / BC`, with `BC` in kg/m² (lb/in² x 703.07) and `v` taken relative to the air, so wind enters naturally. `Cd_G7` is the standard G7 drag function, 84 knots, linear in Mach. Gravity 9.80665 m/s².

**Atmosphere.** ICAO standard by default (15 °C, 1013.25 hPa, dry: 1.2250 kg/m³, 340.3 m/s). Temperature, station pressure, relative humidity and altitude are parameters; density from the ideal-gas mixture of dry air and vapour (Buck saturation pressure), speed of sound from the mixture's molar mass and heat-capacity ratio.

**Integration.** `sim.py`: scipy DOP853, tolerances 1e-10, step capped at 4 ms so the kinks in the drag table are resolved. Runtime: fixed-step RK4 at 1 ms with cubic Hermite interpolation. The two agree to 0.007 m/s and 0.04 mm in drop over every table row out to 600 m.

**Spin drift and Coriolis: do they matter?** No at game ranges, barely at 600 m.

| M855 | 55 m | 100 m | 300 m | 600 m |
|---|---|---|---|---|
| 10 mph (4.5 m/s) full crosswind | 10 mm | 34 mm | 0.35 m | 1.80 m |
| Spin drift, to the right (Litz fit, Miller Sg 2.41) | 0.8 mm | 2.6 mm | 25 mm | 139 mm |
| Coriolis at 45° N, to the right | 0.2 mm | 0.6 mm | 6 mm | 29 mm |

Spin drift is in the runtime because it's nearly free (on by default; `configure({spinDrift:false})`). Coriolis is in `sim.py` only. Wind dwarfs both.

**Sights and zero.** In `hk416.glb` the rear aperture centre, the front post tip and `socket_ads_eye` all sit 65.5 mm above the bore and the sight line is parallel to the bore, so the model as built has no zero. The simulation tilts the bore up by the zero angle about the muzzle. On a real rifle that's the rear aperture rising: 0.505 mm for the 100 yd zero over the 364 mm sight radius. Zero distances and the point-of-impact tables are measured from the eye; range tables are measured from the muzzle crown (0.624 m ahead of the eye).

**Dispersion.** A circular normal distribution in angle. The rifle-plus-ammunition term and the shooter term add in quadrature. A 10-shot extreme spread converts to a per-axis sigma by dividing by 3.817 (Monte Carlo, 40,000 groups; 5 shots: 3.071). Muzzle velocity also varies shot to shot (M855 sigma 7.5 m/s), which matters only at long range.

| | 10-shot group | Per-axis sigma | At 25 m (sigma) |
|---|---|---|---|
| M855, rifle and ammunition | 3.0 MOA | 0.79 MOA | 6 mm |
| Mk 262 | 1.5 MOA | 0.39 MOA | 3 mm |
| M856 tracer | 5.0 MOA | 1.31 MOA | 10 mm |
| Shooter, aimed and supported | | 1.2 MOA | 9 mm |
| Shooter, aimed standing | | 4.0 MOA | 29 mm |
| Shooter, hip | | 60 MOA (1°) | 0.44 m |

For comparison the range page today uses a uniform cone: about 1.5 MOA sigma aimed and 0.41° at the hip.

**Paper.** Hole 4.84 mm (0.85 calibre: the fibres close back behind a pointed bullet), grease ring 5.69 mm. An oblique hit stretches the hole by 1/sin(angle); a yawed bullet prints `d cos(yaw) + L sin(yaw)` (M855 at 5°: 7.7 mm; sideways: 23 mm). Paper takes essentially nothing from the bullet, so it carries on to the berm.

**Steel plate.** The bullet breaks up on the face and its fragments leave along the plate, so the plate takes the bullet's normal momentum once: `p = m v sin(angle)`. For a round plate of radius `r` hinged along its bottom edge, `I = m r²/4 + m r² = 1.25 m r²`, and a hit at height `h` above the hinge starts it swinging at `omega = p h / I`. Whether it falls depends on how far it leans toward the shooter at rest: it must climb `m g r (1 - cos(lean))`. After that it's a pendulum falling from the top. Centre hits at 35 m, 10 mm plate, 2° rest lean:

| Plate radius | Mass | M855 swing rate | Largest lean it still topples from | Time to fall flat | Mk 262 swing rate |
|---|---|---|---|---|---|
| 0.18 m | 8.0 kg | 1.82 rad/s | 15.9° | 0.40 s | 2.06 rad/s |
| 0.20 m | 9.9 kg | 1.33 rad/s | 12.2° | 0.47 s | 1.50 rad/s |
| 0.25 m | 15.4 kg | 0.68 rad/s | 7.0° | 0.65 s | 0.77 rad/s |
| 0.30 m | 22.2 kg | 0.39 rad/s | 4.4° | 0.85 s | 0.45 rad/s |

So the big plates fall slowly and only if they rest nearly upright; a low hit on a 0.30 m plate may just rock it. The heavier Mk 262 kicks plates 13 percent harder despite its lower energy, because plates respond to momentum. The plate's swing takes under 0.05 percent of the bullet's energy (0.2 to 0.7 J of about 1,330 J); the rest breaks and heats the bullet and makes the splash and the sound.

For the sound model: the force on the plate is modelled as a half-sine pulse lasting `bullet length / impact speed`, about 28 µs for M855 at 815 m/s, carrying 3.27 N·s, so the peak is about 180 kN. Its bandwidth (about 35 kHz) is far above the audible range, so the hit excites every plate mode you can hear. `impact()` returns `plateImpulse`, `contactTime` and `peakForce` per hit.

Splash: fragments leave within about 20° of the plate face, at 0.35 to 0.9 of the impact speed, slowing with a 35 ms time constant; an oblique hit throws them forward. M855's steel tip sparks on steel (probability 0.8 at full speed); copper and lead rarely do. Below about 12° from the face the bullet glances off mostly whole. M855 pits the plate above 640 m/s normal speed in this model (lead core: 870 m/s), so every M855 hit here leaves a small pit, about 0.7 mm at 815 m/s.

**Earth.** Poncelet penetration, `depth = m / (2 C rho A) ln(1 + C rho v² / R)`, with the presented area 2.5 times the bullet's cross-section because it tumbles: 11 to 12 cm for M855 at 700 to 850 m/s in the ground, 12 to 13 cm in the looser berm, 14 to 16 cm for Mk 262. Depth barely changes with speed, which is how soil behaves. Dust: scar width and plume height scale with deposited energy to the 1/3 power: a 1,300 J strike on dry dirt gives a 10 cm scar and a puff about 0.8 m high and half as wide that hangs for 1.5 s; damp earth gives less dust and clods instead.

Ricochet off earth: 92 percent at 3° from the surface, 50 percent at 8°, 3 percent at 15°. From a 1.6 m eye height the ground is struck at 4.6° at 20 m and 1.8° at 50 m, so a low shot nearly always skips, leaves about 1.3 times steeper than it arrived, tumbling (three times the drag), keeps roughly 0.9 of its speed at 3°, and ends in the berm. The runtime continues it as a new shot.

**What the shooter can see.** Honestly: almost nothing. A 5.7 mm ball round at 800 m/s is not visible to the naked eye over iron sights. "Trace" is the refracting wake seen from behind through a spotting scope or a magnified optic in good light, usually past 100 m, which the game's range never reaches. A faint condensation streak needs air near saturation (over 90 percent humidity here) and lasts tens of milliseconds. `visibility()` returns `nakedEye: false` for ball in normal air. The bullet stays supersonic to 608 m (Mk 262: 666 m), so the crack exists at every game distance: `sonicCrack()` gives the Whitham N-wave (about 154 dB peak and 0.1 ms long one metre from the path at Mach 2.45; Mach cone half-angle 24°).

M856 tracer is included as an option. Its trace is specified from about 75 yd to at least 875 yd, so on a 62 m range a real tracer is only starting to show as it reaches the berm. The runtime lights it dimly from 15 m (inferred) to full brightness at 70 m.

## Parameters and sources

Fact = from a primary or published source. Recalled = a published figure quoted from memory, not re-checked today. Inferred = my estimate.

| Parameter | Value | Status and source |
|---|---|---|
| Barrel, twist | 14.5 in (368.3 mm), 1 in 7 in right hand | Fact: HK, *Maintenance Manual for HK416 Enhanced Carbine & Rifle System* (HK USA Training Group), p. 7, via `../MANUAL_NOTES.md` |
| Muzzle velocity, M855 | 850 m/s (2,790 ft/s) | Fact: HK manual p. 7 for the 14.5 in barrel. The manual doesn't name the load; taken as M855/SS109 class. US figures for the M4 are higher (2,916 to 2,970 ft/s) |
| Sights | zero at 100 yd on the V notch; diopters 2, 3, 4 for 200, 300, 400 yd; quarter turn about 1.5 in at 100 yd | Fact: HK manual pp. 13 to 15 |
| Effective range | 500 m point, 600 m area | Fact: HK manual p. 7 (the model is run out to 600 m) |
| Sight height over bore | 65.5 mm | Measured from `hk416.glb` (`rear_sight_aperture`, `front_sight_post`, `socket_ads_eye`) |
| Sight radius | 364.0 mm | Measured from `hk416.glb` |
| Eye to muzzle crown | 623.9 mm | Measured from `hk416.glb` (the range page sets the camera 60 mm further back; the effect is under 0.1 mm) |
| G7 and G1 drag functions | 84 and 79 knots | Fact: standard tables, checked today against py-ballisticcalc `drag_tables.py` |
| M855 mass, diameter, length | 62 gr, 5.69 mm, 23.0 mm | Mass: fact. Length (0.906 in): recalled |
| M855 BC | G7 0.151 | Recalled: Litz / Applied Ballistics measurement. G1 0.304 and 0.307 confirmed in today's search; the two agree in this model (see validation) |
| Mk 262 mass, length | 77 gr, 25.2 mm | Mass: fact. Length (0.994 in): recalled |
| Mk 262 BC | G7 0.190 (G1 0.372, Sierra) | Recalled; today's search did not confirm 0.190 |
| Mk 262 muzzle velocity | 770 m/s | Inferred: HK's 850 scaled by the Mk 262 to M855 ratio in 14.5 in chronograph reports |
| M856 mass, length, BC, velocity | 63.7 gr, 29.2 mm, G7 0.140, 810 m/s | Mass and length recalled; BC and velocity inferred |
| M856 trace | 75 yd to 875 yd, red | Recalled specification; the 15 m dim start is inferred |
| Velocity spread | sigma 7.5 (M855), 4.5 (Mk 262), 9 m/s (M856) | Inferred from typical ball and match figures |
| Group sizes | 3.0, 1.5, 5.0 MOA 10-shot extreme spread | Inferred from commonly reported carbine results. HK gives no figure |
| Shooter error | 1.2 MOA supported, 4 MOA standing, 1° hip | Supported: inferred from the US Army grouping standard (4 cm at 25 m). Standing and hip: inferred, tune for feel |
| Spin drift | `1.25 (Sg + 1.2) t^1.83` in | Published: Litz's empirical fit; Sg from the Miller rule |
| Paper hole factor | 0.85 calibre | Inferred |
| Steel density, plate inertia | 7,850 kg/m³, `1.25 m r²` | Fact and geometry |
| Momentum transfer to plate | 1.0 x normal momentum | Physics argument; within about 10 percent |
| Splash angle | within 20° of the face | Published guidance from steel-target makers |
| Fragment speeds, count, sizes, spark odds | see `ballistics.json` | Inferred (visual calibration) |
| Plate pitting thresholds | lead core 870 m/s, steel core 640 m/s | First: makers' guidance (about 2,850 ft/s). Second and the depth slope: inferred |
| Contact time | bullet length / impact speed | Model assumption (the bullet erodes onto the face over its own length) |
| Soil | 1,600 kg/m³, strength 3 MPa (berm 2 MPa), C = 1, tumble factor 2.5 | Inferred; set so ball stops in 10 to 15 cm of packed sand as commonly reported |
| Ricochet curves | dirt 8° ± 2°, steel 12° ± 3° (logistic) | Inferred within the ranges in forensic literature |
| Dust plume | 0.079 m per J^(1/3) high, scar 0.0087 m per J^(1/3) | Inferred (visual calibration) |
| Sonic crack | Whitham N-wave | Published formula |
| Trace and vapour | see `visibility` in `ballistics.json` | Inferred from shooting practice |

## Validation

1. **Analytic.** Vacuum parabola reproduced to 1e-14 m. Exponential decay under constant drag coefficient reproduced to 6 parts in a million (97.8586 against 97.8591 m/s).
2. **Published velocities, M855, 20 in barrel.** A forum post citing Aberdeen data gives 2,751 / 2,420 / 2,115 ft/s at 100 / 200 / 300 m. This model with G7 0.151 from 3,100 ft/s gives 2,751 / 2,424 / 2,119. That's within 4 ft/s, but I saw the figures only in a search summary and had to assume the muzzle velocity, so treat it as supportive, not conclusive.
3. **Sierra Infinity table for M855** (3,025 ft/s, 300 yd zero, 2.25 in sight height, 100 °F, as posted on accuratereloading.com, thread 352101342). With the thread's BC of 0.307 this model is flatter than the posted table: 0.3 in at 100 yd, 4.5 in (12 percent) at 500 yd. Refitting one number, G1 0.260, reproduces all ten rows within 0.11 in. So the geometry and integration agree with Sierra's program, and the posted run evidently used a lower BC than the one quoted beside it. This does not confirm the BC; it confirms the method. See `plots/validation_sierra.png`.
4. **Two descriptions of the same bullet.** M855 as G7 0.151 and as G1 0.304 give 569 and 572 m/s at 300 m and drops of 0.803 and 0.800 m. They part company below Mach 1.3 (345 against 370 m/s at 600 m), which is the known weakness of G1 for this shape.
5. **HK's sight drum.** The model needs 0.423 mrad more elevation for 200 yd than for 100 yd. HK's manual says one quarter turn of the drum is about 1.5 in at 100 yd, which is 0.417 mrad. One drum position is one quarter turn, so the model's M855 trajectory at 850 m/s matches HK's 100-to-200 yd step within 1.5 percent. The steps to 300 and 400 yd are 1.23 and 2.28 mrad.
6. **Runtime against simulation.** `node test.js`: tables, zero angles (within 2 µrad), points of impact, dispersion statistics, plate and soil numbers, and frame-by-frame stepping against instant tracing all agree.

I could not get the US Army's own trajectory tables (FM 3-22.9) or Applied Ballistics' BC list today; items 2 and 3 are forum transcriptions.

## Runtime API

```js
const B = HK416Ballistics;               // global after loading the file; module.exports in node
B.configure({ atmosphere: { tempC: 22, humidity: 0.5, altitudeM: 300 }, muzzleVelocity: 850 });

// ADS: origin is the eye (camera), dir the line of sight. Hip: pass socket_muzzle and the bore direction.
const shot = B.fire({ origin: cam.position, dir: camDir, ammo: 'M855', zero: 'hk100yd',
                      wind: [2, 0, 0], stance: 'aimed', rng: Math.random });
const shot2 = B.fire({ origin: muzzlePos, dir: boreDir, originIs: 'muzzle', stance: 'hip' });

shot.at(t)                               // {pos, vel, speed, mach, energy, momentum, tracer}
shot.advance(dt, targets, raycast)       // per frame: array of hits (usually empty); sets shot.done
shot.trace(targets, raycast)             // or resolve the whole flight now; hits carry their time t

// targets: {type:'disc', center, normal, radius} | {type:'rect', center, normal, u, halfU, halfV}
//          {type:'plane', point, normal} | {type:'sphere', center, radius} | {type:'box', min, max}
//          add passThrough:true for paper. raycast(origin, dir, maxDist) -> {distance, normal, object} | null
// hit: {t, point, normal, dir, vel, speed, energy, momentum, angle, range, target, index, object, offset:{x,y,r}}

const fx = B.impact({ hit, surface: 'steel', plate: { radius: 0.2, thickness: 0.01, leanDeg: 2 } });
// paper: fx.hole {diameter, greaseRing, length}, fx.exitSpeed
// steel: fx.plateImpulse, fx.contactTime, fx.peakForce, fx.plate {omega0, falls, ...}, fx.splash, fx.fragments(n),
//        fx.spark, fx.pitDepth, fx.ricochet, fx.exit
// dirt / berm: fx.penetration, fx.crater, fx.dust {height, width, speedMin, speedMax, linger, axis}, fx.ricochet, fx.exit

const st = B.plateKick(plate, fx.plateImpulse, hit.offset.y);   // then each frame:
B.plateStep(st, dt);                     // st.theta (rad from vertical), st.omega, st.down, st.atRest
const next = B.ricochet(hit, fx);        // a new tumbling Shot, or null

B.zeroAngle('M855', 'hk100yd'); B.poi('M855', 'hk100yd', 25);   // rad; metres high (+) or low (-)
B.visibility({ ammo, humidity, magnification, light }); B.sonicCrack({ mach, missDistance });
```

Vectors go in as `[x, y, z]` or `{x, y, z}` (a `THREE.Vector3` works) and come out as arrays. The world is +Y up by default. `stance` is `'bench'`, `'aimed_supported'`, `'aimed'` (default), `'hip'` or `'none'`; `spreadMoa` adds more (for recoil bloom). Angles are measured from the surface (90 is a square hit).

Speed: one second of 850 rounds/min stepped at 60 frames/s against 16 targets costs about 0.005 ms per frame on this Mac (worst frame 0.1 ms), about 19 µs per shot over its whole life. Hit tests use straight 10 ms chords of the path; the curve departs from a chord by 0.12 mm at most.

## Limitations

- Point mass. No yaw, pitch damping or transonic instability; spin drift is an empirical fit. Past about 550 m M855 goes transonic and real groups open up in ways this doesn't show.
- One BC per bullet. The M855 and Mk 262 values are recalled, not re-verified, and the M856 value is a guess. A 5 percent BC error moves the 600 m drop by about 20 cm and the 55 m impact by less than a millimetre.
- The tracer doesn't lose mass or change drag as it burns.
- Mk 262 and M856 muzzle velocities are scaled estimates; only the 850 m/s figure is HK's.
- Dispersion numbers are typical values, not measurements of an HK416. Shooter error at the hip has no published basis.
- Terminal effects are engineering models with inferred constants, good for believable behaviour and correct scaling, not for prediction. The plate result assumes a rigid plate on a frictionless hinge and ignores the stand; set `damping` if plates should settle faster.
- Real ranges keep rifles at least 100 yd from steel and ban steel-core ammunition on it. The game's 20 to 55 m plates are a game convenience; the splash here is what makes that rule.
- The model's sights are parallel to the bore; the zero is applied in the simulation, not in the GLB.
- No wind gradient, no turbulence, no change of air with height.
