# Checks

| Command (from `assets/hands-gloved/`) | Writes | Needs |
|---|---|---|
| `python3 checks/proportions.py` | `proportions.json` | numpy |
| `python3 checks/limits.py` | `limits.json`, `fk_reference.json` | the frames from `clips/make.py` |
| `node checks/test_runtime.js` | (prints) | `hands-gloved.json`, `fk_reference.json` |
| `python3 checks/contact.py` | `contact.json` | the frames, the local rifle build |
| `python3 checks/penetration.py` | `penetration.json` (interpenetration, soft-pad compression, hand against hand) | the local rifle build, Blender (BVH tree only); about 10 minutes |
| `python3 checks/selector_reach.py` | `selector_reach.json` | the solved grips, the local rifle build; about 2 minutes |
| `python3 checks/selector_scan.py` | `selector_scan.json` | the solved grips, the local rifle build; about 25 minutes on four cores |
| `python3 checks/selector_move.py` | `selector_move.json` | the frames, the local rifle build, and `limits.json` and `penetration.json` from the two checks above |
| `python3 checks/compare.py` | `comparison.json`, `../renders/compare_*.jpg`, `../renders/first_person_*.jpg` | the photographs in `refs-local/`, Blender |

Results and what they do and do not show are in `../notes/NOTES.md`.

- **Proportions.** Rows marked `by construction` or `fitted` only show the recipe built what it was given. The
  independent rows are the finger lengths against two surveys (Hsiao 2015, Greiner 1991). Version 1 failed its
  little-finger row because it took the finger's base crease to lie the same distance beyond every knuckle; version 2
  takes it as a share of the proximal phalanx (an inference, explained in `proportions.py`) and keeps the old rows as
  `reported`.
- **Contact.** For each clip in which a digit works a control: the smallest distance from that digit's glove to the
  control's exact triangles, per frame. At most 1.0 mm counts as touching. It does not say the digit is on the right
  part of the control, only that it touches it; read it with the clip's target error in `hands-gloved.json`.
- **Limits.** The limits are in `model/handlib.py` `LIMITS` with their sources. Arm angles depend on an assumed
  shoulder.
- **Interpenetration.** `tools/bvh_check.py` tests glove vertices, sampled intersecting triangles and rifle vertices
  against the exact triangles of the rifle built from `assets/hk416/model/build.py`. Tolerance 1.0 mm. Twenty-two of
  the rifle's 301 parts are not watertight; a point counts as inside on four of six rays. Depth is per rifle part.
  Hand against hand is tested since version 3 (below).
- **Soft pads (version 3).** The glove is measured with each palm pad pressed in by what the frame carries, and that
  measurement is the interpenetration: one tolerance, 1.0 mm, everywhere, pads included. Compression is reported apart
  from it under `soft_pads`: `commanded` (what the frames carry, against each pad's limit), `overlap_uncompressed` (how
  deep the pad would sit in the rifle with no compression, measured the same way) and `beyond_limit` (overlap that the
  pad's limit could not take up; it must stay inside the tolerance). The limits and where they come from are in
  `model/handlib.py` (`pad_table`, `SRC['SP']`). `limits.py` checks the four compressions like the angles. Before
  version 3 nothing was allowed to compress; the version 2 result (0.57 mm at worst) is in this file's history.
- **Hand against hand (version 3).** Frames in which the two gloves' boxes come within 2 mm are measured: the deepest
  vertex of either glove inside a closed shell of the other. A glove is not tested against itself.
- **Selector reach (version 3).** The thumb's whole range from the firing grip, then again after 700 random small
  moves of the hand, for the smallest distance from the thumb's glove to the lever; and the geometry behind the answer.
- **Selector scan (version 4).** How far the hand has to leave the firing grip for the thumb to reach the lever at both
  ends of its travel: 24,000 hand poses, each kept only if the arm fits it and the palm and trigger finger are clear,
  each kept pose tried with 3,000 thumb poses. Coarse on purpose (it ranks poses; the solver polishes one). It also
  records at which elbow swivels the arm fits each pose, which is what shows that the reaching poses need the elbow
  under the rifle.
- **Selector move (version 4).** The two safety clips against CR-3's conditions, frame by frame: the thumb's glove to
  the lever's exact triangles through the lever's stroke (at most 1.0 mm), glove vertices inside the trigger guard's
  window (none allowed for the trigger finger; `trigger_pull` is measured the same way to show the test sees a finger
  that is there), the hand back exactly on the firing grip, and the size of the move (wrist, turn, palm landmarks,
  elbow). Interpenetration and joint limits are read from `penetration.json` and `limits.json`, so run those first. It
  measures where the glove is, not force: it does not show that the thumb could push the lever.
- **Sleeve.** `comparison.json` gives, for each matched view and two first-person views, the share of each hand's
  glove whose line of sight to the camera is cut by a sleeve (`hand_hidden_by_a_sleeve`).
- **Comparison.** Photo coordinates were read by eye from gridded crops, good to about 15 px. R2: scale from the
  handguard's height. R1: a scaled orthographic camera fitted to five points on the receiver's right side; the
  across-rifle direction is derived, not measured. R3: no ruler (the rifle is wrapped), so angles and distances in
  finger breadths only. It is not a fidelity score.
