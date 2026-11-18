# G44 V: simulated sound (version 2)

Everything here is synthesised from the action simulation and stated physics. No recording, and nothing derived from one,
is in this repository; no audio files are committed. There is no reference recording of this pistol: the model is checked
against published measurements only. `g44v-sound.js` synthesises the sound in the browser at load. Credit: carpetshark.

```
python3 sim.py          # params.json (stage A), compare/check.json, compare/sim_shots.png   (run ../action/sim.py first)
python3 sim.py render   # the same, plus listening WAVs in audio/ (ignored by git)
python3 diagnose.py     # version 1 (rebuilt from git) against version 2 -> compare/before_after.json
python3 verify_js.py    # g44v-sound.js under node against stage B in sim.py -> compare/js_parity.json
```

| File | What it is |
|---|---|
| `sim.py` | stage A (physics to tables, every input in `SRC` with its source and status), stage B (tables to pascals), the checks |
| `params.json` | every derived table: blast waveform per load, path filters, modal tables, room recipes |
| `g44v-sound.js` | browser port of stage B, and the playback chain |
| `metrics.py` | peak, A-duration, B-duration, exposure (LAE), octave-band envelopes |
| `diagnose.py`, `compare/before_after.json` | before and after numbers |
| `compare/check.json`, `compare/js_parity.json`, `compare/sim_shots.png` | checks against published figures, parity, a simulation-only plot |

## Why version 1 sounded like a click (change request, 2026-11-17)

Owner feedback: the shots "are clicks", "like a click on a keyboard or a crackle". Findings, shooter's ear, high-velocity load:

| Finding | Number |
|---|---|
| Playback mapping turned the shot down and hid everything after the blast | measured in Chrome: blast at -13.5 dB full scale, ground echo -23.9, slide closing -36.8 (`chrome_measurement`) |
| Level 5 dB low | 152.3 dB at the ear; a published .22 pistol of nearly the same barrel measures 157.5 dB there |
| Blast too long, and with a net impulse a far field cannot have | A-duration 0.33 ms; published: under 0.2 ms |
| No gas noise | none modelled |
| Mechanical sound thin | three impacts, every mode above 1.9 kHz, decays of 3 ms or less |
| Ground: one broadband copy; the berm overlay used a different, louder ground | reflection factor 0.75 flat; -6 dB in the overlay against -13 dB in the open-air shot |
| Energy in the first 2 ms after the blast arrives | 99.2 % dry, 94.8 % over ground |
| Time for each octave band to fall 20 dB (125 Hz to 8 kHz) | dry: 9.9, 8.5, 2.5, 2.1, 1.1, 0.5, 0.3 ms; over ground: 11.3, 10.4, 8.7, 8.0, 7.5, 7.4, 7.3 ms |

The physical event is short, and the published data say so: an unsuppressed .22 pistol in an open field has an A-duration
under 0.2 ms and a peak 44 dB above its exposure level, which is one clean pulse (Murphy 2018). Version 2 does not stretch
the blast. In life the rest of the shot is audible because it is loud in absolute terms: the ground echo is 138 dB and
the action 122 dB at the ear. Played 70 dB below the real level those parts fall under the room's noise. The fix is
therefore in three places: the physics that was missing or wrong, the level, and the playback mapping.

## What is synthesised

- **Muzzle blast.** The level follows the energy efflux of the sonic muzzle flow (exit pressure, gas temperature, bore area
  from `action.json`): peak ~ efflux^0.55, distance^-1.1, 6 cos(theta) dB directivity. The positive phase is a Friedlander
  pulse whose duration is the Kinney-Graham blast duration for the internal energy of the gas at bullet exit (93 to 215 J):
  0.12 to 0.15 ms. The negative phase follows the decay of the blow-down (volume-source radiation: equal and opposite
  impulse), 0.25 of the peak deep and about 0.4 ms long. Built at 768 kHz, band-limited to 20 kHz.
- **Jet noise** of the blow-down: noise with the Strouhal spectrum of the fully expanded jet (peak at 17 to 22 kHz, mostly
  above hearing) and 0.5 % of its mechanical power; 9 dB below the blast in energy inside the audio band, 0.3 ms long.
- **No ballistic crack.** All three loads leave the 102 mm barrel below the speed of sound (`../ballistics`).
- **The precursor** (air pushed out ahead of the bullet) was estimated by hand (piston radiation from the bore, about 95 dB at 1 m, 60 dB under the blast) and left out.
- **Mechanical sound of the shot**, timed and sized from `action.json`: firing pin on the rim, case on the ejector, slide on
  the frame, breech picking up the next round, firing pin caught by the trigger bar, slide closing on the barrel, the
  magazine stack rising 8 ms later (inferred), the trigger reset at 0.13 s (shooter cadence, inferred), and rail friction
  noise that follows the slide speed. Each impact has a Hertz contact time (under 0.4 ms), which sets how bright it is,
  and excites the modes of the parts it touches.
- **Structure** (`params.json`, `structure`): beam and plate theory on the dimensions in `model/inventory.json`. Grip
  panels 1.0, 1.9, 3.2 kHz; frame bending 1.2, 3.3, 6.4 kHz; slide bending 2.5, 7.0, 13.8 kHz; barrel 1.8, 11.1 kHz;
  magazine wall 1.3, 1.7, 5.0 kHz; recoil spring surge 383, 767, 1150 Hz. Decays from material loss factors: 4 to 42 ms.
- **Hand-operated clips:** `trigger`, `dry_fire`, `slide_rack`, `slide_lock_open`, `slide_release`, `magazine_out`, `magazine_in`, `case_ground`.
- **Propagation.** Per path a 64-tap filter: ISO 9613-1 air absorption and, for the ground path, the spherical-wave
  reflection coefficient of grass over soil (Delany-Bazley impedance, 200 kPa s/m2). Diffuse scatter from rough ground
  (Lambert, 20 % of the incident energy, inferred) arrives over the 15 ms after the reflection.
- **Perspectives:** `shooter` (right ear, from the model's eye socket), `bystander` (3 m to the left), `downrange` (25 m ahead, 2 m off the line).
- **Surroundings** as impulse responses for the shooter: `outdoor_berm` (the same ground, plus the return of a berm 25 m
  away), `indoor_range` (image sources to second order in a 6 x 3 x 28 m hall, then a Sabine tail).

Signal chain: dry shot (pascals) -> convolve with the room -> optional earmuff shelves -> playback mapping. The last two are not physics.

**Playback mapping** (`chain({ ear: true })`, the default; `sim.ear_map` is the same): a low shelf of +10 dB below 150 Hz,
the difference between the equal-loudness contours at the real and the played level, then `asinh(k x) / asinh(k)` with
k = 30 (`params.ear_map_k`): about 2:1 over the top 30 dB and a fixed 17 dB lift below. It replaces a Web Audio
DynamicsCompressor. `chain({ ear: false })` is linear.

## Checks

**Peak level.** One constant is calibrated (first row). The other rows are predictions: the same interior ballistics run at the published barrel length.

| Published measurement | Position | Published | Model | Error |
|---|---|---|---|---|
| Meinke 2014, 4.5 in pistol (calibration) | left ear, 47 cm from the trigger, 1.10 m above ground | 157.5 dB | 157.5 | 0 |
| Murphy 2018, 10 in pistol | 0.6 m left of the muzzle, 1.63 m high | 160 dB | 159.0 | -1.0 |
| Murphy 2018, 10 in pistol | at the ear, 0.35 m off the axis | 152 dB | 151.2 | -0.8 |
| Murphy 2018, 21 in rifle, 1280 ft/s | 0.6 m left of the muzzle | 152 dB | 155.3 | +3.3 |
| Murphy 2018, 21 in rifle, 1050 ft/s | 0.6 m left of the muzzle | 149 dB | 153.4 | +4.4 |
| Murphy 2018, 21 in rifle, 1280 ft/s | at the ear | 141 dB | 145.8 | +4.8 |
| Meinke 2014, 18 in rifles | left ear | 143.0 to 143.8 dB | 147.9 | +4.5 |
| Meinke 2014, 24 in rifle | left ear | 139.6 dB | 144.8 | +5.2 |

The two pistol predictions are within 1 dB. The rifles are 3 to 5 dB high: the scaling falls too slowly with barrel length.
The G44 V barrel (4.02 in) is next to the calibration point (4.5 in), so this error does not reach it.

| Result | CCI Standard Velocity | CCI Mini-Mag | CCI Quiet-22 |
|---|---|---|---|
| Peak, 1 m to the side | 157.9 dB | 159.2 dB | 155.2 dB |
| Peak at the shooter's ear (model; through a 48 kHz system) | 156.4; 156.3 dB | 157.7; 156.4 dB | 153.7; 152.6 dB |
| Bystander, 3 m; 25 m downrange | 146.8; 133.1 dB | 148.0; 134.4 dB | 144.0; 130.4 dB |
| Positive phase of the model (published: under 0.2 ms) | 0.140 ms | 0.152 ms | 0.116 ms |
| A-duration measured on the 48 kHz waveform | 0.167 ms | 0.160 ms | 0.102 ms |
| Peak minus exposure level, 0.6 m left (published 44.4 dB, Murphy) | 43.7 dB | 43.4 dB | 44.0 dB |
| Mechanical sound at the ear: peak, LAE | 120.2 dB, 86.7 dB | 122.0 dB, 86.9 dB | 116.1 dB, 82.6 dB |

- All three loads are inside the 149 to 167 dB that Flamme 2009 measured 1 m left of 15 recreational firearms.
- A free-air burst of all the exit gas energy (Kinney-Graham) gives 161.6 to 164.1 dB at 1 m; the model is 5 to 6 dB below, as a muzzle must be.
- Mechanical sound is below the published suppressed-pistol levels at the ear (133 dB peak, LAE 93.6 dB), which bound it.
- **JS against Python:** 28 outputs (every load, perspective, clip and room), worst difference -296.9 dB relative to peak.
  The new playback mapping in Chrome gives the same numbers as `sim.ear_map` (six window peaks, peak and energy).

**Before and after** (`compare/before_after.json`; shooter's ear, CCI Mini-Mag; t20 is the time after a band's own peak at which it is last within 20 dB of that peak):

| | Energy in the first 2 ms | t20 by octave band, 125 Hz to 8 kHz (ms) |
|---|---|---|
| v1 dry, pascals | 99.2 % | 9.9, 8.5, 2.5, 2.1, 1.1, 0.5, 0.3 |
| v1 open air, pascals | 94.8 % | 11.3, 10.4, 8.7, 8.0, 7.5, 7.4, 7.3 |
| v2 dry, pascals | 99.8 % | 19.8, 8.2, 2.5, 1.3, 1.1, 0.6, 0.2 |
| v2 open air, pascals | 94.0 % | 20.0, 11.1, 8.9, 8.3, 7.6, 7.9, 7.2 |
| v2 open air, as played | 61.6 % | 26.0, 18.3, 11.6, 16.5, 17.6, 15.0, 19.1 |
| v2 outdoor range with berm, as played | 58.7 % | 197, 186, 190, 179, 163, 18.2, 18.2 |

In pascals the open-air shot is still 94 % in its first 2 ms. That is the physics of a .22 pistol in an open field and
it agrees with the published peak-to-exposure figure; it was not tuned. What changed for the listener is the played
signal: the blast is at -1.6 dB full scale (was -13.5), the ground echo and the slide on the frame at -7.8 (was -23.9),
the slide closing at -21.3 (was -36.8). The sound now lasts as long as the action cycle, about 20 ms, and longer with a range around it.

## Limits

- **Not checked by listening, and there is no recording of this pistol.** Whether the shot now reads as a shot is the owner's call.
- **Exposure:** Meinke 2014 reports LAeq8 78.1 dB for the 4.5 in pistol, a peak-to-exposure difference of 34.8 dB; Murphy 2018
  gives 44.4 dB for the 10 in pistol. The model gives 42.8 and 43.9. It agrees with Murphy and is 8 dB short of Meinke's energy. Not resolved.
- **Sound power:** Murphy 2018 gives 150 dB (18 J in 18 ms) for the 10 in pistol; the model gives 139.9 dB. The same paper's
  peak and exposure at 0.6 m give about 1.6 J for a uniform source. The real blast may carry more low-frequency or forward energy than the model.
- Spectra were not checked: the published one-third-octave figure could not be read as numbers.
- The Fansler-Schmidt exponents and the Kinney-Graham formulas are recalled, not re-read. The stand-in loads for the
  published ammunition are the nearest simulated ones. Microphone-to-muzzle distances at the ear are inferred (`check.json`).
- A 48 kHz system shows a 0.15 ms shock 0.2 to 1.3 dB below its true peak.
- Jet noise efficiency is an upper estimate; a 0.3 ms blow-down is not an established jet.
- Mechanical: wall thicknesses, the slide's effective stiffness, loss factors, coupling between parts and the ground scatter share are inferred.
  The radiation efficiency is set from the left-right ear difference of a different pistol.
- The shooter's head and body (shadow, reflections) are not modelled. Listeners are single points.
- The trigger reset time is shooter cadence. The magazine holds no modelled rounds; its damping is a guess.
