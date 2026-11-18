"""Plots for the G44 V action simulation (called by sim.py). Simulation output only."""
import os, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
COL = dict(cci_standard_velocity='#1f6fb4', cci_mini_mag='#c0392b', cci_quiet_22='#2e8b57')
def make(D, here):
    os.makedirs(os.path.join(here, 'plots'), exist_ok=True); L = D['loads']
    def save(fig, name): fig.tight_layout(); fig.savefig(os.path.join(here, 'plots', name), dpi=110); plt.close(fig)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for k, q in L.items():
        b = q['ballistics']; t = np.arange(len(b['chamber_MPa'])) * b['dt'] * 1e3
        ax[0].plot(t, b['chamber_MPa'], color=COL[k], label=q['label']); ax[1].plot(b['bullet_mm'], b['bullet_mps'], color=COL[k], label='%s: %.0f m/s' % (k, q['pistol']['muzzle_velocity_mps']))
    ax[0].axhline(D['params']['p_map']['value'] / 1e6, color='k', ls=':', lw=1); ax[0].text(1.2, D['params']['p_map']['value'] / 1e6 + 2, 'SAAMI maximum average pressure', fontsize=8)
    ax[0].set_xlim(0, 2.0); ax[0].set_xlabel('time after ignition, ms'); ax[0].set_ylabel('breech pressure, MPa'); ax[0].legend(fontsize=8); ax[0].set_title('Internal ballistics, 102 mm barrel')
    ax[1].set_xlabel('bullet travel, mm'); ax[1].set_ylabel('bullet velocity, m/s'); ax[1].legend(fontsize=8); ax[1].set_title('Velocity along the bore')
    save(fig, '01_internal_ballistics.png')
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for k, q in L.items():
        c = q['cycle']; t = np.arange(len(c['slide_mm'])) * c['dt'] * 1e3
        ax[0].plot(t, c['slide_mm'], color=COL[k], label='%s: %s' % (k, q['outcome'])); ax[1].plot(t, c['slide_mps'], color=COL[k])
    m = D['mechanics']
    for y, lab in ((m['full_travel_mm'], 'frame stop'), (m['lock_open_mm'], 'lock-open'), (m['feed_mm'], 'feed pick-up'), (m['eject_mm'], 'ejector')):
        ax[0].axhline(y, color='k', ls=':', lw=0.8); ax[0].text(48, y + 0.5, lab, fontsize=7)
    ax[0].set_xlim(0, 60); ax[1].set_xlim(0, 60); ax[0].set_xlabel('time after the trigger break, ms'); ax[0].set_ylabel('slide travel, mm'); ax[0].legend(fontsize=7); ax[0].set_title('Slide cycle')
    ax[1].set_xlabel('time after the trigger break, ms'); ax[1].set_ylabel('slide velocity relative to the frame, m/s (+ rearward)'); ax[1].set_title('Slide velocity')
    save(fig, '02_slide_cycle.png')
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for k, q in L.items():
        for stn, ls in (('two_hand', '-'), ('one_hand', '--')):
            r = q['recoil'][stn]; t = np.arange(len(r['z_mm'])) * q['cycle']['dt'] * 1e3
            ax[0].plot(t, r['z_mm'], color=COL[k], ls=ls, label='%s, %s' % (k, stn)); ax[1].plot(t, r['pitch_up_deg'], color=COL[k], ls=ls)
    ax[0].set_xlabel('time after the trigger break, ms'); ax[0].set_ylabel('pistol displacement along the bore, mm (- = rearward)'); ax[0].legend(fontsize=6); ax[0].set_title('Recoil: translation')
    ax[1].set_xlabel('time after the trigger break, ms'); ax[1].set_ylabel('muzzle rise, degrees'); ax[1].set_title('Recoil: pitch about the wrist')
    save(fig, '03_recoil.png')
    fig, ax = plt.subplots(figsize=(6, 4)); f = D['firing']; t = np.arange(len(f['striker_mm'])) * f['dt'] * 1e3
    ax.plot(t, f['striker_mm'], 'k'); ax.set_xlabel('time after the trigger break, ms'); ax.set_ylabel('firing pin behind its fired position, mm')
    ax.set_title('Firing train: lock time %.2f ms, %.2f J' % (f['lock_time_s'] * 1e3, f['energy_J'])); save(fig, '04_firing_train.png')
