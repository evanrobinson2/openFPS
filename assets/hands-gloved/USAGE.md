# Gloved hands for the HK416: how to use this asset

First-person hands in generic tactical gloves, built as a recipe: bones with the proportions of the ANSUR II male
mean, joints with ranges from the biomechanics literature, a glove surface over them, grips solved against the
HK416 of `assets/hk416/`, and hand clips that run with that rifle's clips. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) plays every clip as a posed skeleton in the rifle's
frame, with each joint angle drawn against its limit and the measured interpenetration per frame.

## Status

Version 4 (change request CR-3, an interim direction given while the owner slept). **Not reviewed by the owner**, and
neither were versions 2 and 3. Read [`notes/NOTES.md`](notes/NOTES.md) before using it: it says goal by goal what each
change request asked for and what was reached. Version 4 changed two things: the safety clips now move the firing hand
to the selector and back, and `charge` no longer passes one hand through the other.

| Part | State |
|---|---|
| Hand recipe (`model/handlib.py`, `model/glove.py`) | Ready. 21 bones per hand, 25 joint angles and 4 pad compressions, 9 glove shells and 20 sewn-on parts per hand. Version 3: all four metacarpals flex over sourced ranges, the ring and little ones turn as they flex, and four pads of the palm press in under contact, each inside a limit. |
| Grips (`grips/`) | Eight, solved against the rifle with nothing inside it: `fire_indexed`, `fire`, `fire_reach`, `fire_select`, `support`, `mag_grip`, `catch_ready`, `charge_grip`. `fire_select` is not a firing grip: it is where the hand goes to work the selector (wrist 28.9 mm and hand 50.7 degrees from `fire_indexed`, elbow under the rifle). The firing hand lies level on the grip with three fingers round the front; **its web is still 19 mm to the right of the receiver's rear, not under it.** |
| Clips (`clips/`, `hands-gloved.json`) | Twelve at 24 fps: `idle`, `finger_to_trigger`, `finger_off_trigger`, `trigger_pull`, `mag_release`, `safety_to_fire`, `safety_to_safe`, `bolt_catch`, `mag_out`, `mag_in`, `charge`, `dust_cover_open`. The trigger, the magazine release, the bolt catch, the charging handle and the selector are touched (within 1 mm). **The safety clips are 30 frames: the firing hand takes 12 frames to turn on the grip to the selector, with the elbow swinging in under the rifle, the thumb lies on the lever through the rifle's 6 frames, and the hand takes 12 frames back.** None for the stock and sight clips. |
| Runtime (`hands-gloved.js`) | Ready. Matches the Python recipe to 2.7 micrometres. It poses bones; the pads' compression is passed through as numbers. |
| Geometry build (`model/build.py`) | Ready as a recipe: 58 named parts, 30,880 triangles, two armatures, 12 NLA clips, and one shape key per pad on the meshes it moves, animated in each clip. Writes `hands-gloved.glb`, a build output that is never committed. |
| Checks (`checks/`) | Joint limits: 0 of 15,642 values outside. Interpenetration with the rifle: 0.60 mm at worst, tolerance 1.0 mm, with pad compression reported apart and inside its limits (2.43 of 2.90 mm at most). Hand against hand: 0.0 mm. Selector move: both safety clips meet CR-3's conditions (`checks/selector_move.json`); the scan behind it is `checks/selector_scan.json`. Joint limits in version 4: 0 of 17,754. Proportions: 10 of 10 independent rows inside 6 %. Comparison with the references: firing hand's knuckles 16 mm from R1's, support hand's fingertips 21 mm from R2's. |

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
const idle = HandsGloved.grip('support');         // also fire, fire_indexed, fire_reach, fire_select, mag_grip, catch_ready, charge_grip
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
there with `finger_to_trigger`. The safety clips start 12 frames before the rifle's clip and move the whole firing arm:
start them half a second before the lever should turn, and do not blend them with `trigger_pull`. `mag_in` starts where `mag_out` ends, holding the magazine.

## Frame and units

The rifle's frame: metres and seconds, +X to the shooter's left, +Y up, +Z to the muzzle, origin on the bore axis at
the upper receiver's front face. Angles in degrees, flexion positive. The grips are given in that frame and also
relative to the rifle's `socket_hand_right` and `socket_hand_left` (`grips/grips.json`). The hand's own sockets are
`socket_palm`, `socket_wrist`, `socket_index_tip` and `socket_thumb_tip`, each with `_left` or `_right`.

## Rebuild

| What | Command (from `assets/hands-gloved/`) | Needs |
|---|---|---|
| The rifle, locally | copy `../hk416/model/build.py` into `refs-local/build/hk416/`, run `blender -b --python build.py -- --fast` there, then `blender -b refs-local/build/hk416/work/hk416_lod0.blend --python tools/extract_rifle.py` | Blender |
| Grips | `python3 grips/solve.py` (version 3 took about 8 minutes; `fire_select` adds about 8, measured alone; it rebuilds its distance-field caches when they are missing; `python3 grips/solve.py charge_grip` solves one) | numpy, scipy |
| Clips and runtime data | `python3 clips/make.py` (version 3 took about 20 minutes; the two safety clips add about 35, measured alone with other jobs running; a full run of version 4 was not timed; `--only=charge,safety_to_fire` rebuilds the named clips and takes the rest from the last run's cache; `--reuse` redoes only the arm angles and the files) | the grips |
| Model | `blender -b --python model/build.py` | Blender; writes into `refs-local/build/` |
| Checks | see `checks/README.md`: proportions, limits, contact, interpenetration with pad compression and hand against hand, selector reach, selector scan, selector move (after limits and interpenetration), runtime parity, comparison | |
| Frame strips | `python3 tools/strip.py safety_to_fire sel_left,sel_right,rear renders/selector_move_safety_to_fire.jpg 1 4 7 10 13 14 15 16 17 18 22 26 30 --size=300x300` (and the same for `safety_to_safe`); `python3 tools/strip.py charge charge_left,charge_top renders/charge_strip.jpg 1 4 7 10 13 14 18 23 27 30 35 40 45 49 --cols=7 --size=330x330` | Blender, the frames |

Rebuild in that order: a change to `model/handlib.py` means every grip, every clip and every check again.

Everything built goes into `refs-local/build/`, which git ignores.

## Limits

- The web of the firing hand is 19 mm to the right of its seat under the receiver's rear, and from the firing grip the
  thumb cannot reach the selector (10.5 mm at best). The notes give the numbers and the reason: the stance and the
  wrist's range, and a web that is modelled rigid.
- So the safety clips move the whole hand: wrist 28.9 mm, hand 50.7 degrees, elbow 292 mm, half a second each way.
  That is this model's answer inside its limits, not a taught drill, and it looks large (`renders/selector_move_*.jpg`).
  The check shows the thumb's glove on the lever's outer face within 1 mm; it does not show a push.
- All of the selector move and of `charge` is inferred; no reference shows either.
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
