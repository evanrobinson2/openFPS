# Notes: decisions, inferences, results, limits

Version 2, 2026-11-17, modelled by Claude Fable 5.2. Credit: carpetshark. Version 1 is the commit before CR-1 in this
folder's history; its numbers are kept in the "before" columns below.

## Change requests (rule 7)

| No. | Date | Request | State |
|---|---|---|---|
| CR-1 | 2026-11-17 | The owner's review of version 1: references R1 to R3 approved; make version 2 with (1) a folding palm; (2) the firing grip re-solved against R1 and R3 with a numerical comparison; (3) the support grip brought onto R2; (4) contact within 1 mm at the magazine release and at the selector, interpenetration still at most 1.0 mm; (5) the little-finger length row fixed or justified; (6) if time allows, stock and sight clips and a hand-against-hand check. | **Version 2 built; four of the six items are met only in part, and the selector is not reached. Item by item below.** Approved by the owner in the project thread, message `cmsg_01K1vC6sgxYrGKq5a7aX428P3KySEwyFdWgdFJWbWQTJbj`, 2026-11-18 02:49 UTC ("appprove"); the modeller of version 2 read that message itself. |

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
| 1. References chosen | R1, R2, R3 approved by the owner (message above). |
| 2. Source-indexed decomposition | Done (`DECOMPOSITION.md`); version 2 added the points read for the R1 and R3 comparisons. |
| 3. Studies and grammar | Done (`STUDIES.md`); version 2 added the folding palm, the stance and the seat along the grip. |
| 4. Procedural reconstruction | Done: `model/`, `grips/`, `clips/`. |
| 5. Matched comparison | Done with numbers for all three references. **It still shows clear differences. This is not a faithful translation yet.** |
| 6. Owner review | Not done for version 2. The list is at the end of this file. |

Structural results (proportions, limits, interpenetration, contact, runtime parity) and visual results are separate
things. The structural checks say nothing about whether the hands look like the references.

## Results

| Check | Result | File |
|---|---|---|
| Proportions | Hand length, breadth, palm length and forearm equal ANSUR II by construction. Circumferences fitted to 0.02 % and 0.37 %. Finger lengths against Hsiao 2015 and Greiner 1991: ten independent rows, all inside 6 %, worst 1.9 % (index). | `checks/proportions.json` |
| Joint limits | 12,798 values: 0 outside. Margins of 0.0 degrees exist where a pose was clamped at a limit. | `checks/limits.json` |
| Contact | Trigger: touching in 10 of 10 frames. Magazine release: 0.92 and 0.80 mm. Bolt catch: 0.42 mm. Selector: 10.8 and 10.7 mm, not touching. Charging handle: 5.45 mm, not touching (the finger hooks in front of it). | `checks/contact.json` |
| Interpenetration | 474 hand-frames (308 distinct poses) measured against the rifle's triangles: deepest 0.57 mm (`charge`, index finger against the charging handle's latch); tolerance 1.0 mm. | `checks/penetration.json` |
| Runtime parity | JS fingertips against the Python recipe: worst 2.25 micrometres over 2,370 points. Blender skinning against the recipe: 0.00008 mm. | `checks/test_runtime.js`, `model/inventory.json` |
| Matched comparison | R2: mean 18.4 mm. R1: mean 20.6 mm. R3: index finger 14.0 degrees from the other three fingers against 2.5 in the photograph; its tip 0.85 finger breadths below the button against 0.84. | `checks/comparison.json`, `renders/compare_*.jpg` |

Interpenetration tolerance: 1.0 mm, less than the glove's own 1.2 mm shell. Hand against hand, and a hand against its
own fingers, are **not** measured.

## What the comparison shows

- **R1, firing hand.** The camera fit puts it 47 degrees behind square-on and 8 degrees below. The model's four
  knuckles and the middle of the back of its hand lie 19 to 22 mm from the photograph's, all the same way: about 24 mm
  further back and 10 mm lower. The photographed hand has its knuckles at the front of the grip, beside the rear of
  the trigger guard; the model's are 15 mm behind the grip's front edge, because further forward its middle finger no
  longer closes under the trigger guard (measured: at 12 mm further forward it stays straight). The across-rifle
  direction of the camera is derived, not measured, and the knuckle points are read off an outline, so 20 mm is good
  to about 5. Glove: wipe panel, cuff tab and knuckle panel are present, plainer than R1's.
- **R3, firing hand.** In the photograph the index finger lies within 2.5 degrees of the three wrapped fingers; in
  the model 14.0 degrees, because the model's wrapped fingers turn down round the grip while its index rises 13
  degrees with the hand. The tip sits where R3 has it against the magazine release (by construction). The model's
  magazine grip is lower on the magazine than R3's, and its thumb is on the left side where R3's points up at the
  front; neither was reworked in version 2.
- **R2, support hand.** Same arrangement, now in the same place along the handguard. The model's fingertips stop
  10 to 22 mm lower on the side of the handguard, and its thumb tip 27 mm lower, than R2's thick winter glove.
- Light and materials: plain flat materials under a soft sky light; no fabric texture, print or wear.

## Why the firing grip still differs (the main limit)

A real hand holds a pistol grip with the base of the thumb behind the grip and the web under the receiver's rear.
The model cannot: its palm is 18.7 mm deep from the knuckle joints to the palm's skin and does not compress, and its
index and middle metacarpals are rigid (their joints move 11 and 7 degrees in the hand; omitted). So the palm lies
flat on the grip's right side, and the base of the thumb stays about 28 mm right of the rifle's centre plane and 40 mm
behind the grip's back. Measured consequences:

- the web ends beside the receiver's rear, not under it (CR-1 item 2a);
- the thumb, searched over its whole range (6,000 random poses, the best five polished), ends 26 to 30 mm from the
  point on the selector lever it was sent to, and its glove 10.8 mm from the lever (item 4b). `safety_to_fire`
  and `safety_to_safe` are still a reach toward the lever, not a touch;
- turning the hand so the wrist comes round behind the grip, as in R1, needs 41 to 76 degrees of ulnar deviation
  against a limit of 30 with the shoulder 60 to 100 mm below the bore, stock in or out; only a shoulder level with
  the bore, which is not where a shoulder is, brings it inside 30;
- seated where the fingers close, the index finger is 2 mm short of the magazine release, so the hand slides 9 mm
  forward for the press (grip `fire_reach`).

The next change to make is to the palm itself: let the pads under the knuckles and the thenar pad compress by a
sourced amount, and give the index and middle metacarpals their small flexion, so that the hand can turn round the
grip. That is a new change request.

## Stance (changed in version 2)

| | Version 1 | Version 2 |
|---|---|---|
| Stock | collapsed | extended 75 mm for the arms only (the rifle is drawn and checked collapsed) |
| Right shoulder joint | 45 mm behind the buttpad | the same, so 75 mm further back |
| Torso | turned 15 degrees | turned 30 degrees, so the left shoulder stays where it was within 40 mm |
| Elbow swivel allowed | -10 to 75 degrees | -10 to 100 degrees |
| Elbow swivel chosen | least wrist bend | furthest from any limit |
| Firing wrist | 45 extension, 29 ulnar, 1 degree inside the limit, elbow out 45 | 58 extension, 19 ulnar, 11 degrees inside every limit, elbow out 60 |

Why: with the stock collapsed, a level firing hand flat on the grip's side needs 95 degrees of wrist extension
against a limit of 70. The hand as solved (rising 16 degrees) fits with the stock collapsed too, but with only 0.3
degrees to spare (65 extension, 29.7 ulnar). With the elbow straight down it needs 47 to 56 degrees of ulnar
deviation in either stance; the elbow has to come out.

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
| Finger depths, joint centres across the palm, knuckle arc and arch, palm thickness, section shape | `model/handlib.py` `P` | Shape of the hand between the measured dimensions; the palm's depth decides how the hand seats on the grip. |
| Thumb base position and rest direction; the rest pose is the middle of the thumb's range | `P['thumb_cmc']`, `P['thumb_dir']` | Where the thumb can reach. |
| Where the flat hand sits in the ring and little metacarpals' arcs | 15 % in | Their limits. |
| The thenar crease line and how far the skin follows the thumb | `P['thenar_crease']` | The palm's fold. |
| Crease offset as a share of the proximal phalanx | 0.297 | The finger-length check only. |
| Glove thickness 1.2 mm, cuff 2.6 mm, fingertip allowance 1.5 mm | `P` | Clearances. |
| Stance | table above | Every wrist, forearm and elbow angle, and the forearm's direction in the pictures. |
| Where the firing hand sits on the grip, and its 12 degree rise | `GRIP_PADS`, `spec_fire_indexed` | The firing grip. |
| Thumb of the firing hand (never visible in a reference) | toward the left of the grip | R1-F09. |
| The slide forward for the magazine release | 9 mm | `mag_release`, `mag_out`. |
| All of `bolt_catch`, `charge`, `mag_out`, `mag_in`, selector and release clips | `STUDIES.md` study 6 | No reference shows them. |
| A frame that would cut through the rifle is moved clear | `clips/make.py` `ESCAPE` | Up to 77 mm in `charge`, up to 4 mm for the firing hand. |

## Sources

Read this session: ANSUR II (recomputed from the public file); El-Shennawy 2001, Cooney 1981 and Kawanishi 2018
(abstracts, through the PubMed API); Bain 2015 (abstract); Greiner 1991 (the scanned report's text layer: rough, each
mean checked against its 50th percentile). Still carried over or recalled, not re-read: Buryanov and Kotiuk's phalanx
table, Hsiao's breadths and lengths, the end points of Bain's active range, Hume 1990's thumb ranges, the AAOS wrist
values, Kapandji's figure. Each is marked in `model/handlib.py` `SRC`.

## Omissions

- Rifle clips with no hand clip: `stock_extend`, `stock_collapse`, `sights_up`, `sights_down` (CR-1 item 6).
- Hand against hand interpenetration (CR-1 item 6).
- R1's support hold on the front of the magazine well (R1-S01) is not a grip here.
- The printed pattern and the maker's lettering on R1's glove (on purpose), the edge binding R1-F07, fabric texture.
- Only the 50th-percentile hand is solved against the rifle.
- Skinning is linear blend: joints lose a little volume when bent hard, and the palm's fold is a blend, not a crease.
- The recoil of `assets/hk416/action` is not applied to the hands.
- The support grip's search is a random search: longer runs of it gave worse answers (mean 21 to 31 mm), so the
  committed grip is the one its default settings give, not a proven best.

## For the owner to review

1. The side-by-side pictures in `refs-local/build/compare/` (local; rebuild with `checks/compare.py`) and
   `renders/compare_*.jpg`: is version 2's firing grip an acceptable step, given that the web is not under the tang
   and the thumb does not reach the selector?
2. Whether the next change request should be the compressible palm described above.
3. The stance: stock extended for the arms, elbow out 60 degrees.
4. Whether the selector clips may ship while the thumb falls short, and whether the 9 mm slide for the magazine
   release is acceptable.
5. The glove: R1's knit-backed pattern, plain, in coyote tan, with no lettering (unchanged from version 1).
