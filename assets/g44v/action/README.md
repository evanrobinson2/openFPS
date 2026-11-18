# G44 V: action and recoil simulation

One shot of the .22 LR straight-blowback pistol, from the trigger break to the slide back in battery, for three named
factory loads, with the recoil it puts into the shooter and the flight of the ejected case. It produces data for a game
to play back. Credit: carpetshark.

```
python3 sim.py          # writes action.json and plots/ (about 2 seconds; numpy, scipy, matplotlib)
node test_action.js     # checks g44v-action.js against action.json, writes parity.json
```

| File | What it is |
|---|---|
| `sim.py` | the simulation; every parameter is in `PARAMS` with its source and status |
| `action.json` | per load: curves, events, outcome; parameters, validation, sensitivity, brass, parity samples |
| `g44v-action.js` | playback module, no dependencies: `G44VAction.sample(t, opts)`, `.events(ammo)`, `.ejectCase(rng)`, `.stepCase()` |
| `test_action.js`, `parity.json` | Node checks and their result |
| `plots/` | internal ballistics, slide cycle, recoil, firing train |

## Conventions

Frame of the model export: metres, +Z muzzle, +Y up, +X shooter's left. **Time zero is the trigger bar releasing the
firing pin.** `slide_mm` is rearward travel of `p01_slide`. `striker_mm` is how far the firing pin is behind its fired
position (the rest pose of the model is part-cocked, 7.5 mm). Tracks are sampled every 0.1 ms.

## The physics

1. **Firing train.** The firing pin (5.5 g) is released 8.6 mm back and driven by its spring (8 to 16 N, inferred):
   lock time 2.55 ms, 0.10 J. The charge is alight 0.15 ms after the rim is struck.
2. **Internal ballistics.** Energy balance with a covolume gas, a pressure-power burn law, the Lagrange gradient, shot
   start and bore friction as pressures, then isentropic emptying of the bore through a sonic muzzle. For each load the
   burn coefficient and a loss factor are fitted so that a 24 in test barrel gives the load's published velocity at a
   stated peak pressure; the 102 mm barrel is then a prediction.
3. **Blowback.** The gas force on the case head, less 10 % for case friction, drives the slide (101 g) against the
   recoil spring (24 N in battery, 65 N at 45 mm) and rail drag. The slide ejects at 15 mm, meets the frame at 45 mm
   (restitution 0.3) or stops short, returns, picks up a round at 31 mm, compresses the firing pin spring over the last
   8.6 mm as the trigger bar catches the pin, and closes on the barrel (restitution 0.15).
4. **Recoil.** Slide and pistol are separate masses, so the hand feels the spring, then the slide meeting the frame,
   then the slide closing. The shooter is a mass on a spring and damper in translation and in pitch about the wrist
   (two stances; all shooter numbers are inferred).
5. **Brass.** The case leaves at the ejector with half the slide's speed, up and to the right, with seeded scatter,
   then flies with drag and bounces.

## Results

| Load | Published, 24 in | Model, 102 mm barrel | Peak pressure | Slide peak | Travel | Outcome | Back in battery | Muzzle rise, two hands |
|---|---|---|---|---|---|---|---|---|
| CCI Standard Velocity 40 gr | 326 m/s (1070 fps) | 271 m/s (890 fps) | 140 MPa | 7.7 m/s | 45.0 mm | cycles | 20.9 ms | 1.7 deg |
| CCI Mini-Mag 40 gr | 376 m/s (1235 fps) | 300 m/s (983 fps) | 165.5 MPa | 8.7 m/s | 45.0 mm | cycles | 19.2 ms | 1.8 deg |
| CCI Quiet-22 40 gr | 216 m/s (710 fps) | 186 m/s (609 fps) | 60 MPa | 5.2 m/s | 35.0 mm | cycles, will not lock open | 26.9 ms | 1.2 deg |

## Checks

- **Calibration targets met:** the three test-barrel velocities (CCI product pages).
- **Peak pressure** at or under the SAAMI maximum average pressure for .22 Long Rifle, 24,000 psi (165.5 MPa). The
  Mini-Mag is set to that limit; the other two peak pressures are guesses.
- **Function against the makers' statements.** The manual (p. 12) says the pistol is designed for quality SAAMI or CIP
  ammunition and that some loads may lack the energy to cycle the slide fully; CCI says its Quiet-22 may need manual
  cycling in semi-automatics. The model makes the full stroke with the standard and high velocity loads and stops at
  35.0 mm with Quiet-22. This is a qualitative check, and the unpublished slide mass and spring loads were chosen inside
  the window where it holds.
- **Sensitivity** (`action.json`, `sensitivity`): with the slide 30 % heavier, the spring 30 % stiffer or 10 % more case
  friction, Quiet-22 short-strokes before the feed point (28 to 31 mm); with the slide 30 % lighter it makes the full
  stroke. The two full-power loads make the full stroke in every case.
- **Momentum:** the breech impulse equals bullet momentum plus bore friction and gas momentum (gas share 29 to 31 %).
- **JS against Python:** 60 random samples of `sample()` agree to 9e-16; seeded brass rest positions to 0.006 mm.

## Published and inferred

Published: bullet mass and test-barrel velocities (CCI); pressure limit, case and bore dimensions (SAAMI); pistol and
magazine weights, barrel length, trigger pull 26 N, magazine capacity (maker's table); lock-open travel (measured from
manual p. 21). Inferred, and labelled so in `PARAMS`: slide mass, recoil spring loads, firing pin spring loads, case
friction share, charge masses, two of the three peak pressures, powder properties, bore friction, restitutions, feed
and ejection details, the whole shooter model, the brass direction and speed ratio.

## Limits

- No measured velocity from a 102 mm barrel was found to check the pistol velocities against; they are model output.
- The slide mass and spring loads are not published. The cycle times and slide speeds scale with them.
- The pressure curve is a lumped model fitted to two numbers per load, not a measured trace.
- Feeding, extraction and the trigger reset are events with simple forces; malfunctions other than a short stroke are not modelled.
- The recoil model is linear and unmeasured. Pitch only; no yaw.
- `sample()` holds the firing pin at the break position after the shot (trigger still held); the trigger release is not simulated.
