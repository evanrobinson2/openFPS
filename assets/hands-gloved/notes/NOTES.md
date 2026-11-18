# Notes: decisions, inferences, results, limits

Version 1, 2026-11-17, modelled by Claude Fable 5.2. Credit: carpetshark. No change requests yet (rule 7: each one
will be recorded here as a new version).

## Where this stands against the reference-to-3D order

| Step | State |
|---|---|
| 1. References chosen | Done by the modeller under the brief's delegation (`REFERENCES.md`). **Not yet selected by the owner.** |
| 2. Source-indexed decomposition | Done (`DECOMPOSITION.md`). |
| 3. Studies and grammar | Done (`STUDIES.md`). |
| 4. Procedural reconstruction | Done: `model/`, `grips/`, `clips/`. |
| 5. Matched comparison | Done for R2 with numbers; R1 and R3 by eye only. **The comparison shows clear differences from the references (below). This is not a faithful translation yet.** |
| 6. Owner review | Not done. The list is at the end of this file. |

Structural results (proportions, limits, interpenetration, runtime parity) and visual results are separate things.
The structural checks pass; they say nothing about whether the hands look like the references.

## Results

| Check | Result | File |
|---|---|---|
| Proportions | Hand length, breadth, palm length and forearm equal ANSUR II by construction. Hand and wrist circumference fitted to 0.02 % and 0.37 %. Finger lengths against a second sample: ring -0.1 %, index -3.9 %, little **-6.1 % (fails the 6 % tolerance by 0.06)**. | `checks/proportions.json` |
| Joint limits | 12,582 values (23 hand angles and 4 arm angles, both hands, all 233 frames of 12 clips): 0 outside. Smallest margin 0.03 degrees (wrist deviation, `charge`). | `checks/limits.json` |
| Interpenetration | 466 hand-frames (298 distinct poses) measured against the rifle's triangles: deepest 0.60 mm (`charge`, ring finger against the lower receiver); tolerance 1.0 mm. | `checks/penetration.json` |
| Runtime parity | JS fingertips against the Python recipe: worst 2.1 micrometres over 2,330 points. Blender skinning against the recipe: 0.00008 mm. | `checks/test_runtime.js`, `model/inventory.json` |
| Matched comparison, R2 | Fingertips of the support hand are 27 to 65 mm from where R2 has them (mean 41 mm). The model's hand sits 28 mm further forward (centre 117 mm ahead of the receiver against 90 mm) and its fingertips stop about 20 mm lower on the side of the handguard. | `checks/comparison.json` |
| Matched comparison, R1, R3 | No numbers. A camera fit for R1 was tried and rejected (see the file). By eye: see below. | `renders/compare_*.jpg` |

Interpenetration tolerance: 1.0 mm, less than the glove's own 1.2 mm shell, so the skin never reaches the rifle.
Hand against hand, and hand against its own fingers, are **not** measured.

## What the comparison shows (by grid region of the crops)

- **R1, firing hand (B2-E6).** The photographed hand is compact and tight on the grip, the knuckles hard against the
  magazine well side of the grip, the back of the hand filling the view. The model's hand stands off: the palm is
  backed 10 mm off the grip's side, the fingers cross the grip slanting upward, and the hand sits lower and further
  back. The index finger reaches up to the trigger rather than lying level. The thumb-side wipe panel, cuff tab and
  knuckle flex panel are present but plainer and smaller than in R1.
- **R3, firing hand (B2-E4).** In the photo the index finger lies level along the receiver; in the model it rises at
  about 35 degrees, and the middle finger sits close under the trigger guard. Three wrapped fingers are present in
  both. The model's magazine grip (F2-H4) has the fingers round the magazine as in R3 but lower, on the magazine
  body rather than the magazine well, and the thumb lies on the left side where R3's points up at the front.
- **R2, support hand (E2-H4).** Same arrangement (palm under, four fingers up the right side, thumb over the top),
  but further forward and with shorter reach up the side, as measured above. R2's glove is thicker.
- Light and materials: plain flat materials under a soft sky light; no fabric texture, print or wear.

## Why the firing grip differs (the main limit)

The palm is one rigid shell. A real palm folds round a pistol grip (the thumb side comes round the back). With a
rigid palm the solver has to choose between the palm on the side of the grip and the thumb's base behind it, and it
backs the hand off until nothing is inside the rifle. The knock-on effects, all measured:

- the trigger finger's pad ends 11.6 mm from the middle of the trigger face (it touches the trigger lower down);
- the straight trigger finger ends 15.6 mm short of its point beside the magazine release, and its tip ends 12.4 mm
  from the button in `mag_release` and `mag_out`: **the finger does not reach the button**;
- the thumb tip ends 22 to 25 mm short of the selector lever: **`safety_to_fire` and `safety_to_safe` are a reach
  toward the lever, not a touch**;
- the wrist sits at 45 degrees of extension and 29 of ulnar deviation, 1 degree inside the limit, with the elbow
  swung 45 degrees out. A level hand with the elbow down needs about 60 degrees of ulnar deviation, twice the limit.

A palm that folds (a thenar segment hinged along the palm, with a source for its range) is the next change to make.

## Inferences (no measurement found), with their consequences

| Inference | Value | Consequence |
|---|---|---|
| Scale applied to the mixed-sex phalanx lengths | 1.04 | Sets every finger length. |
| Finger depths, joint centres across the palm, knuckle arc and arch, palm thickness, section shape | `model/handlib.py` `P` | Shape of the hand between the measured dimensions. |
| Thumb base position and rest direction; the rest pose is the middle of the thumb's range | `P['thumb_cmc']`, `P['thumb_dir']` | Where the thumb can reach. |
| Glove thickness 1.2 mm, cuff 2.6 mm, fingertip allowance 1.5 mm | `P` | Clearances. |
| Shoulder positions: stock collapsed, right shoulder joint 45 mm behind the buttpad, torso turned 15 degrees | `grips/solve.py` `SHOULDER` | Every wrist, forearm and elbow angle, and the forearm's direction in the pictures. |
| The elbow may swing -10 to 75 degrees outboard of straight down | `SWIVEL` | Same. |
| The firing hand's contact points on the grip, its 8 mm drop and 10 degree turn | `spec_fire_indexed` | The firing grip. Chosen by scanning for the placement where three fingers wrap and the wrist stays in range. |
| Thumb of the firing hand (never visible in a reference) | on the left of the grip | R1-F09. |
| All of `bolt_catch`, `charge`, `mag_out`, `mag_in`, selector and release clips | `STUDIES.md` study 6 | No reference shows them. |
| A frame that would cut through the rifle is moved outboard and down | `clips/make.py` `ESCAPE` | Up to 66 mm in `charge`; nowhere else. |

## Sources not re-read this session

The phalanx table (Buryanov and Kotiuk) and the finger breadths and lengths (Hsiao et al.) were carried over from the
paused build because the publishers refused the requests. The active-range end points of Bain 2015, Hume 1990's thumb
ranges, Cooney 1981's totals, the AAOS values and Kapandji's figure are recalled, with only the citations (and Bain's
abstract) confirmed. ANSUR II was recomputed from the public file. Each is marked in `model/handlib.py` `SRC`.

## Omissions

- Rifle clips with no hand clip: `stock_extend`, `stock_collapse`, `sights_up`, `sights_down`.
- R1's support hold on the front of the magazine well (R1-S01) is not a grip here.
- The printed pattern and the maker's lettering on R1's glove (on purpose), the edge binding R1-F07, fabric texture.
- Only the 50th-percentile hand is solved against the rifle; `handlib.set_size(5 or 95)` scales the hand but the
  grips are not re-solved for it.
- Skinning is linear blend: joints lose a little volume when bent hard.
- The recoil of `assets/hk416/action` is not applied to the hands.

## For the owner to review

1. The three references (`REFERENCES.md`): accept them, or choose others.
2. The side-by-side pictures in `refs-local/build/compare/` (local; rebuild with `checks/compare.py`) against
   `renders/compare_*.jpg`: is the firing grip acceptable as a first version, given the differences above?
3. The glove: R1's knit-backed pattern, plain, in coyote tan, with no lettering.
4. Whether the selector and magazine-release clips may ship while the digits fall short of the controls.
5. The stance assumptions (stock collapsed, elbow out 45 degrees).
6. Whether the hands should get a folding palm before anything else is built on them.
