# Notes: the ruler, inferences, omissions, corrections

Version 3, 2026-11-18. Version 3 restores the version 1 ruler (overall length = 41 in). Version 2 (commit `5300a1e`)
is kept below as history (rule 7).

## Change request 2 (2026-11-18, from the coordinating session): back to the overall-length ruler

**Request.** Undo change request 1. **Reason.** Ruling on the 20 in barrel failed four published or physical figures
(overall length, length of pull, the tube passing a 12 gauge rim, the tube holding eight shells) to fix one; the
overall-length ruler misses only the barrel (21.2 in modelled). The simulations use the published 20 in either way.
**What changed.** Every file touched by `5300a1e` is back to its `303b807` state, except the USAGE.md section on where
the published specifications come from, which stays. Pending the owner's review.

### History: change request 1 (version 2, superseded)

#### Change request 1 (2026-11-17, from the coordinating session): ruler = the 20 in barrel

**Request.** Switch the model's ruler to barrel = 20 in, so that the model matches the simulations.

**Reason.** The reference photo cannot match both the published overall length and the published barrel length
(next section). Version 1 scaled the photo to the 41 in overall length, which left the model with a 21.2 in barrel
while the action, recoil and sound simulations used the published 20 in. The barrel was chosen so the model and the
simulations agree. **This is pending the owner's review**: it settles which figure the model honours, not which
figure is right.

**What changed.**
- `model/tools/trace_reference.py`: 0.9039 mm per pixel (was 0.9563). Every traced length is 5.5 % smaller.
- `model/build.py`: lengths that had been fitted in millimetres under the old ruler (radii, the inferred widths)
  carry over by the same factor (`SC`), so the silhouette match is unchanged. Stroke 92.0 mm (was 97.5; the photo
  now allows at most 94.9), bolt 81 mm, bolt slide 53.5 mm, magazine tube wall 0.5 mm (was 0.9).
- `action/sim.py`: the hull leaves 2 mm (was 5) after it clears the chamber and the next shell is released 6 mm
  (was 8) before the rear stop, so the events stay in order on the shorter stroke.
- Everything downstream was rebuilt: inventory, checks, comparison, renders, `action.json`, `ballistics.json` (sight
  geometry only), `params.json`.

**What it costs** (all reported as not met in `model/checks.json` or `action/action.json`):

| Figure | Version 1 | Version 2 | Published |
|---|---|---|---|
| Barrel, breech to muzzle | 21.16 in | **20.00 in** (the ruler) | 20 in |
| Overall length | 40.96 in (the ruler) | **38.67 in (-5.7 %)** | 41 in |
| Length of pull | 13.93 in | **13.17 in (-5.1 %)** | 13.87 in |
| Magazine tube, outside / inside | 24.5 / 22.7 mm | **23.2 / 22.2 mm** | must pass a 22.45 mm rim: it does not |
| 2 3/4 in shells the modelled tube holds | 8 | **7** | 8 |
| Barrel wall at the muzzle | 1.5 mm | 0.95 mm | - |
| Weight from mesh volumes | 6.24 lb | 4.86 lb | 7.25 lb |

The mechanism in `shotgun590-action.js` still holds the published eight in the magazine; only the geometric check
of the modelled tube fails. Silhouette IoU is 0.973 (was 0.974): the shape did not change, only its size.

## Is there a usable full-length side profile? Yes, with one open problem

`File:Mossberg 590.jpg` on Wikimedia Commons (ATF, public domain) is a clean, square-on, right-side photo of the
configuration the brief names. It is the model's silhouette. No left, top or front view of the same gun was found;
the left side borrows control positions from a public-domain photo of a 590A1.

**The open problem: the photo does not agree with two of the maker's published dimensions at once.** In the photo
the muzzle is at x 1117, the butt at x 29 and the front edge of the ejection port (where the barrel's rear face is)
at x 555. Port-to-muzzle is 51.6 % of the overall length. The published 20 in barrel in a 41 in gun is 48.8 %.
No single scale satisfies both.

| Ruler | mm per px | Overall | Barrel (port front to muzzle) | Length of pull | Tube outside dia. |
|---|---|---|---|---|---|
| Overall length = 41 in (version 1) | 0.9563 | 41.0 in | 21.2 in (+5.8 %) | 13.9 in (+0.4 %) | 24.5 mm |
| Barrel = 20 in (**used since change request 1**) | 0.9039 | 38.7 in (-5.7 %) | 20.0 in | 13.2 in (-5.1 %) | 23.2 mm |

For the barrel ruler: it is the one dimension the simulations depend on, and the manual's Fig. 1A (the 14.375 in
model, a line drawing that does match that model's two published lengths) gives a receiver 61 mm tall and a tube of
about 23.3 mm when scaled by its own published length; the photo scaled by the barrel ruler gives 60.6 mm and
23.2 mm.

For the overall-length ruler: it also gives the published length of pull within 0.4 %; its tube passes a 12 gauge
rim and holds the published eight shells with room for a follower and spring; its barrel wall is 1.5 mm.

**Consequence.** The model is a 20.0 in barrel in a 38.7 in gun. Either the photographed gun is not exactly the
catalogue item, or the catalogue's overall length is measured differently, or the breech is not at the port's front
edge. Unresolved: it needs the owner's decision, ideally with a tape measure on a real gun or a dimensioned drawing.

## Corrections made on the way

1. **Tilt.** The photo was first taken to be tilted by 0.64 degrees, from a line fitted to the barrel's whole top
   edge. That edge rises towards the receiver because the barrel tapers. Fitting only the parallel front part
   (x 820 to 1050) gives no tilt. The first reading had put the ejection port 9 mm below the bore; it is 4 mm below.
2. **Ruler.** The first ruler was the barrel (0.904 mm per px); version 1 replaced it with the overall length; change request 1 put the barrel back.
3. **Bolt and bolt slide lengths.** `model/tools/checks.py` found that the first guessed lengths drove the bolt slide
   25 mm out through the back of the receiver at full stroke. They were shortened (version 2: bolt 81 mm, bolt slide
   53.5 mm, stroke 92.0 mm; the photo allows at most 94.9 mm): at full stroke both stay inside by 0.4 mm.
4. **Receiver material.** A boolean cut left an empty material slot and the receiver rendered white. Fixed in `part()`.

## Inferences (no reference gives these)

| What | Value | Why it matters |
|---|---|---|
| Every width: receiver 37.8 mm, stock 41.6 to 35 mm, guard 12 mm, lug 9 mm | inferred | The top, front and three-quarter views are plausible, not measured. |
| Left side of the receiver | positions by proportion from a photo of a different model (590A1) | Lever, ejector screw and plug are within a few mm at best. |
| Receiver wall 3 mm; cavity; loading port width 22 mm; magazine tube wall 0.5 mm | inferred | Seen only through the ports. |
| Bolt, bolt lock, bolt slide, elevator, cartridge stop and interrupter, ejector, follower, action slide tube: shapes and sizes | blocks sized to fit | The manual's exploded view shows that they exist and roughly how they look, without dimensions. They are right in name, place and motion, not in shape. |
| Stroke 92.0 mm, lost motion 9.5 mm, bolt lock drop 7 degrees, elevator lift 22 degrees, safety travel 7 mm, trigger pull 9 degrees, lever travel 3 mm | bounded by the photo (stroke), otherwise guesses | Clip amplitudes and event positions. |
| The small hole under the port (P10) is an elevator stud hole | inferred from manual p16 | It sets the elevator's pivot. |
| The trigger must be released between shots, and the hammer cannot fall with the action open | inferred | The manual describes neither case. Nothing here models a way round either. |
| Sight picture: the bead resting on the receiver's flat top | inferred from the model's geometry | It tilts the bore 14.9 mrad up from the line of sight, so shots land about 0.4 m high at 30 m (`ballistics/README.md`). The bead is 2 px in the photo: about 1.5 mrad of doubt. A game can aim along the bore instead. |
| Template shell: 59 mm long, 22.3 mm rim, 16 mm brass head | nominal, recalled | Only for drawing shells. |
| Hollow stock: effective density 420 kg/m3 | guess | The mass estimate only. |

## Omissions

| What | Feature | Why | Visual consequence |
|---|---|---|---|
| Vent slots in the recoil pad | P03 | Detail left for a texture pass. | The pad is plain. |
| Rounded corners of the ejection port; the bolt's small hole and slot detail | P07, P08 | Simplified. | The port is a sharp rectangle. |
| Surface wear, texture, the photo's lighting | P24 | No textures in version 1. | Flat, clean materials. |
| Heat shield | L03 | Not in the brief's configuration, not on the profile photo. | None against the profile. |
| Roll marks and serial number | L06 | Rule: no maker's names or logos. Nothing replaces them. | Plain receiver sides. |
| Magazine spring, the swivel stud's ring and washer, action slide tube nut, hammer, sear and everything inside the trigger housing, firing pin, stock bolt | M09 | Never seen by a player; the manual says the housing is not to be taken apart. | None from outside. The `takedown` clip moves the housing as one block. |
| Second level of detail, baked textures, a first-person arms rig | - | Out of scope for version 1. | - |
| A check of the full-length parts schematic | - | The site refused automated requests. | Part names come from the manual's lists. |

## What is and is not established

- Measured: the right-side silhouette against the photo (`COMPARE.md`: IoU 0.973).
- Checked structurally: parts, hierarchy, clips, clearances, the exported file's frame (`model/checks.json`).
- **Not established:** anything about the left, top or front; the shapes of internal parts; colour and material
  fidelity; how it looks in a game engine; the owner's approval.


Version 1, 2026-11-17, Claude Fable 5.2. No change requests yet (rule 7: each one gets a section here).

## Is there a usable full-length side profile? Yes, with one open problem

`File:Mossberg 590.jpg` on Wikimedia Commons (ATF, public domain) is a clean, square-on, right-side photo of the
configuration the brief names. It is the model's silhouette. No left, top or front view of the same gun was found;
the left side borrows control positions from a public-domain photo of a 590A1.

**The open problem: the photo does not agree with two of the maker's published dimensions at once.** In the photo
the muzzle is at x 1117, the butt at x 29 and the front edge of the ejection port (where the barrel's rear face is)
at x 555. Port-to-muzzle is 51.6 % of the overall length. The published 20 in barrel in a 41 in gun is 48.8 %.
No single scale satisfies both.

| Ruler | mm per px | Overall | Barrel (port front to muzzle) | Length of pull | Tube outside dia. |
|---|---|---|---|---|---|
| Overall length = 41 in (**used**) | 0.9563 | 41.0 in | 21.2 in (+5.8 %) | 13.9 in (+0.4 %) | 24.5 mm |
| Barrel = 20 in | 0.9039 | 38.7 in (-5.6 %) | 20.0 in | 13.2 in (-5.1 %) | 23.1 mm |

Why the overall-length ruler was chosen:
- It also gives the published length of pull within 0.4 %, a third published figure it was not fitted to.
- With the barrel ruler the magazine tube comes out 23.1 mm outside: too thin to hold a 12 gauge rim (22.45 mm) with
  any wall, and too short for the published eight shells plus a follower. With the used ruler eight 59 mm shells
  fit with 45 mm left for the follower and the compressed spring (`action/action.json`, check `tube_holds_published_capacity`).
- The barrel's wall at the muzzle would be 0.9 mm with the barrel ruler, 1.5 mm with the used one.

What speaks for the barrel ruler: the manual's Fig. 1A (the 14.375 in model, a line drawing that does match that
model's two published lengths) gives a receiver 61 mm tall and a tube of about 23.3 mm when scaled by its own
published length; the photo scaled by the barrel ruler gives 60.6 mm and 23.1 mm, and by the used ruler 64 mm and
24.5 mm.

**Consequence.** The model is 41.0 in long with a barrel that measures 21.2 in from the breech as modelled. Either the
photographed gun is not exactly the catalogue item, the catalogue's overall length is measured differently, or the
breech is not at the port's front edge by the 30 mm that would reconcile them (the manual's Fig. 1A says it is). This
is unresolved and needs a decision from the owner, ideally with a tape measure on a real gun or a dimensioned
drawing. `model/checks.json` reports the barrel as **not met**. The simulations use the published 20 in, not the
model's 21.2 in.

## Corrections made on the way

1. **Tilt.** The photo was first taken to be tilted by 0.64 degrees, from a line fitted to the barrel's whole top
   edge. That edge rises towards the receiver because the barrel tapers. Fitting only the parallel front part
   (x 820 to 1050) gives no tilt. The first reading had put the ejection port 9 mm below the bore; it is 4 mm below.
2. **Ruler.** The first ruler was the barrel (0.904 mm per px). It was replaced as explained above.
3. **Bolt and bolt slide lengths.** `model/tools/checks.py` found that the first guessed lengths drove the bolt slide
   25 mm out through the back of the receiver at full stroke. The bolt is now 84 mm, the bolt slide 57 mm, and the
   stroke 97.5 mm (the photo allows at most 100.4 mm): at full stroke both stay inside by 0.4 mm or more.
4. **Receiver material.** A boolean cut left an empty material slot and the receiver rendered white. Fixed in `part()`.

## Inferences (no reference gives these)

| What | Value | Why it matters |
|---|---|---|
| Every width: receiver 40 mm, stock 44 to 37 mm, guard 12 mm, lug 9 mm | inferred | The top, front and three-quarter views are plausible, not measured. |
| Left side of the receiver | positions by proportion from a photo of a different model (590A1) | Lever, ejector screw and plug are within a few mm at best. |
| Receiver wall 3 mm; cavity; loading port width 22 mm | inferred | Seen only through the ports. |
| Bolt, bolt lock, bolt slide, elevator, cartridge stop and interrupter, ejector, follower, action slide tube: shapes and sizes | blocks sized to fit | The manual's exploded view shows that they exist and roughly how they look, without dimensions. They are right in name, place and motion, not in shape. |
| Stroke 97.5 mm, lost motion 9.5 mm, bolt lock drop 7 degrees, elevator lift 22 degrees, safety travel 7 mm, trigger pull 9 degrees, lever travel 3 mm | bounded by the photo (stroke), otherwise guesses | Clip amplitudes and event positions. |
| The small hole under the port (P10) is an elevator stud hole | inferred from manual p16 | It sets the elevator's pivot. |
| The trigger must be released between shots, and the hammer cannot fall with the action open | inferred | The manual describes neither case. Nothing here models a way round either. |
| Sight picture: the bead resting on the receiver's flat top | inferred from the model's geometry | It tilts the bore 15 mrad up from the line of sight, so shots land about 0.4 m high at 30 m (`ballistics/README.md`). The bead is 2 px in the photo: about 1.5 mrad of doubt. A game can aim along the bore instead. |
| Template shell: 59 mm long, 22.3 mm rim, 16 mm brass head | nominal, recalled | Only for drawing shells. |
| Hollow stock: effective density 420 kg/m3 | guess | The mass estimate only. |

## Omissions

| What | Feature | Why | Visual consequence |
|---|---|---|---|
| Vent slots in the recoil pad | P03 | Detail left for a texture pass. | The pad is plain. |
| Rounded corners of the ejection port; the bolt's small hole and slot detail | P07, P08 | Simplified. | The port is a sharp rectangle. |
| Surface wear, texture, the photo's lighting | P24 | No textures in version 1. | Flat, clean materials. |
| Heat shield | L03 | Not in the brief's configuration, not on the profile photo. | None against the profile. |
| Roll marks and serial number | L06 | Rule: no maker's names or logos. Nothing replaces them. | Plain receiver sides. |
| Magazine spring, the swivel stud's ring and washer, action slide tube nut, hammer, sear and everything inside the trigger housing, firing pin, stock bolt | M09 | Never seen by a player; the manual says the housing is not to be taken apart. | None from outside. The `takedown` clip moves the housing as one block. |
| Second level of detail, baked textures, a first-person arms rig | - | Out of scope for version 1. | - |
| A check of the full-length parts schematic | - | The site refused automated requests. | Part names come from the manual's lists. |

## What is and is not established

- Measured: the right-side silhouette against the photo (`COMPARE.md`: IoU 0.974).
- Checked structurally: parts, hierarchy, clips, clearances, the exported file's frame (`model/checks.json`).
- **Not established:** anything about the left, top or front; the shapes of internal parts; colour and material
  fidelity; how it looks in a game engine; the owner's approval.
