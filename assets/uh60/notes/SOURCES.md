# UH-60: sources and what is inferred

## The manual
TM 1-1520-237-10, Operator's Manual for UH-60A, UH-60L and EH-60A helicopters (1996 edition, a public US Army
publication). Copy used: archive.org item
`1996-us-army-operators-manual-for-uh-60-a-uh-60-l-eh-60-a-helicopter-841p`. It is a vector PDF, so the drawings can
be measured. It is kept out of git (`model/refs-local/tm10.pdf`).

| Figure | Used for |
|---|---|
| 2-2 Principal dimensions | Rotor diameter 53 ft 8 in, tail rotor 11 ft canted 20 degrees, fuselage width 7 ft 9 in, length 50 ft 7.5 in, wheel base 29 ft, tread 8 ft 10.6 in, stabilator 14 ft 4 in |
| 6-1 Compartment and station diagram | The whole outside shape. Calibration 0.5775 pt per inch; side view x = 157.85 + (STA - 162) k, y = 444.45 - (WL - 150) k; reading accuracy about 1.5 in. Hub at STA 341.2 / WL 315, tail rotor at STA 732 / WL 324.7, static ground line WL 183.7, frame stations 204, 247, 270, 315.5, 343, 370.5, 398, 443.5, 485, 644.6 |
| 6-9 Cabin dimensions | Cabin 151 in long, floor WL 206.75, ceiling WL 261, inside width 72 / 85 / 69 in, door 68 x 54 in |
| 2-1 General arrangement | Which exterior equipment exists and roughly where |
| 2-4, 2-5 Cockpit and cabin | Layout of seats, consoles, controls. 2-4 also gives what stands on the cockpit floor: ribbed pedal pads on arms, the lower console with its circuit breaker panel, parking brake lever, utility light and fire extinguisher, the crew seat frames and the collective boot (`model/cockpit_floor.py`; sizes inferred, the figure is an undimensioned perspective) |
| 2-9 Instrument panel (sheets 1, 2) | The whole panel face. `model/manual_art.py` joins the two sheets (registered on the central display unit's lettering) and uses the drawing itself as the panel face: outline, each of the 40 instruments' outlines (raised plates), dials, legends, 22 knob positions. Fitted to a 67 in panel width; plate and knob heights nominal |
| 2-8 Lower console (sheet 1) | The whole console top, sloped section and aft section, used directly as its face, with a knob or fastener head at each circle the drawing shows. Scaled by the 5.75 in control-head width |
| 2-7 Upper console (sheet 1) | The whole upper console: outline with its forward cut-out, every panel legend as its face, a bat lever at each toggle switch and a button or knob at each breaker and rotary control the drawing shows. A plan seen from below, aft at the top. No dimensions: width 18.5 in is fitted (its toggle-switch nuts are drawn the same size as figure 2-8's). Where it hangs in the cockpit is still read from figure 2-4 |
| 2-13 Engine control quadrant, with 2-7's plan of it | Quadrant cover, two power control levers with disc knobs, two fuel system selector levers, two engine emergency off T-handles. Where each sits across and along the console is figure 2-7's plan; shapes are figure 2-13's perspective. How far the cover and levers stand out of the console is estimated from that perspective. Colours and lettering are not in the manual: all left black |
| 2-14 Collective and cyclic grips (sheet 1) | Collective grip: outline of the figure's one view, with the drawing itself as the switch face. No side view: the head is given the grip tube's thickness, and grip length 6.9 in is an estimate. The HUD switch of detail A (a modification) is left off |
| 2-14 Collective and cyclic grips (sheet 2) | Cyclic grip: lofted through the figure's side and front silhouettes. No dimensions in the figure: grip height 6.2 in is an estimate |
| 6-11 Cargo tiedown arrangement | Dimensioned plan of the cabin floor: STA 247 to 398, BL 36.5 each side, compartment lines at STA 288 and 343, the position and type of all 34 tie-down and seat-stud pans, the cargo hook access door. Text 6.18: fittings rated 5,000 lb with studs for the troop seats, eight net restraint rings at STA 308 and 379, floor 300 lb per sq ft (`model/floor.py`; pan depth, ring and stud sizes, extra panel joints, screw pitch and wear inferred) |
| 2-9 Instrument panel | Which instruments, and their arrangement |
| 2-10 Troop seats | Seat arrangement and construction |
| Chapter 7 examples | Hover and cruise torque used to check the flight model |

`model/tools/fit_drawing.py` renders the built model orthographically and lays figure 6-1 over it; the side and top
overlays are the acceptance check for the shape.

## Published figures (not in the manual)
Mast tilt 3 degrees; blade chord 1.73 ft and tail blade chord 0.81 ft; rotor 258 rpm and tail rotor 1,190 rpm at
100 percent; blade twist about -18 degrees; T700-GE-700 1,560 shp; inertias and Lock number from the published NASA
UH-60 simulation model reports (Howlett, NASA CR-166309). The paint is the Army's flat aircraft green.

## Inferred (looks and fits right, not from a source)
- Body cross-section shape between the measured top, bottom and width lines (superellipse exponents).
- Intermediate frames, stringer lines, access panels, cowl splits, rivet pitch (1.25 in) and screw pitch.
- All hub hardware below the level of "spindle, bearing, damper, pitch link, bifilar absorber": bolt counts and sizes.
- Hinges, latches, handles, hand holds, mooring rings, cargo hook shape; position-light placement on the gear fairings.
- Troop seat tube sizes, lacing and belt routing; crew seat armour shape; cockpit console proportions.
- Gauge tick spacing, radio control head legends, overhead switch legends. The caution legends are the type's usual ones.
- The serial number on the pylon is fictional.
- Wear: all of it.

## Known differences from the drawing
- The long fairing drawn along the lower fuselage side aft of the main gear is not modelled.
- Engine inlet and exhaust are the plain UH-60A fit; no suppressor.
- The gunner's window is one fixed pane with a centre post, not two sliding panes.


## Rule for visible parts (Evan, 2026-11-19)

Every part a camera can see must be shown in a manual figure, photograph or rendering before it is modelled. Still built only from figure 2-4's small perspective view, with estimated sizes, and to be replaced when a proper reference is in hand: cyclic and collective sticks and boots, glare shield depth, console body, fire extinguisher, utility light, cockpit floor surface.

Round 2 (2026-11-20): the upper console, engine control quadrant and collective grip now come from figures 2-7, 2-13
and 2-14 as listed above, so the placeholder upper console is gone. Searched for the maintenance and parts manuals
(TM 1-1520-237-23 and -23P) for pedals, crew seats and stick linkages: archive.org item `micro_IA41152635_0522`
(1989 aviation unit and intermediate maintenance manual, UH-60A / EH-60A) and liberatedmanuals.com
`TM-1-1520-237-23-1.pdf` exist but their hosts were not reachable from the build machine when this was written.

Round 3 (2026-11-20): second manual in use. TM 55-1520-237-23-5 (Aviation Unit and Intermediate Maintenance, UH-60A
and EH-60A, chapters 11 to 15, 29 August 1989 with change 1; public release; archive.org item
`micro_IA41152635_0522`, a page scan, kept out of git at `model/refs-local/tm23/`).

| Figure | Used for |
|---|---|
| 11-22 Replace boots | Each pedal's support comes up through its own zippered boot on a rectangular screwed-down frame |
| 11-23, 11-27 Pedal assembly and pedal support assembly | Pedal: a cast plate with six lightening pockets (three columns, two rows), pivoted on the top of a tubular pedal support. Master cylinders, pivot shaft, support arms and control rods are below the floor and boot and are not built |
| 11-34, 11-35 Cyclic stick boot and stick | Square boot retainer with screws, tapered zippered boot, stick tube bowed forward ("curve in stick facing front") |

These figures are undimensioned perspectives: pedal plate 4.4 x 5.9 in, boot frames (8.0 x 4.4 in pedal, 7.0 in square
cyclic), boot heights and the amount of bow in the stick are estimates. Not yet applied: figure 11-40 (collective boot
and its NO STEP cover assembly) and 11-41 (collective stick socket, drag strut and support). Crew seats are in another
volume: the 2006 edition's volumes 2 to 7 are downloadable from liberatedmanuals.com (volume 1 is general information,
volume 2 troubleshooting).

Round 3, crew seats: third manual in use. TM 1-1520-237-23 (17 April 2006 edition, volume with chapter 5; public
copy at liberatedmanuals.com `TM-1-1520-237-23-5.pdf`, vector drawings; kept out of git), work package 0231 00.

| Figure | Used for |
|---|---|
| 28 sheet 1, 'seat looking to front' | Widths and heights: bucket, headrest pad (10.4 in wide), guide tubes 18.8 in apart, attenuators, yoke, stowage panel band 24.6 x 6.2 in, crossed lower braces, base tube, track fittings. Read at 18 px per inch on a 3.6x render; the view's own routing dimensions (7, 5-3/4, 3 and 4-1/16 in) give 16 to 22, so sizes are good to about 15 % |
| 7, 9, 24 whole-seat perspectives | Bucket with seat and back cushions, five-strap harness into a rotary buckle, strap adjusters, guide tube caps, diagonal struts to the front track fittings, track tubes |
| 14 seat bucket | The bare shell: pan with side walls sweeping up into a flanged back |
| 27 armoured wing | Stationary and movable wing on the outboard side, on an upper and a lower tube |

Estimated: everything along the seat's fore-aft axis (pan length, back lean 10 degrees, how far the frame stands
behind the back), wing outlines and sizes. Seat centre moved to BL 22.5 (from 21) and STA 230.5 so the collective
passes between seat and console and the guide tubes clear the STA 247 frame; both are estimates. Not built: the
three openings at the top of the bare bucket, frangible strut, inertia reel, ICS cables, vertical adjust spring.
