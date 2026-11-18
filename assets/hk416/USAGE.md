# HK416 (14.5 in): how to use this asset

A simulation-grade HK416 with a 14.5 in barrel: the mechanism, recoil, ballistics and sound are simulated from
physics and HK's published figures. The shape is a parametric part-by-part recipe measured on Heckler & Koch's own dimensioned drawing and maintenance manual. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) fires the rifle in a page: synthesised sound with a
choice of surroundings and earmuffs, the bolt carrier and recoil in slow motion, and a point-of-impact table.

## Status

| Part | State |
|---|---|
| Sound (`sound/`) | Ready. Synthesised in the browser from `params.json`; the JS port matches the Python to -160 dB. Not yet validated by listening. |
| Action and recoil (`action/`) | Ready. Calibrated to the manual: 850 m/s, 52,000 psi, about 800 rpm, 3.49 kg. |
| Ballistics (`ballistics/`) | Ready. M855, Mk 262 and M856 with G7 drag, HK's zeros, dispersion and terminal effects. |
| Geometry (`model/`) | Ready as a recipe, version 2 (2026-11-18): every outline and position measured on HK's dimensioned drawing. `build.py` is Blender Python: 272 named parts, 13 clips, 7 sockets, two LODs (89,492 and 26,606 triangles). It writes `hk416.glb`, a build output that is never committed. Renders, including the fit to HK's drawing (`fit_left.jpg`, `fit_top.jpg`), are in `renders/`. |

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

Full APIs: `sound/README.md`, `action/README.md`, `ballistics/README.md`.

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
| Geometry | `blender -b --python model/build.py` (add `-- --fast` for a quick untextured build, `-- --barrel 16.5` for another HK barrel), or `python3 model/build.py` with the `bpy` module | Blender 4.x or 5.x. Writes `model/hk416.glb`, ignored by git. The full build bakes 2048 px textures: minutes on a GPU, about an hour on a 4-core CPU |
| Fit check | `python3 model/tools/fit_drawing.py model/refs-local/HK416_Technical_Data.pdf` after a `--fast --barrel 16.5` build | Your own copy of HK's technical data PDF (see `notes/REFERENCES.md`); pymupdf, opencv |
| Ballistics | `python3 ballistics/sim.py`, then `node ballistics/test.js` | numpy, scipy, matplotlib |

## Limits

- The model is the exterior a player sees; hidden internals are not modelled (no hammer or firing pin nodes).
- The ejection port and dust cover size, the grip width and the full-auto pictogram position are inferred (marked in `build.py`).
- The HK416 A5 lower receiver and stock are not modelled: HK publishes no drawing of them.
- Sound: the dry shot's body comes from the room overlays; it has not been checked by listening.
- See `notes/MANUAL_COMPARE.md` and each simulation's README for the rest.

## Sources

`notes/MANUAL_NOTES.md` summarises the facts used from HK's maintenance manual, with page numbers.
`notes/REFERENCES.md` cites HK's technical data, maintenance and operator manuals used to measure the shape (version 2,
2026-11-18), with the drawing's calibration so every number can be checked. `notes/NOTES.md` records the change from
version 1, which was traced from a photo. None of the documents is in this repository.
