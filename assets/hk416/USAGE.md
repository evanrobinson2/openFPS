# HK416 D14.5RS: how to use this asset

A simulation-grade HK416 with a 14.5 in barrel: the mechanism, recoil, ballistics and sound are simulated from
physics and HK's published figures. The shape is a measured, parametric part-by-part recipe. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) fires the rifle in a page: synthesised sound with a
choice of surroundings and earmuffs, the bolt carrier and recoil in slow motion, the muzzle flash and smoke, and a
point-of-impact table.

## Status

| Part | State |
|---|---|
| Sound (`sound/`) | Ready. Synthesised in the browser from `params.json`; the JS port matches the Python to -160 dB. Not yet validated by listening. |
| Action and recoil (`action/`) | Ready. Calibrated to the manual: 850 m/s, 52,000 psi, about 800 rpm, 3.49 kg. |
| Ballistics (`ballistics/`) | Ready. M855, Mk 262 and M856 with G7 drag, HK's zeros, dispersion and terminal effects. |
| Muzzle flash and smoke (`flash/`) | Ready. Under-expanded jet through the flash hider, driven by `action/`'s bore state at shot exit: flash phases, a light source with intensity over time, smoke puffs. Shape fitted to one reference photo and brightness calibrated to one light-meter test; the JS runtime matches the Python (62 checks). Not yet reviewed by eye by the owner. |
| Geometry (`model/`) | Ready as a recipe. `build.py` is Blender Python: 301 named parts, 13 clips, 7 sockets, two LODs. It writes `hk416.glb`, a build output that is never committed. The sample page doesn't draw the model yet. Renders of a build are in `renders/`. |

## Run the sample

The modules load JSON with `fetch`, so serve the repo over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/hk416/sample/
```

`sound/index.html` is a second, sound-only sample with every perspective, surroundings and mechanical sound.

## Use it in your own page

```html
<script src="assets/hk416/action/hk416-action.js"></script>          <!-- window.HK416Action -->
<script src="assets/hk416/ballistics/hk416-ballistics.js"></script>  <!-- window.HK416Ballistics -->
<script type="module">
import HK416Sound from './assets/hk416/sound/hk416-sound.js';

const ac = new AudioContext({ sampleRate: 48000 });
const S = await HK416Sound.build(ac);                 // loads params.json next to the module
await HK416Action.load('assets/hk416/action/action.json');

// one shot: sound now, mechanism and recoil sampled every frame from t = 0 (the trigger break)
const chain = await S.chain({ overlay: 'range_berm', hpd: false, ear: true });
chain.output.connect(ac.destination);
const src = ac.createBufferSource(); src.buffer = S.shot('single'); src.connect(chain.input); src.start();
const s = HK416Action.sample(t, { stance: 'ads', mode: 'semi' });   // s.carrierZ, s.boltRot, s.recoil.{pos,pitch,yaw,pivot}

// a bullet: from the eye along the line of sight, with HK's 100 yd zero
const shot = HK416Ballistics.fire({ origin: eye, dir: lineOfSight, ammo: 'M855', zero: 'hk100yd' });
const hits = shot.trace(targets);                     // or shot.advance(dt, targets) per frame
</script>
```

Full APIs: `sound/README.md`, `action/README.md`, `ballistics/README.md`, `flash/README.md`.

## Frame and units

Metres and seconds. +Z towards the muzzle, +Y up, +X to the shooter's left; the origin is on the bore axis at the
upper receiver's front face. Time zero for a shot is the sear releasing the hammer; the charge ignites 8.5 ms later.
Sockets include `socket_optic`, `socket_muzzle`, `socket_ads_eye` and `socket_hand_right`; the full list is in
`model/inventory.json` and `model/work/stats_lod0.json`.

## Rebuild

| What | Command (from `assets/hk416/`) | Needs |
|---|---|---|
| Sound tables | `python3 sound/sim.py params` | Python 3, numpy, scipy |
| JS sound parity | `python3 sound/verify_js.py` | node |
| Action | `python3 action/sim.py`, then `node action/test_action.js` | numpy, scipy, matplotlib; socket positions from a local build of the model |
| Geometry | `blender -b --python model/build.py` (add `-- --fast` for a quick untextured build) | Blender 4.x. Writes `model/hk416.glb`, ignored by git. Scoring against the references needs local copies in `refs-local/` |
| Ballistics | `python3 ballistics/sim.py`, then `node ballistics/test.js` | numpy, scipy, matplotlib |
| Flash and smoke | `python3 flash/sim.py`, then `node flash/test_flash.js` | numpy, scipy, matplotlib, Pillow; `action/action.json` and `action/sim.py`. The photo comparison needs local copies in `refs-local/flash/` |

## Muzzle flash and smoke (`flash/`)

```html
<script src="assets/hk416/flash/hk416-flash.js"></script>            <!-- window.HK416Flash -->
<script>
await HK416Flash.load('assets/hk416/flash/flash.json');
// HK416Action counts from the sear; the flash counts from ignition, 8.51 ms later
const t = tAction - HK416Flash.ignitionAfterSear;
const secondary = HK416Flash.rollSecondary();                         // once per shot: a fireball on about 12 % of shots
const L = HK416Flash.light(t - dt, t, { secondary });                 // light for this frame: L.intensity (cd), L.rgb, L.position (gun frame)
const f = HK416Flash.frame(t - dt, t, { secondary });                 // the same frame as additive cards: f.cards
const puffs = HK416Flash.smoke(t, wind);                              // smoke puffs: position, radius, opacity
</script>
```

Nothing shows until the bullet leaves the crown, 0.976 ms after ignition. An ordinary shot's flash peaks at 8.9 cd
for about 33 microseconds (0.030 cd averaged over a 1/60 s frame), so drive the light with `light(t0, t1)` or
`frame(t0, t1)`, which carry the right luminous energy for a frame of any length; `sample(t)` is for slow motion. Positions
are in the gun frame. Rebuild with `python3 flash/sim.py`, then `node flash/test_flash.js`. Physics, sources, checks
and limits: `flash/README.md`; publications and photographs: `flash/REFERENCES.md`.

## Limits

- The model is the exterior a player sees; hidden internals are not modelled (no hammer or firing pin nodes).
- The selector has no auto position; the rear sight is a folding ring rather than HK's diopter drum.
- Sound: the dry shot's body comes from the room overlays; it has not been checked by listening.
- Flash: the hider's effect on the jet is fitted to a photo of a different hider, and absolute brightness rests on one light-meter test.
- See `notes/MANUAL_COMPARE.md` and each simulation's README for the rest.

## Sources

`notes/MANUAL_NOTES.md` summarises the facts used from HK's maintenance manual, with page numbers.
`notes/REFERENCES.md` cites the reference images used to measure the shape. Neither the manual nor the images are in
this repository.
