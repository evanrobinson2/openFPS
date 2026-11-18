"""Stage 3: the blockout. True-scale volumes for every module, with 1.80 m figures, to check that the ship works
as a place before any structure is built.

    python3 blockout.py            # needs the bpy module (pip install bpy) or: blender -b --python blockout.py

Writes work/wayfarer_blockout.blend (ignored by git). Render it with tools/render.py.
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, 'modules')]
import bpy
import numpy as np
import spec, kit
from kit import MB, finish, empty
from hullgrid import Hull
from structure import deck_slab, bulkhead
from figure import figure_mb
S = spec.ST

def build():
    kit.reset_scene()
    root = empty('wayfarer_blockout')
    for g in ('fuselage', 'cockpit', 'engines', 'landing_gear', 'lift_chassis', 'lander_bay', 'gadgets', 'figures'):
        empty(g, root)
    H = Hull()
    # hull shell, translucent, with the canopy band
    jb, js = H.rows['brow'], H.rows['sill']; i0, i1 = H.si(spec.CANOPY['s0']), H.si(spec.CANOPY['s1'])
    shell = MB(); glass = MB()
    for side in (1, -1):
        for (a, b, c, d, m, mb) in ((0, H.ni - 1, 0, H.nr, 'blockout_shell', shell),):
            G = H.nodes(a, b, c, d, 0.0, side)
            H.sheet(mb, G, m, flip=side < 0)
        H.sheet(glass, H.nodes(i0, i1, jb, js, 0.02, side), 'blockout_c', flip=side < 0)
    finish('hull_envelope', shell, 'fuselage'); finish('canopy_band', glass, 'cockpit')
    # decks and bulkheads
    d = MB()
    Lf = spec.LIFT; Lb = spec.LANDER_BAY
    deck_slab(d, spec.Z_MAIN, spec.DECK_T, S['cockpit_fwd'], S['eng_aft'], 'blockout_a', holes=[(6.9, 7.9, 0.9, 1.9)])
    deck_slab(d, spec.Z_LOWER, 0.12, 4.2, S['eng_fwd'] + 1.2, 'blockout_a',
              holes=[(Lf['s0'], Lf['s1'], -Lf['half_w'], Lf['half_w']), (Lb['s0'], Lb['s1'], -Lb['door_half'], Lb['door_half'])])
    for st in ('cockpit_aft', 'vestibule_aft', 'hold_aft', 'eng_fwd', 'eng_aft'):
        bulkhead(d, S[st], 0.10, 'blockout_a', doors=[(-0.5, 0.5, spec.Z_MAIN, spec.Z_MAIN + 2.0)] + ([(-0.5, 0.5, spec.Z_LOWER, spec.Z_LOWER + 2.0)] if st in ('hold_aft', 'eng_fwd') else []))
    finish('decks_and_bulkheads', d, 'fuselage')
    # cockpit: two pilot seats, two rear stations, console
    c = MB()
    for y in (-0.8, 0.8):
        c.box(2.6, 3.2, y - 0.28, y + 0.28, spec.Z_MAIN, spec.Z_MAIN + 0.45, 'blockout_c'); c.box(3.1, 3.25, y - 0.28, y + 0.28, spec.Z_MAIN + 0.45, spec.Z_MAIN + 1.25, 'blockout_c')
    for y in (-1.5, 1.5):
        c.box(4.6, 5.2, y - 0.28, y + 0.28, spec.Z_MAIN, spec.Z_MAIN + 0.45, 'blockout_c')
    c.box(1.5, 2.2, -1.5, 1.5, spec.Z_MAIN, spec.Z_MAIN + 0.85, 'blockout_c')
    finish('cockpit_stations', c, 'cockpit')
    # engines
    e = MB(); E = spec.ENG
    for sd in (1, -1):
        y = sd * E['pod_y']
        e.ngon_prism((E['pod_s0'], y, E['pod_z']), (E['pod_s0'] + 1.6, y, E['pod_z']), E['pod_r'], 8, 'blockout_b', ph=math.pi / 8)
        e.cyl((E['pod_s0'] + 1.6, y, E['pod_z']), (E['pod_s1'] - 0.8, y, E['pod_z']), E['pod_r'] * 0.94, 'blockout_b', n=32)
        e.cyl((E['pod_s1'] - 0.8, y, E['pod_z']), (E['pod_s1'], y, E['pod_z']), E['pod_r'] * 0.94, 'blockout_b', n=32, r1=E['pod_r'] * 0.78)
        y = sd * E['top_y']
        e.cyl((E['top_s0'], y, E['top_z']), (E['top_s1'], y, E['top_z']), E['top_r'], 'blockout_b', n=24)
    e.cyl((E['core_s0'], 0, 0), (E['core_s1'], 0, 0), E['core_r'], 'blockout_b', n=32, r1=E['core_r'] * 0.85)
    finish('engine_pods', e, 'engines')
    # landing gear, down
    g = MB(); Gs = spec.GEAR
    for key in ('fwd', 'aft'):
        for sd in (1, -1):
            s, y = Gs[key]['s'], sd * Gs[key]['y']
            g.cyl((s, y, Gs['trunnion_z']), (s, y, spec.Z_GROUND + 0.15), 0.13, 'blockout_e', n=12)
            g.cyl((s, y, spec.Z_GROUND), (s, y, spec.Z_GROUND + 0.15), Gs['pad_r'], 'blockout_e', n=20)
            w0, w1 = Gs[key]['well']
            g.box(w0, w1, y - 0.5, y + 0.5, Gs['trunnion_z'] - 0.55, Gs['trunnion_z'] + 0.25, 'blockout_e')
    finish('gear_legs_and_wells', g, 'landing_gear')
    # the lift chassis, lowered to the ground
    l = MB(); zc = spec.Z_GROUND + Lf['chassis_depth']
    l.box(Lf['s0'] + 0.05, Lf['s1'] - 0.05, -Lf['half_w'] + 0.05, Lf['half_w'] - 0.05, spec.Z_GROUND, zc, 'blockout_d')
    for s in (Lf['s0'] + 0.25, Lf['s1'] - 0.25):
        for y in (-Lf['half_w'] + 0.25, Lf['half_w'] - 0.25):
            l.cyl((s, y, zc), (s, y, spec.Z_LOWER + spec.HEAD_LOWER), 0.07, 'blockout_d', n=10)
    finish('lift_chassis_lowered', l, 'lift_chassis')
    # lander in its bay
    b = MB(); Ld = spec.LANDER; sc = 0.5 * (Lb['s0'] + Lb['s1'])
    b.box(sc - Ld['length'] / 2, sc + Ld['length'] / 2, -Ld['width'] / 2, Ld['width'] / 2, spec.Z_LOWER + 0.15, spec.Z_LOWER + 0.15 + Ld['height'], 'blockout_f')
    finish('lander_stowed', b, 'lander_bay')
    # gadgets
    q = MB(); C = spec.CHIN_CANNON
    q.sphere((C['s'], 0, C['z']), 0.55, 'blockout_c', n=16)
    for y in (-C['twin'], C['twin']):
        q.cyl((C['s'] - C['barrel_len'], y, C['z'] - 0.1), (C['s'], y, C['z'] - 0.1), C['barrel_r'], 'blockout_c', n=10)
    q.box(spec.BELLY_POD['s'] - 1.3, spec.BELLY_POD['s'] + 1.3, -0.45, 0.45, -3.4, -2.95, 'blockout_c')
    q.box(10.0, 12.5, -0.6, 0.6, 2.95, 3.3, 'blockout_c'); q.box(15.0, 19.0, -0.35, 0.35, 2.95, 3.25, 'blockout_c')
    finish('gadget_volumes', q, 'gadgets')
    # figures: on the ground, on the lift, pilot, on the main deck, in the lander bay
    f = MB()
    f.merge(figure_mb(11.4, 4.6, spec.Z_GROUND)); f.merge(figure_mb(11.4, 0.3, zc)); f.merge(figure_mb(2.9, 0.8, spec.Z_MAIN + 0.45, seated=True))
    f.merge(figure_mb(11.0, 0.0, spec.Z_MAIN)); f.merge(figure_mb(13.9 + 0.2, -1.0, spec.Z_LOWER)); f.merge(figure_mb(22.5, 0.0, spec.Z_MAIN))
    finish('figures_1p80m', f, 'figures')
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'work', 'wayfarer_blockout.blend'))
    print('BLOCKOUT', {k: v['tris'] for k, v in kit.STATS.items()})

if __name__ == '__main__':
    build()
