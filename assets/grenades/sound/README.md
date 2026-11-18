# Grenades: synthesised sound

Every sound is synthesised from the simulation. No recording, and nothing derived from one, is in this repository,
and no audio files are committed. Credit: carpetshark. Simulation by Claude.

| File | What it is |
|---|---|
| `sim.py` | Stage A turns physics and published levels into recipes (`params.json`); stage B renders a recipe to samples. |
| `params.json` | The recipes, ground and body tables, playback mapping, Python checks. |
| `grenades-sound.js` | ES module. The same renderer in the browser, plus bounce synthesis on demand and a play helper. |
| `verify_js.py`, `verify_js.mjs`, `compare/js_parity.json` | The JS renderer against Python, sample by sample, under node. |

Rebuild from `assets/grenades/`: `python3 sound/sim.py`, then `python3 sound/verify_js.py` (needs node).

## How a sound is made

A recipe is a list of three kinds of component, each in pascals at a reference distance:
`pulse` (Friedlander, P (1 - t/T) e^(-t/T)), `modes` (decaying sines) and `noise` (seeded noise through a high-pass
and a low-pass biquad with an envelope). Randomness is a named mulberry32 stream shared by Python and JS.

| Sound | Built from | Level and its source |
|---|---|---|
| `pin_pull` | Wire scrape; ring modes of the pull ring: free-ring bending, 5.70 kHz and 16.1 kHz for a 29.5 mm ring of 2 mm steel wire (model sizes); a click as the pin clears | 68 dB at 0.3 m, game |
| `lever_release_<frag|flash|smoke>` | A click, then the free lever ringing: free-free strip modes from the model's lever length and 1.2 mm sheet (690 Hz, 1.9 kHz, 3.7 kHz for the frag) | 75 to 77 dB at 0.3 m, game |
| `lever_land_<...>` | The same strip landing 0.8 s later, two short knocks | 63 to 64 dB at 1 m, game |
| bounce (on demand) | Hertz contact of the body on the ground: contact time t_c = 2.87 (m^2 / (R E*^2 v))^(1/5) sets the knock's pitch 1 / 2 t_c and, through m v / t_c, its loudness; plus a short damped knock of the outer shell and, on loose ground, scattered grit | Pinned to 85 dB at 1 m for the frag on concrete at 5 m/s, game |
| `detonation_flash` | Friedlander pulse, 0.6 ms (game), a short burst through the side holes, the tube ringing, a low tail | **175 dB at 5 ft: the middle of the published 170 to 180 dB** |
| `detonation_frag` | Friedlander pulse, 1.2 ms (game), a low rumble, dirt falling | 175 dB at 5 ft. **Game value**: the manual gives no level for the frag, so the stun grenade's is borrowed |
| `smoke_ignite` | A small pop and the first rush | 118 dB at 1 m, game |
| `smoke_hiss_loop` | Jet noise from the four top holes, peak at St U / d = 0.2 x 60 m/s / 9 mm = 1.3 kHz (jet speed is game tuning, hole size inferred), 2 s loop | About 72 dB rms at 1 m at full emission, game; scale it with `SmokePlume.rate()` |

Contact times for the frag at 5 m/s: 0.19 ms on concrete, 0.29 wood, 1.8 packed dirt, 3.4 grass, 4.5 sand, so the
same throw knocks at 2.6 kHz on concrete and thuds at 280 Hz on dirt. Ground stiffnesses are estimates.

No loudness here comes from an energetic quantity. Bodies are solid placeholders, so their own sound is a short,
damped knock of the outer shell with estimated frequencies.

## Playback

`S.play(nameOrBuffer, { distance, destination, when, loop, protectionDb, gain })` delays by r / 343 s, lowers the
level by 20 log10(r / ref), low-passes at 18000 / (1 + r / 60) Hz for the air (estimate), and maps level to gain
with `10^((L - 175) / 60)`: a 3:1 compression so a 175 dB bang is full scale and an 85 dB bounce still plays at
about 0.03. **That mapping is game tuning, not physics.** `buffer.info.peakDb` keeps the true level.

```js
import GrenadeSound from './assets/grenades/sound/grenades-sound.js';
const S = await GrenadeSound.build(audioContext);
S.play('pin_pull'); S.play(S.leverRelease('frag'));
S.play(S.bounce('smoke-red', e.surface, e.normalSpeed), { distance: r });   // e: a bounce event from GrenadeThrow
S.play('detonation_flash', { distance: r });
```

## Checks (`params.json` checks and `compare/js_parity.json`, all passed)

- `detonation_flash` renders at 175.0 dB at 5 ft, inside the published 170 to 180 dB.
- `detonation_frag` renders at its labelled game level; the reference bounce at 84.7 dB against its labelled 85.
- Softer ground gives a longer contact, in order concrete, wood, dirt, grass, sand.
- JS against Python over all 11 recipes and 5 bounce cases: worst difference -312 dB relative to the peak (limit -120).

## Limits

Not checked by listening. Free field: no room, no ground reflection, no hearing model. Pulse durations, mechanical
levels, shell frequencies and the playback mapping are game tuning or estimates and are labelled so in `sim.py`.
