# HK416 D14.5RS: how to use this asset

A simulation-grade HK416 with a 14.5 in barrel: the mechanism, recoil, ballistics and sound are simulated from
physics and HK's published figures. The shape is a measured, parametric part-by-part recipe. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) fires the rifle in a page: synthesised sound with a
choice of surroundings and earmuffs, the bolt carrier and recoil in slow motion, and a point-of-impact table.

## Status

| Part | State |
|---|---|
| Sound (`sound/`) | Ready. Synthesised in the browser from `params.json`; the JS port matches the Python to -160 dB. Not yet validated by listening. |
| Action and recoil (`action/`) | Ready. Calibrated to the manual: 850 m/s, 52,000 psi, about 800 rpm, 3.49 kg. |
| Ballistics (`ballistics/`) | Ready. M855, Mk 262 and M856 with G7 drag, HK's zeros, dispersion and terminal effects. |
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

Full APIs: `sound/README.md`, `action/README.md`, `ballistics/README.md`.

## Malfunctions

`malfunctions/` adds stoppages to the operating cycle: failure to fire, hangfire, failure to feed, stovepipe, double
feed, failure to extract, bolt over-ride and squib, with what the shooter sees and the safe clearing response. It is
education about recognising a stoppage and making the rifle safe. State: ready; rates are calibrated to the HK416's
counts in the Army's 2007 dust test and an assumed clean baseline, and the JavaScript equals the Python stoppage for
stoppage. The clearing clips are keyframe data, not yet baked into the model.

```html
<script src="assets/hk416/malfunctions/hk416-malfunctions.js"></script>   <!-- window.HK416Malfunctions -->
<script type="module">
const M = HK416Malfunctions;
await M.load('assets/hk416/malfunctions/malfunctions.json', 'assets/hk416/malfunctions/procedures.json');
const gun = M.create({ seed: 7, dust: 0.5, ammo: 'm855', magType: 'hk_steel', mode: 'range' });   // seeded: the same run every time
const r = gun.fire();                    // { outcome: 'fired' | 'stovepipe' | 'double_feed' | ..., variant, stoppage, travelMm }
if (r.stoppage) {
  gun.pose();                            // carrierMm, boltDeg and the brass to show, in the gun frame
  gun.carrierAt(t);                      // carrier travel t seconds after the trigger break, stopping where the stoppage holds it
  gun.observe(); gun.diagnose();         // what can be seen, and the procedure for it ('immediate_action', 'double_feed_clear', ...)
  gun.step();                            // one clearing step at a time (tap, rack, reassess ...), or gun.clear() for all of it
}
</script>
```

Drive the normal cycle with `HK416Action.sample()` as before; when `r.stoppage` is true use `gun.carrierAt(t)` for the
carrier instead (it is the same curve until the stop) and do not spawn ejected brass unless the case left the port.
Rebuild with `python3 malfunctions/sim.py` (about 3 minutes; needs `action/action.json` and `model/inventory.json`),
then `node malfunctions/test_malfunctions.js`. Rates, sources, the state machine, the clip data and the limits (rates
are calibrated, not predicted; parts breakage and cook-off are not modelled) are in `malfunctions/README.md`. The
sample page has a malfunction section at the bottom.

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

## Limits

- The model is the exterior a player sees; hidden internals are not modelled (no hammer or firing pin nodes).
- The selector has no auto position; the rear sight is a folding ring rather than HK's diopter drum.
- Sound: the dry shot's body comes from the room overlays; it has not been checked by listening.
- See `notes/MANUAL_COMPARE.md` and each simulation's README for the rest.

## Sources

`notes/MANUAL_NOTES.md` summarises the facts used from HK's maintenance manual, with page numbers.
`notes/REFERENCES.md` cites the reference images used to measure the shape. Neither the manual nor the images are in
this repository.
