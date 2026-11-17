# HK416: AAA first-person hero weapon, built part by part

## What this is
The definitive answer to "what does a computer model of the HK416 look like": a first-person hero weapon of the
quality shipped in AAA shooters, built from a recipe (Blender Python), exported as a GLB. Every part a player can see
is its own named object, placed at real dimensions, down to each pin, screw, rail slot and QD socket. Take the time it
needs. There is no economy target: stop when every check below passes.

The previous attempt (a 72-part three.js blockout) failed because its brief asked for dimensions only and said "be
economical". This brief asks for detail. Do not repeat that result.

## Scope
- Model: HK416 D14.5RS as shown in the profiles (quad-rail handguard, HK adjustable stock with ribbed buttpad, curved
  30-round magazine, folding front and rear sights, HK pistol grip). Use the .22 LR close-ups only for small detail that
  the AR pattern shares (pins, selector, dust cover, sights, charging handle). Where they differ, the profiles win.
- Model everything a player sees in first person and third person, including during reload, charging, inspect and
  ADS animations. That includes the bolt carrier's outer face where it shows through the ejection port.
- Do not model what no player ever sees: fire-control internals, springs, gas-system internals, the chamber and bore.
  The receiver interior behind the ejection port and magazine well is a dark cavity. This keeps the triangle budget
  on visible detail, as AAA weapon artists do.
- No markings with maker names or logos (HK, Heckler & Koch, Walther, Umarex). Selector pictograms and rail slot
  numbers are fine. No orange anywhere.

## References (in refs/, read every one)
- `profile-right-photo.png`: right side, muzzle right, studio photo. Primary silhouette for the right side.
- `profile-both-sides-drawing.jpg`: a two-sided drawing (left side top, right side bottom). Secondary for both sides.
- `profile-left-photo-416N.jpg`: left side photo of an HK416N (longer barrel, optic and vertical grip fitted; ignore
  those accessories). Use it for left-side controls and the stock.
- `closeup-right-receiver.jpg`, `closeup-left-lower-controls.jpg`, `closeup-front-sight.jpg`,
  `closeup-rear-sight-charging-handle.jpg`, `closeup-handguard-front.jpg`: close-ups of the .22 LR replica.
Write `refs/README.md` listing each file's source: the right profile was supplied by carpetshark; the drawing and HK416N
photo are from Wikimedia Commons (Category: Heckler & Koch HK416); the close-ups are from lynxdefense.com's HK416 .22 LR
review.

## Scale
- Barrel length 14.5 in (the "14.5" in D14.5RS).
- Picatinny rail (MIL-STD-1913): slot pitch 0.394 in (10.0 mm). Count rail slots in the profiles and use them as a
  ruler for everything else. Cross-check against the barrel length and report any disagreement.
- Record every measurement you took from the images, its source image and pixel span, in NOTES.md.

## Method (in this order)
1. **Detail inventory before any modelling.** Go through every reference, region by region (muzzle device, barrel,
   front sight, handguard, upper receiver, rear sight, charging handle, lower receiver, controls, grip, trigger guard,
   magazine well, magazine, buffer tube, stock, buttpad, sling points), and list every visible feature: each pin, screw
   head, QD socket, rail slot, rail cover, vent, rib, groove, chamfer, detent, pictogram, seam and parting line. Write
   it to `inventory.json` (`region`, `feature`, `seen_in`, `part_name`). Expect 250 to 400 features. Every one becomes
   a named object or an explicit, justified merge into one.
2. **Build** `build.py`, run as `blender -b --python build.py`, rebuilding everything from nothing. Shape numbers in a
   dict at the top. Real bevels on every machined edge (bevel modifiers, applied on export), weighted normals, no
   visible faceting on round parts at first-person distance.
3. **Hierarchy and pivots.** `HK416` root, then `upper`, `lower`, `handguard`, `barrel_assembly`, `stock`, `grip`,
   `magazine`, `sights`, `controls`, `fasteners`. Every moving part has its origin on its real hinge or slide axis.
   Empties for game sockets: `socket_optic` (rail top centre), `socket_muzzle`, `socket_magazine`, `socket_hand_right`,
   `socket_hand_left`, `socket_ads_eye`, `socket_eject`.
4. **Materials and textures.** PBR metal/roughness. Hard-anodized black aluminium (receivers, handguard), black glass-filled
   polymer (grip, stock, magazine), manganese-phosphate steel (barrel, muzzle device, pins), with subtle edge wear,
   handling polish on contact areas and fine surface grain. Build them as procedural Blender materials, then bake
   base colour, roughness, metallic, normal and ambient occlusion (Cycles CPU) to 2048 px texture sets (one set per
   material group is fine) packed into the GLB. Grip and buttpad texturing comes through the normal map.
5. **Animations** as separate glTF clips, 24 fps: `charge` (charging handle back and forward, bolt carrier face moving
   in the port), `mag_out`, `mag_in`, `mag_release`, `dust_cover_open`, `bolt_catch`, `safety_to_fire`, `safety_to_safe`,
   `trigger_pull`, `stock_extend` and `stock_collapse` (each stock position), `sights_up` and `sights_down`.
6. **Budgets.** LOD0 (first person) 80k to 150k triangles. Also export LOD1 at about 25 percent of that for third
   person. Report the per-region triangle counts.

## Checks you must run and pass (no human will catch it for you)
- **Inventory coverage:** every inventory feature maps to an existing object. 100 percent, with the list of any merges.
- **Silhouettes:** render orthographic right and left views at each reference's scale and framing, threshold the
  reference silhouettes, and compute intersection over union. Target 0.92 or better on `profile-right-photo.png` and
  on both sides of the drawing. Then list the five largest mismatch regions and fix them, round after round.
- **Close-up review:** for each close-up, render your model from the same viewpoint and compare region by region. Write
  the differences in NOTES.md and fix them.
- **Assembly:** no floating objects. Every object touches or overlaps a neighbour. Fasteners sit flush in their holes.
- **Animation:** each clip runs to both ends with no interpenetration beyond 0.2 mm.
- **Export:** the GLB reloads cleanly (re-import it in Blender, compare object and material counts), all textures are
  embedded, and the scale is right (measure the barrel in the re-imported file).
- **Presentation renders:** right, left, top, front, three-quarter, a first-person view from `socket_ads_eye`, and an
  exploded view. Save them in `r/`.
- Run at least five review rounds, and keep going while any target is missed. Record each round in `notes.json`
  (format: `rounds` with the change made and the scores).

## Deliverables (in this folder, nothing anywhere else)
`build.py`, `hk416.glb` (LOD0), `hk416_lod1.glb`, `inventory.json`, `notes.json`, `NOTES.md`, `refs/README.md`,
`r/` renders, and `viewer.html`: a page (no doctype, html, head or body tags; a `<title>`; three@0.160.0 from
cdn.jsdelivr.net via an importmap with GLTFLoader and OrbitControls) that loads `./hk416.glb`, with a turntable, a
button for each animation clip, an exploded view, a clickable part list grouped by region, and the check results.

Do not commit, push or publish. Report back: the part count, the triangle counts, the IoU per round, every check
result, and what still differs from the references.
