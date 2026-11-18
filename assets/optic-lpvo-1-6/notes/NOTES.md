# Notes: generic 1-6x24 LPVO

## Version history (rule 7)

| Version | Date | What |
|---|---|---|
| v1 | 2026-11-17 | First version in openFPS. Restart of a paused build that lived in a private repository; its simulation was re-checked against MODELING_RULES.md and extended, its meshes were never built. |

Changes from the paused build's simulation:

1. **Reticle redesigned.** The old reticle had bars for M855 only, on a 50 m zero. The brief asks for holds that
   agree with the rifle's ballistics for M855 and Mk 262. The two loads differ by 0.13 to 0.28 mrad from 300 to
   600 m when both are zeroed at 200 m, too much to share a mark. The new "staple" mark carries both: bar for M855,
   leg tips for Mk 262. The zero is now 200 m for either load. The ring grew from 2.2 to 2.6 mrad so the 300 and
   400 m staples and their numbers sit clear of it.
2. **Exit pupil ceiling** 9.6 mm (a guess) became 10.4 mm, the lower of two published 1x exit pupils.
3. **Cams are solved to machine precision** (bisection) for any magnification, in Python and in the runtime; the old
   code interpolated a scan.
4. **Mount height** was a mixed figure (a "1.93 in" mount computed for a different rail height). It is now a 1.70 in
   mount measured over this rifle's rail: axis 43.18 mm over the rail, 79.97 mm over the bore.
5. **Hold tables use the exact zero angle**; the old ones used the angle rounded to whole clicks, which made the
   "50 m" and "200 m" zeros identical. The rounding is now reported beside the exact angle.
6. Checks added: ray-transfer matrix, published figures of three scopes, sampled eye box, runtime parity, reticle
   against the ballistics runtime.

The focal lengths of the zoom are kept from the paused build. The search that produced them was not kept; the
numbers are in `sim.py` and every property that follows from them is recomputed and checked.

## Geometry and the reference-to-3D rule

The standing rule for reference-led 3D work is: chosen reference, source-indexed decomposition, object studies and
grammar, procedural reconstruction, matched comparison, owner review. **This asset has no chosen reference.** The
brief asks for a generic scope with no maker's identity, and no concept image or photograph was selected for it, so
there is no source to decompose or to compare against. What exists instead:

- Overall length, tube and objective diameters come from class figures (`REFERENCES.md`); the axis height, the
  eyepiece's position, the sockets and the power ring's throw come from `optics/lpvo.json`.
- The proportions of the eyepiece, the turret saddle, the turrets, the flare at the objective end and the whole mount
  are inferred, and `model/inventory.json` marks each part so.
- The shape is therefore a **proposal** for owner review, not a reconstruction, and no fidelity is claimed. If a
  reference is chosen later, that is a new version through the full order above.

Decisions I made that an owner may want to change:

- Capped low-profile turrets, illumination knob on the left of the saddle, a throw lever on the power ring that
  points left at 1x and comes over the top to the right at 6x.
- One-piece cantilever mount, 1.70 in high, base on the receiver rail from rifle L = -94 to -14 mm (ahead of the
  folded rear sight), cross-bolts in the slots at L = -84.1 and -24.1 mm, front ring reaching 26 mm ahead of the base.
- Eyepiece rear face at rifle L = -170 mm, which puts the 6x exit pupil 6.8 mm behind the rifle's iron-sight eye
  point. The eyepiece passes 4.2 mm over the folded rear sight; the raised rear sight would hit it.
- The glass sits at the two ends of the body even though the thin-lens layout is 75 mm shorter than the body.

## Checks that are structural, not visual

`model/fit.json`: with the rifle's sights folded no scope or mount part intersects a rifle part, and both
cross-bolts lie in slots. This proves the mount fits the rail as modelled. It says nothing about whether the scope
looks right.

## Not done

- Lens caps, a sunshade, a mount level, witness marks and numbers on the turrets and the power ring.
- Textures: the materials are flat. The recipe bakes nothing.
- An etched reticle mesh inside the scope: the reticle is data (`optics/lpvo.json` primitives and two SVGs).
- The sample page does not draw the 3D model.
