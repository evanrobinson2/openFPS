"""Plots for the suppressor simulation (called by sim.py). Simulation only: nothing here is drawn from a recording."""
import math, os, sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model'))
import geom, core

C = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


def _save(fig, out, name):
    fig.tight_layout(); fig.savefig(os.path.join(out, name), dpi=110); plt.close(fig)


def make(data, checks, shots, runs, out):
    os.makedirs(out, exist_ok=True)
    cfg = data['config']; sub = shots['sub']; first = shots['first']; bare = shots['bare']
    names = cfg['chambers']['names']

    # 1 chamber pressures
    fig, ax = plt.subplots(figsize=(9, 5))
    t = np.array(sub['rec']['t']) * 1e3; p = np.array(sub['rec']['p']) / 1e6
    ax.semilogy(t, np.array(sub['rec']['p_bore']) / 1e6, 'k', lw=1.6, label='bore')
    for k in range(p.shape[1]): ax.semilogy(t, p[:, k], color=C[k % 8], lw=1.1, label=names[k])
    ax.semilogy(np.array(bare['rec']['t']) * 1e3, np.array(bare['rec']['p_bore']) / 1e6, 'k--', lw=1.0, label='bore, no suppressor')
    ax.set_xlim(0, 12); ax.set_ylim(0.09, 200); ax.set_xlabel('time after the bullet leaves the crown, ms'); ax.set_ylabel('pressure, MPa')
    ax.set_title('Bore and chamber pressures, reference shot (spent gas in the can, 320 K wall)'); ax.grid(alpha=0.3, which='both'); ax.legend(fontsize=8, ncol=2)
    _save(fig, out, 'chamber_pressures.png')

    # 2 first 0.6 ms, linear: the bullet's passage
    fig, ax = plt.subplots(figsize=(9, 4.6))
    m = t < 0.6
    for k in range(p.shape[1]): ax.plot(t[m], p[m, k], color=C[k % 8], lw=1.2, label=names[k])
    for j, x in enumerate(cfg['chambers']['aperture_from_crown_m']):
        ax.axvline(x / cfg['bullet']['v'] * 1e3, color=C[j % 8], ls=':', lw=0.8)
    ax.set_xlabel('time after the bullet leaves the crown, ms'); ax.set_ylabel('pressure, MPa'); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title('Chamber filling while the bullet is in the can (dotted: the bullet base reaches each aperture)')
    _save(fig, out, 'chamber_filling.png')

    # 3 sound pulses at 1 m
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    for s, lab, col in ((sub, 'subsequent shot', C[0]), (first, 'first round (air in a cold can)', C[1])):
        tt = np.array(s['rec']['t']) * 1e3; mono = np.array(s['rec']['mono']); dip = np.array(s['rec']['dip'])
        axs[0].plot(tt, mono, color=col, lw=1.1, label=lab)
        axs[1].plot(tt, mono + cfg['listen']['dip'][1] * dip, color=col, lw=1.1, label=lab)
    for a, ttl in zip(axs, ('1 m to the side (90 degrees)', '1 m toward the shooter (174.8 degrees)')):
        a.set_xlim(0, 3); a.set_xlabel('time after the bullet leaves the crown, ms'); a.set_ylabel('sound pressure at 1 m, Pa'); a.set_title(ttl); a.grid(alpha=0.3); a.legend(fontsize=8)
    _save(fig, out, 'sound_pulse.png')

    # 4 levels
    fig, ax = plt.subplots(figsize=(9, 4.6))
    L = data['sound']; keys = ['side_1m', 'shooter', 'bystander', 'downrange']; lab = ['1 m, 90 degrees', "shooter's ear", 'bystander 5 m right', '50 m down-range']
    x = np.arange(len(keys)); w = 0.2
    ax.bar(x - 1.5 * w, [L['subsequent']['levels'][k]['bare_dB'] for k in keys], w, label='bare muzzle blast', color='#444')
    ax.bar(x - 0.5 * w, [L['first_round']['levels'][k]['suppressed_dB'] for k in keys], w, label='suppressed, first round', color=C[1])
    ax.bar(x + 0.5 * w, [L['subsequent']['levels'][k]['suppressed_dB'] for k in keys], w, label='suppressed, subsequent', color=C[0])
    ax.bar(x + 1.5 * w, [L['hot']['levels'][k]['suppressed_dB'] for k in keys], w, label='suppressed, hot can', color=C[3])
    ck = L['subsequent']['levels']['downrange']['crack_dB']
    ax.plot([3 - 2.2 * w, 3 + 2.2 * w], [ck, ck], 'm-', lw=2); ax.text(3, ck + 0.8, 'bullet crack %.0f dB: unchanged' % ck, ha='center', fontsize=8, color='m')
    ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylim(100, 170); ax.set_ylabel('peak sound pressure level, dB re 20 uPa'); ax.grid(alpha=0.3, axis='y'); ax.legend(fontsize=8)
    ax.set_title('Peak level of the muzzle source, simulated')
    _save(fig, out, 'levels.png')

    # 5 bore pressure and the action
    fig, axs = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    te = data['hk416']['exit_after_sear_s']
    axs[0].semilogy(np.array(bare['rec']['t']) * 1e3, np.array(bare['rec']['p_bore']) / 1e6, 'k--', label='bore, bare')
    axs[0].semilogy(t, np.array(sub['rec']['p_bore']) / 1e6, 'k', label='bore, suppressed')
    for key, r, ls in (('bare', runs['bare'], '--'), ('suppressed', runs['supp'], '-')):
        ev = dict(r['events'][0])
        for nm, col in (('unlock_start', C[2]), ('unlock', C[1])):
            axs[0].axvline((ev[nm] - te) * 1e3, color=col, ls=ls, lw=0.9)
        axs[1].plot((r['t'] - te) * 1e3, r['v'], 'k' + ls, label='carrier speed, ' + key)
    axs[0].set_ylim(0.09, 200); axs[0].set_ylabel('bore pressure, MPa'); axs[0].grid(alpha=0.3, which='both'); axs[0].legend(fontsize=8)
    axs[0].set_title('Residual bore pressure and the HK416 carrier (green: bolt starts to turn, red: lugs clear; dashed = bare)')
    axs[1].set_xlim(0, 30); axs[1].set_ylim(-1, 7); axs[1].set_xlabel('time after the bullet leaves the crown, ms'); axs[1].set_ylabel('carrier speed, m/s (rearward +)'); axs[1].grid(alpha=0.3); axs[1].legend(fontsize=8)
    _save(fig, out, 'back_pressure.png')

    # 6 heat strings
    fig, ax = plt.subplots(figsize=(9, 4.6))
    per = data['action']['cases']['suppressed']['period_s']
    for (nm, times), col in zip((('30 rounds, 1 per second', [i * 1.0 for i in range(30)]), ('30 rounds automatic', [i * per for i in range(30)]),
                                 ('100 rounds, 2 per second', [i * 0.5 for i in range(100)]), ('210 rounds in 10 minutes', [i * (600.0 / 210) for i in range(210)])), C):
        h = core.heat_string(cfg, times)
        ax.plot(range(1, len(h) + 1), [x['T_after_K'] - 273.15 for x in h], color=col, label=nm)
    ax.set_xlabel('round'); ax.set_ylabel('bulk can temperature, C'); ax.grid(alpha=0.3); ax.legend(fontsize=8); ax.set_title('Can heating through a string (still air)')
    _save(fig, out, 'heat_strings.png')

    # 7 the section, from the recipe
    fig, ax = plt.subplots(figsize=(11, 4.2))
    cols = dict(CanBody='#30343a', CanCollar='#15171a', Baffle='#9a948a')
    for nm, part in geom.parts().items():
        for sg in (1, -1):
            ax.fill([q[0] for q in part['poly']], [sg * q[1] for q in part['poly']], color=cols[part['mat']], lw=0)
    for sg in (1, -1):
        hp = geom.hider_poly(); ax.fill([q[0] for q in hp], [sg * q[1] for q in hp], color='#6f7780', lw=0)
        ax.fill([-25, -25, geom.S_HIDER0, geom.S_HIDER0, geom.S_CROWN, geom.S_CROWN], [sg * 2.8, sg * 8.9, sg * 8.9, sg * 6.2, sg * 6.2, sg * 2.8], color='#555c64', lw=0)
        j = geom.jaw(); ax.fill([j['s0'], j['s0'], j['s1'], j['s1']], [sg * j['r_in'], sg * j['r_out'], sg * j['r_out'], sg * j['r_in']], color='#b5651d', lw=0)
    pk = data['states']['subsequent']['peak_p_MPa']
    xs = [45.0] + [geom.baffle_apex(i) + 12.0 for i in range(geom.G['n_baffles'])]
    for k, x in enumerate(xs): ax.text(x, -13.2, '%.1f' % pk[k + 1], ha='center', fontsize=8, color='#b00')
    ax.text(45, 23.5, 'blast chamber', ha='center', fontsize=8)
    for i in range(geom.G['n_baffles']): ax.text(geom.baffle_apex(i) + 5, 23.5, geom.baffle_name(i).replace('_', ' '), ha='center', fontsize=7, rotation=20)
    ax.text(geom.L - 2, 23.5, 'end cap', ha='center', fontsize=8); ax.text(7, 23.5, 'collar, jaws', ha='center', fontsize=8); ax.text(22, -24.5, 'mount', ha='center', fontsize=8)
    ax.text(30, 1.0, 'flash hider (rifle)', ha='center', fontsize=7, color='w'); ax.text(100, -24.5, 'red: peak chamber pressure, MPa (reference shot)', fontsize=8, color='#b00')
    ax.plot([-25, geom.L + 12], [0, 0], 'k-.', lw=0.5); ax.set_aspect('equal'); ax.set_xlim(-27, geom.L + 14); ax.set_ylim(-28, 30)
    ax.set_xlabel('s, mm from the rear face of the can'); ax.set_ylabel('r, mm'); ax.set_title('Section from the recipe (model/geom.py)')
    _save(fig, out, 'section.png')
