# Generic QD 5.56 mm suppressor: gas dynamics, sound, back-pressure, heat and flash input

A lumped simulation of one shot of the HK416 D14.5RS through a generic quick-detach suppressor: the bore emptying
into the blast chamber, the gas working its way through six baffles and out of the end cap, what that does to the
sound of the muzzle, to the rifle's operating cycle, to the can's temperature and to the flash. It produces data and
a runtime module for a game to use; it is not game code. Credit: carpetshark.

Rebuild everything (about 5 minutes; Python 3 with numpy, scipy and matplotlib; node for the test):

```
python3 sim.py        # writes suppressor.json, checks.json and plots/
node test.js          # checks suppressor-qd-556.js against core.py and the HK416 modules; writes parity.json
```

The build is deterministic.

| File | What it is |
|---|---|
| `core.py` | the model: one shot (`run_shot`), pulse parameters (`acoustics`), the sound patch, flash input, heat. Pure Python, the reference for the JS |
| `sim.py` | builds the configuration, calibrates, runs the states, couples the HK416 action, writes the outputs. Every parameter is in its `PARAMS` table with a source |
| `plots.py`, `plots/` | seven plots, simulation only |
| `suppressor.json` | configuration, results per state, the action overlay, parity references. Units stated in each block |
| `checks.json` | every check against a published figure, with its source and whether it was calibrated to or predicted |
| `suppressor-qd-556.js` | the runtime: a line-for-line port of `core.py` plus the baked tables (`window.SuppressorQD556`) |
| `test.js`, `parity.json` | JS against Python, and the patched tables through the HK416 sound and action modules |

## Conventions

- **Time zero is the bullet base leaving the barrel crown.** That is `events.bullet_exit` of the HK416 action,
  9.487 ms after the trigger break and 0.976 ms after ignition.
- Frame: metres, +Z down-range, +Y up, +X to the shooter's left; origin at `socket_mount`, which is the rifle's
  `socket_muzzle` (the tip of its flash hider). The exit is `socket_exit`, 0.122 m further on.
- Chambers are numbered from the breech end: the blast chamber, then the space ahead of each of the six baffles.
- States: `first_round` (293 K wall, the can full of air), `subsequent` (320 K wall, the can full of spent gas:
  the reference state), `hot` (600 K wall).

## The physics

All of it is lumped: eight well-stirred volumes joined by orifices, integrated with fixed-step RK4 (0.2 µs for the
first 4 ms, 2 µs after). It is not a fluid simulation.

1. **The bore.** A reservoir in the state the HK416 interior ballistics leaves it when the bullet exits: 1.691 g of
   gas at 126.4 MPa and 1797 K in 10.04 cm³ (Nobel-Abel gas, γ 1.24, R 350.9 J/kg/K, as `assets/hk416/action`).
   Without the can it empties through a sonic muzzle and reproduces the action's own blowdown.
2. **Chambers and apertures.** Volumes, wall areas and apertures come from the geometry recipe
   (`../model/geom.py`): a 37.7 cm³ blast chamber, six of 10.7 to 11.6 cm³, 105.8 cm³ in all. Flow through each
   aperture is quasi-steady compressible orifice flow, choked or not, either way. The bullet (850 m/s, 23 mm long)
   blocks each aperture down to an annulus while it is in it.
3. **Carry-over down the bore line.** Baffles in line do not see stagnant gas: part of the jet from one aperture
   goes straight through the next. A share α of whatever arrives at an aperture carries on without stopping in the
   chamber. For the baffles α is the kinetic-energy carry-over of labyrinth-seal theory (Vermes 1961) times
   `clip_factor`; for the blast baffle it is the share of the muzzle's source flow inside the aperture's cone
   (Ashkenas and Sherman), which is 0.5 %. Without this term a lumped model is far too quiet (115 dB at 1 m).
4. **Walls.** Convective heat loss with a Stanton number on the through-flow, plus a small still-gas term.
   72 % of the heat goes into the blast chamber.
5. **Oxygen.** A cold can starts full of air (29.5 mg of oxygen). Once the mix in a chamber passes 850 K the oxygen
   burns the fuel-rich propellant gas, 13.1 MJ per kg of oxygen. This is the first-round pop.
6. **Breech.** Once the lugs are clear the withdrawing case lets gas past (the body taper opens 0.24 mm² per mm of
   travel), and once the case is out the chamber stands open. The carrier motion comes from the HK416 action.
7. **Sound.** The exit is a compact source: the exhaust's volume flow at ambient pressure Q(t) radiates as a
   monopole and its thrust F(t) as an axial dipole, p = [ρ₀ dQ/dt + s cos θ / c₀ dF/dt] / (4πr). Both derivatives
   pass through a 21 µs lag, the acoustic transit time of the aperture. The peak is the **uncorking pop**, when the
   bullet base clears the end cap 0.184 ms after it left the crown; a slower **swell** follows while the exit flow
   is still rising. The bare rifle's level and directivity are taken from `assets/hk416/sound`, not recomputed.
8. **Action.** The bore pressure, gas temperature and exit thrust replace the tail of the HK416
   interior-ballistics tables, and the HK416 action model is run again with the can's mass added.
9. **Heat.** The can is one thermal mass (302 J/K). Heat per shot is tabulated against wall temperature;
   between shots it cools by free convection and radiation.

## What is published and what is inferred

Sources, in order of authority:

- **hk416**: taken from the HK416 asset (its own sources are in its READMEs).
- **geometry**: computed from `../model/geom.py`.
- **published**: a named publication (`../notes/REFERENCES.md`).
- **inferred**: an engineering estimate. Nothing with this label was measured.
- **calibrated**: solved by `sim.py` so that a published figure is reproduced. These are not predictions.

Three parameters are calibrated.

| Parameter | Value | Solved for | Without it |
|---|---|---|---|
| `clip_factor` | 0.819 | 22.5 dB peak reduction at 1 m to the side, the midpoint of the published 20 to 25 dB | 15.4 dB with the plain labyrinth carry-over (factor 1) |
| `dipole_share` | 0.393 | 20.5 dB peak reduction at the shooter's ear, the midpoint of the published 17 to 24 dB | 14.9 dB with no dipole (the same in all directions); 50 dB with the whole compact dipole, which cancels the monopole behind the muzzle |
| `port_d_thrust` | 1.156 mm | the bare rifle's cyclic rate unchanged (800 rpm) when the residual-thrust term is switched on | the shipped port, 1.219 mm, gives 826 rpm bare with the term on |

The rest:

| Parameter | Value | Source | Note |
|---|---|---|---|
| bore state at exit | 126.4 MPa, 1797 K, 1.691 g, 10.04 cm³ | hk416 | from `action/sim.py ib_solve` with the calibrated burn law |
| gas | γ 1.24, R 350.9 J/kg/K, covolume 0.95 cm³/g | hk416 | |
| `cd_muzzle` | 1.0 | hk416 | so the bare case reproduces the action's blowdown |
| `cd_aperture`, `cd_breech` | 0.8 | inferred | sharp-edged orifice; the action uses 0.8 too |
| carry-over, baffles 2 to 6 and end cap | 0.642, 0.629 ×4, 0.553 | published × calibrated | Vermes: 8.52 / ((s − t)/c + 7.23), with c the aperture radius (my mapping of a round hole onto his slot), times `clip_factor` |
| carry-over, blast baffle | 0.0046 | published, inferred | source flow of an under-expanded jet; plume angle 1.99 rad extrapolated to γ 1.24 |
| `bullet_ramp` | 6 mm | inferred | travel over which an aperture opens behind the bullet |
| `stanton` | 0.006 | inferred | not fitted to the heat data |
| `h_free` | 30 W/m²/K | inferred | |
| `t_ign`, `tau_burn` | 850 K, 0.1 ms | inferred | |
| `q_o2` | 13.1 MJ/kg | published | Huggett 1980 |
| `tau_ac` | 21 µs | inferred | 7.2 mm / 343.2 m/s |
| bare level at 1 m, 90° | 164 dB | hk416 | Dater, "Firearm Sound Briefing" |
| listener angles | 174.8°, 97.5°, 2.3° | hk416 | shooter, bystander, down-range |
| `case_taper`, `case_d` | 0.0081, 9.3 mm | published | 5.56×45 case drawing |
| `neck_leak` | 1 mm² | inferred | |
| `residual_thrust`, `case_seal_len` | 1.0, 6 mm | inferred | bore pressure on the case head while the neck still seals |
| `h_conv`, `emissivity` | 12 W/m²/K, 0.85 | inferred | still air, matte black |
| `tau_o2` | 20 s | inferred | a guess: how fast air gets back into an open can |
| `flash_mix_ratio`, `flash_t_ign`, `flash_t_width` | 1.2, 1100 K, 60 K | inferred | |

## Results

Peak pressure in each chamber, MPa (blast chamber first):

| State | Blast | 1 | 2 | 3 | 4 | 5 | 6 | Exhaust at peak |
|---|---|---|---|---|---|---|---|---|
| first round | 13.1 | 4.5 | 4.0 | 3.6 | 3.3 | 2.9 | 2.6 | 0.197 kg/s |
| subsequent | 12.8 | 4.2 | 3.8 | 3.4 | 3.1 | 2.8 | 2.5 | 0.193 kg/s |
| hot | 13.2 | 4.4 | 4.0 | 3.6 | 3.3 | 3.0 | 2.6 | 0.194 kg/s |

The bare muzzle peaks at 2.59 kg/s and is empty in 6 ms. With the can the bore still holds 9.4 MPa after 2 ms,
3.0 MPa after 5 ms and 0.88 MPa after 10 ms.

Peak level of the muzzle source, dB re 20 µPa:

| Listener | Bare | First round | Subsequent | Hot can | Reduction (subsequent) |
|---|---|---|---|---|---|
| 1 m, 90° | 164.0 | 143.5 | 141.5 | 143.1 | 22.5 |
| Shooter's ear | 157.5 | 138.5 | 137.0 | 139.6 | 20.5 |
| Bystander, 5 m right | 147.1 | 128.9 | 126.9 | 128.5 | 20.3 |
| 50 m down-range, muzzle blast | 134.9 | 113.2 | 111.0 | 112.2 | 23.8 |
| 50 m down-range, bullet crack | 149.0 | 149.0 | 149.0 | 149.0 | 0 |

The pop is 0.08 ms long (Friedlander time); the swell after it is 36.6 Pa (125 dB) at 1 m for the reference shot.
Jet noise falls to 0.18 of the bare rifle's rms and lasts 7 times longer.

## Validation

| Quantity | Simulation | Published | Status |
|---|---|---|---|
| Peak reduction, 1 m left of the muzzle | 22.5 dB | 20 to 25 dB (Lobarinas et al. 2016, nine AR-15s, 14 cans) | calibration target, not a prediction |
| Peak reduction at the shooter's ear | 20.5 dB | 17 to 24 dB (Murphy et al. 2018) | calibration target |
| Peak reduction about 1 m behind the shooter | 19.0 dB | 20 to 28 dB (Murphy et al. 2018, instructor position) | predicted; 1 dB under the band. The bare reference is the HK416 directivity law extrapolated to 180° |
| Suppressed level at the ear | 137 dB | most suppressed AR-15s 140 to 150 dB; above 140 dB at the right ear (Lobarinas et al.) | below the band: there is no ejection-port or gas-vent source here, and the paper puts the right-ear level down to the port |
| Bullet crack | 149.0 dB, the same samples with and without the can | a can does nothing to the ballistic shock | by construction; `test.js` checks the synthesised crack sample for sample |
| First-round pop, peak | +2.0 dB at the side, +1.5 dB at the ear | no controlled 5.56 figure found; trade sources say 5 to 10 dB in general and little on short 5.56 rifles | predicted, unverified |
| First-round pop, the swell after the pop | +9.5 dB | as above | predicted, unverified. The burn raises the later flow much more than the first peak |
| Heat per shot, cold can | 1970 J, 6.5 K | 7 to 10 °F (3.9 to 5.6 K) per round, rule of thumb | predicted with an inferred Stanton number; above the rule of thumb |
| 100 rounds at 2 per second | +463 K (+834 °F) | about +750 °F (Small Arms Defense Journal) | predicted; 11 % over |
| 30 rounds at 1 per second | +168 K (+303 °F) | 270 to 300 °F after a magazine (blog figures, unclear whether a rise) | predicted, same order |
| Carrier speed at ejection | +6.0 % (4.07 to 4.31 m/s) | M4A1, direct impingement: about +25 % carrier speed (NDIA 2016 briefing) | predicted. No HK416 figure found. The short-stroke piston vents after 3 mm, so less is expected than for a gas-tube rifle |
| Cyclic rate | +3.2 % (800 to 825 rpm) | patents quote +20 to 30 % for gas-tube rifles; HK416 manual 700 to 900 rpm bare | predicted, inside the manual's band |
| Bore pressure when the lugs clear | 7.7 MPa against 3.2 MPa bare | none | predicted |
| Gas out of the breech | 171 mg against 6 mg bare | none; suppressed rifles are known to blow gas back at the shooter | predicted, see limits |
| Recoil impulse | 5.08 N·s against 5.48 N·s (−7 %); free recoil 1.08 against 1.33 m/s with the can's 0.61 kg | none found for this rifle | predicted |
| Bare blowdown against the HK416 action | bore pressure within 1.6 % at 0.5 ms, 2.6 % at 4 ms; impulse 2.237 against 2.256 N·s; 795 against 800 rpm | `assets/hk416/action` | consistency check |
| Mass conservation | error 7 × 10⁻¹⁵ bare, 5 × 10⁻¹⁵ suppressed | | numerical check |
| Blast scaling cross-check | 14.4 dB | Fansler and Schmidt: overpressure ∝ (energy efflux)^0.55 | a lower bound on the reduction: what it would be if the can's exhaust started as abruptly as a bare muzzle |
| JS against Python | 0 difference in 802 numbers (bit-identical) | | `parity.json` |

The honest summary: the two headline sound figures match because two parameters were set to make them match.
Everything else in the table is an output. The level behind the shooter, the heat and the direction and size of the
back-pressure effect are plausible against the little published data there is; the first-round pop and the breech
gas have nothing solid to stand against.

### What the back-pressure does to this rifle

The HK416's piston vents after 3 mm of travel, so holding pressure in the bore for longer adds almost nothing
through the gas system: the peak carrier speed moves 0.8 %. The residual pressure acts on the cartridge case instead.
While the bolt is unlocking and for the first millimetre of extraction it grips the case in the chamber, which slows
the carrier (with only that, the rate falls to 737 rpm). Then, with the lugs clear and the neck still sealing, it
pushes on the case head. The net is a carrier 6 % faster at ejection and a rate 3.2 % higher.

The shipped HK416 action has no case-head thrust term, because for the bare rifle it is small. `sim.py` switches it
on through a new optional input of `action/sim.py` (`over={'residual_thrust': 1.0, 'case_seal_len': 0.006}`) and
re-solves the gas port so that the bare rifle still runs at 800 rpm. The can's effect is the difference between two
runs of that one model.

## Runtime API (`suppressor-qd-556.js`)

```js
await SuppressorQD556.load('suppressor.json');             // or SuppressorQD556.use(parsedJson)

// sound: patch the HK416 tables, then use the HK416 sound module exactly as before
const hkParams = await (await fetch('assets/hk416/sound/params.json')).json();
const S = await HK416Sound.build(ctx, { params: SuppressorQD556.soundParams(hkParams, 'subsequent') });

// action: the suppressed cycle, rate and recoil, in action.json's own format
HK416Action.use(SuppressorQD556.actionData(hkActionJson));

// flash: per-phase scales, the new source position and the delay
const f = SuppressorQD556.flashInput('first_round');       // f.scale.primary, f.scale.secondary, f.exit_offset_m, f.delay_s

// heat: bulk can temperature through a string
const h = SuppressorQD556.heatString([0, 0.5, 1.0, 1.5]);  // [{ t, T_before_K, o2, heat_J, T_after_K }]

// or simulate the shot for any can state (about 50 to 200 ms of CPU)
const shot = SuppressorQD556.runShot({ t_wall: h[3].T_before_K, o2: h[3].o2 });
const ac = SuppressorQD556.acoustics(shot);                // pulse parameters per listener
const patched = SuppressorQD556.soundParams(hkParams, ac); // the patch for exactly that state
```

- `soundParams(hkParams, state)` returns a patched copy; the tables passed in are not changed. For each listener
  it replaces the muzzle blast with the pop (peak, Friedlander time, the 0.122 m shift of the source), replaces
  the bare rifle's afterburn pulse with the swell, scales and lengthens the jet noise, and moves the mechanical
  events and the automatic shot spacing to the suppressed cycle. **It does not touch `nwave`.**
- `levels(state)` gives the table above. Buffers from the HK416 sound module are normalised to −1 dBFS, so to hear
  the difference scale the suppressed buffer by `S.info(buf).peak_pa` over the bare buffer's.
- `actionData(base)` returns a copy of `action.json` with `cycle`, `ballistics`, `events`, `auto`, `recoil.semi`,
  `recoil.auto`, `mechanics.full_stroke_mm` and the brass release replaced.
- `runShot(opts)`: `t_wall` (K), `o2` (0 to 1, the share of the can's fill that is fresh air), `bare`, `breech`
  (`'suppressed'`, `'bare'`, a `{t, area}` table or `null`), `t_end`. Returns peaks, totals and the record `rec`.
- `shotHeat(t_wall, o2)`, `cool(T, dt)`, `heatString(times, T0, idleBefore)`.
- `SuppressorQD556.exitAfterSear` (9.487 ms) converts to the `HK416Action` clock.

### The flash interface

`assets/hk416/flash/` was not on this branch when this was built, so this is a documented interface, not a tested
coupling. `flashInput(state)` gives a scale for each phase the flash model names (`precursor`, `primary`,
`intermediate`, `slot_jet`, `secondary`, `sparks`): multiply the bare flash's luminous output by it, move the source
from `socket_muzzle` to `socket_exit` (`exit_offset_m`), and delay it by `delay_s` (0.184 ms, the bullet clearing the
end cap).

| Phase | Scale, subsequent shot | Why |
|---|---|---|
| precursor, slot jets | 0 | they happen inside the can |
| primary, intermediate | 0.015 (first round 0.021, hot 0.022) | an optically thin emitter: exhaust mass flow times T⁴, with the exhaust at 1240 K against 1864 K bare |
| sparks | 0.00025 | only what stays on the bore line gets through: the product of the carry-over shares |
| secondary | 0.021 (first round 0.057, hot 0.072) | the chance that the exhaust, mixed with the air it needs to burn, is above 1100 K: 862 K against 1236 K bare |

## Limits

- Lumped volumes: no waves, no shock reflections, no transit delays inside the can. The fast first rise at the exit
  comes from the carry-over term and the bullet's gating, and its size was calibrated.
- The bare rifle's exit pressure, 126 MPa, comes from the HK416 action's interior ballistics. It is about twice the
  muzzle pressure usually quoted for a 14.5 in 5.56 barrel. The can's chamber pressures, heat and back-pressure all
  scale with it.
- The flash hider is treated as an open space with solid walls: its slots add volume but do not steer the flow.
- The clips are drawn and their area is counted, but the cross-flow they set up is not modelled; it is folded into
  `clip_factor`.
- The carry-over of an under-expanded jet is taken as that of a subsonic one.
- The sound source is the exit alone. There is no ejection-port, piston-vent or mechanical-ringing-of-the-can
  source, so levels at the shooter's ear are a lower bound. The room responses of the HK416 sound module were built
  for the bare rifle's directivity and are reused unchanged.
- The pop and the swell are fitted into the HK416 sound grammar (two Friedlander pulses). The swell really rises
  over 0.2 ms; a Friedlander pulse starts at its peak.
- Listener directions are the HK416 module's three, plus 90° and 180°.
- The can is one temperature. In reality the blast chamber end runs much hotter than the front; `heat.share_by_chamber`
  says where the heat goes but no temperature map is computed. No conduction into the barrel, no wind, no mirage.
- Heat per shot between the tabulated wall temperatures is interpolated; the first-round extra (133 J) is taken as
  the same at any temperature. How fast air returns to an open can (`tau_o2`) is a guess.
- The breech leak uses the case's taper and an inferred neck clearance. The 171 mg is an estimate of what leaves
  the breech, not of what reaches the shooter's face.
- The action coupling is one pass: the carrier motion that sets the breech leak comes from a run without the leak.
- The can's mass is added to the gun for recoil; its effect on the pitch inertia and on the point of impact is not
  modelled, nor is any change in muzzle velocity (real cans add about 1 %).
- Nothing here has been checked by listening or against a measurement of this rifle.
