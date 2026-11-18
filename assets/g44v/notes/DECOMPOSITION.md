# G44 V: source-indexed decomposition

Written by `model/tools/make_notes.py` from `model/inventory.json`. One row per object the recipe builds. "No." is the item number of the manual's component
list and exploded drawing (pp. 36-37). Status: **traced** = an outline polygon traced from the maker's dimension image (`model/outlines.json`, pixel coordinates kept);
**measured** = read off a named picture with the stated ruler; **published** = the maker's specification table; **inferred** = not visible or not legible in any source,
built from how the part must work (each one is a stated guess). Positions are mm: L from the slide's rear face toward the muzzle, Z up from the bore axis.

| No. | Object | Status | Source region and evidence | Pivot (L, S, Z) | Extent L | Extent Z | Material |
|---|---|---|---|---|---|---|---|
| 1 | `p01_slide` | traced | traced: outlines.json slide; underside p. 27 picture 30; top view p. 23 picture 27 | 0.0, 0.0, 0.0 | -0.0 to 173.6 | -17.5 to 11.8 | PolymerSlide |
| 1 | `p01_slide_guide_rail_l` | measured | dimension image px x 222-1157, y 258-288 | 80.9, 12.8, -6.0 | 0.1 to 161.7 | -8.6 to -3.5 | SteelDark |
| 1 | `p01_slide_guide_rail_r` | measured | dimension image px x 222-1157, y 258-288 | 80.9, -12.8, -6.0 | 0.1 to 161.7 | -8.6 to -3.5 | SteelDark |
| - | `placeholder_panel_slide_logo` | measured | dimension image px 493-560, 197-248: maker's mark replaced by a plain panel | 109.1, 12.8, 2.7 | 103.3 to 114.9 | -1.7 to 7.1 | Placeholder |
| - | `placeholder_panel_slide_text` | measured | dimension image px 585-835, 205-240: model and calibre text replaced by a plain panel | 77.4, 12.8, 2.7 | 55.8 to 99.0 | -0.3 to 5.7 | Placeholder |
| 16a | `p16a_front_sight` | traced | traced: outlines.json front_sight | 163.0, 0.0, 14.2 | 160.4 to 167.4 | 11.7 to 15.6 | Polymer |
| 16a | `p16a_front_sight_dot` | measured | white dot (manual p. 23 picture 27) | 160.3, 0.0, 14.0 | 160.2 to 160.5 | 13.0 to 15.0 | SightWhite |
| 16b | `p16b_front_sight_screw` | inferred | exploded drawing: screw under the front sight | 163.8, -0.0, 10.1 | 162.0 to 165.6 | 8.2 to 11.7 | Steel |
| 15 | `p15_rear_sight` | traced | traced: outlines.json rear_sight; width 17 mm from the top view | 10.0, 0.0, 14.4 | 2.7 to 15.6 | 11.7 to 16.2 | Polymer |
| 15 | `p15_rear_sight_outline` | measured | white notch outline (rear view) | 2.7, 0.0, 14.2 | 2.6 to 2.8 | 12.9 to 15.9 | SightWhite |
| 14 | `p14_slide_cover_plate` | measured | rear view; exploded drawing | 0.8, 0.0, -1.1 | -0.0 to 1.7 | -9.2 to 6.9 | Polymer |
| 4 | `p04_firing_pin` | measured | lug measured in the underside photo (L 19-23 in the fired position, p. 27); manual p. 30 picture 34; shaft and tip inferred | 19.0, 0.0, 2.6 | 11.5 to 66.3 | -11.6 to 4.5 | Steel |
| 5 | `p05_spacer_sleeve` | inferred | exploded drawing item 5 | 16.1, 0.0, 2.6 | 2.2 to 30.0 | -0.1 to 5.3 | Polymer |
| 6 | `p06_firing_pin_spring` | inferred | exploded drawing item 6 | 30.2, 0.0, 2.6 | 30.5 to 44.0 | 0.2 to 5.0 | Spring |
| 7 | `p07_spring_cups` | inferred | exploded drawing item 7 (two half cups) | 53.2, 0.0, 2.6 | 44.5 to 47.0 | -0.1 to 5.3 | Steel |
| 8 | `p08_firing_pin_safety` | measured | underside photo: plunger at L 64-68.5, 4.4 mm right of centre | 66.0, -4.4, -9.6 | 63.6 to 68.4 | -9.6 to -3.6 | Steel |
| 9 | `p09_firing_pin_safety_spring` | inferred | exploded drawing item 9 | 66.0, -4.4, 5.5 | 64.3 to 67.7 | -3.3 to 5.3 | Spring |
| 10 | `p10_extractor` | inferred | exploded drawing item 10; claw named in manual p. 30 picture 34; shape inferred | 62.0, -11.0, 3.0 | 60.8 to 74.3 | -0.9 to 5.7 | Steel |
| 11 | `p11_extractor_depressor_plunger` | inferred | exploded drawing item 11 | 40.0, -8.0, 5.5 | 20.5 to 59.8 | 4.0 to 7.0 | Steel |
| 12 | `p12_extractor_depressor_plunger_spring` | inferred | exploded drawing item 12 | 14.2, -8.0, 5.5 | 8.2 to 20.2 | 4.2 to 6.8 | Spring |
| 13 | `p13_spring_loaded_bearing` | inferred | exploded drawing item 13 | 5.0, -8.0, 5.5 | 1.9 to 8.0 | 4.0 to 7.0 | Polymer |
| 2 | `p02_barrel` | measured | length published; tube diameter and muzzle measured (p. 21 picture 18); hood measured in the top view; lugs inferred from the exploded drawing and p. 32 | 161.5, 0.0, 0.0 | 73.0 to 174.3 | -16.0 to 9.5 | SteelDark |
| - | `placeholder_panel_barrel_hood` | measured | hood markings (manual p. 8 pictures 2-3) replaced by a plain panel | 90.5, -0.8, 9.5 | 80.0 to 101.0 | 9.4 to 9.6 | Placeholder |
| 3 | `p03_recoil_spring_assembly` | inferred | exploded drawing item 3; manual p. 23 pictures 24-25; a dual captive spring simplified to one rod and one spring | 96.5, 0.0, -11.3 | 96.7 to 165.5 | -15.1 to -7.5 | Steel |
| 3 | `p03_recoil_spring` | inferred | as above; 24 coils of 0.8 mm wire are a modelling choice (solid length must fit the stroke) | 98.1, 0.0, -11.3 | 98.6 to 165.9 | -15.1 to -7.5 | Spring |
| 17 | `p17_frame` | traced | traced: outlines.json frame and guard_hole; width from the rear view; cavities inferred | 0.0, 0.0, 0.0 | -9.9 to 172.9 | -106.0 to -9.6 | Polymer |
| - | `placeholder_panel_grip_l` | measured | dimension image px 1030-1095, 660-715: maker's mark on the grip replaced by a plain panel | 16.4, 14.6, -77.7 | 10.8 to 22.0 | -82.5 to -73.0 | Placeholder |
| 17 | `p17_frame_guide_rear_l` | inferred | manual p. 6 (steel guides in the polymer frame); position inferred | 36.0, 9.8, -8.5 | 30.0 to 42.0 | -10.6 to -6.6 | SteelDark |
| 17 | `p17_frame_guide_front_l` | inferred | manual p. 6 (steel guides in the polymer frame); position inferred | 113.0, 9.8, -8.5 | 108.0 to 118.0 | -10.6 to -6.6 | SteelDark |
| - | `placeholder_panel_grip_r` | measured | dimension image px 1030-1095, 660-715: maker's mark on the grip replaced by a plain panel | 16.4, -14.6, -77.7 | 10.8 to 22.0 | -82.5 to -73.0 | Placeholder |
| 17 | `p17_frame_guide_rear_r` | inferred | manual p. 6 (steel guides in the polymer frame); position inferred | 36.0, -9.8, -8.5 | 30.0 to 42.0 | -10.6 to -6.6 | SteelDark |
| 17 | `p17_frame_guide_front_r` | inferred | manual p. 6 (steel guides in the polymer frame); position inferred | 113.0, -9.8, -8.5 | 108.0 to 118.0 | -10.6 to -6.6 | SteelDark |
| 28 | `p28_trigger_pin` | measured | dimension image px (682, 350) | 82.2, 0.0, -19.4 | 80.2 to 84.2 | -21.4 to -17.4 | Steel |
| 29 | `p29_trigger_housing_pin` | measured | dimension image px (1047, 440); manual p. 38 | 19.1, 0.0, -34.9 | 17.6 to 20.6 | -36.4 to -33.4 | Polymer |
| 22 | `p22_locking_block` | inferred | exploded drawing item 22; position from the trigger pin and slide lock in the dimension image | 92.1, 0.0, -17.8 | 76.0 to 98.6 | -23.5 to -10.2 | Steel |
| 21 | `p21_slide_lock` | measured | dimension image px 602-640, 310-355; manual p. 22 picture 23 | 93.1, 0.0, -17.0 | 89.5 to 96.0 | -21.0 to -12.4 | Steel |
| 20 | `p20_slide_lock_spring` | inferred | exploded drawing item 20 | 93.1, 0.0, -24.9 | 92.0 to 94.2 | -24.7 to -21.3 | Spring |
| 23 | `p23_trigger_mechanism_housing` | inferred | exploded drawing item 23; ejector named in manual p. 31 picture 35; shape inferred | 21.4, 0.0, -26.0 | 11.0 to 58.0 | -38.5 to -0.8 | Polymer |
| 24 | `p24_connector` | inferred | exploded drawing item 24; manual p. 28 picture 32 (right rear corner of the frame); simplified to a strip | 18.5, -10.9, -17.2 | 14.0 to 23.0 | -18.3 to -16.2 | Steel |
| 26 | `p26_trigger` | traced | traced: outlines.json trigger; hub to the pin inferred | 82.2, 0.0, -19.4 | 70.3 to 91.2 | -48.4 to -16.2 | Polymer |
| 26 | `p26_trigger_safety` | inferred | manual p. 7 and p. 9 (trigger safety lever in the trigger); the traced outline is the blade, 2 mm proud of the trigger face | 81.6, 0.0, -34.0 | 80.6 to 91.5 | -45.0 to -34.0 | Polymer |
| 26 | `p26_trigger_bar` | inferred | manual p. 7 (trigger bar: holds the firing pin, lifts the firing pin safety, drops on the ramp); exploded drawing item 26; routing inferred | 79.5, -5.0, -28.2 | 9.0 to 81.0 | -29.8 to -9.9 | Steel |
| 27 | `p27_slide_stop_lever` | measured | dimension image px 815-870, 290-325 (pad); rear view shows a pad on each side; arms inferred | 82.2, 0.0, -19.4 | 49.7 to 85.6 | -22.8 to -9.9 | Steel |
| 19 | `p19_magazine_catch` | measured | dimension image px 800-880, 455-515 (pad); manual p. 40; bar and nib inferred | 62.0, 0.0, -42.5 | 48.0 to 64.4 | -47.9 to -37.5 | Polymer |
| 18 | `p18_magazine_catch_spring` | inferred | manual p. 40 pictures 53-54: a straight wire in the front strap | 54.6, 0.0, -63.8 | 47.3 to 61.8 | -81.2 to -46.5 | Spring |
| 17 | `p17_frame_grip_texture_l` | measured | dimension image: studded grip panel, patch outline px (880,500)...(850,540), maker's mark window left clear | 0.0, 0.0, 0.0 | -2.0 to 53.1 | -97.8 to -40.5 | Polymer |
| 17 | `p17_frame_grip_texture_r` | measured | dimension image: studded grip panel, patch outline px (880,500)...(850,540), maker's mark window left clear | 0.0, 0.0, 0.0 | -2.0 to 53.1 | -97.8 to -40.5 | Polymer |
| 17c | `p17c_beavertail_backstrap_m` | inferred | constructed: the traced rear strap grown by 2 / 4 mm (manual p. 38) with the beavertail of p. 9; not traced | -26.0, 0.0, 0.0 | -39.2 to -5.8 | -97.7 to -9.5 | Polymer |
| 17d | `p17d_beavertail_backstrap_l` | inferred | constructed: the traced rear strap grown by 2 / 4 mm (manual p. 38) with the beavertail of p. 9; not traced | -44.0, 0.0, 0.0 | -59.3 to -23.8 | -97.7 to -9.5 | Polymer |
| 31 | `p31_magazine_tube` | inferred | exploded drawing item 31; rake from the traced front strap; depth and width inferred | 37.6, 0.0, -60.0 | 5.6 to 69.9 | -105.3 to -12.0 | Polymer |
| - | `placeholder_panel_magazine` | measured | maker's mark on the tube in the exploded drawing replaced by a plain panel | 23.6, -9.6, -94.0 | 17.6 to 29.6 | -98.0 to -90.0 | Placeholder |
| 35 | `p35_magazine_floor_plate` | traced | traced: outlines.json floor_plate; width 31.5 mm from the rear view | 17.2, 0.0, -106.1 | -0.7 to 42.5 | -109.4 to -101.0 | Polymer |
| 34 | `p34_magazine_insert` | inferred | exploded drawing item 34 | 20.4, 0.0, -101.2 | 7.5 to 33.3 | -103.6 to -98.8 | Polymer |
| 32 | `p32_follower` | measured | manual p. 11 picture 4 (orange) and p. 31 picture 36; the shelf that lifts the slide stop lever is inferred | 53.6, 0.0, -20.0 | 37.6 to 67.5 | -28.4 to -14.1 | FollowerOrange |
| 48 | `p48_loading_assist_right` | measured | exploded drawing items 48 / 49; manual p. 11 pictures 4-5 | 50.6, -10.0, -27.5 | 45.7 to 54.3 | -33.3 to -24.7 | Polymer |
| 49 | `p49_loading_assist_left` | measured | exploded drawing items 48 / 49; manual p. 11 pictures 4-5 | 50.6, 10.0, -27.5 | 45.7 to 54.3 | -33.3 to -24.7 | Polymer |
| 33 | `p33_magazine_spring` | measured | exploded drawing item 33: about ten zig-zags | 22.2, 0.0, -98.5 | 14.2 to 58.2 | -99.3 to -28.6 | Spring |

Objects by status: inferred 26, measured 25, traced 6. Manual items modelled: 38 of 38 (items 25 and 30 are blank in the manual).

## Numbers

| Parameter | Value | Status | Source |
|---|---|---|---|
| `slide_len` | 174 | published | spec table dim 2; traced 173.6 |
| `slide_half_w` | 12.75 | published | spec table dim 4: 25.5 mm |
| `slide_top` | 11.755 | traced | dimension image y = 170 |
| `slide_bot` | -9.2 | traced | parting line y = 291 (ZY = -9.16) |
| `frame_top` | -9.6 | traced | parting line, 0.4 mm running gap (inferred gap) |
| `frame_half_w` | 14.6 | measured | rear view: 163-168 px at 5.647 px/mm (slide width 144 px = 25.5 mm) -> 29.0-29.8 mm |
| `breech_face` | 73 | measured | slide underside photo (manual p. 27 picture 30): 1500-1560 px of 3610 px = 174 mm; agrees with muzzle - barrel length |
| `port_front` | 105 | measured | slide top view (manual p. 23 picture 27): 397 px at 3.494 px/mm |
| `port_left` | 7.7 | measured | slide top view: hood visible to 27 px left of the centre line |
| `port_bottom` | -1 | inferred | right-side port lower edge about mid height (manual p. 23 picture 26, oblique) |
| `barrel_len` | 102 | published | spec table |
| `muzzle` | 174.3 | measured | dimension image: muzzle at px 150, 0.6 mm proud of the traced slide face (px 153.5) |
| `barrel_od` | 13 | measured | lock-open photo: exposed tube 36 px at 2.78 px/mm |
| `bore_groove_d` | 5.6 | published | .22 LR groove diameter 0.2205 in nominal (SAAMI Z299.1 rimfire) |
| `chamber_block_top` | 9.5 | inferred | hood sits recessed below the slide top (close-up, manual p. 8 pictures 2-3); must pass under the slide roof in recoil |
| `rsa_axis` | -11.3 | inferred | guide rod under the barrel, seated on the barrel lug (manual p. 32 pictures 38-40); height from the nose ring in p. 23 picture 26 |
| `lock_open_travel` | 42 | measured | lock-open photo p. 21 picture 18: slide face 110 px behind the frame face at 2.78 px/mm + 2.6 mm; rear check 42.4 |
| `full_travel` | 45 | inferred | lock-open + 3 mm over-travel so the stop can rise into its notch; not measurable from the photos |
| `takedown_retract` | 3 | published | manual p. 22 step 8: about 1/8 in / 3 mm |
| `slide_lock_pull` | 3.5 | inferred | enough for the plate to clear the barrel lug in this model |
| `trigger_pin` | [82.1953327571305, -19.360414866032844] | measured | dimension image: pin centre px (682, 350) |
| `housing_pin` | [19.101123595505616, -34.91789109766638] | measured | dimension image: pin centre px (1047, 440) |
| `trigger_break_deg` | 7.5 | inferred | the traced blade can swing 7.75 deg before it meets the traced guard opening (inventory.json kinematics.trigger_max_deg); real travel is not published |
| `trigger_takeup_deg` | 4.5 | inferred | Safe Action pattern: take-up to a wall, then break |
| `trigger_safety_deg` | 10 | inferred | blade tip flush with the trigger face when pressed |
| `bar_link_r` | 9 | inferred | trigger bar pinned 9 mm below the trigger pin |
| `striker_precock` | 7.5 | inferred | firing pin held part-cocked by the trigger bar with the trigger forward (Safe Action, manual p. 7) |
| `bar_drop` | 0.9 | inferred | the bar's tab overlaps the firing pin lug by 0.7 mm in this model; the drop clears it by 0.2 mm |
| `fp_safety_lift` | 1.5 | inferred | manual p. 7: the trigger bar pushes the firing pin safety up |
| `stop_lift_deg` | 3.7 | inferred | 2 mm rise at the nose, 31 mm behind the pivot |
| `mag_catch_press` | 2.4 | inferred | nib must leave the corner notch of the magazine |
| `follower_travel` | 78 | inferred | count windows 5 / 10 / 15 on the tube in the exploded drawing: about 27 mm per 5 rounds |
| `mag_capacity` | 15 | published | spec table: standard 15, optional 10 |
| `sight_radius` | 158 | published | spec table dim 6, adjustable polymer rear sight; dimension line measures 157.6 |
| `eye_relief` | 450 | inferred | eye to rear sight at arm's length |

## Sockets

| Socket | Parent | L, S, Z (mm) | What it is |
|---|---|---|---|
| `socket_beavertail_backstrap_m` | `frame_group` | -0.0, 0.0, 0.0 | installed position of p17c_beavertail_backstrap_m |
| `socket_beavertail_backstrap_l` | `frame_group` | -0.0, 0.0, 0.0 | installed position of p17d_beavertail_backstrap_l |
| `socket_muzzle` | `frame_group` | 174.3, 0.0, 0.0 | bore axis at the muzzle crown |
| `socket_chamber` | `frame_group` | 73.0, 0.0, 0.0 | bore axis at the breech face in battery |
| `socket_eject` | `frame_group` | 89.0, -12.8, 3.0 | centre of the ejection port, right side |
| `socket_ads_eye` | `frame_group` | -447.4, 0.0, 15.9 | on the sight line (top of the front and rear sights), arm's length behind the rear sight (inferred 450 mm) |
| `socket_front_sight` | `slide_group` | 160.3, 0.0, 15.9 | top rear edge of the front sight |
| `socket_rear_sight` | `slide_group` | 2.6, 0.0, 15.9 | top rear edge of the rear sight |
| `socket_hand_right` | `frame_group` | 16.0, 0.0, -52.0 | firing hand: middle of the grip, web of the hand under the tang |
| `socket_hand_left` | `frame_group` | 40.0, 0.0, -62.0 | support hand: wrapped over the firing hand on the front strap |
| `socket_trigger_finger` | `frame_group` | 83.9, 0.0, -30.6 | trigger face where the spec table measures the trigger distance (px 672, 415) |
| `socket_magazine` | `frame_group` | 19.2, 0.0, -106.0 | mouth of the magazine well; +Y of the magazine axis is tilted 21.8 deg |
| `socket_rail` | `frame_group` | 141.3, 0.0, -23.2 | accessory rail under the dust cover (manual p. 9: mounting rail) |

## Clips (30 fps)

| Clip | Frames | Moving nodes | Interpenetrating pairs |
|---|---|---|---|
| `trigger_safety` | 20 | `p26_trigger_safety` | 0 |
| `trigger_pull` | 30 | `p04_firing_pin`, `p06_firing_pin_spring`, `p08_firing_pin_safety`, `p09_firing_pin_safety_spring`, `p26_trigger`, `p26_trigger_bar`, `p26_trigger_safety` | 0 |
| `slide_cycle` | 24 | `p01_slide`, `p03_recoil_spring`, `p04_firing_pin`, `p06_firing_pin_spring` | 0 |
| `slide_lock_open` | 24 | `p01_slide`, `p03_recoil_spring`, `p27_slide_stop_lever`, `p32_follower`, `p33_magazine_spring` | 0 |
| `slide_release` | 16 | `p01_slide`, `p03_recoil_spring`, `p27_slide_stop_lever` | 0 |
| `magazine_out` | 30 | `p19_magazine_catch`, `p31_magazine_tube`, `p32_follower`, `p33_magazine_spring` | 0 |
| `magazine_in` | 30 | `p19_magazine_catch`, `p31_magazine_tube`, `p32_follower`, `p33_magazine_spring` | 0 |
| `field_strip` | 150 | `p01_slide`, `p02_barrel`, `p03_recoil_spring`, `p03_recoil_spring_assembly`, `p04_firing_pin`, `p06_firing_pin_spring`, `p08_firing_pin_safety`, `p09_firing_pin_safety_spring`, `p20_slide_lock_spring`, `p21_slide_lock`, `p26_trigger`, `p26_trigger_bar`, `p26_trigger_safety`, `p31_magazine_tube`, `p32_follower`, `p33_magazine_spring` | 0 |

## Pairs fixed to each other (skipped by the interpenetration check)

- `p17_frame_grip_texture_l` on `p17_frame`: moulded texture
- `p17_frame_grip_texture_r` on `p17_frame`: moulded texture
- `placeholder_panel_slide_logo` on `p01_slide`: placeholder panel set into the surface
- `placeholder_panel_slide_text` on `p01_slide`: placeholder panel set into the surface
- `placeholder_panel_barrel_hood` on `p02_barrel`: placeholder panel set into the surface
- `placeholder_panel_grip_l` on `p17_frame`: placeholder panel set into the surface
- `placeholder_panel_grip_r` on `p17_frame`: placeholder panel set into the surface
- `placeholder_panel_magazine` on `p31_magazine_tube`: placeholder panel set into the surface
- `p01_slide_guide_rail_l` on `p01_slide`: steel rail moulded into the slide
- `p01_slide_guide_rail_r` on `p01_slide`: steel rail moulded into the slide
- `p16a_front_sight` on `p01_slide`: sight seated on the slide
- `p15_rear_sight` on `p01_slide`: sight seated on the slide
- `p16a_front_sight_dot` on `p16a_front_sight`: painted dot
- `p15_rear_sight_outline` on `p15_rear_sight`: painted outline
- `p16b_front_sight_screw` on `p01_slide`: screw through the slide roof
- `p16b_front_sight_screw` on `p16a_front_sight`: screw into the sight
- `p35_magazine_floor_plate` on `p31_magazine_tube`: floor plate slid onto the tube
- `p34_magazine_insert` on `p35_magazine_floor_plate`: insert locks the floor plate
- `p34_magazine_insert` on `p31_magazine_tube`: insert seated in the tube
- `p48_loading_assist_right` on `p32_follower`: button fixed to the follower
- `p49_loading_assist_left` on `p32_follower`: button fixed to the follower
- `p33_magazine_spring` on `p34_magazine_insert`: spring seated on the insert
- `p33_magazine_spring` on `p32_follower`: spring seated under the follower
- `p07_spring_cups` on `p04_firing_pin`: cups clipped onto the firing pin
- `p17_frame_guide_rear_l` on `p17_frame`: steel guide moulded into the frame
- `p17_frame_guide_front_l` on `p17_frame`: steel guide moulded into the frame
- `p17_frame_guide_rear_r` on `p17_frame`: steel guide moulded into the frame
- `p17_frame_guide_front_r` on `p17_frame`: steel guide moulded into the frame
