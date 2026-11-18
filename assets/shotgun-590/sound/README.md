# Shotgun 590: synthesised sound (version 3)

Thirty-three sounds, built from the action simulation and the model, rendered identically in Python and in the
browser. **No recording was used**: not as a sample, not as a filter, not as something to fit, and there is no
reference recording of this gun. The outside numbers are published measurements of 12 gauge guns, named below.
Credit: carpetshark.

```
python3 sound/sim.py          # writes params.json and compare/{levels,checks,bands}.json, compare/waveforms.png
python3 sound/verify_js.py    # node renders every sound with shotgun590-sound.js; compared sample by sample
python3 sound/sim.py wav      # also writes listening WAVs to sound/audio/ (ignored by git, never committed)
```

Needs Python 3 with numpy and matplotlib (scipy is used if present), and node for the parity check.

| File | What it is |
|---|---|
| `sim.py` | derives the source from `action/action.json` and `model/inventory.json`, builds each sound's component list, renders it, runs the checks. Every outside number is in `SRC` with its basis and source |
| `measure.py` | the measurements: peak, A- and B-duration, 9 ms rms, third-octave maximum, octave-band envelopes |
| `params.json` | component lists, sources, the calibration, the derived source, mode frequencies, the ground filters, peak levels |
| `shotgun590-sound.js` | the runtime: `load()`, `use()`, `names()`, `render()`, `buffer()`, `play()`, `info()` |
| `verify_js.py`, `verify_js.mjs` | the parity check |
| `compare/` | `checks.json` (model against published figures), `bands.json` and `bands_v1.json` (band envelopes of this version and the last), `levels.json`, `js_parity.json`, `waveforms.png` (simulation only) |

## Version 3: the outdoor range

Version 2 made a room the default shot. Version 3 adds an outdoor range and makes it the default; the room shot is
now `..._room`. It also adds six far listeners for the buckshot load. Everything else below is as in version 2.

**The range** (`SRC['outdoor_range']` in `sim.py`; a chosen layout, not a survey): the covered firing point of
version 2, grass, an earth backstop 50 m downrange (60 × 6 m), pine woods from 15 m behind the backstop and in
belts 130 to 230 m to either side.

| Term | Model | Source |
|---|---|---|
| Distance | weak-shock decay and lengthening, `s = √(1 + k ln r)`: the wave is 1.30 to 1.68 times longer at 25 to 100 m | Landau 1945, as in the hk416 asset |
| Air | absorption at 25 °C, 70 % humidity, as a filter on each path: 0.6, 2.2 and 6.6 dB per 100 m at 1, 4 and 8 kHz | ISO 9613-1 |
| Ground at grazing angles | spherical-wave reflection coefficient on Delany-Bazley grass, 0.14 to 0.56 ms after the direct wave | Chien and Soroka 1975 |
| Backstop | Lambert scattering, absorption 0.40, patch by patch | inferred |
| Woods | single scattering by trunks as rigid cylinders (short-wave limit, weaker below about 450 Hz), 500 stems per hectare of 0.12 m radius, with extinction through the stand | Morse and Ingard 1968; the stand is a guess, and branches and foliage are left out, so this is a lower bound |
| Shelter wall | one mirror reflection for listeners whose mirror point lies on the 12 m wall: 18 to 19 ms late, 12 to 14 dB down | image source |

Far listeners, buckshot, microphone 1.5 m up (`compare/checks.json`, `outdoor_range`). "Side" is 90° from the line
of fire, "front" is 40° from it:

| Sound | Peak | Energy 0 to 2 ms | 2 to 10 | 10 to 50 | 50 to 200 | after 200 ms | Backstop, dB re direct | Woods, dB re direct |
|---|---|---|---|---|---|---|---|---|
| `shot_buck00_range_side_25m` | 134.9 dB | 84 % | 13 % | 0 % | 0 % | 4 % | −15.1 (230 to 313 ms late) | −13.6 |
| `shot_buck00_range_front_25m` | 139.2 dB | 79 % | 16 % | 3 % | 1 % | 1 % | −15.3 (169 to 258 ms) | −16.3 |
| `shot_buck00_range_side_50m` | 128.2 dB | 77 % | 11 % | 0 % | 3 % | 9 % | −11.3 (182 to 298 ms) | −7.7 |
| `shot_buck00_range_front_50m` | 133.0 dB | 65 % | 13 % | 3 % | 15 % | 4 % | −7.4 (58 to 207 ms) | −8.7 |
| `shot_buck00_range_side_100m` | 121.2 dB | 58 % | 10 % | 0 % | 5 % | 27 % | −10.9 (131 to 283 ms) | −2.4 |
| `shot_buck00_range_front_100m` | 125.8 dB | 59 % | 12 % | 12 % | 10 % | 7 % | none (it stands beside the backstop, at the edge of the woods) | −3.5 |
| `shot_buck00_shooter` (default) | 159.5 dB | 50 % | 25 % | 24 % | 1 % | 0 % | −38.2 | −37.4 |

What this layout does not produce: energy between 2 and 50 ms at the far listeners. Nothing in it lies 1 to 17 m
further than the direct path except the shelter wall. A real range has benches, posts, target frames, vehicles and
side berms there; which, and where, is not known, and none was invented. No parameter was set from a recording.

## Why version 1 sounded like a click

Measured on version 1's buckshot shot at the shooter's ear (`compare/bands_v1.json`):

| Finding | Number |
|---|---|
| The audible bands were over almost at once | 250 Hz to 8 kHz: 6 to 11 dB down within 2 to 10 ms, 12 to 18 dB down by 10 to 50 ms |
| Most of what followed the pulse was one invented 95 Hz tone | 65 % of the energy came after 2 ms, but the largest third-octave band was 100 Hz (published: 500 to 800 Hz) and 46 % of all energy lay under 250 Hz, where small speakers play nothing |
| The gas noise was a guess | noise at 650 Hz and 2.4 kHz, set at a tenth and a twentieth of the peak and lasting 60 and 25 ms; the jet from the bore stays choked for under 4 ms |
| One reflection, too weak | the ground reflection was given the level of the ray to the rear: 16.6 dB under the direct wave. The ray that reaches the ground leaves the muzzle sideways, where the blast is stronger: 6.6 dB under |
| No surroundings | nothing after the ground reflection: no room, no roof, no wall |
| The rack was three high tones and a hiss | contact tones at 3.1, 5.2 and 7.4 kHz lasting 2 to 4 ms carried each impact; the 500 Hz band from 10 to 50 ms was 51 dB SPL; no shell, sear or elevator sounds, no rattle |

The published energy of a 12 gauge shot (Maher and Shaw, below) agrees with a short pulse in free field. **Outdoors,
a real shot at this distance is brief**: the model's dry shot has 93 % of its energy in the first 2 ms, and the
published figures leave no room for more. What gives a shot its body is where it is fired. The only published
durations for this gun come from indoors. Version 2 therefore made a room the default; version 3 makes it the
outdoor range above and keeps the room as `..._room`.

## Sounds

| Name | What | Peak at the listener |
|---|---|---|
| `shot_buck00_shooter`, `shot_slug_shooter` | the shot at the shooter's ear, **on the default outdoor range** | 159.5 and 160.8 dB |
| `shot_buck00_bystander`, `shot_slug_bystander` | 5 m to the side of the muzzle, same range | 151.8 and 153.1 dB |
| `shot_buck00_range_side_25m`, `_50m`, `_100m`, `shot_buck00_range_front_25m`, `_50m`, `_100m` | buckshot heard far off on the range | 121 to 139 dB |
| `..._room` (all four) | the same shot in a plywood-lined training room | 159.5, 160.8, 152.6, 153.5 dB |
| `..._covered` (all four) | the covered firing point and backstop without the woods | 159.5, 160.8, 151.8, 153.1 dB |
| `..._field` (all four) | on open grass: ground reflection only | the same |
| `..._free` (all four) | free field, no reflection: the dry shot, for a game with its own reverb | the same |
| `pump`, `pump_back`, `pump_forward` | the whole rack, or each stroke | about 106 dB |
| `shell_insert` | a shell pushed into the magazine until its rim snaps past the cartridge stop | 78 dB |
| `dry_fire` | the hammer falling on an empty chamber | 93 dB |
| `safety`, `action_release` | the two small controls | 68 and 64 dB |

Levels are peak dB re 20 µPa. Time zero of a shot or `dry_fire` is the trigger break; of the others, the start of
the motion. The names of version 1 are unchanged; the `_room`, `_covered`, `_field`, `_free` and `range_` shots are new.

## How the shot is made

Four kinds of component, summed: a **Friedlander pulse** (a blast wave), optionally through a short filter; **jet
noise** (filtered noise under the bore's blow-down envelope); a **decaying mode** (a part ringing); a **noise
burst** with an attack and a decay (friction, scattered sound).

### The source, from the action simulation

| Quantity | 00 buck | 1 oz slug | From |
|---|---|---|---|
| Gas energy in the bore at exit, `p V / (γ − 1)` | 4.13 kJ | 6.38 kJ | `action.json` |
| Muzzle pressure | 7.48 MPa | 11.56 MPa | `action.json` |
| Gas sound speed, `√(γ p V / m)` with the charge mass | 859 m/s | 952 m/s | derived (the charge mass is a guess in `action/`) |
| Scale radius `R0 = (E / p0)^(1/3)` | 0.344 m | 0.398 m | derived |
| Positive phase `c_T R0 / c` | 0.456 ms | 0.527 ms | `c_T` = 0.451, from the published 456 µs |
| Blow-down time constant θ | 8.0 ms | 7.2 ms | choked emptying of the bore |
| Jet stays choked for | 3.8 ms | 3.9 ms | derived |
| Fully expanded jet | Mach 3.4, 1890 m/s, 57 mm | Mach 3.6, 2160 m/s, 67 mm | isentropic expansion to 1 atm |
| Jet power at the start, noise peak | 3.5 MW, 6.6 kHz | 6.5 MW, 6.4 kHz | Strouhal 0.2 |

### The terms

1. **Blast wave.** A Friedlander wave (Hamernik and Hsueh 1991), `p = P (1 − t/T) e^(−t/T)`. Peak
   `P = k p0 R0 / r × D(θ)`, with `D = (μ cos θ + √(1 − μ² sin² θ)) / (1 + μ)` (the form of Fansler and Schmidt).
   `k` = 0.243 and `μ` = 0.65 are fitted to four published levels (calibration, below); version 1 guessed 0.25 and
   a 15 dB front-to-back figure. Front to back in peak: 13.5 dB.
2. **Positive and negative phase.** Positive phase 0.456 ms (buckshot), against about 0.3 ms for a 5.56 mm rifle
   (the hk416 asset): the larger bore and charge give a longer wave. The negative phase follows from the
   Friedlander form: it bottoms at −13.5 % of the peak one positive phase after the zero crossing, and is back
   within 10 % of that after 2.2 ms. No published negative-phase figure for a 12 gauge was found.
3. **Jet noise.** The bore empties through the choked muzzle as `p = p_e (1 + t/θ)^(−2γ/(γ−1))`. The jet's
   mechanical power times an acoustic efficiency of 0.5 % (NASA SP-8072) gives its sound power; the level falls as
   `(1 + t/θ)^(−4.5)`. Its source sits 8 jet diameters downstream of the muzzle, so behind the gun it arrives
   1.6 ms after the blast, 19 dB under the blast's peak in rms. It lasts about 4 ms, not version 1's 60 ms.
4. **Ground** (`_field`). The reflected ray is traced: 3.34 m long, leaving the muzzle 106° from the bore, where the
   blast is 4.7 dB stronger than toward the ear. Its delay at the ear is 7.03 ms. The ground is grass in the
   Delany-Bazley model (200 kPa s/m², Embleton et al. 1983), applied as a 96-tap filter; mean |R| from 250 Hz to
   4 kHz is 0.64 at the shooter and 0.49 at the bystander.
5. **Covered firing point** (`_covered`). Image sources for a concrete pad, a roof 2.7 m up and a wall 3 m behind
   the shooter, each ray with the blast's directivity along its own direction: 88 reflections, the first from the
   roof at 4.24 ms and −6.2 dB, the pad at 7.03 ms and −6.6 dB, then a flutter between pad and roof every 15.9 ms.
   Together they carry 1.2 dB less energy than the direct wave. Sound scattered by the roof's framing is a noise
   tail (−6.8 dB, 31 ms). The backstop berm 50 m away returns a diffuse slap at 297 ms, −38 dB in energy.
6. **Room** (`_room`). A plywood-lined room, 8.5 × 2.7 × 10 m, concrete floor: 48 image sources out to 40 ms
   (+3.0 dB in energy over the direct wave), then a statistical tail in three bands with Eyring decay times of
   0.90 s (350 Hz), 1.86 s (1 kHz) and 1.50 s (2.8 kHz). The tail carries 9.2 dB more energy than the direct wave
   at the shooter, because the shooter stands in the blast's quietest direction and the room returns the rest.
7. **The gun.** The hammer falls 2.4 ms before the blast leaves; the barrel and receiver ring afterwards (their
   strength is a guess, about 80 dB under the blast's peak).

## How the mechanical sounds are made

Each event of the pump stroke in `action.json` is an impact at its own time. Its strength is the momentum of what
moves (masses from the model's parts, speeds from the action simulation); its brightness comes from Hertz's
contact time, 0.06 ms for the sear to 0.34 ms for the slide on the receiver, because a contact that long barely
excites modes above about 1/t. Each impact rings the parts it reaches:

| Part | Modes (Hz) | Model |
|---|---|---|
| Barrel | 442, 1220, 2391, 3952, 5904 | free steel tube; a thin tube radiates its low modes badly, so it is heard from 2.4 kHz up |
| Magazine tube | 610, 1682, 3298, 5452, 8145 | free steel tube |
| Receiver walls | 1880, 2378, 3209, 4372, 5867 | aluminium plates, 3 mm |
| Action bars | 381, 1049, 2056, 3399 | steel strips, 2.8 mm |
| Stock shell | 196, 274, 403, 706 | polymer plate, 3 mm: the low thud |
| Forend shell | 509, 670, 938, 1314 | polymer plate, 3 mm |

Events in a full rack, in order: unlock (43 ms), sear (90 ms), hull on the ejector (138 ms), next shell thrown onto
the elevator with the magazine spring rattling (147 ms), slide on its rear stop (150 ms, 0.63 kg at 1.11 m/s),
elevator up (247 ms), bolt on the shell head (265 ms), shell chambered (320 ms), bolt locked and slide home
(330 ms, 0.98 m/s). Through each stroke runs sliding noise in three bands (receiver, forend shell, bars) that grows
with the slide's speed, and nine small knocks of the action bars in their slots.

All mechanical levels hang on one guessed scale (3.5 Pa at the ear per kg m/s), set so a brisk rack peaks near
105 dB. No published level for a pump action was found.

## Checks (`compare/checks.json`)

### Calibration: three fitted numbers against five published ones

| Published | Position | Published | Model |
|---|---|---|---|
| Maher and Shaw 2010, 18 in barrel, 2¾ in 00 buck: rms of a 9 ms window | 3 m, on axis, free field | 145 dB | 145.2 dB |
| The same | 3 m, behind | 129 dB | 131.4 dB |
| Murphy and Tubbs 2007 (NIOSH), 18 in barrel, outdoor range: peak | 1 m left of the shooter, ear height | 159.0 to 161.5 dB | 158.1 dB |
| Krammer, as reproduced by E.A.R. Inc.: peak at the ear, 18.5 in (161.5) and 28 in (151.5) barrels interpolated to 20 in | shooter's ear | 159.9 dB | 159.5 dB |
| Kardous and Willson 2004 (NIOSH), indoor range: impulse duration | just outside the shooter's ear | 456 µs | 456 µs (sets `c_T`) |

Rms error of the four levels: 1.6 dB. The fit cannot satisfy both papers at once: the energy behind the gun is
2.4 dB high while the peak beside it is 2.2 dB low.

### Independent checks

| Check | Published | Model | |
|---|---|---|---|
| Peak at the shooter's ear | shotguns 152 to 170 dB (Meinke et al. 2017); 163 dB indoors (Kardous and Willson) | 159.5 dB buck, 160.8 dB slug | pass |
| Largest third-octave band of the direct wave, 42.67 ms window, 1 m left of the shooter | 500 to 800 Hz for most weapons (Murphy and Tubbs) | 630 Hz | pass |
| Delay of the ground reflection at that microphone | 6.24 ms (Murphy and Tubbs) | 6.15 ms | pass |
| Front to back, 9 ms rms | about 15 dB; 16 dB to the lowest value (Maher and Shaw) | 13.8 dB | 1 to 2 dB short |
| B-duration outdoors | impulses typically under 10 ms (Meinke et al.) | 3.8 ms free field, 5.1 ms open grass, 16.0 ms covered firing point | pass |
| B-duration indoors, at the shooter | 30 to 62 ms and 172 to 185 ms, same gun in a shoothouse (NIOSH HHE 2013-0124-3208, instructor positions) | 182 ms in the room | pass |
| **Parity: Python against JavaScript**, every sound, sample by sample | | worst difference −291 dB re peak | pass |

Not passed or not checkable:

- Murphy and Tubbs also say the largest band exceeded 130 dB for most weapons. The model's largest band is
  123 dB, and its whole level over that window is 133 dB. Maher and Shaw's energy figure, moved to that microphone,
  gives about 131 dB, so no single band of such an impulse can hold 130 dB. The two papers are not reconciled.
- With the ground reflection included, the bands from 315 Hz to 1.6 kHz at that microphone lie within 3 dB of
  each other, and the largest is 315 Hz.
- The room's B-duration falls inside the published range without adjustment, but the published rooms' sizes and
  microphone distances are not given, so this shows the right order of size, no more. The bystander's is 391 ms.
- The published barrels are 18 and 18.5 in; this gun's is 20 in. The model has almost no barrel-length term
  (0.1 dB for 2 in), while Krammer's two figures differ by 10 dB over 9.5 in.

### Before and after: is the shot a click?

Buckshot at the shooter's ear. "20 dB down" is the time after which an octave band's 2 ms rms envelope stays 20 dB
under its own maximum.

| | Energy in the first 2 ms | In the first 10 ms | 20 dB down, 500 Hz to 8 kHz | B-duration |
|---|---|---|---|---|
| Version 1 (its only shot) | 35 % | 55 % | 61 to 88 ms | 29.9 ms |
| Version 3, default (outdoor range, shooter's ear) | 50 % | 75 % | 44 to 50 ms | 16.0 ms |
| Room (`_room`) | 9 % | 17 % | 449 to 591 ms | 181.8 ms |
| Open grass (`_field`) | 83 % | 100 % | 8.5 to 10.4 ms | 5.1 ms |
| Free field (`_free`) | 93 % | 100 % | 4.5 to 8.6 ms | 3.8 ms |

Version 1's 65 % after 2 ms was mostly the 95 Hz tone: in the 1 kHz band it was 14 dB down by 10 to 50 ms and 25 dB
down by 50 to 200 ms. The room shot is 6 dB and 8.5 dB down in the same windows.

Octave-band rms level, dB SPL: version 1's shot, then the room shot:

| Band | 0 to 2 ms | 2 to 10 ms | 10 to 50 ms | 50 to 200 ms | 200 to 500 ms |
|---|---|---|---|---|---|
| 125 Hz | 118.2 → 121.9 | 132.4 → 122.8 | 130.8 → 119.6 | 120.4 → 115.1 | 110.5 → 104.3 |
| 250 Hz | 132.7 → 135.6 | 125.7 → 132.4 | 114.8 → 128.0 | 104.4 → 122.1 | 99.5 → 111.1 |
| 500 Hz | 138.2 → 139.1 | 127.0 → 133.8 | 119.9 → 129.8 | 109.6 → 125.5 | 100.8 → 117.1 |
| 1 kHz | 137.9 → 138.3 | 127.1 → 134.2 | 123.6 → 132.3 | 112.7 → 129.8 | 99.4 → 122.1 |
| 2 kHz | 134.5 → 136.3 | 127.0 → 131.8 | 122.1 → 130.2 | 111.0 → 130.1 | 94.5 → 122.8 |
| 4 kHz | 132.9 → 133.9 | 126.6 → 129.8 | 121.1 → 126.6 | 108.4 → 129.5 | 86.8 → 121.5 |
| 8 kHz | 130.1 → 131.2 | 122.5 → 129.9 | 118.5 → 124.9 | 105.3 → 125.9 | 84.5 → 118.5 |

The rack, version 1 then version 2 (`pump`): 500 Hz band from 10 to 50 ms 50.7 → 68.2 dB, 1 kHz 58.3 → 68.9 dB,
2 kHz 66.8 → 71.0 dB; peak 106.2 → 106.4 dB; 38 → 400 components. `dry_fire`: spectral centroid 5.2 → 3.2 kHz,
250 Hz band 30 → 44 dB sound exposure level. Every sound is in `bands.json` and `bands_v1.json`.

Nothing has been checked by listening, by anyone.

## Runtime

```js
const S = Shotgun590Sound; await S.load('assets/shotgun-590/sound/params.json');
S.play(audioCtx, 'pump', { destination: mixNode, when: audioCtx.currentTime });
const buf = S.buffer(audioCtx, 'shot_buck00_shooter', { normalize: true });   // full scale, mix it yourself
S.buffer(audioCtx, 'shot_buck00_shooter_free', { normalize: true });           // the dry shot, for your own convolver
S.info('pump').peak_db;                                                        // the simulated level
```

The API is that of version 1; `renderSound(snd, fs, filters)` takes the filter table as a third argument. Without
`normalize`, every buffer shares one scale (full scale is `S.fullScalePa` pascals), so the rack is 53 dB under the
shot, as simulated: most games will want `normalize: true` and their own mix. Buffers are mono, 48 kHz, 0.12 to
2 s. The far shots start with the sound's travel time as silence. `params.json` is 0.7 MB.

A shot is 160 dB at the ear with a crest of 20 dB and more over its tail. A page that plays it peak-normalised on
small speakers plays the tail quietly: that is playback mapping (a compressor), not something this module does.
`sim.py wav` writes plain WAVs and, in `audio/listen/`, copies through a stated 3:1 upward compressor.

## Limits

- The blast is one Friedlander wave of a fixed length in every direction. Routh and Maher (2016) found the
  shotgun's muzzle blast the longest and slowest to build of ten firearms, with values only in figures; the real
  wave has structure this does not. No precursor wave, no secondary flash.
- Jet noise: efficiency, source position and directivity are recalled or inferred, and no published jet-noise
  level for a shotgun was found. Its reflections are not modelled; reflections carry the blast only.
- The surroundings are choices, not measured places. The room is an empty box; its early reflections use one
  absorption value per surface and ignore the lengthening of a reflected blast. The covered firing point's
  scattering figures are inferred. No shooter's body, head or gun shadowing; listeners are single points.
- Mechanical sounds: timing, masses and mode frequencies follow the simulation and the model, but the model's
  internal parts are blocks of inferred size, and loss factors, part weights, the level scale, the sliding noise
  and the rattle are guesses. They are heard dry, with no room.
- The supersonic crack of the slug for a listener downrange is not modelled.
- The octave filters in `measure.py` are brick-wall and ring: band times under about 10 ms, and the 63 and 125 Hz
  rows, are coarse.

## Sources

- R. C. Maher and S. R. Shaw, "Directional aspects of forensic gunshot recordings", AES 39th International
  Conference, 2010: Remington 870, 18 in, 00 buck, levels at 3 m against azimuth.
- T. Routh and R. C. Maher, "Determining the muzzle blast duration and acoustical energy of quasi-anechoic gunshot
  recordings", AES 141st Convention, 2016.
- W. J. Murphy and R. L. Tubbs, "Assessment of noise exposure for indoor and outdoor firing ranges", J. Occup.
  Environ. Hyg. 4:688-697, 2007 (NIOSH).
- C. A. Kardous and R. D. Willson, "Limitations of using dosimeters in impulse noise environments", J. Occup.
  Environ. Hyg. 1:456-462, 2004 (NIOSH).
- NIOSH Health Hazard Evaluation Report 2013-0124-3208, Table B3: B-durations of an 870 in a shoothouse.
- D. K. Meinke et al., "Prevention of noise-induced hearing loss from recreational firearms", Semin. Hear.
  38:267-281, 2017.
- W. Krammer (Ball State University), as reproduced in E.A.R. Inc.'s "Gunfire Noise Level Reference Chart": a
  secondary source.
- R. P. Hamernik and K. D. Hsueh, J. Acoust. Soc. Am. 90:189-196, 1991: the Friedlander wave. MIL-STD-1474D: A- and
  B-duration.
- K. Fansler and E. Schmidt (BRL, 1983); Fansler, ARL-TR-1434 (1997): the directivity form. Recalled, not re-read
  (DTIC refused automated requests).
- J. Corner, "Theory of the Interior Ballistics of Guns", 1950: emptying of the bore. NASA SP-8072 (1971): acoustic
  efficiency. Recalled, not re-read.
- Chien and Soroka, J. Sound Vib. 43:9-20, 1975; ISO 9613-1; Morse and Ingard, "Theoretical Acoustics", 1968; Landau
  (1945): the outdoor range. Recalled, not re-read.
- Delany and Bazley (1970); Embleton, Piercy and Daigle (1983): ground. Allen and Berkley (1979); Eyring (1930): room.
- K. L. Johnson, "Contact Mechanics", 1985: Hertz contact time.
