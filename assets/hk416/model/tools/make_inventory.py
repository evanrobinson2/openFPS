"""Detail inventory for the HK416, written BEFORE any modelling (brief, Method step 1).
Each row: region, feature, seen_in (reference codes), part_name, and for merged features the reason.
Run: python3 tools/make_inventory.py  -> inventory.json"""
import json, os
R = {'RP': 'profile-right-photo.png', 'DR': 'profile-both-sides-drawing.jpg (right side, bottom)',
     'DL': 'profile-both-sides-drawing.jpg (left side, top)', 'LP': 'profile-left-photo-416N.jpg',
     'CR': 'closeup-right-receiver.jpg', 'CL': 'closeup-left-lower-controls.jpg', 'CF': 'closeup-front-sight.jpg',
     'CS': 'closeup-rear-sight-charging-handle.jpg', 'CH': 'closeup-handguard-front.jpg'}
rows = []
def f(region, feature, seen, part, merge=None):
    d = dict(region=region, feature=feature, seen_in=[R[s] for s in seen.split()], part_name=part)
    if merge: d['merged'] = True; d['merge_reason'] = merge
    rows.append(d)
VOID = 'a void: cut into the host part with a boolean, so it has no solid of its own'
ONE = 'one physical piece with the host on the real rifle (a turned or moulded feature), modelled in the host mesh'

# ---------------------------------------------------------------- muzzle device
g = 'muzzle device'
f(g, 'birdcage flash hider body', 'RP DR DL LP CH', 'flash_hider')
for i in range(1, 7): f(g, f'flash hider slot {i} of 6 (side slots show daylight)', 'RP DR LP', 'flash_hider', VOID)
f(g, 'flash hider wrench flat, right', 'RP', 'flash_hider', VOID)
f(g, 'flash hider wrench flat, left', 'LP', 'flash_hider', VOID)
f(g, 'flash hider front chamfer and open mouth', 'RP CH', 'flash_hider', ONE)
f(g, 'crush washer behind the flash hider', 'RP DR', 'crush_washer')
f(g, 'jam ring / thread shoulder ring', 'RP DR', 'muzzle_jam_ring')
f(g, 'muzzle crown and bore opening (dark, bore not modelled)', 'CH', 'muzzle_bore')
# ---------------------------------------------------------------- barrel
g = 'barrel'
f(g, 'barrel, 14.5 in', 'RP DR DL LP CH CF', 'barrel')
f(g, 'barrel shoulder in front of the gas block', 'RP', 'barrel', ONE)
f(g, 'barrel necked section (grenade-launcher style cut)', 'RP', 'barrel', ONE)
f(g, 'barrel muzzle shoulder before the threads', 'RP', 'barrel', ONE)
f(g, 'barrel section under the handguard (seen through the vents)', 'RP CH', 'barrel', ONE)
f(g, 'barrel nut (seen through the rear vents)', 'CR', 'barrel_nut')
f(g, 'gas block', 'RP DR LP CF', 'gas_block')
f(g, 'gas block cross pin, front', 'RP', 'gas_block_pin_1')
f(g, 'gas block cross pin, rear', 'RP', 'gas_block_pin_2')
f(g, 'gas regulator plug at the front of the gas block', 'RP LP', 'gas_regulator')
f(g, 'gas piston housing above the barrel (seen through the top vents)', 'RP CH', 'gas_piston_tube')
f(g, 'bayonet lug under the gas block', 'RP LP', 'bayonet_lug')
# ---------------------------------------------------------------- front sight
g = 'front sight'
f(g, 'front sight base on the gas block', 'RP DR LP CF', 'front_sight_base')
f(g, 'folding front sight arm', 'RP DR DL LP CF CH', 'front_sight_arm')
f(g, 'front sight post', 'RP LP', 'front_sight_post')
f(g, 'front sight protective ear, left', 'LP CF', 'front_sight_ear_l')
f(g, 'front sight protective ear, right', 'RP CF', 'front_sight_ear_r')
f(g, 'front sight pivot pin head, left', 'CF', 'front_sight_pivot_head_l')
f(g, 'front sight pivot pin head, right', 'RP CF', 'front_sight_pivot_head_r')
f(g, 'front sight lock detent button', 'CF', 'front_sight_detent')
f(g, 'front sight base clamp screw (hex socket)', 'CF', 'front_sight_base_screw')
# ---------------------------------------------------------------- handguard
g = 'handguard'
f(g, 'quad-rail handguard body (octagonal free-float tube)', 'RP DR DL LP CH', 'handguard_body')
for side, seen in (('right', 'RP DR'), ('left', 'DL LP')):
    for row in ('upper', 'lower'):
        for i in range(1, 5):
            f(g, f'lightening vent {i} of 4, {row} row, {side} side', seen, 'handguard_body', VOID)
    f(g, f'sling crescent slot under the front QD cup, {side}', seen, 'handguard_body', VOID)
f(g, 'handguard bore (barrel and piston run inside)', 'CH', 'handguard_body', VOID)
for rail, seen in (('top', 'RP DR DL LP CF CH'), ('bottom', 'RP DR DL LP'), ('left', 'DL LP CH'), ('right', 'RP DR')):
    f(g, f'{rail} rail rear block', seen, f'hg_rail_{rail}_rear_block')
    for i in range(1, 20):
        f(g, f'{rail} rail lug {i:02d} and the slot behind it (MIL-STD-1913, 10.0 mm pitch)', seen, f'hg_rail_{rail}_lug_{i:02d}')
    f(g, f'{rail} rail front block', seen, f'hg_rail_{rail}_front_block')
f(g, 'retaining-bolt boss, right', 'RP DR', 'hg_bolt_boss_r')
f(g, 'retaining-bolt boss, left', 'DL LP', 'hg_bolt_boss_l')
f(g, 'handguard retaining bolt head (hex socket), right', 'RP DR', 'hg_retaining_bolt')
f(g, 'handguard retaining bolt end, left', 'DL LP', 'hg_retaining_bolt_nut')
f(g, 'front QD sling cup, right', 'RP DR', 'hg_qd_cup_r')
f(g, 'front QD sling cup, left', 'DL LP CF CH', 'hg_qd_cup_l')
f(g, 'handguard front cap ring', 'RP CH CF', 'hg_front_cap')
f(g, 'index screw at the top rear, right', 'DR', 'hg_index_screw_r')
f(g, 'index screw at the top rear, left', 'DL', 'hg_index_screw_l')
f(g, 'small screw near the front, lower right', 'DR', 'hg_front_screw_r')
f(g, 'small screw near the front, lower left', 'DL', 'hg_front_screw_l')
# ---------------------------------------------------------------- upper receiver
g = 'upper receiver'
f(g, 'upper receiver body', 'RP DR DL LP CR CS CL', 'upper_body')
f(g, 'ejection port opening', 'CR', 'upper_body', VOID)
f(g, 'bolt carrier bore (dark cavity behind the port)', 'CR', 'upper_body', VOID)
f(g, 'charging handle channel', 'CS', 'upper_body', VOID)
f(g, 'flat-top rail base with dovetail undercut', 'RP CS CR', 'upper_body', ONE)
for i in range(1, 11):
    f(g, f'receiver rail lug {i:02d} and the slot behind it', 'RP DR DL LP CS CR', f'upper_rail_lug_{i:02d}')
f(g, 'receiver rail front block (bridges to the handguard rail)', 'RP DR', 'upper_rail_front_block')
f(g, 'receiver rail rear block under the rear sight', 'RP CS', 'upper_rail_rear_block')
f(g, 'brass deflector', 'RP DR CR', 'brass_deflector')
f(g, 'forward assist housing', 'RP DR CR', 'forward_assist_housing')
f(g, 'forward assist button', 'RP CR', 'forward_assist_button')
f(g, 'forward assist roll pin', 'CR', 'forward_assist_pin')
f(g, 'dust cover hinge lug, front', 'CR', 'upper_hinge_lug_front')
f(g, 'dust cover hinge lug, rear', 'CR', 'upper_hinge_lug_rear')
f(g, 'dust cover hinge rod', 'RP CR', 'dust_cover_hinge_rod')
f(g, 'dust cover rod C-clip', 'CR', 'dust_cover_rod_clip')
f(g, 'dust cover', 'RP CR', 'dust_cover')
f(g, 'dust cover hinge knuckle, front', 'CR', 'dust_cover_knuckle_1')
f(g, 'dust cover hinge knuckle, rear', 'CR', 'dust_cover_knuckle_2')
f(g, 'dust cover latch housing', 'RP CR', 'dust_cover_latch')
f(g, 'dust cover stamped rib, front', 'RP CR', 'dust_cover_rib_1')
f(g, 'dust cover stamped rib, rear', 'RP CR', 'dust_cover_rib_2')
f(g, 'dust cover torsion spring', 'CR', 'dust_cover_spring')
f(g, 'bolt carrier outer face (through the port)', 'CR', 'bolt_carrier')
f(g, 'bolt carrier forward-assist serrations', 'CR', 'bolt_carrier_serrations')
f(g, 'bolt carrier vent hole, front', 'CR', 'bolt_carrier_vent_1')
f(g, 'bolt carrier vent hole, rear', 'CR', 'bolt_carrier_vent_2')
f(g, 'bolt head at the front of the port', 'CR', 'bolt_head')
f(g, 'teardrop boss on the left side', 'CS', 'upper_left_boss')
f(g, 'horizontal rib along the left side', 'DL LP CL', 'upper_rib_l')
f(g, 'horizontal rib along the right side', 'RP DR CR', 'upper_rib_r')
f(g, 'upper/lower parting line', 'RP DR DL CL CR', 'upper_body', 'a seam: it is the real gap between upper_body and lower_body')
# ---------------------------------------------------------------- rear sight
g = 'rear sight'
f(g, 'rear sight base', 'RP DR DL LP CS', 'rear_sight_base')
f(g, 'rear sight pivot lug, left', 'CS', 'rear_sight_lug_l')
f(g, 'rear sight pivot lug, right', 'RP', 'rear_sight_lug_r')
f(g, 'folding rear sight arm', 'RP DR DL CS', 'rear_sight_arm')
f(g, 'rear sight aperture', 'CS', 'rear_sight_aperture')
f(g, 'windage knob', 'RP CS', 'rear_sight_windage_knob')
f(g, 'windage screw end, left', 'CS', 'rear_sight_windage_screw')
f(g, 'rear sight pivot pin head, left', 'CS', 'rear_sight_pivot_head_l')
f(g, 'rear sight pivot pin head, right', 'RP', 'rear_sight_pivot_head_r')
f(g, 'rail clamp bar', 'CS', 'rear_sight_clamp_bar')
f(g, 'clamp screw head (hex socket)', 'CS DR', 'rear_sight_clamp_screw')
f(g, 'clamp nut', 'RP', 'rear_sight_clamp_nut')
f(g, 'rear sight lock detent', 'CS', 'rear_sight_detent')
# ---------------------------------------------------------------- charging handle
g = 'charging handle'
f(g, 'charging handle (T handle and shaft)', 'RP DL LP CS', 'charging_handle')
f(g, 'charging handle latch', 'LP CS', 'charging_handle_latch')
f(g, 'charging handle latch roll pin', 'CS', 'charging_handle_latch_pin')
# ---------------------------------------------------------------- lower receiver
g = 'lower receiver'
f(g, 'lower receiver body', 'RP DR DL LP CL CR', 'lower_body')
f(g, 'magazine well cavity', 'RP CR', 'lower_body', VOID)
f(g, 'fire-control pocket and trigger slot', 'CL', 'lower_body', VOID)
f(g, 'front pivot lugs', 'RP DR', 'lower_body', ONE)
f(g, 'buffer tower (receiver extension ring)', 'RP DR DL LP CL', 'lower_buffer_tower')
f(g, 'magazine well flare', 'RP DR DL LP CR', 'magwell_flare')
f(g, 'magazine release fence', 'RP CR', 'mag_release_fence')
f(g, 'bolt catch ear, front', 'DL LP CL', 'bolt_catch_ear_front')
f(g, 'bolt catch ear, rear', 'DL LP CL', 'bolt_catch_ear_rear')
f(g, 'selector stop boss (safe), left', 'CL', 'lower_selector_stop_safe_l')
f(g, 'selector stop boss (fire), left', 'CL', 'lower_selector_stop_fire_l')
f(g, 'selector stop boss (safe), right', 'RP', 'lower_selector_stop_safe_r')
f(g, 'selector stop boss (fire), right', 'RP', 'lower_selector_stop_fire_r')
f(g, 'magazine well rear rib, left', 'DL CL', 'magwell_rib_l')
f(g, 'magazine well rear rib, right', 'RP CR', 'magwell_rib_r')
f(g, 'trigger guard', 'RP DR DL LP CL CR', 'trigger_guard')
f(g, 'marking panel, left (blank: no maker marks)', 'DL LP', 'marking_panel_l')
f(g, 'marking panel, right (blank: no maker marks)', 'RP DR CR', 'marking_panel_r')
# ---------------------------------------------------------------- controls
g = 'controls'
f(g, 'safety selector lever, left', 'DL LP CL', 'selector_lever_l')
f(g, 'safety selector lever, right (ambidextrous)', 'RP DR CR', 'selector_lever_r')
f(g, 'selector index mark, left', 'CL', 'selector_index_l')
f(g, 'selector index mark, right', 'RP', 'selector_index_r')
for s, seen in (('l', 'DL LP CL'), ('r', 'RP DR CR')):
    f(g, f'pictogram: safe (white crossed box), {s}', seen, f'pictogram_safe_{s}')
    f(g, f'pictogram: single shot (red), {s}', seen, f'pictogram_semi_{s}')
    f(g, f'pictogram: automatic (red), {s}', seen, f'pictogram_auto_{s}')
f(g, 'bolt catch paddle', 'DL LP CL', 'bolt_catch')
f(g, 'bolt catch grip ribs', 'CL', 'bolt_catch_ribs')
f(g, 'magazine release button', 'RP DR CR', 'mag_release_button')
for i in range(1, 4): f(g, f'magazine release button rib {i}', 'RP CR', f'mag_button_rib_{i}')
f(g, 'magazine catch bar, left', 'DL LP CL', 'mag_catch')
f(g, 'trigger', 'RP DR DL LP CL CR', 'trigger')
# ---------------------------------------------------------------- pins / fasteners on the receivers
g = 'pins'
f(g, 'pivot pin head, right', 'RP DR CR', 'pivot_pin_head_r')
f(g, 'pivot pin end, left', 'DL', 'pivot_pin_end_l')
f(g, 'takedown pin head, right', 'RP CR', 'takedown_pin_head_r')
f(g, 'takedown pin end, left', 'CL', 'takedown_pin_end_l')
f(g, 'trigger pin, left', 'CL', 'trigger_pin_l')
f(g, 'trigger pin, right', 'CR', 'trigger_pin_r')
f(g, 'hammer pin, left', 'CL', 'hammer_pin_l')
f(g, 'hammer pin, right', 'CR', 'hammer_pin_r')
f(g, 'auto sear pin, left', 'CL', 'sear_pin_l')
f(g, 'auto sear pin, right', 'RP', 'sear_pin_r')
f(g, 'bolt catch roll pin', 'CL', 'bolt_catch_pin')
# ---------------------------------------------------------------- grip
g = 'grip'
f(g, 'pistol grip body with beavertail', 'RP DR DL LP CL CR', 'grip_body')
f(g, 'stippled side panel, left', 'LP CL', 'grip_panel_l')
f(g, 'stippled side panel, right', 'RP CR', 'grip_panel_r')
f(g, 'stippled backstrap pad', 'RP LP', 'grip_backstrap_pad')
f(g, 'frontstrap pad', 'RP', 'grip_frontstrap_pad')
f(g, 'finger bump on the frontstrap', 'RP DR DL', 'grip_finger_bump')
f(g, 'grip bottom cap (storage door)', 'RP LP', 'grip_cap')
f(g, 'grip cap latch', 'RP', 'grip_cap_latch')
f(g, 'mould parting line front and back', 'RP', 'grip_body', 'a mould seam 0.1 mm high: carried by the polymer normal map, not geometry')
# ---------------------------------------------------------------- magazine
g = 'magazine'
f(g, 'curved 30-round magazine body', 'RP DR DL LP CR', 'mag_body')
f(g, 'magazine catch notch', 'LP', 'mag_body', VOID)
for s, seen in (('l', 'DL LP'), ('r', 'RP DR CR')):
    for i in range(1, 4): f(g, f'magazine stiffening rib {i}, {s}', seen, f'mag_rib_{s}_{i}')
f(g, 'front spine', 'RP', 'mag_spine_front')
f(g, 'rear spine', 'RP', 'mag_spine_rear')
f(g, 'floorplate', 'RP DR LP', 'mag_floorplate')
f(g, 'floorplate latch', 'LP', 'mag_floorplate_latch')
f(g, 'follower (seen during reload)', 'CR', 'mag_follower')
f(g, 'feed lip, left', 'CR', 'mag_feed_lip_l')
f(g, 'feed lip, right', 'CR', 'mag_feed_lip_r')
f(g, 'top cartridge case', 'CR', 'mag_round_1_case')
f(g, 'top cartridge bullet', 'CR', 'mag_round_1_bullet')
f(g, 'second cartridge case', 'CR', 'mag_round_2_case')
f(g, 'second cartridge bullet', 'CR', 'mag_round_2_bullet')
# ---------------------------------------------------------------- buffer tube
g = 'buffer tube'
f(g, 'receiver extension (buffer tube)', 'RP DR DL LP CS', 'buffer_tube')
f(g, 'castle nut', 'RP DR DL LP', 'castle_nut')
for i in range(1, 5): f(g, f'castle nut wrench notch {i}', 'RP LP', 'castle_nut', VOID)
f(g, 'receiver end plate', 'RP LP', 'receiver_end_plate')
# ---------------------------------------------------------------- stock
g = 'stock'
f(g, 'adjustable stock body', 'RP DR DL LP', 'stock_body')
f(g, 'stock bore for the buffer tube', 'RP', 'stock_body', VOID)
f(g, 'sling slot through the stock', 'RP', 'stock_body', VOID)
f(g, 'front collar', 'RP DR DL LP', 'stock_front_collar')
for s, seen in (('l', 'DL LP'), ('r', 'RP DR')):
    f(g, f'side ridge along the tube, {s}', seen, f'stock_ridge_{s}')
    f(g, f'label plate, {s}', 'DL' if s == 'l' else 'DR', f'stock_label_plate_{s}')
    for i in range(1, 6): f(g, f'diagonal web rib {i}, {s}', seen, f'stock_web_rib_{s}_{i}')
f(g, 'length-adjust latch', 'RP DR DL LP', 'stock_latch')
f(g, 'latch pin', 'RP', 'stock_latch_pin')
# ---------------------------------------------------------------- buttpad
g = 'buttpad'
f(g, 'butt plate (hard frame)', 'RP DR DL LP', 'buttplate')
f(g, 'rubber buttpad (convex)', 'RP DR DL LP', 'buttpad')
for i in range(1, 23): f(g, f'buttpad grip rib {i:02d}', 'RP DR DL LP', f'buttpad_rib_{i:02d}')
for s, seen in (('l', 'LP'), ('r', 'RP')):
    for i in range(1, 8): f(g, f'buttpad lattice strut {i}, {s}', seen, f'buttpad_truss_{s}_{i}')
# ---------------------------------------------------------------- sling points
g = 'sling points'
f(g, 'sling loop at the top of the buttplate', 'RP DR DL LP', 'stock_sling_loop')
f(g, 'end plate sling eye, left', 'LP', 'end_plate_sling_eye_l')
f(g, 'end plate sling eye, right', 'RP', 'end_plate_sling_eye_r')

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'inventory.json')
json.dump(rows, open(out, 'w'), indent=1)
parts = sorted({r['part_name'] for r in rows})
print(len(rows), 'features;', len(parts), 'distinct parts;', sum(1 for r in rows if r.get('merged')), 'merges')
