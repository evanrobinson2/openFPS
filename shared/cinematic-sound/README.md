# Cinematic gun sound: the default sound of every openFPS gun

Credit: carpetshark. Shared by `assets/hk416`, `assets/g44v` and `assets/shotgun-590` (and the suppressor through
the HK416). This folder is outside `assets/` because `tools/check_assets.py` treats every folder there as an asset.

## The decision

The owner listened to the physical simulations and heard "a click on a keyboard or a crackle". That is what the
physics gives: at the shooter's ear a shot is a 0.2 ms shock, and no loudspeaker can play it. His decision
(2026-11-17): a game needs designed sound, "don't copy the mp3, we're simulating". So:

- **`cinematic` is the default mode of every gun.** It is a designed, game-style shot: crack, body, falling
  thump, the action, a long tail and a compressed bus.
- **`realistic` is the physical simulation, unchanged.** Same numbers, same samples as before (proof below).
- Everything is synthesised at runtime from code and from each gun's simulation values. No recording or video was
  used, sampled, analysed or imitated, and no audio file is in git. The VR-game shotgun the owner named was taken
  as genre direction only; nobody here listened to it.

**The cinematic sound is not a physical claim.** Every constant in `cinematic-sound.js` is a design choice and is
labelled so in the code. What comes from the simulations is the input: the numbers in the table below and the
physical blast and action waveforms.

## What drives the sound

| Input (from each gun's simulation) | G44 V, CCI Standard | HK416, M855 | 590, 00 buck | Drives |
|---|---|---|---|---|
| Muzzle energy, J | 95.3 | 1451.3 | 2568.7 | size |
| Muzzle gas energy, J | 166.8 | 4336 | 4127.8 | size |
| Bore, mm | 5.6 | 5.56 | 18.5 | size, body band |
| Barrel, mm | 102 | 368.3 | 508 | body band |
| Gas (charge) mass, g | 0.085 | 1.656 | 1.75 | length of the gas-noise burst |
| Cyclic period, s | 0.13 (trigger reset) | 0.0749 | none (pump) | thump and roar length, voice stealing, tail ducking |
| Muzzle velocity, m/s | 271 | 850 | 404 | bullet crack: present or not, and its lead over the blast |
| Physical blast waveform | yes | yes | yes (blast and jet only) | the crack layer |
| Action events and clips | yes | yes | yes (the pump) | the mechanical layer |
| Surroundings | 2 | 11 | 4 | kind of tail, decay time, slapback delays |

`design(sim)` turns these into the layer parameters. `size = 0.65 e + 0.35 b`, with `e` the log of the total energy
(300 J = 0, 10 kJ = 1) and `b` the log of the bore (5.6 mm = 0, 12 gauge = 1).

| Design output | G44 V | HK416 | 590 buck |
|---|---|---|---|
| size | 0.00 | 0.55 | 0.93 |
| Thump: pitch after one decay time, Hz (starts 3.2 times higher, keeps falling) | 105 | 65 | 47 |
| Thump decay, ms | 38 | 37 (held under half the cyclic period; 96 without) | 135 |
| Body band centre, Hz | 570 | 300 | 178 |
| Body decay / roar decay, ms | 18 / 40 | 36 / 45 | 48 / 142 |
| Gas-noise centre, Hz / decay, ms | 5200 / 4.1 | 3990 / 9.4 | 3160 / 9.6 |
| Tail decay scale / gain re dry, dB | 0.75 / -20 | 1.05 / -16.2 | 1.26 / -13.5 |
| Output trim after the bus, dB | -2.5 | -1.1 | -0.2 |

## The layers

1. **Crack.** The gun's own physical blast waveform (from `realistic`), peak 1, plus a broadband gas-noise burst.
   It is the sample peak and under 3 % of the energy.
2. **Body.** Broadband noise between about a third and four times the body centre, 6 dB/octave skirts, two decay
   rates (punch and roar). There is **no resonant filter and no decaying sine** in the shot: nothing can ring.
3. **Sub thump.** A sine whose pitch is `f_start / (1 + t / tp)`: it never settles on a note. Second and third
   harmonics and a tanh stage put energy between 100 and 450 Hz so that small speakers carry it.
4. **Mechanical.** Self-loaders: the simulated action noise of the cycle on the action's own clock, about 25 dB
   above its physical place. Pump gun: nothing in the shot; the rack is its own sound (below). The receiver, barrel
   and stock modes of the simulated shotgun shot are left out of the cinematic shot; they stay in the pump.
5. **Tail.** A stereo impulse response made of decaying noise (never single taps: each echo is a smear of noise,
   so there is no comb filter). Outdoors: ground scatter, slapback returns at the delays the simulated place
   gives, and a diffuse tail of at least 1.3 s times the size scale. Indoors: fourteen early returns and a dense
   tail at the room's own decay time. A `ConvolverNode` applies it, so it follows the selected surroundings.
6. **Bus.** Drive, soft saturation (tanh, 4x oversampled), compressor (3:1, 8 ms attack), limiter (20:1), soft
   ceiling at -1.5 dBFS, then the output gain (size trim, distance, part of a suppressor's reduction), then
   earmuffs if worn. Every gun drives the bus equally hard; the size order is set after it.

**Mechanical clips** (`mech`, and the pump): the simulated clip at 60 % plus designed weight on each action
event: a clack whose brightness follows the contact time, a low thud and short falling thump for a heavy part
stopping (weight = the event's momentum or level in the simulation), and broadband sliding noise between events.

**Autofire.** `fire()` fades what is still sounding of the previous shot to 8 % over a quarter of the cyclic
period (voice stealing) and dips the tail return to 10 % at each shot, recovering over 3.5 periods. Pre-rendered
multi-shot buffers (`S.shot('auto1s')`) have the same stealing baked in.

**Suppressor** (HK416 with `assets/suppressor-qd-556`). The physical reduction `R` of the muzzle blast at the ear is
read from the patched tables (20.6 dB). Crack: the suppressed pop's own waveform at -0.55 R. Gas noise -0.5 R,
longer and lower. Body -0.4 R. Thump -0.45 R, shorter. Tail -0.5 R and darker. Output -0.15 R. The action noise
and the bullet's shock are not changed.

**Distance.** `distance` in metres from the muzzle and `bearing: 'front' | 'side'` (or a `perspective` name the gun
already has). With each doubling of `1 + d / 4 m` the crack loses 1.8 dB and the body 0.8 dB against the thump,
the top is rolled off (20 kHz / (1 + d / 12 m)), the tail gains 1.2 dB against the dry shot and the output falls
3.2 dB. For a supersonic round heard near the line of fire the bullet's shock (an N-wave and a whip of noise)
comes first and the blast follows `d (1/c - 1/v)` later. At the gun the shock is heard only as a hiss off the
ground downrange. The propagation delay `d / c` itself is not in the buffer: `S.info(buffer).arrival_s` gives it.

## API (the same for all three guns)

```js
// HK416 and G44 V are ES modules; the shotgun is a classic script (window.Shotgun590Sound). All three load
// shared/cinematic-sound/cinematic-sound.js themselves.
import HK416Sound from './assets/hk416/sound/hk416-sound.js';
const ac = new AudioContext({ sampleRate: 48000 });
const S = await HK416Sound.build(ac);                    // mode 'cinematic' unless { mode: 'realistic' }
// const S = await G44VSound.build(ac);                  // same shape
// const S = await Shotgun590Sound.build(ac);            // same shape

const chain = await S.chain({ overlay: 'range_berm' });  // omit overlay for the gun's default; null or 'dry' = no tail
chain.output.connect(ac.destination);

chain.fire();                                            // one shot now
chain.fire({ when: ac.currentTime + 0.1, key: 'single' });   // scheduled; key = variant (HK416) or load (G44 V, shotgun)
chain.auto({ shots: 10 });                               // autofire at the gun's cyclic period; or call fire() per shot
chain.mech('charge');                                    // a mechanical sound ('slide_rack', 'pump', ...: S.mechClips / S.clips)
chain.fire({ pump: true });                              // shotgun: the shot, then the rack 0.45 s later (or pump: seconds)

await chain.set({ distance: 50, bearing: 'front' });     // 50 m down the line of fire; { distance: 0 } = at the gun
await chain.set({ hpd: true });                          // earmuffs
await chain.set({ overlay: 'hallway' });                 // surroundings
await chain.set({ mode: 'realistic' });                  // the physical simulation, through the gun's own realistic chain
S.setMode('realistic');                                  // or switch the default for new chains and S.shot()

// suppressor (HK416): patch the tables as before, hand them to the chain
const hkParams = await (await fetch('assets/hk416/sound/params.json')).json();
await SuppressorQD556.load('assets/suppressor-qd-556/sim/suppressor.json');
const can = SuppressorQD556.soundParams(hkParams, 'subsequent');
await chain.set({ suppressor: can });                    // null takes it off
```

Calls that existed before still work and now follow the mode: `S.shot(key, opts)` and `S.mech(clip, opts)` return
an `AudioBuffer` to connect to `chain.input` yourself (no voice stealing or tail ducking that way; the bus still
protects the output), `S.chain(opts)` returns `{ input, output, set }`, and `HK416Sound.build(ac, { params:
SuppressorQD556.soundParams(...) })` builds a suppressed rifle in either mode. `S.realShot`, `S.realMech` and
`S.realChain` are always the physical ones. `Shotgun590Sound.play(ac, name, opts)` is cinematic unless
`opts.mode === 'realistic'`; `render()` and `buffer()` are the physical sounds as before. Options per shot:
`{ mode, distance, bearing, perspective, suppressor, seed }`. `S.design(key)` returns the table above for a load.

The cinematic chain's output is stereo (the tail differs left and right; the dry shot is centred).

## Acceptance

Measured by `measure.html` on the output of the page's real chain, rendered with `OfflineAudioContext` in Chromium
(two channels, 48 kHz): `compare/results.json`. Targets were fixed in the page before the first measurement.
Onset = the first sample at 10 % of the peak; short-term level = 10 ms RMS; crest = peak over the RMS of the first
300 ms; the tail is "audible" until the short-term level is 40 dB under its maximum.

**The default shot, outdoors** (HK416 `range_berm`, G44 V `outdoor_berm`, shotgun `range`):

| | Target | G44 V | HK416 | 590 buck | Realistic 590, for scale |
|---|---|---|---|---|---|
| Energy in 0-2 ms, % | under 10 (brief: well under 25) | 2.4 | 1.3 | 0.4 | 49.6 |
| 2-10 ms, % | | 16.0 | 10.3 | 2.8 | 25.0 |
| 10-50 ms, % | | 43.2 | 33.0 | 11.6 | 24.1 |
| 50-300 ms, % | | 37.3 | 40.7 | 56.0 | 1.3 |
| after 300 ms, % | | 1.0 | 14.7 | 29.3 | 0.0 |
| Crest factor, dB | under 14 | 12.8 | 12.2 | 6.4 | 30.8 |
| Short-term level down 20 dB after, ms | at least 60 | 255 | 457 | 571 | 46 |
| Audible tail (-40 dB), ms | at least 300 | 611 | 939 | 1207 | 133 |
| 40-120 Hz re total, dB | at least -10 | -6.3 | -7.6 | -4.5 | -25.2 |
| 120-300 Hz re total, dB | at least -12 | -3.9 | -5.0 | -6.2 | -12.3 |
| Peak, dBFS (clipped samples) | at most -1 (0) | -5.0 (0) | -3.6 (0) | -2.2 (0) | |
| Loudness figure, dB | ordered, 3 to 10 dB apart in all | -18.0 | -15.7 | -10.1 | -30.9 |

The highest peak of any cinematic render in the set is -1.63 dBFS (the pump's back stroke); none has a sample at
full scale. Indoors and dry, and the other loads, are in `results.json`.

**Narrow peaks** (the "punched a bucket" check). Power in 1/12-octave bands (never fewer than four FFT bins)
against the same spectrum smoothed over 1/3 octave, 150 Hz to 2 kHz, power spectra averaged over eight renders
with different noise seeds. Limit set before measuring: **4 dB**.

| Largest excess, dB (at Hz) | First 100 ms, outdoors | Tail, outdoors | First 100 ms, indoors | Tail, indoors |
|---|---|---|---|---|
| 590 buck | 1.35 (1469) | 3.54 (159) | 0.99 (1512) | 2.46 (159) |
| HK416 | 1.09 (1512) | 3.18 (168) | 1.10 (1512) | 2.14 (168) |
| G44 V | 0.91 (925) | 3.32 (300) | 1.06 (925) | 2.33 (252) |

How long the worst band rings against its neighbours a third of an octave either side (time to fall 20 dB,
shotgun outdoors): first 100 ms, 515 ms against 519 and 524; tail, 192 ms against 217 and 333. No band outlasts
its neighbours. The tail figures sit at the bottom of the range, where a 1/12-octave band is only 9 to 17 Hz wide
and the thump's third harmonic passes through as it falls.

**The pump on its own** (dry, shotgun): back stroke -8.9 dB and forward stroke -8.7 dB short-term level at the
action's rear stop (0.150 s) and lock (0.330 s), 19.5 dB of gap between them, sliding noise 7.6 dB under the first
stroke. Through the outdoor chain its loudness figure is 5.2 dB under the shot's.

**One-second burst through `fire()`**:

| | Target | G44 V, 8 at 0.13 s | HK416, 14 at 0.0749 s | 590, 3 at 0.5 s |
|---|---|---|---|---|
| Peak, dBFS (clipped) | at most -1 (0) | -3.6 (0) | -2.9 (0) | -2.1 (0) |
| Smallest dip between shots, dB | at least 6 | 17.1 | 7.3 | 11.1 |
| Last shot against first, dB | within 2 | +2.1 | **+2.2** | +1.1 |
| Shots 2 to last, range, dB | | 1.4 | 1.4 | 0.1 |

The first-against-last target is **missed by 0.2 dB** on the HK416 and 0.1 dB on the G44 V. The per-shot levels
(`shot_levels_db`) show why: the first shot is 2 dB under the rest and there is no build-up after it (HK416: -9.4,
then -7.5 to -6.9, with -8.3 where the first shot's noise seed comes round again).

**Suppressed against bare** (HK416, `subsequent` state, physical reduction 20.6 dB):

| | Target | At the gun | 50 m down the line of fire |
|---|---|---|---|
| Quieter by, dB | 6 to 14 | 9.9 | 10.6 |
| Audible tail, ms (bare / suppressed) | shorter | 939 / 580 | 940 / 577 |
| Bullet crack before the blast arrives | unchanged | not heard directly at the gun | identical samples over 87 ms (difference 0) |

**Distance** (loudness figure, dB, and spectral centroid, Hz):

| | At the gun | 10 m | 50 m | 100 m |
|---|---|---|---|---|
| 590 buck, front | -10.1 / 425 | -15.9 / 368 | -22.0 / 308 | -24.9 / 275 |
| HK416, front | -15.7 / 753 | -21.3 / 622 | -27.4 / 478 | -30.2 / 400 |
| HK416, side | | -21.9 / 612 | -28.1 / 468 | -31.1 / 387 |
| G44 V | -18.0 / 637 | -24.0 / 507 | -30.4 / 368 | -33.4 / 307 |

HK416 bullet crack to blast, designed `d (1/c - 1/v)`: 17.4, 86.9, 173.7 ms. Measured from the first arrival to the
loudest 10 ms of the render: 27.0, 96.5, 183.5 ms, a constant 9.7 ms later because the loudest 10 ms is the thump
building, not the blast's first sample. The shotgun's buckshot is supersonic only to 18.6 m: a 4.4 ms lead at
10 m and no crack at 50 and 100 m. The .22 is subsonic: no crack.

**Earmuffs**: quieter by 5.6 dB (shotgun), 12.1 dB (HK416, its own published-attenuation filter) and 8.0 dB (G44 V).

**Realistic is unchanged.** `git archive aa037ac assets/hk416/sound/hk416-sound.js assets/hk416/sound/params.json
assets/g44v/sound/g44v-sound.js assets/g44v/sound/params.json assets/shotgun-590/sound/shotgun590-sound.js
assets/shotgun-590/sound/params.json | tar -x -C shared/cinematic-sound/audio/_base` unpacks the modules of the
merged commit into the ignored folder. Then:

- `measure.html?base=1` renders 19 jobs through the old modules and through the current ones in mode `realistic`
  (shots, bursts, surroundings, earmuffs, ear stage on and off, mechanical clips, `chain.fire()`, `chain.mech()`,
  `Shotgun590Sound.play()`), in `OfflineAudioContext`: **every sample identical, difference 0** (`results.json`,
  `realistic_identity`).
- `node shared/cinematic-sound/check.mjs` compares the raw synthesis: 27 HK416 outputs, 28 G44 V outputs and all 33
  shotgun sounds bit-identical, and the three `params.json` byte-identical (`compare/check.json`).

## Run it

```
python3 shared/cinematic-sound/serve.py 8781       # serves the repository; accepts the page's WAVs and results
# http://127.0.0.1:8781/shared/cinematic-sound/measure.html?save=1&base=1
node shared/cinematic-sound/check.mjs
```

`?save=1` writes 53 labelled WAVs to `shared/cinematic-sound/audio/` (ignored by git: rule 3) and
`compare/results.json`. `?guns=hk416` limits the run.

## Files

| File | What |
|---|---|
| `cinematic-sound.js` | The synthesis, the chain and the measurements. UMD: `globalThis.OpenFPSCinematicSound`. |
| `measure.html`, `identity.js` | The acceptance page and the realistic-identity jobs. |
| `serve.py` | Local server for the page (127.0.0.1 only). |
| `check.mjs` | Node checks: copied simulation values, dry shots, size order, realistic raw identity. |
| `compare/results.json`, `compare/check.json` | The numbers above. |

## Limits

- **Nobody has listened to it.** Every claim here is a measurement. The owner's ear decides whether it sounds
  right; the constants are in one place (`design()`, `BUS`) for that review.
- Designed, not physical: levels, spectra and decay times are choices. Only `realistic` carries simulated levels.
- JavaScript only. There is no Python counterpart of the cinematic synthesis, so no Python parity check for it.
- The bus uses the browser's `DynamicsCompressorNode`. The numbers were measured in Chromium; another engine's
  compressor may differ by a decibel or so. The ceiling stage does not depend on it.
- The burst target "last shot within 2 dB of the first" is missed by 0.2 dB (see above).
- The suppressed shot's crest factor at the gun is 16.9 dB (the 14 dB target is for the default shot).
- Distance is a design law, not propagation: no ground effect, no terrain, the muzzle velocity is held over the
  range, and the bullet's miss distance is fixed at 3 m. `bearing: 'side'` differs from `'front'` only by the
  bullet crack. The propagation delay is left to the game.
- Tail: the kind (indoor or outdoor) of each surroundings is a label in each gun's module; decay time and slapback
  delays come from the simulated place, the rest is design. HK416 outdoors: 0.6 of the simulated response's length
  stands for its decay time.
- Voice stealing and tail ducking need `chain.fire()`. A buffer connected to `chain.input` by hand gets neither.
- The G44 V's cyclic period is the simulation's trigger reset time (0.13 s); the shotgun has none, so its
  three-shot "burst" at 0.5 s is only a test of `fire()`.
- Earmuffs for the shotgun and G44 V are two shelves (about 15 dB at 125 Hz, 33 dB above 1 kHz); the HK416 uses its
  own filter. Realistic mode on the shotgun had no earmuffs before; the new `chain` gives it the same two shelves.
- The suppressor's `soundParams()` now scales the v2 tables' gas-volume body and jet gain (it did not, and gave
  12.2 dB instead of 20.6 dB on sound v2). Its jet is not lengthened in v2's shared envelope, and its own parity
  case `sound overlay` still fails because its reference numbers were generated from the v1 HK416 tables:
  `python3 assets/suppressor-qd-556/sim/sim.py` needs a rerun by that asset's owner.
- `assets/hk416/sound/index.html` and the suppressor's sample page inspect the physical simulation and are pinned
  to `mode: 'realistic'`.
