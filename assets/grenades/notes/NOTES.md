# Grenades: notes, inferences, omissions, corrections

Version 1 (2026-11-17). Built to `~/mac_claude/openFPS-wt/GRENADES_SHOTGUN_BRIEF.md`. No change requests yet; record
each one here with what changed (rule 7).

## Content boundary

This asset models what a player sees, hears and feels: exterior shape, published weight, delay, throwing distance
and effect figures, game-level effects and synthesised sound. The manual's filler and fuze rows are not used and are
not repeated anywhere in this folder. Every interior is a solid placeholder (`core_placeholder` in the flash; the
other bodies are closed shells with nothing inside). Loudness comes from the published 170 to 180 dB at 5 ft or from
a labelled game value. Nothing here was needed from past that line, so there is no "stopped at the boundary" item.

## Corrections and conflicts the owner should decide

1. **M18 paint.** Table B-2 (and the brief) say light green body with black markings. Fig. B-3 shows a dark body
   with light markings and a light band. The default build follows the table (`--m18-livery table`); the matched
   renders use `--m18-livery figure`. Both are one flag apart. Hue cannot be read from a greyscale figure either way.
2. **Flash holes: 18 built, 12 published.** Table A-5 and the brief say 12 holes. Fig. A-12 shows three rows on each
   of three neighbouring columns 60 deg apart (nine visible), and light through the side columns, which means the
   columns behind them are open too. That reads as 6 x 3 = 18 on this unit. The default build follows the figure;
   `--flash-holes 12` builds 6 columns x 2 rows.
3. **Flash "hexagon tube".** Table A-5 calls the body a hexagon tube. In Fig. A-12 the part between the hexagons is
   round (smooth shading, holes on a 60 deg pitch that would cross a hexagon's edges). Built round, 32.3 mm.
4. **Flash length.** Table A-5's 5.25 in is used as the overall length including the fuze, because with that ruler
   the base hexagon measures 39 mm across (1.73 in across corners gives 38 mm across flats). If 5.25 in were the
   body alone the hexagon would have to be 47 mm.
5. **Frag overall length: 84.5 mm built, 89.7 mm commonly published.** The lever plate sits 210 px above the collar
   in Fig. A-2, which at the fitted 20 deg elevation is 25 mm, giving 84.5 mm overall (estimated +/- 4 mm). With
   89.7 mm the matched render's top stood 5 mm above the figure's. The figure was followed.
6. **Smoke can height.** 117.5 mm from the green can. The four photos give 116 to 132 mm with the width as ruler
   (they are scaled differently). With the fuze the model is 142.5 mm (5.6 in) against the 5.7 in Table B-3 gives
   the same can on another grenade.

## Inferences (not visible or not resolved in the figures)

| What | Value | Why |
|---|---|---|
| Frag pull ring and pin | 29.5 mm ring, pin through the lever ears, ring hanging on the side Fig. A-2 hides | Size from Fig. B-3; pose guessed |
| Frag lever width, taper, thickness | 24 mm at the cap (+/- 4), 15 mm at the tip, 1.2 mm sheet | Cap depth measured; the rest unseen |
| Frag fuze tower taper, hinge shape | cone 10.2 to 9.2 mm radius; cross pin and web | Only the right edge and the lug's place are visible |
| Safety clip depth | 26 mm | Seen from one side |
| Rear lever ear | mirror of the front | Hidden |
| Frag flat base | 11 mm radius | From where the limb leaves the circle |
| Flash tube wall, core radius, fuze depth, lever width | 3 mm, 8 mm, 20 mm, 14 mm | Unseen; the core is a placeholder |
| Flash hole columns on the far side | present | See correction 2 |
| Can rim size, lid dome height | 0.5 x 2.4 mm, 3 mm | Visible but not measurable |
| Can emission holes | four, 9 mm, on a 20 mm radius | Table B-2 says four at the top; none visible |
| Can lever width | 16 mm (+/- 6) | The two usable views give 11 and 26 mm |
| Same can for M18 and AN-M8, 2.5 in | | Table B-3 gives it for the third grenade in the family; the figures' proportions agree |
| Paint hues | olive drab, light green, the four smoke colours, white | Tables give names; figures are greyscale |
| Camera of each figure | `model/tools/views.json` | Fitted by hand; no camera data |
| Flash throwing distance | 35 m | Table A-5 gives none; the frag's is used (weights within 5 %) |
| Release angle and height | 40 deg, 1.8 m | The manual gives distances only |
| Drag coefficients, ground restitution and friction, contact stiffness | `throw/sim.py`, `sound/sim.py` | Textbook values and estimates, labelled EST |

## Omissions

- Confidence clip (Fig. A-1) and the flash's second, triangular ring: listed in the tables, not identifiable in the
  figures of the grenades, not modelled.
- Stamped text on the frag's lever cap, the maker's label on the flash (a plain panel), all designations and lot
  numbers (plain bars), by the brief's marking rule.
- Surface wear, the scuffed band, weld seam, paint chips, the photo backdrops and lighting.
- The flash's see-through centre holes (solid placeholder core) and the pastel green band Table A-5 mentions, which
  Fig. A-12 does not show.
- Bottom hole of older smoke cans (Table B-2 notes recent ones have none).
- No baked textures or UV maps: flat materials only.
- Spin in flight, and rolling on slopes or walls. Fragments past the game's 20 m cut-off (the manual warns of 230 m).

## Game-only content

`impact` has no real reference. It is the frag body with a magenta band (a colour no real marking scheme uses) and
the word IMPACT. Its behaviour (arms 0.35 s after release, functions on the first contact faster than 2 m/s, or after
6 s) is game tuning in `data/grenades.json` and imitates no real fuze.

## What was checked and what was not

Checked: silhouettes against the figures (`COMPARISON.md`), throw distances, fuse and burn windows, effect radii,
bang level, JS against Python for all three simulations. Not checked: the sounds by ear, the sample page on a phone,
the model in a game engine (the GLB is exported and re-openable in Blender, nothing more is claimed), colour.
