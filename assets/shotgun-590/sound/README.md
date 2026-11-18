# Shotgun 590: synthesised sound

Eleven sounds, built from the action simulation and the model, rendered identically in Python and in the browser.
**No recordings were used**, not as samples, not as filters, not as references for fitting. Credit: carpetshark.

```
python3 sound/sim.py          # writes params.json, compare/levels.json, compare/waveforms.png
python3 sound/verify_js.py    # node renders every sound with shotgun590-sound.js; compared sample by sample
```

| File | What it is |
|---|---|
| `sim.py` | builds each sound's component list from `action/action.json` and `model/inventory.json`, and renders it |
| `params.json` | the component lists, sources, mode frequencies, peak levels |
| `shotgun590-sound.js` | the runtime: `load()`, `names()`, `render()`, `buffer()`, `play()`, `info()` |
| `verify_js.py`, `verify_js.mjs` | the parity check |
| `compare/` | `js_parity.json`, `levels.json`, `waveforms.png` (simulation only) |

## Sounds

| Name | What | Peak at the listener |
|---|---|---|
| `shot_buck00_shooter`, `shot_slug_shooter` | the shot at the shooter's ear | 158.4 and 160.2 dB |
| `shot_buck00_bystander`, `shot_slug_bystander` | 5 m to the side of the muzzle | 151.2 and 152.3 dB |
| `pump`, `pump_back`, `pump_forward` | the whole rack, or each stroke | about 106 dB |
| `shell_insert` | a shell pushed into the magazine until its rim snaps past the cartridge stop | 91 dB |
| `dry_fire` | the hammer falling on an empty chamber | 99 dB |
| `safety`, `action_release` | the two small controls | 80 and 75 dB |

Levels are peak dB re 20 uPa. The shot's level follows from the simulation and two generic coefficients; the
mechanical levels are tuning guesses.

## How each sound is made

Three kinds of component, summed: a **Friedlander pulse** (a blast wave), a **decaying mode** (a part ringing), and a
**noise burst** through a band-pass filter with an attack and a decay (friction, gas, contact).

- **The shot.** The gas left in the barrel when the payload leaves holds `p V / (gamma - 1)` of energy (4.1 kJ for
  the buckshot load, 6.4 kJ for the slug, from the action simulation's muzzle pressure). A point release of energy E
  has a scale radius `R0 = (E / p0)^(1/3)`; the peak overpressure at distance r is taken as `0.25 p0 R0 / r`, times a
  directivity of 15 dB front to back, and the positive phase lasts `0.5 R0 / c`. One ground reflection follows.
  A noise tail and a low thump stand for the gas emptying; the hammer's click precedes the blast by the barrel time
  and the travel time; the barrel's own bending modes ring after it. The shot leaves the muzzle 8.4 ms after the
  trigger break and reaches the ear 2.6 ms later.
- **The rack.** Each event of the pump stroke in `action.json` makes a sound at its own time, with a strength set by
  the slide's speed at that moment: the unlock, the hull leaving, the rear stop, the shell meeting the bolt, the
  bolt closing, the lock. A hiss that grows with the slide's speed runs through each stroke. Heavy stops ring the
  barrel and the magazine tube.
- **Modes.** The barrel and the magazine tube are treated as free steel tubes of the model's lengths and diameters:
  480, 1322 and 2593 Hz for the barrel, 654, 1802 and 3533 Hz for the tube. The contact clicks at 3.1, 5.2 and
  7.4 kHz, the decay times and the shares of each component are guesses.

## Checks

| Check | Result |
|---|---|
| **Parity: Python against JavaScript**, every sound, sample by sample | worst difference -312 dB re peak (identical to rounding). **Pass.** |
| Shot level at the shooter's ear against published 12 gauge levels (151.5 dB with a 28 in barrel, 161.5 dB with 18.5 in; Krammer, as reproduced by E.A.R. Inc.) | 158.4 and 160.2 dB for a 20 in barrel: inside the range. A loose check: the two coefficients are generic values, and 3 dB either way would still pass. |

Nothing has been checked by listening against a real gun, and nothing was fitted to a recording.

## Runtime

```js
const S = Shotgun590Sound; await S.load('assets/shotgun-590/sound/params.json');
S.play(audioCtx, 'pump', { destination: mixNode, when: audioCtx.currentTime });
const buf = S.buffer(audioCtx, 'shot_buck00_shooter', { normalize: true });   // full scale, mix it yourself
S.info('pump').peak_db;                                                        // the simulated level
```

Without `normalize`, every buffer shares one scale (full scale is `S.fullScalePa` pascals), so the rack is about
50 dB under the shot, as simulated. That is truthful and too quiet to hear after a shot on ordinary speakers: most
games will want `normalize: true` and their own mix. Buffers are mono, 48 kHz, 0.08 to 0.54 s.

## Limits

- Dry sound only: no room, no distance beyond the two listening points, no hearing protection, no supersonic crack
  of the slug for a listener downrange. Put a reverb after it.
- The mechanical sounds are plausible constructions, not measurements. Their timing is the simulation's; their
  timbre and level are tuning.
- The blast is one idealised pulse. A real muzzle blast has structure this does not.
