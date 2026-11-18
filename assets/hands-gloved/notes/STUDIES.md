# Object studies and derived grammar

Step 3 of the reference-to-3D order. Each study is bound to the source regions in `DECOMPOSITION.md` and says what
the recipe builds from it. Every parameter is marked **observed** (read off a reference), **measured** (from a named
publication, see `model/handlib.py` `SRC`), **inferred** (a labelled guess) or **omitted**.

## Study 1: the hand under the glove

The references show gloves, not hands, so the hand itself comes from published measurements, and the references only
check that the result has the right size against the rifle (R2-S01: 24.7 mm per gloved finger; the model's gloved
fingers are 21.7 to 24.5 mm at the middle joint).

| Part | Built from | Status |
|---|---|---|
| Hand length 193.3, breadth 88.3, circumference 212.3, palm length 116.5, wrist circumference 175.9 mm | ANSUR II men, mean (the 50th percentile is within 0.3 mm) | measured |
| Forearm 267.9, upper arm 335.2 mm | ANSUR II men, mean | measured |
| Phalanx and metacarpal lengths of the five rays | Buryanov & Kotiuk 2010 (mixed-sex X-ray sample) times 1.04 | measured, scale inferred |
| Finger breadths at the middle joint (thumb: last joint) | Hsiao et al. 2015, men | measured |
| Finger depths, joint centres across the palm, the metacarpal arc and arch, thumb base position and direction, palm thickness 29.5 mm | none found | inferred |
| Joint ranges | Bain 2015, Hume 1990, Cooney 1981, AAOS 1965, Kapandji | measured (several recalled, see `NOTES.md`) |

Construction: a skeleton of 21 bones per hand (forearm, hand, four metacarpals, twelve finger phalanges, three thumb
segments), each finger a chain MCP (flexion and spread), PIP, DIP; the thumb a chain CMC (three axes), MCP, IP.

The folding palm (version 2, CR-1 item 1):

| Part | Built from | Status |
|---|---|---|
| Ring and little metacarpals flex at their bases: -3 to 17 and -4 to 23 degrees | El-Shennawy et al. 2001: arcs of 20 and 27 degrees (abstract read) | measured; where the flat hand sits in the arc (15 % in) is inferred |
| Index and middle metacarpals rigid | the same paper: 11 and 7 degrees | omitted (small) |
| Thumb base: 53 / 42 / 17 degrees of flexion, abduction and rotation, half each way from the rest pose | Cooney et al. 1981 (abstract read) | measured; the rest pose as the middle of the range is inferred |
| The thenar part of the palm's skin follows the thumb metacarpal, hinged along the thenar crease | Kawanishi et al. 2018: in opposition the metacarpal abducts, rotates and flexes on the trapezium (directions only) | observed direction; the crease line and the blend width are inferred |
| The base of the thumb itself (the trapezium) does not move against the wrist | anatomy | this is why the thumb cannot come round behind the grip (see `NOTES.md`) |

## Study 2: the glove (from R1)

| Part ID | Source region | What the recipe builds | Status |
|---|---|---|---|
| G1 back knit | R1-F01, R1-S01 | Back of the hand and fingers in `glove_back_knit`, coyote tan | observed |
| G2 palm | not seen in R1; R2-S04 shows a separate palm material | Palm side in `glove_palm_synthetic_leather`, a shade darker | inferred (that it differs: observed in R2) |
| G3 side seams | R3-F04 (dark slits between fingers) | A `glove_seam` strip along each side of each finger and round the hand's edge | observed |
| G4 flex panels | R1-F05 | Ribbed bands over the big knuckles and over the two joints of each finger (thumb: one), alternating `glove_flex_rib` and `glove_seam`, one rib per ring of the surface (about 2.2 mm) | observed for the index knuckle; extended to the other joints by inference |
| G5 fingertip caps | R1-S02, R2-S02, R3-F03 | Darker `glove_fingertip` over the end of every digit | observed on some digits, extended to all |
| G6 thumb wipe panel | R1-F02 | `glove_terry` on the back of the thumb's first two segments | observed |
| G7 cuff | R1-F04 | Dark `glove_cuff` band 42 mm past the wrist | observed (length inferred) |
| G8 closure tab | R1-F03 | `cuff_strap` 38 x 16 x 2.6 mm across the back of the wrist, a `cuff_pull_tab` at its outer end, and a plain `cuff_placeholder_panel` where R1 has lettering | observed; lettering omitted on purpose |
| G9 heel patch | R2-S04 | `palm_heel_patch`, a low raised slab on the heel of the palm | observed in R2, carried to this glove by inference |
| G10 sleeve | R1-F10, R2-S05 | Plain pale `sleeve_fabric` tube to 210 mm behind the wrist | observed; the camouflage print is omitted |
| omitted | R1-F01 | The printed line pattern on the knit | omitted (a maker's pattern) |
| omitted | R1-F07 | The dark edge binding between thumb and index | omitted (small; listed for review) |
| omitted | R2, R3 gloves | Leather knuckle band (R3-F02), long gauntlets (R2-S05) | not this glove |

Glove thickness over the skin is 1.2 mm (inferred), 2.6 mm at the cuff (inferred), with 1.5 mm of extra length at the
fingertips (inferred).

## Study 3: the firing grip (R1, R3, R2)

Rules, each with its evidence:

1. The grip sits in the fork between thumb and index, pushed up under the rear of the receiver; the back of the hand
   faces right (R1-F01, R3-F01). **observed**
2. Three fingers wrap the front of the grip, close together, under the trigger guard (R3-F04). **observed**
3. The index finger has two positions: straight along the receiver above the trigger guard, tip toward the magazine
   release (R3-F03, R3-W01), and on the trigger (R1-F06). **observed**
4. The forearm arrives from below and behind, steeply when standing (R2-F01, about 60 degrees from the bore in the
   picture), and the wrist is bent toward the little finger (R1-F10). **observed**; the angle itself is solved from
   the shoulder position, which is **inferred**.
5. The thumb goes round the left side of the grip and rests below the selector. **inferred** (never visible).

What the solver does with them in version 2 (`grips/solve.py`, `fit_palm`): the hand's pose, the elbow swivel and
the ring and little metacarpal joints are searched together so that the middle finger's knuckle pad sits hard under
the trigger guard on the right side of the grip (rule 2), nothing of the palm is inside the rifle, the hand rises
about 12 degrees toward the muzzle and the wrist stays inside its range (rule 4); then the middle, ring and little
fingers close round the front of the grip, choosing the more closed of two poses that touch (rule 2); the index pad
is placed on the receiver below the magazine release, or on the middle of the trigger blade's face (rule 3); the
thumb pad is sent to the left side of the grip (rule 5). `NOTES.md` says how far the result is from the references,
and why the web of the hand ends beside the receiver's rear and not under it.

6. Stance (version 2, **inferred**): the arms are solved for the stock extended 75 mm and the firing elbow raised
   outboard, because with the stock collapsed a level hand seated on the grip needs more wrist extension than a wrist
   has (numbers in `NOTES.md`).
7. Where the hand sits along the grip: the middle finger's knuckle pad 15 mm behind the grip's front edge, the
   furthest forward at which this hand's middle finger still closes under the trigger guard. R1 has the index knuckle
   about 24 mm ahead of that, R3 about 5 mm ahead. **observed, not matched**: see `NOTES.md`.
8. To press the magazine release the hand slides 9 mm forward on the grip (grip `fire_reach`) and back. **inferred**:
   no reference shows the press, and this hand cannot reach the button from the firing grip without moving.

## Study 4: the support grip (R2)

1. The handguard rests on the base of the fingers and the far part of the palm, not on the middle of the palm
   (R2-S04). **observed**
2. Four fingers go up the right side, tips at the upper edge of the side rail, the index a little ahead of the rest
   (R2-S01, R2-S02). **observed**
3. The thumb comes over the top from the left; its tip shows above the top rail (R2-S03). **observed** (tip only)
4. The hand is centred about 100 mm ahead of the receiver (R2-S06); the rifle's `socket_hand_left` is 110 mm ahead.
   **observed**

Solver (version 2): the hand's pose is searched; each candidate is pushed up under the handguard until it touches;
four fingers close on the handguard; the search pulls the four fingertips toward the places R2 has them (read off the
photograph and scaled by the handguard's 68.0 mm height, `R2_TIPS`); the thumb tip is sent to where R2 shows it
above the top rail. Version 1 held the far-palm pad 100 mm ahead of the receiver instead.

## Study 5: the magazine grip (R1-S01, R3-S01, R3-S02)

1. The support hand comes from the left and below; four fingers lie round the magazine from the front and right,
   horizontal (R3-S01, R1-S01). **observed**
2. The thumb is on the left or front, pointing up (R3-S02). **observed**

Used for `mag_out` and `mag_in`: the hand holds the magazine body below the magazine well and moves with it.

## Study 6: controls with no reference (all inferred)

Built from the rifle's own controls and the usual right-handed drill:

| Clip | Hand and digit | Rule |
|---|---|---|
| `trigger_pull` | Right index | Pad stays on the trigger face as the trigger turns 6 degrees. |
| `mag_release` | Right index | From the straight position the pad presses the button on the right side 1.5 mm in. |
| `safety_to_fire`, `safety_to_safe` | Right thumb | The pad rides the left selector lever through its 90 degrees. |
| `bolt_catch` | Left thumb | The support hand comes back to the magazine well and the thumb presses the paddle on the left. |
| `charge` | Left index and middle | The hand goes to the charging handle, hooks its left wing from the front, and rides it 75 mm back and forward. |
| `mag_out`, `mag_in` | Left hand, right index on the release | Study 5 grip on the magazine body; the hand follows the magazine. |
