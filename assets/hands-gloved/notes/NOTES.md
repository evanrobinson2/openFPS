# Notes: decisions, inferences, results, limits

Version 4, 2026-11-18, modelled by Claude Fable 5.2. Credit: carpetshark. Versions 1 to 3 are the earlier commits in this
folder's history (version 3: `b123f6e`); their numbers are kept in the "before" columns below. Sections not marked
version 4 are version 3's and still hold: the hand recipe and the grips `fire`, `fire_indexed`, `fire_reach`, `support`,
`mag_grip` and `catch_ready` did not change.

## Change requests (rule 7)

| No. | Date | Request | State |
|---|---|---|---|
| CR-1 | 2026-11-17 | The owner's review of version 1: references R1 to R3 approved; make version 2 with (1) a folding palm; (2) the firing grip re-solved against R1 and R3 with a numerical comparison; (3) the support grip brought onto R2; (4) contact within 1 mm at the magazine release and at the selector, interpenetration still at most 1.0 mm; (5) the little-finger length row fixed or justified; (6) if time allows, stock and sight clips and a hand-against-hand check. | **Version 2 built; four of the six items are met only in part, and the selector is not reached. Item by item below.** Approved by the owner in the project thread, message `cmsg_01K1vC6sgxYrGKq5a7aX428P3KySEwyFdWgdFJWbWQTJbj`, 2026-11-18 02:49 UTC ("appprove"); the modeller of version 2 read that message itself. |
| CR-2 | 2026-11-18 | The owner was shown version 2 and asked whether he wanted another round. His instruction was to keep the work moving; the next round was named as compressible palm pads, metacarpal flex and the sleeve fix. Goals as passed to the modeller, in priority order: (1) thenar, hypothenar and mid-palm pads and glove padding as soft tissue with sourced limits, compression reported apart from interpenetration; (2) flexion of the 2nd and 3rd metacarpals and metacarpal arching; (3) firing grip against R1 and R3, web high under the tang, three fingers round the grip; (4) thumb on the selector within 1 mm, or numbers showing why not; (5) the forearm sleeve must not hide the hand; (6) keep what version 2 met, improve the support grip and the trigger pad; (7) if time allows, stock and sight clips and hand against hand. Also: fingers, knuckles and seams must read in the matched views. | **Version 3 built. Of the seven goals two are met, three in part and two not; goal by goal below.** This was a direction to continue, not an approval of anything: the owner has not reviewed version 2's result or version 3's. References R1 to R3 stay as approved under CR-1. |
| CR-3 | 2026-11-18 | Passed on by the main session while the owner slept: he had said to keep the work moving. **An interim, reversible choice that he may change; not his approval of any result.** Keep the level firing grip that matches R1 and R3; do not adopt the tucked-elbow grip; do not change `fire` or `fire_indexed`. Goal 1: give `safety_to_fire` and `safety_to_safe` their own deliberate hand move, as large as it needs, trigger finger straight and away from the trigger, thumb on the lever (glove within 1.0 mm) through the lever's whole stroke in step with the rifle's clip, hand back exactly on the level grip, interpenetration at most 1.0 mm in every frame, joint limits respected, no frame with the index finger in the trigger guard; report the size of the move. Goal 2, if it fits: fix the hand-against-hand failure in `charge` by reworking its approach. Keep everything version 3 met; relax no check. | Version 4. Both goals met by the numbers; the selector move is large and takes the elbow under the rifle. See "CR-3" below. **Not reviewed by the owner.** |

### CR-3 (version 4), goal by goal

| Goal | Before (version 3) | After (version 4) | Met? |
|---|---|---|---|
| 1a. Thumb's glove within 1.0 mm of the lever through the lever's whole stroke | 12.1 and 11.7 mm short; the hand did not move | `safety_to_fire`: 0.34, 0.40, 0.51, 0.40, 0.37, 0.42 mm in the six frames of the rifle's clip. `safety_to_safe`: 0.50, 0.45, 0.37, 0.51, 0.45, 0.46 mm | **Yes.** |
| 1b. Interpenetration at most 1.0 mm in every frame | 0.51 mm | 0.51 mm at worst in both clips, and that is the support hand's cuff at rest; the firing hand is never deeper | **Yes.** |
| 1c. Joint limits | 0 outside | 0 of 17,754 values outside; in the two clips the smallest margin is 0.5 degrees, the trigger finger's knuckle as in the firing grip. The arm is kept 1.5 degrees inside its limits through the move | **Yes.** |
| 1d. Trigger finger straight and out of the trigger guard | Not measured | No glove vertex of any finger inside the guard's window in any of the 60 frames (the same test finds at least 78 vertices of the index finger there in every frame of `trigger_pull`). The trigger finger keeps the firing grip's joint angles throughout and never comes nearer the trigger than 19.3 mm | **Yes.** |
| 1e. Hand returns exactly to the level grip | It never left | Last frame equals first: 0.0 mm, 0.0 degrees, every angle equal | **Yes.** |
| 1f. Size of the move | None | **The wrist joint moves 28.9 mm and the hand turns 50.7 degrees; the elbow swings from 55 degrees out to 10 degrees inside straight down, 292 mm at the elbow's point.** Knuckle pads move 22 (index) to 43 mm (little), the trigger finger's tip 90 mm. Mid-move the hand is up to 42.7 mm and 56.8 degrees from the firing grip. Twelve frames (0.5 s) each way | Reported. **It is a large move; see below.** |
| 2. `charge`: hand against hand | 10.3 mm, frames 12 to 19 and 35 | 0.0 mm in every one of the 93 frames where the hands come near; the gloves are never closer than 4.8 mm in `charge`. Its other checks: interpenetration 0.51 mm (was 0.27), limits 0 outside (smallest margin 0.02 degrees, forearm, in the return), index finger on the handle at 0.29 mm in 14 frames (was 6.2 mm, never touching) | **Yes.** |
| Keep: everything version 3 met | | Unchanged clips are taken frame for frame from version 3. Interpenetration 0.60 mm at worst; magazine release 0.51 and 0.51 mm; trigger 0.40 mm; bolt catch 0.42 mm; runtime parity 2.3 micrometres; proportions 10 of 10; comparison with R1, R2, R3 unchanged (16.2 mm, 21.3 mm, 15.1 degrees) | **Yes.** No check was relaxed. |

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
| 6. Owner review | Not done for version 2, 3 or 4. The list is at the end of this file. Version 4's two clips have no reference: they are inferred motion, checked structurally and shown in frame strips, and nothing about them is a comparison with a source. |

Structural results (proportions, limits, interpenetration, compression, contact, runtime parity) and visual results are
separate things. The structural checks say nothing about whether the hands look like the references.

## Results

| Check | Result | File |
|---|---|---|
| Proportions | Unchanged dimensions. Ten independent finger-length rows, all inside 6 %, worst 1.9 % (index). | `checks/proportions.json` |
| Joint limits | Version 4: 17,754 values, 0 outside. Version 3: 15,642 values (25 joint angles and 4 pad compressions per hand, 4 arm angles): 0 outside. Margins of 0.0 degrees exist where a pose was clamped at a limit. | `checks/limits.json` |
| Contact | Trigger: touching in 10 of 10 frames (0.40 mm). Magazine release: 0.51 and 0.51 mm. Bolt catch: 0.42 mm. Selector: version 4, 0.34 and 0.37 mm, touching in all six frames of the lever's stroke in both clips (version 3: 12.1 and 11.7 mm, not touching). Charging handle: version 4, 0.29 mm, touching in 14 frames (version 3: 6.2 mm, not touching). | `checks/contact.json` |
| Selector reach | From the firing grip 10.5 mm at best; after a small move of the hand 10.1 mm at best of 144 that stay clear and in wrist range (version 3 reported 7.8 mm of 135 from a file older than its last grip; see "CR-3"). | `checks/selector_reach.json` |
| Selector scan (version 4) | 24,000 hand poses, 1,827 kept, 107 reach the lever at both ends; none turned under 45 degrees, none with the elbow more than 15 degrees out. | `checks/selector_scan.json` |
| Selector move (version 4) | Both safety clips pass every condition of CR-3 goal 1; the move is 28.9 mm and 50.7 degrees at the wrist and 292 mm at the elbow. | `checks/selector_move.json` |
| Interpenetration with the rifle | Version 4: 538 hand-frames (339 distinct poses), deepest 0.60 mm, the same place. Version 3: 474 hand-frames (310 distinct poses) against the rifle's triangles, pads compressed as each frame says: deepest 0.60 mm (support hand's cuff against the magazine well's flare); tolerance 1.0 mm. | `checks/penetration.json` |
| Soft-pad compression | Most in any frame: distal palm 2.43 mm of 2.90 (41 % strain), hypothenar 4.12 of 7.12 (version 4, in the selector hold; version 3: 0.30), thenar 0 of 5.30, mid-palm 0 of 2.40. Without compression those pads would sit 1.86, 0.65, 0 and 0.21 mm inside the rifle. Nothing beyond what a limit could take up. | `checks/penetration.json` (`soft_pads`) |
| Hand against hand | Version 4: 93 frames with the hands near each other, 83 distinct pairs of poses: 0.0 mm in all four clips. **Passes.** Version 3: 102 frames, 10.3 mm in `charge`, failed. | `checks/penetration.json` (`hand_against_hand`) |
| Runtime parity | JS fingertips against the Python recipe: worst 2.33 micrometres over 2,690 points (version 3: 2.72 over 2,370). Blender skinning with the pads' shape keys against the recipe: 0.00011 mm. | `checks/test_runtime.js`, `model/inventory.json` |
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

## CR-3: the move to the selector (version 4)

What was built, what it rests on, and what it does not show. All of it is inferred: no reference shows a hand at the
selector, and none was chosen for it.

1. **How far the hand has to go** (`checks/selector_scan.json`). 24,000 hand poses as moves from the firing grip; 1,827
   leave the palm and the trigger finger clear of the rifle and the arm in range; each was tried with 3,000 thumb poses
   at both ends of the lever's travel. None of the 879 poses turned less than 45 degrees reaches both ends (best: 1.5
   mm short at 35 to 45 degrees, 6.2 mm at 25 to 35). 107 reach, all with the hand turned 45 degrees or more.
2. **The elbow has to come in.** The firing grip fits the arm only with the elbow 50 to 90 degrees out. Of the poses
   that reach, none fits an elbow more than 15 degrees out, and with the elbow kept 30 degrees or more out the best is
   5.5 mm short. So the reach belongs to the other way of holding the arm, the one version 3 found and rejected as a
   firing grip. CR-3 says not to adopt it as the grip; here the hand goes there for the lever and comes back.
3. **The hold** (`fire_select`, `grips/solve.py` `solve_select`). Started from the scan's smallest reaching move and
   searched on the hand's pose and the thumb at three positions of the lever for the smallest move that keeps the
   thumb's glove on the lever at all three: wrist moved 28.9 mm, hand turned 50.7 degrees, thumb 0.58, 0.51 and 0.59
   mm from the lever. The three fingers close loosely on the grip; the palm leaves the grip's right face.
4. **The way there** (`clips/make.py` `transit`). No single elbow position serves both holds, and halfway along the
   straight blend between them no elbow position fits at all (1.9 degrees past a limit at the worst point). So the elbow is swung
   evenly from 55 to -10 degrees over twelve frames and at each frame the hand is moved off the blend by the least that
   keeps the arm 1.5 degrees inside its limits at that elbow position and everything clear: up to 35 mm and 12 degrees
   off the blend, with the fingers and thumb opened in the middle of the move. Fastest: elbow swivel 9 degrees a frame,
   hand 15.8 degrees a frame.
5. **The thumb on the lever** (`ride_lever`). Hand held still; per frame of the rifle's clip the thumb's joints are
   searched for glove on lever, with the vertex that starts nearest the lever pulled to stay on its spot of the lever.
   It slips 3.0 mm along the lever in `safety_to_fire` and 8.6 mm in `safety_to_safe`.

**What this does not show.**
- **It is contact, not a push.** The thumb's glove lies on the lever's outer face (4 mm out from the wall, within 3 mm
  of the lever's centre line), not behind an edge of it. Nothing measures force. In `safety_to_safe` the thumb starts
  over the pivot and ends 11 mm out along the lever.
- **It is a big, slow way to work a selector**: half a second each way and a 292 mm swing of the elbow for a lever that
  turns in a quarter of a second. It follows from this model's stance, wrist limits and rigid web (the three things
  version 3's notes name), not from how the drill is taught. A draping web or a measured thumb base would probably
  shorten it; that is still the proposed next change.
- Mid-move the three fingers stand straight out from the grip (frames 7 to 10 of the strip). Inside the limits and
  clear of everything, and odd to look at.
- The middle finger's tip passes near the trigger guard's front while the hand is at the lever. Not inside its window
  by the check; visible in the strip.
- The hypothenar pad is pressed 4.12 mm of its 7.12 mm limit in these clips (version 3's most: 0.30 mm).
- The cuff and sleeve are not checked against the rifle with the elbow under it, beyond the glove's own check.
- The hold is solved by a random search; of two runs one ended at 13.5 and one at 4.5 on its score, and the better is
  kept. A rebuild gives the same result (fixed seeds), a changed rifle or hand may not.

**A correction to version 3.** `checks/selector_reach.json` was rerun unchanged and its second figure moved: the best
after a small move of the hand is 10.1 mm, not 7.8 mm (144 moves kept, not 135). Version 3's file had been written
before the firing grip's last re-solve. The first figure (10.5 mm from the firing grip) is the same. CR-3's brief quoted
7.8 mm.

## CR-3: `charge` (version 4)

Version 3's support hand reached the handle from below with its three curled fingers hanging where the firing hand's
thumb lies, and went through it. Now: (a) the hold is turned 24 degrees about the bore's direction and 20 degrees about
the vertical, both through the hooking point, and set 8 mm back, so the wrist is 45 mm higher, 25 mm further left and
34 mm further forward; turning it flatter alone cleared the thumb but brought the wrist within 157 mm of the left
shoulder at full draw, nearer than a folded elbow allows (170 mm). (b) The index pad's point is on the wing's front
face (version 3 had it 3.5 mm beyond the wing's tip) and the finger is closed on the handle. (c) The hand leaves the
handguard down and outboard, arrives from outboard and ahead, and is turned 15 degrees toward pronation at both
waypoints; without that the forearm ran up to 8.5 degrees past its limit in between. The clearance pass now moves a
frame 36 mm at most (version 3: 81 mm). All of it inferred; the waypoints are in `clips/make.py` (`CHARGE_OFF`,
`CHARGE_ON`, `CHARGE_ROLL`). The index finger's knuckle is bent back 17.5 degrees in the hold, of the 19 its limit allows.

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
| Version 4: the selector hold, the twelve frames each way, the even swing of the elbow, the 1.5 degree arm margin, the window taken as the trigger guard | `grips/solve.py` `solve_select`, `TRIGGER_GUARD`; `clips/make.py` `SEL_IN`, `transit` | The whole of both safety clips. |
| Version 4: the charging hold's direction and the waypoints to it | `spec_charge_grip`, `CHARGE_OFF`, `CHARGE_ON`, `CHARGE_ROLL` | `charge`. |
| A frame that would cut through the rifle is moved clear | `clips/make.py` `ESCAPE` | Up to 36 mm in `charge` (version 3: 81 mm); for the firing hand up to 8.4 mm (`mag_release`, `mag_out`), none in the safety clips (version 3: 6.6 mm); version 2: 4 mm. |
| A frame that asks for more elbow flexion than there is has its hand moved out along the shoulder-wrist line | None in version 4 (version 3: 1.45 mm in `charge`) | Joint limits. |

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
- Fixed in version 4: `charge` had the hands passing through each other.
- The selector move is checked for where the glove is, not for whether the thumb could push the lever ("CR-3").
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

Version 4 first (CR-3 was an interim choice made while the owner slept; any of it can be undone, version 3 is `b123f6e`):

1. **The selector move**: `renders/selector_move_safety_to_fire.jpg` and `renders/selector_move_safety_to_safe.jpg`
   (thirteen frames each; rows: from the left, from the right, from behind). It meets every number asked and it is a
   half-second move with the elbow swinging under the rifle and back. Keep it, shorten it by changing the stance or
   softening the web, or go back to version 3's thumb that stops short?
2. Whether a thumb lying on the lever's face counts as working it, or the clip must show it behind an edge.
3. **`charge`**: `renders/charge_strip.jpg`. The hand now comes in flatter and from further forward and no longer
   passes through the firing hand. Does the approach read as right?
4. The firing grip's two answers, still open, and now with a third use: the tucked hold is where the hand goes for the
   selector.

Carried over from version 3:

1. The pictures: `renders/compare_R1_firing_grip.jpg`, `compare_R2_support_grip.jpg`,
   `compare_R3_indexed_and_magazine_grip.jpg`, `first_person_low_ready.jpg`, `first_person_sights.jpg`, and the
   side-by-sides with the photographs in `refs-local/build/compare/` (local; rebuild with `checks/compare.py`).
2. **The firing grip's two answers.** Kept: level hand, fingers on the grip, R1 at 16 mm, web 19 mm right of centre,
   selector out of reach. Rejected: `renders/alternative_tucked_firing_grip.jpg`, web centred and thumb at the selector,
   hand rising 37 degrees, R1 at 42 mm. Which one, or neither?
3. **The stance** (stock extended for the arms only, firing elbow 55 degrees out). It decides item 2.
4. Whether the next change request should be a web that drapes and a measured thumb base, as proposed above.
5. (Answered for now by version 4: the selector clips reach.)
6. (Answered for now by version 4: `charge` reworked.)
7. The support grip: 21.3 mm from R2 with the wrist safely in range, against 18.4 mm at the edge of it.
8. The sleeve in R1's view (38 % of the hand behind it), and the look of the knuckle ribs and the plain glove.
9. The pads' limits: half the tissue thickness, from a 3 mm indenter, applied to a whole grip.
