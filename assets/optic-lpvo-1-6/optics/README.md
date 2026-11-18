# Generic 1-6x24 LPVO: optics, eye box and reticle

The optical simulation of the scope, as data plus a small runtime module. Credit: carpetshark.

| File | What it is |
|---|---|
| `sim.py` | The simulation. `python3 sim.py` rewrites everything below (Python 3 with numpy, scipy, matplotlib; about 5 s). |
| `lpvo.json` | The zoom design, a row per magnification (stop, pupils, eye relief, field, vignetting, eye box), the eye box function, parallax, the reticle as primitives, zero and hold tables for the HK416, sockets, the rendering model. |
| `checks.json` | Six checks against first-order optics and the published figures of three 1-6x24 scopes. |
| `optic-lpvo.js` | Self-contained runtime (no three.js): `window.OpticLPVO`, or `require()` in node. |
| `test.js`, `parity.json` | `node test.js` checks the runtime against `lpvo.json`, and the reticle and zero tables against the rifle's ballistics runtime, and writes `parity.json`. |
| `reticle/` | `staple_bdc_centre.svg` (16 mrad wide) and `staple_bdc_full.svg` (72 mrad wide), drawn from the primitives. |
| `plots/` | `first_order.png`, `eyebox.png`, `reticle.png`, `holds.png` (simulation; markers are published figures). |

## Focal plane: second, and why

The reticle is in the **second focal plane**. It stays the same bold size at every power, so at 1x (where a carbine
spends most of its time) the centre dot and ring are as quick to pick up as a red dot. A first-plane reticle fine
enough to hold with at 6x shrinks six times at 1x, to a speck. The cost is that the range marks are true at 6x only:
at magnification M every subtension covers 6 / M times more of the target. `lpvo.json` lists what each mark means at
3x, 4x and 5x (at 4x the "300" bar is a 341 m hold).

## Headline results

| Power | Field (ft at 100 yd) | Field (°) | m at 100 m | Exit pupil (mm) | Eye relief (mm) | Eye box sideways: half brightness / black (mm) | Eye box along the axis: edge half / edge lost (mm) | Brightness at dusk (6 mm eye pupil) |
|---|---|---|---|---|---|---|---|---|
| 1x | 115.0 | 21.70 | 38.3 | 10.4 | 102.1 | ±5.1 / ±6.7 | ±27 / ±35 | 1.00 |
| 1.5x | 82.0 | 15.56 | 27.3 | 10.4 | 90.8 | ±5.1 / ±6.7 | ±25 / ±33 | 1.00 |
| 2x | 61.5 | 11.70 | 20.5 | 10.4 | 96.4 | ±5.1 / ±6.7 | ±25 / ±33 | 1.00 |
| 3x | 41.0 | 7.81 | 13.7 | 8.0 | 102.7 | ±3.9 / ±5.5 | ±19 / ±27 | 1.00 |
| 4x | 30.7 | 5.87 | 10.2 | 6.0 | 103.1 | ±2.9 / ±4.5 | ±14 / ±22 | 1.00 |
| 5x | 24.6 | 4.69 | 8.2 | 4.8 | 101.9 | ±2.2 / ±3.9 | ±11 / ±19 | 0.64 |
| 6x | 20.5 | 3.91 | 6.8 | 4.0 | 100.4 | ±1.8 / ±3.5 | ±9 / ±17 | 0.44 |

The eye box columns are for a 3 mm (daylight) eye pupil. All thirteen rows, a 6 mm pupil and the vignetting profiles
are in `lpvo.json`.

- **The eye box shrinks with magnification**, in both directions, because the exit pupil does: 10.4 mm at 1x, 4.0 mm
  at 6x. At 6x the eye has ±1.8 mm sideways and ±9 mm along the axis before half the light is gone; at 1x ±5.1 mm
  and ±27 mm.
- **Eye relief** is 100 to 103 mm from 2.5x to 6x and at 1x, and dips to 91 mm at 1.5x. `socket_eye` is at the 6x
  exit pupil, so at 1.5x the eye is 10 mm too far back and still well inside the box.
- **The exit pupil is 24 / M** from 6x down to 2.3x. Below that a stop inside the scope holds it at 10.4 mm.
- **The 1x field is narrower than six times the 6x field** (115 against 123 ft at 100 yd): a stop at the first image
  plane trims it. That is the low-power "tunnel".

## Physics

**The zoom.** Six thin elements on one axis: objective (62.6 mm), a field lens at the first image, two erector
groups (23.2 and 23.1 mm) that slide on cams, a field lens at the second image (where the reticle is) and the
eyepiece (42.5 mm). For a magnification M the erector must image the first plane onto the second at lateral
magnification `-M FE / FO`; that is one equation in the first group's position, solved by bisection, and the second
group follows. The scope is then afocal with angular magnification M. The focal lengths were chosen (in the old
build, by a search) to keep the eye relief flat across the zoom with the first image inside a 30 mm tube. It is a
design of mine fitted to the class, not a measurement of any scope.

**Stops and pupils.** A paraxial marginal ray and a chief ray are traced through the layout. The aperture stop is the
objective rim until the beam would overfill the erector; then a stop in the erector cell, conjugate to the
objective, takes over and caps the exit pupil. The exit pupil is where the chief ray crosses the axis behind the
eyepiece: its distance is the eye relief. Vignetting is the fraction of the entrance pupil whose rays clear every
aperture at a field angle, by sampling.

**Field.** The second-plane field stop sets the apparent field (23.2°); the real field is that divided by M, except
at the low end, where the stop at the first image plane is tighter.

**The eye box and the scope shadow.** Every point of the picture leaves the eyepiece as a parallel bundle that fills
the exit pupil and travels along its apparent direction. A distance `dz` behind the exit pupil that bundle is the
exit pupil's disc shifted sideways by `-dz` times the direction's tangent. The eye collects what falls in its own
pupil:

```
mask(ex, ey, dz, ax, ay) = overlap(disc(exit_pupil / 2), disc(eye_pupil / 2), hypot(ex + dz ax, ey + dz ay)) / (pi min(r)^2)
```

With `dz = 0` the whole picture dims evenly as the eye moves sideways and is gone at `(exit pupil + eye pupil) / 2`.
With the eye too far back or too close a crescent shadow comes in from one side as the eye moves sideways, and with
the eye centred the field closes in to `tan(a) < (exit pupil + eye pupil) / (2 |dz|)`. The eye pupil follows the
scene luminance (Stanley and Davies 1995), so the box is larger at dusk; at dusk a 4 mm exit pupil also shows a
dimmer picture than the naked eye sees (0.44 at 6x).

**Parallax.** Fixed at 100 m. For an eye `e` off the centre of the exit pupil the reticle moves over a target at
distance D by `M e (1/D - 1/100 m)`. The largest `e` that still shows a picture is half the exit pupil, and
`M x exit pupil / 2` is 12 mm at every power above 2.3x, so the worst case does not depend on magnification: 11 mm on
the target at 10 m, 9 mm at 25 m, 24 mm at 300 m.

**Zero.** The optical axis is 79.97 mm over the bore. The bore is tilted up about the muzzle until the bullet path
meets the line of sight at the zero distance; the path comes from the rifle's own tables
(`assets/hk416/ballistics/ballistics.json`).

| Load | Zero | Bore angle (mrad) | Clicks up from centre | Second crossing (m) | Highest point (mm at m) | Within 50 mm from to (m) | At 10 / 25 / 55 / 100 m (mm) |
|---|---|---|---|---|---|---|---|
| M855 | 200 m | 2.013 | 20 | first at 48 | 54 at 127 | 17 to 227 | -62 / -35 / +8 / +47 |
| M855 | 100 m | 1.538 | 15 | touches | 0 at 100 | 23 to 174 | -66 / -47 / -17 / 0 |
| M855 | 50 m | 1.969 | 20 | 194 | 48 at 125 | 17 to 223 | -62 / -36 / +6 / +43 |
| Mk 262 | 200 m | 2.304 | 23 | first at 42 | 67 at 123 | 15 to 224 | -59 / -29 / +20 / +61 |
| Mk 262 | 100 m | 1.686 | 17 | first at 86 | 0 at 93 | 21 to 162 | -65 / -44 / -14 / 0 |

Whole clicks cannot hit the exact angle: 20 clicks instead of 20.13 puts the M855 200 m zero 8 mm low at 200 m.
The hold tables use the exact angle.

## The reticle: "staple BDC"

An original design (`plots/reticle.png`, `reticle/*.svg`); it copies no maker's reticle.

- **Centre:** a 0.3 mrad illuminated dot (the 200 m zero) in a broken ring of 2.6 mrad radius. At 1x the ring is
  15.6 mrad in radius and frames a 45 cm wide target at 14 m: a close-range aiming circle.
- **Range marks:** four staples below the dot, numbered 3 to 6 for 300 to 600 m. The cross-bar of each staple is the
  **M855** hold. The tips of the two short legs hanging from its ends are the **Mk 262** hold. One mark carries both
  loads, each zeroed at 200 m.
- **Ranging:** each bar is as wide as a 45 cm target at its distance.
- **Wind:** the two small dots beside each bar are the hold for a 5 m/s full-value wind (M855).
- **Side bars:** fine lines with ticks at 4 to 8 mrad, then heavy posts to the edge of the field; a heavy post below.

| Mark | M855: bar (mrad) | Mk 262: leg tips (mrad) | Bar width (mrad) | 5 m/s wind dot (mrad) |
|---|---|---|---|---|
| 300 m | 0.922 | 1.052 | 1.50 | 1.31 |
| 400 m | 2.145 | 2.378 | 1.12 | 1.88 |
| 500 m | 3.708 | 3.992 | 0.90 | 2.55 |
| 600 m | 5.717 | 5.955 | 0.75 | 3.35 |

## Parameters and sources

Fact = from a named published source. Class = a published figure of a scope of this class, used as a guide for a
generic one. Inferred = my estimate. Derived = computed here. The published figures were read on 2026-11-17; where I
saw them only in a search summary the table says so.

| Parameter | Value | Status and source |
|---|---|---|
| Magnification, objective | 1-6x, 24 mm | The brief |
| Tube | 30 mm | Class: Vortex Razor HD Gen II-E 1-6x24 (retailer specification page) |
| Length | 257 mm | Class: the same scope, 10.1 in |
| Field of view | 115.0 to 20.5 ft at 100 yd | Derived; the design is fitted to the Razor's published 115.2 to 20.5 |
| Apparent field | 23.2° | Derived from 20.5 ft at 100 yd at 6x |
| Eye relief | 100.4 mm at 6x | Derived. Class: 4.0 in (Razor), 4.0 in constant (Trijicon VCOG, search summary), 3.9 to 4.1 in (SIG Tango6T, search summary) |
| Exit pupil ceiling | 10.4 mm | Class: 10.4 mm at 1x (VCOG), 11.4 mm (Tango6T), both from search summaries |
| Focal lengths, plane spacing | 62.6, 42.5, 23.2, 23.1, 31.0, -78.5, 76.4 mm | Derived: my design, from a search over thin-lens layouts |
| Clear radii | objective 12, first plane 12, erectors 8, ocular 21 mm | Objective: the brief. First plane: set to give the published 1x field. Others inferred |
| Ocular diameters | 42 mm clear, 46 mm outside | Inferred |
| Click, travel | 0.1 mrad, 40 mrad, 100 clicks per turn | Class: the Razor has 1/2 MOA or 0.1 mrad versions and 150 MOA (43.6 mrad) of travel. Clicks per turn inferred |
| Parallax setting | 100 m | Class: fixed at 100 yd (Razor) |
| Power ring | half a turn, angle proportional to ln M | Inferred |
| Mount height | 43.18 mm (1.70 in) axis over the rail | A common mount height (1.5, 1.7, 1.93 in are sold); chosen as the lowest that clears the folded rear sight |
| Axis over the bore | 79.97 mm | Derived: 36.79 mm rail top (measured from a build of the HK416 recipe) + 43.18 |
| Eye point | at the 6x exit pupil, 6.8 mm behind `socket_ads_eye` | Placement: the eyepiece's rear face is at rifle L = -170 mm |
| Distortion | k1 = 0.010 at 1x to 0.030 at 6x | Inferred; thin lenses cannot predict it |
| Transmission | 0.90, slightly warm | Inferred |
| Illumination | 10 steps to 60,000 cd/m² | Inferred |
| Eye pupil | 7.75 - 5.75 f / (f + 2), f = (L 2827 / 846)^0.41 | Published: Stanley and Davies (1995), 60° field |
| Trajectories | M855 850 m/s, Mk 262 770 m/s, G7 | `assets/hk416/ballistics/ballistics.json` (its README gives their status) |
| Mass | 0.61 kg scope, 0.20 kg mount | Class: 21.5 oz (Razor). Mount inferred |

## Checks

`python3 sim.py` writes `checks.json`; `node test.js` writes `parity.json`. All pass.

| Check | Result |
|---|---|
| Afocal, and magnifies by M: ray-transfer matrix of the whole scope (a second code path) at 18 powers | C = 5e-17 per mm; magnification and beam compression equal M to 5e-15; exit pupil distance equals the chief-ray trace to 6e-14 mm |
| Exit pupil = objective / M | 4.00 mm at 6x. Published: 3.8 mm (VCOG), 4.0 mm (Tango6T) |
| Exit pupil at 1x | 10.4 mm. Published: 10.4 mm (VCOG), 11.4 mm (Tango6T) |
| Field of view at 1x and 6x | 115.0 and 20.5 ft at 100 yd. Published: 115.2 and 20.5 (Razor, fitted), 105.8 and 17.7 (Tango6T), 95 and 15.9 (VCOG) |
| Ratio of the 1x field to the 6x field | 5.61. A pure zoom gives 6.00 (VCOG 5.97, Tango6T 5.98). The Razor's 5.62 means a second stop limits its 1x field, which is what the model's first-plane stop does |
| Eye relief | 3.95 to 4.07 in from 2.5x to 6x, 4.02 in at 1x; 3.57 in at 1.5x. Published: 4.0 in; 3.9 to 4.1 in |
| Eye box mask: the disc-overlap formula against 400,000 sampled rays, five cases | within 0.001 |
| Reticle marks against the rifle's ballistics runtime, M855 and Mk 262, 300 to 600 m | within 0.00004 mrad (0.02 mm at 600 m) |
| Every zero angle and hold-table row against the runtime (3 loads, 4 zeros, 19 distances) | zero angle 0.00008 mrad, hold 0.0006 mrad |
| JS against Python: cams, eye relief, exit pupil, field, vignetting, mask | 5e-10 mm and below (the precision of the JSON) |

The reticle check is independent in method: `sim.py` reads the rifle's printed range table and interpolates it;
`test.js` asks the rifle's runtime, which integrates each trajectory itself with the scope's height and eye position.

## Runtime API

```js
const L = OpticLPVO;                         // global after loading the file; module.exports in node
await L.load('optics/lpvo.json');            // or L.init(json)

L.state(M, {luminance | eyePupilMm})         // everything a shader needs at this power (0.3 ms; call when M or the light changes)
L.shade(state, {x, y, z}, ax, ay)            // per pixel: {inField, r, u, v, brightness}
L.firstOrder(M)                              // {eyeRelief, exitPupil, entrancePupil, apertureStop, angularMagnification}
L.field(M)                                   // {tanReal, tanApparent, realFovDeg, apparentFovDeg, fovMAt100m, reticleScale}
L.cam(M)                                     // erector positions [a, b] mm
L.transmission(M, tanField)                  // vignetting fraction
L.mask(ex, ey, dz, ax, ay, exitPupil, eyePupil)
L.parallax(M, eyeOffsetMm, distanceM)        // rad
L.eyePupil(sceneLuminance)                   // mm
L.reticle(M)                                 // {primitives, marks, scale, apparentScale}
L.drawReticle(ctx, cx, cy, pxPerApparentMrad, {illumination})
L.zero('M855', '200m'); L.hold('Mk262', '200m', 450)
L.turret(clicksUp, clicksRight)              // {up, right} mrad
L.powerRingDeg(M); L.magnificationAtRing(deg); L.illumination(position, sceneLuminance)
L.mountTo(HK416Ballistics)                   // sets the rifle's line of sight to this scope
L.data, L.sockets
```

`shade` takes the eye relative to `socket_eye` in millimetres (x right, y up, z back) and the pixel's apparent
direction as tangents from the optical axis. Zero names: `200m` (default, the reticle's), `100m`, `50m`, `25m`. With
the scope mounted pass the zero to the ballistics runtime as a distance: `HK416Ballistics.fire({ zero: 200, ... })`.

## Rendering a picture-in-picture scope

`lpvo.json` `rendering` has the full recipe. In short:

1. World pass as usual from the shooter's eye.
2. Scope pass into a square render target: a camera at `socket_objective` looking along the optical axis, half field
   `state.tanReal`.
3. On the eye lens (material `lens_ocular`) work in angle, not in lens UV: the picture is at infinity, so it stays
   fixed in direction while the housing slides over it as the eye moves. For each pixel take its direction from the
   eye as tangents `(ax, ay)` from the optical axis and call `shade`. Sample the scope pass at `(u, v)`, multiply by
   `brightness` and by `state.transmission`.
4. Draw the reticle in the same angle space at its fixed apparent size (`drawReticle`, or the primitives scaled by
   `apparentScale`), under the same `brightness`: the etched parts darken, the illuminated dot adds.
5. Inside the lens but outside the field stop: black.

The sample page does exactly this on a 2D canvas with an analytic scene.

## Limits

- Thin lenses, first order. No aberrations, no field curvature, no real glass. Distortion, transmission and colour
  are stated estimates. The layout's principal planes span 182 mm in a 257 mm body, because real groups are thick;
  the scope pass camera is placed at the front lens.
- Eye relief varies by 12.5 mm over the zoom (91 to 103 mm); the published scopes move 5 mm or less.
- The exit pupil ceiling and the first-plane stop are each fitted to one published number.
- The eye box mask assumes an unvignetted bundle; near the edge of the field the vignetting profile is multiplied in
  rather than traced per eye position.
- Parallax is the fixed-focus formula; the reticle is assumed to lie exactly in the second image plane at 100 m.
- The reticle's marks hold for this barrel and these loads in a standard atmosphere, at 6x. The Mk 262 velocity and
  both ballistic coefficients are the rifle asset's, with their stated uncertainty (its README).
- Turret travel and the click feel are not simulated beyond the angle per click.
- The published figures for the VCOG and the Tango6T were read in search summaries of maker and retailer pages, not
  in the documents themselves.
