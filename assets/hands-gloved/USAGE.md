# Gloved hands for the HK416: how to use this asset

First-person hands in generic tactical gloves, built as a recipe: bones with the proportions of the ANSUR II male
mean, joints with ranges from the biomechanics literature, a glove surface over them, grips solved against the
HK416 of `assets/hk416/`, and hand clips that run with that rifle's clips. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) plays every clip as a posed skeleton in the rifle's
frame, with each joint angle drawn against its limit and the measured interpenetration per frame.

## Status

Version 2 (change request CR-1), awaiting owner review. Read [`notes/NOTES.md`](notes/NOTES.md) before using it: it
says item by item what CR-1 asked for and what was reached.

| Part | State |
|---|---|
| Hand recipe (`model/handlib.py`, `model/glove.py`) | Ready. 21 bones per hand, 23 joint angles, 9 glove shells and 4 sewn-on parts per hand. Version 2: the ring and little metacarpals flex over sourced ranges and the thenar part of the palm follows the thumb. |
| Grips (`grips/`) | Seven, solved against the rifle with nothing inside it: `fire_indexed`, `fire`, `fire_reach`, `support`, `mag_grip`, `catch_ready`, `charge_grip`. The firing hand now lies on the grip with its fingers closed round the front; its web is beside the receiver's rear, not under it. |
| Clips (`clips/`, `hands-gloved.json`) | Twelve at 24 fps: `idle`, `finger_to_trigger`, `finger_off_trigger`, `trigger_pull`, `mag_release`, `safety_to_fire`, `safety_to_safe`, `bolt_catch`, `mag_out`, `mag_in`, `charge`, `dust_cover_open`. The trigger, the magazine release and the bolt catch are touched (within 1 mm). **The thumb does not reach the selector: it stops 10.8 mm away.** None for the stock and sight clips. |
| Runtime (`hands-gloved.js`) | Ready. Matches the Python recipe to 2.3 micrometres. |
| Geometry build (`model/build.py`) | Ready as a recipe: 26 named parts, 29,936 triangles, two armatures, 12 NLA clips. Writes `hands-gloved.glb`, a build output that is never committed. |
| Checks (`checks/`) | Joint limits: 0 of 12,798 values outside. Interpenetration: 0.57 mm at worst, tolerance 1.0 mm. Contact: see above. Proportions: 10 of 10 independent rows inside 6 %. Comparison with the references: support hand's fingertips 18 mm from R2's on average, firing hand's knuckles 21 mm from R1's. |

## Run the sample

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/hands-gloved/sample/
```

## Use it in your own page

```html
<script src="assets/hands-gloved/hands-gloved.js"></script>     <!-- window.HandsGloved -->
<script>
await HandsGloved.load('assets/hands-gloved/hands-gloved.json');
const s = HandsGloved.sample('charge', t);        // t: seconds from the start of the hand clip
// s.R, s.L: { hand, forearm: [x,y,z,qx,qy,qz,qw], angles: {index_mcp_flex: deg, ...}, bones: {name: 4x4 row-major} }
// s.rifleClip, s.rifleTime: start the rifle's clip when rifleTime turns from null to 0
const idle = HandsGloved.grip('support');         // also fire, fire_indexed, fire_reach, mag_grip, catch_ready, charge_grip
HandsGloved.checkLimits(s.R.angles);              // [] when every joint is inside its range
</script>
```

Skin `hands-gloved.glb` with the bone matrices, or play its NLA clips, which carry the same names. A hand clip can
start before its rifle clip (`pre_roll` frames) and end after it. `trigger_pull` starts from the grip `fire`; go
there with `finger_to_trigger`. `mag_in` starts where `mag_out` ends, holding the magazine.

## Frame and units

The rifle's frame: metres and seconds, +X to the shooter's left, +Y up, +Z to the muzzle, origin on the bore axis at
the upper receiver's front face. Angles in degrees, flexion positive. The grips are given in that frame and also
relative to the rifle's `socket_hand_right` and `socket_hand_left` (`grips/grips.json`). The hand's own sockets are
`socket_palm`, `socket_wrist`, `socket_index_tip` and `socket_thumb_tip`, each with `_left` or `_right`.

## Rebuild

| What | Command (from `assets/hands-gloved/`) | Needs |
|---|---|---|
| The rifle, locally | copy `../hk416/model/build.py` into `refs-local/build/hk416/`, run `blender -b --python build.py -- --fast` there, then `blender -b refs-local/build/hk416/work/hk416_lod0.blend --python tools/extract_rifle.py` | Blender |
| Grips | `python3 grips/solve.py` (about 6 minutes; it rebuilds its distance-field caches when they are missing) | numpy, scipy |
| Clips and runtime data | `python3 clips/make.py` (about 8 minutes) | the grips |
| Model | `blender -b --python model/build.py` | Blender; writes into `refs-local/build/` |
| Checks | see `checks/README.md`: proportions, limits, contact, interpenetration, runtime parity, comparison | |

Rebuild in that order: a change to `model/handlib.py` means every grip, every clip and every check again.

Everything built goes into `refs-local/build/`, which git ignores.

## Limits

- The palm still does not wrap the grip: it lies flat on the grip's right side, the web is not under the receiver's
  rear, and the thumb cannot reach the selector. The notes say why and what would change it.
- The arms are solved for the stock extended 75 mm and the firing elbow out 60 degrees; the shoulder positions are
  assumed, and with them every wrist and elbow angle.
- To press the magazine release the firing hand slides 9 mm forward on the grip (`fire_reach`) and back.
- Hand against hand is not checked for interpenetration.
- Several published numbers are still recalled or carried over, not re-read (`notes/NOTES.md`).
- No fabric texture, print or wear; plain materials.

## Sources

`notes/REFERENCES.md` cites the three photographs (approved by the owner; the record is there). `model/handlib.py` (`SRC`) names the anthropometric and
biomechanics sources for every number. No photograph is in this repository.
