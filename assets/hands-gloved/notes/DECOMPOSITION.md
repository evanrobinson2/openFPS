# Source-indexed decomposition of the references

Step 2 of the reference-to-3D order. Each reference (see `REFERENCES.md`) is cropped to the hands, an 8-column grid
(A to H, left to right) with numbered rows is drawn on the crop, and every meaningful visible feature gets a stable
ID, its grid cells, what it is, and how sure the reading is. `tools/crops.py` cuts the crops and draws the grids
(into `refs-local/crops/`, local only). Crop regions are in the pixel frame of each photo scaled to 1920 px wide.

Rifle-side features are listed only where a hand touches them or where they give scale. IDs are used by
`STUDIES.md`, by the grip specifications in `grips/solve.py` and by the comparison in `checks/compare.py`.

Certainty: **seen** = plainly visible; **partly** = partly hidden or blurred; **inferred** = not visible.

## R1 crop: x 780 to 1300, y 660 to 1040 (shown 1600 x 1169, cells 200 x 195 px)

View: from behind the shooter's right shoulder, slightly below the rifle, looking forward and left. The shooter is
prone. Scale at the rifle: the magazine body is about 370 px front to back (about 5.8 px/mm); the firing hand is
nearer the camera and reads larger.

| ID | Cells | Feature | Reading | Certainty |
|---|---|---|---|---|
| R1-F01 | B2-E6 | Firing hand, back of the hand | Large rounded mass, back of the hand facing the camera (right and rear). Knit fabric, coyote tan, with a tonal printed line pattern. | seen |
| R1-F02 | B2-C3, top edge to D2 | Thumb-side wipe panel | Napped (terry or suede) panel covering the thumb side of the back of the hand; lighter and fuzzy against the knit. | seen |
| R1-F03 | C3-D4 | Wrist closure tab | Moulded rubber tab about 230 x 70 px lying across the back of the wrist, raised border, maker's lettering. A small fabric pull loop stands up at its outer end (C3). | seen |
| R1-F04 | B4-D5 | Dark cuff | Black knit band between the glove and the white sleeve: the glove's cuff or an inner layer. | seen (which layer: inferred) |
| R1-F05 | D2-E3 | Knuckle flex panel | Ribbed, accordion-like panel (about 5 ribs) over the index knuckle, where the finger leaves the hand. | seen |
| R1-F06 | E3-E4 | Index finger | Runs forward from F05 and disappears into the trigger guard: finger on the trigger. Only its base is visible. | partly |
| R1-F07 | D2, x 480-700 | Dark edge binding | Black strip along the top edge of the hand between thumb side and index: a binding or the gusset between them. | seen |
| R1-F08 | (hidden) | Middle, ring, little fingers | Wrapped round the front of the grip, hidden behind the hand. | inferred |
| R1-F09 | (hidden) | Thumb | On the far (left) side of the rifle. Not visible in any reference. | inferred |
| R1-F10 | A5-D6 | Forearm | White over-sleeve arriving from below and behind at roughly 40 degrees to the bore in this view; wrist clearly bent toward the little-finger side. | seen |
| R1-S01 | F2-G4 | Support hand, fingers | Four fingers wrapped round the front of the magazine well from the left, knit backs with the same line print. | seen |
| R1-S02 | F1-G2 | Dark finger panels | Black panels with contrasting stitching on the top two fingers near their tips and last joints. | seen |
| R1-S03 | G4-G5 | Lower fingers | In shadow against the magazine. | partly |
| R1-W01 | E3 | Trigger guard and trigger | Finger enters from the right side. Scale reference. | seen |
| R1-W02 | E4-G6 | Magazine | Scale reference (about 370 px front to back). | seen |
| R1-L01 | whole | Light | Overcast, soft, from above; snow fill from below. No hard shadows. | seen |

Version 2 reading for the comparison (`checks/compare.py`), in this crop's pixels: magazine release button centre
(865, 213); right-side selector pivot (575, 163); magazine well's bottom rear corner (848, 498); ejection port cover
hinge, rear end (808, 18) and front end (1160, 42). Knuckles on the outline of the back of the hand: index (765, 335),
middle (843, 470), ring (852, 620), little (818, 790); middle of the back of the hand (520, 500). Version 1's points
for R1 lie about 95 px to the left of these, as if read off a differently cut crop (an inference from the two sets
of readings); that would explain why its camera fit failed.

## R2 crop: x 880 to 1480, y 440 to 760 (shown 1600 x 853, cells 200 x 213 px)

View: right profile, almost square to the rifle, camera at about rifle height. The shooter stands. Scale: top rail to
bottom rail of the handguard is 270 px; the model's rails are 68.0 mm apart, so 3.97 px/mm at the handguard.

| ID | Cells | Feature | Reading | Certainty |
|---|---|---|---|---|
| R2-S01 | F2-G3 | Support hand, three fingers | Three fingers side by side, pointing up the right side of the handguard, tips at the upper edge of the side rail. Together 295 px wide: 24.7 mm per gloved finger. | seen |
| R2-S02 | H2-H3 | Fourth finger (index) | Foremost finger, set a little apart and angled forward along the rail, brown leather tip. | seen |
| R2-S03 | G1 | Thumb tip | Brown leather tip showing above the top rail, beside the aiming device: the thumb comes over the top from the left. | seen (tip only) |
| R2-S04 | E3-G4 | Palm edge and heel | Brown leather palm wrapping the little-finger edge of the hand under the handguard, double row of stitching. The handguard sits at the base of the fingers, not in the middle of the palm. | seen |
| R2-S05 | E4-F4 | Gauntlet cuff | Long cuff running down and back toward the elbow. | seen |
| R2-S06 | x 1105-1530 of the crop | Position along the handguard | Rear of the handguard at x 920: the little finger starts 47 mm ahead of the receiver, the index finger ends 154 mm ahead. The hand is centred about 100 mm ahead of the receiver. | seen |
| R2-F01 | B3-C4 | Firing hand cuff | Leather-trimmed gauntlet cuff standing steeply (about 60 degrees from the bore), covering the hand. The forearm is near vertical. | seen |
| R2-F02 | (hidden) | Firing hand fingers | Behind the receiver and the cuff. | inferred |
| R2-W01 | B2-H3 | Receiver, handguard, rails | Scale reference; the same pattern as the model's rifle. | seen |
| R2-L01 | whole | Light | Overcast snow light, soft. | seen |

## R3 crop: x 760 to 1520, y 700 to 1060 (shown 1600 x 757, cells 200 x 189 px)

View: right side, close, camera slightly above. The shooter is prone and the rifle is wrapped in white cloth, so the
rifle gives little scale here.

| ID | Cells | Feature | Reading | Certainty |
|---|---|---|---|---|
| R3-F01 | B2-D4 | Firing hand, back of the hand | Back of the hand facing the camera, soft-shell fabric, olive. | seen |
| R3-F02 | C2-C4 | Knuckle reinforcement | Stitched leather band about 120 px wide across the back of the hand behind the knuckles. | seen |
| R3-F03 | D2-E2 | Index finger, straight | Lies straight along the receiver above the trigger guard, leather tip (E2) pointing at the magazine release (F1). Finger off the trigger. | seen |
| R3-F04 | D2-D4 | Middle, ring, little fingers | Three fingers curled round the grip, close together; the gaps between them show as three dark slits. | seen |
| R3-S01 | F2-H3 | Support hand, fingers | Four fingers lying horizontally round the magazine well and magazine, seen from their backs. | seen |
| R3-S02 | H1-H2 | Support thumb | Leather-tipped thumb pointing up at the front of the magazine well. | seen |
| R3-S03 | H2-H4 | Leather edge | Leather trim down the outer edge of the hand. | seen |
| R3-W01 | E1-F1 | Magazine release | Round ribbed button, the index finger's target. | seen |
| R3-L01 | whole | Light | Overcast, soft. | seen |

Version 2 reading for the comparison, in this crop's pixels: index finger axis from (650, 215) to (955, 245); the
three dark gaps between the wrapped fingers from (665, 295) to (800, 330), (680, 455) to (790, 470) and (650, 580) to
(800, 585); tip of the index finger (960, 250); centre of the magazine release (938, 128); one finger to the next,
145 px. The index finger lies within a few degrees of the direction of the other three fingers, and its tip sits
0.8 of a finger breadth below the button.

## Coverage and what the references cannot give

- Firing hand: back, index finger (two positions), knuckles and cuff are seen. The palm, the thumb and the far sides
  of the three wrapped fingers are never seen.
- Support hand: fingers (three positions), thumb tip, palm edge and cuff are seen. The palm itself and the thumb's
  path up the left side are never seen.
- No reference shows a hand working the charging handle, the bolt catch, the selector or removing a magazine. The
  clips for those are built from the HK416 manual's controls (`../../hk416/notes/MANUAL_NOTES.md`) and the standard
  right-handed manual of arms, and are labelled as inference in `NOTES.md`.
- The three references show three different gloves. The glove is modelled on R1's (the common knit-backed tactical
  pattern); R2 and R3 are used for the hands' positions, not for the glove.
