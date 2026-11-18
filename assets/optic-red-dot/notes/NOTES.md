# Notes: generic red-dot sight

## Version history (rule 7)

| Version | Date | What |
|---|---|---|
| v1 | 2026-11-17 | First version in openFPS. Restart of a paused build that lived in a private repository; its simulation was re-checked and largely rewritten against MODELING_RULES.md, its meshes were never built. |

Changes from the paused build's simulation, each a correction:

1. **Parallax was measured from the wrong point.** The old code measured the dot against the point lying on the
   dot's geometric direction. But the eye sees the target through the tilted window, which bends the line of sight
   by a constant 0.7 mrad. That constant was being counted as parallax (about 0.5 MOA for a centred eye, where
   parallax is zero by definition). Parallax is now measured from the point the centred eye's dot covers as seen
   through the window.
2. **The centred dot was 9.4 mrad off the mechanical axis** in the old design (the optimiser's penalty on it was
   weak), which would have used a quarter of the adjustment range to zero and made the dot's direction depend on eye
   distance. The tilt is now solved so the centred dot is exactly on the axis.
3. **A surface-intersection routine picked the wrong root** for a strongly curved surface with the eye inside its
   sphere. Rewritten in the curvature with the root chosen on the vertex cap; a flat surface is now exact.
4. **Housing length** was 120 mm. The class figure in the maker's manual is 135 mm; the generic sight is now 130 mm
   and the emitter sits 92 mm behind the window.
5. **Polynomial order** raised from 3 to 5 (fit residual 49 µrad to 0.03 µrad), and the see-through factor of the
   window added to the fast parallax formula.
6. The JSON lost the polynomial's small coefficients to rounding; numbers are now written to 12 significant digits.

## Geometry and the reference-to-3D rule

The standing rule for reference-led 3D work is: chosen reference, source-indexed decomposition, object studies and
grammar, procedural reconstruction, matched comparison, owner review. **This asset has no chosen reference.** The
brief asks for a generic sight with no maker's identity, and no concept image or photograph was selected for it, so
there is no source to decompose or to compare against. What exists instead:

- The dimensions that matter come from the simulation (`optics/reddot.json`: window and emitter positions, doublet
  radii and tilt, clear apertures, axis height) and from class figures (`REFERENCES.md`).
- Everything else (the lengths of the bell and hood, the knob and cap sizes, the mount's shape) is inferred, and
  `model/inventory.json` marks each part so.
- The shape is therefore a **proposal** for owner review, not a reconstruction, and no fidelity is claimed. If a
  reference is chosen later, that is a new version through the full order above.

Decisions I made that an owner may want to change:

- Layout: emitter and both adjusters in a rear bell, brightness knob with the battery on the left, elevation on top,
  windage on the right, a single ring mount at mid-length. Emitter at 4:30.
- Optical axis 39 mm over the rail. On this rifle model the iron sight line is 28.7 mm over the rail, so raised irons
  show 10.3 mm below the centre of the 24 mm window (a low co-witness), and the sight clears the folded rear sight by
  4.0 mm.
- Housing mid-length 15 mm ahead of `socket_optic`, cross-bolt in the rail slot at rifle L = -44.1 mm.
- 12 switch positions instead of the class's 16.

## Checks that are structural, not visual

`model/fit.json`: with the rifle's sights folded no optic part intersects a rifle part; the cross-bolt lies in a
slot. This proves the mount fits the rail as modelled. It says nothing about whether the sight looks right.

## Not done

- Lens covers, a kill-flash filter, a lanyard for the caps.
- Textures: the materials are flat. The recipe bakes nothing.
- The sample page does not draw the 3D model.
