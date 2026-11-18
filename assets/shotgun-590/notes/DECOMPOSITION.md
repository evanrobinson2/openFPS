# Reference to model: the record

The order followed, as the standing reference-to-3D rule asks: the chosen references (approved 2026-11-18, listed in
`REFERENCES.md`), a source-indexed decomposition, object studies and a derived grammar, a procedural recipe, a matched
comparison (`COMPARE.md`), then the owner's review, which has not happened yet.

## 1. Sources and how they were inspected

- **P**: the public-domain right-side profile photo, 1148 x 263 px. Inspected as a 12 px column grid (the trace tool
  prints the covered runs of every column) and as three enlarged crops: stock (x 0..500), receiver (x 333..733), front
  (x 667..1148).
- **L**: the public-domain left-side photo of a 590A1, for the left-side controls only.
- **M**: the owner's manual, by page and figure, for the mechanism and its part names.

There is **no top view and no front view** in the pack. Everything lateral is inferred (section 4).

## 2. Decomposition

Regions are pixel boxes in the named source. The same table is `model/decomposition.json`; `model/tools/checks.py`
checks that every part of every built feature exists in the build and that every built part names a feature here.

| ID | Src | Region | What is there | Parts | Status |
|---|---|---|---|---|---|
| P01 | P | x 29..365, y 75..229 | buttstock: straight comb rising to the receiver, pistol-grip wrist, belly line to the toe | `stock` | built |
| P02 | P | x 29..76, y 100..229 | recoil pad, joint line slanted (top x 54, bottom x 75), toe further forward than heel | `recoil_pad` | built |
| P03 | P | x 33..72, y 108..222 | slanted vent slots moulded into the pad's side (about 12) | `recoil_pad` | omitted |
| P04 | P | x 129..140, y 190..201 | rear sling swivel stud under the stock | `rear_swivel_stud` | built |
| P05 | P | x 357..577, y 31..99 | receiver: flat sides, flat top from x 405 to 570, rear slope down to the stock joint, small bevel at the front | `receiver` | built |
| P06 | P | x 376..399, y 37..46 | safety button: ribbed slider on the top rear slope | `safety_button`, `safety_red_dot` | built |
| P07 | P | x 483..556, y 47..71 | ejection port, rounded corners; the bolt fills it with the action closed | `receiver`, `bolt` | built |
| P08 | P | x 535..556, y 55..61 | extractor and its slot at the bolt's front right | `extractor` | built |
| P09 | P | x 393..401, y 81..89 | trigger housing retainer pin, round head | `trigger_housing_pin` | built |
| P10 | P | x 492..498, y 84..90 | small hole under the port: taken as an elevator stud hole (manual p16: the elevator's studs fit 1/4 in holes in the receiver) | `elevator_stud_r`, `elevator_stud_l` | built |
| P11 | P | x 405..412, y 62..68 | small round plug on the receiver side, upper rear; the left-side photo shows one at the same place (L04). Function not identified | `receiver_side_plug_r` | built |
| P12 | P | x 436..512, y 33..37 | two filler screws seen at the top edge (x 446 and 510) | `receiver_top_screw_1`, `receiver_top_screw_2` | built |
| P13 | P | x 395..466, y 96..128 | trigger guard loop and the housing's lower edge under the receiver | `trigger_housing`, `trigger_guard` | built |
| P14 | P | x 405..418, y 99..123 | trigger blade, curved forward at the tip | `trigger` | built |
| P15 | P | x 577..1117, y 38..67 | barrel: collar at the receiver, taper over the first 230 px, then parallel to the muzzle | `barrel` | built |
| P16 | P | x 1100..1106, y 39..44 | bead front sight | `front_bead` | built |
| P17 | P | x 577..1084, y 71..98 | magazine tube under the barrel, full length | `magazine_tube` | built |
| P18 | P | x 578..700, y 70..79 | action slide bar between barrel and tube, running into the forend (right bar seen; left assumed by symmetry, manual Fig. 22 names bars in the plural) | `action_bar_right`, `action_bar_left` | built |
| P19 | P | x 683..903, y 67..110 | forend: round, rear lip, about 19 ring ribs from x 735 to 850, smooth nose with a rounded front | `forend` | built |
| P20 | P | x 955..987, y 64..115 | band around barrel and tube with a lug hanging below it (bayonet lug) | `lug_band` | built |
| P21 | P | x 1059..1085, y 64..101 | barrel takedown ring around the tube (manual p6: the barrel's takedown mount hole slides over the magazine tube) | `barrel_ring` | built |
| P22 | P | x 1083..1112, y 72..99 | magazine cap with the front swivel stud at its tip | `magazine_cap`, `front_swivel_stud` | built |
| P23 | P | x 357..372, y 50..99 | stock to receiver joint, slanted | `stock`, `receiver` | merged |
| P24 | P | x 0..1148, y 0..263 | lighting and surface: flat frontal flash on a white ground, matte dark finishes, wear specks on barrel and tube | - | omitted |
| L01 | L | x 1268..1283, y 130..139 | action lock lever behind the trigger guard, left side (manual p6 Fig. 4) | `action_lock_lever` | built |
| L02 | L | x 1064..1070, y 60..66 | ejector screw head on the left wall (manual p28 items 10 and 11) | `ejector_screw`, `ejector` | built |
| L03 | L | x 350..975, y 35..75 | perforated heat shield over the barrel (a 590A1 fitting, also manual p30 items 31 to 34) | - | omitted |
| L04 | L | x 1240..1249, y 68..77 | round plug on the left side, upper rear (mirror of P11) | `receiver_side_plug_l` | built |
| L05 | L | x 1010..1137, y 127..145 | loading port in the receiver's underside, in front of the trigger guard, with the elevator closing it | `receiver`, `elevator` | built |
| L06 | L | x 1105..1290, y 80..112 | maker's roll marks and serial number on the receiver | - | omitted |
| M01 | M | p5 Fig. 2 and 3 | safety: rearward is ON (SAFE) and covers the red dot; forward is OFF (FIRE) and shows it | `safety_button`, `safety_red_dot` | built |
| M02 | M | p6 Fig. 4 | action lock lever: press it up to unlock and open the action without pulling the trigger | `action_lock_lever` | built |
| M03 | M | p13 Fig. 17, p17 Fig. 23 | cartridge stop (right wall) and cartridge interrupter (left wall), loose bars held by the trigger housing | `cartridge_stop`, `cartridge_interrupter` | built |
| M04 | M | p14 Fig. 19, p16 Fig. 21 | elevator: a fork with two arms and studs that pivot in the receiver; the front end lifts the shell | `elevator` | built |
| M05 | M | p14 Fig. 18, p17 Fig. 22 | bolt slide under the bolt, driven by notches in both action slide bars; bolt lock on the bolt | `bolt_slide`, `bolt_lock` | built |
| M06 | M | p14 Fig. 19, p16 Fig. 21 | bolt assembly, removed forwards through the barrel opening; ejector on the wall opposite the port | `bolt`, `ejector` | built |
| M07 | M | p13 Fig. 16, p18 Fig. 24 | trigger housing assembly lifts out rear first once its pin is pushed out; front lugs hook in receiver slots | `trigger_housing` | built |
| M08 | M | p28 and p30 parts lists | magazine follower and spring inside the tube | `magazine_follower` | built |
| M09 | M | p28 and p30 parts lists | magazine spring; retaining ring and washer of the swivel stud; action slide tube nut; hammer and the trigger housing's internals | - | omitted |
| M10 | M | p31 exploded view item 16 | action slide assembly: a tube over the magazine tube carrying both bars; the forend fits over it | `action_slide_tube` | built |

40 features: 34 built, 1 merged, 5 omitted. The omissions and their reasons are in `NOTES.md`.

## 3. Object studies

Each study is bound to its region and says what was measured and how.

- **Buttstock and pad (P01, P02).** Every 2 mm of length, the trace tool gives the top and bottom of the silhouette.
  The recipe lofts cross-sections through those two curves, so the comb line, the wrist and the belly are the photo's,
  not drawn by hand. The swivel stud is taken out of the lower curve with a five-point median and rebuilt as its own
  part. The pad is cut from the same loft along the slanted joint (top x 54, bottom x 75).
- **Receiver (P05, P06, P07, P23).** Top edge flat at y 30.5 from x 409 to 569, a bevel at the front, a slope at the
  rear on which the safety button sits; the silhouette there is the button's top, and the receiver surface is put
  2 to 3 px under it. Bottom edge at y 98.6. The joint to the stock is slanted (x 358 at the top, 368 at the bottom):
  one plane cuts both parts.
- **Barrel (P15).** Its top edge is traced at eight points: a collar at the receiver, a parallel chamber section, a
  taper from x 665 to 809, then parallel to the muzzle at 10.2 mm radius. The photo was first read as tilted by
  0.64 degrees from this edge; the edge is a taper, not a tilt, and the correction is in `NOTES.md`.
- **Magazine tube, ring, cap, lug band (P17, P20, P21, P22).** The tube's two edges give its axis (26.8 mm under the
  bore) and its diameter (23.2 mm). The ring and the band show no hoop over the barrel's top edge, so both are built as
  a ring around the tube joined to the barrel's underside by a web.
- **Forend (P19).** A body of revolution about the tube's axis (the ribs run round it), 21.7 mm in radius, its top
  cut flat under the barrel. About 19 ribs between x 735 and 850.
- **Trigger guard and trigger (P13, P14).** The guard's outer line is ten points read from the photo's rows; the blade
  is an eight-point outline.
- **The mechanism (M01 to M10).** The manual's figures give which parts exist, where they sit and how they come
  apart, but no dimensions. Their shapes are plain blocks sized to fit the traced receiver and to clear each other
  through the stroke (`model/checks.json`, `pump_clearance`). They are marked `manual` or `inferred` in the inventory.

## 4. Derived grammar

| Rule | Basis |
|---|---|
| One ruler: 0.9039 mm per photo pixel, origin at the receiver's front face on the bore axis. | Port front to muzzle = the published 20 in barrel (change request 1; version 1 used the overall length). See `NOTES.md`. |
| Barrel, magazine tube, cap, follower and forend are bodies of revolution on two parallel axes 26.8 mm apart. | Observed: straight parallel edges, ring ribs. |
| The forend, its inner tube and both action bars move as one (`slide_assembly`), straight back along the tube by the stroke. | Manual p14 (the forearm and action slide come off as one); the stroke is bounded by the photo: the forend's rear is 94.9 mm in front of the receiver. |
| The bolt slide moves with the action bars; the bolt follows after the lost motion that drops the bolt lock. | Manual p17 (the bolt slide's lugs sit in the bars' slots and its top lug fits the bolt lock). The 9.5 mm is a guess. |
| The elevator pivots on its studs at the hole under the port and lifts a shell from the tube's axis to the bore's. | Manual pp. 14 and 16; the hole is P10. The 22 degrees follows from 26.8 mm of lift over the elevator's length. |
| The safety slides along the receiver's rear slope: back is safe and covers the dot. | Manual p5. Travel (7 mm) is a guess. |
| Everything is symmetric about the vertical plane through the bore, except the ejection port and extractor (right), the ejector and its screw, the action lock lever and the interrupter (left), and the cartridge stop (right). | Observed (P, L) and manual pp. 13 and 16. |
| Widths: receiver 37.8 mm, stock 41.6 mm at the butt and 35 mm at the wrist, trigger guard 12 mm. | **Inferred.** No reference shows them. The receiver must hold the tube and a 12 gauge shell between two walls. |
| Materials are flat: parkerised steel, dark alloy, black polymer, rubber, brass. No textures, no wear, no markings. | The photo's matte finishes; markings are left off by rule. |

## 5. Recipe and comparison

`model/build.py` instantiates the parts above from these numbers. `model/tools/render.py` renders it in the photo's own
pixel grid and `model/tools/compare.py` measures the difference: see `COMPARE.md`.
