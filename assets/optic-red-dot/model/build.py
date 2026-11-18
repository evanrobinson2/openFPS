"""Generic 2 MOA tube red-dot sight on a rail mount: the parametric recipe. Rebuilds everything from nothing:

    blender -b --python build.py          writes work/optic-red-dot.glb and .blend (ignored by git),
                                          stats.json and inventory.json (committed)

Every optical dimension is read from ../optics/reddot.json (written by ../optics/sim.py), so the shape and the
simulation cannot disagree: the housing length, the window and emitter positions, the doublet's radii and tilt, the
height of the optical axis and the sockets. The remaining numbers are in P below with their status.
This is a generic sight, not a model of any product: no maker's name, logo or trade dress.
Frame: see kit.py. Credit: carpetshark.
"""
import bpy, math, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit
from kit import part, group, socket, key, turned, lathe, cyl, box, prism, join, rotate

J = json.load(open(os.path.join(HERE, '..', 'optics', 'reddot.json')))
B, R, DES = J['body'], J['rifle'], J['optics']['design']
SO = R['socket_optic_l_mm']
H = B['axis_over_rail_mm']                                   # optical axis above the rail top
LC = B['tube_centre_l_mm'] - SO                              # housing mid-length
L0, L1 = LC - B['length_mm'] / 2, LC + B['length_mm'] / 2    # rear and front faces
LW = L1 - B['lens_inset_mm']                                 # window (doublet) vertex
LR = L0 + B['rear_inset_mm']                                 # rear flat window
def from_asset(p): return (p[2] * 1000, p[0] * 1000, p[1] * 1000)       # asset frame metres -> model mm
EM = from_asset(J['sockets']['socket_emitter'])

# ------------------------------------------------------------------ shape numbers that the optics do not fix (mm)
P = dict(
    hood_r=B['hood_od_mm'] / 2, ring_r=B['ring_od_mm'] / 2, bore_r=B['bore_id_mm'] / 2,      # reddot.json body: 38, 30 and 27 mm
    rear_bell_l1=L0 + 26.0,          # inferred: the rear bell holds the emitter and the adjusters
    front_hood_l0=L1 - 36.0,         # inferred: sun shade over the window
    adj_l=L0 + 13.0,                 # adjusters and brightness knob sit over the emitter (which is at l = %.1f)
    adj_boss_r=8.0, adj_cap_r=8.6, adj_cap_h=9.0, adj_screw_r=4.2,                           # inferred
    knob_r=13.5, knob_h=10.0, knob_teeth=30, battery_cap_r=9.5,                              # inferred: holds a 20 mm coin cell
    ring_w=22.0, ring_wall=4.0, ring_flange=21.0, ring_screw_r=2.6,                          # inferred
    base_l0=LC - 15.0, base_l1=LC + 15.0, base_top=9.0, base_half=15.0,                      # inferred
    rail_half_top=7.8, rail_half=10.6, rail_flank=2.8, rail_step=3.3,                        # the HK416 recipe's rail section (assets/hk416/model/build.py)
    bolt_r=2.4, bolt_z=-0.7,         # cross-bolt: it lies in a rail slot (5.23 mm wide, 3.6 mm deep) and is the recoil stop
)
# the cross-bolt goes in the rail slot nearest the housing's middle
slots = [R['upper_lug0_l_mm'] + R['rail_lug_mm'] + (R['rail_pitch_mm'] - R['rail_lug_mm']) / 2 + R['rail_pitch_mm'] * i for i in range(R['n_upper_lugs'] - 1)]
BOLT_L = min(slots, key=lambda L: abs(L - B['tube_centre_l_mm'])) - SO

A, ST, RB = 'anodized', 'steel', 'rubber'
SEAT = 0.05     # the base's seat is drawn this far above the rail top so the two surfaces do not coincide


def materials():
    kit.material('anodized', (0.030, 0.031, 0.034), 0.55, 0.75)
    kit.material('steel', (0.13, 0.13, 0.14), 0.50, 0.90)
    kit.material('rubber', (0.020, 0.020, 0.021), 0.85, 0.0)
    kit.material('lens_front', (0.75, 0.20, 0.12), 0.05, 0.0, alpha=0.30)      # the band-reflecting doublet: a red flash from the front
    kit.material('lens_rear', (0.80, 0.90, 0.92), 0.05, 0.0, alpha=0.12)
    kit.material('emitter', (0.9, 0.05, 0.02), 0.4, 0.0, emit=(1.0, 0.045, 0.012), emit_strength=6.0)
    kit.material('placeholder_panel', (0.10, 0.10, 0.105), 0.7, 0.2)


def build_housing():
    group('housing')
    hr, rr, br = P['hood_r'], P['ring_r'], P['bore_r']
    loop = [(L0, hr - 1.5), (L0 + 1.5, hr), (P['rear_bell_l1'], hr), (P['rear_bell_l1'] + 4, rr), (P['front_hood_l0'] - 4, rr), (P['front_hood_l0'], hr), (L1 - 1.0, hr), (L1, hr - 1.0),
            (L1, br + 1.0), (L1 - 1.0, br), (L0 + 1.0, br), (L0, br + 1.0)]
    al = P['adj_l']
    bosses = [cyl((al, 0, H + hr - 3), (al, 0, H + hr + 4), P['adj_boss_r'], 32), cyl((al, -(hr - 3), H), (al, -(hr + 4), H), P['adj_boss_r'], 32),
              cyl((al, hr - 3, H), (al, hr + 3, H), P['knob_r'] - 0.5, 40)]
    bm = join(lathe(loop, 64, 0, H), *bosses)
    part('housing_body', bm, A, 'housing', bevel=0.4,
         what='one-piece tube housing: rear bell (emitter and adjusters), 30 mm ring section, front sun shade',
         dims=dict(length=B['length_mm'], hood_od=2 * hr, ring_section_od=2 * rr, bore_id=2 * br, axis_over_rail=H),
         source='length, diameters and axis height: reddot.json body (class figures and the recalled 39 mm mount height); the lengths of the bell and hood are inferred')
    # window: cemented doublet, tilted toward the emitter. Its axis points back at the eye and down toward the emitter.
    t = math.radians(DES['tilt_deg']); sl = J['frames']['shooter_from_lens']
    ey = (0.0, -sl[0][1], sl[1][1])                              # lens +y (away from the emitter) in model (l, s, z): s = -right, z = up
    ab = (-math.cos(t), -math.sin(t) * ey[1], -math.sin(t) * ey[2])
    R1, R2, R3, th = DES['R1_eye_side_mm'], DES['R2_dichroic_mm'], DES['R3_target_side_mm'], DES['centre_thickness_mm']
    sag = lambda Rc, r: Rc - math.copysign(math.sqrt(Rc * Rc - r * r), Rc)
    rs = [br * i / 6 for i in range(7)]
    s1 = [(sag(R1, r), r) for r in rs]; s2 = [(-th / 2 + sag(R2, r), r) for r in rs]; s3 = [(-th + sag(R3, r), r) for r in rs]
    part('window_element_rear', turned((LW, 0, H), ab, s1 + s2[::-1], 48), 'lens_front', 'housing', bevel=0,
         what='eye-side element of the window doublet; its front (cemented) surface carries the red band-reflecting coating',
         dims=dict(R1=R1, R2=R2, diameter=2 * br, tilt_deg=DES['tilt_deg']), source='solved in optics/sim.py (design_reddot)')
    part('window_element_front', turned((LW, 0, H), ab, s2 + s3[::-1], 48), 'lens_front', 'housing', bevel=0,
         what='target-side element of the window doublet; its outer radius makes the window zero-power',
         dims=dict(R2=R2, R3=R3, centre_thickness_of_pair=th), source='solved in optics/sim.py')
    part('window_retainer', lathe([(LW + 1.0, br), (LW + 2.5, br), (LW + 2.5, B['window_clear_mm'] / 2), (LW + 1.0, B['window_clear_mm'] / 2)], 48, 0, H), A, 'housing', bevel=0.15,
         what='threaded ring holding the doublet; its bore is the clear aperture', dims=dict(clear_aperture=B['window_clear_mm']), source='clear aperture: reddot.json body (inferred for the class)')
    part('rear_window', cyl((LR, 0, H), (LR + 2.0, 0, H), br, 48), 'lens_rear', 'housing', bevel=0,
         what='flat rear window (seals the housing)', dims=dict(thickness=2.0, diameter=2 * br), source='inferred')
    part('rear_window_retainer', lathe([(LR - 1.5, br), (LR, br), (LR, B['rear_clear_mm'] / 2), (LR - 1.5, B['rear_clear_mm'] / 2)], 48, 0, H), A, 'housing', bevel=0.15,
         what='ring holding the rear window', dims=dict(clear_aperture=B['rear_clear_mm']), source='inferred')
    # emitter: on the bore wall at 4:30 as the shooter sees it
    n = (0.0, EM[1], EM[2] - H); nl = math.hypot(n[1], n[2]); n = (0, n[1] / nl, n[2] / nl)
    part('emitter_carrier', cyl((EM[0], EM[1] + n[1] * 1.6, EM[2] + n[2] * 1.6), (EM[0], EM[1] - n[1] * 0.2, EM[2] - n[2] * 0.2), 2.2, 16), A, 'housing', bevel=0.1,
         what='carrier of the LED; the two adjusters push it across the focal plane', dims=dict(off_axis=DES['led_position_mm']['off_axis'], behind_window=DES['led_position_mm']['behind_window_vertex']),
         source='solved in optics/sim.py; clock position 4:30 is my choice')
    part('emitter_led', cyl((EM[0], EM[1], EM[2]), (EM[0], EM[1] - n[1] * 0.4, EM[2] - n[2] * 0.4), 0.5, 12), 'emitter', 'emitter_carrier', bevel=0,
         what='the LED; its emitting aperture is %.0f um, which the collimator turns into a 2 MOA dot (drawn 1 mm wide here so it can be seen)' % DES['emitter_diameter_um'],
         dims=dict(emitter_diameter_um=DES['emitter_diameter_um']), source='emitter diameter = focal length x 2 MOA, optics/sim.py')


def build_controls():
    group('controls', 'housing')
    al, hr = P['adj_l'], P['hood_r']
    # elevation: top
    z0 = H + hr + 4
    part('elevation_adjuster', cyl((al, 0, z0 - 1), (al, 0, z0 + 2.0), P['adj_screw_r'], 24), ST, 'controls', pivot=(al, 0, z0), bevel=0.2, cuts=[box(al - 0.6, al + 0.6, -6, 6, z0 + 1.0, z0 + 3)],
         what='elevation adjuster, coin slot; 0.5 MOA per click', dims=dict(diameter=2 * P['adj_screw_r'], click_moa=B['click_moa']), source='click value: class figure (reddot.json body); shape inferred')
    cap = [(0, 0), (0, P['adj_cap_r']), (P['adj_cap_h'] - 1, P['adj_cap_r']), (P['adj_cap_h'], P['adj_cap_r'] - 1), (P['adj_cap_h'], 0)]
    part('elevation_cap', turned((al, 0, z0), (0, 0, 1), cap, teeth=(24, 0.5, 1.5, P['adj_cap_h'] - 1.5)), A, 'controls', pivot=(al, 0, z0), bevel=0.15,
         what='screw cap over the elevation adjuster', dims=dict(diameter=2 * P['adj_cap_r'], height=P['adj_cap_h']), source='inferred')
    # windage: right side (-s)
    s0 = -(hr + 4)
    part('windage_adjuster', cyl((al, s0 + 1, H), (al, s0 - 2.0, H), P['adj_screw_r'], 24), ST, 'controls', pivot=(al, s0, H), bevel=0.2, cuts=[box(al - 0.6, al + 0.6, s0 - 3, s0 - 1.0, H - 6, H + 6)],
         what='windage adjuster, coin slot; 0.5 MOA per click', dims=dict(diameter=2 * P['adj_screw_r']), source='as the elevation adjuster')
    part('windage_cap', turned((al, s0, H), (0, -1, 0), cap, teeth=(24, 0.5, 1.5, P['adj_cap_h'] - 1.5)), A, 'controls', pivot=(al, s0, H), bevel=0.15,
         what='screw cap over the windage adjuster', dims=dict(diameter=2 * P['adj_cap_r'], height=P['adj_cap_h']), source='inferred')
    # brightness knob and battery cap: left side (+s)
    k0 = hr + 3; kh = P['knob_h']
    knob = [(0, 0), (0, P['knob_r']), (kh - 1, P['knob_r']), (kh, P['knob_r'] - 1), (kh, 0)]
    part('brightness_knob', turned((al, k0, H), (0, 1, 0), knob, teeth=(P['knob_teeth'], 0.7, 1.0, kh - 1.5)), RB, 'controls', pivot=(al, k0, H), bevel=0.15,
         what='rotary brightness switch: OFF, 3 night-vision and 8 daylight positions, 30 degrees apart', dims=dict(diameter=2 * P['knob_r'], height=kh, positions=12, step_deg=30),
         source='positions and luminances: optics/reddot.json brightness (inferred; the class has 16 positions); shape inferred')
    part('brightness_index', box(al - 0.5, al + 0.5, k0 + kh - 0.2, k0 + kh + 0.3, H + P['knob_r'] - 5, H + P['knob_r'] - 1.5), 'placeholder_panel', 'brightness_knob', bevel=0,
         what='index mark on the knob', source='inferred')
    part('battery_cap', cyl((al, k0 + kh, H), (al, k0 + kh + 1.6, H), P['battery_cap_r'], 32), A, 'brightness_knob', pivot=(al, k0 + kh, H), bevel=0.2,
         cuts=[box(al - 6, al + 6, k0 + kh + 0.8, k0 + kh + 3, H - 0.7, H + 0.7)],
         what='battery cap with a coin slot, in the middle of the knob', dims=dict(diameter=2 * P['battery_cap_r'], cell='20 mm coin cell'), source='inferred')


def build_mount():
    group('mount')
    b0, b1, bt, bh = P['base_l0'], P['base_l1'], P['base_top'], P['base_half']
    ht, hw, fl, st = P['rail_half_top'], P['rail_half'], P['rail_flank'], P['rail_step']
    bolt = lambda: cyl((BOLT_L, -40, P['bolt_z']), (BOLT_L, 40, P['bolt_z']), P['bolt_r'] + 0.15, 20)
    base = [(-bh, bt), (-bh, -st), (-(hw + 0.3), -st), (-(hw + 0.3), -fl), (-(ht + 0.2), SEAT), (8.5, SEAT), (8.5, bt)]
    part('mount_base', prism(base, b0, b1, 'l'), A, 'mount', bevel=0.4, cuts=[bolt()],
         what='rail clamp body with the fixed jaw on the right; it sits on the rail top and against the right flank',
         dims=dict(length=b1 - b0, rail_top_half_width=ht, rail_half_width=hw), source='rail section: assets/hk416/model/build.py (rail_half_top, rail_half, rail_flank); the rest inferred')
    jaw = [(8.8, bt - 1), (bh, bt - 1), (bh, -st), (hw + 0.3, -st), (hw + 0.3, -fl), (8.8, -0.8)]
    part('mount_clamp_jaw', prism(jaw, b0 + 3, b1 - 3, 'l'), A, 'mount', bevel=0.3, cuts=[bolt()],
         what='moving jaw on the left flank of the rail', dims=dict(length=b1 - b0 - 6), source='inferred')
    part('mount_cross_bolt', cyl((BOLT_L, -(bh + 1.5), P['bolt_z']), (BOLT_L, bh + 4.5, P['bolt_z']), P['bolt_r'], 20), ST, 'mount', bevel=0.2,
         what='cross-bolt lying in a rail slot: clamps the jaw and stops the mount moving under recoil', dims=dict(diameter=2 * P['bolt_r'], slot_centre_rifle_L=BOLT_L + SO),
         source='slot position: rail pitch 10.0 mm and lug 4.77 mm from assets/hk416/model/build.py')
    part('mount_bolt_head', cyl((BOLT_L, -bh, P['bolt_z']), (BOLT_L, -(bh + 2.0), P['bolt_z']), 4.2, 20), ST, 'mount_cross_bolt', bevel=0.3, what='head of the cross-bolt', source='inferred')
    part('mount_clamp_nut', cyl((BOLT_L, bh, P['bolt_z']), (BOLT_L, bh + 4.0, P['bolt_z']), 5.2, 6), ST, 'mount', pivot=(BOLT_L, bh, P['bolt_z']), bevel=0.3,
         what='hex nut that closes the clamp', dims=dict(across_corners=10.4), source='inferred')
    rw, wall, fg = P['ring_w'], P['ring_wall'], P['ring_flange']
    r0, r1 = LC - rw / 2, LC + rw / 2; ro = P['ring_r'] + wall
    bore = lambda: cyl((r0 - 1, 0, H), (r1 + 1, 0, H), P['ring_r'] + 0.05, 64)
    lower = [(-fg, H - 0.4), (-fg, H - 6), (-12, bt + 4), (-12, bt), (12, bt), (12, bt + 4), (fg, H - 6), (fg, H - 0.4)]
    part('mount_ring_lower', prism(lower, r0, r1, 'l'), A, 'mount', bevel=0.5, cuts=[bore()],
         what='pedestal and lower half of the 30 mm ring; it sets the optical axis %.1f mm above the rail' % H, dims=dict(ring_id=2 * P['ring_r'], width=rw, axis_over_rail=H),
         source='axis height: reddot.json body (39 mm, recalled class figure); shape inferred')
    a = math.radians(40); upper = [(-fg, H + 0.4), (fg, H + 0.4), (fg, H + 6), (ro * math.cos(a), H + ro * math.sin(a))] + \
        [(ro * math.cos(math.radians(d)), H + ro * math.sin(math.radians(d))) for d in range(50, 131, 10)] + [(-ro * math.cos(a), H + ro * math.sin(a)), (-fg, H + 6)]
    part('mount_ring_cap', prism(upper, r0, r1, 'l'), A, 'mount', bevel=0.5, cuts=[bore()],
         what='upper half of the ring', dims=dict(ring_od=2 * ro), source='inferred')
    for nm, l in (('f', r1 - 4.5), ('r', r0 + 4.5)):
        for sd, s in (('l', fg - 3.2), ('r', -(fg - 3.2))):
            part(f'ring_screw_{nm}{sd}', cyl((l, s, H + 4.0), (l, s, H + 8.5), P['ring_screw_r'], 16), ST, 'mount', bevel=0.15, cuts=[cyl((l, s, H + 6.5), (l, s, H + 9), 1.4, 6)],
                 what='ring screw, socket head', dims=dict(head_diameter=2 * P['ring_screw_r']), source='inferred')
    part('maker_panel_placeholder', box(LC - 6, LC + 6, -5, 5, H + ro - 0.3, H + ro + 0.25), 'placeholder_panel', 'mount_ring_cap', bevel=0.1,
         what='plain panel where a maker\'s mark would be; deliberately blank', dims=dict(length=12, width=10), source='MODELING_RULES.md rule 2')


def sockets_and_clips():
    for nm in ('socket_mount', 'socket_eye', 'socket_objective', 'socket_rear_window', 'socket_emitter'):
        socket(nm, from_asset(J['sockets'][nm]))
    n = len(J['brightness']['settings'])
    key('brightness', 'brightness_knob', ('rot', 's'), [(i + 1, 30 * i) for i in range(n)],
        'frame k+1 = switch position k of reddot.json brightness.settings (0 = OFF .. 11); 30 degrees per position')
    key('elevation_adjust', 'elevation_adjuster', ('rot', 'z'), [(1, 0), (25, -360)], 'one turn in 24 clicks (15 degrees each), clockwise seen from above = dot and POI down; frame k+1 = k clicks')
    key('windage_adjust', 'windage_adjuster', ('rot', 's'), [(1, 0), (25, 360)], 'one turn in 24 clicks; frame k+1 = k clicks')
    key('elevation_cap_off', 'elevation_cap', ('rot', 'z'), [(1, 0), (19, 1080), (24, 1080)], 'unscrew three turns, then lift clear')
    key('elevation_cap_off', 'elevation_cap', ('loc', 'z'), [(1, 0), (19, 3.0), (24, 22.0)])
    key('windage_cap_off', 'windage_cap', ('rot', 's'), [(1, 0), (19, -1080), (24, -1080)], 'unscrew three turns, then pull clear')
    key('windage_cap_off', 'windage_cap', ('loc', 's'), [(1, 0), (19, -3.0), (24, -22.0)])
    key('mount_clamp_open', 'mount_clamp_nut', ('rot', 's'), [(1, 0), (16, 720)], 'two turns of the nut free the jaw')
    key('mount_clamp_open', 'mount_clamp_nut', ('loc', 's'), [(1, 0), (16, 1.6)])
    key('mount_clamp_open', 'mount_clamp_jaw', ('loc', 's'), [(1, 0), (6, 0), (16, 1.5)])


if __name__ == '__main__':
    kit.reset('optic_red_dot')
    materials()
    build_housing(); build_controls(); build_mount(); sockets_and_clips()
    kit.finish_build(HERE, 'optic-red-dot', extra=dict(mounts_on='assets/hk416 socket_optic', cross_bolt_rifle_L_mm=round(BOLT_L + SO, 2), axis_over_rail_mm=H,
                                                       built_from='optics/reddot.json (' + J['meta']['generator'] + ')'))
