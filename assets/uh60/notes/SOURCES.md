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
| 2-4, 2-5 Cockpit and cabin | Layout of seats, consoles, controls |
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
