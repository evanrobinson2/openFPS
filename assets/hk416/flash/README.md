# HK416 D14.5RS: muzzle flash and smoke simulation

What leaves the muzzle after the bullet, as a simulation: the under-expanded jet of propellant gas through the flash
hider (barrel shock and Mach disc), the light it gives off in its three phases, a light source a game can use, and the
smoke. It is driven by the interior ballistics in `../action/`: the pressure, temperature and mass of the gas in the
bore as the bullet leaves, and how the bore then empties, are that simulation's numbers. Model and simulation credit:
carpetshark.

```
python3 sim.py                # flash.json, checks.json, plots/, renders/ (about 20 s; numpy, scipy, matplotlib, Pillow)
node test_flash.js            # hk416-flash.js against the Python physics; writes parity.json
python3 compare/make_compare.py ../refs-local/flash ../refs-local/flash/compare_out   # photo comparison (needs the local photos)
```

| File | What it is |
|---|---|
| `physics.py` | the physics; every constant is in `PARAMS` with its source |
| `sim.py` | runs it and writes `flash.json` (derived tables) and `checks.json` |
| `render.py`, `plots.py` | pictures and plots of the simulation (no game code) |
| `flash.json` | the tables: timing, drive, jet, phases, spectra, light, smoke, parameters, parity numbers |
| `hk416-flash.js` | browser runtime, `window.HK416Flash`, no dependencies |
| `test_flash.js`, `parity.json` | JS-against-Python parity test and its result |
| `checks.json` | the drive against `action.json`, the model against published measurements |
| `compare/` | matched comparison with the reference photos: script, `measurements.json`, model-only matched renders |
| `REFERENCES.md` | publications and photographs, cited; none is committed |

## Conventions

- **Time.** `HK416Flash` takes seconds since the charge ignited. `action/` puts ignition 8.511 ms after the sear
  releases the hammer and the bullet base at the crown 0.976 ms after ignition (9.487 ms after the sear). Tables in
  `flash.json` count milliseconds from bullet exit (`t_ms`); `timing` holds the offsets.
- **Frame.** The gun frame of `hk416.glb`: metres, +Z muzzle, +Y up, +X shooter's left, origin on the bore axis at the
  upper receiver's front face. The tables are in the muzzle frame (same axes, origin at `socket_muzzle`, the hider
  face, z = 0.398 m); the runtime returns gun-frame positions unless asked for `{ frame: 'muzzle' }`.
- **Light.** Luminous intensity in candela as seen from the side, luminance in cd/m², colours as linear sRGB scaled to
  luminance 1. A point light of intensity I (cd) puts I/d² lux on a surface facing it d metres away.

## The physics

1. **Drive (from `action/`).** `physics.drive()` re-runs `../action/sim.py`'s `ib_solve` with the calibration stored in
   `action.json`. As the bullet leaves: 850 m/s, the bore a reservoir at 126.4 MPa and 1797 K holding the 1.691 g
   charge as gas (gamma 1.24, R 350.9 J/kg/K). It then empties isentropically through the sonic muzzle: half pressure
   after 0.35 ms, unchoked after 5.4 ms. The reservoir is taken as the stagnation state of the muzzle flow, the mass
   flow is the choked-nozzle flow of that state, and the gas thrust (1.34 N·s after exit) is `action/`'s bore force
   with its SAAMI momentum scale. `checks.json` shows these equal `action.json` to the digits it prints.
2. **Jet.** At the crown the gas is sonic at 70 MPa, 690 times the air pressure: a strongly under-expanded jet. It
   expands, over-shoots, and is brought back by a barrel shock closed by a normal shock, the Mach disc. Its distance
   follows Lewis & Carlson's correlation for the pressure of the moment, but it cannot be ahead of the bullet's base,
   so it runs out behind the bullet, reaches 125 mm from the hider face 0.23 ms after exit, and retreats as the bore
   empties. Inside the hider the jet expands into the 15.6 mm cage (area ratio 7.7, Mach 3.2 at the mouth if it filled
   it) and the six slots bleed gas sideways as thin jets that lean 40° forward, each with its own small shock.
3. **Flash phases.**
   - *Primary:* the hot gas in the cage, seen through the slots and the open mouth. 1795 K falling with the reservoir.
   - *Intermediate:* gas re-heated behind the Mach disc, with air burning into it (Klingenberg's intermediate flash):
     reservoir temperature plus 300 K while it burns, 1960 K at the peak. This is the brightest part of an ordinary
     shot: 8.9 cd for about 33 microseconds. The same, smaller, behind each slot jet.
   - *Secondary:* the fuel-rich gas (over half CO and H2) re-igniting in air, a fireball at about 2400 K lasting
     several milliseconds and thousands of times brighter. The hider's job is to prevent it. A two-constant mixing
     criterion gives it on 12 % of shots through the hider and 96 % from a bare muzzle. When it lights through the
     hider it is usually partial (0.3 of the full fireball, inferred).
   - Sparks (burning grains) are described in `flash.json` but not simulated.
4. **Colour and light.** Each region radiates as a grey particulate continuum at its temperature plus the sodium and
   potassium lines and CaOH/CuOH bands, integrated against the CIE 1931 observer. The light source is the sum, with a
   position, a colour and a cumulative table so a frame of any length gets the right luminous energy
   (0.50 mcd·s for an ordinary shot: 0.030 cd held for one 1/60 s frame).
5. **Smoke.** 1.5 % of the charge (25 mg, inferred) leaves as particulate in entraining puffs: one through the mouth
   with nearly all the momentum, one per slot, a wisp from the bore afterwards, and small ones at the gas block and
   the ejection port. Each puff swallows air (entrainment 0.28), slows, rises with its heat and takes up the wind
   through the air it swallows. Optical depth through a puff follows from its smoke mass and size.

## Sources of the numbers

`flash.json` `parameters` lists every constant with its source and a note. In short:

| Source | Which |
|---|---|
| `action` | charge mass, bore area, gamma, gas constant, everything at shot exit, the emptying of the bore, the ignition and exit times, `socket_muzzle` |
| `model` | the hider: length 42.9 mm, radius 10.6 mm, cage radius 7.8 mm, crown 34.9 mm behind the face, six slots 17.9 × 3.4 mm (`../model/build.py`) |
| `published` | Mach disc correlation (Lewis & Carlson); the 300 K rise of the intermediate flash and the secondary flash temperature (Klingenberg & Mach); puff entrainment (Turner); the two light-meter readings (TTAG) |
| `photo` | eleven shape constants fitted to the TTAG A2 photo (below); the final size of the secondary flash from two service photos |
| `inferred` | particulate absorption, smoke fraction and extinction, the secondary flash's delay, rise time and partial share, the mass split of the slots, the meter's distance and response, the spread of the ignition margin |

## Checks

### 1. The drive is `action/`'s (`checks.json`)

| Quantity | This simulation | `action.json` |
|---|---|---|
| Muzzle velocity | 850.036 m/s | 850.036 m/s |
| Peak chamber pressure | 358.487 MPa | 358.487 MPa |
| Ignition to exit | 0.976 ms | 0.976 ms |
| Reservoir pressure, first sample after exit | 122.62 MPa | 122.62 MPa |
| Reservoir temperature, same sample | 1788.2 K | 1788 K |

The same model at the manual's other barrel lengths (p. 7): 10 in 746 against 774 m/s, 16.5 in 885 against 880,
20 in 935 against 915. The 16 in run behind the photo and light-meter comparisons is therefore good to about 1 %.

### 2. Published muzzle-flash measurements (`checks.json`, `plots/04_temperatures.png`)

The measured rifle is a 7.62 mm (Klingenberg & Mach 1976), not this one, so about 10 % is the most these can show.

| Quantity | Model | Published | Status |
|---|---|---|---|
| Primary flash temperature | 1603 K at a bare muzzle (1795 K stagnating in the cage) | 1645 K | prediction from `action/`'s exit temperature; 3 % low |
| Intermediate flash, onset | 1660 K | about 1600 K | prediction; 4 % high |
| Intermediate flash, peak | 1960 K | 1940 K | not independent: the 300 K rise is taken from the same paper |
| Secondary flash | 2400 K | about 2500 K | an input |
| Gas in the intermediate region at 0.70 / 1.53 ms | 1432 / 1143 K | 1468 / about 500 K (CARS) | first agrees, second fails: the model has no mixing with cold air |
| Mach disc of the steady bare jet | 114 mm (20 calibres) | 133 mm by Ashkenas & Sherman's form | two published correlations 16 % apart |

### 3. Light meter (calibration, not a check)

TTAG measured 0.48 lx beside a 16 in AR-15 with an A2 birdcage (0.25 lx ambient) and 10,760 lx with a bare muzzle.
One factor on all thermal light makes the 16 in, five-slot run read 0.48 lx on a modelled meter (0.61 m away, 10 ms
response, both inferred): the factor is 0.098, so **before calibration the thermal model is 10 times too bright**.
The secondary flash's peak (15,100 cd for the full fireball) is set by the bare-muzzle reading. Absolute brightness
is therefore fitted, and rests on a guessed meter response: a slower meter would mean a brighter real flash.

### 4. Photographs (`compare/`)

Following the reference-to-model rule, the primary photo (`ttag_a2.jpg`: 16 in, A2 birdcage, three shots in one
exposure) was taken apart feature by feature, the model run for the same barrel with a five-slot cage, rendered at
the photo's scale (3.55 px/mm), framing and camera elevation (25°), and both measured by the same code.

| # | Feature in the photo | Measured | Model (`compare/measurements.json`) | Disposition |
|---|---|---|---|---|
| F1 | Lit slots, bright over their front third, with short flame licks leaning out at the slot fronts | three slots visible | slots lit, brighter to the front | kept; the licks are not modelled |
| F2 | A faint blob above the hider, forward of it | about 28 mm forward, 38 mm out, 12 mm across; 0.42 of the peak (8-bit) | 0.40 | fitted (`slot_reach_cal`, `slot_glow_size`, `slot_glow_factor`); the model shows one per slot, the photo shows the upper one clearly |
| F3 | A dark gap between the hider and the glow | 0.05 of the peak over 40 to 90 mm | 0.05 | fitted (`establish_exp`, `flush_k`, `glow_floor`) |
| F4 | The glow: a sharp upstream face, bright core, tail down-range | face 123 mm, far edge 170 mm, centroid 143 mm, 30 mm high | 118, 181, 142, 32 mm | fitted (`slot_cd`, `disk_d_over_x`, `glow_len_over_x`, `front_t_decel`) |
| F5 | An oblique leading edge above the axis, making the glow an arrowhead | apex about 15 mm upstream of the face | flat face | **not modelled** |
| F6 | A hair-thin straight line along the bore through the glow (a burning grain or the bullet's trace) | full width of the frame | none | **omitted** (sparks are described, not simulated) |
| F7 | Colour: yellow-white clipped core, orange-red edges | haze G/R 0.05 (linear) | 0.26 | **mismatch**: the model is yellower. The camera's white balance is unknown |
| F8 | Brown background haze | ambient light in a 3.2 s exposure | flat tint added | not flash |

This is a fit of eleven shape constants to one photograph and six numbers. It shows that the model's shape family can
be made to look like a real birdcage flash; it is not an independent test, and nothing else was available to test
against. The two service photos fix the secondary flash's final size the same way: full fireball 424 × 416 mm in
the model against 436 × 396 mm (103rd Rescue Squadron M4, ±15 %); partial, through the hider, 232 × 216 mm against
300 × 240 mm (Marine M4A1 at dusk, ±20 %, includes lens glare). The side-by-side sheets contain the photographs, so
they are written to `../refs-local/flash/compare_out/` and not committed; `compare/model_*_matched.png` are the
model halves.

### 5. JS against Python (`test_flash.js`, `parity.json`)

`sim.py` computes a set of numbers straight from `physics.py` (not from the tables) and stores them in `flash.json`
`parity`; `test_flash.js` asks the runtime for the same things. 62 checks pass:

| What | Agreement |
|---|---|
| Ignition and bullet-exit times against `action.json` | exact; exit to 0.05 % (rounding of the stored time) |
| Luminous energy of a frame (five windows, 1/60 s down to 80 microseconds across the peak) | 1 part in 100,000 |
| Instantaneous light between table points, near the peak | within 2 % |
| Instantaneous light in the tail (under 0.1 % of the peak) | within 1 % of the peak (24 % of its own small value at 0.9 ms) |
| Secondary flash pulse, partial and full | within 0.6 % |
| Smoke: position and radius of all ten puffs after 1 s in a 2 m/s cross-wind | 1 part in 10 million (the same sums) |

## The runtime: `hk416-flash.js`

```html
<script src="assets/hk416/flash/hk416-flash.js"></script>   <!-- window.HK416Flash -->
<script>
await HK416Flash.load('assets/hk416/flash/flash.json');      // or HK416Flash.use(json)
const t = tAction - HK416Flash.ignitionAfterSear;            // HK416Action counts from the sear; the flash from ignition
const secondary = HK416Flash.rollSecondary();                // once per shot: true on about 12 % of shots

const L = HK416Flash.light(t0, t1, { secondary });           // the light for a frame from t0 to t1 (seconds)
// L.intensity (cd, mean over the frame), L.rgb, L.colorK, L.position [x, y, z] in the gun frame
const f = HK416Flash.frame(t0, t1, { secondary });           // the same frame as drawable cards: f.cards, f.light
const s = HK416Flash.sample(t, { secondary });               // one instant, for slow motion
const puffs = HK416Flash.smoke(t, [windX, windY, windZ]);    // [{ source, position, radius, tau, opacity, rgb, albedo }]
const tex = HK416Flash.textures(128);                        // { plume, blob, slot, smoke } as RGBA arrays
</script>
```

| Member | Meaning |
|---|---|
| `load(url)`, `use(data)` | read `flash.json` |
| `ignitionAfterSear`, `bulletExit`, `duration`, `secondaryDuration` | seconds: ignition after the sear; exit, end of the ordinary flash and end of a secondary flash after ignition |
| `socketMuzzle`, `secondaryProbability`, `data` | hider face in the gun frame; chance of a secondary flash; the tables |
| `sample(t, opts)` | `{ cards, light, t, tau }` at one instant |
| `frame(t0, t1, opts)` | the time-average over a frame: what a camera or the eye collects. Luminous energy is exact |
| `light(t)` or `light(t0, t1, opts)` | only the light source |
| `smoke(t, wind, opts)` | smoke puffs; `opts.density` scales opacity (cold, humid air: up to 3, inferred) |
| `rollSecondary(p, rng)`, `sparks(seed)`, `textures(size)` | per-shot roll, inferred spark list, card textures |

`opts.secondary`: `false`, `true` (the partial fireball usual through the hider) or a number from 0 to 1 (that share
of the full fireball). `opts.frame`: `'muzzle'` for positions relative to `socket_muzzle`.

A card is an additive quad: emitted colour = `rgb × luminance × texture`. Kinds: `plume` (from `position` along
`axis`, `length` by `width`, turned about its axis to face the camera), `slot` (lies on the hider facing `normal`),
`disc` (the open mouth, seen from the front) and `blob` (camera-facing, the secondary flash). The header of the
module gives the details. At 60 frames a second the whole ordinary flash falls inside one frame: use `frame` or
`light(t0, t1)`, never `sample`, or the 33-microsecond peak will be missed or wildly over-counted.

## Limits

- **Not a flow solver.** The jet is correlations and a few rules for one barrel shock and Mach disc per jet. Weaker
  shock cells further out, the blast wave's own light, the precursor flow ahead of the bullet and the 41
  microseconds the bullet base spends inside the cage are not resolved.
- **The hider's effect on the jet is fitted, not computed.** How the flow splits between the mouth and the slots
  comes from one photograph of a different hider (five-slot A2 on a 16 in barrel) and is carried over to the model's
  six-slot hider. The model's hider itself is a photo-derived shape, not HK's drawing.
- **Brightness is calibrated to one hobbyist light-meter test** with a guessed meter response, and the uncalibrated
  model is 10 times too bright. Treat absolute candela as good to a factor of a few; ratios between phases are better.
- **Duration.** The 33-microsecond peak comes from the fitted decay of the burning (`flush_k`). No time-resolved
  measurement of a 5.56 mm flash was available; the published 7.62 mm work suggests the intermediate flash region
  stays hot for about a millisecond.
- **Colour** is yellower than the reference photo (check 4, F7), and line strengths are guesses.
- **The temperature at exit is `action/`'s book-keeping.** `action/` empties the bore as a reservoir of the whole
  charge as gas, at 1797 K; just before exit it carries the burnt 92.6 % alone at 1954 K. The flash uses the
  reservoir figure for the jet and the light (it is the one the emptying follows), and the in-bore figure only for the
  secondary-flash criterion, because it rises as the barrel shortens, which is the observed trend, and the reservoir
  figure does not. The 7.4 % of the charge still burning at exit is not followed.
- **Secondary flash.** Its probability is a two-constant fit to one bare-muzzle and one three-shot observation;
  its pulse shape, delay and partial share are inferred; its size is fitted to two photos. It is drawn as one blob.
- **Smoke** fractions and extinction are estimates; puffs are spheres with a stem; no condensation mist, no
  lighting of the smoke by the flash, no interaction between puffs.
- **One load, one barrel, standard air.** M855 in the 14.5 in barrel at 20 °C and sea level. No suppressor, no
  barrel heating, no shot-to-shot variation other than the secondary-flash roll.
- **Owner review of the visual match has not happened.** The comparison in check 4 is the evidence offered for it.
