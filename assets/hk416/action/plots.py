"""Plots for sim.py (matplotlib, Agg). One y-scale per panel; fixed categorical colour order."""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']
INK, MUTED, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'bold',
                     'axes.titlelocation': 'left', 'lines.linewidth': 1.6, 'legend.frameon': False, 'figure.dpi': 130})


def marks(ax, ev, names, y=0.97, unit=1e3, shift=0.0):
    for i, k in enumerate(names):
        if k not in ev: continue
        x = (ev[k] - shift) * unit
        ax.axvline(x, color=MUTED, lw=0.6, ls=(0, (2, 3)))
        ax.text(x, y - 0.075 * (i % 4), ' ' + k.replace('_', ' '), transform=ax.get_xaxis_transform(), fontsize=6.5, color=MUTED, va='top')


def save(fig, out, name):
    fig.tight_layout(); fig.savefig(os.path.join(out, name)); plt.close(fig)


def make(data, runs, tab, info, FT, out):
    os.makedirs(out, exist_ok=True)
    ev = data['events']['times']; tig = ev['ignition']
    # 1 ---- internal ballistics
    t = tab['t'] * 1e3; m = t < 3.0
    semi = runs['semi_ads']; ms = (semi['t'] > tig) & (semi['t'] < tig + 3e-3)
    fig, ax = plt.subplots(3, 1, figsize=(7.5, 8), sharex=True)
    ax[0].plot(t[m], tab['pbr'][m] / 1e6, C[0], label='chamber (breech)'); ax[0].plot(t[m], tab['pport'][m] / 1e6, C[1], label='bore at the gas port')
    ax[0].plot((semi['t'][ms] - tig) * 1e3, semi['pc'][ms] / 1e6, C[2], label='gas cylinder'); ax[0].set_ylabel('pressure, MPa'); ax[0].legend(loc='center right')
    ax[0].set_title('Pressure: peak %.0f MPa; %.0f MPa at the port as the bullet passes' % (info['p_max'] / 1e6, info['p_port_at_passage'] / 1e6))
    ax[1].plot(t[m], tab['v'][m], C[0]); ax[1].set_ylabel('bullet velocity, m/s'); ax[1].set_title('Bullet velocity: %.0f m/s at the muzzle, %.2f ms after ignition' % (info['v_exit'], info['t_exit'] * 1e3))
    ax[2].plot(t[m], tab['fg'][m] / 1e3, C[0]); ax[2].set_ylabel('recoil force from the bore, kN'); ax[2].set_xlabel('time after charge ignition, ms')
    ax[2].set_title('Bore recoil force: %.2f N s in total' % info['impulse_total'])
    for a in ax: marks(a, {'bullet passes port': info['t_port'], 'bullet exit': info['t_exit']}, ['bullet passes port', 'bullet exit'])
    save(fig, out, '01_internal_ballistics.png')
    # 2 ---- firing train
    Hd, Sp, fev = FT; tt = np.arange(len(Hd)) * 1e-3
    fig, ax = plt.subplots(3, 1, figsize=(7.5, 7.5))
    ax[0].plot(tt, Hd, C[0]); ax[0].set_ylabel('hammer angle from the sear, deg'); ax[0].set_xlabel('time after sear release, ms')
    ax[0].set_title('Hammer fall: strikes the firing pin at %.2f ms with %.2f J' % (fev['hammer_strike'] * 1e3, fev['hammer_energy']))
    z = (tt > fev['hammer_strike'] * 1e3 - 0.2) & (tt < fev['ignition'] * 1e3 + 0.5)
    ax[1].plot(tt[z], Sp[z] * 1e3, C[0]); ax[1].set_ylabel('firing pin travel, mm'); ax[1].set_xlabel('time after sear release, ms')
    ax[1].set_title('Firing pin: %.1f mm of free travel, then a %.2f mm primer indent' % (data['params']['fp_float']['value'] * 1e3, fev['indent'] * 1e3))
    marks(ax[1], fev, ['hammer_strike', 'primer_contact', 'primer_fire', 'ignition'])
    k = np.arange(len(data['ballistics']['chamber_MPa'])) * data['ballistics']['dt'] * 1e3 + tig * 1e3; zz = k < tig * 1e3 + 0.5
    ax[2].plot(k[zz], np.array(data['ballistics']['chamber_MPa'])[zz], C[0]); ax[2].set_xlim(ax[1].get_xlim()); ax[2].set_ylabel('chamber pressure, MPa')
    ax[2].set_xlabel('time after sear release, ms'); ax[2].set_title('Pressure rise after ignition (lock time to primer contact %.2f ms)' % (fev['primer_contact'] * 1e3))
    save(fig, out, '02_firing_train.png')
    # 3 ---- operating cycle
    c = data['cycle']; tc = np.arange(len(c['carrier_mm'])) * c['dt'] * 1e3
    names = ['ignition', 'unlock', 'eject', 'buffer_impact', 'feed', 'chambered', 'in_battery']
    fig, ax = plt.subplots(4, 1, figsize=(8, 10.5), sharex=True)
    ax[0].plot(tc, c['carrier_mm'], C[0]); ax[0].set_ylabel('carrier travel, mm'); ax[0].set_title('Bolt carrier travel (rearward), one shot'); marks(ax[0], ev, names)
    ax[1].plot(tc, c['carrier_mps'], C[0]); ax[1].set_ylabel('carrier velocity, m/s'); ax[1].set_title('Carrier velocity (rearward positive)')
    ax[2].plot(tc, c['bolt_deg'], C[0]); ax[2].set_ylabel('bolt rotation, deg'); ax[2].set_title('Bolt rotation: 0 locked, 22.5 unlocked')
    ax[3].plot(tc, c['hammer_deg'], C[0]); ax[3].set_ylabel('hammer angle, deg'); ax[3].set_title('Hammer: falls, rests on the pin, is cocked by the carrier, returns to the sear')
    ax[3].set_xlabel('time after sear release, ms')
    save(fig, out, '03_operating_cycle.png')
    # 4 ---- receiver force
    fig, ax = plt.subplots(2, 1, figsize=(8, 6))
    mz = (semi['t'] > tig - 2e-4) & (semi['t'] < tig + 5e-3)
    ax[0].plot((semi['t'][mz]) * 1e3, semi['frecv'][mz] / 1e3, C[0]); ax[0].set_ylabel('force, kN'); ax[0].set_title('Axial force on the gun body, first 5 ms (rearward positive; the dip is the gas piston reaction)')
    marks(ax[0], ev, ['ignition', 'bullet_exit', 'unlock', 'piston_rod_stop'])
    ax[1].plot(tc, np.array(c['receiver_force_N']), C[0]); ax[1].set_ylim(-600, 600); ax[1].set_ylabel('force, N (clipped at 600)'); ax[1].set_xlabel('time after sear release, ms')
    ax[1].set_title('The same force over the whole cycle: spring, buffer impact, bolt closing'); marks(ax[1], ev, ['buffer_impact', 'feed', 'chambered', 'in_battery'])
    save(fig, out, '04_receiver_force.png')
    # 5, 6 ---- recoil pose
    for mode, fn, tmax in (('semi', '05_recoil_semi.png', 0.8), ('auto', '06_recoil_auto_10_rounds.png', 2.0)):
        r = data['recoil'][mode]; fig, ax = plt.subplots(4, 1, figsize=(8, 10), sharex=True)
        for j, (key, lab, ttl) in enumerate((('z_mm', 'translation along the bore, mm', 'Gun translation (negative = rearward)'), ('pitch_up_deg', 'pitch, deg', 'Muzzle rise (pitch about the support pivot)'),
                                             ('yaw_right_deg', 'yaw, deg', 'Yaw to the right (right-handed shooter)'), ('support_force_N', 'force, N', 'Force into the support: shoulder and arms (aimed) or hands (hip)'))):
            for i, st in enumerate(('ads', 'hip')):
                y = np.array(r[st][key]); tt = np.arange(len(y)) * data['recoil']['dt']; mm = tt <= tmax
                ax[j].plot(tt[mm], y[mm], C[i], label={'ads': 'aimed (shouldered)', 'hip': 'hip'}[st])
            ax[j].set_ylabel(lab); ax[j].set_title(ttl)
        ax[0].legend(loc='lower right'); ax[3].set_xlabel('time after the first sear release, s')
        fig.suptitle({'semi': 'One shot', 'auto': 'Ten rounds automatic at %.0f rpm' % data['auto']['rpm']}[mode], x=0.02, ha='left', fontsize=11, fontweight='bold')
        save(fig, out, fn)
    # 7 ---- brass
    b = data['brass']; fig, ax = plt.subplots(1, 2, figsize=(10, 4.6))
    seen = set()
    for tr in b['trajectories']:
        p = np.array(tr['pos']); i = 0 if tr['surface'] == 'concrete' else 1
        lab = tr['surface'] if tr['surface'] not in seen else None; seen.add(tr['surface'])
        ax[0].plot(-p[:, 0], p[:, 2], C[i], lw=1.2, label=lab); ax[0].plot(-p[-1, 0], p[-1, 2], 'o', color=C[i], ms=5, mec=SURF, mew=1)
        ax[1].plot(-p[:, 0], p[:, 1], C[i], lw=1.2); ax[1].plot(-p[-1, 0], p[-1, 1], 'o', color=C[i], ms=5, mec=SURF, mew=1)
    ax[0].set_xlabel('to the shooter\'s right, m'); ax[0].set_ylabel('towards the muzzle, m'); ax[0].set_title('Brass from above (gun at the origin, firing up the page)')
    ax[0].set_aspect('equal'); ax[0].legend(loc='upper right'); ax[0].plot(0, 0, 's', color=INK, ms=5)
    ax[1].set_xlabel('to the shooter\'s right, m'); ax[1].set_ylabel('height relative to the port, m'); ax[1].set_title('Side view: flight, bounce and roll (dot = rest)')
    save(fig, out, '07_brass.png')
    # 8 ---- sensitivity
    s = data['sensitivity']; base = data['auto']['rpm']
    fig, ax = plt.subplots(figsize=(8, 5)); labs = ['%s ×%.2g' % (d['param'].replace('_', ' '), d['factor']) for d in s]; val = [d['rpm'] - base for d in s]
    yy = np.arange(len(s))[::-1]; ax.barh(yy, val, height=0.62, color=C[0]); ax.set_yticks(yy); ax.set_yticklabels(labs); ax.axvline(0, color=INK, lw=0.8)
    for y_, v in zip(yy, val): ax.text(v + (1.5 if v >= 0 else -1.5), y_, '%+.0f' % v, va='center', ha='left' if v >= 0 else 'right', fontsize=7.5, color=MUTED)
    ax.set_xlabel('change in cyclic rate, rounds per minute (baseline %.0f)' % base); ax.set_title('What drives the cyclic rate: one parameter changed at a time'); ax.grid(axis='y', visible=False)
    ax.margins(x=0.12)
    save(fig, out, '08_cyclic_rate_sensitivity.png')
