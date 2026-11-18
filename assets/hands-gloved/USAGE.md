# Gloved hands for the HK416: how to use this asset

First-person hands in generic tactical gloves, built as a recipe: bones with the proportions of the ANSUR II male
mean, joints with ranges from the biomechanics literature, a glove surface over them, grips solved against the
HK416 of `assets/hk416/`, and hand clips that run with that rifle's clips. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) plays every clip as a posed skeleton in the rifle's
frame, with each joint angle drawn against its limit and the measured interpenetration per frame.

## Status

Version 3 (change request CR-2). **Not reviewed by the owner**, and neither was version 2. Read
[`notes/NOTES.md`](notes/NOTES.md) before using it: it says goal by goal what CR-2 asked for and what was reached.

| Part | State |
|---|---|
| Hand recipe (`model/handlib.py`, `model/glove.py`) | Ready. 21 bones per hand, 25 joint angles and 4 pad compressions, 9 glove shells and 20 sewn-on parts per hand. Version 3: all four metacarpals flex over sourced ranges, the ring and little ones turn as they flex, and four pads of the palm press in under contact, each inside a limit. |
| Grips (`grips/`) | Seven, solved against the rifle with nothing inside it: `fire_indexed`, `fire`, `fire_reach`, `support`, `mag_grip`, `catch_ready`, `charge_grip`. The firing hand lies level on the grip with three fingers round the front; **its web is still 19 mm to the right of the receiver's rear, not under it.** |
| Clips (`clips/`, `hands-gloved.json`) | Twelve at 24 fps: `idle`, `finger_to_trigger`, `finger_off_trigger`, `trigger_pull`, `mag_release`, `safety_to_fire`, `safety_to_safe`, `bolt_catch`, `mag_out`, `mag_in`, `charge`, `dust_cover_open`. The trigger, the magazine release and the bolt catch are touched (within 1 mm). **The thumb does not reach the selector: it stops 12 mm away. In `charge` the two hands pass through each other by up to 10 mm.** None for the stock and sight clips. |
| Runtime (`hands-gloved.js`) | Ready. Matches the Python recipe to 2.7 micrometres. It poses bones; the pads' compression is passed through as numbers. |
| Geometry build (`model/build.py`) | Ready as a recipe: 58 named parts, 30,880 triangles, two armatures, 12 NLA clips, and one shape key per pad on the meshes it moves, animated in each clip. Writes `hands-gloved.glb`, a build output that is never committed. |
| Checks (`checks/`) | Joint limits: 0 of 15,642 values outside. Interpenetration with the rifle: 0.60 mm at worst, tolerance 1.0 mm, with pad compression reported apart and inside its limits (2.43 of 2.90 mm at most). Hand against hand: fails in `charge`. Contact and selector reach: see above. Proportions: 10 of 10 independent rows inside 6 %. Comparison with the references: firing hand's knuckles 16 mm from R1's, support hand's fingertips 21 mm from R2's. |

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
// s.R, s.L: { hand, forearm: [x,y,z,qx,qy,qz,qw], angles: {index_mcp_flex: deg, ..., pad_distal: mm}, bones: {name: 4x4 row-major} }
// s.rifleClip, s.rifleTime: start the rifle's clip when rifleTime turns from null to 0
const idle = HandsGloved.grip('support');         // also fire, fire_indexed, fire_reach, mag_grip, catch_ready, charge_grip
HandsGloved.checkLimits(s.R.angles);              // [] when every joint is inside its range
</script>
```

Skin `hands-gloved.glb` with the bone matrices, or play its NLA clips, which carry the same names. The last four
entries of `angles` (`pad_thenar`, `pad_hypothenar`, `pad_midpalm`, `pad_distal`) are not angles: each is how far a pad
of the palm is pressed in at its middle, in millimetres. In the glb each pad is a morph target (shape key) of the same
name on the meshes it moves, at weight compression / limit (`pads` in `hands-gloved.json` gives the limits); the glb's
clips animate those weights. If you pose the bones yourself, set the weights from `angles` too, or the palm sits up to
2.4 mm inside the grip. A hand clip can
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
| Grips | `python3 grips/solve.py` (about 8 minutes; it rebuilds its distance-field caches when they are missing) | numpy, scipy |
| Clips and runtime data | `python3 clips/make.py` (about 20 minutes; `--reuse` redoes only the arm angles and the files from the frames cached by the last full run) | the grips |
| Model | `blender -b --python model/build.py` | Blender; writes into `refs-local/build/` |
| Checks | see `checks/README.md`: proportions, limits, contact, selector reach, interpenetration with pad compression and hand against hand, runtime parity, comparison | |

Rebuild in that order: a change to `model/handlib.py` means every grip, every clip and every check again.

Everything built goes into `refs-local/build/`, which git ignores.

## Limits

- The web of the firing hand is 19 mm to the right of its seat under the receiver's rear, and the thumb cannot reach
  the selector (10.5 mm at best). The notes give the numbers and the reason: the stance and the wrist's range, and a
  web that is modelled rigid.
- In `charge` the hands pass through each other (up to 10.3 mm, frames 12 to 19 and 35).
- The arms are solved for the stock extended 75 mm and the firing elbow 55 degrees out; the shoulder positions are
  assumed, and with them every wrist and elbow angle and the forearms' directions.
- To press the magazine release the firing hand shifts 6.5 mm on the grip (`fire_reach`) and back.
- The pads' limits are half the soft-tissue thickness, a figure from a 3 mm indenter; the tissue thicknesses are
  inferred except over the trapezium. Compression does not bulge the hand elsewhere. Fingertips do not compress.
- A hand is not checked against its own fingers.
- Several published numbers are still recalled or carried over, not re-read (`notes/NOTES.md`).
- No fabric texture, stitching, print or wear; plain materials.

## Sources

`notes/REFERENCES.md` cites the three photographs (approved by the owner as references; the record is there). `model/handlib.py` (`SRC`) names the anthropometric and
biomechanics sources for every number. No photograph is in this repository.
