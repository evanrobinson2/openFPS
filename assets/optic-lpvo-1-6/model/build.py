"""Generic 1-6x24 LPVO in a one-piece cantilever mount: the parametric recipe. Rebuilds everything from nothing:

    blender -b --python build.py          writes work/optic-lpvo-1-6.glb and .blend (ignored by git),
                                          stats.json and inventory.json (committed)

The numbers the optics fix are read from ../optics/lpvo.json (written by ../optics/sim.py): overall length, tube and
objective diameters, the height of the optical axis, where the eyepiece ends, the sockets, the turn of the power ring.
The remaining numbers are in P below with their status.
This is a generic scope, not a model of any product: no maker's name, logo or trade dress.
Frame: see kit.py. Credit: carpetshark.
"""
import bpy, math, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit
from kit import part, group, socket, key, turned, lathe, cyl, box, prism, join, rotate

J = json.load(open(os.path.join(HERE, '..', 'optics', 'lpvo.json')))
B, R = J['body'], J['rifle']
SO = R['socket_optic_l_mm']
H = B['axis_over_rail_mm']                                   # optical axis above the rail top
L0 = B['ocular_rear_l_mm'] - SO; L1 = L0 + B['length_mm']    # rear face of the eyepiece, front face of the objective end
TR = B['tube_mm'] / 2
def from_asset(p): return (p[2] * 1000, p[0] * 1000, p[1] * 1000)       # asset frame metres -> model mm
LOC, LOBJ = from_asset(J['sockets']['socket_ocular_lens'])[0], from_asset(J['sockets']['socket_objective'])[0]

# ------------------------------------------------------------------ shape numbers that the optics do not fix (mm)
P = dict(
    oc_r=B['ocular_od_mm'] / 2, oc_clear_r=B['ocular_clear_mm'] / 2, obj_clear_r=B['objective_clear_mm'] / 2,      # lpvo.json body
    diopter_l1=L0 + 16.0, eyepiece_l1=L0 + 46.0, power_ring_l1=L0 + 62.0, taper_l1=L0 + 70.0,       # inferred: lengths of the eyepiece sections
    eyepiece_r=21.5, power_ring_r=22.5, lever_h=12.0,                                              # inferred
    saddle_l=(L0 + 112.0, L0 + 152.0), saddle_r=20.5,                                              # inferred: turret saddle a little behind the middle of the tube
    bell_l0=L1 - 42.0, bell_r=16.5,                                                                # inferred: a slight flare at the objective end
    turret_r=11.0, turret_h=8.0, cap_r=14.5, cap_h=13.0, boss_h=3.5,                               # inferred: low-profile capped turrets
    illum_r=13.0, illum_h=14.0, battery_cap_r=9.5,                                                 # inferred
    ring_w=20.0, ring_wall=4.5, ring_flange=21.5, ring_screw_r=2.6,                                # inferred
    ring_rear_l=L0 + 90.0, ring_front_l=L0 + 172.0,                                                # ring centres: either side of the saddle
    base_l0=-34.0, base_l1=46.0, base_top=9.0, base_half=15.0, arm_half=10.0,                      # base: rifle L -94 .. -14, ahead of the folded rear sight
    rail_half_top=7.8, rail_half=10.6, rail_flank=2.8, rail_step=3.3,                              # the HK416 recipe's rail section (assets/hk416/model/build.py)
    bolt_r=2.4, bolt_z=-0.7,
)
SL = (P['saddle_l'][0] + P['saddle_l'][1]) / 2
slots = [R['upper_lug0_l_mm'] + R['rail_lug_mm'] + (R['rail_pitch_mm'] - R['rail_lug_mm']) / 2 + R['rail_pitch_mm'] * i - SO for i in range(R['n_upper_lugs'] - 1)]
BOLTS = [min(slots, key=lambda l: abs(l - (P['base_l0'] + 10))), min(slots, key=lambda l: abs(l - (P['base_l1'] - 10)))]

A, ST, RB = 'anodized', 'steel', 'rubber'
SEAT = 0.05     # the base's seat is drawn this far above the rail top so the two surfaces do not coincide


def materials():
    kit.material('anodized', (0.030, 0.031, 0.034), 0.55, 0.75)
    kit.material('steel', (0.13, 0.13, 0.14), 0.50, 0.90)
    kit.material('rubber', (0.020, 0.020, 0.021), 0.85, 0.0)
    kit.material('lens_objective', (0.55, 0.75, 0.60), 0.04, 0.0, alpha=0.18)      # multi-coated: a faint green reflection
    kit.material('lens_ocular', (0.60, 0.70, 0.85), 0.04, 0.0, alpha=0.15)
    kit.material('placeholder_panel', (0.10, 0.10, 0.105), 0.7, 0.2)


def lens(l, r, t_centre, t_edge, toward=1):
    """Biconvex lens outline (h, r) from its rear vertex."""
    n = 6; bulge = (t_centre - t_edge) / 2
    front = [(t_centre - bulge * (i / n) ** 2, r * i / n) for i in range(n + 1)]
    back = [(bulge * (i / n) ** 2, r * i / n) for i in range(n + 1)]
    return turned((l, 0, H), (1, 0, 0), front + back[::-1], 48)


def build_scope():
    group('scope')
    sl0, sl1 = P['saddle_l']; sr = P['saddle_r']; b0, br_ = P['bell_l0'], P['bell_r']; t1 = P['taper_l1']; bore = 12.6
    outer = [(P['power_ring_l1'], 20.0), (t1, TR), (sl0 - 4, TR), (sl0, sr), (sl1, sr), (sl1 + 4, TR), (b0, TR), (b0 + 7, br_), (L1 - 1, br_), (L1, br_ - 1)]
    inner = [(L1, 14.0), (LOBJ + 3, 14.0), (LOBJ + 3, bore), (P['power_ring_l1'], bore)]
    bosses = [cyl((SL, 0, H + sr - 4), (SL, 0, H + sr + P['boss_h']), P['cap_r'], 40), cyl((SL, -(sr - 4), H), (SL, -(sr + P['boss_h']), H), P['cap_r'], 40),
              cyl((SL, sr - 4, H), (SL, sr + P['boss_h'], H), P['illum_r'], 40)]
    part('main_tube', join(lathe(outer + inner, 64, 0, H), *bosses), A, 'scope', bevel=0.4,
         what='one-piece main tube: 30 mm tube, turret saddle with three bosses, objective end',
         dims=dict(tube_od=B['tube_mm'], front_face_l=L1, saddle_od=2 * sr, objective_end_od=2 * br_, axis_over_rail=H),
         source='tube 30 mm and overall length 257 mm: published class figures (lpvo.json published); saddle and flare inferred')
    part('eyepiece_housing', lathe([(P['diopter_l1'] - 6, 20.6), (P['diopter_l1'], 20.6), (P['diopter_l1'], P['eyepiece_r']), (P['eyepiece_l1'], P['eyepiece_r']), (P['eyepiece_l1'], 20.0), (P['power_ring_l1'], 20.0),
                                    (P['power_ring_l1'], bore), (P['eyepiece_l1'] - 4, bore), (P['diopter_l1'] + 8, 19.4), (P['diopter_l1'] - 6, 19.4)], 64, 0, H), A, 'scope', bevel=0.3,
         what='eyepiece housing; the power ring turns on its front, the dioptre ring on its rear', dims=dict(od=2 * P['eyepiece_r'], rear_face_l=L0), source='inferred from the ocular diameter')
    part('power_ring', lathe([(P['eyepiece_l1'] + 0.3, 20.05), (P['eyepiece_l1'] + 0.3, P['power_ring_r']), (P['power_ring_l1'] - 0.3, P['power_ring_r']), (P['power_ring_l1'] - 0.3, 20.05)], 64, 0, H,
                             teeth=(36, 0.8, P['eyepiece_l1'] + 0.3, P['power_ring_l1'] - 0.3)), A, 'scope', pivot=((P['eyepiece_l1'] + P['power_ring_l1']) / 2, 0, H), bevel=0.15,
         what='power (magnification) ring: half a turn from 1x to 6x', dims=dict(od=2 * P['power_ring_r'], throw_deg=B['throw_deg']), source='throw: lpvo.json body (inferred); shape inferred')
    lm = (P['eyepiece_l1'] + P['power_ring_l1']) / 2
    part('throw_lever', prism([(lm - 3.5, P['power_ring_r'] - 1), (lm + 3.5, P['power_ring_r'] - 1), (lm + 2.2, P['power_ring_r'] + P['lever_h']), (lm - 2.2, P['power_ring_r'] + P['lever_h'])], H - 2.5, H + 2.5, 'z'),
         A, 'power_ring', bevel=0.8, what='throw lever on the power ring; it points left at 1x and comes over the top to the right at 6x', dims=dict(height=P['lever_h']), source='inferred')
    part('dioptre_ring', lathe([(L0, P['oc_r'] - 1), (L0 + 1, P['oc_r']), (P['diopter_l1'] - 0.3, P['oc_r']), (P['diopter_l1'] - 0.3, 20.7), (P['diopter_l1'] - 6.3, 20.7), (P['diopter_l1'] - 6.3, 19.4), (LOC + 5.5, 19.4),
                               (LOC + 5.5, P['oc_clear_r']), (L0, P['oc_clear_r'])], 64, 0, H, teeth=(40, 0.6, L0 + 3, P['diopter_l1'] - 3)), RB, 'scope', pivot=(L0 + 8, 0, H), bevel=0.15,
         what='dioptre (reticle focus) ring: the rear of the eyepiece, holding the eye lens', dims=dict(od=B['ocular_od_mm'], clear_aperture=B['ocular_clear_mm']), source='ocular diameters: lpvo.json body (inferred for the class)')
    part('lens_ocular', lens(LOC, P['oc_clear_r'], 5.0, 1.6), 'lens_ocular', 'dioptre_ring', bevel=0,
         what='eye lens (the last surface of the eyepiece); the picture-in-picture shader runs on this material', dims=dict(diameter=B['ocular_clear_mm'], inset=B['ocular_lens_inset_mm']), source='lpvo.json body')
    part('lens_objective', lens(LOBJ, 14.0, 5.5, 2.0), 'lens_objective', 'scope', bevel=0,
         what='objective lens', dims=dict(clear_aperture=B['objective_clear_mm'], inset=B['objective_lens_inset_mm']), source='24 mm objective: the brief; inset inferred')
    part('objective_retainer', lathe([(LOBJ + 5.5, 14.0), (LOBJ + 7.0, 14.0), (LOBJ + 7.0, P['obj_clear_r']), (LOBJ + 5.5, P['obj_clear_r'])], 48, 0, H), A, 'scope', bevel=0.15,
         what='ring holding the objective; its bore is the 24 mm clear aperture', dims=dict(clear_aperture=B['objective_clear_mm']), source='the brief')


def build_turrets():
    group('turrets', 'scope')
    sr = P['saddle_r']; top = H + sr + P['boss_h']; side = sr + P['boss_h']
    dial = [(0, 0), (0, P['turret_r']), (P['turret_h'] - 0.8, P['turret_r']), (P['turret_h'], P['turret_r'] - 0.8), (P['turret_h'], 0)]
    cap = [(0, P['cap_r'] - 2.0), (0, P['cap_r']), (P['cap_h'] - 1.2, P['cap_r']), (P['cap_h'], P['cap_r'] - 1.2), (P['cap_h'], 0), (P['cap_h'] - 1.8, 0), (P['cap_h'] - 1.8, P['cap_r'] - 2.0)]
    part('elevation_turret', turned((SL, 0, top), (0, 0, 1), dial, teeth=(25, 0.4, 2.5, P['turret_h'] - 1)), ST, 'turrets', pivot=(SL, 0, top), bevel=0.1,
         what='elevation turret: 0.1 mrad clicks, 100 per turn', dims=dict(diameter=2 * P['turret_r'], click_mrad=B['click_mrad'], clicks_per_turn=B['clicks_per_rev']), source='click value: class figure (lpvo.json body); shape inferred')
    part('elevation_cap', turned((SL, 0, top), (0, 0, 1), cap, teeth=(30, 0.5, 2, P['cap_h'] - 2.5)), A, 'turrets', pivot=(SL, 0, top), bevel=0.15,
         what='screw cap over the elevation turret (low profile, capped)', dims=dict(diameter=2 * P['cap_r'], height=P['cap_h']), source='inferred')
    part('windage_turret', turned((SL, -side, H), (0, -1, 0), dial, teeth=(25, 0.4, 2.5, P['turret_h'] - 1)), ST, 'turrets', pivot=(SL, -side, H), bevel=0.1,
         what='windage turret: 0.1 mrad clicks', dims=dict(diameter=2 * P['turret_r']), source='as the elevation turret')
    part('windage_cap', turned((SL, -side, H), (0, -1, 0), cap, teeth=(30, 0.5, 2, P['cap_h'] - 2.5)), A, 'turrets', pivot=(SL, -side, H), bevel=0.15,
         what='screw cap over the windage turret', dims=dict(diameter=2 * P['cap_r'], height=P['cap_h']), source='inferred')
    ih = P['illum_h']; knob = [(0, 0), (0, P['illum_r']), (ih - 1, P['illum_r']), (ih, P['illum_r'] - 1), (ih, 0)]
    part('illumination_knob', turned((SL, side, H), (0, 1, 0), knob, teeth=(28, 0.7, 1.5, ih - 1.5)), RB, 'turrets', pivot=(SL, side, H), bevel=0.15,
         what='reticle illumination knob: OFF and 10 brightness positions, 30 degrees apart', dims=dict(diameter=2 * P['illum_r'], height=ih, positions=11), source='positions and luminances: lpvo.json illumination (inferred); shape inferred')
    part('illumination_index', box(SL - 0.5, SL + 0.5, side + ih - 0.2, side + ih + 0.3, H + P['illum_r'] - 5, H + P['illum_r'] - 1.5), 'placeholder_panel', 'illumination_knob', bevel=0, what='index mark on the knob', source='inferred')
    part('illumination_battery_cap', cyl((SL, side + ih, H), (SL, side + ih + 1.6, H), P['battery_cap_r'], 32), A, 'illumination_knob', pivot=(SL, side + ih, H), bevel=0.2,
         cuts=[box(SL - 6, SL + 6, side + ih + 0.8, side + ih + 3, H - 0.7, H + 0.7)], what='battery cap with a coin slot', dims=dict(diameter=2 * P['battery_cap_r']), source='inferred')


def build_mount():
    group('mount')
    b0, b1, bt, bh = P['base_l0'], P['base_l1'], P['base_top'], P['base_half']
    ht, hw, fl, st = P['rail_half_top'], P['rail_half'], P['rail_flank'], P['rail_step']
    bolts = lambda: [cyl((l, -40, P['bolt_z']), (l, 40, P['bolt_z']), P['bolt_r'] + 0.15, 20) for l in BOLTS]
    base = [(-bh, bt), (-bh, -st), (-(hw + 0.3), -st), (-(hw + 0.3), -fl), (-(ht + 0.2), SEAT), (8.5, SEAT), (8.5, bt)]
    part('mount_base', prism(base, b0, b1, 'l'), A, 'mount', bevel=0.4, cuts=bolts(),
         what='rail clamp body with the fixed jaw on the right; it lies on the receiver rail ahead of the folded rear sight',
         dims=dict(length=b1 - b0, rifle_L=[b0 + SO, b1 + SO]), source='rail section and lug positions: assets/hk416/model/build.py; the rest inferred')
    jaw = [(8.8, bt - 1), (bh, bt - 1), (bh, -st), (hw + 0.3, -st), (hw + 0.3, -fl), (8.8, -0.8)]
    part('mount_clamp_bar', prism(jaw, b0 + 2, b1 - 2, 'l'), A, 'mount', bevel=0.3, cuts=bolts(), what='moving jaw on the left flank of the rail', dims=dict(length=b1 - b0 - 4), source='inferred')
    for nm, l in zip(('rear', 'front'), BOLTS):
        part(f'mount_cross_bolt_{nm}', cyl((l, -(bh + 1.5), P['bolt_z']), (l, bh + 4.5, P['bolt_z']), P['bolt_r'], 20), ST, 'mount', bevel=0.2,
             what='cross-bolt lying in a rail slot: clamps the jaw and stops the mount moving under recoil', dims=dict(diameter=2 * P['bolt_r'], slot_centre_rifle_L=round(l + SO, 2)),
             source='slot position: rail pitch 10.0 mm and lug 4.77 mm from assets/hk416/model/build.py')
        part(f'mount_bolt_head_{nm}', cyl((l, -bh, P['bolt_z']), (l, -(bh + 2.0), P['bolt_z']), 4.2, 20), ST, f'mount_cross_bolt_{nm}', bevel=0.3, what='head of the cross-bolt', source='inferred')
        part(f'mount_clamp_nut_{nm}', cyl((l, bh, P['bolt_z']), (l, bh + 4.0, P['bolt_z']), 5.2, 6), ST, 'mount', pivot=(l, bh, P['bolt_z']), bevel=0.3, what='hex nut that closes the clamp', source='inferred')
    rw, wall, fg, ah = P['ring_w'], P['ring_wall'], P['ring_flange'], P['arm_half']
    rr0, rr1 = P['ring_rear_l'] - rw / 2, P['ring_rear_l'] + rw / 2; rf0, rf1 = P['ring_front_l'] - rw / 2, P['ring_front_l'] + rw / 2
    zt = H - TR - wall                                                # underside of the rings
    arm = [(b0, bt - 0.5), (rr0, zt + 0.5), (rr1, zt + 0.5), (rr1 + 6, bt + 9), (rf0 - 12, bt + 9), (rf0, zt + 0.5), (rf1, zt + 0.5), (rf1, zt - 5), (b1 + 2, bt - 0.5)]
    part('mount_arm', prism(arm, -ah, ah, 's'), A, 'mount', bevel=0.6,
         what='the one-piece body of the mount: two ring pedestals, the front one cantilevered %.0f mm ahead of the base' % (rf1 - b1),
         dims=dict(ring_centres_l=[P['ring_rear_l'], P['ring_front_l']], cantilever=rf1 - b1, axis_over_rail=H), source='axis height: a 1.70 in mount (lpvo.json body); shape inferred')
    ro = TR + wall; a = math.radians(40)
    lower = [(-fg, H - 0.4), (-fg, H - 6), (-11, zt + 2), (-11, zt), (11, zt), (11, zt + 2), (fg, H - 6), (fg, H - 0.4)]
    upper = [(-fg, H + 0.4), (fg, H + 0.4), (fg, H + 6), (ro * math.cos(a), H + ro * math.sin(a))] + \
        [(ro * math.cos(math.radians(d)), H + ro * math.sin(math.radians(d))) for d in range(50, 131, 10)] + [(-ro * math.cos(a), H + ro * math.sin(a)), (-fg, H + 6)]
    for nm, (r0, r1) in (('rear', (rr0, rr1)), ('front', (rf0, rf1))):
        bore = lambda: cyl((r0 - 1, 0, H), (r1 + 1, 0, H), TR + 0.05, 64)
        part(f'mount_ring_lower_{nm}', prism(lower, r0, r1, 'l'), A, 'mount', bevel=0.5, cuts=[bore()], what='lower half of a 30 mm ring', dims=dict(ring_id=B['tube_mm'], width=rw), source='inferred')
        part(f'mount_ring_cap_{nm}', prism(upper, r0, r1, 'l'), A, 'mount', bevel=0.5, cuts=[bore()], what='upper half of a 30 mm ring', dims=dict(ring_od=2 * ro), source='inferred')
        for k, l in (('f', r1 - 4.2), ('r', r0 + 4.2)):
            for sd, s in (('l', fg - 3.2), ('r', -(fg - 3.2))):
                part(f'ring_screw_{nm}_{k}{sd}', cyl((l, s, H + 4.0), (l, s, H + 8.5), P['ring_screw_r'], 16), ST, 'mount', bevel=0.15, cuts=[cyl((l, s, H + 6.5), (l, s, H + 9), 1.4, 6)],
                     what='ring screw, socket head', source='inferred')
    part('maker_panel_placeholder', box(P['ring_rear_l'] - 6, P['ring_rear_l'] + 6, -5, 5, H + ro - 0.3, H + ro + 0.25), 'placeholder_panel', 'mount_ring_cap_rear', bevel=0.1,
         what='plain panel where a maker\'s mark would be; deliberately blank', dims=dict(length=12, width=10), source='MODELING_RULES.md rule 2')


def sockets_and_clips():
    for nm in ('socket_mount', 'socket_eye', 'socket_ocular_lens', 'socket_objective'):
        socket(nm, from_asset(J['sockets'][nm]))
    socket('socket_reticle_plane', (LOC + J['design']['eyepiece_f_mm'], 0, H))
    key('magnification', 'power_ring', ('rot', 'l'), [(1, 0), (61, B['throw_deg'])],
        'the ring angle is throw * ln(M) / ln(6): frame f is magnification 6^((f - 1) / 60); frame 1 = 1x, frame 61 = 6x (lpvo.json by_magnification[*].power_ring_deg)')
    key('elevation_turn', 'elevation_turret', ('rot', 'z'), [(1, 0), (101, -360)], 'one turn = 100 clicks of 0.1 mrad; frame k+1 = k clicks up (anticlockwise from above raises the point of impact)')
    key('windage_turn', 'windage_turret', ('rot', 's'), [(1, 0), (101, 360)], 'one turn = 100 clicks of 0.1 mrad; frame k+1 = k clicks')
    key('elevation_cap_off', 'elevation_cap', ('rot', 'z'), [(1, 0), (19, 1080), (24, 1080)], 'unscrew three turns, then lift clear')
    key('elevation_cap_off', 'elevation_cap', ('loc', 'z'), [(1, 0), (19, 3.0), (24, 30.0)])
    key('windage_cap_off', 'windage_cap', ('rot', 's'), [(1, 0), (19, -1080), (24, -1080)], 'unscrew three turns, then pull clear')
    key('windage_cap_off', 'windage_cap', ('loc', 's'), [(1, 0), (19, -3.0), (24, -30.0)])
    key('illumination', 'illumination_knob', ('rot', 's'), [(i + 1, 30 * i) for i in range(11)], 'frame k+1 = knob position k of lpvo.json illumination (0 = OFF .. 10)')
    key('dioptre', 'dioptre_ring', ('rot', 'l'), [(1, -180), (25, 180)], 'reticle focus: one turn end to end; frame 13 is the middle')
    for nm in ('rear', 'front'):
        key('mount_clamp_open', f'mount_clamp_nut_{nm}', ('rot', 's'), [(1, 0), (16, 720)], 'two turns of each nut free the jaw')
        key('mount_clamp_open', f'mount_clamp_nut_{nm}', ('loc', 's'), [(1, 0), (16, 1.6)])
    key('mount_clamp_open', 'mount_clamp_bar', ('loc', 's'), [(1, 0), (6, 0), (16, 1.5)])


if __name__ == '__main__':
    kit.reset('optic_lpvo_1_6')
    materials()
    build_scope(); build_turrets(); build_mount(); sockets_and_clips()
    kit.finish_build(HERE, 'optic-lpvo-1-6', extra=dict(mounts_on='assets/hk416 socket_optic, with the rifle\'s sights folded', cross_bolts_rifle_L_mm=[round(l + SO, 2) for l in BOLTS], axis_over_rail_mm=H,
                                                        built_from='optics/lpvo.json (' + J['meta']['generator'] + ')'))
