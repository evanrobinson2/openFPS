"""Plots for the malfunction simulation (matplotlib, Agg). Simulation output and published counts only."""
import math, os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#8a5cd6', '#c2410c']
INK, MUTED, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'bold',
                     'axes.titlelocation': 'left', 'axes.axisbelow': True, 'lines.linewidth': 1.6, 'legend.frameon': False, 'figure.dpi': 130})
NAMES = dict(FFD='failure to feed\n(with magazine)', FTC='failure to\nchamber', FFR='failure to\nfire', FXT='failure to\nextract', FEJ='failure to\neject', FBR='bolt failed to\nlock back')


def save(fig, out, name):
    fig.tight_layout(); fig.savefig(os.path.join(out, name)); plt.close(fig)


def make(d, out):
    os.makedirs(out, exist_ok=True)
    TAB, P = d['TAB'], d['P']

    # 1. dust test: simulated against published, by type
    rows = d['rows']; fig, ax = plt.subplots(figsize=(7.6, 3.6)); xs = range(len(rows))
    ax.bar([x - 0.2 for x in xs], [r['published'] for r in rows], 0.38, color=C[0], label='published, one run (line: Poisson 95 % of that count)')
    ax.bar([x + 0.2 for x in xs], [r['sim_mean_per_60000'] for r in rows], 0.38, color=C[1], label='simulated, mean of %d runs' % d['reps'])
    for x, r in zip(xs, rows):
        lo, hi = r['poisson95_of_published']; ax.plot([x - 0.2, x - 0.2], [lo, hi], color=INK, lw=1)
        ax.text(x - 0.2, hi * 1.12 + 0.3, str(r['published']), ha='center', fontsize=7, color=MUTED); ax.text(x + 0.2, r['sim_mean_per_60000'] * 1.12 + 0.3, '%.1f' % r['sim_mean_per_60000'], ha='center', fontsize=7, color=MUTED)
    ax.set_yscale('log'); ax.set_ylim(1, 400); ax.set_xticks(list(xs)); ax.set_xticklabels([NAMES[r['category']] for r in rows], fontsize=7.5)
    ax.set_ylabel('stoppages per 60,000 rounds'); ax.set_title('2007 dust test, HK416: stoppages by type (calibration targets)'); ax.legend(fontsize=7.5)
    save(fig, out, '01_dust_test_by_type.png')

    # 2. carrier energy against travel, with the thresholds
    fig, ax = plt.subplots(figsize=(7.6, 3.6)); xs = TAB['x_mm']; xp = TAB['x_peak_mm']
    st = d['new_state']({}); M0 = d['margins'](st)
    st1 = d['new_state'](dict(dust=1.0)); st1['nLube'] = 600; M1 = d['margins'](st1)
    st2 = d['new_state'](dict(pistonRingsWorn=1.0, ammo='commercial_223', ambientC=-20.0)); M2 = d['margins'](st2)
    for M, lab, col in ((M0, 'clean, M855', C[0]), (M1, 'dust 1, 600 rounds since the wipe', C[1]), (M2, 'worn piston rings, commercial .223, -20 C', C[2])):
        ax.plot([x for x in xs if x >= xp], [max(0, TAB['ke_out_J'][i] + M['shift'] - M['drag'] * (x - xp) * 1e-3) for i, x in enumerate(xs) if x >= xp], color=col, label=lab)
    for x, lab in ((TAB['x_eject_mm'], 'case clears the port'), (TAB['x_pick_mm'], 'bolt behind the next round'), (TAB['x_hold_mm'], 'bolt catch'), (94, 'buffer')):
        ax.axvline(x, color=MUTED, lw=0.6, ls=(0, (2, 3))); ax.text(x, 9.2, ' ' + lab, rotation=90, va='top', fontsize=6.5, color=MUTED)
    ax.fill_between([xp, 95], [-P['energy_scatter'] * 1.81 * 2] * 2, [P['energy_scatter'] * 1.81 * 2] * 2, color=GRID, alpha=0.6, lw=0)
    ax.text(94, -0.95, 'grey band: 2 sd of the shot-to-shot scatter about zero', fontsize=6.5, color=MUTED, ha='right')
    ax.set_xlabel('carrier travel, mm'); ax.set_ylabel('carrier kinetic energy, J'); ax.set_ylim(-1.2, 9.5); ax.set_title('Carrier energy on the rearward stroke (curve from action.json)'); ax.legend(fontsize=7.5, loc='lower left', bbox_to_anchor=(0.0, 0.16))
    save(fig, out, '02_carrier_energy_margin.png')

    # 3. probability per round against dust, by type
    fig, ax = plt.subplots(figsize=(7.6, 3.6)); dust = [i / 20 for i in range(21)]; series = {}
    for dv in dust:
        tot = {}
        for n in range(0, 30, 3):
            st = d['new_state'](dict(dust=dv)); st['nLube'] = 300; st['nClean'] = 300; st['mag']['rounds'] = n
            for k, v in d['probabilities'](st, grid=32).items():
                if k != 'fired': tot[k.split(':')[0]] = tot.get(k.split(':')[0], 0.0) + v / 10
        for k, v in tot.items(): series.setdefault(k, []).append(v)
    for i, k in enumerate(['failure_to_feed', 'stovepipe', 'bolt_override', 'double_feed', 'failure_to_fire', 'failure_to_extract']):
        ax.plot(dust, series[k], color=C[i], label=k.replace('_', ' '))
    ax.set_yscale('log'); ax.set_xlabel('dust load (0 clean, 1 the Aberdeen chamber), 300 rounds since the wipe'); ax.set_ylabel('probability per round')
    ax.set_title('How the per-round probabilities move with dust'); ax.legend(fontsize=7, ncol=2)
    save(fig, out, '03_probability_vs_dust.png')

    # 4. one simulated dust test: cumulative stoppages of ten rifles, with the maintenance marks
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    for i, r in enumerate(d['runs']):
        ax.step([0] + r['at'] + [6000], [0] + list(range(1, len(r['at']) + 1)) + [len(r['at'])], where='post', color=C[0], lw=0.8, alpha=0.7)
    for x in range(600, 6000, 600): ax.axvline(x, color=MUTED if x % 1200 else INK, lw=0.5, ls=(0, (2, 3)))
    ax.set_xlabel('rounds fired by the rifle (dotted: wipe and lubricate every 600, clean every 1,200)'); ax.set_ylabel('stoppages so far')
    ax.set_title('One simulated dust test: ten rifles, 6,000 rounds each (seeds 1000 to 1009)', fontsize=9.5)
    save(fig, out, '04_dust_test_run.png')

    # 5. conditions table as a chart: mean rounds between stoppages
    cond = d['cond']; fig, ax = plt.subplots(figsize=(7.6, 5.6)); ys = range(len(cond))
    ax.barh(list(ys), [c['mrbs'] for c in cond], color=C[0]); ax.set_xscale('log'); ax.set_yticks(list(ys)); ax.set_yticklabels([c['condition'] for c in cond], fontsize=6.5); ax.invert_yaxis()
    for y, c in zip(ys, cond): ax.text(c['mrbs'] * 1.08, y, '%.0f' % c['mrbs'], va='center', fontsize=6.5, color=MUTED)
    ax.set_xlabel('mean rounds between stoppages (analytic, averaged over a magazine)'); ax.set_title('One condition at a time (inferred sensitivities)')
    save(fig, out, '05_conditions.png')
