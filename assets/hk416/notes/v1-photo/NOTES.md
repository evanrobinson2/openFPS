# HK416 D14.5RS: modelling notes

Result: 301 named parts, 85,784 triangles at LOD0 and 20,802 at LOD1 (24 percent). Right-photo silhouette IoU 0.968. Drawing IoU 0.831 (right) and 0.821 (left), below the 0.92 target for a reason set out under Scale.

## Scale: the ruler and where the references disagree

- **Ruler.** In `profile-right-photo.png` the top rail lugs repeat every 8.97 px (287 px over 32 pitches). At the MIL-STD-1913 pitch of 10.0 mm that is 0.897 px/mm. Every traced outline in `build.py` is written in that photo's pixels and converted with this one number.
- **Cross-check against the barrel.** The model's barrel is exactly 14.5 in (368.3 mm), with its breech 5 mm inside the receiver face (x = 367.5) and its muzzle 8 mm inside the flash hider (x = 697.9). The photo shows the flash hider tip at x = 729 and the receiver face at x = 372, so a 14.5 in barrel fits with the breech between 0 and 12 mm inside the receiver. Agreement within about 10 mm (3 percent): the photo cannot say where the breech is. The overall length by the ruler is 804 mm, which matches the commonly published 804 mm for the D14.5RS with the stock collapsed.
- **Disagreement 1: the handguard.** By the ruler the photo's handguard is 228.5 mm (9.0 in) with 19 lugs per rail. I had no independent source for the service rail length, so I could not confirm that 9.0 in is right for a D14.5RS. The photo is the primary reference, so the model follows it.
- **Disagreement 2: the drawing is a different rifle at a different scale.** Its rail lugs repeat every 6.0 px, but fitting the model gives 0.8698 px/mm, so the drawn pitch is about 6.9 mm: the drawing's rail is not to MIL-STD scale and cannot be used as a ruler. It also shows a short barrel (0.41 receiver lengths ahead of the handguard against 0.85 in the photo) and a relatively longer handguard.
- **What that does to the silhouette target.** The photo's own silhouette, fitted onto the drawing the same way the model is, scores IoU 0.841 (right side) and 0.830 (left side). Jaccard distance (1 - IoU) obeys the triangle inequality, so a shape that scores 0.92 or better against the photo cannot score above 0.910 against the drawing's left side or 0.921 against its right. The target of 0.92 on all three cannot be met by one model. The model follows the photo (the brief's primary) and scores 0.831 and 0.821 on the drawing, about what the photo itself scores.

## Measurements taken from the images

| What | Image | Pixel span | Result |
|---|---|---|---|
| Rail pitch (the ruler) | profile-right-photo.png | top rail lug leading edges x = 272 to 559 at y = 36: 287 px over 32 pitches | 8.97 px per 10.0 mm, so 0.897 px/mm (1.115 mm/px) |
| Bore axis | profile-right-photo.png | barrel edges y = 61 to 77 at x = 640 to 685 | centre y = 69.0 (Z = 0) |
| Upper receiver front face (L = 0) | profile-right-photo.png | x = 372 (handguard joint) | origin of L |
| Overall length, stock collapsed | profile-right-photo.png | x = 8 to 729 (721 px) | 804 mm (the commonly published figure for the D14.5RS with the stock collapsed is 804 mm) |
| Barrel, visible part | profile-right-photo.png | gas block front x = 593 to flash hider base x = 690.5 | 108.7 mm exposed; diameter 16 px = 17.8 mm |
| Barrel neck | profile-right-photo.png | x = 614 to 636, y = 63 to 76 | 24.5 mm long, 14.5 mm diameter |
| Flash hider | profile-right-photo.png | x = 690.5 to 729, y = 60 to 79 | 42.9 mm long, 21.2 mm diameter |
| Handguard length | profile-right-photo.png | x = 372 to 577 | 228.5 mm (9.0 in) |
| Handguard height over the rails | profile-right-photo.png | y = 36 to 97 | 68.0 mm; slot depth 3.2 px = 3.6 mm |
| Top rail lugs | profile-right-photo.png | receiver: 10 lugs from x = 272; handguard: 19 lugs from x = 388.5 to 553 | 10 + 19 lugs at 10.0 mm pitch; bottom and side rails 19 each |
| Handguard vents | profile-right-photo.png | x = 419-434.5, 449.5-478.5, 493.5-522.5, 530.5-543.5 at y = 58 and y = 80 | 4 vents per row: 17, 32, 32, 14 mm long |
| Front sight | profile-right-photo.png | x = 581 to 588, top y = 6 | arm 7.8 mm thick, tip 70.2 mm above the bore |
| Rear sight | profile-right-photo.png | x = 236 to 269, y = 7 to 40 | base 36.8 mm long, top 69.1 mm above the bore |
| Upper receiver | profile-right-photo.png | x = 201 to 372 | 190.6 mm long |
| Ejection port and dust cover | profile-right-photo.png | cover x = 292 to 356, y = 58 to 75 | cover about 71 x 19 mm; the port behind it is modelled 65 x 16 mm |
| Magazine well | profile-right-photo.png | x = 298 to 361, flare bottom y = 141.5 | magazine opening 62.4 mm long (x = 302 to 358) |
| Magazine | profile-right-photo.png | rear edge (302,141) to (325,247.5); front edge (358,141) to (377.5,225.5) | 119 mm below the well, curved; 62 mm wide in side view |
| Trigger guard opening | profile-right-photo.png | x = 255 to 297, y = 113 to 137 | 47 x 27 mm |
| Pistol grip | profile-right-photo.png | x = 179 to 263, y = 112 to 207.6 | 107 mm tall, backstrap raked about 25 degrees |
| Stock, collapsed | profile-right-photo.png | x = 8 to 185, y = 43 to 164 | 197 mm long, buttpad 129 mm tall |
| Buttpad ribs | profile-right-photo.png | zig-zag on x = 8 to 12 between y = 54 and 158 | 22 ribs at 5.5 mm |
| Castle nut and end plate | profile-right-photo.png | x = 186 to 193.5, y = 54 to 84 | 8.4 mm long, 33 mm diameter |
| Selector axis, right | profile-right-photo.png | (240, 100) | L = -147.2, Z = -34.6 mm |
| Pivot and takedown pins | profile-right-photo.png | (364.5, 87.5) and (223, 88) | pin spacing 141.5 px = 157.7 mm |
| Drawing rail pitch | profile-both-sides-drawing.jpg | right side, lug edges x = 465 to 621 at y = 346: 156 px over 26 pitches | 6.0 px per pitch |
| Drawing scale by fit | profile-both-sides-drawing.jpg | best similarity fit of the model | 0.8698 px/mm right, 0.8698 px/mm left: the drawing's rail pitch is then 6.9 mm, not 10.0 |
| Drawing handguard and barrel | profile-both-sides-drawing.jpg | handguard x = 436 to 638, muzzle x = 705 | handguard 1.25 receiver lengths (photo: 1.16); barrel shows 0.41 receiver lengths ahead of it (photo: 0.85) |
| Left-side controls | profile-left-photo-416N.jpg | no spans taken: the photo is in perspective with an optic and grip fitted | used for the layout of the bolt catch, magazine catch, selector and stock ribs only |

Lateral sizes cannot be read from side views. They are the AR-pattern values: receiver 22.6 mm wide at the fire-control pocket, magazine well 28 mm, magazine 22.4 mm, buffer tube 29.2 mm, handguard 60 mm over the side rails, Picatinny rail 21.2 mm wide.

## Check results

| Check | Result | Numbers |
|---|---|---|
| Inventory coverage | PASS | 100 percent: 349 features map to 301 named objects, 48 of them as justified merges (listed below) |
| Silhouette, right photo | PASS | IoU 0.9677 at the fixed ruler transform (no fitting); 0.9676 if fitted |
| Silhouette, drawing right | NOT MET | IoU 0.8309; photo-vs-drawing 0.8410 |
| Silhouette, drawing left | NOT MET | IoU 0.8212; photo-vs-drawing 0.8304 |
| Close-up review | done | 5 close-ups rendered from the reference viewpoints; differences below |
| Assembly | PASS | 301 parts, 0 floating (gap over 0.25 mm), 0 of 29 fasteners not seated in a host |
| Clip `charge` | PASS | 30 frames, 14 parts move; deepest overlap 0.025 mm (bolt_carrier_serrations into upper_body, frame 15) |
| Clip `dust_cover_open` | PASS | 10 frames, 6 parts move; deepest overlap 0.0 mm |
| Clip `mag_release` | PASS | 10 frames, 5 parts move; deepest overlap 0.0 mm |
| Clip `mag_out` | PASS | 24 frames, 23 parts move; deepest overlap 0.0 mm |
| Clip `mag_in` | PASS | 22 frames, 23 parts move; deepest overlap 0.0 mm |
| Clip `bolt_catch` | PASS | 12 frames, 2 parts move; deepest overlap 0.0 mm |
| Clip `safety_to_fire` | PASS | 6 frames, 4 parts move; deepest overlap 0.0 mm |
| Clip `safety_to_safe` | PASS | 6 frames, 4 parts move; deepest overlap 0.0 mm |
| Clip `trigger_pull` | PASS | 10 frames, 1 parts move; deepest overlap 0.0 mm |
| Clip `stock_extend` | PASS | 46 frames, 57 parts move; deepest overlap 0.0 mm |
| Clip `stock_collapse` | PASS | 46 frames, 57 parts move; deepest overlap 0.0 mm |
| Clip `sights_down` | PASS | 8 frames, 8 parts move; deepest overlap 0.0 mm |
| Clip `sights_up` | PASS | 8 frames, 8 parts move; deepest overlap 0.0 mm |
| Export reload | PASS | 301 objects and 8 materials reloaded (built: 301 and 8), 9 images all embedded, 13 clips, 7 sockets, barrel 368.3 mm = 14.5 in, file 6.1 MB |
| Presentation renders | done | `r/right.png`, `left.png`, `top.png`, `front.png`, `three_quarter.png`, `first_person.png` (from `socket_ads_eye`), `first_person_hip.png`, `exploded.png` |

How the checks work: `tools/score.py` projects every triangle orthographically onto the reference pixel grid (4x4 supersampled, threshold 0.5) and compares with the thresholded reference. `tools/checks.py` builds a BVH per part; parts touch if their surfaces intersect or come within 0.25 mm; for each clip frame it measures how deep any vertex of a moving part sits inside a part it moves relative to (and the reverse). The check did fail during the work (trigger into the grip 0.62 mm, front sight arm into its base 2.5 mm, bolt carrier into the buffer tower 2.1 mm) and those were fixed in the geometry, not in the check.

## Triangles per region

| Region | LOD0 | LOD1 |
|---|---|---|
| upper | 9,722 | 2,996 |
| lower | 4,752 | 1,544 |
| handguard | 21,466 | 3,658 |
| barrel_assembly | 14,036 | 3,008 |
| stock | 12,992 | 3,320 |
| grip | 1,740 | 668 |
| magazine | 4,388 | 1,468 |
| sights | 3,896 | 1,024 |
| controls | 4,544 | 1,780 |
| fasteners | 8,248 | 1,336 |
| **Total** | **85,784** | **20,802** |

## Silhouette rounds

| Round | Change | Photo | Drawing R | Drawing L | Largest mismatches (photo) |
|---|---|---|---|---|---|
| 1 | First full build: 301 parts from the inventory, outlines traced from the right photo with the rail ruler. | 0.7464 | 0.5814 | 0.5284 | stock: 5612 px, reference only (model too small); magazine: 5515 px, model only (model too big); buttpad / butt plate: 552 px, model only (model too big); gas block / front sight: 534 px, reference only (model too small); rear sight: 465 px, reference only (model too small) |
| 2 | Rest pose fixed: clip tracks muted so the stock, magazine and sights sit where the photo shows them (round 1 was scoring the first frame of the last clip). | 0.9601 | 0.8322 | 0.8219 | rear sight: 508 px, reference only (model too small); stock: 147 px, model only (model too big); handguard: 99 px, model only (model too big); lower receiver / trigger guard: 64 px, reference only (model too small); lower receiver / trigger guard: 48 px, reference only (model too small) |
| 3 | Rear sight now folds forward with full-length pivot lugs; trigger and grip horn separated; QD cup, trigger guard, magwell fillet and stock diagonal corrected; round parts get 1.5x segments. | 0.9676 | 0.8312 | 0.8211 | rear sight: 258 px, reference only (model too small); lower receiver / trigger guard: 94 px, model only (model too big); stock: 40 px, model only (model too big); stock: 40 px, model only (model too big); lower receiver / trigger guard: 38 px, reference only (model too small) |
| 4 | Sight arms and bases rebuilt as single outlines (no overlapping shells), ghost-ring aperture opened for ADS, charging handle T reshaped, organic parts rounded in 4 steps, guard horn moved to the trigger guard, tower web closed, LOD1 raised to about 25 percent. | 0.9677 | 0.8309 | 0.8212 | rear sight: 259 px, model only (model too big); lower receiver / trigger guard: 94 px, model only (model too big); stock: 40 px, model only (model too big); stock: 40 px, model only (model too big); lower receiver / trigger guard: 38 px, reference only (model too small) |
| 5 | Final textured build: three baked 2048 px PBR sets, polymer highlight reduced, marking panels less worn; geometry unchanged from round 4; all checks rerun on the shipped GLB. | 0.9677 | 0.8309 | 0.8212 | rear sight: 259 px, reference only (model too small); lower receiver / trigger guard: 94 px, model only (model too big); stock: 40 px, model only (model too big); stock: 40 px, model only (model too big); lower receiver / trigger guard: 38 px, reference only (model too small) |

## Close-up review

### `refs/closeup-right-receiver.jpg` against `r/closeup_right_receiver.png`

Matches: ejection port with the bolt carrier face behind it (two vent holes, forward-assist serrations), dust cover hanging open from a hinge rod along the bottom of the port with its torsion spring and two knuckles, brass deflector behind the port, forward assist, magazine release button in its fence, selector on the right with its marks, pivot pin head, rail lugs above.

Differences:
- The replica's bolt is bright bare steel; the model's carrier is phosphate grey like the service rifle.
- The replica carries maker text on the magazine well and the words SAFE and FIRE; the model has a blank panel and pictograms only (brief: no maker marks).
- The replica's handguard is a slim slotted tube with one QD socket; the model keeps the quad rail of the profiles (profiles win).
- The replica's forward assist sits in a scalloped fairing cast into the receiver; the model's is a plain angled housing.
- The replica's dust cover is one stamping with a pressed centre panel; the model has two ribs and a separate latch housing.

Fixed after this review: the first render showed the cover closed; the comparison is now rendered with the cover open at 175 degrees, and the hinge lugs, C-clip and spring were checked to sit on the rod (assembly check).

### `refs/closeup-left-lower-controls.jpg` against `r/closeup_left_lower_controls.png`

Matches: bolt catch with its ribbed upper pad between two ears at the front, selector hub with the thumb lever pointing to the rear, safe pictogram ahead of the hub and fire above it, two stop bosses above the hub, trigger and hammer pins, rear takedown pin, trigger in the guard.

Differences:
- The replica prints FIRE and SAFE under its pictograms; the model has pictograms only.
- The replica has a slotted screw where the model has the rear takedown pin end.
- The model has a third pictogram (automatic) behind the hub, as the military rifle in the drawing does; the semi-automatic replica has two.
- The replica's selector lever has fine grooves and its receiver a cast texture with a raised fence line around the grip; the model carries these as normal-map grain only.

Fixed after this review: pictogram frames were built from overlapping bars that showed black corners; they are now butt-jointed. The selector stops were moved clear of the auto sear pin.

### `refs/closeup-front-sight.jpg` against `r/closeup_front_sight.png`

Matches: a folding front sight with two protective ears, a post, a cross pivot pin with a visible head, a detent button and a clamp screw; rail lugs with 45 degree flanks behind it; barrel shoulder ahead.

Differences:
- The replica's sight is a low rail-mounted unit shown folded; the profile photo shows a tall arm on the gas block in front of the handguard, standing. The model follows the profile.
- The replica's rail slots carry white numbers (28, 30); the model has no slot numbers.
- The replica's handguard is slim with long slots; the model is the quad rail.

Fixed after this review: the sight base was two ears and a bridge as overlapping solids, which shaded black at the joins; it is now one U-shaped piece and the arm one outline with a half-round foot on the pivot.

### `refs/closeup-rear-sight-charging-handle.jpg` against `r/closeup_rear_sight_charging_handle.png`

Matches: a folding rear sight on a rail clamp with a hex clamp screw, pivot lugs with a pivot pin head, the charging handle T with its latch on the left, the teardrop boss on the left of the upper, rail lugs ahead, castle nut and stock behind.

Differences:
- The replica's sight leaf is a thin plate with a round aperture and a small windage knob; the profile photo shows a bulkier diopter-style unit. The model is a compromise: full-length pivot lugs for the photo's lower block, a folding arm with a ghost ring and windage knob.
- The replica's charging handle has a large extended latch with a serrated face; the model's latch is a plain hooked bar.
- The replica's upper has a scalloped shelf behind the boss; the model has a straight rib.

Fixed after this review: the sight arm was a box plus a cylinder; rotating it pushed a bevelled corner 2.5 mm into the base. It is now one outline, the aperture was opened to a 4.6 mm ghost ring so the front post is visible from socket_ads_eye, and the T handle got swept wings.

### `refs/closeup-handguard-front.jpg` against `r/closeup_handguard_front.png`

Matches: birdcage flash hider with a crush washer, stepped barrel, folding front sight at the handguard front, long vents along the handguard, top rail lugs.

Differences:
- The replica has a slim M-LOK-style handguard with a QD socket at the rear; the model is the quad rail with four Picatinny rails, 8 vents per side and a QD cup at the front, as the profiles show.
- The replica's barrel has no necked section; the profile photo does, and the model follows it.

Fixed after this review: the front QD cup and its sling crescent were too small against the photo (99 px mismatch); hole 6.8 mm, crescent 7 to 10.5 mm radius now.

## What still differs from the references

- Drawing silhouettes are below the 0.92 target: the drawing shows a short-barrel rifle with a longer handguard, and its rail is not drawn to MIL-STD pitch. The photo itself scores about the same against the drawing as the model does. One model cannot score 0.92 on the photo and on the drawing.
- Rear sight: the photo shows a bulky diopter-style sight; the model's folding arm is slimmer and its windage knob sits elsewhere (the largest remaining silhouette mismatch, about 260 px of 53,845).
- Handguard length: the model follows the photo (9.0 in, 19 lugs per rail). Not confirmed against an independent source for the D14.5RS.
- No rail slot numbers, no maker marks, no words on the selector (pictograms only).
- Lateral sizes are AR-pattern values, not measured: no top or front reference was supplied.
- The upper receiver is a clean extrusion with added parts; the real forging's scallops around the forward assist and the cam-pin bulge are simplified.
- Stock and grip are slab-sided lofts with rounded edges; the real mouldings have more compound curvature and a thinner lower strut.
- The magazine follows the photo's wide, strongly ribbed magazine (the .22 LR pattern), not a STANAG steel magazine.
- Mould seams, the selector lever's grooves and the receivers' cast texture exist only as normal-map grain.
- Ambient occlusion is baked at the rest pose (magazine moved out of the well for the bake); the bolt carrier and the stock's bore stay dark when they move.

## Decisions worth knowing

- Frame: Blender Z up, metres, muzzle toward -Y (MODELER.md: front faces -Y), right side at -X. Origin on the bore axis at the upper receiver's front face. In glTF the muzzle points +Z.
- Rest pose matches the right photo: stock collapsed, both sights up, dust cover closed, selector on safe, magazine in.
- Fasteners that never move sit under `fasteners`; fasteners on a moving part are parented to that part (stock latch pin, charging handle latch pin) so they travel with it.
- Front sight folds forward over the barrel; rear sight folds forward over the rail. Both paths were chosen because they are the only ones clear of other parts.
- The `charge` clip also flips the dust cover open in its first four frames, as the real bolt carrier does; it stays open at the end of the clip.
- `mag_in` and `mag_out` press the magazine catch for as long as the magazine body passes its tooth.
- The handguard vents are real through-cuts; the barrel and piston housing sit so that daylight shows through them in side view, as in the photo.
- Bullets are a muted gilding-metal yellow and the fire pictograms deep red: nothing on the model is orange.
- Clip tracks are muted in the build scene so the GLB's node transforms are the rest pose, not the first frame of a clip.
- Textures: one 2048 px set per baked material (Anodized, Polymer, Steel): base colour, occlusion-roughness-metallic and tangent normal, stored as JPEG in the GLB. Paint, brass, gilding metal and the dark cavity are plain factors. LOD1 has its own 1024 px sets.
- Triangle budget: LOD0 sits at the low end of 80k to 150k because flat-sided machined parts need few triangles; round parts use 36 to 60 segments.

## Merged inventory features

| Region | Feature | Merged into | Why |
|---|---|---|---|
| muzzle device | flash hider slot 1 of 6 (side slots show daylight) | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider slot 2 of 6 (side slots show daylight) | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider slot 3 of 6 (side slots show daylight) | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider slot 4 of 6 (side slots show daylight) | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider slot 5 of 6 (side slots show daylight) | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider slot 6 of 6 (side slots show daylight) | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider wrench flat, right | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider wrench flat, left | `flash_hider` | a void: cut into the host part with a boolean, so it has no solid of its own |
| muzzle device | flash hider front chamfer and open mouth | `flash_hider` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| barrel | barrel shoulder in front of the gas block | `barrel` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| barrel | barrel necked section (grenade-launcher style cut) | `barrel` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| barrel | barrel muzzle shoulder before the threads | `barrel` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| barrel | barrel section under the handguard (seen through the vents) | `barrel` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| handguard | lightening vent 1 of 4, upper row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 2 of 4, upper row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 3 of 4, upper row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 4 of 4, upper row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 1 of 4, lower row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 2 of 4, lower row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 3 of 4, lower row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 4 of 4, lower row, right side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | sling crescent slot under the front QD cup, right | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 1 of 4, upper row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 2 of 4, upper row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 3 of 4, upper row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 4 of 4, upper row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 1 of 4, lower row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 2 of 4, lower row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 3 of 4, lower row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | lightening vent 4 of 4, lower row, left side | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | sling crescent slot under the front QD cup, left | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| handguard | handguard bore (barrel and piston run inside) | `handguard_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| upper receiver | ejection port opening | `upper_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| upper receiver | bolt carrier bore (dark cavity behind the port) | `upper_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| upper receiver | charging handle channel | `upper_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| upper receiver | flat-top rail base with dovetail undercut | `upper_body` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| upper receiver | upper/lower parting line | `upper_body` | a seam: it is the real gap between upper_body and lower_body |
| lower receiver | magazine well cavity | `lower_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| lower receiver | fire-control pocket and trigger slot | `lower_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| lower receiver | front pivot lugs | `lower_body` | one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh |
| grip | mould parting line front and back | `grip_body` | a mould seam 0.1 mm high: carried by the polymer normal map, not geometry |
| magazine | magazine catch notch | `mag_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| buffer tube | castle nut wrench notch 1 | `castle_nut` | a void: cut into the host part with a boolean, so it has no solid of its own |
| buffer tube | castle nut wrench notch 2 | `castle_nut` | a void: cut into the host part with a boolean, so it has no solid of its own |
| buffer tube | castle nut wrench notch 3 | `castle_nut` | a void: cut into the host part with a boolean, so it has no solid of its own |
| buffer tube | castle nut wrench notch 4 | `castle_nut` | a void: cut into the host part with a boolean, so it has no solid of its own |
| stock | stock bore for the buffer tube | `stock_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
| stock | sling slot through the stock | `stock_body` | a void: cut into the host part with a boolean, so it has no solid of its own |
