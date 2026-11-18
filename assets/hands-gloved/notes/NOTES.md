# Notes: decisions, inferences, results, limits

Version 3, 2026-11-18, modelled by Claude Fable 5.2. Credit: carpetshark. Versions 1 and 2 are the earlier commits in this
folder's history; their numbers are kept in the "before" columns below.

## Change requests (rule 7)

| No. | Date | Request | State |
|---|---|---|---|
| CR-1 | 2026-11-17 | The owner's review of version 1: references R1 to R3 approved; make version 2 with (1) a folding palm; (2) the firing grip re-solved against R1 and R3 with a numerical comparison; (3) the support grip brought onto R2; (4) contact within 1 mm at the magazine release and at the selector, interpenetration still at most 1.0 mm; (5) the little-finger length row fixed or justified; (6) if time allows, stock and sight clips and a hand-against-hand check. | **Version 2 built; four of the six items are met only in part, and the selector is not reached. Item by item below.** Approved by the owner in the project thread, message `cmsg_01K1vC6sgxYrGKq5a7aX428P3KySEwyFdWgdFJWbWQTJbj`, 2026-11-18 02:49 UTC ("appprove"); the modeller of version 2 read that message itself. |
| CR-2 | 2026-11-18 | The owner was shown version 2 and asked whether he wanted another round. His instruction was to keep the work moving; the next round was named as compressible palm pads, metacarpal flex and the sleeve fix. Goals as passed to the modeller, in priority order: (1) thenar, hypothenar and mid-palm pads and glove padding as soft tissue with sourced limits, compression reported apart from interpenetration; (2) flexion of the 2nd and 3rd metacarpals and metacarpal arching; (3) firing grip against R1 and R3, web high under the tang, three fingers round the grip; (4) thumb on the selector within 1 mm, or numbers showing why not; (5) the forearm sleeve must not hide the hand; (6) keep what version 2 met, improve the support grip and the trigger pad; (7) if time allows, stock and sight clips and hand against hand. Also: fingers, knuckles and seams must read in the matched views. | **Version 3 built. Of the seven goals two are met, three in part and two not; goal by goal below.** This was a direction to continue, not an approval of anything: the owner has not reviewed version 2's result or version 3's. References R1 to R3 stay as approved under CR-1. |

### CR-2, goal by goal

| Goal | Before (version 2) | After (version 3) | Met? |
|---|---|---|---|
| 1. Compressible palm | Rigid palm; nothing may enter the rifle by more than 1.0 mm | Four pads (thenar, hypothenar, mid-palm, distal palm) that press in toward the bone, each with a limit of half the soft tissue under it (Spartacus et al. 2021) plus 0.4 mm of glove. The check measures the glove as compressed (0.60 mm at worst, tolerance 1.0 mm everywhere, pads included) and reports compression apart: most used, distal pad 2.43 of 2.90 mm (41 % of its tissue), hypothenar 0.30 of 7.12 mm, thenar and mid-palm 0 | **Yes** as a mechanism and a check. It did not do what it was meant to do for the grip: see goals 3 and 4. |
| 2. Metacarpal flex and arching | Ring and little metacarpals only | Index and middle metacarpals flex -1.7 to 9.3 and -1.0 to 6.0 degrees (El-Shennawy 2001); the ring and little ones turn toward the thumb as they flex (the same paper's rotation arcs, coupled in proportion: inferred). In the firing grip they stand at -0.9, 1.7, 4.6 and 6.4 degrees | **Yes.** |
| 3a. Web high under the tang | Middle of the web 20 mm right of, 17 mm below and 14 mm behind the notch | 19.3 mm right, 12.2 mm below, 10.4 mm behind; the nearest glove surface is 6.1 mm from the notch | **No** across the rifle (19 mm right, as before); **in part** in height and depth. |
| 3b. Firing grip against R1 | Five landmarks 20.6 mm off on average, all about 24 mm back and 10 mm low | 16.2 mm on average (11.9 to 19.2); the knuckle row stands 2.4 degrees from the picture's vertical against 6.6 in R1 | **In part** (better, not matched). |
| 3c. Firing grip against R3 | Index finger 14.0 degrees from the three wrapped fingers (R3: 2.5), rising 13.1 degrees | 15.1 degrees from them, rising 10.4; the tip sits 0.19 finger breadths ahead of and 0.84 below the button (R3: 0.15 and 0.84) | **In part** (no better). |
| 3d. Three fingers wrap the grip | Wrapped, middle finger under the trigger guard | The same; all three closed on the grip with nothing inside it | **Yes** (kept). |
| 4. Thumb on the selector within 1 mm | 10.8 and 10.7 mm short | 12.1 and 11.7 mm short in the clips; the best the thumb can do from the firing grip is 10.5 mm, and 7.8 mm after moving the whole hand by up to 14 mm and 16 degrees (`checks/selector_reach.json`) | **No.** The numbers that show why are below. No shift of the hand is used: none tried was short and none reached. |
| 5. Sleeve must not hide the hand | Sleeve 101 x 93 mm across 210 mm up the arm; in R1's view it hides 52.7 % of the firing hand | Slimmer, longer sleeve with a forearm's taper, and the firing elbow carried lower (55 degrees out, was 60 to 65). Share of a hand hidden by a sleeve: R1 38.1 %, R2 1.9 %, R3 0.8 %, first person 0.1 % and 0.5 % | **In part.** Clear in first person and in R2 and R3; in R1's view the forearm still crosses the lower hand. |
| 6a. Keep: magazine release, joint limits, runtime parity, proportions | 0.92 and 0.80 mm; 0 of 12,798 outside; 2.3 micrometres; 10 of 10 rows | 0.51 and 0.51 mm; 0 of 15,642 outside; 2.7 micrometres (Blender skinning 0.00011 mm); 10 of 10 rows, worst 1.9 % | **Yes.** |
| 6b. Support grip against R2 | Mean 18.4 mm, max 26.8 mm | Mean 21.3 mm, max 26.5 mm | **No: 2.9 mm worse on average.** The wrist is now 6 degrees inside its limits; see "The support grip". |
| 6c. Trigger pad | 3.4 mm from the middle of the blade's face | 2.65 mm; glove 0.40 mm from the trigger at the nearest, touching in 10 of 10 frames | **In part** (0.7 mm nearer). |
| 7a. Clips for `stock_extend`, `stock_collapse`, `sights_up`, `sights_down` | None | None | **No** (not started). |
| 7b. Hand against hand | Not measured | Measured in the 102 frames where the hands come near each other: nothing in `bolt_catch`, `mag_out`, `mag_in`; **10.3 mm at worst in `charge`**, over the tolerance in 9 of its frames (12 to 19 and 35) | **Check: yes. Result: fails in `charge`.** Version 2 had the same choreography and was never measured. |
| Also: fingers, knuckles and seams must read | Smooth shells with striped bands | Knuckles stand 3.2 mm proud with four raised ribs each, the back of the hand dips between the metacarpals, finger joints swell and their flex ribs are real ridges, dark binding along the web | **In part.** They read in the R1, R2 and R3 views; the hand is still plainly a low-detail glove. Owner's eye needed. |

### CR-1, item by item

| Item | Before (version 1) | After (version 2) | Met? |
|---|---|---|---|
| 1. Folding palm | Rigid palm; ring and little metacarpals 0 to 10 and 0 to 20 degrees, unsourced | Ring and little carpometacarpal flexion -3 to 17 and -4 to 23 degrees (El-Shennawy 2001); the thenar part of the palm's skin follows the thumb metacarpal; thumb-base ranges re-read (Cooney 1981) | **In part.** It folds where a hand folds, but that did not let the palm wrap the grip: see "Why the firing grip still differs". |
| 2a. Web high under the tang | Hand backed 10 mm off the grip's side | Palm on the grip's side with nothing inside it. The middle of the web is 20 mm right of, 17 mm below and 14 mm behind the notch under the receiver's rear | **No.** |
| 2b. Index level in `fire_indexed` | Rises about 35 degrees | Rises 13.1 degrees to the bore; its tip is put where R3 has it against the magazine release | **In part.** |
| 2c. Trigger pad centred | 11.6 mm from its target (which lay 9 mm in front of the blade) | Pad 3.4 mm from the middle of the blade's face; glove 0.30 mm from the trigger in all 10 frames of `trigger_pull` | **In part.** |
| 2d. Numerical comparison, R1 and R3 | None | R1: camera fitted (1.6 mm RMS on five rifle points); five hand landmarks, mean 20.6 mm. R3: finger directions and fingertip position in finger breadths | Done; the numbers show the differences. |
| 3. Support grip on R2 | Fingertips 27 to 65 mm off, mean 40.9; hand 27.8 mm too far forward | Fingertips 10 to 27 mm off, mean 18.4; hand 3.8 mm too far back | **In part.** |
| 4a. Magazine release | Fingertip 12.4 mm from the button | Glove 0.92 mm from the button in `mag_release`, 0.80 mm in `mag_out`; the hand slides 9 mm forward on the grip to do it | **Yes.** |
| 4b. Selector | Thumb tip 22 to 25 mm short | Glove 10.8 and 10.7 mm from the lever | **No.** |
| 4c. Interpenetration at most 1.0 mm | 0.60 mm | 0.57 mm | **Yes.** |
| 5. Little-finger row | -6.1 %, fails | -0.35 % and -0.43 % against two surveys; the method changed, not the finger | **Yes** (justified; see below). |
| 6. Stock and sight clips, hand against hand | Not done | Not done | **No.** |

## Where this stands against the reference-to-3D order

| Step | State |
|---|---|
| 1. References chosen | R1, R2, R3 approved by the owner under CR-1 (message in the CR-1 row). Unchanged. |
| 2. Source-indexed decomposition | Done (`DECOMPOSITION.md`); version 3 added the readings behind the knuckle row and the forearm's route. |
| 3. Studies and grammar | Done (`STUDIES.md`); version 3 added the soft pads, the four metacarpals, the knuckles and the sleeve. |
| 4. Procedural reconstruction | Done: `model/`, `grips/`, `clips/`. |
| 5. Matched comparison | Done with numbers for all three references and two first-person views. **It still shows clear differences. This is not a faithful translation yet.** |
| 6. Owner review | Not done for version 2 or version 3. The list is at the end of this file. |

Structural results (proportions, limits, interpenetration, compression, contact, runtime parity) and visual results are
separate things. The structural checks say nothing about whether the hands look like the references.

## Results

| Check | Result | File |
|---|---|---|
| Proportions | Unchanged dimensions. Ten independent finger-length rows, all inside 6 %, worst 1.9 % (index). | `checks/proportions.json` |
| Joint limits | 15,642 values (25 joint angles and 4 pad compressions per hand, 4 arm angles): 0 outside. Margins of 0.0 degrees exist where a pose was clamped at a limit. | `checks/limits.json` |
| Contact | Trigger: touching in 10 of 10 frames (0.40 mm). Magazine release: 0.51 and 0.51 mm. Bolt catch: 0.42 mm. Selector: 12.1 and 11.7 mm, not touching. Charging handle: 6.2 mm, not touching (the finger hooks in front of it). | `checks/contact.json` |
| Selector reach | From the firing grip 10.5 mm at best; 7.8 mm at best after any of 135 small moves of the hand that stay clear and in wrist range. | `checks/selector_reach.json` |
| Interpenetration with the rifle | 474 hand-frames (310 distinct poses) against the rifle's triangles, pads compressed as each frame says: deepest 0.60 mm (support hand's cuff against the magazine well's flare); tolerance 1.0 mm. | `checks/penetration.json` |
| Soft-pad compression | Most in any frame: distal palm 2.43 mm of 2.90 (41 % strain), hypothenar 0.30 of 7.12, thenar 0 of 5.30, mid-palm 0 of 2.40. Without compression those pads would sit 1.86, 0.65, 0 and 0.21 mm inside the rifle. Nothing beyond what a limit could take up. | `checks/penetration.json` (`soft_pads`) |
| Hand against hand | 102 frames with the hands near each other, 93 distinct pairs of poses: 0 mm in three clips, 10.3 mm in `charge`. **Fails.** | `checks/penetration.json` (`hand_against_hand`) |
| Runtime parity | JS fingertips against the Python recipe: worst 2.72 micrometres over 2,370 points. Blender skinning with the pads' shape keys against the recipe: 0.00011 mm. | `checks/test_runtime.js`, `model/inventory.json` |
| Matched comparison | R1: mean 16.2 mm. R2: mean 21.3 mm. R3: index finger 15.1 degrees from the other three against 2.5 in the photograph. Sleeve: table above. | `checks/comparison.json`, `renders/` |

The interpenetration tolerance is unchanged: 1.0 mm, everywhere. Version 2 allowed no compression at all; version 3 lets
four named pads press in, inside limits, and measures the glove in that state. That is a change to what is measured, made
on purpose under CR-2 goal 1; version 2's result (0.57 mm, no compression) stays in this file and in the history of
`checks/penetration.json`. A hand against its own fingers is still **not** measured.

## What CR-2 was expected to do, and what it did

Version 2's notes said the palm could not wrap the grip because it was rigid, and proposed compressible pads and
metacarpal flexion as the cure. Both are now in the recipe and the solver used them where they help (the distal pad
beds 2.4 mm onto the grip's right face). **The web still sits 19 mm to the right of the rifle's centre plane, and the
thumb still cannot reach the selector.** The cause is not the palm's stiffness. Measured:

1. **The wrist and the stance decide where the web goes.** With the palm on the right face of the grip the web lies in
   the palm's plane, 19 mm right of centre. To bring it to the centre the hand has to turn about the grip by about 24
   degrees, wrist toward the centre plane. The forearm is fixed by the stance: shoulder to wrist is 281 mm, the arm is
   335 + 268 mm, so the forearm always stands 75 degrees from the shoulder-wrist line, which is nearly the bore. With
   the elbow out (the stance kept from version 2) that turn would need about 80 degrees of wrist extension (the 58 the
   level grip had, plus the turn: an estimate, not a solved pose) against a limit of 70. A scan of 1,331 orientations
   with the web held on its seat (a working script, not committed as a check) found 11 that keep the wrist in range and
   the palm clear; all have the elbow tucked under the rifle and **the hand rising 32 to 40 degrees**.
2. **That tucked grip was solved and rejected.** In it the web is 1 mm from the centre plane and the thumb's glove comes
   within 1.2 mm of the selector lever at safe (5.4 mm at fire). But the knuckles ride up: the middle finger's knuckle
   pad sits 33 mm above where the trigger guard lets a finger pass, the three fingers bunch at the top of the grip, and
   the comparison with R1 goes from 16 mm to 42.5 mm. R1 and R3 show a level hand with its fingers on the grip, so the
   level grip was kept. The rejected one is drawn in `renders/alternative_tucked_firing_grip.jpg` for the owner.
3. **The web is modelled as a rigid tube 14.4 mm thick.** A real web is a fold of skin that drapes behind the top of the
   grip while the bones stay to one side. The model's cannot, so "web under the tang" asks for the whole hand to be
   there. This is the part of the hand that should be made soft next (it is not one of CR-2's pads).
4. **The selector.** The lever's rear tip is 50.0 mm above and 90.7 mm from the thumb's base joint; the thumb is 112 mm
   from that joint to the glove's tip, but it has to cross behind the top of the grip under the receiver's rear and then
   lie along the left wall at the lever's height, and its first bone (48.1 mm, turning 26.5 degrees in flexion and 21 in
   abduction each way) cannot both cross and climb that far. With the web on its seat the base joint would be 19 mm
   further left and the distance 80.7 mm, which is the tucked grip's result. So the thumb's reach follows from item 1.
5. **The hand's own proportions between web and knuckles are inferred** (`model/handlib.py` `P['thumb_cmc']`,
   `P['thumb_dir']`): the middle of the web lies 46 mm from the middle finger's knuckle pad. R1 suggests more. No
   measurement of this was found; a sourced one would move every number in this section.

What would change it, in the order I would try: a web that drapes (item 3); a measured position of the thumb's base
and web (item 5); a different stance for the firing arm, which is the owner's call (item 1).

## What the comparison shows

- **R1, firing hand.** The five landmarks are now 11.9 to 19.2 mm from the photograph's (mean 16.2; version 2: 20.6),
  still mostly behind them: the photographed hand has its knuckles at the front of the grip. The knuckle row is nearly
  upright in both (6.6 degrees in R1, 2.4 in the model), so the hand's pitch is right and its place along the grip is
  not. The forearm: R1's leaves the picture toward the lower left with the wrist bent to the little-finger side; the
  model's crosses the lower part of the hand, because it stands 75 degrees from the bore whatever the elbow does
  (above). 38.1 % of the hand is behind the sleeve in this view (version 2: 52.7 %). The camera's across-rifle
  direction is derived, not measured, and the photo's knuckle points are read off an outline: good to about 5 mm.
- **R3, firing hand.** No better than version 2: the index finger lies 15.1 degrees from the three wrapped fingers
  (R3: 2.5), rising 10.4 degrees to the bore. Its tip is where R3 has it against the magazine release (by construction).
  The magazine grip was not reworked: lower on the magazine than R3's, thumb on the left where R3's points up.
- **R2, support hand.** Worse on average than version 2 (21.3 mm against 18.4): fingertips 13.5 to 26.5 mm from R2's,
  all lower on the side of the handguard; thumb tip 21.7 mm low. R2-F01 (the firing hand's cuff standing about 60
  degrees from the bore) agrees with the model's steep firing forearm.
- **Visible construction.** Knuckle ribs, finger joints, fingertip caps, the wipe panel, the cuff tab and the dark
  binding on the web can be told apart in the three matched renders. The glove is still plain shells with flat
  materials: no fabric texture, no stitching, no print, no wear.
- **First person.** No photograph to compare with. From the sights the firing hand is behind the receiver; from above
  and to the left both hands are on screen and neither is behind a sleeve (0.0 % and 0.5 %).

## The support grip

The support grip is found by a random search and scored against where R2 has the fingertips. Three runs this version:
default settings, mean 18.4 mm (max 23.1) with the wrist 1.0 degree from both its ulnar and its pronation limit; pads
allowed to compress, 23.3 mm; and the wrist held 6 degrees inside every limit, 21.3 mm (max 26.5). The first is the best
fit and was not kept: with it the frames in which the hand leaves the handguard in `charge` ran up to 3.7 degrees past
the wrist's limits (18 values outside). The third is committed. So the R2 number got worse to keep the joint limits
met, and this goal is not met. The fingertips stop about 20 mm short of R2's up the side of the handguard in every run;
that is the hand's seat under the handguard (the search rests the handguard on the palm, R2 has it at the base of the
fingers), not the wrist, and it is the thing to rework.

## Stance

| | Version 1 | Version 2 | Version 3 |
|---|---|---|---|
| Stock | collapsed | extended 75 mm for the arms only (the rifle is drawn and checked collapsed) | the same |
| Right shoulder joint | 45 mm behind the buttpad | the same, so 75 mm further back | the same |
| Torso | turned 15 degrees | turned 30 degrees | the same |
| Elbow swivel allowed | -10 to 75 degrees | -10 to 100 degrees | the same |
| Elbow swivel chosen, firing arm | least wrist bend | furthest from any limit (60 to 65 degrees out) | the lowest elbow that keeps every angle 4 degrees inside its limit (55 degrees out), after R1-F10 and R2-F01 |
| Elbow swivel chosen, support arm | least wrist bend | furthest from any limit | the same |
| Firing wrist | 45 extension, 29 ulnar | 58 extension, 19 ulnar | 52 extension, 25.5 ulnar, 38 supination; 4.5 degrees inside the nearest limit |
| Support wrist | | 55 extension, 28 ulnar, 76 supination | 61 extension, 23 ulnar, 74 supination |

The stance is an inference and it fixes the forearm's direction, and through that the grip (above). It is the first
thing for the owner to decide.

## The little-finger row (CR-1 item 5)

Version 1 compared joint-to-tip lengths with a survey's crease-to-tip lengths by subtracting one offset, fitted on
the middle finger, from every finger; the little finger came out 6.1 % short. Version 2 read a second survey
(Greiner 1991, U.S. Army men, n = 1,003). Both surveys give little / middle = 0.772. The bones the recipe uses give
0.764 for the phalanges alone. A skin ratio that close to the bone ratio is only possible if the crease sits nearer
the knuckle on a shorter finger, so the offset is now a fixed share (0.297) of the proximal phalanx. That share is an
inference; with it the little finger is 0.35 % and 0.43 % short. The finger itself did not change. The old rows are
kept in `proportions.json` as `reported` (-6.1 % and -5.6 %).

## Inferences (no measurement found), with their consequences

| Inference | Value | Consequence |
|---|---|---|
| Scale applied to the mixed-sex phalanx lengths | 1.04 | Sets every finger length. |
| Finger depths, joint centres across the palm, knuckle arc and arch, palm thickness, section shape | `model/handlib.py` `P` | Shape of the hand between the measured dimensions. |
| Thumb base position and rest direction; the rest pose is the middle of the thumb's range | `P['thumb_cmc']`, `P['thumb_dir']` | Where the web lies and where the thumb can reach: the firing grip and the selector. |
| Where the flat hand sits in each metacarpal's arc | 15 % in | Their limits. |
| The ring and little metacarpals turn in proportion to their flexion | 1.35 and 0.81 degrees per degree | The hand's arch. |
| Soft-tissue thickness under each pad's middle: thenar 9.8, hypothenar 13.4 mm (model geometry less a bone half-thickness of 6.0 and 4.5 mm), mid-palm 4.0, distal palm 5.0 mm | `P`, `pad_table` | Each pad's limit. Only the 50 % rule and the 2.75 mm over the trapezium are measured. |
| Each pad's footprint and the direction it moves | `pad_fields` | Where compression can take up contact. |
| A wide contact may compress as far as a 3 mm indenter did | 50 % | The limits are generous for a grip; the most used is 41 %. |
| Glove give | 0.4 mm per pad | Part of each limit. |
| Compression does not bulge the tissue elsewhere | none | The hand loses a little volume where it is pressed. |
| The web is rigid | 14.4 mm thick | It cannot drape behind the grip (above). |
| The thenar crease line and how far the skin follows the thumb | `P['thenar_crease']` | The palm's fold. |
| Crease offset as a share of the proximal phalanx | 0.297 | The finger-length check only. |
| Glove thickness 1.2 mm, cuff 2.6 mm, fingertip allowance 1.5 mm | `P` | Clearances. |
| Knuckle height, joint swell, valleys, rib height | `P['knuckle']`, `P['rib_height']` | How the back of the hand reads; the knuckle landmarks used against R1 moved 3.2 mm outward with it. |
| Forearm girth and taper under the sleeve, sleeve cloth 3 mm, shown to 245 mm | `P` | What the sleeve hides. |
| Stance | table above | Every wrist, forearm and elbow angle, and the forearm's direction in the pictures. |
| Where the firing hand sits on the grip | `GRIP_PADS`, `WEB_SEAT`, `spec_fire_indexed` | The firing grip. |
| Thumb of the firing hand (never visible in a reference) | toward the left of the grip | R1-F09. |
| The slide forward for the magazine release | the wrist moves 6.5 mm and turns 3.3 degrees (asked: 9 mm along the grip) | `mag_release`, `mag_out`. |
| All of `bolt_catch`, `charge`, `mag_out`, `mag_in`, selector and release clips | `STUDIES.md` study 6 | No reference shows them. |
| A frame that would cut through the rifle is moved clear | `clips/make.py` `ESCAPE` | Up to 81 mm in `charge`; for the firing hand up to 8.4 mm (`mag_release`, `mag_out`), 6.6 mm (`safety_to_fire`); version 2: 4 mm. |
| A frame that asks for more elbow flexion than there is has its hand moved out along the shoulder-wrist line | 1.45 mm in `charge` | Joint limits. |

## Sources

Read for version 3 (2026-11-17 and -18): Spartacus et al. 2021 (full text, through the Europe PMC API); Lameu et al.
2004 and Choi and Robinovitch 2011 (abstracts, through the PubMed API). Looked for and not found: published thickness
of the thenar and hypothenar muscle bellies (Misirlioglu and Ozyemisci Taskiran 2018 measure them; the abstract gives
no values), a compression figure for a hand on a handle, and a doctrine source for shifting the grip to work the
selector (only a shop's blog says right-handers often alter their grip for it; not used). Read for version 2: ANSUR II
(recomputed from the public file); El-Shennawy 2001, Cooney 1981 and Kawanishi 2018 (abstracts); Bain 2015 (abstract);
Greiner 1991 (scanned report). Still carried over or recalled, not re-read: Buryanov and Kotiuk's phalanx table, Hsiao's
breadths and lengths, the end points of Bain's active range, Hume 1990's thumb ranges, the AAOS wrist values, Kapandji's
figure, and the bone half-thicknesses used for the pads. Each is marked in `model/handlib.py` `SRC` or `P`.

## Omissions

- Rifle clips with no hand clip: `stock_extend`, `stock_collapse`, `sights_up`, `sights_down` (CR-1 item 6, CR-2 goal 7).
- A hand against its own fingers is not measured.
- `charge` has the hands passing through each other (above); not fixed.
- R1's support hold on the front of the magazine well (R1-S01) is not a grip here.
- The printed pattern and the maker's lettering on R1's glove (on purpose), fabric texture, stitching.
- Only the 50th-percentile hand is solved against the rifle.
- Skinning is linear blend: joints lose a little volume when bent hard, and the palm's fold is a blend, not a crease.
- The fingertips' pulp is not compressible; only the four palm pads are.
- The recoil of `assets/hk416/action` is not applied to the hands.
- The solver seats the palm with the cuff straight behind the hand; the check measures it with the wrist bent.
- The glb carries the pads as shape keys with their own animation channels; a viewer that ignores morph targets shows
  the pads uncompressed (up to 2.4 mm into the grip at the distal palm).

## For the owner to review

1. The pictures: `renders/compare_R1_firing_grip.jpg`, `compare_R2_support_grip.jpg`,
   `compare_R3_indexed_and_magazine_grip.jpg`, `first_person_low_ready.jpg`, `first_person_sights.jpg`, and the
   side-by-sides with the photographs in `refs-local/build/compare/` (local; rebuild with `checks/compare.py`).
2. **The firing grip's two answers.** Kept: level hand, fingers on the grip, R1 at 16 mm, web 19 mm right of centre,
   selector out of reach. Rejected: `renders/alternative_tucked_firing_grip.jpg`, web centred and thumb at the selector,
   hand rising 37 degrees, R1 at 42 mm. Which one, or neither?
3. **The stance** (stock extended for the arms only, firing elbow 55 degrees out). It decides item 2.
4. Whether the next change request should be a web that drapes and a measured thumb base, as proposed above.
5. Whether the selector clips may ship while the thumb stops 12 mm short.
6. `charge`: the hands pass through each other by up to 10 mm. Rework the approach, or accept for now?
7. The support grip: 21.3 mm from R2 with the wrist safely in range, against 18.4 mm at the edge of it.
8. The sleeve in R1's view (38 % of the hand behind it), and the look of the knuckle ribs and the plain glove.
9. The pads' limits: half the tissue thickness, from a 3 mm indenter, applied to a whole grip.
