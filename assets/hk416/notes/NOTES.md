# HK416: modelling notes

## Version 2 (2026-11-18): rebuilt from Heckler & Koch's documents

**Change request** (carpetshark, 2026-11-18): every build must be built from real documentation such as manuals and
technical drawings, not photos. The 2026-11-18 source audit found that version 1 was traced from one studio photo.
Version 2 replaces every outline and position with numbers measured on HK's own dimensioned drawing (HKTD p. 12),
with hidden faces and part breakdown from HK's maintenance manual (HKMM Fig. 1a). Sources: [REFERENCES.md](REFERENCES.md).
Version 1's notes stay in [v1-photo/](v1-photo/).

**Variant.** HK416 (HK GmbH configuration) with the 14.5 in barrel by default: quad-rail handguard with the four
lightening vents per face, folding front sight on the gas block, HK drum diopter rear sight, HK adjustable stock,
curved steel magazine. `--barrel 10|11|14.5|16.5|20` sets the barrel from HK's tables. The HK416 A5 (different lower
receiver and stock) is not modelled: HK's documents give its dimensions but no drawing.

**Fit.** Built with `--barrel 16.5`, the model overlays HKTD's side and top views line for line
(`model/tools/fit_drawing.py`, images `renders/fit_left.jpg` and `renders/fit_top.jpg`). The process:

1. Calibrate the drawing (3.682 mm per PDF point from HKTD's A and C; D and E agree within 1 %).
2. Trace the closed outlines (magazine, ribs, pistol grip, grip panel) and read every other edge as a number.
3. Write the recipe from those numbers; build fast; render orthographic left and top views; overlay the drawing.
4. Fix what doesn't sit on the lines. Round 1 found the brass deflector 5 mm short (apex S 26.7 vs 31.8), the forward
   assist cap 10 mm forward of the drawing, and the rear sight's base, drum and ears misread; all fixed in round 2.

**Measured against version 1.** Version 1's widths were guesses: stock 38 mm wide (HKTD: 58), buttplate 42 mm (HKTD
B = 78), magazine well 28 mm (HKTD top view: 36, with a 38 mm flare), lower receiver 22.6 mm (HKTD: 30.4). Its rear
sight was a generic AR flip-up; HKTD shows HK's drum diopter with protective ears.

**What is inferred.** The ejection port and dust cover size (AR-15 pattern), the pistol grip's width, and the
position of the full-auto pictogram, which the selector hub hides in the drawing. Each is marked INFERRED in `build.py`.

**Tools.** `model/tools/fit_drawing.py` is the version 2 check. The version 1 tools that score against the photo
(`score.py`, `make_notes.py`, `closeups.json`) are kept for history and no longer apply.
