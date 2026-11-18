# Checks

| Command (from `assets/hands-gloved/`) | Writes | Needs |
|---|---|---|
| `python3 checks/proportions.py` | `proportions.json` | numpy |
| `python3 checks/limits.py` | `limits.json`, `fk_reference.json` | the frames from `clips/make.py` |
| `node checks/test_runtime.js` | (prints) | `hands-gloved.json`, `fk_reference.json` |
| `python3 checks/contact.py` | `contact.json` | the frames, the local rifle build |
| `python3 checks/penetration.py` | `penetration.json` | the local rifle build, Blender (BVH tree only); about 10 minutes |
| `python3 checks/compare.py` | `comparison.json`, `../renders/compare_*.jpg` | the photographs in `refs-local/`, Blender |

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
  Hand against hand is not tested.
- **Comparison.** Photo coordinates were read by eye from gridded crops, good to about 15 px. R2: scale from the
  handguard's height. R1: a scaled orthographic camera fitted to five points on the receiver's right side; the
  across-rifle direction is derived, not measured. R3: no ruler (the rifle is wrapped), so angles and distances in
  finger breadths only. It is not a fidelity score.
