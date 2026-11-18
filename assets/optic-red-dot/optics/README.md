# Generic 2 MOA red-dot sight: optics

The optical simulation of the sight, as data plus a small runtime module. Credit: carpetshark.

| File | What it is |
|---|---|
| `sim.py` | The simulation. `python3 sim.py` rewrites everything below (Python 3 with numpy, scipy, matplotlib; about 30 s). |
| `reddot.json` | The collimator's design, the parallax map and polynomial, dot size and blur, window tint, brightness table, zero and hold tables for the HK416, sockets, rendering model. |
| `checks.json` | Nine checks of the simulation against first-order optics and published figures. |
| `optic-red-dot.js` | Self-contained runtime (no three.js): `window.OpticRedDot`, or `require()` in node. |
| `test.js`, `parity.json` | `node test.js` checks the runtime against `reddot.json` and against the rifle's ballistics runtime, and writes `parity.json`. |
| `reticle/dot_2moa.svg` | The dot, to scale. |
| `plots/` | `parallax.png`, `brightness.png` (simulation only). |

## Headline results

- **Parallax is small but not zero, and it depends on distance.** With the eye 3 mm off the axis the dot is at most
  0.4 MOA off the aiming point at 50 m (6 mm at that distance); at the edge of the window (11 mm) it is 3.9 MOA
  (56 mm). Close in it grows: 1.2 MOA at 3 mm and 6.9 MOA at the edge for a target at 10 m (20 mm on the target).
- **There are two parallax-free distances**, because the emitter sits off the axis: 19 m for eye movement across the
  emitter's plane and effectively infinity (3.8 km) for movement in it. Sweeping the eye edge to edge moves the dot
  0.2 to 4.4 MOA at 25 m and 2.1 to 2.2 MOA at 100 m, depending on the direction.
- **Eye relief is unlimited** (the beam is collimated: moving the eye 100 mm changes the dot's direction by 0.007 MOA).
  The dot is visible while the line from the eye to it passes both windows: about 12 mm off the axis.
- **Brightness.** The dot is 2 MOA: 15 mm at 25 m, 58 mm at 100 m. Its luminance runs from 0.003 cd/m² (night vision 1)
  to 200,000 cd/m² (position 8). A crisp dot needs position 3 indoors (60 cd/m²), 7 on sunlit grass, 8 on a sunlit paper
  target; on sunlit snow the top position still gives a contrast of 6.6.
- **Zero.** The optical axis is 75.8 mm over the bore. A 50 m zero with M855 crosses again at 186 m, peaks 42 mm high
  at 120 m and stays within 50 mm from 16 m to 216 m. At 10 m the shot lands 59 mm low.

Largest dot error over eight directions of eye offset (MOA), and what a full edge-to-edge sweep of the eye does:

| Target at | 3 mm | 6 mm | 9 mm | 11 mm | Sweep, across / in the emitter plane |
|---|---|---|---|---|---|
| 10 m | 1.22 | 2.88 | 5.07 | 6.88 | 4.7 / 8.9 |
| 25 m | 0.61 | 1.66 | 3.24 | 4.64 | 0.2 / 4.4 |
| 50 m | 0.40 | 1.25 | 2.62 | 3.88 | 1.3 / 2.9 |
| 100 m | 0.44 | 1.04 | 2.31 | 3.50 | 2.1 / 2.2 |
| 300 m | 0.50 | 0.96 | 2.10 | 3.25 | 2.6 / 1.7 |

## Physics

**The collimator.** A tube red dot is a reflex collimator: an LED near the tube wall shines forward onto a tilted,
curved, red-reflecting surface, which sends its light back to the eye as a parallel beam. Here that surface is the
cemented face of a doublet window (a Mangin mirror: the light crosses the eye-side glass, reflects, and crosses it
again), and the outer surface of the doublet is chosen so the window has no power for the scene. `sim.py` traces rays
exactly through the three spherical surfaces (Snell refraction and reflection in 3D; surface intersections written in
the curvature so a flat surface is exact).

**Solving it.** Free: the eye-side radius, the mirror radius and the emitter's focus position. The tilt is not free:
it is solved so the centred eye sees the dot exactly on the mechanical axis. The merit is the mean square parallax
error over a 14 mm eye disc for a target at 50 m, with two constraints: the eye-side radius is at least 150 mm (so
the window stays within about 1 percent of 1x) and the emitter is at most 92 mm behind the window (the housing
length). Result: R1 = 173.7 mm, mirror R2 = 185.4 mm, R3 = 175.4 mm, tilt 4.14°, focal length 95.6 mm, emitter
92.0 mm behind the window and 13.5 mm off the axis. The optimiser balances defocus against the spherical aberration
and astigmatism of an off-axis spherical mirror, which is why the parallax-free distance differs between the two axes
and why the error grows quickly near the edge of the window.

**Parallax.** For an eye at offset `e` the dot appears in direction `a(e)` (zero on the axis). The target point that
the centred eye's dot covers, at distance `D`, appears in direction `-k e / D`. The error is the difference:
`a(e) + k e / D`. Near the axis `a(e) = -e / D0`, which gives the thin-lens relation `e (1/D - 1/D0)`: no error at
the parallax-free distance `D0`, a fixed angle `-e / D0` far away, and an error growing as `1/D` close in.
`reddot.json` stores `a` as an order-5 polynomial in the eye offset, `k` (1.025 and 1.033: the window magnifies by
1.010) and the exact values on a grid. A shot fired with the dot steered back onto the target lands
`-error x distance` away from it.

**Dot size and blur.** A 2 MOA dot needs an emitting aperture of 2 MOA x the focal length = 56 µm. The eye's own
pupil samples a patch of the aberrated beam, which blurs the dot: 0.5 MOA more on the axis and 1.5 MOA more with the
eye 9 mm off toward or away from the emitter (3 mm pupil).

**The window.** The band-reflecting coating takes red out of the scene: transmission 0.79 / 1.00 / 0.99 in linear
sRGB, 95 percent luminous, a faint cyan cast; from the front it flashes deep red. The tint is computed from an
assumed reflectance spectrum (80 percent peak at 650 nm, 15 nm sigma) with the CIE 1931 observer. The tilted meniscus
also bends the line of sight by a constant 0.71 mrad; zeroing absorbs it.

**Brightness.** The dot has a luminance per switch position; what matters is its Weber contrast against the scene
seen through the window, `C = L_dot / (0.954 L_scene)`. Below about 3 it washes out, from 8 to 60 it is crisp, above
300 it blooms (the runtime grows the apparent size as `sqrt(1 + C / 300)` and adds a halo). Eye pupil diameter follows
Stanley and Davies (1995).

**Zero.** The bore is tilted up about the muzzle until the bullet path meets the line of sight at the zero distance.
The path comes from the rifle's own tables (`assets/hk416/ballistics/ballistics.json`); `node test.js` flies the same
zeros in the rifle's runtime.

## Parameters and sources

Fact = from a named published source. Class = a published figure of the class of sight, used as a guide for a generic
one. Recalled = a published figure quoted from memory. Inferred = my estimate. Derived = computed here.

| Parameter | Value | Status and source |
|---|---|---|
| Dot size | 2 MOA | The brief. Class: Aimpoint CompM4 user manual, section 1.1 Specification (2 MOA) |
| Housing length | 130 mm | Inferred for a generic sight. Class: 135 mm (same manual) |
| Ring section, hoods, bore | 30, 38, 27 mm | Class (30 mm ring) and inferred |
| Clear aperture, both windows | 24 mm | Inferred for a 30 mm tube |
| Optical axis over the rail | 39.0 mm | Recalled: the AR-height spacer class of 30 mm tube sights. Not re-checked on 2026-11-17 |
| Axis over the bore | 75.79 mm | Derived: 36.79 mm rail top (measured from a build of the HK416 recipe) + 39.0 |
| Eye point | 257 mm behind the front window, 159 mm behind the rear window | My choice: the same distance along the rifle as the rifle's `socket_ads_eye` |
| Glass | n = 1.5168, 5 mm doublet | Inferred (a common crown glass) |
| Emitter position | 13.5 mm off axis, at 4:30 | At the bore wall; the clock position is my choice |
| Radii, tilt, emitter focus, focal length, emitter size | see above | Derived: solved in `sim.py` |
| Click | 0.5 MOA (14.5 mm at 100 m) | Class: the CompM4 manual gives 16 mm at 100 m |
| Adjustment range | 120 MOA total | Class: the same manual gives ±2 m at 100 m (±69 MOA) |
| Switch positions | OFF, 3 night vision, 8 daylight | Inferred. Class: 16 positions, 7 for night vision (same manual) |
| Dot luminance | 0.003 to 0.3 cd/m² (NV), 91 to 200,000 cd/m² in steps of 3x | Inferred: makers do not publish luminances. The top is set to hold a contrast above 6 on sunlit snow |
| Scene luminances | 0.001 to 32,000 cd/m² | Typical photometric handbook values (recalled) |
| Coating | 80 percent reflectance at 650 nm, sigma 15 nm; 0.5 percent per coated air surface | Inferred |
| Contrast thresholds | 3, 8 to 60, 300 | Inferred (visual calibration) |
| Eye pupil | 7.75 - 5.75 f / (f + 2), f = (L 2827 / 846)^0.41 | Published: Stanley and Davies (1995), 60° field |
| Rifle geometry | rail top 36.79 mm, eye to muzzle 0.6239 m | Measured from a local build of `assets/hk416/model/build.py`; the second is in `ballistics.json` |
| Trajectories | M855, Mk 262, M856 | `assets/hk416/ballistics/ballistics.json` |
| Mass | 0.34 kg with mount | Inferred. Class: 370 g (CompM4 manual) |

## Checks

`python3 sim.py` writes `checks.json`; `node test.js` writes `parity.json`. All pass.

| Check | Result |
|---|---|
| Focal length: ray-transfer matrices of a thick Mangin mirror against the plate scale of the ray trace | 94.84 mm against 95.60 mm (0.8 percent; the emitter is 8.4° off the axis, and 1/cos² of that is 2 percent) |
| Parallax for 1 mm of eye offset: ray trace against the thin-lens relation `e (1/D - 1/D0)` at 10 to 300 m | within 1.0 µrad |
| Dot size: angle between the traced images of the emitter's two edges | 2.0001 MOA |
| Collimation: change in dot direction when the eye moves 100 mm along the axis | 2.0 µrad (0.007 MOA) |
| Window power for the scene | -0.0005 dioptre |
| Order-5 polynomial against the ray trace over an 11.5 mm eye disc | 0.03 µrad |
| Published parallax: mean edge-to-edge dot movement over 25, 50 and 100 yd | model 2.3 MOA. Published averages: 4.5 MOA (Aimpoint Micro T-2), 6.3 (CompM2), 9.7 (Micro T-1), from Green Eye Tactical's 2017 comparative study as transcribed in a forum post. The model is a better sight than those three; the study's figures include the testers' head movement |
| Published brightness: the top position against the brightest background the class is specified for (55,000 lx, taken as a white surface at 15,800 cd/m²) | contrast 13 |
| Click against the class | 14.5 mm against 16 mm at 100 m |
| JS exact ray trace against Python (10 eye positions, 5 distances) | 3e-13 rad |
| JS polynomial path against the Python ray trace (same points) | 0.027 MOA |
| Zero tables against the rifle's ballistics runtime (3 loads, 4 zeros, 19 distances) | zero angle 0.00008 mrad, point of impact 0.08 mm |

The published parallax figures are a plausibility check, not a calibration: I read them in a forum transcription
(accuratereloading.com optics forum, thread 7031016252), not in the study itself. The 55,000 lx figure is from a
search summary of an Aimpoint product sheet, not from the sheet.

## Runtime API

```js
const R = OpticRedDot;                       // global after loading the file; module.exports in node
await R.load('optics/reddot.json');          // or R.init(json)

R.beam(eyeRight, eyeUp, {exact})             // [right, up] rad: the dot's direction relative to the centred eye's
R.parallax(eyeRight, eyeUp, distanceM, {exact})   // {right, up, moa, poiShiftMm: [right, up]}
R.sightPicture({x, y, z}, {clicksUp, clicksRight})  // {front, rear, dot: {x, y, r}, visible, tint}
R.dot(position, sceneLuminance)              // {label, luminance, contrast, look, apparentMoa, halo, starburst}
R.recommend(sceneLuminance)                  // switch position for a crisp dot
R.eyePupil(sceneLuminance)                   // mm
R.zero('M855', '50m')                        // the zero table: bore angle, clicks, crossings, holds
R.hold('M855', '50m', 325)                   // mrad to hold over at 325 m
R.turret(clicksUp, clicksRight)              // {up, right} mrad
R.mountTo(HK416Ballistics)                   // sets the rifle's line of sight to this sight
R.data, R.sockets
```

Eye offsets are in millimetres from the optical axis as the shooter sees them (right, up); `sightPicture` takes the
eye relative to `socket_eye` (z back). Angles are radians; `sightPicture` returns tangents from the optical axis.
`{exact: true}` runs the ray trace (7 µs); the default polynomial takes 0.25 µs and is valid to 11.5 mm of eye offset.
Zero names: `50m` (default), `100m`, `200m`, `25m`. With the sight mounted pass the zero to the ballistics runtime as
a distance: `HK416Ballistics.fire({ zero: 50, ... })`.

Rendering: `reddot.json` `rendering.steps` lists what to draw; the sample page does it in 2D.

## Limits

- One wavelength and one glass index: no colour fringing, no dispersion of the dot.
- Spherical surfaces only. Real sights of this kind may use other surface shapes; this one is a competent spherical
  design, and its parallax is lower than three real sights measured in the one study I could read figures from.
- The emitter is a uniform disc; no LED structure, no stray reflections of the emitter, no "ghost" dots.
- The polynomial covers eye offsets to 11.5 mm and assumes the design eye distance; the dot's direction changes by
  0.007 MOA per 100 mm of eye distance, so this does not matter.
- Parallax tables measure distance from the front window; the zero tables measure it from the eye (0.26 m apart).
- Luminances, coating spectrum and contrast thresholds are inferred. The brightness check uses a figure I did not
  read in its source.
- The eye: pupil size only. No astigmatism, accommodation or glare.
- Adjusters shift the dot; the simulation does not move the emitter and re-trace, so parallax is that of the centred
  emitter (the emitter moves 14 µm per click, 3.3 mm over the whole range).
- The 39 mm mount height is recalled, not re-checked. On this rifle model it puts the axis 10.3 mm above the iron
  sight line, so raised irons show in the bottom of the window rather than at its centre.
