# G44 V: detail pass (v2), source-indexed

Owner review of v1: "g44 is missing some details". This is the second inventory of what the references show against what
the model had, feature by feature, and what was done about each. Sources: **D** the maker's dimension image (left side and
rear view; pixels in `model/outlines.json` coordinates); **R** manual p. 8 picture 1 (right side); **T** manual p. 23
picture 27 (slide from above); **U** manual p. 27 picture 30 (slide from below); **X** exploded drawing p. 37; **L** manual
p. 21 picture 18 (locked open). v1 renders are kept in `renders/v1/` for the before and after.

## Added or corrected

| # | Feature (source) | v1 | v2 |
|---|---|---|---|
| 1 | Trigger guard width (R, D rear view: the guard is far narrower than the grip) | full frame width, 29 mm | 16 mm wide loop with a stepped blend into the frame |
| 2 | Dust cover stepped in ahead of the angled shoulder at px 480-500 (D) | flush with the frame | 0.9 mm step each side; rail groove deepened to match |
| 3 | Rail cross slot (D px 196-214) | at L 158.5-162 (guessed) | at L 163.0-166.1 (measured) |
| 4 | Thumb rests (R: lighter dished area behind the trigger, both sides) | none | shallow spherical dish each side, 16 mm across, 0.8 mm deep (size inferred) |
| 5 | Grip texture over the whole grip (D, R, rear view) | side patch from a hand-drawn outline | side panels bounded by the straps (3.5 mm inside the front strap, the seam at the back, Z -93 to a top edge falling toward the front); studs on the front strap and the back strap, nine across |
| 6 | Backstrap seam (D, R: line parallel to the back strap) | none | 0.6 mm groove 5 mm inside the back strap, both sides |
| 7 | Pins and their heads (D px (682, 350) and (1047, 440)) | pins 0.2-0.3 mm under a flat surface | each head sits in a shallow counterbore; trigger pin dark as in D |
| 8 | Slide lock, the take-down lever (D px 600-632, 310-360; R) | a square ribbed pad with its spring showing below | a thin bar leaning 29 degrees, top toward the muzzle, in a recess that gives it room to be pulled down; spring moved inside |
| 9 | Slide stop lever pads (D px 815-870; R) | plain blocks, bright steel | three ribs on each pad, dark finish |
| 10 | Magazine catch (D px 800-880, 455-515; R shows the far end in its window) | plain pad; its cross bar showed in a slot ahead of the pad | seven vertical ribs; the bar moved 3 mm rearward under the pad, where D shows it must be (and the magazine with it) |
| 11 | Magazine width (X; the maker's tubes are 22 mm) | 19.2 mm all the way | 22 mm body with a 19.2 mm neck above Z -24; magazine well widened to suit |
| 12 | Magazine count windows (X: 5, 10, 15 on the right rear) | none | three windows through the right wall |
| 13 | Floor plate and insert (X items 34, 35) | plate only | insert button showing through the floor plate |
| 14 | Follower buttons, the loading assists (X items 48, 49; p. 11) | plain discs | cross grip cut in each |
| 15 | Recoil spring's two diameters (X item 3) | one diameter | small-diameter section at the flange end, larger toward the muzzle |
| 16 | Muzzle crown (L, D) | flat end | recessed crown |
| 17 | Extractor (R: bar L 57-76, Z -0.2 to 4.3 behind the port) | hidden inside the slide wall, wrong height | flush bar of the measured size in its own pocket, claw at the breech face |
| 18 | Ejection port lower edge (R) | square edge | relief chamfer along the lower edge |
| 19 | Rear sight (T: about 13 mm wide; set includes its screwdriver) | 17 mm wide block on a flat top | 13 mm wide, on a dovetail base across the slide, windage and elevation screw heads |
| 20 | Front sight seat (T, X) | sat on the slide top | seated 0.5 mm into the slide |
| 21 | Serrations, front six and rear seven (D, R) | 0.6 mm deep | 0.8 mm deep; count, pitch and extent already measured in v1 |
| 22 | Markings (D, R) | left grip panel mirrored to the right | right grip: the wide two-line plate R shows; model mark on the left dust cover; all plain placeholder panels |
| 23 | Locking block finish | bright steel, glaring through the guard | dark |

## Merged or left out, with the reason

| Feature (source) | Decision |
|---|---|
| Trigger guard undercut (D) | Already in the traced frame outline; v2 adds only the guard's width. |
| Finger-groove-free front strap (D) | Already so: the traced strap is straight. |
| Frame side contours beyond the thumb rests: the swell of the grip, the flare at the magazine well (D rear view: 29.0 mm at the top, 29.8 mm at the grip) | Merged into the 3.2 mm edge rounding. The recipe extrudes the traced side outline; a 0.4 mm swell per side was not judged worth a second surface. |
| Studs wrapping from the back strap onto the sides behind the seam (D) | Left out: they would sit on the rounded edge, where a flat stud floats off the surface. The back strap's own studs stand in for them. |
| Ribs on the slide lock's finger tabs (D) | Left out: sub-millimetre ribs on a 2.2 mm bar. |
| The necks joining the slide lock's tabs to its plate through the frame walls | Left out, so the walls need no slot that light would pass through. Stated on the part. |
| Fence under the slide stop lever (D px 795-895, 328-345) | Merged into the lever's own lower edge seen in its window; a separate ledge collided with the lever's travel. |
| Round recess low in the back strap (D rear view) | Left out: every cutter tried there left the frame mesh open. Recorded in `build.py`. |
| Serial numbers and proof marks on the slide rail strip, barrel hood and frame (R, p. 8) | Not modelled: they are markings, not shape. |
| Slide underside detail (U: moulded block and rib) | Unchanged from v1: not visible on the assembled pistol. |
| Ejection port outline (T, R) | Extent was already measured (L 73-105, open to the right, 7.7 mm of roof left on the left); v2 adds the lower relief only. |
| Loaded chamber indicator and barrel hood (T, p. 8) | Notch and recessed hood were in v1; unchanged apart from the placeholder panel. |
| White dot and outline on the sights (T, D rear view) | In v1; kept. |

## Matched comparisons, before and after

Both versions were rendered through the same cameras and the same ray-traced lighting (a hard sun from above, as in the
maker's photographs), so the numbers compare like with like. `model/compare.json` has them all.

| View (reference) | Measure | v1 | v2 |
|---|---|---|---|
| Whole left side (D) | silhouette IoU | 0.9877 | 0.9867 |
| Whole left side (D) | reference outline to model outline, mean / p95 / worst | 0.15 / 0.35 / 1.38 mm | 0.17 / 0.38 / 1.38 mm |
| Slide close-up (D px 140-1170, 130-300) | IoU; interior edge coverage; precision | 0.976; 0.383; 0.804 | 0.976; 0.393; 0.812 |
| Grip close-up (D px 840-1240, 430-890) | IoU; coverage; precision | 0.992; 0.682; 0.802 | 0.990; 0.669; 0.796 |
| Controls close-up (D px 560-900, 280-530) | IoU; coverage; precision | 0.967; 0.183; 0.826 | 0.971; 0.316; 0.857 |
| Slide from above (T) | IoU; coverage; precision | 0.921; 0.298; 0.649 | 0.921; 0.307; 0.646 |

Edge coverage is the share of the photograph's interior edges (Canny, after contrast equalisation) that have a model edge
within 0.6 mm; precision is the reverse. What the numbers say, plainly:

- **Controls improved** (coverage 0.18 to 0.32): the slide lock, the ribs and the catch now put edges where the photograph has them.
- **Slide and grip are unchanged within noise.** The grip's side studs were already in v1 and dominate that region's edges; the new strap studs and the guard's width do not show in a square-on left view. The whole-silhouette numbers moved by 0.001 because the strap studs stand 0.45 mm outside the traced outline.
- **The top view's 0.92** is limited by the photograph, not the model: it is a hand-held product shot with perspective, not a true plan.
- Most of v2 is visible only off-axis, where there is no matched reference camera: compare `renders/v1/` with `renders/` (`three_quarter`, `right_three_quarter`, `rear_three_quarter`, `closeup_*`, `magazine`).

Clip interpenetration after the pass: 0 pairs, rest pose and all 8 clips.
