"""Plots for heat/sim.py (matplotlib, Agg). One y-scale per panel; fixed categorical colour order.

    python3 plots.py        # redraw from heat.json without re-running the simulation
"""
import json, os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#8a5cd6', '#52514e']
INK, MUTED, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'bold',
                     'axes.titlelocation': 'left', 'lines.linewidth': 1.6, 'legend.frameon': False, 'figure.dpi': 130})


def save(fig, out, name):
    fig.tight_layout(); fig.savefig(os.path.join(out, name)); plt.close(fig)

def hline(ax, y, text, color=MUTED):
    ax.axhline(y, color=color, lw=0.7, ls=(0, (2, 3)))
    ax.text(0.995, y, text + ' ', transform=ax.get_yaxis_transform(), fontsize=6.5, color=color, va='bottom', ha='right')

def parts(ax, G, y=0.02):
    """Shade the handguard and gas block along a z axis."""
    m = G['marks_mm']
    for (a, b), name in ((m['handguard'], 'handguard'), (m['gas_block'], 'gas block'), (m['neck'], 'neck'), (m['flash_hider'], 'flash hider')):
        b = min(b, G['muzzle_mm'])
        ax.axvspan(a, b, color=GRID, alpha=0.45, lw=0)
        ax.text(0.5 * (a + b), y, name, transform=ax.get_xaxis_transform(), fontsize=6.5, color=MUTED, ha='center', va='bottom', rotation=90 if b - a < 30 else 0)


def make_all(D, here, SH=None):
    out = os.path.join(here, 'plots'); os.makedirs(out, exist_ok=True)
    G = D['geometry']; V = D['validation']; S = D['schedules']; H = D['shot_heat']
    man = S['manual_250_in_3min']; ms = man['series']

    # 1 ---- heat per shot along the bore
    s = np.array(H['s_from_bolt_face_mm'])
    fig, ax = plt.subplots(2, 1, figsize=(7.5, 6.6), sharex=True)
    ax[0].plot(s, H['J_per_m_cold'], C[0], label='bore at 25 °C'); ax[0].plot(s, H['J_per_m_at_600K'], C[1], label='bore at 327 °C (600 K)')
    ax[0].plot(s, H['J_per_m_at_900K'], C[2], label='bore at 627 °C (900 K)'); ax[0].plot(s, H['friction_J_per_m'], C[5], label='bullet friction and engraving')
    ax[0].set_ylabel('heat left in the bore, J per metre per shot'); ax[0].set_ylim(0); ax[0].legend(loc='center', bbox_to_anchor=(0.5, 0.3), fontsize=7.5, ncol=2)
    ax[0].set_title('Heat per shot from the interior ballistics: %.0f J into a cold bore, %.0f J at 627 °C' % (H['bore_J']['cold_bore'], H['bore_J']['bore_at_900K']))
    ax[1].plot(s, H['peak_flux_MW_m2'], C[0]); ax[1].set_ylabel('peak heat flux, MW/m²', color=C[0]); ax[1].set_ylim(0)
    a2 = ax[1].twinx(); a2.plot(s, H['peak_surface_C_cold'], C[1]); a2.set_ylabel('peak bore surface temperature, °C (cold start)', color=C[1]); a2.grid(False); a2.set_ylim(0)
    a2.spines['right'].set_visible(True)
    ax[1].set_xlabel('distance from the bolt face, mm (case mouth at 44.7, muzzle at 368.3)')
    ax[1].set_title('Peak flux and bore surface temperature during one shot')
    save(fig, out, '01_shot_heat.png')

    # 2 ---- Crane chamber temperatures
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    for a, key, title in ((ax[0], 'semi', 'Semi-automatic'), (ax[1], 'double_tap', 'Double taps')):
        g = V['marsh_government'][key]; h = V['marsh_socom'][key]; x1 = np.arange(1, 8); x2 = np.arange(8, 15)
        a.plot(x1, g['measured_C'], 'o', color=INK, ms=5, label='measured (NSWC Crane, Marsh 2006)'); a.plot(x2, g['second_measured_C'], 'o', color=INK, ms=5)
        a.plot(x1, g['model_C'], '-', color=C[0], label='model, government barrel'); a.plot(x2, g['second_model_C'], '-', color=C[0])
        a.plot(x1, h['model_C'], '-', color=C[1], label='model, SOCOM barrel'); a.plot(x2, h['second_model_C'], '-', color=C[1])
        a.axvline(7.5, color=MUTED, lw=0.6, ls=(0, (2, 3)))
        a.text(4, 0.03, 'fitted (magazines 1 to 7)', transform=a.get_xaxis_transform(), ha='center', fontsize=7, color=MUTED)
        a.text(11, 0.03, 'held out (8 to 14, after a pause)', transform=a.get_xaxis_transform(), ha='center', fontsize=7, color=MUTED)
        a.set_xlabel('30-round magazine'); a.set_title(title); a.set_xticks(range(1, 15))
    ax[0].set_ylabel('outside of the chamber at the shoulder, °C'); ax[0].legend(loc='upper left', fontsize=7.5)
    e1 = V['marsh_first_sequence_error_C']; e2 = V['marsh_second_sequence_error_C']
    fig.suptitle('M4A1 chamber temperature: fitted part rms %.1f °C; held-out part rms %.1f °C, bias %+.1f °C' % (e1['rms'], e2['rms'], e2['bias']), x=0.01, ha='left', fontsize=10, fontweight='bold')
    save(fig, out, '02_validation_crane.png')

    # 3 ---- fire to destruction
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for key, name, c in (('destruction_colt', 'M4 government barrel', C[0]), ('destruction_colt_socom', 'M4A1 SOCOM (heavy) barrel', C[1])):
        tr = V[key]['trace']; ax.plot(tr['rounds'], tr['barrel_max_outer_C'], color=c, label='model, ' + name)
    hline(ax, 525, 'visible glow in the dark, 525 °C'); hline(ax, 737, 'weak enough to burst, 737 °C (Army message)'); hline(ax, 817, 'rupture temperature of the Purdue simulation, 817 °C')
    ax.axvline(535, color=INK, lw=1.0); ax.text(535, 0.42, 'Colt test: M4 barrel \nruptured at 535 rounds ', transform=ax.get_xaxis_transform(), fontsize=7, va='top', ha='right')
    ax.axvspan(540, 596, color=C[3], alpha=0.25, lw=0); ax.text(600, 0.22, ' Windham 1996: M4A1 barrels\n ruptured at 540 to 596', transform=ax.get_xaxis_transform(), fontsize=7, ha='left', va='top')
    ax.axvline(911, color=C[1], lw=1.0, ls=(0, (4, 2))); ax.text(911, 0.42, 'Colt: heavy barrel intact \nat 911 rounds (gas tube failed) ', transform=ax.get_xaxis_transform(), fontsize=7, va='top', ha='right')
    ax.set_xlabel('rounds fired (30-round magazines on automatic, %.1f s magazine changes)' % V['destruction_colt']['reload_s']); ax.set_ylabel('hottest point of the barrel surface, °C')
    mk = V['destruction_colt']['marks']
    ax.set_title('Fire to destruction, nothing fitted: 737 °C at %d rounds, 817 °C at %d' % (mk['weakened_737C']['rounds'], mk['rupture_817C']['rounds'] if 'rupture_817C' in mk else -1))
    ax.legend(loc='lower left', bbox_to_anchor=(0.27, 0.0), fontsize=7.5); ax.set_ylim(0)
    save(fig, out, '03_validation_destruction.png')

    # 4 ---- the manual's 250 rounds in 3 minutes
    t = np.array(ms['t']); tf = man['fire_duration_s']
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True, gridspec_kw=dict(width_ratios=[1, 1.25]))
    lines = (('throat_bore', 'bore surface at the throat'), ('barrel_max_outer', 'hottest outer surface'), ('chamber_wall', 'chamber wall'), ('gas_block', 'gas block'),
             ('flash_hider', 'flash hider'), ('handguard_hand', 'handguard under the hand'))
    for a, m, xl in ((ax[0], t <= tf + 1, 'time, s (firing)'), (ax[1], t >= tf, 'time, min (cooling)')):
        for i, (k, name) in enumerate(lines): a.plot(t[m] / (1 if a is ax[0] else 60.0), np.array(ms[k])[m], color=C[i], label=name)
        a.set_xlabel(xl)
    ax[1].set_xscale('log'); ax[1].set_xticks([3, 5, 10, 20, 30, 60, 90]); ax[1].set_xticklabels(['3', '5', '10', '20', '30', '60', '90'])
    ax[0].set_ylabel('temperature, °C'); ax[0].legend(loc='upper left', fontsize=7.5)
    ax[0].set_title("HK manual's limit: 250 rounds in 3 minutes"); ax[1].set_title('then left to cool in still air at 25 °C')
    save(fig, out, '04_manual_250_in_3min.png')

    # 5 ---- profiles along the barrel
    F = man['fields']; z = np.array(G['z_mm']); zh = np.array(G['handguard_z_mm']); ft = np.array(F['t'])
    picks = [int(np.argmin(np.abs(ft - x))) for x in (60, 120, tf, tf + 120, tf + 600, tf + 1800)]
    fig, ax = plt.subplots(3, 1, figsize=(7.5, 8.6), sharex=True)
    cm = plt.get_cmap('viridis')
    for n, i in enumerate(picks):
        col = cm(0.92 * n / (len(picks) - 1)); lab = ('%.0f s' % ft[i]) if ft[i] <= tf + 1 else ('%.0f min after cease fire' % ((ft[i] - tf) / 60))
        ax[0].plot(z, F['bore_C'][i], color=col, label=lab); ax[1].plot(z, F['outer_C'][i], color=col); ax[2].plot(zh, F['handguard_C'][i], color=col)
    ax[0].set_ylabel('bore-side cell, °C'); ax[1].set_ylabel('outer surface, °C'); ax[2].set_ylabel('handguard (mean of section), °C')
    ax[2].legend(*ax[0].get_legend_handles_labels(), fontsize=7, ncol=1, loc='center left', bbox_to_anchor=(0.72, 0.5)); ax[2].set_xlabel('position along the bore, mm (0 = front face of the upper receiver)')
    ax[0].set_title('Temperature along the barrel, 250 rounds in 3 minutes'); ax[1].set_title('Outer surface'); ax[2].set_title('Handguard')
    for a in ax: parts(a, G)
    save(fig, out, '05_profiles.png')

    # 6 ---- all schedules
    ids = list(S.keys()); n = len(ids)
    fig, ax = plt.subplots((n + 1) // 2, 2, figsize=(10.5, 2.6 * ((n + 1) // 2)))
    ax = ax.ravel()
    for a, sid in zip(ax, ids):
        sc = S[sid]; se = sc['series']; tt = np.array(se['t']); m = tt <= sc['fire_duration_s'] * 1.6 + 60
        for i, (k, name) in enumerate((('barrel_max_outer', 'hottest outer surface'), ('chamber_wall', 'chamber wall'), ('gas_block', 'gas block'), ('handguard_hand', 'handguard under the hand'))):
            a.plot(tt[m], np.array(se[k])[m], color=C[i], label=name)
        a.axvline(sc['fire_duration_s'], color=MUTED, lw=0.6, ls=(0, (2, 3)))
        a.set_title(sc['title'], fontsize=7.5); a.set_ylim(0)
    for a in ax[n:]: a.axis('off')
    ax[0].legend(fontsize=6.5, loc='upper left')
    for a in ax[max(0, n - 2):n]: a.set_xlabel('time, s (dotted line: cease fire)')
    for a in ax[::2]: a.set_ylabel('°C')
    save(fig, out, '06_schedules.png')

    # 7 ---- effects on the manual's schedule
    fig, ax = plt.subplots(2, 2, figsize=(10.5, 7.0)); tm = t / 60.0; m = t <= tf + 1800
    a = ax[0, 0]; a.plot(tm[m], np.array(ms['mirage_strength'])[m], C[0]); a.set_ylabel('mirage strength, 0 to 1', color=C[0]); a.set_ylim(0)
    b = a.twinx(); b.plot(tm[m], np.array(ms['mirage_jitter_moa'])[m], C[1]); b.set_ylabel('image jitter on the sight line, MOA rms', color=C[1]); b.grid(False); b.spines['right'].set_visible(True); b.set_ylim(0)
    a.set_title('Mirage (heat shimmer) over the sights')
    a = ax[0, 1]; a.plot(tm[m], np.array(ms['handguard_hand'])[m], C[0], label='bottom rail under the hand'); a.plot(tm[m], np.array(ms['handguard_top_max'])[m], C[1], label='hottest point of the top rail')
    for lv in D['effects']['comfort']['levels'][:-1]: hline(a, lv['below_C'], '%.0f °C' % lv['below_C'])
    a.set_ylabel('handguard surface, °C'); a.legend(fontsize=7.5, loc='lower right'); a.set_title('Handguard against ISO 13732-1 burn thresholds')
    a = ax[1, 0]; a.plot(tm[m], np.array(ms['chamber_wall'])[m], C[0], label='chamber wall'); a.plot(tm[m], np.array(ms['round_case'])[m], C[1], label='case of the chambered round')
    ck = D['effects']['cookoff']['constants']; hline(a, ck['caution_C'], 'caution, %.0f °C' % ck['caution_C']); hline(a, ck['danger_C'], 'cook-off within seconds, %.0f °C' % ck['danger_C'])
    a.set_ylabel('°C'); a.set_xlabel('time, min'); a.legend(fontsize=7.5, loc='lower right'); a.set_title('Cook-off: chamber and chambered round')
    a = ax[1, 1]; a.plot(tm[m], np.array(ms['poi_bow_moa'])[m], C[0]); a.set_ylabel('impact shift from barrel bow, MOA (negative = low)', color=C[0])
    b = a.twinx(); b.plot(tm[m], np.array(ms['mv_delta_next_m_s'])[m], C[1]); b.set_ylabel('muzzle velocity gain of the chambered round, m/s', color=C[1]); b.grid(False); b.spines['right'].set_visible(True)
    a.set_xlabel('time, min'); a.set_title('Point of impact: barrel bow and warm propellant')
    fig.suptitle('Effects during and after 250 rounds in 3 minutes', x=0.01, ha='left', fontsize=10, fontweight='bold')
    save(fig, out, '07_effects.png')

    # 8 ---- sensitivity
    sn = D['sensitivity_manual_250_in_3min']; names = list(sn.keys())
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 4.2), sharey=True)
    for a, k, title in ((ax[0], 'peak_chamber_wall_C', 'peak chamber wall, °C'), (ax[1], 'peak_barrel_outer_C', 'peak outer barrel surface, °C'), (ax[2], 'peak_handguard_hand_C', 'peak handguard under the hand, °C')):
        v = [sn[nm][k] for nm in names]; y = np.arange(len(names))[::-1]
        a.barh(y, v, color=[C[5] if nm == 'still_25C' else C[0] for nm in names], height=0.62)
        for yi, vi in zip(y, v): a.text(vi, yi, ' %.0f' % vi, va='center', fontsize=7)
        a.set_yticks(y); a.set_yticklabels([nm.replace('_', ' ') for nm in names], fontsize=7.5); a.set_title(title, fontsize=9); a.grid(axis='y', visible=False); a.set_xlim(0, max(v) * 1.15)
    fig.suptitle('What moves the answer: 250 rounds in 3 minutes with one input changed', x=0.01, ha='left', fontsize=10, fontweight='bold')
    save(fig, out, '08_sensitivity.png')
    print('plots written to', out)


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    make_all(json.load(open(os.path.join(here, 'heat.json'))), here)
