# G44 V: build notes

Read with `DECOMPOSITION.md` (every object, number and socket with its source), `MANUAL_NOTES.md` and `REFERENCES.md`.

## The reference-to-3D lineage

| Stage | What it is here | Where |
|---|---|---|
| Chosen references | The instructions for use (edition 03-26), named in the build brief, above all its component list and exploded drawing (pp. 36-37); and the maker's dimension image of this model, which is the page the manual's p. 9 sends the reader to for specifications. No other pistol was used as a stand-in. | `REFERENCES.md` |
| Source-indexed decomposition | One row per object: manual item number, source picture and pixel region, status (traced, measured, published, inferred), pivot, extent. | `DECOMPOSITION.md`, `model/inventory.json` |
| Object studies | Square-on pictures measured with their own rulers: dimension image (5.785 px/mm), slide underside p. 27 (20.7 px/mm), slide top and side p. 23 (3.49 px/mm), lock-open p. 21 (2.78 px/mm), rear view (5.647 px/mm from the 25.5 mm slide width). Outlines traced by `model/tools/trace_ref.py` and `outline.py`. | `model/outlines.json`, the `P` table in `model/build.py` |
| Derived grammar | Below. | this file |
| Procedural reconstruction | `model/build.py`: every object from numbers, nothing sculpted or imported. | `model/build.py` |
| Matched visual comparison | Render through the reference's camera (orthographic, same scale and frame), silhouettes compared by area, outline distance and a 6 x 4 grid; then read by eye against the photograph. | `model/compare.json`, `renders/compare_outline.png`, `model/work/compare_overlay.png` (local, contains the photograph) |
| Owner review | **Not done.** Nothing here has been seen or approved by the owner. | |

## Grammar: how the pistol is put together in the recipe

- **Three bodies.** Frame group (frame, barrel, recoil spring assembly, fire control), slide group, magazine group. The barrel belongs to the frame because this is a straight blowback: in the lock-open picture the barrel stays put while the slide is back.
- **Side outline times width.** Frame, slide, trigger, sights and floor plate are their traced side outlines extruded to a measured width, then cut. The slide is its cross-section (flat sides, 3.3 mm top chamfers) intersected with its traced profile, which gives the nose its shape.
- **Everything hangs off measured stations along the bore.** Slide rear face L = 0; firing pin lug slot L 3 to 25 and firing pin safety L 66 (underside picture); breech face L 73 (underside picture, and muzzle minus the published barrel length); ejection port L 73 to 105 (top view); slide stop notch L 93 to 106 and slide lock L 89.5 to 96 (dimension image); trigger pin L 82.2, Z -19.4; nose L 173.6; muzzle L 174.3.
- **Rails.** Four steel guides on the frame run in grooves cut the full length of the slide's inner walls.
- **Lock-open is geometry, not a keyframe.** The stop's nose sits 42.0 mm behind the rear face of the slide's notch, the travel measured from the lock-open picture. The follower's shelf lifts the lever; the lever's nose rises into the notch only between 42 and 52 mm of travel.
- **Firing pin.** The lug hangs below the slide's underside and is held by a tab on the trigger bar: part-cocked 7.5 mm behind its fired position with the trigger forward, drawn further by the bar and released when the bar drops. On a hand cycle the returning lug stops on the tab by itself.
- **Take-down is geometry too.** The slide lock is a plate standing in front of the barrel lug; pulled down 3.5 mm it clears the lug and slide, barrel and spring run forward together. The barrel then goes 10 mm forward, tilts 13 degrees about the nose hole and draws out along its own axis.
- **Magazine.** Raked 21.8 degrees, the slope of the traced front strap; catch notches at both front corners; loading assists fixed to the follower through side slots.
- **Symmetry.** Pads of the slide stop lever and slide lock on both sides (rear view); magazine catch button on the left (reversible).

## What the comparison showed, and what was done

- Nose: the first build's slide stood proud at the top and bottom front corners and the frame's dust cover was 1.9 mm short. Cause: a constant-section slide, and a frame outline cropped at pixel 168 in the old tracing. Fixed: slide intersected with its traced profile; frame front restored from the outer outline.
- Trigger: the model's safety blade stood 2.2 mm outside the photograph's trigger. Cause: the traced trigger outline already includes the blade. Fixed: the blade is the traced face and the trigger face is recessed 2 mm behind it.
- Muzzle: 0.7 mm too far forward. Fixed from the dimension image (L 174.3).
- Remaining silhouette differences after the fixes: mean 0.15 mm, worst 1.4 mm (slide stop pad and magazine floor plate, whose front lip is 1.2 mm short).
- By eye, inside the outline, the model still differs from the photograph in the ways listed under omissions. These are not measured by the silhouette numbers.

## Consequential inferences

1. **Specification table.** The manual has none (p. 9 is a pointer). The maker's page for this model is used and dated.
2. **Rear sight** is taken to be the adjustable polymer one: the dimension line measures 157.6 mm against 158 published for that sight, and the set includes its screwdriver (p. 10).
3. **Bore axis** 11.75 mm below the slide top, from the muzzle's position in the dimension image. Not published.
4. **Slide travel** 45 mm: 42 mm to lock-open is measured; the 3 mm over-travel is a guess.
5. **Internals.** 24 of 60 objects are marked inferred (shape, and partly position), and several marked measured have only their position measured: firing pin body, spacer sleeve, springs, cups, extractor, depressor plunger and bearing, locking block, trigger mechanism housing and ejector, connector, trigger bar, the arms of the slide stop lever, magazine catch bar, magazine tube walls, insert. The exploded drawing is too small to measure; these parts are built from where they must sit and what they must do, with clearances.
6. **Firing pin strikes the rim at 12 o'clock**, axis 2.6 mm above the bore. Not visible in any picture.
7. **Recoil spring assembly** is drawn as a two-diameter captive assembly in the exploded drawing; here (v2) it is one rod and one spring with a small-diameter and a large-diameter section, 24 coils in all so that its solid length fits the stroke.
8. **Magazine tube** (v2) is 22 mm wide with a 19.2 mm neck above Z -24 so that the trigger bar and slide stop arms pass beside it, 31 mm deep, and sits 7.5 mm behind the front strap so the catch bar is hidden under its pad as the photograph shows. Width, neck and depth are inferred. Follower travel 78 mm from the count windows in the exploded drawing.
9. **Frame walls** 2.7 mm, hollow backstrap, cavity shapes: inferred.
10. **Trigger travel** 7.5 degrees (blade tip 3.9 mm), the most the traced outlines allow. Real travel is not published and is probably longer.
11. **Muzzle hole** has 0.8 mm radial clearance so the barrel can tilt out; the real fit is not known.
12. **Masses.** Volumes times nominal densities give 429 g against the published 358 g; scaled to 358 g the split is slide 105 g, barrel and spring 121 g, frame group 133 g (v2; 449 g raw became 429 g). The model magazine is 32 g against 57 g published. The action simulation uses the scaled slide mass and the published totals.
13. **Eye socket** 450 mm behind the rear sight (arm's length).

## Omissions and simplifications

- No maker's names, logos, model text, proof marks or serial numbers: plain panels on the slide (two), barrel hood, grip (both sides) and magazine. The small model mark on the frame above the trigger is left out.
- Frame: an extrusion of the traced outline with 3.2 mm rounded edges, to which v2 adds the narrow trigger guard, stepped dust cover, thumb rests, seam, strap texture and counterbored pins (`DETAIL_PASS_V2.md`). Still missing: the grip's slight swell and the flared magazine well, the rail's exact slot profile, the small nose that latches the backstraps, the recess low in the back strap.
- Slide: the detail of the underside (a moulded block and rib seen on p. 27). The rear sight's dovetail and screws were added in v2.
- Loaded chamber indicator: a plain notch in the hood.
- The slide lock's finger tabs are not joined to its plate through the walls (v2), and the plate stands up to 1.6 mm ahead of the barrel lug it blocks.
- The right-hand slide stop pad is 1.9 mm deeper than the left so its arm clears the trigger bar in this layout.
- No cartridges; the magazine is always empty. No trigger spring (the manual's list has no separate item for one).
- The firing pin safety does not geometrically block the firing pin; it is animated to the manual's description.
- One level of detail, flat PBR materials, no UVs or textures.
- Backstraps are constructed (the traced rear strap grown by 2 and 4 mm with a beavertail), not traced, and shown detached.

## Corrections to the old partial work

- The old tracing's frame polygon was cropped at the front; restored (above).
- The old tools read references from `model/refs-local`; they now read `assets/g44v/refs-local`.
- Height: the traced model is 125.7 mm against 128 mm published (-1.8 %), and trigger distance 68.7 against 70 mm. The dimension image's vertical scale appears to be about 1 % smaller than its horizontal scale; the outlines were not rescaled to hide this.

## Change log (rule 7)

| Version | Date | Change |
|---|---|---|
| sound v2 | 2026-11-17 | Change request (owner: the sounds "are clicks", "like a click on a keyboard or a crackle"). Sound model only; geometry, action and ballistics untouched. Level recalibrated to a published .22 pistol at the ear (+5 dB); blast shortened to the published A-duration with a blow-down negative phase; jet noise, eight timed mechanical events on modes from the model's dimensions, rail friction, a filtered ground reflection and ground scatter added; the playback compressor, measured to turn the shot down 12.5 dB, replaced by a level mapping. Numbers in `sound/compare/before_after.json` and `sound/README.md`. Not validated by listening. |
| v2 | 2026-11-17 | Change request (owner review of v1: "g44 is missing some details"). Detail pass: 23 features added or corrected, 13 merged or left out with reasons, all listed in `DETAIL_PASS_V2.md`. Magazine widened to 22 mm with a neck and moved 3 mm rearward; slide lock redrawn; close-up matched comparisons added. Slide mass share moved from 101 to 105 g, so the action tables were regenerated. v1 renders kept in `renders/v1/`. |
| v1 | 2026-11-17 | First build in openFPS: recipe, clips, sockets, checks; action, ballistics and sound simulations with their JS runtimes; sample page. Carries over the outlines and tracing tools of the paused private build. |
