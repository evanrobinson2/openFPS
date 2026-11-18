# Wayfarer: decisions, limits and open questions

## Decisions

- **Hull.** A super-ellipse section lofted on a grid (stations by 36 rows a side). The exponent rises from 2.25 at
  the nose to 3.2 amidships: a rounder barrel left the lower deck too narrow to stand on. Openings are tagged on the
  grid, so plates, substructure, lining and coamings all agree about where a hole is.
- **Plating.** Plates come from a seeded recursive split of the grid, with gaps, three heights, skirts and bolts. The
  same seed gives the same ship.
- **Canopy.** A 0.80 m slit. A taller glazed band read as an airliner and put glass over the pilots' heads.
- **Two decks.** 2.30 m clear on the main deck and 2.20 m on the lower. The ladder well sits at station 6.9 to 7.7 to
  miss the forward gear wells.
- **Lift chassis.** Four rams, 1.70 m of travel, belly plate lands on the ground. A hinged ramp would have struck the
  belly on the way up, so the ramp is a drawer: it slides forward from under the lift deck. A drawer ramp alone left a
  0.165 m step up to the deck, so the deck's forward edge is a sill flap: it drops, the ramp's hinge end rises into
  that slot on two horns until it is flush with the deck, and then the toe tilts to the ground. The ramp is 2.60 m
  long and lies at about 14 degrees.
- **Lander bay.** Jack screws at y = 1.22 m with clamp arms reaching in, so the screws pass beside the lander rather
  than through it. That set the lander's width at 2.2 m.
- **Lower deck doors** part in the middle, because a single leaf could not slide past the gear wells.
- **Landing gear.** Front pair folds aft, rear pair folds forward, each into a real well with two doors.
- **Level of detail.** `--lod 1` leaves out fasteners (178,000 of 409,000 triangles).

## Limits, plainly

- First-pass detail everywhere except the cockpit, which has had its full-detail pass (flight seats, displays with
  bezel keys, standby gauges, keypads, throttle quadrant, switch panels, overhead panel, pedals, grab handles).
- Flat colours. No textures, wear, decals or markings.
- Clips are kinematic. Nothing is simulated: no mass, thrust, flight, gear loads, hydraulics or sound.
- The lander is a stub.
- No collision meshes.
- The interior is my design. The concept image shows none of it.
- The pilot's view out is narrow. The slit is 0.80 m tall but the wall is 0.40 m thick, so from the seat the glass
  reads as a low band under a deep brow. Raising the seat, thinning the brow lining or deepening the slit would each
  help; none has been done because each changes the look from outside.
- Checks are numeric (sizes, clearances, clip lengths). Part-against-part interference has been looked at in renders
  and cutaways, not tested automatically.
- The sample page needs a local build. The repository holds no mesh.

## Working defaults, 2026-11-18

carpetshark was away, so these were taken as defaults and can all be reversed: keep both the retractable gear and the
stowed lander; keep the interior as drafted; keep the engine reading below; make the ramp flush (done); detail the
cockpit first (done). Questions 1 to 5 still want a real answer.

## Open questions for carpetshark

1. **"Hidden landing craft."** Built both readings: retractable landing gear behind hull doors, and a small lander
   stowed in a belly bay. Which did you mean, or both?
2. **Interior layout.** Is the arrangement on the sheet right (cockpit, vestibule and ladder, crew deck, mission bay,
   engineering above; avionics, hold with the lift, lander bay, reactor below)?
3. **Engines.** I read the image as one large pod with an octagonal intake and a smaller pod above it under a cowl,
   on each side, plus a centre nozzle. Is that your reading?
4. **Ramp.** It now finishes flush with the lift deck, by way of a sill flap. Is that what you want?
5. **Pilot's view.** From the seat the canopy slit is a low band (see `renders/pilot_eye.jpg`). Keep the heavy brow
   as in the image, or open the view up?
6. **Which section next for full detail,** after the cockpit: lift chassis, an engine pod or the lander bay?
7. **The lander.** Its own asset later, or part of this one?

## Next

1. Take one section to full detail.
2. Roll that detail out; materials and wear.
3. Collision set and distance levels.
4. Simulation layers: mass and balance, thrust and flight, gear loads, mechanism timing, sound.
