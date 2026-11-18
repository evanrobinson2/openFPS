# G44 V: how to use this asset

A simulation-grade G44 V, the .22 LR straight-blowback pistol: geometry as a parametric part-by-part recipe with every
item of the manual's exploded drawing, and the action, recoil, ballistics and sound simulated from physics and published
numbers. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) fires the pistol in a page: synthesised sound with a choice of
ammunition, surroundings and earmuffs, the slide cycle and recoil in slow motion, and a point-of-impact table.

## Status

| Part | State |
|---|---|
| Geometry (`model/`) | Ready as a recipe. `build.py` is Blender Python: 60 named objects covering all 38 items of the manual's component list (pp. 36-37), internals included; 13 sockets; 8 clips. It writes `build/g44v/g44v.glb` at the repository root, a build output that is never committed. Renders of a build are in `renders/` (v1's in `renders/v1/`). Silhouette against the reference: IoU 0.987. v2 is the detail pass that followed the owner's review of v1 (`notes/DETAIL_PASS_V2.md`); **v2 itself has not been reviewed**. |
| Action and recoil (`action/`) | Ready. Three named CCI loads, calibrated to CCI's test-barrel velocities; slide mass and spring loads are inferred (not published). JS matches Python to 1e-15. |
| Ballistics (`ballistics/`) | Ready. G1 point mass; reproduces CCI's downrange tables to 4.5 fps and 0.06 in. JS matches Python exactly. |
| Sound (`sound/`) | Ready, version 2. Synthesised in the browser from `params.json`; JS matches Python to -297 dB. Level calibrated to a published .22 pistol at the ear and checked against seven other published figures (pistol within 1 dB, rifles 3 to 5 dB high). Not validated by listening; no recording of this pistol exists. |

## Run the sample

The modules load JSON with `fetch`, so serve the repo over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/g44v/sample/
```

## Use it in your own page

```html
<script src="assets/g44v/action/g44v-action.js"></script>          <!-- window.G44VAction -->
<script src="assets/g44v/ballistics/g44v-ballistics.js"></script>  <!-- window.G44VBallistics -->
<script type="module">
import G44VSound from './assets/g44v/sound/g44v-sound.js';

const ac = new AudioContext({ sampleRate: 48000 });
const S = await G44VSound.build(ac);                    // loads params.json next to the module
await G44VAction.load('assets/g44v/action/action.json');

// one shot: sound now, mechanism and recoil sampled every frame from t = 0 (the trigger break)
const chain = S.chain({ overlay: 'indoor_range', hpd: false, ear: true });
chain.output.connect(ac.destination);
const src = ac.createBufferSource(); src.buffer = S.shot('cci_standard_velocity'); src.connect(chain.input); src.start();
const s = G44VAction.sample(t, { ammo: 'cci_standard_velocity', stance: 'two_hand', lastRound: false });
// s.slideZ (add to p01_slide.position.z), s.springScale (p03_recoil_spring), s.firingPinZ (p04_firing_pin),
// s.slideHeldOpen, s.slideStopRot, s.recoil.{pos, pitch, pivot}

// a bullet: from the eye along the line of sight, 25 m zero
const shot = G44VBallistics.fire({ origin: eye, dir: lineOfSight, ammo: 'cci_standard_velocity', zero: 25, rng: Math.random });
const hits = shot.advance(dt, targets);                 // per frame, or shot.trace(targets)
</script>
```

Ammunition keys: `cci_standard_velocity`, `cci_mini_mag`, `cci_quiet_22`. Full APIs: `action/README.md`,
`ballistics/README.md`, `sound/README.md`.

## Frame and units

Metres and seconds. +Z towards the muzzle, +Y up, +X to the shooter's left; the origin is on the bore axis at the slide's
rear face (slide forward). Time zero for a shot is the trigger bar releasing the firing pin; the charge is alight 2.70 ms
later. The model's node tree:

```
g44v
  frame_group        p17_frame and everything that stays with it: p02_barrel, p03_recoil_spring_assembly (the barrel is fixed
                     in a blowback pistol), locking block, trigger group, slide stop lever, slide lock, magazine catch, pins
    slide_group      p01_slide and what rides in it: firing pin, its spring, sleeve and cups, firing pin safety, extractor,
                     depressor plunger, cover plate, sights
    magazine_group   p31_magazine_tube with follower, spring, insert, floor plate, loading assists
  accessories        the two beavertail backstraps, shown detached behind the grip as on manual p. 9
```

Pivots are the real axes: the trigger and the slide stop lever turn on the trigger pin, the trigger safety on its own pin,
the slide, firing pin and trigger bar slide along the bore, the slide lock and firing pin safety move vertically, the
magazine and follower move along the magazine axis (raked 21.8 degrees). Sockets: `socket_muzzle`, `socket_chamber`,
`socket_eject`, `socket_ads_eye`, `socket_front_sight`, `socket_rear_sight`, `socket_hand_right`, `socket_hand_left`,
`socket_trigger_finger`, `socket_magazine`, `socket_rail`, and one for each backstrap's installed position. There is no
optic socket: neither the manual nor the maker's table shows an optic mount on this model. Clips: `trigger_safety`,
`trigger_pull`, `slide_cycle`, `slide_lock_open`, `slide_release`, `magazine_out`, `magazine_in`, `field_strip`. Positions,
part numbers and sources for every object are in `model/inventory.json` and `notes/DECOMPOSITION.md`.

## Rebuild

| What | Command (from `assets/g44v/`) | Needs |
|---|---|---|
| Geometry and its checks | `model/rebuild.sh` (build, `checks.json`, `notes/DECOMPOSITION.md`) | Blender 4.x or 5.x. Writes `build/g44v/g44v.glb` and `.blend` at the repository root, ignored by git |
| Renders and the matched comparison | `blender -b ../../build/g44v/g44v.blend --python model/tools/render.py -- match_left left right ...`, then `python3 model/tools/compare.py` | The reference mask needs local copies in `refs-local/` (`notes/REFERENCES.md`) |
| Action | `python3 action/sim.py`, then `node action/test_action.js` | numpy, scipy, matplotlib; node |
| Ballistics | `python3 ballistics/sim.py`, then `node ballistics/test.js` | after the action (it reads the pistol muzzle velocities) |
| Sound | `python3 sound/sim.py`, then `python3 sound/verify_js.py` | after the action |

Order matters: model, action, ballistics, sound. Each build is deterministic.

## Checks and their results

| Check | Result | File |
|---|---|---|
| Manual component list covered | 38 of 38 items are named objects (items 25 and 30 are blank in the manual) | `model/checks.json` |
| Dimensions against the maker's specification table | length 184.2 / 185, slide 173.6 / 174, width 32.3 / 32, slide width 25.7 / 25.5, height 125.7 / 128, sight radius 157.7 / 158, trigger distance 68.7 / 70, barrel 101.3 / 102 mm; worst -1.9 % | `model/checks.json` |
| Matched visual comparison (reference cameras) | silhouette IoU 0.987; reference outline to model outline mean 0.17 mm, 95th percentile 0.38 mm, worst 1.4 mm. Close-ups of slide, grip and controls and the slide from above, with interior edge coverage, v1 against v2 | `model/compare.json`, `notes/DETAIL_PASS_V2.md`, `renders/compare_outline.png` |
| Clip interpenetration | 0 intersecting pairs in the rest pose and in all 8 clips, every frame | `model/checks.json` |
| Action: calibration and function | test-barrel velocities reproduced; peak pressures at or under the SAAMI limit; standard and high velocity make the full stroke, CCI Quiet-22 stops at 34.0 of 45 mm, as the manual and CCI say it may | `action/action.json` (`validation`) |
| Action JS against Python | 60 random samples, worst difference 2e-15; seeded brass within 0.006 mm | `action/parity.json` |
| Ballistics against CCI's tables | worst 4.5 fps and 0.06 in over three loads | `ballistics/ballistics.json` (`validation`) |
| Ballistics JS against Python | 9 cases, difference 0 | `ballistics/parity.json` |
| Sound levels against published figures | calibrated on a 4.5 in .22 pistol at the ear (157.5 dB); 10 in pistol predicted within 1 dB at two positions; A-duration 0.12 to 0.15 ms against a published limit of 0.2 ms; pistol 155.2 to 159.2 dB at 1 m to the side, inside the published 149 to 167 dB | `sound/compare/check.json` |
| Sound before and after the click fix | energy in the first 2 ms: 94.8 % before, 94.0 % after in pascals, 61.6 % as played; bands last 12 to 26 ms as played (were 7 to 11) | `sound/compare/before_after.json` |
| Sound JS against Python | 28 outputs, worst -296.9 dB re peak | `sound/compare/js_parity.json` |

## Limits

- **v2 has not had owner review.** The silhouette is traced from the reference, so its agreement is close by
  construction. `notes/DETAIL_PASS_V2.md` lists every feature added in v2 and every one merged or left out, with the reason.
- **Internals are functional reconstructions, not measured parts.** The manual shows them only in a small exploded
  drawing and a few photographs; 24 of 60 objects are marked inferred, and several marked measured have only their position measured. They sit on the right axes, move the right way and
  do not collide, but their shapes are not the maker's.
- No maker's names or logos: plain placeholder panels on the slide, barrel hood, grip and magazine. No cartridges are
  modelled; the magazine is shown empty.
- Trigger travel in the model is 7.5 degrees, set by the traced outlines; the real travel is not published.
- Slide mass (105 g), recoil spring loads (24 to 65 N) and firing pin spring loads are not published. They were chosen so
  the makers' statements about ammunition hold; `action/README.md` gives the sensitivity.
- Sound: two calibration constants (blast level, mechanical radiation), inferred directivity, structure and ground scatter; not checked by listening. In an open field the shot is physically short (94 % of its energy in 2 ms); `chain({ ear: true })` is a playback mapping that keeps the echo and the action audible, and the range surroundings add the tail. See `sound/README.md`.
- See `notes/NOTES.md` for every consequential inference, omission and correction.

## Sources

`notes/MANUAL_NOTES.md` summarises the facts used from the instructions for use, with page numbers, and the maker's
specification table. `notes/REFERENCES.md` cites the images the shape was measured from. Neither the manual nor the
images are in this repository.
