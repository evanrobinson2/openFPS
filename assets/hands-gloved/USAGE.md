# Gloved hands for the HK416: how to use this asset

First-person hands in generic tactical gloves, built as a recipe: bones with the proportions of the ANSUR II male
mean, joints with ranges from the biomechanics literature, a glove surface over them, grips solved against the
HK416 of `assets/hk416/`, and hand clips that run with that rifle's clips. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) plays every clip as a posed skeleton in the rifle's
frame, with each joint angle drawn against its limit and the measured interpenetration per frame.

## Status

Version 1, awaiting owner review. Read [`notes/NOTES.md`](notes/NOTES.md) before using it.

| Part | State |
|---|---|
| Hand recipe (`model/handlib.py`, `model/glove.py`) | Ready. 21 bones per hand, 23 joint angles, 9 glove shells and 4 sewn-on parts per hand. |
| Grips (`grips/`) | Six, solved against the rifle with nothing inside it. The firing grip stands off the pistol grip more than a real hand does; trigger reached, magazine release and selector not reached (measured in the notes). |
| Clips (`clips/`, `hands-gloved.json`) | Twelve at 24 fps: `idle`, `finger_to_trigger`, `finger_off_trigger`, `trigger_pull`, `mag_release`, `safety_to_fire`, `safety_to_safe`, `bolt_catch`, `mag_out`, `mag_in`, `charge`, `dust_cover_open`. None for the stock and sight clips. |
| Runtime (`hands-gloved.js`) | Ready. Matches the Python recipe to 2 micrometres. |
| Geometry build (`model/build.py`) | Ready as a recipe: 26 named parts, 29,936 triangles, two armatures, 12 NLA clips. Writes `hands-gloved.glb`, a build output that is never committed. |
| Checks (`checks/`) | Joint limits: 0 of 12,582 values outside. Interpenetration: 0.60 mm at worst, tolerance 1.0 mm. Proportions: one independent row fails (little finger 6.1 % short). Comparison with the references: clear differences. |

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
const idle = HandsGloved.grip('support');         // also fire, fire_indexed, mag_grip, catch_ready, charge_grip
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
| Grips | `python3 grips/solve.py` (about 6 minutes) | numpy, scipy |
| Clips and runtime data | `python3 clips/make.py` | the grips |
| Model | `blender -b --python model/build.py` | Blender; writes into `refs-local/build/` |
| Checks | see `checks/README.md` | |

Everything built goes into `refs-local/build/`, which git ignores.

## Limits

- The palm is rigid, so the firing hand cannot fold round the grip; see the notes for what that costs.
- The shoulder positions are assumed, and with them every wrist and elbow angle.
- Hand against hand is not checked for interpenetration.
- Several published numbers were recalled or carried over, not re-read (`notes/NOTES.md`).
- No fabric texture, print or wear; plain materials.

## Sources

`notes/REFERENCES.md` cites the three photographs. `model/handlib.py` (`SRC`) names the anthropometric and
biomechanics sources for every number. No photograph is in this repository.
