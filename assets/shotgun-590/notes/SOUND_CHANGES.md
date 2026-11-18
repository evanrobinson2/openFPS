# Shotgun 590: sound change requests

Rule 7: each change request and what changed. Kept apart from `NOTES.md` so the geometry and sound histories do
not collide. Credit: carpetshark.

## Sound change request 1 (2026-11-17, from the owner, through the coordinating session): the sounds are clicks

**Request.** The owner, on the openFPS sound models: "the sounds are clicks", "they aren't not sounding like the
recording", and of the shots, "like a click on a keyboard or a crackle". The page's playback had already been
fixed, so the fault was in the models: more body in the blast and in the action noise, from physics and published
measurements only. There is no reference recording of this gun, and none was used.

**Diagnosis** (numbers in `sound/compare/bands_v1.json`, method in `sound/measure.py`).

- Version 1's shot was one 0.5 ms pulse, a ground reflection 16.6 dB under it, a guessed noise tail and an invented
  95 Hz tone. The tone held most of the late energy (46 % of all energy under 250 Hz), where small speakers play
  nothing. In the bands that are heard, 250 Hz to 8 kHz, the shot was 12 to 18 dB down by 10 to 50 ms.
- The rack's impacts were three guessed tones at 3.1, 5.2 and 7.4 kHz lasting 2 to 4 ms.

**What changed** (sound version 2; `sound/README.md` has the physics and the checks).

| Term | Version 1 | Version 2 |
|---|---|---|
| Blast level and directivity | two guessed coefficients | fitted to four published levels (Maher and Shaw 2010; Murphy and Tubbs 2007; Krammer), rms error 1.6 dB |
| Positive phase | 0.5 R0 / c, a guess | set from the published 456 µs (Kardous and Willson 2004) |
| Gas noise | guessed noise lasting 60 ms; a 95 Hz tone | jet noise from the bore's blow-down (3.8 ms choked), arriving 1.6 ms after the blast behind the gun; the tone is gone |
| Ground | half amplitude, the rear ray's level | the reflected ray's own direction and length, Delany-Bazley grass as a filter |
| Surroundings | none | four builds of every shot: a room (default), a covered firing point, open grass, free field |
| Impacts | guessed tones | momentum from the model's masses and the action simulation's speeds, Hertz contact time, modes of six parts |
| Rack events | 6 | 9, plus sliding noise in three bands and the action bars' rattle |

**Results.** Energy in the first 2 ms of the default shot: 35 % before, 9 % after. Time for the 500 Hz to 8 kHz
bands to stay 20 dB down: 61 to 88 ms before, 449 to 591 ms after. B-duration: 29.9 ms before, 181.8 ms after
(published for this gun indoors: 30 to 62 ms and 172 to 185 ms). The dry shot is shorter than version 1's, not
longer: 93 % of its energy in 2 ms. That is what the published free-field energy supports.

**Consequential choices and inferences.**

- **The default shot is now indoors.** Published free-field levels leave no room for a longer outdoor shot, and
  the only published durations for this gun are indoor ones. The names are unchanged, so the sample page plays the
  room shot without edits; the outdoor and dry shots have new names (`_covered`, `_field`, `_free`).
- The room and the covered firing point are chosen layouts with handbook absorption, not measured places.
- Jet-noise efficiency, source position and directivity, the scattering figures, every mechanical level, loss
  factor and part weight are recalled, inferred or guessed, and are labelled so in `sound/sim.py`.
- Mechanical peak levels changed with the new model: `shell_insert` 91 to 78 dB, `dry_fire` 99 to 93 dB, `safety`
  80 to 68 dB, `action_release` 75 to 64 dB. Both sets are guesses; a page that mixes by peak level is unaffected
  when it plays normalised, as the sample does.

**Not validated.** Nobody has listened. One published statement is not met (a third-octave band above 130 dB,
Murphy and Tubbs): `sound/README.md` explains why it cannot be reconciled with the published energy. The
front-to-back difference is 1 to 2 dB short of the published 15 to 16 dB.

**Files.** `sound/sim.py`, `sound/measure.py` (new), `sound/shotgun590-sound.js`, `sound/params.json`,
`sound/verify_js.py`, `sound/README.md`, `sound/compare/*`, `USAGE.md` (sound section), this file.

## Sound change request 2 (2026-11-17, from the coordinating session): an outdoor range, scored against recordings

**Request.** The owner made downloaded recordings the gate (an outdoor range, microphones roughly 20 to 70 m
away), scored by the coordinating session. Version 2's room had too much tail and its outdoor shots almost none.
Add a physical outdoor-range environment and far listeners; fit nothing to the recordings.

**What changed** (sound version 3). A chosen outdoor range: weak-shock lengthening with distance, ISO 9613-1 air
absorption, spherical-wave ground reflection at grazing angles, Lambert returns from a backstop 50 m away,
single scattering from tree trunks in woods behind and beside the range, one mirror reflection from the shelter
wall. Six far listeners for buckshot at 25, 50 and 100 m, beside the gun and 40 degrees off the line of fire. The
range is the default again; version 2's room shot is `..._room`.

**Not done, on purpose.** I did not open the recordings and set no parameter from them or from the gate's
figures. The layout has nothing 1 to 17 m off the direct path except the shelter wall, so the far shots carry almost
no energy between 10 and 50 ms and only 10 to 16 % between 2 and 10 ms. Benches, posts, vehicles or side berms would
fill that, but their presence and place at the recorded range are unknown, and I did not invent them.

**Results** are in `sound/README.md` (version 3 table) and `sound/compare/checks.json` (`outdoor_range`).

## Sound change request 3 (2026-11-17, from the owner, through the coordinating session): cinematic sound, and "I punched a bucket"

**Request.** The owner, on the physical shots of all three guns: "like a click on a keyboard or a crackle"; an FPS
needs designed sound because the sound at the shooter's ear cannot be reproduced on speakers; "don't copy the mp3,
we're simulating". On this gun: "yours sounds like I punched a bucket". He pointed to a VR game's pump shotgun as
the kind of result he wants: genre direction only, not heard, not looked up, not imitated. Wanted: the heaviest gun
of the set, a deep boom, a dense broadband blast, a long tail, nothing hollow or ringing on the shot, and the pump
as a featured two-stroke rack that also works on its own.

**Diagnosis of the bucket (an inference: nobody measured what the owner heard).** The simulated shot carries 24
structural modes (196 Hz to 5.9 kHz, decaying for up to 90 ms) that start at the hammer fall and at shot exit, and its
surroundings add early reflections from 4.2 ms on. Normalised and played on speakers, with the blast itself too short
to hear, what remains is those tones and that comb. The same narrow-peak measure used for the cinematic shot (one
render, since the simulated shot has no seed to vary) gives, in the first 100 ms: 3.6 dB at 1166 Hz for the default
shot, 4.1 dB at 801 Hz in the room (that band takes 326 ms to fall 20 dB, the band below it 163 ms), and 4.4 dB at
1386 Hz in the free field, with 7.0 dB at 1200 Hz in the free field's tail.

**What changed.**

| | Before | Now |
|---|---|---|
| Default of `play()` | the simulated sound | the cinematic sound (`shared/cinematic-sound/`); `{ mode: 'realistic' }` plays the simulated one |
| Modes on the shot | 24, from the hammer fall | none in the cinematic shot; they stay in the pump and in `realistic` |
| Body | the blast wave and reflections | broadband noise, no resonant filter, two decay rates (48 and 142 ms) |
| Low end | none below 250 Hz to speak of (40 to 120 Hz at -25 dB of the total) | a thump falling from 151 Hz through 47 Hz with harmonics (40 to 120 Hz at -4.5 dB) |
| Tail | 133 ms to -40 dB | 1207 ms outdoors, 1433 ms in the room |
| Pump | the simulated rack | the same rack plus weight, clack and sliding noise on the action's events; 19.5 dB between the strokes |
| API | `load`, `render`, `buffer`, `play` | the same, plus `build()` returning the object the other guns return |

**Unchanged.** `params.json`, `sim.py`, `render()`, `buffer()`: all 33 simulated sounds are bit-identical to commit
aa037ac. **Not done:** no listening test; the cinematic constants are design choices, not physics.
