# Matched comparison: model against the reference photo

`renders/compare_right.jpg` shows the reference (public domain, see `REFERENCES.md`), the model rendered
orthographically in the same pixel grid, and the difference map. Numbers are in `model/compare.json`
(`model/tools/compare.py`). Run 2026-11-17 on the build of `model/build.py` at this commit.

Method: the photo's silhouette is every pixel darker than 200; the model's is the render's alpha. Both are 1148 x 263.
One pixel is 0.956 mm. The ruler was set from the photo's overall extent, so **overall length is a calibration, not a
result**; the shapes inside that length are the result.

## Silhouette

| Measure | Value |
|---|---|
| Intersection over union, whole gun | 0.974 |
| Photo only / model only | 1,354 px / 709 px of 77,691 |
| Top edge, per column | mean 0.28 mm, 95th percentile 0.96 mm, worst 4.8 mm at x 374 (the safety button) |
| Bottom edge, per column | mean 1.0 mm, 95th percentile 2.9 mm, worst 25.8 mm at x 29 (the one column at the butt's heel, 1 px wide) |

| Region (photo x) | IoU | What differs |
|---|---|---|
| Butt and pad (20 to 130) | 0.983 | The heel's corner; the pad's joint is a straight cut. |
| Stock (130 to 300) | 0.988 | The swivel stud is a simple post. |
| Wrist (300 to 365) | 0.973 | The lower curve is smoothed by the 4 mm loft spacing. |
| Receiver rear and trigger guard (365 to 470) | 0.924 | **Weakest.** The guard is a thin loop, so half a pixel either way costs a lot; the trigger's curve and the housing's rear corner are approximate; the safety button's profile is a wedge. |
| Receiver front and port (470 to 580) | 0.985 | - |
| Barrel root and action bars (580 to 683) | 0.980 | The collar's step is slightly high. |
| Forend (683 to 905) | 0.980 | The nose's lower corner is squarer than the photo's. |
| Barrel, tube, lug band (905 to 1055) | 0.970 | The lug's hook is a simplified notch; the band's fillets are missing. |
| Ring, cap, muzzle (1055 to 1125) | 0.934 | The cap's dome and the stud's tip are simplified. |

## Inside the silhouette, by eye

These are not measured.

| Feature | Photo | Model | Verdict |
|---|---|---|---|
| Ejection port | Rounded rectangle; bolt with a slot, a hole and the extractor's line | Sharp rectangle; plain bolt with a block for the extractor | Position and size match; detail missing |
| Receiver pins and holes | Housing pin, a plug, a hole under the port, two screws at the top edge | The same five, as plain discs | Positions from the photo; shapes plain |
| Forend ribs | About 19 fine ribs with rounded crests | 19 trapezoid ribs | Count and extent match |
| Recoil pad | Slanted vent slots | Plain | Omitted |
| Finish | Worn parkerising, specks, matte polymer with moulding texture | Flat clean materials | Not attempted |
| Lighting | Frontal flash on white | Soft studio | Not matched |
| Markings | None legible on this side | None | - |

## What this comparison cannot show

Only the right side has a reference. The left side's controls are placed from a photo of a different model; the top
and front have no reference at all, so widths are inferred. A three-quarter render looking right is not evidence.

## Model against the manual

| Manual | Model | Note |
|---|---|---|
| Safety: back is safe and covers the red dot, forward is fire (p5) | `safety_button` slides 7 mm; `safety_red_dot` is under its rear position | OK; travel is a guess |
| Action lock lever on the left behind the guard (p6) | `action_lock_lever`, clip `action_release` | OK; placed from the 590A1 photo |
| 590 barrel held by the magazine cap over the tube (pp. 6, 11) | `barrel_ring` over `magazine_tube`, `magazine_cap` | OK |
| First shell through the port onto the elevator (p8) | `socket_load`, `socket_lifter`, `loadThroughPort()` | OK |
| Rim snaps past the cartridge stop (p9) | `cartridge_stop`, clip and sound `shell_insert` | OK; the stop does not animate |
| Fully rearward ejects and releases the next shell; fully forward chambers (pp. 9, 10) | clips `pump_back`, `pump_forward`, `pump_stroke`; events in `action.json` | OK |
| Takedown order (pp. 10 to 14) | clip `takedown` in the same order; `renders/exploded.jpg` | OK as a sequence; the bolt slide lifts straight out instead of being tipped |
| Trigger housing lifts out rear first (p13) | `trigger_housing_group` rotates about its front | OK |
| Capacity (p8; maker: nine in all) | Tube holds eight 2 3/4 in shells by the model's own length | OK |
| Function test (p20) | `action/test_action.js`, first five checks | OK |

## Verdict

The right-side outline follows the photo closely (IoU 0.974, edges within about 1 mm on average). That is a result
about one view. Internal detail is schematic, the other views are inferred, the barrel-length question in
`NOTES.md` is open, and the owner has not reviewed it.
