# F-27 Wayfarer: brief and reading of the concept image

A boardable gunship for first-person play. The player walks up to it on its landing gear, rides the lift chassis
up into the hold, walks both decks, sits in the cockpit, and can drop from the lander bay. It is built "down to the
bolt": every plate, frame, door and fastener is a named thing made by code.

- Size: the F-27 spec (24 m) scaled by 1.25, so 30.0 x 9.0 x 6.75 m (length, width over the engine pods, height with
  the gear up). `model/tools/checks.py` measures the build against this.
- Look: realistic, gunmetal armour with red accents. Not brick-built or toy-like.
- Reference: one concept image made by carpetshark with Midjourney. It is used for design reference only and is not
  in this repository (see `REFERENCES.md`).

## What the image shows, region by region

| Region | In the image | In the model |
|---|---|---|
| Overall | A long rounded capsule, nose to the left, seen from the port bow and slightly above. Engines glow at the tail. | A lofted barrel hull, super-ellipse section 6.0 m wide and high, with a 6.5 m nose and a necked-in engine section. |
| Nose | Blunt and drooping, with a jaw line under the glazing. Antenna whiskers and a small sensor cluster at the tip. | Nose tip 0.8 m below the barrel axis; dark sensor cap; air-data probes and whisker antennas. |
| Canopy | A wide glazed slit that wraps the nose under a heavy armoured brow, split by pillars. | A 0.80 m slit from station 0.62 to 4.40, five pillars a side, brow and sill rails, a raised brow plate. Two hull rows are pinned to the brow and sill so the glass has clean edges. |
| Chin | A red stripe sweeping back from the nose under the canopy. A gun under the chin. | Red plates along two hull rows back to station 5.3; a twin-barrel chin turret with yaw and elevation nodes. |
| Hull skin | Layered armour plates of different sizes and heights, in several greys, with a few red ones. | About 1,500 plates cut by a seeded split of the hull grid, at three heights, with applique plates bolted over some. Four greys and two reds. A dark substructure shell shows in the gaps. |
| Waist | A recessed channel painted red along the side, with small rectangular openings in it. | A 0.20 m deep channel from station 7.2 to 21.0 with red floor plates, six viewports a side and two conduits. |
| Under the waist | A row of deeper rectangular recesses with things in them. | Eight equipment bays a side, each with one of four fits: louvres, a pipe manifold, an access hatch, pressure bottles. |
| Top | A spine with boxes, hatches and aerials. | A segmented spine duct, a comms dome, two finned heat exchanger banks, blade antennas, a sensor mast. |
| Belly | Dark, with pipes, tanks and at least one more gun pod with red-tipped barrels. | Keel tanks and pipes beside the lift, a ventral gun pod with two red-muzzled barrels. |
| Engine section | The hull necks in. On the visible side a large pod with an octagonal face and a rectangular intake in a red frame, then ribbed barrel sections, then a nozzle. Above it an armoured shroud in overlapping plates, with more ribbed machinery behind. | Per side: a main pod (octagonal housing, red face, intake with vanes, ribbed barrel between bolted flanges, armour saddles, petal nozzle) and a smaller upper pod under a four-plate cowl. A centre nozzle and four verniers on the aft thrust plate. Pylons and plumbing between hull and pods. |

## Where the image overrules the older written spec

1. Nose: a large wraparound glazed slit, not a narrow armoured window band.
2. Hull: a rounded barrel with a recessed red channel, not a chamfered box.
3. Engines: round pods stacked two high on each side with ribbed machinery, not two octagonal units side by side.
   The octagon survives as the intake face of the main pods.

## What the image does not show, and so is designed here

Everything inside; the landing gear; the bottom entrance; the lander bay. These follow from the brief:

- **Landing gear**: four legs with pads, hidden behind doors that follow the hull, each in a real well.
- **Bottom entrance**: a chassis (a cage with the belly plate, a grating deck and a harness frame) that four
  telescopic rams lower 1.70 m from the hold to the ground. A ramp slides out of a drawer under its deck.
- **Internal landing array**: a lander bay with two belly doors and a cradle on four jack screws that lowers a small
  lander 1.45 m, clear of the belly. The lander is a stub at the right size.
- **Decks**: main deck (cockpit, vestibule with the crew hatch and ladder, crew deck, mission bay, engineering) and
  lower deck (avionics aisle, hold with the lift, lander bay, reactor). 2.30 m and 2.20 m clear height.

The general arrangement is drawn in `../renders/sheet_structure.jpg`.

## Build order

1. Break the image down region by region (this file).
2. Orthographic sheet (`renders/sheet_blockout.jpg`, then `renders/sheet_structure.jpg`).
3. Blockout at true scale with 1.80 m figures (`model/blockout.py`).
4. Structure and hull, module by module (`model/build.py`). **This is where the asset is now.**
5. One section taken to full detail.
6. That detail rolled out across the ship.
