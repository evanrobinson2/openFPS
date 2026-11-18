# Decomposition of the reference figures, object studies and the derived grammar

Source: the four figure crops named in `REFERENCES.md`. Pixel coordinates are (x, y) in those crops, y down.
Status of each number: **PX** measured in the figure, **FM** from the manual's table, **PUB** a named public figure,
**INF** inferred (not visible or not resolved), **GAME** game-only. The same tags are next to each number in
`model/build.py`.

Process followed: chosen references (approved in the brief) -> this decomposition -> studies and grammar below ->
`model/build.py` -> matched renders and numbers (`COMPARISON.md`). Owner review is still to come.

## 1. Fig. A-2 (`figA2-M67.png`, 738 x 928 px): the frag

Ruler: the body's right limb fits a circle of radius 285 px centred (395, 550), checked at seven heights from y 300 to y 700 (worst miss
8 px); below that the flat base cuts the circle. 570 px = 2.5 in (PUB) gives 0.1114 mm/px. Camera: about 20 deg above the horizon (the collar
ring is an ellipse 190 px wide and about 65 px tall), looking at the side opposite the pull ring. The grenade leans
8 deg to the left in the picture (collar centre (360, 305) against the body centre).

| ID | Part | Region (px) | What is seen | Model part | Status |
|---|---|---|---|---|---|
| A2-01 | Body | circle R 285 at (395, 550) | Dark sphere, flat where it stands (limb leaves the circle 18 px above its lowest point) | `body` | PX shape, PUB diameter |
| A2-02 | Collar | x 265..455, y 285..325 | Bright metal ring where the fuze meets the body | `neck_collar` | PX |
| A2-03 | Fuze tower | x 270..450, y 150..300 | Lighter cone, 180 px wide at the collar, right edge leaning in about 10 px | `fuze_body` | PX width, INF taper |
| A2-04 | Lever cap | corners about (165, 120), (240, 40), (435, 57), (480, 100) | Flat plate over the top with stamped text; 85 px deep in the picture | `lever` (top plate) | PX; text omitted |
| A2-05 | Lever ear | (165, 120), (330, 150), (270, 288), (165, 285) | Flat panel hanging from the plate's front edge, level bottom edge at the collar | `lever` (ears, both sides) | PX front, INF back |
| A2-06 | Lever spoon | from (165, 120) down the left limb to (135, 695) | Strip following the body, seen edge on | `lever` (spoon) | PX path, INF width and thickness |
| A2-07 | Hinge | x 400..480, y 80..165 | Cross pin and lug the lever hooks under | `hinge_lug` | PX place, INF shape |
| A2-08 | Pin end | x 150..185, y 180..230 | Small wire loop on the ear | `safety_pin` tail, `safety_clip` eye | PX place |
| A2-09 | Safety clip | x 35..160, y 265..360 | Wire loop with rounded corners round the lever, an arm rising to A2-08 | `safety_clip` | PX; depth INF |
| A2-10 | Pull ring | not visible | Hidden on the far side | `pull_ring` | INF: size from Fig. B-3, pose guessed |
| A2-11 | Markings | two lines, y 600..680 and 690..740, centred x 420 | Yellow stencil text rising to the right (lean plus wrap) | `marking_word`, `marking_bar_*` | PX place and height; text replaced |
| A2-12 | Backdrop | whole frame | White cloth, soft shadow lower left | not modelled | omitted |

## 2. Fig. A-12 (`figA12-M84.png`, 370 x 624 px): the flash

Ruler: top of the fuze (y 22) to the base (y 607) = 585 px = 5.25 in (FM) gives 0.228 mm/px. With that ruler the
base hexagon is 171 px = 39.0 mm wide, which is the across-flats width of a 1.73 in (FM) hexagon seen corner on
(38.0 mm) plus perspective. So Table A-5's length includes the fuze. Camera level with the body, a little above.

| ID | Part | Region (px) | What is seen | Model part | Status |
|---|---|---|---|---|---|
| A12-01 | Base hexagon | x 66..237, y 505..607 | Heavy hexagon, corner towards the camera, 20 px chamfered shoulder | `hex_base` | FM size, PX height |
| A12-02 | Tube | x 87..229, y 200..505 | Round tube (smooth shading, one long highlight), 142 px wide | `tube` | PX. Table A-5 says "hexagon tube": NOTES.md |
| A12-03 | Holes | three rows at y 287, 375, 462 on three columns at x 95, 155, 215 | Round holes 52 x 48 px; side columns 60 deg round from the centre one; light shows through the side columns | cut in `tube` | PX; count on the hidden side INF |
| A12-04 | Inside | through A12-03 | A darker inner part behind the centre holes | `core_placeholder` | replaced by a plain solid |
| A12-05 | Top hexagon | x 68..250, y 135..200 | Hexagon with a label on each front face | `hex_top`, `label_panel_1/2` | FM size, PX height; label replaced |
| A12-06 | Fuze | x 116..225, y 22..135 | Dark block, 109 px wide | `fuze_body` | PX width, INF depth |
| A12-07 | Lever | from (247, 40) out to (300, 180), down to (283, 455), tip turned in to x 264 | Strip seen edge on, standing off the body | `lever`, `lever_tip_band` | PX path; width INF; brown tip FM |
| A12-08 | Pull ring | circle centre (232, 128), radius 67 px | Large wire ring facing the camera | `pull_ring` | PX |
| A12-09 | Hinge end | x 95..115, y 30..60 | Small lug at the fuze's top left | `hinge_lug` | PX place |
| A12-10 | Second ring | not identified | Table A-5 lists a second, triangular ring that is being withdrawn | not modelled | omitted |

## 3. Fig. B-3 (`figB3-M18.png`, 1728 x 706 px): four coloured smoke cans

Ruler per can: its width = 2.5 in (FM Table B-3, same can; INF that it applies). Violet 245 px, yellow 255, green
270, red 240. Camera about 9 deg above the horizon (rim ellipses). The four photos are not scaled alike in height:
with the width as ruler the can is 117 mm (green), 122 (yellow), 128 (violet), 132 (red). The green can is used
because its total height with the fuze, 142.5 mm (5.6 in), agrees best with the 5.7 in Table B-3 gives the family.

| ID | Part | Region, green can (px) | What is seen | Model part | Status |
|---|---|---|---|---|---|
| B3-01 | Can | x 955..1225, rim centres y 150 and 643 | Sheet-steel cylinder with a rolled rim top and bottom | `body` | FM diameter, PX height |
| B3-02 | Lid | y 128..172 | Light top (the smoke colour, FM), rising a little to the fuze | `top_cover` | FM colour, PX dome |
| B3-03 | Emission holes | not visible | Four holes in the top (FM) | `emission_hole_1..4`, `socket_emit_1..4` | INF place and size |
| B3-04 | Fuze | x 1045..1175, y 35..135 | Dark block on a short neck; 130 px wide seen cornerwise | `fuze_body` | PX |
| B3-05 | Lever | yellow can: x 700..760, y 90..465 | Strip from the fuze top down the side, ending 74 mm below the lid | `lever` | PX length; width 11..26 mm depending on the angle assumed |
| B3-06 | Pull ring | ellipse 100 x 125 px at (1200, 120) | Wire ring hanging to the right front | `pull_ring` | PX; a free part, different on each can |
| B3-07 | Markings | lines at y 272, 338, 420; 55 to 60 px tall | Three stencil lines, light on dark | `marking_bar_designation`, `marking_word_1/2` | PX place and height; text replaced |
| B3-08 | Band | y 495..548 | Light, scuffed band round the can | `band_tape` | PX; colour unknown (greyscale) |
| B3-09 | Lot line | y 575..635 | Lot number | `marking_bar_lot` | replaced by a plain bar |

Per can, the fuze sits at a different angle to the markings (it screws in): the lever is about 126 deg round from
the text on the green can, 116 on the red, 96 on the violet and 73 on the yellow (PX, from where the text centre
and the lever fall across the can's width).

## 4. Fig. B-5 (`figB5-ANM8.png`, 470 x 865 px): the white smoke can

Ruler: can width 330 px = 2.5 in. Dark background, light can. Camera about 6 deg up, seeing the lever side.

| ID | Part | Region (px) | What is seen | Model part | Status |
|---|---|---|---|---|---|
| B5-01 | Can | x 100..430, y 185..820 | Light cylinder, crimped rim at the base (y 800..830), no band | `body` | PX; same can as B3-01 |
| B5-02 | Lever | x 100..135, y 190..590 | Dark strip lying on the can's left front, 78 mm long | `lever` | PX |
| B5-03 | Fuze | x 230..350, y 60..140 | Dark block | `fuze_body` | PX |
| B5-04 | Pull ring | x 60..230, y 20..170 | Ring standing out sideways at the top left | `pull_ring` | PX pose, approximate |
| B5-05 | Markings | three dark lines, y 250..320, 370..450, 490..570 | Text partly behind the lever | marks as B3-07, in black | PX; text replaced |
| B5-06 | Lid | hidden | White top (FM) | `top_cover` | FM |

## 5. Object studies and the grammar they give

Reading the four figures together gives one family with three bodies and two fuze heads.

**Body rules**
- `sphere(d, flat)`: a sphere standing on a small flat (A2-01).
- `can(d, h, rim, dome)`: a cylinder with rolled rims and a low domed lid; lid colour = smoke colour (B3-01/02, B5-01).
- `hex_tube(length, across_corners, tube_d, holes)`: two hexagons, corner forward, joined by a round perforated
  tube; holes on a 60 deg pitch in level rows (A12-01..05).

**Fuze head rules** (both figures of the block fuze and the frag head agree on these relationships)
- The fuze stands on the body's axis. A lever is hinged at the top on one side (`hinge_lug`), covers the top as a
  plate, bends down the opposite side and runs down the body, standing off it by a few millimetres.
- A pin crosses the head at right angles to the lever's run. A wire ring hangs from the pin's eye. The ring is free:
  every figure shows a different pose (A12-08 flat to the camera, B3-06 to one side, B5-04 standing out, the violet
  can's across the top), so a rest pose is one sample, not a rule.
- `frag_head`: cone on a bright collar, wide lever cap with two ears through which the pin passes, spoon following
  the sphere to 22 deg below its equator, wire safety clip round the lever (A2-02..09).
- `block_head`: square block on a round neck, lever plate with short skirts, straight spoon (A12-06..09, B3-04/05,
  B5-02/03). Flash: the spoon stands 30 mm off the axis and ends in a turned-in tip. Cans: it lies 2 mm off the can.
- The head's angle about the axis is free relative to the markings (B3, B5): parameter `can_mark_az` per can.

**Marking rules**
- Lines of stencil text wrapped on the body, centred on one side; on cans a designation line, the word SMOKE, the
  colour, then a band and a lot line (B3-07..09). The model keeps the layout, sizes and places and replaces
  designations and lot numbers with plain bars (brief: placeholder panels, no real lot numbers).

**Motion rules** (from the handling sequence a player performs, FM chapter on throwing; game level only)
- Pin: slides out along its own axis, pulled by the ring. Clip `pin_pull`.
- Lever: swings up about the hinge and leaves it. Clips `lever_squeeze`, `lever_release`.
- Safety clip (frag): comes off sideways first. Clip `safety_clip_off`.

**Frame and sockets** (export frame: metres, +Y up the axis, lever on +X, pull ring towards +Z, origin at the
body centre): `socket_grip`, `socket_effect` (centre; lid for smoke), `socket_pin_ring`, `socket_thumb` (on the
lever), `socket_lever_hinge`, `socket_emit_1..4` (smoke).
