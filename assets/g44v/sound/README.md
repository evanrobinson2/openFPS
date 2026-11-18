# G44 V: simulated sound

Everything here is synthesised from the action simulation and stated physics. No recording, and nothing derived from one,
is in this repository; no audio files are committed. `g44v-sound.js` synthesises the sound in the browser at load.
Credit: carpetshark.

```
python3 sim.py          # params.json (stage A) and compare/check.json, compare/sim_shots.png  (run ../action/sim.py first)
python3 verify_js.py    # g44v-sound.js under node against stage B in sim.py -> compare/js_parity.json
```

## What is synthesised

- **Muzzle blast.** A Friedlander pulse per propagation path. Its size follows from the simulated muzzle conditions: the
  energy efflux rate of the sonic exit flow (from the exit pressure, gas temperature and bore area in `action.json`),
  with peak pressure taken to scale as efflux to the power 0.55 and distance to the power -1.1.
- **No ballistic crack.** All three loads leave the 102 mm barrel below the speed of sound (`../ballistics`), so none is synthesised.
- **Mechanical sounds of the shot**, at their simulated times: firing pin on the rim, slide meeting the frame, slide closing. Each is a few damped modes plus a noise click, sized from the energy the impact loses in the action simulation.
- **Hand-operated clips:** `trigger`, `dry_fire`, `slide_rack`, `slide_lock_open`, `slide_release`, `magazine_out`, `magazine_in`, `case_ground`.
- **Perspectives:** `shooter` (right ear, from the model's eye socket), `bystander` (3 m to the left), `downrange` (25 m ahead, 2 m off the line). Free field, or over open ground with a reflected path.
- **Surroundings** as impulse responses: `outdoor_berm`, `indoor_range` (image sources to second order in a 6 x 3 x 28 m hall, then a Sabine tail).

Signal chain: dry shot (pascals) -> convolve with the room -> optional earmuff shelves -> playback compressor. The last two are playback mappings, not physics.

## Levels and the two published figures

| Load | Peak, 1 m to the side | Shooter's ear | Bystander, 3 m | 25 m downrange |
|---|---|---|---|---|
| CCI Standard Velocity | 153.2 dB | 151.3 dB | 140.8 dB | 127.1 dB |
| CCI Mini-Mag | 154.4 dB | 152.3 dB | 142.0 dB | 128.3 dB |
| CCI Quiet-22 | 150.4 dB | 147.8 dB | 138.9 dB | 123.9 dB |

- **Calibration (one constant):** a published figure of about 140 dB peak for a .22 calibre rifle (cited in a firearm suppressor study, PMC8588962). Its measuring position is not stated; it is taken as the shooter's ear. The same loads' simulated 24 in barrel exit conditions set the constant.
- **Check:** the pistol's levels at 1 m to the side, which follow from the simulated 102 mm barrel, lie inside the 149 to 167 dB that Flamme and colleagues measured 1 m to the left of 15 recreational firearms (as summarised in CDC stacks 211059), near its lower end as the smallest cartridge should.
- **JS against Python:** 28 outputs (every load, perspective, clip and room), worst difference -311 dB relative to peak.

## Limits

- The blast scaling exponents are recalled from the muzzle blast literature (Fansler and Schmidt) and were not re-read; the directivity (6 dB front to side) is typical of small arms, not measured for this pistol.
- The rifle anchor's measuring position is an assumption; moving it changes every level by the same amount.
- Modal frequencies, decay times and the radiation efficiency (0.2 %) of the mechanical sounds are inferred.
- Nothing has been checked by listening, or against a recording of this pistol.
- The slide's own sound through the shooter's hands and skull is not modelled.
